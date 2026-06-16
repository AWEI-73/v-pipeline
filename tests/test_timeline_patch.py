import json
import tempfile
import unittest
from pathlib import Path

from tools.timeline_patch import (
    align_clip_to_contract,
    align_plan_to_contract,
    apply_patch,
    validate_patch,
)


def _write(root: Path, name: str, payload) -> None:
    (root / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_root(tmp: str) -> Path:
    root = Path(tmp)
    vid = root / "clip.mp4"
    vid.write_bytes(b"\x00")
    _write(root, "timeline.json", {
        "plan": [
            {"slot_index": 0, "source": str(vid), "slot_dur": 3.5,
             "extract_start": 0.0, "extract_dur": 3.5},
            {"slot_index": 1, "source": str(vid), "slot_dur": 2.0,
             "extract_start": 1.0, "extract_dur": 2.0},
            {"slot_index": 2, "source": str(vid), "slot_dur": 1.5,
             "extract_start": 0.0, "extract_dur": 1.5},
        ],
    })
    _write(root, "project_material_map.json", {
        "artifact_role": "project_material_map", "version": 1,
        "assets": [{"asset_id": "a0", "asset_type": "video",
                    "source": str(vid), "duration_sec": 10.0}],
        "needs": [],
    })
    return root


def _patch(*ops):
    return {"artifact_role": "timeline_patch", "version": 1,
            "base_timeline_ref": "timeline.json", "patches": list(ops), "diagnostics": []}


class TimelinePatchValidateTest(unittest.TestCase):
    def test_set_duration_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors = validate_patch(str(root), _patch(
                {"op": "set_duration", "slot_index": 0,
                 "before": {"duration_sec": 3.5}, "after": {"duration_sec": 5.0}}))
        self.assertTrue(ok, errors)

    def test_invalid_duration_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors = validate_patch(str(root), _patch(
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 0}}))
        self.assertFalse(ok)
        self.assertTrue(any("duration_sec" in e for e in errors))

    def test_set_source_window_valid(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors = validate_patch(str(root), _patch(
                {"op": "set_source_window", "slot_index": 0,
                 "after": {"source_start_sec": 2.2, "source_duration_sec": 5.0}}))
        self.assertTrue(ok, errors)

    def test_source_window_out_of_bounds_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            # asset duration is 10.0; 8 + 5 = 13 > 10
            ok, errors = validate_patch(str(root), _patch(
                {"op": "set_source_window", "slot_index": 0,
                 "after": {"source_start_sec": 8.0, "source_duration_sec": 5.0}}))
        self.assertFalse(ok)
        self.assertTrue(any("exceeds" in e for e in errors))

    def test_negative_source_start_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors = validate_patch(str(root), _patch(
                {"op": "set_source_window", "slot_index": 0,
                 "after": {"source_start_sec": -1.0, "source_duration_sec": 2.0}}))
        self.assertFalse(ok)

    def test_unknown_slot_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors = validate_patch(str(root), _patch(
                {"op": "set_duration", "slot_index": 99, "after": {"duration_sec": 2.0}}))
        self.assertFalse(ok)
        self.assertTrue(any("slot_index" in e for e in errors))

    def test_move_clip_out_of_range_fails(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors = validate_patch(str(root), _patch(
                {"op": "move_clip", "slot_index": 0, "after": {"new_index": 9}}))
        self.assertFalse(ok)


class TimelinePatchApplyTest(unittest.TestCase):
    def test_move_clip_is_deterministic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            result = apply_patch(str(root), _patch(
                {"op": "move_clip", "slot_index": 2, "after": {"new_index": 0}}))
        plan = result["plan"]
        # original scene ordering by slot_dur: [3.5, 2.0, 1.5]; moving last to front
        self.assertAlmostEqual(plan[0]["slot_dur"], 1.5)
        self.assertAlmostEqual(plan[1]["slot_dur"], 3.5)
        self.assertAlmostEqual(plan[2]["slot_dur"], 2.0)
        # slot_index is stable identity; order is represented by array position.
        self.assertEqual([c["slot_index"] for c in plan], [2, 0, 1])

    def test_move_then_edit_still_targets_original_slot_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            result = apply_patch(str(root), _patch(
                {"op": "move_clip", "slot_index": 2, "after": {"new_index": 0}},
                {"op": "set_duration", "slot_index": 2, "after": {"duration_sec": 4.25}},
            ))
        plan = result["plan"]
        self.assertEqual(plan[0]["slot_index"], 2)
        self.assertAlmostEqual(plan[0]["slot_dur"], 4.25)

    def test_apply_set_duration_and_window(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            result = apply_patch(str(root), _patch(
                {"op": "set_duration", "slot_index": 1, "after": {"duration_sec": 4.0}},
                {"op": "set_source_window", "slot_index": 1,
                 "after": {"source_start_sec": 2.0, "source_duration_sec": 4.0}}))
        clip = next(c for c in result["plan"] if c.get("scene_id") is None and c["slot_dur"] == 4.0)
        self.assertEqual(clip["extract_start"], 2.0)
        self.assertEqual(clip["extract_dur"], 4.0)

    def test_invalid_patch_raises_and_writes_nothing(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            with self.assertRaises(ValueError):
                apply_patch(str(root), _patch(
                    {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": -1}}))

    def test_apply_never_overwrites_timeline_json(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = (root / "timeline.json").read_text(encoding="utf-8")
            apply_patch(str(root), _patch(
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 9.0}}))
            after = (root / "timeline.json").read_text(encoding="utf-8")
            self.assertEqual(before, after)


class SpecAlignmentTest(unittest.TestCase):
    def test_clamps_source_window_to_material_duration(self):
        clip = {"slot_index": 0, "source": "a.mp4", "slot_dur": 5.0,
                "extract_start": 8.0, "extract_dur": 5.0}
        aligned, corr = align_clip_to_contract(clip, source_window=10.0)
        # 8 + 5 = 13 > 10  -> extract_dur clamped to 2.0
        self.assertEqual(aligned["extract_dur"], 2.0)
        self.assertTrue(any(c["field"] == "extract_dur" for c in corr))

    def test_image_clip_pinned_to_start_zero(self):
        clip = {"slot_index": 1, "source": "still.png", "slot_dur": 3.0,
                "extract_start": 4.0, "extract_dur": 3.0}
        aligned, corr = align_clip_to_contract(clip, source_window=None)
        self.assertEqual(aligned["extract_start"], 0.0)
        self.assertTrue(any(c["field"] == "extract_start" for c in corr))

    def test_missing_extract_dur_mirrors_slot_dur(self):
        clip = {"slot_index": 2, "source": "a.mp4", "slot_dur": 2.5,
                "extract_start": 0.0, "extract_dur": None}
        aligned, corr = align_clip_to_contract(clip, source_window=10.0)
        self.assertEqual(aligned["extract_dur"], 2.5)

    def test_apply_attaches_spec_alignment_report(self):
        # Base timeline carries pre-existing drift (extract window past the
        # material duration). A *valid* unrelated patch still triggers save-time
        # alignment over the whole plan, clamping and reporting the drift.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            vid = root / "clip.mp4"
            vid.write_bytes(b"\x00")
            _write(root, "timeline.json", {"plan": [
                {"slot_index": 0, "source": str(vid), "slot_dur": 5.0,
                 "extract_start": 9.0, "extract_dur": 5.0},  # 9+5=14 > 10 drift
                {"slot_index": 1, "source": str(vid), "slot_dur": 2.0,
                 "extract_start": 0.0, "extract_dur": 2.0},
            ]})
            _write(root, "project_material_map.json", {
                "artifact_role": "project_material_map", "version": 1,
                "assets": [{"asset_id": "a0", "asset_type": "video",
                            "source": str(vid), "duration_sec": 10.0}], "needs": []})
            result = apply_patch(str(root), _patch(
                {"op": "set_duration", "slot_index": 1, "after": {"duration_sec": 3.0}}))

        self.assertTrue(result["_spec_alignment"]["aligned"])
        self.assertGreaterEqual(result["_spec_alignment"]["correction_count"], 1)
        clip0 = next(c for c in result["plan"] if c["slot_index"] == 0)
        self.assertLessEqual(clip0["extract_start"] + clip0["extract_dur"], 10.0 + 1e-6)


if __name__ == "__main__":
    unittest.main()
