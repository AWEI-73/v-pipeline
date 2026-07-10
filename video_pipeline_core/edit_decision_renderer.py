"""Bounded repo-owned renderer for canonical edit-decision artifacts."""

from __future__ import annotations

import copy
import hashlib
import json
import shutil
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from .motion_graphics import (
    build_motion_graphics_render_plan,
    composite_motion_graphics_outputs,
    run_motion_graphics_render_plan,
)
from .platform_tools import resolve_ffmpeg


class EditDecisionRenderError(ValueError):
    """Raised when canonical composition exceeds this renderer's safe subset."""


SUPPORTED_SOURCE_TYPES = {"video", "image", "generated_background"}
SUPPORTED_TRANSITIONS = {"hard_cut"}
SUPPORTED_OVERLAY_TREATMENTS = {"progressive_typewriter"}
REQUIRED_RESOLUTION = "1920x1080"


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _number(value: Any, field: str, *, positive: bool = False) -> float:
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise EditDecisionRenderError(f"{field} must be numeric") from exc
    if positive and result <= 0:
        raise EditDecisionRenderError(f"{field} must be positive")
    return result


def _is_absolute_path(value: str) -> bool:
    return Path(value).is_absolute() or (len(value) > 2 and value[1:3] in {":\\", ":/"})


def _safe_source_name(value: str) -> str:
    normalized = value.replace("\\", "/")
    return normalized.rsplit("/", 1)[-1] or "asset"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _run_ref(path: Path, run_dir: Path) -> str:
    return path.resolve().relative_to(run_dir.resolve()).as_posix()


def _copy_accepted_inputs(accepted_inputs: Sequence[Mapping[str, Any]], run_dir: Path) -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    if not isinstance(accepted_inputs, Sequence) or isinstance(accepted_inputs, (str, bytes)):
        raise EditDecisionRenderError("accepted_inputs must be a list")
    asset_dir = run_dir / "assets"
    asset_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[str, dict[str, Any]] = {}
    provenance: list[dict[str, Any]] = []
    for index, raw in enumerate(accepted_inputs):
        if not isinstance(raw, Mapping):
            raise EditDecisionRenderError(f"accepted input {index} is not an object")
        if raw.get("accepted") is not True:
            raise EditDecisionRenderError(f"accepted input {index} is not accepted")
        asset_id = str(raw.get("asset_id") or "").strip()
        kind = str(raw.get("kind") or "").lower()
        source = Path(str(raw.get("source_path") or ""))
        if not asset_id or kind not in {"video", "image", "audio"} or not source.is_file():
            raise EditDecisionRenderError(f"accepted input {index} lacks usable asset_id, kind, or source file")
        if asset_id in copied:
            raise EditDecisionRenderError(f"duplicate accepted input asset_id: {asset_id}")
        suffix = source.suffix.lower() or ".bin"
        destination = asset_dir / f"{asset_id}{suffix}"
        shutil.copy2(source, destination)
        run_path = _run_ref(destination, run_dir)
        source_relative_path = str(raw.get("source_relative_path") or "").replace("\\", "/")
        if not source_relative_path or _is_absolute_path(source_relative_path):
            source_relative_path = _safe_source_name(str(source))
        copied[asset_id] = {
            "asset_id": asset_id,
            "kind": kind,
            "path": destination,
            "run_path": run_path,
            "source_relative_path": source_relative_path,
        }
        provenance.append({
            "asset_id": asset_id,
            "kind": kind,
            "accepted": True,
            "run_path": run_path,
            "source_relative_path": source_relative_path,
            "catalog_artifact": raw.get("catalog_artifact"),
            "human_review_status": raw.get("human_review_status"),
            "byte_size": destination.stat().st_size,
            "sha256": _sha256(destination),
        })
    return copied, provenance


def _settings(payload: Mapping[str, Any], field: str) -> tuple[int, str]:
    settings = payload.get("settings") if isinstance(payload, Mapping) else None
    if not isinstance(settings, Mapping):
        raise EditDecisionRenderError(f"{field}.settings is required")
    fps = _number(settings.get("fps"), f"{field}.settings.fps", positive=True)
    if abs(fps - round(fps)) > 1e-9:
        raise EditDecisionRenderError(f"{field}.settings.fps must be an integer")
    resolution = str(settings.get("resolution") or "")
    if resolution != REQUIRED_RESOLUTION:
        raise EditDecisionRenderError(f"{field}.settings.resolution must be {REQUIRED_RESOLUTION}")
    return int(round(fps)), resolution


