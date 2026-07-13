"""Audit no-skip pipeline execution trace for a rehearsal run."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.no_skip_execution_trace import write_strict_trace_audit, write_trace_audit


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run folder to audit")
    parser.add_argument("--contract", help="Committed execution companion for strict closure")
    parser.add_argument("--out-dir", help="Output directory for trace artifacts")
    parser.add_argument("--json", action="store_true", help="Print final artifact check JSON")
    args = parser.parse_args()

    out_dir = Path(args.out_dir) if args.out_dir else (
        ROOT / ".tmp" / f"no_skip_pipeline_execution_trace_{datetime.now().strftime('%Y%m%d-%H%M%S')}"
    )
    if args.contract:
        check = write_strict_trace_audit(ROOT, args.contract, args.run, out_dir)
    else:
        check = write_trace_audit(args.run, out_dir)
    check["output_root"] = str(out_dir)
    if args.json:
        print(json.dumps(check, ensure_ascii=False, indent=2))
    else:
        print(f"no_skip_trace status={check.get('status')} out={out_dir}")
    if args.contract:
        return 0 if check.get("ok") else 1
    return 0 if check.get("status") == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
