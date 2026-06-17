import json
import math
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tools.workbench_export import (
    DEFAULT_OUT,
    apply_effects_to_video,
    export,
    prepare_export_plan,
    resolve_renderable_effects,
)


def _write(root: Path, name: str, payload) -> None:
    (root / name).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


def _make_root(tmp: str) -> Path:
    root = Path(tmp)
    vid = root / "clip.mp4"
    vid.write_bytes(b"\x00")
    (root / "music.wav").write_bytes(b"\x00")
    _write(root, "timeline.json", {"plan": [
        {"slot_index": 0, "source": str(vid), "slot_dur": 3.5,
         "extract_start": 0.0, "extract_dur": 3.5},
        {"slot_index": 1, "source": str(vid), "slot_dur": 2.0,
         "extract_start": 9.0, "extract_dur": 2.0},  # 9+2=11 > 10 drift
    ]})
    _write(root, "project_material_map.json", {
        "artifact_role": "project_material_map", "version": 1,
        "assets": [{"asset_id": "a0", "asset_type": "video",
                    "source": str(vid), "duration_sec": 10.0}], "needs": []})
    return root


def _patch(*ops):
    return {"artifact_role": "timeline_patch", "version": 1,
            "base_timeline_ref": "timeline.json", "patches": list(ops), "diagnostics": []}


class FakeRenderer:
    def __init__(self):
        self.calls = []

    def __call__(self, plan, music_path, out_path, mat_dir=None):
        self.calls.append({"plan": plan, "music": music_path, "out": out_path, "mat_dir": mat_dir})
        Path(out_path).write_bytes(b"\x00\x00")  # pretend ffmpeg wrote a file
        return out_path


class FakeEffectRenderer:
    def __init__(self):
        self.calls = []

    def __call__(self, artifact_root, input_path, output_path):
        self.calls.append({"root": artifact_root, "input": input_path, "output": output_path})
        Path(output_path).write_bytes(Path(input_path).read_bytes() + b"fx")
        return {"applied_count": 1, "skipped_count": 0, "out": output_path}


class WorkbenchExportTest(unittest.TestCase):
    def test_prepare_plan_applies_patch_and_aligns(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            prepared = prepare_export_plan(str(root), patch=_patch(
                {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 5.0}}))
        self.assertEqual(prepared["source"], "patch")
        # the drifted slot-1 window was clamped during alignment
        clip1 = next(c for c in prepared["plan"] if c["slot_index"] == 1)
        self.assertLessEqual(clip1["extract_start"] + clip1["extract_dur"], 10.0 + 1e-6)
        self.assertTrue(any(c["field"] == "extract_dur" for c in prepared["corrections"]))

    def test_export_uses_canonical_renderer_and_writes_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            fake = FakeRenderer()
            res = export(str(root), out=DEFAULT_OUT, renderer=fake)
            self.assertTrue(res["ok"])
            self.assertEqual(res["rendered_clips"], 2)
            self.assertEqual(len(fake.calls), 1)
            self.assertTrue(Path(res["out"]).exists())
            self.assertEqual(Path(res["out"]).name, "workbench_export.mp4")

    def test_export_refuses_protected_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            with self.assertRaises(ValueError):
                export(str(root), out="final.mp4", renderer=FakeRenderer())

    def test_export_never_writes_final_mp4(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            export(str(root), out=DEFAULT_OUT, renderer=FakeRenderer())
            self.assertFalse((Path(tmp) / "final.mp4").exists())

    def test_export_empty_plan_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root, "timeline.json", {"plan": [{"slot_index": 0, "source": None, "slot_dur": 1.0}]})
            with self.assertRaises(ValueError):
                export(str(root), out=DEFAULT_OUT, renderer=FakeRenderer())

    def test_resolve_renderable_effects_filters_supported_presets(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root, "effect_patch.json", {
                "artifact_role": "effect_patch",
                "version": 1,
                "patches": [
                    {"op": "add_effect", "effect_id": "fx_flash",
                     "after": {"preset": "flash", "target_slot_index": 0,
                               "start_sec": 0.0, "duration_sec": 0.5,
                               "intensity": 2}},
                    {"op": "add_effect", "effect_id": "fx_speed",
                     "after": {"preset": "speed_ramp_hint", "target_slot_index": 1,
                               "start_sec": 4.0, "duration_sec": 0.5, "intensity": 1}},
                ],
            })
            resolved = resolve_renderable_effects(str(root))
            self.assertEqual([e["effect_id"] for e in resolved["renderable"]], ["fx_flash"])
            self.assertEqual([e["effect_id"] for e in resolved["skipped"]], ["fx_speed"])

    def test_export_can_apply_effect_patch_to_workbench_export(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root, "effect_patch.json", {
                "artifact_role": "effect_patch",
                "version": 1,
                "patches": [
                    {"op": "add_effect", "effect_id": "fx_flash",
                     "after": {"preset": "flash", "target_slot_index": 0,
                               "start_sec": 0.0, "duration_sec": 0.5, "intensity": 1}},
                ],
            })
            renderer = FakeRenderer()
            effects = FakeEffectRenderer()
            res = export(str(root), out=DEFAULT_OUT, renderer=renderer,
                         render_effects=True, effect_renderer=effects)
            self.assertEqual(len(effects.calls), 1)
            self.assertEqual(res["effect_render"]["applied_count"], 1)
            self.assertTrue(Path(res["out"]).read_bytes().endswith(b"fx"))

    def test_export_without_effect_flag_preserves_existing_behavior(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = _make_root(tmp)
            _write(root, "effect_patch.json", {
                "artifact_role": "effect_patch",
                "version": 1,
                "patches": [
                    {"op": "add_effect", "effect_id": "fx_flash",
                     "after": {"preset": "flash", "target_slot_index": 0,
                               "start_sec": 0.0, "duration_sec": 0.5, "intensity": 1}},
                ],
            })
            effects = FakeEffectRenderer()
            res = export(str(root), out=DEFAULT_OUT, renderer=FakeRenderer(),
                         render_effects=False, effect_renderer=effects)
            self.assertNotIn("effect_render", res)
            self.assertEqual(effects.calls, [])

    @unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg not available")
    def test_apply_flash_effect_true_ffmpeg(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "source.mp4"
            out = root / "out.mp4"
            cmd = [
                "ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=black:s=160x90:d=1",
                "-pix_fmt", "yuv420p", str(source)
            ]
            subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
            _write(root, "timeline.json", {"plan": [
                {"slot_index": 0, "source": str(source), "slot_dur": 1.0,
                 "extract_start": 0.0, "extract_dur": 1.0},
            ]})
            _write(root, "project_material_map.json", {
                "artifact_role": "project_material_map", "version": 1,
                "assets": [{"asset_id": "a0", "asset_type": "video",
                            "source": str(source), "duration_sec": 1.0}],
                "needs": [],
            })
            _write(root, "effect_patch.json", {
                "artifact_role": "effect_patch",
                "version": 1,
                "patches": [
                    {"op": "add_effect", "effect_id": "fx_flash",
                     "after": {"preset": "flash", "target_slot_index": 0,
                               "start_sec": 0.0, "duration_sec": 0.5,
                               "intensity": 3}},
                ],
            })
            res = apply_effects_to_video(str(root), str(source), str(out))
            self.assertEqual(res["applied_count"], 1)
            self.assertTrue(out.is_file())
            self.assertGreater(out.stat().st_size, source.stat().st_size)


if __name__ == "__main__":
    unittest.main()
