import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.human_transcript_review_decision import (
    build_human_transcript_review_decision,
    write_human_transcript_review_decision_for_run,
)


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "write_human_transcript_review_decision.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _v2_run_and_payload(root: Path) -> dict:
    source = root / "IMG_2145.MOV"
    source.write_bytes(b"verified source media")
    draft = root / "subtitles.draft.srt"
    draft.write_text("1\n00:00:00,000 --> 00:00:02,000\napproved draft\n", encoding="utf-8")
    return {
        "decision": "approved",
        "reviewer": "human",
        "reviewed_draft": draft.name,
        "reviewed_cue_ids": ["cue01"],
        "source_binding": {
            "source_path": str(source),
            "source_relative_path": "主任勉勵/IMG_2145.MOV",
            "source_sha256": _sha256(source),
            "window_start_sec": 0.0,
            "window_end_sec": 39.34,
        },
        "approved_cues": [
            {"cue_id": "cue01", "start_sec": 0.0, "end_sec": 2.0, "approved_text": "approved text"},
        ],
    }


class HumanTranscriptReviewDecisionV2Test(unittest.TestCase):
    def test_v2_writer_binds_source_approved_cues_and_reviewed_draft(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload = _v2_run_and_payload(root)

            result = write_human_transcript_review_decision_for_run(root, payload)

            self.assertEqual(result["version"], 2)
            self.assertEqual(result["source_binding"]["source_sha256"], payload["source_binding"]["source_sha256"])
            self.assertEqual(result["approved_cues"], payload["approved_cues"])
            self.assertEqual(result["reviewed_cue_ids"], ["cue01"])
            self.assertEqual(result["reviewed_draft_sha256"], _sha256(root / "subtitles.draft.srt"))
            stored = json.loads((root / "human_transcript_review_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["version"], 2)

    def test_v2_partial_or_invalid_binding_fails_closed(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = _v2_run_and_payload(root)
            cases = {
                "partial": {key: value for key, value in base.items() if key != "approved_cues"},
                "non_human": {**base, "reviewer": "agent"},
                "bad_source_hash": {**base, "source_binding": {**base["source_binding"], "source_sha256": "not-a-sha"}},
                "outside_window": {**base, "approved_cues": [{**base["approved_cues"][0], "end_sec": 39.35}]},
                "duplicate_cue": {**base, "approved_cues": [*base["approved_cues"], base["approved_cues"][0]]},
                "blank_approved_text": {**base, "approved_cues": [{**base["approved_cues"][0], "approved_text": "  "}]},
            }

            for label, payload in cases.items():
                with self.subTest(label=label):
                    with self.assertRaises(ValueError):
                        build_human_transcript_review_decision(payload)

    def test_v2_source_and_reviewed_draft_hash_mismatch_fail_at_write_time(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            base = _v2_run_and_payload(root)
            cases = {
                "source": {**base, "source_binding": {**base["source_binding"], "source_sha256": "0" * 64}},
                "draft": {**base, "reviewed_draft_sha256": "0" * 64},
            }

            for label, payload in cases.items():
                with self.subTest(label=label):
                    with self.assertRaises(ValueError):
                        write_human_transcript_review_decision_for_run(root, payload, out_name=f"{label}.json")
                    self.assertFalse((root / f"{label}.json").exists())

    def test_v1_callers_remain_compatible_when_no_v2_fields_are_supplied(self):
        result = build_human_transcript_review_decision(
            {
                "decision": "approved",
                "reviewer": "human",
                "reviewed_draft": "subtitles.draft.srt",
                "reviewed_cue_ids": ["cue01"],
            }
        )

        self.assertEqual(result["version"], 1)
        self.assertEqual(result["reviewed_cue_ids"], ["cue01"])

    def test_payload_file_writes_a_v2_decision_through_the_existing_writer(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            payload_path = root / "owner_payload.json"
            payload_path.write_text(json.dumps(_v2_run_and_payload(root), ensure_ascii=False), encoding="utf-8")

            proc = subprocess.run(
                [sys.executable, str(TOOL), "--run", str(root), "--payload-file", str(payload_path), "--json"],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            stored = json.loads((root / "human_transcript_review_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["version"], 2)

    def test_legacy_cli_flags_remain_compatible(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)

            proc = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--run",
                    str(root),
                    "--decision",
                    "approved",
                    "--reviewer",
                    "human",
                    "--reviewed-cue-id",
                    "cue01",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 0, proc.stderr)
            stored = json.loads((root / "human_transcript_review_decision.json").read_text(encoding="utf-8"))
            self.assertEqual(stored["version"], 1)


if __name__ == "__main__":
    unittest.main()
