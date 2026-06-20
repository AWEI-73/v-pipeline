"""Unit tests for R67-F1 fuller material replay (pure planning, no footage/render).

Pins: scene-window sampling away from the head, folder→need mapping with canonical
satisfies edges, candidate-count material gaps, fuller script shape, capability
attribution, and the 60s success gate (a short cut is never reported as success).
"""
import unittest

import tools.srp_real67_fuller_replay as F
from tools.srp_real67_fuller_replay import Blocked


def _index():
    """folder -> [(filename, source_path, duration_sec)]; mixes rich and thin needs."""
    return {
        "主任勉勵": [("IMG_2118.MOV", r"C:\footage\主任勉勵\IMG_2118.MOV", 70.0),
                    ("IMG_2119.MOV", r"C:\footage\主任勉勵\IMG_2119.MOV", 40.0)],
        "換桿": [("a.mp4", r"C:\footage\換桿\a.mp4", 30.0),
                ("b.mp4", r"C:\footage\換桿\b.mp4", 25.0)],
        "慶生會": [("c.mp4", r"C:\footage\慶生會\c.mp4", 56.0)],
        "感謝導師": [("d.mp4", r"C:\footage\感謝導師\d.mp4", 5.0)],  # thin: 1 scene
        "運動會": [("e.mp4", r"C:\footage\運動會\e.mp4", 20.0)],
    }


class TestSceneWindows(unittest.TestCase):
    def test_samples_inside_head_and_tail(self):
        wins = F.scene_windows(70.0, max_scenes=3)
        self.assertTrue(wins)
        self.assertGreaterEqual(wins[0][0], 70.0 * 0.12 - 2.0)  # not at the very start
        self.assertLessEqual(wins[-1][1], 70.0)
        for s, e in wins:
            self.assertGreater(e, s)

    def test_count_scales_and_caps(self):
        self.assertEqual(len(F.scene_windows(8.0, max_scenes=3)), 1)
        self.assertEqual(len(F.scene_windows(70.0, max_scenes=3)), 3)

    def test_zero_duration_is_empty(self):
        self.assertEqual(F.scene_windows(0.0), [])
        self.assertEqual(F.scene_windows(-3.0), [])


class TestNeedAssets(unittest.TestCase):
    def test_scenes_carry_accepted_satisfies_to_folder_need(self):
        nid = F.need_id_for("換桿")
        assets, candidates = F.build_need_assets(
            "換桿", _index()["換桿"], max_scenes_per_asset=3)
        self.assertEqual(len(assets), 2)
        self.assertGreaterEqual(candidates, 4)
        edge = assets[0]["scenes"][0]["satisfies"][0]
        self.assertEqual(edge, {"need_id": nid, "status": "accepted"})
        self.assertEqual(assets[0]["scenes"][0]["caption"], "換桿")

    def test_need_id_is_deterministic(self):
        self.assertEqual(F.need_id_for("慶生會"), F.need_id_for("慶生會"))
        self.assertNotEqual(F.need_id_for("慶生會"), F.need_id_for("換桿"))


class TestPlanMaterial(unittest.TestCase):
    def test_curated_order_then_extras(self):
        mp, needs, gaps = F.plan_material(_index(), max_needs=12, min_candidates=2)
        folders = [n["folder"] for n in needs]
        # curated order positions are respected for those present
        self.assertEqual(folders[0], "主任勉勵")
        self.assertIn("換桿", folders)
        self.assertEqual(mp["artifact_role"], "project_material_map")
        # every declared need appears in the map's needs list
        self.assertEqual({n["need_id"] for n in mp["needs"]},
                         {n["need_id"] for n in needs})

    def test_thin_need_is_reported_as_gap(self):
        _mp, _needs, gaps = F.plan_material(_index(), min_candidates=2)
        gap_folders = {g["folder"] for g in gaps}
        self.assertIn("感謝導師", gap_folders)  # only a 5s clip -> 1 scene < 2

    def test_max_needs_cap(self):
        _mp, needs, _gaps = F.plan_material(_index(), max_needs=2)
        self.assertEqual(len(needs), 2)

    def test_map_passes_synthetic_guard(self):
        mp, _needs, _gaps = F.plan_material(_index())
        F.DEMO.assert_no_synthetic_sources(mp)  # real paths -> must not raise


