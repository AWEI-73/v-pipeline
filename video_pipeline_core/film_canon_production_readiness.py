"""Pre-render production readiness for registered film canon routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping

from .film_canon_registry import write_film_canon_route_dry_run


_READINESS_ARTIFACTS = [
    "product_route_review_decision.json",
    "reviewed_catalog_map.json",
    "story_material_planning_handoff.json",
    "opener_closer_design_handoff.json",
    "audio_subtitle_review_handoff.json",
    "production_readiness_gate.json",
    "production_worker_handoff_prompt.md",
    "product_route_review_packet.md",
    "product_route_review_packet.json",
]


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def build_product_route_review_decision(
    *,
    decision: str = "pending_review",
    reviewer: str = "none",
    notes: str = "",
    approve_all_reviewed: bool = False,
    module_overrides: Iterable[Mapping[str, Any]] | None = None,
    created_by: str = "film_canon_readiness",
) -> dict[str, Any]:
    reviewer_type = "human" if reviewer == "human" else reviewer
    return {
        "artifact_role": "product_route_review_decision",
        "version": 1,
        "decision": decision,
        "reviewer": reviewer,
        "reviewer_type": reviewer_type,
        "notes": notes,
        "approve_all_reviewed": bool(approve_all_reviewed),
        "module_overrides": [dict(item) for item in (module_overrides or [])],
        "created_by": created_by,
        "is_final_delivery_approval": False,
        "clears_story_human_review": False,
    }


def _load_product_route_review_decision(path: Path) -> dict[str, Any]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must contain a JSON object")
    if data.get("artifact_role") != "product_route_review_decision":
        raise ValueError(f"{path} is not a product route review decision")
    return data


def _load_route_catalog(route_dir: Path) -> dict[str, Any]:
    for name in ("training_catalog_map.real_source.json", "catalog_map.json"):
        path = route_dir / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("route dry-run catalog map is missing")


def _load_route_packet(route_dir: Path) -> dict[str, Any]:
    for name in ("graduation_real_source_review_packet.json", "review_packet.json"):
        path = route_dir / name
        if path.is_file():
            return json.loads(path.read_text(encoding="utf-8"))
    raise FileNotFoundError("route dry-run review packet is missing")


def _decision_is_human_approved(decision: Mapping[str, Any]) -> bool:
    return (
        _clean(decision.get("decision")) == "approved"
        and (
            _clean(decision.get("reviewer")) == "human"
            or _clean(decision.get("reviewer_type")) == "human"
        )
        and bool(decision.get("approve_all_reviewed"))
    )


def _catalog_status_for_decision(decision: Mapping[str, Any]) -> str:
    value = _clean(decision.get("decision"))
    if _decision_is_human_approved(decision):
        return "accepted"
    if value == "revision_requested":
        return "needs_reassign"
    if value == "rejected":
        return "rejected"
    return "pending_review"


def _module_overrides(decision: Mapping[str, Any]) -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for item in decision.get("module_overrides") or []:
        if not isinstance(item, Mapping):
            continue
        module_id = _clean(item.get("module_id"))
        status = _clean(item.get("status"))
        if not module_id or not status:
            continue
        out[module_id] = {
            "module_id": module_id,
            "status": status,
            "review_note": _clean(item.get("review_note") or item.get("note")),
        }
    return out


def _reviewed_catalog_map(catalog: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
    default_status = _catalog_status_for_decision(decision)
    overrides = _module_overrides(decision)
    modules: list[dict[str, Any]] = []
    counts = {
        "accepted": 0,
        "rejected": 0,
        "needs_reassign": 0,
        "optional": 0,
        "missing": 0,
        "pending_review": 0,
    }
    for module in catalog.get("modules", []):
        module_id = _clean(module.get("module_id"))
        override = overrides.get(module_id)
        status = override["status"] if override else default_status
        review_note = (
            override["review_note"]
            if override and override.get("review_note")
            else (
                "human product-route approval"
                if status == "accepted"
                else _clean(decision.get("notes"), "product-route human review required")
            )
        )
        assignments = []
        raw_assignments = module.get("material_assignments") or []
        if not raw_assignments:
            missing_status = status if override else "missing"
            counts[missing_status] = counts.get(missing_status, 0) + 1
        for item in raw_assignments:
            reviewed = {
                "module_id": module_id,
                "source_relative_path": item.get("source_relative_path"),
                "agent_filled": bool(item.get("agent_filled") or item.get("authority") == "agent_filled"),
                "human_review_status": status,
                "review_note": review_note,
                "original_assignment": item,
            }
            assignments.append(reviewed)
            counts[status] = counts.get(status, 0) + 1
        modules.append({
            "module_id": module_id,
            "reviewed_assignments": assignments,
            "module_review_status": status if assignments else (status if override else "missing"),
            "module_review_note": review_note,
            "module_override": bool(override),
        })
    return {
        "artifact_role": "reviewed_catalog_map",
        "version": 1,
        "film_type": catalog.get("film_type") or "graduation_training_film",
        "modules": modules,
        "summary": {
            "status_counts": counts,
            "total_reviewed_assignments": sum(counts.values()) - counts["missing"],
            "requires_human_review": not _decision_is_human_approved(decision),
            "module_override_count": len(overrides),
        },
    }


def _story_material_handoff(film_type: str, packet: Mapping[str, Any], reviewed: Mapping[str, Any], decision: Mapping[str, Any]) -> dict[str, Any]:
    accepted = [
        module["module_id"]
        for module in reviewed.get("modules", [])
        if module.get("module_review_status") == "accepted"
    ]
    review_needed = [
        module["module_id"]
        for module in reviewed.get("modules", [])
        if module.get("module_review_status") != "accepted"
    ]
    return {
        "artifact_role": "story_material_planning_handoff",
        "version": 1,
        "film_type": film_type,
        "selected_story_shell": packet.get("story_shells", {}).get("A") or packet.get("story_shell"),
        "accepted_module_groups": accepted,
        "review_needed_module_groups": review_needed,
        "story_to_material_planning_prerequisites": [
            "product route review decision",
            "reviewed catalog map",
            "selected story shell",
        ],
        "retargeted_sections": (packet.get("retarget_summary") or {}).get("changed_sections", []),
        "next_owner": "material-map" if _decision_is_human_approved(decision) else "product-route-review",
    }


def _opener_closer_handoff(film_type: str, packet: Mapping[str, Any]) -> dict[str, Any]:
    if film_type == "daily_kids_memory_film":
        sections = ["opening_memory_hook", "closing_memory_note"]
        design_intent = "warm memory hook and closing family note"
    else:
        sections = ["opening_story", "closing_story"]
        design_intent = "designed graduation opener/closer, not white title cards"
    return {
        "artifact_role": "opener_closer_design_handoff",
        "version": 1,
        "film_type": film_type,
        "sections": sections,
        "no_plain_white_card_ending": True,
        "target_duration_ranges": {
            sections[0]: "6-12 sec",
            sections[1]: "8-15 sec",
        },
        "design_intent": design_intent,
        "effect_factory_return_route": "effect-factory",
        "story_shell_basis": packet.get("story_shells") or packet.get("story_shell"),
    }


def _audio_subtitle_handoff(film_type: str) -> dict[str, Any]:
    graduation = film_type == "graduation_training_film"
    return {
        "artifact_role": "audio_subtitle_review_handoff",
        "version": 1,
        "film_type": film_type,
        "supervisor_source_speech_intelligibility_required": graduation,
        "source_speech_subtitles_required_when_preserved": True,
        "mv_music_vs_speech_ducking_policy": (
            "hot-blooded music mainly in training MV; duck under preserved speech"
            if graduation
            else "warm light music; preserve intelligible child speech/laughter when useful"
        ),
        "teacher_class_intro_readability_required": graduation,
        "audio_subtitle_owner_route": "subtitle-voiceover",
    }


def _readiness_gate(film_type: str, decision: Mapping[str, Any], reviewed: Mapping[str, Any]) -> dict[str, Any]:
    decision_value = _clean(decision.get("decision"))
    blockers: list[str] = []
    warnings: list[str] = []
    if not _decision_is_human_approved(decision):
        if decision_value == "approved":
            blockers.append("product_route_approval_must_be_human")
            next_owner = "waiting_product_review"
        elif decision_value in {"revision_requested", "rejected"}:
            blockers.append(f"product_route_{decision_value}")
            next_owner = "repair_product_route"
        else:
            blockers.append("product_route_review_required")
            next_owner = "waiting_product_review"
    else:
        next_owner = "production_worker"
    status_counts = reviewed["summary"]["status_counts"]
    if status_counts.get("missing", 0):
        warnings.append("catalog_has_missing_modules")
    if status_counts.get("needs_reassign", 0):
        blockers.append("catalog_needs_reassign")
    if status_counts.get("rejected", 0):
        blockers.append("catalog_has_rejected_modules")
    ready = (
        not blockers
        and _decision_is_human_approved(decision)
        and not status_counts.get("missing", 0)
    )
    return {
        "artifact_role": "production_readiness_gate",
        "version": 1,
        "film_type": film_type,
        "ready_for_production": ready,
        "blockers": blockers,
        "warnings": warnings,
        "next_owner": next_owner,
        "safe_next_command": "dispatch production worker from production_worker_handoff_prompt.md" if ready else "review or repair product route before production",
    }


def _worker_prompt(
    film_type: str,
    gate: Mapping[str, Any],
    reviewed: Mapping[str, Any],
    story_handoff: Mapping[str, Any],
    opener_handoff: Mapping[str, Any],
    audio_handoff: Mapping[str, Any],
) -> str:
    counts = reviewed["summary"]["status_counts"]
    no_render = []
    if not gate["ready_for_production"]:
        no_render = [
            "",
            "No-render precondition:",
            "Do not render until product readiness is true and the next owner is production_worker.",
        ]
    return "\n".join([
        "# Production Worker Handoff Prompt",
        "",
        f"Film type: {film_type}",
        f"Ready for production: {str(gate['ready_for_production']).lower()}",
        f"Next owner: {gate['next_owner']}",
        "",
        "Selected story shell:",
        json.dumps(story_handoff.get("selected_story_shell"), ensure_ascii=False, indent=2),
        "",
        "Reviewed module status summary:",
        json.dumps(counts, ensure_ascii=False, indent=2),
        "",
        "Opener/closer design requirements:",
        json.dumps(
            {
                "sections": opener_handoff.get("sections"),
                "design_intent": opener_handoff.get("design_intent"),
                "no_plain_white_card_ending": opener_handoff.get("no_plain_white_card_ending"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        "",
        "Training MV music policy:",
        _clean(audio_handoff.get("mv_music_vs_speech_ducking_policy")),
        "",
        "Source speech/subtitle/readability requirements:",
        json.dumps(
            {
                "supervisor_source_speech_intelligibility_required": audio_handoff.get("supervisor_source_speech_intelligibility_required"),
                "source_speech_subtitles_required_when_preserved": audio_handoff.get("source_speech_subtitles_required_when_preserved"),
                "teacher_class_intro_readability_required": audio_handoff.get("teacher_class_intro_readability_required"),
            },
            ensure_ascii=False,
            indent=2,
        ),
        "",
        "Use reviewed_catalog_map.json, story_material_planning_handoff.json, opener_closer_design_handoff.json, and audio_subtitle_review_handoff.json as the only pre-render basis.",
        *no_render,
        "",
    ])


def _review_packet(film_type: str, decision: Mapping[str, Any], reviewed: Mapping[str, Any], gate: Mapping[str, Any], handoff_paths: Mapping[str, str]) -> dict[str, Any]:
    return {
        "artifact_role": "product_route_review_packet",
        "version": 1,
        "film_type": film_type,
        "review_decision": {
            "decision": decision.get("decision"),
            "reviewer": decision.get("reviewer"),
            "reviewer_type": decision.get("reviewer_type"),
            "is_final_delivery_approval": False,
        },
        "reviewed_catalog_status_counts": reviewed["summary"]["status_counts"],
        "production_readiness_gate": {
            "ready_for_production": gate["ready_for_production"],
            "blockers": gate["blockers"],
            "warnings": gate["warnings"],
            "next_owner": gate["next_owner"],
        },
        "handoff_paths": dict(handoff_paths),
        "rendered": False,
        "human_delivery_approval_written": False,
    }


def _review_packet_markdown(packet: Mapping[str, Any]) -> str:
    counts = packet["reviewed_catalog_status_counts"]
    return "\n".join([
        "# Product Route Review Packet",
        "",
        f"- Film type: {packet['film_type']}",
        f"- Decision: {packet['review_decision']['decision']}",
        f"- Reviewer: {packet['review_decision']['reviewer']}",
        f"- Ready for production: {str(packet['production_readiness_gate']['ready_for_production']).lower()}",
        f"- Next owner: {packet['production_readiness_gate']['next_owner']}",
        f"- Catalog accepted: {counts.get('accepted', 0)}",
        f"- Catalog rejected: {counts.get('rejected', 0)}",
        f"- Catalog needs_reassign: {counts.get('needs_reassign', 0)}",
        f"- Catalog pending_review: {counts.get('pending_review', 0)}",
        f"- Catalog missing: {counts.get('missing', 0)}",
        "- Rendered: false",
        "- Final human delivery approval written: false",
        "",
        "## Handoffs",
        "",
        "\n".join(f"- {name}: {path}" for name, path in packet["handoff_paths"].items()),
        "",
    ])


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_film_canon_production_readiness(
    film_type: str,
    source_root: str | Path | None,
    out_dir: str | Path,
    *,
    decision: Mapping[str, Any] | None = None,
    decision_path: str | Path | None = None,
) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    route_dir = out_root / "film_canon_route_dry_run"
    route_summary = write_film_canon_route_dry_run(film_type, source_root, route_dir)
    if decision_path:
        review_decision = _load_product_route_review_decision(Path(decision_path))
    elif decision is not None:
        review_decision = dict(decision)
    elif (out_root / "product_route_review_decision.json").is_file():
        review_decision = _load_product_route_review_decision(out_root / "product_route_review_decision.json")
    else:
        review_decision = build_product_route_review_decision()
    catalog = _load_route_catalog(route_dir)
    route_packet = _load_route_packet(route_dir)
    reviewed = _reviewed_catalog_map(catalog, review_decision)
    story_handoff = _story_material_handoff(film_type, route_packet, reviewed, review_decision)
    opener_handoff = _opener_closer_handoff(film_type, route_packet)
    audio_handoff = _audio_subtitle_handoff(film_type)
    gate = _readiness_gate(film_type, review_decision, reviewed)
    handoff_paths = {
        "story_material_planning_handoff": str(out_root / "story_material_planning_handoff.json"),
        "opener_closer_design_handoff": str(out_root / "opener_closer_design_handoff.json"),
        "audio_subtitle_review_handoff": str(out_root / "audio_subtitle_review_handoff.json"),
        "production_readiness_gate": str(out_root / "production_readiness_gate.json"),
        "production_worker_handoff_prompt": str(out_root / "production_worker_handoff_prompt.md"),
    }
    packet = _review_packet(film_type, review_decision, reviewed, gate, handoff_paths)

    outputs: dict[str, Any] = {
        "product_route_review_decision.json": review_decision,
        "reviewed_catalog_map.json": reviewed,
        "story_material_planning_handoff.json": story_handoff,
        "opener_closer_design_handoff.json": opener_handoff,
        "audio_subtitle_review_handoff.json": audio_handoff,
        "production_readiness_gate.json": gate,
        "product_route_review_packet.json": packet,
    }
    for name, payload in outputs.items():
        _write_json(out_root / name, payload)
    (out_root / "production_worker_handoff_prompt.md").write_text(
        _worker_prompt(film_type, gate, reviewed, story_handoff, opener_handoff, audio_handoff),
        encoding="utf-8",
    )
    (out_root / "product_route_review_packet.md").write_text(_review_packet_markdown(packet), encoding="utf-8")
    return {
        "ok": True,
        "film_type": film_type,
        "out_dir": str(out_root),
        "route_dry_run": route_summary,
        "artifacts": list(_READINESS_ARTIFACTS),
        "review_decision": {
            "decision": review_decision.get("decision"),
            "reviewer": review_decision.get("reviewer"),
            "reviewer_type": review_decision.get("reviewer_type"),
        },
        "reviewed_catalog_status_counts": reviewed["summary"]["status_counts"],
        "handoff_paths": handoff_paths,
        "production_readiness_gate": gate,
        "rendered": False,
        "human_delivery_approval_written": False,
    }
