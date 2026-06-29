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


if __name__ == "__main__":
    unittest.main()
