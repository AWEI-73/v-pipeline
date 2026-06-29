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
    if gate.get("pass") is True and (root / "final.mp4").exists():
        return _contract(
            "done",
            "complete",
            reason="delivery gate passed and final.mp4 exists",
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

    summary = _delivery_gate_summary(root)
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

    summary = _audio_build_handoff_summary(root)
    if summary:
        return summary

    summary = _subtitle_voiceover_handoff_summary(root)
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
