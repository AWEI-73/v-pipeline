"""Build material_understanding_matrix.json from a materials_db.json file."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.material_understanding_matrix import (  # noqa: E402
    build_material_understanding_matrix_file,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--materials-db", required=True, help="materials_db.json input")
    parser.add_argument("--out-dir", required=True, help="output directory")
    parser.add_argument("--max-assets", type=int, default=24)
    parser.add_argument("--frame-budget", type=int, default=3)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    matrix = build_material_understanding_matrix_file(
        args.materials_db,
        out_dir=args.out_dir,
        max_assets=args.max_assets,
        frame_budget=args.frame_budget,
    )
    result = {
        "ok": True,
        "matrix": str(Path(args.out_dir) / "material_understanding_matrix.json"),
        "contact_sheet": matrix.get("visual", {}).get("contact_sheet"),
        "asset_count": matrix.get("asset_count"),
        "next_action": matrix.get("next_action"),
    }
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"material_understanding_matrix assets={result['asset_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
