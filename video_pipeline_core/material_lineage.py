"""M6a Lineage Integration — the end-to-end *reference chain* that lets one
stable requirement be traced through every artifact:

    need_id
      → shooting-brief requirement (`shooting_brief.requirements[].need_id`)
      → scene satisfies edge       (`material_map.scenes[].satisfies[].need_id`)
      → revised segment_contract   (`segment.material_fit.need_refs[]`)

Scope (lineage ONLY): build the brief projection that carries the join key,
read the contract's need references, and link the four artifacts into one join
view while detecting *dangling references* (any hop pointing at a need_id that
is not in the canonical `material_needs`).

Explicitly NOT in scope (this is the M6b boundary — do not add here):
`material_delta` decisions, covered/thin/missing classification, fallback route
selection, script revision, BUILD selection / Visual Diversity ranking. A
requirement with no satisfying scene is NOT flagged here — that is a coverage
verdict M6b owns; lineage only reports the join and broken references.
"""
from __future__ import annotations

from .material_needs import VALID_STATUSES, validate_material_needs


_BRIEF_PROJECTION_FIELDS = (
    "category", "type", "purpose", "count", "must_have",
    "fallback_tier", "fallback_options", "segment_hint",
)


def build_shooting_brief(material_needs):
    """Project canonical material_needs into a structured shooting-brief skeleton
    whose every requirement carries its `need_id` (the join key the human-authored
    prose brief must preserve). The needs are strict-validated first; an invalid
    or un-migrated map raises (run `validate-needs --migrate` to allocate ids).

    This is a projection, NOT a second required-map format: it copies the
    requirement fields verbatim and adds nothing the canonical map does not
    already declare."""
    result = validate_material_needs(material_needs)
    if not result["ok"]:
        raise ValueError(
            "cannot build shooting brief from invalid material_needs: "
            + "; ".join(result["errors"]))
    requirements = []
    for need in result["needs"]:
        req = {"need_id": need["need_id"]}
        for field in _BRIEF_PROJECTION_FIELDS:
            if need.get(field) is not None:
                req[field] = need[field]
        requirements.append(req)
    return {"artifact_role": "shooting_brief", "version": 1,
            "project": result["project"], "requirements": requirements}


def shooting_brief_need_ids(shooting_brief):
    """The set of need_ids a shooting brief references (non-empty strings only)."""
    out = set()
    for req in (shooting_brief or {}).get("requirements") or []:
        nid = req.get("need_id")
        if isinstance(nid, str) and nid.strip():
            out.add(nid)
    return out


def _iter_segments(contract):
    if isinstance(contract, dict):
        return contract.get("segments") or []
    if isinstance(contract, list):
        return contract
    return []


def _segment_ref(segment, index):
    core = segment.get("core") or {}
    return core.get("section_role") or segment.get("segment") or f"#{index}"


def contract_need_refs(contract):
    """Per-segment need_refs as ORDERED RECORDS — never a dict keyed by
    `section_role`, which can repeat and would silently overwrite a sibling's
    references (and lose a dangling ref on the first of two same-role segments)::

        [{"segment_ref": <display>, "segment_index": <stable int>,
          "need_refs": <raw value from material_fit.need_refs>}]

    A record is emitted for every segment that declares a `need_refs` key, even a
    malformed value — the linker validates shape and reports errors rather than
    this reader silently dropping illegal refs. Segments without the key do not
    participate in lineage and are omitted."""
    records = []
    for index, segment in enumerate(_iter_segments(contract)):
        if not isinstance(segment, dict):
            continue
        material_fit = segment.get("material_fit")
        if not isinstance(material_fit, dict) or "need_refs" not in material_fit:
            continue
        records.append({"segment_ref": _segment_ref(segment, index),
                        "segment_index": index,
                        "need_refs": material_fit.get("need_refs")})
    return records


def _collect_brief_ids(shooting_brief, errors):
    """Validate brief requirement shape; collect the need_ids it references."""
    ids = set()
    requirements = shooting_brief.get("requirements")
    if not isinstance(requirements, list):
        errors.append(f"shooting_brief.requirements must be a list, got {requirements!r}")
        return ids
    for i, req in enumerate(requirements):
        if not isinstance(req, dict):
            errors.append(f"shooting_brief requirement #{i} must be an object, got {req!r}")
            continue
        nid = req.get("need_id")
        if not isinstance(nid, str) or not nid.strip():
            errors.append(f"shooting_brief requirement #{i} need_id must be a "
                          f"non-empty string, got {nid!r}")
            continue
        ids.add(nid)
    return ids


def _collect_contract_ids(contract, errors):
    """Validate each segment's need_refs shape; collect ids + segments_by_need."""
    ids, segments_by_need = set(), {}
    for rec in contract_need_refs(contract):
        refs = rec["need_refs"]
        label = f"contract segment {rec['segment_ref']!r} (index {rec['segment_index']})"
        if not (isinstance(refs, list) and refs
                and all(isinstance(r, str) and r.strip() for r in refs)):
            errors.append(f"{label} need_refs must be a non-empty list of need_id "
                          f"strings, got {refs!r}")
            continue
        for nid in refs:
            ids.add(nid)
            segments_by_need.setdefault(nid, []).append(rec["segment_ref"])
    return ids, segments_by_need


