"""Montage design/review contract for opener and MV sections."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _block(rule: str, montage: Mapping[str, Any], message: str) -> dict[str, Any]:
    return {
        "rule": rule,
        "tier": 1,
        "section_id": _text(montage.get("section_id") or montage.get("beat_id")),
        "story_role": _text(montage.get("story_role")),
        "message": message,
        "next_action": "repair_montage_design",
    }


def _montages(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    raw = payload.get("montages") or payload.get("sections") or payload.get("items")
    return [item for item in _as_list(raw) if isinstance(item, dict)]


def evaluate_montage_design_review(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    montages = _montages(payload)
    if not montages:
        blocking.append({
            "rule": "montage_design_plan_missing",
            "tier": 1,
            "message": "montage design review requires montage sections",
            "next_action": "write_montage_design_plan",
        })

    for montage in montages:
        role = _text(montage.get("story_role")).casefold()
        shots = [item for item in _as_list(montage.get("shot_functions")) if isinstance(item, Mapping)]
        shot_count = int(montage.get("shot_count") or len(shots) or 0)
        functions = {_text(shot.get("function")).casefold() for shot in shots}
        longest = max((_float(shot.get("duration_sec")) or 0.0 for shot in shots), default=0.0)
        if role == "opener":
            if shot_count <= 1 and (not functions or functions <= {"title_card"}):
                blocking.append(_block("opener_plain_title_card", montage, "opener cannot be only a plain title card"))
            if shot_count <= 1 and ("static_photo" in functions or longest >= 6.0):
                blocking.append(_block("opener_single_long_static_shot", montage, "opener cannot be a single long static shot"))
            if not _text(montage.get("story_hook")) or not _text(montage.get("payoff")):
                blocking.append(_block("opener_missing_story_hook_or_payoff", montage, "opener montage requires story hook and payoff"))
        if not _text(montage.get("target_mood")):
            blocking.append(_block("montage_missing_target_mood", montage, "montage plan requires target mood"))
        if not shots:
            blocking.append(_block("montage_missing_shot_functions", montage, "montage plan requires shot functions"))
        if not _as_list(montage.get("beat_timing")):
            blocking.append(_block("montage_missing_beat_timing", montage, "montage plan requires beat/energy timing"))
        if not _as_list(montage.get("title_sync_points")):
            blocking.append(_block("montage_missing_title_sync", montage, "montage plan requires title sync points"))
        if not _as_list(montage.get("transitions")):
            blocking.append(_block("montage_missing_transition_rationale", montage, "montage plan requires transitions and rationale"))

    return {
        "artifact_role": "montage_design_review",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "checked_montage_count": len(montages),
        "next_action": None if not blocking else blocking[0]["next_action"],
    }


def write_montage_design_review_for_run(run: str | Path, out_name: str = "montage_design_review.json") -> dict[str, Any]:
    root = Path(run)
    plan = _load_json(root / "montage_design_plan.json")
    report = evaluate_montage_design_review(plan if isinstance(plan, Mapping) else None)
    report["run"] = str(root)
    (root / out_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
