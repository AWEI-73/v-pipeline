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
# Stable, project-local, segment-independent need_id
# ---------------------------------------------------------------------------

def allocate_need_id(project, need):
    """Return a stable project-local id. Explicit `need_id` wins; otherwise it
    is derived from semantic content (project + category + type + purpose) so
    reordering or renumbering segments never changes it."""
    explicit = need.get("need_id")
    if explicit:
        return str(explicit)
    basis = "|".join([
        str(project or ""),
        str(need.get("category") or ""),
        str(need.get("type") or ""),
        str(need.get("purpose") or ""),
    ])
    return "nd_" + hashlib.sha1(basis.encode("utf-8")).hexdigest()[:8]


# ---------------------------------------------------------------------------
# Normalization: legacy nested OR flat -> canonical flat
# ---------------------------------------------------------------------------

def _canonical_need(project, raw_need, *, segment_hint=None, seen=None):
    need_id = allocate_need_id(project, raw_need)
    if seen is not None:
        base, suffix = need_id, 2
        while need_id in seen:
            need_id = f"{base}_{suffix}"
            suffix += 1
        seen.add(need_id)
    out = {
        "need_id": need_id,
        "category": raw_need.get("category"),
        "type": raw_need.get("type"),
        "purpose": raw_need.get("purpose"),
        "count": raw_need.get("count", 1),
        "fallback_tier": raw_need.get("fallback_tier", 1),
        "must_have": bool(raw_need.get("must_have", False)),
    }
    if raw_need.get("fallback_options") is not None:
        out["fallback_options"] = list(raw_need.get("fallback_options") or [])
    if raw_need.get("duration_each") is not None:
        out["duration_each"] = raw_need.get("duration_each")
    # legacy segment-local id kept for human reference only — never a join key
    legacy_id = raw_need.get("id")
    if legacy_id is not None:
        out["display_id"] = str(legacy_id)
    if segment_hint is not None:
        out["segment_hint"] = segment_hint
    if raw_need.get("segment_hint") is not None:
        out["segment_hint"] = raw_need.get("segment_hint")
    return out


def normalize_material_needs(raw):
    """Return canonical flat material-needs. Accepts legacy nested
    ({segments:[{segment, needs:[...]}]}) or flat ({needs:[...]})."""
    raw = raw or {}
    project = raw.get("project")
    seen = set()
    needs = []
    if raw.get("needs") is not None:
        for raw_need in raw.get("needs") or []:
            needs.append(_canonical_need(project, raw_need, seen=seen))
    else:
        for seg in raw.get("segments") or []:
            segment_hint = seg.get("segment")
            for raw_need in seg.get("needs") or []:
                needs.append(_canonical_need(
                    project, raw_need, segment_hint=segment_hint, seen=seen))
    canonical = {
        "artifact_role": "material_needs",
        "version": 1,
        "project": project,
        "needs": needs,
    }
    for key in ("based_on_script", "generated_at"):
        if raw.get(key) is not None:
            canonical[key] = raw.get(key)
    return canonical


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def validate_material_needs(raw):
    """Validate and normalize. Returns {ok, errors, warnings, normalized}."""
    canonical = normalize_material_needs(raw)
    errors = []
    warnings = []
    needs = canonical["needs"]
    if not needs:
        warnings.append("material_needs has no needs")
    seen_ids = set()
    for need in needs:
        nid = need["need_id"]
        ref = nid or need.get("display_id") or "?"
        if nid in seen_ids:
            errors.append(f"duplicate need_id {nid}")
        seen_ids.add(nid)
        for field in REQUIRED_NEED_FIELDS:
            value = need.get(field)
            missing = (not value.strip()) if isinstance(value, str) else (not value)
            if missing:
                errors.append(f"need {ref} missing {field}")
        tier = need.get("fallback_tier")
        if tier is not None and tier not in VALID_FALLBACK_TIERS:
            errors.append(f"need {ref} fallback_tier {tier} not in 1-4")
        count = need.get("count")
        if not isinstance(count, int) or count <= 0:
            warnings.append(f"need {ref} count {count!r} invalid; treated as 1")
        # the deadlock the gap-analyzer skill warns about
        if need.get("must_have") and need.get("fallback_tier") == 1 \
                and not need.get("fallback_options"):
            warnings.append(
                f"need {ref} is must_have at tier 1 with no fallback_options "
                f"(unshootable -> deadlock risk)")
    return {"ok": not errors, "errors": errors, "warnings": warnings,
            "normalized": canonical}


def write_validated_needs(raw, out_path):
    result = validate_material_needs(raw)
    if result["ok"]:
        path = Path(out_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(result["normalized"], ensure_ascii=False, indent=2),
                        encoding="utf-8")
    return result


# ---------------------------------------------------------------------------
# Scene-level satisfies edge (candidate / accepted / rejected + lineage)
# ---------------------------------------------------------------------------

def make_satisfaction(need_id, status="candidate", *, reviewer=None, note=None, at=None,
                      previous_status=None):
    """Build one scene->need satisfaction entry. Timestamps are caller-supplied
    (no hidden clock) to keep the write path deterministic and testable."""
    if status not in VALID_STATUSES:
        raise ValueError(f"invalid satisfaction status: {status!r}")
    if not need_id:
        raise ValueError("satisfaction requires need_id")
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


def apply_satisfaction_verdict(material_map, verdict):
    """Apply a reviewer verdict that links material-map scenes to need_ids.

    Verdict shape::

        {"reviewer": "agent", "at": "...",
         "scenes": [{"scene_index": 0,
                     "satisfies": [{"need_id": "nd_ab12cd34",
                                    "status": "accepted", "note": "..."}]}]}

    Scenes without a verdict entry are untouched (backward compatible)."""
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
            if not need_id:
                continue
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