class TestFullerScript(unittest.TestCase):
    def test_one_segment_per_need_with_need_ref_and_subtitle(self):
        _mp, needs, _gaps = F.plan_material(_index())
        script = F.build_fuller_script(needs)
        self.assertEqual(len(script["segments"]), len(needs))
        for seg, need in zip(script["segments"], needs):
            self.assertEqual(seg["need_ref"], need["need_id"])
            self.assertIn(need["need_id"], seg["subtitle"])
        self.assertFalse(script["disable_auto_sequence"])
        self.assertFalse(script["disable_auto_opening"])


class TestCapabilityAttribution(unittest.TestCase):
    def test_srp_attributed_from_plan_evidence(self):
        plan = [
            {"segment": 0, "opening_role": "hook", "scene_id": "x:0"},
            {"segment": 1, "scene_id": "a:0", "beat_role": "context", "arc_role": "setup"},
            {"segment": 1, "scene_id": "a:1", "beat_role": "action", "arc_role": "setup"},
        ]
        caps = F.attribute_capabilities(plan)
        self.assertTrue(caps["SRP1"]["active"])     # beat_role present
        self.assertEqual(caps["SRP1"]["evidence"].count("1"), 1)  # segment 1 auto
        self.assertTrue(caps["SRP2"]["active"])     # opening clip
        self.assertTrue(caps["SRP3"]["active"])     # arc roles

    def test_vd2_inactive_without_labels_is_honest(self):
        # 67th footage shape: no visual_family/angle_scale labels on slots.
        plan = [{"segment": 1, "scene_id": "a:0", "beat_role": "action"}]
        caps = F.attribute_capabilities(plan)
        self.assertFalse(caps["VD2"]["active"])
        self.assertIn("no visual_family", caps["VD2"]["evidence"])

    def test_vd2_active_only_with_labels_and_reorder(self):
        plan = [{"segment": 1, "scene_id": "a:0", "visual_family": "wide",
                 "angle_scale": "WS",
                 "diversity_selection_reason": "tier_score=4.0, family_pref=1, "
                                               "scale_pref=1, type_pref=1"}]
        caps = F.attribute_capabilities(plan)
        self.assertTrue(caps["VD2"]["active"])

    def test_inactive_when_evidence_absent(self):
        plan = [{"segment": 1, "scene_id": "a:0",
                 "diversity_selection_reason": "diversity_disabled"}]
        caps = F.attribute_capabilities(plan)
        self.assertFalse(caps["VD2"]["active"])
        self.assertFalse(caps["SRP1"]["active"])
        self.assertFalse(caps["SRP2"]["active"])
        self.assertFalse(caps["SRP3"]["active"])


