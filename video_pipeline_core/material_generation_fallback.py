"""MGF1 — material generation fallback planner.

This module converts a validated material delta into provider-neutral generation
jobs. It deliberately does NOT create accepted material-map evidence. Generated
assets must be produced externally, re-ingested, reviewed, and linked back as
candidate/accepted satisfies edges by the material-map lifecycle.
"""
from __future__ import annotations

import hashlib
from typing import Any, Dict, Iterable, Mapping, Optional

from .material_needs import validate_material_needs


GENERATABLE_OUTCOMES = ("missing", "thin")
DEFAULT_NEGATIVE_PROMPT = (
    "text, watermark, signature, logo, subtitle, UI elements, distorted hands, "
    "deformed face, fake organization mark, unrelated subject"
)


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _text(value: Any, default: str = "") -> str:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return default


def _need_index(material_needs: Optional[Mapping[str, Any]]) -> tuple[dict, list]:
    if material_needs is None:
        return {}, []
    validation = validate_material_needs(material_needs)
    if not validation["ok"]:
        return {}, [f"material_needs invalid: {'; '.join(validation['errors'])}"]
    return {need["need_id"]: need for need in validation["needs"]}, []


def _index_by_need(plan: Optional[Mapping[str, Any]]) -> dict:
    if not isinstance(plan, Mapping):
        return {}
    rows: list = []
    for key in ("shots", "items", "materials", "needs"):
        rows.extend(_as_list(plan.get(key)))
    indexed = {}
    for row in rows:
        if isinstance(row, Mapping) and _text(row.get("need_id")):
            indexed.setdefault(row["need_id"], dict(row))
    return indexed


def _concept_text(creative_concept: Optional[Mapping[str, Any]]) -> str:
    if not isinstance(creative_concept, Mapping):
        return ""
    parts = []
    for key in ("core_metaphor", "narrative_device", "logline"):
        value = _text(creative_concept.get(key))
        if value:
            parts.append(value)
    motifs = creative_concept.get("visual_motifs")
    if isinstance(motifs, list) and motifs:
        parts.append("visual motifs: " + ", ".join(str(m) for m in motifs if str(m).strip()))
    return "; ".join(parts)


def _prompt_for(need: Mapping[str, Any], shot: Mapping[str, Any],
                creative_concept: Optional[Mapping[str, Any]]) -> str:
    seeded = [
        _concept_text(creative_concept),
        _text(shot.get("prompt")),
        _text(shot.get("visual_intent")),
        _text(need.get("purpose")),
        _text(shot.get("story_function")),
        _text(shot.get("emotion")),
    ]
    subject = _text(shot.get("subject"))
    if subject:
        seeded.append(f"primary subject: {subject}")
    action = _text(shot.get("action_family"))
    if action:
        seeded.append(f"action: {action}")
    family = _text(shot.get("visual_family"))
    scale = _text(shot.get("angle_scale"))
    if family or scale:
        seeded.append(f"shot language: {family or 'project-defined family'}, {scale or 'unspecified scale'}")
    prompt = "; ".join(part for part in seeded if part)
    if not prompt:
        prompt = f"Generate material for need {need.get('need_id')}: {need.get('purpose') or 'unspecified purpose'}"
    return prompt


def _panel_count(delta: Mapping[str, Any], shot: Mapping[str, Any]) -> int:
    evidence = delta.get("evidence") if isinstance(delta.get("evidence"), Mapping) else {}
    required = evidence.get("required_count", 1)
    accepted = evidence.get("accepted", 0)
    if not isinstance(required, int) or isinstance(required, bool) or required < 1:
        required = 1
    if not isinstance(accepted, int) or isinstance(accepted, bool) or accepted < 0:
        accepted = 0
    if delta.get("outcome") == "thin":
        return max(required - accepted, 1)
    minimum = shot.get("panel_count_min")
    if isinstance(minimum, int) and not isinstance(minimum, bool) and minimum > required:
        return minimum
    return required


def _media_type(shot: Mapping[str, Any]) -> str:
    preference = _text(shot.get("media_preference"), "generated_image")
    if preference in ("generated_video", "video"):
        return "generated_video"
    return "generated_image"


def _job_id(need_id: str, outcome: str, prompt: str) -> str:
    basis = f"{need_id}|{outcome}|{prompt}"
    return "gen_" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:10]


