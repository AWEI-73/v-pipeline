"""Write a visual-selection gate report for a run without modifying the run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.visual_selection_gate import write_visual_selection_gate_for_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Read-only run directory to inspect.")
    parser.add_argument("--out-dir", required=True, help="Directory for visual-selection gate artifacts.")
    parser.add_argument("--json", action="store_true", help="Print gate report JSON.")
    args = parser.parse_args()

    report = write_visual_selection_gate_for_run(args.run, args.out_dir)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            "visual_selection_gate "
            f"pass={report['pass']} "
            f"blocked_token_only={','.join(report['blocked_token_only_selections']) or 'none'} "
            f"out_dir={args.out_dir}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
