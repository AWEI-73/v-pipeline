"""M6d — Independent Material-Map Lifecycle tests.

The runner derives the lifecycle stage FRESH from the artifacts that exist now,
reusing the canonical M6a-M6c tools. It can stop at any planning/await stage
without rendering, and emits a BUILD handoff only when build_ready (pointing at a
gate-passing, existing contract). No second canonical schema, no render.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import material_map_lifecycle as mml
from video_pipeline_core.material_needs import (
    apply_satisfaction_verdict, migrate_material_needs,
)


def _needs(specs):
    raw = {"project": "demo", "needs": [
        {"category": "動作鏡頭", "type": "video", "purpose": p, "count": 1,
         "fallback_tier": 1, "must_have": mh, **({"fallback_options": fb} if fb else {})}
        for p, mh, fb in specs]}
    return migrate_material_needs(raw)


def _map(asset_id, source, need_id=None, status="accepted", start=0, end=3):
    m = {"asset_id": asset_id, "source": source,
         "scenes": [{"start": start, "end": end, "caption": "c"}]}
    if need_id:
        apply_satisfaction_verdict(
            m, {"reviewer": "agent", "scenes": [
                {"scene_index": 0, "satisfies": [{"need_id": need_id, "status": status}]}]},
            valid_need_ids={need_id})
    return m


def _seg(num, need_refs):
    return {"segment": num,
            "core": {"section_role": "montage", "story_purpose": f"p{num}",
                     "timeline_source": "beat"},
            "material_fit": {"visual_desc": f"scene {num}", "reason": f"r{num}",
                             "need_refs": need_refs},
            "audio": {"role": "music", "reason": f"a{num}"},
            "visual_style": {"layout": "montage", "pace": "fast", "reason": f"v{num}"},
            "text_layer": "none"}


def _w(d, name, obj):
    p = Path(d) / name
    p.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    return str(p)


def _covered_db(d, purpose, must_have):
    """A material_db (single source) covering one need; returns (db_path, needs_path, need_id)."""
    needs = _needs([(purpose, must_have, None)])
    nid = needs["needs"][0]["need_id"]
    (Path(d) / "clip.map.json").write_text(
        json.dumps(_map("clip", "a.mp4", need_id=nid, status="accepted")), encoding="utf-8")
    db = _w(d, "materials_db.json", {"files": [{"path": "a.mp4", "material_map": "clip.map.json"}]})
    needs_path = _w(d, "needs.json", needs)
    return db, needs_path, nid


def _maps_dir(d, maps):
    md = Path(d) / "maps"
    md.mkdir(exist_ok=True)
    for m in maps:
        (md / f"{m['asset_id']}.map.json").write_text(json.dumps(m), encoding="utf-8")
    return str(md)


class EntryTest(unittest.TestCase):
    def test_1_material_only_awaits_requirements_no_delta_no_invented_needs(self):
        with tempfile.TemporaryDirectory() as d:
            mapdir = _maps_dir(d, [_map("a", "a.mp4"), _map("b", "b.mp4")])
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", maps_dir=mapdir)
            self.assertEqual(rep["stage"], "await_requirements_discussion")
            self.assertEqual(rep["entry_point"], "existing_material")
            self.assertFalse(rep["can_build"])
            self.assertIsNone(rep["refs"]["material_delta"])      # no delta run
            self.assertIsNone(rep["refs"]["material_needs"])      # no invented needs
            self.assertTrue((Path(d) / "out" / "project_material_map.json").exists())

    def test_2_needs_only_zero_material_awaits_material(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("hero", True, None)])
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=_w(d, "needs.json", needs))
            self.assertEqual(rep["stage"], "await_material")
            self.assertEqual(rep["entry_point"], "script_first")
            self.assertFalse(rep["can_build"])
            self.assertTrue((Path(d) / "out" / "shooting_brief.json").exists())

    def test_3_partial_reports_covered_and_missing_without_overclaiming(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("covered", False, None), ("missing", True, None)])
            ids = [n["need_id"] for n in needs["needs"]]
            mapdir = _maps_dir(d, [_map("a", "a.mp4", need_id=ids[0], status="accepted")])
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    needs_ref=_w(d, "needs.json", needs), maps_dir=mapdir)
            self.assertEqual(rep["entry_point"], "partial")
            self.assertEqual(rep["stage"], "await_material")       # missing must_have blocks
            delta = json.loads((Path(d) / "out" / "material_delta.json").read_text(encoding="utf-8"))
            summ = delta["summary"]
            self.assertEqual(summ["covered"], 1)
            self.assertEqual(summ["missing"], 1)

    def test_4_all_covered_via_material_db_is_build_ready_to_original(self):
        with tempfile.TemporaryDirectory() as d:
            db, needs_path, nid = _covered_db(d, "one", True)
            contract = _w(d, "contract.json", {"material_needs_ref": "needs.json",
                          "segments": [_seg(1, [nid]), _seg(2, [nid])]})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=needs_path,
                                    material_db_ref=db, contract_ref=contract)
            self.assertEqual(rep["stage"], "build_ready")
            self.assertTrue(rep["can_build"])
            self.assertEqual(rep["build_handoff"]["contract_ref"], contract)   # original
            self.assertEqual(rep["build_handoff"]["material_db_ref"], db)
            self.assertTrue(rep["build_handoff"]["ready_for_build"])

    def test_5_accepted_drop_with_waiver_build_ready_handoff_to_original(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("mandatory", True, None), ("keep", False, None)])
            ids = [n["need_id"] for n in needs["needs"]]
            (Path(d) / "clip.map.json").write_text(
                json.dumps(_map("clip", "b.mp4", need_id=ids[1], status="accepted")),
                encoding="utf-8")
            db = _w(d, "materials_db.json",
                    {"files": [{"path": "b.mp4", "material_map": "clip.map.json"}]})
            decisions = _w(d, "decisions.json", [{
                "decision_id": "x1", "need_id": ids[0], "route": "drop_segment",
                "status": "accepted", "target_segment": 1,
                "waiver": {"reviewer": "dir", "reason": "cut"},
                "lineage": {"reviewer": "dir", "reason": "cut", "at": "2026-06-15T00:00"}}])
            contract = _w(d, "contract.json",
                          {"material_needs_ref": "needs.json", "revision_decisions_ref": "decisions.json",
                           "segments": [_seg(1, [ids[0]]), _seg(2, [ids[1]]), _seg(3, [ids[1]])]})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=_w(d, "needs.json", needs),
                                    material_db_ref=db, contract_ref=contract, decisions_ref=decisions)
            self.assertEqual(rep["stage"], "build_ready")
            self.assertEqual(rep["build_handoff"]["contract_ref"], contract)   # original (re-runs M6c)
            self.assertTrue(rep["refs"]["revised_contract"].endswith("revised_segment_contract.json"))
            revised = json.loads(Path(rep["refs"]["revised_contract"]).read_text(encoding="utf-8"))
            self.assertNotIn(1, [s["segment"] for s in revised["segments"]])   # seg dropped (evidence)

    def test_6_rejected_decision_not_applied(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("opt", False, None)])      # missing optional -> script_rewrite compatible
            nid = needs["needs"][0]["need_id"]
            contract = _w(d, "contract.json", {"segments": [_seg(1, [nid]), _seg(2, [nid])]})
            decisions = _w(d, "decisions.json", [{
                "decision_id": "x1", "need_id": nid, "route": "script_rewrite",
                "status": "rejected", "target_segment": 1,
                "patch": {"material_fit": {"visual_desc": "NO"}},
                "lineage": {"reviewer": "d", "reason": "r", "at": "t"}}])
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    needs_ref=_w(d, "needs.json", needs),
                                    contract_ref=contract, decisions_ref=decisions)
            self.assertEqual(rep["stage"], "await_revision_decision")
            self.assertFalse((Path(d) / "out" / "revised_segment_contract.json").exists())


class FreshnessTest(unittest.TestCase):
    def test_stale_lifecycle_report_not_trusted_downgrades(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("hero", True, None)])
            nid = needs["needs"][0]["need_id"]
            out = Path(d) / "out"
            out.mkdir(parents=True)
            # a stale report claiming build_ready
            (out / "material_map_lifecycle.json").write_text(
                json.dumps({"stage": "build_ready", "can_build": True}), encoding="utf-8")
            # current reality: zero material -> must downgrade
            rep = mml.run_lifecycle(out_dir=out, needs_ref=_w(d, "needs.json", needs))
            self.assertEqual(rep["stage"], "await_material")
            self.assertFalse(rep["can_build"])

    def test_stale_delta_overwritten_by_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("hero", True, None)])
            out = Path(d) / "out"
            out.mkdir(parents=True)
            (out / "material_delta.json").write_text(
                json.dumps({"ok": True, "ready_for_build": True, "deltas": []}), encoding="utf-8")
            rep = mml.run_lifecycle(out_dir=out, needs_ref=_w(d, "needs.json", needs))
            fresh = json.loads((out / "material_delta.json").read_text(encoding="utf-8"))
            self.assertFalse(fresh["ready_for_build"])             # recomputed, missing


class FailureTest(unittest.TestCase):
    def test_dangling_need_edge_is_invalid_not_missing(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("hero", True, None)])
            # a map satisfies a need that is NOT in the canonical needs
            bad_map = {"asset_id": "a", "source": "a.mp4", "scenes": [
                {"start": 0, "end": 2, "satisfies": [{"need_id": "nd_ghost", "status": "accepted"}]}]}
            mapdir = _maps_dir(d, [bad_map])
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    needs_ref=_w(d, "needs.json", needs), maps_dir=mapdir)
            self.assertEqual(rep["stage"], "invalid")

    def test_corrupt_needs_is_structured_invalid_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "needs.json"
            p.write_text("{ not json", encoding="utf-8")
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=str(p))
            self.assertEqual(rep["stage"], "invalid")
            self.assertTrue(rep["blocking"])

    def test_duplicate_asset_identity_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("opt", False, None)])
            nid = needs["needs"][0]["need_id"]
            mapdir = _maps_dir(d, [_map("dup", "a.mp4", need_id=nid)])
            # second map file with the SAME asset_id
            (Path(mapdir) / "second.map.json").write_text(
                json.dumps(_map("dup", "b.mp4", need_id=nid)), encoding="utf-8")
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    needs_ref=_w(d, "needs.json", needs), maps_dir=mapdir)
            self.assertEqual(rep["stage"], "invalid")


class StopWithoutRenderTest(unittest.TestCase):
    def test_inventory_and_brief_stages_do_not_require_final(self):
        with tempfile.TemporaryDirectory() as d:
            # inventory-only
            mapdir = _maps_dir(d, [_map("a", "a.mp4")])
            inv = mml.run_lifecycle(out_dir=Path(d) / "inv", maps_dir=mapdir)
            self.assertEqual(inv["stage"], "await_requirements_discussion")
            self.assertIsNone(inv["build_handoff"])
            self.assertFalse((Path(d) / "inv" / "final.mp4").exists())
            # brief-only
            needs = _needs([("hero", True, None)])
            br = mml.run_lifecycle(out_dir=Path(d) / "br", needs_ref=_w(d, "needs.json", needs))
            self.assertIsNone(br["build_handoff"])
            self.assertFalse((Path(d) / "br" / "final.mp4").exists())


class HandoffBindingTest(unittest.TestCase):
    def test_A_contract_without_material_needs_ref_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            db, needs_path, nid = _covered_db(d, "one", True)
            contract = _w(d, "contract.json", {"segments": [_seg(1, [nid]), _seg(2, [nid])]})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=needs_path,
                                    material_db_ref=db, contract_ref=contract)
            self.assertEqual(rep["stage"], "invalid")
            self.assertFalse(rep["can_build"])

    def test_B_contract_pointing_to_different_needs_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            db, needs_path, nid = _covered_db(d, "one", True)
            _w(d, "other.json", _needs([("x", True, None)]))     # a DIFFERENT needs file
            contract = _w(d, "contract.json", {"material_needs_ref": "other.json",
                          "segments": [_seg(1, [nid]), _seg(2, [nid])]})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=needs_path,
                                    material_db_ref=db, contract_ref=contract)
            self.assertEqual(rep["stage"], "invalid")

    def test_C_corrupt_material_db_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("one", True, None)])
            db = Path(d) / "materials_db.json"
            db.write_text("{ corrupt", encoding="utf-8")
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    needs_ref=_w(d, "needs.json", needs), material_db_ref=str(db))
            self.assertEqual(rep["stage"], "invalid")

    def test_D_empty_material_db_with_must_have_is_not_build_ready(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("one", True, None)])
            db = _w(d, "materials_db.json", {"files": []})
            nid = needs["needs"][0]["need_id"]
            contract = _w(d, "contract.json", {"material_needs_ref": "needs.json",
                          "segments": [_seg(1, [nid]), _seg(2, [nid])]})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=_w(d, "needs.json", needs),
                                    material_db_ref=db, contract_ref=contract)
            self.assertEqual(rep["stage"], "await_material")    # missing, not build_ready
            self.assertFalse(rep["can_build"])

    def test_E_spec_invalid_contract_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            db, needs_path, nid = _covered_db(d, "one", True)
            bad = _seg(1, [nid]); bad["audio"] = {}              # missing audio.role/reason
            contract = _w(d, "contract.json", {"material_needs_ref": "needs.json",
                          "segments": [bad, _seg(2, [nid])]})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=needs_path,
                                    material_db_ref=db, contract_ref=contract)
            self.assertEqual(rep["stage"], "invalid")

    def test_categories_missing_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            db, needs_path, nid = _covered_db(d, "one", True)
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=needs_path,
                                    material_db_ref=db,
                                    categories_path=str(Path(d) / "nope_categories.json"))
            self.assertEqual(rep["stage"], "invalid")


class SourceAmbiguityTest(unittest.TestCase):
    def test_G_multiple_sources_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            mapdir = _maps_dir(d, [_map("a", "a.mp4")])
            pm = _w(d, "project_material_map.json",
                    {"artifact_role": "project_material_map", "assets": []})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", maps_dir=mapdir, project_map_ref=pm)
            self.assertEqual(rep["stage"], "invalid")
            self.assertTrue(any("exactly one" in b for b in rep["blocking"]))

    def test_H_missing_maps_dir_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", maps_dir=str(Path(d) / "nope"))
            self.assertEqual(rep["stage"], "invalid")

    def test_I_missing_project_map_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    project_map_ref=str(Path(d) / "nope.json"))
            self.assertEqual(rep["stage"], "invalid")


class DecisionsValidationTest(unittest.TestCase):
    def _base(self, d):
        needs = _needs([("opt", False, None)])
        nid = needs["needs"][0]["need_id"]
        contract = _w(d, "contract.json", {"segments": [_seg(1, [nid]), _seg(2, [nid])]})
        return _w(d, "needs.json", needs), contract, nid

    def test_J_non_list_or_malformed_decisions_invalid(self):
        for payload in ({"not": "a list"}, "a string", [{"decision_id": "d1"}]):
            with tempfile.TemporaryDirectory() as d:
                needs_path, contract, nid = self._base(d)
                dec = _w(d, "decisions.json", payload)
                rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=needs_path,
                                        contract_ref=contract, decisions_ref=dec)
                self.assertEqual(rep["stage"], "invalid", payload)

    def test_K_valid_rejected_only_awaits_decision(self):
        with tempfile.TemporaryDirectory() as d:
            needs_path, contract, nid = self._base(d)
            dec = _w(d, "decisions.json", [{
                "decision_id": "d1", "need_id": nid, "route": "script_rewrite",
                "status": "rejected", "target_segment": 1,
                "patch": {"material_fit": {"visual_desc": "x"}},
                "lineage": {"reviewer": "r", "reason": "r", "at": "t"}}])
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=needs_path,
                                    contract_ref=contract, decisions_ref=dec)
            self.assertEqual(rep["stage"], "await_revision_decision")
            self.assertFalse((Path(d) / "out" / "revised_segment_contract.json").exists())

    def test_L_unknown_need_id_even_when_rejected_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            needs_path, contract, nid = self._base(d)
            dec = _w(d, "decisions.json", [{
                "decision_id": "d1", "need_id": "nd_ghost", "route": "script_rewrite",
                "status": "rejected", "target_segment": 1,
                "patch": {"material_fit": {"visual_desc": "x"}},
                "lineage": {"reviewer": "r", "reason": "r", "at": "t"}}])
            rep = mml.run_lifecycle(out_dir=Path(d) / "out", needs_ref=needs_path,
                                    contract_ref=contract, decisions_ref=dec)
            self.assertEqual(rep["stage"], "invalid")


class MapInputShapeTest(unittest.TestCase):
    def test_A_bad_ref_shapes_are_invalid_not_crash(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("", "   ", 123, True, [], {}):
                r1 = mml.run_lifecycle(out_dir=Path(d) / "o", maps_dir=bad)
                self.assertEqual(r1["stage"], "invalid", ("maps_dir", bad))
                r2 = mml.run_lifecycle(out_dir=Path(d) / "o", project_map_ref=bad)
                self.assertEqual(r2["stage"], "invalid", ("project_map_ref", bad))

    def _maps_dir_with(self, d, *map_objs):
        md = Path(d) / "maps"
        md.mkdir(exist_ok=True)
        for i, obj in enumerate(map_objs):
            (md / f"m{i}.map.json").write_text(json.dumps(obj), encoding="utf-8")
        return str(md)

    def test_B_non_object_scene_is_invalid_not_crash(self):
        for bad_scene in (123, [], "scene"):
            with tempfile.TemporaryDirectory() as d:
                mapdir = self._maps_dir_with(d, {"asset_id": "a", "source": "s",
                                                 "scenes": [bad_scene]})
                rep = mml.run_lifecycle(out_dir=Path(d) / "o", maps_dir=mapdir)
                self.assertEqual(rep["stage"], "invalid", bad_scene)

    def test_C_scenes_not_a_list_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            mapdir = self._maps_dir_with(d, {"asset_id": "a", "source": "s", "scenes": 123})
            rep = mml.run_lifecycle(out_dir=Path(d) / "o", maps_dir=mapdir)
            self.assertEqual(rep["stage"], "invalid")

    def test_D_malformed_asset_in_project_map_is_invalid(self):
        cases = [
            {"artifact_role": "project_material_map", "assets": [123]},
            {"artifact_role": "project_material_map",
             "assets": [{"asset_id": "", "source": "s", "scenes": []}]},
            {"artifact_role": "project_material_map",
             "assets": [{"asset_id": "a", "scenes": []}]},     # missing source
        ]
        for case in cases:
            with tempfile.TemporaryDirectory() as d:
                pm = _w(d, "project_material_map.json", case)
                rep = mml.run_lifecycle(out_dir=Path(d) / "o", project_map_ref=pm)
                self.assertEqual(rep["stage"], "invalid", case)

    def test_E_material_db_with_malformed_scene_is_invalid(self):
        with tempfile.TemporaryDirectory() as d:
            (Path(d) / "clip.map.json").write_text(
                json.dumps({"asset_id": "a", "source": "s", "scenes": [123]}), encoding="utf-8")
            db = _w(d, "materials_db.json",
                    {"files": [{"path": "s", "material_map": "clip.map.json"}]})
            needs = _needs([("one", True, None)])
            rep = mml.run_lifecycle(out_dir=Path(d) / "o",
                                    needs_ref=_w(d, "needs.json", needs), material_db_ref=db)
            self.assertEqual(rep["stage"], "invalid")

    def test_F_legal_project_map_source_inventories(self):
        with tempfile.TemporaryDirectory() as d:
            pm = _w(d, "project_material_map.json", {
                "artifact_role": "project_material_map",
                "assets": [{"asset_id": "a", "source": "a.mp4",
                            "scenes": [{"start": 0, "end": 3, "caption": "c"}]}]})
            rep = mml.run_lifecycle(out_dir=Path(d) / "o", project_map_ref=pm)
            self.assertEqual(rep["stage"], "await_requirements_discussion")
            self.assertEqual(rep["entry_point"], "existing_material")


class BuildHandoffTest(unittest.TestCase):
    def test_handoff_with_missing_ref_returns_none(self):
        with tempfile.TemporaryDirectory() as d:
            existing = Path(d) / "c.json"
            existing.write_text("{}", encoding="utf-8")
            missing = Path(d) / "nope.json"
            self.assertIsNone(mml._build_handoff(str(missing), None, None, []))   # contract missing
            self.assertIsNone(mml._build_handoff(str(existing), None, str(missing), []))  # needs missing
            self.assertIsNone(mml._build_handoff(str(existing), str(missing), None, []))  # db missing
            self.assertIsNotNone(mml._build_handoff(str(existing), None, None, []))

    def test_build_ready_handoff_passes_run_contract_fresh_gate(self):
        """The build_ready handoff, fed to run_contract, re-runs the M6b gate fresh
        (not bypassed) and reaches BUILD. mv_chain is mocked (real render = M6e)."""
        from unittest.mock import patch
        from video_pipeline_core import contract_adapter as ca
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            needs = _needs([("one", True, None)])
            nid = needs["needs"][0]["need_id"]
            needs_path = _w(d, "needs.json", needs)
            # a per-asset map covering the need, referenced by a material_db
            map_file = d / "clip.map.json"
            map_file.write_text(json.dumps(_map("clip", "a.mp4", need_id=nid, status="accepted")),
                                encoding="utf-8")
            db_path = _w(d, "materials_db.json", {"files": [{"path": "a.mp4",
                        "material_map": "clip.map.json"}]})
            # contract declares material_needs_ref so run_contract's gate fires
            contract = {"style": "mv", "music": {"brief": "x"},
                        "material_needs_ref": "needs.json",
                        "segments": [_seg(1, [nid]), _seg(2, [nid])]}
            contract_path = _w(d, "contract.json", contract)

            rep = mml.run_lifecycle(out_dir=d / "out", needs_ref=needs_path,
                                    material_db_ref=db_path, contract_ref=contract_path)
            self.assertEqual(rep["stage"], "build_ready")
            handoff = rep["build_handoff"]
            self.assertEqual(handoff["contract_ref"], contract_path)

            calls = {"mv": False}

            def fake_mv_chain(script, material_db_arg, out_path, music_path=None,
                              mat_dir="/tmp", verbose=True, **kwargs):
                calls["mv"] = True
                Path(out_path).write_bytes(b"mp4")
                st = Path(out_path).parent / "state.json"
                st.write_text(json.dumps({"final": str(out_path), "next_action": None}),
                              encoding="utf-8")
                return {"final": str(out_path), "state": str(st), "plan": []}

            def fake_music(audio_path, out_path, **_k):
                Path(out_path).write_text("{}", encoding="utf-8")
                return {"ok": True, "music_structure": str(out_path)}

            music = d / "bgm.mp3"
            music.write_bytes(b"fake")
            with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
                 patch("video_pipeline_core.music_structure.write_music_structure", fake_music):
                result = ca.run_contract(
                    handoff["contract_ref"], material_db=handoff["material_db_ref"],
                    out_path=d / "out" / "final.mp4", music_path=music,
                    mat_dir=d / "out", verbose=False)
            # the fresh M6b gate ran inside run_contract and did NOT block
            self.assertNotEqual(result.get("stage"), "material_delta")
            self.assertNotEqual(result.get("stage"), "material_revision")
            self.assertTrue(calls["mv"])

    def test_single_segment_contract_does_not_get_build_ready_handoff(self):
        """Lifecycle must not declare build_ready for a contract that the
        contract-run MV validator will always reject before render."""
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            needs = _needs([("one", True, None)])
            nid = needs["needs"][0]["need_id"]
            needs_path = _w(d, "needs.json", needs)
            map_file = d / "clip.map.json"
            map_file.write_text(json.dumps(_map("clip", "a.mp4", need_id=nid, status="accepted")),
                                encoding="utf-8")
            db_path = _w(d, "materials_db.json", {"files": [{"path": "a.mp4",
                        "material_map": "clip.map.json"}]})
            contract = {"style": "mv", "music": {"brief": "x"},
                        "material_needs_ref": "needs.json",
                        "segments": [_seg(1, [nid])]}
            contract_path = _w(d, "contract.json", contract)

            rep = mml.run_lifecycle(out_dir=d / "out", needs_ref=needs_path,
                                    material_db_ref=db_path, contract_ref=contract_path)

            self.assertEqual(rep["stage"], "invalid")
            self.assertFalse(rep["can_build"])
            self.assertIsNone(rep["build_handoff"])
            self.assertIn("at least 2 segments", rep["blocking"][0])


if __name__ == "__main__":
    unittest.main()
