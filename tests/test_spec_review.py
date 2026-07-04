"""Pre-BUILD whole-SPEC review gate (roadmap C0). Every rule encodes a real
incident: soul-v3/v5 (ai-video) and the stock_story_e2e convergence dry-run."""
import unittest
import json
import subprocess
import sys
import tempfile
from pathlib import Path

from video_pipeline_core.spec_review import _parse_target_sec, review_spec


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

    def test_spec_review_cli_accepts_utf8_bom_json(self):
        repo = Path(__file__).resolve().parents[1]
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            contract_path = root / "segment_contract.json"
            brief_path = root / "brief.json"
            contract_path.write_text(
                json.dumps({"segments": [_seg()]}, ensure_ascii=False),
                encoding="utf-8-sig",
            )
            brief_path.write_text(json.dumps(BRIEF, ensure_ascii=False), encoding="utf-8-sig")

            proc = subprocess.run(
                [
                    sys.executable,
                    "video_tools.py",
                    "spec-review",
                    str(contract_path),
                    "--brief",
                    str(brief_path),
                    "--editorial-design",
                    str(brief_path),
                ],
                cwd=repo,
                text=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                check=False,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            payload = json.loads(proc.stdout)
            self.assertTrue(payload["ready_for_build"])


class BlockingRulesTest(unittest.TestCase):
    def test_b6_script_overreach_blocks_above_max_honest_duration(self):
        contract = {"segments": [_seg(segment=1, requested_duration_sec=30)]}
        supply_review = {
            "segments": [{
                "segment": 1,
                "requested_duration_sec": 30,
                "max_honest_duration_sec": 14,
                "feasibility": "thin",
            }]
        }

        r = review_spec(
            contract,
            BRIEF,
            has_editorial_design=True,
            supply_review=supply_review,
        )

        finding = next(b for b in r["blocking"] if b["rule"] == "script_overreach")
        self.assertEqual(finding["segment"], 1)
        self.assertEqual(finding["max_honest_duration_sec"], 14)

    def test_b6_within_max_honest_duration_is_ready(self):
        contract = {"segments": [_seg(segment=1, requested_duration_sec=10)]}
        supply_review = {
            "segments": [{
                "segment": 1,
                "requested_duration_sec": 10,
                "max_honest_duration_sec": 14,
                "feasibility": "ok",
            }]
        }
        r = review_spec(
            contract,
            BRIEF,
            has_editorial_design=True,
            supply_review=supply_review,
        )
        self.assertTrue(r["ready_for_build"])

    def test_b5_out_of_capability_blocks(self):
        contract = {
            "required_capabilities": ["arbitrary_effects"],
            "segments": [_seg()],
        }
        r = review_spec(contract, BRIEF, has_editorial_design=True)
        self.assertFalse(r["ready_for_build"])
        finding = next(b for b in r["blocking"] if b["rule"] == "out_of_capability")
        self.assertEqual(finding["tier"], 1)
        self.assertEqual(finding["capability"], "arbitrary_effects")

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

    def test_mojibake_overlay_text_blocks_before_render(self):
        contract = {"segments": [_seg(
            segment=1,
            text_layer={"narrative": "?????????????????", "reason": "r"},
        )]}

        r = review_spec(contract, BRIEF, has_editorial_design=True)

        self.assertFalse(r["ready_for_build"])
        finding = next(b for b in r["blocking"] if b["rule"] == "text_mojibake")
        self.assertEqual(finding["segment"], 1)


    def test_matching_creative_exception_downgrades_block_to_acknowledged_warning(self):
        exception = {
            "rule_bent": "subtitle_auto_no_speech",
            "reason": "Intentional silent subtitle reveal.",
            "risk": "ASR may produce no text.",
            "requires_review": True,
        }
        contract = {"segments": [_seg(
            creative_exception=exception,
            text_layer={"subtitle": "auto", "reason": "r"},
        )]}

        r = review_spec(contract, BRIEF, has_editorial_design=True)

        self.assertTrue(r["ready_for_build"])
        self.assertEqual(r["blocking"], [])
        finding = next(w for w in r["warnings"] if w["rule"] == "subtitle_auto_no_speech")
        self.assertTrue(finding["acknowledged_exception"])
        self.assertEqual(finding["creative_exception"], exception)


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

    def test_target_length_mismatch_blocks_when_enforced_before_build(self):
        contract = {"segments": [
            _seg(segment=1, requested_duration_sec=16),
            _seg(segment=2, requested_duration_sec=16),
            _seg(segment=3, requested_duration_sec=16),
        ]}
        brief = {
            "video_type": "documentary",
            "target_length": "3 minutes",
            "mode": "warm_documentary",
            "enforce_target_length": True,
        }

        r = review_spec(contract, brief, has_editorial_design=True)

        self.assertFalse(r["ready_for_build"])
        finding = next(w for w in r["blocking"] if w["rule"] == "target_length_mismatch")
        self.assertEqual(finding["estimated_duration_sec"], 48.0)
        self.assertEqual(finding["target_duration_sec"], 180.0)
        self.assertLess(finding["duration_ratio"], 0.5)
        self.assertEqual(finding["enforcement"]["enforce_target_length"], True)

    def test_probe_target_length_parser_handles_hours_and_chinese_forms(self):
        cases = {
            "10 minutes": 600.0,
            "30 minutes": 1800.0,
            "5 hours": 18000.0,
            "2h": 7200.0,
            "1.5 hr": 5400.0,
            "5\u5c0f\u6642": 18000.0,
            "\u7247\u9577\u4e94\u5c0f\u6642": 18000.0,
            "3\u5206\u9418": 180.0,
            "90\u79d2": 90.0,
        }

        for raw, expected in cases.items():
            with self.subTest(raw=raw):
                self.assertEqual(_parse_target_sec(raw), expected)

    def test_probe_five_hours_no_longer_misparses_as_five_seconds(self):
        contract = {"segments": [
            _seg(segment=1, requested_duration_sec=9000),
            _seg(segment=2, requested_duration_sec=9000),
        ]}
        brief = {
            "video_type": "documentary",
            "target_length": "5 hours",
            "mode": "warm_documentary",
            "enforce_target_length": True,
        }

        r = review_spec(contract, brief, has_editorial_design=True)

        self.assertTrue(r["ready_for_build"])
        self.assertNotIn("target_length_mismatch", self._rules(r))
        self.assertEqual(r["stats"]["target_sec"], 18000.0)

    def test_probe_unparseable_target_length_blocks_spec_review(self):
        r = review_spec(
            {"segments": [_seg()]},
            {"video_type": "mv", "target_length": "banana", "mode": "warm_documentary"},
            has_editorial_design=True,
        )

        self.assertFalse(r["ready_for_build"])
        finding = next(w for w in r["blocking"] if w["rule"] == "target_length_unparseable")
        self.assertEqual(finding["target_length"], "banana")
        self.assertEqual(finding["enforcement"]["enforce_target_length"], False)

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

    def test_findings_carry_priority_tier_metadata(self):
        r = review_spec(
            {"segments": [_seg()]},
            {"video_type": "mv", "mode": "warm_documentary"},
            has_editorial_design=True,
        )
        finding = next(w for w in r["warnings"] if w["rule"] == "missing_target_length")
        self.assertEqual(finding["tier"], 3)


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
