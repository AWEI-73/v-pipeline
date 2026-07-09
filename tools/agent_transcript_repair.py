"""Write agent transcript repair suggestions and draft subtitles for a run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.agent_transcript_repair import write_agent_transcript_repair_for_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory containing asr_raw_transcript.json or source_speech_asr_probe.json.")
    parser.add_argument("--json", action="store_true", help="Print JSON report.")
    args = parser.parse_args()

    report = write_agent_transcript_repair_for_run(args.run)
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"agent_transcript_repair suggestions={report['suggestion_count']} run={args.run}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
