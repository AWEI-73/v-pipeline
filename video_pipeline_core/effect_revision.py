"""Effect revision request artifacts for Node 14.

This module converts deterministic light-effect render gaps into a bounded
revision request. It does not render, patch final videos, or rewrite the
canonical effect intent plan.
"""
import json
import copy
import re
from pathlib import Path

from .effect_contract import validate_effect_intent_plan


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


def _validate_revision_request(payload):
    if not isinstance(payload, dict):
        raise ValueError("effect_revision_request must be object")
    if payload.get("artifact_role") != "effect_revision_request":
        raise ValueError("artifact_role must be effect_revision_request")
    if payload.get("version") != 1:
        raise ValueError("effect_revision_request version must be 1")
    requests = payload.get("requests")
    if not isinstance(requests, list):
        raise ValueError("effect_revision_request.requests must be list")
    seen = set()
    for idx, request in enumerate(requests):
        if not isinstance(request, dict):
            raise ValueError(f"effect_revision_request.requests[{idx}] must be object")
        request_id = request.get("request_id")
        if not isinstance(request_id, str) or not request_id.strip():
            raise ValueError(f"effect_revision_request.requests[{idx}].request_id must be non-empty string")
        if request_id in seen:
            raise ValueError(f"duplicate effect revision request_id: {request_id}")
        seen.add(request_id)
        route = request.get("route")
        if route not in {RECIPE_ROUTE, ADAPTER_ROUTE}:
            raise ValueError(f"unsupported effect revision route: {route}")
        effect_id = request.get("effect_id")
        if not isinstance(effect_id, str) or not effect_id.strip():
            raise ValueError(f"effect_revision_request.requests[{idx}].effect_id must be non-empty string")
    return requests


def _patch_type(route):
    if route == ADAPTER_ROUTE:
        return "build_node14_adapter"
    return "wire_effect_recipe"


def _proposed_backend(route):
    if route == ADAPTER_ROUTE:
        return "remotion_render"
    return "ffmpeg_light_effects"


def build_effect_recipe_patch(effect_revision_request, *, source=None):
    """Build a non-canonical effect recipe patch draft for Node14 review."""
    requests = _validate_revision_request(effect_revision_request)
    patches = []
    for request in requests:
        route = request["route"]
        patches.append({
            "patch_id": f"patch_{request['request_id']}",
            "request_id": request["request_id"],
            "effect_id": request["effect_id"],
            "source_effect_id": request.get("source_effect_id"),
            "segment": request.get("segment"),
            "operation": request.get("operation"),
            "patch_type": _patch_type(route),
            "route": route,
            "proposed_backend": _proposed_backend(route),
            "status": "pending",
            "reason": request.get("reason") or "effect render gap requires Node14 handling",
            "evidence": {
                "effect_revision_request": dict(request),
            },
        })
    return {
        "artifact_role": "effect_recipe_patch",
        "version": 1,
        "status": "pending" if patches else "empty",
        "draft_only": True,
        "source": dict(source or {}),
        "summary": {
            "request_count": len(requests),
            "patch_count": len(patches),
            "adapter_patch_count": sum(1 for item in patches if item["patch_type"] == "build_node14_adapter"),
            "recipe_patch_count": sum(1 for item in patches if item["patch_type"] == "wire_effect_recipe"),
        },
        "patches": patches,
        "next_action": "review_effect_recipe_patch" if patches else None,
    }


def build_revised_effect_intent_draft(effect_revision_request, effect_intent_plan, *, source=None):
    """Build a draft-only wrapper around a revised effect intent plan.

    The inner `effect_intent_plan` remains validator-compatible, but the wrapper
    makes the artifact non-canonical. Callers must explicitly review/apply it.
    """
    requests = _validate_revision_request(effect_revision_request)
    validate_effect_intent_plan(effect_intent_plan)
    draft_plan = copy.deepcopy(effect_intent_plan)
    effects_by_id = {
        effect["effect_id"]: effect
        for effect in draft_plan.get("effects", [])
    }
    applied = []
    for request in requests:
        source_effect_id = request.get("source_effect_id")
        if not source_effect_id:
            continue
        effect = effects_by_id.get(source_effect_id)
        if effect is None:
            raise ValueError(f"revision request source_effect_id not found in effect_intent_plan: {source_effect_id}")
        backend = _proposed_backend(request["route"])
        allowed = list(effect.get("allowed_backends") or [])
        if backend not in allowed:
            allowed.append(backend)
            effect["allowed_backends"] = allowed
        lineage = effect.setdefault("node14_revision_lineage", [])
        lineage.append({
            "request_id": request["request_id"],
            "route": request["route"],
            "proposed_backend": backend,
            "reason": request.get("reason"),
        })
        applied.append({
            "request_id": request["request_id"],
            "source_effect_id": source_effect_id,
            "proposed_backend": backend,
        })
    validate_effect_intent_plan(draft_plan)
    return {
        "artifact_role": "revised_effect_intent_plan_draft",
        "version": 1,
        "draft_only": True,
        "source": dict(source or {}),
        "summary": {
            "request_count": len(requests),
            "applied_effect_count": len(applied),
        },
        "effect_intent_plan": draft_plan,
        "applied": applied,
        "next_action": "review_revised_effect_intent_plan" if applied else None,
    }


