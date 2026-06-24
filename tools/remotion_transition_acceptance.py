#!/usr/bin/env python
"""Run bounded Remotion transition/effect acceptance scenarios.

This is a harness for the Brownfield Remotion adapter route. It creates a run
folder, renders a synthetic base draft, produces Remotion effect assets, writes
review artifacts, and composites a non-canonical draft. It never writes
final.mp4.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.remotion_acceptance import run_remotion_transition_acceptance


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run-dir", required=True, help="Run folder to create/use")
    parser.add_argument(
        "--profile",
        choices=["boundary", "micro", "real"],
        default="boundary",
        help="Acceptance scenario size",
    )
    parser.add_argument(
        "--real-worker-command",
        default=None,
        help=(
            "Optional Remotion worker command template. Placeholders: "
            "{job_json}, {job_id}, {preview_file}, {rendered_asset}, {duration_sec}"
        ),
    )
    parser.add_argument("--ffmpeg", default=None, help="Optional ffmpeg executable")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    report = run_remotion_transition_acceptance(
        args.run_dir,
        profile=args.profile,
        real_worker_command=args.real_worker_command,
        ffmpeg=args.ffmpeg,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"ok={report.get('ok')} profile={report.get('profile')} run={args.run_dir}")
        print(f"next_action={report.get('next_action')}")
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
