"""Tier-1 delivery gates over existing GAP, VERIFY, and render artifacts."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any


HARD_AUDITS = (
    "verify_result",
    "timeline_invariants",
    "broll_audit",
    "caption_audit",
    "new_visual_information_audit",
    "black_frame_audit",
)

DELIVERY_MANIFEST_EVIDENCE_KEYS = (
    "audio_build_handoff",
    "audio_mix_report",
    "effect_handoff",
    "effect_render_verification",
    "frame_evidence",
    "generated_material_review",
    "generated_provider_packet",
    "material_generation_fallback",
    "music_manifest",
    "narration_manifest",
    "project_material_map",
    "remotion_effect_handoff",
    "soundtrack_probe_report",
    "subtitle_voiceover_build_handoff",
    "timeline_build",
    "verify_result",
)

VIDEO_ONLY_DELIVERY_WAIVER_ITEMS = {
    "audio",
    "music",
    "subtitle",
    "narration",
    "soundtrack_license",
}

VIDEO_ONLY_DELIVERY_WAIVABLE_RULES = {
    "missing_audio_stream",
    "audio_video_duration_mismatch",
    "missing_audio_mix_report",
    "audio_mix_report_declares_no_audio",
    "required_audio_ducking_not_applied",
    "audio_mix_peak_too_hot",
    "missing_music_manifest",
    "music_not_mixed",
    "missing_soundtrack_probe_report",
    "soundtrack_probe_not_passed",
    "soundtrack_probe_has_no_features",
    "soundtrack_probe_has_no_sections",
    "soundtrack_probe_has_no_section_fit",
    "soundtrack_probe_has_no_editing_fit",
    "soundtrack_probe_missing_vocal_analysis",
    "vocal_music_conflicts_with_voiceover",
    "missing_narration_manifest",
    "missing_narration_audio_refs",
    "invalid_narration_audio_refs",
    "no_usable_narration_audio",
    "narration_declares_fallback",
    "narration_not_mixed",
    "audio_mix_declares_narration_fallback",
    "missing_subtitles",
    "corrupt_subtitles",
    "subtitle_language_mismatch",
}

VIDEO_ONLY_DELIVERY_RULE_FAMILIES = {
    "missing_audio_stream": "audio",
    "audio_video_duration_mismatch": "audio",
    "missing_audio_mix_report": "audio",
    "audio_mix_report_declares_no_audio": "audio",
    "required_audio_ducking_not_applied": "audio",
    "audio_mix_peak_too_hot": "audio",
    "missing_music_manifest": "music",
    "music_not_mixed": "music",
    "missing_soundtrack_probe_report": "soundtrack_license",
    "soundtrack_probe_not_passed": "soundtrack_license",
    "soundtrack_probe_has_no_features": "soundtrack_license",
    "soundtrack_probe_has_no_sections": "soundtrack_license",
    "soundtrack_probe_has_no_section_fit": "soundtrack_license",
    "soundtrack_probe_has_no_editing_fit": "soundtrack_license",
    "soundtrack_probe_missing_vocal_analysis": "soundtrack_license",
    "vocal_music_conflicts_with_voiceover": "soundtrack_license",
    "missing_narration_manifest": "narration",
    "missing_narration_audio_refs": "narration",
    "invalid_narration_audio_refs": "narration",
    "no_usable_narration_audio": "narration",
    "narration_declares_fallback": "narration",
    "narration_not_mixed": "narration",
    "audio_mix_declares_narration_fallback": "narration",
    "missing_subtitles": "subtitle",
    "corrupt_subtitles": "subtitle",
    "subtitle_language_mismatch": "subtitle",
}

ALLOWED_DELIVERY_MUSIC_SOURCE_TYPES = {
    "user_provided",
    "source_folder_audio",
    "licensed_library",
    "youtube_audio_library",
    "pixabay_music",
    "jamendo_song",
    "suno_udio_external",
    "agentic_music_generation_tool",
}

BLOCKED_DELIVERY_MUSIC_SOURCE_TYPES = {
    "synthetic_generated_audio_bed",
    "placeholder",
    "reference_only",
}


def _validate_video_only_delivery_waiver(root: Path) -> tuple[dict[str, Any] | None, list[str]]:
    path = root / "video_only_delivery_waiver.json"
    waiver = _load_json(path)
    if waiver is None:
        return None, []

    errors: list[str] = []
    if waiver.get("artifact_role") != "video_only_delivery_waiver":
        errors.append("artifact_role must be video_only_delivery_waiver")
    if waiver.get("version") != 1:
        errors.append("version must be 1")
    if waiver.get("scope") != "video_only_delivery":
        errors.append("scope must be video_only_delivery")
    for field in ("reviewer", "reason", "at"):
        value = waiver.get(field)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{field} must be a non-empty string")
    waives = waiver.get("waives")
    if not isinstance(waives, list):
        errors.append("waives must be a list")
        waives = []
    else:
        unknown = sorted({str(item) for item in waives if item not in VIDEO_ONLY_DELIVERY_WAIVER_ITEMS})
        if unknown:
            errors.append("waives contains unsupported item(s): " + ", ".join(unknown))
    limitations = waiver.get("limitations")
    if not isinstance(limitations, list) or not any(isinstance(item, str) and item.strip() for item in limitations):
        errors.append("limitations must include at least one non-empty string")

    if errors:
        return None, errors
    return waiver, []


def _apply_video_only_delivery_waiver(
    root: Path,
    blocking: list[dict[str, Any]],
    warnings: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    waiver, errors = _validate_video_only_delivery_waiver(root)
    if errors:
        warnings.append({
            "rule": "invalid_video_only_delivery_waiver",
            "artifact": "video_only_delivery_waiver.json",
            "message": "; ".join(errors),
        })
        return blocking, [], []
    if waiver is None:
        return blocking, [], []

    waived_families = {str(item) for item in waiver.get("waives") or []}
    remaining: list[dict[str, Any]] = []
    limitations: list[dict[str, Any]] = []
    for finding in blocking:
        rule = finding.get("rule")
        family = VIDEO_ONLY_DELIVERY_RULE_FAMILIES.get(str(rule))
        if rule in VIDEO_ONLY_DELIVERY_WAIVABLE_RULES and family in waived_families:
            limitation = dict(finding)
            limitation["waived_by"] = "video_only_delivery_waiver.json"
            limitation["waiver_family"] = family
            limitations.append(limitation)
        else:
            remaining.append(finding)

    if not limitations:
        return blocking, [], []

    for text in waiver.get("limitations") or []:
        if isinstance(text, str) and text.strip():
            limitations.append({
                "rule": "video_only_delivery_limitation",
                "artifact": "video_only_delivery_waiver.json",
                "message": text.strip(),
                "waived_by": "video_only_delivery_waiver.json",
            })

    applied = [{
        "artifact_role": "video_only_delivery_waiver",
        "artifact": "video_only_delivery_waiver.json",
        "scope": waiver.get("scope"),
        "reviewer": waiver.get("reviewer"),
        "reason": waiver.get("reason"),
        "at": waiver.get("at"),
        "waives": list(waiver.get("waives") or []),
    }]
    return remaining, limitations, applied


def apply_video_only_delivery_waiver_to_gate(root: str | Path, gate: dict[str, Any]) -> dict[str, Any]:
    """Return a delivery gate copy with a valid video-only waiver applied."""
    root = Path(root)
    out = dict(gate)
    blocking = [dict(item) for item in _as_list(out.get("blocking")) if isinstance(item, dict)]
    warnings = [dict(item) for item in _as_list(out.get("warnings")) if isinstance(item, dict)]
    remaining, limitations, applied = _apply_video_only_delivery_waiver(root, blocking, warnings)

    if not applied:
        waiver, errors = _validate_video_only_delivery_waiver(root)
        if waiver is not None and not blocking:
            limitations = [
                {
                    "rule": "video_only_delivery_limitation",
                    "artifact": "video_only_delivery_waiver.json",
                    "message": text.strip(),
                    "waived_by": "video_only_delivery_waiver.json",
                }
                for text in waiver.get("limitations") or []
                if isinstance(text, str) and text.strip()
            ]
            applied = [{
                "artifact_role": "video_only_delivery_waiver",
                "artifact": "video_only_delivery_waiver.json",
                "scope": waiver.get("scope"),
                "reviewer": waiver.get("reviewer"),
                "reason": waiver.get("reason"),
                "at": waiver.get("at"),
                "waives": list(waiver.get("waives") or []),
            }]

    if not applied:
        out["blocking"] = blocking
        out["warnings"] = warnings
        out.setdefault("waivers_applied", [])
        out.setdefault("limitations", [])
        return out

    existing_limitations = [
        dict(item)
        for item in _as_list(out.get("limitations"))
        if isinstance(item, dict)
    ]
    out["blocking"] = remaining
    out["warnings"] = warnings
    out["limitations"] = existing_limitations + limitations
    out["waivers_applied"] = [*(_as_list(out.get("waivers_applied"))), *applied]
    out["pass"] = not remaining
    out["next_action"] = remaining[0].get("next_action") if remaining else None
    return out


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _manifest_artifact_value(manifest: dict[str, Any] | None, key: str) -> Any:
    if not isinstance(manifest, dict):
        return None
    value = manifest.get(key)
    artifacts = manifest.get("artifacts")
    if value is None and isinstance(artifacts, dict):
        value = artifacts.get(key)
    if isinstance(value, dict):
        for field in ("path", "file", "ref", "href"):
            ref = value.get(field)
            if isinstance(ref, str) and ref.strip():
                return ref
    return value


def _artifact_ref(root: Path, key: str, fallback_name: str | None = None) -> Path:
    manifest = _load_json(root / "artifact_manifest.json")
    ref = _manifest_artifact_value(manifest, key)
    if isinstance(ref, str) and ref.strip():
        path = Path(ref)
        return path if path.is_absolute() else root / path
    return root / (fallback_name or f"{key}.json")


def _load_artifact_json(root: Path, key: str, fallback_name: str | None = None) -> dict[str, Any] | None:
    return _load_json(_artifact_ref(root, key, fallback_name))


def _manifest_has_items(manifest: dict[str, Any] | None, *keys: str) -> bool:
    if not isinstance(manifest, dict):
        return False
    for key in keys:
        value = manifest.get(key)
        if isinstance(value, list) and value:
            return True
    return False


def _has_mojibake(text: str) -> bool:
    return "\ufffd" in text or "????" in text


def _has_unreadable_review_text(text: str) -> bool:
    if _has_mojibake(text):
        return True
    private_use_count = sum(1 for char in text if "\ue000" <= char <= "\uf8ff")
    if private_use_count:
        return True
    suspicious_markers = ("嚗", "銝", "蝚", "摰", "頝", "璅", "蝯", "蝺")
    return any(marker in text for marker in suspicious_markers)


def _read_text(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def _json_text_has_mojibake(value: Any) -> bool:
    if isinstance(value, str):
        return _has_mojibake(value)
    if isinstance(value, list):
        return any(_json_text_has_mojibake(item) for item in value)
    if isinstance(value, dict):
        return any(_json_text_has_mojibake(item) for item in value.values())
    return False


def _contains_cjk(text: str) -> bool:
    return any("\u4e00" <= char <= "\u9fff" for char in text)


def _text_payload(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, list):
        return "\n".join(_text_payload(item) for item in value)
    if isinstance(value, dict):
        return "\n".join(_text_payload(item) for item in value.values())
    return ""


def _has_text_corruption(value: Any) -> bool:
    return _has_mojibake(_text_payload(value))


def _scripted_chinese_expected(*values: Any) -> bool:
    text = "\n".join(_text_payload(value) for value in values)
    return _contains_cjk(text) or any(_language_requires_cjk(value) for value in values)


def _language_requires_cjk(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).casefold()
            if isinstance(child, str) and (
                "language" in key_text
                or "locale" in key_text
                or key_text in {"lang", "required_lang"}
            ):
                marker = child.strip().casefold()
                if (
                    marker == "zh"
                    or marker.startswith("zh-")
                    or marker in {"chinese", "mandarin"}
                    or "\u4e2d\u6587" in child
                    or "\u7e41\u9ad4" in child
                ):
                    return True
            if _language_requires_cjk(child):
                return True
    if isinstance(value, list):
        return any(_language_requires_cjk(item) for item in value)
    return False


def _text_items(value: Any) -> list[str]:
    items: list[str] = []
    if isinstance(value, dict):
        for key, child in value.items():
            if key in {"text", "subtitle", "caption", "transcript", "line"} and isinstance(child, str):
                items.append(child)
            else:
                items.extend(_text_items(child))
    elif isinstance(value, list):
        for child in value:
            items.extend(_text_items(child))
    return items


def _expected_language(requirements: dict[str, Any]) -> str | None:
    for key in ("language", "required_language", "subtitle_language", "narration_language"):
        value = requirements.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip().lower()
    return None


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _resolve_ref(root: Path, ref: Any) -> Path | None:
    if not isinstance(ref, str) or not ref.strip():
        return None
    path = Path(ref)
    if not path.is_absolute():
        path = root / path
    return path


def _artifact_manifest_stale_blocks(root: Path, keys: tuple[str, ...]) -> list[dict[str, Any]]:
    manifest = _load_json(root / "artifact_manifest.json")
    if not isinstance(manifest, dict):
        return []
    blocking: list[dict[str, Any]] = []
    for key in keys:
        ref = _manifest_artifact_value(manifest, key)
        if not isinstance(ref, str) or not ref.strip():
            continue
        path = _resolve_ref(root, ref)
        if path is None or path.is_file():
            continue
        blocking.append({
            "rule": "artifact_manifest_stale",
            "tier": 1,
            "artifact": "artifact_manifest.json",
            "manifest_key": key,
            "path": str(path),
            "message": f"artifact_manifest.json points {key} to a missing file",
            "next_action": "repair_artifact_manifest_or_regenerate_evidence",
        })
    return blocking


def _audio_duration(path: Path) -> float | None:
    probe = _probe_media(path)
    if probe.get("ok") is False:
        return None
    return _duration_seconds(probe, "audio") or _duration_seconds(probe)


def _string_contains_any(value: Any, needles: tuple[str, ...]) -> bool:
    if isinstance(value, str):
        lower = value.lower()
        return any(needle in lower for needle in needles)
    if isinstance(value, list):
        return any(_string_contains_any(item, needles) for item in value)
    if isinstance(value, dict):
        return any(_string_contains_any(item, needles) for item in value.values())
    return False


def _audio_mix_report_blocks(audio_mix_report: dict[str, Any]) -> list[dict[str, Any]]:
    blocking: list[dict[str, Any]] = []
    if (
        audio_mix_report.get("preview_only") is True
        or audio_mix_report.get("delivery_allowed") is False
    ):
        blocking.append({
            "rule": "preview_only_audio_not_delivery_allowed",
            "tier": 1,
            "artifact": "audio_mix_report.json",
            "message": "preview-only or non-delivery audio mix cannot pass the final delivery gate",
            "next_action": "review_internal_audio_preview",
        })
    placements = _as_list(audio_mix_report.get("placements"))
    for index, placement in enumerate(placements):
        if not isinstance(placement, dict):
            continue
        if placement.get("ducking_policy") == "duck_under_voice" and placement.get("ducking_applied") is not True:
            blocking.append({
                "rule": "required_audio_ducking_not_applied",
                "tier": 1,
                "artifact": "audio_mix_report.json",
                "message": f"audio placement #{index} requires duck_under_voice but ducking_applied is not true",
                "next_action": "repair_audio_mix_plan_ducking",
            })
    try:
        peak_dbfs = float(audio_mix_report.get("peak_dbfs"))
    except (TypeError, ValueError):
        peak_dbfs = None
    if peak_dbfs is not None and peak_dbfs > -0.5:
        blocking.append({
            "rule": "audio_mix_peak_too_hot",
            "tier": 1,
            "artifact": "audio_mix_report.json",
            "message": f"audio mix peak is too close to clipping ({peak_dbfs:.1f} dBFS)",
            "next_action": "lower_audio_mix_gain_or_limit",
        })
    return blocking


def _soundtrack_probe_report_blocks(
    soundtrack_probe_report: dict[str, Any] | None,
    *,
    required: bool,
    require_vocal_clearance: bool = False,
) -> list[dict[str, Any]]:
    blocking: list[dict[str, Any]] = []
    if soundtrack_probe_report is None:
        if required:
            blocking.append({
                "rule": "missing_soundtrack_probe_report",
                "tier": 1,
                "artifact": "soundtrack_probe_report.json",
                "message": "soundtrack/music delivery requires soundtrack_probe_report.json",
                "next_action": "run_soundtrack_probe",
            })
        return blocking
    if soundtrack_probe_report.get("pass") is not True:
        blocking.append({
            "rule": "soundtrack_probe_not_passed",
            "tier": 1,
            "artifact": "soundtrack_probe_report.json",
            "message": "soundtrack_probe_report.json did not pass",
            "next_action": "repair_or_rerun_soundtrack_probe",
        })
    features = soundtrack_probe_report.get("features")
    if not isinstance(features, dict) or not features:
        blocking.append({
            "rule": "soundtrack_probe_has_no_features",
            "tier": 1,
            "artifact": "soundtrack_probe_report.json",
            "message": "soundtrack_probe_report.json must include non-empty features",
            "next_action": "rerun_soundtrack_probe",
        })
    sections = _as_list(soundtrack_probe_report.get("sections"))
    if not sections:
        blocking.append({
            "rule": "soundtrack_probe_has_no_sections",
            "tier": 1,
            "artifact": "soundtrack_probe_report.json",
            "message": "soundtrack_probe_report.json must include music sections",
            "next_action": "rerun_soundtrack_probe",
        })
    section_fit = _as_list(soundtrack_probe_report.get("section_fit"))
    if required and not section_fit:
        blocking.append({
            "rule": "soundtrack_probe_has_no_section_fit",
            "tier": 1,
            "artifact": "soundtrack_probe_report.json",
            "message": "soundtrack_probe_report.json must include section_fit when soundtrack probing is required",
            "next_action": "rerun_soundtrack_probe",
        })
    editing_fit = soundtrack_probe_report.get("editing_fit")
    if not isinstance(editing_fit, dict) or not editing_fit:
        blocking.append({
            "rule": "soundtrack_probe_has_no_editing_fit",
            "tier": 1,
            "artifact": "soundtrack_probe_report.json",
            "message": "soundtrack_probe_report.json must include editing_fit for video placement decisions",
            "next_action": "rerun_soundtrack_probe",
        })
    if require_vocal_clearance:
        vocal = features.get("vocal_analysis") if isinstance(features, dict) else None
        if not isinstance(vocal, dict) or vocal.get("has_vocals") == "unknown" or vocal.get("method") in (None, "", "not_run"):
            blocking.append({
                "rule": "soundtrack_probe_missing_vocal_analysis",
                "tier": 1,
                "artifact": "soundtrack_probe_report.json",
                "message": "voiceover/speech delivery requires soundtrack_probe vocal_analysis; rerun with --enable-asr",
                "next_action": "run_soundtrack_probe_with_asr",
            })
        elif vocal.get("has_vocals") is True and str(vocal.get("vocal_density") or "").lower() in {"medium", "high"}:
            blocking.append({
                "rule": "vocal_music_conflicts_with_voiceover",
                "tier": 1,
                "artifact": "soundtrack_probe_report.json",
                "message": "selected music has medium/high detected vocals and conflicts with narration or preserved speech",
                "next_action": "select_instrumental_music_or_use_instrumental_window",
            })
    return blocking


def _has_explicit_no_narration_approval(root: Path) -> bool:
    for filename in (
        "no_narration_delivery_approval.json",
        "real_user_no_narration_approval.json",
    ):
        approval = _load_json(root / filename)
        if not isinstance(approval, dict):
            continue
        if approval.get("approved") is True and approval.get("real_user_approval") is True:
            return True
    waiver, errors = _validate_video_only_delivery_waiver(root)
    return waiver is not None and not errors and "narration" in set(waiver.get("waives") or [])


def _music_source_values(music_manifest: dict[str, Any]) -> list[dict[str, Any]]:
    sources: list[dict[str, Any]] = [music_manifest]
    for key in ("tracks", "cues", "sources"):
        for item in _as_list(music_manifest.get(key)):
            if isinstance(item, dict):
                sources.append(item)
    return sources


def _music_ref_name(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    return Path(value.replace("\\", "/")).name.lower()


def _delivery_music_source_blocks(music_manifest: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(music_manifest, dict):
        return []
    blocks: list[dict[str, Any]] = []
    source_items = _music_source_values(music_manifest)
    source_types = {
        str(item.get("source_type") or item.get("source_class") or "").strip()
        for item in source_items
        if str(item.get("source_type") or item.get("source_class") or "").strip()
    }
    blocked_types = sorted(source_types & BLOCKED_DELIVERY_MUSIC_SOURCE_TYPES)
    if blocked_types:
        blocks.append({
            "rule": "synthetic_music_not_delivery_allowed",
            "tier": 1,
            "artifact": "music_manifest.json",
            "message": "complete delivery music cannot be a local synthetic, placeholder, or reference-only bed",
            "source_types": blocked_types,
            "next_action": "select_valid_delivery_music_source",
        })

    refs = {
        _music_ref_name(item.get(key))
        for item in source_items
        for key in ("source_file", "source_ref", "audio_file", "file", "path", "source")
    }
    if "generated_bgm.wav" in refs and not (source_types & ALLOWED_DELIVERY_MUSIC_SOURCE_TYPES):
        blocks.append({
            "rule": "synthetic_music_not_delivery_allowed",
            "tier": 1,
            "artifact": "music_manifest.json",
            "message": "generated_bgm.wav is a local generated bed and cannot satisfy delivery music without valid external/provider/tool evidence",
            "next_action": "select_valid_delivery_music_source",
        })

    if not (source_types & ALLOWED_DELIVERY_MUSIC_SOURCE_TYPES):
        blocks.append({
            "rule": "music_source_unavailable",
            "tier": 1,
            "artifact": "music_manifest.json",
            "message": "delivery music requires a user/source-folder/licensed/provider/agentic music source",
            "next_action": "connect_valid_music_source",
        })
    has_license_or_usage = any(
        item.get("license_note")
        or item.get("license")
        or item.get("usage_license")
        or item.get("usage_notes")
        or item.get("tool_name")
        for item in source_items
    )
    if not has_license_or_usage:
        blocks.append({
            "rule": "music_source_missing_license_metadata",
            "tier": 1,
            "artifact": "music_manifest.json",
            "message": "delivery music source must include license, usage, or generation-tool evidence",
            "next_action": "document_music_source_license_or_usage",
        })
    return blocks


def _clip_source_path(clip: dict[str, Any]) -> str | None:
    for key in (
        "source_path",
        "source",
        "path",
        "file",
        "uri",
        "asset_path",
        "material_path",
        "video_path",
    ):
        value = clip.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    trace = clip.get("trace")
    if isinstance(trace, dict):
        return _clip_source_path(trace)
    material = clip.get("material")
    if isinstance(material, dict):
        return _clip_source_path(material)
    return None


def _source_key(source: str) -> str:
    normalized = source.replace("\\", "/").strip().lower()
    return normalized.rstrip("/")


def _source_label(source: str) -> str:
    normalized = source.replace("\\", "/").strip()
    return normalized.rsplit("/", 1)[-1] or normalized


def _clip_duration_sec(clip: dict[str, Any]) -> float:
    for key in ("duration_sec", "duration", "end_sec"):
        value = clip.get(key)
        try:
            parsed = float(value)
        except (TypeError, ValueError):
            continue
        if key == "end_sec" and clip.get("start_sec") is not None:
            try:
                return max(0.0, parsed - float(clip.get("start_sec")))
            except (TypeError, ValueError):
                return max(0.0, parsed)
        return max(0.0, parsed)
    return 0.0


def _segment_id(value: Any) -> str:
    text = str(value or "").strip()
    if text.endswith(".0"):
        text = text[:-2]
    return text


def _contract_segments_by_id(contract: Any) -> dict[str, dict[str, Any]]:
    if isinstance(contract, dict):
        segments = contract.get("segments") or []
    elif isinstance(contract, list):
        segments = contract
    else:
        segments = []
    out: dict[str, dict[str, Any]] = {}
    for segment in segments:
        if not isinstance(segment, dict):
            continue
        sid = _segment_id(segment.get("segment") or segment.get("id") or segment.get("segment_id"))
        if sid:
            out[sid] = segment
    return out


def _segment_need_refs(segment: dict[str, Any]) -> set[str]:
    material_fit = segment.get("material_fit") or {}
    refs: list[str] = []
    for value in (segment.get("need_ref"), material_fit.get("need_ref")):
        if isinstance(value, str) and value.strip():
            refs.append(value.strip())
    for values in (segment.get("need_refs") or [], material_fit.get("need_refs") or []):
        for value in values:
            if isinstance(value, str) and value.strip():
                refs.append(value.strip())
    return set(refs)


def _segment_material_map_ids(segment: dict[str, Any]) -> set[str]:
    values = segment.get("material_map_ids") or segment.get("asset_ids") or []
    return {str(value).strip() for value in values if isinstance(value, str) and value.strip()}


def _timeline_scene_asset_id(scene_id: Any) -> str:
    return str(scene_id or "").split(":", 1)[0].strip()


def _timeline_clip_asset_id(clip: dict[str, Any]) -> str:
    for key in ("material_map_id", "asset_id"):
        value = clip.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()
    return _timeline_scene_asset_id(clip.get("scene_id"))


def _material_assets(material_map: Any) -> dict[str, dict[str, Any]]:
    if isinstance(material_map, dict) and isinstance(material_map.get("assets"), list):
        raw_assets = material_map.get("assets") or []
    elif isinstance(material_map, list):
        raw_assets = material_map
    elif isinstance(material_map, dict) and material_map.get("asset_id"):
        raw_assets = [material_map]
    else:
        raw_assets = []
    assets: dict[str, dict[str, Any]] = {}
    for asset in raw_assets:
        if not isinstance(asset, dict):
            continue
        asset_id = str(asset.get("asset_id") or "").strip()
        if asset_id:
            assets[asset_id] = asset
    return assets


def _scene_need_from_asset(asset: dict[str, Any] | None, scene_id: Any) -> str | None:
    if not asset:
        return None
    raw_index = str(scene_id or "").split(":", 1)[1:] or [None]
    try:
        index = int(raw_index[0])
    except (TypeError, ValueError):
        index = None
    scenes = asset.get("scenes") or []
    scene = scenes[index] if index is not None and 0 <= index < len(scenes) else {}
    if isinstance(scene, dict):
        for status in ("accepted", "candidate"):
            for edge in scene.get("satisfies") or []:
                if isinstance(edge, dict) and edge.get("status") == status and edge.get("need_id"):
                    return str(edge["need_id"])
                if isinstance(edge, str) and edge.strip():
                    return edge.strip()
        if scene.get("need_id"):
            return str(scene["need_id"])
    if asset.get("need_id"):
        return str(asset["need_id"])
    return None


def _timeline_material_contract_blocks(
    timeline_build: Any,
    segment_contract: Any,
    project_material_map: Any,
) -> list[dict[str, Any]]:
    clips = _timeline_clips(timeline_build)
    if not clips:
        return []
    segments_by_id = _contract_segments_by_id(segment_contract)
    if not segments_by_id:
        return []
    assets = _material_assets(project_material_map)
    blocking: list[dict[str, Any]] = []
    for clip in clips:
        sid = _segment_id(clip.get("segment") or clip.get("segment_id"))
        segment = segments_by_id.get(sid)
        if not segment:
            continue
        scene_id = clip.get("scene_id")
        asset_id = _timeline_clip_asset_id(clip)
        if not asset_id:
            continue
        allowed_asset_ids = _segment_material_map_ids(segment)
        if allowed_asset_ids and asset_id not in allowed_asset_ids:
            blocking.append({
                "rule": "timeline_material_map_id_mismatch",
                "tier": 1,
                "artifact": "timeline_build",
                "segment": clip.get("segment"),
                "scene_id": scene_id,
                "message": (
                    f"timeline clip {scene_id} is not in segment material_map_ids "
                    f"{sorted(allowed_asset_ids)}"
                ),
                "next_action": "revise_material_selection_or_review",
            })
        need_refs = _segment_need_refs(segment)
        actual_need = clip.get("need_id") or clip.get("need_ref") or _scene_need_from_asset(assets.get(asset_id), scene_id)
        if need_refs and actual_need and actual_need not in need_refs:
            blocking.append({
                "rule": "timeline_need_ref_mismatch",
                "tier": 1,
                "artifact": "timeline_build",
                "segment": clip.get("segment"),
                "scene_id": scene_id,
                "message": (
                    f"timeline clip {scene_id} satisfies {actual_need}, "
                    f"not segment need_refs {sorted(need_refs)}"
                ),
                "next_action": "revise_material_selection_or_review",
            })
    return blocking


def _stage0_child_contracts_from_artifacts(artifacts: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(artifacts, dict):
        return {}
    candidates = [
        artifacts.get("segment_contract"),
        artifacts.get("contract"),
        artifacts.get("generated_mv_script"),
        artifacts.get("runtime_payload"),
    ]
    for candidate in candidates:
        if isinstance(candidate, dict):
            direct = candidate.get("stage0_child_contracts")
            if isinstance(direct, dict) and direct:
                return direct
            for segment in candidate.get("segments") or []:
                if isinstance(segment, dict) and isinstance(segment.get("stage0_child_contracts"), dict):
                    return segment["stage0_child_contracts"]
    return {}


def _has_soundtrack_evidence(artifacts: dict[str, Any]) -> bool:
    music_manifest = artifacts.get("music_manifest")
    if _manifest_has_items(music_manifest if isinstance(music_manifest, dict) else None, "tracks", "cues"):
        return True
    audio_mix_report = artifacts.get("audio_mix_report")
    if isinstance(audio_mix_report, dict) and (
        audio_mix_report.get("music_included") is True
        or audio_mix_report.get("audio_stream_present") is True
    ):
        return True
    audio_build_handoff = artifacts.get("audio_build_handoff")
    return isinstance(audio_build_handoff, dict) and bool(audio_build_handoff.get("selected_audio"))


def _has_subtitle_evidence(artifacts: dict[str, Any]) -> bool:
    subtitle_voiceover_handoff = artifacts.get("subtitle_voiceover_build_handoff")
    if isinstance(subtitle_voiceover_handoff, dict) and subtitle_voiceover_handoff.get("subtitle_ready") is True:
        return True
    subtitles = artifacts.get("subtitles") or artifacts.get("subtitles_srt")
    if isinstance(subtitles, str) and subtitles.strip():
        return True
    if isinstance(subtitles, dict) and (subtitles.get("path") or subtitles.get("cue_count")):
        return True
    caption_audit = artifacts.get("caption_audit")
    return isinstance(caption_audit, dict) and caption_audit.get("pass") is True


def _has_voiceover_evidence(artifacts: dict[str, Any]) -> bool:
    subtitle_voiceover_handoff = artifacts.get("subtitle_voiceover_build_handoff")
    if isinstance(subtitle_voiceover_handoff, dict) and subtitle_voiceover_handoff.get("voiceover_ready") is True:
        return True
    narration_manifest = artifacts.get("narration_manifest")
    if _manifest_has_items(narration_manifest if isinstance(narration_manifest, dict) else None, "segments", "clips", "lines"):
        return True
    audio_mix_report = artifacts.get("audio_mix_report")
    return isinstance(audio_mix_report, dict) and audio_mix_report.get("narration_included") is True


def _has_effect_evidence(artifacts: dict[str, Any]) -> bool:
    verification = artifacts.get("effect_render_verification")
    if isinstance(verification, dict) and verification.get("pass") is True and _as_list(verification.get("verified_effects")):
        return True
    review = artifacts.get("effect_review")
    if isinstance(review, dict) and review.get("pass") is True:
        return True
    for key in ("effect_handoff", "remotion_effect_handoff"):
        handoff = artifacts.get(key)
        if isinstance(handoff, dict) and bool(handoff.get("accepted_assets") or handoff.get("assets")):
            return True
    return False


def _stage0_child_contract_blocks(artifacts: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(artifacts, dict):
        return []
    contracts = _stage0_child_contracts_from_artifacts(artifacts)
    if not contracts:
        return []
    blocking: list[dict[str, Any]] = []
    soundtrack = contracts.get("soundtrack") if isinstance(contracts.get("soundtrack"), dict) else {}
    music_role = str(soundtrack.get("music_role") or "").strip().lower()
    if music_role not in {"", "none", "unsure"} and not _has_soundtrack_evidence(artifacts):
        blocking.append({
            "rule": "missing_stage0_soundtrack_evidence",
            "tier": 1,
            "artifact": "stage0_child_contracts.soundtrack",
            "message": f"Stage 0 requested soundtrack role {music_role}, but no music/audio evidence is present",
            "next_action": "resolve_soundtrack_license_or_audio_handoff",
        })
    subtitle_voiceover = (
        contracts.get("subtitle_voiceover")
        if isinstance(contracts.get("subtitle_voiceover"), dict)
        else {}
    )
    if subtitle_voiceover.get("subtitle_required") is True and not _has_subtitle_evidence(artifacts):
        blocking.append({
            "rule": "missing_stage0_subtitle_evidence",
            "tier": 1,
            "artifact": "stage0_child_contracts.subtitle_voiceover",
            "message": "Stage 0 requested subtitles, but no subtitle/caption evidence is present",
            "next_action": "generate_or_verify_subtitles",
        })
    if subtitle_voiceover.get("voiceover_required") is True and not _has_voiceover_evidence(artifacts):
        blocking.append({
            "rule": "missing_stage0_voiceover_evidence",
            "tier": 1,
            "artifact": "stage0_child_contracts.subtitle_voiceover",
            "message": "Stage 0 requested voiceover/narration, but no narration/audio evidence is present",
            "next_action": "generate_or_attach_voiceover",
        })
    effect_policy = contracts.get("effect") if isinstance(contracts.get("effect"), dict) else {}
    effect_required = (
        effect_policy.get("required_now") is True
        or effect_policy.get("activation") == "route_to_effect_factory"
    )
    if effect_required and not _has_effect_evidence(artifacts):
        blocking.append({
            "rule": "missing_stage0_effect_evidence",
            "tier": 1,
            "artifact": "stage0_child_contracts.effect",
            "message": "Stage 0 requested a required effect, but no effect review/render evidence is present",
            "next_action": "verify_or_remove_required_effect",
        })
    return blocking


def _is_finished_master_source(source: str, clip: dict[str, Any]) -> bool:
    role_fields = (
        "source_role",
        "asset_role",
        "asset_type",
        "material_role",
        "category",
        "kind",
    )
    role_text = " ".join(
        str(clip.get(field, ""))
        for field in role_fields
        if clip.get(field) is not None
    ).lower()
    role_markers = (
        "finished_master",
        "final_master",
        "exported_final",
        "rendered_final",
        "edited_video",
        "finished_video",
    )
    if any(marker in role_text for marker in role_markers):
        return True

    name = _source_label(source).lower()
    finished_markers = (
        "finished",
        "master",
        "export",
        "render",
        "final",
        "成片",
        "成品",
        "完成",
        "完稿",
        "正式版",
        "剪輯版",
        "結訓影片",
        "回顧影片",
        "影片-終",
        "-終",
        "_終",
        "終.mp4",
    )
    return any(marker in name for marker in finished_markers)


def _timeline_clips(timeline_build: Any) -> list[dict[str, Any]]:
    if isinstance(timeline_build, list):
        candidates = timeline_build
    elif isinstance(timeline_build, dict):
        candidates = (
            timeline_build.get("clips")
            or timeline_build.get("segments")
            or timeline_build.get("items")
            or []
        )
    else:
        candidates = []
    return [clip for clip in candidates if isinstance(clip, dict)]


def _safe_single_source_highlight(artifacts: Any) -> bool:
    if not isinstance(artifacts, dict):
        return False
    contract = artifacts.get("segment_contract") or artifacts.get("contract") or {}
    highlight_report = artifacts.get("highlight_cut_report") or {}
    if not isinstance(contract, dict) or not isinstance(highlight_report, dict):
        return False
    return (
        contract.get("mode") == "single_source_highlight"
        and highlight_report.get("artifact_role") == "highlight_cut_report"
        and highlight_report.get("strategy") == "safe_reencode_highlight"
        and highlight_report.get("source_artifact") == "rough_cut_plan"
        and highlight_report.get("stream_copy") is False
        and int(highlight_report.get("window_count") or 0) > 0
    )


def _source_quality_blocking(timeline_build: Any, artifacts: Any = None) -> list[dict[str, Any]]:
    clips = _timeline_clips(timeline_build)
    if len(clips) < 2:
        return []
    allow_single_source_highlight = _safe_single_source_highlight(artifacts)

    by_source: dict[str, dict[str, Any]] = {}
    total_duration = 0.0
    for clip in clips:
        source = _clip_source_path(clip)
        if not source:
            continue
        key = _source_key(source)
        duration = _clip_duration_sec(clip)
        total_duration += duration
        entry = by_source.setdefault(key, {
            "source": source,
            "count": 0,
            "duration": 0.0,
            "finished_master": False,
        })
        entry["count"] += 1
        entry["duration"] += duration
        entry["finished_master"] = bool(entry["finished_master"] or _is_finished_master_source(source, clip))

    if not by_source:
        return []

    blocking: list[dict[str, Any]] = []
    total_source_clips = sum(int(entry["count"]) for entry in by_source.values())
    for entry in by_source.values():
        count = int(entry["count"])
        duration = float(entry["duration"])
        count_ratio = count / max(1, total_source_clips)
        duration_ratio = duration / total_duration if total_duration > 0 else count_ratio
        label = _source_label(str(entry["source"]))
        if entry["finished_master"] and (count > 1 or duration_ratio >= 0.10):
            blocking.append({
                "rule": "finished_master_as_source",
                "tier": 1,
                "artifact": "timeline_build",
                "message": (
                    f"timeline uses likely finished/master source '{label}' "
                    f"({count} clips, {duration_ratio:.0%} of source duration)"
                ),
                "next_action": "revise_material_selection_or_review",
            })
        if (
            not allow_single_source_highlight
            and count > 2
            and (count_ratio > 0.50 or duration_ratio >= 0.35)
        ):
            blocking.append({
                "rule": "repeated_source_over_limit",
                "tier": 1,
                "artifact": "timeline_build",
                "message": (
                    f"timeline overuses source '{label}' "
                    f"({count}/{total_source_clips} clips, {duration_ratio:.0%} of source duration)"
                ),
                "next_action": "revise_material_selection_or_review",
            })
    return blocking


def _is_real_material_route(root: Path) -> bool:
    intent = _load_json(root / "video_intent.json") or {}
    material_map = _load_json(root / "project_material_map.json") or {}
    route_text = " ".join(
        str(value)
        for value in (
            intent.get("route"),
            intent.get("entry_path"),
            intent.get("material_availability"),
            intent.get("input_state"),
            material_map.get("route"),
            material_map.get("source_truth"),
        )
        if value is not None
    ).lower()
    return any(marker in route_text for marker in (
        "existing-material",
        "material-first",
        "real_material",
        "real material",
        "existing_real_material",
        "real_user_supplied_material",
    ))


def _effects_required(root: Path) -> bool:
    effect_plan = _load_json(root / "effect_intent_plan.json") or {}
    transition_plan = _load_json(root / "transition_plan.json") or {}
    return bool(_as_list(effect_plan.get("effects")) or _as_list(transition_plan.get("transitions")))


def _effect_visual_evidence_refs(root: Path, verification: dict[str, Any]) -> list[str]:
    """Return existing keyframe-grid/visual-audit evidence refs for effects."""
    visual_ref = verification.get("visual_audit_ref") or "visual_audit.json"
    visual_path = _resolve_ref(root, visual_ref)
    visual_audit = _load_json(visual_path) if visual_path else None
    if not isinstance(visual_audit, dict):
        return []
    if visual_audit.get("pass") is not True:
        return []
    if not _as_list(visual_audit.get("samples")):
        return []

    grid_ref = (
        verification.get("keyframe_grid_ref")
        or visual_audit.get("grid_path")
        or visual_audit.get("grid")
        or "keyframe_grid.jpg"
    )
    grid_path = _resolve_ref(root, grid_ref)
    if grid_path is None or not grid_path.is_file() or grid_path.stat().st_size <= 0:
        return []
    return [str(visual_ref), str(grid_ref)]


def _job_asset_keys(job: dict[str, Any]) -> set[str]:
    keys: set[str] = set()
    for field in ("asset_id", "target_file", "output", "path"):
        value = job.get(field)
        if isinstance(value, str) and value.strip():
            keys.add(value.strip())
            keys.add(Path(value.strip()).name)
    return keys


def _generated_prompt_jobs(packet: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(packet, dict):
        return []
    jobs = packet.get("jobs")
    if not isinstance(jobs, list):
        jobs = packet.get("generation_jobs")
    return [job for job in (jobs or []) if isinstance(job, dict)]


def _is_nonempty_string(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _probe_media(path: Path) -> dict[str, Any]:
    proc = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "stream=index,codec_type,codec_name,duration:format=duration",
            "-of",
            "json",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        return {"ok": False, "error": (proc.stderr or proc.stdout or "").strip()}
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError as exc:
        return {"ok": False, "error": f"ffprobe returned invalid json: {exc}"}
    payload["ok"] = True
    return payload


def _has_stream(probe: dict[str, Any], codec_type: str) -> bool:
    return any(
        isinstance(stream, dict) and stream.get("codec_type") == codec_type
        for stream in probe.get("streams") or []
    )


def _duration_seconds(probe: dict[str, Any], codec_type: str | None = None) -> float | None:
    candidates: list[Any] = []
    if codec_type:
        for stream in probe.get("streams") or []:
            if isinstance(stream, dict) and stream.get("codec_type") == codec_type:
                candidates.append(stream.get("duration"))
    else:
        candidates.append(((probe.get("format") or {}) if isinstance(probe.get("format"), dict) else {}).get("duration"))
    for value in candidates:
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return None


def _story_beat_ids(story_contract: dict[str, Any] | None) -> set[str]:
    if not isinstance(story_contract, dict):
        return set()
    beats = _as_list(story_contract.get("required_story_beats")) or _as_list(story_contract.get("beats"))
    out: set[str] = set()
    for item in beats:
        if isinstance(item, dict):
            beat_id = str(item.get("beat_id") or item.get("id") or item.get("name") or "").strip()
            if beat_id:
                out.add(beat_id)
    return out


def _story_map_items(story_map: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(story_map, dict):
        return []
    raw = story_map.get("items") or story_map.get("beats") or story_map.get("mappings")
    return [item for item in _as_list(raw) if isinstance(item, dict)]


def _source_speech_required(story_contract: dict[str, Any] | None, story_map: dict[str, Any] | None) -> bool:
    explicit_markers = {
        "source_speech",
        "preserve_source_speech",
        "preserve_original_audio",
        "visible_speaker_source_speech",
    }
    for item in _story_map_items(story_map):
        fields = (
            item.get("evidence_type"),
            item.get("audio_role"),
            item.get("role"),
            item.get("source_type"),
            item.get("source_audio_policy"),
            item.get("original_audio_policy"),
        )
        if any(str(value or "").strip().casefold() in explicit_markers for value in fields):
            return True
        beat_id = str(item.get("beat_id") or item.get("id") or "").strip().casefold()
        if "source_speech" in beat_id:
            return True
    return _contract_requires_source_speech(story_contract)


def _contract_requires_source_speech(value: Any) -> bool:
    if isinstance(value, dict):
        for key, child in value.items():
            key_text = str(key).strip().casefold()
            if key_text in {"requires_source_speech", "source_speech_required", "preserve_source_speech"}:
                return child is not False
            if key_text in {"source_speech_policy", "original_audio_policy"}:
                policy = str(child or "").strip().casefold()
                if policy in {"required", "preserve", "preserve_speech", "keep", "source_speech"}:
                    return True
            if _contract_requires_source_speech(child):
                return True
    if isinstance(value, list):
        return any(_contract_requires_source_speech(item) for item in value)
    return False


def _source_speech_is_mixed(audio_mix_report: dict[str, Any] | None) -> bool:
    if not isinstance(audio_mix_report, dict):
        return False
    for key in ("tracks", "placements"):
        for item in _as_list(audio_mix_report.get(key)):
            if not isinstance(item, dict):
                continue
            role = str(item.get("role") or "").strip().casefold()
            policy = str(item.get("ducking_policy") or "").strip().casefold()
            source_type = str(item.get("source_type") or "").strip().casefold()
            if role in {"source_speech", "source_speech_preserved", "preserve_original_audio"}:
                return True
            if policy == "preserve_original_audio" and source_type in {"source_speech", "source_speech_preserved"}:
                return True
    return False


def _human_story_review_decision_state(
    decision: dict[str, Any] | None,
    required_beats: set[str],
) -> str:
    if not isinstance(decision, dict):
        return "missing"
    reviewer = str(decision.get("reviewer") or decision.get("reviewer_type") or "").strip().casefold()
    if reviewer != "human":
        return "non_human"
    value = str(decision.get("decision") or "").strip().casefold()
    if value == "approved":
        approved = {
            str(item).strip()
            for item in _as_list(decision.get("approved_beat_ids"))
            if str(item).strip()
        }
        if required_beats and not required_beats.issubset(approved):
            return "partial_approved"
        return "approved"
    if value in {"revision_requested", "rejected"}:
        return value
    return "malformed"


def _story_review_findings(
    story_contract: dict[str, Any] | None,
    story_map: dict[str, Any] | None,
    story_alignment: dict[str, Any] | None,
    story_human_review_decision: dict[str, Any] | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    required = _story_beat_ids(story_contract)
    if not required:
        return blocking, warnings
    items = _story_map_items(story_map)
    if not items:
        blocking.append({
            "rule": "missing_story_to_material_map",
            "tier": 1,
            "artifact": "story_to_material_map.json",
            "message": "story contract has required beats but story_to_material_map.json is missing or empty",
            "next_action": "map_story_beats_to_material",
        })
        return blocking, warnings
    covered = {
        str(item.get("beat_id") or item.get("id") or "").strip()
        for item in items
        if str(item.get("beat_id") or item.get("id") or "").strip()
    }
    missing = sorted(required - covered)
    if missing:
        blocking.append({
            "rule": "story_required_beats_uncovered",
            "tier": 1,
            "artifact": "story_to_material_map.json",
            "message": "required story beats are not covered by story_to_material_map.json",
            "missing_beats": missing,
            "next_action": "map_missing_story_beats_to_material",
        })
    needs_review = [
        item for item in items
        if item.get("needs_human_confirmation") is True
        or str(item.get("evidence_type") or "").strip() == "agent_inferred"
    ]
    decision_state = _human_story_review_decision_state(story_human_review_decision, required)
    if decision_state == "revision_requested":
        blocking.append({
            "rule": "story_human_review_revision_requested",
            "tier": 1,
            "artifact": "story_human_review_decision.json",
            "message": "human story review requested revisions to the story-to-material mapping",
            "next_action": "revise_story_material_mapping",
        })
    elif decision_state == "rejected":
        blocking.append({
            "rule": "story_human_review_rejected",
            "tier": 1,
            "artifact": "story_human_review_decision.json",
            "message": "human story review rejected the story-to-material mapping",
            "next_action": "repair_rejected_story_material_mapping",
        })
    if needs_review:
        if decision_state != "approved":
            warnings.append({
                "rule": "story_human_review_required",
                "tier": 2,
                "artifact": "story_to_material_map.json",
                "message": "story-to-material mapping includes agent-filled or inferred choices; technical delivery still needs human creative review",
                "count": len(needs_review),
                "next_action": "human_review_story_to_material_map",
            })
    if isinstance(story_alignment, dict) and story_alignment.get("ok") is False:
        blocking.append({
            "rule": "story_to_final_alignment_failed",
            "tier": 1,
            "artifact": "story_to_final_alignment_report.json",
            "message": "story-to-final alignment report is not ok",
            "next_action": "repair_story_to_final_alignment",
        })
    return blocking, warnings


def evaluate_complete_video_delivery(root: str | Path, probe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate a run folder as a complete deliverable video, not just a draft.

    This is intentionally stricter than the normal dashboard/workbench run-folder
    check. It only belongs at the final delivery boundary.
    """
    root = Path(root)
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []

    requirements = _load_json(root / "delivery_requirements.json")
    if requirements is None:
        requirements = {}
        blocking.append({
            "rule": "missing_delivery_requirements",
            "tier": 1,
            "artifact": "delivery_requirements.json",
            "message": "missing or invalid delivery_requirements.json",
            "next_action": "define_delivery_requirements",
        })

    requires_audio = bool(requirements.get("requires_audio", True))
    requires_narration = bool(requirements.get("requires_narration", True))
    requires_music = bool(requirements.get("requires_music", True))
    requires_subtitles = bool(requirements.get("requires_subtitles", True))
    requires_soundtrack_probe = bool(requirements.get("requires_soundtrack_probe", False))
    requires_vocal_conflict_check = bool(requirements.get("requires_vocal_conflict_check", False))
    allow_narration_fallback = bool(requirements.get("allow_narration_fallback", False))
    requires_frame_evidence = bool(requirements.get("requires_frame_evidence", False)) or _is_real_material_route(root)
    requires_effect_render_verification = (
        bool(requirements.get("requires_effect_render_verification", False))
        or _effects_required(root)
    )
    language = _expected_language(requirements)
    preferred_voiceover_provider = str(
        requirements.get("preferred_voiceover_provider")
        or requirements.get("voiceover_provider")
        or "voxcpm"
    ).strip().lower()
    fallback_allowed = bool(requirements.get("fallback_allowed", allow_narration_fallback))
    narration_waived_or_approved = _has_explicit_no_narration_approval(root)
    if requires_narration is False and not narration_waived_or_approved:
        blocking.append({
            "rule": "narration_required_for_complete_real_material_delivery",
            "tier": 1,
            "artifact": "delivery_requirements.json",
            "message": "complete real-material delivery requires narration unless a real user no-narration approval artifact is present",
            "next_action": "route_voiceover_voxcpm_or_attach_no_narration_approval",
        })
        requires_narration = True
    if requires_narration and preferred_voiceover_provider == "voxcpm" and not narration_waived_or_approved:
        voxcpm_runtime_check = _load_artifact_json(root, "voxcpm_runtime_check", "voxcpm_runtime_check.json")
        voiceover_provider_plan = _load_artifact_json(root, "voiceover_provider_plan", "voiceover_provider_plan.json")
        if voxcpm_runtime_check is None:
            blocking.append({
                "rule": "missing_voxcpm_runtime_check",
                "tier": 1,
                "artifact": "voxcpm_runtime_check.json",
                "message": "VoxCPM is the default voiceover provider and requires runtime evidence",
                "next_action": "run_voxcpm_runtime_check",
            })
        elif voxcpm_runtime_check.get("ok_to_execute") is False and not fallback_allowed:
            blocking.append({
                "rule": "voiceover_provider_unavailable",
                "tier": 1,
                "artifact": "voxcpm_runtime_check.json",
                "message": "VoxCPM runtime check is not executable and fallback is not allowed",
                "missing_modules": voxcpm_runtime_check.get("missing_modules"),
                "next_action": "install_or_connect_voxcpm_runtime",
            })
        if voiceover_provider_plan is None:
            blocking.append({
                "rule": "missing_voiceover_provider_plan",
                "tier": 1,
                "artifact": "voiceover_provider_plan.json",
                "message": "VoxCPM voiceover branch must record provider plan evidence",
                "next_action": "dispatch_voiceover_voxcpm",
            })
        else:
            selected_provider = str(voiceover_provider_plan.get("selected_provider") or "").strip().lower()
            requested_provider = str(voiceover_provider_plan.get("requested_provider") or preferred_voiceover_provider).strip().lower()
            provider_available = voiceover_provider_plan.get("provider_available")
            fallback_used = bool(voiceover_provider_plan.get("fallback_used"))
            plan_allows_fallback = bool(voiceover_provider_plan.get("fallback_allowed"))
            if selected_provider and selected_provider != "voxcpm":
                blocking.append({
                    "rule": "voiceover_provider_unavailable",
                    "tier": 1,
                    "artifact": "voiceover_provider_plan.json",
                    "message": "VoxCPM is required for this delivery and silent fallback is not allowed",
                    "requested_provider": requested_provider,
                    "selected_provider": selected_provider,
                    "next_action": "install_or_connect_voxcpm_runtime",
                })
            if provider_available is False and not (fallback_allowed or plan_allows_fallback):
                blocking.append({
                    "rule": "voiceover_provider_unavailable",
                    "tier": 1,
                    "artifact": "voiceover_provider_plan.json",
                    "message": "VoxCPM provider is unavailable and fallback is not allowed",
                    "next_action": "install_or_connect_voxcpm_runtime",
                })
            if fallback_used and not (fallback_allowed or plan_allows_fallback):
                blocking.append({
                    "rule": "voiceover_provider_unavailable",
                    "tier": 1,
                    "artifact": "voiceover_provider_plan.json",
                    "message": "voiceover provider fallback was used without explicit fallback approval",
                    "next_action": "rerun_voiceover_with_voxcpm",
                })
    subtitle_voiceover_handoff = _load_artifact_json(
        root,
        "subtitle_voiceover_build_handoff",
        "subtitle_voiceover_build_handoff.json",
    ) or {}
    script_artifact = _load_artifact_json(root, "script", "script.json")
    story_contract = _load_artifact_json(root, "story_contract", "story_contract.json")
    story_to_material_map = _load_artifact_json(root, "story_to_material_map", "story_to_material_map.json")
    story_to_final_alignment = _load_artifact_json(
        root,
        "story_to_final_alignment_report",
        "story_to_final_alignment_report.json",
    )
    story_human_review_decision = _load_artifact_json(
        root,
        "story_human_review_decision",
        "story_human_review_decision.json",
    )
    blocking.extend(_artifact_manifest_stale_blocks(root, DELIVERY_MANIFEST_EVIDENCE_KEYS))

    final_path = root / "final.mp4"
    if not final_path.is_file() or final_path.stat().st_size <= 0:
        blocking.append({
            "rule": "missing_final_video",
            "tier": 1,
            "artifact": "final.mp4",
            "message": "final.mp4 is missing or empty",
            "next_action": "render_final_video",
        })
        media_probe = {}
    else:
        media_probe = probe if probe is not None else _probe_media(final_path)
        if media_probe.get("ok") is False:
            probe_error = media_probe.get("error") or "ffprobe failed"
            blocking.append({
                "rule": "media_probe_failed",
                "tier": 1,
                "artifact": "final.mp4",
                "message": f"final.mp4 is not a valid playable media file: {probe_error}",
                "probe_error": probe_error,
                "next_action": "fix_or_rerender_video",
            })
        elif not _has_stream(media_probe, "video"):
            blocking.append({
                "rule": "missing_video_stream",
                "tier": 1,
                "artifact": "final.mp4",
                "message": "final.mp4 has no video stream",
                "next_action": "render_final_video",
            })
        if requires_audio and not _has_stream(media_probe, "audio"):
            blocking.append({
                "rule": "missing_audio_stream",
                "tier": 1,
                "artifact": "final.mp4",
                "message": "final.mp4 has no audio stream but audio is required",
                "next_action": "render_audio_mix",
            })

        video_duration = _duration_seconds(media_probe, "video")
        audio_duration = _duration_seconds(media_probe, "audio")
        if requires_audio and video_duration and audio_duration:
            if abs(video_duration - audio_duration) > 1.5:
                blocking.append({
                    "rule": "audio_video_duration_mismatch",
                    "tier": 1,
                    "artifact": "final.mp4",
                    "message": "audio duration differs from video duration by more than 1.5 seconds",
                    "next_action": "fix_audio_mix_duration",
                })

    narration_manifest = _load_artifact_json(root, "narration_manifest", "narration_manifest.json")
    if (
        not _manifest_has_items(narration_manifest, "segments", "clips", "lines")
        and isinstance(subtitle_voiceover_handoff, dict)
        and subtitle_voiceover_handoff.get("voiceover_ready") is True
    ):
        handoff_manifest_path = _resolve_ref(root, subtitle_voiceover_handoff.get("narration_manifest"))
        if handoff_manifest_path is not None:
            narration_manifest = _load_json(handoff_manifest_path)
    if requires_narration and not _manifest_has_items(narration_manifest, "segments", "clips", "lines"):
        blocking.append({
            "rule": "missing_narration_manifest",
            "tier": 1,
            "artifact": "narration_manifest.json",
            "message": "narration is required but narration_manifest.json has no segments/clips/lines",
            "next_action": "generate_or_attach_narration",
        })
    if narration_manifest is not None and _json_text_has_mojibake(narration_manifest):
        blocking.append({
            "rule": "corrupt_narration_manifest",
            "tier": 1,
            "artifact": "narration_manifest.json",
            "message": "narration_manifest.json contains mojibake placeholders",
            "next_action": "regenerate_narration_manifest_utf8",
        })
    chinese_expected = _scripted_chinese_expected(requirements, script_artifact, story_contract, narration_manifest)
    if script_artifact is not None:
        script_text_items = _text_items(script_artifact)
        if _has_text_corruption(script_artifact) or (chinese_expected and script_text_items and not _contains_cjk("\n".join(script_text_items))):
            blocking.append({
                "rule": "corrupt_script_text",
                "tier": 1,
                "artifact": "script.json",
                "message": "script.json contains corrupt or non-CJK Chinese narration text",
                "next_action": "regenerate_script_utf8",
            })
    if (
        narration_manifest is not None
        and chinese_expected
        and _text_items(narration_manifest)
        and not _contains_cjk("\n".join(_text_items(narration_manifest)))
    ):
        blocking.append({
            "rule": "corrupt_narration_manifest",
            "tier": 1,
            "artifact": "narration_manifest.json",
            "message": "narration_manifest.json lacks expected CJK narration text",
            "next_action": "regenerate_narration_manifest_utf8",
        })
    if requires_narration and narration_manifest is not None and not allow_narration_fallback:
        narration_segments = (
            _as_list(narration_manifest.get("segments"))
            or _as_list(narration_manifest.get("clips"))
            or _as_list(narration_manifest.get("lines"))
        )
        missing_refs = []
        invalid_refs = []
        usable_refs: set[str] = set()
        for index, segment in enumerate(narration_segments):
            if not isinstance(segment, dict):
                continue
            audio_ref = segment.get("audio_ref") or segment.get("source_ref") or segment.get("file")
            path = _resolve_ref(root, audio_ref)
            if path is None:
                missing_refs.append(index)
                continue
            if not path.is_file():
                invalid_refs.append(str(audio_ref))
                continue
            duration = _audio_duration(path)
            if duration is None or duration < 0.2:
                invalid_refs.append(str(audio_ref))
                continue
            usable_refs.add(str(path.resolve()))
        if missing_refs:
            blocking.append({
                "rule": "missing_narration_audio_refs",
                "tier": 1,
                "artifact": "narration_manifest.json",
                "message": "narration is required but one or more narration segments have no audio_ref",
                "next_action": "generate_narration_audio_refs",
            })
        if invalid_refs:
            blocking.append({
                "rule": "invalid_narration_audio_refs",
                "tier": 1,
                "artifact": "narration_manifest.json",
                "message": "narration audio_ref files are missing, unreadable, or too short",
                "next_action": "regenerate_narration_audio",
            })
        if narration_segments and not usable_refs:
            blocking.append({
                "rule": "no_usable_narration_audio",
                "tier": 1,
                "artifact": "narration_manifest.json",
                "message": "narration is required but no usable narration audio was found",
                "next_action": "generate_narration_audio",
            })
        fallback_markers = ("fallback", "sine cue", "cue only", "tone", "empty wav")
        if _string_contains_any(narration_manifest, fallback_markers):
            blocking.append({
                "rule": "narration_declares_fallback",
                "tier": 1,
                "artifact": "narration_manifest.json",
                "message": "narration manifest declares fallback/cue-only narration",
                "next_action": "replace_fallback_with_real_narration",
            })

    music_manifest = _load_artifact_json(root, "music_manifest", "music_manifest.json")
    if requires_music and not _manifest_has_items(music_manifest, "tracks", "cues"):
        blocking.append({
            "rule": "missing_music_manifest",
            "tier": 1,
            "artifact": "music_manifest.json",
            "message": "music is required but music_manifest.json has no tracks/cues",
            "next_action": "generate_or_attach_music",
        })
    if requires_music:
        blocking.extend(_delivery_music_source_blocks(music_manifest))

    soundtrack_probe_report = _load_artifact_json(
        root,
        "soundtrack_probe_report",
        "soundtrack_probe_report.json",
    )
    if requires_music or soundtrack_probe_report is not None:
        blocking.extend(
            _soundtrack_probe_report_blocks(
                soundtrack_probe_report,
                required=requires_music or requires_soundtrack_probe,
                require_vocal_clearance=requires_vocal_conflict_check,
            )
        )

    audio_mix_report = _load_artifact_json(root, "audio_mix_report", "audio_mix_report.json")
    if requires_audio:
        if audio_mix_report is None:
            blocking.append({
                "rule": "missing_audio_mix_report",
                "tier": 1,
                "artifact": "audio_mix_report.json",
                "message": "audio is required but audio_mix_report.json is missing or invalid",
                "next_action": "write_audio_mix_report",
            })
        else:
            if audio_mix_report.get("audio_stream_present") is False:
                blocking.append({
                    "rule": "audio_mix_report_declares_no_audio",
                    "tier": 1,
                    "artifact": "audio_mix_report.json",
                    "message": "audio_mix_report.json says no audio stream is present",
                    "next_action": "render_audio_mix",
                })
            if requires_narration and audio_mix_report.get("narration_included") is False:
                blocking.append({
                    "rule": "narration_not_mixed",
                    "tier": 1,
                    "artifact": "audio_mix_report.json",
                    "message": "narration is required but audio mix does not include it",
                    "next_action": "mix_narration_audio",
                })
            if requires_music and audio_mix_report.get("music_included") is False:
                blocking.append({
                    "rule": "music_not_mixed",
                    "tier": 1,
                    "artifact": "audio_mix_report.json",
                    "message": "music is required but audio mix does not include it",
                    "next_action": "mix_music_audio",
                })
            if requires_narration and not allow_narration_fallback:
                fallback_markers = ("fallback", "sine cue", "cue only", "tone", "empty wav")
                if _string_contains_any(audio_mix_report, fallback_markers):
                    blocking.append({
                        "rule": "audio_mix_declares_narration_fallback",
                        "tier": 1,
                        "artifact": "audio_mix_report.json",
                        "message": "audio mix report declares fallback/cue-only narration",
                        "next_action": "replace_fallback_with_real_narration",
                    })
            blocking.extend(_audio_mix_report_blocks(audio_mix_report))

    source_speech_preservation = _load_artifact_json(
        root,
        "source_speech_preservation_report",
        "source_speech_preservation_report.json",
    )
    source_speech_rejection = _load_artifact_json(
        root,
        "source_speech_rejection_report",
        "source_speech_rejection_report.json",
    )
    if _source_speech_required(story_contract, story_to_material_map):
        if source_speech_preservation is None and source_speech_rejection is None:
            blocking.append({
                "rule": "missing_source_speech_preservation_evidence",
                "tier": 1,
                "artifact": "source_speech_preservation_report.json",
                "message": "story contract/material map requires visible source speech but no preservation or rejection evidence exists",
                "next_action": "preserve_source_speech_or_write_rejection_report",
            })
        elif isinstance(source_speech_preservation, dict) and source_speech_preservation.get("status") == "preserved":
            if not _source_speech_is_mixed(audio_mix_report):
                blocking.append({
                    "rule": "source_speech_not_mixed",
                    "tier": 1,
                    "artifact": "audio_mix_report.json",
                    "message": "source speech is marked preserved but audio_mix_report does not include a source_speech/preserve_original_audio track",
                    "next_action": "remix_with_preserved_source_speech",
                })
        elif isinstance(source_speech_rejection, dict):
            reason = (
                source_speech_rejection.get("reason")
                or source_speech_rejection.get("unusable_reason")
                or source_speech_rejection.get("evidence")
            )
            if not isinstance(reason, str) or not reason.strip():
                blocking.append({
                    "rule": "invalid_source_speech_rejection",
                    "tier": 1,
                    "artifact": "source_speech_rejection_report.json",
                    "message": "source speech rejection report must state a concrete unusable reason",
                    "next_action": "write_source_speech_rejection_evidence",
                })
        else:
            blocking.append({
                "rule": "invalid_source_speech_rejection",
                "tier": 1,
                "artifact": "source_speech_preservation_report.json",
                "message": "source speech evidence is present but does not preserve speech or state a valid rejection",
                "next_action": "repair_source_speech_evidence",
            })

    subtitles_path = root / "subtitles.srt"
    if (
        isinstance(subtitle_voiceover_handoff, dict)
        and subtitle_voiceover_handoff.get("subtitle_ready") is True
    ):
        handoff_subtitles_path = _resolve_ref(root, subtitle_voiceover_handoff.get("subtitles"))
        if handoff_subtitles_path is not None and handoff_subtitles_path.is_file():
            subtitles_path = handoff_subtitles_path
    subtitles = ""
    if requires_subtitles:
        try:
            subtitles = subtitles_path.read_text(encoding="utf-8")
        except OSError:
            subtitles = ""
        if "-->" not in subtitles:
            blocking.append({
                "rule": "missing_subtitles",
                "tier": 1,
                "artifact": "subtitles.srt",
                "message": "subtitles are required but subtitles.srt is missing or has no timing cues",
                "next_action": "generate_subtitles",
            })
        elif _has_mojibake(subtitles):
            blocking.append({
                "rule": "corrupt_subtitles",
                "tier": 1,
                "artifact": "subtitles.srt",
                "message": "subtitles.srt appears to contain mojibake placeholders",
                "next_action": "regenerate_subtitles_utf8",
            })
        elif language in {
            "zh",
            "zh-tw",
            "traditional chinese",
            "chinese",
            "\u7e41\u9ad4\u4e2d\u6587",
            "\u4e2d\u6587",
        } and not _contains_cjk(subtitles):
            blocking.append({
                "rule": "subtitle_language_mismatch",
                "tier": 1,
                "artifact": "subtitles.srt",
                "message": "Chinese subtitles are required but subtitles.srt does not contain CJK text",
                "next_action": "regenerate_subtitles_in_required_language",
            })

        subtitle_alignment = _load_artifact_json(
            root,
            "subtitle_audio_alignment_report",
            "subtitle_audio_alignment_report.json",
        )
        has_audible_text_source = _manifest_has_items(narration_manifest, "segments", "clips", "lines") or source_speech_preservation is not None
        if has_audible_text_source and subtitle_alignment is None:
            blocking.append({
                "rule": "missing_subtitle_audio_alignment_report",
                "tier": 1,
                "artifact": "subtitle_audio_alignment_report.json",
                "message": "subtitles require subtitle_audio_alignment_report.json when narration or source speech exists",
                "next_action": "build_subtitle_audio_alignment_report",
            })
        elif isinstance(subtitle_alignment, dict):
            alignment_text_items = _text_items(subtitle_alignment)
            if _has_text_corruption(subtitle_alignment) or (
                chinese_expected and alignment_text_items and not _contains_cjk("\n".join(alignment_text_items))
            ):
                blocking.append({
                    "rule": "corrupt_subtitle_alignment",
                    "tier": 1,
                    "artifact": "subtitle_audio_alignment_report.json",
                    "message": "subtitle_audio_alignment_report.json contains corrupt or non-CJK Chinese subtitle text",
                    "next_action": "regenerate_subtitle_audio_alignment_utf8",
                })
            if subtitle_alignment.get("ok") is False:
                blocking.append({
                    "rule": "subtitle_audio_alignment_failed",
                    "tier": 1,
                    "artifact": "subtitle_audio_alignment_report.json",
                    "message": "subtitle_audio_alignment_report.json is not ok",
                    "next_action": "repair_subtitle_audio_alignment",
                })
            for item in _as_list(subtitle_alignment.get("items")):
                if not isinstance(item, dict):
                    continue
                item_type = str(item.get("type") or item.get("kind") or "").strip()
                is_editorial = item.get("editorial_caption") is True or item_type == "editorial_caption"
                corresponds = item.get("corresponds_to_audible_audio")
                if corresponds is False and not is_editorial:
                    blocking.append({
                        "rule": "unlabeled_editorial_subtitles",
                        "tier": 1,
                        "artifact": "subtitle_audio_alignment_report.json",
                        "message": "subtitle text that does not correspond to audible speech/narration must be labeled editorial_caption",
                        "next_action": "label_editorial_captions_or_repair_subtitles",
                    })
                    break

    story_blocks, story_warnings = _story_review_findings(
        story_contract,
        story_to_material_map,
        story_to_final_alignment,
        story_human_review_decision,
    )
    blocking.extend(story_blocks)
    warnings.extend(story_warnings)

    for rel in ("agent_interaction_log.md", "HONEST_REVIEW.md"):
        text = _read_text(root / rel)
        if text is not None and _has_unreadable_review_text(text):
            blocking.append({
                "rule": "corrupt_review_artifact",
                "tier": 1,
                "artifact": rel,
                "message": f"{rel} contains mojibake placeholders",
                "next_action": "rewrite_review_artifact_utf8",
            })

    generated_material_review = _load_artifact_json(root, "generated_material_review", "generated_material_review.json")
    material_generation_fallback = _load_artifact_json(root, "material_generation_fallback", "material_generation_fallback.json")
    generated_provider_packet = _load_artifact_json(root, "generated_provider_packet", "generated_provider_packet.json")
    generated_route = any((root / rel).exists() for rel in (
        "material_generation_fallback.json",
        "generated_provider_packet.json",
        "generated_material_review.json",
    ))
    if generated_material_review is not None and _json_text_has_mojibake(generated_material_review):
        blocking.append({
            "rule": "corrupt_generated_material_review",
            "tier": 1,
            "artifact": "generated_material_review.json",
            "message": "generated_material_review.json contains mojibake placeholders",
            "next_action": "rewrite_generated_material_review_utf8",
        })
    if generated_route:
        if generated_material_review is None:
            blocking.append({
                "rule": "missing_generated_material_review",
                "tier": 1,
                "artifact": "generated_material_review.json",
                "message": "generated material route requires generated_material_review.json",
                "next_action": "review_generated_material",
            })
        else:
            if generated_material_review.get("pass") is not True:
                blocking.append({
                    "rule": "generated_material_review_not_passed",
                    "tier": 1,
                    "artifact": "generated_material_review.json",
                    "message": "generated material review has not passed",
                    "next_action": "revise_generated_material",
                })
            accepted_assets = generated_material_review.get("accepted_assets")
            if not isinstance(accepted_assets, list) or not accepted_assets:
                blocking.append({
                    "rule": "generated_material_review_has_no_accepted_assets",
                    "tier": 1,
                    "artifact": "generated_material_review.json",
                    "message": "generated material review must list accepted assets",
                    "next_action": "review_generated_material",
                })
            consistency = generated_material_review.get("consistency_review")
            if not isinstance(consistency, dict) or consistency.get("pass") is not True:
                blocking.append({
                    "rule": "missing_generated_material_consistency_review",
                    "tier": 1,
                    "artifact": "generated_material_review.json",
                    "message": "generated material review must explicitly pass story/character/segment consistency",
                    "next_action": "review_or_regenerate_inconsistent_material",
                })
        if material_generation_fallback is None:
            blocking.append({
                "rule": "missing_material_generation_fallback",
                "tier": 1,
                "artifact": "material_generation_fallback.json",
                "message": "generated material route requires material_generation_fallback.json",
                "next_action": "rerun_generated_material_fallback",
            })
        elif material_generation_fallback.get("ok") is not True:
            blocking.append({
                "rule": "generated_fallback_not_ok",
                "tier": 1,
                "artifact": "material_generation_fallback.json",
                "message": "material generation fallback did not produce an ok job plan",
                "next_action": "fix_material_needs_and_rerun_fallback",
            })
        fallback_jobs = _generated_prompt_jobs(material_generation_fallback)
        if not fallback_jobs:
            blocking.append({
                "rule": "material_generation_fallback_has_no_jobs",
                "tier": 1,
                "artifact": "material_generation_fallback.json",
                "message": "material generation fallback must list generation jobs",
                "next_action": "rerun_generated_material_fallback",
            })
        provider_jobs = _generated_prompt_jobs(generated_provider_packet)
        if not provider_jobs:
            blocking.append({
                "rule": "generated_provider_packet_has_no_jobs",
                "tier": 1,
                "artifact": "generated_provider_packet.json",
                "message": "generated provider packet must list prompt jobs",
                "next_action": "write_generated_prompt_packet",
            })
        for index, job in enumerate(provider_jobs):
            if not isinstance(job.get("job_id"), str) or not job.get("job_id").strip():
                blocking.append({
                    "rule": "generated_provider_job_missing_job_id",
                    "tier": 1,
                    "artifact": "generated_provider_packet.json",
                    "message": f"provider job #{index} must include job_id",
                    "next_action": "write_generated_prompt_packet",
                })
            if not isinstance(job.get("need_id"), str) or not job.get("need_id").strip():
                blocking.append({
                    "rule": "generated_provider_job_missing_need_id",
                    "tier": 1,
                    "artifact": "generated_provider_packet.json",
                    "message": f"provider job #{index} must include need_id",
                    "next_action": "write_generated_prompt_packet",
                })
            if not isinstance(job.get("prompt"), str) or not job.get("prompt").strip():
                blocking.append({
                    "rule": "generated_provider_job_missing_prompt",
                    "tier": 1,
                    "artifact": "generated_provider_packet.json",
                    "message": f"provider job #{index} must include prompt",
                    "next_action": "write_generated_prompt_packet",
                })
            truth_controls = job.get("truth_controls")
            if not isinstance(truth_controls, dict):
                blocking.append({
                    "rule": "generated_provider_job_missing_truth_controls",
                    "tier": 1,
                    "artifact": "generated_provider_packet.json",
                    "message": f"provider job #{index} must include truth_controls",
                    "next_action": "write_generated_truth_controls",
                })
                truth_controls = {}
            source_truth = truth_controls.get("source_truth")
            truth_usage = truth_controls.get("truth_usage")
            if source_truth not in {"generated", "reference_guided_generated", "composite"}:
                blocking.append({
                    "rule": "generated_provider_job_invalid_source_truth",
                    "tier": 1,
                    "artifact": "generated_provider_packet.json",
                    "message": f"provider job #{index} has invalid truth_controls.source_truth",
                    "next_action": "write_generated_truth_controls",
                })
            if truth_usage not in {"support", "illustrative", "transition"}:
                blocking.append({
                    "rule": "generated_provider_job_invalid_truth_usage",
                    "tier": 1,
                    "artifact": "generated_provider_packet.json",
                    "message": f"provider job #{index} has invalid truth_controls.truth_usage",
                    "next_action": "write_generated_truth_controls",
                })
            if source_truth in {"reference_guided_generated", "composite"}:
                reference_controls = job.get("reference_controls")
                refs = _as_list((reference_controls or {}).get("reference_assets")) if isinstance(reference_controls, dict) else []
                if not refs:
                    blocking.append({
                        "rule": "reference_guided_generated_missing_reference_assets",
                        "tier": 1,
                        "artifact": "generated_provider_packet.json",
                        "message": f"provider job #{index} uses reference-guided generation without reference_assets",
                        "next_action": "attach_reference_assets_or_change_truth_controls",
                    })
                for ref in refs:
                    ref_path = _resolve_ref(root, ref)
                    if ref_path is None or not ref_path.is_file() or ref_path.stat().st_size <= 0:
                        blocking.append({
                            "rule": "reference_guided_generated_reference_missing",
                            "tier": 1,
                            "artifact": "generated_provider_packet.json",
                            "message": f"provider job #{index} references a missing reference asset",
                            "next_action": "attach_reference_assets_or_change_truth_controls",
                        })
            target = _resolve_ref(root, job.get("target_file") or job.get("output") or job.get("path"))
            if target is None or not target.is_file() or target.stat().st_size <= 0:
                blocking.append({
                    "rule": "generated_provider_job_missing_target_file",
                    "tier": 1,
                    "artifact": "generated_provider_packet.json",
                    "message": f"provider job #{index} must reference an existing target file",
                    "next_action": "regenerate_or_import_generated_asset",
                })
        if isinstance(generated_material_review, dict):
            job_keys = set()
            for job in provider_jobs:
                job_keys.update(_job_asset_keys(job))
            for asset in _as_list(generated_material_review.get("accepted_assets")):
                asset_text = str(asset)
                if asset_text not in job_keys and Path(asset_text).name not in job_keys:
                    blocking.append({
                        "rule": "accepted_generated_asset_missing_prompt_lineage",
                        "tier": 1,
                        "artifact": "generated_material_review.json",
                        "message": f"accepted generated asset {asset_text!r} has no matching provider prompt job",
                        "next_action": "link_accepted_asset_to_prompt_job",
                    })

    frame_evidence = _load_json(root / "frame_evidence.json")
    if requires_frame_evidence:
        if frame_evidence is None:
            blocking.append({
                "rule": "missing_frame_evidence",
                "tier": 1,
                "artifact": "frame_evidence.json",
                "message": "real/material-first montage delivery requires frame-level visual evidence",
                "next_action": "run_frame_level_material_recognition",
            })
        else:
            if frame_evidence.get("pass") is not True:
                blocking.append({
                    "rule": "frame_evidence_not_passed",
                    "tier": 1,
                    "artifact": "frame_evidence.json",
                    "message": "frame-level visual evidence did not pass",
                    "next_action": "revise_material_selection_or_review",
                })
            inspected_assets = _as_list(frame_evidence.get("inspected_assets"))
            if not inspected_assets:
                blocking.append({
                    "rule": "frame_evidence_has_no_inspected_assets",
                    "tier": 1,
                    "artifact": "frame_evidence.json",
                    "message": "frame_evidence.json must list inspected_assets",
                    "next_action": "run_frame_level_material_recognition",
                })
            for index, asset in enumerate(inspected_assets):
                if not isinstance(asset, dict):
                    continue
                frames = _as_list(asset.get("frames")) or _as_list(asset.get("frame_refs"))
                observations = _as_list(asset.get("observations"))
                semantic_match = asset.get("semantic_match")
                if not frames:
                    blocking.append({
                        "rule": "frame_evidence_asset_has_no_frames",
                        "tier": 1,
                        "artifact": "frame_evidence.json",
                        "message": f"inspected asset #{index} has no frame refs",
                        "next_action": "run_frame_level_material_recognition",
                    })
                if not observations:
                    blocking.append({
                        "rule": "frame_evidence_asset_has_no_observations",
                        "tier": 1,
                        "artifact": "frame_evidence.json",
                        "message": f"inspected asset #{index} has no visual observations",
                        "next_action": "run_frame_level_material_recognition",
                    })
                if semantic_match is not True:
                    blocking.append({
                        "rule": "frame_evidence_semantic_match_not_passed",
                        "tier": 1,
                        "artifact": "frame_evidence.json",
                        "message": f"inspected asset #{index} does not explicitly pass semantic_match",
                        "next_action": "revise_material_selection_or_review",
                    })

    effect_render_verification = _load_artifact_json(
        root,
        "effect_render_verification",
        "effect_render_verification.json",
    )
    if requires_effect_render_verification:
        if effect_render_verification is None:
            blocking.append({
                "rule": "missing_effect_render_verification",
                "tier": 1,
                "artifact": "effect_render_verification.json",
                "message": "planned effects/transitions require render verification",
                "next_action": "verify_rendered_effects",
            })
        else:
            if effect_render_verification.get("pass") is not True:
                blocking.append({
                    "rule": "effect_render_verification_not_passed",
                    "tier": 1,
                    "artifact": "effect_render_verification.json",
                    "message": "effect render verification did not pass",
                    "next_action": "fix_or_verify_rendered_effects",
                })
            shared_visual_evidence_refs = _effect_visual_evidence_refs(root, effect_render_verification)
            verified_effects = _as_list(effect_render_verification.get("verified_effects"))
            if not verified_effects:
                blocking.append({
                    "rule": "effect_render_verification_has_no_verified_effects",
                    "tier": 1,
                    "artifact": "effect_render_verification.json",
                    "message": "effect_render_verification.json must list verified_effects",
                    "next_action": "verify_rendered_effects",
                })
            for index, item in enumerate(verified_effects):
                if not isinstance(item, dict):
                    continue
                if item.get("rendered") is not True:
                    blocking.append({
                        "rule": "planned_effect_not_rendered",
                        "tier": 1,
                        "artifact": "effect_render_verification.json",
                        "message": f"verified effect #{index} is not marked rendered",
                        "next_action": "render_or_remove_unrendered_effect",
                    })
                evidence_refs = _as_list(item.get("evidence_refs")) or _as_list(item.get("sampled_frames"))
                if not evidence_refs:
                    evidence_refs = shared_visual_evidence_refs
                if not evidence_refs:
                    blocking.append({
                        "rule": "rendered_effect_has_no_evidence_refs",
                        "tier": 1,
                        "artifact": "effect_render_verification.json",
                        "message": f"verified effect #{index} has no evidence refs",
                        "next_action": "sample_rendered_effect_evidence",
                    })

    blocking, limitations, waivers_applied = _apply_video_only_delivery_waiver(root, blocking, warnings)

    return {
        "artifact_role": "complete_video_delivery_gate",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "waivers_applied": waivers_applied,
        "limitations": limitations,
        "next_action": blocking[0]["next_action"] if blocking else None,
        "summary": {
            "requires_audio": requires_audio,
            "requires_narration": requires_narration,
            "requires_music": requires_music,
            "requires_subtitles": requires_subtitles,
            "requires_frame_evidence": requires_frame_evidence,
            "requires_effect_render_verification": requires_effect_render_verification,
            "requires_vocal_conflict_check": requires_vocal_conflict_check,
            "allow_narration_fallback": allow_narration_fallback,
            "language": language,
            "video_stream_present": _has_stream(media_probe, "video") if isinstance(media_probe, dict) else False,
            "audio_stream_present": _has_stream(media_probe, "audio") if isinstance(media_probe, dict) else False,
            "video_duration_sec": _duration_seconds(media_probe, "video") if isinstance(media_probe, dict) else None,
            "audio_duration_sec": _duration_seconds(media_probe, "audio") if isinstance(media_probe, dict) else None,
        },
    }


