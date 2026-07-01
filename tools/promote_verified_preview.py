"""Explicitly promote a verified preview package to final.mp4."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.verified_preview_package import promote_verified_preview_to_final


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="run folder")
    parser.add_argument("--reviewer", default="operator", help="reviewer/operator name")
    parser.add_argument("--final-name", default="final.mp4", help="canonical final video filename")
    parser.add_argument("--report-name", default="final_promotion_report.json")
    parser.add_argument("--overwrite", action="store_true", help="allow replacing an existing final video")
    parser.add_argument("--json", action="store_true", help="print promotion report JSON")
    args = parser.parse_args()

    report = promote_verified_preview_to_final(
        args.run,
        reviewer=args.reviewer,
        final_name=args.final_name,
        report_name=args.report_name,
        overwrite=args.overwrite,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            "final_promotion "
            f"status={report.get('status')} "
            f"final={report.get('final_video')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
