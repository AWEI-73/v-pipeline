"""Build the Canon 67 0:00-0:44 technical opening candidate from accepted inputs."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from video_pipeline_core.graduation_opening_slice import OpeningSliceError, run_graduation_opening_slice  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed-run", required=True)
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        result = run_graduation_opening_slice(
            seed_run=args.seed_run,
            source_root=args.source_root,
            request_path=args.request,
            out_dir=args.out,
        )
    except (OpeningSliceError, OSError, ValueError) as exc:
        result = {"artifact_role": "opening_slice_command_result", "pass": False, "error": str(exc)}
        out = Path(args.out)
        if out.exists() and out.is_dir():
            (out / "opening_slice_command_error.json").write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"opening slice pass={result.get('pass')} out={args.out}")
    return 0 if result.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
