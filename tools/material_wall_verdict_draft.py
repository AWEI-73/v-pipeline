"""Draft a Material Wall review verdict from material_understanding_matrix.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.material_wall_verdict_draft import build_wall_verdict_draft_file  # noqa: E402


def _roles(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--matrix", required=True, help="material_understanding_matrix.json input")
    parser.add_argument("--out", required=True, help="output material_wall_review_verdict draft JSON")
    parser.add_argument("--roles", default="opening,training,closing", help="comma-separated required visual roles")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    payload = build_wall_verdict_draft_file(
        args.matrix,
        out_path=args.out,
        required_roles=_roles(args.roles),
    )
    result = {
        "ok": True,
        "material_wall_review_verdict": str(Path(args.out)),
        "primary_selection": payload.get("primary_selection") or {},
        "alternate_count": len(payload.get("alternate_candidates") or []),
        "next_action": payload.get("next_action"),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "material_wall_review_verdict "
            f"selected={len(result['primary_selection'])} alternates={result['alternate_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
