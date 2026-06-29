"""Write delivery_gate.json from a run folder's delivery evidence."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.dashboard_state import load_dashboard_state
from video_pipeline_core.delivery_gate import evaluate_complete_video_delivery


def _is_complete_delivery_run(root: Path) -> bool:
    return (root / "delivery_requirements.json").is_file() or (root / "final.mp4").is_file()


def write_delivery_gate_report(run_dir: str | Path, out_name: str = "delivery_gate.json") -> dict:
    root = Path(run_dir)
    if _is_complete_delivery_run(root):
        gate = evaluate_complete_video_delivery(root)
        report_source = "complete_video_delivery_gate"
    else:
        state = load_dashboard_state(str(root))
        gate = (state.get("artifacts") or {}).get("delivery_gate")
        report_source = "dashboard_state.artifacts.delivery_gate"
        if not isinstance(gate, dict):
            gate = {
                "artifact_role": "delivery_gate",
                "version": 1,
                "pass": False,
                "blocking": [{
                    "rule": "delivery_gate_unavailable",
                    "artifact": "dashboard_state",
                    "message": "dashboard state did not provide delivery_gate",
                    "next_action": "repair_dashboard_state_or_delivery_gate",
                }],
                "next_action": "repair_dashboard_state_or_delivery_gate",
            }
    gate = dict(gate)
    gate["generated_by"] = "tools/write_delivery_gate_report.py"
    gate["report_source"] = report_source
    out_path = root / out_name
    out_path.write_text(json.dumps(gate, ensure_ascii=False, indent=2), encoding="utf-8")
    return gate


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True, help="run folder")
    parser.add_argument("--out-name", default="delivery_gate.json", help="output filename inside run folder")
    parser.add_argument("--json", action="store_true", help="print delivery gate JSON")
    args = parser.parse_args()

    gate = write_delivery_gate_report(args.run, args.out_name)
    if args.json:
        print(json.dumps(gate, ensure_ascii=False, indent=2))
    else:
        print(
            "delivery_gate "
            f"pass={str(gate.get('pass')).lower()} "
            f"next={gate.get('next_action')}"
        )
    return 0 if gate.get("pass") else 1


if __name__ == "__main__":
    raise SystemExit(main())
