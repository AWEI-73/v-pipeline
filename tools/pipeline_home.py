"""Read-only agent-facing route summary for a video pipeline run folder."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _find_json(root: Path, name: str) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    direct = root / name
    payload = _load_json(direct)
    if payload is not None:
        return direct, payload
    if name != "artifact_manifest.json":
        manifest = _load_json(root / "artifact_manifest.json")
        if manifest:
            key = Path(name).stem
            ref = manifest.get(key)
            if ref:
                candidate = Path(str(ref))
                if not candidate.is_absolute():
                    candidate = root / candidate
                payload = _load_json(candidate)
                if payload is not None:
                    return candidate, payload
    for path in sorted(root.rglob(name)):
        payload = _load_json(path)
        if payload is not None:
            return path, payload
    return None, None


def _find_json_by_role(
    root: Path,
    role: str,
    *,
    prefer_reviewed: bool = False,
) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    candidates = []
    for path in sorted(root.rglob("*.json")):
        payload = _load_json(path)
        if payload and payload.get("artifact_role") == role:
            candidates.append((path, payload))
    if not candidates:
        return None, None
    if prefer_reviewed:
        reviewed_statuses = {
            "reviewed",
            "reviewed_by_operator",
            "agent_reviewed",
            "accepted",
            "approved",
        }
        for path, payload in candidates:
            status = str(payload.get("review_status") or "").strip().casefold()
            if status in reviewed_statuses:
                return path, payload
        for path, payload in candidates:
            if "reviewed" in path.name.casefold():
                return path, payload
    return candidates[0]


def _find_json_name_or_role(root: Path, name: str, role: str) -> tuple[Path, dict[str, Any]] | tuple[None, None]:
    path, payload = _find_json(root, name)
    if payload:
        return path, payload
    return _find_json_by_role(root, role)


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
        "waiting": "WAITING",
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


def _acceptance_summary(root: Path):
    report_path, report = _find_json(root, "material_first_boundary_acceptance_report.json")
    if not report:
        return None

    stages = report.get("stages") or []
    passed = sum(1 for stage in stages if stage.get("ok") is True)
    total = len(stages)
    read = [_rel(root, report_path)]
    if report.get("ok") is False:
        failed_stage = report.get("failed_stage") or "material-first-boundary-acceptance"
        blocking = []
        for stage in stages:
            if stage.get("ok") is False:
                blocking = stage.get("blocking") or []
                break
        reason = "; ".join(
            str(item.get("message") or item.get("rule") or item)
            for item in blocking
            if item
        ) or f"material-first acceptance failed at {failed_stage}"
        return _contract(
            "repair",
            failed_stage,
            next_action=report.get("next_action"),
            reason=reason,
            read=read,
            run_dir=root,
            source="material_first_boundary_acceptance_report.json",
        )

    soundtrack_contract = ((report.get("stage0_contracts") or {}).get("soundtrack") or {})
    soundtrack_requested = (
        soundtrack_contract.get("handoff_to") == "soundtrack-arranger"
        and str(soundtrack_contract.get("music_role") or "").strip().lower() not in {"", "none", "unsure"}
    )
    soundtrack_plan_path, soundtrack_plan = _find_json(root, "soundtrack_plan.json")
    if soundtrack_requested and not soundtrack_plan:
        return _contract(
            "run",
            "soundtrack_arranger",
            next_action="soundtrack-arrange",
            reason=(
                "material-first acceptance passed; Stage 0 soundtrack contract "
                f"requests {soundtrack_contract.get('music_role')}"
            ),
            read=read,
            run_dir=root,
            source="material_first_boundary_acceptance_report.json",
        )

    subtitle_voiceover_contract = ((report.get("stage0_contracts") or {}).get("subtitle_voiceover") or {})
    subtitle_required = subtitle_voiceover_contract.get("subtitle_required") is True
    voiceover_required = subtitle_voiceover_contract.get("voiceover_required") is True
    if subtitle_required or voiceover_required:
        _handoff_path, handoff = _find_json(root, "subtitle_voiceover_build_handoff.json")
        subtitle_ready = isinstance(handoff, dict) and handoff.get("subtitle_ready") is True
        voiceover_ready = isinstance(handoff, dict) and handoff.get("voiceover_ready") is True
        if (subtitle_required and not subtitle_ready) or (voiceover_required and not voiceover_ready):
            required = []
            if subtitle_required:
                required.append("subtitles")
            if voiceover_required:
                required.append("voiceover")
            return _contract(
                "repair",
                "subtitle_voiceover_handoff",
                next_action="subtitle-voiceover-handoff-accept",
                resume="subtitle_voiceover",
                reason=(
                    "material-first acceptance passed; Stage 0 requires "
                    + " and ".join(required)
                    + " before BUILD handoff"
                ),
                read=read,
                run_dir=root,
                source="material_first_boundary_acceptance_report.json",
            )

    rough_preview_path, rough_preview = _find_json(root, "rough_cut_preview_report.json")
    if rough_preview and rough_preview.get("ok") is True:
        output = rough_preview.get("output_video") or rough_preview.get("out")
        output_path = Path(str(output)) if output else None
        if output_path and not output_path.is_absolute():
            output_path = root / output_path
        output_rel = _rel(root, output_path) if output_path and output_path.is_file() else None
        if output_rel:
            return _contract(
                "run",
                "stage5_final_review",
                next_action="review_motion_preview",
                reason=(
                    "material-first motion preview ready "
                    f"({rough_preview.get('clip_count', '?')} clips)"
                ),
                read=read + [_rel(root, rough_preview_path), output_rel],
                run_dir=root,
                source="rough_cut_preview_report.json",
            )

    storyboard_path, storyboard = _find_json(root, "rough_cut_storyboard_preview_report.json")
    if storyboard and storyboard.get("ok") is True:
        output = storyboard.get("output_video") or storyboard.get("out")
        output_path = Path(str(output)) if output else None
        if output_path and not output_path.is_absolute():
            output_path = root / output_path
        output_rel = _rel(root, output_path) if output_path and output_path.is_file() else None
        if output_rel:
            return _contract(
                "run",
                "stage5_final_review",
                next_action="review_storyboard_preview",
                reason=(
                    "material-first storyboard preview ready "
                    f"({storyboard.get('clip_count', '?')} clips)"
                ),
                read=read + [_rel(root, storyboard_path), output_rel],
                run_dir=root,
                source="rough_cut_storyboard_preview_report.json",
            )

    if rough_preview and rough_preview.get("ok") is False:
        read.append(_rel(root, rough_preview_path))
        error_type = rough_preview.get("error_type")
        message = rough_preview.get("message") or "rough cut preview failed"
        reason = f"{error_type}: {message}" if error_type else message
        return _contract(
            "repair",
            "stage5_preview_build",
            next_action=rough_preview.get("next_action") or "use_rough_cut_storyboard_preview_or_reduce_clip_count",
            reason=str(reason),
            read=read,
            run_dir=root,
            source="rough_cut_preview_report.json",
        )

    return _contract(
        "run",
        "stage5_final_review",
        next_action=report.get("next_action") or "ready_for_render_or_human_review",
        reason=f"material-first boundary acceptance passed: {passed}/{total} stages passed",
        read=read,
        run_dir=root,
        source="material_first_boundary_acceptance_report.json",
    )


def _remotion_material_first_memory_summary(root: Path):
    report_path, report = _find_json(root, "remotion_material_first_memory_acceptance_report.json")
    if not report:
        return None

    read = [_rel(root, report_path)]
    handoff_path, handoff = _find_json(root, "remotion_effect_handoff.json")
    if handoff:
        read.append(_rel(root, handoff_path))
    if report.get("ok") is False:
        failed_stage = report.get("failed_stage") or "remotion_material_first_memory_acceptance"
        errors = [str(item) for item in report.get("errors") or [] if item]
        reason = "; ".join(errors) or f"Remotion material-first memory acceptance failed at {failed_stage}"
        return _contract(
            "repair",
            failed_stage,
            next_action=report.get("next_action"),
            reason=reason,
            read=read,
            run_dir=root,
            source="remotion_material_first_memory_acceptance_report.json",
        )

    summary = report.get("summary") or {}
    selected = summary.get("selected_ref_count", 0)
    component = summary.get("build_component") or "Remotion effect"
    handoff_note = ""
    if handoff:
        count = len(handoff.get("accepted_assets") or [])
        handoff_note = f"; handoff ready with {count} accepted asset(s)"
    return _contract(
        "run",
        "remotion_material_first_memory_acceptance",
        next_action=report.get("next_action") or "ready_for_human_effect_review_or_pipeline_promotion",
        reason=f"{component} material-first effect acceptance passed: {selected} refs{handoff_note}",
        read=read,
        run_dir=root,
        source="remotion_material_first_memory_acceptance_report.json",
    )


def _effect_factory_boundary_summary(root: Path):
    report_path, report = _find_json(root, "effect_factory_boundary_acceptance_report.json")
    if not report:
        return None

    read = [_rel(root, report_path)]
    handoff_path, handoff = _find_json(root, "effect_handoff.json")
    if handoff:
        read.append(_rel(root, handoff_path))
    summary = report.get("summary") or {}
    if report.get("ok") is False:
        errors = [str(item) for item in report.get("validation_errors") or [] if item]
        reason = "; ".join(errors) or "Effect Factory boundary acceptance failed"
        return _contract(
            "repair",
            report.get("failed_stage") or "effect_factory_boundary",
            next_action=report.get("next_action"),
            reason=reason,
            read=read,
            run_dir=root,
            source="effect_factory_boundary_acceptance_report.json",
        )

    family_count = len(report.get("style_signatures") or [])
    job_count = summary.get("job_count", 0)
    rendered_count = summary.get("rendered_count", 0)
    return _contract(
        "run",
        "effect_factory_boundary",
        next_action=report.get("next_action") or "ready_for_human_effect_review_or_pipeline_promotion",
        reason=(
            "Effect Factory boundary passed: "
            f"{family_count} semantic families, {rendered_count}/{job_count} dry-run worker outputs"
        ),
        read=read,
        run_dir=root,
        source="effect_factory_boundary_acceptance_report.json",
    )


def _effect_factory_route_summary(root: Path):
    report_path, report = _find_json(root, "effect_factory_route_acceptance_report.json")
    if not report:
        return None

    read = [_rel(root, report_path)]
    handoff_path, handoff = _find_json(root, "effect_handoff.json")
    if handoff:
        read.append(_rel(root, handoff_path))
    summary = report.get("summary") or {}
    if report.get("ok") is False:
        errors = [str(item) for item in report.get("validation_errors") or [] if item]
        reason = "; ".join(errors) or "Effect Factory route acceptance failed"
        return _contract(
            "repair",
            report.get("failed_stage") or "effect_factory_route_acceptance",
            next_action=report.get("next_action"),
            reason=reason,
            read=read,
            run_dir=root,
            source="effect_factory_route_acceptance_report.json",
        )

    style_family = summary.get("style_family") or "unknown_style"
    rendered_count = summary.get("worker_rendered_count", 0)
    job_count = summary.get("worker_job_count", 0)
    capability = summary.get("capability_decision") or "unknown_capability"
    return _contract(
        "run",
        "effect_factory_route_acceptance",
        next_action=report.get("next_action") or "ready_for_human_effect_review_or_pipeline_promotion",
        reason=(
            "Effect Factory route acceptance passed: "
            f"{style_family}, capability={capability}, "
            f"{rendered_count}/{job_count} dry-run worker outputs"
        ),
        read=read,
        run_dir=root,
        source="effect_factory_route_acceptance_report.json",
    )


def _visual_technique_summary(root: Path):
    confirmed_path, confirmed = _find_json(root, "visual_technique_plan.confirmed.json")
    plan_path, plan = (confirmed_path, confirmed) if confirmed else _find_json(root, "visual_technique_plan.json")
    if not plan:
        return None

    read = [_rel(root, plan_path)]
    candidate_path = None
    candidate = None
    if confirmed:
        candidate_path, candidate = _find_json(root, "visual_technique_plan.json")
        if candidate:
            read.append(_rel(root, candidate_path))
    review_path, review = _find_json(root, "visual_technique_review.json")
    if review:
        read.append(_rel(root, review_path))
    handoff_to = str(plan.get("handoff_to") or "")
    style = str(plan.get("style_family") or "unknown_style")
    role = str(plan.get("effect_role") or "unknown_role")
    options = [
        str(item.get("option_id") or item.get("label") or item)
        for item in plan.get("candidate_options") or []
        if item
    ]
    option_note = f"; options={', '.join(options)}" if options else ""
    if handoff_to == "review_candidate_parameters":
        if review:
            selected = str(review.get("selected_option") or review.get("option_id") or "").strip()
            selected_note = f": selected={selected}" if selected else ""
            return _contract(
                "repair",
                "effect_factory_parameter_review_apply",
                next_action="visual-technique-review-apply",
                reason=f"visual technique review awaits apply{selected_note}",
                read=read,
                run_dir=root,
                source="visual_technique_review.json",
            )
        return _contract(
            "repair",
            "effect_factory_parameter_review",
            next_action="review_visual_technique_plan_or_rerun_with_confirmed",
            reason=f"visual technique candidate awaits review: {style}/{role}{option_note}",
            read=read,
            run_dir=root,
            source="visual_technique_plan.json",
        )
    if handoff_to == "remotion_prompt_parameters":
        source = "visual_technique_plan.confirmed.json" if confirmed else "visual_technique_plan.json"
        return _contract(
            "run",
            "effect_factory_contract",
            next_action="effect_contract_or_remotion_prompt_pack",
            reason=f"visual technique confirmed for effect contract: {style}/{role}",
            read=read,
            run_dir=root,
            source=source,
        )
    return _contract(
        "repair",
        "effect_factory_parameter_review",
        next_action="fix_visual_technique_plan",
        reason=f"visual technique plan has unsupported handoff_to={handoff_to or 'missing'}",
        read=read,
        run_dir=root,
        source="visual_technique_plan.json",
    )


def _generated_material_summary(root: Path):
    quality_path, quality = _find_json_name_or_role(
        root,
        "generated_material_quality_review.json",
        "generated_material_quality_review",
    )
    review_path, review = _find_json_name_or_role(
        root,
        "generated_material_review.json",
        "generated_material_review",
    )
    delta_path, delta = _find_json(root, "delta_after_generated_review.json")
    fallback_path, fallback = _find_json(root, "material_generation_fallback.json")
    packet_path, packet = _find_json_name_or_role(
        root,
        "generated_provider_packet.json",
        "generated_image_provider_packet",
    )
    handoff_path, handoff = _find_json_name_or_role(
        root,
        "image_agent_prompt_handoff.json",
        "image_agent_prompt_handoff",
    )
    outputs_path, outputs = _find_json(root, "generated_provider_outputs.json")
    production_path, production = _find_json_name_or_role(
        root,
        "generated_material_production.json",
        "generated_material_production",
    )
    if not any((quality, review, delta, fallback, packet, outputs, production)):
        return None

    read = []
    for path in (
        quality_path,
        review_path,
        delta_path,
        fallback_path,
        packet_path,
        handoff_path,
        outputs_path,
        production_path,
    ):
        rel = _rel(root, path)
        if rel and rel not in read:
            read.append(rel)

    if quality and quality.get("pass") is False:
        blocking = quality.get("blocking") or quality.get("findings") or []
        reason = "generated material quality review failed"
        if blocking:
            reason += ": " + "; ".join(
                str(item.get("message") or item.get("rule") or item)
                for item in blocking[:3]
                if item
            )
        return _contract(
            "repair",
            "generated_material_review",
            next_action="repair_generated_material_candidates",
            resume="stage2_material_map",
            reason=reason,
            read=read,
            run_dir=root,
            source=_rel(root, quality_path),
        )

    decisions = review.get("decisions") if isinstance(review, dict) else None
    if isinstance(decisions, list) and decisions:
        accepted_statuses = {"accept", "accepted", "approve", "approved", "keep", "selected", "use"}
        accepted = [
            item for item in decisions
            if str((item or {}).get("status") or "").strip().casefold() in accepted_statuses
        ]
        if not accepted:
            return _contract(
                "repair",
                "generated_material_review",
                next_action="repair_generated_material_candidates",
                resume="stage2_material_map",
                reason=f"generated material review rejected all {len(decisions)} candidate(s)",
                read=read,
                run_dir=root,
                source=_rel(root, review_path),
            )

    if isinstance(delta, dict) and (
        delta.get("ready_for_build") is False
        or delta.get("blocks_ready_for_build") is True
    ):
        summary = delta.get("summary") if isinstance(delta.get("summary"), dict) else {}
        missing = summary.get("missing")
        reason = "generated material delta is not ready for build"
        if missing is not None:
            reason += f": missing={missing}"
        return _contract(
            "repair",
            "generated_material_review",
            next_action="repair_generated_material_candidates",
            resume="stage2_material_map",
            reason=reason,
            read=read,
            run_dir=root,
            source=_rel(root, delta_path),
        )

    if packet and handoff and not outputs and not production:
        item_count = len(handoff.get("items") or []) if isinstance(handoff, dict) else 0
        return _contract(
            "waiting",
            "generated_image_agent",
            next_action="call_image_generation_agent",
            resume="generated-material-import",
            reason=f"image agent handoff awaits real generated images: {item_count} image(s)",
            read=read,
            run_dir=root,
            source=_rel(root, handoff_path),
        )

    if packet and not outputs and not production:
        item_count = len(packet.get("items") or []) if isinstance(packet, dict) else 0
        return _contract(
            "waiting",
            "generated_image_provider",
            next_action="wait_for_generated_provider",
            resume="generated-material-import",
            reason=f"generated image provider packet awaits real provider output: {item_count} image(s)",
            read=read,
            run_dir=root,
            source=_rel(root, packet_path),
        )

    if outputs and not production:
        return _contract(
            "run",
            "generated_material_import",
            next_action="generated-material-import",
            resume="stage2_material_map",
            reason="generated provider outputs are ready for import and quality review",
            read=read,
            run_dir=root,
            source=_rel(root, outputs_path),
        )

    if fallback and not review:
        return _contract(
            "run",
            "generated_image_provider",
            next_action="generated-image-provider-packet",
            resume="stage2_material_map",
            reason="generated material fallback jobs need a real provider packet",
            read=read,
            run_dir=root,
            source=_rel(root, fallback_path),
        )
    return None


def _soundtrack_summary(root: Path):
    plan_path, plan = _find_json(root, "soundtrack_plan.json")
    license_path, license_manifest = _find_json(root, "sound_license_manifest.json")
    handoff_path, handoff = _find_json(root, "audio_director_handoff.json")
    if not (plan or license_manifest or handoff):
        return None

    read = []
    for path in (plan_path, license_path, handoff_path):
        rel = _rel(root, path)
        if rel and rel not in read:
            read.append(rel)

    blocks = []
    if isinstance(handoff, dict):
        blocks.extend(str(item) for item in handoff.get("blocks") or [] if item)
    if isinstance(license_manifest, dict):
        blocks.extend(str(item) for item in license_manifest.get("blocked_reasons") or [] if item)
        if license_manifest.get("delivery_allowed") is False and not blocks:
            blocks.append("license_not_deliverable")
    blocks = sorted(set(blocks))

    if blocks or (handoff and handoff.get("ready_for_audio_director") is False):
        return _contract(
            "repair",
            "soundtrack_review",
            next_action="resolve_soundtrack_license_or_reference_only",
            resume="audio_director",
            reason="soundtrack blocks: " + ", ".join(blocks or ["not ready for audio director"]),
            read=read,
            run_dir=root,
            source="audio_director_handoff.json" if handoff else "sound_license_manifest.json",
        )

    if handoff and handoff.get("ready_for_audio_director") is True:
        section_count = len(plan.get("sections") or []) if isinstance(plan, dict) else 0
        return _contract(
            "run",
            "audio_director",
            next_action="tts_mix_ducking_or_audio_director",
            reason=f"soundtrack handoff ready for Audio Director: {section_count} section(s)",
            read=read,
            run_dir=root,
            source="audio_director_handoff.json",
        )

    return _contract(
        "repair",
        "soundtrack_review",
        next_action="write_or_fix_audio_director_handoff",
        reason="soundtrack artifacts exist but audio_director_handoff.json is missing or incomplete",
        read=read,
        run_dir=root,
        source="soundtrack_plan.json" if plan else None,
    )


def _audio_acceptance_summary(root: Path):
    acceptance_path, acceptance = _find_json(root, "audio_handoff_acceptance.json")
    mix_path, mix_plan = _find_json(root, "audio_mix_plan.json")
    if not (acceptance or mix_plan):
        return None

    read = []
    for path in (acceptance_path, mix_path):
        rel = _rel(root, path)
        if rel and rel not in read:
            read.append(rel)

    if acceptance and acceptance.get("ok") is False:
        blocking = acceptance.get("blocking") or []
        reason = "; ".join(
            str(item.get("rule") or item.get("message") or item)
            for item in blocking
            if item
        ) or "audio handoff acceptance failed"
        return _contract(
            "repair",
            "audio_handoff_acceptance",
            next_action=acceptance.get("next_action") or "repair_audio_handoff",
            resume="audio_director",
            reason=reason,
            read=read,
            run_dir=root,
            source="audio_handoff_acceptance.json",
        )

    if acceptance and acceptance.get("ok") is True and mix_plan and mix_plan.get("ready_for_mix") is True:
        track_count = len(mix_plan.get("tracks") or [])
        return _contract(
            "run",
            "audio_mix",
            next_action="mix_audio_from_audio_mix_plan",
            reason=f"audio handoff accepted: {track_count} accepted track(s)",
            read=read,
            run_dir=root,
            source="audio_mix_plan.json",
        )

    return _contract(
        "repair",
        "audio_handoff_acceptance",
        next_action="soundtrack-audio-handoff-accept",
        reason="audio handoff artifacts are incomplete",
        read=read,
        run_dir=root,
        source="audio_handoff_acceptance.json" if acceptance else "audio_mix_plan.json",
    )


def _audio_ready_summary(root: Path):
    final_audio = root / "final_audio.wav"
    report_path, report = _find_json(root, "audio_mix_report.json")
    if not (final_audio.is_file() or report):
        return None

    read = []
    if final_audio.is_file():
        read.append(_rel(root, final_audio))
    rel_report = _rel(root, report_path)
    if rel_report and rel_report not in read:
        read.append(rel_report)

    if not final_audio.is_file():
        return _contract(
            "repair",
            "audio_ready",
            next_action="write_final_audio_from_audio_mix_report",
            resume="audio_director",
            reason="audio_mix_report exists but final_audio.wav is missing",
            read=read,
            run_dir=root,
            source="audio_mix_report.json",
        )
    if report and report.get("ok") is False:
        blocking = report.get("blocking") or []
        reason = "; ".join(
            str(item.get("rule") or item.get("message") or item)
            for item in blocking
            if item
        ) or "audio_mix_report blocks delivery"
        return _contract(
            "repair",
            "audio_ready",
            next_action=report.get("next_action") or "repair_audio_mix_plan",
            resume="audio_director",
            reason=reason,
            read=read,
            run_dir=root,
            source="audio_mix_report.json",
        )
    if report and report.get("audio_stream_present") is False:
        return _contract(
            "repair",
            "audio_ready",
            next_action="repair_audio_mix_report",
            resume="audio_director",
            reason="audio_mix_report declares no audio stream",
            read=read,
            run_dir=root,
            source="audio_mix_report.json",
        )
    return _contract(
        "run",
        "audio_ready",
        next_action="return_to_build_with_final_audio",
        reason="final_audio.wav and audio_mix_report.json are ready",
        read=read,
        run_dir=root,
        source="audio_mix_report.json" if report else "final_audio.wav",
    )


def _audio_build_handoff_summary(root: Path):
    handoff_path, handoff = _find_json(root, "audio_build_handoff.json")
    if not handoff:
        return None
    read = [_rel(root, handoff_path)]
    selected_audio = handoff.get("selected_audio")
    if handoff.get("audio_ready") is not True or not selected_audio:
        return _contract(
            "repair",
            "audio_build_handoff",
            next_action="repair_audio_build_handoff",
            resume="audio_director",
            reason="audio_build_handoff exists but does not declare audio_ready selected_audio",
            read=read,
            run_dir=root,
            source="audio_build_handoff.json",
        )
    return _contract(
        "run",
        "audio_build_handoff",
        next_action="continue_build_or_material_gate",
        reason=f"BUILD audio handoff uses {Path(str(selected_audio)).name}",
        read=read,
        run_dir=root,
        source="audio_build_handoff.json",
    )


def _subtitle_voiceover_handoff_summary(root: Path):
    acceptance_path, acceptance = _find_json(root, "subtitle_voiceover_handoff_acceptance.json")
    handoff_path, handoff = _find_json(root, "subtitle_voiceover_build_handoff.json")
    if not (acceptance or handoff):
        return None
    read = []
    for path in (acceptance_path, handoff_path):
        rel = _rel(root, path)
        if rel and rel not in read:
            read.append(rel)
    if acceptance and acceptance.get("ok") is False:
        blocking = acceptance.get("blocking") or []
        reason = "; ".join(
            str(item.get("rule") or item.get("message") or item)
            for item in blocking
            if item
        ) or "subtitle/voiceover handoff acceptance failed"
        return _contract(
            "repair",
            "subtitle_voiceover_handoff",
            next_action=acceptance.get("next_action") or "repair_subtitle_voiceover_handoff",
            resume="subtitle_voiceover",
            reason=reason,
            read=read,
            run_dir=root,
            source="subtitle_voiceover_handoff_acceptance.json",
        )
    if handoff and (
        handoff.get("subtitle_ready") is True
        or handoff.get("voiceover_ready") is True
    ):
        ready = []
        if handoff.get("subtitle_ready") is True:
            ready.append("subtitles")
        if handoff.get("voiceover_ready") is True:
            ready.append("voiceover")
        return _contract(
            "run",
            "subtitle_voiceover_build_handoff",
            next_action="continue_build_or_material_gate",
            reason="subtitle/voiceover BUILD handoff ready: " + ", ".join(ready),
            read=read,
            run_dir=root,
            source="subtitle_voiceover_build_handoff.json",
        )
    return _contract(
        "repair",
        "subtitle_voiceover_handoff",
        next_action="subtitle-voiceover-handoff-accept",
        reason="subtitle/voiceover handoff artifacts are incomplete",
        read=read,
        run_dir=root,
        source="subtitle_voiceover_build_handoff.json" if handoff else "subtitle_voiceover_handoff_acceptance.json",
    )


def _stage0_subtitle_voiceover_gap_summary(root: Path):
    intent_path, intent = _find_json(root, "video_intent.json")
    if not intent:
        return None
    contract = intent.get("subtitle_voiceover_contract")
    if not isinstance(contract, dict):
        return None
    subtitle_required = contract.get("subtitle_required") is True
    voiceover_required = contract.get("voiceover_required") is True
    if not (subtitle_required or voiceover_required):
        return None

    _handoff_path, handoff = _find_json(root, "subtitle_voiceover_build_handoff.json")
    if isinstance(handoff, dict):
        subtitle_ready = handoff.get("subtitle_ready") is True
        voiceover_ready = handoff.get("voiceover_ready") is True
        if (not subtitle_required or subtitle_ready) and (not voiceover_required or voiceover_ready):
            return None

    required = []
    if subtitle_required:
        required.append("subtitles")
    if voiceover_required:
        required.append("voiceover")
    return _contract(
        "repair",
        "subtitle_voiceover_handoff",
        next_action="subtitle-voiceover-handoff-accept",
        resume="subtitle_voiceover",
        reason="Stage 0 requires " + " and ".join(required) + " before BUILD handoff",
        read=[_rel(root, intent_path)],
        run_dir=root,
        source="video_intent.json",
    )


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


def _verify_summary(root: Path):
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
    return None


def _delivery_gate_summary(root: Path):
    gate_path, gate = _find_json(root, "delivery_gate.json")
    if not gate:
        return None
    read = [_rel(root, gate_path)]
    promotion_path, promotion = _find_json(root, "final_promotion_report.json")
    if promotion:
        read.append(_rel(root, promotion_path))
    if gate.get("pass") is True and (root / "final.mp4").exists():
        return _contract(
            "done",
            "complete",
            reason=(
                "delivery gate passed and final.mp4 exists"
                + (" after explicit preview promotion" if promotion else "")
            ),
            read=read,
            run_dir=root,
            source="delivery_gate.json",
        )
    if gate.get("pass") is True:
        return _contract(
            "run",
            "stage5_final_review",
            next_action="promote_or_package_verified_preview",
            reason="delivery gate passed for a verified preview candidate; final.mp4 is not present",
            read=read,
            run_dir=root,
            source="delivery_gate.json",
        )
    if gate.get("pass") is False:
        blocking = gate.get("blocking") or []
        reason = "; ".join(
            str(item.get("message") or item.get("rule") or item)
            for item in blocking
            if item
        ) or "delivery gate failed"
        return _contract(
            "repair",
            "stage5_final_review",
            next_action=gate.get("next_action") or "repair_delivery_gate",
            reason=reason,
            read=read,
            run_dir=root,
            source="delivery_gate.json",
        )
    return None


def _verified_preview_package_summary(root: Path):
    package_path, package = _find_json(root, "verified_preview_package.json")
    if not package:
        return None
    if (root / "final.mp4").exists():
        return None
    _gate_path, gate = _find_json(root, "delivery_gate.json")
    if isinstance(gate, dict) and gate.get("pass") is False:
        return None
    read = [_rel(root, package_path)]
    for ref_key in ("packaged_video", "review_packet", "review_report_md"):
        ref = package.get(ref_key)
        if ref:
            rel = _rel(root, ref)
            if rel and rel not in read:
                read.append(rel)
    status = str(package.get("status") or "").strip()
    if status == "ready_for_operator_delivery_review":
        return _contract(
            "run",
            "verified_preview_delivery_candidate",
            next_action=package.get("next_action") or "operator_review_or_explicit_final_promotion",
            reason=(
                "verified preview package is ready for operator delivery review; "
                "final.mp4 has not been promoted"
            ),
            read=read,
            run_dir=root,
            source="verified_preview_package.json",
        )
    return _contract(
        "repair",
        "verified_preview_delivery_candidate",
        next_action="repair_verified_preview_package",
        reason=f"verified_preview_package has unsupported status={status or 'missing'}",
        read=read,
        run_dir=root,
        source="verified_preview_package.json",
    )


def _verified_preview_review_decision_summary(root: Path):
    decision_path, decision = _find_json(root, "verified_preview_review_decision.json")
    if not decision:
        return None
    if (root / "final.mp4").exists():
        return None
    package_path, package = _find_json(root, "verified_preview_package.json")
    read = [_rel(root, decision_path)]
    if package_path:
        read.append(_rel(root, package_path))
    candidate = decision.get("candidate_video") or (package or {}).get("packaged_video")
    candidate_ref = _rel(root, candidate)
    if candidate_ref and candidate_ref not in read:
        read.append(candidate_ref)
    if isinstance(package, dict):
        for ref_key in ("review_packet", "review_report_md"):
            ref = _rel(root, package.get(ref_key))
            if ref and ref not in read:
                read.append(ref)
    handoff_path, handoff = _find_json(root, "workbench_handoff.json")
    if handoff_path:
        handoff_ref = _rel(root, handoff_path)
        if handoff_ref and handoff_ref not in read:
            read.append(handoff_ref)
    if isinstance(handoff, dict):
        for ref in (handoff.get("artifacts") or {}).values():
            rel = _rel(root, ref)
            if rel and rel not in read:
                read.append(rel)

    mode = decision.get("mode")
    if mode not in {"run", "repair", "waiting"}:
        mode = "repair" if decision.get("decision") in {"rebuild_motion_preview", "reject"} else "run"
    next_action = decision.get("next_action") or "review_verified_preview_decision"
    return _contract(
        mode,
        "verified_preview_review_decision",
        next_action=next_action,
        reason=f"verified preview operator decision={decision.get('decision')}: {next_action}",
        read=read,
        run_dir=root,
        source="verified_preview_review_decision.json",
    )


def _build_summary(root: Path):
    timeline_path, timeline = _find_json(root, "timeline_build.json")
    editor_path, editor = _find_json(root, "editor_review.json")
    if timeline and editor:
        return _contract(
            "run",
            "stage5_final_review",
            next_action=f"python tools/boundary_smoke.py {root}",
            reason="timeline/editor artifacts are ready for final review",
            read=[_rel(root, timeline_path), _rel(root, editor_path)],
            run_dir=root,
            source="timeline_build.json",
        )

    contract_path, contract = _find_json(root, "segment_contract.json")
    if contract:
        return _contract(
            "run",
            "stage4_dry_build",
            next_action=f"python tools/boundary_smoke.py {root}",
            reason="segment contract is ready for dry-build planning",
            read=[_rel(root, contract_path)],
            run_dir=root,
            source="segment_contract.json",
        )
    return None


def _source_highlight_summary(root: Path):
    timeline_path, timeline = _find_json(root, "source_timeline_map.json")
    selection_path, selection = _find_json(root, "highlight_selection_plan.json")
    rough_path, rough = _find_json(root, "rough_cut_plan.json")
    if not (timeline and selection and rough):
        return None

    read = [_rel(root, path) for path in (timeline_path, selection_path, rough_path) if path]
    highlight_path, highlight = _find_json(root, "highlight_cut_report.json")
    candidate_names = [
        "final.mp4",
        "highlight_final_quiet.mp4",
        "highlight_safe.mp4",
        "highlight_final.mp4",
    ]
    candidate = next((name for name in candidate_names if (root / name).is_file()), None)
    if highlight_path:
        read.append(_rel(root, highlight_path))
    if not candidate and isinstance(highlight, dict):
        reported_out = highlight.get("out") or highlight.get("output")
        if reported_out:
            reported_path = Path(str(reported_out))
            if not reported_path.is_absolute():
                reported_path = root / reported_path
            if reported_path.is_file():
                candidate = _rel(root, reported_path) or reported_path.name

    if candidate:
        return _contract(
            "run",
            "stage5_final_review",
            next_action="write_delivery_gate_report_or_review_highlight_candidate",
            reason=f"single-source highlight candidate ready: {candidate}",
            read=read + [candidate],
            run_dir=root,
            source="highlight_selection_plan.json",
        )

    return _contract(
        "run",
        "stage4_highlight_build",
        next_action="safe_highlight_cut",
        reason="source highlight plan is ready but no playable highlight candidate was found",
        read=read,
        run_dir=root,
        source="highlight_selection_plan.json",
    )


def _one_source_dialogue_preview_summary(root: Path):
    script_path, script = _find_json_by_role(
        root,
        "dialogue_edit_script",
        prefer_reviewed=True,
    )
    windows_path, windows = _find_json_by_role(
        root,
        "dialogue_highlight_windows",
        prefer_reviewed=True,
    )
    highlight_path, highlight = _find_json_name_or_role(
        root,
        "highlight_cut_report.json",
        "highlight_cut_report",
    )
    verify_path, verify = _find_json_name_or_role(
        root,
        "final_product_verify_bundle.json",
        "final_product_verify_bundle",
    )
    if not (script or windows or highlight or verify):
        return None

    read = []
    for path in (script_path, windows_path, highlight_path, verify_path):
        rel = _rel(root, path)
        if rel and rel not in read:
            read.append(rel)

    reviewed = bool(
        script
        and str(script.get("review_status") or "").strip().casefold()
        in {"reviewed", "reviewed_by_operator", "agent_reviewed", "accepted", "approved"}
    )
    if script and not reviewed:
        return _contract(
            "waiting",
            "dialogue_script_review",
            next_action="review_dialogue_edit_script_then_cut",
            reason="one-source dialogue script exists but is not reviewed",
            read=read,
            run_dir=root,
            source=_rel(root, script_path),
        )

    if script and not highlight:
        return _contract(
            "run",
            "stage4_highlight_build",
            next_action="safe_highlight_cut",
            reason="reviewed dialogue script is ready for safe highlight cut",
            read=read,
            run_dir=root,
            source=_rel(root, script_path),
        )

    output_path = None
    if highlight:
        output_path = highlight.get("out") or highlight.get("output")
    output_exists = bool(output_path and Path(str(output_path)).is_file())
    output_probe = highlight.get("output_probe") if isinstance(highlight, dict) else {}
    playable = bool(
        highlight
        and (
            output_exists
            or (
                isinstance(output_probe, dict)
                and output_probe.get("video")
                and output_probe.get("audio")
            )
        )
    )
    if highlight and not playable:
        return _contract(
            "repair",
            "stage4_highlight_build",
            next_action="repair_safe_highlight_cut",
            reason="highlight_cut_report exists but playable output evidence is missing",
            read=read,
            run_dir=root,
            source=_rel(root, highlight_path),
        )

    if highlight and not verify:
        return _contract(
            "run",
            "stage5_final_review",
            next_action="final-product-verify",
            reason="one-source dialogue highlight cut exists and needs final-product-verify",
            read=read,
            run_dir=root,
            source=_rel(root, highlight_path),
        )

    verify_pass = bool(verify and verify.get("pass") is True)
    if verify and not verify_pass:
        return _contract(
            "repair",
            "stage5_final_review",
            next_action=verify.get("next_action") or "repair_final_product_verify_evidence",
            reason="one-source dialogue preview failed final-product-verify",
            read=read,
            run_dir=root,
            source=_rel(root, verify_path),
        )

    if verify_pass:
        clip_count = script.get("clip_count") if isinstance(script, dict) else None
        duration = (
            highlight.get("duration_sec")
            if isinstance(highlight, dict)
            else script.get("planned_duration_sec") if isinstance(script, dict) else None
        )
        reason = "one-source dialogue preview verified"
        if clip_count is not None:
            reason += f": {clip_count} clip(s)"
        if duration is not None:
            reason += f", {duration}s"
        return _contract(
            "run",
            "stage5_final_review",
            next_action="write_delivery_gate_report_or_promote_one_source_preview",
            reason=reason,
            read=read,
            run_dir=root,
            source=Path(str(script_path)).name if script_path else "dialogue_edit_script.json",
        )
    return None


def _story_summary(root: Path):
    story_path, story = _find_json(root, "story_world.json")
    beats_path, beats = _find_json(root, "screenplay_beats.json")
    needs_path, needs = _find_json(root, "material_needs.json")
    if story and beats and needs:
        return _contract(
            "run",
            "stage2_material_map",
            next_action="material-map lifecycle / material acquisition",
            reason="story blueprint artifacts are ready for material mapping",
            read=[_rel(root, story_path), _rel(root, beats_path), _rel(root, needs_path)],
            run_dir=root,
            source="material_needs.json",
        )
    return None


def _material_wall_handoff_summary(root: Path):
    report_path, report = _find_json(root, "material_wall_handoff_report.json")
    if not report:
        return None

    selected = len(report.get("selected_asset_ids") or [])
    rejected = len(report.get("rejected_asset_ids") or [])
    duplicate_assets = len(report.get("duplicate_asset_ids") or [])
    missing = [str(item) for item in report.get("missing_need_ids") or []]
    duplicate_needs = [str(item) for item in report.get("duplicate_need_ids") or []]
    read = [_rel(root, report_path)]
    if missing or report.get("ready_for_mapping") is False:
        parts = []
        if missing:
            parts.append("missing needs: " + ", ".join(missing))
        if duplicate_needs:
            parts.append("duplicate needs: " + ", ".join(duplicate_needs))
        parts.append(
            f"selected={selected}, rejected={rejected}, duplicate_assets={duplicate_assets}"
        )
        return _contract(
            "repair",
            "stage2_material_wall_review",
            resume="stage3_review_apply",
            reason="; ".join(parts),
            read=read,
            run_dir=root,
            source="material_wall_handoff_report.json",
        )
    return _contract(
        "run",
        "stage3_review_apply",
        next_action="material-map review apply / lifecycle",
        reason=(
            f"material wall handoff ready: selected={selected}, rejected={rejected}, "
            f"duplicate_assets={duplicate_assets}"
        ),
        read=read,
        run_dir=root,
        source="material_wall_handoff_report.json",
    )


def _material_inventory_summary(root: Path):
    summary_path, summary = _find_json(root, "material_inventory_summary.json")
    if not summary:
        return None
    counts = summary.get("counts") if isinstance(summary.get("counts"), dict) else {}
    total = counts.get("total_files", 0)
    videos = counts.get("videos", 0)
    images = counts.get("images", 0)
    audio = counts.get("audio", 0)
    actions = [
        str(item)
        for item in summary.get("recommended_next_actions") or []
        if str(item).strip()
    ]
    next_action = actions[0] if actions else "review_material_inventory_summary"
    return _contract(
        "waiting",
        "material_inventory_review",
        next_action=next_action,
        reason=(
            f"material quick inventory ready: {total} file(s), "
            f"{videos} video(s), {images} image(s), {audio} audio file(s)"
        ),
        read=[_rel(root, summary_path)],
        run_dir=root,
        source="material_inventory_summary.json",
    )


def _intent_summary(root: Path):
    intent_path, intent = _find_json(root, "video_intent.json")
    if not intent:
        return None

    entry_path = str(intent.get("entry_path") or intent.get("route") or "").strip()
    route_hint = str(
        intent.get("semantic_route_hint")
        or intent.get("specialized_route")
        or intent.get("handoff_branch")
        or ""
    ).strip()
    route_hint = route_hint.replace("_", "-").casefold()
    effect_policy = intent.get("effect_policy") if isinstance(intent.get("effect_policy"), dict) else {}
    effect_activation = str(effect_policy.get("activation") or "").strip().casefold()
    effect_required_now = effect_policy.get("required_now") is True
    questions = [str(item) for item in intent.get("required_followup_questions") or [] if item]
    if questions:
        reason = "needs context before route handoff"
        reason = "needs context: " + "; ".join(questions[:3])
        if route_hint:
            reason += f"; route hint held for later: {route_hint}"
        return _contract(
            "waiting",
            "stage0_video_intent",
            next_action="ask_followup_questions",
            reason=reason,
            read=[_rel(root, intent_path)],
            run_dir=root,
            source="video_intent.json",
        )
    if entry_path == "needs-context":
        reason = "needs context before route handoff"
        if route_hint:
            reason += f"; route hint held for later: {route_hint}"
        return _contract(
            "waiting",
            "stage0_video_intent",
            next_action="ask_followup_questions",
            reason=reason,
            read=[_rel(root, intent_path)],
            run_dir=root,
            source="video_intent.json",
        )
    if route_hint in {"brownfield", "brownfield-edit", "workbench", "draft-edit", "rough-cut-edit"}:
        return _contract(
            "run",
            "workbench_draft_review",
            next_action="workbench-handoff-validate",
            reason=f"video intent requests bounded draft/brownfield review: {route_hint}",
            read=[_rel(root, intent_path)],
            run_dir=root,
            source="video_intent.json",
        )
    if route_hint in {"final-review", "verify", "delivery-review", "existing-final-review"}:
        return _contract(
            "run",
            "stage5_final_review",
            next_action="verify_existing_final_or_delivery_gate",
            reason=f"video intent requests existing final review: {route_hint}",
            read=[_rel(root, intent_path)],
            run_dir=root,
            source="video_intent.json",
        )
    effect_hint = route_hint in {"effect-factory", "effect-only", "effects", "visual-effect"}
    effect_hint_is_primary = (
        effect_hint
        and (
            not effect_policy
            or effect_required_now
            or effect_activation == "route_to_effect_factory"
        )
    )
    if effect_hint_is_primary:
        return _contract(
            "run",
            "effect_factory_parameter_review",
            next_action="visual-technique-plan",
            reason=f"video intent requests Effect Factory route: {route_hint}",
            read=[_rel(root, intent_path)],
            run_dir=root,
            source="video_intent.json",
        )
    material_first = {"material-first", "existing-material-first", "hybrid"}
    structure_first = {"structure-first", "story-first"}
    if entry_path in material_first:
        scan = intent.get("material_scan_decision") if isinstance(intent.get("material_scan_decision"), dict) else {}
        if scan.get("needed") is True and scan.get("scan_depth") == "quick_inventory_first":
            return _contract(
                "run",
                "stage2_material_inventory",
                next_action="material-quick-inventory",
                reason="video intent requests material-first quick inventory before deep material map",
                read=[_rel(root, intent_path)],
                run_dir=root,
                source="video_intent.json",
            )
        return _contract(
            "run",
            "stage2_material_map",
            next_action="material-map lifecycle / material acquisition",
            reason=f"video intent entry_path is {entry_path}",
            read=[_rel(root, intent_path)],
            run_dir=root,
            source="video_intent.json",
        )
    if entry_path in structure_first:
        return _contract(
            "run",
            "stage1_story_blueprint",
            next_action="story-soul-blueprint / structure planner",
            reason=f"video intent entry_path is {entry_path}",
            read=[_rel(root, intent_path)],
            run_dir=root,
            source="video_intent.json",
        )
    return _contract(
        "repair",
        "stage0_video_intent",
        next_action="video-intent-plan",
        reason="video_intent.json does not declare a recognized entry_path",
        read=[_rel(root, intent_path)],
        run_dir=root,
        source="video_intent.json",
    )


def summarize_run(run_dir):
    root = Path(run_dir).resolve()

    summary = _verified_preview_review_decision_summary(root)
    if summary:
        return summary

    summary = _verified_preview_package_summary(root)
    if summary:
        return summary

    summary = _delivery_gate_summary(root)
    if summary:
        return summary

    summary = _generated_material_summary(root)
    if summary:
        return summary

    summary = _effect_factory_route_summary(root)
    if summary:
        return summary

    summary = _effect_factory_boundary_summary(root)
    if summary:
        return summary

    summary = _visual_technique_summary(root)
    if summary:
        return summary

    summary = _remotion_material_first_memory_summary(root)
    if summary:
        return summary

    acceptance_summary = _acceptance_summary(root)
    if acceptance_summary and acceptance_summary.get("mode") == "repair":
        return acceptance_summary

    if not acceptance_summary:
        summary = _subtitle_voiceover_handoff_summary(root)
        if summary:
            return summary

        summary = _stage0_subtitle_voiceover_gap_summary(root)
        if summary:
            return summary

    summary = _audio_build_handoff_summary(root)
    if summary:
        return summary

    summary = _audio_ready_summary(root)
    if summary:
        return summary

    summary = _audio_acceptance_summary(root)
    if summary:
        return summary

    summary = _soundtrack_summary(root)
    if summary:
        return summary

    if acceptance_summary:
        return acceptance_summary

    summary = _subtitle_voiceover_handoff_summary(root)
    if summary:
        return summary

    summary = _stage0_subtitle_voiceover_gap_summary(root)
    if summary:
        return summary

    _boundary_path, boundary = _find_json(root, "boundary_report.json")
    if boundary:
        summary = _boundary_summary(root, boundary)
        if summary:
            return summary

    summary = _verify_summary(root)
    if summary:
        return summary

    summary = _build_summary(root)
    if summary:
        return summary

    summary = _source_highlight_summary(root)
    if summary:
        return summary

    summary = _one_source_dialogue_preview_summary(root)
    if summary:
        return summary

    _lifecycle_path, lifecycle = _find_json(root, "material_map_lifecycle.json")
    if lifecycle:
        summary = _lifecycle_summary(root, lifecycle)
        if summary:
            return summary

    for summarize in (_material_wall_handoff_summary, _material_inventory_summary, _story_summary, _intent_summary):
        summary = summarize(root)
        if summary:
            return summary

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
