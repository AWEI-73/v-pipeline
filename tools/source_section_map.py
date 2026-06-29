"""CLI for building source_section_map.json from one long source video."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.keyframe_grid import probe_duration  # noqa: E402
from video_pipeline_core.mv_cut import detect_shots  # noqa: E402
from video_pipeline_core.source_section_map import write_source_section_map  # noqa: E402


def _load_energy_curve(path: str | None) -> list[dict]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    features = payload.get("features") if isinstance(payload, dict) else {}
    curve = features.get("energy_curve") if isinstance(features, dict) else []
    return curve if isinstance(curve, list) else []


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, help="single long source video")
    parser.add_argument("--out", required=True, help="source_section_map.json output")
    parser.add_argument("--soundtrack-probe", default=None, help="optional source_soundtrack_probe_report.json")
    parser.add_argument("--target-section-sec", type=float, default=80.0)
    parser.add_argument("--min-section-sec", type=float, default=24.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    duration_sec = probe_duration(args.video)
    shots = detect_shots(args.video)
    result = write_source_section_map(
        args.out,
        duration_sec=duration_sec,
        energy_curve=_load_energy_curve(args.soundtrack_probe),
        shots=shots,
        target_section_sec=args.target_section_sec,
        min_section_sec=args.min_section_sec,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"source_section_map sections={len(result.get('sections') or [])} "
            f"boundaries={len(result.get('boundaries') or [])}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
