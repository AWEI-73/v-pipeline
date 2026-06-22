from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from . import reviewer_registry


def _read_json(path: str | Path | None) -> dict[str, Any]:
    if not path:
        return {}
    p = Path(path)
    if not p.is_file():
        return {}
    return json.loads(p.read_text(encoding="utf-8"))


def _duration_sec(brief: Mapping[str, Any]) -> float | None:
    raw = brief.get("duration_sec")
    if isinstance(raw, (int, float)) and raw > 0:
        return float(raw)
    text = str(brief.get("target_length") or "").lower()
    digits = "".join(ch if ch.isdigit() or ch == "." else " " for ch in text).split()
    if not digits:
        return None
    value = float(digits[0])
    if "minute" in text or "min" in text:
        return value * 60.0
    return value


def _accepted_visual_count(project_map: Mapping[str, Any]) -> int:
    count = 0
    for asset in project_map.get("assets") or []:
        if str(asset.get("asset_type") or "").lower() not in {"generated_image", "image", "photo", "video"}:
            continue
        has_acceptance = False
        for scene in asset.get("scenes") or []:
            for edge in scene.get("satisfies") or []:
                if edge.get("status") == "accepted":
                    has_acceptance = True
        if has_acceptance:
            count += 1
    return count


def _beat_count(screenplay: Mapping[str, Any]) -> int:
    beats = screenplay.get("beats") or []
    return len(beats) if isinstance(beats, list) else 0


def _need_count(needs: Mapping[str, Any]) -> int:
    items = needs.get("needs") or []
    return len(items) if isinstance(items, list) else 0


def _delta_summary(delta: Mapping[str, Any]) -> dict[str, int]:
    summary = delta.get("summary") if isinstance(delta.get("summary"), Mapping) else {}
    out: dict[str, int] = {}
    for key in ("covered", "thin", "missing", "excess"):
        raw = summary.get(key)
        if raw is None and isinstance(delta.get(key), list):
            raw = len(delta.get(key) or [])
        try:
            out[key] = int(raw or 0)
        except (TypeError, ValueError):
            out[key] = 0
    return out


def _base_review(role: str) -> dict[str, Any]:
    registry = reviewer_registry.build_reviewer_registry()
    specs = {r["reviewer_role"]: r for r in registry["reviewers"]}
    if role not in specs:
        raise ValueError(f"unknown reviewer role: {role!r}")
    spec = specs[role]
    return {
        "artifact_role": "artifact_review",
        "version": 1,
        "reviewer_role": role,
        "review_type": spec["review_type"],
        "input_artifacts": list(spec["input_artifacts"]),
        "expected_output_artifact": spec["output_artifact"],
        "decision": "pass",
        "gate_strength": spec["gate_strength"],
        "scores": {},
        "metrics": {},
        "findings": [],
        "next_action": spec["typical_next_actions"][-1],
        "eval_principles_checked": [p["criterion"] for p in spec["eval_principles"]],
    }


def _story_director_review(
    review: dict[str, Any],
    brief: Mapping[str, Any],
    screenplay: Mapping[str, Any],
    material_needs: Mapping[str, Any],
    project_map: Mapping[str, Any],
) -> dict[str, Any]:
    duration = _duration_sec(brief)
    visuals = _accepted_visual_count(project_map)
    beats = _beat_count(screenplay)
    needs = _need_count(material_needs)
    avg_hold = (duration / visuals) if duration and visuals else None
    visual_per_beat = (visuals / beats) if beats else None

    review["metrics"] = {
        "duration_sec": duration,
        "beat_count": beats,
        "need_count": needs,
        "accepted_visual_count": visuals,
        "avg_hold_per_visual_sec": round(avg_hold, 3) if avg_hold is not None else None,
        "accepted_visuals_per_beat": round(visual_per_beat, 3) if visual_per_beat is not None else None,
    }
    review["scores"] = {
        "narrative_device": 4 if beats else 1,
        "turn_per_beat": 4 if beats and needs >= beats else 2,
        "shot_intent_density": 2 if avg_hold and avg_hold > 10 else 4,
    }

    if avg_hold and avg_hold > 10:
        review["decision"] = "revise"
        review["next_action"] = "revise_shot_plan"
        review["findings"].append(
            {
                "severity": "major",
                "code": "visual_rhythm_too_sparse",
                "message": (
                    "The story route is structurally covered, but the accepted visual "
                    "moments are too sparse for the declared duration."
                ),
                "evidence": {
                    "duration_sec": duration,
                    "accepted_visual_count": visuals,
                    "avg_hold_per_visual_sec": round(avg_hold, 3),
                },
                "suggestion": (
                    "Keep the story beats, but split long beats into setup, action, "
                    "reaction, transition, or consequence moments; alternatively shorten "
                    "the target duration if the intended format is very slow narration."
                ),
                "failure_route": "revise_shot_plan",
            }
        )
    return review


def _material_producer_review(
    review: dict[str, Any],
    material_needs: Mapping[str, Any],
    project_map: Mapping[str, Any],
    material_delta: Mapping[str, Any],
    ) -> dict[str, Any]:
    summary = _delta_summary(material_delta)
    ready = bool(material_delta.get("ready_for_build"))
    review_ready = ready and summary["missing"] == 0 and summary["thin"] == 0
    review["metrics"] = {
        "need_count": _need_count(material_needs),
        "asset_count": len(project_map.get("assets") or []),
        "covered": summary["covered"],
        "thin": summary["thin"],
        "missing": summary["missing"],
        "excess": summary["excess"],
        "ready_for_build": ready,
        "review_ready": review_ready,
    }
    review["scores"] = {
        "coverage_truth": 4 if review_ready else 1,
        "reference_integrity": 4 if project_map.get("assets") is not None else 1,
        "candidate_status": 4 if review_ready else 2,
    }
    if not review_ready:
        review["decision"] = "block"
        if summary["missing"] > 0:
            next_action = "await_material"
        elif summary["thin"] > 0:
            next_action = "generate_material"
        else:
            next_action = "revise_contract"
        review["next_action"] = next_action
        review["findings"].append(
            {
                "severity": "critical",
                "code": "material_delta_not_ready",
                "message": "Material delta is not ready for BUILD; material coverage must be resolved before rendering.",
                "evidence": {
                    "ready_for_build": ready,
                    "summary": summary,
                },
                "suggestion": "Resolve missing/thin material through collection, generation, waiver, or contract revision, then rerun material_delta.",
                "failure_route": next_action,
            }
        )
    return review


def review_artifacts(role: str, artifact_paths: Mapping[str, str | Path]) -> dict[str, Any]:
    role = str(role or "").strip()
    review = _base_review(role)
    brief = _read_json(artifact_paths.get("project_brief"))
    screenplay = _read_json(artifact_paths.get("screenplay_beats"))
    needs = _read_json(artifact_paths.get("material_needs"))
    project_map = _read_json(artifact_paths.get("project_material_map") or artifact_paths.get("project_map"))
    material_delta = _read_json(artifact_paths.get("material_delta"))

    if role == "story_director":
        return _story_director_review(review, brief, screenplay, needs, project_map)
    if role == "material_producer":
        return _material_producer_review(review, needs, project_map, material_delta)
    raise ValueError(f"reviewer role runner is not implemented for {role!r}")
