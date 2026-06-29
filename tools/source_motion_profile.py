"""CLI for building source_motion_profile.json from one long source video."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.mv_cut import detect_shots  # noqa: E402
from video_pipeline_core.source_motion_profile import build_source_motion_profile  # noqa: E402


def _load_energy_curve(path: str | None) -> list[dict]:
    if not path:
        return []
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    features = payload.get("features") if isinstance(payload, dict) else {}
    curve = features.get("energy_curve") if isinstance(features, dict) else []
    return curve if isinstance(curve, list) else []


def _shot_boundaries(shots: list[tuple[float, float]]) -> list[float]:
    values = set()
    for start, end in shots or []:
        if end > start:
            values.add(round(float(start), 3))
            values.add(round(float(end), 3))
    return sorted(values)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--video", required=True, help="single long source video")
    parser.add_argument("--out-dir", required=True, dest="out_dir", help="output directory")
    parser.add_argument("--soundtrack-probe", default=None, help="optional source_soundtrack_probe_report.json")
    parser.add_argument("--start-sec", type=float, default=0.0)
    parser.add_argument("--end-sec", type=float, default=None)
    parser.add_argument("--sample-sec", type=float, default=1.0)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    shots = detect_shots(args.video)
    result = build_source_motion_profile(
        args.video,
        out_dir=args.out_dir,
        audio_curve=_load_energy_curve(args.soundtrack_probe),
        shot_boundaries=_shot_boundaries(shots),
        start_sec=args.start_sec,
        end_sec=args.end_sec,
        sample_sec=args.sample_sec,
    )
    summary = {
        "artifact_role": result["artifact_role"],
        "source_motion_profile": str(Path(args.out_dir) / "source_motion_profile.json"),
        "sample_count": result.get("sample_count"),
        "ranked_edit_point_count": len(result.get("ranked_edit_points") or []),
        "motion_points_sheet": str(Path(args.out_dir) / "source_motion_points.jpg"),
    }
    if args.json:
        print(json.dumps(summary, ensure_ascii=False, indent=2))
    else:
        print(
            f"source_motion_profile samples={summary['sample_count']} "
            f"ranked={summary['ranked_edit_point_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
