import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import video_pipeline as vp
from video_pipeline_core import content_qa


class ContentQATest(unittest.TestCase):
    def test_pipeline_invokes_packaged_content_qa_module(self):
        calls = []

        class Result:
            returncode = 0
            stderr = ""
            stdout = '{"status":"ok","low_segments":[]}\n'

        def fake_run(cmd, capture_output=True, text=True):
            calls.append(cmd)
            return Result()

        with patch.object(vp.subprocess, "run", fake_run):
            summary = vp.run_content_qa("out", "fake-model", 0.3)

        from video_pipeline_core.platform_tools import resolve_python
        self.assertEqual(summary["status"], "ok")
        self.assertEqual(
            calls[0],
            [
                resolve_python(),
                "-m",
                "video_pipeline_core.content_qa",
                "out",
                "--model",
                "fake-model",
                "--weight",
                "0.3",
            ],
        )

    def test_montage_segment_is_scored(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            (outdir / "script.json").write_text(
                json.dumps(
                    [
                        {
                            "segment": 1,
                            "title": "Montage",
                            "layout": "montage",
                            "search_query": "雨夜 街道",
                            "visual_desc": "夜晚下雨的城市街道，路面反光",
                            "text": "雨下得很慢。",
                        }
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            (outdir / "final_frame_1.jpg").write_bytes(b"fake image placeholder")

            def fake_score_segment(model, image_path, verify_desc, zh_title, verbose=False):
                return 88.0, "rainy street montage frame", "primary=yes, related=yes"

            with patch.object(content_qa, "score_segment", fake_score_segment), \
                 patch.object(sys, "argv", ["content_qa.py", str(outdir), "--model", "fake-model"]):
                content_qa.main()

            report = json.loads((outdir / "content_qa.json").read_text(encoding="utf-8"))
            seg = report["segments"][0]
            self.assertEqual(seg["segment"], 1)
            self.assertEqual(seg["score"], 88.0)
            self.assertEqual(seg["image_desc"], "rainy street montage frame")

    def test_title_and_local_segments_remain_exempt(self):
        with tempfile.TemporaryDirectory() as tmp:
            outdir = Path(tmp)
            (outdir / "script.json").write_text(
                json.dumps(
                    [
                        {
                            "segment": 1,
                            "title": "Title",
                            "kind": "title",
                            "duration_sec": 5,
                            "text": "片頭。",
                        },
                        {
                            "segment": 2,
                            "title": "Local",
                            "source": "local",
                            "search_query": "雨後 街道",
                            "visual_desc": "雨後街道",
                            "text": "天亮了。",
                        },
                    ],
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )

            def fail_if_called(*args, **kwargs):
                raise AssertionError("score_segment should not be called")

            with patch.object(content_qa, "score_segment", fail_if_called), \
                 patch.object(sys, "argv", ["content_qa.py", str(outdir)]):
                content_qa.main()

            report = json.loads((outdir / "content_qa.json").read_text(encoding="utf-8"))
            self.assertEqual(report["segments"][0]["reason"], "title_sequence")
            self.assertEqual(report["segments"][1]["reason"], "local_material")



class SubjectDistillRescueTest(unittest.TestCase):
    """D5 two-stage scoring: a director-style multi-clause desc makes the 4b
    literal-minded (city-day seg8/seg11 scored 10 on perfectly matching frames);
    a subject-clause primary match rescues to 60, honest off-topic stays low."""

    def test_distill_subject(self):
        self.assertEqual(content_qa.distill_subject(
            "手沖注水特寫：細水柱螺旋畫圈、咖啡粉膨脹冒泡"), "手沖注水特寫")
        self.assertEqual(content_qa.distill_subject(
            "辦公室裡的工作場景，手在鍵盤上敲打，螢幕亮著"), "辦公室裡的工作場景")
        self.assertEqual(content_qa.distill_subject(""), "")

    def _fake_ollama(self, answers):
        calls = {"n": 0}

        def fake(model, prompt, image_path, num_predict=10):
            i = min(calls["n"], len(answers) - 1)
            calls["n"] += 1
            return answers[i]
        return fake

    def test_full_desc_reject_subject_match_rescues_to_60(self):
        fake = self._fake_ollama(["an office scene", "否", "否", "是"])
        with patch.object(content_qa, "call_ollama_full", fake):
            score, desc, reason = content_qa.score_segment(
                "m", "frame.jpg", "辦公室裡的工作場景，手在鍵盤上敲打，螢幕亮著", "")
        self.assertEqual(score, 60.0)
        self.assertIn("subject_match=yes", reason)

    def test_true_off_topic_stays_low(self):
        fake = self._fake_ollama(["a dancing robot", "否", "否", "否"])
        with patch.object(content_qa, "call_ollama_full", fake):
            score, desc, reason = content_qa.score_segment(
                "m", "frame.jpg", "辦公室裡的工作場景，手在鍵盤上敲打", "")
        self.assertEqual(score, 10.0)

    def test_full_desc_pass_skips_rescue(self):
        fake = self._fake_ollama(["an office scene", "是", "是"])
        with patch.object(content_qa, "call_ollama_full", fake):
            score, _, _ = content_qa.score_segment(
                "m", "frame.jpg", "辦公室裡的工作場景，手在鍵盤上敲打", "")
        self.assertEqual(score, 100.0)

    def test_single_clause_desc_no_rescue_loop(self):
        fake = self._fake_ollama(["x", "否", "否", "是"])
        with patch.object(content_qa, "call_ollama_full", fake):
            score, _, reason = content_qa.score_segment("m", "frame.jpg", "辦公室", "")
        self.assertEqual(score, 10.0)
        self.assertNotIn("subject_match", reason)

if __name__ == "__main__":
    unittest.main()
