"""Unit tests for the 67th real-footage review demo harness.

These are PURE tests: no real footage, no render. They pin the review contract —
need_ref + subtitle per segment, SRT derivation, semantic-alignment surfacing,
fail-closed behavior, subset-boundary disclosure, no-synthetic guard, and scope
containment (no delivery-gate / Node14 / UI / effects coupling).
"""
import json
import unittest
from pathlib import Path

import tools.srp_real67_review_demo as DEMO
from tools.srp_real67_review_demo import Blocked

REPO = Path(__file__).resolve().parent.parent


def _covered_map():
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [
            {"asset_id": "director_encouragement", "asset_type": "video",
             "source": r"C:\footage\主任勉勵\IMG_2118.MOV",
             "scenes": [{"start": 0.0, "end": 6.0, "caption": "主任對學員的期勉講話",
                         "satisfies": [{"need_id": "nd_dir", "status": "accepted"}]}]},
            {"asset_id": "birthday", "asset_type": "video",
             "source": r"C:\footage\慶生會\IMG_1408.MOV",
             "scenes": [{"start": 0.0, "end": 6.0, "caption": "結訓期間的慶生會同樂",
                         "satisfies": [{"need_id": "nd_bday", "status": "accepted"}]}]},
            {"asset_id": "thanks_mentor", "asset_type": "video",
             "source": r"C:\footage\感謝導師\67期養成班0326-3.mp4",
             "scenes": [{"start": 0.0, "end": 6.0, "caption": "學員感謝導師的橋段",
                         "satisfies": [{"need_id": "nd_thx", "status": "accepted"}]}]},
        ],
        "needs": [{"need_id": "nd_dir"}, {"need_id": "nd_bday"}, {"need_id": "nd_thx"}],
    }


def _runtime_script():
    def seg(num, nid, desc):
        return {"segment": num, "visual_desc": desc,
                "material_fit": {"visual_desc": desc, "need_refs": [nid]}}
    return {"style": "mv", "segments": [
        seg(1, "nd_dir", "主任對學員的期勉講話"),
        seg(2, "nd_bday", "結訓期間的慶生會同樂"),
        seg(3, "nd_thx", "學員感謝導師的橋段")]}


def _plan_matched():
    """A need-correct plan: 1 hook opening + 3 story slots bound to the right need."""
    return [
        {"slot_index": 0, "segment": 0, "scene_id": "birthday:0", "opening_role": "hook",
         "source": r"C:\footage\慶生會\IMG_1408.MOV", "extract_dur": 2.0, "text": None},
        {"slot_index": 1, "segment": 1, "scene_id": "director_encouragement:0",
         "arc_role": "setup", "source": r"C:\f\a.MOV", "extract_dur": 3.0,
         "text": {"subtitle": "Seg 1 | nd_dir 主任對學員的期勉講話"}},
        {"slot_index": 2, "segment": 2, "scene_id": "birthday:0", "arc_role": "climax",
         "source": r"C:\f\b.MOV", "extract_dur": 3.0,
         "text": {"subtitle": "Seg 2 | nd_bday 結訓期間的慶生會同樂"}},
        {"slot_index": 3, "segment": 3, "scene_id": "thanks_mentor:0", "arc_role": "resolution",
         "source": r"C:\f\c.MOV", "extract_dur": 3.0,
         "text": {"subtitle": "Seg 3 | nd_thx 學員感謝導師的橋段"}},
    ]


class TestReviewScript(unittest.TestCase):
    # A. every segment has need_ref and a subtitle
    def test_need_ref_and_subtitle_per_segment(self):
        out = DEMO.build_review_script(_runtime_script())
        for seg in out["segments"]:
            self.assertTrue(seg["need_ref"], "segment missing need_ref")
            self.assertIn(seg["need_ref"], seg["subtitle"])
            self.assertIn(f"Seg {seg['segment']}", seg["subtitle"])
        # enhanced path keeps auto-structuring on
        self.assertFalse(out["disable_auto_sequence"])
        self.assertFalse(out["disable_auto_opening"])
        self.assertNotIn("story_arc", out)

    # D (partial). a segment without a resolvable need_ref fails closed
    def test_missing_need_ref_blocks(self):
        bad = {"segments": [{"segment": 1, "visual_desc": "x",
                             "material_fit": {"need_refs": []}}]}
        with self.assertRaises(Blocked):
            DEMO.build_review_script(bad)

    def test_empty_script_blocks(self):
        with self.assertRaises(Blocked):
            DEMO.build_review_script({"segments": []})


class TestNeedLookup(unittest.TestCase):
    def test_reads_canonical_satisfies_without_scene_need_projection(self):
        lookup, declared = DEMO.scene_need_lookup(_covered_map())
        self.assertEqual(lookup["director_encouragement:0"], "nd_dir")
        self.assertEqual(lookup["birthday:0"], "nd_bday")
        self.assertEqual(declared, {"nd_dir", "nd_bday", "nd_thx"})
        self.assertNotIn("need_id", _covered_map()["assets"][0]["scenes"][0])


class TestNoSyntheticGuard(unittest.TestCase):
    # F. tool must refuse Gemini synthetic material
    def test_blocks_gemini_source(self):
        m = _covered_map()
        m["assets"][0]["source"] = r"C:\Users\user\.gemini\antigravity\brain\x\n01.png"
        with self.assertRaises(Blocked):
            DEMO.assert_no_synthetic_sources(m)

    def test_allows_real_footage_source(self):
        DEMO.assert_no_synthetic_sources(_covered_map())  # must not raise


