"""treatment_audit.py — Node 11 treatment-fit audit (§Node 11 of material-treatment-grammar-spec).

Audits whether the rendered timeline_build actually matches the declared
treatment from the assembly_plan. All functions are pure (no I/O, no print).

Checks:
  treatment_fit  — structural match between declared treatment and rendered clips
  label_pairing  — per-item-label treatments have labels on each clip
  beat_lock      — stack/bridge cut times align to beat grid

Spec source: docs/material-treatment-grammar-spec.md §Node 11
"""
from __future__ import annotations

from typing import Optional

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding(check: str, level: str, message: str, route: str | None = None) -> dict:
    """Create a single audit finding."""
    return {
        "check": check,
        "level": level,
        "message": message,
        "route": route,
    }


def _clips_for_segment(timeline_build: dict, seg_id) -> list[dict]:
    """Extract clips belonging to a specific segment from timeline_build."""
    clips = timeline_build.get("clips") or []
    return [c for c in clips if c.get("segment") == seg_id]


def _segments_from_plan(assembly_plan: dict) -> list[dict]:
    """Extract segment entries from assembly_plan."""
    return assembly_plan.get("segments") or []


def _get_treatment(seg_plan: dict) -> str | None:
    """Get the resolved treatment for a planned segment."""
    return seg_plan.get("treatment")


def _get_n_required(seg_plan: dict) -> int | None:
    """Get the expected item/slot count from the plan."""
    return seg_plan.get("n_required")


def _get_items(seg_plan: dict) -> list:
    """Get declared items list for enumeration / per-item-label segments."""
    return seg_plan.get("items") or []


def _get_labels_required(seg_plan: dict) -> bool:
    """Whether this segment plan requires per-item labels."""
    return bool(seg_plan.get("label_per_item"))


def _get_beat_grid(seg_plan: dict) -> list[float]:
    """Get beat timestamps associated with this segment's plan."""
    return seg_plan.get("beat_grid") or []


def _clip_has_label(clip: dict) -> bool:
    """Check if a timeline clip carries a label (text_overlay or label field)."""
    if clip.get("label"):
        return True
    overlay = clip.get("text_overlay")
    if overlay and overlay != "none":
        return True
    return False


# ---------------------------------------------------------------------------
# Individual checks
# ---------------------------------------------------------------------------


def _check_treatment_fit(
    seg_plan: dict,
    rendered_clips: list[dict],
) -> list[dict]:
    """Check that rendered clips structurally match the declared treatment.

    Failures:
      - enumeration/photo_stack_beat rendered as single hold → fail (collapsed stack)
      - stack item count ≠ expected n_required → fail
      - bridge rendered as one long shot → fail (no compression)
    """
    findings: list[dict] = []
    treatment = _get_treatment(seg_plan)
    n_required = _get_n_required(seg_plan)
    seg_id = seg_plan.get("segment")
    n_clips = len(rendered_clips)

    if treatment == "photo_stack_beat":
        # Enumeration rendered as a single hold
        if n_clips <= 1 and (n_required is None or n_required > 1):
            findings.append(_finding(
                "treatment_fit", "fail",
                f"segment {seg_id}: enumeration (photo_stack_beat) collapsed to "
                f"{n_clips} clip(s), expected stack of {n_required or '>1'}",
                route="editor",
            ))
        # Stack item count mismatch
        if n_required is not None and n_clips != n_required and n_clips > 1:
            findings.append(_finding(
                "treatment_fit", "fail",
                f"segment {seg_id}: stack has {n_clips} clips but expected {n_required} items",
                route="editor",
            ))

    elif treatment == "quick_cut_bridge":
        # Bridge rendered as one long shot
        if n_clips <= 1:
            findings.append(_finding(
                "treatment_fit", "fail",
                f"segment {seg_id}: bridge collapsed to {n_clips} clip, "
                f"expected 2-4 quick cuts",
                route="editor",
            ))

    elif treatment == "single_hold":
        # single_hold chopped into a montage → warn (fought the intent)
        if n_clips > 1:
            findings.append(_finding(
                "treatment_fit", "warn",
                f"segment {seg_id}: single_hold emotional shot chopped into "
                f"{n_clips} clips (fought the intent)",
                route="editor",
            ))

    return findings


