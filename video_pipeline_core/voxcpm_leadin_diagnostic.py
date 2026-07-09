"""VoxCPM lead-in artifact diagnostic helpers."""

from __future__ import annotations

import json
import subprocess
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from video_pipeline_core.voiceover_leadin_qa import evaluate_voiceover_leadin_qa, normalize_text


CLASSIFICATIONS = {
    "actual_audio_leadin_artifact",
    "asr_false_positive_likely",
    "prompt_or_style_leak",
    "segmentation_or_punctuation_sensitive",
    "transient_provider_process_issue",
    "safe_trim_postprocess_available",
    "provider_blocked_no_safe_fix",
    "insufficient_evidence",
}


@dataclass(frozen=True)
class DiagnosticCase:
    label: str
    text: str
    voice_style: str
    path_mode: str = "normal"
    segments: int = 1

    def as_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "text": self.text,
            "voice_style": self.voice_style,
            "path_mode": self.path_mode,
            "segments": self.segments,
        }


def plan_diagnostic_matrix() -> list[dict[str, Any]]:
    """Return the minimum required provider diagnostic matrix."""
    cases = [
        DiagnosticCase("starts_zhe_yi_tian_calm_ascii_path", "這一天我們開始。", "calm", "ascii"),
        DiagnosticCase("starts_zhe_yi_tian_blank_style", "這一天我們開始。", ""),
        DiagnosticCase("starts_zhe_yi_tian_neutral_style", "這一天我們開始。", "neutral"),
        DiagnosticCase("starts_basic_training_blank_style", "基本訓練開始。", ""),
        DiagnosticCase("starts_basic_training_calm_style", "基本訓練開始。", "calm"),
        DiagnosticCase("starts_basic_training_no_punctuation", "基本訓練開始", "calm"),
        DiagnosticCase("starts_basic_training_chinese_punctuation", "基本訓練，開始。", "calm"),
        DiagnosticCase("starts_basic_training_newline", "基本訓練\n開始。", "calm"),
        DiagnosticCase("starts_basic_training_repeat_1", "基本訓練開始。", "neutral"),
        DiagnosticCase("starts_basic_training_repeat_2", "基本訓練開始。", "neutral"),
        DiagnosticCase("multi_segment_basic_training", "基本訓練開始。", "calm", "normal", 2),
    ]
    return [case.as_dict() for case in cases]


def write_case_script(case: Mapping[str, Any], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    segments = []
    count = int(case.get("segments") or 1)
    for index in range(1, count + 1):
        segments.append({
            "index": index,
            "segment": f"{case.get('label')}_{index}",
            "text": str(case.get("text") or ""),
        })
    script = {
        "artifact_role": "voxcpm_leadin_diagnostic_script",
        "version": 1,
        "label": case.get("label"),
        "segments": segments,
    }
    path = out_dir / "script.json"
    path.write_text(json.dumps(script, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def wav_duration_sec(path: Path) -> float | None:
    try:
        with wave.open(str(path), "rb") as handle:
            frames = handle.getnframes()
            rate = handle.getframerate()
            return round(frames / float(rate), 3) if rate else None
    except (OSError, wave.Error):
        return None


def first_800ms_analysis(asr_text: str, expected_text: str) -> dict[str, Any]:
    recognized_norm = normalize_text(asr_text)
    expected_norm = normalize_text(expected_text)
    first_token = recognized_norm[:1]
    expected_first = expected_norm[:1]
    return {
        "recognized_first_token": first_token,
        "expected_first_token": expected_first,
        "recognized_prefix": recognized_norm[:12],
        "expected_prefix": expected_norm[:12],
        "first_token_matches_expected": bool(first_token and first_token == expected_first),
        "first_800ms_note": "ASR segment-level proxy; no subsecond ASR timestamps available in this diagnostic",
    }


def evaluate_case_leadin(case: Mapping[str, Any], recognized_text: str, segment_id: str = "seg01") -> dict[str, Any]:
    return evaluate_voiceover_leadin_qa({
        "expected_segments": [{"segment_id": segment_id, "text": str(case.get("text") or "")}],
        "asr_segments": [{"segment_id": segment_id, "recognized_text": recognized_text}],
    })


def run_ffmpeg_trim(source: Path, target: Path, offset_ms: int) -> dict[str, Any]:
    target.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-v",
        "error",
        "-ss",
        f"{offset_ms / 1000.0:.3f}",
        "-i",
        str(source),
        str(target),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    return {
        "command": cmd,
        "returncode": proc.returncode,
        "stdout_tail": proc.stdout[-500:],
        "stderr_tail": proc.stderr[-500:],
        "path": str(target),
        "exists": target.exists(),
        "size_bytes": target.stat().st_size if target.exists() else 0,
        "duration_sec": wav_duration_sec(target) if target.exists() else None,
    }


def classify_provider_leadin(matrix_rows: Iterable[Mapping[str, Any]], trim_summary: Mapping[str, Any] | None = None) -> dict[str, Any]:
    rows = list(matrix_rows)
    trim = trim_summary if isinstance(trim_summary, Mapping) else {}
    if not rows:
        classification = "insufficient_evidence"
    elif any(str(row.get("returncode")) not in ("0", "") and row.get("returncode") is not None for row in rows):
        failed = [row for row in rows if row.get("returncode") not in (0, None)]
        classification = "transient_provider_process_issue" if len(failed) < len(rows) else "provider_blocked_no_safe_fix"
    elif trim.get("safe_trim_available") is True:
        classification = "safe_trim_postprocess_available"
    elif any(row.get("lead_in_qa_pass") is False for row in rows):
        labels = {str(row.get("label")) for row in rows if row.get("lead_in_qa_pass") is False}
        if any("punctuation" in label or "newline" in label for label in labels):
            classification = "segmentation_or_punctuation_sensitive"
        else:
            classification = "provider_blocked_no_safe_fix"
    elif any("clear narration" in str(row.get("voice_style", "")).casefold() for row in rows):
        classification = "prompt_or_style_leak"
    else:
        classification = "asr_false_positive_likely"
    if classification not in CLASSIFICATIONS:
        classification = "insufficient_evidence"
    return {
        "artifact_role": "provider_leadin_classification",
        "version": 1,
        "classification": classification,
        "safe_for_production": classification == "safe_trim_postprocess_available",
        "matrix_count": len(rows),
        "blocking_count": sum(1 for row in rows if row.get("lead_in_qa_pass") is False),
        "next_action": "do_not_assemble_final_media" if classification != "safe_trim_postprocess_available" else "prove_postprocess_in_pipeline_before_final",
    }
