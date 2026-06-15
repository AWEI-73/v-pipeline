"""M6b pre-BUILD material-delta gate tests.

The gate makes material_delta a real BUILD-blocking dependency: a build may run
only when delta.ok AND delta.ready_for_build. It lives in contract_adapter.run_contract,
AFTER spec_review and BEFORE any render. Existing-material-first projects (no
declared material_needs) skip it. Verdict is computed fresh from current inputs —
never a stale material_delta.json.
"""
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from video_pipeline_core import contract_adapter as ca
from video_pipeline_core import material_delta as md
from video_pipeline_core.material_needs import (
    apply_satisfaction_verdict, migrate_material_needs,
)

EXAMPLES = Path(__file__).resolve().parent.parent / "examples"


def _needs(*specs):
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


def _map(need_id, status="accepted"):
    m = {"asset_id": "clip-a", "source": "a.mp4",
         "scenes": [{"start": 0, "end": 3, "caption": "c"}]}
    apply_satisfaction_verdict(
        m, {"reviewer": "agent", "scenes": [
            {"scene_index": 0, "satisfies": [{"need_id": need_id, "status": status}]}]},
        valid_need_ids={need_id})
    return [m]


# ── gate verdict unit tests (B-H) ──────────────────────────────────────────
class GateVerdictTest(unittest.TestCase):
    def test_B_all_covered_passes(self):
        needs = _needs(("hero", 1, True, None))
        gate = md.material_delta_gate(needs, _map(_first_id(needs)))
        self.assertEqual(gate["status"], "pass")
        self.assertTrue(gate["ok"] and gate["ready_for_build"])
        self.assertIsNone(gate["route"])

    def test_C_must_have_missing_no_fallback_blocks(self):
        needs = _needs(("hero", 1, True, None))
        gate = md.material_delta_gate(needs, [])
        self.assertEqual(gate["status"], "block")
        self.assertTrue(gate["ok"])                       # delta computed fine...
        self.assertFalse(gate["ready_for_build"])         # ...but not ready
        self.assertEqual(gate["blocking_need_ids"], [_first_id(needs)])
        self.assertEqual(gate["route"], "await_material")
        self.assertEqual(gate["next_action"], "await_material")

    def test_D_must_have_with_fallback_does_not_block_on_tier1(self):
        needs = _needs(("hero", 1, True, ["reshoot", "stock"]))
        gate = md.material_delta_gate(needs, [])
        self.assertEqual(gate["status"], "pass")          # tier-2, not a tier-1 block
        self.assertTrue(gate["ready_for_build"])

    def test_E_broken_satisfies_edge_blocks_as_fix_not_missing(self):
        needs = _needs(("hero", 1, True, None))
        maps = [{"asset_id": "a", "source": "a.mp4", "scenes": [
            {"start": 0, "end": 2, "satisfies": [{"need_id": "nd_ghost", "status": "accepted"}]}]}]
        gate = md.material_delta_gate(needs, maps)
        self.assertEqual(gate["status"], "block")
        self.assertFalse(gate["ok"])                      # broken join, not "missing"
        self.assertEqual(gate["route"], "fix_material_map_or_needs")
        self.assertEqual(gate["blocking_need_ids"], [])

    def test_F_resolution_error_blocks(self):
        gate = md.material_delta_gate(
            None, None, resolution_error="material_needs_ref declared but file not found: x")
        self.assertEqual(gate["status"], "block")
        self.assertFalse(gate["ok"])
        self.assertEqual(gate["route"], "fix_material_map_or_needs")
        self.assertIsNone(gate["delta"])

    def test_G_invalid_asset_identity_blocks(self):
        needs = _needs(("hero", 1, False, None))   # optional -> would pass if maps clean
        dup = [{"asset_id": "dup", "source": "a.mp4", "scenes": []},
               {"asset_id": "dup", "source": "b.mp4", "scenes": []}]
        gate = md.material_delta_gate(needs, dup)
        self.assertEqual(gate["status"], "block")
        self.assertFalse(gate["ok"])
        self.assertEqual(gate["route"], "fix_material_map_or_needs")

    def test_fail_closed_requires_both_ok_and_ready(self):
        # a blocked delta must never be allowed by checking blocks_ready_for_build alone
        needs = _needs(("hero", 1, True, None))
        gate = md.material_delta_gate(needs, [])
        allowed = gate["ok"] and gate["ready_for_build"]
        self.assertFalse(allowed)
        self.assertEqual(gate["status"], "block")


