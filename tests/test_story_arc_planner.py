"""SRP3 — Story Arc Planner pure-function tests (A–K).

Planner eligibility, role assignment, manual/auto precedence, fallback shape,
immutability, and determinism. No ffmpeg / no run_mv here.
"""
from __future__ import annotations

import copy
import unittest

from video_pipeline_core.story_arc_planner import (
    plan_story_arc, apply_story_arc_hints)


def _segs(n, overrides=None):
    out = []
    for i in range(n):
        s = {"segment": i + 1, "visual_desc": f"seg{i+1}", "audio_role": "music"}
        out.append(s)
    for idx, fields in (overrides or {}).items():
        out[idx].update(fields)
    return out


def _roles(plan):
    return [h["arc_role"] for h in plan["segment_hints"]]


class EligibilityTest(unittest.TestCase):
    def test_A_two_segments_not_applicable(self):
        plan = plan_story_arc({"segments": _segs(2)})
        self.assertEqual(plan["status"], "not_applicable")
        self.assertEqual(plan["segment_hints"], [])
        self.assertIn("at least 3", plan["reason"])

    def test_H_disable_flags_not_applicable(self):
        for flag in ({"story_arc": False}, {"disable_auto_story_arc": True}):
            script = {"segments": _segs(5), **flag}
            plan = plan_story_arc(script)
            self.assertEqual(plan["status"], "not_applicable")
            self.assertIn("disabled", plan["reason"])

    def test_I_non_object_segment_not_applicable(self):
        plan = plan_story_arc({"segments": [{"segment": 1}, "bad", {"segment": 3}]})
        self.assertEqual(plan["status"], "not_applicable")
        self.assertIn("non-object", plan["reason"])

    def test_I_duplicate_identity_not_applicable(self):
        segs = _segs(3)
        segs[2]["segment"] = 1            # duplicate identity
        plan = plan_story_arc({"segments": segs})
        self.assertEqual(plan["status"], "not_applicable")
        self.assertIn("duplicate", plan["reason"])

    def test_pure_source_speech_not_applicable(self):
        segs = _segs(3, {0: {"audio_role": "source_speech"},
                           1: {"audio_role": "source_speech"},
                           2: {"audio_role": "source_speech"}})
        plan = plan_story_arc({"segments": segs})
        self.assertEqual(plan["status"], "not_applicable")
        self.assertIn("source_speech", plan["reason"])

    def test_pure_stock_not_applicable(self):
        segs = _segs(4)
        for s in segs:
            s["source"] = "stock"
        plan = plan_story_arc({"segments": segs})
        self.assertEqual(plan["status"], "not_applicable")
        self.assertIn("stock", plan["reason"])


class RoleAssignmentTest(unittest.TestCase):
    def test_B_three_segments(self):
        plan = plan_story_arc({"segments": _segs(3)})
        self.assertEqual(plan["status"], "planned")
        self.assertEqual(_roles(plan), ["setup", "climax", "resolution"])

    def test_C_four_segments(self):
        plan = plan_story_arc({"segments": _segs(4)})
        self.assertEqual(_roles(plan),
                         ["setup", "challenge", "climax", "resolution"])

    def test_D_five_segments(self):
        plan = plan_story_arc({"segments": _segs(5)})
        self.assertEqual(_roles(plan),
                         ["setup", "challenge", "progression", "climax", "resolution"])

    def test_E_six_segments(self):
        plan = plan_story_arc({"segments": _segs(6)})
        roles = _roles(plan)
        self.assertEqual(roles[0], "setup")
        self.assertEqual(roles[-1], "resolution")
        self.assertEqual(roles[-2], "climax")
        # deterministic middle: earlier challenge block, later progression block
        self.assertEqual(roles, ["setup", "challenge", "challenge",
                                 "progression", "climax", "resolution"])

    def test_E_seven_segments_deterministic(self):
        plan = plan_story_arc({"segments": _segs(7)})
        self.assertEqual(_roles(plan),
                         ["setup", "challenge", "challenge", "progression",
                          "progression", "climax", "resolution"])

    def test_climax_weight_exceeds_setup(self):
        plan = plan_story_arc({"segments": _segs(5)})
        by_role = {h["arc_role"]: h for h in plan["segment_hints"]}
        self.assertGreater(by_role["climax"]["weight_multiplier"],
                           by_role["setup"]["weight_multiplier"])


