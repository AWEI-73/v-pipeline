"""Draft Material Wall review decisions from a material understanding matrix.

This is an assisted review layer, not material truth. It turns the observation
matrix into a conservative wall verdict draft: one primary candidate per
required role, with alternates kept outside the formal keep/maybe set.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping, Sequence


BLOCKING_RISKS = {"looks_like_finished_export", "source_missing", "unsupported_media_type"}
DUPLICATE_RISKS = {"possible_duplicate_name"}
ROLE_PREFERENCES = {
    "opening": {
        "prefer": ("aerial", "establish", "opening", "intro", "空拍", "開場", "全景"),
        "avoid": ("meeting", "briefing", "早會", "簡報"),
    },
    "training": {
        "prefer": (
            "practice",
            "practical",
            "operation",
            "hands-on",
            "field",
            "換桿",
            "訓練",
            "實作",
            "操作",
            "演練",
        ),
        "avoid": ("meeting", "briefing", "classroom", "早會", "簡報", "會議"),
    },
    "closing": {
        "prefer": ("group", "chant", "closing", "ending", "隊呼", "合照", "結尾", "收尾"),
        "avoid": (),
    },
}


def _write_json(path: Path, payload: Mapping[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _duration(asset: Mapping[str, Any]) -> float:
    try:
        return max(0.0, float(asset.get("duration_sec") or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _roles(asset: Mapping[str, Any]) -> list[str]:
    return [str(role).strip() for role in (asset.get("role_hints") or []) if str(role).strip()]


def _risks(asset: Mapping[str, Any]) -> set[str]:
    return {str(flag).strip() for flag in (asset.get("risk_flags") or []) if str(flag).strip()}


def _text_blob(asset: Mapping[str, Any]) -> str:
    visual = asset.get("visual_evidence") if isinstance(asset.get("visual_evidence"), Mapping) else {}
    parts = [
        asset.get("asset_id"),
        asset.get("source_path"),
        visual.get("caption_hint"),
    ]
    parts.extend(asset.get("folder_tags") or [])
    return " ".join(str(part) for part in parts if part).lower()


def _evidence_refs(asset: Mapping[str, Any]) -> list[str]:
    visual = asset.get("visual_evidence") if isinstance(asset.get("visual_evidence"), Mapping) else {}
    refs: list[str] = []
    photo = visual.get("photo")
    if isinstance(photo, str) and photo.strip():
        refs.append(photo.strip())
    for frame in visual.get("keyframes") or []:
        if not isinstance(frame, Mapping):
            continue
        image = frame.get("image_path")
        if isinstance(image, str) and image.strip():
            refs.append(image.strip())
    caption = visual.get("caption_hint")
    if isinstance(caption, str) and caption.strip():
        refs.append(f"caption:{caption.strip()[:120]}")
    return refs or [str(asset.get("source_path") or asset.get("asset_id") or "matrix_observation")]


def _usable_ranges(asset: Mapping[str, Any]) -> list[dict[str, float]]:
    duration = _duration(asset)
    if duration <= 0:
        return []
    start = 1.0 if duration > 2.0 else 0.0
    end = min(duration, start + 6.0)
    if end <= start:
        start = 0.0
        end = min(duration, 4.0)
    return [{"start": round(start, 3), "end": round(end, 3)}]


def _preference_score(asset: Mapping[str, Any], role: str) -> int:
    prefs = ROLE_PREFERENCES.get(role) or {}
    text = _text_blob(asset)
    prefer = sum(1 for keyword in prefs.get("prefer", ()) if keyword.lower() in text)
    avoid = sum(1 for keyword in prefs.get("avoid", ()) if keyword.lower() in text)
    return avoid - prefer


def _candidate_score(asset: Mapping[str, Any], role: str, index: int) -> tuple[int, int, int, float, int]:
    roles = _roles(asset)
    risks = _risks(asset)
    role_miss = 0 if role in roles else 1
    risk_penalty = len(risks.intersection(BLOCKING_RISKS)) * 100 + len(risks.intersection(DUPLICATE_RISKS)) * 10
    # Prefer assets with enough footage, but keep order as the main tie breaker.
    duration_bonus = -min(_duration(asset), 12.0)
    return (role_miss, risk_penalty, _preference_score(asset, role), duration_bonus, index)


def _select_primaries(assets: list[Mapping[str, Any]], required_roles: Sequence[str]) -> dict[str, str]:
    selected: dict[str, str] = {}
    used: set[str] = set()
    indexed = list(enumerate(assets))
    for role in required_roles:
        candidates = [
            (index, asset) for index, asset in indexed
            if role in _roles(asset)
            and str(asset.get("asset_id") or "") not in used
            and not _risks(asset).intersection(BLOCKING_RISKS | DUPLICATE_RISKS)
        ]
        if not candidates:
            candidates = [
                (index, asset) for index, asset in indexed
                if role in _roles(asset)
                and str(asset.get("asset_id") or "") not in used
                and not _risks(asset).intersection(BLOCKING_RISKS)
            ]
        if not candidates:
            continue
        _, primary = min(candidates, key=lambda pair: _candidate_score(pair[1], role, pair[0]))
        asset_id = str(primary.get("asset_id") or "")
        if asset_id:
            selected[role] = asset_id
            used.add(asset_id)
    return selected


def _best_role_for_asset(asset: Mapping[str, Any], required_roles: Sequence[str]) -> str | None:
    roles = _roles(asset)
    for role in required_roles:
        if role in roles:
            return role
    return roles[0] if roles else None


def build_wall_verdict_draft(
    matrix: Mapping[str, Any],
    *,
    out_path: str | Path | None = None,
    required_roles: Sequence[str] | None = None,
) -> dict[str, Any]:
    roles = [str(role).strip() for role in (required_roles or ["opening", "training", "closing"]) if str(role).strip()]
    assets = [asset for asset in (matrix.get("assets") or []) if isinstance(asset, Mapping) and asset.get("asset_id")]
    primary_selection = _select_primaries(assets, roles)
    primary_by_asset = {asset_id: role for role, asset_id in primary_selection.items()}
    primary_for_role = dict(primary_selection)

    verdict_assets: list[dict[str, Any]] = []
    alternates: list[dict[str, Any]] = []
    for asset in assets:
        asset_id = str(asset.get("asset_id"))
        role = primary_by_asset.get(asset_id) or _best_role_for_asset(asset, roles)
        risks = sorted(_risks(asset))
        if asset_id in primary_by_asset:
            status = "keep"
            why_not_selected = None
            duplicate_of = None
            quality = "primary_candidate"
            visual_role = [primary_by_asset[asset_id]]
        elif risks and set(risks).intersection(DUPLICATE_RISKS) and role and primary_for_role.get(role):
            status = "duplicate"
            why_not_selected = f"alternate duplicate candidate for {role}; primary is {primary_for_role[role]}"
            duplicate_of = primary_for_role[role]
            quality = "alternate_duplicate"
            visual_role = [role]
        elif role and not set(risks).intersection(BLOCKING_RISKS):
            status = "reject"
            why_not_selected = f"alternate_candidate for {role}; not primary for bounded acceptance"
            duplicate_of = None
            quality = "alternate_candidate"
            visual_role = [role]
        else:
            status = "reject"
            why_not_selected = "not selected by material understanding matrix draft"
            duplicate_of = None
            quality = "not_recommended"
            visual_role = [role] if role else []

        if quality.startswith("alternate"):
            alternates.append({
                "asset_id": asset_id,
                "for_role": role,
                "reason": why_not_selected,
                "risk_flags": risks,
                "source_path": asset.get("source_path"),
            })

        item: dict[str, Any] = {
            "asset_id": asset_id,
            "coarse_status": status,
            "visual_role": visual_role,
            "quality": quality,
            "duplicate_of": duplicate_of,
            "usable_ranges": _usable_ranges(asset) if status == "keep" else [],
            "visual_evidence": _evidence_refs(asset) if status == "keep" else [],
            "why_not_selected": why_not_selected,
            "notes": "drafted from material_understanding_matrix; requires human/agent review before high-stakes use",
        }
        verdict_assets.append(item)

    missing_roles = [role for role in roles if role not in primary_selection]
    payload = {
        "artifact_role": "material_wall_review_verdict",
        "version": 1,
        "reviewer": "material_understanding_matrix:draft",
        "source_artifact": matrix.get("artifact_role") or "material_understanding_matrix",
        "primary_selection": primary_selection,
        "alternate_candidates": alternates,
        "assets": verdict_assets,
        "review_findings": {
            "required_roles": roles,
            "missing_primary_roles": missing_roles,
            "selected_count": len(primary_selection),
            "alternate_count": len(alternates),
            "scope": "assisted_draft_not_final_material_truth",
        },
        "next_action": "review_or_apply_primary_wall_verdict",
    }
    if out_path is not None:
        _write_json(Path(out_path), payload)
    return payload


def build_wall_verdict_draft_file(
    matrix_path: str | Path,
    *,
    out_path: str | Path,
    required_roles: Sequence[str] | None = None,
) -> dict[str, Any]:
    matrix = json.loads(Path(matrix_path).read_text(encoding="utf-8-sig"))
    return build_wall_verdict_draft(matrix, out_path=out_path, required_roles=required_roles)
