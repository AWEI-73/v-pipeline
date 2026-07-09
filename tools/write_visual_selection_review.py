"""Write visual_selection_review.json from visual-selection candidates."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.visual_selection_gate import build_visual_selection_candidates_from_run
from video_pipeline_core.visual_selection_review_decision import write_visual_selection_review


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing candidates file: {path}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"candidates file is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("candidates file must contain a JSON object")
    return data


def _candidate_items(candidates: dict[str, Any]) -> list[dict[str, Any]]:
    raw = candidates.get("selections") or candidates.get("items") or []
    return [item for item in raw if isinstance(item, dict)]


def _beat_id(item: dict[str, Any]) -> str:
    return str(item.get("beat_id") or item.get("module_id") or item.get("section_id") or "").strip()


def _fixture_decisions(candidates: dict[str, Any], fixture: str) -> list[dict[str, Any]]:
    decisions: list[dict[str, Any]] = []
    for item in _candidate_items(candidates):
        beat = _beat_id(item)
        if not beat:
            continue
        if fixture == "accepted-valid":
            decision = {
                "beat_id": beat,
                "decision": "accepted",
                "reviewer_type": "agent_visual_review",
                "candidate_source": "agent_visual_review",
                "representative_frame": f"visual_selection_frames/{beat}.jpg",
                "reason": f"fixture accepted visual evidence for {beat}",
                "forbidden_role_flags_checked": True,
                "forbidden_role_flags": {
                    "supervisor_primary": False,
                    "director_primary": False,
                    "portrait_primary": False,
                },
            }
            if beat == "supervisor_source_speech":
                decision.update({
                    "video_evidence": True,
                    "audio_evidence": True,
                    "speech_evidence": True,
                    "reason": "fixture accepted talking-head supervisor source-speech evidence",
                })
        elif fixture == "rejected":
            decision = {
                "beat_id": beat,
                "decision": "rejected",
                "reviewer_type": "agent_visual_review",
                "reason": f"fixture rejected visual selection for {beat}",
            }
        elif fixture == "needs-repick":
            decision = {
                "beat_id": beat,
                "decision": "needs_repick",
                "reviewer_type": "agent_visual_review",
                "reason": f"fixture needs repick for {beat}",
            }
        else:
            raise ValueError(f"unsupported fixture: {fixture}")
        decisions.append(decision)
    if not decisions:
        raise ValueError("no visual-selection candidates found")
    return decisions


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run", help="Read-only run directory to build visual-selection candidates from.")
    source.add_argument("--candidates", help="visual_selection_candidates.json path.")
    parser.add_argument("--out-dir", help="Output directory. Required unless --write-to-run is used.")
    parser.add_argument("--write-to-run", action="store_true", help="Write visual_selection_review.json into --run.")
    parser.add_argument("--fixture", choices=["accepted-valid", "rejected", "needs-repick"], required=True)
    parser.add_argument("--created-at", default="", help="Override created_at timestamp.")
    parser.add_argument("--json", action="store_true", help="Print summary JSON.")
    args = parser.parse_args(argv)

    try:
        if args.run:
            run = Path(args.run)
            candidates = build_visual_selection_candidates_from_run(run)
            if args.write_to_run:
                out_dir = run
            elif args.out_dir:
                out_dir = Path(args.out_dir)
            else:
                raise ValueError("--out-dir is required unless --write-to-run is set")
        else:
            candidates = _load_json(Path(args.candidates))
            if not args.out_dir:
                raise ValueError("--out-dir is required with --candidates")
            out_dir = Path(args.out_dir)

        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "visual_selection_candidates.json").write_text(
            json.dumps(candidates, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        decisions = _fixture_decisions(candidates, args.fixture)
        review_path, review, gate = write_visual_selection_review(
            candidates,
            decisions,
            out_dir,
            created_at=args.created_at,
        )
    except ValueError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2

    summary = {
        "ok": True,
        "artifact": str(review_path),
        "fixture": args.fixture,
        "reviewed_count": review["summary"]["reviewed_count"],
        "gate_pass": gate["pass"],
        "gate_blocking_rules": [item["rule"] for item in gate["blocking"]],
        "is_final_story_approval": review["is_final_story_approval"],
        "is_legal_music_approval": review["is_legal_music_approval"],
    }
    print(json.dumps(summary if args.json else review, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
