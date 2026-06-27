import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.material_gap_brief import (
    build_material_gap_brief,
    build_shooting_brief_markdown,
    jobs_for_route,
)


def _delta():
    return {
        "artifact_role": "material_delta",
        "version": 1,
        "ok": True,
        "ready_for_build": False,
        "deltas": [
            {
                "need_id": "nd_opening",
                "outcome": "missing",
                "route": "reshoot",
                "blocks_ready_for_build": True,
                "reason": "must_have need has no usable material",
                "evidence": {"must_have": True, "fallback_options": []},
            },
            {
                "need_id": "nd_bridge",
                "outcome": "missing",
                "route": "collect_material",
                "blocks_ready_for_build": False,
                "reason": "fallback exists",
                "evidence": {"must_have": True, "fallback_options": ["generated_image"]},
            },
            {
                "need_id": "nd_closing",
                "outcome": "covered",
                "route": "none",
                "blocks_ready_for_build": False,
                "evidence": {"must_have": True, "fallback_options": []},
            },
        ],
    }


def _needs():
    return {
        "artifact_role": "material_needs",
        "needs": [
            {
                "need_id": "nd_opening",
                "purpose": "opening class context",
                "must_have": True,
                "segment_refs": ["seg_01"],
                "proof_sensitive": True,
            },
            {
                "need_id": "nd_bridge",
                "purpose": "symbolic bridge card",
                "must_have": True,
                "fallback_options": ["generated_image"],
                "segment_refs": ["seg_02"],
            },
        ],
    }


class MaterialGapBriefTest(unittest.TestCase):
    def test_builds_tasks_only_for_missing_and_thin_needs(self):
        brief = build_material_gap_brief(_delta(), material_needs=_needs(), route="material-first")

        self.assertEqual(brief["artifact_role"], "material_gap_brief")
        self.assertEqual(brief["task_count"], 2)
        self.assertTrue(brief["does_not_release_build"])
        self.assertEqual(brief["tasks"][0]["recommended_route"], "reshoot")
        self.assertEqual(brief["tasks"][0]["priority"], "must_have")
        self.assertEqual(brief["tasks"][0]["visual_intent"], "opening class context")
        self.assertEqual(brief["tasks"][1]["recommended_route"], "generated_material")
        self.assertEqual(brief["summary"]["generated_material"], 1)

    def test_markdown_and_job_packets_are_derived_from_gap_brief(self):
        brief = build_material_gap_brief(_delta(), material_needs=_needs())

        md = build_shooting_brief_markdown(brief)
        generated = jobs_for_route(brief, "generated_material")
        stock = jobs_for_route(brief, "stock_retrieval")

        self.assertIn("nd_opening", md)
        self.assertIn("does not satisfy material coverage", md)
        self.assertEqual(generated["job_count"], 1)
        self.assertEqual(generated["jobs"][0]["need_id"], "nd_bridge")
        self.assertEqual(stock["job_count"], 0)

    def test_cli_writes_all_gap_artifacts(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            delta = root / "material_delta.json"
            needs = root / "material_needs.json"
            out = root / "material_gap_brief.json"
            shooting = root / "shooting_brief.md"
            generated = root / "generated_material_jobs.json"
            stock = root / "stock_retrieval_jobs.json"
            delta.write_text(json.dumps(_delta()), encoding="utf-8")
            needs.write_text(json.dumps(_needs()), encoding="utf-8")

            proc = subprocess.run(
                [
                    sys.executable,
                    "tools/material_gap_brief.py",
                    "--delta", str(delta),
                    "--needs", str(needs),
                    "--out", str(out),
                    "--shooting-out", str(shooting),
                    "--generated-jobs-out", str(generated),
                    "--stock-jobs-out", str(stock),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertTrue(out.is_file())
            self.assertTrue(shooting.is_file())
            self.assertTrue(generated.is_file())
            self.assertTrue(stock.is_file())
            payload = json.loads(out.read_text(encoding="utf-8"))
            self.assertTrue(payload["does_not_release_build"])


if __name__ == "__main__":
    unittest.main()
