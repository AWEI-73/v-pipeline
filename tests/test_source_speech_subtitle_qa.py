import hashlib
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from video_pipeline_core.human_transcript_review_decision import write_human_transcript_review_decision_for_run
from video_pipeline_core.source_speech_subtitle_qa import evaluate_source_speech_subtitle_qa, write_source_speech_subtitle_qa_for_run


ROOT = Path(__file__).resolve().parents[1]
TOOL = ROOT / "tools" / "source_speech_subtitle_qa.py"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest().upper()


def _write_bound_v2_run(
    root: Path,
    actual_srt_text: str,
    evidence_text: str = "APPROVED",
    approved_text: str = "APPROVED",
) -> None:
    source = root / "IMG_2145.MOV"
    source.write_bytes(b"bound source")
    draft = root / "subtitles.draft.srt"
    draft.write_text(f"1\n00:00:00,000 --> 00:00:02,000\n{approved_text}\n", encoding="utf-8")
    source_binding = {
        "source_path": str(source),
        "source_relative_path": "主任勉勵/IMG_2145.MOV",
        "source_sha256": _sha256(source),
        "window_start_sec": 0.0,
        "window_end_sec": 2.0,
    }
    write_human_transcript_review_decision_for_run(
        root,
        {
            "decision": "approved",
            "reviewer": "human",
            "reviewed_draft": draft.name,
            "reviewed_cue_ids": ["cue01"],
            "source_binding": source_binding,
            "approved_cues": [
                {"cue_id": "cue01", "start_sec": 0.0, "end_sec": 2.0, "approved_text": approved_text},
            ],
        },
    )
    (root / "subtitles.srt").write_text(actual_srt_text, encoding="utf-8")
    (root / "source_speech_subtitle_evidence.json").write_text(
        json.dumps(
            {
                "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 0.0, "end_sec": 2.0}],
                "subtitle_cues": [{"start_sec": 0.0, "end_sec": 2.0, "text": evidence_text}],
                "source_binding": source_binding,
                "human_transcript_present": True,
            }
        ),
        encoding="utf-8",
    )


def _rules(report: dict) -> set[str]:
    return {item["rule"] for item in report["blocking"]}


