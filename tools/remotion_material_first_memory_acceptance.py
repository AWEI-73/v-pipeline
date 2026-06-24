#!/usr/bin/env python
"""Run bounded material-first MemoryPhotoWall acceptance.

This checks that reviewed material-wall evidence can drive the Remotion effect
contract and delivery-gate evidence without rendering final.mp4.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.remotion_material_first_acceptance import run_material_first_memory_acceptance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Run folder to create/use")
    parser.add_argument("--project-map", required=True, help="project_material_map.json")
    parser.add_argument("--wall-verdict", required=True, help="material_wall_review_verdict.json")
    parser.add_argument("--wall-request", required=True, help="material_wall_request.json with keyframe evidence")
    parser.add_argument("--max-refs", type=int, default=6, help="maximum reviewed refs to pass into MemoryPhotoWall")
    parser.add_argument("--duration-sec", type=float, default=8.0, help="short effect duration")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run_material_first_memory_acceptance(
        args.run_dir,
        project_map=args.project_map,
        wall_verdict=args.wall_verdict,
        wall_request=args.wall_request,
        max_refs=args.max_refs,
        duration_sec=args.duration_sec,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok={report.get('ok')} run={args.run_dir}")
        print(f"failed_stage={report.get('failed_stage')}")
        print(f"next_action={report.get('next_action')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
