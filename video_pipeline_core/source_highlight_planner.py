"""Plan single-source highlight windows from timeline/audio evidence."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable

from .platform_tools import resolve_ffprobe


def _probe_duration(source: str | Path) -> float:
    result = subprocess.run(
        [
            resolve_ffprobe(),
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "json",
            str(source),
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout)
    return float((payload.get("format") or {}).get("duration") or 0.0)


def _load_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}
    data = json.loads(p.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else {}


def _energy_lookup(soundtrack_probe: dict[str, Any]) -> list[dict[str, Any]]:
    features = soundtrack_probe.get("features") if isinstance(soundtrack_probe, dict) else {}
    curve = features.get("energy_curve") if isinstance(features, dict) else []
    return [item for item in curve if isinstance(item, dict)]


def _matrix_window_lookup(source_material_matrix: dict[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not isinstance(source_material_matrix, dict):
        return {}
    windows = source_material_matrix.get("windows") or []
    return {
        str(item.get("window_id")): item
        for item in windows
        if isinstance(item, dict) and item.get("window_id")
    }


def _avg_energy(curve: list[dict[str, Any]], start: float, end: float) -> float:
    values = []
    for item in curve:
        try:
            item_start = float(item.get("start_sec"))
            item_end = float(item.get("end_sec"))
            energy = float(item.get("relative_energy"))
        except (TypeError, ValueError):
            continue
        if item_end <= start or item_start >= end:
            continue
        values.append(energy)
    return round(sum(values) / len(values), 3) if values else 0.0


def _role_for_window(start: float, end: float, duration: float, energy: float) -> str:
    midpoint = (start + end) / 2.0
    ratio = midpoint / duration if duration > 0 else 0.0
    if ratio < 0.12:
        return "opening"
    if ratio > 0.86:
        return "ending"
    if energy >= 0.42:
        return "practice_highlight"
    if ratio < 0.30:
        return "setup"
    if ratio > 0.70:
        return "reflection_or_closing_setup"
    return "practice_or_training"


def _tags_for_role(role: str) -> list[str]:
    mapping = {
        "opening": ["opening", "intro", "title"],
        "setup": ["setup", "context"],
        "practice_or_training": ["practice", "training", "internship"],
        "practice_highlight": ["practice", "training", "internship", "highlight", "high_energy"],
        "reflection_or_closing_setup": ["reflection", "closing_setup"],
        "ending": ["ending", "closing"],
    }
    return mapping.get(role, [role])


def build_source_timeline_map(
    source: str | Path,
    *,
    soundtrack_probe: dict[str, Any] | None = None,
    source_material_matrix: dict[str, Any] | None = None,
    window_sec: float = 12.0,
    hop_sec: float | None = None,
    duration_probe: Callable[[str | Path], float] | None = None,
) -> dict[str, Any]:
    source = str(Path(source).resolve())
    duration = float((duration_probe or _probe_duration)(source))
    hop = float(hop_sec or window_sec)
    curve = _energy_lookup(soundtrack_probe or {})
    matrix_by_window = _matrix_window_lookup(source_material_matrix)
    windows: list[dict[str, Any]] = []
    start = 0.0
    index = 0
    while start < duration:
        end = min(start + float(window_sec), duration)
        if end - start < 3.0 and windows:
            windows[-1]["end_sec"] = round(end, 3)
            windows[-1]["duration_sec"] = round(windows[-1]["end_sec"] - windows[-1]["start_sec"], 3)
            break
        energy = _avg_energy(curve, start, end)
        role = _role_for_window(start, end, duration, energy)
        window_id = f"win_{index:03d}"
        matrix_window = matrix_by_window.get(window_id) or {}
        visual = matrix_window.get("visual") if isinstance(matrix_window, dict) else {}
        selection = matrix_window.get("selection") if isinstance(matrix_window, dict) else {}
        visual = visual if isinstance(visual, dict) else {}
        selection = selection if isinstance(selection, dict) else {}
        visual_tags = []
        visual_tags.extend(str(item) for item in (visual.get("usable_for") or []) if item)
        if visual.get("content_type"):
            visual_tags.append(str(visual.get("content_type")))
        tags = list(dict.fromkeys([*_tags_for_role(role), *visual_tags]))
        windows.append(
            {
                "window_id": window_id,
                "source_path": source,
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "duration_sec": round(end - start, 3),
                "midpoint_sec": round((start + end) / 2.0, 3),
                "audio_energy": energy,
                "timeline_role": role,
                "selection_tags": tags,
                "visual_review_status": visual.get("review_status"),
                "visual_content_type": visual.get("content_type"),
                "visual_usable_for": visual.get("usable_for") or [],
                "visual_decision": selection.get("decision"),
                "visual_reject_reason": selection.get("reject_reason"),
            }
        )
        index += 1
        if end >= duration:
            break
        start += hop
    return {
        "artifact_role": "source_timeline_map",
        "version": 1,
        "source_path": source,
        "duration_sec": round(duration, 3),
        "window_sec": float(window_sec),
        "hop_sec": hop,
        "analysis_inputs": {
            "soundtrack_probe": bool(soundtrack_probe),
            "source_material_matrix": bool(source_material_matrix),
            "visual_understanding": "reviewed_matrix" if source_material_matrix else "not_run",
        },
        "windows": windows,
        "limitations": [
            "This map uses deterministic timeline/audio evidence unless a reviewed source material matrix is supplied.",
            "A human or VLM reviewer should refine roles when content accuracy matters.",
        ],
    }


def _intent_tokens(intent: str | list[str]) -> set[str]:
    if isinstance(intent, list):
        text = " ".join(str(item) for item in intent)
    else:
        text = str(intent or "")
    lower = text.lower()
    tokens = set(lower.replace("/", " ").replace(",", " ").split())
    zh_map = {
        "\u5be6\u7fd2": "internship",
        "\u5be6\u4f5c": "practice",
        "\u9805\u76ee": "practice",
        "\u8a13\u7df4": "training",
        "\u7cbe\u83ef": "highlight",
        "\u7d50\u5c3e": "ending",
        "\u6536\u5c3e": "ending",
        "\u958b\u5834": "opening",
        "\u97f3\u6a02": "music",
        "\u91cd\u88dc": "refill",
    }
    for zh, token in zh_map.items():
        if zh in text:
            tokens.add(token)
    return tokens


def _score_window(window: dict[str, Any], tokens: set[str], index: int) -> float:
    tags = set(window.get("selection_tags") or [])
    role = str(window.get("timeline_role") or "")
    score = float(window.get("audio_energy") or 0.0)
    if tags.intersection(tokens):
        score += 1.0
    if {"practice", "training", "internship"}.intersection(tokens) and "practice" in tags:
        score += 1.2
    if "ending" in tokens and "ending" in tags:
        score += 1.5
    if "opening" in tokens and "opening" in tags:
        score += 0.9
    if role == "practice_highlight":
        score += 0.3
    if str(window.get("visual_decision") or "").lower() == "keep":
        score += 2.0
    if set(window.get("visual_usable_for") or []).intersection(tokens):
        score += 1.4
    return round(score - index * 0.001, 4)


def build_highlight_selection_plan(
    timeline_map: dict[str, Any],
    *,
    intent: str | list[str] = "",
    target_sec: float = 90.0,
    clip_sec: float = 10.0,
) -> dict[str, Any]:
    tokens = _intent_tokens(intent)
    windows = [
        w for w in timeline_map.get("windows") or []
        if isinstance(w, dict) and str(w.get("visual_decision") or "").lower() != "reject"
    ]
    selected: list[dict[str, Any]] = []

    def add_best(predicate: Callable[[dict[str, Any]], bool], reason: str) -> None:
        candidates = [(i, w) for i, w in enumerate(windows) if predicate(w)]
        if not candidates:
            return
        candidates.sort(key=lambda pair: _score_window(pair[1], tokens, pair[0]), reverse=True)
        chosen = candidates[0][1]
        if chosen.get("window_id") not in {item.get("window_id") for item in selected}:
            item = dict(chosen)
            item["selection_reason"] = reason
            if str(item.get("visual_decision") or "").lower() == "keep":
                item["selection_reason"] += " from reviewed material matrix"
            selected.append(item)

    add_best(lambda w: "opening" in (w.get("selection_tags") or []), "include opening context")
    add_best(lambda w: "practice" in (w.get("selection_tags") or []), "include practice/internship highlight")
    add_best(lambda w: str(w.get("timeline_role")) == "practice_highlight", "include highest-energy practice section")
    add_best(lambda w: "ending" in (w.get("selection_tags") or []), "include ending/closing")

    selected_ids = {item.get("window_id") for item in selected}
    remaining = [w for w in windows if w.get("window_id") not in selected_ids]
    remaining.sort(key=lambda w: _score_window(w, tokens, windows.index(w)), reverse=True)
    max_clips = max(1, int(float(target_sec) // float(clip_sec)))
    role_caps = {
        "opening": 1,
        "ending": 2,
        "reflection_or_closing_setup": 2,
    }
    for window in remaining:
        if len(selected) >= max_clips:
            break
        role = str(window.get("timeline_role") or "")
        role_cap = role_caps.get(role)
        if role_cap is not None:
            current = sum(1 for item in selected if item.get("timeline_role") == role)
            if current >= role_cap:
                continue
        item = dict(window)
        item["selection_reason"] = "fill target duration with best matching remaining window"
        if str(item.get("visual_decision") or "").lower() == "keep":
            item["selection_reason"] += " from reviewed material matrix"
        selected.append(item)

    selected.sort(key=lambda w: float(w.get("start_sec") or 0.0))
    clips = []
    timeline = 0.0
    for index, window in enumerate(selected[:max_clips], 1):
        start = float(window["start_sec"])
        available = float(window["end_sec"]) - start
        duration = min(float(clip_sec), available)
        clips.append(
            {
                "segment_id": f"seg{index:02d}_{window.get('timeline_role')}",
                "segment": index,
                "track": "video",
                "source_path": timeline_map.get("source_path"),
                "source_in_sec": round(start, 3),
                "source_out_sec": round(start + duration, 3),
                "timeline_in_sec": round(timeline, 3),
                "duration_sec": round(duration, 3),
                "role": window.get("timeline_role"),
                "window_id": window.get("window_id"),
                "visual_decision": window.get("visual_decision"),
                "visual_content_type": window.get("visual_content_type"),
                "selection_reason": window.get("selection_reason"),
            }
        )
        timeline += duration

    return {
        "artifact_role": "highlight_selection_plan",
        "version": 1,
        "target_duration_sec": float(target_sec),
        "clip_duration_sec": float(clip_sec),
        "planned_duration_sec": round(timeline, 3),
        "intent_tokens": sorted(tokens),
        "selected_window_ids": [clip["window_id"] for clip in clips],
        "clips": clips,
        "rough_cut_plan": {
            "artifact_role": "rough_cut_plan",
            "version": 1,
            "route": "single_source_highlight",
            "source_path": timeline_map.get("source_path"),
            "target_duration_sec": float(target_sec),
            "planned_duration_sec": round(timeline, 3),
            "audio_policy": {
                "mode": "replace_or_refill_music_pending_audio_director",
                "reason": "highlight selection was driven by practice/ending intent; music can be rebuilt after cut review",
            },
            "clips": clips,
            "gaps": [],
            "review_notes": [
                "Generated from source_timeline_map, not hand-picked timestamps.",
                "Reviewed source material matrix labels are used when present; otherwise deterministic audio/timeline evidence is used.",
            ],
        },
    }


def write_source_highlight_plan(
    source: str | Path,
    *,
    out_dir: str | Path,
    soundtrack_probe_path: str | Path | None = None,
    source_material_matrix_path: str | Path | None = None,
    intent: str | list[str] = "",
    target_sec: float = 90.0,
    window_sec: float = 12.0,
    clip_sec: float = 10.0,
    duration_probe: Callable[[str | Path], float] | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    soundtrack_probe = _load_json(soundtrack_probe_path)
    source_material_matrix = _load_json(source_material_matrix_path)
    timeline_map = build_source_timeline_map(
        source,
        soundtrack_probe=soundtrack_probe,
        source_material_matrix=source_material_matrix,
        window_sec=window_sec,
        hop_sec=window_sec,
        duration_probe=duration_probe,
    )
    selection = build_highlight_selection_plan(
        timeline_map,
        intent=intent,
        target_sec=target_sec,
        clip_sec=clip_sec,
    )
    (out / "source_timeline_map.json").write_text(
        json.dumps(timeline_map, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "highlight_selection_plan.json").write_text(
        json.dumps(selection, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out / "rough_cut_plan.json").write_text(
        json.dumps(selection["rough_cut_plan"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "ok": True,
        "source_timeline_map": str(out / "source_timeline_map.json"),
        "highlight_selection_plan": str(out / "highlight_selection_plan.json"),
        "rough_cut_plan": str(out / "rough_cut_plan.json"),
        "planned_duration_sec": selection["planned_duration_sec"],
        "selected_window_ids": selection["selected_window_ids"],
    }
