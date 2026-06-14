"""M6b — Material delta (coverage-based, increment 1).

Compare canonical requirements against actual supply over the M6a lineage join
(`need_id` ↔ scene satisfies edges) and emit one deterministic outcome per need:

    covered | thin | missing | excess

Each delta carries evidence (the counts it was decided from), a single route,
and a tier. The only tier-1 (build-blocking) case in this increment is a
``must_have`` need with no usable material AND no permitted fallback — surfaced
as machine-readable ``blocks_ready_for_build: true``.

Scope (increment 1 — confirmed bounded):
  - built ONLY on validated material_needs + satisfies edges via link_lineage;
  - a broken reference chain / invalid needs FAILS (`ok=False`) and is never
    misread as `missing` — "no material" and "broken join" are different;
  - thresholds are deterministic and testable.

Only BUILD-renderable evidence counts toward coverage: a satisfying scene whose
source is missing or whose start/end is invalid/non-positive is recorded as
``dropped_evidence`` and never makes a need `covered` (it cannot become a real
window). Evidence is counted once per ``(need_id, asset_id, scene_index)``.

FUTURE pre-BUILD GATE CONTRACT (for whoever wires this in the next batch):
a build may proceed only when BOTH ``delta.ok is True`` AND
``delta.ready_for_build is True``. Checking ``blocks_ready_for_build`` alone is
INSUFFICIENT — a broken/invalid delta has ``ok=False`` with no deltas and must
also block. ``delivery_gate`` remains a backstop, not the primary block site.

Explicitly NOT here (do not add):
  - `wrong_semantics` / `insufficient_action_phases` — they need the F2 canonical
    shot-function vocabulary, deferred until a real case proves it necessary;
  - no `action_progression` / semantic-phase dependency;
  - no delivery_gate / HARD_AUDITS wiring (the gate consumes
    `blocks_ready_for_build` in a later batch; delivery_gate is only a backstop);
  - no BUILD ranking / script revision / timeline change.
"""
from __future__ import annotations

from .material_lineage import link_lineage
from .material_needs import validate_material_needs


# routes are the M6b enum (roadmap M6b); this increment uses a subset
VALID_ROUTES = ("none", "collect_material", "reshoot", "shorten_or_merge",
                "script_rewrite", "drop_segment", "dashboard_review")
VALID_OUTCOMES = ("covered", "thin", "missing", "excess")

# a scene that is both accepted and (say) candidate is counted once, at its
# strongest status — deterministic dedupe by (asset_id, scene_index).
_STATUS_PRIORITY = {"accepted": 3, "candidate": 2, "rejected": 1}


def _validate_asset_ids(material_maps):
    """asset_id is the identity half of the (asset_id, scene_index) evidence key.
    A missing/blank/non-string or duplicate asset_id makes evidence resolution
    ambiguous and order-dependent, so it is a hard failure — not something to
    silently resolve into covered/missing. Returns a list of errors."""
    errors = []
    seen = set()
    for index, material_map in enumerate(material_maps or []):
        if not isinstance(material_map, dict):
            errors.append(f"material map #{index} must be an object, got {material_map!r}")
            continue
        asset_id = material_map.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            errors.append(f"material map #{index} asset_id must be a non-empty "
                          f"string, got {asset_id!r}")
            continue
        if asset_id in seen:
            errors.append(f"duplicate asset_id {asset_id!r} — must be unique "
                          f"across material maps (ambiguous evidence identity)")
            continue
        seen.add(asset_id)
    return errors


def _scene_lookup(material_maps):
    """{(asset_id, scene_index): (source, scene)} from the per-asset maps."""
    lookup = {}
    for material_map in material_maps or []:
        if not isinstance(material_map, dict):
            continue
        asset_id = material_map.get("asset_id")
        source = material_map.get("source")
        for index, scene in enumerate(material_map.get("scenes") or []):
            lookup[(asset_id, index)] = (source, scene if isinstance(scene, dict) else {})
    return lookup


def _renderable(source, scene):
    """A scene only counts toward coverage if it can become a real window:
    non-empty source + numeric start/end with positive length. Returns
    (ok, reason)."""
    if not (isinstance(source, str) and source.strip()):
        return False, "missing_source"
    start, end = scene.get("start"), scene.get("end")
    for value in (start, end):
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return False, "invalid_bounds"
    if not (end > start):
        return False, "non_positive_length"
    return True, None


