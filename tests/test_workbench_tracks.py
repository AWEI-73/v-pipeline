import json
import math
import tempfile
import unittest
from pathlib import Path

from tools.subtitle_patch import (
    apply_subtitle_patch,
    load_base_subtitles,
    validate_subtitle_patch,
)
from tools.audio_cue_patch import apply_audio_cue_patch, validate_audio_cue_patch
from tools.effect_patch import apply_effect_patch, validate_effect_patch
from tools.workbench_handoff import build_handoff


def _write(root: Path, name: str, payload) -> None:
    if isinstance(payload, str):
        (root / name).write_text(payload, encoding="utf-8")
    else:
        (root / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


SRT = ("1\n00:00:00,000 --> 00:00:03,000\nHello\n\n"
       "2\n00:00:03,000 --> 00:00:05,500\nWorld\n")


def _make_root(tmp: str) -> Path:
    root = Path(tmp)
    vid = root / "clip.mp4"
    vid.write_bytes(b"\x00")
    _write(root, "timeline.json", {"plan": [
        {"slot_index": 0, "segment": 1, "source": str(vid), "slot_dur": 3.0,
         "extract_start": 0.0, "extract_dur": 3.0},
        {"slot_index": 1, "segment": 1, "source": str(vid), "slot_dur": 2.5,
         "extract_start": 0.0, "extract_dur": 2.5},
    ]})
    _write(root, "project_material_map.json", {
        "artifact_role": "project_material_map", "version": 1,
        "assets": [{"asset_id": "a0", "asset_type": "video", "source": str(vid),
                    "duration_sec": 30.0, "scenes": []}], "needs": []})
    _write(root, "review_subtitles.srt", SRT)
    return root


def _sub_patch(*ops):
    return {"artifact_role": "subtitle_patch", "version": 1,
            "base_subtitle_ref": "review_subtitles.srt", "patches": list(ops), "diagnostics": []}


def _cue_patch(*ops):
    return {"artifact_role": "audio_cue_patch", "version": 1, "patches": list(ops), "diagnostics": []}


def _fx_patch(*ops):
    return {"artifact_role": "effect_patch", "version": 1, "patches": list(ops), "diagnostics": []}


# --------------------------------------------------------------------------- #
# Layer 1 — Subtitle
# --------------------------------------------------------------------------- #
class SubtitleTrackTest(unittest.TestCase):
    def test_A_parse_srt_into_track(self):
        with tempfile.TemporaryDirectory() as tmp:
            subs, name = load_base_subtitles(str(_make_root(tmp)))
        self.assertEqual(name, "review_subtitles.srt")
        self.assertEqual([s["id"] for s in subs], ["sub-1", "sub-2"])
        self.assertEqual(subs[0]["text"], "Hello")

    def test_B_edit_text_validates_and_applies(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            patch = _sub_patch({"op": "set_subtitle_text", "subtitle_id": "sub-1",
                                "after": {"text": "Hi there"}})
            ok, errors, _ = validate_subtitle_patch(str(root), patch)
            self.assertTrue(ok, errors)
            result = apply_subtitle_patch(str(root), patch)
            self.assertEqual(result["subtitles"][0]["text"], "Hi there")

    def test_C_timing_requires_positive_duration(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors, _ = validate_subtitle_patch(str(root), _sub_patch(
                {"op": "set_subtitle_timing", "subtitle_id": "sub-1",
                 "after": {"start_sec": 1.0, "duration_sec": 0}}))
            self.assertFalse(ok)
            self.assertTrue(any("duration_sec" in e for e in errors))

    def test_D_invalid_subtitle_id_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors, _ = validate_subtitle_patch(str(root), _sub_patch(
                {"op": "set_subtitle_text", "subtitle_id": "sub-99", "after": {"text": "x"}}))
            self.assertFalse(ok)
            with self.assertRaises(ValueError):
                apply_subtitle_patch(str(root), _sub_patch(
                    {"op": "set_subtitle_text", "subtitle_id": "sub-99", "after": {"text": "x"}}))

    def test_E_original_srt_unchanged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            before = (root / "review_subtitles.srt").read_text(encoding="utf-8")
            apply_subtitle_patch(str(root), _sub_patch(
                {"op": "set_subtitle_text", "subtitle_id": "sub-1", "after": {"text": "Changed"}}))
            self.assertEqual((root / "review_subtitles.srt").read_text(encoding="utf-8"), before)

    def test_overlap_is_warning_not_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            # push sub-1 to overlap sub-2
            ok, errors, diags = validate_subtitle_patch(str(root), _sub_patch(
                {"op": "set_subtitle_timing", "subtitle_id": "sub-1",
                 "after": {"start_sec": 0.0, "duration_sec": 4.0}}))
            self.assertTrue(ok, errors)
            self.assertTrue(any(d["code"] == "subtitle_overlap" for d in diags))


# --------------------------------------------------------------------------- #
# Layer 2 — Audio cue
# --------------------------------------------------------------------------- #
class AudioCueTrackTest(unittest.TestCase):
    def test_F_add_move_delete_produces_cues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            patch = _cue_patch(
                {"op": "add_cue", "cue_id": "c1", "after": {"time_sec": 1.0, "cue_type": "impact", "strength": 3}},
                {"op": "add_cue", "cue_id": "c2", "after": {"time_sec": 4.0, "cue_type": "bell", "strength": 2}},
                {"op": "move_cue", "cue_id": "c1", "after": {"time_sec": 2.0}},
                {"op": "delete_cue", "cue_id": "c2"})
            ok, errors, _ = validate_audio_cue_patch(str(root), patch)
            self.assertTrue(ok, errors)
            result = apply_audio_cue_patch(str(root), patch)
            self.assertEqual([c["cue_id"] for c in result["cues"]], ["c1"])
            self.assertEqual(result["cues"][0]["time_sec"], 2.0)

    def test_G_invalid_cue_type_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors, _ = validate_audio_cue_patch(str(root), _cue_patch(
                {"op": "add_cue", "cue_id": "c1", "after": {"time_sec": 1.0, "cue_type": "explosion", "strength": 3}}))
            self.assertFalse(ok)
            self.assertTrue(any("cue_type" in e for e in errors))

    def test_H_invalid_time_and_strength_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            # timeline duration is 5.5; 99 > 5.5 + 1
            ok1, e1, _ = validate_audio_cue_patch(str(root), _cue_patch(
                {"op": "add_cue", "cue_id": "c1", "after": {"time_sec": 99.0, "cue_type": "hit", "strength": 3}}))
            self.assertFalse(ok1)
            ok2, e2, _ = validate_audio_cue_patch(str(root), _cue_patch(
                {"op": "add_cue", "cue_id": "c2", "after": {"time_sec": 1.0, "cue_type": "hit", "strength": 9}}))
            self.assertFalse(ok2)
            ok3, e3, _ = validate_audio_cue_patch(str(root), _cue_patch(
                {"op": "add_cue", "cue_id": "c3", "after": {"time_sec": float("nan"), "cue_type": "hit", "strength": 3}}))
            self.assertFalse(ok3)

    def test_anchor_slot_missing_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors, _ = validate_audio_cue_patch(str(root), _cue_patch(
                {"op": "add_cue", "cue_id": "c1",
                 "after": {"time_sec": 1.0, "cue_type": "hit", "strength": 3, "anchor_clip_slot_index": 99}}))
            self.assertFalse(ok)
            self.assertTrue(any("anchor" in e for e in errors))


# --------------------------------------------------------------------------- #
# Layer 3 — Effect intent
# --------------------------------------------------------------------------- #
class EffectIntentTrackTest(unittest.TestCase):
    def test_I_add_preset_produces_effect(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            patch = _fx_patch({"op": "add_effect", "effect_id": "e1", "after": {
                "preset": "zoom_punch", "target_slot_index": 1, "start_sec": 3.2,
                "duration_sec": 0.6, "intensity": 3}})
            ok, errors, _ = validate_effect_patch(str(root), patch)
            self.assertTrue(ok, errors)
            result = apply_effect_patch(str(root), patch)
            self.assertEqual(result["effects"][0]["preset"], "zoom_punch")
            self.assertIn("intent only", result["note"])

    def test_J_invalid_preset_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors, _ = validate_effect_patch(str(root), _fx_patch(
                {"op": "add_effect", "effect_id": "e1", "after": {
                    "preset": "matrix_bullet_time", "target_slot_index": 0,
                    "start_sec": 0.0, "duration_sec": 0.5, "intensity": 3}}))
            self.assertFalse(ok)
            self.assertTrue(any("preset" in e for e in errors))

    def test_K_target_slot_missing_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            ok, errors, _ = validate_effect_patch(str(root), _fx_patch(
                {"op": "add_effect", "effect_id": "e1", "after": {
                    "preset": "flash", "target_slot_index": 99,
                    "start_sec": 0.0, "duration_sec": 0.5, "intensity": 3}}))
            self.assertFalse(ok)
            self.assertTrue(any("target_slot_index" in e for e in errors))

    def test_L_effect_window_outside_clip_fail_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            # slot 0 window is [0, 3]; start 2.8 + 0.6 = 3.4 > 3 -> fail (documented behaviour)
            ok, errors, _ = validate_effect_patch(str(root), _fx_patch(
                {"op": "add_effect", "effect_id": "e1", "after": {
                    "preset": "flash", "target_slot_index": 0,
                    "start_sec": 2.8, "duration_sec": 0.6, "intensity": 3}}))
            self.assertFalse(ok)
            self.assertTrue(any("outside target clip" in e for e in errors))

    def test_effect_patch_may_reference_effect_overlay_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            effect_asset = root / "light_sweep.webm"
            effect_asset.write_bytes(b"\x00")
            _write(root, "project_material_map.json", {
                "artifact_role": "project_material_map", "version": 1,
                "assets": [
                    {"asset_id": "a0", "asset_type": "video", "source": str(root / "clip.mp4"),
                     "duration_sec": 30.0, "scenes": []},
                    {"asset_id": "fx-light", "asset_type": "effect_overlay", "source": str(effect_asset),
                     "duration_sec": 1.2, "scenes": []},
                ], "needs": []})
            patch = _fx_patch({"op": "add_effect", "effect_id": "e1", "after": {
                "preset": "flash", "asset_id": "fx-light", "target_slot_index": 0,
                "start_sec": 0.0, "duration_sec": 0.5, "intensity": 3}})
            ok, errors, _ = validate_effect_patch(str(root), patch)
            self.assertTrue(ok, errors)
            result = apply_effect_patch(str(root), patch)
            self.assertEqual(result["effects"][0]["asset_id"], "fx-light")

    def test_effect_patch_rejects_non_effect_asset_reference(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            patch = _fx_patch({"op": "add_effect", "effect_id": "e1", "after": {
                "preset": "flash", "asset_id": "a0", "target_slot_index": 0,
                "start_sec": 0.0, "duration_sec": 0.5, "intensity": 3}})
            ok, errors, _ = validate_effect_patch(str(root), patch)
            self.assertFalse(ok)
            self.assertTrue(any("effect asset" in e for e in errors))


# --------------------------------------------------------------------------- #
# Layer 4 — Handoff
# --------------------------------------------------------------------------- #
class HandoffTest(unittest.TestCase):
    def test_O_handoff_references_and_counts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root, "timeline_patch.json", {"artifact_role": "timeline_patch", "version": 1,
                   "patches": [{"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 4}}]})
            _write(root, "subtitle_patch.json", _sub_patch(
                {"op": "set_subtitle_text", "subtitle_id": "sub-1", "after": {"text": "x"}},
                {"op": "set_subtitle_timing", "subtitle_id": "sub-2", "after": {"start_sec": 3, "duration_sec": 2}}))
            _write(root, "audio_cue_patch.json", _cue_patch(
                {"op": "add_cue", "cue_id": "c1", "after": {"time_sec": 1, "cue_type": "hit", "strength": 2}},
                {"op": "delete_cue", "cue_id": "c1"}))
            _write(root, "effect_patch.json", _fx_patch(
                {"op": "add_effect", "effect_id": "e1", "after": {
                    "preset": "flash", "target_slot_index": 0, "start_sec": 0, "duration_sec": 0.5, "intensity": 3}}))

            h = build_handoff(str(root))
        self.assertEqual(h["artifact_role"], "workbench_handoff")
        self.assertEqual(h["summary"]["timeline_edits"], 1)
        self.assertEqual(h["summary"]["subtitle_edits"], 2)
        self.assertEqual(h["summary"]["audio_cues"], 1)   # add_cue count
        self.assertEqual(h["summary"]["effect_intents"], 1)
        self.assertEqual(h["artifacts"]["subtitle_patch"], "subtitle_patch.json")
        self.assertEqual(h["next_action"], "review_workbench_route_back")
        self.assertEqual(
            {item["owner"] for item in h["route_back"]},
            {"build-planning", "subtitle-director", "audio-director", "effect-factory"},
        )


if __name__ == "__main__":
    unittest.main()