def _check_label_pairing(
    seg_plan: dict,
    rendered_clips: list[dict],
) -> list[dict]:
    """Check that per-item-label treatments have labels on each clip."""
    findings: list[dict] = []
    treatment = _get_treatment(seg_plan)
    seg_id = seg_plan.get("segment")

    # Only treatments that require per-item labels
    if treatment not in ("photo_stack_beat",) and not _get_labels_required(seg_plan):
        return findings

    labels_required = _get_labels_required(seg_plan)
    if not labels_required and treatment != "photo_stack_beat":
        return findings

    # For photo_stack_beat, labels are expected by default from the spec
    # (per-item label captions); explicit label_per_item=true makes it hard fail
    for clip in rendered_clips:
        if not _clip_has_label(clip):
            findings.append(_finding(
                "label_pairing", "fail",
                f"segment {seg_id}: per-item-label treatment missing label on clip "
                f"(source: {clip.get('source_path', '?')})",
                route="writer",
            ))

    return findings


def _check_beat_lock(
    seg_plan: dict,
    rendered_clips: list[dict],
    beat_tolerance_sec: float = 0.15,
) -> list[dict]:
    """Check that stack/bridge cut points align to the beat grid.

    Uses the beat_grid timestamps from the plan and checks if each clip's
    timeline_in_sec is close to a beat time.
    """
    findings: list[dict] = []
    treatment = _get_treatment(seg_plan)
    seg_id = seg_plan.get("segment")

    if treatment not in ("photo_stack_beat", "quick_cut_bridge"):
        return findings

    beat_grid = _get_beat_grid(seg_plan)
    if not beat_grid:
        return findings  # No beat grid to check against

    for clip in rendered_clips:
        t_in = clip.get("timeline_in_sec")
        if t_in is None:
            continue
        t_in = float(t_in)
        # Check if t_in is close to any beat
        aligned = any(
            abs(t_in - float(beat)) <= beat_tolerance_sec
            for beat in beat_grid
        )
        if not aligned:
            findings.append(_finding(
                "beat_lock", "warn",
                f"segment {seg_id}: clip at {t_in:.3f}s not aligned to any beat "
                f"(nearest beats: {[round(float(b), 3) for b in beat_grid[:5]]}…)",
                route="editor",
            ))

    return findings


# ---------------------------------------------------------------------------
# Main audit entry point
# ---------------------------------------------------------------------------


def audit_treatment(
    assembly_plan: dict,
    timeline_build: dict,
    *,
    beat_tolerance_sec: float = 0.15,
) -> dict:
    """Audit that the rendered timeline matches the declared treatments.

    Args:
        assembly_plan:  Node 9 assembly plan with resolved treatments per segment.
        timeline_build: Node 10 timeline with concrete clips.
        beat_tolerance_sec: Tolerance for beat-lock alignment check.

    Returns a dict:
        artifact_role:  "treatment_audit"
        version:        1
        pass:           bool — True if no fail-level findings
        findings:       list of {check, level, message, route}
    """
    all_findings: list[dict] = []

    for seg_plan in _segments_from_plan(assembly_plan):
        seg_id = seg_plan.get("segment")
        treatment = _get_treatment(seg_plan)
        if treatment is None:
            continue  # No treatment declared, skip

        rendered_clips = _clips_for_segment(timeline_build, seg_id)

        # treatment_fit
        all_findings.extend(_check_treatment_fit(seg_plan, rendered_clips))

        # label_pairing
        all_findings.extend(_check_label_pairing(seg_plan, rendered_clips))

        # beat_lock
        all_findings.extend(
            _check_beat_lock(seg_plan, rendered_clips, beat_tolerance_sec)
        )

    has_fail = any(f["level"] == "fail" for f in all_findings)

    return {
        "artifact_role": "treatment_audit",
        "version": 1,
        "pass": not has_fail,
        "findings": all_findings,
    }
