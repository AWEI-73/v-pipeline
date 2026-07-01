"""Package a verified preview candidate without promoting it to final.mp4."""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any


KNOWN_PREVIEW_NAMES = (
    "rough_cut_preview.mp4",
    "rough_cut_storyboard_preview.mp4",
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
        if not report or report.get("artifact_role") not in {
            "highlight_cut_report",
            "rough_cut_preview_report",
            "rough_cut_storyboard_preview_report",
        }:
            continue
        if report.get("artifact_role") in {
            "rough_cut_preview_report",
            "rough_cut_storyboard_preview_report",
        } and report.get("ok") is not True:
            continue
        output = report.get("out") or report.get("output") or report.get("output_video")
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


def _write_json_if_missing(path: Path, payload: dict[str, Any]) -> bool:
    if path.exists():
        return False
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return True


def _find_preview_report(root: Path, source: Path) -> tuple[Path | None, dict[str, Any] | None]:
    roles = {"rough_cut_storyboard_preview_report", "rough_cut_preview_report", "highlight_cut_report"}
    for path in sorted(root.rglob("*.json")):
        payload = _load_json(path)
        if not payload or payload.get("artifact_role") not in roles:
            continue
        output = payload.get("output_video") or payload.get("out") or payload.get("output")
        if not output:
            continue
        output_path = Path(str(output))
        if not output_path.is_absolute():
            output_path = root / output_path
        try:
            if output_path.resolve() == source.resolve():
                return path, payload
        except OSError:
            continue
    return None, None


def _preview_duration_sec(preview_report: dict[str, Any] | None, verify: dict[str, Any] | None) -> float | None:
    if preview_report:
        for value in (
            preview_report.get("duration_sec"),
            preview_report.get("planned_duration_sec"),
            ((preview_report.get("output_probe") or {}).get("format") or {}).get("duration")
            if isinstance(preview_report.get("output_probe"), dict)
            else None,
        ):
            try:
                if value is not None:
                    return float(value)
            except (TypeError, ValueError):
                pass
    if verify:
        for section in ("visual", "audio"):
            payload = verify.get(section)
            if isinstance(payload, dict):
                try:
                    value = payload.get("duration_sec")
                    if value is not None:
                        return float(value)
                except (TypeError, ValueError):
                    pass
    return None


def _write_review_packet(
    root: Path,
    *,
    package: dict[str, Any],
    source: Path,
    destination: Path,
    gate_path: Path,
    gate: dict[str, Any],
    verify_path: Path | None,
    verify: dict[str, Any] | None,
) -> dict[str, Any]:
    preview_path, preview_report = _find_preview_report(root, source)
    duration = _preview_duration_sec(preview_report, verify)
    limitations = []
    if isinstance(preview_report, dict):
        limitations.extend(str(item) for item in preview_report.get("limitations") or [] if item)
    if not limitations:
        limitations.append("This is a verified preview candidate, not canonical final.mp4.")

    packet = {
        "artifact_role": "verified_preview_review_packet",
        "version": 1,
        "status": "ready_for_operator_review",
        "candidate_video": _rel(root, destination),
        "source_video": _rel(root, source),
        "duration_sec": duration,
        "delivery_gate_pass": gate.get("pass") is True,
        "final_product_verify_pass": bool(verify and verify.get("pass") is True),
        "preview_report": _rel(root, preview_path) if preview_path else None,
        "delivery_gate": _rel(root, gate_path),
        "final_product_verify": _rel(root, verify_path) if verify_path else None,
        "promotes_to_final_mp4": False,
        "limitations": limitations,
        "operator_questions": [
            "Does the candidate represent the requested story/sequence well enough for review?",
            "Should this preview be promoted, revised in Workbench, or rebuilt as a motion preview?",
        ],
        "next_action": "operator_review_or_explicit_final_promotion",
    }
    packet_path = root / "verified_preview_review_packet.json"
    packet_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    duration_note = f"{duration:.1f}s" if isinstance(duration, (int, float)) else "unknown"
    md = [
        "# Verified Preview Review Packet",
        "",
        f"- Candidate: `{packet['candidate_video']}`",
        f"- Source: `{packet['source_video']}`",
        f"- Duration: `{duration_note}`",
        f"- Delivery gate: `{str(packet['delivery_gate_pass']).lower()}`",
        f"- Final product verify: `{str(packet['final_product_verify_pass']).lower()}`",
        f"- Promotes to final.mp4: `{str(packet['promotes_to_final_mp4']).lower()}`",
        "",
        "## Limitations",
        *[f"- {item}" for item in limitations],
        "",
        "## Operator Questions",
        *[f"- {item}" for item in packet["operator_questions"]],
        "",
    ]
    (root / "review_report.md").write_text("\n".join(md), encoding="utf-8")
    return packet


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
    packet = _write_review_packet(
        root,
        package=package,
        source=source,
        destination=destination,
        gate_path=gate_path,
        gate=gate,
        verify_path=verify_path,
        verify=verify,
    )
    package["review_packet"] = "verified_preview_review_packet.json"
    package["review_report_md"] = "review_report.md"
    package["review_packet_status"] = packet.get("status")
    out_path.write_text(json.dumps(package, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return package


def promote_verified_preview_to_final(
    run_dir: str | Path,
    *,
    reviewer: str = "operator",
    final_name: str = "final.mp4",
    report_name: str = "final_promotion_report.json",
    overwrite: bool = False,
) -> dict[str, Any]:
    """Promote a packaged delivery candidate to the canonical final video.

    Promotion is intentionally explicit. Packaging proves a preview is ready for
    review; this function records the operator decision and writes ``final.mp4``.
    """
    root = Path(run_dir).resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"run folder not found: {root}")

    package_path = root / "verified_preview_package.json"
    package = _load_json(package_path)
    if not package or package.get("artifact_role") != "verified_preview_package":
        raise FileNotFoundError("verified_preview_package.json is required before final promotion")

    if package.get("status") != "ready_for_operator_delivery_review":
        raise ValueError("verified preview package is not ready for operator delivery review")

    source_ref = package.get("packaged_video")
    if not source_ref:
        raise ValueError("verified preview package is missing packaged_video")
    source = Path(str(source_ref))
    if not source.is_absolute():
        source = root / source
    if not source.is_file() or source.stat().st_size <= 0:
        raise FileNotFoundError(f"packaged video not found: {source}")

    final_path = root / final_name
    if final_path.exists() and not overwrite:
        raise FileExistsError(f"{final_name} already exists; pass overwrite=True to replace it")

    if source.resolve() != final_path.resolve():
        shutil.copy2(source, final_path)

    wrote_requirements = _write_json_if_missing(root / "delivery_requirements.json", {
        "artifact_role": "delivery_requirements",
        "version": 1,
        "delivery_mode": "single_source_highlight_preserve_original_audio",
        "requires_audio": True,
        "requires_narration": False,
        "requires_music": False,
        "requires_subtitles": False,
        "requires_soundtrack_probe": False,
        "requires_vocal_conflict_check": False,
        "requires_frame_evidence": False,
        "requires_effect_render_verification": False,
        "source": "verified_preview_promotion",
    })
    wrote_audio_mix = _write_json_if_missing(root / "audio_mix_report.json", {
        "artifact_role": "audio_mix_report",
        "version": 1,
        "audio_stream_present": True,
        "narration_included": False,
        "music_included": False,
        "mix_strategy": "preserve_candidate_original_audio",
        "source_video": _rel(root, source),
        "final_video": _rel(root, final_path),
    })

    report = {
        "artifact_role": "final_promotion_report",
        "version": 1,
        "status": "promoted",
        "run_dir": str(root),
        "reviewer": reviewer,
        "source_package": _rel(root, package_path),
        "source_video": _rel(root, source),
        "final_video": _rel(root, final_path),
        "overwrote_existing_final": bool(overwrite),
        "wrote_delivery_requirements": wrote_requirements,
        "wrote_audio_mix_report": wrote_audio_mix,
        "next_action": "write_delivery_gate_report",
    }
    report_path = root / report_name
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
