"""Build material gap task packets from material_delta artifacts."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARTIFACT_ROLE = "material_gap_brief"
VERSION = 1


def _need_index(material_needs: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for need in (material_needs or {}).get("needs") or []:
        if not isinstance(need, dict):
            continue
        need_id = need.get("need_id")
        if isinstance(need_id, str) and need_id.strip():
            out[need_id] = need
    return out


def _route_for(delta: dict[str, Any], need: dict[str, Any]) -> str:
    outcome = delta.get("outcome")
    route = delta.get("route")
    evidence = delta.get("evidence") if isinstance(delta.get("evidence"), dict) else {}
    fallback_options = evidence.get("fallback_options") or need.get("fallback_options") or []
    fallback_text = " ".join(str(item).lower() for item in fallback_options)
    must_have = bool(evidence.get("must_have", need.get("must_have")))
    proof_sensitive = bool(need.get("proof_sensitive") or need.get("identity_sensitive"))

    if route == "reshoot" or (must_have and proof_sensitive):
        return "reshoot"
    if "generated" in fallback_text or "image" in fallback_text:
        return "generated_material"
    if "stock" in fallback_text or "bridge" in fallback_text:
        return "stock_retrieval"
    if outcome == "thin":
        return "collect_existing"
    if route == "script_rewrite":
        return "script_rewrite"
    if route == "drop_segment":
        return "waiver"
    return "collect_existing"


def _priority(delta: dict[str, Any], need: dict[str, Any]) -> str:
    if delta.get("blocks_ready_for_build"):
        return "must_have"
    if bool((delta.get("evidence") or {}).get("must_have", need.get("must_have"))):
        return "important"
    return "optional"


def _segment_refs(need: dict[str, Any]) -> list[str]:
    refs = []
    for key in ("segment_refs", "segments", "used_by_segments"):
        for value in need.get(key) or []:
            if isinstance(value, str) and value.strip() and value.strip() not in refs:
                refs.append(value.strip())
            elif isinstance(value, (int, float)):
                text = str(int(value))
                if text not in refs:
                    refs.append(text)
    return refs


def _task(delta: dict[str, Any], need: dict[str, Any], index: int) -> dict[str, Any]:
    need_id = delta.get("need_id")
    recommended_route = _route_for(delta, need)
    visual_intent = (
        need.get("visual_intent")
        or need.get("purpose")
        or need.get("description")
        or delta.get("reason")
        or need_id
    )
    criteria = [
        "matches the need_id and visual intent",
        "has enough usable duration or image quality for the target segment",
        "can be mapped back through material-map review evidence",
    ]
    if recommended_route == "reshoot":
        criteria.insert(1, "is stable, horizontal 16:9 when possible, and avoids fast pans")
    return {
        "task_id": f"gap-task-{index:03d}",
        "need_id": need_id,
        "delta_status": delta.get("outcome"),
        "recommended_route": recommended_route,
        "priority": _priority(delta, need),
        "segment_refs": _segment_refs(need),
        "visual_intent": visual_intent,
        "acceptance_criteria": criteria,
        "constraints": {
            "proof_sensitive": bool(need.get("proof_sensitive")),
            "identity_sensitive": bool(need.get("identity_sensitive")),
            "generation_allowed": recommended_route == "generated_material",
        },
        "notes": delta.get("reason"),
    }


def build_material_gap_brief(
    material_delta: dict[str, Any],
    *,
    material_needs: dict[str, Any] | None = None,
    lifecycle: dict[str, Any] | None = None,
    route: str | None = None,
) -> dict[str, Any]:
    needs = _need_index(material_needs)
    tasks = []
    for delta in material_delta.get("deltas") or []:
        if not isinstance(delta, dict):
            continue
        if delta.get("outcome") not in {"missing", "thin"}:
            continue
        need_id = delta.get("need_id")
        if not isinstance(need_id, str) or not need_id.strip():
            continue
        tasks.append(_task(delta, needs.get(need_id, {}), len(tasks) + 1))

    generated_jobs = [task for task in tasks if task["recommended_route"] == "generated_material"]
    stock_jobs = [task for task in tasks if task["recommended_route"] == "stock_retrieval"]
    shooting_tasks = [
        task for task in tasks
        if task["recommended_route"] in {"collect_existing", "reshoot"}
    ]
    rewrite_or_waiver = [
        task for task in tasks
        if task["recommended_route"] in {"script_rewrite", "waiver", "text_bridge"}
    ]

    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": VERSION,
        "source_refs": {
            "material_needs": "material_needs.json" if material_needs is not None else None,
            "material_delta": "material_delta.json",
            "material_map_lifecycle": "material_map_lifecycle.json" if lifecycle is not None else None,
        },
        "route": route or _infer_route(lifecycle),
        "ok": bool(material_delta.get("ok", True)),
        "task_count": len(tasks),
        "tasks": tasks,
        "summary": {
            "shooting_or_collect": len(shooting_tasks),
            "generated_material": len(generated_jobs),
            "stock_retrieval": len(stock_jobs),
            "rewrite_or_waiver": len(rewrite_or_waiver),
        },
        "handoff": {
            "shooting_brief": "shooting_brief.md",
            "generated_material_jobs": "generated_material_jobs.json",
            "stock_retrieval_jobs": "stock_retrieval_jobs.json",
        },
        "does_not_release_build": True,
    }


def _infer_route(lifecycle: dict[str, Any] | None) -> str | None:
    if not isinstance(lifecycle, dict):
        return None
    for key in ("route", "entry_path", "input_route"):
        value = lifecycle.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return None


def build_shooting_brief_markdown(gap_brief: dict[str, Any]) -> str:
    lines = [
        "# Shooting Brief",
        "",
        "Source: material_delta.json",
        "",
        "This brief is a follow-up task list. It does not satisfy material coverage.",
        "",
    ]
    shooting_tasks = [
        task for task in gap_brief.get("tasks") or []
        if task.get("recommended_route") in {"collect_existing", "reshoot"}
    ]
    if not shooting_tasks:
        lines.extend(["No collect/reshoot tasks. See generated/stock/rewrite jobs.", ""])
        return "\n".join(lines)

    for task in shooting_tasks:
        lines.extend([
            f"## {task.get('need_id')}",
            "",
            f"- Priority: {task.get('priority')}",
            f"- Route: {task.get('recommended_route')}",
            f"- Purpose: {task.get('visual_intent')}",
            f"- Segment refs: {', '.join(task.get('segment_refs') or []) or 'not specified'}",
            "- Acceptance:",
        ])
        for item in task.get("acceptance_criteria") or []:
            lines.append(f"  - {item}")
        lines.extend([
            f"- Notes: {task.get('notes') or ''}",
            "",
        ])
    return "\n".join(lines)


def jobs_for_route(gap_brief: dict[str, Any], route: str) -> dict[str, Any]:
    tasks = [
        task for task in gap_brief.get("tasks") or []
        if task.get("recommended_route") == route
    ]
    return {
        "artifact_role": f"{route}_jobs",
        "version": 1,
        "source_ref": "material_gap_brief.json",
        "job_count": len(tasks),
        "jobs": tasks,
    }


def load_json(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def write_json(path: str | Path, payload: dict[str, Any]) -> None:
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
