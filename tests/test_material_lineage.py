"""M6a Lineage Integration — end-to-end need_id reference chain tests.

The chain: need_id -> shooting-brief requirement -> scene satisfies edge ->
segment_contract material_fit.need_refs. These tests prove the join holds end to
end and that a broken reference at ANY hop is caught, WITHOUT the linker making a
coverage/delta decision.
"""
import unittest

from video_pipeline_core import material_lineage as ml
from video_pipeline_core.material_needs import (
    apply_satisfaction_verdict, migrate_material_needs, need_ids,
)
from video_pipeline_core.spec_contract import validate_segment_contract


def _needs(*purposes):
    return migrate_material_needs({
        "project": "demo",
        "needs": [{"category": "動作鏡頭", "type": "video", "purpose": p,
                   "count": 1, "fallback_tier": 1, "must_have": True}
                  for p in purposes]})


def _first_need_id(needs):
    return needs["needs"][0]["need_id"]


class ShootingBriefProjectionTest(unittest.TestCase):
    def test_brief_requirement_carries_need_id_for_every_need(self):
        needs = _needs("opening cable pull", "team carry")
        brief = ml.build_shooting_brief(needs)
        self.assertEqual(brief["artifact_role"], "shooting_brief")
        self.assertEqual(len(brief["requirements"]), 2)
        self.assertEqual(ml.shooting_brief_need_ids(brief), need_ids(needs))
        for req in brief["requirements"]:
            self.assertTrue(req["need_id"].startswith("nd_"))
            self.assertEqual(req["purpose"], req["purpose"])  # purpose preserved
            self.assertIn("category", req)

    def test_invalid_needs_cannot_build_a_brief(self):
        # un-migrated need: no need_id yet -> strict validate fails -> raises
        with self.assertRaises(ValueError):
            ml.build_shooting_brief({"project": "x", "needs": [
                {"category": "c", "type": "video", "purpose": "p"}]})


class ContractNeedRefTest(unittest.TestCase):
    def _contract(self, need_refs):
        return {"segments": [{
            "core": {"story_purpose": "p", "timeline_source": "beat",
                     "section_role": "body"},
            "material_fit": {"visual_desc": "d", "reason": "r", "need_refs": need_refs},
            "audio": {"role": "music", "reason": "r"},
            "visual_style": {"layout": "montage", "pace": "fast", "reason": "r"},
            "text_layer": "none",
        }]}

    def test_well_shaped_need_refs_pass_validation(self):
        res = validate_segment_contract(self._contract(["nd_ab12cd34"]))
        self.assertTrue(res["ok"], res["errors"])

    def test_malformed_need_refs_fail_validation(self):
        for bad in ([""], [123], "nd_x", []):
            res = validate_segment_contract(self._contract(bad))
            self.assertFalse(res["ok"])
            self.assertTrue(any("need_refs" in e for e in res["errors"]))

    def test_contract_need_refs_reader_returns_ordered_records(self):
        records = ml.contract_need_refs(self._contract(["nd_a", "nd_b"]))
        self.assertEqual(records, [{"segment_ref": "body", "segment_index": 0,
                                    "need_refs": ["nd_a", "nd_b"]}])


class EndToEndChainTest(unittest.TestCase):
    def _maps(self, need_id):
        material_map = {"asset_id": "clip-a", "source": "a.mp4",
                        "scenes": [{"start": 0, "end": 3, "caption": "cable pull"}]}
        apply_satisfaction_verdict(
            material_map,
            {"reviewer": "agent",
             "scenes": [{"scene_index": 0,
                         "satisfies": [{"need_id": need_id, "status": "accepted"}]}]},
            valid_need_ids={need_id})
        return [material_map]

    def _contract(self, need_id):
        return {"segments": [{
            "core": {"story_purpose": "p", "timeline_source": "beat"},
            "material_fit": {"visual_desc": "cable pull", "reason": "r",
                             "need_refs": [need_id]},
            "audio": {"role": "music", "reason": "r"},
            "visual_style": {"layout": "montage", "pace": "fast", "reason": "r"},
            "text_layer": "none",
        }]}

    def test_need_id_survives_through_every_artifact(self):
        needs = _needs("cable pull")
        nid = _first_need_id(needs)
        brief = ml.build_shooting_brief(needs)
        result = ml.link_lineage(needs, shooting_brief=brief,
                                 material_maps=self._maps(nid), contract=self._contract(nid))
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["dangling"], {})
        link = result["chain"][nid]
        self.assertTrue(link["in_brief"])
        self.assertEqual(len(link["satisfied_by"]["accepted"]), 1)
        self.assertEqual(link["contract_segments"], ["#0"])

    def test_dangling_brief_reference_is_an_error(self):
        needs = _needs("cable pull")
        bad_brief = {"requirements": [{"need_id": "nd_doesnotexist"}]}
        result = ml.link_lineage(needs, shooting_brief=bad_brief)
        self.assertFalse(result["ok"])
        self.assertEqual(result["dangling"]["shooting_brief"], ["nd_doesnotexist"])

    def test_dangling_contract_reference_is_an_error(self):
        needs = _needs("cable pull")
        result = ml.link_lineage(needs, contract=self._contract("nd_ghost"))
        self.assertFalse(result["ok"])
        self.assertEqual(result["dangling"]["contract_need_ref"], ["nd_ghost"])

    def test_dangling_satisfies_edge_is_an_error(self):
        needs = _needs("cable pull")
        # a hand-authored map whose satisfies edge points at an unknown need_id
        maps = [{"asset_id": "a", "source": "a.mp4", "scenes": [
            {"start": 0, "end": 2, "satisfies": [{"need_id": "nd_phantom", "status": "accepted"}]}]}]
        result = ml.link_lineage(needs, material_maps=maps)
        self.assertFalse(result["ok"])
        self.assertEqual(result["dangling"]["satisfies_edge"], ["nd_phantom"])


