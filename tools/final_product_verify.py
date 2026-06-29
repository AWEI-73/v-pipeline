"""CLI for building final product eye/ear VERIFY evidence."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.final_product_verify import build_final_product_verify_bundle  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, help="final/draft video candidate")
    parser.add_argument("--out-dir", required=True, dest="out_dir", help="run/output directory")
    parser.add_argument("--sample-count", type=int, default=12)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_final_product_verify_bundle(
        args.video,
        out_dir=args.out_dir,
        sample_count=args.sample_count,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"final_product_verify pass={str(result.get('pass')).lower()}")
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
