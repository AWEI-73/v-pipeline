"""M6d — Independent Material-Map Lifecycle (orchestration only).

Compose the existing M6a–M6c canonical tools into ONE runnable, pausable,
resumable material-map workflow. M6d adds NO new editing capability and NO second
source of truth: it strictly resolves the artifacts that exist right now, calls
the canonical tools, decides the current lifecycle stage, and emits the next
action (and a BUILD handoff only when the work is genuinely build-ready).

Single source of truth (unchanged):
  required → material_needs.json
  actual   → per-asset maps / project_material_map.json
  diff     → material_delta.json
  revision → material_revision.json + revised_segment_contract.json

Three entry points are NOT exclusive workflows — they are different starting
artifacts; the stage is derived from what is present:
  existing_material : maps, no needs   → inventory, discuss requirements
  script_first      : needs, no maps   → shooting brief, await material
  partial           : needs + some maps → fresh delta drives the stage

The workflow may stop at any planning/await stage WITHOUT producing a video.
A `build_ready` stage is the ONLY one that yields a handoff, which `run_contract`
still re-verifies with its own fresh M6b/M6c gate (M6d never bypasses it).

Reuses ONLY: validate_material_needs, build_shooting_brief,
build_project_material_map/expand_project_material_map/load_asset_maps,
link_lineage, compute_material_delta, gate_from_delta, apply_revisions,
write_revision_artifacts, and contract_adapter's strict material_db/map loaders.
"""
from __future__ import annotations

import json
import os
from pathlib import Path

from . import spec_contract
from .contract_adapter import (
    _load_current_material_maps, _load_material_db_strict, _resolve_declared_ref,
)
from .material_delta import compute_material_delta, gate_from_delta
from .material_lineage import build_shooting_brief, link_lineage
from .material_needs import validate_material_needs
from .material_revision import apply_revisions, write_revision_artifacts
from .project_material_map import (
    build_project_material_map, expand_project_material_map, load_asset_maps,
)

STAGES = (
    "inventory_ready", "await_requirements_discussion", "await_material",
    "await_map_review", "await_revision_decision", "revision_blocked",
    "build_ready", "invalid",
)


def _load_json(path):
    with open(path, encoding="utf-8-sig") as handle:
        return json.load(handle)


def _report(stage, *, can_build=False, entry_point=None, refs=None, blocking=None,
            warnings=None, next_action=None, build_handoff=None, metrics=None):
    report = {
        "artifact_role": "material_map_lifecycle", "version": 1,
        "stage": stage, "can_build": can_build, "entry_point": entry_point,
        "refs": {"material_needs": None, "shooting_brief": None,
                 "project_material_map": None, "material_delta": None,
                 "revision_decisions": None, "revised_contract": None},
        "blocking": blocking or [], "warnings": warnings or [],
        "next_action": next_action, "build_handoff": build_handoff,
    }
    if refs:
        report["refs"].update(refs)
    if metrics is not None:
        report["metrics"] = metrics
    return report


def _same_path(a, b):
    return os.path.normcase(os.path.realpath(str(a))) == os.path.normcase(os.path.realpath(str(b)))


def _load_actual(kind, project_map_ref, maps_dir, material_db_ref):
    """Strict load of the single declared actual-side source. Returns (maps, error).
    Reuses the canonical loaders; any malformed/missing input is fail-closed."""
    if kind == "project_map":
        if not Path(project_map_ref).exists():
            return None, f"project_map_ref not found: {project_map_ref}"
        try:
            return expand_project_material_map(_load_json(project_map_ref)), None
        except (OSError, ValueError) as exc:
            return None, f"project_material_map could not be loaded: {exc}"
    if kind == "maps_dir":
        path = Path(maps_dir)
        if not path.exists() or not path.is_dir():
            return None, f"maps_dir not found or not a directory: {maps_dir}"
        try:
            return load_asset_maps(maps_dir), None
        except (OSError, ValueError) as exc:
            return None, f"per-asset maps could not be loaded: {exc}"
    if kind == "material_db":
        payload, error = _load_material_db_strict(material_db_ref)
        if error:
            return None, error
        maps, map_error = _load_current_material_maps(payload, Path(material_db_ref).parent)
        if map_error:
            return None, map_error
        return maps, None
    return None, None


def _total_satisfies(maps):
    return sum(len(scene.get("satisfies") or [])
              for m in maps or [] for scene in (m.get("scenes") or []))


