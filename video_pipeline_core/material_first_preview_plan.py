"""Build a reviewable material-first preview rough-cut proposal.

The preview plan is deliberately not canonical BUILD truth. It expands the
matrix + wall verdict draft into a 60-90 second review proposal so a human or
agent can decide whether the material-first route is strong enough before
rendering.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


DEFAULT_ROLES = ["opening", "training", "closing"]


def _write_json(path: Path, payload: Mapping[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _duration(asset: Mapping[str, Any]) -> float:
    try:
        return max(0.0, float(asset.get("duration_sec") or 0.0))
    except (TypeError, ValueError):
        return 0.0


def _asset_role(asset: Mapping[str, Any], fallback: str | None = None) -> str:
    roles = [str(role).strip() for role in (asset.get("role_hints") or []) if str(role).strip()]
    return roles[0] if roles else (fallback or "support")


def _asset_index(matrix: Mapping[str, Any]) -> dict[str, Mapping[str, Any]]:
    return {
        str(asset.get("asset_id")): asset
        for asset in (matrix.get("assets") or [])
        if isinstance(asset, Mapping) and asset.get("asset_id")
    }


def _ordered_candidates(matrix: Mapping[str, Any], draft: Mapping[str, Any], roles: list[str]) -> list[dict[str, Any]]:
    assets = _asset_index(matrix)
    primaries = draft.get("primary_selection") or {}
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for role in roles:
        asset_id = primaries.get(role)
        asset = assets.get(str(asset_id))
        if asset and str(asset_id) not in seen:
            out.append({"asset": asset, "role": role, "selection_status": "primary"})
            seen.add(str(asset_id))
    for item in draft.get("alternate_candidates") or []:
        if not isinstance(item, Mapping):
            continue
        asset_id = str(item.get("asset_id") or "")
        asset = assets.get(asset_id)
        if asset and asset_id not in seen:
            out.append({
                "asset": asset,
                "role": str(item.get("for_role") or _asset_role(asset)),
                "selection_status": "alternate",
                "selection_note": item.get("reason"),
            })
            seen.add(asset_id)
    return out


def build_preview_plan(
    matrix: Mapping[str, Any],
    wall_verdict_draft: Mapping[str, Any],
    *,
    target_duration_sec: float = 75.0,
    min_duration_sec: float = 60.0,
    max_duration_sec: float = 90.0,
    clip_duration_sec: float = 6.0,
    roles: list[str] | None = None,
) -> dict[str, Any]:
    roles = roles or DEFAULT_ROLES
    candidates = _ordered_candidates(matrix, wall_verdict_draft, roles)
    clips: list[dict[str, Any]] = []
    total = 0.0
    index = 0
    if not candidates:
        return {
            "artifact_role": "material_first_preview_rough_cut_plan",
            "version": 1,
            "ok": False,
            "decision_scope": "preview_proposal_not_canonical_timeline",
            "review_required": "material_wall_or_workbench_review_before_render",
            "target_duration_sec": target_duration_sec,
            "total_duration_sec": 0.0,
            "clips": [],
            "gaps": [{"reason": "no primary or alternate candidates in wall verdict draft"}],
        }

    while total < min_duration_sec and total < max_duration_sec:
        candidate = candidates[index % len(candidates)]
        asset = candidate["asset"]
        asset_id = str(asset.get("asset_id"))
        available = _duration(asset) or clip_duration_sec
        duration = min(float(clip_duration_sec), available, max_duration_sec - total)
        if duration <= 0:
            break
        cycle = index // len(candidates)
        start = min(max(0.0, cycle * float(clip_duration_sec)), max(0.0, available - duration))
        clips.append({
            "segment": len(clips) + 1,
            "role": candidate["role"],
            "asset_id": asset_id,
            "source_path": asset.get("source_path"),
            "selection_status": candidate["selection_status"],
            "selection_note": candidate.get("selection_note"),
            "start_sec": round(start, 3),
            "duration_sec": round(duration, 3),
            "available_duration_sec": round(available, 3),
            "caption": (asset.get("visual_evidence") or {}).get("caption_hint"),
            "review_required": True,
            "reason": "preview proposal from material understanding matrix and wall verdict draft",
        })
        total += duration
        index += 1
        if total >= target_duration_sec and total >= min_duration_sec:
            break

    gaps = []
    if total < min_duration_sec:
        gaps.append({
            "reason": "candidate footage could not reach minimum preview duration",
            "minimum_duration_sec": float(min_duration_sec),
            "selected_duration_sec": round(total, 3),
        })
    plan = {
        "artifact_role": "material_first_preview_rough_cut_plan",
        "version": 1,
        "ok": not gaps,
        "decision_scope": "preview_proposal_not_canonical_timeline",
        "review_required": "material_wall_or_workbench_review_before_render",
        "source_artifacts": [
            wall_verdict_draft.get("source_artifact") or "material_understanding_matrix",
            "material_wall_review_verdict.draft.json",
        ],
        "target_duration_sec": float(target_duration_sec),
        "min_duration_sec": float(min_duration_sec),
        "max_duration_sec": float(max_duration_sec),
        "clip_count": len(clips),
        "total_duration_sec": round(total, 3),
        "clips": clips,
        "gaps": gaps,
        "next_action": "review_preview_rough_cut_before_render",
    }
    return plan


def build_preview_plan_file(
    matrix_path: str | Path,
    wall_verdict_draft_path: str | Path,
    *,
    out_path: str | Path,
    target_duration_sec: float = 75.0,
    min_duration_sec: float = 60.0,
    max_duration_sec: float = 90.0,
    clip_duration_sec: float = 6.0,
    roles: list[str] | None = None,
) -> dict[str, Any]:
    matrix = json.loads(Path(matrix_path).read_text(encoding="utf-8-sig"))
    draft = json.loads(Path(wall_verdict_draft_path).read_text(encoding="utf-8-sig"))
    plan = build_preview_plan(
        matrix,
        draft,
        target_duration_sec=target_duration_sec,
        min_duration_sec=min_duration_sec,
        max_duration_sec=max_duration_sec,
        clip_duration_sec=clip_duration_sec,
        roles=roles,
    )
    _write_json(Path(out_path), plan)
    return plan
