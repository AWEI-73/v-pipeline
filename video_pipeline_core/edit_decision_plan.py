from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


def _load_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    return data if isinstance(data, dict) else None


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _clip_start(clip: Mapping[str, Any]) -> float:
    return float(clip.get("start_sec", clip.get("source_in_sec", 0)) or 0)


def _clip_duration(clip: Mapping[str, Any]) -> float:
    if clip.get("duration_sec") is not None:
        return float(clip.get("duration_sec") or 0)
    if clip.get("source_out_sec") is not None:
        return max(0.0, float(clip.get("source_out_sec") or 0) - _clip_start(clip))
    return 0.0


def _compile_cuts(rough_cut: Mapping[str, Any] | None) -> list[dict[str, Any]]:
    cuts: list[dict[str, Any]] = []
    if not isinstance(rough_cut, Mapping):
        return cuts
    for idx, clip in enumerate(rough_cut.get("clips") or []):
        if not isinstance(clip, Mapping):
            continue
        start = _clip_start(clip)
        duration = _clip_duration(clip)
        source = clip.get("source_path") or clip.get("src") or clip.get("source")
        cuts.append({
            "id": str(clip.get("id") or f"cut_{idx + 1:03d}"),
            "source": source,
            "in_seconds": start,
            "out_seconds": start + duration,
            "target_duration_sec": duration,
            "layer": "primary",
            "segment": clip.get("segment"),
            "scene_id": clip.get("scene_id"),
            "need_id": clip.get("need_id"),
            "reason": clip.get("reason") or clip.get("caption") or "rough cut material selection",
        })
    return cuts


