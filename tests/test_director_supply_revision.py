import json
import tempfile
import types
import unittest
from pathlib import Path

from video_tools import cmd_director_supply_revise


class DirectorSupplyRevisionTest(unittest.TestCase):
    def test_shorten_overreach_segments_to_honest_supply_duration(self):
        root = Path(tempfile.mkdtemp())
        contract = {
            "material_needs_ref": "material_needs.json",
            "segments": [
                {"segment": 1, "requested_duration_sec": 12, "label": "opening"},
                {"segment": 2, "requested_duration_sec": 12, "label": "arrival"},
                {"segment": 3, "requested_duration_sec": 18, "label": "training"},
            ],
        }
        supply = {
            "artifact_role": "supply_review",
            "segments": [
                {"segment": 1, "requested_duration_sec": 12, "max_honest_duration_sec": 12,
                 "action": "ok"},
                {"segment": 2, "requested_duration_sec": 12, "max_honest_duration_sec": 6,
                 "action": "shorten_or_merge"},
                {"segment": 3, "requested_duration_sec": 18, "max_honest_duration_sec": 6,
                 "action": "shorten_or_merge"},
            ],
        }
        contract_path = root / "segment_contract.json"
        supply_path = root / "supply_review.json"
        out_contract = root / "segment_contract.revised.json"
        out_report = root / "director_supply_revision.json"
        contract_path.write_text(json.dumps(contract), encoding="utf-8")
        supply_path.write_text(json.dumps(supply), encoding="utf-8")

        result = cmd_director_supply_revise(types.SimpleNamespace(
            contract=str(contract_path),
            supply_review=str(supply_path),
            out_contract=str(out_contract),
            out_report=str(out_report),
        ))

        revised = json.loads(out_contract.read_text(encoding="utf-8"))
        self.assertTrue(result["ok"])
        self.assertEqual(result["updated_segments"], [2, 3])
        self.assertEqual(revised["segments"][0]["requested_duration_sec"], 12)
        self.assertEqual(revised["segments"][1]["requested_duration_sec"], 6)
        self.assertEqual(revised["segments"][2]["requested_duration_sec"], 6)
        self.assertEqual(revised["segments"][1]["director_revision"]["reason"],
                         "script_overreach")
        report = json.loads(out_report.read_text(encoding="utf-8"))
        self.assertEqual(report["artifact_role"], "director_supply_revision")
        self.assertEqual(len(report["changes"]), 2)


if __name__ == "__main__":
    unittest.main()
