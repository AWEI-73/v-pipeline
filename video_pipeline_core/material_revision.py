"""M6c — Delta-driven script revision.

Deterministically convert ACCEPTED human/director decisions about a
`material_delta` into a revised `segment_contract`. The agent never invents
aesthetics or silently edits the script: M6c only executes decisions that a
reviewer explicitly accepted, and only the narrow, allow-listed mutation each
route permits.

Division of responsibility:
  - `material_delta` (M6b)  : states the problem + a compatible route per need.
  - `revision_decisions`    : the human/director's explicit accepted handling.
  - `material_revision` (M6c): applies ONLY accepted decisions, with lineage.

Hard invariants:
  - the original contract is never mutated in place (a deep copy is revised);
  - every change is traceable to a `need_id` + decision lineage;
  - the revised contract must re-pass `spec_contract.validate_segment_contract`;
  - a patch may never touch segment identity / `need_refs` / any `need_id`;
  - a tier-1 must_have block is only released by an EXPLICIT waiver.

Reuses the existing `need_id` and route vocabulary; it does NOT define a second
material-need / delta schema. Scope: revision engine + artifacts only — wiring
into `run_contract` is a separate later increment (kept out so revision and the
BUILD gate do not entangle). No F2 / no BUILD ranking / timeline / render change.
"""
from __future__ import annotations

import copy
import hashlib
import json

from . import spec_contract


# the routes a decision may carry (the M6b route enum minus the no-op "none")
DECISION_ROUTES = ("collect_material", "reshoot", "shorten_or_merge",
                   "script_rewrite", "drop_segment", "dashboard_review")
# routes that change the script (need a resolvable target segment)
MODIFYING_ROUTES = {"shorten_or_merge", "script_rewrite", "drop_segment"}
# routes that keep the block and do not touch the script
NON_MODIFYING_ROUTES = {"collect_material", "reshoot", "dashboard_review"}

# which routes are compatible with each delta outcome (a route that cannot
# possibly address the outcome is rejected — e.g. you cannot shorten a missing
# need into existence, nor collect more of an over-supplied one)
_OUTCOME_ROUTES = {
    "covered": {"dashboard_review"},
    "thin": {"collect_material", "reshoot", "shorten_or_merge",
             "script_rewrite", "drop_segment", "dashboard_review"},
    "missing": {"collect_material", "reshoot", "script_rewrite",
                "drop_segment", "dashboard_review"},
    "excess": {"shorten_or_merge", "drop_segment", "dashboard_review"},
}

# fields a shorten_or_merge patch may set (nothing else)
_SHORTEN_KEYS = {"requested_duration_sec", "duration_sec"}


def _hash(obj):
    return hashlib.sha1(
        json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")
    ).hexdigest()[:12]


def _segments(contract):
    if isinstance(contract, dict):
        return contract.get("segments") or []
    if isinstance(contract, list):
        return contract
    return []


def _valid_waiver(waiver):
    return (isinstance(waiver, dict)
            and isinstance(waiver.get("reviewer"), str) and waiver["reviewer"].strip()
            and isinstance(waiver.get("reason"), str) and waiver["reason"].strip())


def _valid_lineage(lineage):
    return (isinstance(lineage, dict)
            and all(isinstance(lineage.get(k), str) and lineage[k].strip()
                    for k in ("reviewer", "reason", "at")))


def _contains_need_id_key(value):
    """True if a need_id key appears anywhere in a nested structure."""
    if isinstance(value, dict):
        if "need_id" in value:
            return True
        return any(_contains_need_id_key(v) for v in value.values())
    if isinstance(value, list):
        return any(_contains_need_id_key(v) for v in value)
    return False


def _patch_identity_violation(patch):
    """A patch may never change segment identity, need_refs, or any need_id."""
    if not isinstance(patch, dict):
        return "patch must be an object"
    if "segment" in patch:
        return "patch may not change segment identity"
    if "need_id" in patch or _contains_need_id_key(patch):
        return "patch may not set or change a need_id"
    if isinstance(patch.get("material_fit"), dict) and "need_refs" in patch["material_fit"]:
        return "patch may not change material_fit.need_refs"
    if isinstance(patch.get("core"), dict) and "section_role" in patch["core"]:
        return "patch may not change core.section_role (segment identity)"
    return None


def _deep_merge(target, patch):
    """Merge patch into target dict, recursing into nested dicts only."""
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(target.get(key), dict):
            _deep_merge(target[key], value)
        else:
            target[key] = value


def _resolve_target_index(segments, target):
    """Resolve a decision's target_segment to exactly one segment by its
    `segment` identity. Returns (index, error)."""
    if target is None:
        return None, "target_segment is required for this route"
    matches = [i for i, seg in enumerate(segments)
               if isinstance(seg, dict) and seg.get("segment") == target]
    if len(matches) == 0:
        return None, f"target_segment {target!r} does not exist"
    if len(matches) > 1:
        return None, f"target_segment {target!r} is ambiguous (matches {len(matches)} segments)"
    return matches[0], None