def _usable_counts(satisfied_by, lookup):
    """Dedupe evidence by (asset_id, scene_index) at its strongest status, then
    keep only BUILD-renderable scenes. Returns (usable_by_status, usable_scenes,
    dropped) where dropped records every unusable-but-referenced scene."""
    best = {}
    for status in ("accepted", "candidate", "rejected"):
        for ref in satisfied_by.get(status) or []:
            key = (ref.get("asset_id"), ref.get("scene_index"))
            if key not in best or _STATUS_PRIORITY[status] > _STATUS_PRIORITY[best[key]]:
                best[key] = status
    usable = {"accepted": 0, "candidate": 0, "rejected": 0}
    usable_scenes = {"accepted": [], "candidate": [], "rejected": []}
    dropped = []
    for key in sorted(best, key=lambda k: (str(k[0]), k[1] if isinstance(k[1], int) else -1)):
        status = best[key]
        ref = {"asset_id": key[0], "scene_index": key[1]}
        if key not in lookup:
            dropped.append({**ref, "status": status, "reason": "scene_not_found"})
            continue
        source, scene = lookup[key]
        ok_render, reason = _renderable(source, scene)
        if ok_render:
            usable[status] += 1
            usable_scenes[status].append(ref)
        else:
            dropped.append({**ref, "status": status, "reason": reason})
    return usable, usable_scenes, dropped


def _classify(need, accepted, candidate):
    """Pure, deterministic per-need classification from USABLE counts. Returns
    (outcome, tier, route, blocks, reason)."""
    count = need.get("count") or 1
    must_have = bool(need.get("must_have"))
    has_fallback = bool(need.get("fallback_options"))
    usable = accepted + candidate

    if usable == 0:
        # genuine no-material (the join is intact — verified before we get here)
        if must_have and not has_fallback:
            return ("missing", 1, "reshoot", True,
                    "must_have need has no usable material and no permitted "
                    "fallback (unshootable -> blocks build)")
        if must_have:
            return ("missing", 2, "collect_material", False,
                    "must_have need missing but a permitted fallback exists "
                    "(collect/substitute, does not block)")
        return ("missing", 2, "collect_material", False,
                "optional need has no usable material")
    if accepted > count:
        return ("excess", 2, "shorten_or_merge", False,
                f"{accepted} accepted exceed required {count} (over-supply)")
    if accepted >= count:
        return ("covered", None, "none", False,
                f"{accepted} accepted meet required {count}")
    # some usable material exists but accepted is short of count
    return ("thin", 2, "dashboard_review", False,
            f"only {accepted} accepted of required {count} "
            f"({candidate} candidate pending review)")


