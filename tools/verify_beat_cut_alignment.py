"""Verify intended montage cuts against a declared soundtrack beat grid."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from video_pipeline_core.beat_cut_composer import (  # noqa: E402
    BeatCutCompositionError,
    write_beat_cut_alignment_report,
)


def _load_json(path: Path) -> dict:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise BeatCutCompositionError(f"{path} must contain a JSON object")
    return payload


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--timeline", required=True)
    parser.add_argument("--beats", required=True)
    parser.add_argument("--window-start", required=True, type=float)
    parser.add_argument("--window-end", required=True, type=float)
    parser.add_argument("--fps", required=True, type=float)
    parser.add_argument("--out", required=True)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        report = write_beat_cut_alignment_report(
            _load_json(Path(args.timeline)),
            _load_json(Path(args.beats)),
            window_start=args.window_start,
            window_end=args.window_end,
            fps=args.fps,
            out_path=args.out,
        )
    except (OSError, ValueError, BeatCutCompositionError) as exc:
        report = {
            "artifact_role": "beat_cut_alignment_report",
            "version": 1,
            "pass": False,
            "error": str(exc),
        }
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("pass") is True else 1


if __name__ == "__main__":
    raise SystemExit(main())