def _build_ready_or_error(contract, contract_ref, needs_ref, categories,
                          *, decisions_ref=None, require_decisions_binding=False):
    """Return an error string if this is NOT a runnable build_ready, else None.
    The contract must validate AND its material_needs_ref must bind to the same
    needs file the lifecycle used, so run_contract's fresh gate re-verifies the
    same inputs. A revised build also requires the contract to declare the same
    revision_decisions_ref so run_contract re-derives the waivers."""
    validation = spec_contract.validate_segment_contract(contract, categories=categories)
    if not validation["ok"]:
        return "contract failed spec_contract validation: " + "; ".join(validation["errors"])
    nref = contract.get("material_needs_ref")
    if not isinstance(nref, str) or not nref.strip():
        return "contract does not declare material_needs_ref (run_contract gate cannot re-verify)"
    npath, nerr = _resolve_declared_ref(nref.strip(), contract_ref)
    if nerr:
        return f"contract.material_needs_ref unresolved: {nerr}"
    if not _same_path(npath, needs_ref):
        return (f"contract.material_needs_ref ({nref}) does not bind to the lifecycle "
                f"material_needs ({needs_ref})")
    if require_decisions_binding:
        dref = contract.get("revision_decisions_ref")
        if not isinstance(dref, str) or not dref.strip():
            return ("a revised build requires the contract to declare revision_decisions_ref "
                    "so run_contract re-applies the decisions and re-derives the waivers")
        dpath, derr = _resolve_declared_ref(dref.strip(), contract_ref)
        if derr or decisions_ref is None or not _same_path(dpath, decisions_ref):
            return "contract.revision_decisions_ref does not bind to the lifecycle decisions"
    return None


