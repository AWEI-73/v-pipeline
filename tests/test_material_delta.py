"""M6b — Material delta (coverage-based, increment 1) tests.

Outcomes covered/thin/missing/excess are computed deterministically from the
validated M6a lineage join. A broken reference chain must FAIL, never be misread
as `missing`. The only tier-1 build-blocker is a must_have need with no usable
material and no permitted fallback.
"""
import unittest

from video_pipeline_core import material_delta as md
from video_pipeline_core.material_needs import (
    apply_satisfaction_verdict, migrate_material_needs,
)


def _needs(*specs):
    """specs: (purpose, count, must_have, fallback_options)."""
    needs = []
    for purpose, count, must_have, fallback in specs:
        need = {"category": "動作鏡頭", "type": "video", "purpose": purpose,
                "count": count, "fallback_tier": 1, "must_have": must_have}
        if fallback:
            need["fallback_options"] = fallback
        needs.append(need)
    return migrate_material_needs({"project": "demo", "needs": needs})


def _first_id(needs):
    return needs["needs"][0]["need_id"]


def _map_with_satisfies(need_id, *statuses):
    """A material map with one scene per status pointing at need_id."""
    scenes = [{"start": i, "end": i + 1, "caption": "c"} for i in range(len(statuses))]
    material_map = {"asset_id": "clip-a", "source": "a.mp4", "scenes": scenes}
    apply_satisfaction_verdict(
        material_map,
        {"reviewer": "agent", "scenes": [
            {"scene_index": i, "satisfies": [{"need_id": need_id, "status": st}]}
            for i, st in enumerate(statuses)]},
        valid_need_ids={need_id})
    return [material_map]


class OutcomeThresholdTest(unittest.TestCase):
    def _run(self, needs, maps):
        result = md.compute_material_delta(needs, maps)
        self.assertTrue(result["ok"], result["errors"])
        return result["deltas"][0], result

    def test_covered_when_accepted_meets_count(self):
        needs = _needs(("cable pull", 2, True, None))
        delta, _ = self._run(needs, _map_with_satisfies(_first_id(needs), "accepted", "accepted"))
        self.assertEqual(delta["outcome"], "covered")
        self.assertIsNone(delta["tier"])
        self.assertFalse(delta["blocks_ready_for_build"])

    def test_thin_when_accepted_short_of_count(self):
        needs = _needs(("cable pull", 3, True, None))
        delta, _ = self._run(needs, _map_with_satisfies(_first_id(needs), "accepted", "candidate"))
        self.assertEqual(delta["outcome"], "thin")
        self.assertEqual(delta["tier"], 2)
        self.assertFalse(delta["blocks_ready_for_build"])
        self.assertEqual(delta["evidence"]["accepted"], 1)
        self.assertEqual(delta["evidence"]["candidate"], 1)

    def test_thin_when_only_candidates_present(self):
        needs = _needs(("cable pull", 1, False, None))
        delta, _ = self._run(needs, _map_with_satisfies(_first_id(needs), "candidate"))
        self.assertEqual(delta["outcome"], "thin")   # candidate-only is thin, not missing

    def test_excess_when_accepted_exceeds_count(self):
        needs = _needs(("cable pull", 1, True, None))
        delta, _ = self._run(needs, _map_with_satisfies(_first_id(needs), "accepted", "accepted"))
        self.assertEqual(delta["outcome"], "excess")
        self.assertEqual(delta["route"], "shorten_or_merge")

    def test_rejected_only_is_missing(self):
        needs = _needs(("cable pull", 1, False, None))
        delta, _ = self._run(needs, _map_with_satisfies(_first_id(needs), "rejected"))
        self.assertEqual(delta["outcome"], "missing")


