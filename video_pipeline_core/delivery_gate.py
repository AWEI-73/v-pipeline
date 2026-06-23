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


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


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


def _source_quality_blocking(timeline_build: Any) -> list[dict[str, Any]]:
    clips = _timeline_clips(timeline_build)
    if len(clips) < 2:
        return []

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
        if count > 2 and (count_ratio > 0.50 or duration_ratio >= 0.35):
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


def evaluate_complete_video_delivery(root: str | Path, probe: dict[str, Any] | None = None) -> dict[str, Any]:
    """Validate a run folder as a complete deliverable video, not just a draft.

    This is intentionally stricter than the normal dashboard/workbench run-folder
    check. It only belongs at the final delivery boundary.
    """
    root = Path(root)
    blocking: list[dict[str, Any]] = []
    warnings: list[str] = []

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
    allow_narration_fallback = bool(requirements.get("allow_narration_fallback", False))
    requires_frame_evidence = bool(requirements.get("requires_frame_evidence", False)) or _is_real_material_route(root)
    requires_effect_render_verification = (
        bool(requirements.get("requires_effect_render_verification", False))
        or _effects_required(root)
    )
    language = _expected_language(requirements)

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
            blocking.append({
                "rule": "media_probe_failed",
                "tier": 1,
                "artifact": "final.mp4",
                "message": media_probe.get("error") or "ffprobe failed",
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

    narration_manifest = _load_json(root / "narration_manifest.json")
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

    music_manifest = _load_json(root / "music_manifest.json")
    if requires_music and not _manifest_has_items(music_manifest, "tracks", "cues"):
        blocking.append({
            "rule": "missing_music_manifest",
            "tier": 1,
            "artifact": "music_manifest.json",
            "message": "music is required but music_manifest.json has no tracks/cues",
            "next_action": "generate_or_attach_music",
        })

    audio_mix_report = _load_json(root / "audio_mix_report.json")
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

    subtitles_path = root / "subtitles.srt"
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
        elif "????" in subtitles:
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

    generated_material_review = _load_json(root / "generated_material_review.json")
    material_generation_fallback = _load_json(root / "material_generation_fallback.json")
    generated_provider_packet = _load_json(root / "generated_provider_packet.json")
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

    effect_render_verification = _load_json(root / "effect_render_verification.json")
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

    return {
        "artifact_role": "complete_video_delivery_gate",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "warnings": warnings,
        "next_action": blocking[0]["next_action"] if blocking else None,
        "summary": {
            "requires_audio": requires_audio,
            "requires_narration": requires_narration,
            "requires_music": requires_music,
            "requires_subtitles": requires_subtitles,
            "requires_frame_evidence": requires_frame_evidence,
            "requires_effect_render_verification": requires_effect_render_verification,
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
    coverage = (artifacts or {}).get("material_coverage") or {}
    material_ready = delta_ready or lifecycle_ready
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

    blocking.extend(_source_quality_blocking((artifacts or {}).get("timeline_build")))

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
