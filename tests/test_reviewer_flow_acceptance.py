import json
import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from tools.reviewer_flow_acceptance import run_acceptance
from video_pipeline_core import reviewer_registry
from video_pipeline_core.timeline_review_packet import plan_evidence_reuse


ROOT = Path(__file__).resolve().parents[1]


class ReviewerFlowAcceptanceTest(unittest.TestCase):
    @staticmethod
    def _admission_subject(source_sha="a" * 64):
        return {
            "path": "candidate.wav",
            "artifact_role": "timeline_review_subject",
            "sha256": source_sha,
            "duration_sec": 60.0,
            "media_role": "current_candidate",
        }

    @classmethod
    def _admission_manifest(cls, *, source_sha="a" * 64, picture="b" * 64, audio="c" * 64, subtitle="d" * 64):
        subject = cls._admission_subject(source_sha)
        return {
            "artifact_role": "editorial_evidence_manifest",
            "version": 1,
            "subject": subject,
            "picture_stream_fingerprint": {"status": "bound", "sha256": picture},
            "audio_stream_fingerprint": {"status": "bound", "sha256": audio},
            "subtitle_fingerprint": {"status": "bound", "sha256": subtitle},
            "evidence_items": [
                {
                    "evidence_id": "timeline_wall_index",
                    "kind": "wall_index",
                    "path": "wall_index.json",
                    "sha256": "e" * 64,
                    "generator_capability": "cap.verify.uniform-timeline-review.v1",
                    "covered_timeline_window": {"start_sec": 0.0, "end_sec": 60.0},
                    "source_binding": {"subject_sha256": source_sha},
                    "limitations": ["navigation only"],
                },
                {
                    "evidence_id": "wall_1",
                    "kind": "timeline_wall",
                    "path": "walls/wall_30s_01.jpg",
                    "sha256": "f" * 64,
                    "generator_capability": "cap.verify.uniform-timeline-review.v1",
                    "covered_timeline_window": {"start_sec": 0.0, "end_sec": 30.0},
                    "source_binding": {"subject_sha256": source_sha},
                    "limitations": ["navigation only"],
                },
                {
                    "evidence_id": "wall_2",
                    "kind": "timeline_wall",
                    "path": "walls/wall_30s_02.jpg",
                    "sha256": "1" * 64,
                    "generator_capability": "cap.verify.uniform-timeline-review.v1",
                    "covered_timeline_window": {"start_sec": 30.0, "end_sec": 60.0},
                    "source_binding": {"subject_sha256": source_sha},
                    "limitations": ["navigation only"],
                },
                {
                    "evidence_id": "soundtrack_probe",
                    "kind": "audio_probe",
                    "path": "soundtrack_probe_report.json",
                    "sha256": "2" * 64,
                    "generator_capability": "cap.soundtrack-arranger.soundtrack-probe.v1",
                    "covered_timeline_window": {"start_sec": 0.0, "end_sec": 60.0},
                    "source_binding": {"subject_sha256": source_sha},
                    "limitations": [],
                },
                {
                    "evidence_id": "subtitle_binding",
                    "kind": "subtitle_binding",
                    "path": "subtitles.srt",
                    "sha256": "3" * 64,
                    "generator_capability": "cap.verify.uniform-timeline-review.v1",
                    "covered_timeline_window": {"start_sec": 0.0, "end_sec": 60.0},
                    "source_binding": {"subject_sha256": source_sha},
                    "limitations": [],
                },
            ],
            "generated_at": "2026-07-19T00:00:00+00:00",
            "generator_version": "admission/1",
            "reuse_policy": {"unknown_or_mismatched_subject": "fail_closed"},
            "invalidated_by": [],
            "parent_manifest": None,
        }

    @classmethod
    def _admission_review(cls, *, status="ready_for_owner_verdict", findings=None, evidence_gaps=None):
        subject = cls._admission_subject()
        return {
            "artifact_role": "editorial_review",
            "version": 2,
            "status": status,
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
            "evidence_manifest": cls._admission_manifest(),
            "inspection_scope": {"timeline_windows": [[0.0, 60.0]]},
            "not_inspected": ["continuous playback outside cited windows"],
            "strengths": ["Persisted evidence was inspected before requesting new evidence."],
            "findings": list(findings or []),
            "evidence_gaps": list(evidence_gaps or []),
            "human_creative_approval": False,
            "final_delivery_claimed": False,
        }

    @staticmethod
    def _admission_finding(*, finding_class="objective", capability_id="cap.verify.uniform-timeline-review.v1", machine_verdict=None):
        finding = {
            "finding_id": "f-contradiction",
            "rubric_id": "rendered-pixel-truth",
            "class": finding_class,
            "priority": "high" if finding_class != "taste" else "low",
            "confidence": "high" if finding_class == "objective" else "medium",
            "observation": "The visible wall contradicts the declared material role.",
            "interpretation": "The source binding needs owner review.",
            "why_it_matters": "The candidate may communicate the wrong event.",
            "fixable_at": "segment",
            "target": {"segment_id": "seg-1", "timeline_window": {"start_sec": 31.0, "end_sec": 32.0}},
            "evidence_refs": [{"evidence_id": "wall_2", "time_range": {"start_sec": 31.0, "end_sec": 32.0}}],
            "falsification_test": "Inspect the cited source frame and source-hash binding.",
            "requires_reopen": False,
            "lock_conflicts": [],
            "proposed_fix": {
                "route": "verify-delivery" if capability_id else "no_existing_route",
                "capability_id": capability_id,
                "target": {"segment_id": "seg-1"},
                "expected_change": "Refresh the bounded evidence review.",
                "expected_unchanged": "Canonical timeline and source map remain unchanged.",
                "rerun_gates": ["timeline_review", "owner_verdict"],
                "requires_owner_or_integrator_verdict": True,
            },
        }
        if finding_class == "taste":
            finding["human_taste_only"] = True
            finding["observation"] = "The ending feels abrupt to this reviewer."
            finding["interpretation"] = "An owner may prefer a longer landing hold."
        if machine_verdict is not None:
            finding["machine_verdict"] = machine_verdict
        return finding

    def test_admission_v1_proves_editorial_review_boundaries_and_reuse(self):
        root = ROOT / ".tmp" / "editorial_reviewer_convergence" / "admission_v1"
        root.mkdir(parents=True, exist_ok=True)
        tiny_media = ROOT / "assets" / "sfx" / "hit_1.wav"
        if tiny_media.is_file() and not (root / "candidate.wav").exists():
            shutil.copyfile(tiny_media, root / "candidate.wav")
        frozen = root / "s9_governance_frozen_evidence.md"
        if not frozen.exists():
            frozen.write_text(
                "Frozen evidence only.\n"
                "The current handoff/current-state claim is stale.\n"
                "The required work order is missing.\n"
                "The receipt, attestation, and manifest are missing.\n"
                "The output sample-rate decision is not recorded.\n"
                "The latest finding is absent from the ledger.\n",
                encoding="utf-8",
            )

        def write_once(name, payload):
            path = root / name
            if not path.exists():
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            return json.loads(path.read_text(encoding="utf-8"))

        clean = self._admission_review()
        contradictory = self._admission_review(findings=[self._admission_finding()])
        insufficient = self._admission_review(
            status="unknown",
            evidence_gaps=[{"gap_id": "gap-1", "reason": "No continuous playback evidence for the cited window."}],
        )
        taste_fail = self._admission_review(findings=[self._admission_finding(finding_class="taste", machine_verdict="fail")])
        unknown_capability = self._admission_review(findings=[self._admission_finding(capability_id="cap.unknown.repair.v1")])
        claimed = dict(clean, human_creative_approval=True, final_delivery_claimed=True)
        legacy = {
            "artifact_role": "artifact_review",
            "version": 1,
            "reviewer_role": "story_director",
            "decision": "pass",
            "gate_strength": "revise",
            "findings": [],
        }
        fixtures = {
            "clean.json": clean,
            "contradictory.json": contradictory,
            "insufficient_evidence.json": insufficient,
            "taste_machine_fail.json": taste_fail,
            "unknown_capability.json": unknown_capability,
            "approval_delivery_claim.json": claimed,
            "legacy_artifact_review_v1.json": legacy,
            "multiple_lenses.json": clean,
        }
        for name, payload in fixtures.items():
            write_once(name, payload)
        write_once("editorial_evidence_manifest.json", self._admission_manifest())

        results = {}
        results["clean_no_material_findings"] = reviewer_registry.validate_editorial_review(clean)["ok"] and not clean["findings"]
        contradictory_result = reviewer_registry.validate_editorial_review(contradictory)
        results["contradictory_claim_evidence_bound"] = contradictory_result["ok"] and bool(contradictory["findings"][0]["evidence_refs"])
        results["insufficient_evidence_unknown"] = reviewer_registry.validate_editorial_review(insufficient)["ok"] and insufficient["status"] == "unknown" and bool(insufficient["evidence_gaps"])
        results["taste_not_machine_fail"] = not reviewer_registry.validate_editorial_review(taste_fail)["ok"]
        results["unknown_capability_rejected"] = not reviewer_registry.validate_editorial_review(unknown_capability)["ok"]
        valid_result = reviewer_registry.validate_editorial_review(contradictory)
        results["valid_existing_route_capability"] = valid_result["ok"]

        previous = self._admission_manifest()
        unchanged = self._admission_manifest(source_sha="1" * 64)
        audio_only = self._admission_manifest(source_sha="2" * 64, audio="4" * 64)
        subtitle_only = self._admission_manifest(source_sha="3" * 64, subtitle="5" * 64)
        picture_changed = self._admission_manifest(source_sha="6" * 64, picture="e" * 64)
        unchanged_plan = plan_evidence_reuse(previous, unchanged)
        audio_plan = plan_evidence_reuse(previous, audio_only)
        subtitle_plan = plan_evidence_reuse(previous, subtitle_only)
        picture_plan = plan_evidence_reuse(previous, picture_changed, changed_picture_window={"start_sec": 35.0, "end_sec": 40.0})
        results["unchanged_hashes_reused"] = unchanged_plan["reason"] == "identical_picture_audio_subtitle"
        results["audio_only_reuses_visual_invalidates_audio"] = "wall_1" in audio_plan["reused_evidence_ids"] and "soundtrack_probe" in audio_plan["regenerated_evidence_ids"]
        results["picture_change_invalidates_intersecting_wall"] = "wall_2" in picture_plan["invalidated_evidence_ids"] and "wall_1" in picture_plan["reused_evidence_ids"]
        results["subtitle_only_regenerates_binding"] = "subtitle_binding" in subtitle_plan["regenerated_evidence_ids"]
        results["approval_delivery_claims_rejected"] = not reviewer_registry.validate_editorial_review(claimed)["ok"]
        results["legacy_v1_validates"] = reviewer_registry.validate_review_artifact(legacy)["ok"]
        results["one_identity_multiple_lenses"] = clean["reviewer_identity"] == "editorial_reviewer" and len(clean["rubric_lenses"]) == 2

        frozen_text = frozen.read_text(encoding="utf-8")
        onboarding = {
            "stale_handoff_current_state_claim": "stale" in frozen_text and "current handoff" in frozen_text,
            "missing_work_order": "work order is missing" in frozen_text,
            "missing_receipt_attestation_manifest": all(term in frozen_text for term in ("receipt", "attestation", "manifest")),
            "output_sample_rate_decision_not_recorded": "sample-rate decision is not recorded" in frozen_text,
            "latest_finding_absent_from_ledger": "latest finding is absent from the ledger" in frozen_text,
        }
        results["s9_onboarding_flags_frozen_evidence"] = all(onboarding.values())
        self.assertTrue(all(results.values()), results)

        report = {
            "artifact_role": "editorial_reviewer_admission_v1",
            "version": 1,
            "status": "PASS",
            "root": str(root),
            "cases": results,
            "reuse_plans": {
                "unchanged": unchanged_plan,
                "audio_only": audio_plan,
                "subtitle_only": subtitle_plan,
                "bounded_picture": picture_plan,
            },
            "onboarding_flags": onboarding,
            "human_creative_approval": False,
            "final_delivery_claimed": False,
            "fixture_sha256": {
                str(path.relative_to(root).as_posix()): hashlib.sha256(path.read_bytes()).hexdigest()
                for path in sorted(root.iterdir()) if path.is_file()
            },
        }
        report_path = root / "admission_report.json"
        if not report_path.exists():
            report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        else:
            existing = json.loads(report_path.read_text(encoding="utf-8"))
            self.assertEqual(existing["status"], "PASS")
            self.assertEqual(existing["cases"], results)
    def test_normal_route_smoke_validates_core_reviewers(self):
        result = run_acceptance(level="normal", scenario="route_smoke")
        self.assertTrue(result["ok"], result)
        self.assertEqual(
            result["scenario_reviewers"],
            ["story_director", "material_producer", "editorial_timeline", "technical_verify"],
        )
        self.assertTrue(result["negative_checks"]["technical_verify_rejects_revise_gate"])

    def test_upstream_story_requires_deep_policy(self):
        result = run_acceptance(level="deep", scenario="upstream_story")
        self.assertTrue(result["ok"], result)
        roles = {r["reviewer_role"] for r in result["reviews"]}
        self.assertIn("literary_editor", roles)
        self.assertIn("story_director", roles)
        self.assertIn("generated_material_art_director", roles)

    def test_effects_brownfield_reviewers_are_covered(self):
        result = run_acceptance(level="deep", scenario="effects_brownfield")
        self.assertTrue(result["ok"], result)
        roles = {r["reviewer_role"] for r in result["reviews"]}
        self.assertEqual(
            roles,
            {"editorial_timeline", "audio_subtitle_reviewer", "effect_reviewer", "technical_verify"},
        )

    def test_light_policy_fails_for_effects_brownfield(self):
        result = run_acceptance(level="light", scenario="effects_brownfield")
        self.assertFalse(result["ok"], result)
        self.assertTrue(any("missing scenario reviewer" in e for e in result["errors"]))

    def test_cli_writes_report_packet_and_review_artifacts(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            report = root / "reviewer_flow_acceptance.json"
            artifacts = root / "reviewer_artifacts"
            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/reviewer_flow_acceptance.py",
                    "--level",
                    "deep",
                    "--scenario",
                    "all",
                    "--artifact-dir",
                    str(artifacts),
                    "--out",
                    str(report),
                ],
                cwd=ROOT,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )
            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            result = json.loads(report.read_text(encoding="utf-8"))
            self.assertTrue(result["ok"], result)
            self.assertTrue((artifacts / "reviewer_policy_packet.json").is_file())
            self.assertTrue((artifacts / "artifact_reviews" / "effect_reviewer.artifact_review.json").is_file())
            self.assertTrue((artifacts / "artifact_reviews" / "literary_editor.artifact_review.json").is_file())


if __name__ == "__main__":
    unittest.main()
