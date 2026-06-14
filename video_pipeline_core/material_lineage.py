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

from .material_needs import need_ids, summarize_satisfaction, validate_material_needs


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
    """Read `material_fit.need_refs` per segment → {segment_ref: [need_id, ...]}.
    Only well-shaped non-empty string refs are returned; shape errors are the
    segment_contract validator's job (see spec_contract.validate_segment_contract)."""
    refs = {}
    for index, segment in enumerate(_iter_segments(contract)):
        if not isinstance(segment, dict):
            continue
        material_fit = segment.get("material_fit") or {}
        need_refs = material_fit.get("need_refs")
        if not isinstance(need_refs, list):
            continue
        clean = [r for r in need_refs if isinstance(r, str) and r.strip()]
        if clean:
            refs[_segment_ref(segment, index)] = clean
    return refs


def _satisfies_need_ids(material_maps):
    """Every need_id referenced by a scene satisfies edge (across all maps)."""
    out = set()
    for material_map in material_maps or []:
        for scene in material_map.get("scenes") or []:
            for edge in scene.get("satisfies") or []:
                nid = edge.get("need_id")
                if isinstance(nid, str) and nid.strip():
                    out.add(nid)
    return out


def link_lineage(material_needs, *, shooting_brief=None, material_maps=None, contract=None):
    """Join the four artifacts on `need_id` and report referential integrity.

    Returns a `material_lineage` artifact::

        {ok, errors, chain: {need_id: {requirement, in_brief, satisfied_by,
                                       contract_segments}}, dangling: {...}}

    `ok` is True iff no dangling reference exists — i.e. every brief requirement,
    satisfies edge, and contract need_ref resolves to a declared canonical need.
    The `chain` is a neutral join view (which scenes/segments point at each need
    and with what satisfaction status); it makes NO coverage decision — a need
    with an empty `satisfied_by` is reported as-is, never flagged as missing."""
    validation = validate_material_needs(material_needs)
    canonical = {need["need_id"] for need in validation["needs"]
                 if isinstance(need.get("need_id"), str) and need["need_id"].strip()}

    errors = []
    if not validation["ok"]:
        errors.append("material_needs invalid: " + "; ".join(validation["errors"]))

    brief_ids = shooting_brief_need_ids(shooting_brief) if shooting_brief is not None else set()
    satisfies_ids = _satisfies_need_ids(material_maps) if material_maps is not None else set()
    contract_refs = contract_need_refs(contract) if contract is not None else {}
    contract_ids = {nid for ids in contract_refs.values() for nid in ids}

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

    satisfaction = summarize_satisfaction(material_maps) if material_maps is not None else {}
    segments_by_need = {}
    for seg_ref, ids in contract_refs.items():
        for nid in ids:
            segments_by_need.setdefault(nid, []).append(seg_ref)

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
