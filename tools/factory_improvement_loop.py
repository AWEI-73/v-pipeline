from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.factory_improvement_loop import write_factory_improvement_backlog


def _load_findings(path: Path) -> list[dict]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if isinstance(payload, dict):
        if isinstance(payload.get("blocking"), list):
            return [dict(item, source=payload.get("source_tool", "rendered_product_qa")) for item in payload["blocking"]]
        if isinstance(payload.get("findings"), list):
            return [dict(item) for item in payload["findings"]]
    if isinstance(payload, list):
        return [dict(item) for item in payload]
    return []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build factory improvement backlog from QA/review findings.")
    parser.add_argument("--findings", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    backlog = write_factory_improvement_backlog(_load_findings(Path(args.findings)), args.out)
    if args.json:
        print(json.dumps(backlog, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
