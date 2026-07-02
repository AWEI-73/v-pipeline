"""Accept subtitle/voiceover evidence into a no-render BUILD handoff."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.subtitle_voiceover_handoff import accept_subtitle_voiceover_handoff_files


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--contract", required=True, help="subtitle_voiceover_contract.json or equivalent Stage 0 contract")
    parser.add_argument("--caption-audit", default=None, help="caption_audit.json")
    parser.add_argument("--narration-manifest", default=None, help="narration_manifest.json")
    parser.add_argument("--voiceover-provider-plan", default=None, help="voiceover_provider_plan.json")
    parser.add_argument("--voxcpm-runtime-check", default=None, help="voxcpm_runtime_check.json")
    parser.add_argument("--subtitles", default=None, help="subtitles.srt")
    parser.add_argument("--out-dir", required=True, help="run folder for handoff artifacts")
    parser.add_argument("--json", action="store_true", help="print result JSON")
    args = parser.parse_args()

    result = accept_subtitle_voiceover_handoff_files(
        args.contract,
        caption_audit_path=args.caption_audit,
        narration_manifest_path=args.narration_manifest,
        voiceover_provider_plan_path=args.voiceover_provider_plan,
        voxcpm_runtime_check_path=args.voxcpm_runtime_check,
        subtitles_path=args.subtitles,
        out_dir=args.out_dir,
    )
    ok = result["subtitle_voiceover_handoff_acceptance"].get("ok") is True
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            "subtitle_voiceover_handoff_accept "
            f"ok={str(ok).lower()} "
            f"next={result['subtitle_voiceover_handoff_acceptance'].get('next_action')}"
        )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
