"""visual_fatigue.py — Visual fatigue audit module (§Node 11).

Audits timeline builds against editing policies and checks for visual fatigue.
All functions are pure (no I/O, no print).
"""
from __future__ import annotations

import os
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Default Constants (Spec §Node 8 / §Node 11)
# ---------------------------------------------------------------------------

DEFAULT_PACING_BY_MODE = {
    "warm_documentary": [4.0, 8.0],
    "story_documentary": [3.0, 8.0],
    "rhythmic_mv": [1.5, 4.0],
    "training_recap": [2.5, 6.0],
}

DEFAULT_MAX_SINGLE_SOURCE_BY_MODE = {
    "warm_documentary": 12.0,
    "story_documentary": 10.0,
    "rhythmic_mv": 6.0,
    "training_recap": 8.0,
}

DEFAULT_MAX_STILL_HOLD_BY_MODE = {
    "warm_documentary": 7.0,
    "story_documentary": 6.0,
    "rhythmic_mv": 3.0,
    "training_recap": 4.0,
}

DEFAULT_SOURCE_REUSE = {
    "max_reuse_per_run": 2,
    "reuse_cooldown_sec": 25.0,
}

DEFAULT_MIN_SHOTS_PER_SEGMENT = 2


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _finding(check: str, level: str, message: str, route: str, segments=None) -> dict:
    """Create a single audit finding."""
    finding = {
        "check": check,
        "level": level,
        "message": message,
        "route": route,
    }
    if segments:
        finding["segments"] = list(dict.fromkeys(segments))
    return finding


def _has_reason(clip: dict) -> bool:
    """Check if a clip has a valid justification reason."""
    for key in ("shot_reason", "reason", "cut_reason"):
        val = clip.get(key)
        if val and isinstance(val, str) and val.strip():
            return True
    return False


def _is_still_image(clip: dict) -> bool:
    """Check if the clip is a still image."""
    if clip.get("media_type") == "photo":
        return True
    if clip.get("still_treatment") is not None:
        return True
    source = clip.get("source_path") or ""
    _, ext = os.path.splitext(source.lower())
    if ext in (".jpg", ".jpeg", ".png", ".webp", ".gif"):
        return True
    return False


def _has_still_treatment(clip: dict) -> bool:
    """Check if the clip has active still motion treatment."""
    treatment = clip.get("still_treatment")
    if not treatment:
        return False
    if isinstance(treatment, str) and treatment.lower() == "none":
        return False
    if isinstance(treatment, dict):
        mode = treatment.get("mode")
        if mode and str(mode).lower() != "none":
            return True
        return False
    return True


# ---------------------------------------------------------------------------
# Audit implementation
# ---------------------------------------------------------------------------

