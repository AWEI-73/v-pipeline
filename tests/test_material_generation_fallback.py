import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.material_generation_fallback import (
    plan_material_generation_fallback,
)


def _needs():
    return {
        "artifact_role": "material_needs",
        "version": 1,
        "project": "training-film",
        "needs": [
            {
                "need_id": "nd_report_memory",
                "category": "story",
                "type": "symbolic_panel",
                "purpose": "show the internship-report memory frame that starts the training recollection",
                "count": 3,
                "must_have": True,
                "fallback_tier": 2,
                "fallback_options": ["generated symbolic panels clearly marked as non-documentary inserts"],
            },
            {
                "need_id": "nd_daily_life",
                "category": "human",
                "type": "daily_life_cutaway",
                "purpose": "show warm trainee daily-life moments between hard training beats",
                "count": 2,
                "must_have": False,
                "fallback_tier": 3,
                "fallback_options": ["generated illustration insert"],
            },
            {
                "need_id": "nd_real_director",
                "category": "proof",
                "type": "real_person_speech",
                "purpose": "show the real training director encouragement speech",
                "count": 1,
                "must_have": True,
                "fallback_tier": 1,
                "fallback_options": ["title card quoting approved transcript"],
            },
        ],
    }


def _delta():
    return {
        "artifact_role": "material_delta",
        "version": 1,
        "ok": True,
        "ready_for_build": False,
        "blocks_ready_for_build": True,
        "deltas": [
            {
                "need_id": "nd_report_memory",
                "outcome": "missing",
                "tier": 2,
                "route": "await_material",
                "blocks_ready_for_build": False,
                "reason": "no candidate scenes",
                "evidence": {"required_count": 3, "accepted": 0, "candidate": 0, "must_have": True},
            },
            {
                "need_id": "nd_daily_life",
                "outcome": "thin",
                "tier": 3,
                "route": "await_material",
                "blocks_ready_for_build": False,
                "reason": "one scene short",
                "evidence": {"required_count": 2, "accepted": 1, "candidate": 0, "must_have": False},
            },
            {
                "need_id": "nd_real_director",
                "outcome": "covered",
                "tier": 1,
                "route": "none",
                "blocks_ready_for_build": False,
                "reason": "accepted evidence exists",
                "evidence": {"required_count": 1, "accepted": 1, "candidate": 0, "must_have": True},
            },
        ],
    }


def _concept():
    return {
        "core_metaphor": "0.66% of a life spent learning how to carry responsibility",
        "narrative_device": "an internship report triggers memory fragments",
        "visual_motifs": ["notebook", "helmet", "morning light"],
    }


def _director_plan():
    return {
        "shots": [
            {
                "need_id": "nd_report_memory",
                "beat_id": "b01",
                "story_function": "open the memory frame before the course montage",
                "emotion": "quiet anticipation",
                "visual_family": "report_memory_insert",
                "angle_scale": "close",
                "action_family": "writing_reflection",
                "subject": "trainee hands writing internship report",
                "media_preference": "generated_image",
                "panel_count_min": 3,
                "prompt": "trainee writing an internship report at a desk, helmet and notebook beside the page",
                "negative_prompt": "text, watermark, fake logo, distorted hands",
            },
            {
                "need_id": "nd_daily_life",
                "beat_id": "b07",
                "story_function": "restore human warmth after hard training",
                "emotion": "warm relief",
                "visual_family": "daily_life_memory",
                "angle_scale": "medium",
                "action_family": "shared_rest",
                "subject": "trainees laughing over a simple meal",
                "media_preference": "generated_image",
                "panel_count_min": 1,
            },
        ]
    }


