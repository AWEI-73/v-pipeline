"""M6c runtime plumbing — run_contract applies accepted revision decisions before
the M6b gate, then BUILDs on the revised contract. Fail-closed everywhere; the
original input is never written; blocked runs stop before render.

mv_chain and music_structure are mocked (house convention) so we can assert what
the BUILD received and whether render was reached, without real ffmpeg.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import contract_adapter as ca
from video_pipeline_core.material_needs import migrate_material_needs

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"
CATS = EXAMPLES / "material_categories.json"


def _needs(specs):
    """specs: list of (purpose, must_have, fallback) -> migrated needs + ids."""
    raw = {"project": "demo", "needs": [
        {"category": "動作鏡頭", "type": "video", "purpose": p, "count": 1,
         "fallback_tier": 1, "must_have": mh, **({"fallback_options": fb} if fb else {})}
        for p, mh, fb in specs]}
    needs = migrate_material_needs(raw)
    return needs, [n["need_id"] for n in needs["needs"]]


def _seg(num, need_refs):
    return {"segment": num,
            "core": {"section_role": "montage", "story_purpose": f"purpose {num}",
                     "timeline_source": "beat"},
            "material_fit": {"visual_desc": f"distinct scene number {num}",
                             "reason": f"because segment {num} matters", "need_refs": need_refs},
            "audio": {"role": "music", "reason": f"music reason {num}"},
            "visual_style": {"layout": "montage", "pace": "fast", "reason": f"vis {num}"},
            "text_layer": "none"}


def _dec(decision_id, need_id, route, status="accepted", **over):
    d = {"decision_id": decision_id, "need_id": need_id, "route": route, "status": status,
         "lineage": {"reviewer": "director", "reason": "reviewed", "at": "2026-06-15T10:00"}}
    d.update(over)
    return d


class _Harness:
    """Builds inputs in dir d and runs run_contract with mocked render."""
    def __init__(self, d):
        self.d = Path(d)

    def write(self, *, segments, needs=None, decisions=None, material_db=None,
              declare_needs=True, declare_decisions=True):
        contract = {"style": "mv", "music": {"brief": "warm"}, "segments": segments}
        if needs is not None and declare_needs:
            contract["material_needs_ref"] = "needs.json"
            (self.d / "needs.json").write_text(json.dumps(needs, ensure_ascii=False), encoding="utf-8")
        if decisions is not None and declare_decisions:
            contract["revision_decisions_ref"] = "decisions.json"
            (self.d / "decisions.json").write_text(json.dumps(decisions, ensure_ascii=False),
                                                   encoding="utf-8")
        self.contract_path = self.d / "contract.json"
        self.contract_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        self.db_path = self.d / "material_db.json"
        self.db_path.write_text(json.dumps(material_db or {"files": []}), encoding="utf-8")
        self.music = self.d / "bgm.mp3"
        self.music.write_bytes(b"fake")
        self.outdir = self.d / "out"
        return self

    def run(self):
        calls = {"mv": False, "script": None}

        def fake_mv_chain(script, material_db_arg, out_path, music_path=None,
                          mat_dir="/tmp", verbose=True, **kwargs):
            calls["mv"] = True
            calls["script"] = script
            Path(out_path).write_bytes(b"mp4")
            state = Path(out_path).parent / "state.json"
            state.write_text(json.dumps({"final": str(out_path), "next_action": None}),
                             encoding="utf-8")
            return {"final": str(out_path), "state": str(state),
                    "plan": [{"segment": 1, "source": "a.mp4", "extract_start": 0,
                              "extract_dur": 1.5, "slot_index": 0, "slot_dur": 1.5}]}

        def fake_music(audio_path, out_path, **_k):
            Path(out_path).write_text("{}", encoding="utf-8")
            return {"ok": True, "music_structure": str(out_path)}

        with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
             patch("video_pipeline_core.music_structure.write_music_structure", fake_music):
            result = ca.run_contract(
                self.contract_path, material_db=self.db_path,
                out_path=self.outdir / "final.mp4", music_path=self.music,
                categories_path=CATS, mat_dir=self.outdir, verbose=False)
        return result, calls


class RuntimePlumbingTest(unittest.TestCase):
    def test_A_no_decisions_ref_unchanged_flow(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                needs=needs, decisions=None).run()           # decisions not declared
            self.assertTrue(calls["mv"])
            self.assertNotEqual(result.get("stage"), "material_revision")

    def test_B_accepted_rewrite_builds_on_revised_contract(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            decisions = [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                              patch={"material_fit": {"visual_desc": "REVISED SCENE"}})]
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                needs=needs, decisions=decisions).run()
            self.assertTrue(calls["mv"])
            descs = [s.get("visual_desc") for s in calls["script"]["segments"]]
            self.assertIn("REVISED SCENE", descs)            # BUILD got the revised contract
            self.assertTrue((Path(d) / "out" / "revised_segment_contract.json").exists())
            self.assertTrue((Path(d) / "out" / "material_revision.json").exists())

    def test_C_drop_with_waiver_passes_gate_and_builds_revised(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("mandatory", True, None), ("keep", False, None)])
            decisions = [_dec("d1", ids[0], "drop_segment", target_segment=1,
                              waiver={"reviewer": "director", "reason": "cut for time"})]
            result, calls = _Harness(d).write(    # 3 segments so dropping 1 leaves >=2 (MV needs >=2)
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[1]]), _seg(3, [ids[1]])],
                needs=needs, decisions=decisions).run()
            self.assertTrue(calls["mv"])
            seg_ids = [s.get("segment") for s in calls["script"]["segments"]]
            self.assertNotIn(1, seg_ids)                     # dropped segment gone
            self.assertIn(2, seg_ids)

    def test_D_reshoot_does_not_render_and_awaits_material(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("mandatory", True, None)])
            decisions = [_dec("d1", ids[0], "reshoot")]      # tier-1 gap, no waiver
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                needs=needs, decisions=decisions).run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse(calls["mv"])
            self.assertEqual(result["next_action"], "await_material")
            self.assertFalse((Path(d) / "out" / "final.mp4").exists())

    def test_E_rejected_decision_builds_original_with_lineage(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            decisions = [_dec("d1", ids[0], "script_rewrite", status="rejected",
                              target_segment=1, patch={"material_fit": {"visual_desc": "NO"}})]
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                needs=needs, decisions=decisions).run()
            self.assertTrue(calls["mv"])
            descs = [s.get("visual_desc") for s in calls["script"]["segments"]]
            self.assertNotIn("NO", descs)                    # rejected patch not applied
            report = json.loads((Path(d) / "out" / "material_revision.json").read_text(encoding="utf-8"))
            self.assertTrue(report["no_op"])
            self.assertEqual(report["decisions"][0]["status"], "rejected")

    def test_F_missing_decisions_file_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=[_dec("d1", ids[0], "script_rewrite",
                                  target_segment=1, patch={"material_fit": {"visual_desc": "x"}})])
            (Path(d) / "decisions.json").unlink()            # remove the declared file
            result, calls = h.run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse(calls["mv"])

    def test_H_revised_contract_invalid_does_not_render(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            # blank out a required field -> revised contract fails validation
            decisions = [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                              patch={"material_fit": {"reason": ""}})]
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                needs=needs, decisions=decisions).run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse(calls["mv"])

    def test_I_gate_revision_disagreement_does_not_render(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("mandatory", True, None)])   # fresh gate will block
            decisions = [_dec("d1", ids[0], "reshoot")]
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=decisions)
            # force a report that lies: ready_for_build True with no waivers
            real = ca.material_revision.apply_revisions if hasattr(ca, "material_revision") else None
            from video_pipeline_core import material_revision as mrmod
            orig = mrmod.apply_revisions

            def lying(contract, delta, decs, **kw):
                report, revised = orig(contract, delta, decs, **kw)
                report = dict(report, ok=True, ready_for_build=True, next_action=None, waivers=[])
                return report, (revised if revised is not None else contract)
            with patch.object(mrmod, "apply_revisions", lying):
                result, calls = h.run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertIn("disagreement", result["reason"].lower())
            self.assertFalse(calls["mv"])

    def test_J_blocked_quarantines_stale_final(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("mandatory", True, None)])
            decisions = [_dec("d1", ids[0], "reshoot")]
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=decisions)
            h.outdir.mkdir(parents=True, exist_ok=True)
            (h.outdir / "final.mp4").write_bytes(b"OLD-RENDER")
            result, calls = h.run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse((h.outdir / "final.mp4").exists())
            self.assertTrue((h.outdir / "stale_previous_final.mp4").exists())
            self.assertEqual(result["stale_final_path"], str(h.outdir / "stale_previous_final.mp4"))

    def test_K_original_contract_file_never_written(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            decisions = [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                              patch={"material_fit": {"visual_desc": "REVISED"}})]
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=decisions)
            snapshot = h.contract_path.read_text(encoding="utf-8")
            h.run()
            self.assertEqual(h.contract_path.read_text(encoding="utf-8"), snapshot)

    def test_L_build_smoke_after_revision(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            decisions = [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                              patch={"material_fit": {"visual_desc": "REVISED"}})]
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                needs=needs, decisions=decisions).run()
            self.assertTrue(result.get("render_ok"))         # full (mocked) BUILD reached


class AdversarialTest(unittest.TestCase):
    def test_decisions_ref_without_needs_ref_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            # declare decisions but NOT material_needs_ref
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                needs=needs, decisions=[_dec("d1", ids[0], "script_rewrite", target_segment=1,
                                        patch={"material_fit": {"visual_desc": "x"}})],
                declare_needs=False).run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse(calls["mv"])
            self.assertEqual(result["next_action"], "revise:material(material_delta)")

    def test_decisions_not_a_list_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=[])
            (Path(d) / "decisions.json").write_text(json.dumps({"not": "a list"}), encoding="utf-8")
            result, calls = h.run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse(calls["mv"])

    def test_revision_does_not_mask_unrelated_tier1_gap(self):
        with tempfile.TemporaryDirectory() as d:
            # nd0 optional (rewritten), nd1 mandatory-missing and untouched -> gate must block
            needs, ids = _needs([("optional", False, None), ("mandatory", True, None)])
            decisions = [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                              patch={"material_fit": {"visual_desc": "REVISED"}})]
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[1]])],
                needs=needs, decisions=decisions).run()
            self.assertEqual(result["stage"], "material_revision")   # nd1 still blocks
            self.assertFalse(calls["mv"])

    def test_conflicting_accepted_decisions_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None), ("two", False, None)])
            decisions = [
                _dec("d1", ids[0], "script_rewrite", target_segment=1,
                     patch={"material_fit": {"visual_desc": "A"}}),
                _dec("d2", ids[1], "script_rewrite", target_segment=1,   # same target
                     patch={"material_fit": {"visual_desc": "B"}})]
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0], ids[1]]), _seg(2, [ids[0]])],
                needs=needs, decisions=decisions).run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse(calls["mv"])

    def test_G_stale_revised_artifact_overwritten_with_fresh(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            decisions = [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                              patch={"material_fit": {"visual_desc": "FRESH REVISED"}})]
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=decisions)
            h.outdir.mkdir(parents=True, exist_ok=True)
            (h.outdir / "revised_segment_contract.json").write_text("STALE-JUNK", encoding="utf-8")
            h.run()
            revised = json.loads((h.outdir / "revised_segment_contract.json").read_text(encoding="utf-8"))
            descs = [s["material_fit"]["visual_desc"] for s in revised["segments"]]
            self.assertIn("FRESH REVISED", descs)            # fresh, not the stale junk


class StrictResolutionTest(unittest.TestCase):
    def _rewrite_dec(self, ids):
        return [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                     patch={"material_fit": {"visual_desc": "REVISED"}})]

    def test_A_missing_decisions_beside_contract_blocks_despite_cwd_copy(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cwd:
            needs, ids = _needs([("optional", False, None)])
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=self._rewrite_dec(ids))
            (Path(d) / "decisions.json").unlink()                  # not beside the contract
            (Path(cwd) / "decisions.json").write_text(            # but present in the cwd
                json.dumps(self._rewrite_dec(ids)), encoding="utf-8")
            old = os.getcwd()
            try:
                os.chdir(cwd)
                result, calls = h.run()
            finally:
                os.chdir(old)
            self.assertEqual(result["stage"], "material_revision")  # cwd copy NOT used
            self.assertFalse(calls["mv"])

    def test_B_missing_needs_beside_contract_blocks_despite_cwd_copy(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cwd:
            needs, ids = _needs([("optional", False, None)])
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=self._rewrite_dec(ids))
            (Path(d) / "needs.json").unlink()                      # not beside the contract
            (Path(cwd) / "needs.json").write_text(json.dumps(needs), encoding="utf-8")
            old = os.getcwd()
            try:
                os.chdir(cwd)
                result, calls = h.run()
            finally:
                os.chdir(old)
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse(calls["mv"])
            self.assertEqual(result["next_action"], "revise:material(material_delta)")

    def test_C_valid_relative_refs_resolve_from_a_different_cwd(self):
        with tempfile.TemporaryDirectory() as d, tempfile.TemporaryDirectory() as cwd:
            needs, ids = _needs([("optional", False, None)])
            h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                                  needs=needs, decisions=self._rewrite_dec(ids))
            old = os.getcwd()
            try:
                os.chdir(cwd)                                       # unrelated cwd
                result, calls = h.run()
            finally:
                os.chdir(old)
            self.assertTrue(calls["mv"])                            # resolved beside contract
            descs = [s.get("visual_desc") for s in calls["script"]["segments"]]
            self.assertIn("REVISED", descs)


class MaterialDbFailClosedTest(unittest.TestCase):
    def _dec_rewrite(self, ids):
        return [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                     patch={"material_fit": {"visual_desc": "REVISED"}})]

    def _run_with_db(self, db_bytes):
        d = tempfile.mkdtemp()
        needs, ids = _needs([("optional", False, None)])
        h = _Harness(d).write(segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                              needs=needs, decisions=self._dec_rewrite(ids))
        if db_bytes is None:
            (Path(d) / "material_db.json").unlink()                # missing DB
        else:
            (Path(d) / "material_db.json").write_bytes(db_bytes)
        result, calls = h.run()
        return Path(d), result, calls

    def test_D_corrupt_missing_nonobject_db_all_block_without_exception(self):
        for db in (None, b"{ not json", b"[1,2,3]",
                   b'{"files": "notalist"}', b'{"files": [1, 2]}'):
            d, result, calls = self._run_with_db(db)
            self.assertEqual(result["stage"], "material_revision", db)
            self.assertFalse(calls["mv"], db)
            self.assertEqual(result["next_action"], "revise:material(material_delta)")

    def test_E_optional_only_needs_with_corrupt_db_does_not_pass(self):
        # would normally pass (optional need) — a corrupt DB must still block,
        # never be treated as zero material.
        d, result, calls = self._run_with_db(b"{ corrupt")
        self.assertEqual(result["stage"], "material_revision")
        self.assertFalse(calls["mv"])

    def test_F_invalid_db_writes_no_artifacts_and_no_build(self):
        d, result, calls = self._run_with_db(b'{"files": {"bad": "shape"}}')
        self.assertFalse(calls["mv"])
        self.assertFalse((d / "out" / "revised_segment_contract.json").exists())
        self.assertFalse((d / "out" / "material_revision.json").exists())
        self.assertFalse((d / "out" / "final.mp4").exists())


class InputShapeTest(unittest.TestCase):
    def test_A_db_none_or_nonpath_is_structured_block_no_typeerror(self):
        for bad in (None, "", "   ", 123, [], {}):
            payload, error = ca._load_material_db_strict(bad)
            self.assertIsNone(payload, bad)
            self.assertTrue(error, bad)

    def test_B_material_map_bad_shapes_are_structured_block(self):
        for bad in (None, "", " ", 123, True, [], {}):
            payload = {"files": [{"path": "a.mp4", "material_map": bad}]}
            maps, error = ca._load_current_material_maps(payload, ".")
            self.assertIsNone(maps, bad)
            self.assertTrue(error, bad)

    def test_material_map_key_absent_is_skipped(self):
        payload = {"files": [{"path": "a.mp4"}, {"path": "b.mp4"}]}   # no material_map key
        maps, error = ca._load_current_material_maps(payload, ".")
        self.assertIsNone(error)
        self.assertEqual(maps, [])

    def test_C_material_map_pointing_to_directory_is_block(self):
        with tempfile.TemporaryDirectory() as d:
            sub = Path(d) / "amap"
            sub.mkdir()
            payload = {"files": [{"path": "a.mp4", "material_map": "amap"}]}
            maps, error = ca._load_current_material_maps(payload, d)
            self.assertIsNone(maps)
            self.assertIn("directory", error)

    def test_D_bad_material_map_in_revision_blocks_no_artifacts_no_build(self):
        with tempfile.TemporaryDirectory() as d:
            needs, ids = _needs([("optional", False, None)])
            decisions = [_dec("d1", ids[0], "script_rewrite", target_segment=1,
                              patch={"material_fit": {"visual_desc": "REVISED"}})]
            # a declared but bad-shaped material_map (numeric) on a db entry
            db = {"files": [{"path": "a.mp4", "material_map": 123}]}
            result, calls = _Harness(d).write(
                segments=[_seg(1, [ids[0]]), _seg(2, [ids[0]])],
                needs=needs, decisions=decisions, material_db=db).run()
            self.assertEqual(result["stage"], "material_revision")
            self.assertFalse(calls["mv"])
            self.assertFalse((Path(d) / "out" / "revised_segment_contract.json").exists())
            self.assertFalse((Path(d) / "out" / "material_revision.json").exists())


if __name__ == "__main__":
    unittest.main()