class TestSoulSelectionDiff(unittest.TestCase):
    def test_reports_real_on_off_flip_when_soul_changes_selected_window(self):
        script = {"segments": [{
            "segment": 1,
            "visual_desc": "training",
            "material_fit": {"visual_desc": "training", "need_refs": ["N01"]},
            "core": {
                "emotional_movement": "fear to courage",
                "intended_viewer_feeling": "brave teacher focus",
            },
        }]}
        material_map = {"assets": [
            {"asset_id": "a", "source": "a.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "training wide",
                 "satisfies": [{"need_id": "N01", "status": "accepted"}]},
            ]},
            {"asset_id": "b", "source": "b.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "training courage teacher closeup",
                 "satisfies": [{"need_id": "N01", "status": "accepted"}]},
            ]},
        ]}

        diff = F.soul_selection_diff(script, material_map, clip_dur=2.0)

        self.assertEqual(diff["segment_count"], 1)
        self.assertEqual(diff["flip_count"], 1)
        seg = diff["segments"][0]
        self.assertEqual(seg["off_scene_id"], "a:0")
        self.assertEqual(seg["on_scene_id"], "b:0")
        self.assertGreater(seg["on_score_breakdown"]["soul"], 0)
        self.assertEqual(diff["zero_flip_reason"], None)

    def test_zero_flip_reports_missing_differentiating_soul_evidence(self):
        script = {"segments": [{
            "segment": 1,
            "visual_desc": "folder theme",
            "material_fit": {"visual_desc": "folder theme", "need_refs": ["N01"]},
            "core": {"emotional_movement": "fear to courage"},
        }]}
        material_map = {"assets": [
            {"asset_id": "a", "source": "a.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "folder theme",
                 "satisfies": [{"need_id": "N01", "status": "accepted"}]},
            ]},
            {"asset_id": "b", "source": "b.mp4", "asset_type": "video", "scenes": [
                {"start": 0, "end": 5, "caption": "folder theme",
                 "satisfies": [{"need_id": "N01", "status": "accepted"}]},
            ]},
        ]}

        diff = F.soul_selection_diff(script, material_map, clip_dur=2.0)

        self.assertEqual(diff["flip_count"], 0)
        self.assertEqual(diff["positive_soul_segments"], 0)
        self.assertIn("no positive soul", diff["zero_flip_reason"])


class TestReportAndGate(unittest.TestCase):
    def _ctx(self):
        mp, needs, gaps = F.plan_material(_index())
        script = F.build_fuller_script(needs)
        # bind each segment to the first scene of its need's first asset
        plan = []
        for i, need in enumerate(needs, start=1):
            asset = next(a for a in mp["assets"]
                         if a["scenes"][0]["satisfies"][0]["need_id"] == need["need_id"])
            plan.append({"segment": i, "scene_id": f"{asset['asset_id']}:0",
                         "source": asset["source"], "extract_dur": 4.0,
                         "arc_role": "setup",
                         "text": {"subtitle": f"Seg {i}"}})
        result = {"plan": plan, "opening_plan": {"status": "planned"},
                  "story_arc_plan": {"status": "planned", "execution": {"status": "applied"}}}
        return mp, needs, gaps, script, result

    def _clean_ctx(self):
        # an index where every need has >=2 scenes (no gaps): drop the thin 感謝導師.
        idx = {k: v for k, v in _index().items() if k != "感謝導師"}
        mp, needs, gaps = F.plan_material(idx, min_candidates=2)
        assert not gaps, gaps
        script = F.build_fuller_script(needs)
        plan = []
        for i, need in enumerate(needs, start=1):
            asset = next(a for a in mp["assets"]
                         if a["scenes"][0]["satisfies"][0]["need_id"] == need["need_id"])
            plan.append({"segment": i, "scene_id": f"{asset['asset_id']}:0",
                         "source": asset["source"], "extract_dur": 4.0,
                         "arc_role": "setup", "text": {"subtitle": f"Seg {i}"}})
        result = {"plan": plan, "opening_plan": {"status": "planned"},
                  "story_arc_plan": {"status": "planned", "execution": {"status": "applied"}}}
        return mp, needs, gaps, script, result

    def _report(self, ctx, *, render_sec, slot_check):
        mp, needs, gaps, script, result = ctx
        return F.compute_fuller_report(
            result, mp, script, needs, gaps, footage_root=r"C:\f",
            render_sec=render_sec, slot_check=slot_check, music_name="m.mp4",
            capabilities={}, min_candidates=2,
            soul_selection=F.soul_selection_diff(script, mp, clip_dur=2.0))

    _OK = {"ok": True, "checked_slots": 5, "failed_slots": []}
    _BAD = {"ok": False, "checked_slots": 5, "failed_slots": [3, 4]}

    # P1: a < 60s cut is an outright fail, never a pass
    def test_short_cut_is_fail(self):
        rep = self._report(self._ctx(), render_sec=42.0, slot_check=self._OK)
        self.assertEqual(rep["status"], "fail")
        self.assertFalse(rep["clean_pass"])

    # P1: material_gaps must NOT be a clean pass — they are findings
    def test_gaps_are_pass_with_findings_not_clean(self):
        rep = self._report(self._ctx(), render_sec=75.0, slot_check=self._OK)
        self.assertTrue(rep["material_gaps"])             # 感謝導師 thin gap present
        self.assertEqual(rep["status"], "pass_with_findings")
        self.assertFalse(rep["clean_pass"])
        self.assertTrue(any("floor" in f for f in rep["findings"]))

    # P1: failed render slots are findings, not clean
    def test_slot_failures_are_pass_with_findings(self):
        rep = self._report(self._clean_ctx(), render_sec=75.0, slot_check=self._BAD)
        self.assertEqual(rep["status"], "pass_with_findings")
        self.assertTrue(any("render gate" in f for f in rep["findings"]))

    # P1: only a >=60s, need-correct, no-gap, all-slots-ok cut is clean_pass
    def test_clean_pass(self):
        rep = self._report(self._clean_ctx(), render_sec=75.0, slot_check=self._OK)
        self.assertEqual(rep["status"], "clean_pass")
        self.assertTrue(rep["clean_pass"])
        self.assertEqual(rep["findings"], [])

    def test_report_md_renders_status_and_findings(self):
        rep = self._report(self._ctx(), render_sec=75.0, slot_check=self._BAD)
        md = F.report_md(rep)
        self.assertIn("Status: PASS_WITH_FINDINGS", md)
        self.assertIn("## Findings", md)
        self.assertIn("Material gaps", md)
        self.assertIn("BSA1 soul selection", md)