def apply_revisions(contract, material_delta, decisions, *, categories=None):
    """Apply accepted revision decisions to a COPY of the contract.

    Returns (report, revised_contract_or_None). On any hard validation error the
    report has ``ok=False`` and the revised contract is ``None`` (callers must
    not write a half-baked artifact). The original ``contract`` is never mutated.
    """
    errors = []

    def fail():
        return ({"artifact_role": "material_revision", "version": 1, "ok": False,
                 "errors": errors, "before_contract_hash": _hash(contract),
                 "after_contract_hash": None, "decisions": [],
                 "unresolved_blocking_needs": [], "ready_for_build": False,
                 "next_action": "revise:material(material_revision)"}, None)

    # M6b safety: a broken/invalid delta cannot be the basis of a revision
    if not isinstance(material_delta, dict) or not material_delta.get("ok"):
        errors.append("material_delta.ok is not true — revision is not permitted")
        return fail()

    delta_by_need = {}
    for d in material_delta.get("deltas") or []:
        nid = d.get("need_id")
        if isinstance(nid, str):
            delta_by_need[nid] = d
    tier1_blocking = {d["need_id"] for d in material_delta.get("deltas") or []
                      if d.get("blocks_ready_for_build")}

    decisions = decisions or []
    if not isinstance(decisions, list):
        errors.append("revision_decisions must be a list")
        return fail()

    # ---- validate every decision (fail closed, order-independent) -----------
    seen_ids = set()
    accepted, validated = [], []
    for i, dec in enumerate(decisions):
        if not isinstance(dec, dict):
            errors.append(f"decision #{i} must be an object")
            continue
        did = dec.get("decision_id")
        if not isinstance(did, str) or not did.strip():
            errors.append(f"decision #{i} decision_id must be a non-empty string")
            continue
        if did in seen_ids:
            errors.append(f"duplicate decision_id {did!r}")
            continue
        seen_ids.add(did)

        status = dec.get("status")
        if status not in ("accepted", "rejected"):
            errors.append(f"decision {did!r} status must be accepted|rejected, got {status!r}")
            continue

        nid = dec.get("need_id")
        if nid not in delta_by_need:
            errors.append(f"decision {did!r} need_id {nid!r} not in current material_delta "
                          f"(stale or unknown)")
            continue
        route = dec.get("route")
        if route not in DECISION_ROUTES:
            errors.append(f"decision {did!r} route {route!r} not in {DECISION_ROUTES}")
            continue
        outcome = delta_by_need[nid].get("outcome")
        if route not in _OUTCOME_ROUTES.get(outcome, set()):
            errors.append(f"decision {did!r} route {route!r} is not compatible with "
                          f"delta outcome {outcome!r} for need {nid!r}")
            continue

        validated.append(dec)
        if status == "accepted":
            if not _valid_lineage(dec.get("lineage")):
                errors.append(f"decision {did!r} accepted but lineage is incomplete "
                              f"(reviewer/reason/at required)")
                continue
            accepted.append(dec)

    if errors:
        return fail()

    # ---- conflict detection: at most one accepted modifying decision per
    #      target segment (order-independent) ---------------------------------
    segments = _segments(contract)
    target_owner = {}
    for dec in accepted:
        if dec["route"] not in MODIFYING_ROUTES:
            continue
        idx, err = _resolve_target_index(segments, dec.get("target_segment"))
        if err:
            errors.append(f"decision {dec['decision_id']!r}: {err}")
            continue
        if idx in target_owner:
            errors.append(f"conflicting accepted patches on the same target segment "
                          f"{dec.get('target_segment')!r}: {target_owner[idx]!r} and "
                          f"{dec['decision_id']!r}")
        else:
            target_owner[idx] = dec["decision_id"]
    if errors:
        return fail()

    # ---- pre-validate each modifying decision before mutating anything ------
    revised = copy.deepcopy(contract)
    revised_segments = _segments(revised)
    plan = []   # (decision, action, idx)
    for dec in accepted:
        did, route, nid = dec["decision_id"], dec["route"], dec["need_id"]
        if route in NON_MODIFYING_ROUTES:
            plan.append((dec, "blocked", None))
            continue
        idx, err = _resolve_target_index(revised_segments, dec.get("target_segment"))
        if err:
            errors.append(f"decision {did!r}: {err}")
            continue
        seg = revised_segments[idx]
        if route == "shorten_or_merge":
            patch = dec.get("patch")
            if not isinstance(patch, dict) or not patch:
                errors.append(f"decision {did!r} shorten_or_merge requires a patch")
                continue
            bad_keys = set(patch) - _SHORTEN_KEYS
            if bad_keys:
                errors.append(f"decision {did!r} shorten_or_merge patch may only set "
                              f"{sorted(_SHORTEN_KEYS)}, got disallowed {sorted(bad_keys)}")
                continue
            if any((not isinstance(v, (int, float))) or isinstance(v, bool) or v <= 0
                   for v in patch.values()):
                errors.append(f"decision {did!r} shorten_or_merge durations must be positive numbers")
                continue
            plan.append((dec, "shorten", idx))
        elif route == "script_rewrite":
            patch = dec.get("patch")
            if not isinstance(patch, dict) or not patch:
                errors.append(f"decision {did!r} script_rewrite requires a patch")
                continue
            violation = _patch_identity_violation(patch)
            if violation:
                errors.append(f"decision {did!r} script_rewrite {violation}")
                continue
            plan.append((dec, "rewrite", idx))
        elif route == "drop_segment":
            must_have = bool((delta_by_need[nid].get("evidence") or {}).get("must_have"))
            if must_have and not _valid_waiver(dec.get("waiver")):
                errors.append(f"decision {did!r} cannot drop a must_have need {nid!r} "
                              f"without an explicit waiver (reviewer+reason)")
                continue
            plan.append((dec, "drop", idx))
    if errors:
        return fail()

    # ---- apply (deterministic; drops last so indices stay valid) ------------
    decision_records = []
    resolved_need_ids = set()
    drops = []
    for dec, action, idx in plan:
        did, route, nid = dec["decision_id"], dec["route"], dec["need_id"]
        lineage = dec.get("lineage")
        if _valid_waiver(dec.get("waiver")):
            resolved_need_ids.add(nid)
        if action == "blocked":
            decision_records.append(_record(dec, "blocked",
                                             f"route {route}: no script change; remains pending"))
            continue
        seg = revised_segments[idx]
        if action == "shorten":
            for key, value in dec["patch"].items():
                seg[key] = value
            _stamp_lineage(seg, dec)
            decision_records.append(_record(dec, "applied",
                                             f"shortened segment {dec['target_segment']} "
                                             f"({dec['patch']})"))
        elif action == "rewrite":
            _deep_merge(seg, dec["patch"])
            _stamp_lineage(seg, dec)
            decision_records.append(_record(dec, "applied",
                                             f"rewrote segment {dec['target_segment']}"))
        elif action == "drop":
            drops.append((idx, dec))

    # rejected / non-accepted decisions are recorded as-is, no contract change
    accepted_ids = {d["decision_id"] for d in accepted}
    for dec in validated:
        if dec["decision_id"] in accepted_ids:
            continue
        decision_records.append(_record(dec, "rejected", "decision not accepted; no change"))

    # apply drops by descending index so earlier indices remain valid
    for idx, dec in sorted(drops, key=lambda t: -t[0]):
        revised_segments.pop(idx)
        decision_records.append(_record(dec, "applied",
                                         f"dropped segment {dec['target_segment']}"
                                         + (" (waived)" if _valid_waiver(dec.get("waiver")) else "")))

    if isinstance(revised, dict):
        revised["segments"] = revised_segments
    else:
        revised = revised_segments

    # ---- the revised contract must still be a valid contract ----------------
    validation = spec_contract.validate_segment_contract(revised, categories=categories)
    if not validation["ok"]:
        errors.append("revised contract failed spec_contract validation: "
                      + "; ".join(validation["errors"]))
        return fail()

    # ---- re-check the M6b block at the artifact level: a tier-1 block is only
    #      released by an explicit waiver (never auto-cleared) ----------------
    unresolved = sorted(nid for nid in tier1_blocking if nid not in resolved_need_ids)
    accepted_routes = {d["route"] for d in accepted}
    if unresolved:
        next_action = "await_material"
    elif accepted_routes & {"collect_material", "reshoot"}:
        next_action = "await_material"
    elif "dashboard_review" in accepted_routes:
        next_action = "await_review"
    else:
        next_action = None

    no_op = not accepted
    report = {
        "artifact_role": "material_revision", "version": 1, "ok": True,
        "errors": [], "no_op": no_op,
        "before_contract_hash": _hash(contract),
        "after_contract_hash": _hash(revised),
        "decisions": decision_records,
        "unresolved_blocking_needs": unresolved,
        "ready_for_build": not unresolved,
        "next_action": next_action,
    }
    return report, revised


def _stamp_lineage(seg, dec):
    """Append revision lineage to a modified segment (need_refs preserved)."""
    entry = {"decision_id": dec["decision_id"], "need_id": dec["need_id"],
             "route": dec["route"], "lineage": dec.get("lineage")}
    if _valid_waiver(dec.get("waiver")):
        entry["waiver"] = dec["waiver"]
    seg.setdefault("revision_lineage", []).append(entry)


def _record(dec, status, summary):
    record = {"decision_id": dec.get("decision_id"), "need_id": dec.get("need_id"),
              "route": dec.get("route"), "status": status, "summary": summary,
              "lineage": dec.get("lineage")}
    if dec.get("target_segment") is not None:
        record["target_segment"] = dec.get("target_segment")
    if _valid_waiver(dec.get("waiver")):
        record["waiver"] = dec["waiver"]
    return record