def _compile_audio(handoff: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not isinstance(handoff, Mapping):
        return {}, None
    selected = [item for item in handoff.get("selected_audio_files") or [] if isinstance(item, Mapping)]
    tracks = []
    for idx, item in enumerate(selected):
        tracks.append({
            "track_id": str(item.get("candidate_id") or item.get("section_id") or f"track_{idx + 1:03d}"),
            "section_id": item.get("section_id"),
            "asset_id": item.get("audio_file"),
            "source_type": item.get("source_type"),
            "license_note": item.get("license_note"),
            "music_role": item.get("music_role"),
            "vocal_policy": item.get("vocal_policy"),
            "ducking_policy": item.get("ducking_policy"),
        })
    decision = {
        "artifact_role": "audio_decision_plan",
        "version": 1,
        "ready": bool(handoff.get("ready_for_audio_director")),
        "source_audio_policy": handoff.get("speech_preservation") or handoff.get("source_audio_policy"),
        "tracks": tracks,
        "blocks": list(handoff.get("blocks") or []),
        "source_handoff": "audio_director_handoff.json",
    }
    music = {}
    if tracks:
        first = tracks[0]
        music = {
            "asset_id": first.get("asset_id"),
            "section_id": first.get("section_id"),
            "vocal_policy": first.get("vocal_policy"),
            "ducking": True,
            "fade_in_seconds": 1.0,
            "fade_out_seconds": 1.5,
        }
    return {"music": music} if music else {}, decision


def _compile_effects(handoff: Mapping[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, Any] | None]:
    if not isinstance(handoff, Mapping):
        return [], None
    effects = []
    for idx, item in enumerate(handoff.get("accepted_assets") or []):
        if not isinstance(item, Mapping):
            continue
        effect_id = str(item.get("effect_id") or item.get("job_id") or f"effect_{idx + 1:03d}")
        effects.append({
            "id": effect_id,
            "effect_id": effect_id,
            "asset_id": item.get("rendered_asset") or item.get("preview_file"),
            "duration_sec": item.get("duration_sec"),
            "story_function": item.get("story_function"),
            "evidence_refs": list(item.get("evidence_refs") or []),
        })
    decision = {
        "artifact_role": "effect_decision_plan",
        "version": 1,
        "status": handoff.get("status"),
        "effects": effects,
        "source_handoff": "effect_handoff.json",
        "boundary": dict(handoff.get("boundary") or {}),
    }
    return effects, decision


def _compile_subtitles(handoff: Mapping[str, Any] | None) -> tuple[dict[str, Any], dict[str, Any] | None]:
    if not isinstance(handoff, Mapping):
        return {}, None
    enabled = bool(handoff.get("subtitle_ready"))
    subtitle = {
        "enabled": enabled,
        "source": handoff.get("subtitles"),
        "language": handoff.get("language"),
        "position": "bottom-center",
        "style": "sentence",
    } if enabled else {"enabled": False}
    decision = {
        "artifact_role": "subtitle_voiceover_decision_plan",
        "version": 1,
        "subtitle_ready": bool(handoff.get("subtitle_ready")),
        "voiceover_ready": bool(handoff.get("voiceover_ready")),
        "language": handoff.get("language"),
        "subtitles": handoff.get("subtitles"),
        "narration_manifest": handoff.get("narration_manifest"),
        "source_handoff": "subtitle_voiceover_build_handoff.json",
    }
    return subtitle, decision


def _deferred(owner: str, reason: str) -> dict[str, Any]:
    return {
        "owner": owner,
        "reason": reason,
        "return_point": "before_build",
        "gate_status": "deferred",
    }


def compile_edit_decision_plan(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    rough_cut = _load_json(root / "rough_cut_plan.json") or _load_json(root / "preview_rough_cut_plan.json")
    audio_handoff = _load_json(root / "audio_director_handoff.json")
    effect_handoff = _load_json(root / "effect_handoff.json") or _load_json(root / "remotion_effect_handoff.json")
    subtitle_handoff = _load_json(root / "subtitle_voiceover_build_handoff.json")
    intent = _load_json(root / "video_intent.json") or {}

    cuts = _compile_cuts(rough_cut)
    audio, audio_decision = _compile_audio(audio_handoff)
    effects, effect_decision = _compile_effects(effect_handoff)
    subtitles, subtitle_decision = _compile_subtitles(subtitle_handoff)

    edit_decision = {
        "artifact_role": "edit_decision_plan",
        "version": 1,
        "source_intent": "video_intent.json" if intent else None,
        "video_type": intent.get("video_type"),
        "goal": intent.get("goal"),
        "cuts": cuts,
        "overlays": [],
        "audio": audio,
        "effects": effects,
        "subtitles": subtitles,
        "transitions": [],
        "review_focus": [
            "cuts trace to material evidence",
            "audio/effect/subtitle policies match Stage 0 intent",
            "deferred items are resolved before BUILD",
        ],
    }

    deferred_items: list[dict[str, Any]] = []
    accepted_handoffs: dict[str, str] = {}
    if audio_handoff:
        accepted_handoffs["audio"] = "audio_director_handoff.json"
    else:
        deferred_items.append(_deferred("soundtrack-arranger", "audio_director_handoff.json is absent"))
    if effect_handoff:
        accepted_handoffs["effect"] = "effect_handoff.json" if (root / "effect_handoff.json").is_file() else "remotion_effect_handoff.json"
    else:
        deferred_items.append(_deferred("effect-factory", "effect_handoff.json is absent"))
    if subtitle_handoff:
        accepted_handoffs["subtitle_voiceover"] = "subtitle_voiceover_build_handoff.json"
    else:
        deferred_items.append(_deferred("subtitle-voiceover", "subtitle_voiceover_build_handoff.json is absent"))
    if rough_cut:
        accepted_handoffs["material"] = "rough_cut_plan.json" if (root / "rough_cut_plan.json").is_file() else "preview_rough_cut_plan.json"
    else:
        deferred_items.append(_deferred("material-map", "rough_cut_plan.json is absent"))

    audio_decision = audio_decision or {
        "artifact_role": "audio_decision_plan",
        "version": 1,
        "ready": False,
        "tracks": [],
        "source_audio_policy": None,
        "deferred_reason": "audio_director_handoff.json is absent",
    }
    effect_decision = effect_decision or {
        "artifact_role": "effect_decision_plan",
        "version": 1,
        "status": "deferred",
        "effects": [],
        "deferred_reason": "effect_handoff.json is absent",
    }
    subtitle_decision = subtitle_decision or {
        "artifact_role": "subtitle_voiceover_decision_plan",
        "version": 1,
        "subtitle_ready": False,
        "voiceover_ready": False,
        "deferred_reason": "subtitle_voiceover_build_handoff.json is absent",
    }
    build_handoff = {
        "artifact_role": "build_handoff",
        "version": 1,
        "accepted_handoffs": accepted_handoffs,
        "deferred_items": deferred_items,
        "build_inputs": {
            "edit_decision_plan": "edit_decision_plan.json",
            "audio_decision_plan": "audio_decision_plan.json",
            "effect_decision_plan": "effect_decision_plan.json",
            "subtitle_voiceover_decision_plan": "subtitle_voiceover_decision_plan.json",
        },
        "forbidden_writes": ["final.mp4"],
        "ready_for_build": not deferred_items and bool(cuts),
    }

    artifacts = {
        "edit_decision_plan": edit_decision,
        "audio_decision_plan": audio_decision,
        "effect_decision_plan": effect_decision,
        "subtitle_voiceover_decision_plan": subtitle_decision,
        "build_handoff": build_handoff,
    }
    return artifacts


def write_product_artifacts(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir)
    root.mkdir(parents=True, exist_ok=True)
    artifacts = compile_edit_decision_plan(root)
    for key, payload in artifacts.items():
        _write_json(root / f"{key}.json", payload)
    return artifacts
