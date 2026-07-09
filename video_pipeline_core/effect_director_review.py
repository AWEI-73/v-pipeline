"""Director-level review for title/effect visual quality."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


PASSING_REVIEW_BASES = {"frame_sequence", "video_sample"}


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _block(rule: str, message: str, finding: Mapping[str, Any] | None = None) -> dict[str, Any]:
    item = {
        "rule": rule,
        "tier": 1,
        "message": message,
        "next_action": "repair_effect_director_findings",
    }
    if finding:
        item["finding"] = dict(finding)
    return item


def evaluate_effect_director_review(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    basis = _text(data.get("review_basis")).casefold()
    frames = _as_list(data.get("frame_sequence") or data.get("frames"))
    effects = _as_list(data.get("effects") or data.get("title_effects"))

    if basis not in PASSING_REVIEW_BASES:
        blocking.append(_block("effect_review_requires_visual_evidence", "effect director review requires frame_sequence or video_sample basis; metadata_only cannot pass"))
    if basis == "frame_sequence" and len(frames) < 3:
        blocking.append(_block("effect_review_missing_frame_sequence", "effect review requires before/active/after frame evidence"))
    if not effects:
        blocking.append(_block("effect_review_missing_effect_records", "effect review requires effect/title records"))

    for finding in _as_list(data.get("findings")):
        if not isinstance(finding, Mapping):
            continue
        severity = _text(finding.get("severity")).casefold()
        if severity in {"blocking", "blocker", "fail", "tier1"}:
            blocking.append(_block(
                _text(finding.get("rule")) or "effect_director_blocking_finding",
                _text(finding.get("message")) or "effect director review has a blocking finding",
                finding,
            ))

    return {
        "artifact_role": "effect_director_review",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "review_basis": basis,
        "checked_effect_count": len(effects),
        "checked_frame_count": len(frames),
        "checks": data.get("checks") if isinstance(data.get("checks"), Mapping) else {},
        "findings": _as_list(data.get("findings")),
        "next_action": None if not blocking else blocking[0]["next_action"],
    }


def write_effect_director_review_for_run(run: str | Path, out_name: str = "effect_director_review.json") -> dict[str, Any]:
    root = Path(run)
    packet = _load_json(root / "effect_director_review_packet.json")
    report = evaluate_effect_director_review(packet if isinstance(packet, Mapping) else None)
    report["run"] = str(root)
    (root / out_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
