from __future__ import annotations

import copy
import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, payload: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return path


def _decision_record(decision: str = "use the evidence-led progression") -> dict:
    return {
        "decision": decision,
        "decision_reason": "It changes the audience's understanding without inventing facts.",
        "evidence_refs": ["project_brief.json#goal"],
        "owner_or_agent": "owner",
        "status": "accepted",
        "remaining_unknowns": [],
        "allowed_downstream_interpretation": "Workers may realize the accepted causal job but may not rename factual events.",
    }


def _valid_package(root: Path) -> tuple[Path, Path, Path]:
    brief_path = _write(
        root / "project_brief.json",
        {"artifact_role": "project_brief", "goal": "show a training journey"},
    )
    story_path = _write(
        root / "story_decision_packet.json",
        {
            "artifact_role": "upstream_story_decision_packet",
            "schema_version": 1,
            "project_id": "fixture-project",
            "stage0_intent_ref": {
                "path": brief_path.name,
                "sha256": _sha256(brief_path),
            },
            "decision_mode": "ab_comparison",
            "hypotheses": [
                {
                    "hypothesis_id": "option_a",
                    "thesis": "Training turns a group into dependable peers.",
                    "causal_promise": "arrival -> practice -> mutual reliance",
                    "material_assumptions": ["group practice is visible"],
                    "sacrifices": ["individual hero framing"],
                    "evidence_refs": ["project_brief.json#goal"],
                },
                {
                    "hypothesis_id": "option_b",
                    "thesis": "Repeated practice makes difficult work ordinary.",
                    "causal_promise": "uncertainty -> repetition -> competence",
                    "material_assumptions": ["repeated actions are visible"],
                    "sacrifices": ["broad social-life coverage"],
                    "evidence_refs": ["project_brief.json#goal"],
                },
            ],
            "selected_hypothesis_id": "option_a",
            "decision_record": _decision_record(),
            "narrative_contract": {
                "subject": "the trainee cohort",
                "audience_change": "from seeing activities to seeing earned trust",
                "thesis": "Training turns a group into dependable peers.",
                "causal_arc": [
                    {
                        "beat_id": "beat_01",
                        "factual_claim": "the cohort begins as a newly gathered group",
                        "story_change": "individuals become a visible collective",
                        "entry_state": "separate arrivals",
                        "exit_state": "shared routine",
                        "evidence_refs": ["project_brief.json#goal"],
                    }
                ],
            },
            "remaining_unknowns": [
                {
                    "unknown_id": "u01",
                    "question": "which exact exercise supplies the opening detail",
                    "route_impact": "local",
                    "status": "open",
                    "owner_or_agent": "agent",
                    "resolution": None,
                    "evidence_refs": [],
                }
            ],
            "retired_story_intents": [],
            "deferred_due_to_material": [],
        },
    )
    segment_path = _write(
        root / "segment_story_contract.json",
        {
            "artifact_role": "segment_story_contract",
            "schema_version": 1,
            "project_id": "fixture-project",
            "story_decision_ref": {
                "path": story_path.name,
                "sha256": _sha256(story_path),
            },
            "stage2_status": "accepted",
            "segments": [
                {
                    "segment_id": "seg01",
                    "factual_claim": "the cohort begins with shared routine",
                    "story_change": "separate people become one working group",
                    "entry_state": "arrival",
                    "exit_state": "coordination",
                    "required_picture_roles": ["establish", "action", "result"],
                    "allowed_source_families": ["arrival", "group_training"],
                    "forbidden_substitutions": ["unrelated ceremony posed as training"],
                    "minimum_unique_windows": 3,
                    "duration_policy": {
                        "min_sec": 12,
                        "target_sec": 18,
                        "max_sec": 24,
                        "shorten_if_material_short": True,
                    },
                    "transition_in": {
                        "story_job": "open from place into people",
                        "continuity_rule": "keep location continuity",
                    },
                    "transition_out": {
                        "story_job": "hand shared rhythm to technical practice",
                        "continuity_rule": "match group motion",
                    },
                    "title_card_role": "opening_identity",
                    "defer_or_shorten_rule": "shorten before repeating an event family",
                    "review_question": "Does the segment visibly change arrival into coordination?",
                    "evidence_refs": ["project_brief.json#goal"],
                    "decision_record": _decision_record("use a three-role opening micro-story"),
                }
            ],
        },
    )
    evidence_path = _write(
        root / "evidence_need_map.json",
        {
            "artifact_role": "evidence_need_map",
            "schema_version": 1,
            "project_id": "fixture-project",
            "story_decision_ref": {
                "path": story_path.name,
                "sha256": _sha256(story_path),
            },
            "segment_contract_ref": {
                "path": segment_path.name,
                "sha256": _sha256(segment_path),
            },
            "material_truth_status": "not_started",
            "needs": [
                {
                    "need_id": "need_seg01_establish",
                    "segment_id": "seg01",
                    "picture_role": "establish",
                    "factual_claim": "where the cohort gathers",
                    "evidence_kind": "visual",
                    "required_observation": "the training place and cohort are both visible",
                    "allowed_source_families": ["arrival"],
                    "forbidden_substitutions": ["generic exterior without the cohort"],
                    "status": "needed",
                    "evidence_refs": [],
                },
                {
                    "need_id": "need_seg01_action",
                    "segment_id": "seg01",
                    "picture_role": "action",
                    "factual_claim": "the cohort performs one shared routine",
                    "evidence_kind": "visual",
                    "required_observation": "multiple members perform the same action",
                    "allowed_source_families": ["group_training"],
                    "forbidden_substitutions": ["posed group photo"],
                    "status": "needed",
                    "evidence_refs": [],
                },
                {
                    "need_id": "need_seg01_result",
                    "segment_id": "seg01",
                    "picture_role": "result",
                    "factual_claim": "the group reaches visible coordination",
                    "evidence_kind": "visual",
                    "required_observation": "a synchronized or completed group action",
                    "allowed_source_families": ["group_training"],
                    "forbidden_substitutions": ["unrelated applause"],
                    "status": "needed",
                    "evidence_refs": [],
                },
            ],
        },
    )
    return story_path, segment_path, evidence_path


