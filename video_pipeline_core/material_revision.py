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
import os
from pathlib import Path

from . import spec_contract
from .material_delta import gate_from_delta, is_canonical_waiver


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


def _decision_waivers(dec):
    """CANONICAL per-need waivers carried by a decision → list of
    {need_id, reviewer, reason, at} records that pass the SINGLE shared validator
    `material_delta.is_canonical_waiver` (no second rule). The `waiver` field
    waives the decision's own need_id (its `at` defaults to the decision lineage's
    `at`); an optional `waivers` list waives additional referenced needs. A
    malformed/incomplete waiver is simply not canonical and releases nothing."""
    at = (dec.get("lineage") or {}).get("at")
    candidates = []
    single = dec.get("waiver")
    if isinstance(single, dict) and isinstance(dec.get("need_id"), str):
        candidates.append({"need_id": dec["need_id"], "reviewer": single.get("reviewer"),
                           "reason": single.get("reason"), "at": single.get("at", at)})
    for entry in dec.get("waivers") or []:
        if isinstance(entry, dict):
            candidates.append({"need_id": entry.get("need_id"), "reviewer": entry.get("reviewer"),
                               "reason": entry.get("reason"), "at": entry.get("at", at)})
    # de-dup by need_id, keep only canonical waivers (the shared validator decides)
    out = {}
    for record in candidates:
        if is_canonical_waiver(record):
            out[record["need_id"]] = record
    return out


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
    affected_need_ids = {}   # decision_id -> all need_refs of a dropped segment
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
            # Protect EVERY need the dropped segment references, not just the
            # decision's own need_id: each referenced need that is must_have or a
            # tier-1 blocker needs its own explicit waiver; an unknown need_ref
            # (absent from the current delta) is fail-closed.
            affected = list((seg.get("material_fit") or {}).get("need_refs") or [])
            waivers_here = _decision_waivers(dec)
            drop_failed = False
            for ref in affected:
                if ref not in delta_by_need:
                    errors.append(f"decision {did!r} drops a segment referencing unknown "
                                  f"need_id {ref!r} (not in current material_delta)")
                    drop_failed = True
                    continue
                d = delta_by_need[ref]
                protected = (bool((d.get("evidence") or {}).get("must_have"))
                             or bool(d.get("blocks_ready_for_build")))
                if protected and ref not in waivers_here:
                    errors.append(f"decision {did!r} cannot drop a segment referencing "
                                  f"must_have/tier-1 need {ref!r} without an explicit "
                                  f"waiver for it")
                    drop_failed = True
            if drop_failed:
                continue
            affected_need_ids[did] = affected
            plan.append((dec, "drop", idx))
    if errors:
        return fail()

    # ---- apply (deterministic; drops last so indices stay valid) ------------
    decision_records = []
    drops = []
    for dec, action, idx in plan:
        did, route, nid = dec["decision_id"], dec["route"], dec["need_id"]
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
        affected = affected_need_ids.get(dec["decision_id"], [])
        decision_records.append(_record(
            dec, "applied",
            f"dropped segment {dec['target_segment']} (affected needs: {affected})"
            + (" (waived)" if _decision_waivers(dec) else ""),
            affected_need_ids=affected))

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

    # ---- canonical waiver artifact + ACTUAL M6b gate re-run -----------------
    # ready_for_build is taken from gate_from_delta(delta, waivers) — the SAME
    # verdict run_contract's gate uses — so material_revision.ready can never
    # contradict the M6b gate. We never hand-roll the unresolved list.
    collected = {}
    for dec in accepted:
        for need_id_w, rec in _decision_waivers(dec).items():
            collected[need_id_w] = {"need_id": need_id_w, **rec}
    waivers_artifact = [collected[k] for k in sorted(collected)]
    gate = gate_from_delta(material_delta, waivers=waivers_artifact)

    accepted_routes = {d["route"] for d in accepted}
    if gate["status"] == "block":
        next_action = gate["next_action"]                 # await_material
    elif accepted_routes & {"collect_material", "reshoot"}:
        next_action = "await_material"
    elif "dashboard_review" in accepted_routes:
        next_action = "await_review"
    else:
        next_action = None

    report = {
        "artifact_role": "material_revision", "version": 1, "ok": True,
        "errors": [], "no_op": not accepted,
        "before_contract_hash": _hash(contract),
        "after_contract_hash": _hash(revised),
        "decisions": decision_records,
        "waivers": waivers_artifact,
        "unresolved_blocking_needs": gate["blocking_need_ids"],
        "ready_for_build": gate["status"] == "pass",
        "next_action": next_action,
    }
    return report, revised


def _stamp_lineage(seg, dec):
    """Append revision lineage to a modified segment (need_refs preserved)."""
    entry = {"decision_id": dec["decision_id"], "need_id": dec["need_id"],
             "route": dec["route"], "lineage": dec.get("lineage")}
    waivers = _decision_waivers(dec)
    if waivers:
        entry["waivers"] = [v for _, v in sorted(waivers.items())]
    seg.setdefault("revision_lineage", []).append(entry)


