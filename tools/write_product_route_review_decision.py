"""Write product_route_review_decision.json for a film canon readiness run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.product_route_review_decision import write_review_decision


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="film canon readiness run folder")
    parser.add_argument(
        "--decision",
        required=True,
        choices=["approved", "revision_requested", "rejected"],
        help="human product-route review decision",
    )
    parser.add_argument("--reviewer", required=True, help="must be human")
    parser.add_argument(
        "--approve-all-reviewed",
        action="store_true",
        help="broadly approve all reviewed route assignments",
    )
    parser.add_argument(
        "--module-status",
        action="append",
        default=[],
        help="module override as MODULE=accepted|optional|needs_reassign|rejected:note",
    )
    parser.add_argument("--note", action="append", default=[], help="decision note")
    parser.add_argument("--created-at", default="", help="override created_at timestamp")
    parser.add_argument(
        "--out-name",
        default="product_route_review_decision.json",
        help="output artifact name; must remain product_route_review_decision.json",
    )
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args(argv)

    try:
        out_path, payload = write_review_decision(
            run=args.run,
            decision=args.decision,
            reviewer=args.reviewer,
            approve_all_reviewed=args.approve_all_reviewed,
            module_statuses=args.module_status,
            notes=args.note,
            out_name=args.out_name,
            created_at=args.created_at,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    summary = {
        "ok": True,
        "artifact": str(out_path),
        "decision": payload["decision"],
        "reviewer": payload["reviewer"],
        "approve_all_reviewed": payload["approve_all_reviewed"],
        "module_override_count": len(payload["module_overrides"]),
        "is_final_delivery_approval": payload["is_final_delivery_approval"],
        "clears_story_human_review": payload["clears_story_human_review"],
    }
    print(json.dumps(summary if args.json else payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
