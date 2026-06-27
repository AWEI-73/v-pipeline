from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from video_pipeline_core.route_orchestrator import STAGES, accept_task_result, write_next_task
from video_pipeline_core.video_intent_planner import plan_video_intent


ROUTE_CHOICES = {"existing-material-first", "story-first", "hybrid"}


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _artifact_payload(filename: str, *, route: str, stage: str, stage_index: int) -> dict[str, Any]:
    if filename == "video_intent.json":
        if route == "story-first":
            return plan_video_intent({
                "request": "children story video with no existing material",
                "video_type": "storybook",
                "audience": "children",
                "goal": "tell a gentle story",
                "target_length": "3 minutes",
                "material_availability": "none",
                "text_availability": "brief",
                "generation_allowed": True,
                "tone": "warm story-driven",
            })
        if route == "hybrid":
            return plan_video_intent({
                "request": "graduation event recap with partial material",
                "video_type": "graduation-event",
                "audience": "classmates and instructors",
                "goal": "commemorate the training journey",
                "target_length": "4 minutes",
                "material_availability": "partial",
                "material_quality": "some gaps",
                "tone": "energetic and warm",
            })
        return plan_video_intent({
            "request": "teaching video with existing class and screen-recording material",
            "video_type": "teaching",
            "audience": "new students",
            "goal": "teach clearly",
            "target_length": "5 minutes",
            "material_availability": "existing",
            "material_quality": "enough usable screen recordings",
            "tone": "clear instructional",
        })
    role = Path(filename).stem
    payload: dict[str, Any] = {
        "artifact_role": role,
        "version": 1,
        "route": route,
        "stage": stage,
        "stage_index": stage_index,
        "fake_worker_note": "deterministic route replay artifact",
    }
    if filename == "project_brief.json":
        payload["material_availability"] = route
    elif filename == "story_soul_blueprint.json":
        payload["narrative_device"] = "route replay smoke"
    elif filename == "material_needs.json":
        payload["needs"] = []
    elif filename == "project_material_map.json":
        payload["assets"] = []
    elif filename == "material_delta.json":
        payload["ok"] = True
        payload["ready_for_build"] = True
    elif filename == "timeline_build.json":
        payload["clips"] = []
    return payload


def _fake_worker(task: dict[str, Any], *, route: str, inject_bad: bool = False) -> Path:
    allowed = [Path(p) for p in task.get("allowed_outputs", [])]
    if not allowed:
        raise ValueError("task has no allowed_outputs")
    out = allowed[0]
    _write_json(
        out,
        _artifact_payload(out.name, route=route, stage=task["stage"], stage_index=int(task["stage_index"])),
    )
    issued = float(task["issued_at_epoch"])
    os.utime(out, (issued + 1.0, issued + 1.0))
    if inject_bad:
        protected = [Path(p) for p in task.get("must_not_touch", [])]
        if protected:
            protected[0].parent.mkdir(parents=True, exist_ok=True)
            protected[0].write_bytes(b"BAD-TOUCH")
    return out


def run_route_orchestrator_acceptance(
    run_dir: str | Path,
    *,
    route: str,
    stage_count: int = 4,
    inject_bad_stage: int | None = None,
    base_epoch: float = 1000.0,
) -> dict[str, Any]:
    if route not in ROUTE_CHOICES:
        raise ValueError(f"route must be one of {sorted(ROUTE_CHOICES)}")
    if stage_count < 1 or stage_count > len(STAGES):
        raise ValueError(f"stage_count must be 1..{len(STAGES)}")
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    state = run_dir / "route_orchestrator_state.json"
    steps: list[dict[str, Any]] = []
    errors: list[str] = []

    for idx in range(stage_count):
        task_path = run_dir / f"route_task_{idx:02d}.json"
        result_path = run_dir / f"route_result_{idx:02d}.json"
        task = write_next_task(
            run_dir,
            task_path,
            state=state if state.exists() else None,
            now_epoch=base_epoch + idx * 10.0,
        )
        output = _fake_worker(task, route=route, inject_bad=(inject_bad_stage == idx))
        result = {
            "artifact_role": "route_subagent_result",
            "task_id": task["task_id"],
            "status": "done",
            "outputs": [str(output)],
            "summary": f"{route} fake worker completed {task['stage']}",
        }
        _write_json(result_path, result)
        verdict = accept_task_result(task_path, result_path, state_out=state)
        step = {
            "stage_index": idx,
            "stage": task["stage"],
            "status": "done" if verdict.get("ok") else "rejected",
            "task": str(task_path),
            "result": str(result_path),
            "output": str(output),
            "verdict": verdict,
        }
        steps.append(step)
        if not verdict.get("ok"):
            errors.extend(verdict.get("errors") or [])
            return {
                "artifact_role": "route_orchestrator_acceptance",
                "version": 1,
                "ok": False,
                "route": route,
                "requested_stage_count": stage_count,
                "blocked_at_stage": idx,
                "errors": errors,
                "steps": steps,
                "final_state": _read_json(state) if state.exists() else None,
            }

    return {
        "artifact_role": "route_orchestrator_acceptance",
        "version": 1,
        "ok": True,
        "route": route,
        "requested_stage_count": stage_count,
        "blocked_at_stage": None,
        "errors": [],
        "steps": steps,
        "final_state": _read_json(state),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Replay route orchestrator task packets with a deterministic fake worker.")
    parser.add_argument("run_dir")
    parser.add_argument("--route", required=True, choices=sorted(ROUTE_CHOICES))
    parser.add_argument("--stage-count", type=int, default=4)
    parser.add_argument("--inject-bad-stage", type=int, default=None)
    parser.add_argument("--base-epoch", type=float, default=1000.0)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    report = run_route_orchestrator_acceptance(
        args.run_dir,
        route=args.route,
        stage_count=args.stage_count,
        inject_bad_stage=args.inject_bad_stage,
        base_epoch=args.base_epoch,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
