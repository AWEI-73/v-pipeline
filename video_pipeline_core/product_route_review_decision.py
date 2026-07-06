"""Product-route review decision writer helpers."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping


_DECISIONS = {"approved", "revision_requested", "rejected"}
_MODULE_STATUSES = {"accepted", "optional", "needs_reassign", "rejected"}


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ValueError(f"missing required artifact: {path.name}") from exc
    except json.JSONDecodeError as exc:
        raise ValueError(f"{path.name} is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.name} must contain a JSON object")
    return data


def _known_module_ids(run: Path) -> set[str]:
    modules: set[str] = set()
    reviewed_path = run / "reviewed_catalog_map.json"
    if reviewed_path.is_file():
        reviewed = _load_json(reviewed_path)
        for module in reviewed.get("modules") or []:
            if isinstance(module, Mapping):
                module_id = _clean(module.get("module_id"))
                if module_id:
                    modules.add(module_id)
    for catalog_name in ("training_catalog_map.real_source.json", "catalog_map.json"):
        catalog_path = run / "film_canon_route_dry_run" / catalog_name
        if catalog_path.is_file():
            catalog = _load_json(catalog_path)
            for module in catalog.get("modules") or []:
                if isinstance(module, Mapping):
                    module_id = _clean(module.get("module_id"))
                    if module_id:
                        modules.add(module_id)
    if not modules:
        raise ValueError("cannot find product route modules in run artifacts")
    return modules


def parse_module_status(raw: str) -> dict[str, str]:
    text = _clean(raw)
    if "=" not in text:
        raise ValueError("--module-status must use MODULE=STATUS:note")
    module_id, rest = text.split("=", 1)
    status, _, note = rest.partition(":")
    module_id = _clean(module_id)
    status = _clean(status)
    note = _clean(note)
    if not module_id:
        raise ValueError("--module-status is missing module id")
    if status not in _MODULE_STATUSES:
        raise ValueError(f"unsupported module status for {module_id}: {status}")
    if status in {"needs_reassign", "rejected", "optional"} and not note:
        raise ValueError(f"{status} module override requires a note: {module_id}")
    return {
        "module_id": module_id,
        "status": status,
        "review_note": note,
    }


def build_review_decision(
    *,
    run: str | Path,
    decision: str,
    reviewer: str,
    approve_all_reviewed: bool = False,
    module_statuses: Iterable[str] | None = None,
    notes: Iterable[str] | None = None,
    created_at: str = "",
) -> dict[str, Any]:
    run_path = Path(run)
    decision_value = _clean(decision)
    reviewer_value = _clean(reviewer)
    if decision_value not in _DECISIONS:
        raise ValueError(f"unsupported decision: {decision_value}")
    if reviewer_value.casefold() != "human":
        raise ValueError("product-route review decision requires --reviewer human")

    known_modules = _known_module_ids(run_path)
    module_overrides = [parse_module_status(item) for item in (module_statuses or [])]
    unknown = sorted({item["module_id"] for item in module_overrides} - known_modules)
    if unknown:
        raise ValueError("unknown module id in --module-status: " + ", ".join(unknown))

    note_list = [_clean(item) for item in (notes or []) if _clean(item)]
    if decision_value == "approved" and not approve_all_reviewed:
        raise ValueError("approved product-route decision requires --approve-all-reviewed")
    if decision_value in {"revision_requested", "rejected"}:
        has_module_reason = any(
            item["status"] in {"needs_reassign", "rejected"} and item.get("review_note")
            for item in module_overrides
        )
        if not note_list and not has_module_reason:
            raise ValueError(f"{decision_value} requires --note or a module reason")

    return {
        "artifact_role": "product_route_review_decision",
        "version": 1,
        "decision": decision_value,
        "reviewer": reviewer_value,
        "reviewer_type": "human",
        "approve_all_reviewed": bool(approve_all_reviewed),
        "module_overrides": module_overrides,
        "notes": note_list,
        "is_final_delivery_approval": False,
        "clears_story_human_review": False,
        "reviewed_artifacts": {
            "product_route_review_packet": "product_route_review_packet.json",
            "reviewed_catalog_map": "reviewed_catalog_map.json",
            "story_material_planning_handoff": "story_material_planning_handoff.json",
            "opener_closer_design_handoff": "opener_closer_design_handoff.json",
            "audio_subtitle_review_handoff": "audio_subtitle_review_handoff.json",
        },
        "created_at": created_at or _now_iso(),
    }


def write_review_decision(
    *,
    run: str | Path,
    decision: str,
    reviewer: str,
    approve_all_reviewed: bool = False,
    module_statuses: Iterable[str] | None = None,
    notes: Iterable[str] | None = None,
    out_name: str = "product_route_review_decision.json",
    created_at: str = "",
) -> tuple[Path, dict[str, Any]]:
    out_name_path = Path(out_name)
    if out_name_path.is_absolute() or out_name_path.name != out_name:
        raise ValueError("--out-name must be a run-local file name, not a path")
    if out_name != "product_route_review_decision.json":
        raise ValueError("--out-name must be product_route_review_decision.json")
    payload = build_review_decision(
        run=run,
        decision=decision,
        reviewer=reviewer,
        approve_all_reviewed=approve_all_reviewed,
        module_statuses=module_statuses,
        notes=notes,
        created_at=created_at,
    )
    out_path = Path(run) / out_name
    out_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return out_path, payload
