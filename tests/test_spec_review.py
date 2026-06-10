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


if __name__ == "__main__":
    unittest.main()
