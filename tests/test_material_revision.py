"""M6c — Delta-driven script revision tests.

M6c applies ONLY accepted human/director decisions to a COPY of the contract,
deterministically, with lineage. It never invents content, never mutates the
original, and a tier-1 must_have block is released only by an explicit waiver.
"""
import copy
import unittest

from video_pipeline_core import material_revision as mr
from video_pipeline_core.spec_contract import validate_segment_contract


def _seg(num, *, need_refs=None, **over):
    seg = {
        "segment": num,
        "core": {"section_role": "montage", "story_purpose": "p", "timeline_source": "beat"},
        "material_fit": {"visual_desc": f"desc {num}", "reason": "r"},
        "audio": {"role": "music", "reason": "r"},
        "visual_style": {"layout": "montage", "pace": "fast", "reason": "r"},
        "text_layer": "none",
    }
    if need_refs is not None:
        seg["material_fit"]["need_refs"] = need_refs
    for k, v in over.items():
        seg[k] = v
    return seg


def _contract(*segs):
    return {"segments": list(segs)}


def _delta(need_id, outcome, *, route="collect_material", tier=2,
           blocks=False, must_have=False):
    return {"artifact_role": "material_delta", "version": 1, "ok": True,
            "ready_for_build": not blocks, "blocks_ready_for_build": blocks,
            "deltas": [{"need_id": need_id, "outcome": outcome, "tier": tier,
                        "route": route, "blocks_ready_for_build": blocks,
                        "reason": "r", "evidence": {"must_have": must_have,
                                                    "required_count": 1, "accepted": 0,
                                                    "candidate": 0, "rejected": 0}}],
            "summary": {outcome: 1}}


def _lineage():
    return {"reviewer": "director", "reason": "ok by review", "at": "2026-06-15T10:00:00"}


def _dec(decision_id, need_id, route, status="accepted", **over):
    d = {"decision_id": decision_id, "need_id": need_id, "route": route,
         "status": status, "lineage": _lineage()}
    d.update(over)
    return d


class NoOpAndRejectTest(unittest.TestCase):
    def test_A_no_accepted_decision_is_no_op_identical_contract(self):
        contract = _contract(_seg(1, need_refs=["nd_x"]))
        delta = _delta("nd_x", "thin")
        report, revised = mr.apply_revisions(contract, delta, [])
        self.assertTrue(report["ok"])
        self.assertTrue(report["no_op"])
        self.assertEqual(report["before_contract_hash"], report["after_contract_hash"])
        self.assertEqual(revised, contract)

    def test_B_rejected_decision_does_not_change_contract(self):
        contract = _contract(_seg(1, need_refs=["nd_x"]))
        delta = _delta("nd_x", "excess", route="shorten_or_merge")
        dec = _dec("d1", "nd_x", "shorten_or_merge", status="rejected",
                   target_segment=1, patch={"requested_duration_sec": 2.0})
        report, revised = mr.apply_revisions(contract, delta, [dec])
        self.assertTrue(report["ok"])
        self.assertEqual(report["after_contract_hash"], report["before_contract_hash"])
        self.assertEqual(report["decisions"][0]["status"], "rejected")


class NonModifyingRouteTest(unittest.TestCase):
    def test_C_collect_reshoot_review_do_not_change_contract(self):
        for route, expect_action in (("collect_material", "await_material"),
                                     ("reshoot", "await_material"),
                                     ("dashboard_review", "await_review")):
            outcome = "missing" if route != "dashboard_review" else "thin"
            contract = _contract(_seg(1, need_refs=["nd_x"]))
            delta = _delta("nd_x", outcome, route=route,
                           tier=(1 if route == "reshoot" else 2),
                           blocks=False, must_have=(route == "reshoot"))
            dec = _dec("d1", "nd_x", route)
            report, revised = mr.apply_revisions(contract, delta, [dec])
            self.assertTrue(report["ok"], report["errors"])
            self.assertEqual(revised, contract)                       # unchanged
            self.assertEqual(report["decisions"][0]["status"], "blocked")
            self.assertEqual(report["next_action"], expect_action)


