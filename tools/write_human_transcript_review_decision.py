"""Write human_transcript_review_decision.json for a run."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.human_transcript_review_decision import write_human_transcript_review_decision_for_run


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="Run directory to write human_transcript_review_decision.json into.")
    parser.add_argument("--decision", choices=["approved", "revision_requested", "rejected"])
    parser.add_argument("--reviewer", help="Must be human for approval or routing decisions.")
    parser.add_argument("--reviewed-draft", default="subtitles.draft.srt", help="Reviewed draft subtitle artifact.")
    parser.add_argument("--reviewed-cue-id", action="append", default=[], help="Reviewed cue id; required for approved.")
    parser.add_argument("--note", action="append", default=[], help="Required for revision_requested or rejected.")
    parser.add_argument("--payload-file", help="UTF-8 JSON payload for the existing transcript review decision writer.")
    parser.add_argument("--out-name", default="human_transcript_review_decision.json")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args()

    try:
        if args.payload_file:
            payload = json.loads(Path(args.payload_file).read_text(encoding="utf-8-sig"))
            if not isinstance(payload, dict):
                raise ValueError("payload file must contain a JSON object")
        else:
            if not args.decision or not args.reviewer:
                parser.error("--decision and --reviewer are required without --payload-file")
            payload = {
                "decision": args.decision,
                "reviewer": args.reviewer,
                "reviewed_draft": args.reviewed_draft,
                "reviewed_cue_ids": args.reviewed_cue_id,
                "note": args.note,
            }
        decision = write_human_transcript_review_decision_for_run(
            args.run,
            payload,
            out_name=args.out_name,
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    summary = {
        "ok": True,
        "artifact": decision["path"],
        "decision": decision["decision"],
        "reviewer": decision["reviewer"],
        "clears_human_transcript_review": decision["clears_human_transcript_review"],
        "reviewed_cue_count": len(decision["reviewed_cue_ids"]),
        "note_count": len(decision["notes"]),
    }
    print(json.dumps(summary if args.json else decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