def _validate_composition(decision: Mapping[str, Any], timeline: Mapping[str, Any], assets: Mapping[str, Mapping[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], int, str, float]:
    if not isinstance(decision, Mapping) or decision.get("artifact_role") != "edit_decision_plan":
        raise EditDecisionRenderError("decision must be an edit_decision_plan")
    if decision.get("unsupported_instructions"):
        raise EditDecisionRenderError("decision contains unsupported_instructions")
    if decision.get("effects"):
        raise EditDecisionRenderError("bounded renderer does not support external effect assets")
    fps, resolution = _settings(decision, "decision")
    timeline_fps, timeline_resolution = _settings(timeline, "timeline")
    if (timeline_fps, timeline_resolution) != (fps, resolution):
        raise EditDecisionRenderError("decision and timeline settings disagree")
    raw_cuts = decision.get("cuts")
    raw_clips = timeline.get("clips")
    if not isinstance(raw_cuts, list) or not isinstance(raw_clips, list) or not raw_cuts or len(raw_cuts) != len(raw_clips):
        raise EditDecisionRenderError("decision cuts and timeline clips must be matching non-empty lists")
    clips: list[dict[str, Any]] = []
    for index, (cut, raw_clip) in enumerate(zip(raw_cuts, raw_clips)):
        if not isinstance(cut, Mapping) or not isinstance(raw_clip, Mapping):
            raise EditDecisionRenderError(f"cut {index} is not an object")
        if cut.get("id") and raw_clip.get("id") and cut.get("id") != raw_clip.get("id"):
            raise EditDecisionRenderError(f"cut {index} id differs from timeline")
        source_type = str(raw_clip.get("source_type") or cut.get("source_type") or "")
        if source_type not in SUPPORTED_SOURCE_TYPES:
            raise EditDecisionRenderError(f"unsupported source_type at cut {index}: {source_type or 'missing'}")
        timeline_in = _number(raw_clip.get("timeline_in_sec"), f"timeline clip {index}.timeline_in_sec")
        timeline_out = _number(raw_clip.get("timeline_out_sec"), f"timeline clip {index}.timeline_out_sec", positive=True)
        if timeline_out <= timeline_in:
            raise EditDecisionRenderError(f"timeline clip {index} has non-positive duration")
        clip = dict(raw_clip)
        clip["id"] = str(raw_clip.get("id") or cut.get("id") or f"clip_{index + 1:03d}")
        clip["source_type"] = source_type
        clip["timeline_in_sec"] = timeline_in
        clip["timeline_out_sec"] = timeline_out
        clip["in_seconds"] = _number(raw_clip.get("in_seconds", cut.get("in_seconds", 0.0)), f"timeline clip {index}.in_seconds")
        if source_type == "generated_background":
            generated = raw_clip.get("generated_background") or cut.get("generated_background")
            if not isinstance(generated, Mapping) or generated.get("color") != "black":
                raise EditDecisionRenderError("only generated black backgrounds are supported")
            clip["generated_background"] = {"color": "black"}
        else:
            asset_id = str(raw_clip.get("asset_id") or cut.get("asset_id") or "")
            if asset_id not in assets:
                raise EditDecisionRenderError(f"timeline clip {index} references unaccepted asset_id {asset_id!r}")
            expected_kind = "image" if source_type == "image" else "video"
            if assets[asset_id]["kind"] != expected_kind:
                raise EditDecisionRenderError(f"asset {asset_id} kind does not match {source_type}")
            clip["asset_id"] = asset_id
        clips.append(clip)
    clips.sort(key=lambda clip: clip["timeline_in_sec"])
    for previous, current in zip(clips, clips[1:]):
        if abs(previous["timeline_out_sec"] - current["timeline_in_sec"]) > (1.0 / fps):
            raise EditDecisionRenderError("bounded renderer requires contiguous hard-cut timeline clips")
    transitions = [dict(item) for item in (decision.get("transitions") or []) if isinstance(item, Mapping)]
    if len(transitions) != len(decision.get("transitions") or []):
        raise EditDecisionRenderError("transitions must be objects")
    if any(item.get("type") not in SUPPORTED_TRANSITIONS for item in transitions):
        raise EditDecisionRenderError("bounded renderer supports hard_cut transitions only")
    overlays = [dict(item) for item in (decision.get("overlays") or []) if isinstance(item, Mapping)]
    if len(overlays) != len(decision.get("overlays") or []):
        raise EditDecisionRenderError("overlays must be objects")
    target_duration = clips[-1]["timeline_out_sec"]
    for index, overlay in enumerate(overlays):
        if overlay.get("kind") != "text" or overlay.get("treatment") not in SUPPORTED_OVERLAY_TREATMENTS:
            raise EditDecisionRenderError(f"unsupported overlay instruction at index {index}")
        start = _number(overlay.get("start_sec"), f"overlay {index}.start_sec")
        end = _number(overlay.get("end_sec"), f"overlay {index}.end_sec", positive=True)
        if end <= start or start < 0 or end > target_duration + (1.0 / fps):
            raise EditDecisionRenderError(f"overlay {index} is outside the timeline")
        if not isinstance(overlay.get("text"), Mapping):
            raise EditDecisionRenderError(f"overlay {index}.text must be an object")
    music = ((decision.get("audio") or {}).get("music") or {}) if isinstance(decision.get("audio"), Mapping) else {}
    music_asset_id = str(music.get("asset_id") or "")
    if music_asset_id not in assets or assets[music_asset_id]["kind"] != "audio":
        raise EditDecisionRenderError("one accepted BGM audio asset is required")
    return clips, overlays, transitions, fps, resolution, target_duration


def _persist_clip(clip: Mapping[str, Any], assets: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    persisted = copy.deepcopy(dict(clip))
    if persisted.get("source_type") == "generated_background":
        persisted.pop("source", None)
        persisted.pop("source_path", None)
        return persisted
    asset = assets[str(persisted["asset_id"])]
    persisted["source_path"] = asset["run_path"]
    persisted["source"] = asset["run_path"]
    lineage = dict(persisted.get("source_lineage") or persisted.get("lineage") or {})
    lineage.update({
        "asset_id": asset["asset_id"],
        "source_relative_path": asset["source_relative_path"],
        "accepted": True,
    })
    persisted["source_lineage"] = lineage
    persisted.pop("lineage", None)
    return persisted


def _persist_decision(decision: Mapping[str, Any], clips: Sequence[Mapping[str, Any]], assets: Mapping[str, Mapping[str, Any]]) -> dict[str, Any]:
    persisted = copy.deepcopy(dict(decision))
    persisted["cuts"] = [_persist_clip(clip, assets) for clip in clips]
    return persisted


def _assert_portable(payload: Any) -> None:
    if isinstance(payload, Mapping):
        for value in payload.values():
            _assert_portable(value)
    elif isinstance(payload, list):
        for value in payload:
            _assert_portable(value)
    elif isinstance(payload, str) and _is_absolute_path(payload):
        raise EditDecisionRenderError("persisted canonical artifacts must not contain absolute paths")


def _segment_command(clip: Mapping[str, Any], assets: Mapping[str, Mapping[str, Any]], fps: int, output_ref: str) -> list[str]:
    duration = float(clip["timeline_out_sec"]) - float(clip["timeline_in_sec"])
    scale = f"scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih):color=black,setsar=1,fps={fps}"
    common = ["-t", f"{duration:.6f}", "-vf", scale, "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", output_ref]
    if clip["source_type"] == "generated_background":
        return ["-f", "lavfi", "-i", f"color=c=black:s=1920x1080:r={fps}", *common]
    asset = assets[str(clip["asset_id"])]
    if clip["source_type"] == "image":
        return ["-loop", "1", "-framerate", str(fps), "-i", asset["run_path"], *common]
    return ["-ss", f"{float(clip['in_seconds']):.6f}", "-i", asset["run_path"], *common]


def _run_ffmpeg(command: list[str], *, run_dir: Path, command_log: list[dict[str, Any]]) -> None:
    executable = resolve_ffmpeg()
    completed = subprocess.run([executable, "-y", *command], cwd=run_dir, capture_output=True, text=True, encoding="utf-8")
    command_log.append({
        "argv": ["ffmpeg", "-y", *command],
        "exit_code": completed.returncode,
        "stderr_tail": (completed.stderr or "")[-2000:],
    })
    if completed.returncode != 0:
        raise EditDecisionRenderError(f"ffmpeg render failed: {(completed.stderr or '')[-600:]}")


def _motion_graphics_contract(overlays: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    return {
        "motion_graphics_version": 1,
        "contract_hash": "canonical-edit-decision",
        "items": [
            {
                "id": str(overlay.get("id") or f"overlay_{index + 1:03d}"),
                "effect_type": "title_sequence",
                "timing": {
                    "start_sec": float(overlay["start_sec"]),
                    "duration_sec": float(overlay["end_sec"]) - float(overlay["start_sec"]),
                },
                "text": dict(overlay.get("text") or {}),
                "style": {"motion": overlay["treatment"], "safe_area": "title_safe"},
                "reason": "canonical progressive text overlay",
            }
            for index, overlay in enumerate(overlays)
        ],
    }


def render_edit_decision(
    decision: Mapping[str, Any],
    timeline: Mapping[str, Any],
    *,
    run_dir: str | Path,
    accepted_inputs: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    """Render the bounded canonical composition to a technically reviewable MP4."""
    run = Path(run_dir)
    if (run / "final.mp4").exists():
        raise EditDecisionRenderError("run directory already contains final.mp4")
    run.mkdir(parents=True, exist_ok=True)
    assets, provenance = _copy_accepted_inputs(accepted_inputs, run)
    clips, overlays, transitions, fps, resolution, target_duration = _validate_composition(decision, timeline, assets)
    persisted_timeline = copy.deepcopy(dict(timeline))
    persisted_timeline["clips"] = [_persist_clip(clip, assets) for clip in clips]
    persisted_timeline["overlays"] = copy.deepcopy(overlays)
    persisted_timeline["transitions"] = copy.deepcopy(transitions)
    persisted_decision = _persist_decision(decision, clips, assets)
    for payload in (persisted_timeline, persisted_decision):
        _assert_portable(payload)
    command_manifest = {
        "artifact_role": "render_command_manifest",
        "version": 1,
        "renderer": "video_pipeline_core.edit_decision_renderer",
        "status": "planned",
        "commands": [],
    }
    input_manifest = {
        "artifact_role": "render_input_manifest",
        "version": 1,
        "asset_store": "assets",
        "accepted_inputs": provenance,
    }
    render_handoff = {
        "artifact_role": "render_handoff",
        "version": 1,
        "owner": "main-pipeline",
        "ok": True,
        "status": "ready_for_render_rehearsal",
        "selected_profile": "bounded_edit_decision",
        "final_delivery_claimed": False,
        "composition_artifacts": [
            "edit_decision_plan.json",
            "timeline_build.json",
            "render_input_manifest.json",
            "render_command_manifest.json",
        ],
        "limitations": ["technical_rehearsal_only", "human_creative_approval_required"],
    }
    _write_json(run / "edit_decision_plan.json", persisted_decision)
    _write_json(run / "timeline_build.json", persisted_timeline)
    _write_json(run / "render_input_manifest.json", input_manifest)
    _write_json(run / "render_command_manifest.json", command_manifest)
    _write_json(run / "render_handoff.json", render_handoff)

    command_log: list[dict[str, Any]] = []
    segments_dir = run / "segments"
    segments_dir.mkdir(parents=True, exist_ok=True)
    segment_refs: list[str] = []
    for index, clip in enumerate(clips):
        segment_ref = f"segments/segment_{index + 1:03d}.mp4"
        _run_ffmpeg(_segment_command(clip, assets, fps, segment_ref), run_dir=run, command_log=command_log)
        segment_refs.append(segment_ref)
    concat_ref = "segments/concat.txt"
    (run / concat_ref).write_text(
        "".join(f"file '{Path(ref).name}'\n" for ref in segment_refs), encoding="utf-8"
    )
    _run_ffmpeg(["-f", "concat", "-safe", "0", "-i", concat_ref, "-an", "-c:v", "libx264", "-preset", "veryfast", "-pix_fmt", "yuv420p", "base_video.mp4"], run_dir=run, command_log=command_log)
    music_asset_id = str(((decision.get("audio") or {}).get("music") or {}).get("asset_id"))
    _run_ffmpeg([
        "-i", "base_video.mp4", "-stream_loop", "-1", "-i", assets[music_asset_id]["run_path"],
        "-t", f"{target_duration:.6f}", "-map", "0:v:0", "-map", "1:a:0", "-c:v", "copy", "-c:a", "aac",
        "-movflags", "+faststart", "with_audio.mp4",
    ], run_dir=run, command_log=command_log)
    final = run / "final.mp4"
    if overlays:
        contract = _motion_graphics_contract(overlays)
        plan = build_motion_graphics_render_plan(contract)
        render_outputs = run_motion_graphics_render_plan(plan, run)
        _write_json(run / "motion_graphics_contract.json", contract)
        _write_json(run / "motion_graphics_render_plan.json", plan)
        _write_json(run / "motion_graphics_manifest.json", {
            "artifact_role": "motion_graphics_manifest",
            "version": 1,
            "render_outputs": [
                {**output, "path": _run_ref(Path(output["path"]), run) if output.get("path") else None}
                for output in render_outputs
            ],
        })
        composite = composite_motion_graphics_outputs(run / "with_audio.mp4", render_outputs, output_path=final)
        command_log.append({
            "backend": "ffmpeg_libass",
            "input": "with_audio.mp4",
            "output": "final.mp4",
            "status": composite.get("status"),
        })
        if not composite.get("ok") or not final.is_file():
            raise EditDecisionRenderError(f"motion graphics composite failed: {composite}")
    else:
        shutil.copy2(run / "with_audio.mp4", final)
    command_manifest["status"] = "completed"
    command_manifest["commands"] = command_log
    _write_json(run / "render_command_manifest.json", command_manifest)
    return {
        "ok": True,
        "run_dir": str(run),
        "final_mp4": str(final),
        "duration_sec": target_duration,
        "fps": fps,
        "resolution": resolution,
        "final_delivery_claimed": False,
    }
