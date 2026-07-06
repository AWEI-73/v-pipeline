"""Build film canon product-route pre-render production readiness artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.film_canon_production_readiness import (
    build_product_route_review_decision,
    write_film_canon_production_readiness,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--film-type", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--decision", choices=["approved", "revision_requested", "rejected", "pending_review"])
    parser.add_argument("--reviewer", choices=["human", "agent", "none"])
    parser.add_argument("--notes", default="")
    parser.add_argument("--decision-path", help="existing product_route_review_decision.json to consume")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    decision = None
    if not args.decision_path:
        decision_value = args.decision
        reviewer = args.reviewer
        if not decision_value:
            if args.film_type == "daily_kids_memory_film":
                decision_value = "approved"
                reviewer = reviewer or "human"
            else:
                decision_value = "pending_review"
                reviewer = reviewer or "none"
        reviewer = reviewer or "none"
        decision = build_product_route_review_decision(
            decision=decision_value,
            reviewer=reviewer,
            notes=args.notes or (
                "fixture product route approval"
                if decision_value == "approved" and reviewer == "human"
                else "product-route human review required"
            ),
            approve_all_reviewed=(decision_value == "approved" and reviewer == "human"),
        )
    try:
        summary = write_film_canon_production_readiness(
            args.film_type,
            args.source_root,
            args.out_dir,
            decision=decision,
            decision_path=args.decision_path,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        gate = summary["production_readiness_gate"]
        print(
            "film_canon_readiness "
            f"film_type={summary['film_type']} "
            f"ready={gate['ready_for_production']} "
            f"next_owner={gate['next_owner']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