class ManualPrecedenceTest(unittest.TestCase):
    def test_F_manual_arc_role_preserved(self):
        segs = _segs(5, {0: {"arc_role": "climax"}})   # director forces seg1=climax
        plan = plan_story_arc({"segments": segs})
        h0 = plan["segment_hints"][0]
        self.assertEqual(h0["arc_role"], "climax")
        self.assertTrue(h0["manual_role"])
        # the other four are auto-assigned and not forced to collide
        self.assertFalse(plan["segment_hints"][1]["manual_role"])
        self.assertEqual(plan["evidence"]["manual_role_count"], 1)

    def test_F_apply_does_not_relabel_manual_role(self):
        segs = _segs(5, {0: {"arc_role": "climax"}})
        script = {"segments": segs}
        plan = plan_story_arc(script)
        runtime = copy.deepcopy(script)
        apply_story_arc_hints(runtime, plan)
        self.assertEqual(runtime["segments"][0]["arc_role"], "climax")
        self.assertNotIn("story_arc_source", runtime["segments"][0])  # not auto
        self.assertEqual(runtime["segments"][1]["story_arc_source"], "auto")

    def test_G_manual_pace_weight_requested_preserved(self):
        segs = _segs(5, {
            0: {"pace": "hold"},
            1: {"weight": 2.0},
            2: {"requested_duration_sec": 5.0}})
        script = {"segments": segs}
        plan = plan_story_arc(script)
        runtime = copy.deepcopy(script)
        applied = apply_story_arc_hints(runtime, plan)
        self.assertEqual(runtime["segments"][0]["pace"], "hold")     # manual pace kept
        self.assertEqual(runtime["segments"][1]["weight"], 2.0)      # manual weight kept
        self.assertEqual(runtime["segments"][2]["requested_duration_sec"], 5.0)
        # manual-weight / requested segments never receive an auto weight override
        trace1 = next(t for t in applied if t["segment_index"] == 1)
        self.assertNotIn("weight", trace1)

    def test_O_duration_protected_no_weight_multiplier(self):
        segs = _segs(5, {0: {"hold": True}, 3: {"audio_role": "source_speech"}})
        script = {"segments": segs}
        plan = plan_story_arc(script)
        runtime = copy.deepcopy(script)
        apply_story_arc_hints(runtime, plan)
        # hold seg0 and source_speech seg3 keep default weight (no multiplier)
        self.assertIsNone(runtime["segments"][0].get("weight"))
        self.assertIsNone(runtime["segments"][3].get("weight"))
        # a plain flexible segment still gets its multiplier
        self.assertIsNotNone(runtime["segments"][1].get("weight"))

    def test_pace_fast_only_applied(self):
        segs = _segs(5)
        script = {"segments": segs}
        plan = plan_story_arc(script)
        runtime = copy.deepcopy(script)
        apply_story_arc_hints(runtime, plan)
        roles = [h["arc_role"] for h in plan["segment_hints"]]
        for s, role in zip(runtime["segments"], roles):
            if role in ("progression", "climax"):
                self.assertEqual(s.get("pace"), "fast")
            else:
                self.assertIsNone(s.get("pace"))     # steady/hold never written