# ── run_contract integration (A, F, G, H, I, J) ────────────────────────────
def _fake_music_structure(audio_path, out_path, **_kw):
    Path(out_path).write_text(json.dumps({"source_audio": str(audio_path)}), encoding="utf-8")
    return {"ok": True, "music_structure": str(out_path)}


class GateIntegrationTest(unittest.TestCase):
    def _setup(self, d, *, needs_ref=True, needs_payload=None, material_db=None):
        d = Path(d)
        contract = json.loads((EXAMPLES / "segment_contract_graduation_mv.json")
                              .read_text(encoding="utf-8"))
        if needs_ref:
            contract["material_needs_ref"] = "material_needs.json"
        contract_path = d / "contract.json"
        contract_path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
        if needs_payload is not None:
            (d / "material_needs.json").write_text(
                json.dumps(needs_payload, ensure_ascii=False), encoding="utf-8")
        db_path = d / "material_db.json"
        db_path.write_text(json.dumps(material_db or {"files": []}), encoding="utf-8")
        music = d / "bgm.mp3"
        music.write_bytes(b"fake")
        return contract_path, db_path, music

    def _run(self, contract_path, db_path, music, outdir):
        calls = {"mv": False}

        def fake_mv_chain(script, material_db_arg, out_path, music_path=None,
                          mat_dir="/tmp", verbose=True, **kwargs):
            calls["mv"] = True
            Path(out_path).write_bytes(b"mp4")
            state = Path(out_path).parent / "state.json"
            state.write_text(json.dumps({"final": str(out_path), "next_action": None}),
                             encoding="utf-8")
            return {"final": str(out_path), "state": str(state),
                    "plan": [{"segment": 1, "source": "a.mp4", "extract_start": 0,
                              "extract_dur": 1.5, "slot_index": 0, "slot_dur": 1.5}]}

        with patch("video_pipeline_core.mv_cut.mv_chain", fake_mv_chain), \
             patch("video_pipeline_core.music_structure.write_music_structure", _fake_music_structure):
            result = ca.run_contract(
                contract_path, material_db=db_path, out_path=outdir / "final.mp4",
                music_path=music, categories_path=EXAMPLES / "material_categories.json",
                mat_dir=outdir, verbose=False)
        return result, calls["mv"]

    def test_A_no_material_needs_runs_existing_flow(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            contract_path, db, music = self._setup(d, needs_ref=False)
            result, mv_called = self._run(contract_path, db, music, outdir)
            self.assertTrue(mv_called)                    # gate skipped -> build runs
            self.assertNotEqual(result.get("stage"), "material_delta")

    def test_I_tier1_block_stops_before_render(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            needs = _needs(("the mandatory hero", 1, True, None))
            contract_path, db, music = self._setup(d, needs_payload=needs)
            result, mv_called = self._run(contract_path, db, music, outdir)
            self.assertEqual(result["stage"], "material_delta")
            self.assertFalse(mv_called)                   # render NOT called
            self.assertFalse((outdir / "final.mp4").exists())   # no final video
            self.assertEqual(result["next_action"], "await_material")
            self.assertTrue(result["blocking_need_ids"])
            self.assertTrue((outdir / "material_delta.json").exists())   # evidence

    def test_J_gate_pass_allows_render(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            needs = _needs(("optional broll", 1, False, None))   # ready_for_build
            contract_path, db, music = self._setup(d, needs_payload=needs)
            result, mv_called = self._run(contract_path, db, music, outdir)
            self.assertTrue(mv_called)                    # gate passed -> render ran
            self.assertNotEqual(result.get("stage"), "material_delta")

    def test_F_declared_needs_file_missing_fails_closed(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            # needs_ref declared but the file is NOT written
            contract_path, db, music = self._setup(d, needs_payload=None)
            result, mv_called = self._run(contract_path, db, music, outdir)
            self.assertEqual(result["stage"], "material_delta")
            self.assertFalse(mv_called)
            self.assertEqual(result["route"], "fix_material_map_or_needs")

    def test_G_corrupt_material_map_blocks_when_needs_declared(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            needs = _needs(("optional broll", 1, False, None))
            bad_map = Path(d) / "missing.map.json"   # declared but does not exist
            db = {"files": [{"path": "a.mp4", "material_map": str(bad_map)}]}
            contract_path, db_path, music = self._setup(d, needs_payload=needs, material_db=db)
            result, mv_called = self._run(contract_path, db_path, music, outdir)
            # the unified loader now fail-closes the corrupt map at supply-review
            # (stage material_map), earlier than the delta gate — still blocked,
            # still no render.
            self.assertIn(result["stage"], ("material_map", "material_delta"))
            self.assertFalse(mv_called)
            self.assertFalse((outdir / "final.mp4").exists())

    def test_H_stale_material_delta_artifact_is_ignored(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            outdir.mkdir(parents=True, exist_ok=True)
            # a stale artifact claiming the build is ready
            (outdir / "material_delta.json").write_text(
                json.dumps({"ok": True, "ready_for_build": True, "deltas": []}),
                encoding="utf-8")
            needs = _needs(("the mandatory hero", 1, True, None))   # current input blocks
            contract_path, db, music = self._setup(d, needs_payload=needs)
            result, mv_called = self._run(contract_path, db, music, outdir)
            self.assertEqual(result["stage"], "material_delta")     # current input wins
            self.assertFalse(mv_called)
            fresh = json.loads((outdir / "material_delta.json").read_text(encoding="utf-8"))
            self.assertFalse(fresh["ready_for_build"])              # overwritten with truth


class FinalHardeningTest(unittest.TestCase):
    def test_A_block_quarantines_preexisting_final(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / "final.mp4").write_bytes(b"OLD-GOOD-RENDER")   # previous build
            needs = _needs(("the mandatory hero", 1, True, None))     # current input blocks
            contract_path, db, music = GateIntegrationTest()._setup(d, needs_payload=needs)
            result, mv_called = GateIntegrationTest()._run(contract_path, db, music, outdir)
            self.assertEqual(result["stage"], "material_delta")
            self.assertFalse(mv_called)
            # the old final no longer sits at the canonical path
            self.assertFalse((outdir / "final.mp4").exists())
            stale = outdir / "stale_previous_final.mp4"
            self.assertTrue(stale.exists())
            self.assertEqual(stale.read_bytes(), b"OLD-GOOD-RENDER")   # preserved, not deleted
            self.assertEqual(result["stale_final_path"], str(stale))
            state = json.loads((outdir / "state.json").read_text(encoding="utf-8"))
            self.assertIsNone(state["final"])                         # not claimed as output
            self.assertEqual(state["stale_final_path"], str(stale))

    def test_B_malformed_material_needs_ref_fails_closed_without_crash(self):
        with tempfile.TemporaryDirectory() as d:
            for bad in ("", "   ", 123, [], {}):
                gate = ca._run_material_delta_gate(
                    {"material_needs_ref": bad}, source=None, out_dir=d,
                    material_db=str(Path(d) / "material_db.json"),
                    material_db_payload={"files": []})
                self.assertIsNotNone(gate, bad)               # declared -> not skipped
                self.assertEqual(gate["status"], "block", bad)
                self.assertFalse(gate["ok"], bad)

    def test_E_absent_key_still_skips(self):
        gate = ca._run_material_delta_gate(
            {}, source=None, out_dir=tempfile.gettempdir(),
            material_db="material_db.json", material_db_payload={"files": []})
        self.assertIsNone(gate)                               # existing-material-first

    def test_C_relative_map_path_resolves_against_db_dir_not_cwd(self):
        import os
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "clip.map.json").write_text(json.dumps(
                {"asset_id": "clip-a", "source": "a.mp4",
                 "scenes": [{"start": 0, "end": 3, "caption": "c"}]}), encoding="utf-8")
            db = d / "material_db.json"
            db.write_text(json.dumps({"files": [{"path": "a.mp4", "material_map": "clip.map.json"}]}),
                          encoding="utf-8")
            needs = _needs(("optional broll", 1, False, None))   # would be ready if maps resolve
            (d / "material_needs.json").write_text(json.dumps(needs, ensure_ascii=False),
                                                   encoding="utf-8")
            contract = {"material_needs_ref": "material_needs.json"}
            cwd = os.getcwd()
            other = tempfile.mkdtemp()
            try:
                os.chdir(other)         # cwd that knows nothing about clip.map.json
                gate = ca._run_material_delta_gate(
                    contract, source=str(d / "contract.json"), out_dir=str(d),
                    material_db=str(db),
                    material_db_payload=json.loads(db.read_text(encoding="utf-8")))
            finally:
                os.chdir(cwd)
            self.assertEqual(gate["status"], "pass")           # map resolved via db dir
            self.assertNotIn("not found", gate["reason"])

    def test_D_unresolvable_relative_map_path_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            db = d / "material_db.json"
            db.write_text(json.dumps({"files": [{"path": "a.mp4", "material_map": "nope.map.json"}]}),
                          encoding="utf-8")
            needs = _needs(("optional broll", 1, False, None))
            (d / "material_needs.json").write_text(json.dumps(needs, ensure_ascii=False),
                                                   encoding="utf-8")
            gate = ca._run_material_delta_gate(
                {"material_needs_ref": "material_needs.json"},
                source=str(d / "contract.json"), out_dir=str(d), material_db=str(db),
                material_db_payload=json.loads(db.read_text(encoding="utf-8")))
            self.assertEqual(gate["status"], "block")
            self.assertEqual(gate["route"], "fix_material_map_or_needs")


class QuarantineIdentityTest(unittest.TestCase):
    def test_does_not_overwrite_existing_stale(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "final.mp4").write_bytes(b"CURRENT-OLD")
            (d / "stale_previous_final.mp4").write_bytes(b"EARLIER-OLD")   # pre-existing
            path, err = ca._quarantine_stale_final(d / "final.mp4")
            self.assertIsNone(err)
            self.assertEqual(path, str(d / "stale_previous_final_2.mp4"))
            self.assertEqual((d / "stale_previous_final.mp4").read_bytes(), b"EARLIER-OLD")  # untouched
            self.assertEqual(Path(path).read_bytes(), b"CURRENT-OLD")       # both preserved
            self.assertFalse((d / "final.mp4").exists())

    def test_three_consecutive_quarantines_keep_all(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            produced = []
            for content in (b"R1", b"R2", b"R3"):
                (d / "final.mp4").write_bytes(content)
                path, err = ca._quarantine_stale_final(d / "final.mp4")
                self.assertIsNone(err)
                produced.append((path, content))
            names = {Path(p).name for p, _ in produced}
            self.assertEqual(names, {"stale_previous_final.mp4",
                                     "stale_previous_final_2.mp4",
                                     "stale_previous_final_3.mp4"})
            for path, content in produced:          # nothing overwritten
                self.assertEqual(Path(path).read_bytes(), content)

    def test_move_failure_reports_error_and_preserves_final(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "final.mp4").write_bytes(b"CURRENT-OLD")
            with patch.object(ca.Path, "replace", side_effect=OSError("disk on fire")):
                path, err = ca._quarantine_stale_final(d / "final.mp4")
            self.assertIsNone(path)
            self.assertIn("disk on fire", err)
            self.assertTrue((d / "final.mp4").exists())   # not moved, not lost

    def test_block_with_quarantine_failure_does_not_claim_cleared(self):
        with tempfile.TemporaryDirectory() as d:
            outdir = Path(d) / "out"
            outdir.mkdir(parents=True, exist_ok=True)
            (outdir / "final.mp4").write_bytes(b"OLD")
            needs = _needs(("the mandatory hero", 1, True, None))
            contract_path, db, music = GateIntegrationTest()._setup(d, needs_payload=needs)
            with patch("video_pipeline_core.contract_adapter._quarantine_stale_final",
                       return_value=(None, "boom")):
                result, mv_called = GateIntegrationTest()._run(contract_path, db, music, outdir)
            self.assertEqual(result["stage"], "material_delta")    # still blocked
            self.assertFalse(mv_called)
            self.assertEqual(result["quarantine_error"], "boom")
            self.assertFalse(result["canonical_final_cleared"])    # never claim cleared
            state = json.loads((outdir / "state.json").read_text(encoding="utf-8"))
            self.assertEqual(state["quarantine_error"], "boom")
            self.assertFalse(state["canonical_final_cleared"])


if __name__ == "__main__":
    unittest.main()
