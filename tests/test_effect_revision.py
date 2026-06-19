import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.effect_revision import build_effect_revision_request


def _review(gaps):
    return {
        "artifact_role": "light_effects_baseline_review",
        "light_effects_baseline_review_version": 1,
        "status": "gaps_found" if gaps else "pass",
        "metrics": {"gap_count": len(gaps)},
        "gaps": gaps,
    }


def _plan(items):
    return {
        "artifact_role": "light_effects_plan",
        "light_effects_plan_version": 1,
        "status": "planned",
        "items": items,
    }


class EffectRevisionRequestTest(unittest.TestCase):
    def test_no_gaps_produces_empty_revision_request(self):
        result = build_effect_revision_request(_review([]), _plan([]))

        self.assertEqual(result["artifact_role"], "effect_revision_request")
        self.assertEqual(result["version"], 1)
        self.assertEqual(result["status"], "empty")
        self.assertEqual(result["requests"], [])
        self.assertIsNone(result["next_action"])

    def test_ffmpeg_safe_gap_routes_to_recipe_implementation(self):
        result = build_effect_revision_request(
            _review([{
                "effect_id": "seg1_lower_third_1",
                "segment": 1,
                "operation": "lower_third",
                "reason": "no_render_output",
            }]),
            _plan([{
                "id": "seg1_lower_third_1",
                "segment": 1,
                "operation": "lower_third",
                "source_effect_id": "fx_lower",
            }]),
        )

        self.assertEqual(result["status"], "pending")
        self.assertEqual(result["summary"]["gap_count"], 1)
        request = result["requests"][0]
        self.assertEqual(request["route"], "implement_or_wire_effect_recipe")
        self.assertEqual(request["effect_id"], "seg1_lower_third_1")
        self.assertEqual(request["source_effect_id"], "fx_lower")
        self.assertEqual(request["operation"], "lower_third")
        self.assertEqual(request["status"], "pending")

    def test_external_backend_gap_routes_to_node14_or_remotion_adapter(self):
        result = build_effect_revision_request(
            _review([{
                "effect_id": "fxintent_2_external_effect_1",
                "segment": 2,
                "operation": "external_effect",
                "reason": "no_render_output",
            }]),
            _plan([{
                "id": "fxintent_2_external_effect_1",
                "segment": 2,
                "operation": "external_effect",
                "source_effect_id": "fx_page_turn",
                "next_action": "route_to_node14_or_remotion_adapter",
            }]),
        )

        request = result["requests"][0]
        self.assertEqual(request["route"], "route_to_node14_or_remotion_adapter")
        self.assertEqual(request["source_effect_id"], "fx_page_turn")
        self.assertTrue(request["evidence"]["planned_effect"]["next_action"])

    def test_malformed_baseline_review_fails_closed(self):
        with self.assertRaises(ValueError):
            build_effect_revision_request({"artifact_role": "wrong", "gaps": []}, None)
        with self.assertRaises(ValueError):
            build_effect_revision_request({
                "artifact_role": "light_effects_baseline_review",
                "light_effects_baseline_review_version": 1,
                "gaps": "not-list",
            }, None)

    def test_cli_writes_revision_request(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            review = root / "review.json"
            plan = root / "plan.json"
            out = root / "effect_revision_request.json"
            review.write_text(json.dumps(_review([{
                "effect_id": "fxintent_2_external_effect_1",
                "segment": 2,
                "operation": "external_effect",
                "reason": "no_render_output",
            }])), encoding="utf-8")
            plan.write_text(json.dumps(_plan([{
                "id": "fxintent_2_external_effect_1",
                "segment": 2,
                "operation": "external_effect",
                "source_effect_id": "fx_page_turn",
                "next_action": "route_to_node14_or_remotion_adapter",
            }])), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "effect-revision-request",
                "--baseline-review", str(review),
                "--light-effects-plan", str(plan),
                "--out", str(out),
            ], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            written = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(written["requests"][0]["route"], "route_to_node14_or_remotion_adapter")


if __name__ == "__main__":
    unittest.main()