def _generation_job(delta: Mapping[str, Any], need: Mapping[str, Any],
                    shot: Mapping[str, Any],
                    creative_concept: Optional[Mapping[str, Any]]) -> dict:
    need_id = _text(delta.get("need_id"))
    prompt = _prompt_for(need, shot, creative_concept)
    return {
        "job_id": _job_id(need_id, _text(delta.get("outcome")), prompt),
        "need_id": need_id,
        "beat_id": _text(shot.get("beat_id"), None),
        "source_type": "generated",
        "status": "planned",
        "media_type": _media_type(shot),
        "panel_count": _panel_count(delta, shot),
        "story_function": _text(shot.get("story_function"), _text(need.get("purpose"))),
        "emotion": _text(shot.get("emotion")),
        "visual_family": _text(shot.get("visual_family")),
        "angle_scale": _text(shot.get("angle_scale")),
        "action_family": _text(shot.get("action_family")),
        "subject": _text(shot.get("subject")),
        "prompt": prompt,
        "negative_prompt": _text(shot.get("negative_prompt"), DEFAULT_NEGATIVE_PROMPT),
        "review_criteria": [
            "matches declared need_id and purpose",
            "supports the beat story_function rather than decorative filler",
            "keeps project visual style and visual_family consistent",
            "contains no fake documentary proof, fake logo, watermark, or unreadable text",
            "must not be accepted without visual review and material-map satisfies edge",
        ],
        "fallback_if_generation_fails": _text(
            shot.get("fallback_if_missing"),
            "; ".join(need.get("fallback_options") or []) or "return to material_delta revision decision",
        ),
        "derived_from": {
            "artifact_role": "material_delta",
            "need_id": need_id,
            "outcome": _text(delta.get("outcome")),
            "route": _text(delta.get("route")),
            "tier": delta.get("tier"),
            "reason": _text(delta.get("reason")),
        },
        "material_map_return": {
            "must_reingest": True,
            "initial_satisfies_status": "candidate",
            "reviewer_must_accept_before_build": True,
        },
        "honesty": {
            "must_not_claim_real_event": True,
            "must_not_replace_identity_sensitive_real_footage_without_waiver": True,
        },
    }


def plan_material_generation_fallback(
    material_delta: Mapping[str, Any],
    *,
    material_needs: Optional[Mapping[str, Any]] = None,
    story_world: Optional[Mapping[str, Any]] = None,
    creative_concept: Optional[Mapping[str, Any]] = None,
    screenplay_beats: Optional[Mapping[str, Any]] = None,
    director_shot_plan: Optional[Mapping[str, Any]] = None,
) -> dict:
    """Create provider-neutral generation jobs from missing/thin material needs.

    Extra context arguments are accepted so the artifact can preserve the
    upstream creative chain; only the director shot plan and creative concept are
    used for deterministic prompt construction in MGF1.
    """
    del story_world, screenplay_beats  # reserved for future prompt enrichment
    errors = []
    if not isinstance(material_delta, Mapping):
        errors.append("material_delta must be an object")
    elif material_delta.get("ok") is not True:
        errors.append("delta is not ok; fix lineage/material map before planning generation")
    needs_by_id, need_errors = _need_index(material_needs)
    errors.extend(need_errors)
    if errors:
        return {
            "artifact_role": "material_generation_fallback",
            "version": 1,
            "ok": False,
            "errors": errors,
            "generation_jobs": [],
            "review_gate": {
                "generated_assets_enter_as": "candidate",
                "must_reingest": True,
                "must_not_claim_real_footage": True,
            },
            "summary": {"jobs": 0, "needs": 0, "skipped": 0},
        }

    shot_by_need = _index_by_need(director_shot_plan)
    jobs = []
    skipped = 0
    seen_needs = set()
    for delta in _as_list(material_delta.get("deltas")):
        if not isinstance(delta, Mapping):
            skipped += 1
            continue
        outcome = delta.get("outcome")
        if outcome not in GENERATABLE_OUTCOMES:
            skipped += 1
            continue
        need_id = _text(delta.get("need_id"))
        if not need_id:
            skipped += 1
            continue
        need = needs_by_id.get(need_id, {"need_id": need_id})
        shot = shot_by_need.get(need_id, {})
        jobs.append(_generation_job(delta, need, shot, creative_concept))
        seen_needs.add(need_id)

    return {
        "artifact_role": "material_generation_fallback",
        "version": 1,
        "ok": True,
        "errors": [],
        "generation_jobs": jobs,
        "review_gate": {
            "generated_assets_enter_as": "candidate",
            "must_reingest": True,
            "must_not_claim_real_footage": True,
            "generated_assets_do_not_bypass_m6_delta": True,
        },
        "summary": {
            "jobs": len(jobs),
            "needs": len(seen_needs),
            "skipped": skipped,
        },
    }
