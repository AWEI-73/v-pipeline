"""Write Soundtrack Arranger artifacts from a brief or video_intent file."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.soundtrack_arranger import write_soundtrack_artifacts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input brief/video_intent JSON.")
    parser.add_argument("--out-dir", required=True, help="Run folder or output directory.")
    parser.add_argument("--json", action="store_true", help="Print summary JSON.")
    args = parser.parse_args()

    payload = json.loads(Path(args.input).read_text(encoding="utf-8-sig"))
    artifacts = write_soundtrack_artifacts(payload, args.out_dir)
    summary = {
        "ok": True,
        "out_dir": str(Path(args.out_dir)),
        "ready_for_audio_director": artifacts["audio_director_handoff"]["ready_for_audio_director"],
        "blocks": artifacts["audio_director_handoff"]["blocks"],
        "artifacts": [
            "soundtrack_plan.json",
            "music_source_candidates.json",
            "sound_license_manifest.json",
            "audio_director_handoff.json",
        ],
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            "soundtrack_arranger "
            f"ready_for_audio_director={summary['ready_for_audio_director']} "
            f"blocks={','.join(summary['blocks']) or 'none'}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
