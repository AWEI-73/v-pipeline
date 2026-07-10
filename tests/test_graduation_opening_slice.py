import importlib
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def _slice_module():
    path = ROOT / "video_pipeline_core" / "graduation_opening_slice.py"
    return importlib.import_module("video_pipeline_core.graduation_opening_slice") if path.is_file() else None


class GraduationOpeningSliceTest(unittest.TestCase):
    def test_acceptance_rejects_timing_only_title_qa_without_rendered_frames(self):
        opening_slice = _slice_module()
        self.assertIsNotNone(opening_slice, "graduation opening slice module is required")

        result = opening_slice.validate_opening_slice_acceptance({
            "duration_sec": 44.0,
            "has_video_stream": True,
            "has_audio_stream": True,
            "montage_distinct_asset_count": 15,
            "beat_alignment": {"pass": True, "within_one_frame_ratio": 1.0},
            "rendered_qa": {"pass": True},
            "title_effect_lifecycle_qa": {"pass": True, "effects": [{"start_sec": 0.0, "end_sec": 11.0}]},
            "required_artifacts_present": True,
            "reference_film_used": False,
            "all_sources_accepted": True,
        })

        self.assertFalse(result["pass"])
        self.assertIn("title_effect_evidence_missing", [item["rule"] for item in result["blocking"]])
