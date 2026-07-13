"""Inspect rendered rehearsal/final candidates with executable evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.rendered_product_qa import write_rendered_product_qa


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run folder to inspect")
    parser.add_argument("--out-dir", required=True, help="Directory for rendered_product_qa.json and frame evidence")
    parser.add_argument(
        "--audio-contract",
        help="Readable JSON audio contract located within the run root",
    )
    parser.add_argument("--json", action="store_true", help="Print rendered product QA JSON")
    args = parser.parse_args()

    result = write_rendered_product_qa(args.run, args.out_dir, audio_contract=args.audio_contract)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"rendered_product_qa pass={result.get('pass')} out={Path(args.out_dir) / 'rendered_product_qa.json'}")
    return 0 if result.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