class TestReviewSubtitles(unittest.TestCase):
    # B. SRT derives from the timeline, is contiguous, and excludes the opening
    def test_srt_contiguous_and_excludes_opening(self):
        srt = DEMO.timeline_review_srt(_plan_matched())
        self.assertTrue(srt.strip(), "empty SRT")
        # opening clip carries no subtitle, so the first cue starts at the hook's end
        self.assertNotIn("hook", srt)
        # three story cues, one per segment subtitle
        self.assertEqual(srt.count("-->"), 3)
        self.assertIn("Seg 1 | nd_dir", srt)
        self.assertIn("Seg 3 | nd_thx", srt)
        # times are continuous: cue1 end == cue2 start (08.000 line appears twice)
        self.assertIn("00:00:02,000 --> 00:00:05,000", srt)  # after 2.0s opening
        self.assertIn("00:00:05,000 --> 00:00:08,000", srt)


class TestSemanticAlignment(unittest.TestCase):
    # C. alignment lists matched / drift results per segment
    def test_all_matched(self):
        script = DEMO.build_review_script(_runtime_script())
        al = DEMO.semantic_alignment(_plan_matched(), _covered_map(), script)
        self.assertTrue(al["all_matched"])
        self.assertEqual(al["drift_segments"], [])
        self.assertEqual(al["segments"]["1"]["status"], "matched")
        self.assertEqual(al["segments"]["1"]["slots"][0]["selected_need_id"], "nd_dir")

    def test_wrong_need_is_flagged_as_drift(self):
        script = DEMO.build_review_script(_runtime_script())
        plan = _plan_matched()
        # bind segment 1 to the birthday clip (wrong need) -> drift
        plan[1]["scene_id"] = "birthday:0"
        al = DEMO.semantic_alignment(plan, _covered_map(), script)
        self.assertIn(1, al["drift_segments"])
        self.assertEqual(al["segments"]["1"]["status"], "wrong_need")
        self.assertFalse(al["all_matched"])

    def test_missing_slot_is_gap(self):
        script = DEMO.build_review_script(_runtime_script())
        plan = [c for c in _plan_matched() if c.get("segment") != 3]
        al = DEMO.semantic_alignment(plan, _covered_map(), script)
        self.assertEqual(al["segments"]["3"]["status"], "gap")


class TestReport(unittest.TestCase):
    def _report(self):
        script = DEMO.build_review_script(_runtime_script())
        result = {"plan": _plan_matched(),
                  "opening_plan": {"status": "planned"},
                  "story_arc_plan": {"status": "planned", "execution": {"status": "applied"}}}
        slot_check = {"ok": True, "checked_slots": 4, "failed_slots": []}
        return DEMO.compute_review_report(
            result, _covered_map(), script, footage_root=r"C:\footage",
            subset_scene_count=3, render_sec=11.0,
            slot_check=slot_check, music_name="7感性收尾.mp4")

    # E. report discloses the subset boundary
    def test_discloses_subset_boundary(self):
        rep = self._report()
        lim = rep["limitations"]
        self.assertTrue(lim["m6e_covered_subset_only"])
        self.assertEqual(lim["covered_scene_count"], 3)
        self.assertFalse(lim["full_ingest"])
        self.assertFalse(lim["ten_minute_film"])
        self.assertFalse(lim["synthetic_material"])

    # report lists expected need + selected scene per segment
    def test_lists_per_segment_binding(self):
        rep = self._report()
        segs = rep["semantic_alignment"]["segments"]
        self.assertEqual(segs["1"]["expected_need_ref"], "nd_dir")
        self.assertEqual(segs["1"]["slots"][0]["scene_id"], "director_encouragement:0")
        self.assertEqual(rep["need_aware"]["scene_need_ids_stamped"], 0)
        self.assertIn("satisfies", rep["need_aware"]["deterministic_evidence"])

    # SRP1 reports 0 eligible on the 1-slot-per-segment subset, with disclosure
    def test_srp1_zero_eligible_disclosed(self):
        rep = self._report()
        srp1 = rep["srp1_segment_sequence"]
        self.assertEqual(srp1["eligible_count"], 0)
        self.assertIn("subset", srp1["note"].lower())

    # SRP3 cannot prove climax > setup on equal single slots; disclosed honestly
    def test_srp3_climax_not_exceeding_setup_disclosed(self):
        rep = self._report()
        self.assertFalse(rep["srp3_story_arc"]["climax_exceeds_setup"])
        self.assertIn("subset", rep["srp3_story_arc"]["note"].lower())

    def test_report_md_renders(self):
        md = DEMO.report_md(self._report())
        self.assertIn("Per-segment material binding", md)
        self.assertIn("nd_dir", md)
        self.assertIn("review_subtitles.srt", md)
        self.assertIn("contact_sheet.jpg", md)


class TestScopeContainment(unittest.TestCase):
    # G. the harness must not touch delivery gate / Node14 / UI / effects
    def test_no_forbidden_imports(self):
        src = (REPO / "tools" / "srp_real67_review_demo.py").read_text(encoding="utf-8")
        for forbidden in ("delivery_gate", "node14", "node_14", "effects_director",
                          "dashboard", "audio_graph", "HARD_AUDITS"):
            self.assertNotIn(forbidden, src.lower(),
                             f"harness unexpectedly references {forbidden}")


if __name__ == "__main__":
    unittest.main()
