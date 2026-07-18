import json
import subprocess
import tempfile
import unittest
from pathlib import Path

from PIL import Image


class TimelineReviewPacketTest(unittest.TestCase):
    def _fake_renderer(self, _video, walls_dir, *, expected_page_count, **_kwargs):
        paths = []
        for page in range(1, expected_page_count + 1):
            path = Path(walls_dir) / f"wall_30s_{page:02d}.jpg"
            Image.new("RGB", (320, 180), "#123456").save(path)
            paths.append(path)
        return paths

    def test_builds_uniform_wall_index_and_binds_audio_subtitle_context(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            probe = root / "soundtrack_probe_report.json"
            probe.write_text(json.dumps({
                "artifact_role": "soundtrack_probe_report",
                "pass": True,
                "duration_sec": 61.0,
                "analysis_depth": "basic_ffmpeg",
                "features": {
                    "has_audio": True,
                    "mean_dbfs": -25.0,
                    "peak_dbfs": -4.0,
                    "tempo_bpm": 96.0,
                    "beat_times": [0.5, 1.0],
                    "energy_curve": [{"start_sec": 0.0, "end_sec": 10.0, "relative_energy": 0.2}],
                    "vocal_analysis": {"has_vocals": True, "segments": [{"start_sec": 10.0, "end_sec": 15.0}]},
                },
                "sections": [{"start_sec": 0.0, "end_sec": 30.0, "role": "opening"}],
                "sampling_anchors": {"beat_times": [0.5], "speech_starts": [10.0]},
            }), encoding="utf-8")
            srt = root / "subtitles.srt"
            srt.write_text(
                "1\n00:00:10,000 --> 00:00:12,000\nFirst line\n\n"
                "2\n00:00:30,000 --> 00:00:33,500\nSecond line\n",
                encoding="utf-8",
            )

            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
                duration_sec=61.0,
                wall_renderer=self._fake_renderer,
                soundtrack_probe_path=probe,
                srt_path=srt,
                text_authority="owner_approved",
            )

            self.assertEqual(packet["artifact_role"], "timeline_review_packet")
            self.assertEqual(packet["status"], "ready_for_agent_review")
            self.assertEqual(packet["review_subject"]["type"], "current_candidate")
            self.assertEqual(packet["reviewer_contract"]["authority"], "candidate_findings_only")
            self.assertEqual(packet["uniform_timeline_wall"]["sample_count"], 122)
            self.assertEqual(packet["uniform_timeline_wall"]["page_count"], 3)
            index = json.loads((root / "review" / "wall_index.json").read_text(encoding="utf-8"))
            self.assertEqual([wall["sample_count"] for wall in index["walls"]], [60, 60, 2])
            self.assertEqual(index["walls"][-1]["last_sample_sec"], 60.5)
            self.assertEqual(packet["review_tracks"]["audio"]["status"], "bound")
            self.assertEqual(packet["review_tracks"]["audio"]["beat_count"], 2)
            self.assertEqual(packet["review_tracks"]["audio"]["duration_binding"]["status"], "match")
            self.assertEqual(packet["review_tracks"]["subtitles"]["cue_count"], 2)
            self.assertEqual(packet["review_tracks"]["subtitles"]["text_authority"], "owner_approved")
            self.assertEqual(packet["review_tracks"]["subtitles"]["cues"][1]["text"], "Second line")
            self.assertEqual(
                packet["reviewer_contract"]["visible_evidence_precedence"][0],
                "rendered_pixels_over_declared_metadata_for_visible_content",
            )
            questions = "\n".join(packet["reviewer_contract"]["questions"])
            self.assertIn("adjacent shots", questions)
            self.assertIn("rendered pixels contradict", questions)
            findings_template = json.loads(
                (root / "review" / "timeline_reviewer_findings.template.json").read_text(encoding="utf-8")
            )
            self.assertEqual(findings_template["packet_sha256"], packet["packet_sha256"])
            self.assertEqual(findings_template["status"], "PENDING_AGENT_REVIEW")
            self.assertEqual(findings_template["review_subject"]["type"], "current_candidate")
            self.assertEqual(findings_template["effect_observations"], [])
            self.assertNotIn("effect_requests", findings_template)

    def test_optional_tracks_remain_explicitly_unbound(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "silent.mp4"
            video.write_bytes(b"candidate")
            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
            )
            self.assertEqual(packet["review_tracks"]["audio"]["status"], "not_supplied")
            self.assertEqual(packet["review_tracks"]["subtitles"]["status"], "not_supplied")
            self.assertTrue(packet["uniform_timeline_wall"]["coverage_pass"])

    def test_rejects_wrong_audio_artifact_and_existing_wall_outputs(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            bad_probe = root / "bad.json"
            bad_probe.write_text(json.dumps({"artifact_role": "not_a_probe"}), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "soundtrack_probe_contract_mismatch"):
                build_timeline_review_packet(
                    video,
                    root / "review_bad",
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                    soundtrack_probe_path=bad_probe,
                )
            self.assertFalse((root / "review_bad").exists())

            wrong_duration_probe = root / "wrong_duration.json"
            wrong_duration_probe.write_text(json.dumps({
                "artifact_role": "soundtrack_probe_report",
                "duration_sec": 18.0,
                "features": {},
            }), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "soundtrack_probe_duration_mismatch"):
                build_timeline_review_packet(
                    video,
                    root / "review_wrong_duration",
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                    soundtrack_probe_path=wrong_duration_probe,
                )
            self.assertFalse((root / "review_wrong_duration").exists())

            occupied = root / "occupied"
            (occupied / "walls").mkdir(parents=True)
            (occupied / "walls" / "wall_30s_01.jpg").write_bytes(b"old")
            with self.assertRaisesRegex(FileExistsError, "timeline_review_output_exists"):
                build_timeline_review_packet(
                    video,
                    occupied,
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                )

    def test_reference_film_is_non_blocking_and_effects_remain_observations(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "reference.mp4"
            video.write_bytes(b"reference")
            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="reference_film",
                duration_sec=4.0,
                wall_renderer=self._fake_renderer,
            )
            self.assertEqual(packet["review_subject"]["type"], "reference_film")
            self.assertEqual(packet["review_subject"]["decision_effect"], "non_blocking_reference")
            self.assertEqual(packet["reviewer_contract"]["authority"], "reference_observations_only")
            self.assertFalse(packet["reviewer_contract"]["effect_boundary"]["effect_factory_handoff_allowed"])
            self.assertIn(
                "evidence_refs",
                packet["reviewer_contract"]["effect_boundary"]["observation_schema"],
            )
            findings = json.loads(
                (root / "review" / "timeline_reviewer_findings.template.json").read_text(encoding="utf-8")
            )
            self.assertEqual(findings["finding_effect"], "reference_observation")
            self.assertEqual(findings["effect_observations"], [])
            self.assertNotIn("effect_requests", findings)

    def test_srt_requires_explicit_text_authority(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            srt = root / "subtitles.srt"
            srt.write_text("1\n00:00:00,000 --> 00:00:01,000\nDraft\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "timeline_review_text_authority_required"):
                build_timeline_review_packet(
                    video,
                    root / "missing_authority",
                    review_subject_type="current_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                    srt_path=srt,
                )
            self.assertFalse((root / "missing_authority").exists())
            with self.assertRaisesRegex(ValueError, "timeline_review_text_authority_without_srt"):
                build_timeline_review_packet(
                    video,
                    root / "authority_without_srt",
                    review_subject_type="current_candidate",
                    text_authority="asr_draft",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                )
            self.assertFalse((root / "authority_without_srt").exists())

    def test_rejects_unknown_review_subject_type(self):
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "candidate.mp4"
            video.write_bytes(b"candidate")
            with self.assertRaisesRegex(ValueError, "timeline_review_subject_type_invalid"):
                build_timeline_review_packet(
                    video,
                    root / "review",
                    review_subject_type="delivery_candidate",
                    duration_sec=4.0,
                    wall_renderer=self._fake_renderer,
                )

    def test_real_renderer_writes_one_uniform_wall_for_short_video(self):
        try:
            from video_pipeline_core.platform_tools import resolve_ffmpeg
            ffmpeg = resolve_ffmpeg()
        except Exception:
            self.skipTest("ffmpeg not available")
        from video_pipeline_core.timeline_review_packet import build_timeline_review_packet

        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "fixture.mp4"
            subprocess.run(
                [
                    ffmpeg, "-y", "-f", "lavfi", "-i",
                    "testsrc=duration=4:size=320x180:rate=12",
                    "-pix_fmt", "yuv420p", str(video),
                ],
                capture_output=True,
                check=True,
            )
            packet = build_timeline_review_packet(
                video,
                root / "review",
                review_subject_type="current_candidate",
            )
            self.assertEqual(packet["uniform_timeline_wall"]["sample_count"], 8)
            self.assertEqual(packet["uniform_timeline_wall"]["page_count"], 1)
            wall = root / "review" / "walls" / "wall_30s_01.jpg"
            self.assertTrue(wall.is_file())
            self.assertGreater(wall.stat().st_size, 0)


if __name__ == "__main__":
    unittest.main()
