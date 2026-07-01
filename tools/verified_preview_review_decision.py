"""Record an operator decision for a verified preview candidate."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.verified_preview_package import record_verified_preview_review_decision


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="run folder")
    parser.add_argument(
        "--decision",
        required=True,
        choices=["accept_promote", "revise_workbench", "rebuild_motion_preview", "reject"],
        help="operator decision for delivery_candidate.mp4",
    )
    parser.add_argument("--reviewer", default="operator", help="reviewer/operator name")
    parser.add_argument("--notes", default="", help="short operator notes")
    parser.add_argument("--out-name", default="verified_preview_review_decision.json")
    parser.add_argument("--json", action="store_true", help="print decision JSON")
    args = parser.parse_args()

    decision = record_verified_preview_review_decision(
        args.run,
        decision=args.decision,
        reviewer=args.reviewer,
        notes=args.notes,
        out_name=args.out_name,
    )
    if args.json:
        print(json.dumps(decision, ensure_ascii=False, indent=2))
    else:
        print(
            "verified_preview_review_decision "
            f"decision={decision.get('decision')} "
            f"next={decision.get('next_action')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
