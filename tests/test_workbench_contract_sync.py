import json
import tempfile
import unittest
from pathlib import Path

from tools.workbench_patch_to_contract import (
    OUT_CONTRACT,
    OUT_TIMELINE,
    PROTECTED_OUTPUTS,
    _safe_out,
    sync_patch_to_contract,
)
from tools.workbench_export import export


def _write(root: Path, name: str, payload) -> None:
    (root / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_root(tmp: str, with_contract: bool = True) -> Path:
    """Two segments (1: slots 0,1 / 2: slots 2,3), one video asset with scenes."""
    root = Path(tmp)
    vid = root / "clip.mp4"
    vid.write_bytes(b"\x00")
    _write(root, "timeline.json", {"plan": [
        {"slot_index": 0, "segment": 1, "source": str(vid), "scene_id": "clip:0",
         "slot_dur": 2.0, "extract_start": 1.0, "extract_dur": 2.0},
        {"slot_index": 1, "segment": 1, "source": str(vid), "scene_id": "clip:1",
         "slot_dur": 2.0, "extract_start": 5.0, "extract_dur": 2.0},
        {"slot_index": 2, "segment": 2, "source": str(vid), "scene_id": "clip:2",
         "slot_dur": 2.0, "extract_start": 10.0, "extract_dur": 2.0},
        {"slot_index": 3, "segment": 2, "source": str(vid), "scene_id": "clip:3",
         "slot_dur": 2.0, "extract_start": 15.0, "extract_dur": 2.0},
    ]})
    _write(root, "project_material_map.json", {
        "artifact_role": "project_material_map", "version": 1,
        "assets": [{"asset_id": "clip", "asset_type": "video", "source": str(vid),
                    "duration_sec": 30.0, "scenes": [
                        {"start": 0.0, "end": 4.0}, {"start": 4.0, "end": 8.0},
                        {"start": 9.0, "end": 13.0}, {"start": 14.0, "end": 18.0}]}],
        "needs": []})
    if with_contract:
        _write(root, "segment_contract.json", {
            "artifact_role": "segment_contract", "version": 1,
            "segments": [{"segment": 1, "duration_sec": 4.0},
                         {"segment": 2, "duration_sec": 4.0}]})
    return root


def _patch(*ops):
    return {"artifact_role": "timeline_patch", "version": 1,
            "base_timeline_ref": "timeline.json", "patches": list(ops), "diagnostics": []}


def _canonical_snapshot(root: Path):
    snap = {}
    for name in ("timeline.json", "segment_contract.json",
                 "project_material_map.json", "material_needs.json"):
        p = root / name
        snap[name] = p.read_text(encoding="utf-8") if p.exists() else None
    return snap


class ContractSyncTest(unittest.TestCase):
    # A
    def test_set_duration_makes_contract_draft_not_canonical(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = _canonical_snapshot(root)
            res = sync_patch_to_contract(str(root), _patch(
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 5.0}}))
            self.assertTrue(res["ok"], res.get("errors"))
            changes = res["workbench_contract_patch"]["changes"]
            self.assertEqual(len(changes), 1)
            self.assertEqual(changes[0]["op"], "segment_duration_suggestion")
            self.assertEqual(changes[0]["segment"], 1)
            self.assertEqual(changes[0]["to"]["requested_duration_sec"], 5.0)
            # the function never writes; canonical untouched
            self.assertEqual(before, _canonical_snapshot(root))

    # B
    def test_set_source_window_makes_material_override(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            res = sync_patch_to_contract(str(root), _patch(
                {"op": "set_source_window", "slot_index": 0,
                 "after": {"source_start_sec": 1.5, "source_duration_sec": 2.0}}))
        self.assertTrue(res["ok"], res.get("errors"))
        change = res["workbench_contract_patch"]["changes"][0]
        self.assertEqual(change["op"], "material_window_override")
        self.assertEqual(change["scene_id"], "clip:0")
        self.assertEqual(change["to"]["source_start_sec"], 1.5)

    # C
    def test_source_window_beyond_scene_bounds_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            # scene 0 is [0,4]; 3.0 + 2.0 = 5.0 > 4 -> fail
            res = sync_patch_to_contract(str(root), _patch(
                {"op": "set_source_window", "slot_index": 0,
                 "after": {"source_start_sec": 3.0, "source_duration_sec": 2.0}}))
        self.assertFalse(res["ok"])
        self.assertIsNone(res["workbench_contract_patch"])
        self.assertIsNone(res["patched_draft_timeline"])
        self.assertTrue(any("scene bounds" in e for e in res["errors"]))

    # D
    def test_move_within_segment_is_timeline_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            res = sync_patch_to_contract(str(root), _patch(
                {"op": "move_clip", "slot_index": 1, "after": {"new_index": 0}}))
        self.assertTrue(res["ok"], res.get("errors"))
        # no segment-order change emitted
        self.assertEqual(res["workbench_contract_patch"]["changes"], [])
        codes = {d["code"] for d in res["diagnostics"]}
        self.assertIn("intra_segment_reorder", codes)

    # E
    def test_cross_segment_move_is_unsupported_not_silent(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            # move slot 0 (segment 1) to the end among segment 2 clips
            res = sync_patch_to_contract(str(root), _patch(
                {"op": "move_clip", "slot_index": 0, "after": {"new_index": 3}}))
        self.assertTrue(res["ok"], res.get("errors"))
        self.assertEqual(res["workbench_contract_patch"]["changes"], [])
        codes = {d["code"] for d in res["diagnostics"]}
        self.assertIn("unsupported_for_contract_sync", codes)

    # F
    def test_slot_identity_preserved_after_move_then_edit(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            res = sync_patch_to_contract(str(root), _patch(
                {"op": "move_clip", "slot_index": 2, "after": {"new_index": 0}},
                {"op": "set_duration", "slot_index": 2, "after": {"duration_sec": 4.0}}))
        self.assertTrue(res["ok"], res.get("errors"))
        # duration suggestion still targets original clip identity (slot 2, segment 2)
        dur_change = next(c for c in res["workbench_contract_patch"]["changes"]
                          if c["op"] == "segment_duration_suggestion")
        self.assertEqual(dur_change["slot_index"], 2)
        self.assertEqual(dur_change["segment"], 2)
        # and the patched timeline draft moved slot 2 to the front with new dur
        plan = res["patched_draft_timeline"]["plan"]
        self.assertEqual(plan[0]["slot_index"], 2)
        self.assertEqual(plan[0]["slot_dur"], 4.0)

    # G
    def test_fail_closed_on_bad_patches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            for bad in (
                {"op": "set_duration", "slot_index": 99, "after": {"duration_sec": 2.0}},   # unknown slot
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 0}},       # non-positive
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": float("nan")}},  # NaN
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": float("inf")}},  # Inf
            ):
                res = sync_patch_to_contract(str(root), _patch(bad))
                self.assertFalse(res["ok"], bad)
                self.assertIsNone(res["workbench_contract_patch"])

    # H
    def test_safe_out_refuses_canonical_targets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            for canonical in ("timeline.json", "segment_contract.json",
                              "project_material_map.json", "material_needs.json", "final.mp4"):
                self.assertIn(canonical, PROTECTED_OUTPUTS | {"final.mp4", "timeline.json"})
                with self.assertRaises(ValueError):
                    _safe_out(root, canonical, OUT_CONTRACT)
            # allowed targets resolve fine
            self.assertEqual(_safe_out(root, OUT_CONTRACT, OUT_CONTRACT).name, OUT_CONTRACT)
            self.assertEqual(_safe_out(root, OUT_TIMELINE, OUT_TIMELINE).name, OUT_TIMELINE)

    def test_no_contract_present_still_syncs_with_null_ref(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp, with_contract=False)
            res = sync_patch_to_contract(str(root), _patch(
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 3.0}}))
        self.assertTrue(res["ok"])
        self.assertIsNone(res["workbench_contract_patch"]["base_contract_ref"])
        self.assertEqual(len(res["workbench_contract_patch"]["changes"]), 1)


class FakeRenderer:
    def __init__(self):
        self.calls = 0

    def __call__(self, plan, music_path, out_path, mat_dir=None):
        self.calls += 1
        Path(out_path).write_bytes(b"\x00\x00")
        return out_path


class PreviewRenderTest(unittest.TestCase):
    # I
    def test_preview_render_from_patched_draft_not_final(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            res = sync_patch_to_contract(str(root), _patch(
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 3.0}}))
            patched = res["patched_draft_timeline"]
            out = export(str(root), out="preview_render.mp4",
                         patched_timeline=patched, renderer=FakeRenderer())
            self.assertTrue(out["ok"])
            self.assertEqual(Path(out["out"]).name, "preview_render.mp4")
            self.assertTrue((Path(tmp) / "preview_render.mp4").exists())
            self.assertFalse((Path(tmp) / "final.mp4").exists())


if __name__ == "__main__":
    unittest.main()
