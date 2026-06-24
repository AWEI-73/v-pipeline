"""Material-first MemoryPhotoWall boundary acceptance.

This harness verifies the narrow Brownfield bridge:

material wall reviewed keyframes -> effect collage refs -> MemoryPhotoWall
effect_build_spec -> prompt pack -> worker review -> effect render verification.

It never writes final.mp4 and does not composite a video.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .effect_collage_refs import write_collage_media_refs
from .effect_render_verification import write_effect_render_verification
from .effect_revision import ADAPTER_ROUTE
from .remotion_acceptance import accept_all_review_items
from .remotion_effects import (
    build_remotion_prompt_pack,
    run_remotion_worker_smoke,
    validate_remotion_worker_outputs,
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _load_json(path: str | Path) -> Any:
    with Path(path).open(encoding="utf-8-sig") as f:
        return json.load(f)


def _memory_effect(collage_refs: list[dict[str, Any]], *, duration_sec: float) -> dict[str, Any]:
    return {
        "effect_id": "fx_material_memory_wall_01",
        "role": "title_card",
        "intent": "open the material-first training recap with a slow emotional reviewed-material wall",
        "intensity": "medium",
        "target": {"beat_id": "beat_opening_memory", "segment_id": "opening_memory"},
        "visual_language": ["memory photo wall", "slow emotional reveal", "reviewed material refs"],
        "required_for_story": True,
        "must_preserve_proof": True,
        "allowed_backends": ["remotion_preview", "remotion_render"],
        "fallback": "static contact sheet hold",
        "duration_sec": duration_sec,
        "template_id": "memory_photo_wall",
        "display_text": "Training recap",
        "subtitle_text": "Reviewed material memory wall",
        "prompt_parameters": {
            "effect_build_spec": {
                "component": "MemoryPhotoWall",
                "duration_sec": duration_sec,
                "story_function": "emotional_setup",
                "pacing": "slow",
                "density": "low",
                "reveal_mode": "one_by_one",
                "reveal_interval_sec": 1.2,
                "hold_after_full_wall_sec": 2.0,
                "camera_motion": "slow_push_in",
                "caption_mode": "minimal",
                "accent_light": "soft_warm",
                "material_refs": collage_refs,
            },
        },
    }


def _write_report(run_dir: Path, payload: Mapping[str, Any]) -> dict[str, Any]:
    report = dict(payload)
    _write_json(run_dir / "remotion_material_first_memory_acceptance_report.json", report)
    return report


def run_material_first_memory_acceptance(run_dir: str | Path, *,
                                         project_map: str | Path,
                                         wall_verdict: str | Path,
                                         wall_request: str | Path,
                                         max_refs: int = 6,
                                         duration_sec: float = 8.0) -> dict[str, Any]:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    artifacts: dict[str, str] = {}

    try:
        collage_refs_path = run_dir / "effect_collage_media_refs.json"
        collage_refs = write_collage_media_refs(
            project_map,
            collage_refs_path,
            material_wall_review_verdict_path=wall_verdict,
            material_wall_request_path=wall_request,
            max_refs=max_refs,
        )
        artifacts["effect_collage_media_refs"] = str(collage_refs_path)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return _write_report(run_dir, {
            "artifact_role": "remotion_material_first_memory_acceptance_report",
            "version": 1,
            "ok": False,
            "failed_stage": "effect_collage_refs",
            "errors": [str(exc)],
            "next_action": "repair_reviewed_material_refs",
            "artifacts": artifacts,
        })

    refs = list(collage_refs.get("collage_media_refs") or [])
    if not refs:
        return _write_report(run_dir, {
            "artifact_role": "remotion_material_first_memory_acceptance_report",
            "version": 1,
            "ok": False,
            "failed_stage": "effect_collage_refs",
            "errors": ["no reviewed material refs available for MemoryPhotoWall"],
            "next_action": "provide_material_wall_keyframes_or_reviewed_stills",
            "artifacts": artifacts,
        })

    effect_intent_plan = {
        "artifact_role": "effect_intent_plan",
        "version": 1,
        "effects": [_memory_effect(refs, duration_sec=duration_sec)],
    }
    effect_revision_request = {
        "artifact_role": "effect_revision_request",
        "version": 1,
        "status": "pending",
        "summary": {"request_count": 1},
        "requests": [{
            "request_id": "fxrev_material_memory_wall_01",
            "effect_id": "fx_material_memory_wall_01_gap",
            "source_effect_id": "fx_material_memory_wall_01",
            "segment": "opening_memory",
            "operation": "external_effect",
            "route": ADAPTER_ROUTE,
            "reason": "material-first memory wall requires reviewable Remotion preview from reviewed material refs",
            "status": "pending",
        }],
    }
    timeline_build = {
        "artifact_role": "timeline_build",
        "version": 1,
        "duration_sec": max(duration_sec, 12.0),
        "clips": [{"segment": "opening_memory", "timeline_in_sec": 0.0, "timeline_out_sec": duration_sec}],
    }
    effect_intent_path = _write_json(run_dir / "effect_intent_plan.json", effect_intent_plan)
    revision_path = _write_json(run_dir / "effect_revision_request.json", effect_revision_request)
    timeline_path = _write_json(run_dir / "timeline_build.json", timeline_build)
    artifacts.update({
        "effect_intent_plan": str(effect_intent_path),
        "effect_revision_request": str(revision_path),
        "timeline_build": str(timeline_path),
    })

    pack = build_remotion_prompt_pack(
        effect_revision_request,
        effect_intent_plan,
        timeline=timeline_build,
        output_dir=str(run_dir / "remotion_effects"),
        collage_media_refs=collage_refs,
    )
    prompt_pack_path = _write_json(run_dir / "remotion_prompt_pack.json", pack)
    artifacts["remotion_prompt_pack"] = str(prompt_pack_path)

    worker_outputs = run_remotion_worker_smoke(pack, run_dir / "remotion_effects")
    worker_outputs_path = _write_json(run_dir / "remotion_worker_outputs.json", worker_outputs)
    artifacts["remotion_worker_outputs"] = str(worker_outputs_path)

    validation = validate_remotion_worker_outputs(worker_outputs, pack)
    if not validation.get("ok"):
        return _write_report(run_dir, {
            "artifact_role": "remotion_material_first_memory_acceptance_report",
            "version": 1,
            "ok": False,
            "failed_stage": "remotion_worker_outputs",
            "errors": validation.get("errors") or [],
            "next_action": "repair_remotion_worker_outputs",
            "artifacts": artifacts,
        })

    pending_review_path = _write_json(run_dir / "remotion_effect_review.pending.json", validation["review_artifact"])
    artifacts["remotion_effect_review_pending"] = str(pending_review_path)
    review = accept_all_review_items(
        validation["review_artifact"],
        reviewer="remotion-material-first-memory-acceptance",
        reason="bounded dry-run artifact chain passed and review evidence exists",
    )
    review_path = _write_json(run_dir / "remotion_effect_review.json", review)
    artifacts["remotion_effect_review"] = str(review_path)

    verification = write_effect_render_verification(
        effect_intent_path,
        review_path,
        run_dir / "effect_render_verification.json",
        root=run_dir,
    )
    artifacts["effect_render_verification"] = str(run_dir / "effect_render_verification.json")

    report = {
        "artifact_role": "remotion_material_first_memory_acceptance_report",
        "version": 1,
        "ok": verification.get("pass") is True,
        "failed_stage": None if verification.get("pass") is True else "effect_render_verification",
        "next_action": "ready_for_human_effect_review_or_pipeline_promotion"
        if verification.get("pass") is True else "repair_effect_render_verification",
        "summary": {
            "selected_ref_count": len(refs),
            "evidence_kinds": sorted({str(ref.get("evidence_kind") or "") for ref in refs if ref.get("evidence_kind")}),
            "build_component": "MemoryPhotoWall",
            "prompt_pack_job_count": pack.get("summary", {}).get("job_count", 0),
            "rendered_count": worker_outputs.get("summary", {}).get("rendered_count", 0),
            "verification": verification.get("summary", {}),
            "canonical_final_exists": (run_dir / "final.mp4").exists(),
        },
        "artifacts": artifacts,
        "review_notes": [
            "dry-run worker only; no visual quality render is claimed",
            "no final.mp4 or canonical renderer output is written",
        ],
    }
    return _write_report(run_dir, report)
