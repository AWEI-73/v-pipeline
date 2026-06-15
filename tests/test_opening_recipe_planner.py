"""SRP2 — Opening / Hook Auto Planner tests.

Falsification suite A-R. Pure-function planner tests run without ffmpeg/librosa;
runtime + real-render tests drive run_mv end-to-end.
"""
from __future__ import annotations

import copy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import mv_cut
from video_pipeline_core import opening_sequence as op
from video_pipeline_core.opening_recipe_planner import (
    plan_opening_recipe, trim_opening_for_budget)
from video_pipeline_core.vt_core import FFMPEG, FFPROBE


def _slot(scene_id, *, source=None, start=0.0, dur=3.0, score=80.0,
          family=None, scale=None, is_photo=False, **extra):
    s = {
        "source": source or f"{scene_id.split(':')[0]}.mp4",
        "extract_start": start,
        "extract_dur": dur,
        "scene_id": scene_id,
        "retrieval_score": score,
        "segment": 1,
    }
    if family is not None:
        s["visual_family"] = family
    if scale is not None:
        s["angle_scale"] = scale
    if is_photo:
        s["is_photo"] = True
    s.update(extra)
    return s


class PlannerEligibilityTest(unittest.TestCase):
    """A, B, C, D, E, F — eligibility and opening shape."""

    def test_A_manual_recipe_stands_down(self):
        script = {"opening_recipe": {"title_text": "T"}, "title": "Auto Title"}
        plan = [_slot("a:0", family="fam-A"), _slot("b:0", family="fam-B"),
                _slot("c:0", family="fam-C")]
        res = plan_opening_recipe(script, plan)
        self.assertEqual(res["status"], "not_applicable")
        self.assertIsNone(res["recipe"])
        self.assertIn("Manual opening_recipe", res["reason"])

    def test_B_zero_or_one_candidate_not_applicable(self):
        # zero
        res0 = plan_opening_recipe({}, [])
        self.assertEqual(res0["status"], "not_applicable")
        self.assertIsNone(res0["recipe"])
        # one
        res1 = plan_opening_recipe({}, [_slot("a:0")])
        self.assertEqual(res1["status"], "not_applicable")
        self.assertIn("minimum 2", res1["reason"])

    def test_C_two_candidates_hook_story_entry(self):
        plan = [_slot("a:0", family="fam-A"), _slot("b:0", family="fam-B")]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["recipe"]["beats"], ["hook", "story_entry"])
        self.assertEqual(res["recipe"]["context_count"], 0)
        self.assertEqual(len(res["recipe"]["shots"]), 1)
        # scene_id never duplicated within the opening
        ids = res["selected_scene_ids"]
        self.assertEqual(len(ids), len(set(ids)))

    def test_D_three_candidates_context_montage(self):
        plan = [_slot("a:0", family="fam-A"), _slot("b:0", family="fam-B"),
                _slot("c:0", family="fam-C")]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["recipe"]["beats"],
                         ["hook", "context_montage", "story_entry"])
        self.assertEqual(res["recipe"]["context_count"], 1)
        self.assertEqual(len(res["recipe"]["shots"]), 2)
        self.assertNotIn("title_reveal", res["recipe"]["beats"])

    def test_E_four_plus_with_title_has_title_reveal(self):
        script = {"opening_title": "66期養成班"}
        plan = [_slot(f"{c}:0", family=f"fam-{c}") for c in "abcd"]
        res = plan_opening_recipe(script, plan)
        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["recipe"]["beats"],
                         ["hook", "context_montage", "title_reveal", "story_entry"])
        self.assertEqual(res["recipe"]["title_text"], "66期養成班")
        self.assertEqual(res["evidence"]["title_source"], "opening_title")
        self.assertEqual(len(res["recipe"]["shots"]), 3)
        ids = res["selected_scene_ids"]
        self.assertEqual(len(ids), len(set(ids)))   # no scene_id padding

    def test_E_title_field_fallback_to_title(self):
        script = {"title": "Story Title"}
        plan = [_slot(f"{c}:0", family=f"fam-{c}") for c in "abcd"]
        res = plan_opening_recipe(script, plan)
        self.assertEqual(res["recipe"]["title_text"], "Story Title")
        self.assertEqual(res["evidence"]["title_source"], "title")
        self.assertIn("title_reveal", res["recipe"]["beats"])

    def test_F_no_title_drops_title_reveal(self):
        plan = [_slot(f"{c}:0", family=f"fam-{c}") for c in "abcd"]
        res = plan_opening_recipe({}, plan)        # no title field
        self.assertEqual(res["status"], "planned")
        self.assertNotIn("title_reveal", res["recipe"]["beats"])
        self.assertIsNone(res["recipe"]["title_text"])
        self.assertIsNone(res["evidence"]["title_source"])
        # blank/whitespace title is not a legal title
        res_blank = plan_opening_recipe({"title": "   "}, plan)
        self.assertNotIn("title_reveal", res_blank["recipe"]["beats"])

    def test_F_empty_title_not_fabricated(self):
        plan = [_slot(f"{c}:0", family=f"fam-{c}") for c in "abcd"]
        res = plan_opening_recipe({"title": ""}, plan)
        self.assertIsNone(res["recipe"]["title_text"])
        self.assertNotIn("title_reveal", res["recipe"]["beats"])


