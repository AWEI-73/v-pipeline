import unittest

from video_pipeline_core import material_retrieval


class MaterialRetrievalRepeatCapTest(unittest.TestCase):
    def _map(self, asset_id, source, caption, start=0.0):
        return {
            "asset_id": asset_id,
            "asset_type": "video",
            "source": source,
            "scenes": [{
                "start": start,
                "end": start + 8.0,
                "caption": caption,
                "function": "establish",
                "visual_family": "group",
                "angle_scale": "wide",
                "satisfies": [{"need_id": "need_a", "status": "accepted"}],
            }],
        }

    def test_plan_ranked_windows_respects_cross_segment_source_repeat_cap(self):
        segment = {
            "segment": 2,
            "visual_desc": "training group",
            "material_fit": {"need_refs": ["need_a"]},
        }
        maps = [
            self._map("a", "same.mp4", "training group"),
            self._map("b", "fresh.mp4", "training group"),
        ]
        history = [{"source": "same.mp4"}]

        slots = material_retrieval.plan_ranked_windows(
            segment,
            maps,
            limit=1,
            clip_dur=4.0,
            history=history,
            max_source_repeats=1,
        )

        self.assertEqual(slots[0]["source"], "fresh.mp4")
        self.assertEqual(slots[0]["source_repeat_count"], 0)

    def test_plan_ranked_windows_counts_selected_sources_within_segment(self):
        segment = {
            "segment": 1,
            "visual_desc": "training group",
            "material_fit": {"need_refs": ["need_a"]},
        }
        maps = [
            self._map("a", "same.mp4", "training group", start=0.0),
            self._map("b", "same.mp4", "training group", start=10.0),
            self._map("c", "fresh.mp4", "training group", start=20.0),
        ]

        slots = material_retrieval.plan_ranked_windows(
            segment,
            maps,
            limit=2,
            clip_dur=4.0,
            max_source_repeats=1,
        )

        self.assertEqual([slot["source"] for slot in slots], ["same.mp4", "fresh.mp4"])

    def test_unique_visual_family_policy_prefers_eligible_cutaway_family(self):
        ranked = [
            {"scene_id": "a:0", "source": "a.mp4", "score": 5,
             "visual_family": "group", "angle_scale": "wide", "start": 0, "end": 5},
            {"scene_id": "b:0", "source": "b.mp4", "score": 5,
             "visual_family": "classroom", "angle_scale": "medium", "start": 0, "end": 5},
            {"scene_id": "c:0", "source": "c.mp4", "score": 5,
             "visual_family": "group", "angle_scale": "close", "start": 0, "end": 5},
        ]

        selected = material_retrieval.select_diverse_ranked_scenes(
            ranked, [], limit=2, max_source_repeats=1,
            require_unique_visual_family=True,
        )

        self.assertEqual([item["scene_id"] for item in selected], ["a:0", "b:0"])
        self.assertEqual([item["visual_family"] for item in selected], ["group", "classroom"])
        self.assertNotIn("diversity_fallback_reason", selected[0])
        self.assertNotIn("diversity_fallback_reason", selected[1])

    def test_unique_visual_family_records_supply_exhaustion_fallback(self):
        ranked = [
            {"scene_id": "a:0", "source": "a.mp4", "score": 5,
             "visual_family": "group", "angle_scale": "wide", "start": 0, "end": 5},
            {"scene_id": "b:0", "source": "b.mp4", "score": 4,
             "visual_family": "group", "angle_scale": "medium", "start": 0, "end": 5},
        ]

        selected = material_retrieval.select_diverse_ranked_scenes(
            ranked, [], limit=2, max_source_repeats=1,
            require_unique_visual_family=True,
        )

        self.assertEqual(len(selected), 2)
        self.assertEqual(selected[1]["diversity_fallback_reason"], "eligible_supply_exhausted")

    def test_protected_talking_head_does_not_consume_cutaway_source_ceiling(self):
        ranked = [
            {"scene_id": "speech:0", "source": "same.mp4", "score": 5,
             "visual_family": "talking_head", "protected_speech_anchor": True,
             "start": 0, "end": 5},
            {"scene_id": "cutaway:0", "source": "same.mp4", "score": 4,
             "visual_family": "utility_action", "start": 0, "end": 5},
        ]

        selected = material_retrieval.select_diverse_ranked_scenes(
            ranked, [], limit=2, max_source_repeats=1,
            require_unique_visual_family=True,
        )

        self.assertEqual([item["scene_id"] for item in selected], ["speech:0", "cutaway:0"])
        self.assertEqual(selected[1]["source_repeat_count"], 0)

    def test_rank_scenes_matches_any_accepted_need_on_a_multi_role_scene(self):
        material_map = self._map("memory", "memory.jpg", "birthday memory")
        material_map["scenes"][0]["satisfies"] = [
            {"need_id": "need_other_segment", "status": "accepted"},
            {"need_id": "need_memory_entry", "status": "accepted"},
        ]
        segment = {
            "segment": "ending",
            "material_fit": {
                "visual_desc": "memory entry",
                "need_refs": ["need_memory_entry"],
            },
        }

        ranked = material_retrieval.rank_scenes(segment, [material_map])

        self.assertEqual(1, len(ranked))
        self.assertEqual("need_memory_entry", ranked[0]["need_id"])

    def test_rank_scenes_prefers_accepted_need_evidence_over_candidate_hint(self):
        accepted = self._map("accepted", "accepted.mp4", "same visual evidence")
        candidate = self._map("candidate", "candidate.mp4", "same visual evidence")
        candidate["scenes"][0]["satisfies"][0]["status"] = "candidate"
        segment = {
            "segment": "discipline",
            "material_fit": {
                "visual_desc": "same visual evidence",
                "need_refs": ["need_a"],
            },
        }

        ranked = material_retrieval.rank_scenes(segment, [candidate, accepted])

        self.assertEqual("accepted", ranked[0]["asset_id"])
        self.assertEqual("accepted", ranked[0]["need_status"])
        self.assertEqual("candidate", ranked[1]["need_status"])
        self.assertGreater(
            ranked[0]["score_breakdown"]["need"],
            ranked[1]["score_breakdown"]["need"],
        )


if __name__ == "__main__":
    unittest.main()
