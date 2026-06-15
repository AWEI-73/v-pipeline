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
    """A hold / source_speech / diegetic / keep_audio segment has load-bearing
    duration that a weight multiplier must never shrink (req. VI.2 / O)."""
    return bool(s.get("hold") or s.get("keep_audio")
                or s.get("audio_role") in _DURATION_PROTECTED_AUDIO)


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

    # Duplicate segment identity is fail-closed (ambiguous, order-dependent hints).
    ids = [s.get("segment") for s in segments if s.get("segment") is not None]
    if len(ids) != len(set(ids)):
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
        segment_ref = s.get("segment") if s.get("segment") is not None else i
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

    For each segment:
      * arc_role + arc_intensity (+ auto trace) only when the segment has no manual
        `arc_role`; a manual role is preserved and never relabeled as auto.
      * weight = base(1.0) * weight_multiplier only when the segment has no manual
        `weight`, no positive `requested_duration_sec`, and is not duration-
        protected (hold / source_speech / keep_audio).
      * pace = "fast" only for a "fast" pace_hint and only when no manual `pace`
        ("steady"/"hold" hints are recorded in the plan but never written, since
        the engine pace vocabulary is {fast, hold} and only "fast" changes
        allocation).

    Never changes segment identity, text, material needs, or audio role.
    """
    segments = script.get("segments") or []
    applied = []
    for hint in plan.get("segment_hints", []):
        i = hint["segment_index"]
        s = segments[i]
        trace = {"segment_index": i, "segment_ref": hint.get("segment_ref")}
        applied_any = False

        if not hint.get("manual_role"):
            s["arc_role"] = hint["arc_role"]
            s["arc_intensity"] = hint["intensity"]
            s["story_arc_source"] = "auto"
            s["story_arc_reason"] = hint["reason"]
            trace["arc_role"] = hint["arc_role"]
            trace["arc_intensity"] = hint["intensity"]
            trace["story_arc_source"] = "auto"
            applied_any = True

        if (s.get("weight") is None and not _has_requested_duration(s)
                and not _is_duration_protected(s)):
            s["weight"] = round(1.0 * float(hint["weight_multiplier"]), 4)
            trace["weight"] = s["weight"]
            applied_any = True

        if hint.get("pace_hint") == "fast" and not s.get("pace"):
            s["pace"] = "fast"
            trace["pace"] = "fast"
            applied_any = True

        if applied_any:
            applied.append(trace)
    return applied
