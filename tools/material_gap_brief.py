"""CLI for material gap brief planning."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.material_gap_brief import (  # noqa: E402
    build_material_gap_brief,
    build_shooting_brief_markdown,
    jobs_for_route,
    load_json,
    write_json,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--delta", required=True, help="material_delta.json")
    parser.add_argument("--needs", help="material_needs.json")
    parser.add_argument("--lifecycle", help="material_map_lifecycle.json")
    parser.add_argument("--out", required=True, help="material_gap_brief.json output")
    parser.add_argument("--shooting-out", help="shooting_brief.md output")
    parser.add_argument("--generated-jobs-out", help="generated_material_jobs.json output")
    parser.add_argument("--stock-jobs-out", help="stock_retrieval_jobs.json output")
    parser.add_argument("--route")
    args = parser.parse_args(argv)

    gap_brief = build_material_gap_brief(
        load_json(args.delta),
        material_needs=load_json(args.needs) if args.needs else None,
        lifecycle=load_json(args.lifecycle) if args.lifecycle else None,
        route=args.route,
    )
    write_json(args.out, gap_brief)
    if args.shooting_out:
        Path(args.shooting_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.shooting_out).write_text(
            build_shooting_brief_markdown(gap_brief),
            encoding="utf-8",
        )
    if args.generated_jobs_out:
        write_json(args.generated_jobs_out, jobs_for_route(gap_brief, "generated_material"))
    if args.stock_jobs_out:
        write_json(args.stock_jobs_out, jobs_for_route(gap_brief, "stock_retrieval"))

    print(json.dumps({
        "ok": gap_brief["ok"],
        "material_gap_brief": str(Path(args.out)),
        "task_count": gap_brief["task_count"],
        "summary": gap_brief["summary"],
        "does_not_release_build": gap_brief["does_not_release_build"],
    }, ensure_ascii=False, indent=2))
    return 0 if gap_brief["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
