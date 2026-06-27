"""Execute audio_mix_plan.json into final_audio.wav without rendering video."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.audio_mix_plan_executor import execute_audio_mix_plan_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--plan", required=True, help="audio_mix_plan.json")
    parser.add_argument("--acceptance", default=None, help="audio_handoff_acceptance.json")
    parser.add_argument("--out-dir", required=True, help="run folder for final_audio.wav and audio_mix_report.json")
    parser.add_argument("--output-name", default="final_audio.wav", help="output audio filename")
    parser.add_argument("--ffmpeg", default=None, help="optional ffmpeg executable")
    parser.add_argument("--ffprobe", default=None, help="optional ffprobe executable")
    parser.add_argument("--json", action="store_true", help="print result JSON")
    args = parser.parse_args()

    try:
        result = execute_audio_mix_plan_files(
            args.plan,
            acceptance_path=args.acceptance,
            out_dir=args.out_dir,
            output_name=args.output_name,
            ffmpeg=args.ffmpeg,
            ffprobe=args.ffprobe,
        )
    except Exception as exc:
        result = {"ok": False, "failed_stage": "audio_mix_plan", "error": str(exc)}
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 2

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "audio_mix_plan_execute "
            f"ok={str(result.get('ok')).lower()} "
            f"output={result.get('final_audio') or 'none'}"
        )
    return 0 if result.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
