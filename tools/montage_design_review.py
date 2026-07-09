"""Write montage design review for a run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.montage_design_review import write_montage_design_review_for_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory to inspect/write.")
    parser.add_argument("--json", action="store_true", help="Print review JSON.")
    args = parser.parse_args()

    report = write_montage_design_review_for_run(args.run)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"montage_design_review pass={report['pass']} run={args.run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