class ModifyingRouteTest(unittest.TestCase):
    def test_D_shorten_only_touches_target_and_keeps_need_refs(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))
        delta = _delta("nd_b", "excess", route="shorten_or_merge")
        dec = _dec("d1", "nd_b", "shorten_or_merge", target_segment=2,
                   patch={"requested_duration_sec": 2.5})
        report, revised = mr.apply_revisions(contract, delta, [dec])
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(revised["segments"][1]["requested_duration_sec"], 2.5)
        self.assertEqual(revised["segments"][1]["material_fit"]["need_refs"], ["nd_b"])
        self.assertNotIn("requested_duration_sec", revised["segments"][0])   # other seg untouched
        self.assertEqual(revised["segments"][1]["revision_lineage"][0]["decision_id"], "d1")

    def test_E_script_rewrite_applies_only_explicit_patch(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]))
        delta = _delta("nd_a", "thin", route="script_rewrite")
        dec = _dec("d1", "nd_a", "script_rewrite", target_segment=1,
                   patch={"material_fit": {"visual_desc": "rewritten desc"}})
        report, revised = mr.apply_revisions(contract, delta, [dec])
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(revised["segments"][0]["material_fit"]["visual_desc"], "rewritten desc")
        self.assertEqual(revised["segments"][0]["material_fit"]["need_refs"], ["nd_a"])  # preserved
        self.assertEqual(revised["segments"][0]["material_fit"]["reason"], "r")          # untouched

    def test_F_drop_optional_ok_drop_must_have_without_waiver_fails(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))
        # optional drop ok
        delta_opt = _delta("nd_b", "thin", route="drop_segment", must_have=False)
        ok, revised = mr.apply_revisions(
            contract, delta_opt, [_dec("d1", "nd_b", "drop_segment", target_segment=2)])
        self.assertTrue(ok["ok"], ok["errors"])
        self.assertEqual(len(revised["segments"]), 1)
        # must_have drop without waiver fails
        delta_must = _delta("nd_a", "thin", route="drop_segment", must_have=True)
        bad, none_revised = mr.apply_revisions(
            contract, delta_must, [_dec("d1", "nd_a", "drop_segment", target_segment=1)])
        self.assertFalse(bad["ok"])
        self.assertIsNone(none_revised)
        self.assertTrue(any("waiver" in e for e in bad["errors"]))

    def test_G_explicit_waiver_releases_block_with_lineage(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))
        delta = _delta("nd_a", "missing", route="drop_segment", tier=1,
                       blocks=True, must_have=True)
        waiver = {"reviewer": "director", "reason": "cut from final per client"}
        dec = _dec("d1", "nd_a", "drop_segment", target_segment=1, waiver=waiver)
        report, revised = mr.apply_revisions(contract, delta, [dec])
        self.assertTrue(report["ok"], report["errors"])
        self.assertEqual(len(revised["segments"]), 1)                  # seg 2 remains
        self.assertEqual(revised["segments"][0]["segment"], 2)
        self.assertEqual(report["unresolved_blocking_needs"], [])      # waived
        self.assertTrue(report["ready_for_build"])
        rec = report["decisions"][0]
        self.assertEqual(rec["status"], "applied")
        self.assertEqual(rec["affected_need_ids"], ["nd_a"])
        self.assertEqual(rec["waivers"][0]["need_id"], "nd_a")
        self.assertEqual(rec["waivers"][0]["reason"], waiver["reason"])
        # canonical waiver artifact + gate reproducibility
        self.assertEqual(report["waivers"][0]["need_id"], "nd_a")


