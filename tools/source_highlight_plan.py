"""CLI for planning a single-source highlight rough cut."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.source_highlight_planner import write_source_highlight_plan  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Plan source timeline windows and a rough cut for one long source video")
    parser.add_argument("--source", required=True, help="source video file")
    parser.add_argument("--out-dir", required=True, help="run/output directory")
    parser.add_argument("--soundtrack-probe", help="optional soundtrack_probe_report.json for the source audio")
    parser.add_argument("--source-material-matrix", help="optional reviewed source_material_matrix.json")
    parser.add_argument("--intent", default="", help="brief selection intent, e.g. internship highlights and ending")
    parser.add_argument("--target-sec", type=float, default=90.0)
    parser.add_argument("--window-sec", type=float, default=12.0)
    parser.add_argument("--clip-sec", type=float, default=10.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = write_source_highlight_plan(
        args.source,
        out_dir=args.out_dir,
        soundtrack_probe_path=args.soundtrack_probe,
        source_material_matrix_path=args.source_material_matrix,
        intent=args.intent,
        target_sec=args.target_sec,
        window_sec=args.window_sec,
        clip_sec=args.clip_sec,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"rough_cut_plan: {result['rough_cut_plan']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
