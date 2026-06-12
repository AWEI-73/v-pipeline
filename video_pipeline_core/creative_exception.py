"""Shared validation and acknowledgment for segment-level creative exceptions."""
from __future__ import annotations


REQUIRED_FIELDS = ("rule_bent", "reason", "risk")


def validation_errors(value) -> list[str]:
    if not isinstance(value, dict):
        return ["must be an object"]
    errors = [
        f"{field} must be a non-empty string"
        for field in REQUIRED_FIELDS
        if not isinstance(value.get(field), str) or not value[field].strip()
    ]
    if value.get("requires_review") is not True:
        errors.append("requires_review must be true")
    return errors


def matching_exception(rule: str, *items: dict | None) -> dict | None:
    for item in items:
        if not isinstance(item, dict):
            continue
        value = item.get("creative_exception")
        if not validation_errors(value) and value["rule_bent"] == rule:
            return value
    return None


def acknowledge(finding: dict, exception: dict, *, level: str = "warn") -> dict:
    finding = dict(finding)
    finding["level"] = level
    finding["acknowledged_exception"] = True
    finding["creative_exception"] = exception
    return finding


def legacy_hold_exception(item: dict, allowed_reasons=None) -> dict | None:
    allowed = set(allowed_reasons or ())
    for field in ("allow_long_hold_when", "hold_reason", "cut_reason", "shot_reason"):
        value = item.get(field)
        values = value if isinstance(value, (list, tuple)) else [value]
        reason = next(
            (str(entry) for entry in values if entry and (not allowed or str(entry) in allowed)),
            None,
        )
        if reason:
            return {
                "rule_bent": "hold_discipline",
                "reason": reason,
                "risk": "Legacy hold exemption requires review.",
                "requires_review": True,
                "legacy_field": field,
            }
    return None
