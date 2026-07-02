import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.effect_factory_route_acceptance import (
    run_effect_factory_route_acceptance,
)


class EffectFactoryRouteAcceptanceTest(unittest.TestCase):
    def test_route_acceptance_runs_semantic_to_reviewed_worker_handoff(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = run_effect_factory_route_acceptance(
                root,
                request="electric lightning title opening with sparks and readable text",
                effect_role="opening_title",
                duration_sec=4,
            )

            self.assertTrue(report["ok"], report)
            self.assertFalse((root / "final.mp4").exists())
            self.assertEqual(report["summary"]["capability_decision"], "supported")
            self.assertEqual(report["summary"]["worker_review_status"], "pending_review")
            self.assertEqual(report["summary"]["handoff_status"], "ready_for_human_review")
            intent = json.loads((root / "effect_intent_plan.json").read_text(encoding="utf-8"))
            self.assertIsNone(intent["effects"][0]["template_id"])
            self.assertEqual(
                intent["effects"][0]["prompt_parameters"]["effect_build_spec"]["component"],
                "GenericRemotionEffect",
            )
            prompt_pack = json.loads((root / "remotion_prompt_pack.json").read_text(encoding="utf-8"))
            self.assertIsNone(prompt_pack["jobs"][0]["props"]["template_id"])
            self.assertNotIn("template_inferred:training_opening_title", prompt_pack["jobs"][0]["diagnostics"])
            worker_outputs = json.loads((root / "remotion_worker_outputs.json").read_text(encoding="utf-8"))
            self.assertTrue(worker_outputs["jobs"][0]["dry_run"])
            self.assertFalse(worker_outputs["jobs"][0]["playable_preview"])
            self.assertIn("not a playable", worker_outputs["jobs"][0]["preview_note"])
            for name in [
                "effect_design_brief.json",
                "effect_concept_options.json",
                "effect_concept_selection.json",
                "visual_technique_plan.json",
                "visual_technique_plan.confirmed.json",
                "effect_capability_review.json",
                "effect_intent_plan.json",
                "effect_revision_request.json",
                "timeline_build.json",
                "remotion_prompt_pack.json",
                "remotion_worker_outputs.json",
                "remotion_effect_review.json",
                "effect_handoff.json",
                "effect_factory_route_acceptance_report.json",
            ]:
                self.assertTrue((root / name).is_file(), name)

            capability = json.loads((root / "effect_capability_review.json").read_text(encoding="utf-8"))
            self.assertTrue(capability["production_handoff_allowed"])
            selection = json.loads((root / "effect_concept_selection.json").read_text(encoding="utf-8"))
            self.assertEqual(selection["artifact_role"], "effect_concept_selection")
            self.assertIn("downstream_requirements", selection)
            intent_with_design = json.loads((root / "effect_intent_plan.json").read_text(encoding="utf-8"))
            params = intent_with_design["effects"][0]["prompt_parameters"]
            self.assertIn("design_concept", params)
            self.assertIn("negative_rules", params)
            prompt_pack_with_design = json.loads((root / "remotion_prompt_pack.json").read_text(encoding="utf-8"))
            job_params = prompt_pack_with_design["jobs"][0]["props"]["prompt_parameters"]
            self.assertIn("design_concept", job_params)
            handoff = json.loads((root / "effect_handoff.json").read_text(encoding="utf-8"))
            self.assertFalse(handoff["boundary"]["owns_final_delivery"])
            self.assertFalse(handoff["boundary"]["owns_material_truth"])
            manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(manifest["effect_factory_route_acceptance_report"], "effect_factory_route_acceptance_report.json")
            self.assertEqual(manifest["effect_handoff"], "effect_handoff.json")
            self.assertEqual(manifest["remotion_effect_review"], "remotion_effect_review.json")
            self.assertEqual(manifest["remotion_worker_outputs"], "remotion_worker_outputs.json")
            self.assertEqual(manifest["artifacts"]["effect_handoff"]["path"], "effect_handoff.json")
            self.assertEqual(manifest["artifacts"]["effect_handoff"]["owner"], "effect_factory")
            self.assertEqual(manifest["artifacts"]["effect_handoff"]["status"], "accepted")

    def test_route_acceptance_fails_closed_for_unsupported_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = run_effect_factory_route_acceptance(
                root,
                request="make a realistic 3D dragon character fly through the footage",
                effect_role="opening_title",
                duration_sec=4,
            )

            self.assertFalse(report["ok"])
            self.assertEqual(report["failed_stage"], "effect_capability_review")
            self.assertFalse((root / "remotion_prompt_pack.json").exists())
            self.assertFalse((root / "final.mp4").exists())
            manifest = json.loads((root / "artifact_manifest.json").read_text(encoding="utf-8"))
            self.assertNotIn("effect_handoff", manifest)
            self.assertEqual(
                manifest["artifacts"]["effect_factory_route_acceptance_report"]["status"],
                "blocked",
            )

    def test_cli_runs_route_acceptance(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/effect_factory_route_acceptance.py",
                    "--out",
                    str(root),
                    "--request",
                    "terminal data stream opening title",
                    "--effect-role",
                    "opening_title",
                    "--duration-sec",
                    "4",
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(payload["artifact_role"], "effect_factory_route_acceptance_report")

    def test_closing_title_uses_generic_build_spec_without_auto_template(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = run_effect_factory_route_acceptance(
                root,
                request="warm legacy fire closing title with soft particles",
                effect_role="closing_title",
                duration_sec=4,
                display_text="精神傳承",
            )

            self.assertTrue(report["ok"], report)
            intent = json.loads((root / "effect_intent_plan.json").read_text(encoding="utf-8"))
            self.assertIsNone(intent["effects"][0]["template_id"])
            self.assertEqual(
                intent["effects"][0]["prompt_parameters"]["template_policy"],
                "templates_are_carriers_not_creative_locks",
            )
            prompt_pack = json.loads((root / "remotion_prompt_pack.json").read_text(encoding="utf-8"))
            self.assertIsNone(prompt_pack["jobs"][0]["props"]["template_id"])
            self.assertNotIn("template_inferred:clean_white_quote_card", prompt_pack["jobs"][0]["diagnostics"])
            self.assertFalse((root / "final.mp4").exists())


if __name__ == "__main__":
    unittest.main()
