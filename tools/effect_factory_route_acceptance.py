"""Run Effect Factory semantic-to-worker route acceptance without final render."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.effect_factory_route_acceptance import (  # noqa: E402
    run_effect_factory_route_acceptance,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Effect Factory route acceptance: semantic request to reviewed worker handoff.",
    )
    parser.add_argument("--out", "--run-dir", dest="run_dir", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--effect-role", required=True)
    parser.add_argument("--duration-sec", type=float, default=4.0)
    parser.add_argument("--display-text", default="Opening")
    parser.add_argument("--subtitle-text", default="")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    report = run_effect_factory_route_acceptance(
        args.run_dir,
        request=args.request,
        effect_role=args.effect_role,
        duration_sec=args.duration_sec,
        display_text=args.display_text,
        subtitle_text=args.subtitle_text,
    )

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            "effect_factory_route_acceptance "
            f"ok={report.get('ok')} "
            f"failed_stage={report.get('failed_stage')} "
            f"next_action={report.get('next_action')}"
        )
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
