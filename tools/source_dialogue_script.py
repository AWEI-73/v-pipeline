"""CLI for building source_transcript.json and dialogue_edit_script.json."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.source_dialogue_script import write_dialogue_edit_script  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json3", required=True, help="yt-dlp json3 subtitle file")
    parser.add_argument("--out-dir", required=True, dest="out_dir", help="output directory")
    parser.add_argument("--rough-windows", default=None, help="optional rough dialogue_highlight_windows.json")
    parser.add_argument("--target-sec", type=float, default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = write_dialogue_edit_script(
        args.json3,
        out_dir=args.out_dir,
        rough_windows_path=args.rough_windows,
        target_sec=args.target_sec,
    )
    summary = {
        "artifact_role": result["artifact_role"],
        "dialogue_edit_script": str(Path(args.out_dir) / "dialogue_edit_script.json"),
        "source_transcript": str(Path(args.out_dir) / "source_transcript.json"),
        "dialogue_highlight_windows": str(Path(args.out_dir) / "dialogue_highlight_windows.json"),
        "planned_duration_sec": result.get("planned_duration_sec"),
        "clip_count": result.get("clip_count"),
        "next_action": result.get("next_action"),
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"dialogue_edit_script clips={summary['clip_count']} "
            f"planned={summary['planned_duration_sec']}s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
