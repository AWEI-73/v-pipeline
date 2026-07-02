"""Final product eye/ear verification bundle for complete video candidates."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from .keyframe_grid import generate_keyframe_grid
from .platform_tools import resolve_ffmpeg
from .soundtrack_probe import build_soundtrack_probe
from .visual_audit import audit_visual


def _extract_audio(video: str | Path, out_path: str | Path) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            resolve_ffmpeg(),
            "-y",
            "-i",
            str(video),
            "-vn",
            "-ac",
            "2",
            "-ar",
            "44100",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=300,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "audio extraction failed")
    return str(out)


def _is_no_audio_error(error: Exception) -> bool:
    text = str(error).lower()
    return (
        "does not contain any stream" in text
        or "output file #0 does not contain any stream" in text
        or ("stream map" in text and "matches no streams" in text)
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def build_final_product_verify_bundle(
    video: str | Path,
    *,
    out_dir: str | Path,
    sample_count: int = 12,
    keyframe_grid_builder: Callable[[str | Path, str | Path], dict[str, Any]] | None = None,
    visual_audit_builder: Callable[[dict[str, Any], str | Path], dict[str, Any]] | None = None,
    audio_extractor: Callable[[str | Path, str | Path], str] | None = None,
    soundtrack_probe_builder: Callable[[str | Path], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    video_path = str(Path(video).resolve())

    grid_path = out / "keyframe_grid.jpg"
    if keyframe_grid_builder:
        grid_meta = keyframe_grid_builder(video_path, grid_path)
        if not grid_path.exists():
            grid_path.write_bytes(b"")
    else:
        grid_meta = generate_keyframe_grid(
            video_path,
            grid_path,
            sample_count=sample_count,
            columns=4,
        )

    visual_path = out / "visual_audit.json"
    if visual_audit_builder:
        visual_audit = visual_audit_builder(grid_meta, visual_path)
    else:
        visual_audit = audit_visual(grid_meta, min_samples=1)
    _write_json(visual_path, visual_audit)

    audio_path = out / "final_audio.wav"
    try:
        (audio_extractor or _extract_audio)(video_path, audio_path)
    except RuntimeError as exc:
        if not _is_no_audio_error(exc):
            raise
        audio_path = None
        audio_status = "no_audio_stream"
        probe = (soundtrack_probe_builder or build_soundtrack_probe)(video_path)
    else:
        audio_status = "extracted"
        probe = (soundtrack_probe_builder or build_soundtrack_probe)(audio_path)
    probe_path = out / "soundtrack_probe_report.json"
    _write_json(probe_path, probe)

    visual_pass = bool(visual_audit.get("pass") is True)
    audio_pass = bool(probe.get("pass") is True)
    
    findings = []
    suggested_branch = "verify-delivery"
    if not visual_pass:
        findings.append({
            "code": "VISUAL_AUDIT_FAILED",
            "severity": "blocker",
            "message": str(visual_audit.get("error") or "Visual verification check failed.")
        })
    if not audio_pass:
        findings.append({
            "code": "AUDIO_PROBE_FAILED",
            "severity": "blocker",
            "message": str(probe.get("error") or "Audio/Soundtrack verification check failed.")
        })

    if not visual_pass:
        suggested_branch = "material-map"
    elif not audio_pass:
        suggested_branch = "soundtrack-arranger"

    bundle = {
        "artifact_role": "final_product_verify_bundle",
        "version": 1,
        "pass": visual_pass and audio_pass,
        "video": video_path,
        "visual": {
            "keyframe_grid": "keyframe_grid.jpg",
            "visual_audit": "visual_audit.json",
            "pass": visual_pass,
            "sample_count": grid_meta.get("sample_count"),
        },
        "audio": {
            "final_audio": "final_audio.wav" if audio_path else None,
            "audio_status": audio_status,
            "soundtrack_probe_report": "soundtrack_probe_report.json",
            "pass": audio_pass,
            "analysis_depth": probe.get("analysis_depth"),
        },
        "next_action": None if visual_pass and audio_pass else "repair_final_product_verify_evidence",
    }
    _write_json(out / "final_product_verify_bundle.json", bundle)

    if not bundle["pass"]:
        from .revision_packet_schema import RevisionPacket
        revision_targets = []
        if not visual_pass:
            revision_targets.append({
                "artifact": "project_material_map.json",
                "field": "assets",
                "issue": str(visual_audit.get("error") or "Visual verification check failed."),
                "suggested_change": "review material wall",
                "target_branch": "material-map",
            })
        if not audio_pass:
            revision_targets.append({
                "artifact": "soundtrack_plan.json",
                "field": "sections",
                "issue": str(probe.get("error") or "Audio/Soundtrack verification check failed."),
                "suggested_change": "adjust audio levels or choose different soundtrack",
                "target_branch": "soundtrack-arranger",
            })

        if not visual_pass and not audio_pass:
            suggested_branch = "verify-delivery"
            problem_type = "multi_branch"
        elif not audio_pass:
            problem_type = "audio"
        else:
            problem_type = "material"

        packet = RevisionPacket(
            source_review="final_product_verify_bundle.json",
            target_branch=suggested_branch,
            problem_type=problem_type,
            severity="blocking",
            revision_targets=revision_targets,
            allowed_actions=["patch_contract", "rerun_branch", "ask_user", "route_back", "stop"],
            forbidden_actions=["overwrite_final_mp4", "mutate_material_truth", "silently_downgrade_required_feature"],
            rerun_policy={
                "allowed": True,
                "max_attempts": 1,
                "requires_agent_decision": True
            }
        )
        packet.save(out / "verify_revision_packet.json")

    return bundle
