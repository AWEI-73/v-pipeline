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


def _classify(need, satisfied_by):
    """Pure, deterministic per-need classification. Returns
    (outcome, tier, route, blocks, reason)."""
    count = need.get("count") or 1
    accepted = len(satisfied_by.get("accepted") or [])
    candidate = len(satisfied_by.get("candidate") or [])
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
    if errors:
        return {"artifact_role": "material_delta", "version": 1, "ok": False,
                "errors": errors, "ready_for_build": False,
                "blocks_ready_for_build": False, "deltas": [],
                "summary": {o: 0 for o in VALID_OUTCOMES}}

    chain = lineage["chain"]
    deltas = []
    summary = {o: 0 for o in VALID_OUTCOMES}
    for need in validation["needs"]:
        nid = need["need_id"]
        satisfied_by = chain.get(nid, {}).get(
            "satisfied_by", {"accepted": [], "candidate": [], "rejected": []})
        outcome, tier, route, blocks, reason = _classify(need, satisfied_by)
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
                "accepted": len(satisfied_by.get("accepted") or []),
                "candidate": len(satisfied_by.get("candidate") or []),
                "rejected": len(satisfied_by.get("rejected") or []),
                "must_have": bool(need.get("must_have")),
                "fallback_options": list(need.get("fallback_options") or []),
                "accepted_scenes": satisfied_by.get("accepted") or [],
                "candidate_scenes": satisfied_by.get("candidate") or [],
            },
        })

    blocks_any = any(d["blocks_ready_for_build"] for d in deltas)
    return {"artifact_role": "material_delta", "version": 1, "ok": True,
            "errors": [], "ready_for_build": not blocks_any,
            "blocks_ready_for_build": blocks_any, "deltas": deltas,
            "summary": summary}
