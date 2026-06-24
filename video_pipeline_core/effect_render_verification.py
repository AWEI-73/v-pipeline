"""Build delivery-gate effect render verification from reviewed effect assets."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8-sig") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _write_json(path: str | Path, payload: Mapping[str, Any]) -> str:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return str(path)


def _existing_refs(refs: Any, root: Path | None) -> list[str]:
    if not isinstance(refs, list):
        return []
    existing: list[str] = []
    for ref in refs:
        if not isinstance(ref, str) or not ref.strip():
            continue
        path = Path(ref)
        if root is not None and not path.is_absolute():
            path = root / path
        if path.is_file() and path.stat().st_size > 0:
            existing.append(str(path))
    return existing


def _planned_effects(effect_intent_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    if effect_intent_plan.get("artifact_role") != "effect_intent_plan":
        raise ValueError("artifact_role must be effect_intent_plan")
    effects = effect_intent_plan.get("effects")
    if not isinstance(effects, list):
        raise ValueError("effect_intent_plan.effects must be list")
    planned = []
    for idx, effect in enumerate(effects):
        if not isinstance(effect, dict):
            raise ValueError(f"effects[{idx}] must be object")
        effect_id = effect.get("effect_id")
        if not isinstance(effect_id, str) or not effect_id.strip():
            raise ValueError(f"effects[{idx}].effect_id must be non-empty string")
        planned.append(effect)
    return planned


def _accepted_review_items(remotion_effect_review: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    if remotion_effect_review.get("artifact_role") != "remotion_effect_review":
        raise ValueError("artifact_role must be remotion_effect_review")
    if remotion_effect_review.get("version") != 1:
        raise ValueError("remotion_effect_review version must be 1")
    items = remotion_effect_review.get("items")
    if not isinstance(items, list):
        raise ValueError("remotion_effect_review.items must be list")
    accepted: dict[str, dict[str, Any]] = {}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"items[{idx}] must be object")
        status = item.get("status")
        review = item.get("review") if isinstance(item.get("review"), dict) else {}
        if status != "accepted" and review.get("decision") != "accept":
            continue
        source_effect_id = item.get("source_effect_id") or item.get("effect_id")
        if isinstance(source_effect_id, str) and source_effect_id.strip():
            accepted[source_effect_id.strip()] = item
    return accepted


def build_effect_render_verification(
    effect_intent_plan: Mapping[str, Any],
    remotion_effect_review: Mapping[str, Any],
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Build effect_render_verification.json for delivery gate consumption."""
    root_path = Path(root) if root is not None else None
    planned = _planned_effects(effect_intent_plan)
    accepted = _accepted_review_items(remotion_effect_review)

    verified = []
    for effect in planned:
        effect_id = str(effect["effect_id"])
        item = accepted.get(effect_id)
        if item is None:
            verified.append({
                "effect_id": effect_id,
                "kind": effect.get("role") or effect.get("type"),
                "rendered": False,
                "required_for_story": bool(effect.get("required_for_story", effect.get("render_required", True))),
                "reason": "missing_accepted_remotion_review_item",
            })
            continue
        evidence_refs = _existing_refs(item.get("evidence_refs"), root_path)
        rendered_asset_refs = _existing_refs([item.get("rendered_asset")], root_path)
        preview_refs = _existing_refs([item.get("preview_file")], root_path)
        rendered = bool(evidence_refs and (rendered_asset_refs or preview_refs))
        record = {
            "effect_id": effect_id,
            "kind": effect.get("role") or effect.get("type") or item.get("role"),
            "rendered": rendered,
            "required_for_story": bool(effect.get("required_for_story", effect.get("render_required", True))),
            "source": "remotion_effect_review",
            "review_status": item.get("status"),
            "evidence_refs": evidence_refs,
        }
        if rendered_asset_refs:
            record["rendered_asset"] = rendered_asset_refs[0]
        if preview_refs:
            record["preview_file"] = preview_refs[0]
        if not rendered:
            record["reason"] = "accepted_review_item_missing_render_or_evidence"
        verified.append(record)

    rendered_count = sum(1 for item in verified if item.get("rendered") is True)
    return {
        "artifact_role": "effect_render_verification",
        "version": 1,
        "pass": rendered_count == len(verified),
        "source": {
            "effect_intent_plan_role": effect_intent_plan.get("artifact_role"),
            "remotion_effect_review_role": remotion_effect_review.get("artifact_role"),
        },
        "summary": {
            "planned_count": len(verified),
            "rendered_count": rendered_count,
            "missing_count": len(verified) - rendered_count,
        },
        "verified_effects": verified,
        "next_action": None if rendered_count == len(verified) else "review_or_render_missing_effects",
    }


def write_effect_render_verification(
    effect_intent_plan_path: str | Path,
    remotion_review_path: str | Path,
    out_path: str | Path,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_effect_render_verification(
        _load_json(effect_intent_plan_path),
        _load_json(remotion_review_path),
        root=root,
    )
    _write_json(out_path, payload)
    return payload
