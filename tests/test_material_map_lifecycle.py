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

    def test_4_all_covered_with_contract_is_build_ready_to_original(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("one", True, None)])
            nid = needs["needs"][0]["need_id"]
            mapdir = _maps_dir(d, [_map("a", "a.mp4", need_id=nid, status="accepted")])
            contract = _w(d, "contract.json", {"segments": [_seg(1, [nid]), _seg(2, [nid])]})
            db = _w(d, "materials_db.json", {"files": []})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    needs_ref=_w(d, "needs.json", needs), maps_dir=mapdir,
                                    contract_ref=contract, material_db_ref=db)
            self.assertEqual(rep["stage"], "build_ready")
            self.assertTrue(rep["can_build"])
            self.assertEqual(rep["build_handoff"]["contract_ref"], contract)
            self.assertTrue(rep["build_handoff"]["ready_for_build"])

    def test_5_accepted_drop_with_waiver_build_ready_to_revised(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("mandatory", True, None), ("keep", False, None)])
            ids = [n["need_id"] for n in needs["needs"]]
            mapdir = _maps_dir(d, [_map("a", "a.mp4", need_id=ids[1], status="accepted")])
            contract = _w(d, "contract.json",
                          {"segments": [_seg(1, [ids[0]]), _seg(2, [ids[1]]), _seg(3, [ids[1]])]})
            decisions = _w(d, "decisions.json", [{
                "decision_id": "x1", "need_id": ids[0], "route": "drop_segment",
                "status": "accepted", "target_segment": 1,
                "waiver": {"reviewer": "dir", "reason": "cut"},
                "lineage": {"reviewer": "dir", "reason": "cut", "at": "2026-06-15T00:00"}}])
            db = _w(d, "materials_db.json", {"files": []})
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    needs_ref=_w(d, "needs.json", needs), maps_dir=mapdir,
                                    contract_ref=contract, decisions_ref=decisions,
                                    material_db_ref=db)
            self.assertEqual(rep["stage"], "build_ready")
            self.assertTrue(rep["build_handoff"]["contract_ref"].endswith(
                "revised_segment_contract.json"))
            revised = json.loads(Path(rep["build_handoff"]["contract_ref"]).read_text(encoding="utf-8"))
            self.assertNotIn(1, [s["segment"] for s in revised["segments"]])

    def test_6_pending_decision_not_applied(self):
        with tempfile.TemporaryDirectory() as d:
            needs = _needs([("opt", False, None)])
            nid = needs["needs"][0]["need_id"]
            mapdir = _maps_dir(d, [_map("a", "a.mp4", need_id=nid, status="accepted")])
            contract = _w(d, "contract.json", {"segments": [_seg(1, [nid]), _seg(2, [nid])]})
            decisions = _w(d, "decisions.json", [{
                "decision_id": "x1", "need_id": nid, "route": "script_rewrite",
                "status": "rejected", "target_segment": 1,
                "patch": {"material_fit": {"visual_desc": "NO"}},
                "lineage": {"reviewer": "d", "reason": "r", "at": "t"}}])
            rep = mml.run_lifecycle(out_dir=Path(d) / "out",
                                    needs_ref=_w(d, "needs.json", needs), maps_dir=mapdir,
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


if __name__ == "__main__":
    unittest.main()
