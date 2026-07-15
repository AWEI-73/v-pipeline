import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.material_pool_store import checkout_pool_map, commit_campaign_map


def _project_map(*, caption=None, state=None):
    scene = {"start": 0.0, "end": 8.0, "kind": "video"}
    if caption:
        scene.update({
            "caption": caption,
            "visual_family": "teamwork",
            "observed_content": "trainees pull cable together",
            "review": {
                "state": state or "confirmed",
                "reviewer": "agent:campaign-a",
                "confidence": 0.9,
                "visual_evidence": ["campaign-a contact sheet cell 02"],
            },
            "satisfies": [{"need_id": "campaign_a_need", "status": "accepted"}],
        })
    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": [{
            "asset_id": "clip-a",
            "asset_type": "video",
            "source": "C:/media/clip-a.mp4",
            "source_hash": "a" * 64,
            "duration_sec": 8.0,
            "scenes": [scene],
            "speech": [],
        }],
        "needs": [],
        "satisfaction_summary": {},
        "metrics": {"asset_count": 1, "scene_count": 1},
    }


class MaterialPoolStoreTest(unittest.TestCase):
    def test_second_campaign_checks_out_first_campaign_reviewed_labels(self):
        root = Path(tempfile.mkdtemp())
        campaign_a = root / "campaign-a-map.json"
        campaign_a.write_text(json.dumps(_project_map(
            caption="trainees pull cable together", state="corrected")), encoding="utf-8")

        first = commit_campaign_map(
            pool_root=root / "pools",
            pool_id="canon67-main",
            campaign_id="campaign-a",
            campaign_map_path=campaign_a,
            expected_base_sha256="EMPTY",
        )
        self.assertEqual(first["version"], 1)

        checked_out = checkout_pool_map(
            pool_root=root / "pools",
            pool_id="canon67-main",
            campaign_id="campaign-b",
            out_path=root / "campaign-b" / "project_material_map.pool-base.json",
        )
        payload = json.loads(Path(checked_out["project_material_map"]).read_text(
            encoding="utf-8"))
        scene = payload["assets"][0]["scenes"][0]
        self.assertEqual(scene["caption"], "trainees pull cable together")
        self.assertEqual(scene["review"]["state"], "corrected")
        self.assertNotIn("satisfies", scene, "campaign need edges must not leak into pool truth")

    def test_commit_rejects_stale_campaign_base(self):
        root = Path(tempfile.mkdtemp())
        campaign = root / "map.json"
        campaign.write_text(json.dumps(_project_map(caption="first")), encoding="utf-8")
        commit_campaign_map(
            pool_root=root / "pools",
            pool_id="canon67-main",
            campaign_id="campaign-a",
            campaign_map_path=campaign,
            expected_base_sha256="EMPTY",
        )

        with self.assertRaisesRegex(ValueError, "stale material-pool base"):
            commit_campaign_map(
                pool_root=root / "pools",
                pool_id="canon67-main",
                campaign_id="campaign-b",
                campaign_map_path=campaign,
                expected_base_sha256="0" * 64,
            )


if __name__ == "__main__":
    unittest.main()
