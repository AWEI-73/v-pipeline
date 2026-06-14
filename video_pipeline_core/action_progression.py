"""Tier-2 action-progression audit and deterministic shot-function classifier.

The 2026-06-13 replay reported action_phase_coverage = 0.0 because shot
functions were only ever populated by agent caption review, never by a
fallback. This module supplies a deterministic caption+motion classifier so
retrieval can tag every window, and an audit that fails course/action segments
missing their function spine (establish -> action -> result).
"""
from __future__ import annotations

import json
import re
from pathlib import Path


FUNCTIONS = ("establish", "action", "detail", "result", "reaction")

# Bilingual keyword cues. Order matters: earlier wins on ties handled by score.
_KEYWORDS = {
    "establish": ("establish", "wide", "aerial", "landscape", "overview", "venue",
                  "全景", "空拍", "遠景", "場域", "場地", "校門", "建立", "鳥瞰", "外觀"),
    "action": ("action", "operate", "climb", "pull", "drill", "lift", "run", "work",
               "操作", "攀爬", "施工", "拉", "敲", "搬", "作業", "演練", "動作", "練習", "奔跑"),
    "detail": ("close", "closeup", "close-up", "hand", "tool", "detail", "macro",
               "特寫", "手部", "工具", "細節", "近景", "局部", "螺絲"),
    "result": ("result", "finish", "complete", "done", "success", "achievement",
               "完成", "成果", "結果", "成功", "達成", "證書", "頒"),
    "reaction": ("reaction", "smile", "laugh", "applause", "cheer", "expression",
                 "反應", "表情", "笑", "掌聲", "歡呼", "合影", "互看", "感動"),
}


def classify_function(caption, *, motion_peaks=None, duration_sec=0.0):
    """Best-effort deterministic shot-function label. Returns None if unknown."""
    text = str(caption or "").lower()
    scores = {fn: 0 for fn in FUNCTIONS}
    for fn, cues in _KEYWORDS.items():
        for cue in cues:
            if cue in text:
                scores[fn] += 1
    best = max(scores, key=lambda fn: scores[fn])
    if scores[best] > 0:
        return best
    # No caption cue: fall back to motion/duration heuristics.
    peak_count = len(motion_peaks or [])
    if peak_count >= 2:
        return "action"
    if duration_sec and float(duration_sec) >= 4.0 and peak_count == 0:
        return "establish"
    return None


def _clip_function(clip):
    explicit = clip.get("function") or clip.get("shot_function")
    if explicit:
        return str(explicit)
    return classify_function(
        clip.get("caption"),
        motion_peaks=clip.get("motion_peaks"),
        duration_sec=clip.get("duration_sec") or clip.get("extract_dur") or 0.0,
    )


def audit_action_progression(segments, *, min_coverage=0.6, spine=("establish", "action", "result")):
    """Audit segments that declare required_functions for phase coverage."""
    reviewed = []
    findings = []
    total_required = 0
    total_covered = 0
    for segment in segments or []:
        grammar = segment.get("sequence_grammar") or {}
        required = list(grammar.get("required_functions") or [])
        if not required:
            continue
        present = set()
        ordered = []
        for clip in segment.get("clips") or []:
            fn = _clip_function(clip)
            if fn:
                present.add(fn)
                ordered.append(fn)
        covered = [fn for fn in required if fn in present]
        missing = [fn for fn in required if fn not in present]
        total_required += len(required)
        total_covered += len(covered)
        coverage = round(len(covered) / len(required), 4) if required else 1.0
        sid = segment.get("segment")
        reviewed.append({
            "segment": sid, "required": required, "covered": covered,
            "missing": missing, "coverage": coverage,
        })
        missing_spine = [fn for fn in spine if fn in required and fn not in present]
        if coverage < float(min_coverage) or missing_spine:
            findings.append({
                "check": "action_phase_coverage", "level": "fail",
                "segment": sid, "coverage": coverage, "missing": missing,
                "missing_spine": missing_spine,
                "message": (f"segment {sid} action progression incomplete: "
                            f"missing {missing or missing_spine}"),
                "fix_class": "material", "next_route": "curator",
            })
        required_spine = [fn for fn in spine if fn in required]
        if not missing_spine and required_spine:
            cursor = 0
            for fn in ordered:
                if cursor < len(required_spine) and fn == required_spine[cursor]:
                    cursor += 1
            if cursor < len(required_spine):
                findings.append({
                    "check": "action_phase_order", "level": "fail",
                    "segment": sid, "required_order": required_spine,
                    "observed_order": ordered,
                    "message": f"segment {sid} action phases are present but out of order",
                    "fix_class": "edit", "next_route": "editor",
                })
    overall = round(total_covered / total_required, 4) if total_required else None
    next_action = None
    if findings:
        next_action = (
            "editor" if all(item.get("check") == "action_phase_order" for item in findings)
            else "curator"
        )
    result = {
        "artifact_role": "action_progression_audit",
        "version": 1,
        "pass": not findings,
        "metrics": {
            "action_phase_coverage": overall,
            "segments_reviewed": len(reviewed),
        },
        "segments": reviewed,
        "findings": findings,
        "next_action": next_action,
    }
    if not total_required:
        result["reason"] = "no_required_functions"
    return result


def write_action_progression_audit(segments, out_path, **kwargs):
    result = audit_action_progression(segments, **kwargs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return {"ok": True, "action_progression_audit": str(path), "result": result}