def _non_empty_string(value, field):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{field} must be a non-empty string")
    return value.strip()


def apply_revised_effect_intent_draft(revised_effect_intent_plan_draft, *,
                                      accept=False, reviewer=None, reason=None):
    """Return a reviewed canonical effect_intent_plan from a Node14 draft.

    The caller must make the review action explicit. This function does not
    mutate or overwrite the original effect_intent_plan; it only converts a
    draft wrapper into a validator-clean plan object for a later contract-run.
    """
    if not accept:
        raise ValueError("accept=True is required to apply revised effect intent draft")
    reviewer = _non_empty_string(reviewer, "reviewer")
    reason = _non_empty_string(reason, "reason")
    draft = revised_effect_intent_plan_draft
    if not isinstance(draft, dict):
        raise ValueError("revised_effect_intent_plan_draft must be object")
    if draft.get("artifact_role") != "revised_effect_intent_plan_draft":
        raise ValueError("artifact_role must be revised_effect_intent_plan_draft")
    if draft.get("version") != 1:
        raise ValueError("revised_effect_intent_plan_draft version must be 1")
    if draft.get("draft_only") is not True:
        raise ValueError("revised_effect_intent_plan_draft must declare draft_only=true")
    plan = copy.deepcopy(draft.get("effect_intent_plan"))
    validate_effect_intent_plan(plan)
    plan.pop("draft_only", None)
    plan["node14_apply_lineage"] = {
        "reviewer": reviewer,
        "reason": reason,
        "draft_artifact_role": draft.get("artifact_role"),
        "source": copy.deepcopy(draft.get("source") or {}),
        "applied": copy.deepcopy(draft.get("applied") or []),
    }
    validate_effect_intent_plan(plan)
    return plan


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


def write_effect_revision_draft(request_path, out_patch_path, *,
                                effect_intent_plan_path=None,
                                out_intent_draft_path=None):
    request_path = Path(request_path)
    out_patch_path = Path(out_patch_path)
    with request_path.open(encoding="utf-8-sig") as f:
        request = json.load(f)
    source = {"effect_revision_request": str(request_path)}
    patch = build_effect_recipe_patch(request, source=source)
    out_patch_path.parent.mkdir(parents=True, exist_ok=True)
    with out_patch_path.open("w", encoding="utf-8") as f:
        json.dump(patch, f, ensure_ascii=False, indent=2)

    intent_draft = None
    if effect_intent_plan_path or out_intent_draft_path:
        if not effect_intent_plan_path or not out_intent_draft_path:
            raise ValueError("effect_intent_plan_path and out_intent_draft_path must be provided together")
        effect_intent_plan_path = Path(effect_intent_plan_path)
        out_intent_draft_path = Path(out_intent_draft_path)
        with effect_intent_plan_path.open(encoding="utf-8-sig") as f:
            effect_intent_plan = json.load(f)
        intent_draft = build_revised_effect_intent_draft(
            request,
            effect_intent_plan,
            source={**source, "effect_intent_plan": str(effect_intent_plan_path)},
        )
        out_intent_draft_path.parent.mkdir(parents=True, exist_ok=True)
        with out_intent_draft_path.open("w", encoding="utf-8") as f:
            json.dump(intent_draft, f, ensure_ascii=False, indent=2)
    return {
        "effect_recipe_patch": str(out_patch_path),
        "patch": patch,
        "revised_effect_intent_plan_draft": str(out_intent_draft_path) if intent_draft else None,
        "intent_draft": intent_draft,
    }


def write_revised_effect_intent_plan(draft_path, out_path, *,
                                     accept=False, reviewer=None, reason=None):
    draft_path = Path(draft_path)
    out_path = Path(out_path)
    if draft_path.resolve() == out_path.resolve():
        raise ValueError("reviewed effect_intent_plan output must not overwrite the draft")
    with draft_path.open(encoding="utf-8-sig") as f:
        draft = json.load(f)
    plan = apply_revised_effect_intent_draft(
        draft,
        accept=accept,
        reviewer=reviewer,
        reason=reason,
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    return plan
