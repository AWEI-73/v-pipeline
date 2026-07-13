"""Live, read-only Capability Card catalog derived from Skill contracts."""

from __future__ import annotations

from typing import Any, Iterable

from . import skill_tool_contract


CARD_FIELDS = (
    "capability_id", "owner", "stage_owner", "kind", "loops", "maturity",
    "certified_scope", "tool", "command", "execution_class", "capability_role",
    "when", "inputs", "outputs", "stop_if", "source_skill",
)


def _card(contract: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    return {
        "capability_id": entry.get("capability_id"),
        "owner": contract.get("skill"),
        "stage_owner": contract.get("stage_owner"),
        "kind": "canonical" if entry.get("_section") == "canonical_tools" else entry.get("_section", "supporting").removesuffix("_tools"),
        "loops": list(entry.get("loops") or []),
        "maturity": entry.get("maturity"),
        "certified_scope": entry.get("certified_scope"),
        "tool": skill_tool_contract.normalize_tool_ref(entry.get("tool")),
        "command": skill_tool_contract.projected_command_ref(entry),
        "execution_class": entry.get("execution_class"),
        "capability_role": entry.get("capability_role"),
        "when": entry.get("when"),
        "inputs": list(entry.get("inputs") or []),
        "outputs": list(entry.get("outputs") or []),
        "stop_if": list(entry.get("stop_if") or []),
        "source_skill": contract.get("_source"),
    }


def build_catalog(contracts: Iterable[dict[str, Any]], *, validation_errors: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    errors = list(validation_errors)
    if errors:
        return {"ok": False, "cards": [], "errors": errors, "artifact_role": "capability_catalog", "version": 1}
    cards = []
    for contract in contracts:
        for entry in skill_tool_contract.iter_tool_entries(contract):
            if entry.get("_section") != "canonical_tools":
                continue
            cards.append(_card(contract, entry))
    cards.sort(key=lambda item: (str(item.get("capability_id") or ""), str(item.get("source_skill") or "")))
    ids = [card.get("capability_id") for card in cards]
    if any(not value for value in ids) or len(ids) != len(set(ids)):
        return {
            "ok": False,
            "cards": [],
            "errors": [{"code": "invalid_catalog", "message": "capability catalog contains missing or duplicate IDs"}],
            "artifact_role": "capability_catalog",
            "version": 1,
        }
    return {"ok": True, "cards": cards, "errors": [], "artifact_role": "capability_catalog", "version": 1}


def _search_text(card: dict[str, Any]) -> str:
    values = []
    for field in (
        "capability_id",
        "owner",
        "stage_owner",
        "tool",
        "command",
        "execution_class",
        "capability_role",
        "when",
        "certified_scope",
        "source_skill",
    ):
        values.append(str(card.get(field) or ""))
    for field in ("inputs", "outputs", "stop_if", "loops"):
        values.extend(str(value) for value in card.get(field) or [])
    return " ".join(values).casefold()


def query_catalog(catalog: dict[str, Any], *, selector: str, value: str) -> dict[str, Any]:
    envelope = {
        "artifact_role": "capability_query_result",
        "version": 1,
        "ok": False,
        "selector": {"type": selector, "value": value},
        "count": 0,
        "results": [],
        "error": None,
    }
    if not catalog.get("ok"):
        envelope["error"] = {"code": "invalid_catalog", "message": "capability query: live catalog invalid"}
        return envelope
    cards = list(catalog.get("cards") or [])
    selector = str(selector)
    value = str(value or "")
    if selector == "id":
        matches = [card for card in cards if card.get("capability_id") == value]
    elif selector == "owner":
        matches = [card for card in cards if str(card.get("owner") or "").casefold() == value.casefold()]
    elif selector == "loop":
        matches = [card for card in cards if value.upper() in {str(loop).upper() for loop in card.get("loops") or []}]
    elif selector == "query":
        terms = [term.casefold() for term in value.split() if term.strip()]
        matches = [card for card in cards if all(term in _search_text(card) for term in terms)]
    else:
        envelope["error"] = {"code": "invalid_selector", "message": "capability query: invalid selector"}
        return envelope
    matches.sort(key=lambda item: (str(item.get("capability_id") or ""), str(item.get("source_skill") or "")))
    envelope["count"] = len(matches)
    envelope["results"] = matches
    if matches:
        envelope["ok"] = True
    else:
        envelope["error"] = {"code": "no_match", "message": "capability query: no matches"}
    return envelope


def load_live_catalog(skills_dir: str, *, repository_errors: Iterable[dict[str, Any]] = ()) -> dict[str, Any]:
    contracts, parse_errors = skill_tool_contract.load_contracts(skills_dir)
    errors = [*parse_errors, *skill_tool_contract.validate_contract_schema(contracts), *list(repository_errors)]
    return build_catalog(contracts, validation_errors=errors)
