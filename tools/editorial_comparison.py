"""Thin CLI adapter for the bounded editorial comparison core."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.editorial_comparison import (
    ComparisonError,
    build_comparison_packet,
    build_owner_delta,
    validate_flags,
)


def _json_output(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Blind A/B editorial comparison adapter")
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build-packet", help="materialize an immutable blind comparison packet")
    build.add_argument("--decision-id", required=True)
    build.add_argument("--rubric-json", "--proposition-rubric", dest="rubric_json", required=True)
    build.add_argument("--variant", action="append", nargs=2, metavar=("VARIANT_ID", "FILE"), default=[])
    build.add_argument("--variant-id", action="append", default=[])
    build.add_argument("--variant-file", action="append", default=[])
    build.add_argument("--output-dir", required=True)
    build.add_argument("--seed", type=int)

    flags = sub.add_parser("validate-flags", help="validate a flag-only reviewer result")
    flags.add_argument("--packet", "--packet-path", dest="packet", required=True)
    flags.add_argument("--flags", "--flags-path", dest="flags", required=True)

    delta = sub.add_parser("build-owner-delta", help="write a Human-owned proposed delta without applying it")
    delta.add_argument("--packet", "--packet-path", dest="packet", required=True)
    delta.add_argument("--key", "--key-path", dest="key", required=True)
    delta.add_argument("--flags", "--flags-path", dest="flags", required=True)
    delta.add_argument("--verdict", "--verdict-path", dest="verdict")
    delta.add_argument("--base-state", required=True)
    delta.add_argument("--output", "--output-path", dest="output", required=True)
    return parser


def _load_json(path: Path) -> dict:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ComparisonError("comparison_invalid_input", "cannot read JSON input: " + str(path)) from exc
    if not isinstance(value, dict):
        raise ComparisonError("comparison_invalid_input", "JSON input must be an object: " + str(path))
    return value


def _variants(args: argparse.Namespace) -> list[dict[str, str]]:
    pairs = list(args.variant or [])
    if args.variant_id or args.variant_file:
        if len(args.variant_id) != 2 or len(args.variant_file) != 2:
            raise ComparisonError("comparison_requires_exactly_two_variants", "two variant IDs and files are required")
        pairs.extend(zip(args.variant_id, args.variant_file))
    if len(pairs) != 2:
        raise ComparisonError("comparison_requires_exactly_two_variants", "exactly two --variant ID FILE pairs are required")
    return [{"id": pair[0], "path": pair[1]} for pair in pairs]


def run(args: argparse.Namespace) -> dict:
    if args.command == "build-packet":
        return build_comparison_packet(
            decision_id=args.decision_id,
            proposition_rubric=_load_json(Path(args.rubric_json)),
            variants=_variants(args),
            output_dir=Path(args.output_dir),
            seed=args.seed,
        )
    if args.command == "validate-flags":
        return validate_flags(Path(args.packet), Path(args.flags))
    if args.command == "build-owner-delta":
        return build_owner_delta(
            packet_path=Path(args.packet),
            key_path=Path(args.key),
            flags_path=Path(args.flags),
            verdict_path=Path(args.verdict) if args.verdict else None,
            base_state_path=Path(args.base_state),
            output_path=Path(args.output),
        )
    raise ComparisonError("comparison_invalid_input", "unknown command")


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        _json_output(run(args))
        return 0
    except ComparisonError as exc:
        _json_output({"status": "FAIL", "code": exc.code, "message": exc.message})
        return 1
    except Exception as exc:
        _json_output({"status": "FAIL", "code": "unexpected_error", "message": str(exc)})
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