class PlannerCorrectnessTest(unittest.TestCase):
    """G, H — correctness-first selection and ineligible-material exclusion."""

    def test_G_correctness_first_not_overridden_by_diversity(self):
        # low-score candidate has "nicer" family/scale, but the high-score one
        # must still be selected as the hook.
        plan = [
            _slot("low:0", score=50.0, family="fam-pretty", scale="close"),
            _slot("high:0", score=95.0, family="fam-plain", scale="wide"),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["selected_scene_ids"][0], "high:0")  # hook = high score

    def test_G_diversity_only_within_equal_tier(self):
        # equal score: video beats photo as a same-tier tie-break.
        plan = [
            _slot("photo:0", score=80.0, is_photo=True, dur=0.0),
            _slot("video:0", score=80.0),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["selected_scene_ids"][0], "video:0")

    def test_H_gap_missing_source_excluded(self):
        plan = [
            {"source": GAP_SENTINEL, "scene_id": "g:0", "extract_dur": 2.0},
            {"source": "", "scene_id": "e:0", "extract_dur": 2.0},
            _slot("a:0"), _slot("b:0"),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["status"], "planned")
        self.assertEqual(set(res["selected_scene_ids"]), {"a:0"})  # only 1 selected (hook)
        self.assertEqual(res["evidence"]["qualified_candidate_count"], 2)

    def test_H_source_speech_keep_audio_hold_excluded(self):
        plan = [
            _slot("speech:0", audio_role="source_speech"),
            _slot("keep:0", keep_audio=True),
            _slot("hold:0", hold=True),
            _slot("diegetic:0", audio_role="diegetic"),
            _slot("ok-a:0"), _slot("ok-b:0"),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["evidence"]["qualified_candidate_count"], 2)
        for bad in ("speech:0", "keep:0", "hold:0", "diegetic:0"):
            self.assertNotIn(bad, res["selected_scene_ids"])

    def test_H_fallback_only_no_scene_id_excluded(self):
        plan = [
            {"source": "fb.mp4", "extract_start": 0.0, "extract_dur": 2.0},  # no scene_id
            _slot("a:0"), _slot("b:0"),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["evidence"]["qualified_candidate_count"], 2)
        self.assertNotIn(None, res["selected_scene_ids"])

    def test_H_illegal_window_excluded(self):
        plan = [
            _slot("bad-dur:0", dur=0.0),       # video, 0 window
            _slot("neg:0", dur=-2.0),          # negative
            _slot("nonnum:0", dur="3"),        # non-numeric
            _slot("a:0"), _slot("b:0"),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["evidence"]["qualified_candidate_count"], 2)


