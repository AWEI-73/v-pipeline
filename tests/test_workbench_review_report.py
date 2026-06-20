import json
import tempfile
import unittest
from pathlib import Path

from tools.workbench_review_report import build_review_report, write_review_report


def _write_json(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class WorkbenchReviewReportTest(unittest.TestCase):
    def test_no_patch_reports_no_changes(self):
        with tempfile.TemporaryDirectory() as tmp:
            report = build_review_report(tmp)

        self.assertTrue(report["ok"])
        self.assertFalse(report["canonical_changed"])
        self.assertEqual(report["status"], "no_changes")
        self.assertEqual(report["summary"]["timeline_edits"], 0)
        self.assertEqual(report["edits"], [])

    def test_duration_and_source_window_edits_are_summarized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "timeline.json", {
                "plan": [
                    {
                        "slot_index": 0,
                        "segment": 1,
                        "source": "a.mov",
                        "slot_dur": 2.0,
                        "extract_start": 4.0,
                        "extract_dur": 2.0,
                    }
                ]
            })
            _write_json(root / "timeline_patch.json", {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [
                    {"op": "set_duration", "slot_index": 0, "after": {"duration_sec": 3.0}},
                    {
                        "op": "set_source_window",
                        "slot_index": 0,
                        "after": {"source_start_sec": 5.0, "source_duration_sec": 1.5},
                    },
                ],
            })

            report = build_review_report(tmp)

        self.assertEqual(report["status"], "changes_present")
        self.assertEqual(report["summary"]["timeline_edits"], 2)
        self.assertEqual(report["summary"]["duration_edits"], 1)
        self.assertEqual(report["summary"]["source_window_edits"], 1)
        self.assertEqual(report["edits"][0]["before"]["duration_sec"], 2.0)
        self.assertEqual(report["edits"][0]["after"]["duration_sec"], 3.0)
        self.assertEqual(report["edits"][1]["before"]["source_start_sec"], 4.0)
        self.assertEqual(report["edits"][1]["after"]["source_start_sec"], 5.0)

    def test_replace_clip_edit_lists_old_and_new_asset(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "timeline.json", {
                "plan": [
                    {
                        "slot_index": 3,
                        "segment": "S1",
                        "source": "old.mov",
                        "scene_id": "old:0",
                        "asset_id": "old",
                    }
                ]
            })
            _write_json(root / "timeline_patch.json", {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [
                    {"op": "replace_clip", "slot_index": 3, "after": {"asset_id": "new", "scene_index": 2}}
                ],
            })

            report = build_review_report(tmp)

        self.assertEqual(report["summary"]["replacement_edits"], 1)
        edit = report["edits"][0]
        self.assertEqual(edit["op"], "replace_clip")
        self.assertEqual(edit["before"]["asset_id"], "old")
        self.assertEqual(edit["after"]["asset_id"], "new")
        self.assertEqual(edit["after"]["scene_index"], 2)

    def test_quality_fallback_slots_are_surfaced_for_review(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "timeline.json", {
                "plan": [
                    {"slot_index": 0, "segment": 1, "source": "ok.mov", "duration_sec": 2.0},
                    {
                        "slot_index": 1,
                        "segment": 2,
                        "source": "fallback.mov",
                        "duration_sec": 2.0,
                        "scene_id": "asset:3",
                        "window_quality_fallback": True,
                    },
                ]
            })

            report = build_review_report(tmp)
            write_review_report(tmp)

            md = (root / "workbench_review_report.md").read_text(encoding="utf-8")

        self.assertEqual(report["summary"]["quality_fallback_slots"], 1)
        self.assertEqual(report["quality_fallback_slots"], [{
            "slot_index": 1,
            "segment": 2,
            "scene_id": "asset:3",
            "source": "fallback.mov",
        }])
        self.assertIn("quality_fallback_slots: 1", md)

    def test_subtitle_audio_and_effect_patch_counts_are_summarized(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_json(root / "subtitle_patch.json", {
                "artifact_role": "subtitle_patch",
                "patches": [{"op": "set_subtitle_text"}, {"op": "set_subtitle_timing"}],
            })
            _write_json(root / "audio_cue_patch.json", {
                "artifact_role": "audio_cue_patch",
                "patches": [{"op": "add_cue"}, {"op": "add_cue"}],
            })
            _write_json(root / "effect_patch.json", {
                "artifact_role": "effect_patch",
                "patches": [{"op": "add_effect"}],
            })

            report = build_review_report(tmp)

        self.assertEqual(report["summary"]["subtitle_edits"], 2)
        self.assertEqual(report["summary"]["audio_cues"], 2)
        self.assertEqual(report["summary"]["effect_intents"], 1)
        self.assertEqual(len(report["edits"]), 5)

    def test_write_review_report_writes_json_and_markdown_only(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            canonical = root / "timeline.json"
            canonical.write_text("[]", encoding="utf-8")
            write_review_report(tmp)

            json_report = root / "workbench_review_report.json"
            md_report = root / "workbench_review_report.md"
            self.assertTrue(json_report.is_file())
            self.assertTrue(md_report.is_file())
            self.assertEqual(canonical.read_text(encoding="utf-8"), "[]")
            payload = json.loads(json_report.read_text(encoding="utf-8"))
            self.assertFalse(payload["canonical_changed"])
            self.assertIn("canonical_changed: false", md_report.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