def _collect_satisfies(material_maps, errors):
    """Validate scene satisfies-edge shape; collect ids + a crash-safe inversion
    (need_id -> {status: [{asset_id, scene_index}]}). Reuses material_needs'
    VALID_STATUSES — no parallel status vocabulary."""
    ids, satisfaction = set(), {}
    if not isinstance(material_maps, list):
        errors.append(f"material_maps must be a list, got {material_maps!r}")
        return ids, satisfaction
    for material_map in material_maps:
        if not isinstance(material_map, dict):
            errors.append(f"material map must be an object, got {material_map!r}")
            continue
        asset_id = material_map.get("asset_id")
        scenes = material_map.get("scenes") or []
        if not isinstance(scenes, list):
            errors.append(f"asset {asset_id!r} scenes must be a list, got {scenes!r}")
            continue
        for index, scene in enumerate(scenes):
            if not isinstance(scene, dict):
                errors.append(f"asset {asset_id!r} scene {index} must be an object, got {scene!r}")
                continue
            edges = scene.get("satisfies")
            if edges is None:
                continue
            if not isinstance(edges, list):
                errors.append(f"asset {asset_id!r} scene {index} satisfies must be a list, got {edges!r}")
                continue
            for edge in edges:
                ref = f"asset {asset_id!r} scene {index}"
                if not isinstance(edge, dict):
                    errors.append(f"{ref} satisfies edge must be an object, got {edge!r}")
                    continue
                nid = edge.get("need_id")
                if not isinstance(nid, str) or not nid.strip():
                    errors.append(f"{ref} satisfies need_id must be a non-empty string, got {nid!r}")
                    continue
                status = edge.get("status")
                if status not in VALID_STATUSES:
                    errors.append(f"{ref} satisfies status must be one of "
                                  f"{VALID_STATUSES}, got {status!r}")
                    continue
                ids.add(nid)
                satisfaction.setdefault(
                    nid, {"accepted": [], "candidate": [], "rejected": []}
                )[status].append({"asset_id": asset_id, "scene_index": index})
    return ids, satisfaction


def link_lineage(material_needs, *, shooting_brief=None, material_maps=None, contract=None):
    """Join the four artifacts on `need_id` and report referential integrity.

    Returns a `material_lineage` artifact::

        {ok, errors, chain: {need_id: {requirement, in_brief, satisfied_by,
                                       contract_segments}}, dangling: {...}}

    Every artifact reference that is actually supplied is shape-validated first
    (brief requirements are objects with a non-empty-string need_id; contract
    need_refs is a non-empty list of need_id strings; satisfies edges are objects
    with a non-empty-string need_id and a candidate/accepted/rejected status).
    Malformed input yields `ok=False` + `errors` — never a crash, never a silent
    drop. `ok` is True iff there is no shape error AND no dangling reference (a
    well-shaped ref to a need_id absent from canonical needs).

    The `chain` is a neutral join view; it makes NO coverage decision — a need
    with an empty `satisfied_by` is reported as-is, never flagged as missing."""
    validation = validate_material_needs(material_needs)
    canonical = {need["need_id"] for need in validation["needs"]
                 if isinstance(need.get("need_id"), str) and need["need_id"].strip()}

    errors = []
    if not validation["ok"]:
        errors.append("material_needs invalid: " + "; ".join(validation["errors"]))

    brief_ids = _collect_brief_ids(shooting_brief, errors) if shooting_brief is not None else set()
    contract_ids, segments_by_need = (
        _collect_contract_ids(contract, errors) if contract is not None else (set(), {}))
    satisfies_ids, satisfaction = (
        _collect_satisfies(material_maps, errors) if material_maps is not None else (set(), {}))

    dangling = {}

    def _record_dangling(kind, ids):
        bad = sorted(nid for nid in ids if nid not in canonical)
        if bad:
            dangling[kind] = bad
            for nid in bad:
                errors.append(
                    f"{kind} references unknown need_id {nid!r} "
                    f"(not in canonical material_needs)")

    _record_dangling("shooting_brief", brief_ids)
    _record_dangling("satisfies_edge", satisfies_ids)
    _record_dangling("contract_need_ref", contract_ids)

    chain = {}
    for nid in sorted(canonical):
        chain[nid] = {
            "requirement": True,
            "in_brief": nid in brief_ids,
            "satisfied_by": satisfaction.get(nid, {"accepted": [], "candidate": [], "rejected": []}),
            "contract_segments": segments_by_need.get(nid, []),
        }

    return {"artifact_role": "material_lineage", "version": 1,
            "ok": not errors, "errors": errors, "dangling": dangling,
            "chain": chain}