class ValidationTest(unittest.TestCase):
    def test_H_unknown_dup_id_incompatible_route_fail(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]))
        delta = _delta("nd_a", "missing", route="reshoot", tier=1, blocks=True, must_have=True)
        # unknown need_id
        r1, _ = mr.apply_revisions(contract, delta, [_dec("d1", "nd_ghost", "reshoot")])
        self.assertFalse(r1["ok"])
        # duplicate decision_id
        r2, _ = mr.apply_revisions(contract, delta,
                                   [_dec("d1", "nd_a", "reshoot"), _dec("d1", "nd_a", "reshoot")])
        self.assertFalse(r2["ok"])
        self.assertTrue(any("duplicate" in e for e in r2["errors"]))
        # incompatible route (shorten on a missing need)
        r3, _ = mr.apply_revisions(
            contract, delta, [_dec("d1", "nd_a", "shorten_or_merge", target_segment=1,
                                   patch={"requested_duration_sec": 2.0})])
        self.assertFalse(r3["ok"])
        self.assertTrue(any("not compatible" in e for e in r3["errors"]))

    def test_I_ambiguous_or_missing_target_fails(self):
        # missing target
        contract = _contract(_seg(1, need_refs=["nd_a"]))
        delta = _delta("nd_a", "excess", route="shorten_or_merge")
        r1, _ = mr.apply_revisions(
            contract, delta, [_dec("d1", "nd_a", "shorten_or_merge",
                                   patch={"requested_duration_sec": 2.0})])
        self.assertFalse(r1["ok"])
        # ambiguous target (two segments share segment id 1)
        dup_contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(1, need_refs=["nd_a"]))
        r2, _ = mr.apply_revisions(
            dup_contract, delta, [_dec("d1", "nd_a", "shorten_or_merge", target_segment=1,
                                       patch={"requested_duration_sec": 2.0})])
        self.assertFalse(r2["ok"])
        self.assertTrue(any("ambiguous" in e for e in r2["errors"]))

    def test_J_conflicting_patches_fail_order_independent(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))
        delta = {"artifact_role": "material_delta", "version": 1, "ok": True,
                 "ready_for_build": True, "blocks_ready_for_build": False,
                 "deltas": [
                     {"need_id": "nd_a", "outcome": "thin", "tier": 2, "route": "script_rewrite",
                      "blocks_ready_for_build": False, "reason": "r",
                      "evidence": {"must_have": False}},
                     {"need_id": "nd_b", "outcome": "excess", "tier": 2, "route": "shorten_or_merge",
                      "blocks_ready_for_build": False, "reason": "r",
                      "evidence": {"must_have": False}}],
                 "summary": {}}
        d1 = _dec("d1", "nd_a", "script_rewrite", target_segment=2,
                  patch={"material_fit": {"visual_desc": "x"}})
        d2 = _dec("d2", "nd_b", "shorten_or_merge", target_segment=2,
                  patch={"requested_duration_sec": 2.0})
        r_fwd, _ = mr.apply_revisions(contract, delta, [d1, d2])
        r_rev, _ = mr.apply_revisions(contract, delta, [d2, d1])
        self.assertFalse(r_fwd["ok"])
        self.assertFalse(r_rev["ok"])
        self.assertTrue(any("conflicting" in e for e in r_fwd["errors"]))
        self.assertTrue(any("conflicting" in e for e in r_rev["errors"]))

    def test_K_patch_touching_identity_fails(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]))
        delta = _delta("nd_a", "thin", route="script_rewrite")
        for bad_patch in ({"segment": 99},
                          {"material_fit": {"need_refs": ["nd_evil"]}},
                          {"need_id": "nd_evil"},
                          {"core": {"section_role": "opening"}}):
            r, none_revised = mr.apply_revisions(
                contract, delta, [_dec("d1", "nd_a", "script_rewrite",
                                       target_segment=1, patch=bad_patch)])
            self.assertFalse(r["ok"], bad_patch)
            self.assertIsNone(none_revised)


class IntegrityTest(unittest.TestCase):
    def test_L_original_contract_never_mutated(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))
        snapshot = copy.deepcopy(contract)
        delta = _delta("nd_b", "excess", route="shorten_or_merge")
        mr.apply_revisions(contract, delta, [_dec("d1", "nd_b", "shorten_or_merge",
                                                  target_segment=2,
                                                  patch={"requested_duration_sec": 2.0})])
        self.assertEqual(contract, snapshot)        # untouched

    def test_M_revised_contract_passes_validator(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]))
        delta = _delta("nd_a", "thin", route="script_rewrite")
        _, revised = mr.apply_revisions(
            contract, delta, [_dec("d1", "nd_a", "script_rewrite", target_segment=1,
                                   patch={"material_fit": {"visual_desc": "new"}})])
        self.assertTrue(validate_segment_contract(revised)["ok"])

    def test_N_unresolved_tier1_gap_still_blocks_after_revision(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]))
        delta = _delta("nd_a", "missing", route="reshoot", tier=1, blocks=True, must_have=True)
        # accept a reshoot (no waiver) -> the tier-1 gap is NOT resolved
        report, _ = mr.apply_revisions(contract, delta, [_dec("d1", "nd_a", "reshoot")])
        self.assertTrue(report["ok"])
        self.assertEqual(report["unresolved_blocking_needs"], ["nd_a"])
        self.assertFalse(report["ready_for_build"])
        self.assertEqual(report["next_action"], "await_material")

    def test_broken_delta_forbids_revision(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]))
        broken = {"ok": False, "errors": ["bad"], "deltas": []}
        report, revised = mr.apply_revisions(contract, broken, [])
        self.assertFalse(report["ok"])
        self.assertIsNone(revised)

    def test_dropping_last_segment_fails_validation(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]))
        delta = _delta("nd_a", "thin", route="drop_segment", must_have=False)
        report, revised = mr.apply_revisions(
            contract, delta, [_dec("d1", "nd_a", "drop_segment", target_segment=1)])
        self.assertFalse(report["ok"])     # empty contract is invalid
        self.assertIsNone(revised)


