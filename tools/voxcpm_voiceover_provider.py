#!/usr/bin/env python
"""Dedicated VoxCPM voiceover provider wrapper for Hermes.

This is the operator-friendly entrypoint for the local VoxCPM repo under
``reference repo/VoxCPM-main``. It writes the same canonical artifacts as
``video_tools.py voiceover-provider-plan`` so BUILD and delivery gates do not
need provider-specific logic.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from video_pipeline_core.voiceover_provider import (  # noqa: E402
    DEFAULT_VOXCPM_MODEL_ID,
    DEFAULT_VOICE_STYLE,
    VoiceoverProviderError,
    build_voiceover_provider_plan,
    write_voiceover_provider_artifacts,
)


DEFAULT_VOXCPM_REPO = REPO_ROOT / "reference repo" / "VoxCPM-main"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Plan or run local VoxCPM narration and write Hermes voiceover handoff artifacts."
    )
    parser.add_argument("script", help="script.json or segment_contract.json with narration/text")
    parser.add_argument("--out-dir", required=True, help="run/output directory for voiceover artifacts")
    parser.add_argument(
        "--voxcpm-repo",
        default=str(DEFAULT_VOXCPM_REPO),
        help="local VoxCPM repo path; default is reference repo\\VoxCPM-main",
    )
    parser.add_argument(
        "--voxcpm-python",
        help="Python executable for the VoxCPM runtime; env VOXCPM_PYTHON also works",
    )
    parser.add_argument(
        "--voice-style",
        default=DEFAULT_VOICE_STYLE,
        help="VoxCPM control text, e.g. warm clear Mandarin narrator",
    )
    parser.add_argument(
        "--model-id",
        default=DEFAULT_VOXCPM_MODEL_ID,
        help="VoxCPM Hugging Face model id",
    )
    parser.add_argument("--reference-audio", help="optional reference audio for VoxCPM clone mode")
    parser.add_argument("--device", default="auto", help="VoxCPM device: auto/cuda/cpu/cuda:0")
    parser.add_argument("--local-files-only", action="store_true", help="disable model downloads")
    parser.add_argument("--inference-timesteps", type=int, default=10)
    parser.add_argument("--cfg-value", type=float, default=2.0)
    parser.add_argument(
        "--execute",
        action="store_true",
        help="actually run VoxCPM; omitted means artifact planning only",
    )
    parser.add_argument(
        "--allow-legacy-fallback",
        action="store_true",
        help="if the local VoxCPM repo is unavailable, fall back to legacy edge-tts plan",
    )
    parser.add_argument("--timeout-sec", type=int, default=1200)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        payload = build_voiceover_provider_plan(
            script_path=args.script,
            out_dir=args.out_dir,
            provider="voxcpm",
            voice_style=args.voice_style,
            model_id=args.model_id,
            reference_audio=args.reference_audio,
            device=args.device,
            local_files_only=args.local_files_only,
            inference_timesteps=args.inference_timesteps,
            cfg_value=args.cfg_value,
            execute=args.execute,
            allow_fallback=args.allow_legacy_fallback,
            execute_fallback=False,
            voxcpm_repo=args.voxcpm_repo,
            voxcpm_python=args.voxcpm_python,
            timeout_sec=args.timeout_sec,
        )
    except VoiceoverProviderError as exc:
        print(json.dumps({"ok": False, "error": str(exc)}, ensure_ascii=False, indent=2))
        return 2

    written = write_voiceover_provider_artifacts(payload, args.out_dir)
    ok = not bool(payload["plan"].get("errors"))
    print(
        json.dumps(
            {
                "ok": ok,
                "selected_provider": payload["plan"].get("selected_provider"),
                "provider_available": payload["plan"].get("provider_available"),
                "provider_entry_type": payload["plan"].get("provider_entry_type"),
                "provider_repo": payload["plan"].get("provider_repo"),
                "provider_python": payload["plan"].get("provider_python"),
                "voiceover_ready": payload["handoff"].get("voiceover_ready"),
                "execute": args.execute,
                "artifacts": written,
                "error_count": len(payload["plan"].get("errors") or []),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