class SourceSpeechSubtitleQATest(unittest.TestCase):
    def test_missing_later_subtitle_coverage_blocks(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [{"start_sec": 24.2, "end_sec": 31.0, "text": "early cue"}],
            "human_transcript_present": True,
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "source_speech_later_subtitle_coverage_missing")

    def test_placeholder_review_marker_subtitles_block(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [
                {"start_sec": 24.0, "end_sec": 32.0, "text": "review marker"},
                {"start_sec": 32.0, "end_sec": 42.0, "text": "coverage marker"},
            ],
            "subtitle_source": "asr",
            "human_transcript_present": False,
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "source_speech_placeholder_subtitles")
        self.assertEqual(result["next_action"], "human_transcript_review")

    def test_subtitle_outside_source_speech_segment_blocks(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [{"start_sec": 21.0, "end_sec": 25.0, "text": "outside cue"}],
            "human_transcript_present": True,
        })

        self.assertFalse(result["pass"])
        self.assertEqual(result["blocking"][0]["rule"], "source_speech_subtitle_timing_outside_segment")

    def test_asr_without_human_transcript_marks_human_review_needed_but_honest(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [
                {"start_sec": 24.2, "end_sec": 32.0, "text": "early cue"},
                {"start_sec": 32.2, "end_sec": 41.7, "text": "later cue"},
            ],
            "subtitle_source": "asr",
            "human_transcript_present": False,
        })

        self.assertTrue(result["pass"], result)
        self.assertTrue(result["needs_human_transcript_review"])
        self.assertEqual(result["warnings"][0]["rule"], "needs_human_transcript_review")

    def test_valid_human_transcript_coverage_passes(self):
        result = evaluate_source_speech_subtitle_qa({
            "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
            "subtitle_cues": [
                {"start_sec": 24.2, "end_sec": 32.0, "text": "early cue"},
                {"start_sec": 32.2, "end_sec": 41.8, "text": "later cue"},
            ],
            "human_transcript_present": True,
        })

        self.assertTrue(result["pass"], result)
        self.assertFalse(result["needs_human_transcript_review"])

    def test_write_for_run_reads_artifact_and_writes_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "source_speech_subtitle_evidence.json").write_text(
                json.dumps({
                    "source_speech_segments": [{"segment_id": "supervisor", "start_sec": 24.0, "end_sec": 42.0}],
                    "subtitle_cues": [
                        {"start_sec": 24.2, "end_sec": 32.0, "text": "early cue"},
                        {"start_sec": 32.2, "end_sec": 41.8, "text": "later cue"},
                    ],
                    "human_transcript_present": True,
                }),
                encoding="utf-8",
            )

            report = write_source_speech_subtitle_qa_for_run(root)

            self.assertTrue(report["pass"], report)
            self.assertTrue((root / "source_speech_subtitle_qa.json").exists())

    def test_v2_binding_checks_actual_srt_text_not_copied_evidence_cues(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(root, "1\n00:00:00,000 --> 00:00:02,000\nWRONG\n")

            report = write_source_speech_subtitle_qa_for_run(root)

            self.assertFalse(report["pass"], report)
            self.assertTrue(report["approved_text_equality_checked"])
            self.assertIn("approved_text_binding_text_mismatch", _rules(report))

    def test_v2_binding_blocks_missing_actual_srt(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(root, "1\n00:00:00,000 --> 00:00:02,000\nAPPROVED\n")
            (root / "subtitles.srt").unlink()

            report = write_source_speech_subtitle_qa_for_run(root)

            self.assertFalse(report["pass"], report)
            self.assertIn("approved_text_binding_srt_missing", _rules(report))

    def test_v2_binding_blocks_source_hash_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(root, "1\n00:00:00,000 --> 00:00:02,000\nAPPROVED\n")
            evidence_path = root / "source_speech_subtitle_evidence.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["source_binding"]["source_sha256"] = "0" * 64
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            report = write_source_speech_subtitle_qa_for_run(root)

            self.assertFalse(report["pass"], report)
            self.assertIn("approved_text_binding_source_mismatch", _rules(report))

    def test_v2_binding_blocks_actual_srt_cue_count_or_timing_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(
                root,
                "1\n00:00:00,003 --> 00:00:01,000\nAPPROVED\n\n2\n00:00:01,000 --> 00:00:02,000\nEXTRA\n",
            )

            report = write_source_speech_subtitle_qa_for_run(root)

            self.assertFalse(report["pass"], report)
            self.assertIn("approved_text_binding_cue_set_mismatch", _rules(report))

    def test_v2_binding_blocks_same_count_actual_srt_timing_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(root, "1\n00:00:00,003 --> 00:00:02,000\nAPPROVED\n")

            report = write_source_speech_subtitle_qa_for_run(root, require_approved_text_binding=True)

            self.assertFalse(report["pass"], report)
            self.assertIn("approved_text_binding_timing_mismatch", _rules(report))

    def test_v2_binding_blocks_source_window_mismatch(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(root, "1\n00:00:00,000 --> 00:00:02,000\nAPPROVED\n")
            evidence_path = root / "source_speech_subtitle_evidence.json"
            evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
            evidence["source_binding"]["window_end_sec"] = 1.99
            evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

            report = write_source_speech_subtitle_qa_for_run(root, require_approved_text_binding=True)

            self.assertFalse(report["pass"], report)
            self.assertIn("approved_text_binding_source_mismatch", _rules(report))

    def test_v2_binding_uses_actual_line_wrapped_srt_not_copied_evidence_text(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(
                root,
                "1\n00:00:00,000 --> 00:00:02,000\nAPPROVED\nTEXT\n",
                evidence_text="coverage marker",
                approved_text="APPROVED TEXT",
            )

            report = write_source_speech_subtitle_qa_for_run(root)

            self.assertTrue(report["pass"], report)
            self.assertTrue(report["approved_text_equality_checked"])

    def test_required_binding_blocks_missing_or_legacy_decision(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(root, "1\n00:00:00,000 --> 00:00:02,000\nAPPROVED\n")
            (root / "human_transcript_review_decision.json").unlink()

            missing = write_source_speech_subtitle_qa_for_run(root, require_approved_text_binding=True)

            self.assertFalse(missing["pass"], missing)
            self.assertIn("approved_text_binding_decision_missing", _rules(missing))

            write_human_transcript_review_decision_for_run(
                root,
                {
                    "decision": "approved",
                    "reviewer": "human",
                    "reviewed_draft": "subtitles.draft.srt",
                    "reviewed_cue_ids": ["cue01"],
                },
            )
            legacy = write_source_speech_subtitle_qa_for_run(root, require_approved_text_binding=True)

            self.assertFalse(legacy["pass"], legacy)
            self.assertIn("approved_text_binding_decision_legacy", _rules(legacy))

    def test_v2_binding_fails_closed_for_tampered_decision_contract(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(root, "1\n00:00:00,000 --> 00:00:02,000\nAPPROVED\n")
            decision_path = root / "human_transcript_review_decision.json"
            valid = json.loads(decision_path.read_text(encoding="utf-8"))
            cases = {
                "not_approved": {**valid, "decision": "rejected"},
                "non_human": {**valid, "reviewer": "agent"},
                "missing_draft_hash": {key: value for key, value in valid.items() if key != "reviewed_draft_sha256"},
            }

            for label, tampered in cases.items():
                with self.subTest(label=label):
                    decision_path.write_text(json.dumps(tampered), encoding="utf-8")

                    report = write_source_speech_subtitle_qa_for_run(root, require_approved_text_binding=True)

                    self.assertFalse(report["pass"], report)
                    self.assertIn("approved_text_binding_decision_invalid", _rules(report))

    def test_cli_required_binding_strict_exit_returns_one_with_blocking_report(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            _write_bound_v2_run(root, "1\n00:00:00,000 --> 00:00:02,000\nAPPROVED\n")
            (root / "human_transcript_review_decision.json").unlink()

            proc = subprocess.run(
                [
                    sys.executable,
                    str(TOOL),
                    "--run",
                    str(root),
                    "--require-approved-text-binding",
                    "--strict-exit",
                    "--json",
                ],
                cwd=ROOT,
                text=True,
                capture_output=True,
            )

            self.assertEqual(proc.returncode, 1, proc.stderr)
            self.assertIn("approved_text_binding_decision_missing", _rules(json.loads(proc.stdout)))

    def test_cli_strict_exit_blocks_text_hash_and_timing_mismatches(self):
        cases = {
            "text": ("1\n00:00:00,000 --> 00:00:02,000\nAPPROVEX\n", None, "approved_text_binding_text_mismatch"),
            "hash": ("1\n00:00:00,000 --> 00:00:02,000\nAPPROVED\n", "source_sha256", "approved_text_binding_source_mismatch"),
            "timing": ("1\n00:00:00,003 --> 00:00:02,000\nAPPROVED\n", None, "approved_text_binding_timing_mismatch"),
        }
        for label, (srt_text, changed_binding_field, expected_rule) in cases.items():
            with self.subTest(label=label), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                _write_bound_v2_run(root, srt_text)
                if changed_binding_field:
                    evidence_path = root / "source_speech_subtitle_evidence.json"
                    evidence = json.loads(evidence_path.read_text(encoding="utf-8"))
                    evidence["source_binding"][changed_binding_field] = "0" * 64
                    evidence_path.write_text(json.dumps(evidence), encoding="utf-8")

                proc = subprocess.run(
                    [
                        sys.executable,
                        str(TOOL),
                        "--run",
                        str(root),
                        "--require-approved-text-binding",
                        "--strict-exit",
                        "--json",
                    ],
                    cwd=ROOT,
                    text=True,
                    capture_output=True,
                )

                self.assertEqual(proc.returncode, 1, proc.stderr)
                self.assertIn(expected_rule, _rules(json.loads(proc.stdout)))


if __name__ == "__main__":
    unittest.main()
