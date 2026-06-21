from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any, Iterable


VALID_RESULT_STATUSES = {"done", "blocked", "needs_context", "failed"}


STAGES = [
    {
        "stage": "Video Intent Planner",
        "role": "intent_planner",
        "objective": "Clarify user intent, route, material availability, and initial constraints.",
        "allowed_outputs": ["project_brief.json", "route_decision.json"],
        "must_not_touch": [
            "final.mp4",
            "timeline_build.json",
            "project_material_map.json",
            "material_delta.json",
        ],
        "success_criteria": [
            "Output must state existing-material-first, story-first, or hybrid route.",
            "Output must not claim BUILD readiness.",
        ],
    },
    {
        "stage": "Story / Structure Planner",
        "role": "story_planner",
        "objective": "Create the story soul, beat structure, and director-level shot plan.",
        "allowed_outputs": [
            "story_soul_blueprint.json",
            "screenplay_beats.json",
            "director_shot_plan.json",
        ],
        "must_not_touch": ["final.mp4", "timeline_build.json", "project_material_map.json"],
        "success_criteria": ["Beats must preserve story intent and identify material needs."],
    },
    {
        "stage": "Spec / Contract Compile",
        "role": "contract_compiler",
        "objective": "Compile needs, segment contract, and neutral effect intent.",
        "allowed_outputs": ["material_needs.json", "segment_contract.json", "effect_intent_plan.json"],
        "must_not_touch": ["final.mp4", "timeline_build.json"],
        "success_criteria": ["Contract artifacts must remain schema-valid and fail-closed."],
    },
    {
        "stage": "Material Truth",
        "role": "material_curator",
        "objective": "Build or review material map truth from existing or generated materials.",
        "allowed_outputs": ["project_material_map.json", "material_review_report.md"],
        "must_not_touch": ["final.mp4", "timeline_build.json"],
        "success_criteria": ["Do not invent satisfies edges; evidence must point to real files."],
    },
    {
        "stage": "Coverage / Decision Gate",
        "role": "coverage_reviewer",
        "objective": "Compute coverage and capture human or route decisions before BUILD.",
        "allowed_outputs": [
            "material_delta.json",
            "revision_decisions.json",
            "revised_segment_contract.json",
        ],
        "must_not_touch": ["final.mp4", "timeline_build.json"],
        "success_criteria": ["Must-have missing material must not silently pass."],
    },
    {
        "stage": "BUILD Planning",
        "role": "build_planner",
        "objective": "Create script, timeline, cues, and render plan from accepted contracts.",
        "allowed_outputs": ["generated_mv_script.json", "timeline_build.json", "sfx_cues.json"],
        "must_not_touch": ["final.mp4"],
        "success_criteria": ["Timeline must only use approved material windows."],
    },
    {
        "stage": "Official Render",
        "role": "renderer",
        "objective": "Render the official ffmpeg output and render manifest.",
        "allowed_outputs": ["final.mp4", "subtitles.srt", "artifact_manifest.json", "state.json"],
        "must_not_touch": [],
        "success_criteria": ["Render must be produced by the canonical pipeline, not stale artifacts."],
    },
    {
        "stage": "Verify / Reviewer Layer",
        "role": "verifier",
        "objective": "Run deterministic and reviewer checks on the rendered artifact.",
        "allowed_outputs": ["verify_result.json", "review_report.md", "contact_sheet.jpg"],
        "must_not_touch": ["final.mp4", "timeline_build.json"],
        "success_criteria": ["Report failures instead of hiding them."],
    },
    {
        "stage": "Workbench Draft Review",
        "role": "workbench_operator",
        "objective": "Capture human timeline patches without touching canonical artifacts.",
        "allowed_outputs": [
            "preview_timeline.json",
            "timeline_patch.json",
            "patched_draft_timeline.json",
            "workbench_contract_patch.json",
        ],
        "must_not_touch": ["final.mp4", "timeline_build.json", "segment_contract.json"],
        "success_criteria": ["Workbench artifacts must remain drafts unless explicitly accepted."],
    },
    {
        "stage": "Brownfield Edit / Finishing",
        "role": "finishing_operator",
        "objective": "Apply accepted finishing or effect revisions through bounded patches.",
        "allowed_outputs": [
            "effect_revision_request.json",
            "effect_recipe_patch.json",
            "remotion_prompt_pack.json",
            "remotion_effect_review.json",
        ],
        "must_not_touch": ["final.mp4", "timeline_build.json"],
        "success_criteria": ["Effects remain neutral until a backend route is selected."],
    },
    {
        "stage": "Delivery",
        "role": "delivery_operator",
        "objective": "Collect final delivery evidence and operator notes.",
        "allowed_outputs": ["delivery_notes.md", "run_layout.json"],
        "must_not_touch": ["final.mp4"],
        "success_criteria": ["Delivery must reference the final verified artifact."],
    },
]


def initial_state() -> dict[str, Any]:
    return {
        "artifact_role": "route_orchestrator_state",
        "version": 1,
        "current_stage": 0,
        "status": "ready",
        "history": [],
    }


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _sha256(path: Path) -> str | None:
    if not path.exists() or not path.is_file():
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _snapshot_path(path: Path) -> dict[str, Any]:
    exists = path.exists()
    item: dict[str, Any] = {
        "exists": exists,
        "is_file": path.is_file() if exists else False,
        "sha256": _sha256(path),
    }
    if exists:
        item["mtime"] = path.stat().st_mtime
        item["size"] = path.stat().st_size if path.is_file() else None
    return item