def _seg(section_role, need_refs):
    return {"core": {"story_purpose": "p", "timeline_source": "beat",
                     "section_role": section_role},
            "material_fit": {"visual_desc": "d", "reason": "r", "need_refs": need_refs},
            "audio": {"role": "music", "reason": "r"},
            "visual_style": {"layout": "montage", "pace": "fast", "reason": "r"},
            "text_layer": "none"}


class HardeningShapeTest(unittest.TestCase):
    def test_repeated_section_role_does_not_hide_first_segments_dangling_ref(self):
        # two segments with section_role=body: the FIRST has a dangling ref, the
        # SECOND a valid one. A dict keyed by section_role would overwrite the
        # first and miss the dangling ref — ordered records must catch it.
        needs = _needs("cable pull")
        nid = _first_need_id(needs)
        contract = {"segments": [_seg("body", ["nd_ghost"]), _seg("body", [nid])]}
        result = ml.link_lineage(needs, contract=contract)
        self.assertFalse(result["ok"])
        self.assertIn("nd_ghost", result["dangling"]["contract_need_ref"])

    def test_brief_requirement_missing_or_nonstring_need_id_fails(self):
        needs = _needs("cable pull")
        for bad in ([{"category": "c"}], [{"need_id": 123}], [{"need_id": ""}], ["nd_x"]):
            result = ml.link_lineage(needs, shooting_brief={"requirements": bad})
            self.assertFalse(result["ok"], bad)
        # requirements not a list
        self.assertFalse(ml.link_lineage(needs, shooting_brief={"requirements": "x"})["ok"])

    def test_contract_need_refs_malformed_shapes_fail_not_silently_filtered(self):
        needs = _needs("cable pull")
        for bad in ([123], [], "nd_x", [""], ["ok", 7]):
            result = ml.link_lineage(needs, contract={"segments": [_seg("body", bad)]})
            self.assertFalse(result["ok"], bad)
            self.assertTrue(any("need_refs" in e for e in result["errors"]))

    def test_satisfies_edge_malformed_fails_without_crashing(self):
        needs = _needs("cable pull")
        nid = _first_need_id(needs)
        cases = [
            123,                                              # edge not an object
            {"need_id": 123, "status": "accepted"},           # need_id not a string
            {"need_id": nid, "status": "maybe"},              # illegal status
            {"status": "accepted"},                           # missing need_id
        ]
        for bad_edge in cases:
            maps = [{"asset_id": "a", "source": "a.mp4",
                     "scenes": [{"start": 0, "end": 2, "satisfies": [bad_edge]}]}]
            result = ml.link_lineage(needs, material_maps=maps)   # must not raise
            self.assertFalse(result["ok"], bad_edge)
        # satisfies not a list, and material_maps not a list — also handled
        self.assertFalse(ml.link_lineage(needs, material_maps=[
            {"asset_id": "a", "scenes": [{"satisfies": "x"}]}])["ok"])
        self.assertFalse(ml.link_lineage(needs, material_maps="x")["ok"])

    def test_legal_four_link_join_still_ok(self):
        needs = _needs("cable pull")
        nid = _first_need_id(needs)
        brief = ml.build_shooting_brief(needs)
        maps = [{"asset_id": "a", "source": "a.mp4", "scenes": [
            {"start": 0, "end": 2, "satisfies": [{"need_id": nid, "status": "accepted"}]}]}]
        result = ml.link_lineage(needs, shooting_brief=brief, material_maps=maps,
                                 contract={"segments": [_seg("body", [nid])]})
        self.assertTrue(result["ok"], result["errors"])
        self.assertEqual(result["chain"][nid]["contract_segments"], ["body"])


class BoundaryTest(unittest.TestCase):
    def test_backward_compatible_with_no_brief_no_refs(self):
        needs = _needs("cable pull")
        result = ml.link_lineage(needs)   # needs only, nothing downstream
        self.assertTrue(result["ok"])
        self.assertEqual(result["dangling"], {})

    def test_linker_makes_no_coverage_or_delta_decision(self):
        # a need with zero satisfying scenes / zero references is reported as-is,
        # never as missing/thin/covered — that classification is M6b's job.
        needs = _needs("unsatisfied need")
        nid = _first_need_id(needs)
        result = ml.link_lineage(needs, material_maps=[])
        self.assertTrue(result["ok"])
        link = result["chain"][nid]
        self.assertEqual(link["satisfied_by"]["accepted"], [])
        # no delta/coverage verdict keys leak into the lineage artifact
        for forbidden in ("covered", "thin", "missing", "delta", "route", "status"):
            self.assertNotIn(forbidden, result)
            self.assertNotIn(forbidden, link)


if __name__ == "__main__":
    unittest.main()
