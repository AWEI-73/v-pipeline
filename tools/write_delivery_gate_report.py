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


def _load_json(path: Path) -> dict | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None
    return payload if isinstance(payload, dict) else None


def _has_video_candidate(root: Path) -> bool:
    candidate_names = {
        "final.mp4",
        "rough_cut_preview.mp4",
        "dialogue_highlight_cut.mp4",
        "dialogue_highlight_cut_reviewed.mp4",
        "highlight_final_quiet.mp4",
        "highlight_safe.mp4",
        "highlight_final.mp4",
    }
    for name in candidate_names:
        path = root / name
        if path.is_file() and path.stat().st_size > 0:
            return True

    for report_path in root.rglob("*.json"):
        report = _load_json(report_path)
        if not report or report.get("artifact_role") != "highlight_cut_report":
            continue
        output = report.get("out") or report.get("output")
        if not output:
            continue
        output_path = Path(str(output))
        if not output_path.is_absolute():
            output_path = root / output_path
        if output_path.is_file() and output_path.stat().st_size > 0:
            return True
    for report_path in root.rglob("*.json"):
        report = _load_json(report_path)
        if not report or report.get("artifact_role") != "rough_cut_preview_report":
            continue
        if report.get("ok") is not True:
            continue
        output = report.get("output_video") or report.get("out")
        if not output:
            continue
        output_path = Path(str(output))
        if not output_path.is_absolute():
            output_path = root / output_path
        if output_path.is_file() and output_path.stat().st_size > 0:
            return True
    return False


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
        elif gate.get("pass") is True and not _has_video_candidate(root):
            gate = dict(gate)
            blocking = list(gate.get("blocking") or [])
            blocking.append({
                "rule": "missing_video_candidate",
                "artifact": "final.mp4",
                "message": "delivery gate cannot pass without final.mp4 or a verified video preview candidate",
                "next_action": "create_or_verify_video_candidate",
            })
            gate["pass"] = False
            gate["blocking"] = blocking
            gate["next_action"] = "create_or_verify_video_candidate"
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