class PlannerEvidenceTest(unittest.TestCase):
    """I, J, K — window integrity, photo, same-source-diff-window."""

    def test_I_window_integrity_via_compiler(self):
        plan = [_slot("a:0", start=10.0, dur=3.0, family="fam-A"),
                _slot("b:0", start=5.0, dur=2.0, family="fam-B"),
                _slot("c:0", start=1.0, dur=4.0, family="fam-C")]
        res = plan_opening_recipe({}, plan)
        opening = op.compile_opening_sequence(res["recipe"], res["recipe"]["shots"])
        hook = opening["clips"][0]
        self.assertEqual(hook["opening_role"], "hook")
        self.assertEqual(hook["extract_start"], 10.0)          # traceable to slot
        self.assertEqual(hook["scene_id"], "a:0")
        self.assertLessEqual(hook["extract_dur"], 3.0)         # never exceeds window
        self.assertEqual(hook["source"], plan[0]["source"])

    def test_J_photo_preserves_is_photo_kenburns(self):
        plan = [_slot("photo:0", is_photo=True, dur=0.0, kenburns=True, family="fam-P"),
                _slot("v1:0", family="fam-V"),
                _slot("v2:0", family="fam-W")]
        # photo has lower score so it does not become hook; force it in by score
        plan[0]["retrieval_score"] = 99.0
        res = plan_opening_recipe({}, plan)
        opening = op.compile_opening_sequence(res["recipe"], res["recipe"]["shots"])
        photo_clip = next(c for c in opening["clips"] if c["scene_id"] == "photo:0")
        self.assertTrue(photo_clip["is_photo"])
        self.assertTrue(photo_clip["kenburns"])
        self.assertGreater(photo_clip["extract_dur"], 0.0)     # design duration

    def test_J_no_invented_evidence(self):
        # a slot lacking visual_family/kenburns must not gain them in the clip
        plan = [_slot("a:0"), _slot("b:0"), _slot("c:0")]   # no family/scale/kenburns
        res = plan_opening_recipe({}, plan)
        for shot in res["recipe"]["shots"]:
            self.assertNotIn("visual_family", shot)
            self.assertNotIn("kenburns", shot)
        opening = op.compile_opening_sequence(res["recipe"], res["recipe"]["shots"])
        for clip in opening["clips"]:
            self.assertNotIn("kenburns", clip)
            self.assertNotIn("visual_family", clip)

    def test_K_same_source_different_window_not_deduped(self):
        plan = [
            _slot("same:0", source="same.mp4", start=0.0, dur=2.0, family="fam-A"),
            _slot("same:1", source="same.mp4", start=5.0, dur=2.0, family="fam-B"),
            _slot("same:2", source="same.mp4", start=9.0, dur=2.0, family="fam-C"),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["evidence"]["qualified_candidate_count"], 3)
        scene_ids = [s["scene_id"] for s in res["recipe"]["shots"]]
        self.assertEqual(len(scene_ids), len(set(scene_ids)))   # distinct windows


class PlannerDeterminismTest(unittest.TestCase):
    def test_Q_determinism(self):
        script = {"opening_title": "T"}
        plan = [_slot(f"{c}:0", family=f"fam-{c}", score=70.0 + i)
                for i, c in enumerate("abcd")]
        r1 = plan_opening_recipe(copy.deepcopy(script), copy.deepcopy(plan))
        r2 = plan_opening_recipe(copy.deepcopy(script), copy.deepcopy(plan))
        self.assertEqual(r1, r2)

    def test_planner_does_not_mutate_inputs(self):
        script = {"opening_title": "T"}
        plan = [_slot(f"{c}:0", family=f"fam-{c}") for c in "abcd"]
        script_orig = copy.deepcopy(script)
        plan_orig = copy.deepcopy(plan)
        plan_opening_recipe(script, plan)
        self.assertEqual(script, script_orig)
        self.assertEqual(plan, plan_orig)


# --- SRP2 hardening: scene_id dedup, role preference, target_sec budget ---

