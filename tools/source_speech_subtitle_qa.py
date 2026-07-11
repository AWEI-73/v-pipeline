"""Write source-speech subtitle QA for a run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.source_speech_subtitle_qa import write_source_speech_subtitle_qa_for_run


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory to inspect and write source_speech_subtitle_qa.json into.")
    parser.add_argument("--require-approved-text-binding", action="store_true", help="Require a v2 human-approved transcript binding and actual subtitles.srt equality.")
    parser.add_argument("--strict-exit", action="store_true", help="Return non-zero when the QA report has blocking rules.")
    parser.add_argument("--json", action="store_true", help="Print QA JSON.")
    args = parser.parse_args(argv)

    report = write_source_speech_subtitle_qa_for_run(
        args.run,
        require_approved_text_binding=args.require_approved_text_binding,
    )
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"source_speech_subtitle_qa pass={report['pass']} run={args.run}")
    return 1 if args.strict_exit and report["blocking"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
