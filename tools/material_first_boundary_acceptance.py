"""Run the material-first boundary acceptance chain for Stage 2/3 through Stage 5."""
from __future__ import annotations

import argparse
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.material_first_stage2_3_smoke import run_stage2_3_smoke  # noqa: E402
from tools.stage4_build_smoke import run_stage4_build_smoke  # noqa: E402
from tools.stage5_final_review_smoke import run_stage5_final_review_smoke  # noqa: E402
from video_pipeline_core.material_rough_cut import write_json  # noqa: E402


STAGE_REPORT_FILES = {
    "stage2_3_material_wall_to_review_apply": "stage2_3_smoke_report.json",
    "stage4_build": "stage4_build_smoke_report.json",
    "stage5_final_review": "stage5_final_review_smoke_report.json",
}


def _prepare_wall_verdict(run_dir: Path, wall_verdict) -> tuple[Path, dict | None]:
    verdict_path = Path(wall_verdict).resolve()
    payload = json.loads(verdict_path.read_text(encoding="utf-8-sig"))
    try:
        verdict_path.relative_to(run_dir)
    except ValueError:
        return verdict_path, None

    temp = tempfile.NamedTemporaryFile(
        "w",
        suffix=".material_wall_review_verdict.json",
        encoding="utf-8",
        delete=False,
    )
    with temp:
        json.dump(payload, temp, ensure_ascii=False, indent=2)
    return Path(temp.name), {"path": verdict_path, "payload": payload}


def _restore_in_run_wall_verdict(saved: dict | None):
    if not saved:
        return
    write_json(saved["path"], saved["payload"])


def _cleanup_temp_wall_verdict(verdict_path: Path, saved: dict | None):
    if not saved:
        return
    try:
        verdict_path.unlink()
    except OSError:
        pass


def _stage_entry(result: dict) -> dict:
    report = result.get("report") or {}
    return {
        "stage": report.get("stage"),
        "ok": bool(result.get("ok")),
        "next_action": report.get("next_action"),
        "blocking": report.get("blocking") or report.get("issues") or [],
        "report": STAGE_REPORT_FILES.get(report.get("stage")),
    }


def _failed_stage_entry(stage: str, message: str, report_file: str | None = None) -> dict:
    return {
        "stage": stage,
        "ok": False,
        "next_action": f"repair:{stage}",
        "blocking": [{
            "rule": "stage_exception",
            "message": message,
            "repair": stage,
        }],
        "report": report_file,
    }


def _build_report(run_dir: Path, stages: list[dict]) -> dict:
    failed = next((stage for stage in stages if not stage.get("ok")), None)
    if failed:
        next_action = failed.get("next_action") or f"repair:{failed.get('stage')}"
        failed_stage = failed.get("stage")
        ok = False
    else:
        final = stages[-1] if stages else {}
        next_action = final.get("next_action") or "ready_for_render_or_human_review"
        failed_stage = None
        ok = True
    return {
        "artifact_role": "material_first_boundary_acceptance_report",
        "version": 1,
        "route": "material-first",
        "ok": ok,
        "next_action": next_action,
        "failed_stage": failed_stage,
        "stages": stages,
        "stage_reports": {
            stage["stage"]: stage["report"]
            for stage in stages
            if stage.get("stage") and stage.get("report")
        },
        "run_dir": str(run_dir),
        "read": [
            "stage2_3_smoke_report.json",
            "stage4_build_smoke_report.json",
            "stage5_final_review_smoke_report.json",
        ],
    }


def run_material_first_boundary_acceptance(run_dir, *, source_dir, wall_verdict, max_assets=12) -> dict:
    root = Path(run_dir).resolve()
    stages: list[dict] = []
    verdict_for_runner, saved_in_run_verdict = _prepare_wall_verdict(root, wall_verdict)

    try:
        stage2_3 = run_stage2_3_smoke(
            root,
            source_dir=source_dir,
            wall_verdict=verdict_for_runner,
            max_assets=max_assets,
        )
        _restore_in_run_wall_verdict(saved_in_run_verdict)
    except Exception as exc:
        _restore_in_run_wall_verdict(saved_in_run_verdict)
        _cleanup_temp_wall_verdict(verdict_for_runner, saved_in_run_verdict)
        stages.append(_failed_stage_entry(
            "stage2_3_material_wall_to_review_apply",
            str(exc),
            STAGE_REPORT_FILES["stage2_3_material_wall_to_review_apply"],
        ))
        report = _build_report(root, stages)
        write_json(root / "material_first_boundary_acceptance_report.json", report)
        return {"ok": False, "run_dir": str(root), "report": report}
    _cleanup_temp_wall_verdict(verdict_for_runner, saved_in_run_verdict)
    stages.append(_stage_entry(stage2_3))
    if not stage2_3.get("ok"):
        report = _build_report(root, stages)
        write_json(root / "material_first_boundary_acceptance_report.json", report)
        return {"ok": False, "run_dir": str(root), "report": report}

    stage4 = run_stage4_build_smoke(root)
    stages.append(_stage_entry(stage4))
    if not stage4.get("ok"):
        report = _build_report(root, stages)
        write_json(root / "material_first_boundary_acceptance_report.json", report)
        return {"ok": False, "run_dir": str(root), "report": report}

    stage5 = run_stage5_final_review_smoke(root)
    stages.append(_stage_entry(stage5))
    report = _build_report(root, stages)
    write_json(root / "material_first_boundary_acceptance_report.json", report)
    return {"ok": bool(report.get("ok")), "run_dir": str(root), "report": report}


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="run folder to create")
    parser.add_argument("--source-dir", required=True, help="source folder with existing media")
    parser.add_argument("--wall-verdict", required=True, help="material_wall_review_verdict.json")
    parser.add_argument("--max-assets", type=int, default=12)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_material_first_boundary_acceptance(
        args.out,
        source_dir=args.source_dir,
        wall_verdict=args.wall_verdict,
        max_assets=args.max_assets,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} run_dir={result['run_dir']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
