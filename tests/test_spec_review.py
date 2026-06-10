"""Pre-BUILD whole-SPEC review gate (roadmap C0). Every rule encodes a real
incident: soul-v3/v5 (ai-video) and the stock_story_e2e convergence dry-run."""
import unittest

from video_pipeline_core.spec_review import review_spec


def _seg(**over):
    base = {
        "segment": over.pop("segment", 1),
        "core": {"section_role": "develop", "story_purpose": "x", "timeline_source": "beat"},
        "material_fit": {"visual_desc": "團隊討論", "search_query": "bright office team",
                         "reason": "r"},
        "audio": {"role": "music", "reason": "r"},
        "visual_style": {"layout": "single", "pace": "fast", "reason": "r"},
        "text_layer": "none",
    }
    base.update(over)
    return base


BRIEF = {"video_type": "mv", "target_length": "45 seconds", "mode": "warm_documentary"}


class ReadySpecTest(unittest.TestCase):
    def test_clean_spec_is_ready(self):
        contract = {"segments": [_seg()]}
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertTrue(r["ready_for_build"])
        self.assertEqual(r["blocking"], [])
        self.assertIsNone(r["next_action"])


class BlockingRulesTest(unittest.TestCase):
    def test_b1_pacing_conflict_blocks(self):
        # establishing → single_hold vs multi-shot pacing over a real budget
        contract = {"segments": [_seg(
            editing_intent={"content_pattern": "establishing"},
            pacing={"preferred_shot_sec": [4, 8]},
        )]}
        brief = dict(BRIEF, target_length="120 seconds")  # 120s/1seg → huge budget
        r = review_spec(contract, brief, has_editorial_design=True)
        self.assertFalse(r["ready_for_build"])
        self.assertEqual(r["blocking"][0]["rule"], "pacing_conflict")
        self.assertEqual(r["next_action"], "revise:director(spec_review)")

    def test_b2_must_include_on_stock_first_blocks(self):
        contract = {"material_source_mode": "stock_first",
                    "segments": [_seg(material_fit={
                        "visual_desc": "致詞", "must_include": "主任", "reason": "r"})]}
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertFalse(r["ready_for_build"])
        self.assertEqual(r["blocking"][0]["rule"], "must_include_stock_conflict")

    def test_b2_local_source_exempts_must_include(self):
        contract = {"material_source_mode": "stock_first",
                    "segments": [_seg(source="local", material_fit={
                        "visual_desc": "致詞", "must_include": "主任", "reason": "r"})]}
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertTrue(r["ready_for_build"])

    def test_b3_subtitle_auto_without_speech_blocks(self):
        contract = {"segments": [_seg(
            text_layer={"subtitle": "auto", "reason": "r"})]}  # audio.role=music
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertFalse(r["ready_for_build"])
        self.assertEqual(r["blocking"][0]["rule"], "subtitle_auto_no_speech")

    def test_b3_subtitle_auto_with_duck_is_fine(self):
        contract = {"segments": [_seg(
            audio={"role": "duck", "reason": "r"},
            text_layer={"subtitle": "auto", "reason": "r"})]}
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertTrue(r["ready_for_build"])


class WarningRulesTest(unittest.TestCase):
    def _rules(self, r):
        return [w["rule"] for w in r["warnings"]]

    def test_w1_cg_bait_query_warns(self):
        contract = {"segments": [_seg(material_fit={
            "visual_desc": "未來感", "search_query": "futuristic team hologram discussion",
            "reason": "r"})]}
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertTrue(r["ready_for_build"])     # warn, not blocking
        self.assertIn("cg_bait_query", self._rules(r))

    def test_w2_missing_target_length_warns(self):
        r = review_spec({"segments": [_seg()]}, {"video_type": "mv", "mode": "warm_documentary"},
                        has_editorial_design=True)
        self.assertIn("missing_target_length", self._rules(r))

    def test_w3_implicit_mode_trap_warns(self):
        brief = {"video_type": "mv", "target_length": "45 seconds"}  # no explicit mode
        contract = {"segments": [_seg(pacing={"preferred_shot_sec": [4, 8]})]}
        r = review_spec(contract, brief, has_editorial_design=True)
        self.assertIn("implicit_mode_trap", self._rules(r))

    def test_w3_explicit_mode_silences_trap(self):
        contract = {"segments": [_seg(pacing={"preferred_shot_sec": [4, 8]})]}
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertNotIn("implicit_mode_trap", self._rules(r))

    def test_w4_soul_without_editorial_design_warns(self):
        contract = {"segments": [_seg(editing_intent={"content_pattern": "process"})]}
        r = review_spec(contract, BRIEF, has_editorial_design=False)
        self.assertIn("soul_without_editorial_design", self._rules(r))


class PerfunctorySpecTest(unittest.TestCase):
    """Anti-laziness: copy-paste contracts (soul-v3/v5 signature) must be caught.
    Single signals warn; >=3 co-occurring signals on a >=4-seg film block."""

    def _lazy_contract(self, n=5):
        # the soul-v5 signature: identical pacing, duplicated desc/query, "r" reasons
        return {"segments": [
            _seg(segment=i + 1,
                 material_fit={"visual_desc": "團隊", "search_query": "team work",
                               "reason": "r"},
                 pacing={"preferred_shot_sec": [4, 8]})
            for i in range(n)
        ]}

    def test_full_laziness_blocks(self):
        r = review_spec(self._lazy_contract(), BRIEF, has_editorial_design=True)
        self.assertFalse(r["ready_for_build"])
        rules = [b["rule"] for b in r["blocking"]]
        self.assertIn("perfunctory_spec", rules)
        self.assertGreaterEqual(len(r["stats"]["laziness_signals"]), 3)

    def test_single_signal_only_warns(self):
        # identical pacing everywhere, but desc/query/reasons are real → warn only
        contract = {"segments": [
            _seg(segment=i + 1,
                 material_fit={"visual_desc": f"工程師在明亮辦公室{i}號桌前專注除錯",
                               "search_query": f"bright office engineer desk {i}",
                               "reason": f"第{i}段需要具體工作畫面支撐論點"},
                 pacing={"preferred_shot_sec": [4, 8]})
            for i in range(5)
        ]}
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertTrue(r["ready_for_build"])
        self.assertIn("uniform_pacing", [w["rule"] for w in r["warnings"]])

    def test_differentiated_spec_has_no_laziness_signals(self):
        pacings = [{"preferred_shot_sec": [6, 12]}, {"preferred_shot_sec": [2, 4]},
                   {"preferred_shot_sec": [3, 6]}, {"preferred_shot_sec": [1.5, 4]},
                   {"preferred_shot_sec": [6, 12]}]
        contract = {"segments": [
            _seg(segment=i + 1,
                 material_fit={"visual_desc": f"第{i}段specific畫面描述含主體與光線",
                               "search_query": f"distinct scene {i} warm light",
                               "reason": f"段{i}的設計依據:服務該段故事功能"},
                 audio={"role": "music", "reason": f"段{i}配樂墊底不搶戲"},
                 visual_style={"layout": "single", "pace": "fast",
                               "reason": f"段{i}節奏服務內容密度"},
                 pacing=pacings[i])
            for i in range(5)
        ]}
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertTrue(r["ready_for_build"])
        self.assertEqual(r["stats"]["laziness_signals"], [])

    def test_small_contract_never_blocks_on_laziness(self):
        r = review_spec(self._lazy_contract(n=3), BRIEF, has_editorial_design=True)
        self.assertTrue(r["ready_for_build"])  # signals warn, but n<4 → no block


if __name__ == "__main__":
    unittest.main()
