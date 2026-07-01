from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.run_artifact_index import write_run_artifact_index  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Classify run-folder artifacts for review.")
    parser.add_argument("--run", required=True, help="Run folder to scan.")
    parser.add_argument("--out", default=None, help="Output JSON path. Defaults to RUN_DIR/run_artifact_index.json.")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout.")
    args = parser.parse_args()

    result = write_run_artifact_index(args.run, args.out)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        out = args.out or str(Path(args.run) / "run_artifact_index.json")
        print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