def run_lifecycle(*, out_dir, needs_ref=None, maps_dir=None, project_map_ref=None,
                  material_db_ref=None, contract_ref=None, decisions_ref=None,
                  categories_path=None):
    """Compute the current lifecycle stage from the artifacts present and write
    the canonical artifacts the stage produces. Returns the lifecycle report
    (a projection of refs + summaries, never a second canonical schema)."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    refs = {}

    # ── Fix: exactly ONE actual-side source (no silent priority). material_db is
    #    the ONLY source that can lead to build_ready; maps_dir/project_map are
    #    inventory-only. ────────────────────────────────────────────────────────
    provided = [name for name, val in (("project_map", project_map_ref),
                                       ("maps_dir", maps_dir),
                                       ("material_db", material_db_ref)) if val]
    if len(provided) > 1:
        return _report("invalid", refs=refs, next_action="provide_inputs",
                       blocking=[f"multiple actual-side sources provided ({provided}); "
                                 f"provide exactly one"])
    source_kind = provided[0] if provided else None
    build_source = source_kind == "material_db"

    # ── Fix: categories fail-closed (a declared-but-bad categories file blocks). ─
    categories = None
    if categories_path:
        try:
            categories = set(spec_contract.load_material_categories(categories_path))
        except (OSError, ValueError) as exc:
            return _report("invalid", refs=refs, next_action="provide_inputs",
                           blocking=[f"categories could not be loaded: {exc}"])

    # ── resolve the single actual-side source (strict) ───────────────────────
    maps, maps_error = _load_actual(source_kind, project_map_ref, maps_dir, material_db_ref)
    if maps_error:
        return _report("invalid", blocking=[maps_error],
                       next_action="revise:material(material_delta)", refs=refs)

    # ── existing-material entry: maps but no declared needs ──────────────────
    if not needs_ref:
        if not maps:
            return _report("invalid", blocking=["no material_needs and no material maps"],
                           next_action="provide_inputs", refs=refs)
        try:
            project_map = build_project_material_map(maps)   # no needs -> library aggregate
        except ValueError as exc:
            return _report("invalid", blocking=[f"project map aggregation failed: {exc}"],
                           next_action="revise:material(material_delta)", refs=refs)
        pmm_path = out_dir / "project_material_map.json"
        pmm_path.write_text(json.dumps(project_map, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        refs["project_material_map"] = str(pmm_path)
        return _report("await_requirements_discussion", entry_point="existing_material",
                       refs=refs, metrics=project_map["metrics"],
                       warnings=["material exists but no requirements declared — discuss "
                                 "the script against this inventory before BUILD"],
                       next_action="await_requirements_discussion")

    # ── needs declared: validate ─────────────────────────────────────────────
    try:
        needs = _load_json(needs_ref)
    except (OSError, ValueError) as exc:
        return _report("invalid", blocking=[f"material_needs could not be parsed: {exc}"],
                       next_action="revise:material(material_delta)", refs=refs)
    refs["material_needs"] = str(needs_ref)
    validation = validate_material_needs(needs)
    if not validation["ok"]:
        return _report("invalid", blocking=validation["errors"],
                       next_action="revise:material(material_delta)", refs=refs)

    # shooting brief is always derivable once needs are canonical
    try:
        brief = build_shooting_brief(needs)
    except ValueError as exc:
        return _report("invalid", blocking=[str(exc)],
                       next_action="revise:material(material_delta)", refs=refs)
    brief_path = out_dir / "shooting_brief.json"
    brief_path.write_text(json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
    refs["shooting_brief"] = str(brief_path)

    # contract (optional; required to actually BUILD or to revise)
    contract = None
    if contract_ref:
        try:
            contract = _load_json(contract_ref)
        except (OSError, ValueError) as exc:
            return _report("invalid", blocking=[f"contract could not be parsed: {exc}"],
                           next_action="revise:material(material_delta)", refs=refs)

    # aggregate the project map WITH needs (validates satisfies edges / dangling)
    if maps:
        try:
            project_map = build_project_material_map(maps, needs=needs)
        except ValueError as exc:
            return _report("invalid", blocking=[f"project map / satisfies invalid: {exc}"],
                           next_action="revise:material(material_delta)", refs=refs)
        pmm_path = out_dir / "project_material_map.json"
        pmm_path.write_text(json.dumps(project_map, ensure_ascii=False, indent=2),
                            encoding="utf-8")
        refs["project_material_map"] = str(pmm_path)

    # reference integrity across needs/brief/maps/contract
    lineage = link_lineage(needs, shooting_brief=brief, material_maps=maps, contract=contract)
    if not lineage["ok"]:
        return _report("invalid", blocking=lineage["errors"],
                       next_action="revise:material(material_delta)", refs=refs)

    # fresh delta (broken join fails, never silently "missing")
    delta = compute_material_delta(needs, maps)
    if not delta["ok"]:
        return _report("invalid", blocking=delta["errors"],
                       next_action="revise:material(material_delta)", refs=refs)
    delta_path = out_dir / "material_delta.json"
    delta_path.write_text(json.dumps(delta, ensure_ascii=False, indent=2), encoding="utf-8")
    refs["material_delta"] = str(delta_path)
    entry_point = "partial" if maps else "script_first"
    warnings = [f"need {d['need_id']} is {d['outcome']}: {d['reason']}"
                for d in delta["deltas"] if d["outcome"] in ("thin", "excess")]

    # ── revision branch: decisions are ALWAYS canonically validated ──────────
    if decisions_ref:
        refs["revision_decisions"] = str(decisions_ref)
        try:
            decisions = _load_json(decisions_ref)
        except (OSError, ValueError) as exc:
            return _report("invalid", blocking=[f"revision_decisions could not be parsed: {exc}"],
                           next_action="revise:material(material_revision)", refs=refs)
        # a revision is defined against a contract; validate decisions unconditionally
        # (reuse apply_revisions — the single canonical validator — even if none are
        # accepted; non-list/dup/unknown/illegal status/route all fail here).
        if contract is None:
            return _report("invalid", entry_point=entry_point, refs=refs,
                           blocking=["revision_decisions require a contract to validate against"],
                           next_action="revise:material(material_revision)")
        report, revised = apply_revisions(contract, delta, decisions, categories=categories)
        if not report["ok"]:
            return _report("invalid", entry_point=entry_point, refs=refs,
                           blocking=report["errors"],
                           next_action="revise:material(material_revision)")
        accepted = any(isinstance(d, dict) and d.get("status") == "accepted"
                       for d in decisions)
        if not accepted:
            # valid but nothing accepted -> awaiting human acceptance; no revision applied
            return _report("await_revision_decision", entry_point=entry_point, refs=refs,
                           warnings=warnings, next_action="await_revision_decision")
        revised_path = out_dir / "revised_segment_contract.json"
        revision_path = out_dir / "material_revision.json"
        try:
            write_revision_artifacts(revised, report, revised_path, revision_path)
        except (ValueError, OSError, RuntimeError) as exc:
            return _report("invalid", entry_point=entry_point, refs=refs,
                           blocking=[f"could not write revision artifacts: {exc}"],
                           next_action="revise:material(material_revision)")
        refs["revised_contract"] = str(revised_path)
        gate = gate_from_delta(delta, waivers=report["waivers"])
        if (gate["status"] == "pass") != bool(report["ready_for_build"]):
            return _report("invalid", entry_point=entry_point, refs=refs,
                           blocking=["revision/gate disagreement"],
                           next_action="revise:material(material_revision)")
        if report["ready_for_build"] and report["next_action"] is None:
            if not build_source:
                return _report("await_map_review", entry_point=entry_point, refs=refs,
                               warnings=warnings + ["revision applied and gate passes; provide "
                                                    "a --material-db to BUILD the revised result"],
                               next_action="await_map_review")
            err = _build_ready_or_error(contract, contract_ref, needs_ref, categories,
                                        decisions_ref=decisions_ref,
                                        require_decisions_binding=True)
            if err:
                return _report("invalid", entry_point=entry_point, refs=refs,
                               blocking=[err], next_action="revise:material(material_revision)")
            # handoff points at the ORIGINAL contract (it declares the bound
            # material_needs_ref + revision_decisions_ref); run_contract re-runs M6c
            # fresh, re-derives the waivers, and BUILDs the revised result — the
            # revised_segment_contract.json is recorded as evidence in refs.
            handoff = _build_handoff(contract_ref, material_db_ref, needs_ref, report["waivers"])
            if handoff is None:
                return _report("invalid", entry_point=entry_point, refs=refs,
                               blocking=["build handoff refs do not all exist"],
                               next_action="revise:material(material_revision)")
            return _report("build_ready", can_build=True, entry_point=entry_point,
                           refs=refs, warnings=warnings, next_action="build",
                           build_handoff=handoff)
        if gate["status"] == "block":
            return _report("revision_blocked", entry_point=entry_point, refs=refs,
                           blocking=[f"unresolved after revision: {gate['blocking_need_ids']}"],
                           warnings=warnings, next_action=report["next_action"] or "await_material")
        if report["next_action"] == "await_review":
            return _report("await_revision_decision", entry_point=entry_point, refs=refs,
                           warnings=warnings, next_action="await_review")
        return _report("await_material", entry_point=entry_point, refs=refs,
                       warnings=warnings, next_action=report["next_action"] or "await_material")

    # ── no decisions: maps with scenes but no satisfies edges → review first ──
    if maps and _total_satisfies(maps) == 0:
        return _report("await_map_review", entry_point=entry_point, refs=refs,
                       warnings=warnings, next_action="await_map_review")

    gate = gate_from_delta(delta)
    if gate["status"] == "block":
        return _report("await_material", entry_point=entry_point, refs=refs,
                       blocking=[f"unresolved must_have needs: {gate['blocking_need_ids']}"],
                       warnings=warnings, next_action="await_material")
    # gate passes — build_ready needs material_db (the only runnable source) + a
    # contract whose material_needs_ref binds to the lifecycle needs.
    if not build_source:
        return _report("await_map_review", entry_point=entry_point, refs=refs,
                       warnings=warnings + ["material is sufficient; provide a --material-db "
                                            "(the only runnable BUILD source) + contract to BUILD"],
                       next_action="await_map_review")
    if contract is None:
        return _report("await_map_review", entry_point=entry_point, refs=refs,
                       warnings=warnings + ["material is sufficient; attach a contract to BUILD"],
                       next_action="await_map_review")
    err = _build_ready_or_error(contract, contract_ref, needs_ref, categories)
    if err:
        return _report("invalid", entry_point=entry_point, refs=refs,
                       blocking=[err], next_action="revise:material(material_delta)")
    handoff = _build_handoff(contract_ref, material_db_ref, needs_ref, [])
    if handoff is None:
        return _report("invalid", entry_point=entry_point, refs=refs,
                       blocking=["build handoff refs do not all exist"],
                       next_action="revise:material(material_delta)")
    return _report("build_ready", can_build=True, entry_point=entry_point, refs=refs,
                   warnings=warnings, next_action="build", build_handoff=handoff)


def _build_handoff(contract_ref, material_db_ref, needs_ref, waivers):
    """Build a BUILD handoff that points only at EXISTING files. Returns None if
    any required ref is missing (caller treats that as fail-closed)."""
    if not contract_ref or not Path(contract_ref).exists():
        return None
    if needs_ref and not Path(needs_ref).exists():
        return None
    if material_db_ref and not Path(material_db_ref).exists():
        return None
    return {
        "contract_ref": str(contract_ref),
        "material_db_ref": str(material_db_ref) if material_db_ref else None,
        "material_needs_ref": str(needs_ref) if needs_ref else None,
        "revision_waivers": waivers or [],
        "ready_for_build": True,
    }
