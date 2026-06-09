"""Tests for blueprint_to_contract.compile_contract."""
import unittest

from video_pipeline_core import blueprint_to_contract as b2c
from video_pipeline_core import spec_contract, blueprint as bp_mod


def _bp():
    return {
        "artifact_role": "narrative_blueprint", "version": 1,
        "thesis": "a short, real thing", "mode_hint": "warm_documentary",
        "beats": [
            {"id": "B1", "role": "setup", "summary": "quiet open"},
            {"id": "B2", "role": "turn", "summary": "the peak"},
            {"id": "B3", "role": "resolve", "summary": "the speech"},
        ],
    }


def _decisions():
    return {
        "B1": {"content_pattern": "establishing", "material_hint": "open"},
        "B2": {"content_pattern": "action", "emphasis": "hero", "material_hint": "peak",
               "audio": {"role": "diegetic", "original_audio_policy": "keep"}},
        "B3": {"content_pattern": "testimony", "must_include": "director speech"},
    }


class TestCompileContract(unittest.TestCase):
    def setUp(self):
        self.c = b2c.compile_contract(_bp(), _decisions())
        self.segs = self.c["segments"]

    def test_one_segment_per_beat_with_ref(self):
        self.assertEqual(len(self.segs), 3)
        self.assertEqual([s["core"]["blueprint_ref"] for s in self.segs], ["B1", "B2", "B3"])

    def test_editing_grammar_is_segment_level_not_in_core(self):
        # the bug that silently dropped weight: editing_grammar must NOT be in core
        for s in self.segs:
            self.assertIn("editing_grammar", s)
            self.assertNotIn("editing_grammar", s["core"])
        self.assertEqual(self.segs[1]["editing_grammar"]["role"], "hero")

    def test_density_fields_present(self):
        for s in self.segs:
            self.assertIn("required_functions", s["sequence_grammar"])
            self.assertIn("preferred_shot_sec", s["pacing"])
            self.assertIn("content_pattern", s["editing_intent"])

    def test_pace_tiers(self):
        # action -> fast band; establishing -> calm (vis pace fast, slow band);
        # testimony -> hold
        by = {s["core"]["blueprint_ref"]: s for s in self.segs}
        self.assertEqual(by["B2"]["visual_style"]["pace"], "fast")
        self.assertEqual(by["B2"]["pacing"]["preferred_shot_sec"], [1.5, 4])
        self.assertEqual(by["B1"]["visual_style"]["pace"], "fast")      # calm maps to cutting
        self.assertEqual(by["B1"]["pacing"]["preferred_shot_sec"], [4, 8])
        self.assertEqual(by["B3"]["visual_style"]["pace"], "hold")

    def test_honesty_guard_trace(self):
        by = {s["core"]["blueprint_ref"]: s for s in self.segs}
        self.assertEqual(by["B3"]["_honesty"], "real_material_only")
        self.assertEqual(by["B3"]["audio"]["original_audio_policy"], "keep")
        self.assertEqual(by["B3"]["text_layer"]["subtitle"], "auto")
        self.assertIn("collection_instructions", by["B3"]["material_fit"])

    def test_output_validates_and_beat_gate_passes(self):
        v = spec_contract.validate_segment_contract(self.c)
        self.assertTrue(v["ok"], v.get("errors"))
        cov = bp_mod.beat_coverage(_bp(), self.c)
        self.assertTrue(cov["pass"])
        self.assertEqual(cov["dropped"], [])
        self.assertEqual(cov["invalid_refs"], [])

    def test_missing_decision_raises(self):
        bp = _bp()
        with self.assertRaises(ValueError):
            b2c.compile_contract(bp, {"B1": {"content_pattern": "action"}})  # B2/B3 missing


if __name__ == "__main__":
    unittest.main()
