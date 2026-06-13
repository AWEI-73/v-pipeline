"""CLI dispatch tests for the P1 verification tool pack."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import video_tools


def _ffmpeg_available():
    try:
        from video_pipeline_core.platform_tools import resolve_ffmpeg
        resolve_ffmpeg()
        return True
    except Exception:
        return False


def _write(path, payload):
    Path(path).write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class AuditCliTest(unittest.TestCase):
    def test_replay_acceptance_cmd(self):
        with tempfile.TemporaryDirectory() as d:
            timeline = os.path.join(d, "timeline.json")
            gates = os.path.join(d, "gates.json")
            verdicts = os.path.join(d, "verdicts.json")
            adaptation = os.path.join(d, "adaptation.json")
            out = os.path.join(d, "replay.json")
            _write(timeline, {"clips": [{"duration_sec": 2, "source_path": "a.mp4",
                                         "scene_id": "a:0"}]})
            _write(gates, {"spec_review": {"ready_for_build": True}})
            _write(verdicts, [{"decision": "accept", "reviewer": "agent"}])
            _write(adaptation, {"duration": "shortened", "chapters": "reduced"})
            args = SimpleNamespace(timeline=timeline, gates=gates, verdicts=verdicts,
                                   jumpcut_plan=None, new_visual_audit=None,
                                   adaptation=adaptation, out=out)
            video_tools.cmd_replay_acceptance(args)
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "m4_replay_acceptance")

    def test_timeline_audit_cmd(self):
        with tempfile.TemporaryDirectory() as d:
            timeline = os.path.join(d, "timeline_build.json")
            out = os.path.join(d, "timeline_invariants.json")
            _write(timeline, {"clips": [
                {"segment": 1, "source_path": "a.mp4", "start_sec": 0, "end_sec": 3,
                 "duration_sec": 3, "timeline_in_sec": 0, "timeline_out_sec": 3,
                 "trace": {"segment_contract_segment": 1}},
            ]})
            args = SimpleNamespace(timeline=timeline, out=out,
                                   expected_duration=None, must_include=None)
            video_tools.cmd_timeline_audit(args)
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "timeline_invariants")
            self.assertTrue(saved["pass"])

    def test_broll_audit_cmd(self):
        with tempfile.TemporaryDirectory() as d:
            timeline = os.path.join(d, "timeline_build.json")
            out = os.path.join(d, "broll_audit.json")
            _write(timeline, {"clips": [
                {"segment": 1, "source_path": "a.mp4", "duration_sec": 3, "source": "stock"},
                {"segment": 2, "source_path": "a.mp4", "duration_sec": 3, "source": "stock"},
            ]})
            args = SimpleNamespace(timeline=timeline, out=out,
                                   target_ratio=None, max_source_repeats=1)
            video_tools.cmd_broll_audit(args)
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "broll_audit")
            self.assertFalse(saved["pass"])  # repeated source exceeds ceiling 1

    def test_new_visual_information_audit_cmd(self):
        with tempfile.TemporaryDirectory() as d:
            timeline = os.path.join(d, "timeline_build.json")
            out = os.path.join(d, "new_visual_information_audit.json")
            _write(timeline, {"clips": [
                {"scene_id": "a:0", "duration_sec": 2},
                {"scene_id": "a:0", "duration_sec": 5},
            ]})
            args = SimpleNamespace(
                timeline=timeline,
                out=out,
                min_new_visual_ratio=0.6,
                max_repeated_hold_sec=3,
            )
            video_tools.cmd_new_visual_information_audit(args)
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "new_visual_information_audit")
            self.assertFalse(saved["pass"])

    def test_caption_audit_cmd_accepts_list_or_dict(self):
        with tempfile.TemporaryDirectory() as d:
            captions = os.path.join(d, "captions.json")
            out = os.path.join(d, "caption_audit.json")
            _write(captions, [
                {"start_sec": 0, "end_sec": 3, "text": "一", "kind": "subtitle"},
                {"start_sec": 2, "end_sec": 4, "text": "二", "kind": "subtitle"},
            ])
            args = SimpleNamespace(captions=captions, out=out,
                                   max_gap_sec=None, max_cps=None)
            video_tools.cmd_caption_audit(args)
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["artifact_role"], "caption_audit")
            self.assertEqual(saved["metrics"]["overlap_count"], 1)


    def test_caption_audit_cmd_reads_srt(self):
        with tempfile.TemporaryDirectory() as d:
            srt = os.path.join(d, "subtitles.srt")
            out = os.path.join(d, "caption_audit.json")
            Path(srt).write_text(
                "1\n00:00:00,000 --> 00:00:03,000\n句一\n\n"
                "2\n00:00:02,000 --> 00:00:04,000\n句二\n",
                encoding="utf-8")
            args = SimpleNamespace(captions=None, srt=srt, out=out,
                                   max_gap_sec=None, max_cps=None)
            video_tools.cmd_caption_audit(args)
            saved = json.loads(Path(out).read_text(encoding="utf-8"))
            self.assertEqual(saved["metrics"]["overlap_count"], 1)


@unittest.skipUnless(_ffmpeg_available(), "ffmpeg not available")
class AuditCliFfmpegTest(unittest.TestCase):
    def setUp(self):
        from video_pipeline_core.platform_tools import resolve_ffmpeg
        self.ffmpeg = resolve_ffmpeg()
        self.tmp = tempfile.mkdtemp()
        self.video = os.path.join(self.tmp, "clip.mp4")
        subprocess.run(
            [self.ffmpeg, "-y", "-f", "lavfi", "-i", "testsrc=duration=2:size=320x240:rate=10",
             "-pix_fmt", "yuv420p", self.video],
            capture_output=True, check=True,
        )

    def test_keyframe_grid_cmd(self):
        out = os.path.join(self.tmp, "keyframe_grid.jpg")
        args = SimpleNamespace(video=self.video, out=out, samples=4, columns=2)
        video_tools.cmd_keyframe_grid(args)
        self.assertTrue(os.path.exists(out))
        self.assertGreater(os.path.getsize(out), 0)

    def test_keyframe_grid_cmd_fails_on_unreadable_input(self):
        bogus = os.path.join(self.tmp, "not_a_video.mp4")
        Path(bogus).write_text("this is not a video", encoding="utf-8")
        out = os.path.join(self.tmp, "empty_grid.jpg")
        args = SimpleNamespace(video=bogus, out=out, samples=4, columns=2)
        with self.assertRaises(video_tools.ToolError):
            video_tools.cmd_keyframe_grid(args)
        self.assertFalse(os.path.exists(out) and os.path.getsize(out) > 0)

    def test_visual_audit_cmd_mechanical(self):
        out = os.path.join(self.tmp, "visual_audit.json")
        grid = os.path.join(self.tmp, "keyframe_grid.jpg")
        args = SimpleNamespace(video=self.video, out=out, grid=grid, samples=4, columns=2)
        video_tools.cmd_visual_audit(args)
        saved = json.loads(Path(out).read_text(encoding="utf-8"))
        self.assertEqual(saved["artifact_role"], "visual_audit")
        self.assertIsNone(saved["model_review"])  # mechanical-only via CLI
        self.assertTrue(os.path.exists(grid))

    def test_verify_evidence_cmd(self):
        timeline = os.path.join(self.tmp, "timeline.json")
        out_dir = os.path.join(self.tmp, "verify_evidence")
        _write(timeline, {"clips": [
            {"segment": 1, "timeline_in_sec": 0, "timeline_out_sec": 2,
             "duration_sec": 2, "adjustment_reason": "motion_phase"},
        ]})
        args = SimpleNamespace(video=self.video, timeline=timeline, out_dir=out_dir,
                               overview_samples=4, chapter_samples=2,
                               critical_samples=2)
        video_tools.cmd_verify_evidence(args)
        saved = json.loads(
            (Path(out_dir) / "verify_evidence_bundle.json").read_text(encoding="utf-8"))
        self.assertEqual(saved["artifact_role"], "verify_evidence_bundle")
        self.assertTrue((Path(out_dir) / "rhythm_strip.svg").exists())


if __name__ == "__main__":
    unittest.main()
