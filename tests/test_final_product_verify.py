import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.final_product_verify import build_final_product_verify_bundle


class FinalProductVerifyTests(unittest.TestCase):
    def test_builds_visual_and_audio_verify_bundle_for_final_video(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "final.mp4"
            video.write_bytes(b"placeholder")

            bundle = build_final_product_verify_bundle(
                video,
                out_dir=root,
                keyframe_grid_builder=lambda _video, out: {
                    "grid": Path(out).name,
                    "grid_path": str(out),
                    "sample_count": 2,
                    "samples": [{"timestamp_sec": 1.0}, {"timestamp_sec": 2.0}],
                },
                visual_audit_builder=lambda grid_meta, out: {
                    "artifact_role": "visual_audit",
                    "pass": True,
                    "grid_path": grid_meta["grid_path"],
                    "samples": grid_meta["samples"],
                },
                audio_extractor=lambda _video, out: Path(out).write_bytes(b"wav") or str(out),
                soundtrack_probe_builder=lambda audio: {
                    "artifact_role": "soundtrack_probe_report",
                    "pass": True,
                    "audio_file": str(audio),
                    "features": {"tempo_bpm": 100, "vocal_analysis": {"has_vocals": False}},
                    "sections": [{"start_sec": 0, "end_sec": 3, "role": "full_track"}],
                    "section_fit": [{"video_section": "montage", "fit": "medium"}],
                    "editing_fit": {"montage": "medium"},
                },
            )

            self.assertEqual(bundle["artifact_role"], "final_product_verify_bundle")
            self.assertTrue(bundle["pass"])
            self.assertTrue((root / "keyframe_grid.jpg").is_file())
            self.assertTrue((root / "visual_audit.json").is_file())
            self.assertTrue((root / "final_audio.wav").is_file())
            self.assertTrue((root / "soundtrack_probe_report.json").is_file())
            saved = json.loads((root / "final_product_verify_bundle.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["audio"]["soundtrack_probe_report"], "soundtrack_probe_report.json")

    def test_video_without_audio_stream_still_gets_verify_bundle(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "silent.mp4"
            video.write_bytes(b"placeholder")

            def no_audio_extractor(_video, _out):
                raise RuntimeError("Output file #0 does not contain any stream")

            bundle = build_final_product_verify_bundle(
                video,
                out_dir=root,
                keyframe_grid_builder=lambda _video, out: {
                    "grid": Path(out).name,
                    "grid_path": str(out),
                    "sample_count": 1,
                    "samples": [{"timestamp_sec": 1.0}],
                },
                visual_audit_builder=lambda grid_meta, out: {
                    "artifact_role": "visual_audit",
                    "pass": True,
                    "grid_path": grid_meta["grid_path"],
                    "samples": grid_meta["samples"],
                },
                audio_extractor=no_audio_extractor,
                soundtrack_probe_builder=lambda audio: {
                    "artifact_role": "soundtrack_probe_report",
                    "pass": True,
                    "audio_file": str(audio),
                    "analysis_depth": "no_audio_stream",
                    "features": {"has_audio": False},
                    "limitations": ["Input media has no audio stream."],
                },
            )

            self.assertTrue(bundle["pass"])
            self.assertIsNone(bundle["audio"]["final_audio"])
            self.assertEqual(bundle["audio"]["audio_status"], "no_audio_stream")
            self.assertFalse((root / "final_audio.wav").exists())
            saved_probe = json.loads((root / "soundtrack_probe_report.json").read_text(encoding="utf-8"))
            self.assertFalse(saved_probe["features"]["has_audio"])

    def test_verify_packet_written_on_failure(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            video = root / "fail.mp4"
            video.write_bytes(b"placeholder")

            bundle = build_final_product_verify_bundle(
                video,
                out_dir=root,
                keyframe_grid_builder=lambda _video, out: {
                    "grid_path": str(out),
                    "samples": [],
                },
                visual_audit_builder=lambda grid_meta, out: {
                    "artifact_role": "visual_audit",
                    "pass": False,
                    "error": "Too many blank frames",
                },
                audio_extractor=lambda _video, out: Path(out).write_bytes(b"wav") or str(out),
                soundtrack_probe_builder=lambda audio: {
                    "artifact_role": "soundtrack_probe_report",
                    "pass": False,
                    "error": "Audio clips clipping",
                },
            )

            self.assertFalse(bundle["pass"])
            packet_path = root / "verify_revision_packet.json"
            self.assertTrue(packet_path.is_file())

            packet_data = json.loads(packet_path.read_text(encoding="utf-8"))
            self.assertEqual(packet_data["artifact_role"], "revision_packet")
            self.assertEqual(packet_data["source_review"], "final_product_verify_bundle.json")
            self.assertEqual(packet_data["target_branch"], "verify-delivery")
            self.assertEqual(packet_data["problem_type"], "multi_branch")
            self.assertEqual(packet_data["severity"], "blocking")
            
            targets = packet_data["revision_targets"]
            self.assertEqual(len(targets), 2)
            self.assertEqual(targets[0]["artifact"], "project_material_map.json")
            self.assertEqual(targets[0]["issue"], "Too many blank frames")
            self.assertEqual(targets[0]["target_branch"], "material-map")
            self.assertEqual(targets[1]["artifact"], "soundtrack_plan.json")
            self.assertEqual(targets[1]["issue"], "Audio clips clipping")
            self.assertEqual(targets[1]["target_branch"], "soundtrack-arranger")


if __name__ == "__main__":
    unittest.main()
