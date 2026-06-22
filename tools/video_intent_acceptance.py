from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from video_pipeline_core.video_intent_planner import plan_video_intent


CASES: list[dict[str, Any]] = [
    {
        "id": "teaching_existing",
        "brief": {
            "request": "teaching video with existing class and screen-recording material",
            "video_type": "teaching",
            "audience": "new students",
            "goal": "teach clearly",
            "target_length": "5 minutes",
            "material_availability": "existing",
        },
        "expect": {
            "input_state": "material_available",
            "entry_path": "material-first",
            "route": "material-first",
            "legacy_route": "existing-material-first",
            "handoff_to": "material_map_lifecycle",
            "later_planner": "teaching-structure-planner",
            "needs_material_map_first": True,
        },
    },
    {
        "id": "children_story_no_material",
        "brief": {
            "request": "children storybook video with no material",
            "video_type": "storybook",
            "audience": "children",
            "goal": "tell a gentle story",
            "target_length": "3 minutes",
            "material_availability": "none",
            "text_availability": "brief",
            "generation_allowed": True,
        },
        "expect": {
            "input_state": "text_available",
            "entry_path": "structure-first",
            "route": "structure-first",
            "legacy_route": "story-first",
            "handoff_to": "upstream_structure_route",
            "later_planner": "story-soul-blueprint",
            "needs_generated_material_fallback": True,
        },
    },
    {
        "id": "graduation_partial",
        "brief": {
            "request": "graduation event recap with partial material",
            "video_type": "graduation-event",
            "audience": "classmates and instructors",
            "goal": "commemorate the training journey",
            "target_length": "4 minutes",
            "material_availability": "partial",
        },
        "expect": {
            "input_state": "material_available",
            "entry_path": "material-first",
            "route": "material-first",
            "legacy_route": "hybrid",
            "handoff_to": "material_map_lifecycle",
            "later_planner": "event-recap-planner",
            "needs_material_map_first": True,
        },
    },
    {
        "id": "vague_request",
        "brief": {"request": "make me a video"},
        "expect": {
            "input_state": "unknown",
            "entry_path": "needs-context",
            "legacy_route": None,
            "handoff_to": "ask_followup",
            "min_followup_questions": 4,
        },
    },
]


def _case_errors(actual: dict[str, Any], expect: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    for key, value in expect.items():
        if key == "min_followup_questions":
            if len(actual.get("required_followup_questions") or []) < int(value):
                errors.append(f"required_followup_questions shorter than {value}")
            continue
        if actual.get(key) != value:
            errors.append(f"{key}: expected {value!r}, got {actual.get(key)!r}")
    return errors


def run_video_intent_acceptance() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []
    errors: list[str] = []
    for case in CASES:
        actual = plan_video_intent(case["brief"])
        case_errors = _case_errors(actual, case["expect"])
        if actual.get("artifact_role") != "video_intent":
            case_errors.append("artifact_role must be video_intent")
        if case_errors:
            errors.extend(f"{case['id']}: {err}" for err in case_errors)
        cases.append(
            {
                "id": case["id"],
                "ok": not case_errors,
                "errors": case_errors,
                "actual": actual,
            }
        )
    return {
        "artifact_role": "video_intent_acceptance",
        "version": 1,
        "ok": not errors,
        "case_count": len(cases),
        "errors": errors,
        "cases": cases,
        "boundaries": [
            "no_vip1_or_vip2_templates",
            "no_renderer",
            "no_node14_or_remotion",
            "no_build_ranking",
        ],
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run VIP0 video intent route acceptance.")
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    report = run_video_intent_acceptance()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    return 0 if report.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
