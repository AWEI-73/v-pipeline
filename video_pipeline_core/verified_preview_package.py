"""Package a verified preview candidate without promoting it to final.mp4."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


KNOWN_PREVIEW_NAMES = (
    "single_source_highlight_preview.mp4",
    "dialogue_highlight_cut_reviewed.mp4",
    "dialogue_highlight_cut.mp4",
    "highlight_final_quiet.mp4",
    "highlight_safe.mp4",
    "highlight_final.mp4",
)


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path.resolve())


def _resolve_candidate_from_highlight_report(root: Path) -> Path | None:
    for report_path in sorted(root.rglob("*.json")):
        report = _load_json(report_path)
        if not report or report.get("artifact_role") != "highlight_cut_report":
            continue
        output = report.get("out") or report.get("output")
        if not output:
            continue
        output_path = Path(str(output))
        if not output_path.is_absolute():
            output_path = root / output_path
        if output_path.is_file() and output_path.stat().st_size > 0:
            return output_path.resolve()
    return None


def _resolve_preview_candidate(root: Path) -> Path | None:
    candidate = _resolve_candidate_from_highlight_report(root)
    if candidate:
        return candidate
    for name in KNOWN_PREVIEW_NAMES:
        path = root / name
        if path.is_file() and path.stat().st_size > 0:
            return path.resolve()
    return None


def _find_verify_bundle(root: Path) -> tuple[Path | None, dict[str, Any] | None]:
    direct = root / "final_product_verify" / "final_product_verify_bundle.json"
    payload = _load_json(direct)
    if payload:
        return direct, payload
    direct = root / "final_product_verify_bundle.json"
    payload = _load_json(direct)
    if payload:
        return direct, payload
    for path in sorted(root.rglob("final_product_verify_bundle.json")):
        payload = _load_json(path)
        if payload:
            return path, payload
    return None, None


def package_verified_preview(
    run_dir: str | Path,
    *,
    out_name: str = "verified_preview_package.json",
    candidate_name: str = "delivery_candidate.mp4",
) -> dict[str, Any]:
    """Create a reviewable delivery candidate package from a verified preview.

    This intentionally does not create or overwrite ``final.mp4``. The package is
    a handoff point: a human/operator can review it and explicitly promote later.
    """
    root = Path(run_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"run folder not found: {root}")

    gate_path = root / "delivery_gate.json"
    gate = _load_json(gate_path)
    if not gate or gate.get("pass") is not True:
        raise ValueError("delivery_gate.json must exist and pass before packaging a verified preview")

    verify_path, verify = _find_verify_bundle(root)
    if not verify or verify.get("pass") is not True:
        raise ValueError("final_product_verify_bundle.json must exist and pass before packaging")

    source = _resolve_preview_candidate(root)
    if not source:
        raise FileNotFoundError("no verified preview video candidate found")

    destination = root / candidate_name
    if source.resolve() != destination.resolve():
        shutil.copy2(source, destination)

    package = {
        "artifact_role": "verified_preview_package",
        "version": 1,
        "status": "ready_for_operator_delivery_review",
        "run_dir": str(root),
        "source_video": _rel(root, source),
        "packaged_video": _rel(root, destination),
        "delivery_gate": _rel(root, gate_path),
        "final_product_verify": _rel(root, verify_path),
        "promotes_to_final_mp4": False,
        "next_action": "operator_review_or_explicit_final_promotion",
    }
    out_path = root / out_name
    out_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return package
