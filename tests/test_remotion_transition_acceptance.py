import json
import tempfile
import unittest
from pathlib import Path


class RemotionTransitionAcceptanceTest(unittest.TestCase):
    def test_fixture_profiles_scale_jobs_without_final_output(self):
        from video_pipeline_core.remotion_acceptance import build_acceptance_fixture

        boundary = build_acceptance_fixture("boundary")
        micro = build_acceptance_fixture("micro")
        real = build_acceptance_fixture("real")

        self.assertEqual(len(boundary["effect_intent_plan"]["effects"]), 1)
        self.assertEqual(len(micro["effect_intent_plan"]["effects"]), 3)
        self.assertEqual(len(real["effect_intent_plan"]["effects"]), 4)
        self.assertTrue(all(
            request["route"] == "route_to_node14_or_remotion_adapter"
            for request in real["effect_revision_request"]["requests"]
        ))

    def test_micro_fixture_uses_reviewed_prompt_parameter_contracts(self):
        from video_pipeline_core.remotion_acceptance import build_acceptance_fixture
        from video_pipeline_core.remotion_effects import build_remotion_prompt_pack

        fixture = build_acceptance_fixture("micro")
        effects = {
            effect["effect_id"]: effect
            for effect in fixture["effect_intent_plan"]["effects"]
        }
        opening = effects["fx_title_intro_01"]
        transition = effects["fx_chapter_transition_01"]

        self.assertEqual(opening["template_id"], "training_opening_title")
        self.assertEqual(opening["presentation"]["variant"], "cinematic_collage_reveal")
        self.assertIn("gold_title_sweep", opening["prompt_parameters"]["motion_grammar"])
        self.assertEqual(
            opening["prompt_parameters"]["material_strategy"]["hero_source"],
            "reviewed_people_group",
        )
        self.assertEqual(transition["template_id"], "film_strip_transition_card")
        self.assertEqual(transition["presentation"]["variant"], "story_to_mv_film_transition")
        self.assertEqual(transition["prompt_parameters"]["transition_strength"], "impact")
        self.assertIn("hard_cut_bars", transition["prompt_parameters"]["motion_grammar"])

        pack = build_remotion_prompt_pack(
            fixture["effect_revision_request"],
            fixture["effect_intent_plan"],
            timeline=fixture["timeline_build"],
            output_dir="remotion_effects",
        )
        jobs = {job["source_effect_id"]: job for job in pack["jobs"]}
        self.assertEqual(
            jobs["fx_title_intro_01"]["props"]["prompt_parameters"]["effect_goal"],
            "formal_training_opening",
        )
        self.assertEqual(
            jobs["fx_chapter_transition_01"]["props"]["prompt_parameters"]["cut_point"],
            "midpoint_impact",
        )
        self.assertEqual(jobs["fx_chapter_transition_01"]["timing"]["duration_sec"], 1.8)

    def test_worker_output_evidence_refs_are_carried_into_review(self):
        from video_pipeline_core.remotion_effects import (
            build_remotion_prompt_pack,
            validate_remotion_worker_outputs,
        )
        from video_pipeline_core.remotion_acceptance import build_acceptance_fixture

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            fixture = build_acceptance_fixture("boundary")
            pack = build_remotion_prompt_pack(
                fixture["effect_revision_request"],
                fixture["effect_intent_plan"],
                timeline=fixture["timeline_build"],
                output_dir=str(root / "fx"),
            )
            preview = root / "preview.mp4"
            rendered = root / "rendered.mov"
            evidence = root / "contact_sheet.jpg"
            preview.write_bytes(b"preview")
            rendered.write_bytes(b"rendered")
            evidence.write_bytes(b"jpg")
            outputs = {
                "artifact_role": "remotion_worker_outputs",
                "version": 1,
                "jobs": [{
                    "job_id": pack["jobs"][0]["job_id"],
                    "source_effect_id": pack["jobs"][0]["source_effect_id"],
                    "status": "rendered",
                    "preview_file": str(preview),
                    "rendered_asset": str(rendered),
                    "duration_sec": pack["jobs"][0]["timing"]["duration_sec"],
                    "backend": "remotion",
                    "evidence_refs": [str(evidence)],
                }],
            }

            result = validate_remotion_worker_outputs(outputs, pack)

        self.assertTrue(result["ok"], result)
        item = result["review_artifact"]["items"][0]
        self.assertEqual(item["evidence_refs"], [str(evidence)])

    def test_acceptance_dry_run_writes_expected_artifacts(self):
        from video_pipeline_core.remotion_acceptance import run_remotion_transition_acceptance

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = run_remotion_transition_acceptance(root, profile="boundary")

            self.assertTrue(report["ok"], report)
            self.assertFalse(report["canonical_final_exists"])
            self.assertEqual(report["job_count"], 1)
            self.assertEqual(report["rendered_count"], 1)
            self.assertEqual(report["profile"], "boundary")
            self.assertTrue((root / "remotion_transition_acceptance_report.json").is_file())
            self.assertTrue((root / "remotion_prompt_pack.json").is_file())
            self.assertTrue((root / "remotion_worker_outputs.json").is_file())
            self.assertTrue((root / "remotion_effect_review.json").is_file())
            self.assertFalse((root / "final.mp4").exists())
            written = json.loads((root / "remotion_composite_draft_report.json").read_text(encoding="utf-8"))
            self.assertEqual(written["status"], "dry_run")

    def test_acceptance_prompt_pack_includes_reviewable_still_refs(self):
        from video_pipeline_core.remotion_acceptance import run_remotion_transition_acceptance

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = run_remotion_transition_acceptance(root, profile="micro")
            pack = json.loads((root / "remotion_prompt_pack.json").read_text(encoding="utf-8"))

            self.assertTrue(report["ok"], report)
            jobs = {job["source_effect_id"]: job for job in pack["jobs"]}
            for source_effect_id in ("fx_title_intro_01", "fx_chapter_transition_01"):
                refs = jobs[source_effect_id]["props"]["collage_media_refs"]
                self.assertGreaterEqual(len(refs), 3)
                self.assertTrue(any(ref.get("visual_role") == "people_group" for ref in refs))
                for ref in refs:
                    path = Path(ref["path"])
                    self.assertTrue(path.is_file(), ref)
                    self.assertEqual(path.suffix.lower(), ".png")
                    self.assertEqual(path.read_bytes()[:8], b"\x89PNG\r\n\x1a\n")


if __name__ == "__main__":
    unittest.main()
