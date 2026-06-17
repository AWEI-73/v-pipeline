import json
import tempfile
import unittest
from pathlib import Path

from tools.workbench_handoff import build_handoff


def _write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")


class WorkbenchHandoffTest(unittest.TestCase):
    def test_handoff_records_draft_artifact_hashes_and_sizes(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            timeline_patch = {
                "artifact_role": "timeline_patch",
                "version": 1,
                "patches": [{"op": "set_duration"}],
            }
            _write(root / "timeline_patch.json", timeline_patch)
            _write(root / "patched_draft_timeline.json", {"plan": []})

            handoff = build_handoff(str(root))

        self.assertEqual(handoff["artifact_role"], "workbench_handoff")
        self.assertIn("timeline_patch", handoff["artifacts"])
        self.assertEqual(handoff["artifacts"]["timeline_patch"], "timeline_patch.json")
        detail = handoff["artifact_details"]["timeline_patch"]
        self.assertEqual(detail["path"], "timeline_patch.json")
        self.assertGreater(detail["size_bytes"], 0)
        self.assertRegex(detail["sha256"], r"^[0-9a-f]{64}$")
        self.assertEqual(handoff["summary"]["timeline_edits"], 1)

    def test_handoff_ignores_canonical_artifacts(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write(root / "timeline.json", {"canonical": True})
            _write(root / "final.mp4", {"not": "real video"})
            handoff = build_handoff(str(root))

        self.assertEqual(handoff["artifacts"], {})
        self.assertEqual(handoff["artifact_details"], {})
        self.assertEqual(handoff["summary"]["timeline_edits"], 0)


if __name__ == "__main__":
    unittest.main()

