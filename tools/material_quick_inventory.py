"""Build material_inventory_summary.json from Stage 0 material_scan_decision."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.material_inventory_summary import write_material_inventory_summary


def _load_decision(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        return {}
    if isinstance(payload.get("material_scan_decision"), dict):
        return dict(payload["material_scan_decision"])
    if payload.get("artifact_role") == "stage0_material_scan_decision":
        return payload
    return {}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", required=True, help="material source folder")
    parser.add_argument("--out", required=True, help="material_inventory_summary.json output")
    parser.add_argument("--video-intent", default="", help="video_intent.json containing material_scan_decision")
    parser.add_argument("--scan-decision", default="", help="standalone stage0_material_scan_decision JSON")
    parser.add_argument("--json", action="store_true", help="print summary JSON")
    args = parser.parse_args(argv)

    decision = _load_decision(args.scan_decision) or _load_decision(args.video_intent)
    payload = write_material_inventory_summary(
        args.source_dir,
        args.out,
        material_scan_decision=decision,
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        counts = payload.get("counts") or {}
        print(
            "material_quick_inventory "
            f"files={counts.get('total_files', 0)} "
            f"videos={counts.get('videos', 0)} "
            f"images={counts.get('images', 0)} "
            f"audio={counts.get('audio', 0)}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
