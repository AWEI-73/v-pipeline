"""Prompt-driven Remotion effect adapter artifacts for Brownfield Edit.

This module does not import or run Remotion. It translates reviewed effect gaps
into a stable prompt pack for an image/video-capable worker, then validates the
worker's output before Workbench/Brownfield review can accept it.
"""

from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any, Mapping

from .effect_contract import validate_effect_intent_plan
from .effect_revision import ADAPTER_ROUTE


DEFAULT_DURATION_SEC = 3.0
PROTECTED_OUTPUTS = {
    "final.mp4",
    "timeline.json",
    "timeline_build.json",
    "segment_contract.json",
    "project_material_map.json",
}

ROLE_COMPONENT_FAMILY = {
    "chapter_transition": "page_turn_transition",
    "transition_plate": "page_turn_transition",
    "title_card": "title_reveal",
    "lower_third": "lower_third_motion",
    "overlay": "overlay_motion",
    "particle": "particle_overlay",
    "light_leak": "light_leak_overlay",
    "motion_background": "motion_background",
    "panel_frame": "panel_frame_motion",
    "speed_line": "speed_line_overlay",
}


def _non_empty_str(value: Any, field: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def _optional_str(value: Any, field: str, default: str = "") -> str:
    if value is None:
        return default
    if not isinstance(value, str):
        raise ValueError(f"{field} must be a string when present")
    return value.strip()


def _finite_positive(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{field} must be a positive finite number")
    value = float(value)
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{field} must be a positive finite number")
    return value


def _safe_id(value: str) -> str:
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", value).strip("_.-")
    return slug or "effect"


def _load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8-sig") as f:
        return json.load(f)


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _validate_revision_request(request: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if not isinstance(request, dict):
        raise ValueError("effect_revision_request must be object")
    if request.get("artifact_role") != "effect_revision_request":
        raise ValueError("artifact_role must be effect_revision_request")
    if request.get("version") != 1:
        raise ValueError("effect_revision_request version must be 1")
    requests = request.get("requests")
    if not isinstance(requests, list):
        raise ValueError("effect_revision_request.requests must be list")
    for idx, item in enumerate(requests):
        if not isinstance(item, dict):
            raise ValueError(f"effect_revision_request.requests[{idx}] must be object")
        _non_empty_str(item.get("request_id"), f"requests[{idx}].request_id")
        _non_empty_str(item.get("effect_id"), f"requests[{idx}].effect_id")
        route = item.get("route")
        if not isinstance(route, str) or not route.strip():
            raise ValueError(f"requests[{idx}].route must be non-empty string")
    return requests


def _effects_by_id(effect_intent_plan: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    validate_effect_intent_plan(effect_intent_plan)
    return {
        effect["effect_id"]: effect
        for effect in effect_intent_plan.get("effects") or []
    }


def _segment_key(value: Any) -> Any:
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return value


def _timeline_span(timeline: Mapping[str, Any] | None, segment: Any) -> tuple[dict[str, float], list[str]]:
    diagnostics: list[str] = []
    if not timeline:
        diagnostics.append("timeline_missing: using default timing")
        return {"start_sec": 0.0, "duration_sec": DEFAULT_DURATION_SEC}, diagnostics
    clips = [
        clip for clip in (timeline or {}).get("clips", [])
        if _segment_key(clip.get("segment")) == _segment_key(segment)
    ]
    starts = []
    ends = []
    for clip in clips:
        try:
            start = float(clip.get("timeline_in_sec"))
            end = float(clip.get("timeline_out_sec"))
        except (TypeError, ValueError):
            continue
        if math.isfinite(start) and math.isfinite(end) and end > start:
            starts.append(start)
            ends.append(end)
    if not starts:
        diagnostics.append(f"timeline_segment_missing:{segment}; using default timing")
        return {"start_sec": 0.0, "duration_sec": DEFAULT_DURATION_SEC}, diagnostics
    start = min(starts)
    end = max(ends)
    return {"start_sec": round(start, 3), "duration_sec": round(end - start, 3)}, diagnostics


def _component_family(effect: Mapping[str, Any]) -> str:
    return ROLE_COMPONENT_FAMILY.get(str(effect.get("role") or ""), "custom_motion_effect")


def _prompt_text(effect: Mapping[str, Any], request: Mapping[str, Any],
                 timing: Mapping[str, Any], component_family: str) -> str:
    visual = effect.get("visual_language") or []
    visual_text = ", ".join(visual) if visual else "clean motion graphic"
    return (
        f"Create a {component_family} Remotion effect for the Hermes video pipeline. "
        f"Intent: {effect.get('intent')}. Visual language: {visual_text}. "
        f"Intensity: {effect.get('intensity')}. Segment: {request.get('segment')}. "
        f"Duration: {timing['duration_sec']} seconds. "
        "Render as a reviewable overlay/fullscreen asset with deterministic timing. "
        "Do not use story-evidence footage to satisfy material coverage."
    )


def build_remotion_prompt_pack(effect_revision_request: Mapping[str, Any],
                               effect_intent_plan: Mapping[str, Any], *,
                               timeline: Mapping[str, Any] | None = None,
                               output_dir: str | Path = "remotion_effects") -> dict[str, Any]:
    """Build prompt jobs for adapter-route effect gaps.

    Only `route_to_node14_or_remotion_adapter` requests become jobs. Regular
    ffmpeg recipe gaps remain in FX3 and are not sent to Remotion.
    """

    requests = _validate_revision_request(effect_revision_request)
    effects = _effects_by_id(effect_intent_plan)
    jobs = []
    output_dir = str(output_dir).replace("\\", "/").rstrip("/")
    for request in requests:
        if request.get("route") != ADAPTER_ROUTE:
            continue
        source_effect_id = _non_empty_str(
            request.get("source_effect_id"),
            f"{request.get('request_id')}.source_effect_id",
        )
        effect = effects.get(source_effect_id)
        if effect is None:
            raise ValueError(f"source_effect_id not found in effect_intent_plan: {source_effect_id}")
        timing, diagnostics = _timeline_span(timeline, request.get("segment"))
        family = _component_family(effect)
        job_id = f"rm_{_safe_id(source_effect_id)}"
        target_file = f"{output_dir}/{job_id}.mov"
        preview_file = f"{output_dir}/{job_id}.preview.mp4"
        jobs.append({
            "job_id": job_id,
            "request_id": request.get("request_id"),
            "source_effect_id": source_effect_id,
            "effect_id": request.get("effect_id"),
            "route": request.get("route"),
            "role": effect.get("role"),
            "component_family": family,
            "prompt": _prompt_text(effect, request, timing, family),
            "props": {
                "intent": effect.get("intent"),
                "visual_language": list(effect.get("visual_language") or []),
                "intensity": effect.get("intensity"),
                "segment": request.get("segment"),
                "duration_sec": timing["duration_sec"],
            },
            "timing": timing,
            "output": {
                "type": "overlay_video",
                "alpha": True,
                "target_file": target_file,
                "preview_file": preview_file,
            },
            "acceptance": {
                "must_exist": ["preview_file", "target_file"],
                "must_match_duration_sec": timing["duration_sec"],
                "requires_workbench_review": True,
            },
            "diagnostics": diagnostics,
        })
    return {
        "artifact_role": "remotion_prompt_pack",
        "version": 1,
        "status": "pending" if jobs else "empty",
        "source": {
            "effect_revision_request_role": effect_revision_request.get("artifact_role"),
            "effect_intent_plan_role": effect_intent_plan.get("artifact_role"),
        },
        "summary": {
            "request_count": len(requests),
            "job_count": len(jobs),
            "skipped_non_adapter_count": len(requests) - len(jobs),
        },
        "jobs": jobs,
        "next_action": "run_remotion_worker_and_review" if jobs else None,
    }


def _validate_prompt_pack(pack: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    if not isinstance(pack, dict):
        raise ValueError("remotion_prompt_pack must be object")
    if pack.get("artifact_role") != "remotion_prompt_pack":
        raise ValueError("artifact_role must be remotion_prompt_pack")
    if pack.get("version") != 1:
        raise ValueError("remotion_prompt_pack version must be 1")
    jobs = pack.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("remotion_prompt_pack.jobs must be list")
    by_id = {}
    for idx, job in enumerate(jobs):
        if not isinstance(job, dict):
            raise ValueError(f"remotion_prompt_pack.jobs[{idx}] must be object")
        job_id = _non_empty_str(job.get("job_id"), f"jobs[{idx}].job_id")
        if job_id in by_id:
            raise ValueError(f"duplicate remotion job_id: {job_id}")
        by_id[job_id] = job
    return by_id


def _path_exists(path: Any, field: str) -> str:
    value = _non_empty_str(path, field)
    if not Path(value).exists() or Path(value).is_dir():
        raise ValueError(f"{field} must point to an existing file: {value}")
    return value


def _relative_or_absolute(path: Any, base: Path) -> Path:
    value = Path(_non_empty_str(path, "path"))
    if value.is_absolute():
        return value
    return base / value


def validate_remotion_worker_outputs(worker_outputs: Mapping[str, Any],
                                     remotion_prompt_pack: Mapping[str, Any]) -> dict[str, Any]:
    """Validate worker outputs and return a Workbench-review artifact.

    This does not accept outputs into BUILD. It only proves the worker produced
    files that correspond to prompt-pack jobs and can be surfaced for review.
    """

    errors: list[str] = []
    prompt_jobs = _validate_prompt_pack(remotion_prompt_pack)
    if not isinstance(worker_outputs, dict):
        raise ValueError("remotion_worker_outputs must be object")
    if worker_outputs.get("artifact_role") != "remotion_worker_outputs":
        raise ValueError("artifact_role must be remotion_worker_outputs")
    if worker_outputs.get("version") != 1:
        raise ValueError("remotion_worker_outputs version must be 1")
    jobs = worker_outputs.get("jobs")
    if not isinstance(jobs, list):
        raise ValueError("remotion_worker_outputs.jobs must be list")
    review_items = []
    seen = set()
    for idx, output in enumerate(jobs):
        if not isinstance(output, dict):
            errors.append(f"jobs[{idx}] must be object")
            continue
        try:
            job_id = _non_empty_str(output.get("job_id"), f"jobs[{idx}].job_id")
            if job_id in seen:
                raise ValueError(f"duplicate job_id: {job_id}")
            seen.add(job_id)
            prompt_job = prompt_jobs.get(job_id)
            if prompt_job is None:
                raise ValueError(f"unknown job_id: {job_id}")
            status = _non_empty_str(output.get("status"), f"jobs[{idx}].status")
            if status != "rendered":
                raise ValueError(f"jobs[{idx}].status must be rendered")
            preview = _path_exists(output.get("preview_file"), f"jobs[{idx}].preview_file")
            rendered = _path_exists(output.get("rendered_asset"), f"jobs[{idx}].rendered_asset")
            duration_sec = _finite_positive(output.get("duration_sec"), f"jobs[{idx}].duration_sec")
            review_items.append({
                "job_id": job_id,
                "source_effect_id": prompt_job.get("source_effect_id"),
                "effect_id": prompt_job.get("effect_id"),
                "role": prompt_job.get("role"),
                "component_family": prompt_job.get("component_family"),
                "prompt": prompt_job.get("prompt"),
                "preview_file": preview,
                "rendered_asset": rendered,
                "duration_sec": duration_sec,
                "timing": prompt_job.get("timing"),
                "status": "pending_review",
                "next_action": "workbench_review_remotion_effect",
            })
        except ValueError as exc:
            errors.append(str(exc))
    rendered_count = len(review_items)
    review = {
        "artifact_role": "remotion_effect_review",
        "version": 1,
        "status": "pending_review" if rendered_count else "blocked",
        "summary": {
            "job_count": len(prompt_jobs),
            "rendered_count": rendered_count,
            "error_count": len(errors),
        },
        "items": review_items,
        "errors": errors,
        "next_action": "review_remotion_effect_outputs" if rendered_count else "fix_remotion_worker_outputs",
    }
    return {
        "ok": not errors,
        "errors": errors,
        "summary": review["summary"],
        "review_artifact": review,
    }


def write_remotion_prompt_pack(request_path: str | Path, effect_intent_plan_path: str | Path,
                               out_path: str | Path, *, timeline_path: str | Path | None = None,
                               output_dir: str | Path = "remotion_effects") -> dict[str, Any]:
    request = _load_json(request_path)
    effect_intent_plan = _load_json(effect_intent_plan_path)
    timeline = _load_json(timeline_path) if timeline_path else None
    pack = build_remotion_prompt_pack(
        request,
        effect_intent_plan,
        timeline=timeline,
        output_dir=output_dir,
    )
    _write_json(out_path, pack)
    return pack


def write_remotion_worker_review(prompt_pack_path: str | Path, worker_outputs_path: str | Path,
                                 out_review_path: str | Path) -> dict[str, Any]:
    pack = _load_json(prompt_pack_path)
    outputs = _load_json(worker_outputs_path)
    result = validate_remotion_worker_outputs(outputs, pack)
    if result["ok"]:
        _write_json(out_review_path, result["review_artifact"])
    return result


def _dry_run_renderer(job: Mapping[str, Any], preview_file: str | Path,
                      rendered_asset: str | Path) -> dict[str, Any]:
    """Deterministic test/smoke renderer.

    This is not the real Remotion backend. It is intentionally opt-in via
    `--dry-run`, so regression tests can exercise the worker contract without
    requiring Node/Remotion.
    """
    preview_file = Path(preview_file)
    rendered_asset = Path(rendered_asset)
    preview_file.parent.mkdir(parents=True, exist_ok=True)
    rendered_asset.parent.mkdir(parents=True, exist_ok=True)
    preview_file.write_bytes(b"remotion preview dry-run\n")
    rendered_asset.write_bytes(b"remotion rendered dry-run\n")
    return {"ok": True, "backend": "dry_run", "command": []}


def _command_renderer(command_template: str):
    def _run(job: Mapping[str, Any], preview_file: str | Path,
             rendered_asset: str | Path) -> dict[str, Any]:
        preview_file = Path(preview_file)
        rendered_asset = Path(rendered_asset)
        preview_file.parent.mkdir(parents=True, exist_ok=True)
        rendered_asset.parent.mkdir(parents=True, exist_ok=True)
        job_file = preview_file.with_suffix(".job.json")
        job_file.write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")
        command = command_template.format(
            job_json=str(job_file),
            job_id=job.get("job_id"),
            preview_file=str(preview_file),
            rendered_asset=str(rendered_asset),
            duration_sec=(job.get("timing") or {}).get("duration_sec"),
        )
        proc = subprocess.run(command, shell=True, stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0:
            return {
                "ok": False,
                "backend": "command",
                "command": command,
                "error": (proc.stderr or proc.stdout or "").strip(),
            }
        return {
            "ok": True,
            "backend": "command",
            "command": command,
            "stdout": proc.stdout.strip(),
        }
    return _run


def run_remotion_worker_smoke(remotion_prompt_pack: Mapping[str, Any],
                              out_dir: str | Path,
                              *,
                              renderer=None,
                              command_template: str | None = None) -> dict[str, Any]:
    """Run a bounded Remotion-worker smoke over a prompt pack.

    The default behavior requires either an injected renderer or a command
    template. This keeps Remotion optional in normal tests while allowing a real
    environment to pass a command such as an `npx remotion render ...` wrapper.
    """
    jobs_by_id = _validate_prompt_pack(remotion_prompt_pack)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    if renderer is None:
        if command_template:
            renderer = _command_renderer(command_template)
        else:
            renderer = _dry_run_renderer
    outputs = []
    for job in jobs_by_id.values():
        output = job.get("output") or {}
        preview_file = _relative_or_absolute(
            output.get("preview_file") or f"{job['job_id']}.preview.mp4",
            out_dir,
        )
        rendered_asset = _relative_or_absolute(
            output.get("target_file") or f"{job['job_id']}.mov",
            out_dir,
        )
        try:
            result = renderer(job, preview_file, rendered_asset)
        except Exception as exc:  # worker boundary: record failure, don't crash loop
            result = {"ok": False, "error": str(exc)}
        if result.get("ok") and preview_file.is_file() and rendered_asset.is_file():
            status = "rendered"
            error = None
        else:
            status = "failed"
            error = result.get("error") or "renderer did not create expected files"
        item = {
            "job_id": job["job_id"],
            "source_effect_id": job.get("source_effect_id"),
            "status": status,
            "preview_file": str(preview_file),
            "rendered_asset": str(rendered_asset),
            "duration_sec": (job.get("timing") or {}).get("duration_sec", DEFAULT_DURATION_SEC),
            "backend": result.get("backend") or "remotion_worker",
        }
        if result.get("command"):
            item["command"] = result["command"]
        if error:
            item["error"] = error
        outputs.append(item)
    rendered_count = sum(1 for item in outputs if item["status"] == "rendered")
    return {
        "artifact_role": "remotion_worker_outputs",
        "version": 1,
        "status": "rendered" if rendered_count == len(outputs) else "failed",
        "summary": {
            "job_count": len(outputs),
            "rendered_count": rendered_count,
            "failed_count": len(outputs) - rendered_count,
        },
        "jobs": outputs,
    }


def write_remotion_worker_smoke(prompt_pack_path: str | Path, out_worker_outputs_path: str | Path,
                                out_dir: str | Path, *, dry_run: bool = False,
                                command_template: str | None = None) -> dict[str, Any]:
    pack = _load_json(prompt_pack_path)
    if not dry_run and not command_template:
        raise ValueError("remotion worker smoke requires --dry-run or --command")
    renderer = _dry_run_renderer if dry_run else None
    outputs = run_remotion_worker_smoke(
        pack,
        out_dir,
        renderer=renderer,
        command_template=command_template,
    )
    _write_json(out_worker_outputs_path, outputs)
    return outputs


def _is_accepted_review_item(item: Mapping[str, Any]) -> bool:
    review = item.get("review") or {}
    return item.get("status") == "accepted" and review.get("decision") == "accept"


def _accepted_remotion_items(review: Mapping[str, Any]) -> list[Mapping[str, Any]]:
    if not isinstance(review, dict):
        raise ValueError("remotion_effect_review must be object")
    if review.get("artifact_role") != "remotion_effect_review":
        raise ValueError("artifact_role must be remotion_effect_review")
    if review.get("version") != 1:
        raise ValueError("remotion_effect_review version must be 1")
    items = review.get("items")
    if not isinstance(items, list):
        raise ValueError("remotion_effect_review.items must be list")
    accepted = []
    pending = []
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"items[{idx}] must be object")
        if _is_accepted_review_item(item):
            rendered = _path_exists(item.get("rendered_asset"), f"items[{idx}].rendered_asset")
            timing = item.get("timing") or {}
            start = float(timing.get("start_sec", 0.0))
            duration = _finite_positive(timing.get("duration_sec") or item.get("duration_sec"),
                                        f"items[{idx}].duration_sec")
            if not math.isfinite(start) or start < 0:
                raise ValueError(f"items[{idx}].timing.start_sec must be finite >= 0")
            accepted_item = dict(item)
            accepted_item["rendered_asset"] = rendered
            accepted_item["_start_sec"] = start
            accepted_item["_duration_sec"] = duration
            accepted.append(accepted_item)
        else:
            pending.append(item.get("job_id") or f"items[{idx}]")
    if not accepted:
        raise ValueError("no accepted Remotion effect outputs to composite")
    if pending:
        raise ValueError("unaccepted Remotion effect outputs remain: " + ", ".join(map(str, pending)))
    return accepted


def _overlay_filter(accepted_items: list[Mapping[str, Any]]) -> tuple[str, str]:
    filters = []
    prev = "[0:v]"
    for idx, item in enumerate(accepted_items):
        start = float(item["_start_sec"])
        duration = float(item["_duration_sec"])
        end = start + duration
        ov = f"[ov{idx}]"
        out = f"[v{idx}]"
        filters.append(
            f"[{idx + 1}:v]setpts=PTS-STARTPTS+{start:.3f}/TB,format=rgba{ov}"
        )
        filters.append(
            f"{prev}{ov}overlay=0:0:enable='between(t,{start:.3f},{end:.3f})':"
            f"eof_action=pass{out}"
        )
        prev = out
    return ";".join(filters), prev


def composite_accepted_remotion_effects(remotion_effect_review: Mapping[str, Any],
                                        base_video: str | Path,
                                        out_path: str | Path,
                                        *,
                                        ffmpeg: str = "ffmpeg",
                                        runner=subprocess.run,
                                        dry_run: bool = False) -> dict[str, Any]:
    """Composite accepted Remotion outputs onto a non-canonical draft video."""
    out_path = Path(out_path)
    if out_path.name in PROTECTED_OUTPUTS:
        raise ValueError(f"refusing to write protected canonical artifact: {out_path.name}")
    base_video = Path(base_video)
    if not base_video.is_file() or base_video.is_dir():
        raise ValueError(f"base_video must point to an existing file: {base_video}")
    accepted = _accepted_remotion_items(remotion_effect_review)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    command = [ffmpeg, "-y", "-i", str(base_video)]
    for item in accepted:
        command.extend(["-i", str(item["rendered_asset"])])
    filter_complex, final_label = _overlay_filter(accepted)
    command.extend([
        "-filter_complex", filter_complex,
        "-map", final_label,
        "-map", "0:a?",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(out_path),
    ])
    if dry_run:
        out_path.write_bytes(b"remotion composite dry-run\n")
        status = "dry_run"
    else:
        proc = runner(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
        if proc.returncode != 0 or not out_path.is_file():
            raise RuntimeError(f"remotion composite failed: {(proc.stderr or '')[-800:]}")
        status = "rendered"
    return {
        "artifact_role": "remotion_composite_draft_report",
        "version": 1,
        "ok": True,
        "status": status,
        "base_video": str(base_video),
        "out": str(out_path),
        "applied_count": len(accepted),
        "items": [
            {
                "job_id": item.get("job_id"),
                "source_effect_id": item.get("source_effect_id"),
                "rendered_asset": item.get("rendered_asset"),
                "start_sec": item["_start_sec"],
                "duration_sec": item["_duration_sec"],
            }
            for item in accepted
        ],
        "command": command,
        "note": "non-canonical draft composite; final.mp4 untouched",
        "next_action": "workbench_review_remotion_composite_draft",
    }


def write_remotion_composite_draft(review_path: str | Path, base_video: str | Path,
                                   out_path: str | Path, report_out_path: str | Path | None = None,
                                   *, ffmpeg: str = "ffmpeg",
                                   dry_run: bool = False) -> dict[str, Any]:
    review = _load_json(review_path)
    result = composite_accepted_remotion_effects(
        review,
        base_video,
        out_path,
        ffmpeg=ffmpeg,
        dry_run=dry_run,
    )
    if report_out_path:
        _write_json(report_out_path, result)
    return result
