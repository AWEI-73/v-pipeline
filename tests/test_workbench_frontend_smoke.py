import json
import tempfile
import unittest
from pathlib import Path

from tools.workbench_frontend_smoke import (
    SmokeError,
    build_duration_patch,
    build_replacement_patch,
    canonical_hashes,
    run_smoke,
    start_threaded_server,
)


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class WorkbenchFrontendSmokeTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.media = self.root / "clip.mp4"
        self.media.write_bytes(b"0123456789" * 20)
        self.replacement = self.root / "replacement.mp4"
        self.replacement.write_bytes(b"abcdefghij" * 20)
        _write_json(self.root / "timeline.json", {
            "plan": [{
                "slot_index": 0,
                "segment": 1,
                "source": str(self.media),
                "slot_dur": 2.0,
                "extract_start": 0.0,
                "extract_dur": 2.0,
                "asset_id": "a0",
                "caption": "demo",
            }]
        })
        _write_json(self.root / "project_material_map.json", {
            "artifact_role": "project_material_map",
            "version": 1,
            "assets": [{
                "asset_id": "a0",
                "asset_type": "video",
                "source": str(self.media),
                "duration_sec": 2.0,
                "scenes": [{"start": 0.0, "end": 2.0, "caption": "demo"}],
            }, {
                "asset_id": "b0",
                "asset_type": "video",
                "source": str(self.replacement),
                "duration_sec": 4.0,
                "scenes": [{"index": 1, "start": 1.0, "end": 3.0, "caption": "replacement"}],
            }],
        })
        (self.root / "final.mp4").write_bytes(b"canonical-final")
        self.server, self.thread, self.base_url = start_threaded_server(self.root)

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.tmp.cleanup()

    def test_build_duration_patch_uses_first_editable_clip(self):
        patch = build_duration_patch({
            "clips": [
                {"slot_index": 0, "status": "gap", "duration_sec": 1.0},
                {"slot_index": 1, "status": "ok", "duration_sec": 2.25},
            ]
        })
        self.assertEqual(patch["patches"][0]["slot_index"], 1)
        self.assertEqual(patch["patches"][0]["after"]["duration_sec"], 2.25)

    def test_build_replacement_patch_uses_material_candidate(self):
        patch = build_replacement_patch({
            "clips": [{"slot_index": 0, "status": "ok", "asset_id": "a0"}],
            "material_assets": [
                {"asset_id": "a0", "scenes": [{"scene_index": 0}]},
                {"asset_id": "b0", "scenes": [{"scene_index": 1}]},
            ],
        })
        self.assertEqual(patch["patches"][0]["op"], "replace_clip")
        self.assertEqual(patch["patches"][0]["after"], {"asset_id": "b0", "scene_index": 1})

    def test_run_smoke_writes_drafts_and_preserves_canonical(self):
        before = canonical_hashes(self.root)
        result = run_smoke(self.root, self.base_url)
        after = canonical_hashes(self.root)

        self.assertTrue(result["ok"])
        self.assertEqual(before, after)
        self.assertTrue((self.root / "timeline_patch.json").is_file())
        self.assertTrue((self.root / "patched_draft_timeline.json").is_file())
        self.assertTrue((self.root / "workbench_handoff.json").is_file())
        self.assertTrue((self.root / "workbench_review_report.json").is_file())
        self.assertTrue((self.root / "workbench_review_report.md").is_file())

    def test_run_smoke_can_exercise_replace_clip_flow(self):
        before = canonical_hashes(self.root)
        result = run_smoke(self.root, self.base_url, exercise_replace=True)
        after = canonical_hashes(self.root)

        self.assertTrue(result["ok"])
        self.assertEqual(result["exercised"], "replace_clip")
        self.assertEqual(before, after)
        patch = json.loads((self.root / "timeline_patch.json").read_text(encoding="utf-8"))
        self.assertEqual(patch["patches"][0]["op"], "replace_clip")
        draft = json.loads((self.root / "patched_draft_timeline.json").read_text(encoding="utf-8"))
        self.assertEqual(draft["plan"][0]["scene_id"], "b0:0")
        report = json.loads((self.root / "workbench_review_report.json").read_text(encoding="utf-8"))
        self.assertEqual(report["summary"]["replacement_edits"], 1)
        handoff = json.loads((self.root / "workbench_handoff.json").read_text(encoding="utf-8"))
        self.assertIn("timeline_patch", handoff["artifacts"])

    def test_run_smoke_fails_when_preview_has_no_editable_clip(self):
        _write_json(self.root / "timeline.json", {"plan": [{"slot_index": 0, "slot_dur": 1.0}]})
        with self.assertRaises(SmokeError) as cm:
            run_smoke(self.root, self.base_url)
        self.assertIn("editable clip", str(cm.exception))


if __name__ == "__main__":
    unittest.main()
