import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import reviewer_registry


ROOT = Path(__file__).resolve().parents[1]


class ReviewerRegistryTest(unittest.TestCase):
    @staticmethod
    def _editorial_review(*, findings=None):
        subject = {
            "path": "candidate.mp4",
            "artifact_role": "timeline_review_subject",
            "sha256": "a" * 64,
            "duration_sec": 10.0,
            "media_role": "current_candidate",
        }
        manifest = {
            "artifact_role": "editorial_evidence_manifest",
            "version": 1,
            "subject": dict(subject),
            "picture_stream_fingerprint": {"status": "bound", "sha256": "b" * 64},
            "audio_stream_fingerprint": {"status": "bound", "sha256": "c" * 64},
            "subtitle_fingerprint": {"status": "bound", "sha256": "d" * 64},
            "evidence_items": [{
                "evidence_id": "wall_1",
                "kind": "timeline_wall",
                "path": "walls/wall_30s_01.jpg",
                "sha256": "e" * 64,
                "generator_capability": "cap.verify.uniform-timeline-review.v1",
                "covered_timeline_window": {"start_sec": 0.0, "end_sec": 10.0},
                "source_binding": {"subject_sha256": subject["sha256"]},
                "limitations": ["navigation only"],
            }],
            "generated_at": "2026-07-19T00:00:00+00:00",
            "generator_version": "test/1",
            "reuse_policy": {"unknown_or_mismatched_subject": "fail_closed"},
            "invalidated_by": [],
            "parent_manifest": None,
        }
        return {
            "artifact_role": "editorial_review",
            "version": 2,
            "status": "ready_for_owner_verdict",
            "reviewer_identity": "editorial_reviewer",
            "review_mode": "full_context",
            "rubric_lenses": ["story_director", "editorial_timeline"],
            "authority": "findings_and_proposals_only",
            "forbidden_actions": [
                "canonical_state_mutation",
                "repair_or_construction",
                "creative_approval",
                "delivery_claim",
            ],
            "subject": subject,
            "evidence_manifest": manifest,
            "inspection_scope": {"timeline_windows": [[0.0, 10.0]]},
            "not_inspected": ["source speech identity"],
            "strengths": ["Clean evidence-backed candidate."],
            "findings": list(findings or []),
            "evidence_gaps": [],
            "human_creative_approval": False,
            "final_delivery_claimed": False,
        }

    def test_policy_expands_to_expected_roles(self):
        self.assertEqual(
            reviewer_registry.expand_review_policy("light"),
            ["material_producer", "technical_verify"],
        )
        self.assertEqual(
            reviewer_registry.expand_review_policy("normal"),
            ["story_director", "material_producer", "editorial_timeline", "technical_verify"],
        )
        self.assertIn("literary_editor", reviewer_registry.expand_review_policy("deep"))
        self.assertIn("effect_reviewer", reviewer_registry.expand_review_policy("deep"))

    def test_unknown_policy_fails_closed(self):
        with self.assertRaises(ValueError):
            reviewer_registry.expand_review_policy("everything")

    def test_registry_declares_eval_principles_for_every_role(self):
        registry = reviewer_registry.build_reviewer_registry()
        roles = {r["reviewer_role"]: r for r in registry["reviewers"]}
        for role in reviewer_registry.expand_review_policy("deep"):
            self.assertIn(role, roles)
            spec = roles[role]
            self.assertTrue(spec["input_artifacts"], role)
            self.assertTrue(spec["output_artifact"], role)
            self.assertIn(spec["gate_strength"], reviewer_registry.VALID_GATE_STRENGTHS)
            self.assertGreaterEqual(len(spec["eval_principles"]), 3, role)
            self.assertTrue(all(p["criterion"] and p["evidence"] and p["failure_route"]
                                for p in spec["eval_principles"]), role)

    def test_reviewer_write_contract_is_live_and_minimal_example_validates(self):
        contract = reviewer_registry.build_reviewer_write_contract()
        self.assertEqual(contract["artifact_role"], "reviewer_write_contract")
        self.assertIn("cap.editorial-reviewer.structured-review-validation.v1", contract["routing_capability_ids"])
        self.assertEqual(
            contract["validator_capability_id"],
            "cap.editorial-reviewer.structured-review-validation.v1",
        )
        result = reviewer_registry.validate_editorial_review(contract["minimal_valid_example"])
        self.assertTrue(result["ok"], result)

    def test_review_artifact_validator_accepts_valid_review(self):
        review = {
            "artifact_role": "artifact_review",
            "version": 1,
            "reviewer_role": "story_director",
            "review_type": "creative_review",
            "input_artifact_role": "story_soul_blueprint",
            "decision": "revise",
            "gate_strength": "revise",
            "scores": {"narrative_device": 3},
            "findings": [{"severity": "major", "message": "Ending lacks turn"}],
            "next_action": "revise_story_soul",
        }
        result = reviewer_registry.validate_review_artifact(review)
        self.assertTrue(result["ok"], result)

    def test_review_artifact_validator_accepts_guided_revision_schema(self):
        review = {
            "artifact_role": "artifact_review",
            "version": 1,
            "reviewer_role": "story_director",
            "review_type": "creative_review",
            "status": "revise",
            "decision": "revise",
            "blocking_level": "soft_block",
            "gate_strength": "revise",
            "findings": [{"severity": "major", "message": "The middle has no visual turn"}],
            "required_revisions": ["Add one visual turn before the resolution"],
            "recommended_actions": ["Revise director_shot_plan.json"],
            "handoff_to": "director_shot_plan",
            "can_continue_to_delivery": False,
        }

        result = reviewer_registry.validate_review_artifact(review)

        self.assertTrue(result["ok"], result)

    def test_review_artifact_validator_rejects_delivery_continue_with_soft_block(self):
        review = {
            "artifact_role": "artifact_review",
            "version": 1,
            "reviewer_role": "story_director",
            "status": "revise",
            "decision": "revise",
            "blocking_level": "soft_block",
            "gate_strength": "revise",
            "findings": [{"severity": "major", "message": "Pacing needs revision"}],
            "required_revisions": ["Shorten long holds"],
            "recommended_actions": ["Open workbench draft review"],
            "handoff_to": "workbench_edit",
            "can_continue_to_delivery": True,
        }

        result = reviewer_registry.validate_review_artifact(review)

        self.assertFalse(result["ok"])
        self.assertIn("can_continue_to_delivery must be false", "\n".join(result["errors"]))

    def test_review_artifact_validator_rejects_unknown_role_or_gate(self):
        bad_role = {
            "artifact_role": "artifact_review",
            "version": 1,
            "reviewer_role": "random_reviewer",
            "decision": "pass",
            "gate_strength": "advisory",
            "findings": [],
        }
        self.assertFalse(reviewer_registry.validate_review_artifact(bad_role)["ok"])
        bad_gate = dict(bad_role, reviewer_role="technical_verify", gate_strength="revise")
        self.assertFalse(reviewer_registry.validate_review_artifact(bad_gate)["ok"])

    def test_editorial_reviewer_identity_accepts_multiple_legacy_lenses(self):
        registry = reviewer_registry.build_reviewer_registry()
        contract = registry["editorial_reviewer_contract"]
        self.assertEqual(contract["reviewer_identity"], "editorial_reviewer")
        self.assertIn("story_director", {r["reviewer_role"] for r in registry["reviewers"]})
        self.assertIn("editorial_timeline", contract["rubric_lenses"])
        result = reviewer_registry.validate_editorial_review(self._editorial_review())
        self.assertTrue(result["ok"], result)

    def test_core_closure_rejects_source_binding_and_fingerprint_gaps(self):
        mismatch = self._editorial_review()
        mismatch["evidence_manifest"]["evidence_items"][0]["source_binding"] = {
            "subject_sha256": "b" * 64,
        }
        invalid_bound = self._editorial_review()
        invalid_bound["evidence_manifest"]["picture_stream_fingerprint"] = {
            "status": "bound",
            "sha256": "not-a-sha256",
        }
        unreasoned_unbound = self._editorial_review()
        unreasoned_unbound["evidence_manifest"]["audio_stream_fingerprint"] = {
            "status": "unbound",
        }
        results = {
            "source_binding_mismatch": not reviewer_registry.validate_editorial_review(mismatch)["ok"],
            "invalid_bound_fingerprint": not reviewer_registry.validate_editorial_review(invalid_bound)["ok"],
            "unreasoned_unbound_fingerprint": not reviewer_registry.validate_editorial_review(unreasoned_unbound)["ok"],
        }
        self.assertEqual(
            {
                "source_binding_mismatch": True,
                "invalid_bound_fingerprint": True,
                "unreasoned_unbound_fingerprint": True,
            },
            results,
        )

    def test_reviewer_capability_references_public_validation_entry(self):
        from video_pipeline_core.capability_catalog import load_live_catalog

        catalog = load_live_catalog(ROOT / "skills")
        self.assertTrue(catalog["ok"], catalog)
        card = next(
            card for card in catalog["cards"]
            if card["capability_id"] == "cap.editorial-reviewer.structured-review-validation.v1"
        )
        self.assertEqual(
            "video_tools.py reviewer-policy --validate-review",
            card["tool"],
        )
        self.assertIn("video_tools.py reviewer-policy", card["command"])

    def test_editorial_finding_binds_evidence_and_existing_route_capability(self):
        finding = {
            "finding_id": "f-contradiction",
            "rubric_id": "rendered-pixel-truth",
            "class": "objective",
            "priority": "high",
            "confidence": "high",
            "observation": "The visible wall contradicts the declared material role.",
            "interpretation": "The source binding needs owner review.",
            "why_it_matters": "The candidate may communicate the wrong event.",
            "fixable_at": "segment",
            "target": {"segment_id": "seg-1", "timeline_window": {"start_sec": 1.0, "end_sec": 2.0}},
            "evidence_refs": [{"evidence_id": "wall_1", "time_range": {"start_sec": 1.0, "end_sec": 2.0}}],
            "falsification_test": "Inspect the cited source frame and source-hash binding.",
            "requires_reopen": False,
            "lock_conflicts": [],
            "proposed_fix": {
                "route": "verify-delivery",
                "capability_id": "cap.verify.uniform-timeline-review.v1",
                "target": {"segment_id": "seg-1"},
                "expected_change": "Refresh the bounded evidence review.",
                "expected_unchanged": "Canonical timeline and source map remain unchanged.",
                "rerun_gates": ["timeline_review", "owner_verdict"],
                "requires_owner_or_integrator_verdict": True,
            },
        }
        result = reviewer_registry.validate_editorial_review(self._editorial_review(findings=[finding]))
        self.assertTrue(result["ok"], result)

    def test_editorial_rejects_unknown_capability_and_deterministic_taste_fail(self):
        finding = {
            "finding_id": "f-unknown",
            "rubric_id": "taste-rubric",
            "class": "taste",
            "priority": "low",
            "confidence": "medium",
            "observation": "The ending feels abrupt.",
            "interpretation": "The owner may prefer a longer hold.",
            "why_it_matters": "The ending controls the final emotional landing.",
            "fixable_at": "story",
            "target": {"segment_id": "ending"},
            "evidence_refs": [{"evidence_id": "wall_1", "time_range": {"start_sec": 8.0, "end_sec": 10.0}}],
            "human_taste_only": True,
            "machine_verdict": "fail",
            "requires_reopen": False,
            "lock_conflicts": [],
            "proposed_fix": {
                "route": "verify-delivery",
                "capability_id": "cap.unknown.repair.v1",
                "target": {"segment_id": "ending"},
                "expected_change": "Owner may request a bounded editorial revision.",
                "expected_unchanged": "No canonical state changes are made by the reviewer.",
                "rerun_gates": ["owner_verdict"],
                "requires_owner_or_integrator_verdict": True,
            },
        }
        result = reviewer_registry.validate_editorial_review(self._editorial_review(findings=[finding]))
        self.assertFalse(result["ok"], result)
        joined = "\n".join(result["errors"])
        self.assertIn("unknown capability_id", joined)
        self.assertIn("cannot carry a deterministic machine verdict", joined)

    def test_editorial_review_accepts_progression_and_no_existing_route_reopen(self):
        finding = {
            "finding_id": "f-lock-conflict",
            "rubric_id": "locked-truth-reopen",
            "class": "objective",
            "priority": "high",
            "confidence": "high",
            "observation": "The proposed recut conflicts with the locked picture order.",
            "interpretation": "The owner must reopen the locked decision before any recut.",
            "why_it_matters": "A silent recut would violate the accepted story boundary.",
            "fixable_at": "process",
            "target": {"timeline_window": {"start_sec": 2.0, "end_sec": 3.0}},
            "evidence_refs": [{"evidence_id": "wall_1", "time_range": {"start_sec": 2.0, "end_sec": 3.0}}],
            "falsification_test": "Compare the visible sequence with the locked context before proposing a recut.",
            "requires_reopen": True,
            "lock_conflicts": [{"lock_key": "allow_recut", "reason": "locked false"}],
            "proposed_fix": {
                "route": "no_existing_route",
                "capability_id": None,
                "target": {"timeline_window": {"start_sec": 2.0, "end_sec": 3.0}},
                "no_route_reason": "No registered route can change this accepted lock without an owner reopen verdict.",
                "requires_owner_or_integrator_verdict": True,
            },
        }
        review = self._editorial_review(findings=[finding])
        review["chapter_candidates"] = [{
            "chapter_id": "chapter-1",
            "timeline_window": {"start_sec": 0.0, "end_sec": 10.0},
            "opens_with": "Orientation and setup",
            "ends_with": "A new activity family begins",
            "information_gain": "The viewer can identify the transition into the activity sequence.",
            "evidence_refs": [{"evidence_id": "wall_1", "time_range": {"start_sec": 0.0, "end_sec": 10.0}}],
        }]
        result = reviewer_registry.validate_editorial_review(review)
        self.assertTrue(result["ok"], result)

        stagnant = json.loads(json.dumps(review))
        stagnant["chapter_candidates"][0]["ends_with"] = stagnant["chapter_candidates"][0]["opens_with"]
        stagnant_result = reviewer_registry.validate_editorial_review(stagnant)
        self.assertFalse(stagnant_result["ok"], stagnant_result)
        self.assertIn("no-progression", "\n".join(stagnant_result["errors"]))

    def test_cli_writes_policy_packet(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "reviewer_policy_packet.json"
            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "reviewer-policy",
                    "--level",
                    "deep",
                    "--out",
                    str(out),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            packet = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(packet["artifact_role"], "reviewer_policy_packet")
            self.assertEqual(packet["review_policy"]["level"], "deep")
            self.assertIn("generated_material_art_director", packet["enabled_reviewers"])

    def test_docs_and_command_manifest_reference_reviewer_policy(self):
        for rel in [
            "docs/artifact-reviewer-map.md",
            "docs/video-pipeline-operating-map.md",
            "skills/video-pipeline-route.md",
        ]:
            text = (ROOT / rel).read_text(encoding="utf-8")
            self.assertIn("reviewer-policy", text, rel)
            self.assertIn("eval", text.lower(), rel)

        proc = subprocess.run(
            [sys.executable, "video_tools.py", "commands-manifest"],
            cwd=ROOT,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
        self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
        self.assertIn("reviewer-policy", proc.stdout)


if __name__ == "__main__":
    unittest.main()
