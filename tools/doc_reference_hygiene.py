from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.doc_reference_hygiene import write_doc_reference_hygiene_report


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check docs/reference hygiene.")
    parser.add_argument("--repo-root", default=".")
    parser.add_argument("--out", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = write_doc_reference_hygiene_report(Path(args.repo_root), args.out)
    if args.json:
        print(json.dumps(report, ensure_ascii=False))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
