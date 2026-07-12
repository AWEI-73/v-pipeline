import unittest

from video_pipeline_core import semantic_novelty_audit as sna
from video_pipeline_core.delivery_gate import evaluate_delivery_gate


def _clip(seg, t_in, t_out):
    return {"segment": seg, "timeline_in_sec": t_in, "timeline_out_sec": t_out,
            "duration_sec": round(t_out - t_in, 3),
            "stable_segment_id": f"segment_{seg}", "clip_id": f"clip_{seg}"}


class HashTest(unittest.TestCase):
    def test_hamming_counts_differing_bits(self):
        self.assertEqual(sna.hamming(0b1010, 0b1000), 1)
        self.assertEqual(sna.hamming(0xFF, 0x00), 8)

    def test_cluster_groups_near_hashes_and_splits_far_ones(self):
        # 0 and 1 differ by 1 bit (same cluster at d=10); a far hash splits off
        ids = sna.cluster_by_similarity([0b0, 0b1, (1 << 40) | 0xFFFF], max_distance=10)
        self.assertEqual(ids[0], ids[1])
        self.assertNotEqual(ids[0], ids[2])


class AuditTest(unittest.TestCase):
    def test_distinct_compositions_pass(self):
        clips = [_clip(1, 0, 3), _clip(2, 3, 6), _clip(3, 6, 9)]
        # three hashes each >10 bits apart -> three distinct compositions
        hashes = iter([0x0, 0xFFFFF, 0xFFFFFFFFFF])
        result = sna.audit_semantic_novelty(
            clips, frame_hasher=lambda _t: next(hashes),
            min_distinct_ratio=0.5, max_similar_run_sec=6.0)
        self.assertTrue(result["pass"])
        self.assertEqual(result["metrics"]["distinct_compositions"], 3)

    def test_same_idea_different_files_fails_distinct_ratio(self):
        clips = [_clip(i, i * 3, i * 3 + 3) for i in range(4)]
        # all four hash to the same composition (the muster-shot problem)
        result = sna.audit_semantic_novelty(
            clips, frame_hasher=lambda _t: 0b101010,
            min_distinct_ratio=0.5, max_similar_run_sec=6.0)
        self.assertFalse(result["pass"])
        checks = {f["check"] for f in result["findings"]}
        self.assertIn("distinct_composition_ratio", checks)
        self.assertIn("max_similar_composition_run_sec", checks)
        for finding in result["findings"]:
            self.assertTrue(finding["affected_stable_ids"])
        self.assertIn("segment_1", result["findings"][0]["affected_stable_ids"])

    def test_long_similar_run_fails_even_when_ratio_ok(self):
        # 2 distinct ideas (ratio 0.667 ok) but first idea holds 8s in a row
        clips = [_clip(1, 0, 4), _clip(2, 4, 8), _clip(3, 8, 11)]
        seq = iter([0x0, 0x0, 0xFFFFFFFFFF])
        result = sna.audit_semantic_novelty(
            clips, frame_hasher=lambda _t: next(seq),
            min_distinct_ratio=0.5, max_similar_run_sec=6.0)
        self.assertFalse(result["pass"])
        self.assertEqual(result["findings"][0]["check"], "max_similar_composition_run_sec")

    def test_planning_replay_without_render_is_unknown_not_pass(self):
        result = sna.audit_semantic_novelty([_clip(1, 0, 3)], video_path=None)
        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["applicability"], "unknown")
        self.assertEqual(result["reason"], "no_render")

    def test_hash_unavailable_is_unknown_not_pass(self):
        result = sna.audit_semantic_novelty(
            [_clip(1, 0, 3)], frame_hasher=lambda _t: None,
        )

        self.assertFalse(result["pass"])
        self.assertEqual(result["status"], "unknown")
        self.assertEqual(result["applicability"], "unknown")
        self.assertEqual(result["reason"], "hash_unavailable")

    def test_unhashed_long_clip_does_not_count_as_similar_composition_run(self):
        clips = [_clip(1, 0, 10), _clip(2, 10, 12)]
        hashes = iter([None, 0xFFFF])
        result = sna.audit_semantic_novelty(
            clips, frame_hasher=lambda _t: next(hashes),
            max_similar_run_sec=6.0,
        )
        self.assertTrue(result["pass"])
        self.assertEqual(result["metrics"]["max_similar_composition_run_sec"], 2.0)


class DeliveryGateIntegrationTest(unittest.TestCase):
    def test_failed_semantic_audit_is_quality_evidence_not_tier1_blocker(self):
        gate = evaluate_delivery_gate({
            "verify_result": {"pass": True},
            "semantic_novelty_audit": {"pass": False, "next_action": "fix_timeline_or_assembly"},
        })
        self.assertTrue(gate["pass"])
        self.assertFalse(any(b["artifact"] == "semantic_novelty_audit" for b in gate["blocking"]))


if __name__ == "__main__":
    unittest.main()
