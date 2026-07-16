"""Build a dense whole-timeline wall packet for horizontal Reviewer/L5 use."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.timeline_review_packet import build_timeline_review_packet  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, help="rendered rough cut, candidate, or reference film")
    parser.add_argument("--out-dir", required=True, dest="out_dir", help="fresh review packet output directory")
    parser.add_argument(
        "--review-subject-type",
        required=True,
        choices=["current_candidate", "reference_film"],
        dest="review_subject_type",
        help="declare whether observations apply to the current candidate or a non-blocking reference film",
    )
    parser.add_argument("--interval-sec", type=float, default=0.5, dest="interval_sec")
    parser.add_argument("--wall-duration-sec", type=float, default=30.0, dest="wall_duration_sec")
    parser.add_argument("--soundtrack-probe", default=None, dest="soundtrack_probe")
    parser.add_argument("--srt", default=None, help="optional reviewed/draft SRT context")
    parser.add_argument(
        "--text-authority",
        default=None,
        choices=["asr_draft", "owner_approved", "reference_transcript", "ocr_inferred"],
        dest="text_authority",
        help="required provenance class whenever --srt is supplied",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    result = build_timeline_review_packet(
        args.video,
        args.out_dir,
        review_subject_type=args.review_subject_type,
        interval_sec=args.interval_sec,
        wall_duration_sec=args.wall_duration_sec,
        soundtrack_probe_path=args.soundtrack_probe,
        srt_path=args.srt,
        text_authority=args.text_authority,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "timeline_review_packet "
            f"status={result['status']} pages={result['uniform_timeline_wall']['page_count']} "
            f"samples={result['uniform_timeline_wall']['sample_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
