"""Convert QA/review findings into structured factory improvement backlog."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Iterable, Mapping


OWNER_BY_RULE_PREFIX = {
    "title_effect": "effect-factory",
    "effect": "effect-factory",
    "voiceover": "subtitle-voiceover",
    "subtitle": "subtitle-voiceover",
    "music": "soundtrack-arranger",
    "audio": "soundtrack-arranger",
    "visual": "film-canon-product-route",
    "no_skip": "verify-delivery",
    "rendered": "verify-delivery",
}


def _owner_for(rule: str, source: str) -> str:
    token = f"{rule} {source}".lower()
    for prefix, owner in OWNER_BY_RULE_PREFIX.items():
        if prefix in token:
            return owner
    return "main-pipeline"


def _acceptance_hook(source: str) -> str:
    if source == "rendered_product_qa":
        return "tools/rendered_product_qa.py"
    if source == "no_skip_execution_trace":
        return "tools/no_skip_execution_trace.py"
    return "route owner acceptance command"


def build_factory_improvement_backlog(findings: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    items: list[dict[str, Any]] = []
    for index, finding in enumerate(findings, start=1):
        source = str(finding.get("source") or "unknown")
        rule = str(finding.get("rule") or finding.get("id") or "unclassified")
        owner = _owner_for(rule, source)
        items.append(
            {
                "item_id": f"improvement_{index:03d}",
                "source": source,
                "rule": rule,
                "message": str(finding.get("message") or ""),
                "artifact": str(finding.get("artifact") or ""),
                "owner_branch": owner,
                "product_level_impact": "rendered candidate cannot clear QA/no-skip",
                "proposed_acceptance_hook": _acceptance_hook(source),
                "golden_path_worthy": source in {"rendered_product_qa", "no_skip_execution_trace"},
                "auto_edits_media": False,
                "updates_golden_path": False,
            }
        )
    return {
        "artifact_role": "factory_improvement_backlog",
        "version": 1,
        "items": items,
    }


def write_factory_improvement_backlog(findings: Iterable[Mapping[str, Any]], out: str | Path) -> dict[str, Any]:
    backlog = build_factory_improvement_backlog(findings)
    path = Path(out)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(backlog, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return backlog
