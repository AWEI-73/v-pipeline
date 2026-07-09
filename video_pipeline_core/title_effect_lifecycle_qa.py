"""Title/effect lifecycle QA for render-facing overlays."""

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


def _float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _effects(payload: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(payload, Mapping):
        return []
    raw = payload.get("effects") or payload.get("title_effects") or payload.get("items")
    return [item for item in _as_list(raw) if isinstance(item, dict)]


def _has_timing_evidence(effect: Mapping[str, Any]) -> bool:
    if _text(effect.get("evidence_frame") or effect.get("timing_evidence") or effect.get("evidence_ref")):
        return True
    evidence = effect.get("evidence")
    if isinstance(evidence, Mapping):
        return any(_text(evidence.get(key)) for key in ("frame", "start_frame", "end_frame", "timing_ref"))
    return bool(_as_list(effect.get("evidence_frames")))


def _block(rule: str, effect: Mapping[str, Any], message: str) -> dict[str, Any]:
    return {
        "rule": rule,
        "tier": 1,
        "effect_id": _text(effect.get("effect_id") or effect.get("id")),
        "section_id": _text(effect.get("section_id") or effect.get("beat_id")),
        "message": message,
        "next_action": "repair_title_effect_lifecycle",
    }


def evaluate_title_effect_lifecycle_qa(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    effects = _effects(payload)

    if not effects:
        blocking.append({
            "rule": "title_effect_lifecycle_artifact_missing",
            "tier": 1,
            "message": "title/effect lifecycle QA requires at least one effect record",
            "next_action": "write_title_effect_lifecycle_plan",
        })
        return _report(blocking, warnings, 0)

    for effect in effects:
        start = _float(effect.get("start_sec"))
        end = _float(effect.get("end_sec"))
        max_duration = _float(effect.get("max_duration_sec"))
        next_start = _float(effect.get("next_section_start_sec"))
        if start is None:
            blocking.append(_block("title_effect_missing_start_time", effect, "title/effect lacks appear/start time"))
        if end is None:
            blocking.append(_block("title_effect_missing_end_time", effect, "title/effect lacks disappear/end time"))
        if start is not None and end is not None and end <= start:
            blocking.append(_block("title_effect_invalid_time_range", effect, "title/effect end time must be after start time"))
        if start is not None and end is not None and max_duration is not None and (end - start) > max_duration:
            blocking.append(_block("title_effect_exceeds_max_duration", effect, "title/effect duration exceeds max duration"))
        if bool(effect.get("must_clear_before_next_section")) and end is not None and next_start is not None and end > next_start:
            blocking.append(_block("title_effect_overlaps_next_section", effect, "title/effect persists into the next section"))
        if not _has_timing_evidence(effect):
            blocking.append(_block("title_effect_missing_timing_evidence", effect, "title/effect lacks evidence frame or timing proof"))

    return _report(blocking, warnings, len(effects))


def _report(blocking: list[dict[str, Any]], warnings: list[dict[str, Any]], checked_effect_count: int) -> dict[str, Any]:
    return {
        "artifact_role": "title_effect_lifecycle_qa",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "checked_effect_count": checked_effect_count,
        "next_action": None if not blocking else blocking[0]["next_action"],
    }


def write_title_effect_lifecycle_qa_for_run(run: str | Path, out_name: str = "title_effect_lifecycle_qa.json") -> dict[str, Any]:
    root = Path(run)
    plan = _load_json(root / "title_effect_lifecycle_plan.json")
    report = evaluate_title_effect_lifecycle_qa(plan if isinstance(plan, Mapping) else None)
    report["run"] = str(root)
    (root / out_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
