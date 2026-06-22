from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from . import reviewer_registry


DECISION_WEIGHT = {"block": 40, "blocked": 40, "revise": 30, "advisory": 10, "pass": 0}
GATE_WEIGHT = {"delivery_gate": 400, "hard_gate": 300, "revise": 200, "advisory": 100}
SEVERITY_WEIGHT = {"critical": 40, "major": 30, "minor": 20, "info": 10}


def read_review(path: str | Path) -> dict[str, Any]:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _weight(review: Mapping[str, Any], finding: Mapping[str, Any] | None = None) -> int:
    gate = str(review.get("gate_strength") or "").strip()
    decision = str(review.get("decision") or "").strip()
    severity = str((finding or {}).get("severity") or "").strip()
    return (
        GATE_WEIGHT.get(gate, 0)
        + DECISION_WEIGHT.get(decision, 0)
        + SEVERITY_WEIGHT.get(severity, 0)
    )


def _overall_decision(reviews: Iterable[Mapping[str, Any]]) -> str:
    decisions = {str(review.get("decision") or "").strip() for review in reviews}
    if "block" in decisions or "blocked" in decisions:
        return "block"
    if "revise" in decisions:
        return "revise"
    if "advisory" in decisions:
        return "advisory"
    return "pass"


def _status_for_review(review: Mapping[str, Any]) -> str:
    status = str(review.get("status") or "").strip()
    if status:
        return status
    decision = str(review.get("decision") or "").strip()
    if decision in {"block", "blocked"}:
        return "blocked"
    if decision == "revise":
        return "revise"
    return "pass"


def _overall_status(reviews: Iterable[Mapping[str, Any]], errors: list[str]) -> str:
    if errors:
        return "blocked"
    statuses = {_status_for_review(review) for review in reviews}
    if "blocked" in statuses:
        return "blocked"
    if "revise" in statuses:
        return "revise"
    return "pass"


def _collect_list(review: Mapping[str, Any], key: str) -> list[Any]:
    value = review.get(key)
    return value if isinstance(value, list) else []


def _route_task_packet(review: Mapping[str, Any], queue_item: Mapping[str, Any] | None) -> dict[str, Any] | None:
    status = _status_for_review(review)
    if status == "pass":
        return None
    handoff_to = review.get("handoff_to") or review.get("next_action") or ((queue_item or {}).get("next_action"))
    return {
        "artifact_role": "route_task_packet",
        "version": 1,
        "source": "reviewer_aggregation",
        "status": status,
        "blocking_level": review.get("blocking_level") or ("hard_block" if status == "blocked" else "soft_block"),
        "reviewer_role": review.get("reviewer_role"),
        "handoff_to": handoff_to,
        "next_action": (queue_item or {}).get("next_action") or review.get("next_action") or handoff_to,
        "required_revisions": _collect_list(review, "required_revisions"),
        "recommended_actions": _collect_list(review, "recommended_actions"),
        "source_finding": dict(queue_item or {}),
    }


def aggregate_reviews(reviews: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    review_list = [dict(review) for review in reviews]
    errors: list[str] = []
    priority_queue: list[dict[str, Any]] = []

    for index, review in enumerate(review_list):
        validation = reviewer_registry.validate_review_artifact(review)
        if not validation.get("ok"):
            errors.extend(f"review[{index}]: {err}" for err in validation.get("errors") or [])
            continue
        findings = review.get("findings") or []
        for finding_index, finding in enumerate(findings):
            if not isinstance(finding, Mapping):
                continue
            next_action = finding.get("failure_route") or review.get("next_action")
            priority_queue.append(
                {
                    "rank_score": _weight(review, finding),
                    "reviewer_role": review.get("reviewer_role"),
                    "decision": review.get("decision"),
                    "gate_strength": review.get("gate_strength"),
                    "severity": finding.get("severity"),
                    "finding_code": finding.get("code"),
                    "message": finding.get("message"),
                    "next_action": next_action,
                    "source_review_index": index,
                    "source_finding_index": finding_index,
                }
            )

    priority_queue.sort(
        key=lambda item: (
            -int(item.get("rank_score") or 0),
            str(item.get("reviewer_role") or ""),
            int(item.get("source_finding_index") or 0),
        )
    )
    overall = "invalid" if errors else _overall_decision(review_list)
    overall_status = _overall_status(review_list, errors)
    top_review = None
    if priority_queue:
        top_index = priority_queue[0].get("source_review_index")
        if isinstance(top_index, int) and 0 <= top_index < len(review_list):
            top_review = review_list[top_index]
    elif review_list:
        top_review = next((review for review in review_list if _status_for_review(review) != "pass"), None)
    return {
        "artifact_role": "reviewer_aggregation",
        "version": 1,
        "overall_decision": overall,
        "overall_status": overall_status,
        "can_continue_to_delivery": overall_status == "pass",
        "review_count": len(review_list),
        "finding_count": len(priority_queue),
        "priority_queue": priority_queue,
        "route_task_packet": _route_task_packet(top_review, priority_queue[0] if priority_queue else None)
        if top_review else None,
        "next_action": priority_queue[0]["next_action"] if priority_queue else None,
        "errors": errors,
    }


def aggregate_review_files(paths: Iterable[str | Path]) -> dict[str, Any]:
    return aggregate_reviews(read_review(path) for path in paths)