def evaluate_delivery_gate(artifacts):
    blocking = []
    for role in HARD_AUDITS:
        audit = (artifacts or {}).get(role)
        if isinstance(audit, dict) and audit.get("pass") is False:
            default_action = (
                "verify_failed" if role == "verify_result"
                else "fix_timeline_or_assembly"
            )
            blocking.append({
                "rule": "failed_audit",
                "tier": 1,
                "artifact": role,
                "message": f"{role} failed",
                "next_action": audit.get("next_action") or default_action,
            })

    material_delta = (artifacts or {}).get("material_delta") or {}
    material_lifecycle = (artifacts or {}).get("material_map_lifecycle") or {}
    delta_ready = (
        isinstance(material_delta, dict)
        and material_delta.get("ok") is True
        and material_delta.get("ready_for_build") is True
    )
    lifecycle_ready = (
        isinstance(material_lifecycle, dict)
        and material_lifecycle.get("can_build") is True
        and material_lifecycle.get("next_action") in (None, "build")
    )
    material_ready = delta_ready or lifecycle_ready
    blocking.extend(_stage0_child_contract_blocks(artifacts or {}))
    blocking.extend(_source_quality_blocking((artifacts or {}).get("timeline_build"), artifacts or {}))
    blocking.extend(_timeline_material_contract_blocks(
        (artifacts or {}).get("timeline_build"),
        (artifacts or {}).get("segment_contract") or (artifacts or {}).get("contract"),
        (artifacts or {}).get("project_material_map") or (artifacts or {}).get("material_maps"),
    ))

    coverage = (artifacts or {}).get("material_coverage") or {}
    for gap in coverage.get("gaps") or []:
        if material_ready:
            continue
        blocking.append({
            "rule": "unresolved_gap",
            "tier": 1,
            "segment": gap.get("segment"),
            "message": gap.get("reason") or "material gap unresolved",
            "next_action": "await_material",
        })

    rough_cut_plan = (artifacts or {}).get("rough_cut_plan") or {}
    if isinstance(rough_cut_plan, dict) and rough_cut_plan.get("ok") is False:
        for gap in rough_cut_plan.get("gaps") or []:
            if not isinstance(gap, dict):
                continue
            blocking.append({
                "rule": "rough_cut_gap",
                "tier": 1,
                "artifact": "rough_cut_plan",
                "segment": gap.get("segment"),
                "need_id": gap.get("need_id"),
                "message": gap.get("reason") or "rough-cut plan has unresolved material gap",
                "next_action": "revise_material_selection_or_review",
            })

    return {
        "artifact_role": "delivery_gate",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "next_action": blocking[0]["next_action"] if blocking else None,
    }