class Tier1BlockTest(unittest.TestCase):
    def test_must_have_no_fallback_missing_is_tier1_and_blocks(self):
        needs = _needs(("hero shot", 1, True, None))
        result = md.compute_material_delta(needs, [])   # zero material
        self.assertTrue(result["ok"])
        delta = result["deltas"][0]
        self.assertEqual(delta["outcome"], "missing")
        self.assertEqual(delta["tier"], 1)
        self.assertTrue(delta["blocks_ready_for_build"])
        self.assertTrue(result["blocks_ready_for_build"])
        self.assertFalse(result["ready_for_build"])

    def test_must_have_with_legal_fallback_missing_does_not_block(self):
        needs = _needs(("hero shot", 1, True, ["stock bridge", "reshoot"]))
        result = md.compute_material_delta(needs, [])
        delta = result["deltas"][0]
        self.assertEqual(delta["outcome"], "missing")
        self.assertEqual(delta["tier"], 2)              # permitted fallback -> not tier1
        self.assertFalse(delta["blocks_ready_for_build"])
        self.assertTrue(result["ready_for_build"])

    def test_optional_missing_does_not_block(self):
        needs = _needs(("nice b-roll", 1, False, None))
        result = md.compute_material_delta(needs, [])
        self.assertEqual(result["deltas"][0]["tier"], 2)
        self.assertTrue(result["ready_for_build"])

    def test_minimal_disproof_one_must_have_zero_material_blocks_build(self):
        # the contracted minimal counter-example
        needs = _needs(("the one mandatory shot", 1, True, None))
        result = md.compute_material_delta(needs, None)   # no maps at all
        self.assertEqual(result["summary"]["missing"], 1)
        self.assertTrue(result["blocks_ready_for_build"])
        self.assertFalse(result["ready_for_build"])


class BrokenChainFailsNotMissingTest(unittest.TestCase):
    def test_dangling_satisfies_edge_fails_not_missing(self):
        needs = _needs(("cable pull", 1, True, None))
        # hand-authored map whose satisfies edge points at an unknown need_id:
        # this is a BROKEN JOIN, not absent material -> must fail, never "missing".
        maps = [{"asset_id": "a", "source": "a.mp4", "scenes": [
            {"start": 0, "end": 2, "satisfies": [{"need_id": "nd_phantom", "status": "accepted"}]}]}]
        result = md.compute_material_delta(needs, maps)
        self.assertFalse(result["ok"])
        self.assertTrue(result["errors"])
        self.assertEqual(result["deltas"], [])
        self.assertFalse(result["ready_for_build"])
        # the real need is NOT reported as missing — there are no deltas at all
        self.assertEqual(result["summary"]["missing"], 0)

    def test_malformed_satisfies_status_fails_without_crash(self):
        needs = _needs(("cable pull", 1, True, None))
        maps = [{"asset_id": "a", "source": "a.mp4", "scenes": [
            {"start": 0, "end": 2,
             "satisfies": [{"need_id": _first_id(needs), "status": "maybe"}]}]}]
        result = md.compute_material_delta(needs, maps)
        self.assertFalse(result["ok"])
        self.assertEqual(result["deltas"], [])

    def test_invalid_needs_fail_not_missing(self):
        # un-migrated need has no need_id -> validation fails -> overall fail
        result = md.compute_material_delta(
            {"project": "x", "needs": [{"category": "c", "type": "video", "purpose": "p"}]}, [])
        self.assertFalse(result["ok"])
        self.assertEqual(result["deltas"], [])


def _map(source, *scene_specs):
    """scene_specs: (start, end, need_id, status). Hand-authored so we can craft
    unrenderable / duplicate evidence the verdict API would not normally write."""
    scenes = []
    for start, end, need_id, status in scene_specs:
        scenes.append({"start": start, "end": end,
                       "satisfies": [{"need_id": need_id, "status": status}]})
    return [{"asset_id": "clip-a", "source": source, "scenes": scenes}]


