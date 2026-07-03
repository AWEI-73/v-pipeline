import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import spec_review
from video_pipeline_core.dashboard_state import load_dashboard_state
from video_pipeline_core.e2e_smoke import run_e2e_smoke


def _write_json(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class E2ESmokeTest(unittest.TestCase):
    def test_smoke_chain_reaches_terminal(self):
        with tempfile.TemporaryDirectory() as tmp:
            result = run_e2e_smoke("stock_story", base_dir=tmp)

        self.assertTrue(result["ok"], result)
        self.assertEqual(result["final_next_action"], "complete_review_final")
        self.assertEqual(
            [item["step"] for item in result["trace"]],
            ["spec_review", "contract_dry_build", "simulated_verify"],
        )
        self.assertIsNone(result["stalled_action"])

    def test_target_length_enforced(self):
        brief = {"target_length": "30 seconds", "enforce_target_length": True}
        contract = {
            "segments": [
                {"segment": 1, "duration_sec": 30, "source": "local"},
                {"segment": 2, "duration_sec": 30, "source": "local"},
            ]
        }

        review = spec_review.review_spec(contract, brief, has_editorial_design=True)

        self.assertFalse(review["ready_for_build"])
        self.assertIn(
            "target_length_mismatch",
            {item.get("rule") for item in review.get("blocking", [])},
        )

    def test_render_output_path_does_not_stall(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            external = workdir.parent / f"{workdir.name}_external_final.mp4"
            try:
                _write_json(workdir / "artifact_manifest.json", {"final": str(external)})
                _write_json(workdir / "verify_result.json", {"pass": True})
                external.write_bytes(b"external-final-placeholder")

                state = load_dashboard_state(str(workdir))

                self.assertNotEqual(state["run"]["next_action"], "missing_artifact:final.mp4")
                self.assertFalse(
                    str(state["run"]["next_action"] or "").startswith("missing_artifact:")
                )
            finally:
                external.unlink(missing_ok=True)

    def test_revise_director_routes_to_supply_revision(self):
        with tempfile.TemporaryDirectory() as tmp:
            workdir = Path(tmp)
            _write_json(workdir / "state.json", {
                "next_action": "revise:director(spec_review)",
                "blocking": [{"rule": "script_overreach"}],
            })
            _write_json(workdir / "spec_review.json", {
                "artifact_role": "spec_review",
                "ready_for_build": False,
                "blocking": [{"rule": "script_overreach"}],
                "next_action": "revise:director(spec_review)",
            })
            _write_json(workdir / "supply_review.json", {
                "artifact_role": "supply_review",
                "segments": [{
                    "segment": 1,
                    "action": "shorten_or_merge",
                    "max_honest_duration_sec": 3,
                }],
            })

            state = load_dashboard_state(str(workdir))

            self.assertEqual(state["run"]["next_action"], "director_supply_revision")


if __name__ == "__main__":
    unittest.main()
