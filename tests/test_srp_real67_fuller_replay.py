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

    def test_short_cut_is_not_success(self):
        mp, needs, gaps, script, result = self._ctx()
        rep = F.compute_fuller_report(
            result, mp, script, needs, gaps, footage_root=r"C:\f",
            render_sec=42.0, slot_check={"ok": True, "checked_slots": 5, "failed_slots": []},
            music_name="m.mp4", capabilities={}, min_candidates=2)
        self.assertFalse(rep["success"])
        self.assertEqual(rep["duration_gate"]["status"], "insufficient_material")

    def test_long_clean_cut_is_success(self):
        mp, needs, gaps, script, result = self._ctx()
        rep = F.compute_fuller_report(
            result, mp, script, needs, gaps, footage_root=r"C:\f",
            render_sec=75.0, slot_check={"ok": True, "checked_slots": 5, "failed_slots": []},
            music_name="m.mp4", capabilities={}, min_candidates=2)
        self.assertTrue(rep["success"])
        self.assertEqual(rep["semantic_alignment"]["drift_segments"], [])
        self.assertTrue(rep["material_gaps"])  # 感謝導師 thin gap is surfaced

    def test_report_md_renders_gate_and_gaps(self):
        mp, needs, gaps, script, result = self._ctx()
        rep = F.compute_fuller_report(
            result, mp, script, needs, gaps, footage_root=r"C:\f",
            render_sec=42.0, slot_check={"ok": True, "checked_slots": 5, "failed_slots": []},
            music_name="m.mp4",
            capabilities={"VD2": {"active": True, "evidence": "x"},
                          "SRP1": {"active": True, "evidence": "y"},
                          "SRP2": {"active": True, "evidence": "z"},
                          "SRP3": {"active": False, "evidence": "w"}},
            min_candidates=2)
        md = F.report_md(rep)
        self.assertIn("Success: False", md)
        self.assertIn("Material gaps", md)
        self.assertIn("insufficient_material", md.lower() + rep["duration_gate"]["status"])


if __name__ == "__main__":
    unittest.main()
