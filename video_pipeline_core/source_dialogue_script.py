"""Correct-transcript and sentence-safe dialogue highlight script helpers."""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any


_PAREN_ONLY = re.compile(r"^\s*[\(\[].*[\)\]]\s*$")
_END_PUNCT = (".", "?", "!", "\u3002", "\uff1f", "\uff01")


def _clean_text(value: str) -> str:
    return " ".join(str(value or "").replace("\n", " ").split())


def _cue_text(event: dict[str, Any]) -> str:
    return _clean_text("".join(str(seg.get("utf8") or "") for seg in event.get("segs") or []))


def import_json3_transcript(path: str | Path) -> dict[str, Any]:
    payload = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    cues = []
    for event in payload.get("events") or []:
        text = _cue_text(event)
        if not text or _PAREN_ONLY.match(text):
            continue
        start = float(event.get("tStartMs") or 0) / 1000.0
        end = start + float(event.get("dDurationMs") or 0) / 1000.0
        if end <= start:
            continue
        cues.append({
            "cue_id": f"cue_{len(cues) + 1:04d}",
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "text": text,
        })

    sentence_units = []
    current: list[dict[str, Any]] = []
    for cue in cues:
        if current and float(cue["start_sec"]) - float(current[-1]["end_sec"]) > 1.25:
            sentence_units.append(_merge_sentence(current, len(sentence_units) + 1))
            current = []
        current.append(cue)
        if cue["text"].rstrip().endswith(_END_PUNCT):
            sentence_units.append(_merge_sentence(current, len(sentence_units) + 1))
            current = []
    if current:
        sentence_units.append(_merge_sentence(current, len(sentence_units) + 1))

    return {
        "artifact_role": "source_transcript",
        "version": 1,
        "source": str(Path(path).resolve()),
        "source_format": "yt_dlp_json3",
        "cues": cues,
        "sentence_units": sentence_units,
        "limitations": [
            "Subtitle source may still contain recognition errors; user/agent should review important names and terms.",
            "Sentence units preserve spoken timing and avoid half-sentence cuts; they are not a summary by themselves.",
        ],
    }


def _merge_sentence(cues: list[dict[str, Any]], index: int) -> dict[str, Any]:
    return {
        "sentence_id": f"sent_{index:03d}",
        "start_sec": round(float(cues[0]["start_sec"]), 3),
        "end_sec": round(float(cues[-1]["end_sec"]), 3),
        "duration_sec": round(float(cues[-1]["end_sec"]) - float(cues[0]["start_sec"]), 3),
        "text": _clean_text(" ".join(str(cue.get("text") or "") for cue in cues)),
        "cue_ids": [cue["cue_id"] for cue in cues],
    }


def _overlaps(unit: dict[str, Any], start: float, end: float) -> bool:
    return float(unit["end_sec"]) > start and float(unit["start_sec"]) < end


def build_dialogue_edit_script(
    transcript: dict[str, Any],
    *,
    rough_windows: dict[str, Any] | list[dict[str, Any]] | None = None,
    target_sec: float | None = None,
) -> dict[str, Any]:
    units = [u for u in transcript.get("sentence_units") or [] if isinstance(u, dict)]
    windows = rough_windows.get("windows") if isinstance(rough_windows, dict) else rough_windows
    windows = windows if isinstance(windows, list) else []

    selected: list[dict[str, Any]] = []
    seen = set()
    for window in windows:
        try:
            start = float(window.get("start"))
            end = float(window.get("end"))
        except (TypeError, ValueError, AttributeError):
            continue
        for unit in units:
            if not _overlaps(unit, start, end):
                continue
            sentence_id = unit.get("sentence_id")
            if sentence_id in seen:
                continue
            selected.append({
                **unit,
                "selection_label": str(window.get("label") or sentence_id),
                "selection_reason": "rough window expanded to complete sentence",
            })
            seen.add(sentence_id)

    if not selected:
        selected = units[:]

    clips = []
    timeline = 0.0
    for index, unit in enumerate(selected, 1):
        duration = round(float(unit["end_sec"]) - float(unit["start_sec"]), 3)
        if target_sec and clips and timeline + duration > float(target_sec) * 1.25:
            break
        clips.append({
            "segment_id": f"dlg_{index:02d}",
            "source_in_sec": round(float(unit["start_sec"]), 3),
            "source_out_sec": round(float(unit["end_sec"]), 3),
            "timeline_in_sec": round(timeline, 3),
            "duration_sec": duration,
            "sentence_ids": [unit.get("sentence_id")],
            "subtitle_text": unit.get("text"),
            "selection_label": unit.get("selection_label"),
            "selection_reason": unit.get("selection_reason"),
        })
        timeline += duration

    windows_payload = {
        "artifact_role": "dialogue_highlight_windows",
        "version": 1,
        "audio_policy": "preserve_original_dialogue_audio_no_bgm",
        "windows": [
            {
                "start": clip["source_in_sec"],
                "end": clip["source_out_sec"],
                "label": clip["selection_label"] or clip["segment_id"],
                "subtitle_text": clip["subtitle_text"],
            }
            for clip in clips
        ],
    }
    return {
        "artifact_role": "dialogue_edit_script",
        "version": 1,
        "target_duration_sec": target_sec,
        "planned_duration_sec": round(timeline, 3),
        "clip_count": len(clips),
        "clips": clips,
        "dialogue_highlight_windows": windows_payload,
        "next_action": "review_dialogue_edit_script_then_cut",
        "limitations": [
            "This artifact protects sentence boundaries; semantic ordering still needs agent/user review.",
            "Do not force exact target duration if it breaks sentence completeness or flow.",
        ],
    }


def write_dialogue_edit_script(
    json3_path: str | Path,
    *,
    out_dir: str | Path,
    rough_windows_path: str | Path | None = None,
    target_sec: float | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    transcript = import_json3_transcript(json3_path)
    rough = {}
    if rough_windows_path:
        rough = json.loads(Path(rough_windows_path).read_text(encoding="utf-8-sig"))
    script = build_dialogue_edit_script(transcript, rough_windows=rough, target_sec=target_sec)
    (out / "source_transcript.json").write_text(json.dumps(transcript, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "dialogue_edit_script.json").write_text(json.dumps(script, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "dialogue_highlight_windows.json").write_text(
        json.dumps(script["dialogue_highlight_windows"], ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return script
