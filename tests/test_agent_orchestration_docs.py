from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class AgentOrchestrationDocsTest(unittest.TestCase):
    def test_runner_protocol_declares_bounded_workers_and_parent_owned_execution(self):
        protocol = (ROOT / "docs" / "route-agent-runner-protocol.md").read_text(encoding="utf-8")
        harness = (ROOT / "docs" / "route-orchestrator-harness.md").read_text(encoding="utf-8")
        integrated = (
            ROOT / "docs" / "construction-guides" / "agent-orchestration"
            / "2026-06-22-integrated-e2e-review-action-plan.md"
        ).read_text(encoding="utf-8")

        combined = "\n".join([protocol, harness, integrated])
        for phrase in (
            "bounded worker",
            "parent-owned long execution",
            "long-running render",
            "state.json and artifacts are the handoff",
            "do not run the whole video pipeline",
        ):
            self.assertIn(phrase, combined)


if __name__ == "__main__":
    unittest.main()