class HardeningContractTest(unittest.TestCase):
    """Codex hardening reverse proofs: protected segments, identity fail-closed,
    manual-role derives nothing, manual-intensity precedence."""

    def _apply(self, script):
        plan = plan_story_arc(script)
        runtime = copy.deepcopy(script)
        applied = apply_story_arc_hints(runtime, plan)
        return plan, runtime, applied

    # A — protected hold even at the climax position gets no auto weight/pace
    def test_A_protected_hold_at_climax(self):
        plan, rt, _ = self._apply({"segments": _segs(5, {3: {"hold": True}})})
        s3 = rt["segments"][3]                          # position 3 == climax (fast)
        self.assertEqual(s3.get("arc_role"), "climax")  # trace-only role allowed
        self.assertIsNone(s3.get("weight"))
        self.assertIsNone(s3.get("pace"))
        self.assertEqual(s3.get("story_arc_applied_fields"), ["arc_role", "arc_intensity"])

    def test_A_protected_hold_reason_at_progression(self):
        plan, rt, _ = self._apply({"segments": _segs(5, {2: {"hold_reason": "ceremony"}})})
        s2 = rt["segments"][2]                          # position 2 == progression (fast)
        self.assertIsNone(s2.get("weight"))
        self.assertIsNone(s2.get("pace"))

    # B — protected source_speech / keep_audio at climax/progression: no weight/pace
    def test_B_source_speech_at_climax(self):
        plan, rt, _ = self._apply(
            {"segments": _segs(5, {3: {"audio_role": "source_speech"}})})
        s3 = rt["segments"][3]
        self.assertIsNone(s3.get("weight"))
        self.assertIsNone(s3.get("pace"))

    def test_B_keep_audio_at_progression(self):
        plan, rt, _ = self._apply({"segments": _segs(5, {2: {"keep_audio": True}})})
        s2 = rt["segments"][2]
        self.assertIsNone(s2.get("weight"))
        self.assertIsNone(s2.get("pace"))

    # C — segment identity fail-closed
    def test_C_all_missing_identity_not_applicable(self):
        segs = [{"visual_desc": "x", "audio_role": "music"} for _ in range(3)]
        plan = plan_story_arc({"segments": segs})
        self.assertEqual(plan["status"], "not_applicable")
        self.assertIn("identity", plan["reason"])

    def test_C_mixed_missing_identity_not_applicable(self):
        segs = _segs(3)
        del segs[1]["segment"]
        plan = plan_story_arc({"segments": segs})
        self.assertEqual(plan["status"], "not_applicable")
        self.assertIn("identity", plan["reason"])

    def test_C_blank_and_none_identity_not_applicable(self):
        for bad in ("", "   ", None):
            segs = _segs(3)
            segs[1]["segment"] = bad
            plan = plan_story_arc({"segments": segs})
            self.assertEqual(plan["status"], "not_applicable", f"id={bad!r}")
            self.assertIn("identity", plan["reason"])

    # D — manual arc_role derives nothing; auto fields are traceable
    def test_D_manual_role_derives_nothing(self):
        plan, rt, applied = self._apply({"segments": _segs(5, {0: {"arc_role": "climax"}})})
        s0 = rt["segments"][0]
        self.assertEqual(s0.get("arc_role"), "climax")        # manual preserved
        self.assertNotIn("weight", s0)
        self.assertNotIn("pace", s0)
        self.assertNotIn("story_arc_source", s0)              # not relabeled auto
        self.assertNotIn("story_arc_applied_fields", s0)
        self.assertTrue(all(t["segment_index"] != 0 for t in applied))
        # an auto-role segment that got weight records it traceably
        seg3 = next(t for t in applied if t["segment_index"] == 3)   # auto climax
        self.assertEqual(seg3["story_arc_source"], "auto")
        self.assertIn("weight", seg3["applied_fields"])

    # E — manual intensity precedence (no conflicting auto intensity)
    def test_E_manual_intensity_preserved_no_conflict(self):
        plan, rt, applied = self._apply({"segments": _segs(5, {1: {"intensity": 5}})})
        s1 = rt["segments"][1]                                # auto role challenge
        self.assertEqual(s1["intensity"], 5)                  # manual kept
        self.assertNotIn("arc_intensity", s1)                 # no conflicting value
        self.assertEqual(s1.get("arc_role"), "challenge")     # role still auto
        t1 = next(t for t in applied if t["segment_index"] == 1)
        self.assertNotIn("arc_intensity", t1["applied_fields"])

    def test_E_manual_arc_intensity_preserved(self):
        plan, rt, _ = self._apply({"segments": _segs(5, {2: {"arc_intensity": 1}})})
        self.assertEqual(rt["segments"][2]["arc_intensity"], 1)   # untouched


class ImmutabilityDeterminismTest(unittest.TestCase):
    def test_J_planner_does_not_mutate_script(self):
        script = {"segments": _segs(5, {0: {"arc_role": "setup"}})}
        original = copy.deepcopy(script)
        plan_story_arc(script)
        self.assertEqual(script, original)

    def test_J_apply_does_not_touch_original(self):
        script = {"segments": _segs(5)}
        original = copy.deepcopy(script)
        plan = plan_story_arc(script)
        runtime = copy.deepcopy(script)
        apply_story_arc_hints(runtime, plan)
        self.assertEqual(script, original)            # original untouched
        self.assertNotEqual(runtime, original)        # runtime copy changed

    def test_K_determinism(self):
        script = {"segments": _segs(6, {2: {"arc_role": "climax"}})}
        p1 = plan_story_arc(copy.deepcopy(script))
        p2 = plan_story_arc(copy.deepcopy(script))
        self.assertEqual(p1, p2)


if __name__ == "__main__":
    unittest.main()
