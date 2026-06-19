"""Effect revision request artifacts for Node 14.

This module converts deterministic light-effect render gaps into a bounded
revision request. It does not render, patch final videos, or rewrite the
canonical effect intent plan.
"""
import json
import re
from pathlib import Path


ADAPTER_ROUTE = "route_to_node14_or_remotion_adapter"
RECIPE_ROUTE = "implement_or_wire_effect_recipe"


def _validate_baseline_review(review):
    if not isinstance(review, dict):
        raise ValueError("light_effects_baseline_review must be object")
    if review.get("artifact_role") != "light_effects_baseline_review":
        raise ValueError("artifact_role must be light_effects_baseline_review")
    if review.get("light_effects_baseline_review_version") != 1:
        raise ValueError("light_effects_baseline_review_version must be 1")
    gaps = review.get("gaps")
    if not isinstance(gaps, list):
        raise ValueError("light_effects_baseline_review.gaps must be list")
    for idx, gap in enumerate(gaps):
        if not isinstance(gap, dict):
            raise ValueError(f"light_effects_baseline_review.gaps[{idx}] must be object")
        effect_id = gap.get("effect_id")
        if not isinstance(effect_id, str) or not effect_id.strip():
            raise ValueError(f"light_effects_baseline_review.gaps[{idx}].effect_id must be non-empty string")
    return gaps


def _validate_plan(plan):
    if plan is None:
        return {}
    if not isinstance(plan, dict):
        raise ValueError("light_effects_plan must be object")
    if plan.get("artifact_role") != "light_effects_plan":
        raise ValueError("artifact_role must be light_effects_plan")
    if plan.get("light_effects_plan_version") != 1:
        raise ValueError("light_effects_plan_version must be 1")
    items = plan.get("items")
    if not isinstance(items, list):
        raise ValueError("light_effects_plan.items must be list")
    by_id = {}
    for idx, item in enumerate(items):
        if not isinstance(item, dict):
            raise ValueError(f"light_effects_plan.items[{idx}] must be object")
        item_id = item.get("id")
        if not isinstance(item_id, str) or not item_id.strip():
            raise ValueError(f"light_effects_plan.items[{idx}].id must be non-empty string")
        if item_id in by_id:
            raise ValueError(f"duplicate light effect item id: {item_id}")
        by_id[item_id] = item
    return by_id


def _route_for(gap, planned):
    operation = (planned or gap).get("operation")
    next_action = (planned or {}).get("next_action") or gap.get("next_action")
    if operation == "external_effect" or next_action == ADAPTER_ROUTE:
        return ADAPTER_ROUTE
    return RECIPE_ROUTE


def _request_id(effect_id):
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "_", str(effect_id)).strip("_.-")
    return f"fxrev_{slug or 'effect'}"


def build_effect_revision_request(baseline_review, light_effects_plan=None, *, source=None):
    """Build a Node14 revision request from light-effect render gaps."""
    gaps = _validate_baseline_review(baseline_review)
    planned_by_id = _validate_plan(light_effects_plan)
    requests = []
    for gap in gaps:
        effect_id = gap["effect_id"].strip()
        planned = planned_by_id.get(effect_id)
        route = _route_for(gap, planned)
        requests.append({
            "request_id": _request_id(effect_id),
            "effect_id": effect_id,
            "source_effect_id": (planned or {}).get("source_effect_id"),
            "segment": (planned or gap).get("segment"),
            "operation": (planned or gap).get("operation"),
            "route": route,
            "reason": gap.get("reason") or "light effect did not reach render output",
            "required_for_story": bool((planned or {}).get("required_for_story")),
            "next_action": route,
            "status": "pending",
            "evidence": {
                "baseline_gap": dict(gap),
                "planned_effect": dict(planned) if planned else None,
            },
        })
    status = "pending" if requests else "empty"
    return {
        "artifact_role": "effect_revision_request",
        "version": 1,
        "status": status,
        "source": dict(source or {}),
        "summary": {
            "gap_count": len(gaps),
            "request_count": len(requests),
            "adapter_route_count": sum(1 for item in requests if item["route"] == ADAPTER_ROUTE),
            "recipe_route_count": sum(1 for item in requests if item["route"] == RECIPE_ROUTE),
        },
        "requests": requests,
        "next_action": "node14_effect_revision" if requests else None,
    }


def write_effect_revision_request(baseline_review_path, out_path, *, light_effects_plan_path=None):
    baseline_review_path = Path(baseline_review_path)
    out_path = Path(out_path)
    with baseline_review_path.open(encoding="utf-8-sig") as f:
        baseline_review = json.load(f)
    light_effects_plan = None
    if light_effects_plan_path:
        light_effects_plan_path = Path(light_effects_plan_path)
        with light_effects_plan_path.open(encoding="utf-8-sig") as f:
            light_effects_plan = json.load(f)
    source = {
        "light_effects_baseline_review": str(baseline_review_path),
        "light_effects_plan": str(light_effects_plan_path) if light_effects_plan_path else None,
    }
    result = build_effect_revision_request(
        baseline_review,
        light_effects_plan,
        source=source,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return result
