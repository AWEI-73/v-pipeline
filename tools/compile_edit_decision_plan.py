from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.edit_decision_plan import write_product_artifacts  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compile product-facing edit/audio/effect/subtitle decisions from existing branch handoffs."
    )
    parser.add_argument("--run", required=True, help="Run folder containing rough cut and branch handoffs.")
    parser.add_argument("--json", action="store_true", help="Print JSON summary.")
    args = parser.parse_args(argv)

    try:
        artifacts = write_product_artifacts(args.run)
        root = Path(args.run)
        summary = {
            "ok": True,
            "rendered": False,
            "outputs": {
                "edit_decision_plan": str(root / "edit_decision_plan.json"),
                "audio_decision_plan": str(root / "audio_decision_plan.json"),
                "effect_decision_plan": str(root / "effect_decision_plan.json"),
                "subtitle_voiceover_decision_plan": str(root / "subtitle_voiceover_decision_plan.json"),
                "build_handoff": str(root / "build_handoff.json"),
            },
            "ready_for_build": artifacts["build_handoff"].get("ready_for_build"),
            "deferred_count": len(artifacts["build_handoff"].get("deferred_items") or []),
        }
    except Exception as exc:
        summary = {
            "ok": False,
            "rendered": False,
            "failed_stage": "compile_edit_decision_plan",
            "error": str(exc),
        }

    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            "compile_edit_decision_plan "
            f"ok={str(summary.get('ok')).lower()} "
            f"ready_for_build={str(summary.get('ready_for_build')).lower()} "
            f"deferred_count={summary.get('deferred_count', 'n/a')}"
        )
    return 0 if summary.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
