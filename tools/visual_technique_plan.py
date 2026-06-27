"""Create a reviewable visual technique plan from fuzzy effect language."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.visual_technique_plan import plan_visual_technique


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--request", required=True, help="Fuzzy visual/effect request.")
    parser.add_argument("--effect-role", default="", help="opening_title, transition, lower_third, montage_hit, closing_title, or outro.")
    parser.add_argument("--duration-sec", type=float, default=None, help="Optional intended duration in seconds.")
    parser.add_argument("--material-state", default=None, help="Optional material context, for example group_photo_available.")
    parser.add_argument(
        "--confirmed",
        action="store_true",
        help="Mark the candidate direction as user/reviewer confirmed for downstream handoff.",
    )
    parser.add_argument("--out", required=True, help="Output visual_technique_plan.json path.")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout.")
    args = parser.parse_args()

    brief = {
        "request": args.request,
        "effect_role": args.effect_role,
        "duration_sec": args.duration_sec,
        "material_state": args.material_state,
    }
    if args.confirmed:
        brief["confirmed_style_family"] = True
    plan = plan_visual_technique(brief)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    if args.json:
        print(json.dumps(plan, ensure_ascii=False, indent=2))
    else:
        print(
            "visual_technique_plan "
            f"style_family={plan.get('style_family')} "
            f"handoff_to={plan.get('handoff_to')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

