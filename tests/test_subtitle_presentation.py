import unittest

from video_pipeline_core.subtitle_presentation import (
    build_ass_style,
    polish_caption_text,
    polish_srt_text,
)


class TestSubtitlePresentation(unittest.TestCase):
    def test_polish_caption_replaces_punctuation_and_wraps_at_sixteen_cjk_chars(self):
        text = "這是一段需要清理，並且需要自動換行的中文字幕內容。"

        polished = polish_caption_text(text, max_chars_per_line=16, max_lines=2)

        self.assertNotIn("，", polished)
        self.assertNotIn("。", polished)
        self.assertIn("\u3000", polished)
        self.assertLessEqual(len(polished.splitlines()), 2)
        self.assertTrue(all(len(line) <= 16 for line in polished.splitlines()))

    def test_polish_caption_never_emits_more_than_two_lines(self):
        polished = polish_caption_text("測" * 50, max_chars_per_line=16, max_lines=2)

        self.assertEqual(len(polished.splitlines()), 2)
        self.assertTrue(polished.endswith("…"))

    def test_polish_srt_preserves_timing_and_polishes_only_caption_lines(self):
        source = "1\n00:00:00,000 --> 00:00:03,000\n第一句，第二句。\n"

        polished = polish_srt_text(source)

        self.assertIn("00:00:00,000 --> 00:00:03,000", polished)
        self.assertIn("第一句\u3000第二句", polished)
        self.assertNotIn("第一句，第二句。", polished)

    def test_ass_style_is_bottom_center_and_scales_with_resolution(self):
        hd = build_ass_style(1080)
        sd = build_ass_style(720)

        self.assertIn("Alignment=2", hd)
        self.assertIn("FontSize=38", hd)
        self.assertIn("MarginV=90", hd)
        self.assertIn("FontSize=25", sd)
        self.assertIn("MarginV=60", sd)


if __name__ == "__main__":
    unittest.main()
