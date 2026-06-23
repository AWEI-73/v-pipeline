"""Read-only agent-facing route summary for a video pipeline run folder."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _find_json(root: Path, name: str) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    direct = root / name
    payload = _load_json(direct)
    if payload is not None:
        return direct, payload
    for path in sorted(root.rglob(name)):
        payload = _load_json(path)
        if payload is not None:
            return path, payload
    return None, None


def _rel(root: Path, path: Any) -> str | None:
    if not path:
        return None
    candidate = Path(str(path))
    if not candidate.is_absolute():
        return str(candidate).replace("\\", "/")
    try:
        return str(candidate.relative_to(root)).replace("\\", "/")
    except ValueError:
        return str(candidate).replace("\\", "/")


def _read_refs(root: Path, *values: Any) -> list[str]:
    refs = []
    for value in values:
        if isinstance(value, dict):
            refs.extend(_read_refs(root, *value.values()))
        elif isinstance(value, list):
            refs.extend(_read_refs(root, *value))
        else:
            ref = _rel(root, value)
            if ref and ref not in refs:
                refs.append(ref)
    return refs


def _contract(mode, cursor, *, next_action=None, resume=None, reason=None, read=None,
              run_dir=None, source=None):
    status = {
        "run": "RUN",
        "repair": "REPAIR",
        "done": "DONE",
        "unknown": "UNKNOWN",
    }.get(mode, "UNKNOWN")
    return {
        "mode": mode,
        "cursor": cursor,
        "next": next_action,
        "resume": resume,
        "reason": reason,
        "read": read or [],
        "run": str(run_dir) if run_dir else None,
        "status": status,
        "command": next_action,
        "source": source,
    }


def _boundary_summary(root: Path, boundary: dict[str, Any]):
    stage = boundary.get("stage") or "boundary"
    refs = _read_refs(root, boundary.get("refs") or {})
    if boundary.get("pass") is False:
        regressions = boundary.get("regressions") or []
        reason = "; ".join(str(item) for item in regressions if item) or f"{stage} failed"
        return _contract(
            "repair",
            stage,
            resume=None,
            reason=reason,
            read=refs,
            run_dir=root,
            source="boundary_report.json",
        )
    return None


def _lifecycle_summary(root: Path, lifecycle: dict[str, Any]):
    stage = lifecycle.get("stage")
    refs = _read_refs(root, lifecycle.get("refs") or {})
    if stage == "build_ready" and lifecycle.get("can_build") is True:
        return _contract(
            "run",
            "stage4_dry_build",
            next_action=f"python tools/boundary_smoke.py {root}",
            reason="material lifecycle is build_ready",
            read=refs,
            run_dir=root,
            source="material_map_lifecycle.json",
        )
    if stage == "await_map_review":
        return _contract(
            "repair",
            "stage3_review_apply",
            resume="stage4_dry_build",
            reason="await_map_review: missing or unapplied scene-to-need review edges",
            read=refs,
            run_dir=root,
            source="material_map_lifecycle.json",
        )
    if stage in ("await_material", "revision_blocked", "invalid"):
        return _contract(
            "repair",
            "stage2_material_map",
            resume="stage3_review_apply",
            reason=f"material lifecycle is {stage}",
            read=refs,
            run_dir=root,
            source="material_map_lifecycle.json",
        )
    return None


def summarize_run(run_dir):
    root = Path(run_dir).resolve()

    _boundary_path, boundary = _find_json(root, "boundary_report.json")
    if boundary:
        summary = _boundary_summary(root, boundary)
        if summary:
            return summary

    _lifecycle_path, lifecycle = _find_json(root, "material_map_lifecycle.json")
    if lifecycle:
        summary = _lifecycle_summary(root, lifecycle)
        if summary:
            return summary

    verify_path, verify = _find_json(root, "verify_result.json")
    if verify is None:
        verify_path, verify = _find_json(root, "qa_report.json")
    if verify and verify.get("pass") is True and (root / "final.mp4").exists():
        return _contract(
            "done",
            "complete",
            reason=f"verify passed (score: {verify.get('score', 100)})",
            read=[_rel(root, verify_path)],
            run_dir=root,
            source=_rel(root, verify_path),
        )
    if verify and verify.get("pass") is False:
        return _contract(
            "repair",
            "stage5_final_review",
            reason=f"verify failed (score: {verify.get('score', 0)})",
            read=[_rel(root, verify_path)],
            run_dir=root,
            source=_rel(root, verify_path),
        )

    state_path, state = _find_json(root, "state.json")
    if state and state.get("next_action"):
        return _contract(
            "repair" if str(state.get("next_action")).startswith("revise:") else "run",
            str(state.get("next_action")),
            next_action=str(state.get("next_action")),
            reason="state.json declares next_action",
            read=[_rel(root, state_path)],
            run_dir=root,
            source=_rel(root, state_path),
        )

    return _contract(
        "unknown",
        "unknown",
        reason="no recognized pipeline routing artifact found",
        read=[],
        run_dir=root,
        source=None,
    )


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="run folder to inspect")
    parser.add_argument("--json", action="store_true", help="print JSON contract")
    args = parser.parse_args(argv)
    summary = summarize_run(args.run)
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(summary["mode"])
        print(f"cursor={summary['cursor']}")
        print(f"next={summary['next'] or ''}")
        if summary["resume"]:
            print(f"resume={summary['resume']}")
        if summary["reason"]:
            print(f"reason={summary['reason']}")
        if summary["read"]:
            print("read=" + ";".join(summary["read"]))
    return 0 if summary["mode"] != "unknown" else 2


if __name__ == "__main__":
    raise SystemExit(main())
