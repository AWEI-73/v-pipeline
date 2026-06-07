"""caption_audit — Node 11/12 caption gap/overlap/reading-speed audit (P1-A)."""
import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import caption_audit as ca


def _cap(start, end, text, kind="subtitle"):
    return {"start_sec": start, "end_sec": end, "text": text, "kind": kind}


def _checks(result):
    return {f["check"] for f in result["findings"]}


class CaptionAuditTest(unittest.TestCase):
    def test_clean_captions_pass(self):
        captions = [
            _cap(0.0, 2.0, "第一句"),
            _cap(2.5, 4.5, "第二句"),
        ]
        result = ca.audit_captions(captions)
        self.assertEqual(result["artifact_role"], "caption_audit")
        self.assertEqual(result["version"], 1)
        self.assertTrue(result["pass"])
        self.assertEqual(result["metrics"]["overlap_count"], 0)
        self.assertIsNone(result["next_action"])

    def test_overlap_detected_fails(self):
        captions = [
            _cap(0.0, 3.0, "句子一"),
            _cap(2.0, 4.0, "句子二"),  # overlaps previous subtitle
        ]
        result = ca.audit_captions(captions)
        self.assertFalse(result["pass"])
        self.assertEqual(result["metrics"]["overlap_count"], 1)
        self.assertIn("overlap", _checks(result))
        self.assertIsNotNone(result["next_action"])

    def test_labels_and_name_supers_not_treated_as_subtitles(self):
        # A name_super that visually overlaps a subtitle must NOT be flagged as a
        # caption overlap — labels/name supers are not subtitles.
        captions = [
            _cap(0.0, 3.0, "歡迎致詞", kind="subtitle"),
            _cap(0.0, 3.0, "鍾峻松 老師", kind="name_super"),
            _cap(0.5, 2.5, "養成訓練", kind="label"),
        ]
        result = ca.audit_captions(captions)
        self.assertEqual(result["metrics"]["overlap_count"], 0)
        self.assertTrue(result["pass"])

    def test_too_fast_reading_speed_warns(self):
        # 20 chars in 1 second, ceiling 10 cps -> too fast
        captions = [_cap(0.0, 1.0, "一" * 20)]
        result = ca.audit_captions(captions, max_chars_per_sec=10)
        self.assertEqual(result["metrics"]["too_fast_count"], 1)
        self.assertIn("too_fast", _checks(result))
        # reading-speed issue is advisory (warn), does not block by itself
        self.assertTrue(result["pass"])

    def test_gap_over_threshold_warns_but_intended_silence_excluded(self):
        captions = [
            _cap(0.0, 2.0, "開頭"),
            _cap(10.0, 12.0, "結尾"),  # 8s gap
        ]
        result = ca.audit_captions(captions, max_gap_sec=3.0)
        self.assertEqual(result["metrics"]["gap_count"], 1)

        # declaring the silent window as intended removes the finding
        result2 = ca.audit_captions(
            captions, max_gap_sec=3.0,
            intended_silence_intervals=[[2.0, 10.0]],
        )
        self.assertEqual(result2["metrics"]["gap_count"], 0)

    def test_narrative_kind_is_audited(self):
        captions = [
            _cap(0.0, 3.0, "旁白一", kind="narrative"),
            _cap(2.0, 4.0, "旁白二", kind="narrative"),
        ]
        result = ca.audit_captions(captions)
        self.assertEqual(result["metrics"]["overlap_count"], 1)

    def test_parse_srt_basic(self):
        srt = (
            "1\n00:00:00,000 --> 00:00:03,000\n第一句\n\n"
            "2\n00:00:03,500 --> 00:00:05,000\n第二句\n"
        )
        events = ca.parse_srt(srt)
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0]["kind"], "subtitle")
        self.assertAlmostEqual(events[0]["start_sec"], 0.0)
        self.assertAlmostEqual(events[0]["end_sec"], 3.0)
        self.assertEqual(events[0]["text"], "第一句")
        self.assertAlmostEqual(events[1]["start_sec"], 3.5)

    def test_parse_srt_multiline_text_joined(self):
        srt = "1\n00:00:01,000 --> 00:00:02,000\n行一\n行二\n"
        events = ca.parse_srt(srt)
        self.assertEqual(len(events), 1)
        self.assertIn("行一", events[0]["text"])
        self.assertIn("行二", events[0]["text"])

    def test_srt_then_audit_catches_overlap(self):
        srt = (
            "1\n00:00:00,000 --> 00:00:03,000\n句一\n\n"
            "2\n00:00:02,000 --> 00:00:04,000\n句二\n"
        )
        result = ca.audit_captions(ca.parse_srt(srt))
        self.assertEqual(result["metrics"]["overlap_count"], 1)

    def test_writer_outputs_stable_json(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "caption_audit.json"
            result = ca.write_caption_audit([], p)
            saved = json.loads(p.read_text(encoding="utf-8"))
            self.assertEqual(result["caption_audit"], str(p))
            self.assertEqual(saved["artifact_role"], "caption_audit")
            self.assertTrue(saved["pass"])


if __name__ == "__main__":
    unittest.main()