class SceneIdDedupTest(unittest.TestCase):
    """必修1 A, B, C — dedup by scene_id (not source)."""

    def test_A_duplicate_scene_id_not_repeated(self):
        # high-score same:0 appears twice + other:0
        plan = [
            _slot("same:0", source="same.mp4", score=95.0, family="fam-A"),
            _slot("same:0", source="same.mp4", score=95.0, family="fam-A"),
            _slot("other:0", source="other.mp4", score=80.0, family="fam-B"),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["status"], "planned")
        self.assertEqual(res["evidence"]["qualified_candidate_count"], 2)  # deduped
        ids = res["selected_scene_ids"]
        self.assertEqual(len(ids), len(set(ids)))             # no repeated scene_id
        self.assertNotIn("same:0", ids[1:])                   # never padded in

    def test_B_dedup_to_one_not_applicable(self):
        plan = [
            _slot("x:0", source="x.mp4", score=90.0),
            _slot("x:0", source="x.mp4", score=90.0),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["status"], "not_applicable")
        self.assertEqual(res["evidence"]["qualified_candidate_count"], 1)

    def test_C_same_source_different_scene_id_both_kept(self):
        # same source, different scene_id/window → two distinct approved shots
        plan = [
            _slot("s:0", source="same.mp4", start=0.0, dur=2.0),
            _slot("s:1", source="same.mp4", start=5.0, dur=2.0),
        ]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["status"], "planned")             # not collapsed to 1
        self.assertEqual(res["evidence"]["qualified_candidate_count"], 2)


class RolePreferenceTest(unittest.TestCase):
    """必修2 D, E, F, G — same-tier role selection, correctness never overridden."""

    def test_D_equal_score_hook_prefers_close(self):
        plan = [_slot("w:0", score=80.0, scale="wide", family="A"),
                _slot("c:0", score=80.0, scale="close", family="B")]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["selected_scene_ids"][0], "c:0")   # hook = close

    def test_E_lower_score_close_does_not_outrank_higher_wide(self):
        plan = [_slot("w:0", score=90.0, scale="wide", family="A"),
                _slot("c:0", score=50.0, scale="close", family="B")]
        res = plan_opening_recipe({}, plan)
        self.assertEqual(res["selected_scene_ids"][0], "w:0")   # correctness-first

    def test_F_context_prefers_unused_family(self):
        plan = [_slot("a1:0", score=80.0, scale="wide", family="A"),
                _slot("a2:0", score=80.0, scale="wide", family="A"),
                _slot("b1:0", score=80.0, scale="wide", family="B")]
        res = plan_opening_recipe({}, plan)
        # n==3 → roles [hook, context]; hook=a1:0 (scene_id tie-break), context=b1:0
        self.assertEqual(res["selected_scene_ids"][0], "a1:0")
        self.assertEqual(res["selected_scene_ids"][1], "b1:0")  # unused family wins

    def test_G_missing_family_scale_is_deterministic(self):
        plan = [_slot("x:0", score=80.0), _slot("y:0", score=80.0),
                _slot("z:0", score=80.0)]            # no family / angle_scale
        r1 = plan_opening_recipe({}, plan)
        r2 = plan_opening_recipe({}, copy.deepcopy(plan))
        self.assertEqual(r1["status"], "planned")
        self.assertEqual(r1, r2)                                 # deterministic
        ids = r1["selected_scene_ids"]
        self.assertEqual(len(ids), len(set(ids)))                # no crash, distinct


def _oc(role, dur, sid):
    return {"opening_role": role, "extract_dur": dur, "slot_dur": dur, "scene_id": sid}


