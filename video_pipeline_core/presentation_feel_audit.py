"""Deterministic anti-presentation-feel audit for Node 12."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .visual_fatigue import DEFAULT_MAX_STILL_HOLD_BY_MODE


PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


def _finding(check, level, message, affected=None):
    return {
        "check": check,
        "level": level,
        "message": message,
        "affected": affected or [],
        "fix_class": "editorial",
        "next_route": "editor/effects-director",
    }


def _is_photo(clip):
    if clip.get("media_type") == "photo" or clip.get("still_treatment") is not None:
        return True
    return os.path.splitext(str(clip.get("source_path") or "").lower())[1] in PHOTO_EXTS


def _has_text(clip):
    text = clip.get("text_overlay")
    if isinstance(text, dict):
        return any(value for value in text.values())
    return bool(text and str(text).strip().lower() != "none")


def _is_text_block(clip):
    text = clip.get("text_overlay")
    area = float(clip.get("text_area_ratio") or 0.0)
    return area > 0.25 or (isinstance(text, dict) and bool(text.get("narrative")))


def _treatment_mode(clip):
    treatment = clip.get("still_treatment")
    if isinstance(treatment, dict):
        return treatment.get("mode")
    return treatment if isinstance(treatment, str) else None


def _layer_count(clip):
    if clip.get("composition_layers") is not None:
        return int(clip["composition_layers"])
    return 1 + int(_has_text(clip)) + int(bool(clip.get("effect_overlays")))


def _default_motion_probe(clip):
    source = clip.get("source_path")
    if not source or not os.path.exists(source) or _is_photo(clip):
        return None
    from .mv_cut import window_static_ratio
    return window_static_ratio(
        source,
        float(clip.get("start_sec") or 0.0),
        float(clip.get("duration_sec") or 0.0),
    )


def audit_presentation_feel(assembly_plan, timeline_build, editing_policy=None, motion_probe=None):
    """Return mechanical findings for common presentation-like video patterns."""
    policy = editing_policy or {}
    motion_probe = motion_probe or _default_motion_probe
    mode = (
        (assembly_plan or {}).get("mode")
        or (assembly_plan or {}).get("execution_plan", {}).get("mode")
        or "warm_documentary"
    )
    max_still = (
        policy.get("max_still_hold_sec_by_mode", {}).get(mode)
        or DEFAULT_MAX_STILL_HOLD_BY_MODE.get(mode)
        or 5.0
    )
    max_static_ratio = float(policy.get("presentation_max_static_ratio", 0.85))
    max_text_ratio = float(policy.get("presentation_max_text_block_ratio", 0.5))
    repeated_treatment_limit = int(policy.get("presentation_repeated_treatment_limit", 3))
    single_layer_limit = int(policy.get("presentation_single_layer_limit", 3))

    clips = sorted(
        (timeline_build or {}).get("clips") or [],
        key=lambda clip: float(clip.get("timeline_in_sec") or 0.0),
    )
    segments = {
        segment.get("segment"): segment
        for segment in ((assembly_plan or {}).get("segments") or [])
        if segment.get("segment") is not None
    }
    findings = []

    for clip in clips:
        duration = float(clip.get("duration_sec") or 0.0)
        if _is_photo(clip) and duration > max_still:
            findings.append(_finding(
                "static_photo_too_long",
                "fail",
                f"Still source exceeds {mode} hold limit: {duration:.2f}s > {max_still:.2f}s.",
                [clip.get("segment")],
            ))
        if not _is_photo(clip):
            ratio = motion_probe(clip)
            if ratio is not None and float(ratio) >= max_static_ratio:
                findings.append(_finding(
                    "no_foreground_motion",
                    "fail",
                    f"Video source is visually static for {float(ratio):.0%} of the sampled window.",
                    [clip.get("segment")],
                ))

        segment = segments.get(clip.get("segment")) or {}
        placement = (
            segment.get("execution_plan", {}).get("subtitles", {}).get("placement")
            or clip.get("text_placement")
        )
        if placement in {"center", "centered", "middle"} and _is_text_block(clip):
            findings.append(_finding(
                "centered_caption_card",
                "fail",
                "Centered text block dominates the frame.",
                [clip.get("segment")],
            ))

    modes = [_treatment_mode(clip) for clip in clips]
    for index in range(len(modes) - repeated_treatment_limit + 1):
        run = modes[index:index + repeated_treatment_limit]
        if run[0] and len(set(run)) == 1:
            affected = [clip.get("segment") for clip in clips[index:index + repeated_treatment_limit]]
            findings.append(_finding(
                "repeated_push_in",
                "fail",
                f"Treatment '{run[0]}' repeats {repeated_treatment_limit} times consecutively.",
                affected,
            ))
            break

    total_duration = sum(float(clip.get("duration_sec") or 0.0) for clip in clips)
    text_duration = sum(
        float(clip.get("duration_sec") or 0.0) for clip in clips if _is_text_block(clip)
    )
    if total_duration and text_duration / total_duration > max_text_ratio:
        findings.append(_finding(
            "text_blocks_dominate",
            "fail",
            f"Text-block duration ratio {text_duration / total_duration:.0%} exceeds {max_text_ratio:.0%}.",
        ))

    for index in range(len(clips) - single_layer_limit + 1):
        run = clips[index:index + single_layer_limit]
        if all(_layer_count(clip) <= 1 for clip in run):
            findings.append(_finding(
                "single_layer_composition",
                "warn",
                f"{single_layer_limit} consecutive clips use a single composition layer.",
                [clip.get("segment") for clip in run],
            ))
            break

    fail_count = sum(finding["level"] == "fail" for finding in findings)
    warn_count = sum(finding["level"] == "warn" for finding in findings)
    return {
        "artifact_role": "presentation_feel_audit",
        "version": 1,
        "pass": fail_count == 0,
        "score": max(0, 100 - fail_count * 20 - warn_count * 10),
        "findings": findings,
        "next_action": "fix_timeline_or_assembly" if fail_count else None,
    }


def write_presentation_feel_audit(
    assembly_plan, timeline_build, out_path, editing_policy=None, motion_probe=None
):
    payload = audit_presentation_feel(
        assembly_plan,
        timeline_build,
        editing_policy=editing_policy,
        motion_probe=motion_probe,
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return str(out_path)
