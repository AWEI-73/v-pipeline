import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.effect_factory_boundary import (
    run_effect_factory_boundary_acceptance,
)


class EffectFactoryBoundaryAcceptanceTest(unittest.TestCase):
    def test_acceptance_writes_bounded_effect_artifacts_without_final(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = run_effect_factory_boundary_acceptance(root)

            self.assertTrue(report["ok"], report)
            self.assertFalse((root / "final.mp4").exists())
            for name in [
                "effect_design_map.json",
                "effect_contract.json",
                "effect_intent_plan.json",
                "effect_revision_request.json",
                "timeline_build.json",
                "remotion_prompt_pack.json",
                "remotion_worker_outputs.json",
                "remotion_effect_review.json",
                "effect_review.json",
                "effect_handoff.json",
                "effect_factory_boundary_acceptance_report.json",
            ]:
                self.assertTrue((root / name).is_file(), name)

            handoff = json.loads((root / "effect_handoff.json").read_text(encoding="utf-8"))
            self.assertFalse(handoff["boundary"]["owns_final_delivery"])
            self.assertFalse(handoff["boundary"]["owns_material_truth"])
            self.assertEqual(handoff["status"], "ready_for_human_review")
            design_map = json.loads((root / "effect_design_map.json").read_text(encoding="utf-8"))
            self.assertEqual(
                design_map["dictionary_policy"]["role"],
                "reviewable_parameter_surface",
            )
            self.assertEqual(
                design_map["dictionary_policy"]["templates_are"],
                "worker_carriers_or_samples",
            )

    def test_semantic_families_do_not_collapse_to_one_generic_template(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            report = run_effect_factory_boundary_acceptance(root)
            signatures = report["style_signatures"]

            self.assertEqual(len(signatures), 4)
            self.assertTrue(report["summary"]["semantic_diversity_ok"])
            self.assertEqual(
                {item["style_family"] for item in signatures},
                {
                    "electric_lightning_energy",
                    "earthquake_crack_impact",
                    "mothers_day_heart_stage",
                    "warm_legacy_fire",
                },
            )
            visual_sets = {tuple(item["visual_primitives"]) for item in signatures}
            motion_sets = {tuple(item["motion_primitives"]) for item in signatures}
            self.assertEqual(len(visual_sets), 4)
            self.assertEqual(len(motion_sets), 4)

            pack = json.loads((root / "remotion_prompt_pack.json").read_text(encoding="utf-8"))
            for job in pack["jobs"]:
                params = job["props"]["prompt_parameters"]
                self.assertIn("style_family", params)
                self.assertIn("visual_primitives", params)
                self.assertIn("motion_primitives", params)
                self.assertIn("controls", params)

    def test_cli_writes_report(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/effect_factory_boundary_acceptance.py",
                    "--out",
                    str(root),
                    "--json",
                ],
                cwd=Path(__file__).resolve().parents[1],
                capture_output=True,
                text=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ok"], payload)
            self.assertEqual(
                payload["artifact_role"],
                "effect_factory_boundary_acceptance_report",
            )


if __name__ == "__main__":
    unittest.main()
