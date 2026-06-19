import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.effect_revision import (
    apply_revised_effect_intent_draft,
    build_effect_recipe_patch,
    build_effect_revision_request,
    build_revised_effect_intent_draft,
)
from video_pipeline_core.effect_contract import validate_effect_intent_plan


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


def _request(requests):
    return {
        "artifact_role": "effect_revision_request",
        "version": 1,
        "status": "pending" if requests else "empty",
        "summary": {"request_count": len(requests)},
        "requests": requests,
    }


def _effect_intent_plan():
    return {
        "artifact_role": "effect_intent_plan",
        "version": 1,
        "effects": [{
            "effect_id": "fx_lower",
            "role": "lower_third",
            "intent": "Chapter caption",
            "intensity": "low",
            "target": {"beat_id": "b01", "segment_id": "1"},
            "visual_language": ["clean lower third"],
            "required_for_story": False,
            "must_preserve_proof": True,
            "allowed_backends": ["motion_graphics"],
            "fallback": "none",
        }, {
            "effect_id": "fx_page_turn",
            "role": "chapter_transition",
            "intent": "Page turn",
            "intensity": "medium",
            "target": {"beat_id": "b02", "segment_id": "2"},
            "visual_language": ["paper"],
            "required_for_story": False,
            "must_preserve_proof": False,
            "allowed_backends": ["remotion_preview"],
            "fallback": "simple fade",
        }],
        "backend_boundary": {"neutral_contract": True},
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


class EffectRevisionDraftTest(unittest.TestCase):
    def test_revision_request_builds_noncanonical_recipe_patch(self):
        patch = build_effect_recipe_patch(_request([{
            "request_id": "fxrev_lower",
            "effect_id": "seg1_lower_third_1",
            "source_effect_id": "fx_lower",
            "segment": 1,
            "operation": "lower_third",
            "route": "implement_or_wire_effect_recipe",
            "reason": "no_render_output",
            "status": "pending",
        }, {
            "request_id": "fxrev_page",
            "effect_id": "fxintent_2_external_effect_1",
            "source_effect_id": "fx_page_turn",
            "segment": 2,
            "operation": "external_effect",
            "route": "route_to_node14_or_remotion_adapter",
            "reason": "no_render_output",
            "status": "pending",
        }]))

        self.assertEqual(patch["artifact_role"], "effect_recipe_patch")
        self.assertEqual(patch["version"], 1)
        self.assertEqual(patch["status"], "pending")
        self.assertEqual(
            [item["patch_type"] for item in patch["patches"]],
            ["wire_effect_recipe", "build_node14_adapter"],
        )
        self.assertNotIn("final.mp4", json.dumps(patch))

    def test_revised_effect_intent_draft_adds_backend_proposals_without_mutating_original(self):
        original = _effect_intent_plan()
        draft = build_revised_effect_intent_draft(_request([{
            "request_id": "fxrev_lower",
            "effect_id": "seg1_lower_third_1",
            "source_effect_id": "fx_lower",
            "segment": 1,
            "operation": "lower_third",
            "route": "implement_or_wire_effect_recipe",
            "reason": "no_render_output",
            "status": "pending",
        }, {
            "request_id": "fxrev_page",
            "effect_id": "fxintent_2_external_effect_1",
            "source_effect_id": "fx_page_turn",
            "segment": 2,
            "operation": "external_effect",
            "route": "route_to_node14_or_remotion_adapter",
            "reason": "no_render_output",
            "status": "pending",
        }]), original)

        self.assertEqual(draft["artifact_role"], "revised_effect_intent_plan_draft")
        self.assertTrue(draft["draft_only"])
        effects = {item["effect_id"]: item for item in draft["effect_intent_plan"]["effects"]}
        self.assertIn("ffmpeg_light_effects", effects["fx_lower"]["allowed_backends"])
        self.assertIn("remotion_render", effects["fx_page_turn"]["allowed_backends"])
        self.assertNotIn("ffmpeg_light_effects", original["effects"][0]["allowed_backends"])
        self.assertNotIn("remotion_render", original["effects"][1]["allowed_backends"])

    def test_revised_effect_intent_draft_fails_on_unknown_source_effect_id(self):
        with self.assertRaises(ValueError):
            build_revised_effect_intent_draft(_request([{
                "request_id": "fxrev_missing",
                "effect_id": "seg1_lower_third_1",
                "source_effect_id": "fx_missing",
                "segment": 1,
                "operation": "lower_third",
                "route": "implement_or_wire_effect_recipe",
                "reason": "no_render_output",
                "status": "pending",
            }]), _effect_intent_plan())

    def test_revision_draft_cli_writes_patch_and_optional_intent_draft(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "effect_revision_request.json"
            plan = root / "effect_intent_plan.json"
            patch = root / "effect_recipe_patch.json"
            intent_draft = root / "revised_effect_intent_plan.draft.json"
            request.write_text(json.dumps(_request([{
                "request_id": "fxrev_page",
                "effect_id": "fxintent_2_external_effect_1",
                "source_effect_id": "fx_page_turn",
                "segment": 2,
                "operation": "external_effect",
                "route": "route_to_node14_or_remotion_adapter",
                "reason": "no_render_output",
                "status": "pending",
            }])), encoding="utf-8")
            plan.write_text(json.dumps(_effect_intent_plan()), encoding="utf-8")

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "effect-revision-draft",
                "--request", str(request),
                "--out-patch", str(patch),
                "--effect-intent-plan", str(plan),
                "--out-intent-draft", str(intent_draft),
            ], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(patch.read_text(encoding="utf-8"))["artifact_role"], "effect_recipe_patch")
            self.assertEqual(
                json.loads(intent_draft.read_text(encoding="utf-8"))["artifact_role"],
                "revised_effect_intent_plan_draft",
            )

    def test_apply_revised_effect_intent_draft_requires_explicit_review_acceptance(self):
        draft = build_revised_effect_intent_draft(_request([{
            "request_id": "fxrev_page",
            "effect_id": "fxintent_2_external_effect_1",
            "source_effect_id": "fx_page_turn",
            "segment": 2,
            "operation": "external_effect",
            "route": "route_to_node14_or_remotion_adapter",
            "reason": "no_render_output",
            "status": "pending",
        }]), _effect_intent_plan())

        with self.assertRaises(ValueError):
            apply_revised_effect_intent_draft(draft, accept=False, reviewer="codex", reason="reviewed")
        with self.assertRaises(ValueError):
            apply_revised_effect_intent_draft(draft, accept=True, reviewer="", reason="reviewed")
        with self.assertRaises(ValueError):
            apply_revised_effect_intent_draft(draft, accept=True, reviewer="codex", reason="")

    def test_apply_revised_effect_intent_draft_returns_validator_clean_canonical_plan(self):
        original = _effect_intent_plan()
        draft = build_revised_effect_intent_draft(_request([{
            "request_id": "fxrev_page",
            "effect_id": "fxintent_2_external_effect_1",
            "source_effect_id": "fx_page_turn",
            "segment": 2,
            "operation": "external_effect",
            "route": "route_to_node14_or_remotion_adapter",
            "reason": "no_render_output",
            "status": "pending",
        }]), original)

        applied = apply_revised_effect_intent_draft(
            draft,
            accept=True,
            reviewer="codex",
            reason="accepted bounded Node14 draft",
        )

        self.assertEqual(applied["artifact_role"], "effect_intent_plan")
        self.assertNotIn("draft_only", applied)
        validate_effect_intent_plan(applied)
        effects = {item["effect_id"]: item for item in applied["effects"]}
        self.assertIn("remotion_render", effects["fx_page_turn"]["allowed_backends"])
        self.assertEqual(applied["node14_apply_lineage"]["reviewer"], "codex")
        self.assertEqual(
            applied["node14_apply_lineage"]["draft_artifact_role"],
            "revised_effect_intent_plan_draft",
        )
        self.assertNotIn("remotion_render", original["effects"][1]["allowed_backends"])

    def test_apply_revised_effect_intent_draft_cli_writes_reviewed_plan_without_overwriting_original(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            request = root / "effect_revision_request.json"
            plan = root / "effect_intent_plan.json"
            draft_path = root / "revised_effect_intent_plan.draft.json"
            reviewed_path = root / "effect_intent_plan.reviewed.json"
            original_payload = _effect_intent_plan()
            request.write_text(json.dumps(_request([{
                "request_id": "fxrev_lower",
                "effect_id": "seg1_lower_third_1",
                "source_effect_id": "fx_lower",
                "segment": 1,
                "operation": "lower_third",
                "route": "implement_or_wire_effect_recipe",
                "reason": "no_render_output",
                "status": "pending",
            }])), encoding="utf-8")
            plan.write_text(json.dumps(original_payload), encoding="utf-8")
            draft_path.write_text(json.dumps(
                build_revised_effect_intent_draft(json.loads(request.read_text()), original_payload)
            ), encoding="utf-8")
            original_bytes = plan.read_bytes()

            blocked = subprocess.run([
                sys.executable,
                "video_tools.py",
                "effect-revision-apply",
                "--draft", str(draft_path),
                "--out", str(reviewed_path),
                "--reviewer", "codex",
                "--reason", "accepted bounded Node14 draft",
            ], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)
            self.assertNotEqual(blocked.returncode, 0)
            self.assertFalse(reviewed_path.exists())

            proc = subprocess.run([
                sys.executable,
                "video_tools.py",
                "effect-revision-apply",
                "--draft", str(draft_path),
                "--out", str(reviewed_path),
                "--reviewer", "codex",
                "--reason", "accepted bounded Node14 draft",
                "--accept",
            ], cwd=Path(__file__).resolve().parents[1], text=True, capture_output=True)

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(plan.read_bytes(), original_bytes)
            reviewed = json.loads(reviewed_path.read_text(encoding="utf-8"))
            validate_effect_intent_plan(reviewed)
            self.assertIn("ffmpeg_light_effects", reviewed["effects"][0]["allowed_backends"])
            self.assertEqual(reviewed["node14_apply_lineage"]["reviewer"], "codex")


if __name__ == "__main__":
    unittest.main()
