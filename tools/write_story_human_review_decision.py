"""Write story_human_review_decision.json for a scripted delivery run."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required artifact: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def _required_beat_ids(story_contract: dict[str, Any]) -> list[str]:
    beats = story_contract.get("required_story_beats") or story_contract.get("beats") or []
    out: list[str] = []
    if not isinstance(beats, list):
        return out
    for item in beats:
        if not isinstance(item, dict):
            continue
        beat_id = str(item.get("beat_id") or item.get("id") or item.get("name") or "").strip()
        if beat_id and beat_id not in out:
            out.append(beat_id)
    return out


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _build_decision(args: argparse.Namespace) -> dict[str, Any]:
    run = Path(args.run)
    story_contract = _load_json(run / "story_contract.json")
    required_beats = _required_beat_ids(story_contract)
    decision = str(args.decision or "").strip()
    reviewer = str(args.reviewer or "").strip()
    notes = [str(item).strip() for item in (args.note or []) if str(item).strip()]
    rejected = [str(item).strip() for item in (args.rejected_beat_id or []) if str(item).strip()]
    explicit_approved = [
        str(item).strip()
        for item in (args.approved_beat_id or [])
        if str(item).strip()
    ]

    if reviewer.casefold() != "human":
        raise ValueError("story human review decision requires --reviewer human")

    approved: list[str] = []
    if decision == "approved":
        approved = list(required_beats) if args.approve_all else explicit_approved
        missing = sorted(set(required_beats) - set(approved))
        if missing:
            raise ValueError("approved decision does not cover required story beats: " + ", ".join(missing))
    elif decision == "revision_requested":
        if not notes:
            raise ValueError("revision_requested requires at least one --note")
    elif decision == "rejected":
        if not notes and not rejected:
            raise ValueError("rejected requires at least one --note or --rejected-beat-id")
    else:
        raise ValueError(f"unsupported decision: {decision}")

    return {
        "artifact_role": "story_human_review_decision",
        "version": 1,
        "decision": decision,
        "reviewer": reviewer,
        "reviewed_artifacts": {
            "story_contract": "story_contract.json",
            "story_to_material_map": "story_to_material_map.json",
            "story_to_final_alignment_report": "story_to_final_alignment_report.json",
        },
        "approved_beat_ids": approved,
        "revision_notes": notes,
        "rejected_beat_ids": rejected,
        "created_at": args.created_at or _now_iso(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="scripted delivery run folder")
    parser.add_argument(
        "--decision",
        required=True,
        choices=["approved", "revision_requested", "rejected"],
        help="human story review decision",
    )
    parser.add_argument("--reviewer", required=True, help="must be human for delivery decisions")
    parser.add_argument("--approve-all", action="store_true", help="approve every required story beat")
    parser.add_argument("--approved-beat-id", action="append", default=[], help="approved required beat id")
    parser.add_argument("--note", action="append", default=[], help="revision or rejection note")
    parser.add_argument("--rejected-beat-id", action="append", default=[], help="rejected beat id")
    parser.add_argument("--created-at", default="", help="override created_at timestamp")
    parser.add_argument("--out-name", default="story_human_review_decision.json", help="output artifact name")
    parser.add_argument("--json", action="store_true", help="print JSON summary")
    args = parser.parse_args(argv)

    try:
        decision = _build_decision(args)
        out_name = Path(args.out_name)
        if out_name.is_absolute() or out_name.name != args.out_name:
            raise ValueError("--out-name must be a run-local file name, not a path")
        out_path = Path(args.run) / out_name
        out_path.write_text(json.dumps(decision, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    summary = {
        "ok": True,
        "artifact": str(out_path),
        "decision": decision["decision"],
        "reviewer": decision["reviewer"],
        "approved_beat_count": len(decision["approved_beat_ids"]),
        "revision_note_count": len(decision["revision_notes"]),
        "rejected_beat_count": len(decision["rejected_beat_ids"]),
    }
    print(json.dumps(summary if args.json else decision, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
