"""Neutral effect-intent contract for FX1.

This module intentionally does not import Remotion or ffmpeg render code. It
compiles upstream director/story effect intent into Hermes-native artifacts that
later BUILD/Node14 adapters can consume.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping


ALLOWED_EFFECT_ROLES = {
    "title_card",
    "chapter_transition",
    "lower_third",
    "color_grade",
    "overlay",
    "particle",
    "light_leak",
    "transition_plate",
    "motion_background",
    "panel_frame",
    "speed_line",
}

ALLOWED_INTENSITIES = {"none", "low", "medium", "high"}
ALLOWED_BACKENDS = {
    "ffmpeg_light_effects",
    "motion_graphics",
    "remotion_preview",
    "remotion_render",
}
DEFAULT_ALLOWED_BACKENDS = ["ffmpeg_light_effects", "motion_graphics", "remotion_preview"]

REMOTION_SPECIFIC_FIELDS = {
    "component",
    "durationFrames",
    "fps",
    "springConfig",
    "remotion_component",
    "remotion_props",
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


def _bool(value: Any, field: str, default: bool = False) -> bool:
    if value is None:
        return default
    if not isinstance(value, bool):
        raise ValueError(f"{field} must be boolean")
    return value


def _string_list(value: Any, field: str) -> List[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"{field} must be list[str]")
    out = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field} must contain non-empty strings")
        out.append(item.strip())
    return out


def _effect_id(beat_id: str, role: str) -> str:
    safe_beat = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in beat_id)
    safe_role = "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in role)
    return f"fx_{safe_beat}_{safe_role}"


def _asset_id(effect_id: str, role: str, visual_language: Iterable[str]) -> str:
    seed = "|".join([effect_id, role, *visual_language])
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]
    return f"efa_{digest}"


def _iter_beats(payload: Mapping[str, Any]) -> Iterable[Mapping[str, Any]]:
    beats = payload.get("beats")
    if beats is None:
        beats = payload.get("director_shot_plan")
    if beats is None:
        return []
    if not isinstance(beats, list):
        raise ValueError("director shot plan beats must be a list")
    for idx, beat in enumerate(beats):
        if not isinstance(beat, dict):
            raise ValueError(f"beat {idx} must be object")
        yield beat


def _normalize_allowed_backends(value: Any, required_for_story: bool) -> List[str]:
    if value is None:
        allowed = list(DEFAULT_ALLOWED_BACKENDS)
    else:
        allowed = _string_list(value, "allowed_backends")
        if not allowed:
            raise ValueError("allowed_backends must not be empty when present")
    for backend in allowed:
        if backend not in ALLOWED_BACKENDS:
            raise ValueError(f"unsupported effect backend: {backend}")
    if required_for_story and not allowed:
        raise ValueError("required effect needs at least one allowed backend")
    return allowed


def _ensure_no_backend_specific_fields(payload: Mapping[str, Any], context: str) -> None:
    for field in REMOTION_SPECIFIC_FIELDS:
        if field in payload:
            raise ValueError(f"{context} must not contain backend-specific field {field}")


def compile_effect_contract(director_shot_plan: Mapping[str, Any]) -> Dict[str, Any]:
    """Compile director-shot-plan effect intents into neutral effect artifacts."""

    if not isinstance(director_shot_plan, dict):
        raise ValueError("director_shot_plan must be object")

    effects: List[Dict[str, Any]] = []
    assets: List[Dict[str, Any]] = []
    seen_effect_ids = set()

    for idx, beat in enumerate(_iter_beats(director_shot_plan)):
        raw = beat.get("effect_intent") or beat.get("effect")
        if raw is None:
            continue
        if not isinstance(raw, dict):
            raise ValueError(f"beat {idx} effect_intent must be object")
        _ensure_no_backend_specific_fields(raw, f"beat {idx} effect_intent")

        beat_id = _non_empty_str(beat.get("beat_id") or beat.get("id") or f"beat_{idx + 1}", "beat_id")
        role = _non_empty_str(raw.get("role"), "effect role")
        if role not in ALLOWED_EFFECT_ROLES:
            raise ValueError(f"unsupported effect role: {role}")
        intensity = _optional_str(raw.get("intensity"), "effect intensity", default="medium") or "medium"
        if intensity not in ALLOWED_INTENSITIES:
            raise ValueError(f"unsupported effect intensity: {intensity}")

        effect_id = _optional_str(raw.get("effect_id"), "effect_id") or _effect_id(beat_id, role)
        if effect_id in seen_effect_ids:
            raise ValueError(f"duplicate effect_id: {effect_id}")
        seen_effect_ids.add(effect_id)

        required = _bool(raw.get("required_for_story"), "required_for_story", default=False)
        visual_language = _string_list(raw.get("visual_language"), "visual_language")
        allowed_backends = _normalize_allowed_backends(raw.get("allowed_backends"), required)
        target = {
            "beat_id": beat_id,
            "segment_id": _optional_str(beat.get("segment_id"), "segment_id"),
            "story_function": _optional_str(beat.get("story_function"), "story_function"),
        }
        target = {k: v for k, v in target.items() if v}
        if "beat_id" not in target:
            target["beat_id"] = beat_id

        effect = {
            "effect_id": effect_id,
            "role": role,
            "intent": _non_empty_str(raw.get("intent") or raw.get("purpose") or role, "effect intent"),
            "intensity": intensity,
            "target": target,
            "visual_language": visual_language,
            "required_for_story": required,
            "must_preserve_proof": _bool(raw.get("must_preserve_proof"), "must_preserve_proof", default=False),
            "allowed_backends": allowed_backends,
            "fallback": _optional_str(raw.get("fallback"), "fallback", default="simple_fade"),
        }
        effects.append(effect)

        if role in {"title_card", "chapter_transition", "lower_third", "overlay", "particle",
                    "light_leak", "transition_plate", "motion_background", "panel_frame", "speed_line"}:
            assets.append({
                "effect_asset_id": _asset_id(effect_id, role, visual_language),
                "effect_id": effect_id,
                "asset_role": "effect",
                "asset_type": _asset_type_for_role(role),
                "source_type": "planned_or_generated",
                "visual_language": visual_language,
                "must_not_satisfy_material_need": True,
                "required_for_story": required,
            })

    plan = {
        "artifact_role": "effect_intent_plan",
        "version": 1,
        "effects": effects,
        "backend_boundary": {
            "neutral_contract": True,
            "backend_specific_fields_forbidden": sorted(REMOTION_SPECIFIC_FIELDS),
            "canonical_final_renderer": "ffmpeg_contract_run",
        },
    }
    spec = {
        "artifact_role": "effect_asset_spec",
        "version": 1,
        "assets": assets,
        "truth_boundary": {
            "effect_assets_are_not_event_evidence": True,
            "must_not_satisfy_material_need": True,
        },
    }
    validate_effect_intent_plan(plan)
    validate_effect_asset_spec(spec)
    return {"effect_intent_plan": plan, "effect_asset_spec": spec}


def _asset_type_for_role(role: str) -> str:
    if role in {"title_card", "lower_third"}:
        return "text_graphic"
    if role in {"chapter_transition", "transition_plate"}:
        return "transition_plate"
    if role in {"particle", "light_leak", "overlay", "speed_line", "panel_frame"}:
        return "overlay"
    if role == "motion_background":
        return "motion_background"
    return "effect"


def validate_effect_intent_plan(plan: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(plan, dict):
        raise ValueError("effect_intent_plan must be object")
    if plan.get("artifact_role") != "effect_intent_plan":
        raise ValueError("artifact_role must be effect_intent_plan")
    if plan.get("version") != 1:
        raise ValueError("effect_intent_plan version must be 1")
    effects = plan.get("effects")
    if not isinstance(effects, list):
        raise ValueError("effects must be list")
    seen = set()
    for idx, effect in enumerate(effects):
        if not isinstance(effect, dict):
            raise ValueError(f"effect {idx} must be object")
        _ensure_no_backend_specific_fields(effect, f"effect {idx}")
        effect_id = _non_empty_str(effect.get("effect_id"), "effect_id")
        if effect_id in seen:
            raise ValueError(f"duplicate effect_id: {effect_id}")
        seen.add(effect_id)
        role = _non_empty_str(effect.get("role"), "role")
        if role not in ALLOWED_EFFECT_ROLES:
            raise ValueError(f"unsupported effect role: {role}")
        intensity = _non_empty_str(effect.get("intensity"), "intensity")
        if intensity not in ALLOWED_INTENSITIES:
            raise ValueError(f"unsupported intensity: {intensity}")
        target = effect.get("target")
        if not isinstance(target, dict) or not target:
            raise ValueError("effect target must be non-empty object")
        _string_list(effect.get("visual_language"), "visual_language")
        _normalize_allowed_backends(effect.get("allowed_backends"), bool(effect.get("required_for_story")))
        _bool(effect.get("required_for_story"), "required_for_story")
        _bool(effect.get("must_preserve_proof"), "must_preserve_proof")
    return plan


def validate_effect_asset_spec(spec: Mapping[str, Any]) -> Mapping[str, Any]:
    if not isinstance(spec, dict):
        raise ValueError("effect_asset_spec must be object")
    if spec.get("artifact_role") != "effect_asset_spec":
        raise ValueError("artifact_role must be effect_asset_spec")
    if spec.get("version") != 1:
        raise ValueError("effect_asset_spec version must be 1")
    assets = spec.get("assets")
    if not isinstance(assets, list):
        raise ValueError("assets must be list")
    seen = set()
    for idx, asset in enumerate(assets):
        if not isinstance(asset, dict):
            raise ValueError(f"asset {idx} must be object")
        asset_id = _non_empty_str(asset.get("effect_asset_id"), "effect_asset_id")
        if asset_id in seen:
            raise ValueError(f"duplicate effect_asset_id: {asset_id}")
        seen.add(asset_id)
        if asset.get("asset_role") != "effect":
            raise ValueError("effect assets must use asset_role=effect")
        if asset.get("must_not_satisfy_material_need") is not True:
            raise ValueError("effect assets must declare must_not_satisfy_material_need=true")
        _non_empty_str(asset.get("effect_id"), "effect_id")
        _non_empty_str(asset.get("asset_type"), "asset_type")
        _string_list(asset.get("visual_language"), "visual_language")
        _bool(asset.get("required_for_story"), "required_for_story")
    return spec


def compile_effect_contract_file(source: str | Path, *, out_plan: str | Path, out_spec: str | Path) -> Dict[str, str]:
    with Path(source).open(encoding="utf-8") as f:
        payload = json.load(f)
    compiled = compile_effect_contract(payload)
    out_plan = Path(out_plan)
    out_spec = Path(out_spec)
    out_plan.parent.mkdir(parents=True, exist_ok=True)
    out_spec.parent.mkdir(parents=True, exist_ok=True)
    out_plan.write_text(json.dumps(compiled["effect_intent_plan"], ensure_ascii=False, indent=2), encoding="utf-8")
    out_spec.write_text(json.dumps(compiled["effect_asset_spec"], ensure_ascii=False, indent=2), encoding="utf-8")
    return {
        "effect_intent_plan": str(out_plan),
        "effect_asset_spec": str(out_spec),
    }

