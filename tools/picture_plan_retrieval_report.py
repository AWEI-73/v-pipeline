"""CLI for the picture-plan retrieval/ranking evidence gate."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.picture_plan_retrieval_gate import build_retrieval_ranking_report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--picture-plan", required=True)
    parser.add_argument("--segment-contract", required=True)
    parser.add_argument("--project-map", required=True)
    parser.add_argument("--evidence-map")
    parser.add_argument("--out", required=True)
    parser.add_argument("--top-k", type=int, default=10)
    args = parser.parse_args(argv)

    picture_path = Path(args.picture_plan)
    contract_path = Path(args.segment_contract)
    project_path = Path(args.project_map)
    evidence_path = Path(args.evidence_map) if args.evidence_map else None
    out_path = Path(args.out)
    picture = json.loads(picture_path.read_text(encoding="utf-8-sig"))
    contract = json.loads(contract_path.read_text(encoding="utf-8-sig"))
    project = json.loads(project_path.read_text(encoding="utf-8-sig"))
    evidence = (
        json.loads(evidence_path.read_text(encoding="utf-8-sig"))
        if evidence_path else None
    )
    report = build_retrieval_ranking_report(
        picture_plan=picture,
        segment_contract=contract,
        project_map=project,
        project_map_path=project_path,
        picture_plan_path=picture_path,
        report_path=out_path,
        top_k=args.top_k,
        evidence_map=evidence,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
