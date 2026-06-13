"""Deterministic M4 same-case replay metrics and acceptance checks."""
from __future__ import annotations

import json
from pathlib import Path

from .broll_audit import audit_broll
from .new_visual_information_audit import audit_new_visual_information


def _clips(timeline):
    return timeline if isinstance(timeline, list) else (timeline or {}).get("clips") or []


def _gate_pass(payload):
    if not isinstance(payload, dict):
        return False
    if "ready_for_build" in payload:
        return bool(payload["ready_for_build"])
    return bool(payload.get("pass"))


def build_replay_report(timeline, *, gate_artifacts=None, judge_verdicts=None,
                        jumpcut_plan=None, new_visual_audit=None,
                        adaptation_decisions=None):
    clips = _clips(timeline)
    total_clips = len(clips)
    short_count = sum(1 for item in clips if float(item.get("duration_sec") or 0) <= 2.0)
    broll = audit_broll(timeline)
    nvi = new_visual_audit or audit_new_visual_information(timeline)
    action = [item for item in clips if item.get("beat_alignment") == "action"]
    aligned = [item for item in action if item.get("adjustment_reason") == "motion_phase"]
    gates = gate_artifacts or {}
    verdicts = judge_verdicts or []
    jumpcut_applicable = bool((jumpcut_plan or {}).get("requires_review"))
    jumpcut_count = 1 if (jumpcut_plan or {}).get("approved") else 0
    jumpcut_check = (
        "pass" if jumpcut_applicable and jumpcut_count
        else "fail" if jumpcut_applicable
        else "not_applicable"
    )
    adaptation = adaptation_decisions or {}
    duration_check = "pass" if adaptation.get("duration") == "shortened" else "unproven"
    chapter_check = "pass" if adaptation.get("chapters") == "reduced" else "unproven"
    checks = {
        "tier1_gates": "pass" if gates and all(_gate_pass(v) for v in gates.values()) else "fail",
        "judge_lineage": "pass" if verdicts and all(
            item.get("decision") == "accept" for item in verdicts) else "fail",
        "new_visual_information": "pass" if nvi.get("pass") else "fail",
        "jumpcut_when_applicable": jumpcut_check,
        "duration_adaptation": duration_check,
        "chapter_adaptation": chapter_check,
    }
    return {
        "artifact_role": "m4_replay_acceptance",
        "version": 1,
        "pass": all(value in ("pass", "not_applicable") for value in checks.values()),
        "metrics": {
            "shot_le_2s_ratio": round(short_count / total_clips, 4) if total_clips else 0.0,
            "unique_source_ratio": broll["metrics"]["unique_source_ratio"],
            "max_source_repeats": broll["metrics"]["max_source_repeats"],
            "new_visual_information_ratio": nvi["metrics"]["new_visual_information_ratio"],
            "action_phase_coverage": round(len(aligned) / len(action), 4) if action else 0.0,
            "sound_bite_count": sum(1 for item in clips if item.get("keep_audio")),
            "jumpcut_count": jumpcut_count,
        },
        "checks": checks,
        "judge_verdicts": verdicts,
        "adaptation_decisions": adaptation,
    }


def write_replay_report(timeline, out_path, **kwargs):
    result = build_replay_report(timeline, **kwargs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
