"""Summarize final review gates before render or delivery handoff."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.material_rough_cut import load_json, write_json  # noqa: E402


def _safe_load(path: Path) -> dict:
    if not path.exists():
        return {}
    return load_json(path)


def _input_status(artifact: dict, pass_key: str = "ok") -> str:
    if not artifact:
        return "missing"
    if artifact.get(pass_key) is False:
        return "fail"
    return "pass"


def _block(rule: str, message: str, repair: str, **extra) -> dict:
    out = {"rule": rule, "message": message, "repair": repair}
    out.update(extra)
    return out


def _stage4_blocks(stage4: dict) -> list[dict]:
    if not stage4:
        return [_block(
            "missing_stage4_build_smoke",
            "stage4_build_smoke_report.json is missing",
            "stage4_build",
        )]
    if stage4.get("ok") is False:
        return [_block(
            "stage4_build_failed",
            "Stage 4 build smoke has blocking issues",
            "stage4_build",
            issues=stage4.get("issues") or [],
        )]
    return []


def _boundary_blocks(boundary: dict) -> list[dict]:
    if not boundary:
        return []
    if boundary.get("pass") is False or boundary.get("gate_status") == "failed":
        return [_block(
            "boundary_failed",
            "Stage 5 boundary report failed",
            "stage5_final_review",
            regressions=boundary.get("regressions") or [],
        )]
    return []


def _verify_blocks(verify: dict) -> list[dict]:
    if not verify:
        return []
    if verify.get("pass") is False:
        return [_block(
            "verify_failed",
            f"verify_result failed with score {verify.get('score')}",
            "verify",
            issues=verify.get("issues") or [],
        )]
    return []


def _editor_blocks(editor_review: dict) -> list[dict]:
    if editor_review:
        return []
    return [_block(
        "missing_editor_review",
        "editor_review.json is required before final review handoff",
        "stage4_build",
    )]


def _rough_cut_blocks(rough_cut: dict) -> list[dict]:
    if not rough_cut:
        return []
    if rough_cut.get("ok") is False or rough_cut.get("gaps"):
        return [_block(
            "rough_cut_gap",
            "rough_cut_plan still has gaps",
            "stage4_build",
            gaps=rough_cut.get("gaps") or [],
        )]
    return []


def _next_action(blocking: list[dict]) -> str:
    if not blocking:
        return "ready_for_render_or_human_review"
    priority = ("stage4_build", "stage5_final_review", "verify")
    repairs = [item.get("repair") for item in blocking]
    for repair in priority:
        if repair in repairs:
            return f"repair:{repair}"
    return f"repair:{repairs[0]}"


def build_stage5_report(run_dir: Path) -> dict:
    stage4 = _safe_load(run_dir / "stage4_build_smoke_report.json")
    boundary = _safe_load(run_dir / "boundary_report.json")
    editor_review = _safe_load(run_dir / "editor_review.json")
    rough_cut = _safe_load(run_dir / "rough_cut_plan.json")
    timeline = _safe_load(run_dir / "timeline_build.json")
    verify = _safe_load(run_dir / "verify_result.json")

    blocking = []
    blocking.extend(_stage4_blocks(stage4))
    blocking.extend(_boundary_blocks(boundary))
    blocking.extend(_verify_blocks(verify))
    blocking.extend(_editor_blocks(editor_review))
    blocking.extend(_rough_cut_blocks(rough_cut))

    return {
        "artifact_role": "stage5_final_review_smoke_report",
        "version": 1,
        "stage": "stage5_final_review",
        "ok": not blocking,
        "next_action": _next_action(blocking),
        "blocking": blocking,
        "inputs": {
            "stage4_build_smoke_report": _input_status(stage4),
            "boundary_report": _input_status(boundary, "pass"),
            "editor_review": "pass" if editor_review else "missing",
            "rough_cut_plan": _input_status(rough_cut),
            "timeline_build": "pass" if timeline else "missing",
            "verify_result": _input_status(verify, "pass") if verify else "missing_optional",
        },
        "read": [
            "stage4_build_smoke_report.json",
            "boundary_report.json",
            "editor_review.json",
            "rough_cut_plan.json",
            "timeline_build.json",
            "verify_result.json",
        ],
    }


def run_stage5_final_review_smoke(run_dir) -> dict:
    root = Path(run_dir).resolve()
    report = build_stage5_report(root)
    write_json(root / "stage5_final_review_smoke_report.json", report)
    return {
        "ok": bool(report.get("ok")),
        "run_dir": str(root),
        "report": report,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="run folder to inspect")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_stage5_final_review_smoke(args.run)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} run_dir={result['run_dir']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
