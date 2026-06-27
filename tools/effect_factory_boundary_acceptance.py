"""Run a no-render Effect Factory boundary acceptance probe."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.effect_factory_boundary import (
    run_effect_factory_boundary_acceptance,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        "--run-dir",
        dest="run_dir",
        required=True,
        help="Run folder for effect factory boundary artifacts.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print the acceptance report JSON.",
    )
    args = parser.parse_args()

    report = run_effect_factory_boundary_acceptance(Path(args.run_dir))
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            "effect_factory_boundary_acceptance "
            f"ok={str(report.get('ok')).lower()} "
            f"next_action={report.get('next_action')}"
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