class MaterialGenerationFallbackTest(unittest.TestCase):
    def test_missing_need_creates_generation_job_with_story_context_and_candidate_gate(self):
        result = plan_material_generation_fallback(
            _delta(), material_needs=_needs(), creative_concept=_concept(),
            director_shot_plan=_director_plan())

        self.assertTrue(result["ok"])
        job = result["generation_jobs"][0]
        self.assertEqual(job["need_id"], "nd_report_memory")
        self.assertEqual(job["panel_count"], 3)
        self.assertEqual(job["source_type"], "generated")
        self.assertEqual(job["status"], "planned")
        self.assertEqual(job["material_map_return"]["initial_satisfies_status"], "candidate")
        self.assertIn("0.66%", job["prompt"])
        self.assertIn("internship report", job["prompt"])
        self.assertIn("must not be accepted without visual review", " ".join(job["review_criteria"]))
        self.assertTrue(result["review_gate"]["must_reingest"])
        self.assertEqual(result["review_gate"]["generated_assets_enter_as"], "candidate")

    def test_delta_not_ok_fails_without_jobs(self):
        bad = _delta()
        bad["ok"] = False
        bad["errors"] = ["dangling satisfies edge"]
        result = plan_material_generation_fallback(bad, material_needs=_needs())
        self.assertFalse(result["ok"])
        self.assertEqual(result["generation_jobs"], [])
        self.assertIn("delta is not ok", result["errors"][0])

    def test_covered_and_excess_do_not_create_jobs(self):
        delta = _delta()
        delta["deltas"] = [
            {"need_id": "a", "outcome": "covered", "evidence": {"required_count": 1}},
            {"need_id": "b", "outcome": "excess", "evidence": {"required_count": 1}},
        ]
        result = plan_material_generation_fallback(delta)
        self.assertTrue(result["ok"])
        self.assertEqual(result["generation_jobs"], [])
        self.assertEqual(result["summary"]["skipped"], 2)

    def test_thin_need_creates_only_missing_topup_count(self):
        result = plan_material_generation_fallback(
            _delta(), material_needs=_needs(), director_shot_plan=_director_plan())
        jobs = {job["need_id"]: job for job in result["generation_jobs"]}
        self.assertEqual(jobs["nd_daily_life"]["panel_count"], 1)
        self.assertEqual(jobs["nd_daily_life"]["derived_from"]["outcome"], "thin")

    def test_no_job_claims_real_footage_or_accepted_status(self):
        result = plan_material_generation_fallback(
            _delta(), material_needs=_needs(), director_shot_plan=_director_plan())
        for job in result["generation_jobs"]:
            self.assertNotEqual(job.get("source_type"), "real_footage")
            self.assertNotEqual(job["material_map_return"]["initial_satisfies_status"], "accepted")
            self.assertTrue(job["honesty"]["must_not_claim_real_event"])

    def test_invalid_needs_fails_without_jobs(self):
        needs = _needs()
        needs["needs"][0]["fallback_options"] = [""]
        result = plan_material_generation_fallback(_delta(), material_needs=needs)
        self.assertFalse(result["ok"])
        self.assertEqual(result["generation_jobs"], [])
        self.assertIn("material_needs invalid", result["errors"][0])

    def test_cli_writes_artifact(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            delta = d / "material_delta.json"
            needs = d / "material_needs.json"
            concept = d / "creative_concept.json"
            director = d / "director_shot_plan.json"
            out = d / "material_generation_fallback.json"
            delta.write_text(json.dumps(_delta(), ensure_ascii=False), encoding="utf-8")
            needs.write_text(json.dumps(_needs(), ensure_ascii=False), encoding="utf-8")
            concept.write_text(json.dumps(_concept(), ensure_ascii=False), encoding="utf-8")
            director.write_text(json.dumps(_director_plan(), ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "material-generation-fallback",
                    str(delta),
                    "--needs", str(needs),
                    "--creative-concept", str(concept),
                    "--director-shot-plan", str(director),
                    "--out", str(out),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr + proc.stdout)
            artifact = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(artifact["artifact_role"], "material_generation_fallback")
            self.assertEqual(artifact["summary"]["jobs"], 2)


if __name__ == "__main__":
    unittest.main()
