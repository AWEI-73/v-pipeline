"""M6a — canonical material-needs contract, validator, and the scene-level
`satisfies` edge that links a requirement to the actual material that fills it.

Scope (M6a only):
  - validate + normalize `material_needs.json` (accepts legacy nested OR flat).
  - stable, project-local `need_id` that is NOT derived from segment number,
    so a requirement survives script revision / chapter renumbering.
  - scene-level `satisfies` edge with candidate / accepted / rejected status
    and review lineage.
  - a read-only inversion (scene->need edges into need->scenes) so the edge can
    be validated end to end.

Explicitly NOT in scope (do not add here): material_delta routing, BUILD
selection / Visual Diversity ranking, Node 14 / effects, supply_review changes,
M5b action spine.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path


REQUIRED_NEED_FIELDS = ("category", "type", "purpose")
VALID_STATUSES = ("candidate", "accepted", "rejected")
VALID_FALLBACK_TIERS = (1, 2, 3, 4)


# ---------------------------------------------------------------------------
# Three separated concerns (M6a-hardening):
#   1. allocation / migration  — assign an id ONCE to a need that has none.
#   2. validation              — strict checks; never allocates, never mutates
#                                the join key, never silently coerces types.
#   3. editing                 — content edits never touch need_id (a need that
#                                already has an id keeps it through migration).
# ---------------------------------------------------------------------------

def _migration_id(project, need):
    """Content fingerprint used ONLY to assign an id to a legacy need that has
    none. It is the *initial value*, not the identity: once a need carries a
    need_id, that id is preserved verbatim and never regenerated from content."""
    basis = "|".join([
        str(project or ""),
        str(need.get("category") or ""),
        str(need.get("type") or ""),
        str(need.get("purpose") or ""),
    ])
    return "nd_" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:8]


def _flatten(raw):
    """Flatten legacy nested or flat needs WITHOUT allocating ids. An existing
    need_id is preserved verbatim; an absent one stays None for the caller."""
    raw = raw or {}
    project = raw.get("project")
    if raw.get("needs") is not None:
        source = [(None, n) for n in raw.get("needs") or []]
    else:
        source = [(seg.get("segment"), n)
                  for seg in raw.get("segments") or []
                  for n in seg.get("needs") or []]
    rows = []
    for segment_hint, raw_need in source:
        row = {
            "need_id": raw_need.get("need_id"),          # may be None
            "category": raw_need.get("category"),
            "type": raw_need.get("type"),
            "purpose": raw_need.get("purpose"),
            "count": raw_need.get("count"),              # None == absent
            "fallback_tier": raw_need.get("fallback_tier", 1),
            "must_have": raw_need.get("must_have", False),  # type-checked later
        }
        if raw_need.get("fallback_options") is not None:
            # keep the raw value verbatim — type is validated, never coerced
            row["fallback_options"] = raw_need.get("fallback_options")
        if raw_need.get("duration_each") is not None:
            row["duration_each"] = raw_need.get("duration_each")
        if raw_need.get("id") is not None:               # legacy display only
            row["display_id"] = str(raw_need.get("id"))
        hint = raw_need.get("segment_hint", segment_hint)
        if hint is not None:
            row["segment_hint"] = hint
        rows.append(row)
    return project, rows


def migrate_material_needs(raw):
    """One-time allocation. Assigns an id ONLY to needs lacking one; an existing
    need_id is always preserved (so editing purpose/type/category never changes
    it). Content-identical fresh needs are disambiguated and noted."""
    project, rows = _flatten(raw)
    used = {row["need_id"] for row in rows if row.get("need_id")}
    notes = []
    for row in rows:
        if row.get("need_id"):
            continue
        candidate = base = _migration_id(project, row)
        suffix = 2
        while candidate in used:
            candidate = f"{base}_{suffix}"
            suffix += 1
        if candidate != base:
            notes.append(f"allocated {candidate} for content-identical need")
        row["need_id"] = candidate
        used.add(candidate)
        if row.get("count") is None:
            row["count"] = 1
    canonical = {"artifact_role": "material_needs", "version": 1,
                 "project": project, "needs": rows}
    for key in ("based_on_script", "generated_at"):
        if (raw or {}).get(key) is not None:
            canonical[key] = raw[key]
    if notes:
        canonical["migration_notes"] = notes
    return canonical


def _positive_int(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def _valid_tier(value):
    # bool is an int subclass and True == 1, so reject booleans explicitly.
    return isinstance(value, int) and not isinstance(value, bool) \
        and value in VALID_FALLBACK_TIERS


def validate_material_needs(raw):
    """Strict validation. Does NOT allocate ids, mutate join keys, or coerce
    types. A canonical need must carry an explicit need_id; duplicate explicit
    ids and bad types are errors, not silent fixes."""
    project, rows = _flatten(raw)
    errors, warnings = [], []
    if not rows:
        warnings.append("material_needs has no needs")
    counts = {}
    for row in rows:
        nid = row.get("need_id")
        ref = nid if isinstance(nid, str) and nid.strip() else (row.get("display_id") or "?")
        if not isinstance(nid, str) or not nid.strip():
            errors.append(f"need {ref} need_id must be a non-empty string, got {nid!r} "
                          f"(run migration to allocate a stable id)")
        else:
            counts[nid] = counts.get(nid, 0) + 1
        for field in REQUIRED_NEED_FIELDS:
            value = row.get(field)
            missing = (not value.strip()) if isinstance(value, str) else (not value)
            if missing:
                errors.append(f"need {ref} missing {field}")
        tier = row.get("fallback_tier")
        if not _valid_tier(tier):
            errors.append(f"need {ref} fallback_tier must be an integer 1-4, "
                          f"got {tier!r}")
        if not isinstance(row.get("must_have"), bool):
            errors.append(f"need {ref} must_have must be boolean, got "
                          f"{row.get('must_have')!r}")
        count = row.get("count")
        if count is None:
            warnings.append(f"need {ref} count absent; migration sets it to 1")
        elif not _positive_int(count):
            errors.append(f"need {ref} count must be a positive integer, got {count!r}")
        fallback_options = row.get("fallback_options")
        if fallback_options is not None and not (
                isinstance(fallback_options, list)
                and all(isinstance(item, str) for item in fallback_options)):
            errors.append(f"need {ref} fallback_options must be a list of strings, "
                          f"got {fallback_options!r}")
        if row.get("must_have") is True and row.get("fallback_tier") == 1 \
                and not row.get("fallback_options"):
            warnings.append(
                f"need {ref} is must_have at tier 1 with no fallback_options "
                f"(unshootable -> deadlock risk)")
    for nid, n in counts.items():
        if n > 1:
            errors.append(f"duplicate need_id {nid} ({n} needs) — join key must be unique")
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "project": project, "needs": rows}


def need_ids(raw):
    """Convenience: the set of declared need_ids (for satisfies validation)."""
    _project, rows = _flatten(raw)
    return {row["need_id"] for row in rows if row.get("need_id")}


# ---------------------------------------------------------------------------
# Scene-level satisfies edge (candidate / accepted / rejected + lineage)
# ---------------------------------------------------------------------------

def make_satisfaction(need_id, status="candidate", *, reviewer=None, note=None, at=None,
                      previous_status=None):
    """Build one scene->need satisfaction entry. Timestamps are caller-supplied
    (no hidden clock) to keep the write path deterministic and testable."""
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid satisfaction status: {status!r}")
    if not isinstance(need_id, str) or not need_id.strip():
        raise ValueError(f"satisfaction need_id must be a non-empty string, got {need_id!r}")
    lineage = {}
    for key, value in (("reviewer", reviewer), ("note", note), ("at", at),
                       ("previous_status", previous_status)):
        if value is not None:
            lineage[key] = value
    return {"need_id": str(need_id), "status": status, "lineage": lineage}


def _merge_satisfies(existing, incoming):
    """Replace by need_id; record previous_status when a status changes."""
    index = {entry["need_id"]: entry for entry in (existing or [])
             if isinstance(entry, dict) and entry.get("need_id")}
    for entry in incoming:
        prior = index.get(entry["need_id"])
        if prior and prior.get("status") != entry.get("status") \
                and "previous_status" not in entry["lineage"]:
            entry["lineage"]["previous_status"] = prior.get("status")
        index[entry["need_id"]] = entry
    return list(index.values())


def apply_satisfaction_verdict(material_map, verdict, *, valid_need_ids=None):
    """Apply a reviewer verdict that links material-map scenes to need_ids.

    Verdict shape::

        {"reviewer": "agent", "at": "...",
         "scenes": [{"scene_index": 0,
                     "satisfies": [{"need_id": "nd_ab12cd34",
                                    "status": "accepted", "note": "..."}]}]}

    ``valid_need_ids`` is REQUIRED (the canonical need_id set, e.g.
    `need_ids(material_needs)`). Omitting it, or referencing a need_id outside
    it, raises ValueError — an unchecked or typo'd edge must never reach a
    future delta as a phantom requirement. Scenes without a verdict entry are
    untouched (backward compatible)."""
    if valid_need_ids is None:
        raise ValueError(
            "valid_need_ids is required: satisfies edges must be validated "
            "against the canonical material_needs (pass need_ids(...))")
    known = set(valid_need_ids)
    scenes = material_map.get("scenes") or []
    default_reviewer = verdict.get("reviewer")
    default_at = verdict.get("at")
    for item in verdict.get("scenes") or []:
        index = item.get("scene_index")
        if not isinstance(index, int) or not (0 <= index < len(scenes)):
            continue
        incoming = []
        for raw in item.get("satisfies") or []:
            need_id = raw.get("need_id")
            if need_id is None:
                continue
            if not isinstance(need_id, str) or not need_id.strip():
                raise ValueError(
                    f"satisfies need_id must be a non-empty string, got {need_id!r}")
            if need_id not in known:
                raise ValueError(
                    f"satisfies references unknown need_id {need_id!r} "
                    f"(not in canonical material_needs)")
            incoming.append(make_satisfaction(
                need_id,
                raw.get("status", "candidate"),
                reviewer=raw.get("reviewer") or default_reviewer,
                note=raw.get("note"),
                at=raw.get("at") or default_at,
            ))
        if incoming:
            scenes[index]["satisfies"] = _merge_satisfies(
                scenes[index].get("satisfies"), incoming)
    return material_map


def summarize_satisfaction(material_maps):
    """Read-only inversion of scene->need edges into need->scenes.

    NOT a delta: no covered/thin/missing routing, no script decisions — just
    surfaces which scenes point at which need_id and with what status."""
    summary = {}
    for material_map in material_maps or []:
        asset_id = material_map.get("asset_id")
        for scene_index, scene in enumerate(material_map.get("scenes") or []):
            for entry in scene.get("satisfies") or []:
                need_id = entry.get("need_id")
                status = entry.get("status")
                if not need_id:
                    continue
                bucket = summary.setdefault(
                    need_id, {"accepted": [], "candidate": [], "rejected": []})
                ref = {"asset_id": asset_id, "scene_index": scene_index}
                if status in bucket:
                    bucket[status].append(ref)
    return summary
