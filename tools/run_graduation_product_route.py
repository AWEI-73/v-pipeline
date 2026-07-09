"""Run the thin graduation product route execution harness."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.graduation_product_route_runner import GraduationProductRouteRunner


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory to inspect")
    parser.add_argument("--source-root", required=True, help="Read-only source root for route context")
    parser.add_argument("--mode", required=True, choices=("no-render", "render-rehearsal"))
    parser.add_argument("--out-dir", required=True, help="Output directory for trace/result artifacts")
    parser.add_argument("--json", action="store_true", help="Print harness result JSON")
    args = parser.parse_args()

    runner = GraduationProductRouteRunner(repo_root=ROOT)
    result = runner.run(
        run=args.run,
        source_root=args.source_root,
        out_dir=args.out_dir,
        mode=args.mode,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "graduation_product_route "
            f"pass={result.get('pass')} stop_gate={result.get('stop_gate')} out={args.out_dir}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