class CliTest(unittest.TestCase):
    def test_O_cli_writes_both_artifacts_and_fails_closed(self):
        import json as _json
        import subprocess
        import sys
        import tempfile
        from pathlib import Path
        root = Path(__file__).resolve().parent.parent
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            (d / "contract.json").write_text(_json.dumps(
                _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))),
                encoding="utf-8")
            (d / "delta.json").write_text(_json.dumps(
                _delta("nd_b", "excess", route="shorten_or_merge")), encoding="utf-8")
            (d / "decisions.json").write_text(_json.dumps(
                [_dec("d1", "nd_b", "shorten_or_merge", target_segment=2,
                      patch={"requested_duration_sec": 2.0})]), encoding="utf-8")
            out_c, out_r = d / "revised.json", d / "revision.json"

            def run():
                return subprocess.run(
                    [sys.executable, "video_tools.py", "material-revision",
                     str(d / "contract.json"), "--delta", str(d / "delta.json"),
                     "--decisions", str(d / "decisions.json"),
                     "--out-contract", str(out_c), "--out-revision", str(out_r)],
                    cwd=root, capture_output=True, text=True)

            ok = run()
            self.assertEqual(ok.returncode, 0, ok.stderr)
            self.assertTrue(out_c.exists() and out_r.exists())

            # invalid input (unknown need_id) -> non-zero, no half-baked artifacts
            out_c.unlink(); out_r.unlink()
            (d / "decisions.json").write_text(_json.dumps(
                [_dec("d1", "nd_ghost", "shorten_or_merge", target_segment=2,
                      patch={"requested_duration_sec": 2.0})]), encoding="utf-8")
            bad = run()
            self.assertNotEqual(bad.returncode, 0)
            self.assertFalse(out_c.exists())
            self.assertFalse(out_r.exists())


class WaiverGateContractTest(unittest.TestCase):
    def test_A_waiver_ready_reproduced_by_m6b_gate(self):
        from video_pipeline_core import material_delta as md
        contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))
        delta = _delta("nd_a", "missing", route="drop_segment", tier=1,
                       blocks=True, must_have=True)
        dec = _dec("d1", "nd_a", "drop_segment", target_segment=1,
                   waiver={"reviewer": "director", "reason": "cut"})
        report, _ = mr.apply_revisions(contract, delta, [dec])
        self.assertTrue(report["ready_for_build"])
        # the M6b gate, re-run with the canonical waiver artifact, AGREES
        gate = md.gate_from_delta(delta, waivers=report["waivers"])
        self.assertEqual(gate["status"], "pass")
        self.assertEqual(gate["status"] == "pass", report["ready_for_build"])

    def test_B_no_canonical_waiver_means_no_release(self):
        from video_pipeline_core import material_delta as md
        contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))
        delta = _delta("nd_a", "missing", route="reshoot", tier=1,
                       blocks=True, must_have=True)
        report, _ = mr.apply_revisions(contract, delta, [_dec("d1", "nd_a", "reshoot")])
        self.assertEqual(report["waivers"], [])
        self.assertFalse(report["ready_for_build"])
        gate = md.gate_from_delta(delta, waivers=report["waivers"])
        self.assertEqual(gate["status"], "block")           # no contradiction


