import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.title_effect_lifecycle_qa import evaluate_title_effect_lifecycle_qa, write_title_effect_lifecycle_qa_for_run


class TitleEffectLifecycleQATest(unittest.TestCase):
    def test_title_without_end_time_blocks(self):
        result = evaluate_title_effect_lifecycle_qa({
            "effects": [{
                "effect_id": "opening_title",
                "section_id": "opening_story",
                "start_sec": 0.0,
                "must_clear_before_next_section": True,
                "next_section_start_sec": 7.0,
                "evidence_frame": "frames/opening.jpg",
            }],
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "title_effect_missing_end_time")

    def test_title_overlap_next_section_blocks(self):
        result = evaluate_title_effect_lifecycle_qa({
            "effects": [{
                "effect_id": "opening_title",
                "section_id": "opening_story",
                "start_sec": 0.0,
                "end_sec": 8.0,
                "max_duration_sec": 4.0,
                "must_clear_before_next_section": True,
                "next_section_start_sec": 7.0,
                "evidence_frame": "frames/opening.jpg",
            }],
        })

        self.assertFalse(result["pass"])
        rules = {item["rule"] for item in result["blocking"]}
        self.assertIn("title_effect_overlaps_next_section", rules)

    def test_missing_timing_evidence_blocks(self):
        result = evaluate_title_effect_lifecycle_qa({
            "effects": [{
                "effect_id": "opening_title",
                "section_id": "opening_story",
                "start_sec": 0.0,
                "end_sec": 3.0,
                "max_duration_sec": 4.0,
                "must_clear_before_next_section": True,
                "next_section_start_sec": 7.0,
            }],
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "title_effect_missing_timing_evidence")

    def test_valid_lifecycle_passes(self):
        result = evaluate_title_effect_lifecycle_qa({
            "effects": [{
                "effect_id": "opening_title",
                "section_id": "opening_story",
                "start_sec": 0.0,
                "end_sec": 3.0,
                "max_duration_sec": 4.0,
                "must_clear_before_next_section": True,
                "next_section_start_sec": 7.0,
                "evidence_frame": "frames/opening.jpg",
            }],
        })

        self.assertTrue(result["pass"], result)

    def test_write_for_run_reads_plan_and_writes_artifact(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "title_effect_lifecycle_plan.json").write_text(
                json.dumps({"effects": [{
                    "effect_id": "opening_title",
                    "section_id": "opening_story",
                    "start_sec": 0.0,
                    "end_sec": 3.0,
                    "max_duration_sec": 4.0,
                    "must_clear_before_next_section": True,
                    "next_section_start_sec": 7.0,
                    "evidence_frame": "frames/opening.jpg",
                }]}),
                encoding="utf-8",
            )

            report = write_title_effect_lifecycle_qa_for_run(root)

            self.assertTrue(report["pass"], report)
            self.assertTrue((root / "title_effect_lifecycle_qa.json").exists())


if __name__ == "__main__":
    unittest.main()
