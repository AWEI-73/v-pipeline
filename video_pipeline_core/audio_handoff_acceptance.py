"""No-render acceptance gate from Soundtrack Arranger to Audio Director."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


BAD_LICENSE_STATUSES = {"license_missing", "provider_unavailable", "reference_only"}
SPEECH_DUCKING_POLICIES = {"duck_under_voice", "preserve_original_audio"}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _section_map(soundtrack_plan: Mapping[str, Any] | None) -> dict[str, dict[str, Any]]:
    if not soundtrack_plan:
        return {}
    sections = soundtrack_plan.get("sections") or []
    return {
        _clean(section.get("section_id")): dict(section)
        for section in sections
        if _clean(section.get("section_id"))
    }


def _float_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _mix_sections(soundtrack_plan: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    if not soundtrack_plan:
        return []
    sections = soundtrack_plan.get("sections") or []
    if not any(
        isinstance(section, Mapping)
        and (section.get("duration_sec") is not None or section.get("end_sec") is not None)
        for section in sections
    ):
        return []
    out: list[dict[str, Any]] = []
    cursor = 0.0
    for section in sections:
        if not isinstance(section, Mapping):
            continue
        section_id = _clean(section.get("section_id"))
        if not section_id:
            continue
        start = _float_value(section.get("start_sec")) if section.get("start_sec") is not None else cursor
        duration = _float_value(section.get("duration_sec"))
        if duration <= 0 and section.get("end_sec") is not None:
            duration = max(0.0, _float_value(section.get("end_sec")) - start)
        item = {
            "section_id": section_id,
            "start_sec": round(start, 3),
            "duration_sec": round(duration, 3),
        }
        for key in ("story_function", "music_role", "vocal_policy", "ducking_policy"):
            if section.get(key) is not None:
                item[key] = section.get(key)
        if section.get("audio_required") is not None:
            item["audio_required"] = bool(section.get("audio_required"))
        elif section.get("required_audio") is not None:
            item["audio_required"] = bool(section.get("required_audio"))
        out.append(item)
        cursor = max(cursor, start + duration)
    return out


def _resolve_audio_path(value: Any, out_dir: Path) -> Path:
    path = Path(_clean(value))
    if path.is_absolute():
        return path
    return out_dir / path


def _role_for_track(selected: Mapping[str, Any], section: Mapping[str, Any] | None) -> str:
    section = section or {}
    ducking = _clean(selected.get("ducking_policy") or section.get("ducking_policy"))
    music_role = _clean(section.get("music_role") or selected.get("music_role"))
    if ducking == "preserve_original_audio":
        return "preserve_original_audio"
    if ducking == "duck_under_voice":
        return "music_ducked"
    if music_role == "song" or _clean(selected.get("source_type")) == "jamendo_song":
        return "music_main"
    return "music_bed"


def accept_audio_handoff(
    audio_director_handoff: Mapping[str, Any],
    *,
    soundtrack_plan: Mapping[str, Any] | None = None,
    sound_license_manifest: Mapping[str, Any] | None = None,
    out_dir: str | Path,
) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    sections = _section_map(soundtrack_plan)
    selected = list(audio_director_handoff.get("selected_audio_files") or [])
    blocking: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    tracks: list[dict[str, Any]] = []

    if not selected:
        blocking.append({
            "rule": "selected_audio_missing",
            "message": "audio_director_handoff.selected_audio_files must contain at least one item",
        })

    if sound_license_manifest and sound_license_manifest.get("delivery_allowed") is False:
        blocking.append({
            "rule": "license_manifest_blocks_delivery",
            "message": "sound_license_manifest.delivery_allowed is false",
        })

    for item in selected:
        candidate_id = _clean(item.get("candidate_id")) or "selected_audio"
        section_id = _clean(item.get("section_id"))
        section = sections.get(section_id)
        if sections and not section:
            blocking.append({
                "rule": "section_not_in_soundtrack_plan",
                "candidate_id": candidate_id,
                "section_id": section_id,
                "message": f"selected audio section_id is not in soundtrack_plan: {section_id}",
            })
            section = {}

        source_type = _clean(item.get("source_type"))
        license_status = _clean(item.get("license_status"))
        if source_type == "reference_only":
            blocking.append({
                "rule": "reference_only_source",
                "candidate_id": candidate_id,
                "message": "reference_only source cannot enter audio mix plan",
            })
        if item.get("delivery_allowed") is not True:
            blocking.append({
                "rule": "delivery_not_allowed",
                "candidate_id": candidate_id,
                "message": "selected audio is not delivery_allowed",
            })
        if license_status in BAD_LICENSE_STATUSES:
            blocking.append({
                "rule": "bad_license_status",
                "candidate_id": candidate_id,
                "message": f"selected audio license_status is {license_status}",
            })

        audio_path = _resolve_audio_path(item.get("audio_file"), out_root)
        if not audio_path.is_file():
            blocking.append({
                "rule": "audio_file_missing",
                "candidate_id": candidate_id,
                "audio_file": str(audio_path),
                "message": "selected audio_file does not exist",
            })

        vocal_policy = _clean((section or {}).get("vocal_policy") or item.get("vocal_policy"))
        ducking_policy = _clean(item.get("ducking_policy") or (section or {}).get("ducking_policy") or "none")
        if vocal_policy == "preserve_speech" and ducking_policy not in SPEECH_DUCKING_POLICIES:
            blocking.append({
                "rule": "speech_ducking_missing",
                "candidate_id": candidate_id,
                "section_id": section_id,
                "message": "preserve_speech section requires duck_under_voice or preserve_original_audio",
            })

        if audio_path.is_file() and source_type != "reference_only" and item.get("delivery_allowed") is True and license_status not in BAD_LICENSE_STATUSES:
            tracks.append({
                "section_id": section_id,
                "candidate_id": candidate_id,
                "audio_file": str(audio_path),
                "role": _role_for_track(item, section),
                "ducking_policy": ducking_policy,
                "usage_scope": item.get("usage_scope") or "unknown",
                "source_type": source_type,
                "license_status": license_status,
            })

    ok = not blocking
    mix_sections = _mix_sections(soundtrack_plan)
    acceptance = {
        "artifact_role": "audio_handoff_acceptance",
        "version": 1,
        "ok": ok,
        "blocking": blocking,
        "warnings": warnings,
        "accepted_track_count": len(tracks) if ok else 0,
        "next_action": "audio_mix_plan_ready" if ok else "repair_audio_handoff",
    }
    mix_plan = {
        "artifact_role": "audio_mix_plan",
        "version": 1,
        "ready_for_mix": ok,
        "tracks": tracks if ok else [],
        "sections": mix_sections if ok else [],
        "requires_ffmpeg": True,
        "rendered": False,
    }
    (out_root / "audio_handoff_acceptance.json").write_text(
        json.dumps(acceptance, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (out_root / "audio_mix_plan.json").write_text(
        json.dumps(mix_plan, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "audio_handoff_acceptance": acceptance,
        "audio_mix_plan": mix_plan,
    }


def accept_audio_handoff_files(
    handoff_path: str | Path,
    *,
    out_dir: str | Path,
    soundtrack_plan_path: str | Path | None = None,
    license_manifest_path: str | Path | None = None,
) -> dict[str, Any]:
    handoff = json.loads(Path(handoff_path).read_text(encoding="utf-8-sig"))
    soundtrack = None
    license_manifest = None
    if soundtrack_plan_path:
        soundtrack = json.loads(Path(soundtrack_plan_path).read_text(encoding="utf-8-sig"))
    if license_manifest_path:
        license_manifest = json.loads(Path(license_manifest_path).read_text(encoding="utf-8-sig"))
    return accept_audio_handoff(
        handoff,
        soundtrack_plan=soundtrack,
        sound_license_manifest=license_manifest,
        out_dir=out_dir,
    )
