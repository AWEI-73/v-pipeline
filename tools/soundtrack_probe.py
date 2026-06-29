#!/usr/bin/env python
"""CLI for building soundtrack_probe_report.json."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.soundtrack_probe import build_soundtrack_probe


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build agent-readable soundtrack_probe_report.json")
    parser.add_argument("--audio", required=True, help="audio file to inspect")
    parser.add_argument("--out", required=True, help="soundtrack_probe_report.json output")
    parser.add_argument("--ffmpeg", default="ffmpeg")
    parser.add_argument("--ffprobe", default="ffprobe")
    parser.add_argument("--enable-asr", action="store_true", help="run optional faster-whisper vocal/transcript analysis")
    parser.add_argument("--asr-model", default="small", help="faster-whisper model name when --enable-asr is set")
    parser.add_argument("--language", default=None, help="optional ASR language code, or auto")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    payload = build_soundtrack_probe(
        args.audio,
        ffprobe=args.ffprobe,
        ffmpeg=args.ffmpeg,
        enable_asr=args.enable_asr,
        asr_model=args.asr_model,
        language=args.language,
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"[soundtrack_probe] wrote {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
