"""End-to-end no-render acceptance for the Effect Factory route.

This module stitches the existing Effect Factory pieces together:

visual technique plan -> confirmation -> capability review -> prompt pack ->
dry-run worker outputs -> worker review -> bounded handoff.

It does not render real Remotion, write final.mp4, or claim delivery pass.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .effect_capability_review import review_effect_capability
from .effect_factory_boundary import build_effect_revision_request, build_handoff, build_timeline
from .remotion_effects import (
    build_remotion_prompt_pack,
    run_remotion_worker_smoke,
    validate_remotion_worker_outputs,
)
from .visual_technique_plan import plan_visual_technique, technique_to_effect


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _update_artifact_manifest(run_dir: Path, *, accepted: bool | None = None) -> None:
    manifest_path = run_dir / "artifact_manifest.json"
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        manifest = {}
    if not isinstance(manifest, dict):
        manifest = {}
    manifest.setdefault("artifact_role", "artifact_manifest")
    manifest.setdefault("artifact_manifest_version", 1)
    artifacts = manifest.setdefault("artifacts", {})
    if not isinstance(artifacts, dict):
        artifacts = {}
        manifest["artifacts"] = artifacts
    status = "accepted" if accepted is True else "blocked" if accepted is False else "present"
    for key, filename in {
        "visual_technique_plan": "visual_technique_plan.json",
        "visual_technique_plan_confirmed": "visual_technique_plan.confirmed.json",
        "effect_capability_review": "effect_capability_review.json",
        "effect_intent_plan": "effect_intent_plan.json",
        "effect_revision_request": "effect_revision_request.json",
        "timeline_build": "timeline_build.json",
        "remotion_prompt_pack": "remotion_prompt_pack.json",
        "remotion_worker_outputs": "remotion_worker_outputs.json",
        "remotion_effect_review": "remotion_effect_review.json",
        "effect_handoff": "effect_handoff.json",
        "effect_factory_route_acceptance_report": "effect_factory_route_acceptance_report.json",
    }.items():
        if (run_dir / filename).is_file():
            manifest[key] = filename
            artifacts[key] = {
                "path": filename,
                "owner": "effect_factory",
                "status": status if key in {"effect_handoff", "effect_factory_route_acceptance_report"} else "evidence",
                "updated_by": "tools/effect_factory_route_acceptance.py",
            }
    _write_json(manifest_path, manifest)


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _failed_report(run_dir: Path, artifacts: dict[str, str], stage: str, next_action: str,
                   summary: Mapping[str, Any]) -> dict[str, Any]:
    report = {
        "artifact_role": "effect_factory_route_acceptance_report",
        "version": 1,
        "ok": False,
        "failed_stage": stage,
        "next_action": next_action,
        "summary": dict(summary),
        "artifacts": _copy_json(artifacts),
        "boundary_notes": [
            "Effect Factory is a bounded effect asset route, not final delivery.",
            "final.mp4 must remain absent during route acceptance.",
        ],
    }
    artifacts["effect_factory_route_acceptance_report"] = _write_json(
        run_dir / "effect_factory_route_acceptance_report.json",
        report,
    )
    report["artifacts"] = _copy_json(artifacts)
    _write_json(run_dir / "effect_factory_route_acceptance_report.json", report)
    _update_artifact_manifest(run_dir, accepted=False)
    return report


def _accept_pending_remotion_review(review: Mapping[str, Any]) -> dict[str, Any]:
    accepted = json.loads(json.dumps(review, ensure_ascii=False))
    for item in accepted.get("items") or []:
        item["status"] = "accepted"
        item["review"] = {
            "decision": "accept",
            "reviewer": "effect_factory_route_acceptance",
            "reason": "Dry-run worker evidence exists; human visual review is still required before final delivery.",
        }
    return accepted


def run_effect_factory_route_acceptance(
    run_dir: str | Path,
    *,
    request: str,
    effect_role: str,
    duration_sec: float = 4.0,
    display_text: str = "Opening",
    subtitle_text: str = "",
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    artifacts: dict[str, str] = {}

    candidate_plan = plan_visual_technique({
        "request": request,
        "effect_role": effect_role,
        "duration_sec": duration_sec,
    })
    artifacts["visual_technique_plan"] = _write_json(
        run_dir / "visual_technique_plan.json",
        candidate_plan,
    )
    if candidate_plan.get("handoff_to") == "ask_followup":
        return _failed_report(
            run_dir,
            artifacts,
            "visual_technique_plan",
            "answer_visual_technique_followup_questions",
            {
                "style_family": candidate_plan.get("style_family"),
                "followup_questions": candidate_plan.get("followup_questions") or [],
            },
        )

    confirmed_plan = plan_visual_technique({
        "request": request,
        "effect_role": effect_role,
        "duration_sec": duration_sec,
        "confirmed_style_family": True,
    })
    artifacts["visual_technique_plan_confirmed"] = _write_json(
        run_dir / "visual_technique_plan.confirmed.json",
        confirmed_plan,
    )

    effect = technique_to_effect(
        confirmed_plan,
        effect_id="fx_route_acceptance_01",
        display_text=display_text,
        subtitle_text=subtitle_text,
    )
    capability_payload = {
        "request": request,
        "effect_role": effect_role,
        "duration_sec": duration_sec,
        "style_family": confirmed_plan.get("style_family"),
        "story_function": (confirmed_plan.get("semantic_slots") or {}).get("story_function"),
        "effect_build_spec": (effect.get("prompt_parameters") or {}).get("effect_build_spec"),
    }
    capability = review_effect_capability(capability_payload)
    artifacts["effect_capability_review"] = _write_json(
        run_dir / "effect_capability_review.json",
        capability,
    )
    if capability.get("production_handoff_allowed") is not True:
        return _failed_report(
            run_dir,
            artifacts,
            "effect_capability_review",
            capability.get("next_action") or "revise_effect_capability",
            {
                "capability_decision": capability.get("decision"),
                "capability_reason": capability.get("reason"),
                "missing_inputs": capability.get("missing_inputs") or [],
            },
        )

    intent_plan = {
        "artifact_role": "effect_intent_plan",
        "version": 1,
        "effects": [effect],
    }
    artifacts["effect_intent_plan"] = _write_json(run_dir / "effect_intent_plan.json", intent_plan)
    revision_request = build_effect_revision_request(intent_plan)
    artifacts["effect_revision_request"] = _write_json(
        run_dir / "effect_revision_request.json",
        revision_request,
    )
    timeline = build_timeline(intent_plan)
    artifacts["timeline_build"] = _write_json(run_dir / "timeline_build.json", timeline)

    pack = build_remotion_prompt_pack(
        revision_request,
        intent_plan,
        timeline=timeline,
        output_dir="remotion_effects",
    )
    artifacts["remotion_prompt_pack"] = _write_json(run_dir / "remotion_prompt_pack.json", pack)

    worker_outputs = run_remotion_worker_smoke(pack, run_dir / "remotion_effects")
    artifacts["remotion_worker_outputs"] = _write_json(
        run_dir / "remotion_worker_outputs.json",
        worker_outputs,
    )
    validation = validate_remotion_worker_outputs(worker_outputs, pack)
    remotion_review = validation["review_artifact"]
    artifacts["remotion_effect_review"] = _write_json(
        run_dir / "remotion_effect_review.json",
        remotion_review,
    )
    accepted_review = _accept_pending_remotion_review(remotion_review)
    handoff = build_handoff({"status": "pass"}, accepted_review)
    artifacts["effect_handoff"] = _write_json(run_dir / "effect_handoff.json", handoff)

    final_exists = (run_dir / "final.mp4").exists()
    ok = bool(
        capability.get("production_handoff_allowed") is True
        and validation.get("ok") is True
        and remotion_review.get("status") == "pending_review"
        and handoff.get("status") == "ready_for_human_review"
        and not final_exists
    )
    report = {
        "artifact_role": "effect_factory_route_acceptance_report",
        "version": 1,
        "ok": ok,
        "failed_stage": None if ok else "effect_factory_route_acceptance",
        "next_action": (
            "ready_for_human_effect_review_or_pipeline_promotion"
            if ok else "revise_effect_factory_route"
        ),
        "summary": {
            "style_family": confirmed_plan.get("style_family"),
            "capability_decision": capability.get("decision"),
            "worker_job_count": pack.get("summary", {}).get("job_count"),
            "worker_rendered_count": worker_outputs.get("summary", {}).get("rendered_count"),
            "worker_review_status": remotion_review.get("status"),
            "handoff_status": handoff.get("status"),
            "canonical_final_exists": final_exists,
        },
        "artifacts": _copy_json(artifacts),
        "validation_errors": list(validation.get("errors") or []),
        "boundary_notes": [
            "This route acceptance uses dry-run worker outputs; it proves artifact flow, not visual quality.",
            "Effect assets are bounded finishing assets and do not satisfy material truth.",
            "Human visual review is still required before final delivery.",
            "final.mp4 must remain absent.",
        ],
    }
    artifacts["effect_factory_route_acceptance_report"] = _write_json(
        run_dir / "effect_factory_route_acceptance_report.json",
        report,
    )
    report["artifacts"] = _copy_json(artifacts)
    _write_json(run_dir / "effect_factory_route_acceptance_report.json", report)
    _update_artifact_manifest(run_dir, accepted=ok)
    return report
