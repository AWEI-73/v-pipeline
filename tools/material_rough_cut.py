"""CLI for material-map rough-cut planning."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.material_rough_cut import (  # noqa: E402
    build_rough_cut_plan,
    load_json,
    write_json,
)


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--contract", required=True, help="segment_contract.json")
    parser.add_argument("--project-map", required=True, help="reviewed project_material_map.json")
    parser.add_argument("--out", required=True, help="rough_cut_plan.json output")
    parser.add_argument("--timeline-out", help="optional timeline_build.json output")
    parser.add_argument("--default-clip-sec", type=float, default=3.0)
    args = parser.parse_args(argv)

    plan = build_rough_cut_plan(
        load_json(args.contract),
        load_json(args.project_map),
        default_clip_sec=args.default_clip_sec,
    )
    write_json(args.out, plan)
    if args.timeline_out:
        write_json(args.timeline_out, plan["timeline_build"])
    print(json.dumps({
        "ok": plan["ok"],
        "rough_cut_plan": str(Path(args.out)),
        "timeline_build": str(Path(args.timeline_out)) if args.timeline_out else None,
        "clip_count": plan["clip_count"],
        "gap_count": plan["gap_count"],
    }, ensure_ascii=False, indent=2))
    return 0 if plan["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
