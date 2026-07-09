"""Reviewer role registry and policy expansion for Hermes Video Pipeline.

This module is intentionally deterministic. It does not call an LLM and does
not decide creative quality. It defines which reviewer roles exist, which
artifacts they inspect, which gate strength they are allowed to emit, and the
evaluation principles agents should apply when producing review artifacts.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


ARTIFACT_ROLE = "reviewer_registry"
POLICY_PACKET_ROLE = "reviewer_policy_packet"
VERSION = 1

VALID_DECISIONS = {"pass", "revise", "block", "blocked", "advisory"}
VALID_STATUSES = {"pass", "revise", "blocked"}
VALID_BLOCKING_LEVELS = {"none", "soft_block", "hard_block"}
VALID_GATE_STRENGTHS = {"advisory", "revise", "hard_gate", "delivery_gate"}

POLICIES = {
    "light": ["material_producer", "technical_verify"],
    "normal": [
        "story_director",
        "material_producer",
        "editorial_timeline",
        "technical_verify",
    ],
    "deep": [
        "literary_editor",
        "story_director",
        "material_producer",
        "generated_material_art_director",
        "editorial_timeline",
        "audio_subtitle_reviewer",
        "effect_reviewer",
        "technical_verify",
    ],
}


def _principle(criterion: str, evidence: str, failure_route: str) -> dict[str, str]:
    return {
        "criterion": criterion,
        "evidence": evidence,
        "failure_route": failure_route,
    }


REVIEWERS = [
    {
        "reviewer_role": "literary_editor",
        "review_type": "creative_review",
        "input_artifacts": ["literary_role_lens.json", "longform_source.md", "blueprint.md"],
        "output_artifact": "literary_master_review.json",
        "gate_strength": "revise",
        "allowed_gate_strengths": ["revise", "advisory"],
        "typical_next_actions": ["revise_longform", "ready_for_story_soul"],
        "eval_principles": [
            _principle("voice_and_role_fit", "tone, lens, audience, genre constraints", "revise_longform"),
            _principle("internal_logic", "cause/effect, contradiction checks, moral clarity", "revise_longform"),
            _principle("emotional_truth", "specific stakes and non-generic feeling", "ready_for_story_soul"),
        ],
    },
    {
        "reviewer_role": "story_director",
        "review_type": "creative_review",
        "input_artifacts": [
            "story_soul_blueprint.json",
            "screenplay_beats.json",
            "director_shot_plan.json",
            "blueprint.json",
        ],
        "output_artifact": "story_director_review.json",
        "gate_strength": "revise",
        "allowed_gate_strengths": ["revise", "advisory"],
        "typical_next_actions": ["revise_story_soul", "revise_shot_plan", "ready_for_material_truth"],
        "eval_principles": [
            _principle("narrative_device", "creative_concept and beat ordering", "revise_story_soul"),
            _principle("turn_per_beat", "conflict_or_turn and intended_viewer_feeling", "revise_story_soul"),
            _principle("shot_intent_density", "director_intent and material_prompt_requirements", "revise_shot_plan"),
        ],
    },
    {
        "reviewer_role": "material_producer",
        "review_type": "contract_material_review",
        "input_artifacts": ["material_needs.json", "project_material_map.json", "material_delta.json"],
        "output_artifact": "material_delta.json",
        "gate_strength": "hard_gate",
        "allowed_gate_strengths": ["hard_gate", "revise", "advisory"],
        "typical_next_actions": ["await_material", "generate_material", "revise_contract"],
        "eval_principles": [
            _principle("coverage_truth", "covered/thin/missing/excess delta outcomes", "await_material"),
            _principle("reference_integrity", "need_id and satisfies edge validation", "fix_material_map_or_needs"),
            _principle("candidate_status", "generated/real candidates accepted before BUILD", "await_material_visual_review"),
        ],
    },
    {
        "reviewer_role": "generated_material_art_director",
        "review_type": "generated_material_review",
        "input_artifacts": [
            "generated_material_quality_review.json",
            "generated_provider_packet.json",
            "generated_project_material_map.json",
        ],
        "output_artifact": "generated_material_review.json",
        "gate_strength": "revise",
        "allowed_gate_strengths": ["revise", "hard_gate", "advisory"],
        "typical_next_actions": ["regenerate_material", "accept_generated_candidate", "revise_prompt_pack"],
        "eval_principles": [
            _principle("style_consistency", "character/style bible and generated panels", "regenerate_material"),
            _principle("story_need_fit", "need_id purpose vs generated image content", "revise_prompt_pack"),
            _principle("camera_language", "shot role, scale, composition, action clarity", "regenerate_material"),
        ],
    },
    {
        "reviewer_role": "editorial_timeline",
        "review_type": "build_timeline_review",
        "input_artifacts": ["timeline_build.json", "preview_timeline.json", "contact_sheet.jpg"],
        "output_artifact": "editorial_timeline_review.json",
        "gate_strength": "revise",
        "allowed_gate_strengths": ["revise", "advisory"],
        "typical_next_actions": ["workbench_draft_review", "brownfield_edit", "rerender"],
        "eval_principles": [
            _principle("story_order", "timeline order vs screenplay beats", "workbench_draft_review"),
            _principle("visual_variety", "source/family/angle repetition and fatigue", "brownfield_edit"),
            _principle("rhythm_and_hold", "clip durations, pacing, opening/ending fit", "workbench_draft_review"),
        ],
    },
    {
        "reviewer_role": "audio_subtitle_reviewer",
        "review_type": "audio_subtitle_review",
        "input_artifacts": ["subtitles.srt", "audio_mix.wav", "sfx_cues.json", "timeline_build.json"],
        "output_artifact": "audio_subtitle_review.json",
        "gate_strength": "revise",
        "allowed_gate_strengths": ["revise", "advisory"],
        "typical_next_actions": ["fix_subtitles", "fix_audio_mix", "brownfield_edit"],
        "eval_principles": [
            _principle("subtitle_readability", "SRT timing, CPS, language correctness", "fix_subtitles"),
            _principle("audio_balance", "voice/BGM/SFX level and ducking evidence", "fix_audio_mix"),
            _principle("cue_alignment", "cue timestamps vs timeline beats", "brownfield_edit"),
        ],
    },
    {
        "reviewer_role": "effect_reviewer",
        "review_type": "effect_review",
        "input_artifacts": [
            "effect_intent_plan.json",
            "light_effects_plan.json",
            "remotion_effect_review.json",
            "draft_composite.mp4",
        ],
        "output_artifact": "effect_reviewer_review.json",
        "gate_strength": "advisory",
        "allowed_gate_strengths": ["advisory", "revise"],
        "typical_next_actions": ["revise_effect_intent", "accept_effect_draft", "drop_effect"],
        "eval_principles": [
            _principle("intent_alignment", "effect intent vs rendered/draft effect", "revise_effect_intent"),
            _principle("non_destructive_fit", "effect does not hide story/material evidence", "drop_effect"),
            _principle("backend_boundary", "ffmpeg/Remotion adapter output remains draft unless accepted", "accept_effect_draft"),
        ],
    },
    {
        "reviewer_role": "technical_verify",
        "review_type": "technical_verify",
        "input_artifacts": ["final.mp4", "subtitles.srt", "timeline_build.json", "verify_result.json"],
        "output_artifact": "verify_result.json",
        "gate_strength": "delivery_gate",
        "allowed_gate_strengths": ["delivery_gate"],
        "typical_next_actions": ["fix_technical_issue", "delivery_ready"],
        "eval_principles": [
            _principle("render_integrity", "final video exists, duration, no stale final", "fix_technical_issue"),
            _principle("technical_defects", "black/blank frames, captions, audio, timeline audits", "fix_technical_issue"),
            _principle("delivery_evidence", "verify_result and known limitations", "delivery_ready"),
        ],
    },
    {
        "reviewer_role": "delivery_reviewer",
        "review_type": "delivery_review",
        "input_artifacts": ["final.mp4", "review_report.md", "contact_sheet.jpg", "run_layout.json"],
        "output_artifact": "delivery_review.json",
        "gate_strength": "delivery_gate",
        "allowed_gate_strengths": ["delivery_gate", "advisory"],
        "typical_next_actions": ["delivery_ready", "fix_handoff_package"],
        "eval_principles": [
            _principle("handoff_completeness", "final/report/subtitle/contact-sheet availability", "fix_handoff_package"),
            _principle("limitation_disclosure", "known warnings and unresolved issues", "fix_handoff_package"),
            _principle("current_artifacts", "artifacts belong to current run, not stale outputs", "delivery_ready"),
        ],
    },
    {
        "reviewer_role": "effect_director",
        "review_type": "effect_director_review",
        "input_artifacts": ["effect_director_review_packet.json", "title_effect_lifecycle_qa.json"],
        "output_artifact": "effect_director_review.json",
        "gate_strength": "hard_gate",
        "allowed_gate_strengths": ["hard_gate", "revise", "advisory"],
        "typical_next_actions": ["repair_effect_director_findings", "human_review_or_promote_effect_assets_to_timeline"],
        "eval_principles": [
            _principle("visual_evidence_basis", "frame_sequence or video_sample, before/active/after frames", "repair_effect_director_findings"),
            _principle("effect_records_present", "title/effect records exist and are reviewed", "repair_effect_director_findings"),
        ],
    },
    {
        "reviewer_role": "montage_design_reviewer",
        "review_type": "montage_design_review",
        "input_artifacts": ["montage_design_plan.json"],
        "output_artifact": "montage_design_review.json",
        "gate_strength": "revise",
        "allowed_gate_strengths": ["revise", "advisory", "hard_gate"],
        "typical_next_actions": ["repair_montage_design", "write_montage_design_plan"],
        "eval_principles": [
            _principle("opener_mv_structure", "opener/MV montage section design, hook and payoff", "repair_montage_design"),
            _principle("shot_and_timing", "shot functions, beat/energy timing, title sync, transitions", "repair_montage_design"),
        ],
    },
]


def build_reviewer_registry() -> dict[str, Any]:
    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": VERSION,
        "policies": {k: list(v) for k, v in POLICIES.items()},
        "reviewers": [dict(r) for r in REVIEWERS],
        "eval_artifact_contract": {
            "artifact_role": "artifact_review",
            "version": 1,
            "required_fields": [
                "artifact_role",
                "version",
                "reviewer_role",
                "decision",
                "gate_strength",
                "findings",
            ],
            "valid_decisions": sorted(VALID_DECISIONS),
            "valid_statuses": sorted(VALID_STATUSES),
            "valid_blocking_levels": sorted(VALID_BLOCKING_LEVELS),
            "valid_gate_strengths": sorted(VALID_GATE_STRENGTHS),
        },
    }


def _role_map() -> dict[str, dict[str, Any]]:
    return {r["reviewer_role"]: r for r in REVIEWERS}


def expand_review_policy(level: str) -> list[str]:
    key = str(level or "").strip().lower()
    if key not in POLICIES:
        raise ValueError(f"unknown review policy level: {level!r}")
    return list(POLICIES[key])


def build_policy_packet(level: str) -> dict[str, Any]:
    enabled = expand_review_policy(level)
    roles = _role_map()
    return {
        "artifact_role": POLICY_PACKET_ROLE,
        "version": VERSION,
        "review_policy": {"level": str(level).strip().lower()},
        "enabled_reviewers": enabled,
        "reviewers": [roles[r] for r in enabled],
        "eval_artifact_contract": build_reviewer_registry()["eval_artifact_contract"],
    }


def validate_review_artifact(review: Mapping[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    if not isinstance(review, Mapping):
        return {"ok": False, "errors": ["review must be an object"]}

    if review.get("artifact_role") != "artifact_review":
        errors.append("artifact_role must be artifact_review")
    if review.get("version") != 1:
        errors.append("version must be 1")

    role = str(review.get("reviewer_role") or "").strip()
    roles = _role_map()
    spec = roles.get(role)
    if not spec:
        errors.append(f"unknown reviewer_role: {role!r}")

    decision = str(review.get("decision") or "").strip()
    if decision not in VALID_DECISIONS:
        errors.append(f"decision must be one of {sorted(VALID_DECISIONS)}")

    status = str(review.get("status") or "").strip()
    if status:
        if status not in VALID_STATUSES:
            errors.append(f"status must be one of {sorted(VALID_STATUSES)}")
        if status == "blocked" and decision not in {"block", "blocked"}:
            errors.append("status blocked requires decision block/blocked")
        if status == "revise" and decision != "revise":
            errors.append("status revise requires decision revise")

    blocking_level = str(review.get("blocking_level") or "").strip()
    if blocking_level:
        if blocking_level not in VALID_BLOCKING_LEVELS:
            errors.append(f"blocking_level must be one of {sorted(VALID_BLOCKING_LEVELS)}")
        if blocking_level in {"soft_block", "hard_block"} and review.get("can_continue_to_delivery") is not False:
            errors.append("can_continue_to_delivery must be false when blocking_level is soft_block or hard_block")

    gate = str(review.get("gate_strength") or "").strip()
    if gate not in VALID_GATE_STRENGTHS:
        errors.append(f"gate_strength must be one of {sorted(VALID_GATE_STRENGTHS)}")
    elif spec and gate not in spec["allowed_gate_strengths"]:
        errors.append(f"gate_strength {gate!r} is not allowed for reviewer_role {role!r}")

    findings = review.get("findings")
    if not isinstance(findings, list):
        errors.append("findings must be a list")

    return {"ok": not errors, "errors": errors}


def sign_review(
    reviewer_role: str,
    *,
    passed: bool,
    findings: list[Any] | None = None,
    gate_strength: str | None = None,
    next_action: str | None = None,
) -> dict[str, Any]:
    """Build a consistent, validatable review signature for an agentic review.

    The signature is the canonical ``artifact_review`` envelope so the state
    machine can detect any signed agentic review with one format regardless of
    which gate produced it.
    """
    spec = _role_map().get(reviewer_role)
    if not spec:
        raise ValueError(f"unknown reviewer_role: {reviewer_role!r}")
    gate = gate_strength or spec["gate_strength"]
    if passed:
        decision = "pass"
    elif gate in {"hard_gate", "delivery_gate"}:
        decision = "block"
    else:
        decision = "revise"
    signature: dict[str, Any] = {
        "artifact_role": "artifact_review",
        "version": 1,
        "reviewer_role": reviewer_role,
        "decision": decision,
        "gate_strength": gate,
        "findings": list(findings or []),
    }
    if next_action:
        signature["next_action"] = next_action
    check = validate_review_artifact(signature)
    if not check["ok"]:
        raise ValueError(f"invalid review signature: {check['errors']}")
    return signature


def detect_review_signature(payload: Mapping[str, Any] | None) -> dict[str, Any] | None:
    """Return the valid ``artifact_review`` signature carried by a payload.

    Accepts either a payload with an embedded ``review_signature`` block or a
    payload that is itself an ``artifact_review``. Returns None when no valid
    signature is present, so the state machine can distinguish signed agentic
    reviews from unsigned artifacts.
    """
    if not isinstance(payload, Mapping):
        return None
    candidate: Any = payload.get("review_signature")
    if not isinstance(candidate, Mapping) and payload.get("artifact_role") == "artifact_review":
        candidate = payload
    if not isinstance(candidate, Mapping):
        return None
    return dict(candidate) if validate_review_artifact(candidate)["ok"] else None


def write_policy_packet(level: str, out: str | Path) -> dict[str, Any]:
    packet = build_policy_packet(level)
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
    return packet
