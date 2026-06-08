import json
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core import blueprint


def _bp(beats=("B1", "B2", "B3")):
    return {
        "thesis": "A quiet morning, done with care, is a small complete thing.",
        "intended_feeling": "warm",
        "beats": [{"id": b, "role": "develop", "summary": f"beat {b}"} for b in beats],
    }


def _contract(refs_by_seg):
    """refs_by_seg: {segment_id: blueprint_ref value}. None => no ref (orphan)."""
    segs = []
    for sid, ref in refs_by_seg.items():
        core = {"story_purpose": "x"}
        if ref is not None:
            core["blueprint_ref"] = ref
        segs.append({"segment": sid, "core": core})
    return {"segments": segs}


class ValidateBlueprintTests(unittest.TestCase):
    def test_ok(self):
        self.assertTrue(blueprint.validate_blueprint(_bp())["ok"])

    def test_missing_thesis(self):
        bp = _bp()
        bp["thesis"] = ""
        v = blueprint.validate_blueprint(bp)
        self.assertFalse(v["ok"])
        self.assertTrue(any("thesis" in e for e in v["errors"]))

    def test_no_beats(self):
        bp = _bp()
        bp["beats"] = []
        self.assertFalse(blueprint.validate_blueprint(bp)["ok"])

    def test_beat_missing_id(self):
        bp = _bp()
        bp["beats"].append({"role": "resolve"})
        self.assertFalse(blueprint.validate_blueprint(bp)["ok"])

    def test_duplicate_beat_id(self):
        bp = _bp(("B1", "B1"))
        v = blueprint.validate_blueprint(bp)
        self.assertFalse(v["ok"])
        self.assertTrue(any("重複" in e for e in v["errors"]))

    def test_not_dict(self):
        self.assertFalse(blueprint.validate_blueprint(["nope"])["ok"])


class BeatCoverageTests(unittest.TestCase):
    def test_all_realized_passes(self):
        contract = _contract({1: "B1", 2: ["B2", "B3"]})
        r = blueprint.beat_coverage(_bp(), contract)
        self.assertTrue(r["pass"])
        self.assertEqual(r["dropped"], [])
        self.assertEqual(sorted(r["realized"]), ["B1", "B2", "B3"])
        self.assertEqual(r["next_action"], None)

    def test_dropped_beat_blocks(self):
        contract = _contract({1: "B1", 2: "B2"})  # B3 never realized
        r = blueprint.beat_coverage(_bp(), contract)
        self.assertFalse(r["pass"])
        self.assertIn("B3", r["dropped"])
        self.assertTrue(any(f["check"] == "dropped_beat" and f["level"] == "error"
                            for f in r["findings"]))
        self.assertEqual(r["next_action"], "revise:director")

    def test_invalid_ref_blocks(self):
        contract = _contract({1: "B1", 2: "B2", 3: "BX"})  # BX not a real beat
        r = blueprint.beat_coverage(_bp(), contract)
        self.assertFalse(r["pass"])
        self.assertEqual(r["invalid_refs"], [{"segment": 3, "ref": "BX"}])

    def test_orphan_segment_warns_not_blocks(self):
        # all beats realized, but seg 9 serves nothing -> warn, still passes
        contract = _contract({1: "B1", 2: "B2", 3: "B3", 9: None})
        r = blueprint.beat_coverage(_bp(), contract)
        self.assertTrue(r["pass"])
        self.assertIn(9, r["orphan_segments"])
        self.assertTrue(any(f["check"] == "orphan_segment" and f["level"] == "warn"
                            for f in r["findings"]))

    def test_contract_as_list(self):
        contract = [{"segment": 1, "core": {"blueprint_ref": ["B1", "B2", "B3"]}}]
        r = blueprint.beat_coverage(_bp(), contract)
        self.assertTrue(r["pass"])

    def test_string_ref_normalized(self):
        contract = _contract({1: "B1", 2: "B2", 3: "B3"})
        r = blueprint.beat_coverage(_bp(), contract)
        self.assertTrue(r["pass"])

    def test_write_artifact(self):
        contract = _contract({1: "B1", 2: "B2", 3: "B3"})
        with tempfile.TemporaryDirectory() as d:
            out = Path(d) / "blueprint_coverage.json"
            r = blueprint.write_blueprint_coverage(_bp(), contract, out)
            self.assertTrue(out.exists())
            on_disk = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(on_disk["pass"], r["pass"])
            self.assertEqual(on_disk["artifact_role"], "blueprint_coverage")


class CheckRunTests(unittest.TestCase):
    def _write_run(self, d, bp=None, contract=None):
        if bp is not None:
            (Path(d) / "blueprint.json").write_text(json.dumps(bp), encoding="utf-8")
        if contract is not None:
            (Path(d) / "segment_contract.json").write_text(json.dumps(contract), encoding="utf-8")

    def test_inert_when_no_blueprint(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_run(d, contract=_contract({1: "B1"}))
            self.assertIsNone(blueprint.check_run(d))

    def test_pass_writes_artifact(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_run(d, bp=_bp(), contract=_contract({1: "B1", 2: "B2", 3: "B3"}))
            r = blueprint.check_run(d)
            self.assertTrue(r["pass"])
            self.assertTrue((Path(d) / "blueprint_coverage.json").exists())

    def test_dropped_beat_blocks_run(self):
        with tempfile.TemporaryDirectory() as d:
            self._write_run(d, bp=_bp(), contract=_contract({1: "B1", 2: "B2"}))  # B3 dropped
            r = blueprint.check_run(d)
            self.assertFalse(r["pass"])
            self.assertIn("B3", r["dropped"])

    def test_invalid_blueprint_blocks(self):
        with tempfile.TemporaryDirectory() as d:
            bad = _bp()
            bad["thesis"] = ""
            self._write_run(d, bp=bad, contract=_contract({1: "B1"}))
            r = blueprint.check_run(d)
            self.assertFalse(r["pass"])
            self.assertEqual(r["stage"], "validate_blueprint")


if __name__ == "__main__":
    unittest.main()