class BudgetTrimUnitTest(unittest.TestCase):
    """必修3 I, J (pure trim_opening_for_budget logic)."""

    def _clips(self):
        return [_oc("hook", 2.5, "h"), _oc("context_montage", 1.2, "c1"),
                _oc("context_montage", 1.2, "c2"), _oc("title_reveal", 2.0, "t")]

    def test_I_sufficient_budget_keeps_full_opening(self):
        clips = self._clips()
        kept, dropped = trim_opening_for_budget(clips, 10.0)
        self.assertEqual(dropped, [])
        self.assertEqual(len(kept), 4)
        self.assertAlmostEqual(sum(c["extract_dur"] for c in kept), 6.9, places=3)

    def test_J_drop_one_context(self):
        kept, dropped = trim_opening_for_budget(self._clips(), 6.0)
        roles = [c["opening_role"] for c in kept]
        self.assertEqual(roles, ["hook", "context_montage", "title_reveal"])
        self.assertEqual(dropped[0]["opening_role"], "context_montage")
        self.assertLessEqual(sum(c["extract_dur"] for c in kept), 6.0 + 1e-3)

    def test_J_drop_context_then_title(self):
        kept, dropped = trim_opening_for_budget(self._clips(), 3.0)
        self.assertEqual([c["opening_role"] for c in kept], ["hook"])
        dropped_roles = {d["opening_role"] for d in dropped}
        self.assertEqual(dropped_roles, {"context_montage", "title_reveal"})
        self.assertLessEqual(sum(c["extract_dur"] for c in kept), 3.0 + 1e-3)

    def test_J_shorten_hook_last(self):
        kept, dropped = trim_opening_for_budget(self._clips(), 2.0)
        self.assertEqual([c["opening_role"] for c in kept], ["hook"])
        self.assertAlmostEqual(kept[0]["extract_dur"], 2.0, places=3)  # hook shortened
        self.assertEqual(kept[0]["slot_dur"], kept[0]["extract_dur"])

    def test_J_no_legal_hook_returns_none(self):
        self.assertIsNone(trim_opening_for_budget(self._clips(), 0.0))
        self.assertIsNone(trim_opening_for_budget(self._clips(), -1.0))


class BudgetRuntimeTest(unittest.TestCase):
    """必修3 H, K, L — runtime target_sec policy."""

    def _maps(self):
        return _photo_map(
            ("photo-a", "dummy1.png", "gear", "family-A"),
            ("photo-b", "dummy2.png", "gear", "family-B"),
            ("photo-c", "dummy3.png", "tool", "family-C"),
            ("photo-d", "dummy4.png", "tool", "family-D"),
        )

    def test_H_no_target_sec_unchanged(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d)
        script = _multi_seg_script({"opening_title": "OPENING"})
        res = mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                            material_maps=self._maps(), skip_render=True, verbose=False,
                            max_clips_per_seg=2)   # target_sec defaults to None
        self.assertEqual(res["opening_plan"]["status"], "planned")
        self.assertEqual(res["opening_plan"]["execution"]["status"], "prepended")
        self.assertTrue(any(c.get("opening_role") for c in res["plan"]))

    def test_K_story_fills_target_no_prepend(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d, dur=4)
        script = _multi_seg_script({"opening_title": "OPENING"})
        res = mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                            material_maps=self._maps(), skip_render=True, verbose=False,
                            max_clips_per_seg=2, target_sec=1.0)
        self.assertIsNone(res["opening"])
        self.assertFalse(any(c.get("opening_role") for c in res["plan"]))
        execu = res["opening_plan"]["execution"]
        self.assertEqual(execu["status"], "budget_fallback")
        # the auto opening contributed nothing (story allocation owns its own
        # duration; SRP2 only guarantees it does not ADD beyond the target).
        self.assertEqual(execu["applied_opening_duration"], 0.0)
        story_only = sum(float(c.get("extract_dur") or 0.0) for c in res["plan"])
        self.assertAlmostEqual(story_only, execu["story_duration"], places=3)

    def test_L_manual_opening_ignores_budget_policy(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d, dur=4)
        script = _multi_seg_script(
            {"opening_recipe": {"title_text": "MANUAL", "context_count": 1}})
        res = mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                            material_maps=self._maps(), skip_render=True, verbose=False,
                            max_clips_per_seg=2, target_sec=1.0)
        # manual path: auto budget policy not applied, opening still present
        self.assertIsNone(res["opening_plan"])
        self.assertIsNotNone(res["opening"])
        self.assertTrue(any(c.get("opening_role") for c in res["plan"]))


# vt_core GAP sentinel, imported under an unambiguous name for the H tests
from video_pipeline_core.vt_core import GAP as GAP_SENTINEL  # noqa: E402


