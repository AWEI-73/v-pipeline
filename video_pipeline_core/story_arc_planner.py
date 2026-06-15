"""SRP3 — Story Arc / Emotional Progression Planner.

A whole-film-level, SHALLOW, DETERMINISTIC planner. It assigns story-arc roles to
the EXISTING script segments and suggests per-segment intensity / pace / relative
weight as BUILD planning hints. It is NOT an auto-director and does NOT understand
story semantics: roles are derived from segment ORDER and explicit manual metadata
only.

SRP3 never: re-picks material, touches the material map, changes correctness
ranking, reorders/drops segments, rewrites script text, invents segments, calls
ffmpeg, or builds a hard gate. Manual intent always wins — SRP3 only fills in
missing hints. The output is a runtime-ephemeral plan; it is NOT a new canonical
schema/artifact. The final duration decision still belongs to `allocate_segments`.
"""
from __future__ import annotations

# Default hints per arc role (shallow, order-based — not semantic understanding).
ARC_DEFAULTS = {
    "setup":       {"intensity": 2, "pace_hint": "steady", "weight_multiplier": 0.9},
    "challenge":   {"intensity": 3, "pace_hint": "steady", "weight_multiplier": 1.0},
    "progression": {"intensity": 4, "pace_hint": "fast",   "weight_multiplier": 1.1},
    "climax":      {"intensity": 5, "pace_hint": "fast",   "weight_multiplier": 1.3},
    "resolution":  {"intensity": 2, "pace_hint": "hold",   "weight_multiplier": 1.0},
}
_NEUTRAL_HINT = {"intensity": 3, "pace_hint": "steady", "weight_multiplier": 1.0}

# Segments whose necessary duration must never be reduced by a weight multiplier.
_DURATION_PROTECTED_AUDIO = ("source_speech", "diegetic", "duck")


def _na(reason, segments=None):
    evidence = {}
    if isinstance(segments, list):
        evidence["segment_count"] = len(segments)
    return {"status": "not_applicable", "segment_hints": [],
            "evidence": evidence, "reason": reason}


def _auto_roles(n):
    """Deterministic order-based arc roles scaled to the segment count."""
    if n == 3:
        return ["setup", "climax", "resolution"]
    if n == 4:
        return ["setup", "challenge", "climax", "resolution"]
    if n == 5:
        return ["setup", "challenge", "progression", "climax", "resolution"]
    # n >= 6: first=setup, last=resolution, second-to-last=climax; the middle is
    # split deterministically into an earlier challenge block and a later
    # progression block (progression sits closer to the climax).
    roles = [None] * n
    roles[0] = "setup"
    roles[-1] = "resolution"
    roles[-2] = "climax"
    middle = list(range(1, n - 2))          # indices 1 .. n-3
    split = (len(middle) + 1) // 2          # earlier (ceil) half = challenge
    for i in middle[:split]:
        roles[i] = "challenge"
    for i in middle[split:]:
        roles[i] = "progression"
    return roles


def _has_requested_duration(s):
    try:
        return float(s.get("requested_duration_sec")) > 0
    except (TypeError, ValueError):
        return False


def _is_duration_protected(s):
    """A hold / source_speech / diegetic / duck / keep_audio segment has load-
    bearing duration and audio semantics. SRP3 must never apply a BUILD-rhythm-
    changing auto hint to it — no auto `weight`, no auto `pace` (trace-only
    arc_role / arc_intensity is still allowed). Covers `hold` and `hold_reason`."""
    return bool(s.get("hold") or s.get("hold_reason") or s.get("keep_audio")
                or s.get("audio_role") in _DURATION_PROTECTED_AUDIO)


def _has_manual_intensity(s):
    """A segment that already declares manual intensity (`intensity` or
    `arc_intensity`) owns it — SRP3 must not write a conflicting auto value."""
    for key in ("intensity", "arc_intensity"):
        if key in s and s[key] is not None:
            return True
    return False


def _segment_identity(s):
    """Return a stable, non-empty segment identity, or None when invalid. SRP3
    requires every segment to carry one (no segment_index fallback for the runtime
    trace join). Accepts a non-bool int/float or a non-blank string (trimmed)."""
    if not isinstance(s, dict) or "segment" not in s:
        return None
    v = s["segment"]
    if v is None or isinstance(v, bool):
        return None
    if isinstance(v, str):
        v = v.strip()
        return v or None
    if isinstance(v, (int, float)):
        return v
    return None