def _resolve_many(run_dir: Path, rels: Iterable[str]) -> list[Path]:
    out = []
    for rel in rels:
        p = Path(rel)
        if not p.is_absolute():
            p = run_dir / rel
        out.append(p)
    return out


def _load_state(state: Path | None) -> dict[str, Any]:
    if state and state.exists():
        data = _read_json(state)
        if not isinstance(data.get("current_stage", 0), int):
            raise ValueError("route state current_stage must be an integer")
        data.setdefault("history", [])
        data.setdefault("status", "ready")
        return data
    return initial_state()


def write_next_task(
    run_dir: str | Path,
    out: str | Path,
    *,
    state: str | Path | None = None,
    now_epoch: float | None = None,
    clear_allowed_outputs: bool = True,
) -> dict[str, Any]:
    run_dir = Path(run_dir)
    out = Path(out)
    state_path = Path(state) if state else None
    state_obj = _load_state(state_path)
    stage_index = int(state_obj.get("current_stage", 0))
    if stage_index >= len(STAGES):
        raise ValueError("route is already complete")
    stage = STAGES[stage_index]
    issued = float(time.time() if now_epoch is None else now_epoch)
    allowed_paths = _resolve_many(run_dir, stage["allowed_outputs"])
    if clear_allowed_outputs:
        for path in allowed_paths:
            if path.exists():
                if path.is_dir():
                    raise ValueError(f"allowed output points to directory and cannot be cleared: {path}")
                path.unlink()
    protected_paths = _resolve_many(run_dir, stage["must_not_touch"])
    packet = {
        "artifact_role": "route_subagent_task",
        "version": 1,
        "task_id": f"route-{stage_index:02d}-{int(issued * 1000)}",
        "stage_index": stage_index,
        "stage": stage["stage"],
        "role": stage["role"],
        "objective": stage["objective"],
        "issued_at_epoch": issued,
        "read_only_inputs": [str(p) for p in sorted(run_dir.glob("*.json"))],
        "allowed_outputs": [str(p) for p in allowed_paths],
        "must_not_touch": [str(p) for p in protected_paths],
        "success_criteria": list(stage["success_criteria"]),
        "state_ref": str(state_path) if state_path else None,
        "snapshot": {
            "must_not_touch": {str(p): _snapshot_path(p) for p in protected_paths},
        },
    }
    _write_json(out, packet)
    return packet


def _compare_snapshot(path: Path, expected: dict[str, Any]) -> str | None:
    actual = _snapshot_path(path)
    for key in ("exists", "is_file", "sha256"):
        if actual.get(key) != expected.get(key):
            return f"must_not_touch changed: {path}"
    return None


def accept_task_result(
    task_path: str | Path,
    result_path: str | Path,
    *,
    state_out: str | Path,
) -> dict[str, Any]:
    task_path = Path(task_path)
    result_path = Path(result_path)
    state_out = Path(state_out)
    task = _read_json(task_path)
    result = _read_json(result_path)
    errors: list[str] = []

    if task.get("artifact_role") != "route_subagent_task":
        errors.append("task artifact_role must be route_subagent_task")
    if result.get("artifact_role") != "route_subagent_result":
        errors.append("result artifact_role must be route_subagent_result")
    if result.get("task_id") != task.get("task_id"):
        errors.append("result task_id does not match task")

    status = result.get("status")
    if status not in VALID_RESULT_STATUSES:
        errors.append(f"result status must be one of {sorted(VALID_RESULT_STATUSES)}")

    for path_s, snap in (task.get("snapshot", {}).get("must_not_touch") or {}).items():
        err = _compare_snapshot(Path(path_s), snap)
        if err:
            errors.append(err)

    allowed = {str(Path(p)) for p in task.get("allowed_outputs", [])}
    outputs = result.get("outputs", [])
    if not isinstance(outputs, list):
        errors.append("result outputs must be a list")
        outputs = []
    for output in outputs:
        p = Path(output)
        if str(p) not in allowed:
            errors.append(f"output outside allowed_outputs: {p}")
            continue
        if status == "done":
            if not p.exists() or not p.is_file():
                errors.append(f"missing output: {p}")
                continue
            if p.stat().st_mtime < float(task.get("issued_at_epoch", 0)):
                errors.append(f"stale output: {p}")

    if errors:
        return {"ok": False, "errors": errors}

    previous = _load_state(Path(task["state_ref"]) if task.get("state_ref") else None)
    current_stage = int(task["stage_index"])
    next_stage = current_stage + 1 if status == "done" else current_stage
    route_status = "complete" if status == "done" and next_stage >= len(STAGES) else (
        "ready" if status == "done" else status
    )
    history = list(previous.get("history", []))
    history.append(
        {
            "task_id": task["task_id"],
            "stage_index": current_stage,
            "stage": task["stage"],
            "accepted_status": status,
            "outputs": outputs,
            "summary": result.get("summary"),
        }
    )
    state = {
        "artifact_role": "route_orchestrator_state",
        "version": 1,
        "current_stage": next_stage,
        "status": route_status,
        "history": history,
    }
    if status != "done":
        state["next_action"] = result.get("next_action") or status
    _write_json(state_out, state)
    return {"ok": True, "state": state, "errors": []}


def build_orchestrator_report(state_path: str | Path) -> dict[str, Any]:
    state = _read_json(Path(state_path))
    idx = int(state.get("current_stage", 0))
    next_stage = STAGES[idx]["stage"] if idx < len(STAGES) else None
    return {
        "artifact_role": "route_orchestrator_report",
        "version": 1,
        "status": state.get("status"),
        "current_stage": idx,
        "next_stage": next_stage,
        "history_count": len(state.get("history", [])),
    }
