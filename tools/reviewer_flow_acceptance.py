#!/usr/bin/env python
"""Acceptance harness for reviewer policy wiring.

This does not call LLM reviewers. It proves the deterministic reviewer registry
can be expanded, minimal review artifacts can be validated, and route-specific
reviewer sets cover upstream story and effects/brownfield cases.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core import reviewer_registry


ARTIFACT_ROLE = "reviewer_flow_acceptance"
VERSION = 1

SCENARIO_REQUIRED_ROLES = {
    "route_smoke": ["story_director", "material_producer", "editorial_timeline", "technical_verify"],
    "upstream_story": ["literary_editor", "story_director", "generated_material_art_director"],
    "effects_brownfield": ["editorial_timeline", "audio_subtitle_reviewer", "effect_reviewer", "technical_verify"],
}


def _role_specs() -> dict[str, dict[str, Any]]:
    return {r["reviewer_role"]: r for r in reviewer_registry.build_reviewer_registry()["reviewers"]}


def _review_for(spec: dict[str, Any]) -> dict[str, Any]:
    gate = spec["gate_strength"]
    decision = "advisory" if gate == "advisory" else "pass"
    return {
        "artifact_role": "artifact_review",
        "version": 1,
        "reviewer_role": spec["reviewer_role"],
        "review_type": spec["review_type"],
        "input_artifacts": list(spec["input_artifacts"]),
        "expected_output_artifact": spec["output_artifact"],
        "decision": decision,
        "gate_strength": gate,
        "scores": {p["criterion"]: 3 for p in spec["eval_principles"]},
        "eval_principles_checked": [p["criterion"] for p in spec["eval_principles"]],
        "findings": [],
        "next_action": spec["typical_next_actions"][-1],
    }


def _scenario_roles(scenario: str, enabled: Iterable[str]) -> list[str]:
    enabled_set = set(enabled)
    if scenario == "all":
        required = []
        for roles in SCENARIO_REQUIRED_ROLES.values():
            required.extend(roles)
    else:
        if scenario not in SCENARIO_REQUIRED_ROLES:
            raise ValueError(f"unknown reviewer flow scenario: {scenario!r}")
        required = SCENARIO_REQUIRED_ROLES[scenario]
    return sorted(set(required), key=required.index)


def run_acceptance(
    *,
    level: str = "deep",
    scenario: str = "all",
    artifact_dir: str | Path | None = None,
) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    packet: dict[str, Any] | None = None
    reviews: list[dict[str, Any]] = []
    written: list[str] = []

    try:
        packet = reviewer_registry.build_policy_packet(level)
    except ValueError as exc:
        return _result(level, scenario, None, [], [], [str(exc)], warnings)

    enabled = packet["enabled_reviewers"]
    roles = _role_specs()
    required = _scenario_roles(scenario, enabled)
    missing = [r for r in required if r not in enabled]
    if missing:
        errors.append(f"policy {level!r} missing scenario reviewer(s): {', '.join(missing)}")

    out_dir = Path(artifact_dir) if artifact_dir else None
    if out_dir:
        out_dir.mkdir(parents=True, exist_ok=True)
        (out_dir / "reviewer_policy_packet.json").write_text(
            json.dumps(packet, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        written.append(str(out_dir / "reviewer_policy_packet.json"))
        reviews_dir = out_dir / "artifact_reviews"
        reviews_dir.mkdir(parents=True, exist_ok=True)
    else:
        reviews_dir = None

    for role in required:
        spec = roles.get(role)
        if not spec:
            errors.append(f"unknown reviewer role in scenario: {role}")
            continue
        review = _review_for(spec)
        verdict = reviewer_registry.validate_review_artifact(review)
        if not verdict["ok"]:
            errors.extend([f"{role}: {e}" for e in verdict["errors"]])
        reviews.append({
            "reviewer_role": role,
            "gate_strength": review["gate_strength"],
            "decision": review["decision"],
            "output_artifact": spec["output_artifact"],
            "eval_principles_checked": review["eval_principles_checked"],
        })
        if reviews_dir:
            path = reviews_dir / f"{role}.artifact_review.json"
            path.write_text(json.dumps(review, ensure_ascii=False, indent=2), encoding="utf-8")
            written.append(str(path))

    negative_checks = _negative_checks()
    for name, passed in negative_checks.items():
        if not passed:
            errors.append(f"negative check failed: {name}")

    return _result(level, scenario, packet, required, reviews, errors, warnings,
                   written=written, negative_checks=negative_checks)


def _negative_checks() -> dict[str, bool]:
    bad_technical_gate = {
        "artifact_role": "artifact_review",
        "version": 1,
        "reviewer_role": "technical_verify",
        "decision": "pass",
        "gate_strength": "revise",
        "findings": [],
    }
    bad_unknown_role = {
        "artifact_role": "artifact_review",
        "version": 1,
        "reviewer_role": "unknown_reviewer",
        "decision": "pass",
        "gate_strength": "advisory",
        "findings": [],
    }
    return {
        "technical_verify_rejects_revise_gate": not reviewer_registry.validate_review_artifact(bad_technical_gate)["ok"],
        "unknown_reviewer_rejected": not reviewer_registry.validate_review_artifact(bad_unknown_role)["ok"],
    }


def _result(
    level: str,
    scenario: str,
    packet: dict[str, Any] | None,
    required: list[str],
    reviews: list[dict[str, Any]],
    errors: list[str],
    warnings: list[str],
    *,
    written: list[str] | None = None,
    negative_checks: dict[str, bool] | None = None,
) -> dict[str, Any]:
    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": VERSION,
        "ok": not errors,
        "review_policy": {"level": level},
        "scenario": scenario,
        "enabled_reviewers": list(packet.get("enabled_reviewers", [])) if packet else [],
        "scenario_reviewers": required,
        "reviews": reviews,
        "negative_checks": negative_checks or {},
        "written": written or [],
        "errors": errors,
        "warnings": warnings,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--level", default="deep", choices=["light", "normal", "deep"])
    parser.add_argument("--scenario", default="all",
                        choices=["route_smoke", "upstream_story", "effects_brownfield", "all"])
    parser.add_argument("--artifact-dir", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)

    result = run_acceptance(level=args.level, scenario=args.scenario, artifact_dir=args.artifact_dir)
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    print(text)
    return 0 if result["ok"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
