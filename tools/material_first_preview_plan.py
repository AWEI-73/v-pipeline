"""Build a 60-90s material-first preview rough-cut proposal without rendering."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.material_first_preview_plan import build_preview_plan_file  # noqa: E402


def _roles(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, help="material_understanding_matrix.json")
    parser.add_argument("--wall-verdict-draft", required=True, help="material_wall_review_verdict.draft.json")
    parser.add_argument("--out", required=True, help="output preview rough cut plan")
    parser.add_argument("--target-duration", type=float, default=75.0)
    parser.add_argument("--min-duration", type=float, default=60.0)
    parser.add_argument("--max-duration", type=float, default=90.0)
    parser.add_argument("--clip-duration", type=float, default=6.0)
    parser.add_argument("--roles", default="opening,training,closing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    plan = build_preview_plan_file(
        args.matrix,
        args.wall_verdict_draft,
        out_path=args.out,
        target_duration_sec=args.target_duration,
        min_duration_sec=args.min_duration,
        max_duration_sec=args.max_duration,
        clip_duration_sec=args.clip_duration,
        roles=_roles(args.roles),
    )
    result = {
        "ok": bool(plan.get("ok")),
        "preview_rough_cut_plan": str(Path(args.out)),
        "clip_count": plan.get("clip_count"),
        "total_duration_sec": plan.get("total_duration_sec"),
        "next_action": plan.get("next_action"),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"ok={result['ok']} duration={result['total_duration_sec']} "
            f"clips={result['clip_count']} out={result['preview_rough_cut_plan']}"
        )
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