def compute_material_delta(material_needs, material_maps=None):
    """Compute the coverage delta over the validated lineage join.

    Returns a ``material_delta`` artifact::

        {ok, errors, ready_for_build, blocks_ready_for_build,
         deltas: [{need_id, outcome, tier, route, blocks_ready_for_build,
                   reason, evidence}], summary: {covered, thin, missing, excess}}

    ``ok`` is False (and ``deltas`` empty) when material_needs is invalid or the
    satisfies-edge reference chain is broken — those are reported as errors, NOT
    classified as `missing`. ``ready_for_build`` is False iff any tier-1 delta
    blocks the build."""
    validation = validate_material_needs(material_needs)
    lineage = link_lineage(material_needs, material_maps=material_maps)

    errors = []
    if not validation["ok"]:
        errors.extend(validation["errors"])
    # a dangling/malformed satisfies edge is a broken join, never "missing"
    if not lineage["ok"]:
        errors.extend(lineage["errors"])
    # asset_id identity must be sound before any (asset_id, scene_index) lookup
    errors.extend(_validate_asset_ids(material_maps))
    if errors:
        return {"artifact_role": "material_delta", "version": 1, "ok": False,
                "errors": errors, "ready_for_build": False,
                "blocks_ready_for_build": False, "deltas": [],
                "summary": {o: 0 for o in VALID_OUTCOMES}}

    chain = lineage["chain"]
    lookup = _scene_lookup(material_maps)
    deltas = []
    summary = {o: 0 for o in VALID_OUTCOMES}
    for need in validation["needs"]:
        nid = need["need_id"]
        satisfied_by = chain.get(nid, {}).get(
            "satisfied_by", {"accepted": [], "candidate": [], "rejected": []})
        # count only deduped, BUILD-renderable evidence toward coverage
        usable, usable_scenes, dropped = _usable_counts(satisfied_by, lookup)
        outcome, tier, route, blocks, reason = _classify(
            need, usable["accepted"], usable["candidate"])
        summary[outcome] += 1
        deltas.append({
            "need_id": nid,
            "outcome": outcome,
            "tier": tier,
            "route": route,
            "blocks_ready_for_build": blocks,
            "reason": reason,
            "evidence": {
                "required_count": need.get("count") or 1,
                "accepted": usable["accepted"],
                "candidate": usable["candidate"],
                "rejected": usable["rejected"],
                "must_have": bool(need.get("must_have")),
                "fallback_options": list(need.get("fallback_options") or []),
                "accepted_scenes": usable_scenes["accepted"],
                "candidate_scenes": usable_scenes["candidate"],
                "dropped_evidence": dropped,   # referenced but not BUILD-usable
            },
        })

    blocks_any = any(d["blocks_ready_for_build"] for d in deltas)
    return {"artifact_role": "material_delta", "version": 1, "ok": True,
            "errors": [], "ready_for_build": not blocks_any,
            "blocks_ready_for_build": blocks_any, "deltas": deltas,
            "summary": summary}


# routes the pre-BUILD gate may emit (a subset of the M6b route enum)
GATE_ROUTES = ("fix_material_map_or_needs", "await_material")


def material_delta_gate(material_needs, material_maps=None, *,
                        resolution_error=None, material_delta_path=None):
    """Fail-closed pre-BUILD gate verdict, built ONLY on `compute_material_delta`
    (no second delta logic). The build may proceed iff BOTH ``delta.ok`` AND
    ``delta.ready_for_build`` are true — checking ``blocks_ready_for_build`` alone
    is insufficient (a broken/invalid delta has ``ok=False`` and must also block).

    ``resolution_error`` is a string set by the caller when the project DECLARED
    material_needs but they (or the maps) could not be resolved — declared but
    missing / unparseable input is a hard block, never a silent skip.

    Returns a machine-readable verdict::

        {gate, status: pass|block, ok, ready_for_build, blocking_need_ids,
         reason, route, material_delta (path), next_action, delta}
    """
    if resolution_error:
        return {"gate": "material_delta", "status": "block", "ok": False,
                "ready_for_build": False, "blocking_need_ids": [],
                "reason": resolution_error, "route": "fix_material_map_or_needs",
                "material_delta": material_delta_path,
                "next_action": "revise:material(material_delta)", "delta": None}

    delta = compute_material_delta(material_needs, material_maps)
    base = {"gate": "material_delta", "ok": delta["ok"],
            "ready_for_build": delta["ready_for_build"],
            "material_delta": material_delta_path, "delta": delta}

    if delta["ok"] and delta["ready_for_build"]:
        return {**base, "status": "pass", "blocking_need_ids": [],
                "reason": "all required material is covered or has a permitted fallback",
                "route": None, "next_action": None}

    if not delta["ok"]:
        # invalid needs / broken reference chain / bad material map — never a
        # plain `missing`; the fix is the map or the needs contract, not a reshoot
        return {**base, "status": "block", "blocking_need_ids": [],
                "reason": "material_delta could not be computed: "
                          + "; ".join(delta["errors"]),
                "route": "fix_material_map_or_needs",
                "next_action": "revise:material(material_delta)"}

    # ok but not ready: one or more tier-1 must_have gaps with no permitted fallback
    blocking = [d["need_id"] for d in delta["deltas"] if d["blocks_ready_for_build"]]
    return {**base, "status": "block", "blocking_need_ids": blocking,
            "reason": f"{len(blocking)} must_have need(s) missing with no permitted "
                      f"fallback: {blocking}",
            "route": "await_material", "next_action": "await_material"}
