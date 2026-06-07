"""capcut_backend — P3 optional Node 13 render-candidate backend."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import capcut_backend as cc


def _timeline():
    return {"clips": [
        {"segment": 1, "source_path": "a.mp4", "start_sec": 0, "end_sec": 3,
         "duration_sec": 3, "timeline_in_sec": 0, "timeline_out_sec": 3,
         "text_overlay": "開場", "audio_policy": "music"},
        {"segment": 2, "source_path": "b.mp4", "start_sec": 5, "end_sec": 7,
         "duration_sec": 2, "timeline_in_sec": 3, "timeline_out_sec": 5,
         "text_overlay": "none", "audio_policy": "duck"},
    ]}


class DraftManifestTest(unittest.TestCase):
    def test_build_draft_manifest_shape(self):
        m = cc.build_draft_manifest(_timeline(), project_name="coffee")
        self.assertEqual(m["artifact_role"], "capcut_draft_manifest")
        self.assertEqual(m["version"], 1)
        self.assertEqual(m["backend"], "capcut_draft")
        # CapCut GUI export is a human/Computer-Use gate
        self.assertTrue(m["requires_human_or_computer_use"])
        # real proprietary .draft serialization is a version-gated boundary
        self.assertEqual(m["draft_serialization"]["status"], "pending")
        self.assertIn("capcut", m["draft_serialization"]["reason"].lower())
        self.assertEqual(m["project"]["name"], "coffee")

    def test_items_map_from_timeline(self):
        m = cc.build_draft_manifest(_timeline())
        items = m["video_track"]
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]["source_path"], "a.mp4")
        self.assertEqual(items[0]["source_in_sec"], 0)
        self.assertEqual(items[0]["source_out_sec"], 3)
        self.assertEqual(items[0]["timeline_in_sec"], 0)
        # text overlays preserved, "none" dropped
        texts = [t["text"] for t in m["text_overlays"]]
        self.assertIn("開場", texts)
        self.assertNotIn("none", texts)

    def test_writer_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "capcut_draft_manifest.json"
            res = cc.write_draft_manifest(_timeline(), p, project_name="x")
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(res["capcut_draft_manifest"], str(p))
            self.assertEqual(saved["artifact_role"], "capcut_draft_manifest")


class ExportManifestTest(unittest.TestCase):
    def test_export_is_render_candidate_not_accepted(self):
        draft = cc.build_draft_manifest(_timeline(), project_name="coffee")
        ex = cc.record_export(draft, "exported.mp4", export_method="human")
        self.assertEqual(ex["artifact_role"], "capcut_export_manifest")
        self.assertTrue(ex["render_candidate"])
        self.assertFalse(ex["accepted"])           # never auto-accepted
        self.assertTrue(ex["requires_node12_verify"])
        self.assertEqual(ex["export_method"], "human")
        self.assertEqual(ex["exported_video"], "exported.mp4")

    def test_export_method_validation(self):
        draft = cc.build_draft_manifest(_timeline())
        with self.assertRaises(ValueError):
            cc.record_export(draft, "x.mp4", export_method="auto_magic")

    def test_write_export_manifest_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            draft = cc.build_draft_manifest(_timeline())
            p = Path(d) / "capcut_export_manifest.json"
            res = cc.write_export_manifest(draft, "out.mp4", p, export_method="computer_use")
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(res["capcut_export_manifest"], str(p))
            self.assertFalse(saved["accepted"])
            self.assertEqual(saved["export_method"], "computer_use")


class CapcutCliTest(unittest.TestCase):
    def test_capcut_draft_cmd(self):
        import video_tools
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as d:
            timeline = Path(d) / "timeline_build.json"
            timeline.write_text(json.dumps(_timeline()), encoding="utf-8")
            out = str(Path(d) / "capcut_draft_manifest.json")
            video_tools.cmd_capcut_draft(
                SimpleNamespace(timeline=str(timeline), out=out, project="coffee"))
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "capcut_draft_manifest")
            self.assertTrue(saved["requires_human_or_computer_use"])


if __name__ == "__main__":
    unittest.main()
