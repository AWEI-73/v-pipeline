"""Thin CLI adapter for the global editorial state contract."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.global_editorial_state import (
    EditorialStateError,
    apply_delta,
    build_canon67_seed,
    build_forward_delta,
    create_revision_zero,
    validate_state_file,
    validate_worker_context,
)


def _json_output(payload: dict) -> None:
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Immutable global editorial state adapter")
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser("init", help="create revision 0")
    init.add_argument("--output-dir", required=True)
    init.add_argument("--project-id", default="canon67_540s_route_acceptance")
    init.add_argument("--repo-root", default=".")
    init.add_argument("--canon67-root", action="store_true")
    init.add_argument("--seed-json")
    init.add_argument("--focused-test-evidence", action="append", default=[])
    init.add_argument("--json", action="store_true")

    validate = sub.add_parser("validate", help="validate a state revision")
    validate.add_argument("--state", required=True)
    validate.add_argument("--repo-root")
    validate.add_argument("--json", action="store_true")

    context = sub.add_parser("write-worker-context", help="write an immutable pinned worker context")
    context.add_argument("--state", required=True)
    context.add_argument("--output", required=True)
    context.add_argument("--json", action="store_true")

    make_delta = sub.add_parser("build-forward-delta", help="build accepted Canon 67 forward delta")
    make_delta.add_argument("--base-state", required=True)
    make_delta.add_argument("--repo-root", default=".")
    make_delta.add_argument("--json", action="store_true")

    apply = sub.add_parser("apply-delta", help="apply a hash-bound delta")
    apply.add_argument("--base-state", required=True)
    apply.add_argument("--delta", required=True)
    apply.add_argument("--output-dir", required=True)
    apply.add_argument("--json", action="store_true")

    worker = sub.add_parser("validate-worker-context", help="validate a worker pinned context")
    worker.add_argument("--context-json", required=True)
    worker.add_argument("--current-state", required=True)
    worker.add_argument("--json", action="store_true")
    return parser


def _load_seed(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorialStateError("invalid_json_input", "cannot read seed JSON: " + str(path)) from exc
    if not isinstance(data, dict):
        raise EditorialStateError("invalid_json_input", "seed JSON must be an object")
    return data


def _load_context(path: Path) -> dict:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise EditorialStateError("invalid_json_input", "cannot read worker context JSON: " + str(path)) from exc
    if not isinstance(data, dict):
        raise EditorialStateError("invalid_json_input", "worker context JSON must be an object")
    return data


def run(args: argparse.Namespace) -> dict:
    if args.command == "init":
        repo_root = Path(args.repo_root).resolve()
        if args.canon67_root:
            seed, source_artifacts = build_canon67_seed(repo_root)
        elif args.seed_json:
            seed = _load_seed(Path(args.seed_json))
            source_artifacts = seed.pop("source_artifacts", [])
        else:
            raise EditorialStateError("seed_required", "init requires --canon67-root or --seed-json")
        if args.focused_test_evidence:
            seed["verification_state"]["focused_tests"] = {
                "status": "PASS",
                "evidence": args.focused_test_evidence,
            }
        path = create_revision_zero(
            output_dir=Path(args.output_dir),
            project_id=args.project_id,
            seed=seed,
            source_artifacts=source_artifacts,
        )
        return {"status": "PASS", "operation": "init", "revision_id": 0, "path": str(path)}
    if args.command == "validate":
        return validate_state_file(
            Path(args.state),
            repo_root=Path(args.repo_root).resolve() if args.repo_root else None,
        )
    if args.command == "write-worker-context":
        from video_pipeline_core.global_editorial_state import write_worker_context

        path = write_worker_context(Path(args.state), Path(args.output))
        return {"status": "PASS", "operation": "write-worker-context", "path": str(path)}
    if args.command == "build-forward-delta":
        path = build_forward_delta(Path(args.base_state), Path(args.repo_root).resolve())
        return {"status": "PASS", "operation": "build-forward-delta", "path": str(path)}
    if args.command == "apply-delta":
        path = apply_delta(Path(args.base_state), Path(args.delta), Path(args.output_dir))
        result = validate_state_file(path)
        return {
            "status": "PASS",
            "operation": "apply-delta",
            "revision_id": result["revision_id"],
            "path": str(path),
        }
    if args.command == "validate-worker-context":
        return validate_worker_context(
            _load_context(Path(args.context_json)),
            current_state_path=Path(args.current_state),
        )
    raise EditorialStateError("unknown_command", "unknown command")


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    try:
        _json_output(run(args))
        return 0
    except EditorialStateError as exc:
        _json_output({"status": "FAIL", "code": exc.code, "message": exc.message})
        return 1
    except Exception as exc:
        _json_output({"status": "FAIL", "code": "unexpected_error", "message": str(exc)})
        return 1


if __name__ == "__main__":
    sys.exit(main())