class RenderableEvidenceTest(unittest.TestCase):
    def test_zero_length_accepted_scene_does_not_satisfy_must_have(self):
        needs = _needs(("hero", 1, True, None))
        nid = _first_id(needs)
        maps = _map("a.mp4", (2.0, 2.0, nid, "accepted"))   # zero-length window
        result = md.compute_material_delta(needs, maps)
        self.assertTrue(result["ok"])
        delta = result["deltas"][0]
        self.assertEqual(delta["outcome"], "missing")       # not covered
        self.assertEqual(delta["tier"], 1)
        self.assertTrue(delta["blocks_ready_for_build"])
        self.assertFalse(result["ready_for_build"])
        self.assertEqual(delta["evidence"]["accepted"], 0)
        self.assertEqual(delta["evidence"]["dropped_evidence"][0]["reason"],
                         "non_positive_length")

    def test_zero_length_photo_scene_counts_as_renderable_still_evidence(self):
        needs = _needs(("group portrait", 1, True, None))
        nid = _first_id(needs)
        maps = [{
            "asset_id": "photo-a",
            "asset_type": "photo",
            "source": "a.jpg",
            "scenes": [{
                "start": 0.0,
                "end": 0.0,
                "kind": "still",
                "satisfies": [{"need_id": nid, "status": "accepted"}],
            }],
        }]

        result = md.compute_material_delta(needs, maps)

        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["deltas"][0]["outcome"], "covered")
        self.assertEqual(result["deltas"][0]["evidence"]["accepted"], 1)
        self.assertEqual(result["deltas"][0]["evidence"]["dropped_evidence"], [])

    def test_accepted_scene_missing_source_does_not_pass(self):
        needs = _needs(("hero", 1, True, None))
        nid = _first_id(needs)
        maps = _map("", (0.0, 3.0, nid, "accepted"))        # no source
        result = md.compute_material_delta(needs, maps)
        delta = result["deltas"][0]
        self.assertEqual(delta["outcome"], "missing")
        self.assertTrue(delta["blocks_ready_for_build"])
        self.assertEqual(delta["evidence"]["dropped_evidence"][0]["reason"],
                         "missing_source")

    def test_invalid_bounds_accepted_scene_dropped(self):
        needs = _needs(("hero", 1, True, ["reshoot"]))      # has fallback -> tier2
        nid = _first_id(needs)
        maps = _map("a.mp4", ("soon", 3.0, nid, "accepted"))
        result = md.compute_material_delta(needs, maps)
        delta = result["deltas"][0]
        self.assertEqual(delta["outcome"], "missing")
        self.assertEqual(delta["evidence"]["accepted"], 0)

    def test_duplicate_accepted_scene_counted_once(self):
        needs = _needs(("hero", 1, True, None))
        nid = _first_id(needs)
        # one scene carrying the SAME accepted edge twice
        maps = [{"asset_id": "clip-a", "source": "a.mp4", "scenes": [
            {"start": 0, "end": 3, "satisfies": [
                {"need_id": nid, "status": "accepted"},
                {"need_id": nid, "status": "accepted"}]}]}]
        result = md.compute_material_delta(needs, maps)
        delta = result["deltas"][0]
        self.assertEqual(delta["evidence"]["accepted"], 1)   # not 2
        self.assertEqual(delta["outcome"], "covered")        # not excess

    def test_duplicate_generated_content_hash_does_not_satisfy_multi_panel_need(self):
        needs = _needs(("storybook beat", 2, True, ["generated_image"]))
        nid = _first_id(needs)
        maps = [
            {"asset_id": "gen-a", "source": "a.png", "source_type": "generated",
             "content_hash": "same-image", "scenes": [
                 {"start": 0, "end": 4, "source_type": "generated",
                  "satisfies": [{"need_id": nid, "status": "accepted"}]}]},
            {"asset_id": "gen-b", "source": "b.png", "source_type": "generated",
             "content_hash": "same-image", "scenes": [
                 {"start": 0, "end": 4, "source_type": "generated",
                  "satisfies": [{"need_id": nid, "status": "accepted"}]}]},
        ]

        result = md.compute_material_delta(needs, maps)

        self.assertTrue(result["ok"], result["errors"])
        delta = result["deltas"][0]
        self.assertEqual(delta["outcome"], "thin")
        self.assertEqual(delta["evidence"]["accepted"], 1)
        self.assertEqual(delta["evidence"]["dropped_evidence"][0]["reason"],
                         "duplicate_generated_asset")


