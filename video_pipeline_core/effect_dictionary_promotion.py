"""Promote reviewed generic effect graphs into a reusable Effect Factory dictionary."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .effect_build_spec import validate_effect_build_spec


def _load_dictionary(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {
            "artifact_role": "effect_factory_dictionary",
            "version": 1,
            "entries": [],
        }
    with path.open(encoding="utf-8-sig") as f:
        payload = json.load(f)
    if not isinstance(payload, dict):
        raise ValueError("effect dictionary must contain a JSON object")
    payload.setdefault("artifact_role", "effect_factory_dictionary")
    payload.setdefault("version", 1)
    payload.setdefault("entries", [])
    if not isinstance(payload["entries"], list):
        raise ValueError("effect dictionary entries must be a list")
    return payload


def _clean_string_list(value: Any, field: str) -> list[str]:
    if not isinstance(value, list) or not value:
        raise ValueError(f"{field} must be a non-empty string list")
    cleaned = []
    for idx, item in enumerate(value):
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"{field}[{idx}] must be a non-empty string")
        cleaned.append(item.strip())
    return cleaned


def _review_evidence(review: Any) -> dict[str, Any]:
    if not isinstance(review, Mapping):
        raise ValueError("promotion requires accepted review evidence")
    decision = str(review.get("decision") or "").lower()
    evidence_refs = review.get("evidence_refs") or review.get("evidenceRefs") or []
    if decision not in {"accept", "accepted", "pass", "passed"} or not isinstance(evidence_refs, list) or not evidence_refs:
        raise ValueError("promotion requires accepted review evidence")
    return {
        "decision": decision,
        "reviewer": review.get("reviewer", ""),
        "reason": review.get("reason", ""),
        "evidence_refs": [str(ref) for ref in evidence_refs],
    }


def promote_effect_dictionary_entry(
    request: Mapping[str, Any],
    dictionary_path: str | Path,
    out_path: str | Path,
) -> dict[str, Any]:
    if not isinstance(request, Mapping):
        raise ValueError("promotion request must be an object")

    entry_id = request.get("entry_id") or request.get("id")
    if not isinstance(entry_id, str) or not entry_id.strip():
        raise ValueError("entry_id must be a non-empty string")
    display_name = request.get("display_name_zh") or request.get("display_name") or entry_id
    if not isinstance(display_name, str) or not display_name.strip():
        raise ValueError("display_name_zh must be a non-empty string")
    intent_tags = _clean_string_list(request.get("intent_tags"), "intent_tags")
    story_functions = _clean_string_list(request.get("story_functions"), "story_functions")
    spec = validate_effect_build_spec(request.get("effect_build_spec"))
    if spec["component"] != "GenericRemotionEffect":
        raise ValueError("only reviewed GenericRemotionEffect graphs can be promoted here")
    review = _review_evidence(request.get("review"))

    dictionary_file = Path(dictionary_path)
    payload = _load_dictionary(dictionary_file)
    entry = {
        "id": entry_id.strip(),
        "display_name_zh": display_name.strip(),
        "status": "reviewed",
        "intent_tags": intent_tags,
        "story_functions": story_functions,
        "layer_graph": spec["layers"],
        "default_controls": {
            "duration_sec": spec["duration_sec"],
            "canvas": spec["canvas"],
            "timing": spec["timing"],
        },
        "tunable_controls": sorted({
            key
            for layer in spec["layers"]
            for key in (layer.get("params") or {}).keys()
        }),
        "evidence": review,
        "avoid_for": list(request.get("avoid_for") or []),
    }

    entries = [item for item in payload["entries"] if not (isinstance(item, Mapping) and item.get("id") == entry["id"])]
    entries.append(entry)
    payload["entries"] = entries

    out_file = Path(out_path)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return {
        "ok": True,
        "effect_factory_dictionary": str(out_file),
        "entry_id": entry["id"],
        "entry_count": len(entries),
    }