class TestRenderableWindows(unittest.TestCase):
    def test_skips_black_windows(self):
        # a probe where frames in [40, 60) are black (low stdev), elsewhere bright
        def probe(_source, t):
            return 2.0 if 40.0 <= t < 60.0 else 30.0
        wins = F.renderable_windows("C:\\v.mp4", 100.0, probe, max_scenes=3)
        self.assertTrue(wins)
        for s, e in wins:
            mid = (s + e) / 2.0
            self.assertFalse(40.0 <= mid < 60.0, f"chose a black window at {mid}")

    def test_rejects_window_when_head_sample_is_black(self):
        # BUILD may later shorten a selected 3.5s scene to ~1.5s, so checking only
        # the scene midpoint can still leave a black/transition frame at render
        # time. A window whose head is black must be rejected even when its mid is
        # bright.
        def probe(_source, t):
            return 2.0 if 23.8 <= t <= 24.1 else 30.0
        wins = F.renderable_windows("C:\\v.mp4", 100.0, probe, max_scenes=3)
        self.assertTrue(wins)
        for s, _e in wins:
            head_sample = round(s + 0.35, 3)
            self.assertFalse(23.8 <= head_sample <= 24.1,
                             f"chose a window with black head sample at {head_sample}")

    def test_rejects_temporally_unstable_window(self):
        # A high-stdev window can still straddle a cut/violent motion. If head/mid
        # source frames are structurally unrelated, small seek/render differences
        # can make the final slot fail source-correlation. Treat that as an
        # unstable window and pick an alternative.
        def probe(_source, t):
            if 23.8 <= t <= 25.7:
                gray = [1, 2, 3, 4] if t < 25.0 else [4, 3, 2, 1]
            else:
                gray = [1, 2, 3, 4]
            return {"stdev": 30.0, "gray": gray}
        wins = F.renderable_windows("C:\\v.mp4", 100.0, probe, max_scenes=3)
        self.assertTrue(wins)
        for s, e in wins:
            self.assertFalse(s <= 24.0 and e >= 25.0,
                             f"chose temporally unstable window {(s, e)}")

    def test_all_black_drops_to_empty(self):
        wins = F.renderable_windows("C:\\v.mp4", 100.0, lambda *_: 1.0, max_scenes=3)
        self.assertEqual(wins, [])

    def test_unreadable_probe_is_not_renderable(self):
        wins = F.renderable_windows("C:\\v.mp4", 100.0, lambda *_: None, max_scenes=3)
        self.assertEqual(wins, [])


if __name__ == "__main__":
    unittest.main()
