import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.generated_material_review import (
    apply_generated_material_review,
)
from video_pipeline_core.material_delta import compute_material_delta


def _needs():
    return {
        "artifact_role": "material_needs",
        "version": 1,
        "project": "generated-review-test",
        "needs": [
            {
                "need_id": "nd_panel",
                "category": "comic",
                "type": "panel",
                "purpose": "show the hero crossing the bridge",
                "count": 2,
                "must_have": True,
                "fallback_tier": 2,
                "fallback_options": ["generated panel"],
            }
        ],
    }


def _project_map():
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "needs": _needs()["needs"],
        "assets": [
            {
                "asset_id": "generated_a",
                "asset_type": "photo",
                "source": "generated_images/a.png",
                "scenes": [
                    {
                        "start": 0,
                        "end": 4,
                        "source_type": "generated",
                        "satisfies": [
                            {
                                "need_id": "nd_panel",
                                "status": "candidate",
                                "lineage": {"generated_job_id": "gen_panel"},
                            }
                        ],
                    }
                ],
            },
            {
                "asset_id": "generated_b",
                "asset_type": "photo",
                "source": "generated_images/b.png",
                "scenes": [
                    {
                        "start": 0,
                        "end": 4,
                        "source_type": "generated",
                        "satisfies": [
                            {
                                "need_id": "nd_panel",
                                "status": "candidate",
                                "lineage": {"generated_job_id": "gen_panel"},
                            }
                        ],
                    }
                ],
            },
        ],
    }


def _accept_verdict():
    return {
        "artifact_role": "generated_material_review",
        "version": 1,
        "reviewer": "director-agent",
        "at": "2026-06-19T00:00:00+08:00",
        "decisions": [
            {
                "asset_id": "generated_a",
                "scene_index": 0,
                "need_id": "nd_panel",
                "status": "accepted",
                "reason": "matches bridge panel and style anchors",
            },
            {
                "asset_id": "generated_b",
                "scene_index": 0,
                "need_id": "nd_panel",
                "status": "accepted",
                "reason": "second required panel matches same story beat",
            },
        ],
    }


class GeneratedMaterialReviewTest(unittest.TestCase):
    def test_accepting_generated_candidates_turns_delta_from_thin_to_covered(self):
        before = compute_material_delta(_needs(), _project_map()["assets"])
        self.assertEqual(before["summary"]["thin"], 1)

        result = apply_generated_material_review(_project_map(), _accept_verdict(), _needs())

        self.assertTrue(result["ok"], result.get("errors"))
        reviewed = result["project_material_map"]
        statuses = [
            edge["status"]
            for asset in reviewed["assets"]
            for scene in asset["scenes"]
            for edge in scene["satisfies"]
        ]
        self.assertEqual(statuses, ["accepted", "accepted"])
        after = compute_material_delta(_needs(), reviewed["assets"])
        self.assertEqual(after["summary"]["covered"], 1)
        self.assertEqual(after["summary"]["thin"], 0)

    def test_rejecting_candidate_does_not_count_as_coverage(self):
        verdict = _accept_verdict()
        verdict["decisions"][1]["status"] = "rejected"
        verdict["decisions"][1]["reason"] = "character is inconsistent"

        result = apply_generated_material_review(_project_map(), verdict, _needs())

        self.assertTrue(result["ok"], result.get("errors"))
        after = compute_material_delta(_needs(), result["project_material_map"]["assets"])
        self.assertEqual(after["summary"]["thin"], 1)
        rejected = result["project_material_map"]["assets"][1]["scenes"][0]["satisfies"][0]
        self.assertEqual(rejected["status"], "rejected")

    def test_unknown_or_non_generated_reference_fails_closed(self):
        verdict = _accept_verdict()
        verdict["decisions"][0]["asset_id"] = "missing"
        result = apply_generated_material_review(_project_map(), verdict, _needs())
        self.assertFalse(result["ok"])
        self.assertIn("unknown review target", "; ".join(result["errors"]))

        pm = _project_map()
        pm["assets"][0]["scenes"][0]["source_type"] = "real"
        result = apply_generated_material_review(pm, _accept_verdict(), _needs())
        self.assertFalse(result["ok"])
        self.assertIn("not generated candidate", "; ".join(result["errors"]))

    def test_missing_reviewer_reason_or_bad_status_fails_closed(self):
        verdict = _accept_verdict()
        verdict["reviewer"] = " "
        self.assertFalse(apply_generated_material_review(_project_map(), verdict, _needs())["ok"])

        verdict = _accept_verdict()
        verdict["decisions"][0]["reason"] = ""
        self.assertFalse(apply_generated_material_review(_project_map(), verdict, _needs())["ok"])

        verdict = _accept_verdict()
        verdict["decisions"][0]["status"] = "candidate"
        self.assertFalse(apply_generated_material_review(_project_map(), verdict, _needs())["ok"])

    def test_accepting_failed_quality_generated_asset_fails_without_waiver(self):
        quality_review = {
            "artifact_role": "generated_material_quality_review",
            "version": 1,
            "pass": False,
            "items": [
                {"job_id": "gen_panel", "pass": False, "score": 40,
                 "findings": ["visual_family_missing"]},
            ],
        }

        result = apply_generated_material_review(
            _project_map(),
            _accept_verdict(),
            _needs(),
            quality_review=quality_review,
        )

        self.assertFalse(result["ok"])
        self.assertIn("quality review failed", "; ".join(result["errors"]))

    def test_quality_waiver_allows_accepting_failed_quality_with_lineage(self):
        quality_review = {
            "artifact_role": "generated_material_quality_review",
            "version": 1,
            "pass": False,
            "items": [
                {"job_id": "gen_panel", "pass": False, "score": 40,
                 "findings": ["visual_family_missing"]},
            ],
        }
        verdict = _accept_verdict()
        for decision in verdict["decisions"]:
            decision["quality_waiver"] = {
                "reviewer": "director-agent",
                "reason": "temporary storyboard placeholder accepted for rough cut",
                "at": "2026-06-22T00:00:00+08:00",
            }

        result = apply_generated_material_review(
            _project_map(),
            verdict,
            _needs(),
            quality_review=quality_review,
        )

        self.assertTrue(result["ok"], result.get("errors"))
        edge = result["project_material_map"]["assets"][0]["scenes"][0]["satisfies"][0]
        self.assertEqual(edge["lineage"]["quality_review"]["score"], 40)
        self.assertTrue(edge["lineage"]["quality_waiver"]["reason"])

    def test_cli_writes_reviewed_project_map(self):
        root = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            d = Path(td)
            pm = d / "project_material_map.json"
            needs = d / "material_needs.json"
            verdict = d / "generated_material_review.json"
            out = d / "reviewed_project_material_map.json"
            pm.write_text(json.dumps(_project_map()), encoding="utf-8")
            needs.write_text(json.dumps(_needs()), encoding="utf-8")
            verdict.write_text(json.dumps(_accept_verdict()), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "generated-material-review",
                    str(pm),
                    "--needs",
                    str(needs),
                    "--verdict",
                    str(verdict),
                    "--out",
                    str(out),
                ],
                cwd=root,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stdout + proc.stderr)
            reviewed = json.loads(out.read_text(encoding="utf-8"))
            after = compute_material_delta(_needs(), reviewed["assets"])
            self.assertEqual(after["summary"]["covered"], 1)


if __name__ == "__main__":
    unittest.main()