def audit_visual_fatigue(
    assembly_plan: dict,
    timeline_build: dict,
    editing_policy: dict | None = None,
) -> dict:
    """Audit the timeline build for visual fatigue.

    Args:
        assembly_plan: Node 9 assembly plan or segment contracts list.
        timeline_build: Node 10 timeline build containing clips.
        editing_policy: Optional build policy override thresholds.

    Returns:
        dict: {
            "artifact_role": "visual_fatigue_audit",
            "version": 1,
            "pass": bool,
            "findings": list of findings
        }
    """
    editing_policy = editing_policy or {}
    findings: list[dict] = []
    from .attention_budget import resolve_attention_budget

    # 1. Resolve Mode
    mode = (
        assembly_plan.get("mode")
        or assembly_plan.get("execution_plan", {}).get("mode")
        or timeline_build.get("mode")
        or editing_policy.get("default_mode")
    )
    if not mode:
        # Fallback check on segments
        segs = assembly_plan.get("segments") or []
        for s in segs:
            m = s.get("editing_intent", {}).get("mode")
            if m:
                mode = m
                break
    if not mode:
        mode = "warm_documentary"

    # 2. Extract Thresholds
    # target_shot_sec
    pacing_bounds = (
        editing_policy.get("target_shot_sec_by_mode", {}).get(mode)
        or DEFAULT_PACING_BY_MODE.get(mode)
        or [2.0, 8.0]
    )

    # max_single_source_sec
    max_single_source = (
        editing_policy.get("max_single_source_sec_by_mode", {}).get(mode)
        or DEFAULT_MAX_SINGLE_SOURCE_BY_MODE.get(mode)
        or 10.0
    )

    # max_still_hold_sec
    max_still_hold = (
        editing_policy.get("max_still_hold_sec_by_mode", {}).get(mode)
        or DEFAULT_MAX_STILL_HOLD_BY_MODE.get(mode)
        or 5.0
    )

    # source_reuse
    reuse_policy = editing_policy.get("source_reuse") or DEFAULT_SOURCE_REUSE
    max_reuse = reuse_policy.get("max_reuse_per_run", 2)
    cooldown = reuse_policy.get("reuse_cooldown_sec", 25.0)

    # min_shots_per_segment
    min_shots = editing_policy.get("min_shots_per_segment", DEFAULT_MIN_SHOTS_PER_SEGMENT)

    # 3. Extract and Sort Clips
    clips = timeline_build.get("clips") or []
    # Make a copy and sort by timeline_in_sec to ensure linear time processing
    sorted_clips = sorted(
        [c for c in clips if c.get("timeline_in_sec") is not None],
        key=lambda x: float(x["timeline_in_sec"]),
    )
    plan_segments = assembly_plan.get("segments") or []
    plan_by_segment = {
        s.get("segment"): s for s in plan_segments if s.get("segment") is not None
    }

    # -----------------------------------------------------------------------
    # Check A: single_source_fatigue (Consecutive same-source duration check)
    # -----------------------------------------------------------------------
    if sorted_clips:
        current_source = sorted_clips[0].get("source_path")
        current_group = [sorted_clips[0]]

        def check_group(group: list[dict], src: str | None):
            if not src:
                return
            tot_dur = sum(float(c.get("duration_sec") or 0) for c in group)
            if tot_dur > max_single_source:
                # Check if any clip in the group has a reason
                if not any(_has_reason(c) for c in group):
                    findings.append(_finding(
                        "single_source_fatigue",
                        "fail",
                        f"Source '{src}' consecutive duration {tot_dur:.2f}s "
                        f"exceeds mode '{mode}' limit of {max_single_source}s without reason.",
                        route="editor",
                        segments=[c.get("segment") for c in group if c.get("segment") is not None],
                    ))

        for clip in sorted_clips[1:]:
            src = clip.get("source_path")
            if src == current_source:
                current_group.append(clip)
            else:
                check_group(current_group, current_source)
                current_source = src
                current_group = [clip]
        check_group(current_group, current_source)

    # -----------------------------------------------------------------------
    # Check B: still_image_fatigue
    # -----------------------------------------------------------------------
    for clip in sorted_clips:
        if _is_still_image(clip):
            dur = float(clip.get("duration_sec") or 0)
            plan_segment = plan_by_segment.get(clip.get("segment")) or {}
            attention = resolve_attention_budget(
                plan_segment,
                mode=mode,
                is_still=True,
                has_motion=_has_still_treatment(clip),
            )
            narration_owns_time = (
                attention["owner"] == "narration"
                and dur <= attention["shot_sec"][1]
            )
            if dur > max_still_hold and not narration_owns_time:
                if not _has_still_treatment(clip) and not _has_reason(clip):
                    findings.append(_finding(
                        "still_image_fatigue",
                        "fail",
                        f"Still image '{clip.get('source_path')}' hold time {dur:.2f}s "
                        f"exceeds mode '{mode}' limit of {max_still_hold}s with no treatment or reason.",
                        route="editor/effects-director",
                        segments=[clip.get("segment")],
                    ))

    # -----------------------------------------------------------------------
    # Check C: shot_density_fit (per segment shot count check)
    # -----------------------------------------------------------------------
    # Collect segments from assembly plan
    seg_ids = [s.get("segment") for s in plan_segments if s.get("segment") is not None]
    if not seg_ids:
        # Fallback to unique segment IDs in clips
        seg_ids = list(set(c.get("segment") for c in sorted_clips if c.get("segment") is not None))

    for seg_id in seg_ids:
        seg_clips = [c for c in sorted_clips if c.get("segment") == seg_id]
        if len(seg_clips) < min_shots:
            findings.append(_finding(
                "shot_density_fit",
                "warn",
                f"Segment {seg_id} has {len(seg_clips)} shot(s), which is fewer "
                f"than the required {min_shots} for mode '{mode}'.",
                route="editor",
                segments=[seg_id],
            ))

    # -----------------------------------------------------------------------
    # Check D: source_repetition (reused too soon or too often)
    # -----------------------------------------------------------------------
    # Group all clip occurrences by source
    source_map: dict[str, list[dict]] = {}
    for clip in sorted_clips:
        src = clip.get("source_path")
        if src:
            source_map.setdefault(src, []).append(clip)

    for src, src_clips in source_map.items():
        # D1: Max reuse
        # Count unique segments using this source
        unique_segs = set(c.get("segment") for c in src_clips if c.get("segment") is not None)
        # Note: If no segments are defined, count clip occurrences
        use_count = len(unique_segs) if unique_segs else len(src_clips)
        if use_count > max_reuse:
            findings.append(_finding(
                "source_repetition",
                "warn",
                f"Source '{src}' is reused in {use_count} segments/clips, "
                f"exceeding the limit of {max_reuse}.",
                route="curator",
                segments=list(unique_segs),
            ))

        # D2: Cooldown check
        # For non-consecutive occurrences, check the gap between end of previous and start of next
        # Since we sorted sorted_clips, src_clips is also sorted by timeline_in_sec
        for i in range(len(src_clips) - 1):
            c1 = src_clips[i]
            c2 = src_clips[i + 1]
            t1_end = float(c1["timeline_in_sec"]) + float(c1.get("duration_sec") or 0)
            t2_start = float(c2["timeline_in_sec"])

            # Check if they are non-consecutive (i.e. another clip was cut in between)
            # We can verify if there's any clip in sorted_clips between c1 and c2
            idx1 = sorted_clips.index(c1)
            idx2 = sorted_clips.index(c2)
            if idx2 - idx1 > 1:
                # There is another clip between them
                gap = t2_start - t1_end
                if gap < cooldown:
                    findings.append(_finding(
                        "source_repetition",
                        "warn",
                        f"Source '{src}' reused too soon: gap of {gap:.2f}s "
                        f"is less than cooldown of {cooldown}s.",
                        route="curator",
                        segments=[c1.get("segment"), c2.get("segment")],
                    ))

    # -----------------------------------------------------------------------
    # Check E: pacing_fit (shot duration matches mode pacing range)
    # -----------------------------------------------------------------------
    min_pacing, max_pacing = pacing_bounds[0], pacing_bounds[1]
    for clip in sorted_clips:
        dur = float(clip.get("duration_sec") or 0)
        plan_segment = plan_by_segment.get(clip.get("segment")) or {}
        attention = resolve_attention_budget(
            plan_segment,
            mode=mode,
            is_still=_is_still_image(clip),
            has_motion=_has_still_treatment(clip),
        )
        att_min, att_max = attention["shot_sec"]
        has_attention_signal = bool(
            plan_segment.get("treatment")
            or plan_segment.get("still_motion")
            or plan_segment.get("execution_plan")
        )
        if has_attention_signal and (dur < att_min or dur > att_max):
            is_untreated_still = _is_still_image(clip) and not _has_still_treatment(clip)
            level = "fail" if attention["owner"] == "visual" and is_untreated_still else "warn"
            route = "editor/effects-director" if level == "fail" else "editor"
            findings.append(_finding(
                "attention_budget_fit",
                level,
                f"Shot duration {dur:.2f}s is outside attention budget "
                f"[{att_min}, {att_max}] owned by {attention['owner']}: {attention['reason']}.",
                route=route,
                segments=[clip.get("segment")],
            ))
        elif not has_attention_signal and (dur < min_pacing or dur > max_pacing):
            if not _has_reason(clip):
                findings.append(_finding(
                    "pacing_fit",
                    "warn",
                    f"Shot duration {dur:.2f}s is outside target pacing range "
                    f"[{min_pacing}, {max_pacing}] for mode '{mode}' and has no reason.",
                    route="editor",
                    segments=[clip.get("segment")],
                ))

    from .creative_exception import acknowledge, matching_exception
    for index, finding in enumerate(findings):
        candidates = [plan_by_segment.get(segment_id) for segment_id in finding.get("segments", [])]
        exception = matching_exception(finding["check"], *candidates)
        if exception:
            findings[index] = acknowledge(finding, exception)

    # Determine if audit passes
    has_fail = any(f["level"] == "fail" for f in findings)

    return {
        "artifact_role": "visual_fatigue_audit",
        "version": 1,
        "pass": not has_fail,
        "findings": findings,
    }