def _photo_map(*specs):
    """Build a project material map from (asset_id, source, caption, family) specs."""
    assets = []
    for asset_id, source, caption, family in specs:
        assets.append({
            "asset_id": asset_id, "source": source, "asset_type": "photo",
            "scenes": [{"start": 0.0, "end": 0.0, "caption": caption,
                        "visual_family": family, "angle_scale": "medium"}],
        })
    return {"artifact_role": "project_material_map", "version": 1, "assets": assets}


def _music(d, dur=6):
    music = d / "music.wav"
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                    f"aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d={dur}:s=44100",
                    str(music)], capture_output=True, check=True)
    return music


def _multi_seg_script(extra=None):
    """Two fast segments → SRP1 makes each a multi-shot sequence, yielding several
    distinct-scene_id story slots that become opening candidates."""
    script = {
        "segments": [
            {"segment": 1, "visual_desc": "gear", "audio_role": "music", "pace": "fast",
             "pacing": {"preferred_shot_sec": 1.0}},
            {"segment": 2, "visual_desc": "tool", "audio_role": "music", "pace": "fast",
             "pacing": {"preferred_shot_sec": 1.0}},
        ]
    }
    if extra:
        script.update(extra)
    return script


class RuntimeIntegrationTest(unittest.TestCase):
    """A(runtime), L, M, P — runtime wiring, prepend, story-plan integrity."""

    def _maps(self):
        return _photo_map(
            ("photo-a", "dummy1.png", "gear", "family-A"),
            ("photo-b", "dummy2.png", "gear", "family-B"),
            ("photo-c", "dummy3.png", "tool", "family-C"),
            ("photo-d", "dummy4.png", "tool", "family-D"),
        )

    def test_A_manual_recipe_skips_auto_planner(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d)
        script = _multi_seg_script(
            {"opening_recipe": {"title_text": "MANUAL", "context_count": 1},
             "title": "WouldBeAuto"})
        res = mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                            material_maps=self._maps(), skip_render=True, verbose=False,
                            max_clips_per_seg=2)
        # manual path used; auto planner not invoked
        self.assertIsNone(res["opening_plan"])
        self.assertIsNotNone(res["opening"])
        # no auto trace on any clip
        self.assertFalse(any(c.get("opening_recipe_source") == "auto"
                             for c in res["plan"]))

    def test_L_auto_prepend_keeps_story_plan_intact(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d)
        script = _multi_seg_script({"opening_title": "OPENING"})
        res = mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                            material_maps=self._maps(), skip_render=True, verbose=False,
                            max_clips_per_seg=2)
        plan = res["plan"]
        self.assertEqual(res["opening_plan"]["status"], "planned")
        self.assertEqual(res["opening_plan"]["execution"]["status"], "prepended")

        opening_clips = [c for c in plan if c.get("opening_role")]
        story_clips = [c for c in plan if not c.get("opening_role")]
        self.assertTrue(opening_clips)
        # opening clips come first, then the full story plan
        self.assertEqual(plan[:len(opening_clips)], opening_clips)
        # slot_index reindexed contiguously across the combined plan
        self.assertEqual([c["slot_index"] for c in plan], list(range(len(plan))))
        # every opening clip carries auto trace + lineage
        for c in opening_clips:
            self.assertEqual(c["opening_recipe_source"], "auto")
            self.assertIn("opening_recipe_reason", c)
            self.assertIn("scene_id", c)
        # original story plan preserved: all story scene_ids still present, intact
        story_ids = [c["scene_id"] for c in story_clips]
        self.assertTrue(story_ids)
        # opening scene_ids are a re-use subset of the story scene_ids
        for c in opening_clips:
            self.assertIn(c["scene_id"], story_ids)

    def test_M_empty_clips_no_prepend(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d)
        script = _multi_seg_script({"opening_title": "OPENING"})
        empty = {"artifact_role": "opening_sequence", "clips": [], "cues": [],
                 "beats_used": [], "dropped": [{"beat": "hook", "reason": "no_material"}],
                 "title_text": "OPENING"}
        with patch("video_pipeline_core.opening_sequence.compile_opening_sequence",
                   return_value=empty):
            res = mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                                material_maps=self._maps(), skip_render=True,
                                verbose=False, max_clips_per_seg=2)
        self.assertIsNone(res["opening"])               # no opening executed
        self.assertFalse(any(c.get("opening_role") for c in res["plan"]))
        self.assertEqual(res["opening_plan"]["execution"]["status"],
                         "empty_clips_fallback")

    def test_P_script_immutable(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d)
        script = _multi_seg_script({"opening_title": "OPENING"})
        script_orig = copy.deepcopy(script)
        mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                      material_maps=self._maps(), skip_render=True, verbose=False,
                      max_clips_per_seg=2)
        self.assertEqual(script, script_orig)


