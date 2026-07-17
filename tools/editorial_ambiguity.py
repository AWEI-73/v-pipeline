"""Thin CLI for the Stage 0-2 editorial ambiguity contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.editorial_ambiguity import EditorialAmbiguityError, validate_package


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Validate an evidence-carrying Stage 0-2 editorial package")
    subparsers = parser.add_subparsers(dest="command", required=True)
    validate = subparsers.add_parser("validate", help="validate story decision, segment grammar, and evidence needs")
    validate.add_argument("--story-decision", required=True)
    validate.add_argument("--segment-contract", required=True)
    validate.add_argument("--evidence-map", required=True)
    validate.add_argument("--out")
    validate.add_argument("--json", action="store_true")
    return parser


def _write_report(path: Path, report: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        report = validate_package(
            Path(args.story_decision),
            Path(args.segment_contract),
            Path(args.evidence_map),
        )
    except EditorialAmbiguityError as exc:
        report = {
            "artifact_role": "stage2_ambiguity_gate_report",
            "schema_version": 1,
            "ok": False,
            "stage2_completion": "FAIL",
            "ready_for_stage3": False,
            "errors": [{"code": exc.code, "location": "input", "message": exc.message}],
            "warnings": [],
        }
    if args.out:
        _write_report(Path(args.out), report)
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
