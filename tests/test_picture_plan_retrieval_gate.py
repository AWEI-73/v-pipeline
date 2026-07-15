import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.picture_plan_retrieval_gate import build_retrieval_ranking_report


def _project_map():
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [{
            "asset_id": "clip-a",
            "asset_type": "video",
            "source": "C:/media/clip-a.mp4",
            "source_hash": "a" * 64,
            "duration_sec": 8,
            "scenes": [{
                "start": 0,
                "end": 8,
                "caption": "trainees pull electrical cable together",
                "visual_family": "teamwork",
                "angle_scale": "wide",
                "satisfies": [{"need_id": "need_teamwork", "status": "accepted"}],
            }],
            "speech": [],
        }],
        "needs": [],
        "satisfaction_summary": {},
        "metrics": {"asset_count": 1, "scene_count": 1},
    }


def _contract():
    return {
        "artifact_role": "segment_contract",
        "version": 1,
        "segments": [{
            "segment": "seg01",
            "material_fit": {
                "visual_desc": "trainees pull electrical cable together",
                "need_refs": ["need_teamwork"],
            },
        }],
    }


class PicturePlanRetrievalGateTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.map_path = self.root / "project_material_map.json"
        self.picture_path = self.root / "l1_picture_plan.json"
        self.report_path = self.root / "retrieval_ranking_report.json"

    def _plan(self, **clip_updates):
        clip = {
            "clip_id": "c01",
            "asset_id": "clip-a",
            "scene_id": "clip-a:0",
            "segment": "seg01",
            "source_path": "C:/media/clip-a.mp4",
            "start_sec": 0,
            "duration_sec": 4,
            "selection_mode": "ranked_candidate",
        }
        clip.update(clip_updates)
        return {
            "artifact_role": "l1_picture_plan",
            "version": 1,
            "retrieval_evidence": {
                "project_material_map_ref": str(self.map_path),
                "project_material_map_sha256": "PLACEHOLDER",
                "ranking_report_ref": str(self.report_path),
            },
            "clips": [clip],
        }

    def test_ranked_picture_plan_emits_candidates_and_selected_rank(self):
        report = build_retrieval_ranking_report(
            picture_plan=self._plan(),
            segment_contract=_contract(),
            project_map=_project_map(),
            project_map_path=self.map_path,
            picture_plan_path=self.picture_path,
            report_path=self.report_path,
            allow_declared_hash_placeholder=True,
        )

        self.assertTrue(report["ok"])
        self.assertEqual(report["segments"][0]["candidates"][0]["scene_id"], "clip-a:0")
        self.assertEqual(report["segments"][0]["selections"][0]["rank_position"], 1)

    def test_hand_arranged_plan_without_retrieval_evidence_fails_closed(self):
        plan = self._plan()
        plan.pop("retrieval_evidence")
        report = build_retrieval_ranking_report(
            picture_plan=plan,
            segment_contract=_contract(),
            project_map=_project_map(),
            project_map_path=self.map_path,
            picture_plan_path=self.picture_path,
            report_path=self.report_path,
        )

        self.assertFalse(report["ok"])
        self.assertIn("missing_retrieval_evidence", report["errors"])

    def test_override_requires_reason_and_evidence(self):
        report = build_retrieval_ranking_report(
            picture_plan=self._plan(selection_mode="agent_override"),
            segment_contract=_contract(),
            project_map=_project_map(),
            project_map_path=self.map_path,
            picture_plan_path=self.picture_path,
            report_path=self.report_path,
            allow_declared_hash_placeholder=True,
        )

        self.assertFalse(report["ok"])
        self.assertTrue(any("agent_override_requires_reason_and_evidence" in item
                            for item in report["errors"]))


if __name__ == "__main__":
    unittest.main()
