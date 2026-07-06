"""Film canon registry / product route selector."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.film_canon_registry import (
    get_film_canon_route,
    list_supported_film_types,
    write_film_canon_route_dry_run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--list", action="store_true", help="List supported film types.")
    parser.add_argument("--film-type", help="Film type to dry-run.")
    parser.add_argument("--source-root", help="Fixture source root to inventory.")
    parser.add_argument("--out-dir", help="Dry-run output directory.")
    parser.add_argument("--json", action="store_true", help="Print JSON output.")
    args = parser.parse_args()

    if args.list:
        payload = {
            "ok": True,
            "supported_film_types": list_supported_film_types(),
            "routes": [get_film_canon_route(film_type) for film_type in list_supported_film_types()],
        }
        if args.json:
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        else:
            print("\n".join(payload["supported_film_types"]))
        return 0

    if not args.film_type or not args.out_dir:
        parser.error("--film-type and --out-dir are required unless --list is used")

    try:
        summary = write_film_canon_route_dry_run(args.film_type, args.source_root, args.out_dir)
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            "film_canon_route "
            f"film_type={summary['film_type']} "
            f"out_dir={summary['out_dir']} "
            f"rendered={summary['rendered']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
