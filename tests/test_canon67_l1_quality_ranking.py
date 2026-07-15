import unittest

from video_pipeline_core.material_retrieval import rank_scenes


def _segment():
    return {
        "segment": "seg04_cable_teamwork",
        "visual_desc": "students pull electrical cable",
        "material_fit": {"visual_desc": "students pull electrical cable", "need_refs": ["need_a"]},
    }


def _scene(*, confidence, direct, story_function, support_subtype):
    return {
        "start": 0.0,
        "end": 8.0,
        "caption": "students pull electrical cable",
        "satisfies": [{"need_id": "need_a", "status": "accepted"}],
        "direct_story_evidence": direct,
        "assigned_story_function": story_function,
        "support_subtype": support_subtype,
        "review": {
            "state": "observed",
            "confidence": confidence,
            "visual_evidence": ["l0_matrix#cell"],
        },
    }


class Canon67EvidenceQualityRankingTest(unittest.TestCase):
    def test_direct_resolved_high_confidence_beats_unresolved_same_need(self):
        maps = [
            {
                "asset_id": "asset-a-unresolved",
                "asset_type": "video",
                "source": "a.mp4",
                "scenes": [_scene(
                    confidence=0.55,
                    direct=False,
                    story_function=None,
                    support_subtype="unresolved_cutaway",
                )],
            },
            {
                "asset_id": "asset-z-direct",
                "asset_type": "video",
                "source": "z.mp4",
                "scenes": [_scene(
                    confidence=0.95,
                    direct=True,
                    story_function="cable_task_and_teamwork",
                    support_subtype="operational_teamwork",
                )],
            },
        ]

        ranked = rank_scenes(_segment(), maps)

        self.assertEqual(ranked[0]["asset_id"], "asset-z-direct")
        self.assertGreater(
            ranked[0]["score_breakdown"]["evidence_quality"],
            ranked[1]["score_breakdown"]["evidence_quality"],
        )

    def test_filename_prior_still_cannot_admit_scene_without_base_evidence(self):
        maps = [{
            "asset_id": "asset-filename-only",
            "asset_type": "video",
            "source": "students_pull_electrical_cable.mp4",
            "filename_prior": {"text": "students pull electrical cable"},
            "scenes": [{"start": 0.0, "end": 8.0}],
        }]

        self.assertEqual(rank_scenes(_segment(), maps), [])


if __name__ == "__main__":
    unittest.main()
