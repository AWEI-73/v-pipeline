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


def _multi_role_project_map():
    project = _project_map()
    project["assets"].append({
        "asset_id": "clip-b",
        "asset_type": "video",
        "source": "C:/media/clip-b.mp4",
        "source_hash": "b" * 64,
        "duration_sec": 8,
        "scenes": [{
            "start": 0,
            "end": 8,
            "caption": "class portrait closes the film",
            "visual_family": "group_photo",
            "angle_scale": "wide",
            "satisfies": [{"need_id": "need_final_group", "status": "accepted"}],
        }],
        "speech": [],
    })
    project["assets"][0]["scenes"][0]["satisfies"] = [
        {"need_id": "need_other_segment", "status": "accepted"},
        {"need_id": "need_memory_entry", "status": "accepted"},
    ]
    return project


def _multi_role_contract():
    return {
        "artifact_role": "segment_contract",
        "version": 1,
        "segments": [{
            "segment": "ending",
            "material_fit": {
                "visual_desc": "memory entry final group photo",
                "need_refs": ["need_memory_entry", "need_final_group"],
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

    def test_editorial_segment_id_and_evidence_needs_adapt_to_public_ranker(self):
        contract = {
            "artifact_role": "segment_story_contract",
            "version": 1,
            "segments": [{"segment_id": "seg01"}],
        }
        evidence = {
            "artifact_role": "evidence_need_map",
            "version": 1,
            "needs": [{
                "need_id": "need_teamwork",
                "segment_id": "seg01",
                "required_observation": "trainees pull electrical cable together",
                "factual_claim": "the team pulls the cable",
            }],
        }
        plan = self._plan()
        plan["clips"][0]["segment_id"] = plan["clips"][0].pop("segment")
        report = build_retrieval_ranking_report(
            picture_plan=plan,
            segment_contract=contract,
            evidence_map=evidence,
            project_map=_project_map(),
            project_map_path=self.map_path,
            picture_plan_path=self.picture_path,
            report_path=self.report_path,
            allow_declared_hash_placeholder=True,
        )
        self.assertTrue(report["ok"])
        self.assertTrue(report["editorial_contract_adaptation"]["segment_aliases_applied"])
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

    def _multi_role_plan(self, *, first_need="need_memory_entry", include_need=True,
                         include_clip_id=True):
        clips = [
            {
                "clip_id": "memory" if include_clip_id else None,
                "asset_id": "clip-a",
                "scene_id": "clip-a:0",
                "source_hash": "a" * 64,
                "segment": "ending",
                "start_sec": 0,
                "duration_sec": 4,
                "selection_mode": "ranked_candidate",
            },
            {
                "clip_id": "landing",
                "asset_id": "clip-b",
                "scene_id": "clip-b:0",
                "source_hash": "b" * 64,
                "segment": "ending",
                "need_id": "need_final_group",
                "start_sec": 0,
                "duration_sec": 4,
                "selection_mode": "ranked_candidate",
            },
        ]
        if include_need:
            clips[0]["need_id"] = first_need
        return {
            "artifact_role": "l1_picture_plan",
            "version": 1,
            "retrieval_evidence": {
                "project_material_map_ref": str(self.map_path),
                "project_material_map_sha256": "PLACEHOLDER",
                "ranking_report_ref": str(self.report_path),
            },
            "clips": clips,
        }

    def test_multi_role_segment_validates_each_clip_against_its_need(self):
        report = build_retrieval_ranking_report(
            picture_plan=self._multi_role_plan(),
            segment_contract=_multi_role_contract(),
            project_map=_multi_role_project_map(),
            project_map_path=self.map_path,
            picture_plan_path=self.picture_path,
            report_path=self.report_path,
            allow_declared_hash_placeholder=True,
        )

        self.assertTrue(report["ok"])
        roles = report["segments"][0]["roles"]
        self.assertEqual(
            ["need_memory_entry", "need_final_group"],
            [role["need_id"] for role in roles],
        )
        self.assertEqual(
            ["need_memory_entry", "need_final_group"],
            [selection["need_id"] for selection in report["segments"][0]["selections"]],
        )

    def test_multi_role_segment_rejects_clip_ranked_for_a_different_need(self):
        report = build_retrieval_ranking_report(
            picture_plan=self._multi_role_plan(first_need="need_final_group"),
            segment_contract=_multi_role_contract(),
            project_map=_multi_role_project_map(),
            project_map_path=self.map_path,
            picture_plan_path=self.picture_path,
            report_path=self.report_path,
            allow_declared_hash_placeholder=True,
        )

        self.assertFalse(report["ok"])
        self.assertIn("clip_0_not_in_ranked_candidates:memory", report["errors"])

    def test_multi_role_segment_requires_clip_id_and_need_id(self):
        report = build_retrieval_ranking_report(
            picture_plan=self._multi_role_plan(include_need=False, include_clip_id=False),
            segment_contract=_multi_role_contract(),
            project_map=_multi_role_project_map(),
            project_map_path=self.map_path,
            picture_plan_path=self.picture_path,
            report_path=self.report_path,
            allow_declared_hash_placeholder=True,
        )

        self.assertFalse(report["ok"])
        self.assertIn("clip_0_missing_clip_id_for_multi_role_segment", report["errors"])
        self.assertIn("clip_0_missing_need_id_for_multi_role_segment", report["errors"])

    def test_multi_role_segment_requires_source_hash_and_explicit_selection_mode(self):
        plan = self._multi_role_plan()
        plan["clips"][0].pop("source_hash")
        plan["clips"][0].pop("selection_mode")
        report = build_retrieval_ranking_report(
            picture_plan=plan,
            segment_contract=_multi_role_contract(),
            project_map=_multi_role_project_map(),
            project_map_path=self.map_path,
            picture_plan_path=self.picture_path,
            report_path=self.report_path,
            allow_declared_hash_placeholder=True,
        )

        self.assertFalse(report["ok"])
        self.assertIn("clip_0_missing_source_hash_for_multi_role_segment", report["errors"])
        self.assertIn("clip_0_missing_selection_mode_for_multi_role_segment", report["errors"])


if __name__ == "__main__":
    unittest.main()
