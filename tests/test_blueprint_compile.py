"""Tests for video_pipeline_core.blueprint_compile.

Covers:
  - compile_blueprint_md (valid full markdown parsing, inline feeling, anti-goals)
  - ValueError exceptions for missing thesis or missing beats
"""
import unittest

from video_pipeline_core.blueprint_compile import compile_blueprint_md


class TestBlueprintCompile(unittest.TestCase):
    """Test narrative blueprint markdown compilation."""

    def test_compile_valid_markdown(self):
        md_text = """
Mode: rhythmic_mv
Intended feeling: warm_pride

# Thesis
This is the main thesis of the story. It spans multiple sentences. But only the first sentence is selected.

# Big Story
- [B1|setup] Introduction of the morning routine. [feeling: calm]
- [B2] Preparing the coffee beans.
- [B3|result] Pouring the fresh cup of espresso. {feeling: pride}

# Anti-goals
- Avoid generic pop music.
- Do not use shaky stock videos.
"""
        res = compile_blueprint_md(md_text)
        self.assertEqual(res["artifact_role"], "narrative_blueprint")
        self.assertEqual(res["version"], 1)
        self.assertEqual(res["mode_hint"], "rhythmic_mv")
        self.assertEqual(res["intended_feeling"], "warm_pride")
        self.assertEqual(res["thesis"], "This is the main thesis of the story.")

        # Beats validation
        self.assertEqual(len(res["beats"]), 3)
        self.assertEqual(res["beats"][0]["id"], "B1")
        self.assertEqual(res["beats"][0]["role"], "setup")
        self.assertEqual(res["beats"][0]["summary"], "Introduction of the morning routine.")
        self.assertEqual(res["beats"][0]["intended_feeling"], "calm")

        self.assertEqual(res["beats"][1]["id"], "B2")
        self.assertEqual(res["beats"][1]["role"], "detail")  # default role
        self.assertEqual(res["beats"][1]["summary"], "Preparing the coffee beans.")
        self.assertNotIn("intended_feeling", res["beats"][1])

        self.assertEqual(res["beats"][2]["id"], "B3")
        self.assertEqual(res["beats"][2]["role"], "result")
        self.assertEqual(res["beats"][2]["summary"], "Pouring the fresh cup of espresso.")
        self.assertEqual(res["beats"][2]["intended_feeling"], "pride")

        # Anti-goals validation
        self.assertEqual(res["anti_goals"], ["Avoid generic pop music.", "Do not use shaky stock videos."])

    def test_missing_thesis_raises_error(self):
        md_text = """
Mode: rhythmic_mv

# Big Story
- [B1|setup] Introduction of the morning routine.
"""
        with self.assertRaises(ValueError) as ctx:
            compile_blueprint_md(md_text)
        self.assertIn("thesis", str(ctx.exception).lower())

    def test_missing_beats_raises_error(self):
        md_text = """
# Thesis
This is the thesis.

# Anti-goals
- Do not do anything.
"""
        with self.assertRaises(ValueError) as ctx:
            compile_blueprint_md(md_text)
        self.assertIn("beats", str(ctx.exception).lower())


if __name__ == "__main__":
    unittest.main()
