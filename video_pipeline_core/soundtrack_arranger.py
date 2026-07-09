"""Deterministic soundtrack planning and license handoff artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping

from .branch_env import build_branch_env_probe


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _text(*values: Any) -> str:
    chunks: list[str] = []
    for value in values:
        if isinstance(value, Mapping):
            chunks.extend(_clean(v) for v in value.values())
        elif isinstance(value, (list, tuple)):
            chunks.extend(_clean(v) for v in value)
        else:
            chunks.append(_clean(value))
    return " ".join(item for item in chunks if item).casefold()


def _has_any(text: str, tokens: tuple[str, ...]) -> bool:
    return any(token.casefold() in text for token in tokens)


_AUDIO_EXTENSIONS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".wma"}
_VIDEO_AUDIO_EXTENSIONS = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm"}
_SOURCE_MUSIC_TOKENS = (
    "music",
    "bgm",
    "sound",
    "audio",
    "theme",
    "\u97f3\u6a02",
    "\u914d\u6a02",
    "\u97f3\u6548",
    "\u7247\u982d",
)
_EXTERNAL_FALLBACK_PROVIDERS = ["jamendo", "yt-dlp"]
HUMAN_DECLARED_MUSIC_USE_STATUSES = {
    "human_declared_allowed",
    "human_declared_internal_use",
    "user_asserted_internal_use",
}
INTERNAL_MUSIC_USE_SCOPES = {
    "internal",
    "internal_only",
    "internal_review",
    "internal_rehearsal",
    "rehearsal",
    "review",
}


def _path_text(path: Path) -> str:
    return " ".join(part.casefold() for part in path.parts)


def _source_root_from_payload(payload: Mapping[str, Any]) -> str:
    for key in ("source_root", "material_source_root", "source_folder", "source_dir"):
        value = _clean(payload.get(key))
        if value:
            return value
    source = payload.get("source")
    if isinstance(source, Mapping):
        for key in ("root", "source_root", "folder", "path"):
            value = _clean(source.get(key))
            if value:
                return value
    return ""


def _music_use_basis_from_payload(payload: Mapping[str, Any], contract: Mapping[str, Any] | None = None) -> dict[str, Any] | None:
    contract = contract or {}
    raw = contract.get("music_use_basis") if isinstance(contract.get("music_use_basis"), Mapping) else None
    if raw is None and isinstance(payload.get("music_use_basis"), Mapping):
        raw = payload.get("music_use_basis")
    if raw is None:
        return None
    status = _clean(raw.get("status")).casefold()
    usage_scope = _clean(raw.get("usage_scope")).casefold()
    declared_by = _clean(raw.get("declared_by")).casefold()
    if status not in HUMAN_DECLARED_MUSIC_USE_STATUSES:
        return None
    if usage_scope not in INTERNAL_MUSIC_USE_SCOPES:
        return None
    if declared_by and declared_by not in {"human", "user", "operator"}:
        return None
    return {
        "status": "human_declared_allowed",
        "usage_scope": usage_scope,
        "declared_by": declared_by or "human",
        "basis_note": _clean(raw.get("basis_note") or raw.get("note")),
        "pipeline_legal_search_performed": bool(raw.get("pipeline_legal_search_performed")),
        "legal_approval_claimed": False,
        "external_publication_requires_rights_review": True,
    }


def _has_human_declared_internal_music_use(basis: Mapping[str, Any] | None) -> bool:
    if not basis:
        return False
    return (
        _clean(basis.get("status")).casefold() == "human_declared_allowed"
        and _clean(basis.get("usage_scope")).casefold() in INTERNAL_MUSIC_USE_SCOPES
        and basis.get("legal_approval_claimed") is False
    )


def _source_root_candidate_score(path: Path, relative_path: Path) -> tuple[int, list[str]]:
    suffix = path.suffix.casefold()
    text = _path_text(relative_path)
    signals: list[str] = []
    score = 0
    token_hits = [token for token in _SOURCE_MUSIC_TOKENS if token.casefold() in text]
    if not token_hits:
        return 0, []
    if suffix in _AUDIO_EXTENSIONS:
        score += 50
        signals.append("audio_extension")
    elif suffix in _VIDEO_AUDIO_EXTENSIONS:
        score += 20
        signals.append("video_container")
    else:
        return 0, []
    score += 30 + len(token_hits)
    signals.extend(f"name_signal:{token}" for token in token_hits)
    return score, signals


def discover_source_root_music(source_root: str | Path | None, *, max_candidates: int = 20) -> dict[str, Any]:
    """Find likely music/audio inside the active source root without provider calls."""
    root_text = _clean(source_root)
    fallback_intent = {
        "status": "external_fallback_available",
        "providers": list(_EXTERNAL_FALLBACK_PROVIDERS),
        "note": "Use sourceable external music search/download only when source-root music is absent or rejected.",
    }
    result: dict[str, Any] = {
        "artifact_role": "source_root_music_discovery",
        "version": 1,
        "source_root": root_text,
        "source_root_music_available": False,
        "selected_candidate": None,
        "candidates": [],
        "fallback_intent": fallback_intent,
        "legal_review_required": True,
        "legal_caveat": "Source-folder audio is source evidence, not a legal/music-use approval.",
    }
    if not root_text:
        result["status"] = "source_root_not_provided"
        return result

    root = Path(root_text)
    if not root.exists() or not root.is_dir():
        result["status"] = "source_root_missing"
        return result

    resolved_root = root.resolve()
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for path in resolved_root.rglob("*"):
        if not path.is_file():
            continue
        try:
            relative_path = path.resolve().relative_to(resolved_root)
        except ValueError:
            continue
        score, signals = _source_root_candidate_score(path, relative_path)
        if score <= 0:
            continue
        source_relative_path = relative_path.as_posix()
        candidate = {
            "candidate_id": f"source_root_music_{len(candidates) + 1}",
            "source_type": "source_folder_audio",
            "provider": "source_root",
            "path": str(path),
            "source_relative_path": source_relative_path,
            "file_name": path.name,
            "score": score,
            "signals": signals,
            "license_status": "source_folder_audio_requires_review",
            "delivery_allowed": False,
            "legal_review_required": True,
            "note": "source-root audio candidate; source evidence recorded, music-use/legal review still required",
        }
        candidates.append((-score, source_relative_path.casefold(), candidate))

    candidates.sort(key=lambda item: (item[0], item[1]))
    result["candidates"] = [candidate for _, _, candidate in candidates[:max_candidates]]
    if result["candidates"]:
        result["source_root_music_available"] = True
        result["status"] = "source_root_music_selected"
        result["selected_candidate"] = dict(result["candidates"][0])
        result["fallback_intent"] = {
            "status": "not_selected_source_root_available",
            "providers": list(_EXTERNAL_FALLBACK_PROVIDERS),
            "note": "External fallback remains available only if source-root candidate is rejected or fails probe.",
        }
    else:
        result["status"] = "source_root_music_absent"
    return result


def _target_duration_sec(value: Any, default: int = 300) -> int:
    if isinstance(value, bool) or value is None:
        return default
    if isinstance(value, (int, float)):
        return max(15, int(round(float(value))))
    text = _clean(value).casefold()
    match = re.search(r"(\d+(?:\.\d+)?)\s*(minutes?|mins?|min|分鐘|分)", text)
    if match:
        return max(15, int(round(float(match.group(1)) * 60)))
    match = re.search(r"(\d+(?:\.\d+)?)\s*(seconds?|secs?|sec|秒)", text)
    if match:
        return max(15, int(round(float(match.group(1)))))
    return default


def _split_duration(total_sec: int) -> dict[str, int]:
    if total_sec <= 150:
        return {
            "intro": max(8, int(total_sec * 0.12)),
            "warm_story": int(total_sec * 0.30),
            "training_drive": int(total_sec * 0.24),
            "mv_climax": int(total_sec * 0.26),
            "ending_reflection": max(8, int(total_sec * 0.08)),
        }
    return {
        "intro": min(30, max(12, int(total_sec * 0.10))),
        "warm_story": int(total_sec * 0.28),
        "training_drive": int(total_sec * 0.28),
        "mv_climax": int(total_sec * 0.24),
        "ending_reflection": total_sec,
    }


def _normalize_split(raw: dict[str, int], total_sec: int) -> dict[str, int]:
    fixed = dict(raw)
    if "ending_reflection" in fixed:
        fixed["ending_reflection"] = max(8, total_sec - sum(v for k, v in fixed.items() if k != "ending_reflection"))
    return fixed


def _speech_markers(payload: Mapping[str, Any], text: str) -> list[str]:
    markers = payload.get("speech_critical") or payload.get("preserve_audio") or []
    if isinstance(markers, str):
        markers = [markers]
    normalized = [_clean(item) for item in markers if _clean(item)]
    if _has_any(text, ("director speech", "主任", "致詞", "勉勵")) and "director speech" not in normalized:
        normalized.append("director speech")
    if _has_any(text, ("chant", "喊聲", "隊呼", "宣誓")) and "student chants" not in normalized:
        normalized.append("student chants")
    return normalized


def _base_sections(total_sec: int, text: str, speech_markers: list[str]) -> list[dict[str, Any]]:
    split = _normalize_split(_split_duration(total_sec), total_sec)
    sections: list[dict[str, Any]] = [
        {
            "section_id": "intro",
            "story_function": "intro",
            "duration_sec": split["intro"],
            "music_role": "bgm",
            "vocal_policy": "no_vocal",
            "energy_curve": "build",
            "ducking_policy": "duck_under_voice" if _has_any(text, ("voiceover", "旁白", "口白")) else "none",
            "source_type": "licensed_library",
            "license_status": "candidate_missing_license",
            "handoff_to": "audio-director",
        },
        {
            "section_id": "warm_story",
            "story_function": "warm_story",
            "duration_sec": split["warm_story"],
            "music_role": "bgm",
            "vocal_policy": "instrumental_required",
            "energy_curve": "low",
            "ducking_policy": "duck_under_voice",
            "source_type": "pixabay_music",
            "license_status": "candidate_missing_license",
            "handoff_to": "audio-director",
        },
        {
            "section_id": "training_drive",
            "story_function": "training_drive",
            "duration_sec": split["training_drive"],
            "music_role": "bgm",
            "vocal_policy": "no_vocal",
            "energy_curve": "medium",
            "ducking_policy": "duck_under_voice",
            "source_type": "pixabay_music",
            "license_status": "candidate_missing_license",
            "handoff_to": "audio-director",
        },
        {
            "section_id": "mv_climax",
            "story_function": "mv_climax",
            "duration_sec": split["mv_climax"],
            "music_role": "song" if _has_any(text, ("song", "vocal", "歌聲", "流行歌", "pop")) else "bgm",
            "vocal_policy": "vocal_ok" if _has_any(text, ("song", "vocal", "歌聲", "流行歌", "pop")) else "no_vocal",
            "energy_curve": "high" if _has_any(text, ("hot-blooded", "熱血", "mv", "澎湃", "爆發")) else "medium",
            "ducking_policy": "none",
            "source_type": "jamendo_song" if _has_any(text, ("song", "vocal", "歌聲", "流行歌", "pop")) else "licensed_library",
            "license_status": "candidate_missing_license",
            "handoff_to": "audio-director",
        },
        {
            "section_id": "ending_reflection",
            "story_function": "ending_reflection",
            "duration_sec": split["ending_reflection"],
            "music_role": "bgm",
            "vocal_policy": "instrumental_required",
            "energy_curve": "resolve",
            "ducking_policy": "duck_under_voice",
            "source_type": "licensed_library",
            "license_status": "candidate_missing_license",
            "handoff_to": "audio-director",
        },
    ]
    for marker in speech_markers:
        lower = marker.casefold()
        if _has_any(lower, ("director", "主任", "致詞", "勉勵")):
            sections.append(
                {
                    "section_id": "director_speech",
                    "story_function": "speech_preservation",
                    "duration_sec": 30,
                    "music_role": "bgm",
                    "vocal_policy": "preserve_speech",
                    "energy_curve": "low",
                    "ducking_policy": "duck_under_voice",
                    "source_type": "licensed_library",
                    "license_status": "candidate_missing_license",
                    "handoff_to": "audio-director",
                }
            )
        elif _has_any(lower, ("chant", "喊聲", "隊呼", "宣誓")):
            sections.append(
                {
                    "section_id": "student_chants",
                    "story_function": "diegetic_energy",
                    "duration_sec": 20,
                    "music_role": "diegetic",
                    "vocal_policy": "preserve_speech",
                    "energy_curve": "high",
                    "ducking_policy": "preserve_original_audio",
                    "source_type": "user_provided",
                    "license_status": "source_is_original_material",
                    "handoff_to": "audio-director",
                }
            )
    return sections


def _candidate_for_section(section: Mapping[str, Any], text: str) -> dict[str, Any]:
    famous_reference = _has_any(text, ("youtube", "famous", "很紅", "熱門", "流行歌", "pop song"))
    source_type = _clean(section.get("source_type"))
    if section.get("music_role") == "song" and famous_reference:
        source_type = "reference_only"
    delivery_allowed = source_type in {"user_provided"} or section.get("license_status") == "source_is_original_material"
    if source_type == "reference_only":
        delivery_allowed = False
    return {
        "candidate_id": f"music_{section.get('section_id')}",
        "section_id": section.get("section_id"),
        "source_type": source_type,
        "search_brief": {
            "story_function": section.get("story_function"),
            "music_role": section.get("music_role"),
            "vocal_policy": section.get("vocal_policy"),
            "energy_curve": section.get("energy_curve"),
        },
        "license_status": "reference_only" if source_type == "reference_only" else section.get("license_status"),
        "delivery_allowed": delivery_allowed,
        "note": "style reference only; do not mix into final" if source_type == "reference_only" else "candidate requires source/license evidence",
    }


def _stage0_soundtrack_contract(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    contract = payload.get("soundtrack_contract")
    return contract if isinstance(contract, Mapping) else {}


def _apply_stage0_soundtrack_contract(sections: list[dict[str, Any]], contract: Mapping[str, Any]) -> list[dict[str, Any]]:
    music_role = _clean(contract.get("music_role")).casefold()
    contract_status = _clean(contract.get("contract_status")).casefold()
    vocal_policy = _clean(contract.get("vocal_policy")).casefold()
    speech_preservation = _clean(contract.get("speech_preservation")).casefold()
    ducking_policy = _clean(contract.get("ducking_policy")) or "duck_under_voice"
    if contract_status == "not_applicable":
        music_role = "none"
    if music_role not in {"song", "bgm", "mixed", "none"}:
        return sections
    adjusted: list[dict[str, Any]] = []
    for section in sections:
        item = dict(section)
        is_climax = item.get("section_id") == "mv_climax"
        if music_role == "none":
            item.update({
                "music_role": "silence",
                "vocal_policy": "none",
                "source_type": "placeholder",
                "license_status": "not_required",
            })
        elif music_role == "bgm" and is_climax:
            item.update({
                "music_role": "bgm",
                "vocal_policy": "no_vocal" if vocal_policy in {"instrumental_preferred", "instrumental_required"} else "no_vocal",
                "source_type": "licensed_library",
                "license_status": "candidate_missing_license",
            })
        elif music_role in {"song", "mixed"} and is_climax:
            item.update({
                "music_role": "song",
                "vocal_policy": "vocal_ok",
                "source_type": "jamendo_song",
                "license_status": "candidate_missing_license",
            })
        if speech_preservation == "required" and item.get("music_role") == "bgm":
            item["ducking_policy"] = ducking_policy
        adjusted.append(item)
    return adjusted


def _source_type_priority(section: Mapping[str, Any]) -> list[str]:
    role = _clean(section.get("music_role")).casefold()
    source_type = _clean(section.get("source_type"))
    if role == "song":
        priority = ["jamendo_song", "manual_import", "reference_only"]
    elif role == "diegetic":
        priority = ["user_provided"]
    elif role == "silence":
        priority = ["placeholder"]
    else:
        priority = ["pixabay_music", "licensed_library", "manual_import"]
    if source_type and source_type not in priority:
        priority.insert(0, source_type)
    return priority


def _delivery_allowed_requires_license(section: Mapping[str, Any]) -> bool:
    source_type = _clean(section.get("source_type")).casefold()
    license_status = _clean(section.get("license_status")).casefold()
    role = _clean(section.get("music_role")).casefold()
    if role in {"silence", "diegetic"}:
        return False
    return not (
        source_type in {"user_provided", "placeholder"}
        or license_status in {"source_is_original_material", "not_required"}
    )


def _required_audio(section: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "role": section.get("music_role"),
        "story_function": section.get("story_function"),
        "duration_sec": section.get("duration_sec"),
        "vocal_policy": section.get("vocal_policy"),
        "energy_curve": section.get("energy_curve"),
        "ducking_policy": section.get("ducking_policy"),
        "speech_preservation": (
            "required"
            if section.get("vocal_policy") == "preserve_speech"
            or section.get("ducking_policy") in {"duck_under_voice", "preserve_original_audio"}
            else "not_required"
        ),
    }


def _enrich_section_requirements(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    enriched: list[dict[str, Any]] = []
    for section in sections:
        item = dict(section)
        item["required_audio"] = _required_audio(item)
        item["source_type_priority"] = _source_type_priority(item)
        item["probe_required"] = item.get("music_role") not in {"silence", "diegetic"}
        item["delivery_allowed_requires_license"] = _delivery_allowed_requires_license(item)
        enriched.append(item)
    return enriched


def _apply_source_root_music_priority(sections: list[dict[str, Any]], discovery: Mapping[str, Any]) -> list[dict[str, Any]]:
    if not discovery.get("source_root_music_available"):
        return sections
    adjusted: list[dict[str, Any]] = []
    for section in sections:
        item = dict(section)
        role = _clean(item.get("music_role")).casefold()
        if role in {"bgm", "song"}:
            priority = list(item.get("source_type_priority") or [])
            if "source_folder_audio" in priority:
                priority.remove("source_folder_audio")
            item["source_type_priority"] = ["source_folder_audio", *priority]
        adjusted.append(item)
    return adjusted


def _required_track_count(sections: list[Mapping[str, Any]]) -> int:
    roles: set[str] = set()
    for section in sections:
        role = _clean(section.get("music_role")).casefold()
        if role in {"bgm", "song"}:
            roles.add(role)
    return len(roles)


def _section_music_requirements(sections: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
    return [
        {
            "section_id": section.get("section_id"),
            "required_audio": section.get("required_audio"),
            "source_type_priority": section.get("source_type_priority"),
            "probe_required": section.get("probe_required"),
            "delivery_allowed_requires_license": section.get("delivery_allowed_requires_license"),
        }
        for section in sections
    ]


def _first_music_section_id(sections: list[Mapping[str, Any]]) -> str:
    for section in sections:
        if _clean(section.get("music_role")).casefold() in {"bgm", "song"}:
            return _clean(section.get("section_id"))
    return ""


def _source_root_candidate_for_plan(discovery: Mapping[str, Any], sections: list[Mapping[str, Any]]) -> dict[str, Any] | None:
    selected = discovery.get("selected_candidate")
    if not isinstance(selected, Mapping):
        return None
    section_id = _first_music_section_id(sections)
    if not section_id:
        return None
    candidate = dict(selected)
    candidate["candidate_id"] = f"music_{section_id}_source_root"
    candidate["section_id"] = section_id
    candidate["search_brief"] = {
        "story_function": "source_root_music_discovery",
        "music_role": "source_folder_audio",
        "vocal_policy": "requires_probe",
        "energy_curve": "unknown_until_probe",
    }
    candidate["note"] = "source-root candidate preferred before external fallback; legal/music-use review still required"
    candidate["delivery_allowed"] = False
    return candidate


def _apply_human_declared_music_use_to_candidate(candidate: dict[str, Any], basis: Mapping[str, Any] | None) -> dict[str, Any]:
    if not _has_human_declared_internal_music_use(basis):
        return candidate
    source_type = _clean(candidate.get("source_type")).casefold()
    if source_type not in {"source_folder_audio", "user_provided", "manual_import", "reviewed_manual"}:
        return candidate
    item = dict(candidate)
    item["license_status"] = "human_declared_allowed"
    item["music_use_status"] = "human_declared_internal_use"
    item["music_use_basis"] = dict(basis or {})
    item["usage_scope"] = basis.get("usage_scope")
    item["delivery_allowed"] = True
    item["legal_approval_claimed"] = False
    item["external_publication_requires_rights_review"] = True
    item["note"] = (
        "human-declared internal/rehearsal music use; source evidence recorded; "
        "legal approval is not claimed"
    )
    return item


def arrange_soundtrack(payload: Mapping[str, Any]) -> dict[str, Any]:
    text = _text(payload)
    total_sec = _target_duration_sec(payload.get("target_length") or payload.get("target_duration_sec") or payload.get("duration"))
    speech_markers = _speech_markers(payload, text)
    stage0_contract = dict(_stage0_soundtrack_contract(payload))
    music_use_basis = _music_use_basis_from_payload(payload, stage0_contract)
    sections = _apply_stage0_soundtrack_contract(
        _base_sections(total_sec, text, speech_markers),
        stage0_contract,
    )
    sections = _enrich_section_requirements(sections)
    source_root_music_discovery = discover_source_root_music(_source_root_from_payload(payload))
    sections = _apply_source_root_music_priority(sections, source_root_music_discovery)
    required_track_count = _required_track_count(sections)
    section_music_requirements = _section_music_requirements(sections)
    candidates = [
        _apply_human_declared_music_use_to_candidate(_candidate_for_section(section, text), music_use_basis)
        for section in sections
        if section.get("music_role") != "silence"
    ]
    source_root_candidate = _source_root_candidate_for_plan(source_root_music_discovery, sections)
    if source_root_candidate:
        candidates.insert(0, _apply_human_declared_music_use_to_candidate(source_root_candidate, music_use_basis))

    blocks: list[str] = []
    if any(candidate["source_type"] == "reference_only" for candidate in candidates):
        blocks.append("reference_only")
    if _has_human_declared_internal_music_use(music_use_basis):
        if candidates and not any(candidate.get("delivery_allowed") is True for candidate in candidates):
            blocks.append("license_missing")
    elif any(not candidate["delivery_allowed"] for candidate in candidates):
        blocks.append("license_missing")
    if any(
        section.get("vocal_policy") == "preserve_speech" and section.get("ducking_policy") not in {"duck_under_voice", "preserve_original_audio"}
        for section in sections
    ):
        blocks.append("speech_policy_missing")

    # Vocal Conflict Gate
    preserve_speech_globally = _clean(stage0_contract.get("speech_preservation")).casefold() == "required"
    for section in sections:
        role = _clean(section.get("music_role")).casefold()
        policy = _clean(section.get("vocal_policy")).casefold()
        required_audio = section.get("required_audio")
        required_vocal_policy = ""
        if isinstance(required_audio, Mapping):
            required_vocal_policy = _clean(required_audio.get("vocal_policy")).casefold()
        speech_sensitive = preserve_speech_globally or policy == "preserve_speech"
        uses_vocal_music = role == "song" or policy in {"vocal_ok", "vocal_required"} or required_vocal_policy in {"vocal_ok", "vocal_required"}
        if speech_sensitive and uses_vocal_music:
            blocks.append("vocal_conflict_detected")
            break

    fallback_policy = stage0_contract.get("fallback_policy") if isinstance(stage0_contract.get("fallback_policy"), Mapping) else {}
    if fallback_policy.get("role_fallback"):
        blocks.append("role_fallback_requires_review")

    soundtrack_plan = {
        "artifact_role": "soundtrack_plan",
        "version": 1,
        "target_duration_sec": total_sec,
        "required_track_count": required_track_count,
        "stage0_soundtrack_contract": stage0_contract,
        "sections": sections,
        "section_music_requirements": section_music_requirements,
        "source_root_music_discovery": source_root_music_discovery,
        "music_use_policy": {
            "music_use_basis": music_use_basis,
            "legal_approval_claimed": False,
            "external_publication_requires_rights_review": True,
        },
        "assumptions": [
            "provider search is optional; this plan is deterministic and does not require API tokens",
            "commercial/famous songs remain reference_only until license evidence is provided",
            (
                "source-folder or user-provided audio can be used for internal/rehearsal review "
                "when a human-declared music_use_basis is recorded; legal approval is not claimed"
            ),
        ],
        "handoff_to": "audio-director" if not blocks else "soundtrack_review",
    }
    music_source_candidates = {
        "artifact_role": "music_source_candidates",
        "version": 1,
        "candidates": candidates,
    }
    sound_license_manifest = {
        "artifact_role": "sound_license_manifest",
        "version": 1,
        "delivery_allowed": not blocks,
        "blocked_reasons": sorted(set(blocks)),
        "fallback_policy": fallback_policy,
        "music_use_basis": music_use_basis,
        "legal_approval_claimed": False,
        "external_publication_requires_rights_review": True,
        "sources": [
            {
                "candidate_id": candidate["candidate_id"],
                "source_type": candidate["source_type"],
                "license_status": candidate["license_status"],
                "delivery_allowed": candidate["delivery_allowed"],
                **({"music_use_status": candidate["music_use_status"]} if candidate.get("music_use_status") else {}),
                **({"music_use_basis": candidate["music_use_basis"]} if candidate.get("music_use_basis") else {}),
                **({"legal_approval_claimed": candidate["legal_approval_claimed"]} if "legal_approval_claimed" in candidate else {}),
                **({"path": candidate["path"]} if candidate.get("path") else {}),
                **({"source_relative_path": candidate["source_relative_path"]} if candidate.get("source_relative_path") else {}),
            }
            for candidate in candidates
        ],
    }
    audio_director_handoff = {
        "artifact_role": "audio_director_handoff",
        "version": 1,
        "handoff_to": "audio-director",
        "ready_for_audio_director": not blocks,
        "required_track_count": required_track_count,
        "blocks": sorted(set(blocks)),
        "speech_preservation": stage0_contract.get("speech_preservation"),
        "fallback_policy": fallback_policy,
        "music_use_basis": music_use_basis,
        "legal_approval_claimed": False,
        "external_publication_requires_rights_review": True,
        "sections": [
            {
                "section_id": section["section_id"],
                "music_role": section["music_role"],
                "vocal_policy": section["vocal_policy"],
                "ducking_policy": section["ducking_policy"],
                "required_audio": section.get("required_audio"),
                "source_type_priority": section.get("source_type_priority"),
                "probe_required": section.get("probe_required"),
                "delivery_allowed_requires_license": section.get("delivery_allowed_requires_license"),
                "source_type": next(
                    (candidate["source_type"] for candidate in candidates if candidate["section_id"] == section["section_id"]),
                    section["source_type"],
                ),
            }
            for section in sections
        ],
    }
    return {
        "soundtrack_plan": soundtrack_plan,
        "music_source_candidates": music_source_candidates,
        "sound_license_manifest": sound_license_manifest,
        "audio_director_handoff": audio_director_handoff,
    }


def write_soundtrack_artifacts(
    payload: Mapping[str, Any],
    out_dir: str | Path,
    *,
    repo_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    artifacts = arrange_soundtrack(payload)
    artifacts["soundtrack_branch_env_probe"] = build_branch_env_probe(repo_root=repo_root, env=env)
    for name, artifact in artifacts.items():
        (out_root / f"{name}.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    blocks = artifacts.get("audio_director_handoff", {}).get("blocks", [])
    if blocks:
        from .revision_packet_schema import RevisionPacket
        revision_targets = []
        for block in blocks:
            revision_targets.append({
                "artifact": "soundtrack_plan.json",
                "field": "sections",
                "issue": f"Soundtrack arranger blocked on: {block}",
                "suggested_change": "adjust_ducking" if block == "speech_policy_missing" else "choose_instrumental_bgm" if block == "vocal_conflict_detected" else "provide_license"
            })

        packet = RevisionPacket(
            source_review="soundtrack_plan.json",
            target_branch="soundtrack-arranger",
            problem_type="audio",
            severity="blocking",
            revision_targets=revision_targets,
            allowed_actions=["patch_contract", "rerun_branch", "ask_user", "route_back", "stop"],
            forbidden_actions=["overwrite_final_mp4", "mutate_material_truth", "silently_downgrade_required_feature"],
            rerun_policy={
                "allowed": True,
                "max_attempts": 1,
                "requires_agent_decision": True
            }
        )
        packet.save(out_root / "soundtrack_revision_packet.json")

    return artifacts
