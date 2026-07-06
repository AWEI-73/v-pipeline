"""Write delivery_gate.json from a run folder's delivery evidence."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.dashboard_state import load_dashboard_state
from video_pipeline_core.delivery_gate import (
    apply_video_only_delivery_waiver_to_gate,
    evaluate_complete_video_delivery,
)


def _is_complete_delivery_run(root: Path) -> bool:
    return (root / "delivery_requirements.json").is_file() or (root / "final.mp4").is_file()


def _load_json(path: Path) -> dict | None:
    try:
        raw = path.read_bytes()
    except OSError:
        return None
    payload = None
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            payload = json.loads(raw.decode(encoding))
            break
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    if payload is None:
        return None
    return payload if isinstance(payload, dict) else None


def _has_video_candidate(root: Path) -> bool:
    candidate_names = {
        "final.mp4",
        "rough_cut_preview.mp4",
        "rough_cut_storyboard_preview.mp4",
        "dialogue_highlight_cut.mp4",
        "dialogue_highlight_cut_reviewed.mp4",
        "highlight_final_quiet.mp4",
        "highlight_safe.mp4",
        "highlight_final.mp4",
        "verified_preview.mp4",
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
        if not report or report.get("artifact_role") not in {
            "rough_cut_preview_report",
            "rough_cut_storyboard_preview_report",
        }:
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


def _target_length_bounds_sec(value) -> tuple[float | None, float | None]:
    if value is None:
        return None, None
    if isinstance(value, (int, float)):
        seconds = float(value)
        return seconds, seconds
    text = str(value).strip().lower()
    if not text:
        return None, None
    range_match = re.search(
        r"(\d+(?:\.\d+)?)\s*(?:-|–|~|to)\s*(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m)\b",
        text,
    )
    if range_match:
        low = float(range_match.group(1))
        high = float(range_match.group(2))
        unit = range_match.group(3)
        multiplier = 60.0 if unit.startswith(("m", "min")) else 1.0
        return low * multiplier, high * multiplier
    single_match = re.search(r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|s|minutes?|mins?|m)\b", text)
    if single_match:
        seconds = float(single_match.group(1))
        unit = single_match.group(2)
        if unit.startswith(("m", "min")):
            seconds *= 60.0
        return seconds, seconds
    return None, None


def _preview_report_duration_sec(report: dict) -> float | None:
    duration = report.get("duration_sec") or report.get("planned_duration_sec")
    if duration is None:
        probe = report.get("output_probe") if isinstance(report.get("output_probe"), dict) else {}
        fmt = probe.get("format") if isinstance(probe.get("format"), dict) else {}
        duration = fmt.get("duration")
    try:
        return float(duration)
    except (TypeError, ValueError):
        return None


def _review_preview_duration_sec(root: Path) -> float | None:
    for report_path in root.rglob("*.json"):
        report = _load_json(report_path)
        if not report or report.get("artifact_role") not in {
            "rough_cut_preview_report",
            "rough_cut_storyboard_preview_report",
        }:
            continue
        if report.get("ok") is not True:
            continue
        duration = _preview_report_duration_sec(report)
        if duration is not None:
            return duration
    return None


def _preview_duration_target_block(root: Path) -> dict | None:
    intent = _load_json(root / "video_intent.json")
    if not intent:
        return None
    min_target, _max_target = _target_length_bounds_sec(intent.get("target_length"))
    if min_target is None or min_target <= 0:
        return None
    duration = _review_preview_duration_sec(root)
    if duration is None:
        return None
    if duration + 0.5 >= min_target:
        return None
    return {
        "rule": "preview_duration_below_stage0_target",
        "artifact": "rough_cut_preview_report.json",
        "message": (
            f"rough cut preview is {duration:.1f}s, below Stage 0 target minimum "
            f"{min_target:.1f}s"
        ),
        "preview_duration_sec": duration,
        "target_min_duration_sec": min_target,
        "next_action": "extend_or_rebuild_preview_to_target_length",
    }


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
        elif gate.get("pass") is True:
            duration_block = _preview_duration_target_block(root)
            if duration_block:
                gate = dict(gate)
                blocking = list(gate.get("blocking") or [])
                blocking.append(duration_block)
                gate["pass"] = False
                gate["blocking"] = blocking
                gate["next_action"] = duration_block["next_action"]
        gate = apply_video_only_delivery_waiver_to_gate(root, gate)
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