class FallbackValidationTest(unittest.TestCase):
    def test_empty_string_fallback_fails_and_keeps_block(self):
        for bad in ([""], ["   "], ["ok", ""]):
            needs = _needs(("hero", 1, True, bad))
            result = md.compute_material_delta(needs, [])
            self.assertFalse(result["ok"], bad)              # validation failure
            self.assertEqual(result["deltas"], [])
            self.assertFalse(result["ready_for_build"])      # block not relieved


class AssetIdentityTest(unittest.TestCase):
    def _scene_map(self, asset_id, source, need_id):
        return {"asset_id": asset_id, "source": source, "scenes": [
            {"start": 0, "end": 3, "satisfies": [{"need_id": need_id, "status": "accepted"}]}]}

    def test_duplicate_asset_id_fails_in_both_orders(self):
        needs = _needs(("hero", 1, True, None))
        nid = _first_id(needs)
        m1 = self._scene_map("dup", "a.mp4", nid)
        m2 = self._scene_map("dup", "b.mp4", nid)
        for maps in ([m1, m2], [m2, m1]):     # order must not change the verdict
            result = md.compute_material_delta(needs, maps)
            self.assertFalse(result["ok"], maps)
            self.assertEqual(result["deltas"], [])
            self.assertFalse(result["ready_for_build"])
            self.assertEqual(result["summary"]["covered"], 0)
            self.assertEqual(result["summary"]["missing"], 0)
            self.assertTrue(any("duplicate asset_id" in e for e in result["errors"]))

    def test_missing_blank_or_nonstring_asset_id_fails(self):
        needs = _needs(("hero", 1, False, None))
        for asset_id in (None, "", "   ", 123, ["x"]):
            maps = [{"asset_id": asset_id, "source": "a.mp4", "scenes": []}]
            result = md.compute_material_delta(needs, maps)
            self.assertFalse(result["ok"], asset_id)
            self.assertEqual(result["deltas"], [])
            self.assertFalse(result["ready_for_build"])

    def test_unique_asset_ids_still_pass(self):
        needs = _needs(("a", 1, True, None), ("b", 1, True, None))
        na, nb = needs["needs"][0]["need_id"], needs["needs"][1]["need_id"]
        maps = [self._scene_map("x", "a.mp4", na), self._scene_map("y", "b.mp4", nb)]
        result = md.compute_material_delta(needs, maps)
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["summary"]["covered"], 2)
        self.assertTrue(result["ready_for_build"])


class BoundaryTest(unittest.TestCase):
    def test_no_semantic_or_phase_fields_in_output(self):
        needs = _needs(("cable pull", 1, True, None))
        result = md.compute_material_delta(needs, _map_with_satisfies(_first_id(needs), "accepted"))
        delta = result["deltas"][0]
        # increment-1 boundary: no semantic/function-phase outcomes leak in
        self.assertIn(delta["outcome"], md.VALID_OUTCOMES)
        for forbidden in ("wrong_semantics", "insufficient_action_phases",
                          "function", "action_phase", "semantic"):
            self.assertNotIn(forbidden, delta)
            self.assertNotIn(forbidden, delta["evidence"])

    def test_multiple_needs_summary_counts(self):
        needs = _needs(("a", 1, True, None), ("b", 1, False, None))
        nid_a = needs["needs"][0]["need_id"]
        result = md.compute_material_delta(needs, _map_with_satisfies(nid_a, "accepted"))
        self.assertEqual(result["summary"]["covered"], 1)   # a covered
        self.assertEqual(result["summary"]["missing"], 1)   # b missing
        self.assertTrue(result["ready_for_build"])          # b optional -> no block


if __name__ == "__main__":
    unittest.main()
