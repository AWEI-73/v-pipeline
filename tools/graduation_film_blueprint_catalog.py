"""Write graduation film canon/blueprint/catalog dry-run artifacts."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.graduation_film_blueprint_catalog import (
    write_graduation_film_dry_run,
    write_graduation_film_real_source_dry_run,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--brief", help="Optional JSON brief with title/theme.")
    parser.add_argument("--source-root", help="Fixture or read-only source root to inventory.")
    parser.add_argument("--out-dir", required=True, help="Dry-run output directory.")
    parser.add_argument("--json", action="store_true", help="Print summary JSON.")
    args = parser.parse_args()

    if args.source_root:
        summary = write_graduation_film_real_source_dry_run(args.source_root, args.out_dir)
    else:
        brief = {}
        if args.brief:
            brief = json.loads(Path(args.brief).read_text(encoding="utf-8-sig"))
        summary = write_graduation_film_dry_run(
            brief,
            args.out_dir,
            source_root=args.source_root,
        )
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        canon_sections = summary.get("canon_sections") or summary.get("retarget_summary", {}).get("changed_sections") or []
        agent_filled = (
            summary.get("training_catalog_summary", {}).get("agent_filled_count")
            or sum(summary.get("module_counts", {}).values())
            or 0
        )
        print(
            "graduation_film_blueprint_catalog "
            f"out_dir={summary['out_dir']} "
            f"canon_sections={','.join(canon_sections)} "
            f"agent_filled={agent_filled}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
