import json
import tempfile
import unittest
from pathlib import Path

from tools.workbench_export import DEFAULT_OUT, export, prepare_export_plan


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


if __name__ == "__main__":
    unittest.main()
