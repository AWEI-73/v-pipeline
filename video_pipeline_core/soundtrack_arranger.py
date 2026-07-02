"""Deterministic soundtrack planning and license handoff artifacts."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, Mapping


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


def arrange_soundtrack(payload: Mapping[str, Any]) -> dict[str, Any]:
    text = _text(payload)
    total_sec = _target_duration_sec(payload.get("target_length") or payload.get("target_duration_sec") or payload.get("duration"))
    speech_markers = _speech_markers(payload, text)
    stage0_contract = dict(_stage0_soundtrack_contract(payload))
    sections = _apply_stage0_soundtrack_contract(
        _base_sections(total_sec, text, speech_markers),
        stage0_contract,
    )
    sections = _enrich_section_requirements(sections)
    required_track_count = _required_track_count(sections)
    section_music_requirements = _section_music_requirements(sections)
    candidates = [_candidate_for_section(section, text) for section in sections if section.get("music_role") != "silence"]

    blocks: list[str] = []
    if any(candidate["source_type"] == "reference_only" for candidate in candidates):
        blocks.append("reference_only")
    if any(not candidate["delivery_allowed"] for candidate in candidates):
        blocks.append("license_missing")
    if any(
        section.get("vocal_policy") == "preserve_speech" and section.get("ducking_policy") not in {"duck_under_voice", "preserve_original_audio"}
        for section in sections
    ):
        blocks.append("speech_policy_missing")
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
        "assumptions": [
            "provider search is optional; this plan is deterministic and does not require API tokens",
            "commercial/famous songs remain reference_only until license evidence is provided",
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
        "sources": [
            {
                "candidate_id": candidate["candidate_id"],
                "source_type": candidate["source_type"],
                "license_status": candidate["license_status"],
                "delivery_allowed": candidate["delivery_allowed"],
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


def write_soundtrack_artifacts(payload: Mapping[str, Any], out_dir: str | Path) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    artifacts = arrange_soundtrack(payload)
    for name, artifact in artifacts.items():
        (out_root / f"{name}.json").write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    return artifacts
