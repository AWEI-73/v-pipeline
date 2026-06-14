"""Tier-1 delivery gate over existing GAP and VERIFY artifacts."""
from __future__ import annotations


HARD_AUDITS = (
    "verify_result",
    "timeline_invariants",
    "broll_audit",
    "caption_audit",
    "new_visual_information_audit",
    "black_frame_audit",
)


def evaluate_delivery_gate(artifacts):
    blocking = []
    for role in HARD_AUDITS:
        audit = (artifacts or {}).get(role)
        if isinstance(audit, dict) and audit.get("pass") is False:
            default_action = (
                "verify_failed" if role == "verify_result"
                else "fix_timeline_or_assembly"
            )
            blocking.append({
                "rule": "failed_audit",
                "tier": 1,
                "artifact": role,
                "message": f"{role} failed",
                "next_action": audit.get("next_action") or default_action,
            })

    coverage = (artifacts or {}).get("material_coverage") or {}
    for gap in coverage.get("gaps") or []:
        blocking.append({
            "rule": "unresolved_gap",
            "tier": 1,
            "segment": gap.get("segment"),
            "message": gap.get("reason") or "material gap unresolved",
            "next_action": "await_material",
        })

    return {
        "artifact_role": "delivery_gate",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "next_action": blocking[0]["next_action"] if blocking else None,
    }