class EditorialAmbiguityContractTest(unittest.TestCase):
    def test_skill_and_route_docs_name_the_same_stage2_gate(self):
        skill = (ROOT / "skills" / "editorial-ambiguity-loop.md").read_text(encoding="utf-8")
        index = (ROOT / "skills" / "INDEX.md").read_text(encoding="utf-8")
        runbook = (ROOT / "RUNBOOK.md").read_text(encoding="utf-8")
        boundary = (ROOT / "docs" / "stage-boundary-matrix.md").read_text(encoding="utf-8")
        for expected in [
            "story_decision_packet.json",
            "segment_story_contract.json",
            "evidence_need_map.json",
            "tools/editorial_ambiguity.py",
            "ready_for_stage3",
            "Stage cursor",
        ]:
            self.assertIn(expected, skill)
        self.assertIn("skills/editorial-ambiguity-loop.md", index)
        self.assertIn("editorial-ambiguity-loop", runbook)
        self.assertIn("stage2_ambiguity_gate_report.json", boundary)

    def test_valid_package_is_ready_for_stage3(self):
        from video_pipeline_core.editorial_ambiguity import validate_package

        with tempfile.TemporaryDirectory() as tmp:
            story, segment, evidence = _valid_package(Path(tmp))
            report = validate_package(story, segment, evidence)
        self.assertTrue(report["ok"], report)
        self.assertEqual("PASS", report["stage2_completion"])
        self.assertTrue(report["ready_for_stage3"])
        self.assertEqual([], report["errors"])

    def test_open_structural_unknown_blocks_stage2_completion(self):
        from video_pipeline_core.editorial_ambiguity import validate_package

        with tempfile.TemporaryDirectory() as tmp:
            story, segment, evidence = _valid_package(Path(tmp))
            payload = json.loads(story.read_text(encoding="utf-8"))
            payload["remaining_unknowns"][0]["route_impact"] = "structural"
            _write(story, payload)
            segment_payload = json.loads(segment.read_text(encoding="utf-8"))
            segment_payload["story_decision_ref"]["sha256"] = _sha256(story)
            _write(segment, segment_payload)
            evidence_payload = json.loads(evidence.read_text(encoding="utf-8"))
            evidence_payload["story_decision_ref"]["sha256"] = _sha256(story)
            evidence_payload["segment_contract_ref"]["sha256"] = _sha256(segment)
            _write(evidence, evidence_payload)
            report = validate_package(story, segment, evidence)
        self.assertFalse(report["ok"])
        self.assertIn("unresolved_high_impact_unknown", {e["code"] for e in report["errors"]})

    def test_placeholder_semantics_fail_closed_even_when_shape_is_complete(self):
        from video_pipeline_core.editorial_ambiguity import validate_package

        with tempfile.TemporaryDirectory() as tmp:
            story, segment, evidence = _valid_package(Path(tmp))
            payload = json.loads(story.read_text(encoding="utf-8"))
            payload["narrative_contract"]["thesis"] = "owner-approved evidence statement"
            _write(story, payload)
            segment_payload = json.loads(segment.read_text(encoding="utf-8"))
            segment_payload["story_decision_ref"]["sha256"] = _sha256(story)
            _write(segment, segment_payload)
            evidence_payload = json.loads(evidence.read_text(encoding="utf-8"))
            evidence_payload["story_decision_ref"]["sha256"] = _sha256(story)
            evidence_payload["segment_contract_ref"]["sha256"] = _sha256(segment)
            _write(evidence, evidence_payload)
            report = validate_package(story, segment, evidence)
        self.assertFalse(report["ok"])
        self.assertIn("narrative_contract_incomplete", {e["code"] for e in report["errors"]})

    def test_segment_need_reference_must_exist_in_evidence_map(self):
        from video_pipeline_core.editorial_ambiguity import validate_package

        with tempfile.TemporaryDirectory() as tmp:
            story, segment, evidence = _valid_package(Path(tmp))
            payload = json.loads(segment.read_text(encoding="utf-8"))
            payload["segments"][0]["evidence_refs"].append("N_MISSING_REACTION")
            _write(segment, payload)

            evidence_payload = json.loads(evidence.read_text(encoding="utf-8"))
            evidence_payload["segment_contract_ref"]["sha256"] = _sha256(segment)
            _write(evidence, evidence_payload)

            report = validate_package(story, segment, evidence)
        self.assertFalse(report["ok"])
        self.assertIn(
            "segment_evidence_need_ref_missing",
            {error["code"] for error in report["errors"]},
        )

    def test_ab_comparison_requires_two_materially_distinct_options(self):
        from video_pipeline_core.editorial_ambiguity import validate_package

        with tempfile.TemporaryDirectory() as tmp:
            story, segment, evidence = _valid_package(Path(tmp))
            payload = json.loads(story.read_text(encoding="utf-8"))
            payload["hypotheses"][1]["causal_promise"] = payload["hypotheses"][0]["causal_promise"]
            _write(story, payload)
            segment_payload = json.loads(segment.read_text(encoding="utf-8"))
            segment_payload["story_decision_ref"]["sha256"] = _sha256(story)
            _write(segment, segment_payload)
            evidence_payload = json.loads(evidence.read_text(encoding="utf-8"))
            evidence_payload["story_decision_ref"]["sha256"] = _sha256(story)
            evidence_payload["segment_contract_ref"]["sha256"] = _sha256(segment)
            _write(evidence, evidence_payload)
            report = validate_package(story, segment, evidence)
        self.assertFalse(report["ok"])
        self.assertIn("ab_options_not_distinct", {e["code"] for e in report["errors"]})

    def test_every_required_picture_role_needs_evidence_entry(self):
        from video_pipeline_core.editorial_ambiguity import validate_package

        with tempfile.TemporaryDirectory() as tmp:
            story, segment, evidence = _valid_package(Path(tmp))
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["needs"] = [need for need in payload["needs"] if need["picture_role"] != "result"]
            _write(evidence, payload)
            report = validate_package(story, segment, evidence)
        self.assertFalse(report["ok"])
        self.assertIn("picture_role_without_evidence_need", {e["code"] for e in report["errors"]})

    def test_cross_artifact_hash_drift_fails_closed(self):
        from video_pipeline_core.editorial_ambiguity import validate_package

        with tempfile.TemporaryDirectory() as tmp:
            story, segment, evidence = _valid_package(Path(tmp))
            payload = json.loads(segment.read_text(encoding="utf-8"))
            payload["story_decision_ref"]["sha256"] = "0" * 64
            _write(segment, payload)
            report = validate_package(story, segment, evidence)
        self.assertFalse(report["ok"])
        self.assertIn("story_decision_hash_mismatch", {e["code"] for e in report["errors"]})

    def test_material_defer_requires_owner_confirmation(self):
        from video_pipeline_core.editorial_ambiguity import validate_package

        with tempfile.TemporaryDirectory() as tmp:
            story, segment, evidence = _valid_package(Path(tmp))
            payload = json.loads(evidence.read_text(encoding="utf-8"))
            payload["needs"][0]["status"] = "deferred_due_to_material"
            payload["needs"][0]["material_defer"] = {
                "reason": "not_found",
                "owner_confirmed": False,
                "evidence_refs": ["inventory.json#missing"],
            }
            _write(evidence, payload)
            report = validate_package(story, segment, evidence)
        self.assertFalse(report["ok"])
        self.assertIn("unconfirmed_material_defer", {e["code"] for e in report["errors"]})

    def test_cli_writes_report_and_uses_exit_status(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            story, segment, evidence = _valid_package(root)
            report_path = root / "stage2_ambiguity_gate_report.json"
            completed = subprocess.run(
                [
                    sys.executable,
                    "tools/editorial_ambiguity.py",
                    "validate",
                    "--story-decision",
                    str(story),
                    "--segment-contract",
                    str(segment),
                    "--evidence-map",
                    str(evidence),
                    "--out",
                    str(report_path),
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )
            self.assertEqual(0, completed.returncode, completed.stdout + completed.stderr)
            self.assertTrue(report_path.is_file())
            report = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertTrue(report["ready_for_stage3"])


if __name__ == "__main__":
    unittest.main()