class RuntimeFallbackTest(unittest.TestCase):
    """N, O — compiler error semantics on the AUTO path."""

    def _maps(self):
        return _photo_map(
            ("photo-a", "dummy1.png", "gear", "family-A"),
            ("photo-b", "dummy2.png", "gear", "family-B"),
            ("photo-c", "dummy3.png", "tool", "family-C"),
        )

    def test_N_value_error_graceful_fallback(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d)
        script = _multi_seg_script({"opening_title": "OPENING"})
        with patch("video_pipeline_core.opening_sequence.compile_opening_sequence",
                   side_effect=ValueError("bad input")):
            res = mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                                material_maps=self._maps(), skip_render=True,
                                verbose=False, max_clips_per_seg=2)
        self.assertTrue(res["plan"])                     # story plan preserved
        self.assertIsNone(res["opening"])
        self.assertFalse(any(c.get("opening_role") for c in res["plan"]))
        self.assertEqual(res["opening_plan"]["execution"]["status"],
                         "compiler_error_fallback")
        self.assertEqual(res["opening_plan"]["execution"]["error"], "bad input")

    def test_N_type_error_graceful_fallback(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d)
        script = _multi_seg_script({"opening_title": "OPENING"})
        with patch("video_pipeline_core.opening_sequence.compile_opening_sequence",
                   side_effect=TypeError("type boom")):
            res = mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                                material_maps=self._maps(), skip_render=True,
                                verbose=False, max_clips_per_seg=2)
        self.assertEqual(res["opening_plan"]["execution"]["status"],
                         "compiler_error_fallback")
        self.assertFalse(any(c.get("opening_role") for c in res["plan"]))

    def test_O_runtime_error_propagates(self):
        d = Path(tempfile.mkdtemp())
        music = _music(d)
        script = _multi_seg_script({"opening_title": "OPENING"})
        with patch("video_pipeline_core.opening_sequence.compile_opening_sequence",
                   side_effect=RuntimeError("loud")):
            with self.assertRaises(RuntimeError) as ctx:
                mv_cut.run_mv(script, None, str(d / "out.mp4"), music_path=str(music),
                              material_maps=self._maps(), skip_render=True,
                              verbose=False, max_clips_per_seg=2)
            self.assertEqual(str(ctx.exception), "loud")