class DropProtectsAllNeedRefsTest(unittest.TestCase):
    def _delta2(self, specs):
        # specs: list of (need_id, must_have, blocks)
        return {"artifact_role": "material_delta", "version": 1, "ok": True,
                "ready_for_build": True, "blocks_ready_for_build": False,
                "deltas": [{"need_id": nid, "outcome": "thin", "tier": 2,
                            "route": "drop_segment", "blocks_ready_for_build": blk,
                            "reason": "r", "evidence": {"must_have": mh}}
                           for nid, mh, blk in specs],
                "summary": {}}

    def test_C_drop_segment_with_a_must_have_ref_needs_that_waiver(self):
        contract = _contract(_seg(1, need_refs=["nd_opt", "nd_must"]), _seg(2, need_refs=["nd_z"]))
        delta = self._delta2([("nd_opt", False, False), ("nd_must", True, False),
                              ("nd_z", False, False)])
        # decision is "about" the optional need but the segment also refs a must_have
        dec = _dec("d1", "nd_opt", "drop_segment", target_segment=1)   # no waiver for nd_must
        report, revised = mr.apply_revisions(contract, delta, [dec])
        self.assertFalse(report["ok"])
        self.assertIsNone(revised)
        self.assertTrue(any("nd_must" in e for e in report["errors"]))

    def test_D_each_must_have_ref_needs_its_own_waiver(self):
        contract = _contract(_seg(1, need_refs=["nd_m1", "nd_m2"]), _seg(2, need_refs=["nd_z"]))
        delta = self._delta2([("nd_m1", True, False), ("nd_m2", True, False),
                              ("nd_z", False, False)])
        # only one of the two must_have refs waived -> fail
        one = _dec("d1", "nd_m1", "drop_segment", target_segment=1,
                   waiver={"reviewer": "d", "reason": "r"})
        report, _ = mr.apply_revisions(contract, delta, [one])
        self.assertFalse(report["ok"])
        self.assertTrue(any("nd_m2" in e for e in report["errors"]))
        # both waived via the waivers list -> ok
        both = _dec("d2", "nd_m1", "drop_segment", target_segment=1,
                    waiver={"reviewer": "d", "reason": "r"},
                    waivers=[{"need_id": "nd_m2", "reviewer": "d", "reason": "r"}])
        report2, revised2 = mr.apply_revisions(contract, delta, [both])
        self.assertTrue(report2["ok"], report2["errors"])
        self.assertEqual(len(revised2["segments"]), 1)

    def test_E_drop_segment_referencing_unknown_need_fails(self):
        contract = _contract(_seg(1, need_refs=["nd_known", "nd_ghost"]), _seg(2, need_refs=["nd_z"]))
        delta = self._delta2([("nd_known", False, False), ("nd_z", False, False)])  # nd_ghost absent
        dec = _dec("d1", "nd_known", "drop_segment", target_segment=1)
        report, _ = mr.apply_revisions(contract, delta, [dec])
        self.assertFalse(report["ok"])
        self.assertTrue(any("nd_ghost" in e and "unknown" in e for e in report["errors"]))

    def test_F_affected_need_ids_recorded(self):
        contract = _contract(_seg(1, need_refs=["nd_a", "nd_b"]), _seg(2, need_refs=["nd_z"]))
        delta = self._delta2([("nd_a", False, False), ("nd_b", False, False),
                              ("nd_z", False, False)])
        dec = _dec("d1", "nd_a", "drop_segment", target_segment=1)
        report, _ = mr.apply_revisions(contract, delta, [dec])
        self.assertTrue(report["ok"], report["errors"])
        rec = report["decisions"][0]
        self.assertEqual(rec["affected_need_ids"], ["nd_a", "nd_b"])


class ArtifactAtomicityTest(unittest.TestCase):
    def _ok_inputs(self):
        contract = _contract(_seg(1, need_refs=["nd_a"]), _seg(2, need_refs=["nd_b"]))
        delta = _delta("nd_b", "excess", route="shorten_or_merge")
        report = {"artifact_role": "material_revision", "ok": True, "decisions": []}
        return contract, report

    def test_I_same_output_path_fails(self):
        import tempfile
        from pathlib import Path
        contract, report = self._ok_inputs()
        with tempfile.TemporaryDirectory() as d:
            p = str(Path(d) / "same.json")
            with self.assertRaises(ValueError):
                mr.write_revision_artifacts(contract, report, p, p)

    def test_G_creates_missing_parent_and_writes_both(self):
        import tempfile
        from pathlib import Path
        contract, report = self._ok_inputs()
        with tempfile.TemporaryDirectory() as d:
            out_c = Path(d) / "a" / "revised.json"
            out_r = Path(d) / "b" / "revision.json"      # parent does not exist yet
            mr.write_revision_artifacts(contract, report, out_c, out_r)
            self.assertTrue(out_c.exists() and out_r.exists())

    def test_H_second_write_failure_leaves_no_new_first_artifact(self):
        import tempfile
        from pathlib import Path
        contract, report = self._ok_inputs()
        with tempfile.TemporaryDirectory() as d:
            out_c = Path(d) / "revised.json"
            out_r = Path(d) / "revision.json"
            out_c.write_text("OLD-OFFICIAL", encoding="utf-8")   # pre-existing official

            def writer(path, text):
                if str(path).endswith("revision.json.m6c.tmp"):
                    raise OSError("disk full")
                Path(path).write_text(text, encoding="utf-8")

            with self.assertRaises(OSError):
                mr.write_revision_artifacts(contract, report, out_c, out_r, _writer=writer)
            self.assertEqual(out_c.read_text(encoding="utf-8"), "OLD-OFFICIAL")  # untouched
            self.assertFalse(out_r.exists())
            self.assertFalse((Path(d) / "revised.json.m6c.tmp").exists())   # temp cleaned
            self.assertFalse((Path(d) / "revision.json.m6c.tmp").exists())


if __name__ == "__main__":
    unittest.main()
