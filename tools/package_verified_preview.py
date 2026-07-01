"""Package a verified preview candidate as delivery_candidate.mp4."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.verified_preview_package import package_verified_preview


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="run folder")
    parser.add_argument("--out-name", default="verified_preview_package.json")
    parser.add_argument("--candidate-name", default="delivery_candidate.mp4")
    parser.add_argument("--json", action="store_true", help="print package JSON")
    args = parser.parse_args()

    package = package_verified_preview(
        args.run,
        out_name=args.out_name,
        candidate_name=args.candidate_name,
    )
    if args.json:
        print(json.dumps(package, ensure_ascii=False, indent=2))
    else:
        print(
            "verified_preview_package "
            f"status={package.get('status')} "
            f"video={package.get('packaged_video')}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