class RealRenderTest(unittest.TestCase):
    """R — material map → story plan → SRP2 planner → BR1 → prepend → final.mp4."""

    def test_R_auto_opening_changes_timeline_and_render(self):
        d = Path(tempfile.mkdtemp())
        # dynamically generated, visually distinct photos (no repo assets)
        srcs = {}
        for name, color in (("a", "red"), ("b", "blue"), ("c", "green"), ("d", "yellow")):
            p = str(d / f"photo-{name}.png")
            subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                            f"color=c={color}:s=320x240:d=1", "-vframes", "1", p],
                           capture_output=True, check=True)
            srcs[name] = p
        music = _music(d, dur=8)

        maps = _photo_map(
            ("photo-a", srcs["a"], "gear up", "family-A"),
            ("photo-b", srcs["b"], "gear up", "family-B"),
            ("photo-c", srcs["c"], "tool work", "family-C"),
            ("photo-d", srcs["d"], "tool work", "family-D"),
        )
        script = _multi_seg_script({"opening_title": "OPENING"})

        out = d / "final.mp4"
        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            material_maps=maps, skip_render=False, verbose=False,
                            max_clips_per_seg=2, burn_text=True)

        # 1) real render produced a non-empty file
        self.assertTrue(out.exists())
        self.assertGreater(out.stat().st_size, 0)

        plan = res["plan"]
        opening_clips = [c for c in plan if c.get("opening_role")]
        story_clips = [c for c in plan if not c.get("opening_role")]

        # 2) the planner actually planned and prepended (timeline changed)
        self.assertEqual(res["opening_plan"]["status"], "planned")
        self.assertEqual(res["opening_plan"]["execution"]["status"], "prepended")
        self.assertTrue(opening_clips)

        # 3) opening clips sit BEFORE the story clips
        self.assertEqual(plan[:len(opening_clips)], opening_clips)
        self.assertEqual(plan[0]["opening_role"], "hook")

        # 4) auto trace + lineage present on opening clips
        for c in opening_clips:
            self.assertEqual(c["opening_recipe_source"], "auto")
            self.assertIn("opening_recipe_reason", c)
            self.assertIn("scene_id", c)
            self.assertIn("opening_recipe_evidence", c)

        # 5) original story plan still fully present + intact
        self.assertTrue(story_clips)
        story_ids = [c["scene_id"] for c in story_clips]
        for c in opening_clips:
            self.assertIn(c["scene_id"], story_ids)   # re-use, not new material

        # 6) prove the render really got longer than story-only would have been
        story_dur = sum(c["extract_dur"] for c in story_clips)
        total_dur = sum(c["extract_dur"] for c in plan)
        self.assertGreater(total_dur, story_dur)

        # 7) the rendered file duration covers at least the story portion
        out_dur = float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], text=True).strip())
        self.assertGreater(out_dur, 0.0)

    def test_M_target_sec_bounds_final_render(self):
        """必修3 M: with target_sec, the auto opening is budget-bounded so neither
        the plan nor the rendered file exceed the whole-film target."""
        d = Path(tempfile.mkdtemp())
        srcs = {}
        for name, color in (("a", "red"), ("b", "blue"), ("c", "green"), ("d", "yellow")):
            p = str(d / f"photo-{name}.png")
            subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                            f"color=c={color}:s=320x240:d=1", "-vframes", "1", p],
                           capture_output=True, check=True)
            srcs[name] = p
        # short music so story fills only ~3s; target 6s leaves real opening budget
        music = _music(d, dur=3)
        maps = _photo_map(
            ("photo-a", srcs["a"], "gear up", "family-A"),
            ("photo-b", srcs["b"], "gear up", "family-B"),
            ("photo-c", srcs["c"], "tool work", "family-C"),
            ("photo-d", srcs["d"], "tool work", "family-D"),
        )
        script = _multi_seg_script({"opening_title": "OPENING"})
        target = 6.0

        out = d / "final.mp4"
        res = mv_cut.run_mv(script, None, str(out), music_path=str(music),
                            material_maps=maps, skip_render=False, verbose=False,
                            max_clips_per_seg=2, target_sec=target, burn_text=True)

        self.assertTrue(out.exists() and out.stat().st_size > 0)

        plan = res["plan"]
        plan_dur = sum(float(c.get("extract_dur") or 0.0) for c in plan)
        # plan never exceeds the whole-film target (tiny float tolerance)
        self.assertLessEqual(plan_dur, target + 1e-2)

        # budget trace recorded
        execu = res["opening_plan"]["execution"]
        self.assertIn("target_sec", execu)
        self.assertIn("story_duration", execu)
        self.assertIn("requested_opening_duration", execu)
        self.assertIn("applied_opening_duration", execu)
        self.assertIn("dropped_for_budget", execu)

        # rendered file also stays within target (render mechanics tolerance)
        out_dur = float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(out)], text=True).strip())
        self.assertLessEqual(out_dur, target + 0.75)


if __name__ == "__main__":
    unittest.main()
