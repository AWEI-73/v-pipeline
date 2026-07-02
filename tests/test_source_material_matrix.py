import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.source_material_matrix import build_source_material_matrix


class SourceMaterialMatrixTests(unittest.TestCase):
    def test_builds_window_matrix_with_visual_and_audio_slots(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            source.write_bytes(b"placeholder")

            matrix = build_source_material_matrix(
                source,
                out_dir=root,
                window_sec=10,
                duration_probe=lambda _source: 35,
                frame_extractor=lambda _source, _ts, out: Path(out).write_bytes(b"jpg") or str(out),
                audio_extractor=lambda _source, out: Path(out).write_bytes(b"wav") or str(out),
                soundtrack_probe_builder=lambda _audio: {
                    "artifact_role": "soundtrack_probe_report",
                    "features": {
                        "energy_curve": [
                            {"start_sec": 0, "end_sec": 10, "relative_energy": 0.2},
                            {"start_sec": 10, "end_sec": 20, "relative_energy": 0.8},
                        ],
                        "vocal_analysis": {
                            "has_vocals": True,
                            "segments": [{"start_sec": 12, "end_sec": 18, "text": "speech"}],
                        },
                    },
                },
            )

            self.assertEqual(matrix["artifact_role"], "source_material_matrix")
            self.assertTrue((root / "source_audio.wav").is_file())
            self.assertTrue((root / "source_soundtrack_probe_report.json").is_file())
            self.assertTrue((root / "source_material_matrix_contact_sheet.jpg").is_file())
            self.assertEqual(matrix["visual"]["contact_sheet"], "source_material_matrix_contact_sheet.jpg")
            self.assertEqual(len(matrix["windows"]), 4)
            self.assertEqual(matrix["windows"][1]["audio"]["relative_energy"], 0.8)
            self.assertTrue(matrix["windows"][1]["audio"]["has_speech"])
            self.assertEqual(matrix["windows"][0]["visual"]["review_status"], "unreviewed")
            self.assertTrue(Path(matrix["windows"][0]["visual"]["keyframe"]).is_file())

    def test_applies_visual_review_labels_without_guessing(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            source.write_bytes(b"placeholder")
            review = {
                "artifact_role": "source_material_matrix_review",
                "decisions": [
                    {
                        "window_id": "win_000",
                        "content_type": "training_practice",
                        "usable_for": ["practice_highlight"],
                        "decision": "keep",
                        "note": "hands-on training",
                    },
                    {
                        "window_id": "win_002",
                        "content_type": "teacher_speech",
                        "usable_for": [],
                        "decision": "reject",
                        "note": "not requested for this highlight",
                    },
                ],
            }

            matrix = build_source_material_matrix(
                source,
                out_dir=root,
                window_sec=10,
                duration_probe=lambda _source: 30,
                frame_extractor=lambda _source, _ts, out: Path(out).write_bytes(b"jpg") or str(out),
                audio_extractor=lambda _source, out: Path(out).write_bytes(b"wav") or str(out),
                soundtrack_probe_builder=lambda _audio: {"features": {"energy_curve": []}},
                visual_review=review,
            )

            self.assertEqual(matrix["windows"][0]["visual"]["content_type"], "training_practice")
            self.assertEqual(matrix["windows"][0]["selection"]["decision"], "keep")
            self.assertEqual(matrix["windows"][2]["visual"]["content_type"], "teacher_speech")
            self.assertEqual(matrix["windows"][2]["selection"]["decision"], "reject")
            saved = json.loads((root / "source_material_matrix.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["windows"][0]["visual"]["content_type"], "training_practice")

    def test_reuses_precomputed_soundtrack_probe_for_speech_windows(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            source.write_bytes(b"placeholder")
            precomputed = root / "probe.json"
            precomputed.write_text(json.dumps({
                "artifact_role": "soundtrack_probe_report",
                "features": {
                    "energy_curve": [
                        {"start_sec": 0, "end_sec": 10, "relative_energy": 0.4},
                    ],
                    "vocal_analysis": {
                        "segments": [
                            {"start_sec": 2, "end_sec": 5, "text": "important answer"},
                        ],
                    },
                },
            }), encoding="utf-8")

            matrix = build_source_material_matrix(
                source,
                out_dir=root,
                window_sec=10,
                duration_probe=lambda _source: 10,
                frame_extractor=lambda _source, _ts, out: Path(out).write_bytes(b"jpg") or str(out),
                audio_extractor=lambda _source, out: Path(out).write_bytes(b"wav") or str(out),
                soundtrack_probe_path=precomputed,
            )

            self.assertTrue(matrix["windows"][0]["audio"]["has_speech"])
            self.assertEqual(
                matrix["windows"][0]["audio"]["speech_segments"][0]["text"],
                "important answer",
            )
            saved_probe = json.loads((root / "source_soundtrack_probe_report.json").read_text(encoding="utf-8"))
            self.assertEqual(
                saved_probe["features"]["vocal_analysis"]["segments"][0]["text"],
                "important answer",
            )

    def test_source_without_audio_still_builds_visual_matrix(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            source.write_bytes(b"placeholder")

            def no_audio_extractor(_source, _out):
                raise RuntimeError("Output file #0 does not contain any stream")

            matrix = build_source_material_matrix(
                source,
                out_dir=root,
                window_sec=10,
                duration_probe=lambda _source: 21,
                frame_extractor=lambda _source, _ts, out: Path(out).write_bytes(b"jpg") or str(out),
                audio_extractor=no_audio_extractor,
            )

            self.assertEqual(len(matrix["windows"]), 3)
            self.assertIsNone(matrix["audio"]["source_audio"])
            self.assertEqual(matrix["audio"]["audio_status"], "no_audio_stream")
            self.assertFalse((root / "source_audio.wav").exists())
            self.assertTrue((root / "source_soundtrack_probe_report.json").is_file())
            self.assertIsNone(matrix["windows"][0]["audio"]["relative_energy"])
            self.assertFalse(matrix["windows"][0]["audio"]["has_speech"])
            saved_probe = json.loads((root / "source_soundtrack_probe_report.json").read_text(encoding="utf-8"))
            self.assertFalse(saved_probe["features"]["has_audio"])

    def test_precomputed_no_audio_probe_does_not_claim_source_audio_file(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            source = root / "source.mp4"
            source.write_bytes(b"placeholder")
            precomputed = root / "probe.json"
            precomputed.write_text(json.dumps({
                "artifact_role": "soundtrack_probe_report",
                "analysis_depth": "no_audio_stream",
                "features": {"has_audio": False, "energy_curve": []},
            }), encoding="utf-8")

            matrix = build_source_material_matrix(
                source,
                out_dir=root,
                window_sec=10,
                duration_probe=lambda _source: 10,
                frame_extractor=lambda _source, _ts, out: Path(out).write_bytes(b"jpg") or str(out),
                soundtrack_probe_path=precomputed,
            )

            self.assertIsNone(matrix["audio"]["source_audio"])
            self.assertEqual(matrix["audio"]["audio_status"], "no_audio_stream")


if __name__ == "__main__":
    unittest.main()
