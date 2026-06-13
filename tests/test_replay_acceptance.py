import unittest

from video_pipeline_core import replay_acceptance


TIMELINE = {"clips": [
    {"segment": 1, "duration_sec": 1.5, "source_path": "a.mp4",
     "scene_id": "a:0", "beat_alignment": "action",
     "adjustment_reason": "motion_phase"},
    {"segment": 1, "duration_sec": 3.0, "source_path": "b.mp4",
     "scene_id": "b:0", "keep_audio": True},
    {"segment": 2, "duration_sec": 2.0, "source_path": "c.mp4",
     "scene_id": "c:0"},
]}


class ReplayMetricsTest(unittest.TestCase):
    def test_collects_m4_metrics(self):
        report = replay_acceptance.build_replay_report(
            TIMELINE,
            gate_artifacts={"spec_review": {"ready_for_build": True}},
            judge_verdicts=[{"decision": "accept", "reviewer": "agent"}],
            jumpcut_plan={"requires_review": False, "approved": False},
            adaptation_decisions={"duration": "shortened", "chapters": "reduced"},
        )
        metrics = report["metrics"]
        self.assertEqual(metrics["shot_le_2s_ratio"], 0.6667)
        self.assertEqual(metrics["unique_source_ratio"], 1.0)
        self.assertEqual(metrics["max_source_repeats"], 1)
        self.assertEqual(metrics["action_phase_coverage"], 1.0)
        self.assertEqual(metrics["sound_bite_count"], 1)
        self.assertEqual(metrics["jumpcut_count"], 0)
        self.assertEqual(report["checks"]["jumpcut_when_applicable"], "not_applicable")
        self.assertEqual(report["checks"]["duration_adaptation"], "pass")
        self.assertEqual(report["checks"]["chapter_adaptation"], "pass")

    def test_gate_bypass_and_missing_verdict_fail(self):
        report = replay_acceptance.build_replay_report(
            TIMELINE,
            gate_artifacts={"spec_review": {"ready_for_build": False}},
            judge_verdicts=[],
        )
        self.assertFalse(report["pass"])
        self.assertEqual(report["checks"]["tier1_gates"], "fail")
        self.assertEqual(report["checks"]["judge_lineage"], "fail")

    def test_missing_adaptation_evidence_is_unproven(self):
        report = replay_acceptance.build_replay_report(
            TIMELINE,
            gate_artifacts={"spec_review": {"ready_for_build": True}},
            judge_verdicts=[{"decision": "accept"}],
        )
        self.assertFalse(report["pass"])
        self.assertEqual(report["checks"]["duration_adaptation"], "unproven")
        self.assertEqual(report["checks"]["chapter_adaptation"], "unproven")


if __name__ == "__main__":
    unittest.main()
