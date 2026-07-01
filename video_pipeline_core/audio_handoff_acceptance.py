"""No-render acceptance gate from Soundtrack Arranger to Audio Director."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


BAD_LICENSE_STATUSES = {"license_missing", "provider_unavailable", "reference_only"}
SPEECH_DUCKING_POLICIES = {"duck_under_voice", "preserve_original_audio"}
MUSIC_SOURCE_TYPES = {
    "licensed_library",
    "youtube_audio_library",
    "jamendo_song",
    "pixabay_music",
    "manual_import",
    "reviewed_manual",
}
STRICT_INSTRUMENTAL_POLICIES = {
    "instrumental_required",
    "instrumental_preferred",
    "no_vocal",
    "preserve_speech",
}
VOCAL_CONFLICT_DENSITIES = {"medium", "high"}


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


def _music_track_requires_probe(selected: Mapping[str, Any], section: Mapping[str, Any] | None) -> bool:
    section = section or {}
    if _clean(selected.get("ducking_policy") or section.get("ducking_policy")) == "preserve_original_audio":
        return False
    if _clean(selected.get("source_type")) in {"original_audio", "user_provided_original"}:
        return False
    role = _clean(section.get("music_role") or selected.get("music_role"))
    source_type = _clean(selected.get("source_type"))
    return role in {"bgm", "song", "music", "mixed"} or source_type in MUSIC_SOURCE_TYPES


def _same_path(left: Any, right: Path) -> bool:
    value = _clean(left)
    if not value:
        return False
    try:
        return Path(value).resolve() == right.resolve()
    except OSError:
        return str(Path(value)) == str(right)


def _probe_matches(
    report: Mapping[str, Any],
    *,
    selected_audio_file: Path,
    candidate_id: str,
    section_id: str,
) -> bool:
    report_candidate = _clean(report.get("candidate_id"))
    if report_candidate and report_candidate != candidate_id:
        return False

    report_section = _clean(report.get("section_id"))
    if report_section and section_id and report_section != section_id:
        return False

    report_audio = _clean(report.get("audio_file"))
    if report_audio and not _same_path(report_audio, selected_audio_file):
        return False

    return bool(report_candidate or report_section or report_audio)


def _select_probe_report(
    soundtrack_probe_report: Mapping[str, Any] | None,
    *,
    selected_audio_file: Path,
    candidate_id: str,
    section_id: str,
) -> Mapping[str, Any] | None:
    if not soundtrack_probe_report:
        return None

    track_reports = soundtrack_probe_report.get("track_reports")
    if isinstance(track_reports, list):
        for report in track_reports:
            if isinstance(report, Mapping) and _probe_matches(
                report,
                selected_audio_file=selected_audio_file,
                candidate_id=candidate_id,
                section_id=section_id,
            ):
                return report
        return None

    return soundtrack_probe_report


def _probe_blocks(
    *,
    soundtrack_probe_report: Mapping[str, Any] | None,
    selected_audio_file: Path,
    candidate_id: str,
) -> list[dict[str, Any]]:
    if not soundtrack_probe_report:
        return [{
            "rule": "missing_soundtrack_probe_report",
            "candidate_id": candidate_id,
            "message": "selected music must have soundtrack_probe_report.json before Audio Director handoff",
        }]
    if soundtrack_probe_report.get("pass") is not True:
        return [{
            "rule": "soundtrack_probe_not_passed",
            "candidate_id": candidate_id,
            "message": "soundtrack_probe_report.pass must be true before Audio Director handoff",
        }]
    section_fit = soundtrack_probe_report.get("section_fit")
    if not isinstance(section_fit, list) or not section_fit:
        return [{
            "rule": "soundtrack_probe_has_no_section_fit",
            "candidate_id": candidate_id,
            "message": "soundtrack_probe_report must include section_fit for music placement",
        }]
    features = soundtrack_probe_report.get("features")
    if not isinstance(features, Mapping) or not features:
        return [{
            "rule": "soundtrack_probe_has_no_features",
            "candidate_id": candidate_id,
            "message": "soundtrack_probe_report must include audio features for music placement",
        }]
    reported_audio = _clean(soundtrack_probe_report.get("audio_file"))
    if reported_audio:
        try:
            if Path(reported_audio).resolve() != selected_audio_file.resolve():
                return [{
                    "rule": "soundtrack_probe_audio_mismatch",
                    "candidate_id": candidate_id,
                    "message": "soundtrack_probe_report.audio_file does not match selected audio_file",
                }]
        except OSError:
            return [{
                "rule": "soundtrack_probe_audio_mismatch",
                "candidate_id": candidate_id,
                "message": "soundtrack_probe_report.audio_file cannot be resolved against selected audio_file",
            }]
    return []


def _requires_vocal_clearance(selected: Mapping[str, Any], section: Mapping[str, Any] | None) -> bool:
    section = section or {}
    vocal_policy = _clean(section.get("vocal_policy") or selected.get("vocal_policy")).casefold()
    ducking_policy = _clean(selected.get("ducking_policy") or section.get("ducking_policy")).casefold()
    if vocal_policy == "vocal_ok":
        return False
    return vocal_policy in STRICT_INSTRUMENTAL_POLICIES or ducking_policy == "duck_under_voice"


def _vocal_conflict_blocks(
    *,
    soundtrack_probe_report: Mapping[str, Any] | None,
    candidate_id: str,
    section_id: str,
) -> list[dict[str, Any]]:
    features = soundtrack_probe_report.get("features") if isinstance(soundtrack_probe_report, Mapping) else None
    vocal = features.get("vocal_analysis") if isinstance(features, Mapping) else None
    if not isinstance(vocal, Mapping):
        return [{
            "rule": "soundtrack_probe_missing_vocal_analysis",
            "candidate_id": candidate_id,
            "section_id": section_id,
            "message": (
                "instrumental or speech-underlay music requires soundtrack_probe "
                "with vocal_analysis; rerun with --enable-asr"
            ),
        }]

    has_vocals = vocal.get("has_vocals")
    method = _clean(vocal.get("method"))
    density = _clean(vocal.get("vocal_density")).casefold()
    if has_vocals == "unknown" or method in {"", "not_run", "faster_whisper_unavailable", "faster_whisper_error"}:
        return [{
            "rule": "soundtrack_probe_missing_vocal_analysis",
            "candidate_id": candidate_id,
            "section_id": section_id,
            "message": (
                "instrumental or speech-underlay music requires a completed vocal_analysis; "
                "rerun soundtrack_probe with --enable-asr"
            ),
        }]
    if has_vocals is True and density in VOCAL_CONFLICT_DENSITIES:
        return [{
            "rule": "vocal_music_conflicts_with_voiceover",
            "candidate_id": candidate_id,
            "section_id": section_id,
            "vocal_density": density,
            "vocal_ratio": vocal.get("vocal_ratio"),
            "instrumental_windows": vocal.get("instrumental_windows") or [],
            "message": (
                "selected music has medium/high detected vocals and cannot be used "
                "under voiceover or preserved speech"
            ),
        }]
    return []


def _source_audio_policy(
    soundtrack_plan: Mapping[str, Any] | None,
    tracks: list[dict[str, Any]],
    sections: Mapping[str, Mapping[str, Any]],
) -> dict[str, Any]:
    if soundtrack_plan and isinstance(soundtrack_plan.get("source_audio_policy"), Mapping):
        raw = soundtrack_plan["source_audio_policy"]
        return {
            "artifact_role": "audio_source_policy",
            "original_audio_policy": _clean(raw.get("original_audio_policy")) or "undecided",
            "music_policy": _clean(raw.get("music_policy")) or "undecided",
            "time_authority": _clean(raw.get("time_authority")) or "video_sections",
            "ducking_policy": _clean(raw.get("ducking_policy")) or "duck_under_voice",
        }

    roles = {_clean(track.get("role")) for track in tracks}
    ducking = {_clean(track.get("ducking_policy")) for track in tracks}
    section_music_roles = {
        _clean(section.get("music_role"))
        for section in sections.values()
        if _clean(section.get("music_role"))
    }
    if "mixed" in section_music_roles:
        music_policy = "mixed"
    elif "song" in section_music_roles:
        music_policy = "song"
    elif any(role in section_music_roles for role in ("bgm", "music")) or any(role.startswith("music") for role in roles):
        music_policy = "bgm"
    else:
        music_policy = "none"

    if "preserve_original_audio" in roles or "preserve_original_audio" in ducking:
        original_audio_policy = "preserve_speech"
    elif "music_ducked" in roles or "duck_under_voice" in ducking:
        original_audio_policy = "mixed"
    elif any(role.startswith("music") for role in roles) or "bgm" in section_music_roles or "song" in section_music_roles:
        original_audio_policy = "replace_with_music"
    else:
        original_audio_policy = "undecided"

    return {
        "artifact_role": "audio_source_policy",
        "original_audio_policy": original_audio_policy,
        "music_policy": music_policy,
        "time_authority": "video_sections",
        "ducking_policy": "duck_under_voice" if original_audio_policy in {"preserve_speech", "mixed"} else "none",
    }


def accept_audio_handoff(
    audio_director_handoff: Mapping[str, Any],
    *,
    soundtrack_plan: Mapping[str, Any] | None = None,
    sound_license_manifest: Mapping[str, Any] | None = None,
    soundtrack_probe_report: Mapping[str, Any] | None = None,
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
        if item.get("delivery_allowed") is True and _music_track_requires_probe(item, section):
            probe_report = _select_probe_report(
                soundtrack_probe_report,
                selected_audio_file=audio_path,
                candidate_id=candidate_id,
                section_id=section_id,
            )
            blocking.extend(
                _probe_blocks(
                    soundtrack_probe_report=probe_report,
                    selected_audio_file=audio_path,
                    candidate_id=candidate_id,
                )
            )
            if _requires_vocal_clearance(item, section):
                blocking.extend(
                    _vocal_conflict_blocks(
                        soundtrack_probe_report=probe_report,
                        candidate_id=candidate_id,
                        section_id=section_id,
                    )
                )

        if audio_path.is_file() and source_type != "reference_only" and item.get("delivery_allowed") is True and license_status not in BAD_LICENSE_STATUSES:
            track = {
                "section_id": section_id,
                "candidate_id": candidate_id,
                "audio_file": str(audio_path),
                "role": _role_for_track(item, section),
                "ducking_policy": ducking_policy,
                "usage_scope": item.get("usage_scope") or "unknown",
                "source_type": source_type,
                "license_status": license_status,
            }
            if item.get("delivery_allowed") is True and _music_track_requires_probe(item, section):
                probe_report = _select_probe_report(
                    soundtrack_probe_report,
                    selected_audio_file=audio_path,
                    candidate_id=candidate_id,
                    section_id=section_id,
                )
            else:
                probe_report = None
            if probe_report and _music_track_requires_probe(item, section):
                track["soundtrack_probe"] = {
                    "artifact": "soundtrack_probe_report.json",
                    "duration_sec": probe_report.get("duration_sec"),
                    "section_fit_count": len(probe_report.get("section_fit") or []),
                    "analysis_depth": probe_report.get("analysis_depth"),
                }
            tracks.append(track)

    ok = not blocking
    rules = {_clean(item.get("rule")) for item in blocking if isinstance(item, Mapping)}
    next_action = "audio_mix_plan_ready" if ok else "repair_audio_handoff"
    if not ok and any(rule.startswith("soundtrack_probe") or rule == "missing_soundtrack_probe_report" for rule in rules):
        next_action = "run_soundtrack_probe"
    if not ok and "soundtrack_probe_missing_vocal_analysis" in rules:
        next_action = "run_soundtrack_probe_with_asr"
    if not ok and "vocal_music_conflicts_with_voiceover" in rules:
        next_action = "select_instrumental_music_or_use_instrumental_window"
    mix_sections = _mix_sections(soundtrack_plan)
    source_audio_policy = _source_audio_policy(soundtrack_plan, tracks if ok else [], sections)
    acceptance = {
        "artifact_role": "audio_handoff_acceptance",
        "version": 1,
        "ok": ok,
        "blocking": blocking,
        "warnings": warnings,
        "accepted_track_count": len(tracks) if ok else 0,
        "next_action": next_action,
    }
    mix_plan = {
        "artifact_role": "audio_mix_plan",
        "version": 1,
        "ready_for_mix": ok,
        "source_audio_policy": source_audio_policy,
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
    soundtrack_probe_report_path: str | Path | None = None,
) -> dict[str, Any]:
    handoff = json.loads(Path(handoff_path).read_text(encoding="utf-8-sig"))
    soundtrack = None
    license_manifest = None
    if soundtrack_plan_path:
        soundtrack = json.loads(Path(soundtrack_plan_path).read_text(encoding="utf-8-sig"))
    if license_manifest_path:
        license_manifest = json.loads(Path(license_manifest_path).read_text(encoding="utf-8-sig"))
    soundtrack_probe_report = None
    if soundtrack_probe_report_path:
        soundtrack_probe_report = json.loads(Path(soundtrack_probe_report_path).read_text(encoding="utf-8-sig"))
    return accept_audio_handoff(
        handoff,
        soundtrack_plan=soundtrack,
        sound_license_manifest=license_manifest,
        soundtrack_probe_report=soundtrack_probe_report,
        out_dir=out_dir,
    )
