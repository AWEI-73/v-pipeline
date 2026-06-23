"""Build a deterministic material-first boundary acceptance run folder."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.boundary_smoke import run_boundary  # noqa: E402
from video_pipeline_core import material_map_lifecycle  # noqa: E402
from video_pipeline_core.material_map_review_apply import apply_review_to_maps  # noqa: E402
from video_pipeline_core.material_rough_cut import build_rough_cut_plan, load_json, write_json  # noqa: E402


def _copytree_contents(source: Path, target: Path):
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)


def run_material_first_landing_case(run_dir) -> dict:
    run_dir = Path(run_dir).resolve()
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    repo = Path(__file__).resolve().parents[1]
    fixture_input = repo / "examples" / "boundary_fixtures" / "stage3_review_apply" / "input"
    _copytree_contents(fixture_input, run_dir)

    write_json(run_dir / "video_intent.json", {
        "artifact_role": "video_intent",
        "entry_path": "material-first",
        "video_type": "graduation-event",
        "goal": "prove existing material can move from map review to rough timeline",
    })

    apply_review_to_maps(
        run_dir / "maps",
        run_dir / "material_needs.json",
        run_dir / "material_map_review_verdict.json",
        run_dir / "project_material_map.json",
        material_db_path=run_dir / "materials_db.json",
    )
    lifecycle = material_map_lifecycle.run_lifecycle(
        out_dir=run_dir,
        needs_ref=run_dir / "material_needs.json",
        material_db_ref=run_dir / "materials_db.json",
        contract_ref=run_dir / "segment_contract.json",
    )
    write_json(run_dir / "material_map_lifecycle.json", lifecycle)

    rough = build_rough_cut_plan(
        load_json(run_dir / "segment_contract.json"),
        load_json(run_dir / "project_material_map.json"),
    )
    write_json(run_dir / "rough_cut_plan.json", rough)
    write_json(run_dir / "timeline_build.json", rough["timeline_build"])
    write_json(run_dir / "editor_review.json", {
        "artifact_role": "editor_review",
        "decision": "human_review",
        "reason": "rough timeline is ready for review; render is intentionally skipped",
    })

    stage_dir = run_dir / "_stage5_boundary"
    input_dir = stage_dir / "input"
    input_dir.mkdir(parents=True)
    for name in ("rough_cut_plan.json", "timeline_build.json", "editor_review.json"):
        shutil.copy2(run_dir / name, input_dir / name)
    write_json(input_dir / "boundary_config.json", {
        "stage": "stage5_final_review",
        "expected": {"pass": True},
    })
    report = run_boundary(stage_dir)
    write_json(run_dir / "boundary_report.json", report)

    return {
        "ok": bool(lifecycle.get("can_build") and rough.get("ok") and report.get("pass")),
        "run_dir": str(run_dir),
        "lifecycle_stage": lifecycle.get("stage"),
        "rough_clip_count": rough.get("clip_count"),
        "boundary_pass": report.get("pass"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="run folder to create")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_material_first_landing_case(args.out)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} run_dir={result['run_dir']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
