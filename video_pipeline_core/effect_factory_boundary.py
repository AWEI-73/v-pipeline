"""Boundary acceptance for the Effect Factory route.

This module checks the semantic planning boundary without running real Remotion
or touching final delivery. It proves that different effect intents produce
distinct reviewable contracts, prompt-pack jobs, dry-run worker outputs, and
handoff artifacts that stay inside the bounded effect route.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .effect_revision import ADAPTER_ROUTE
from .remotion_effects import (
    build_remotion_prompt_pack,
    run_remotion_worker_smoke,
    validate_remotion_worker_outputs,
)


SCENARIOS: tuple[dict[str, Any], ...] = (
    {
        "effect_id": "fx_opening_lightning_01",
        "role": "title_card",
        "effect_role": "opening_title",
        "style_family": "electric_lightning_energy",
        "story_function": "high-impact opening that signals momentum and energy",
        "display_text": "全力啟動",
        "subtitle_text": "把能量集中到第一秒",
        "tone": "powerful, sharp, energetic, controlled",
        "duration_sec": 6.0,
        "template_id": "training_opening_title",
        "visual_primitives": [
            "branching_lightning_arcs",
            "electric_blue_glow",
            "dark_storm_gradient",
            "brief_white_flash",
        ],
        "motion_primitives": [
            "arc_strike",
            "micro_jitter",
            "flash_reveal",
            "afterglow_decay",
        ],
        "controls": {
            "strike_count": 4,
            "flash_intensity": "high",
            "jitter_strength": "medium",
            "title_reveal_frame": 54,
        },
        "negative_rules": [
            "no horror tone",
            "no unreadable strobe",
            "no full-white frame longer than 0.12 seconds",
        ],
    },
    {
        "effect_id": "fx_opening_earthquake_01",
        "role": "title_card",
        "effect_role": "opening_title",
        "style_family": "earthquake_crack_impact",
        "story_function": "dramatic opening that signals disruption and challenge",
        "display_text": "突破臨界點",
        "subtitle_text": "從壓力裡長出新的穩定",
        "tone": "dramatic, heavy, grounded, serious",
        "duration_sec": 6.0,
        "template_id": "training_opening_title",
        "visual_primitives": [
            "surface_crack_lines",
            "dust_burst",
            "dark_concrete_texture",
            "impact_shadow",
        ],
        "motion_primitives": [
            "impact_shake",
            "crack_expand",
            "dust_rise",
            "title_settle",
        ],
        "controls": {
            "crack_count": 5,
            "shake_strength": "medium",
            "shake_decay": "fast",
            "dust_density": "low",
        },
        "negative_rules": [
            "no injury implication",
            "no collapsing building",
            "no comedy wobble",
        ],
    },
    {
        "effect_id": "fx_opening_mothers_day_01",
        "role": "title_card",
        "effect_role": "opening_title",
        "style_family": "mothers_day_heart_stage",
        "story_function": "gentle opening for gratitude, family warmth, and blessing",
        "display_text": "謝謝妳的溫柔",
        "subtitle_text": "把愛放在今天最亮的位置",
        "tone": "warm, gentle, grateful, celebratory",
        "duration_sec": 6.0,
        "template_id": "clean_white_quote_card",
        "visual_primitives": [
            "soft_heart_bokeh",
            "pink_gold_gradient",
            "ribbon_curve",
            "flower_petal_drift",
        ],
        "motion_primitives": [
            "heart_float",
            "petal_drift",
            "soft_scale_in",
            "gentle_breathing_glow",
        ],
        "controls": {
            "heart_count": 16,
            "petal_count": 24,
            "glow_strength": "medium",
            "background_density": "clean",
        },
        "negative_rules": [
            "no sticker overload",
            "no harsh red",
            "no wedding-only mood",
        ],
    },
    {
        "effect_id": "fx_closing_legacy_01",
        "role": "title_card",
        "effect_role": "emotional_closing",
        "style_family": "warm_legacy_fire",
        "story_function": "restrained emotional closing that passes the spirit forward",
        "display_text": "走向下一個階段",
        "subtitle_text": "把這段日子的精神，帶到更遠的地方",
        "tone": "moving, restrained, warm, ceremonial",
        "duration_sec": 8.0,
        "template_id": "clean_white_quote_card",
        "visual_primitives": [
            "soft_ember_particles",
            "afterglow_warm_light",
            "gentle_vignette",
            "dimmed_group_photo_background",
        ],
        "motion_primitives": [
            "slow_rise",
            "gentle_drift",
            "breathing_flicker",
            "very_slow_push_in",
        ],
        "controls": {
            "ember_density": "low",
            "photo_dim_strength": "medium",
            "glow_strength": "soft",
            "ending_hold_sec": 2.0,
        },
        "negative_rules": [
            "no aggressive flames",
            "no disaster mood",
            "no heavy smoke",
            "do not cover faces",
        ],
    },
)


def _write_json(path: Path, payload: Mapping[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(path)


def _copy_json(value: Any) -> Any:
    return json.loads(json.dumps(value, ensure_ascii=False))


def _as_list(value: Iterable[str]) -> list[str]:
    return [str(item) for item in value]


def build_effect_design_map(scenarios: Iterable[Mapping[str, Any]] = SCENARIOS) -> dict[str, Any]:
    families = []
    for scenario in scenarios:
        families.append({
            "style_family": scenario["style_family"],
            "status": "reviewed",
            "communicates": scenario["story_function"],
            "best_roles": [scenario["effect_role"], scenario["role"]],
            "avoid_when": _as_list(scenario["negative_rules"]),
            "visual_primitives": _as_list(scenario["visual_primitives"]),
            "motion_primitives": _as_list(scenario["motion_primitives"]),
            "controls": dict(scenario["controls"]),
        })
    return {
        "artifact_role": "effect_design_map",
        "version": 1,
        "route": "effect-factory",
        "source_context": {
            "video_route": "standalone_probe",
            "segment_ids": [f"seg_{idx:02d}" for idx, _ in enumerate(families, start=1)],
            "material_refs": [],
            "user_intent": "verify semantic effect families do not collapse into one generic template",
        },
        "design_families": families,
        "dictionary_policy": {
            "role": "reviewable_parameter_surface",
            "templates_are": "worker_carriers_or_samples",
            "templates_are_not": "creative_locks_or_final_style_decisions",
            "unconfirmed_candidates_must": "return_to_user_or_reviewer_before_worker_handoff",
        },
        "followup_questions": [
            "Which effect role is needed: opening, transition, overlay, lower third, or ending?",
            "Should the tone be energetic, dramatic, warm, cute, documentary, or ceremonial?",
            "Is the effect required for story meaning or only decorative finishing?",
        ],
        "assumptions": [
            "No real material-map evidence is used in this boundary probe.",
            "Dry-run worker outputs prove contract shape only, not visual render quality.",
        ],
    }


def build_effect_contract(scenarios: Iterable[Mapping[str, Any]] = SCENARIOS) -> dict[str, Any]:
    effects = []
    for scenario in scenarios:
        effect = {
            "effect_id": scenario["effect_id"],
            "role": scenario["role"],
            "effect_role": scenario["effect_role"],
            "style_family": scenario["style_family"],
            "story_function": scenario["story_function"],
            "display_text": scenario["display_text"],
            "subtitle_text": scenario["subtitle_text"],
            "tone": scenario["tone"],
            "duration_sec": scenario["duration_sec"],
            "visual_primitives": _as_list(scenario["visual_primitives"]),
            "motion_primitives": _as_list(scenario["motion_primitives"]),
            "controls": dict(scenario["controls"]),
            "negative_rules": _as_list(scenario["negative_rules"]),
            "review_questions": [
                f"Does this read as {scenario['style_family']} rather than a generic title card?",
                "Is the Chinese title readable and inside title-safe area?",
                "Are the required controls visible or explicitly documented by the worker?",
            ],
            "backend_policy": {
                "preferred": "remotion-effect-worker",
                "fallback": "explicit_degraded_or_ask_followup",
            },
        }
        effects.append(effect)
    return {
        "artifact_role": "effect_contract",
        "version": 1,
        "effects": effects,
    }


def build_effect_intent_plan(scenarios: Iterable[Mapping[str, Any]] = SCENARIOS) -> dict[str, Any]:
    effects = []
    for index, scenario in enumerate(scenarios, start=1):
        effect = {
            "effect_id": scenario["effect_id"],
            "role": scenario["role"],
            "intent": scenario["story_function"],
            "intensity": "high" if "lightning" in scenario["style_family"] else "medium",
            "target": {"beat_id": f"beat_{index:02d}", "segment_id": f"seg_{index:02d}"},
            "visual_language": _as_list(scenario["visual_primitives"]),
            "required_for_story": True,
            "must_preserve_proof": False,
            "allowed_backends": ["remotion_preview", "remotion_render"],
            "fallback": "explicit degraded title card after human review",
            "duration_sec": scenario["duration_sec"],
            "template_id": scenario["template_id"],
            "display_text": scenario["display_text"],
            "subtitle_text": scenario["subtitle_text"],
            "prompt_parameters": {
                "effect_goal": scenario["effect_role"],
                "style_family": scenario["style_family"],
                "tone": scenario["tone"],
                "story_function": scenario["story_function"],
                "duration_sec": scenario["duration_sec"],
                "visual_primitives": _as_list(scenario["visual_primitives"]),
                "motion_primitives": _as_list(scenario["motion_primitives"]),
                "controls": dict(scenario["controls"]),
                "negative_rules": _as_list(scenario["negative_rules"]),
            },
            "presentation": {
                "variant": scenario["style_family"],
                "motion_energy": "high" if "lightning" in scenario["style_family"] else "medium",
                "title_hierarchy": "hero",
                "effect_strength": "emphasis" if "lightning" in scenario["style_family"] else "medium",
                "safe_area": "title_safe",
            },
        }
        effects.append(effect)
    return {
        "artifact_role": "effect_intent_plan",
        "version": 1,
        "effects": effects,
    }


def build_effect_revision_request(effect_intent_plan: Mapping[str, Any]) -> dict[str, Any]:
    requests = []
    for effect in effect_intent_plan.get("effects") or []:
        segment = (effect.get("target") or {}).get("segment_id")
        requests.append({
            "request_id": f"fxrev_{effect['effect_id']}",
            "effect_id": f"{effect['effect_id']}_gap",
            "source_effect_id": effect["effect_id"],
            "segment": segment,
            "operation": "external_effect",
            "route": ADAPTER_ROUTE,
            "reason": "effect-factory boundary acceptance routes this designed effect to Remotion worker",
            "status": "pending",
        })
    return {
        "artifact_role": "effect_revision_request",
        "version": 1,
        "status": "pending",
        "summary": {"request_count": len(requests)},
        "requests": requests,
    }


def build_timeline(effect_intent_plan: Mapping[str, Any]) -> dict[str, Any]:
    segments = []
    cursor = 0.0
    for effect in effect_intent_plan.get("effects") or []:
        duration = float(
            effect.get("duration_sec")
            or (effect.get("prompt_parameters") or {}).get("duration_sec")
            or 0
        ) or 0.0
        if duration <= 0:
            duration = 6.0
        segment_id = (effect.get("target") or {}).get("segment_id")
        segments.append({
            "segment_id": segment_id,
            "start_sec": round(cursor, 3),
            "duration_sec": round(duration, 3),
            "effect_id": effect["effect_id"],
        })
        cursor += duration
    return {
        "artifact_role": "timeline_build",
        "version": 1,
        "duration_sec": round(cursor, 3),
        "segments": segments,
    }


def review_effects(contract: Mapping[str, Any], remotion_review: Mapping[str, Any]) -> dict[str, Any]:
    items_by_effect = {
        item.get("source_effect_id"): item
        for item in remotion_review.get("items") or []
    }
    reviewed = []
    blocking = []
    for effect in contract.get("effects") or []:
        item = items_by_effect.get(effect.get("effect_id"))
        evidence = list((item or {}).get("evidence_refs") or [])
        status = "pass" if item and evidence else "fail"
        if status != "pass":
            blocking.append({
                "effect_id": effect.get("effect_id"),
                "reason": "missing matching worker output or evidence refs",
            })
        reviewed.append({
            "effect_id": effect.get("effect_id"),
            "style_family": effect.get("style_family"),
            "intent_match": status,
            "visual_distinction": "pass" if status == "pass" else "fail",
            "text_readability": "pending_human_visual_review" if status == "pass" else "fail",
            "controls_preserved": "pending_human_visual_review" if status == "pass" else "fail",
            "negative_rules": "pending_human_visual_review" if status == "pass" else "fail",
            "evidence_refs": evidence,
        })
    return {
        "artifact_role": "effect_review",
        "version": 1,
        "status": "pass" if not blocking else "fail",
        "reviewed_effects": reviewed,
        "blocking_issues": blocking,
        "next_action": "handoff" if not blocking else "rerun_worker",
    }


def build_handoff(effect_review: Mapping[str, Any], remotion_review: Mapping[str, Any]) -> dict[str, Any]:
    accepted = []
    evidence = []
    for item in remotion_review.get("items") or []:
        refs = list(item.get("evidence_refs") or [])
        evidence.extend(refs)
        accepted.append({
            "job_id": item.get("job_id"),
            "effect_id": item.get("source_effect_id"),
            "preview_file": item.get("preview_file"),
            "rendered_asset": item.get("rendered_asset"),
            "duration_sec": item.get("duration_sec"),
            "evidence_refs": refs,
        })
    return {
        "artifact_role": "effect_handoff",
        "version": 1,
        "status": "ready_for_human_review" if effect_review.get("status") == "pass" else "blocked",
        "boundary": {
            "role": "bounded_effect_asset_route",
            "owns_final_delivery": False,
            "owns_material_truth": False,
            "owns_rough_cut_selection": False,
            "final_assembly_owner": "ffmpeg_contract_run",
        },
        "accepted_assets": accepted,
        "review_evidence": evidence,
        "next_action": "human_review_or_promote_effect_assets_to_timeline",
    }


def _style_signatures(contract: Mapping[str, Any], pack: Mapping[str, Any]) -> list[dict[str, Any]]:
    effects_by_id = {effect["effect_id"]: effect for effect in contract.get("effects") or []}
    signatures = []
    for job in pack.get("jobs") or []:
        effect = effects_by_id.get(job.get("source_effect_id")) or {}
        params = ((job.get("props") or {}).get("prompt_parameters") or {})
        signatures.append({
            "effect_id": job.get("source_effect_id"),
            "style_family": params.get("style_family") or effect.get("style_family"),
            "component_family": job.get("component_family"),
            "visual_primitives": list(params.get("visual_primitives") or []),
            "motion_primitives": list(params.get("motion_primitives") or []),
            "controls": dict(params.get("controls") or {}),
        })
    return signatures


def _semantic_diversity_ok(signatures: list[Mapping[str, Any]]) -> bool:
    families = {item.get("style_family") for item in signatures}
    visual_sets = {tuple(item.get("visual_primitives") or []) for item in signatures}
    motion_sets = {tuple(item.get("motion_primitives") or []) for item in signatures}
    return (
        len(signatures) >= 3
        and len(families) == len(signatures)
        and len(visual_sets) == len(signatures)
        and len(motion_sets) == len(signatures)
    )


def run_effect_factory_boundary_acceptance(run_dir: str | Path) -> dict[str, Any]:
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)

    design_map = build_effect_design_map()
    contract = build_effect_contract()
    intent_plan = build_effect_intent_plan()
    revision_request = build_effect_revision_request(intent_plan)
    timeline = build_timeline(intent_plan)

    artifacts: dict[str, str] = {}
    artifacts["effect_design_map"] = _write_json(run_dir / "effect_design_map.json", design_map)
    artifacts["effect_contract"] = _write_json(run_dir / "effect_contract.json", contract)
    artifacts["effect_intent_plan"] = _write_json(run_dir / "effect_intent_plan.json", intent_plan)
    artifacts["effect_revision_request"] = _write_json(run_dir / "effect_revision_request.json", revision_request)
    artifacts["timeline_build"] = _write_json(run_dir / "timeline_build.json", timeline)

    pack = build_remotion_prompt_pack(
        revision_request,
        intent_plan,
        timeline=timeline,
        output_dir="remotion_effects",
    )
    artifacts["remotion_prompt_pack"] = _write_json(run_dir / "remotion_prompt_pack.json", pack)

    worker_outputs = run_remotion_worker_smoke(pack, run_dir / "remotion_effects")
    artifacts["remotion_worker_outputs"] = _write_json(run_dir / "remotion_worker_outputs.json", worker_outputs)

    validation = validate_remotion_worker_outputs(worker_outputs, pack)
    if validation["ok"]:
        remotion_review = validation["review_artifact"]
    else:
        remotion_review = validation["review_artifact"]
    artifacts["remotion_effect_review"] = _write_json(run_dir / "remotion_effect_review.json", remotion_review)

    effect_review = review_effects(contract, remotion_review)
    artifacts["effect_review"] = _write_json(run_dir / "effect_review.json", effect_review)
    handoff = build_handoff(effect_review, remotion_review)
    artifacts["effect_handoff"] = _write_json(run_dir / "effect_handoff.json", handoff)

    signatures = _style_signatures(contract, pack)
    diversity_ok = _semantic_diversity_ok(signatures)
    final_exists = (run_dir / "final.mp4").exists()
    ok = bool(
        validation["ok"]
        and effect_review["status"] == "pass"
        and handoff["status"] == "ready_for_human_review"
        and diversity_ok
        and not final_exists
    )
    report = {
        "artifact_role": "effect_factory_boundary_acceptance_report",
        "version": 1,
        "ok": ok,
        "failed_stage": None if ok else "effect_factory_boundary",
        "next_action": (
            "ready_for_human_effect_review_or_pipeline_promotion"
            if ok else "revise_effect_factory_contract"
        ),
        "summary": {
            "effect_count": len(contract["effects"]),
            "job_count": pack["summary"]["job_count"],
            "rendered_count": worker_outputs["summary"]["rendered_count"],
            "semantic_diversity_ok": diversity_ok,
            "canonical_final_exists": final_exists,
        },
        "style_signatures": signatures,
        "artifacts": _copy_json(artifacts),
        "validation_errors": list(validation.get("errors") or []),
        "boundary_notes": [
            "This is a no-render dry-run worker acceptance; it does not prove visual quality.",
            "Effect assets are bounded finishing assets and do not satisfy material truth.",
            "Style families are reviewable parameter surfaces, not fixed creative templates.",
            "final.mp4 must remain absent.",
        ],
    }
    artifacts["effect_factory_boundary_acceptance_report"] = _write_json(
        run_dir / "effect_factory_boundary_acceptance_report.json",
        report,
    )
    report["artifacts"] = _copy_json(artifacts)
    _write_json(run_dir / "effect_factory_boundary_acceptance_report.json", report)
    return report