def plan_story_arc(script, *, policy=None):
    """Plan a shallow deterministic story arc over the script's segments.

    Returns a runtime-ephemeral plan:
    {
      "status": "planned" | "not_applicable",
      "segment_hints": [ {segment_ref, segment_index, arc_role, intensity,
                          pace_hint, weight_multiplier, manual_role, reason} ],
      "evidence": {...},
      "reason": "...",
    }
    Pure function — never mutates `script`.
    """
    script = script or {}
    # Disable flags — explicit director opt-out keeps the existing flow unchanged.
    if script.get("story_arc") is False or script.get("disable_auto_story_arc") is True:
        return _na("auto story arc disabled by script flag", script.get("segments"))

    segments = script.get("segments")
    if not isinstance(segments, list):
        return _na("no segments list")
    n = len(segments)
    if n < 3:
        return _na(f"need at least 3 segments to form an arc, got {n}", segments)
    if not all(isinstance(s, dict) for s in segments):
        return _na("non-object segment present (invalid script shape)", segments)

    # Segment identity is fail-closed: every segment must carry a stable, non-empty
    # identity, and they must be unique (the runtime trace join is keyed on it — no
    # segment_index fallback). Missing / None / blank / non-unique → not_applicable.
    identities = [_segment_identity(s) for s in segments]
    if any(idv is None for idv in identities):
        return _na("missing or invalid segment identity", segments)
    if len(identities) != len(set(identities)):
        return _na("duplicate segment identity", segments)

    # Skip the special whole-film cases SRP3 does not plan for.
    if all(s.get("audio_role") == "source_speech" for s in segments):
        return _na("pure source_speech script", segments)
    if all(s.get("source") == "stock" for s in segments):
        return _na("pure stock script", segments)

    auto = _auto_roles(n)
    hints = []
    manual_count = 0
    for i, s in enumerate(segments):
        manual_role = s.get("arc_role")
        if manual_role:
            role = manual_role
            manual_count += 1
        else:
            role = auto[i]
        defaults = ARC_DEFAULTS.get(role, _NEUTRAL_HINT)
        segment_ref = s.get("segment")          # validated above; no index fallback
        reason = ("manual arc_role preserved" if manual_role
                  else f"auto role '{role}' at position {i + 1}/{n}")
        hints.append({
            "segment_ref": segment_ref,
            "segment_index": i,
            "arc_role": role,
            "intensity": defaults["intensity"],
            "pace_hint": defaults["pace_hint"],
            "weight_multiplier": defaults["weight_multiplier"],
            "manual_role": bool(manual_role),
            "reason": reason,
        })

    return {
        "status": "planned",
        "segment_hints": hints,
        "evidence": {
            "segment_count": n,
            "manual_role_count": manual_count,
            "auto_role_count": n - manual_count,
        },
        "reason": f"Planned {n - manual_count} auto arc role(s) over {n} segments",
    }


def apply_story_arc_hints(script, plan):
    """Apply auto hints to a RUNTIME script copy, manual intent first. Mutates
    `script['segments']` in place and returns the per-segment applied trace.

    Contract (conservative + honestly traceable):
      * MANUAL arc_role → SRP3 derives NOTHING for that segment (no auto
        weight / pace / intensity / source). The manual role is preserved and is
        never relabeled as auto. This keeps director intent fully owning the
        segment and avoids ambiguous "manual role but auto rhythm" states.
      * AUTO arc_role → write `arc_role` + `story_arc_source="auto"` +
        `story_arc_reason`, and `arc_intensity` ONLY when the segment declares no
        manual `intensity`/`arc_intensity` (no conflicting value).
      * weight / pace are BUILD-rhythm hints applied ONLY to an auto-role,
        non-duration-protected segment: `weight = 1.0 * weight_multiplier` when no
        manual `weight` and no positive `requested_duration_sec`; `pace="fast"`
        for a fast role when no manual `pace`. A duration-protected segment
        (hold / hold_reason / source_speech / keep_audio / diegetic / duck) never
        receives auto weight or pace, even at a progression/climax position —
        only trace-only arc_role/arc_intensity.
      * Every auto-applied field is recorded in `story_arc_applied_fields` on the
        segment and in the returned trace, so downstream can see exactly which
        BUILD fields SRP3 derived. Never changes segment identity, text, material
        needs, or audio role.
    """
    segments = script.get("segments") or []
    applied = []
    for hint in plan.get("segment_hints", []):
        i = hint["segment_index"]
        s = segments[i]
        if hint.get("manual_role"):
            continue                            # conservative: derive nothing

        applied_fields = []
        trace = {"segment_index": i, "segment_ref": hint.get("segment_ref")}

        s["arc_role"] = hint["arc_role"]
        s["story_arc_source"] = "auto"
        s["story_arc_reason"] = hint["reason"]
        applied_fields.append("arc_role")
        trace["arc_role"] = hint["arc_role"]

        if not _has_manual_intensity(s):
            s["arc_intensity"] = hint["intensity"]
            applied_fields.append("arc_intensity")
            trace["arc_intensity"] = hint["intensity"]

        if not _is_duration_protected(s):
            if s.get("weight") is None and not _has_requested_duration(s):
                s["weight"] = round(1.0 * float(hint["weight_multiplier"]), 4)
                applied_fields.append("weight")
                trace["weight"] = s["weight"]
            if hint.get("pace_hint") == "fast" and not s.get("pace"):
                s["pace"] = "fast"
                applied_fields.append("pace")
                trace["pace"] = "fast"

        s["story_arc_applied_fields"] = list(applied_fields)
        trace["story_arc_source"] = "auto"
        trace["applied_fields"] = applied_fields
        applied.append(trace)
    return applied
