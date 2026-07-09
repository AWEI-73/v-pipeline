"""Write voiceover lead-in mismatch QA for a run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.voiceover_leadin_qa import write_voiceover_leadin_qa_for_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory with narration_manifest.json and voiceover_output_probe.json.")
    parser.add_argument("--json", action="store_true", help="Print QA JSON.")
    args = parser.parse_args()

    report = write_voiceover_leadin_qa_for_run(args.run)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"voiceover_leadin_qa pass={report['pass']} run={args.run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
