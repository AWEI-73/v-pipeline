"""Reviewer role registry and policy expansion for Hermes Video Pipeline.

This module is intentionally deterministic. It does not call an LLM and does
not decide creative quality. It defines which reviewer roles exist, which
artifacts they inspect, which gate strength they are allowed to emit, and the
evaluation principles agents should apply when producing review artifacts.
"""
from __future__ import annotations

import json
import hashlib
import re
from pathlib import Path
from typing import Any, Mapping


ARTIFACT_ROLE = "reviewer_registry"
POLICY_PACKET_ROLE = "reviewer_policy_packet"
VERSION = 1

VALID_DECISIONS = {"pass", "revise", "block", "blocked", "advisory"}
VALID_STATUSES = {"pass", "revise", "blocked"}
VALID_BLOCKING_LEVELS = {"none", "soft_block", "hard_block"}
VALID_GATE_STRENGTHS = {"advisory", "revise", "hard_gate", "delivery_gate"}

EDITORIAL_REVIEWER_IDENTITY = "editorial_reviewer"
EDITORIAL_REVIEW_VERSION = 2
EDITORIAL_BINDING_CONTRACT_VERSION = 1
SHA256_HASH_METHOD = "sha256_file_bytes_v1"
EDITORIAL_REVIEW_ARTIFACT_ROLE = "editorial_review"
EDITORIAL_REVIEW_AUTHORITY = "findings_and_proposals_only"
EDITORIAL_REVIEW_MODES = {"full_context", "cold_start"}
EDITORIAL_REVIEW_STATUSES = {
    "ready_for_owner_verdict",
    "findings_present",
    "unknown",
    "incomplete",
}
EDITORIAL_FINDING_CLASSES = {"objective", "process", "structural_candidate", "taste"}
EDITORIAL_FINDING_PRIORITIES = {"critical", "high", "medium", "low", "info"}
EDITORIAL_FINDING_CONFIDENCES = {"high", "medium", "low"}
EDITORIAL_FIXABLE_AT = {"clip", "segment", "story", "process", "future_project"}
EDITORIAL_STAGE_ROUTES = {
    "main-pipeline",
    "material-map",
    "soundtrack-arranger",
    "subtitle-voiceover",
    "effect-factory",
    "workbench-brownfield",
    "verify-delivery",
    "stage_0_2",
    "stage_3",
    "stage_4_5",
    "stage_6",
    "stage_7_8",
    "stage_9",
    "stage_10",
    "no_existing_route",
}
EDITORIAL_REQUIRED_FORBIDDEN_ACTIONS = {
    "canonical_state_mutation",
    "repair_or_construction",
    "creative_approval",
    "delivery_claim",
}
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")
_FORBIDDEN_REVIEW_KEYS = {
    "repair_command",
    "repair_commands",
    "apply_command",
    "command",
    "mutate_artifact",
    "canonical_mutation",
    "write_canonical_state",
    "canonical_state_write",
}

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
    {
        "reviewer_role": "visual_selection_reviewer",
        "review_type": "visual_selection_review",
        "input_artifacts": ["visual_selection_candidates.json"],
        "output_artifact": "visual_selection_review.json",
        "gate_strength": "revise",
        "allowed_gate_strengths": ["revise", "hard_gate", "advisory"],
        "typical_next_actions": ["repick_visual_material", "run_visual_selection_review"],
        "eval_principles": [
            _principle("visual_evidence", "representative frame, contact sheet, or frame evidence per beat", "repick_visual_material"),
            _principle("forbidden_role_flags", "supervisor/director/portrait not marked primary where forbidden", "repick_visual_material"),
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
        "editorial_reviewer_contract": {
            "reviewer_identity": EDITORIAL_REVIEWER_IDENTITY,
            "version": EDITORIAL_REVIEW_VERSION,
            "authority": EDITORIAL_REVIEW_AUTHORITY,
            "rubric_lenses": sorted(r["reviewer_role"] for r in REVIEWERS),
            "forbidden_actions": sorted(EDITORIAL_REQUIRED_FORBIDDEN_ACTIONS),
            "review_modes": sorted(EDITORIAL_REVIEW_MODES),
            "finding_classes": sorted(EDITORIAL_FINDING_CLASSES),
            "stage_return_routes": sorted(EDITORIAL_STAGE_ROUTES),
            "allowed_enums": {
                "statuses": sorted(EDITORIAL_REVIEW_STATUSES),
                "review_modes": sorted(EDITORIAL_REVIEW_MODES),
                "rubric_lenses": sorted(r["reviewer_role"] for r in REVIEWERS),
                "finding_classes": sorted(EDITORIAL_FINDING_CLASSES),
                "priorities": sorted(EDITORIAL_FINDING_PRIORITIES),
                "confidences": sorted(EDITORIAL_FINDING_CONFIDENCES),
                "fixable_at": sorted(EDITORIAL_FIXABLE_AT),
                "routes": sorted(EDITORIAL_STAGE_ROUTES),
            },
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


def _load_live_capability_catalog() -> tuple[dict[str, Any] | None, list[str]]:
    try:
        from .capability_catalog import load_live_catalog

        skills_dir = Path(__file__).resolve().parents[1] / "skills"
        catalog = load_live_catalog(str(skills_dir))
    except Exception as exc:  # pragma: no cover - defensive fail-closed path
        return None, [f"capability_catalog_unavailable: {exc}"]
    if not catalog.get("ok"):
        return None, ["capability_catalog_invalid"]
    return catalog, []


def build_reviewer_write_contract() -> dict[str, Any]:
    """Build the reviewer write surface from the live registry and catalog."""
    registry = build_reviewer_registry()
    catalog, catalog_errors = _load_live_capability_catalog()
    if catalog_errors or catalog is None:
        raise ValueError(f"reviewer_write_contract_catalog_unavailable: {catalog_errors}")
    cards = [card for card in catalog.get("cards") or [] if isinstance(card, Mapping)]
    validator_cards = [
        card for card in cards
        if card.get("owner") == "editorial-reviewer"
        and card.get("capability_role") == "review"
        and str(card.get("tool") or "").startswith("video_tools.py reviewer-policy")
    ]
    timeline_cards = [
        card for card in cards
        if str(card.get("tool") or "") == "tools/timeline_review_packet.py"
    ]
    if len(validator_cards) != 1 or len(timeline_cards) != 1:
        raise ValueError("reviewer_write_contract_required_live_capabilities_missing")
    validator = validator_cards[0]
    editorial = registry["editorial_reviewer_contract"]
    minimal_subject = {
        "path": "candidate.mp4",
        "artifact_role": "timeline_review_subject",
        "sha256": "a" * 64,
        "hash_method": SHA256_HASH_METHOD,
        "duration_sec": 1.0,
        "media_role": "current_candidate",
    }
    minimal_manifest = {
        "artifact_role": "editorial_evidence_manifest",
        "version": 1,
        "subject": minimal_subject,
        "picture_stream_fingerprint": {"status": "unbound", "reason": "picture_stream_probe_not_supplied"},
        "audio_stream_fingerprint": {"status": "unbound", "reason": "soundtrack_probe_not_supplied"},
        "subtitle_fingerprint": {"status": "unbound", "reason": "srt_not_supplied"},
        "evidence_items": [{
            "evidence_id": "wall_1",
            "kind": "timeline_wall",
            "path": "walls/wall_30s_01.jpg",
            "sha256": "b" * 64,
            "generator_capability": timeline_cards[0]["capability_id"],
            "covered_timeline_window": {"start_sec": 0.0, "end_sec": 1.0},
            "source_binding": {
                "subject_sha256": minimal_subject["sha256"],
                "hash_method": SHA256_HASH_METHOD,
            },
            "limitations": ["navigation only"],
        }],
        "generated_at": "2026-01-01T00:00:00+00:00",
        "generator_version": "reviewer_write_contract/example",
        "reuse_policy": {"unknown_or_mismatched_subject": "fail_closed"},
        "invalidated_by": [],
        "parent_manifest": None,
    }
    minimal_example = {
        "artifact_role": EDITORIAL_REVIEW_ARTIFACT_ROLE,
        "version": EDITORIAL_REVIEW_VERSION,
        "status": "ready_for_owner_verdict",
        "reviewer_identity": EDITORIAL_REVIEWER_IDENTITY,
        "review_mode": "full_context",
        "rubric_lenses": ["editorial_timeline"],
        "authority": EDITORIAL_REVIEW_AUTHORITY,
        "forbidden_actions": sorted(EDITORIAL_REQUIRED_FORBIDDEN_ACTIONS),
        "subject": minimal_subject,
        "binding_contract_version": EDITORIAL_BINDING_CONTRACT_VERSION,
        "reviewed_subject_sha256": minimal_subject["sha256"],
        "applies_to_candidate_sha256": minimal_subject["sha256"],
        "subject_hash_method": SHA256_HASH_METHOD,
        "evidence_manifest": minimal_manifest,
        "inspection_scope": {"timeline_windows": [[0.0, 1.0]]},
        "not_inspected": [],
        "strengths": [],
        "chapter_candidates": [],
        "findings": [],
        "evidence_gaps": [],
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }
    return {
        "artifact_role": "reviewer_write_contract",
        "version": 1,
        "generated_from": {
            "reviewer_registry": {
                "artifact_role": registry["artifact_role"],
                "version": registry["version"],
            },
            "capability_catalog": {
                "artifact_role": catalog["artifact_role"],
                "version": catalog["version"],
            },
        },
        "reviewer_identity": EDITORIAL_REVIEWER_IDENTITY,
        "review_artifact_role": EDITORIAL_REVIEW_ARTIFACT_ROLE,
        "review_version": EDITORIAL_REVIEW_VERSION,
        "allowed_enums": {key: list(value) for key, value in editorial["allowed_enums"].items()},
        "authority": editorial["authority"],
        "forbidden_actions": list(editorial["forbidden_actions"]),
        "routing_capability_ids": sorted(str(card["capability_id"]) for card in cards),
        "validator_capability_id": validator["capability_id"],
        "validator": {
            "capability_id": validator["capability_id"],
            "tool": validator["tool"],
            "command": validator["command"],
        },
        "minimal_valid_example": minimal_example,
    }


def _is_sha256(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA256_RE.fullmatch(value))


def _has_text(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _validate_timeline_window(value: Any, label: str) -> list[str]:
    if isinstance(value, Mapping):
        start = value.get("start_sec")
        end = value.get("end_sec")
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        start, end = value
    else:
        return [f"{label} must be a {label} mapping or [start,end] pair"]
    try:
        start_value = float(start)
        end_value = float(end)
    except (TypeError, ValueError):
        return [f"{label} must contain numeric start_sec and end_sec"]
    if start_value < 0 or end_value < start_value:
        return [f"{label} must be a non-negative ordered time window"]
    return []


def _window_bounds(value: Any) -> tuple[float, float] | None:
    if isinstance(value, Mapping):
        start, end = value.get("start_sec"), value.get("end_sec")
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        start, end = value
    else:
        return None
    try:
        return float(start), float(end)
    except (TypeError, ValueError):
        return None


def _forbidden_keys(value: Any, path: str = "") -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, nested in value.items():
            key_text = str(key)
            key_path = f"{path}.{key_text}" if path else key_text
            if key_text in _FORBIDDEN_REVIEW_KEYS:
                found.append(key_path)
            found.extend(_forbidden_keys(nested, key_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            found.extend(_forbidden_keys(nested, f"{path}[{index}]"))
    return found


def _live_capability_ids() -> tuple[set[str], list[str]]:
    catalog, catalog_errors = _load_live_capability_catalog()
    if catalog_errors or catalog is None:
        return set(), catalog_errors
    return {
        str(card.get("capability_id"))
        for card in catalog.get("cards") or []
        if isinstance(card, Mapping) and _has_text(card.get("capability_id"))
    }, []


def _validate_subject(subject: Any, label: str = "subject") -> list[str]:
    errors: list[str] = []
    if not isinstance(subject, Mapping):
        return [f"{label} must be an object"]
    for key in ("path", "artifact_role", "media_role"):
        if not _has_text(subject.get(key)):
            errors.append(f"{label}.{key} must be a non-empty string")
    if not _is_sha256(subject.get("sha256")):
        errors.append(f"{label}.sha256 must be a full SHA-256")
    try:
        if float(subject.get("duration_sec")) < 0:
            errors.append(f"{label}.duration_sec must be non-negative")
    except (TypeError, ValueError):
        errors.append(f"{label}.duration_sec must be numeric")
    return errors


def _validate_fingerprint(value: Any, label: str) -> list[str]:
    if not isinstance(value, Mapping):
        return [f"{label} must be an object"]
    status = value.get("status")
    if status == "bound":
        fingerprint = value.get("sha256") or value.get("fingerprint")
        if not _is_sha256(fingerprint):
            return [f"{label}.sha256 must be a 64-character hexadecimal SHA-256"]
        return []
    if status == "unbound":
        if not _has_text(value.get("reason")):
            return [f"{label}.reason is required when fingerprint is unbound"]
        return []
    return [f"{label}.status must be bound or unbound"]


def _validate_evidence_manifest(
    manifest: Any,
    subject: Mapping[str, Any],
    *,
    prefix: str = "evidence_manifest",
) -> tuple[list[str], dict[str, Mapping[str, Any]]]:
    errors: list[str] = []
    items_by_id: dict[str, Mapping[str, Any]] = {}
    if not isinstance(manifest, Mapping):
        return [f"{prefix} must be an object"], items_by_id
    if manifest.get("artifact_role") != "editorial_evidence_manifest":
        errors.append(f"{prefix}.artifact_role must be editorial_evidence_manifest")
    if manifest.get("version") != 1:
        errors.append(f"{prefix}.version must be 1")
    manifest_subject = manifest.get("subject")
    errors.extend(_validate_subject(manifest_subject, f"{prefix}.subject"))
    if isinstance(manifest_subject, Mapping) and manifest_subject.get("sha256") != subject.get("sha256"):
        errors.append(f"{prefix}.subject.sha256 must match subject.sha256")
    if not _has_text(manifest.get("generated_at")):
        errors.append(f"{prefix}.generated_at is required")
    if not _has_text(manifest.get("generator_version")):
        errors.append(f"{prefix}.generator_version is required")
    if not isinstance(manifest.get("reuse_policy"), Mapping):
        errors.append(f"{prefix}.reuse_policy must be an object")
    if not isinstance(manifest.get("invalidated_by"), list):
        errors.append(f"{prefix}.invalidated_by must be a list")
    parent = manifest.get("parent_manifest")
    if parent is not None and not isinstance(parent, (str, Mapping)):
        errors.append(f"{prefix}.parent_manifest must be null, a path, or an object")
    for fingerprint_key in (
        "picture_stream_fingerprint",
        "audio_stream_fingerprint",
        "audio_probe_artifact_fingerprint",
        "subtitle_fingerprint",
    ):
        if fingerprint_key in manifest:
            errors.extend(_validate_fingerprint(manifest.get(fingerprint_key), f"{prefix}.{fingerprint_key}"))

    capability_ids, capability_errors = _live_capability_ids()
    errors.extend(capability_errors)
    items = manifest.get("evidence_items")
    if not isinstance(items, list):
        errors.append(f"{prefix}.evidence_items must be a list")
        return errors, items_by_id
    for index, item in enumerate(items):
        label = f"{prefix}.evidence_items[{index}]"
        if not isinstance(item, Mapping):
            errors.append(f"{label} must be an object")
            continue
        evidence_id = item.get("evidence_id")
        if not _has_text(evidence_id):
            errors.append(f"{label}.evidence_id is required")
        elif evidence_id in items_by_id:
            errors.append(f"duplicate evidence_id: {evidence_id}")
        else:
            items_by_id[str(evidence_id)] = item
        for key in ("kind", "path"):
            if not item.get(key):
                errors.append(f"{label}.{key} is required")
        source_binding = item.get("source_binding")
        if not isinstance(source_binding, Mapping):
            errors.append(f"{label}.source_binding is required")
        elif source_binding.get("subject_sha256") != subject.get("sha256"):
            errors.append(f"{label}.source_binding.subject_sha256 must match subject.sha256")
        if not _is_sha256(item.get("sha256")):
            errors.append(f"{label}.sha256 must be a full SHA-256")
        generator = item.get("generator_capability")
        if generator not in capability_ids:
            errors.append(f"unknown generator capability: {generator!r}")
        window = item.get("covered_timeline_window")
        errors.extend(_validate_timeline_window(window, f"{label}.covered_timeline_window"))
        if not isinstance(item.get("limitations"), list):
            errors.append(f"{label}.limitations must be a list")
    return errors, items_by_id


def _validate_chapter_candidates(
    chapters: Any,
    subject: Mapping[str, Any],
    manifest_items: Mapping[str, Mapping[str, Any]],
) -> list[str]:
    if chapters is None:
        return []
    if not isinstance(chapters, list):
        return ["chapter_candidates must be a list"]
    errors: list[str] = []
    try:
        duration = float(subject.get("duration_sec"))
    except (TypeError, ValueError):
        duration = None
    for index, chapter in enumerate(chapters):
        label = f"chapter_candidates[{index}]"
        if not isinstance(chapter, Mapping):
            errors.append(f"{label} must be an object")
            continue
        if not _has_text(chapter.get("chapter_id")):
            errors.append(f"{label}.chapter_id is required")
        window_errors = _validate_timeline_window(chapter.get("timeline_window"), f"{label}.timeline_window")
        errors.extend(window_errors)
        bounds = _window_bounds(chapter.get("timeline_window"))
        if duration is not None and bounds and bounds[1] > duration:
            errors.append(f"{label}.timeline_window must be within subject duration")
        for key in ("opens_with", "ends_with", "information_gain"):
            if not _has_text(chapter.get(key)):
                errors.append(f"{label}.{key} is required")
        if chapter.get("opens_with") == chapter.get("ends_with"):
            if not (_has_text(chapter.get("no_progression_observation")) or _has_text(chapter.get("no_progression_finding_id"))):
                errors.append(f"{label} requires an explicit no-progression observation or finding")
        refs = chapter.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{label}.evidence_refs must be a non-empty list")
            continue
        for ref_index, ref in enumerate(refs):
            ref_label = f"{label}.evidence_refs[{ref_index}]"
            if not isinstance(ref, Mapping):
                errors.append(f"{ref_label} must be an object")
                continue
            evidence_id = ref.get("evidence_id") or ref.get("id")
            item = manifest_items.get(str(evidence_id)) if evidence_id else None
            if item is None:
                errors.append(f"{ref_label} unresolved evidence_id: {evidence_id!r}")
                continue
            window = ref.get("time_range") or ref.get("covered_timeline_window")
            errors.extend(_validate_timeline_window(window, f"{ref_label}.time_range"))
            ref_bounds = _window_bounds(window)
            item_bounds = _window_bounds(item.get("covered_timeline_window"))
            if ref_bounds and item_bounds and (ref_bounds[0] < item_bounds[0] or ref_bounds[1] > item_bounds[1]):
                errors.append(f"{ref_label}.time_range must be within evidence item window")
    return errors


def _validate_proposed_fix(
    fix: Any,
    label: str,
    capability_ids: set[str],
    capability_errors: list[str],
) -> list[str]:
    errors: list[str] = []
    if not isinstance(fix, Mapping):
        return [f"{label} must be an object"]
    route = fix.get("route")
    if route not in EDITORIAL_STAGE_ROUTES:
        errors.append(f"{label}.route must be an existing stage return route or no_existing_route")
    capability_id = fix.get("capability_id")
    if route == "no_existing_route":
        if capability_id is not None:
            errors.append(f"{label}.capability_id must be null when route is no_existing_route")
        if not fix.get("no_route_reason"):
            errors.append(f"{label}.no_route_reason is required when route is no_existing_route")
        if not fix.get("target"):
            errors.append(f"{label}.target is required")
        if fix.get("requires_owner_or_integrator_verdict") is not True:
            errors.append(f"{label}.requires_owner_or_integrator_verdict must be true")
        errors.extend(f"{label} contains forbidden mutation key {key}" for key in _forbidden_keys(fix))
        return errors
    if capability_id not in capability_ids:
        errors.extend(capability_errors)
        errors.append(f"unknown capability_id: {capability_id!r}")
    for key in ("target", "expected_change", "expected_unchanged"):
        if not fix.get(key):
            errors.append(f"{label}.{key} is required")
    if not isinstance(fix.get("rerun_gates"), list) or not fix.get("rerun_gates"):
        errors.append(f"{label}.rerun_gates must be a non-empty list")
    if fix.get("requires_owner_or_integrator_verdict") is not True:
        errors.append(f"{label}.requires_owner_or_integrator_verdict must be true")
    errors.extend(f"{label} contains forbidden mutation key {key}" for key in _forbidden_keys(fix))
    return errors


def _validate_exact_subject_binding(
    review: Mapping[str, Any],
    subject: Any,
) -> list[str]:
    binding_version = review.get("binding_contract_version")
    if binding_version is None:
        return []
    if binding_version != EDITORIAL_BINDING_CONTRACT_VERSION:
        return [
            "binding_contract_version must be 1 when exact-subject binding is supplied"
        ]

    errors: list[str] = []
    reviewed_sha256 = review.get("reviewed_subject_sha256")
    applicable_sha256 = review.get("applies_to_candidate_sha256")
    if not _is_sha256(reviewed_sha256):
        errors.append("reviewed_subject_sha256 must be a full SHA-256")
    if not _is_sha256(applicable_sha256):
        errors.append("applies_to_candidate_sha256 must be a full SHA-256")
    if not _is_sha256(subject.get("sha256") if isinstance(subject, Mapping) else None):
        errors.append("subject.sha256 must be a full SHA-256 for exact-subject binding")
    if (
        _is_sha256(reviewed_sha256)
        and _is_sha256(subject.get("sha256") if isinstance(subject, Mapping) else None)
        and reviewed_sha256.lower() != str(subject["sha256"]).lower()
    ):
        errors.append("reviewed_subject_sha256 must match subject.sha256")
    if (
        _is_sha256(reviewed_sha256)
        and _is_sha256(applicable_sha256)
        and applicable_sha256.lower() != reviewed_sha256.lower()
    ):
        errors.append("applies_to_candidate_sha256 must match reviewed_subject_sha256")
    if review.get("subject_hash_method") != SHA256_HASH_METHOD:
        errors.append("subject_hash_method must be sha256_file_bytes_v1")
    return errors


def validate_editorial_review(review: Mapping[str, Any]) -> dict[str, Any]:
    """Validate the additive V Pipeline Editorial Reviewer v2 contract."""
    errors: list[str] = []
    if not isinstance(review, Mapping):
        return {"ok": False, "errors": ["editorial review must be an object"]}
    if review.get("artifact_role") not in {EDITORIAL_REVIEW_ARTIFACT_ROLE, "artifact_review"}:
        errors.append("artifact_role must be editorial_review or artifact_review")
    if review.get("version") != EDITORIAL_REVIEW_VERSION:
        errors.append(f"version must be {EDITORIAL_REVIEW_VERSION}")
    if review.get("status") not in EDITORIAL_REVIEW_STATUSES:
        errors.append(f"status must be one of {sorted(EDITORIAL_REVIEW_STATUSES)}")
    if review.get("reviewer_identity") != EDITORIAL_REVIEWER_IDENTITY:
        errors.append("reviewer_identity must be editorial_reviewer")
    if review.get("review_mode") not in EDITORIAL_REVIEW_MODES:
        errors.append(f"review_mode must be one of {sorted(EDITORIAL_REVIEW_MODES)}")
    lenses = review.get("rubric_lenses")
    roles = _role_map()
    if not isinstance(lenses, list) or not lenses:
        errors.append("rubric_lenses must be a non-empty list")
    else:
        unknown_lenses = [lens for lens in lenses if lens not in roles]
        if unknown_lenses:
            errors.append(f"unknown rubric_lens: {unknown_lenses!r}")
    if review.get("authority") != EDITORIAL_REVIEW_AUTHORITY:
        errors.append("authority must be findings_and_proposals_only")
    forbidden = review.get("forbidden_actions")
    if not isinstance(forbidden, list) or not EDITORIAL_REQUIRED_FORBIDDEN_ACTIONS.issubset(set(forbidden)):
        errors.append("forbidden_actions must include canonical mutation, repair, creative approval, and delivery claim bans")
    for key in ("inspection_scope", "not_inspected", "strengths", "findings", "evidence_gaps"):
        expected = list if key != "inspection_scope" else Mapping
        if not isinstance(review.get(key), expected):
            errors.append(f"{key} must be a {'list' if expected is list else 'mapping'}")
    subject = review.get("subject")
    errors.extend(_validate_subject(subject))
    errors.extend(_validate_exact_subject_binding(review, subject))
    manifest = review.get("evidence_manifest")
    manifest_errors, manifest_items = _validate_evidence_manifest(manifest, subject if isinstance(subject, Mapping) else {}, prefix="evidence_manifest")
    errors.extend(manifest_errors)
    errors.extend(_validate_chapter_candidates(
        review.get("chapter_candidates"),
        subject if isinstance(subject, Mapping) else {},
        manifest_items,
    ))
    if review.get("human_creative_approval") is not False:
        errors.append("human_creative_approval must be false")
    if review.get("final_delivery_claimed") is not False:
        errors.append("final_delivery_claimed must be false")

    findings = review.get("findings") if isinstance(review.get("findings"), list) else []
    taste_count = 0
    capability_ids, capability_errors = _live_capability_ids()
    for index, finding in enumerate(findings):
        label = f"findings[{index}]"
        if not isinstance(finding, Mapping):
            errors.append(f"{label} must be an object")
            continue
        for key in ("finding_id", "rubric_id", "observation", "interpretation", "why_it_matters"):
            if not _has_text(finding.get(key)):
                errors.append(f"{label}.{key} is required")
        finding_class = finding.get("class")
        if finding_class not in EDITORIAL_FINDING_CLASSES:
            errors.append(f"{label}.class must be one of {sorted(EDITORIAL_FINDING_CLASSES)}")
        if finding.get("priority") not in EDITORIAL_FINDING_PRIORITIES:
            errors.append(f"{label}.priority must be one of {sorted(EDITORIAL_FINDING_PRIORITIES)}")
        if finding.get("confidence") not in EDITORIAL_FINDING_CONFIDENCES:
            errors.append(f"{label}.confidence must be one of {sorted(EDITORIAL_FINDING_CONFIDENCES)}")
        if finding.get("fixable_at") not in EDITORIAL_FIXABLE_AT:
            errors.append(f"{label}.fixable_at must be one of {sorted(EDITORIAL_FIXABLE_AT)}")
        if not finding.get("target"):
            errors.append(f"{label}.target is required")
        if not isinstance(finding.get("requires_reopen"), bool):
            errors.append(f"{label}.requires_reopen must be true or false")
        lock_conflicts = finding.get("lock_conflicts", [])
        if not isinstance(lock_conflicts, list):
            errors.append(f"{label}.lock_conflicts must be a list")
        elif finding.get("requires_reopen") is True and not lock_conflicts:
            errors.append(f"{label}.lock_conflicts must explain requires_reopen=true")
        elif finding.get("requires_reopen") is False and lock_conflicts:
            errors.append(f"{label}.lock_conflicts require requires_reopen=true")
        refs = finding.get("evidence_refs")
        if not isinstance(refs, list) or not refs:
            errors.append(f"{label}.evidence_refs must be a non-empty list")
        else:
            for ref_index, ref in enumerate(refs):
                ref_label = f"{label}.evidence_refs[{ref_index}]"
                if not isinstance(ref, Mapping):
                    errors.append(f"{ref_label} must be an object")
                    continue
                evidence_id = ref.get("evidence_id") or ref.get("id")
                item = manifest_items.get(str(evidence_id)) if evidence_id else None
                if item is None:
                    errors.append(f"{ref_label} unresolved evidence_id: {evidence_id!r}")
                    continue
                window = ref.get("time_range") or ref.get("covered_timeline_window")
                errors.extend(_validate_timeline_window(window, f"{ref_label}.time_range"))
                ref_bounds = _window_bounds(window)
                item_bounds = _window_bounds(item.get("covered_timeline_window"))
                if ref_bounds and item_bounds and (ref_bounds[0] < item_bounds[0] or ref_bounds[1] > item_bounds[1]):
                    errors.append(f"{ref_label}.time_range must be within evidence item window")
        falsification = finding.get("falsification_test")
        human_taste_only = finding.get("human_taste_only") is True
        if finding_class == "taste":
            taste_count += 1
            if not human_taste_only and not _has_text(falsification):
                errors.append(f"{label} taste finding requires human_taste_only or falsification_test")
            if str(finding.get("machine_verdict") or "").lower() in {"pass", "fail", "block", "blocked"}:
                errors.append(f"{label} taste finding cannot carry a deterministic machine verdict")
        elif not _has_text(falsification):
            errors.append(f"{label} requires falsification_test")
        if "proposed_fix" not in finding:
            errors.append(f"{label}.proposed_fix is required")
        else:
            errors.extend(_validate_proposed_fix(finding.get("proposed_fix"), f"{label}.proposed_fix", capability_ids, capability_errors))
        if "fallback_fix" in finding and finding.get("fallback_fix") is not None:
            errors.extend(_validate_proposed_fix(finding.get("fallback_fix"), f"{label}.fallback_fix", capability_ids, capability_errors))
        errors.extend(f"{label} contains forbidden mutation key {key}" for key in _forbidden_keys(finding))
    if taste_count > 3:
        errors.append("taste findings are capped at three")
    errors.extend(f"review contains forbidden mutation key {key}" for key in _forbidden_keys(review))
    return {"ok": not errors, "errors": errors, "contract": "editorial_review_v2"}


def validate_review_artifact(review: Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(review, Mapping) and review.get("editorial_review") is not None:
        block = review.get("editorial_review")
        if isinstance(block, Mapping):
            payload = dict(block)
            payload.setdefault("artifact_role", EDITORIAL_REVIEW_ARTIFACT_ROLE)
            result = validate_editorial_review(payload)
            if not result["ok"]:
                result["errors"] = [f"editorial_review: {error}" for error in result["errors"]]
            return result
        return {"ok": False, "errors": ["editorial_review must be an object"]}
    if isinstance(review, Mapping) and (
        review.get("artifact_role") == EDITORIAL_REVIEW_ARTIFACT_ROLE
        or review.get("version") == EDITORIAL_REVIEW_VERSION
    ):
        return validate_editorial_review(review)
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


def sha256_file(path: str | Path) -> str:
    """Return the SHA-256 of a persisted artifact, after it is fully written."""
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _resolve_review_reference(raw_path: Any, *, review_path: Path) -> Path | None:
    if not isinstance(raw_path, str) or not raw_path.strip():
        return None
    candidate = Path(raw_path)
    if candidate.is_file():
        return candidate
    if not candidate.is_absolute():
        for base in (Path.cwd(), review_path.parent):
            resolved = base / candidate
            if resolved.is_file():
                return resolved
    return None


def write_editorial_review_receipt(
    review_path: str | Path,
    validation: Mapping[str, Any],
    out: str | Path,
) -> dict[str, Any]:
    """Persist a hash-bound receipt for a validated editorial review.

    The receipt is intentionally additive: it does not mutate the review or
    canonical state. It records the bytes actually validated, plus any packet
    and subject rechecks that were available at the time of validation.
    """
    if not validation.get("ok"):
        raise ValueError("cannot write a receipt for an invalid editorial review")
    review_file = Path(review_path)
    if not review_file.is_file():
        raise ValueError(f"review artifact not found: {review_file}")
    review = json.loads(review_file.read_text(encoding="utf-8-sig"))
    receipt: dict[str, Any] = {
        "artifact_role": "editorial_review_receipt",
        "version": 1,
        "validator_contract": validation.get("contract", "editorial_review_v2"),
        "review": {
            "path": str(review_file),
            "sha256": sha256_file(review_file),
        },
        "validation": {
            "ok": True,
            "errors": list(validation.get("errors") or []),
        },
        "authority_flags": {
            "human_creative_approval": bool(review.get("human_creative_approval", False)),
            "final_delivery_claimed": bool(review.get("final_delivery_claimed", False)),
        },
    }

    subject = review.get("subject")
    if isinstance(subject, Mapping):
        receipt["subject"] = {
            "path": subject.get("path"),
            "sha256": subject.get("sha256"),
            "recheck": "not_available",
        }
        subject_file = _resolve_review_reference(subject.get("path"), review_path=review_file)
        if subject_file is not None:
            actual = sha256_file(subject_file)
            receipt["subject"]["recheck"] = {
                "path": str(subject_file),
                "sha256": actual,
                "matches_declared": actual == subject.get("sha256"),
            }
            if actual != subject.get("sha256"):
                raise ValueError("subject_sha256_mismatch")

    packet_path = review.get("packet_path")
    packet_hash = review.get("packet_sha256")
    if packet_path or packet_hash:
        packet_file = _resolve_review_reference(packet_path, review_path=review_file)
        packet_record: dict[str, Any] = {
            "path": packet_path,
            "sha256": packet_hash,
            "recheck": "not_available",
        }
        if packet_file is None:
            raise ValueError("packet_artifact_not_found")
        actual = sha256_file(packet_file)
        packet_record["recheck"] = {
            "path": str(packet_file),
            "sha256": actual,
            "matches_declared": actual == packet_hash,
        }
        if packet_hash and actual != packet_hash:
            raise ValueError("packet_sha256_mismatch")
        receipt["packet"] = packet_record

    if review.get("binding_contract_version") == EDITORIAL_BINDING_CONTRACT_VERSION:
        for key in (
            "binding_contract_version",
            "reviewed_subject_sha256",
            "applies_to_candidate_sha256",
            "subject_hash_method",
        ):
            receipt[key] = review[key]

    out_file = Path(out)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(receipt, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return receipt


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