def _record(dec, status, summary, *, affected_need_ids=None):
    record = {"decision_id": dec.get("decision_id"), "need_id": dec.get("need_id"),
              "route": dec.get("route"), "status": status, "summary": summary,
              "lineage": dec.get("lineage")}
    if dec.get("target_segment") is not None:
        record["target_segment"] = dec.get("target_segment")
    waivers = _decision_waivers(dec)
    if waivers:
        record["waivers"] = [{"need_id": k, **v} for k, v in sorted(waivers.items())]
    if affected_need_ids is not None:
        record["affected_need_ids"] = affected_need_ids
    return record


def _unlink_quietly(*paths):
    for path in paths:
        try:
            if Path(path).exists():
                Path(path).unlink()
        except OSError:
            pass


def write_revision_artifacts(revised, report, out_contract, out_revision, *, _writer=None):
    """All-or-nothing write of the two M6c artifacts.

    The two output paths must differ; both parent dirs are created. Both files
    are written to temporaries first; existing officials are backed up; the temps
    are then ``os.replace``d into place. If a commit step fails, the prior
    officials are rolled back from backup (or the newly-created file removed when
    there was none), so the on-disk state is never a new/old mix. On rollback
    success all temps/backups are cleaned. If rollback ITSELF fails, the backups
    are preserved and a RuntimeError is raised — atomic success is never claimed.
    """
    out_contract, out_revision = Path(out_contract), Path(out_revision)
    # path identity must be case-insensitive on Windows: A.json and a.json are the
    # SAME file there, so they can never be two distinct outputs.
    def _norm(p):
        return os.path.normcase(os.path.abspath(str(p)))
    if _norm(out_contract) == _norm(out_revision):
        raise ValueError("out_contract and out_revision must be different paths "
                         "(case-insensitive on this platform)")
    out_contract.parent.mkdir(parents=True, exist_ok=True)
    out_revision.parent.mkdir(parents=True, exist_ok=True)
    writer = _writer or (lambda path, text: Path(path).write_text(text, encoding="utf-8"))
    tmp_c = out_contract.with_name(out_contract.name + ".m6c.tmp")
    tmp_r = out_revision.with_name(out_revision.name + ".m6c.tmp")
    bak_c = out_contract.with_name(out_contract.name + ".m6c.bak")
    bak_r = out_revision.with_name(out_revision.name + ".m6c.bak")

    # 0) a pre-existing backup means a previous transaction may have failed; it
    # may hold the only good copy, so refuse rather than overwrite/delete it.
    for bak in (bak_c, bak_r):
        if Path(bak).exists():
            raise RuntimeError(
                f"refusing to start: existing backup {bak} found (a previous "
                f"transaction may have failed and left the only good copy here) — "
                f"manually recover or remove it before retrying")
    # stale scratch temporaries never hold official content; clear them explicitly
    _unlink_quietly(tmp_c, tmp_r)

    # 1) write both temporaries (no official touched yet)
    try:
        writer(tmp_c, json.dumps(revised, ensure_ascii=False, indent=2))
        writer(tmp_r, json.dumps(report, ensure_ascii=False, indent=2))
    except Exception:
        _unlink_quietly(tmp_c, tmp_r)
        raise

    # 2) back up existing officials (transactional): if a later backup fails, the
    # earlier backup is restored to its official path — never unlink a backup that
    # now holds the only copy of official content.
    had_c, had_r = out_contract.exists(), out_revision.exists()
    backed_up = []
    try:
        if had_c:
            os.replace(out_contract, bak_c)
            backed_up.append((out_contract, bak_c))
        if had_r:
            os.replace(out_revision, bak_r)
            backed_up.append((out_revision, bak_r))
    except OSError as exc:
        rollback_errors = []
        for official, bak in reversed(backed_up):
            try:
                os.replace(bak, official)              # restore the backed-up official
            except OSError as rollback_exc:
                rollback_errors.append(f"{official}: {rollback_exc}")
        _unlink_quietly(tmp_c, tmp_r)                  # temps never held official data
        if rollback_errors:
            raise RuntimeError(
                "backup failed AND backup-rollback failed (on-disk state is NOT "
                f"atomic; backups preserved): {exc}; rollback errors: {rollback_errors}")
        raise OSError(f"backup failed; restored prior state: {exc}")

    # 3) commit both; any failure rolls the officials back to their prior state
    try:
        os.replace(tmp_c, out_contract)
        os.replace(tmp_r, out_revision)
    except OSError as exc:
        rollback_errors = []
        for path, had, bak in ((out_contract, had_c, bak_c), (out_revision, had_r, bak_r)):
            try:
                if had:
                    if Path(bak).exists():
                        os.replace(bak, path)          # restore prior official
                elif Path(path).exists():
                    Path(path).unlink()                # nothing existed before -> remove new
            except OSError as rollback_exc:
                rollback_errors.append(f"{path}: {rollback_exc}")
        if rollback_errors:
            # keep backups for manual recovery; never claim atomic success
            _unlink_quietly(tmp_c, tmp_r)
            raise RuntimeError(
                "artifact commit failed AND rollback failed (on-disk state is NOT "
                f"atomic; backups preserved): {exc}; rollback errors: {rollback_errors}")
        _unlink_quietly(tmp_c, tmp_r, bak_c, bak_r)
        raise OSError(f"artifact commit failed; rolled back to prior state: {exc}")

    # 4) success: drop the backups
    _unlink_quietly(bak_c, bak_r)
    return str(out_contract), str(out_revision)
