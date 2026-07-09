"""Voiceover lead-in mismatch QA."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


EXTRA_LEADIN_TOKENS = ("抗", "康", "看我們", "看我们")
SIMPLE_TRAD_MAP = str.maketrans({
    "这": "這",
    "们": "們",
    "练": "練",
    "顺": "順",
    "进": "進",
    "阶": "階",
    "压": "壓",
    "变": "變",
    "节": "節",
    "个": "個",
})


def _as_list(value: Any) -> list[Any]:
    if isinstance(value, list):
        return value
    if value is None:
        return []
    return [value]


def _text(value: Any) -> str:
    return str(value or "").strip()


def normalize_text(value: Any) -> str:
    text = _text(value).translate(SIMPLE_TRAD_MAP)
    return re.sub(r"[\s\W_]+", "", text, flags=re.UNICODE).casefold()


def _load_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError):
        return None


def _expected_segments(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    source = payload.get("expected_segments")
    if source is None and isinstance(payload.get("narration_manifest"), Mapping):
        source = payload["narration_manifest"].get("segments")
    out = []
    for index, item in enumerate(_as_list(source), start=1):
        if not isinstance(item, Mapping):
            continue
        out.append({
            "segment_id": _text(item.get("segment_id") or item.get("id") or f"seg{item.get('index') or index:02d}"),
            "expected_text": _text(item.get("text") or item.get("expected_text") or item.get("script_text")),
        })
    return out


def _asr_segments(payload: Mapping[str, Any]) -> list[dict[str, str]]:
    source = payload.get("asr_segments")
    if source is None and isinstance(payload.get("voiceover_output_probe"), Mapping):
        source = payload["voiceover_output_probe"].get("segments")
    out = []
    for item in _as_list(source):
        if not isinstance(item, Mapping):
            continue
        seg_id = _text(item.get("segment_id") or item.get("id") or item.get("audio_ref"))
        text = _text(item.get("recognized_text") or item.get("text") or item.get("asr_text") or item.get("transcript"))
        if seg_id and text:
            out.append({"segment_id": seg_id, "recognized_text": text})
    return out


def _find_extra_leadin(expected_norm: str, recognized_norm: str) -> str:
    for token in EXTRA_LEADIN_TOKENS:
        token_norm = normalize_text(token)
        if recognized_norm.startswith(token_norm) and not expected_norm.startswith(token_norm):
            return token
    if expected_norm and not recognized_norm.startswith(expected_norm[: min(4, len(expected_norm))]):
        idx = recognized_norm.find(expected_norm[: min(4, len(expected_norm))])
        if 0 < idx <= 6:
            return recognized_norm[:idx]
    return ""


def evaluate_voiceover_leadin_qa(payload: Mapping[str, Any] | None) -> dict[str, Any]:
    data = payload if isinstance(payload, Mapping) else {}
    expected = _expected_segments(data)
    asr = _asr_segments(data)
    blocking: list[dict[str, Any]] = []
    results: list[dict[str, Any]] = []

    if not expected:
        blocking.append({
            "rule": "expected_script_missing",
            "tier": 1,
            "message": "voiceover lead-in QA requires expected narration script/manifests",
            "next_action": "provide_narration_manifest",
        })
    if not asr:
        blocking.append({
            "rule": "independent_asr_missing",
            "tier": 1,
            "message": "voiceover lead-in QA requires independent ASR recognized text",
            "next_action": "run_independent_voiceover_asr",
        })

    asr_by_segment: dict[str, str] = {}
    for segment in asr:
        asr_by_segment.setdefault(segment["segment_id"], "")
        asr_by_segment[segment["segment_id"]] = (asr_by_segment[segment["segment_id"]] + " " + segment["recognized_text"]).strip()

    for item in expected:
        segment_id = item["segment_id"]
        expected_text = item["expected_text"]
        recognized_text = asr_by_segment.get(segment_id, "")
        if not recognized_text:
            blocking.append({
                "rule": "segment_independent_asr_missing",
                "tier": 1,
                "segment_id": segment_id,
                "message": "expected voiceover segment has no matching independent ASR evidence",
                "next_action": "run_independent_voiceover_asr",
            })
        expected_norm = normalize_text(expected_text)
        recognized_norm = normalize_text(recognized_text)
        extra = _find_extra_leadin(expected_norm, recognized_norm) if recognized_norm else ""
        item_result = {
            "segment_id": segment_id,
            "expected_text": expected_text,
            "recognized_asr_text": recognized_text,
            "normalized_expected_prefix": expected_norm[:16],
            "normalized_recognized_prefix": recognized_norm[:16],
            "detected_extra_leadin": extra,
            "pass": not extra and bool(recognized_text),
            "next_action": None if not extra and recognized_text else "repair_voiceover_leadin",
        }
        results.append(item_result)
        if extra:
            blocking.append({
                "rule": "voiceover_extra_leadin",
                "tier": 1,
                "segment_id": segment_id,
                "expected_text": expected_text,
                "recognized_asr_text": recognized_text,
                "normalized_expected_prefix": item_result["normalized_expected_prefix"],
                "normalized_recognized_prefix": item_result["normalized_recognized_prefix"],
                "detected_extra_leadin": extra,
                "message": "recognized voiceover starts with an extra token/phrase before expected narration",
                "next_action": "repair_voiceover_leadin",
            })

    return {
        "artifact_role": "voiceover_leadin_qa",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "segments": results,
        "checked_segment_count": len(results),
        "detected_leadin_mismatches": [item for item in results if item["detected_extra_leadin"]],
        "next_action": None if not blocking else blocking[0]["next_action"],
    }


def write_voiceover_leadin_qa_for_run(run: str | Path, out_name: str = "voiceover_leadin_qa.json") -> dict[str, Any]:
    root = Path(run)
    manifest = _load_json(root / "narration_manifest.json")
    probe = _load_json(root / "voiceover_output_probe.json")
    report = evaluate_voiceover_leadin_qa({
        "narration_manifest": manifest if isinstance(manifest, Mapping) else None,
        "voiceover_output_probe": probe if isinstance(probe, Mapping) else None,
    })
    report["run"] = str(root)
    (root / out_name).write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return report
