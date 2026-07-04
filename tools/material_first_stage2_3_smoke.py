"""Run the material-first Stage 2/3 handoff smoke and summarize verdict effects."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.material_first_landing_case import run_material_first_landing_case  # noqa: E402
from tools.pipeline_home import summarize_run  # noqa: E402
from video_pipeline_core.material_rough_cut import load_json, write_json  # noqa: E402


def _rough_cut_starts(rough_cut: dict) -> dict:
    starts = {}
    for clip in rough_cut.get("clips") or []:
        asset_id = clip.get("asset_id")
        if asset_id:
            starts[asset_id] = clip.get("start_sec")
    return starts


def _build_report(run_dir: Path, result: dict) -> dict:
    if result.get("next_action") == "needs-context":
        return {
            "artifact_role": "stage2_3_smoke_report",
            "version": 1,
            "stage": "stage2_3_material_wall_to_review_apply",
            "ok": False,
            "next_action": "needs-context",
            "blocking": result.get("blocking") or [],
            "source_run_result": result,
            "read": [
                "material_first_source_refusal.json",
                "materials_db.source_candidates.json",
            ],
        }
    handoff = load_json(run_dir / "material_wall_handoff_report.json")
    rough_cut = load_json(run_dir / "rough_cut_plan.json")
    project_map = load_json(run_dir / "project_material_map.json")
    pipeline_home = summarize_run(run_dir)

    rough_cut_asset_ids = [
        clip.get("asset_id")
        for clip in rough_cut.get("clips") or []
        if clip.get("asset_id")
    ]
    mapped_asset_ids = [
        asset.get("asset_id")
        for asset in project_map.get("assets") or []
        if asset.get("asset_id")
    ]
    selected = handoff.get("selected_asset_ids") or []
    rejected = handoff.get("rejected_asset_ids") or []
    duplicates = handoff.get("duplicate_asset_ids") or []
    invalid_rough_cut_assets = sorted(set(rejected + duplicates).intersection(rough_cut_asset_ids))

    return {
        "artifact_role": "stage2_3_smoke_report",
        "version": 1,
        "stage": "stage2_3_material_wall_to_review_apply",
        "ok": bool(
            result.get("ok")
            and handoff.get("ready_for_mapping")
            and not invalid_rough_cut_assets
        ),
        "source_run_result": result,
        "selected_asset_ids": selected,
        "maybe_asset_ids": handoff.get("maybe_asset_ids") or [],
        "duplicate_asset_ids": duplicates,
        "rejected_asset_ids": rejected,
        "missing_need_ids": handoff.get("missing_need_ids") or [],
        "duplicate_need_ids": handoff.get("duplicate_need_ids") or [],
        "mapped_asset_ids": mapped_asset_ids,
        "rough_cut_asset_ids": rough_cut_asset_ids,
        "rough_cut_starts": _rough_cut_starts(rough_cut),
        "invalid_rough_cut_assets": invalid_rough_cut_assets,
        "pipeline_home": pipeline_home,
        "read": [
            "material_wall_handoff_report.json",
            "project_material_map.json",
            "rough_cut_plan.json",
        ],
    }


def run_stage2_3_smoke(run_dir, *, source_dir, wall_verdict, max_assets=12) -> dict:
    run_dir = Path(run_dir).resolve()
    result = run_material_first_landing_case(
        run_dir,
        source_dir=source_dir,
        max_assets=max_assets,
        wall_verdict=wall_verdict,
    )
    report = _build_report(run_dir, result)
    write_json(run_dir / "stage2_3_smoke_report.json", report)
    return {
        "ok": bool(report.get("ok")),
        "run_dir": str(run_dir),
        "report": report,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="run folder to create")
    parser.add_argument("--source-dir", required=True, help="source folder with existing media")
    parser.add_argument("--wall-verdict", required=True, help="material_wall_review_verdict.json")
    parser.add_argument("--max-assets", type=int, default=12)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_stage2_3_smoke(
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
