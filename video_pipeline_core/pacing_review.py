"""pacing_review.py — gold-calibrated pacing review gate (Node 12).

Mechanical verify scores spec compliance (resolution, A/V sync, duration alignment)
but is BLIND to editorial pacing: the bakery smoke test rendered segments of
43s / 0.4s / 1.5s / 53s and still scored 95.5. This gate measures the actual
timeline's shot-length profile against a gold-calibrated band per mode and scores
it, so a broken-pacing edit fails REVIEW even when technical verify passes.

The "gold board" (`_GOLD_PROFILE`) is calibrated from the human reference film
(66期養成班: ~368 shots / 804s, median ~1.47s, key holds up to ~6-12s) plus the
mode presets in docs/editing-intent-sequence-grammar-spec.md.

Pure (no I/O, no print).
"""
from __future__ import annotations

from statistics import median
from typing import Optional

# mode -> gold-calibrated pacing profile.
#   band         : healthy per-shot seconds (typical range)
#   max_hold     : a single shot longer than this is an unjustified dead hold
#   min_shot     : a shot shorter than this is an invisible flash
#   cuts_min     : acceptable whole-film cuts-per-minute window
_GOLD_PROFILE: dict[str, dict] = {
    "warm_documentary": {"band": (4, 8),   "max_hold": 12, "min_shot": 0.8, "cuts_min": (8, 22)},
    "story_documentary": {"band": (3, 8),  "max_hold": 10, "min_shot": 0.8, "cuts_min": (8, 22)},
    "training_recap":   {"band": (2.5, 6), "max_hold": 8,  "min_shot": 0.8, "cuts_min": (12, 30)},
    "rhythmic_mv":      {"band": (1.5, 4), "max_hold": 6,  "min_shot": 0.7, "cuts_min": (18, 40)},
    "promo":            {"band": (1.5, 4), "max_hold": 8,  "min_shot": 0.8, "cuts_min": (15, 35)},
}
_DEFAULT_MODE = "warm_documentary"

# a hold may exceed max_hold when the clip/segment declares one of these reasons
_HOLD_JUSTIFICATIONS = frozenset({
    "story_payoff", "emotion_developing", "action_incomplete",
    "group_photo", "emotional_memory", "certificate_proof", "proof_photo",
})


def _clip_durations(timeline_build: dict) -> list[float]:
    clips = timeline_build.get("clips") or timeline_build.get("segments") or []
    out = []
    for c in clips:
        d = c.get("duration_sec")
        if d is None and c.get("source_out_sec") is not None and c.get("source_in_sec") is not None:
            d = float(c["source_out_sec"]) - float(c["source_in_sec"])
        if d is not None:
            out.append((float(d), c))
    return out  # list of (duration, clip)


def _justified(clip: dict) -> bool:
    reasons = []
    for k in ("allow_long_hold_when", "hold_reason", "cut_reason", "shot_reason"):
        v = clip.get(k)
        if isinstance(v, (list, tuple)):
            reasons += list(v)
        elif v:
            reasons.append(v)
    return any(str(r) in _HOLD_JUSTIFICATIONS for r in reasons)


def review_pacing(
    timeline_build: dict,
    *,
    mode: str = _DEFAULT_MODE,
    target_sec: Optional[float] = None,
    editing_policy: dict | None = None,
) -> dict:
    """Score a timeline's pacing against the gold-calibrated profile for its mode.

    Returns {artifact_role, version, pass, score, mode, dimensions, findings, stats}.
    Hard violations (dead holds, invisible flashes, gross duration miss) are
    level="error" and force pass=False; pacing-band drift is a warn.
    """
    profile = _GOLD_PROFILE.get(mode) or _GOLD_PROFILE[_DEFAULT_MODE]
    band_lo, band_hi = profile["band"]
    max_hold = (editing_policy or {}).get("max_meaningful_shot_sec") or profile["max_hold"]
    min_shot = profile["min_shot"]

    pairs = _clip_durations(timeline_build)
    durs = [d for d, _ in pairs]
    findings: list[dict] = []
    dims = {"duration_fit": 100, "hold_discipline": 100, "flash_avoidance": 100, "pacing_band": 100}

    if not durs:
        return {"artifact_role": "pacing_review", "version": 1, "pass": False, "score": 0,
                "mode": mode, "dimensions": dims,
                "findings": [{"level": "error", "dimension": "duration_fit",
                              "message": "timeline has no clips with durations", "route": "editor"}],
                "stats": {}}

    total = sum(durs)
    med = median(durs)
    n = len(durs)
    cuts_min = n / (total / 60.0) if total > 0 else 0

    # 1. dead holds (unjustified shots longer than max_hold)
    dead = [(d, c) for d, c in pairs if d > max_hold and not _justified(c)]
    for d, c in dead:
        pen = min(45, (d - max_hold) * 2.0)
        dims["hold_discipline"] -= pen
        findings.append({"level": "error", "dimension": "hold_discipline",
                         "segment": c.get("segment"),
                         "message": f"dead hold: {d:.1f}s shot exceeds {mode} max {max_hold}s with no payoff reason",
                         "route": "editor"})

    # 2. invisible flashes
    flashes = [(d, c) for d, c in pairs if d < min_shot]
    for d, c in flashes:
        pen = min(25, (min_shot - d) * 30.0)
        dims["flash_avoidance"] -= pen
        findings.append({"level": "error", "dimension": "flash_avoidance",
                         "segment": c.get("segment"),
                         "message": f"invisible flash: {d:.2f}s shot below {min_shot}s minimum",
                         "route": "editor"})

    # 3. duration fit vs target
    if target_sec:
        off = abs(total - target_sec) / target_sec
        if off > 0.3:
            pen = min(40, off * 40.0)
            dims["duration_fit"] -= pen
            findings.append({"level": "error" if off > 0.6 else "warn", "dimension": "duration_fit",
                             "message": f"duration {total:.0f}s vs target {target_sec:.0f}s ({off*100:.0f}% off)",
                             "route": "director" if off > 0.6 else "editor"})

    # 4. pacing band (median shot length + cuts/min vs gold window)
    if med > band_hi * 1.5 or med < max(band_lo * 0.5, min_shot):
        dims["pacing_band"] -= 25
        findings.append({"level": "warn", "dimension": "pacing_band",
                         "message": f"median shot {med:.1f}s outside gold band [{band_lo},{band_hi}] for {mode}",
                         "route": "editor"})
    cm_lo, cm_hi = profile["cuts_min"]
    if cuts_min and (cuts_min < cm_lo * 0.5 or cuts_min > cm_hi * 1.5):
        dims["pacing_band"] -= 15
        findings.append({"level": "warn", "dimension": "pacing_band",
                         "message": f"{cuts_min:.1f} cuts/min outside gold window [{cm_lo},{cm_hi}] for {mode}",
                         "route": "editor"})

    for k in dims:
        dims[k] = max(0, min(100, int(round(dims[k]))))
    score = int(round(sum(dims.values()) / len(dims)))
    has_error = any(f["level"] == "error" for f in findings)
    passed = (score >= 70) and not has_error

    return {
        "artifact_role": "pacing_review", "version": 1,
        "pass": passed, "score": score, "mode": mode,
        "dimensions": dims, "findings": findings,
        "stats": {"shots": n, "total_sec": round(total, 1), "median_shot_sec": round(med, 2),
                  "cuts_per_min": round(cuts_min, 1), "longest_sec": round(max(durs), 1),
                  "shortest_sec": round(min(durs), 2)},
    }
