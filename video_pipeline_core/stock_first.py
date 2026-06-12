"""stock_first.py — stock-first MVP routing artifact.

This is the Node 2 -> Node 8 bridge for conceptual stock-based runs. It decides
which canonical segments may use stock footage and leaves protected segments
unmodified for collection/reshoot/review.
"""
import copy
import json
from pathlib import Path

from . import spec_contract


def _stock_first_enabled(contract):
    cfg = contract.get("run_config") or {}
    return (
        contract.get("material_source_mode") == "stock_first"
        or cfg.get("material_source_mode") == "stock_first"
    )


def _story_truth_level(contract):
    cfg = contract.get("run_config") or {}
    return contract.get("story_truth_level") or cfg.get("story_truth_level") or "documentary"


def _segment_query(seg):
    mat = seg.get("material_fit") or {}
    return mat.get("search_query") or mat.get("visual_desc") or mat.get("material_hint") or ""


def _can_use_stock(contract, seg):
    if seg.get("source") in ("local", "generated"):
        return False
    mat = seg.get("material_fit") or {}
    core = seg.get("core") or {}
    if mat.get("must_include") or core.get("identity_sensitive") or core.get("proof_critical"):
        return False
    if mat.get("fallback_policy") == "stock_bridge":
        return True
    return _stock_first_enabled(contract) and _story_truth_level(contract) == "conceptual"


def build_stock_first_route(contract):
    segments = []
    for seg in contract.get("segments", []):
        mat = seg.get("material_fit") or {}
        core = seg.get("core") or {}
        can_stock = _can_use_stock(contract, seg)
        route = spec_contract.suggest_fallback_route(
            "missing",
            identity_sensitive=bool(core.get("identity_sensitive")),
            proof_critical=bool(core.get("proof_critical")),
            must_include=bool(mat.get("must_include")),
            section_role=core.get("section_role"),
            can_reshoot=True,
            material_collected=True,
            explicitly_allowed=["stock_bridge"] if can_stock else [],
        )
        selected = "stock_bridge" if can_stock else route["selected_route"]
        source = "stock" if selected == "stock_bridge" else None
        segments.append({
            "segment": seg.get("segment"),
            "section_role": core.get("section_role"),
            "visual_desc": mat.get("visual_desc"),
            "search_query": _segment_query(seg),
            "selected_route": selected,
            "source": source,
            "allowed_routes": route["allowed_routes"],
            "rejected_routes": route["rejected_routes"],
            "review_required": bool(route["review_required"]),
            "reason": route["reason"],
            "node_trace": ["Node 2", "Node 8", "Node 9"],
        })
    return {
        "artifact_role": "stock_first_route",
        "stock_first_route_version": 1,
        "material_source_mode": "stock_first" if _stock_first_enabled(contract) else "unchanged",
        "story_truth_level": _story_truth_level(contract),
        "segments": segments,
    }


def apply_stock_first_route(contract):
    if not _stock_first_enabled(contract):
        return copy.deepcopy(contract)
    routed = copy.deepcopy(contract)
    route = build_stock_first_route(routed)
    by_seg = {x["segment"]: x for x in route["segments"]}
    for seg in routed.get("segments", []):
        if seg.get("source") in ("local", "generated"):
            continue
        decision = by_seg.get(seg.get("segment")) or {}
        if decision.get("source") != "stock":
            continue
        seg["source"] = "stock"
        mat = seg.setdefault("material_fit", {})
        if not mat.get("search_query"):
            mat["search_query"] = decision.get("search_query") or mat.get("visual_desc") or ""
    routed["stock_first_route"] = route
    return routed


def write_stock_first_route(contract, out_path):
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    route = build_stock_first_route(contract)
    with path.open("w", encoding="utf-8") as f:
        json.dump(route, f, ensure_ascii=False, indent=2)
    return str(path)
