"""CLI for building source_material_matrix.json from one long source video."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.source_material_matrix import build_source_material_matrix  # noqa: E402


def _load_review(path: str | None) -> dict | None:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="source video")
    parser.add_argument("--out-dir", required=True, dest="out_dir", help="run/output directory")
    parser.add_argument("--window-sec", type=float, default=12.0)
    parser.add_argument("--visual-review", default=None, help="optional source_material_matrix_review.json")
    parser.add_argument("--soundtrack-probe", default=None, help="optional precomputed source_soundtrack_probe_report.json")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    result = build_source_material_matrix(
        args.source,
        out_dir=args.out_dir,
        window_sec=args.window_sec,
        visual_review=_load_review(args.visual_review),
        soundtrack_probe_path=args.soundtrack_probe,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"source_material_matrix windows={len(result.get('windows') or [])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
