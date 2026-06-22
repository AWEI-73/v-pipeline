from __future__ import annotations

from typing import Any


ENTRY_PATHS = {"material-first", "structure-first", "needs-context"}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _lower_text(*values: Any) -> str:
    return " ".join(_clean(v).lower() for v in values if _clean(v))


def _detect_video_type(brief: dict[str, Any]) -> str | None:
    explicit = _clean(brief.get("video_type") or brief.get("type"))
    if explicit:
        return explicit
    text = _lower_text(brief.get("request"), brief.get("goal"), brief.get("tone"))
    if any(k in text for k in ("teaching", "tutorial", "lesson", "screen recording")):
        return "teaching"
    if any(k in text for k in ("storybook", "children", "comic", "picture book")):
        return "storybook"
    if any(k in text for k in ("graduation", "event recap")):
        return "graduation-event"
    if any(k in text for k in ("brand", "product")):
        return "brand-product"
    if any(k in text for k in ("memory", "personal")):
        return "personal-memory"
    return None


def _detect_material_availability(brief: dict[str, Any]) -> str | None:
    explicit = _clean(brief.get("material_availability") or brief.get("material_mode"))
    if explicit:
        text = explicit.lower()
        if text in {"existing-material-first", "existing", "available", "has_material"}:
            return "existing"
        if text in {"story-first", "none", "no_material", "zero"}:
            return "none"
        if text in {"hybrid", "partial", "some"}:
            return "partial"
    text = _lower_text(
        brief.get("request"),
        brief.get("material_summary"),
        brief.get("material_quality"),
        brief.get("materials"),
    )
    if any(k in text for k in ("no material", "without material", "none")):
        return "none"
    if any(k in text for k in ("some material", "partial", "some gaps", "gap")):
        return "partial"
    if any(k in text for k in ("screen recording", "footage", "photos", "materials")):
        return "existing"
    return None


def _detect_text_availability(brief: dict[str, Any]) -> str:
    explicit = _clean(brief.get("text_availability") or brief.get("text_state"))
    if explicit:
        text = explicit.lower()
        if text in {"article", "outline", "brief", "script", "story", "idea_text"}:
            return text
        if text in {"none", "no_text", "unknown"}:
            return text
    text = _lower_text(
        brief.get("request"),
        brief.get("article"),
        brief.get("outline"),
        brief.get("script"),
        brief.get("story"),
    )
    if any(k in text for k in ("article", "outline", "script", "story", "essay", "brief")):
        return "brief"
    return "none"


def _input_state(material_availability: str | None, text_availability: str) -> str:
    if material_availability in {"existing", "partial"}:
        return "material_available"
    if text_availability not in {"none", "unknown", ""}:
        return "text_available"
    if material_availability == "none":
        return "idea_only"
    return "unknown"


def _entry_path_for(input_state: str, questions: list[str]) -> str:
    if questions and input_state in {"unknown", "idea_only"}:
        return "needs-context"
    if input_state == "material_available":
        return "material-first"
    if input_state in {"text_available", "idea_only"}:
        return "structure-first"
    return "needs-context"


def _legacy_route_for(material_availability: str | None, entry_path: str) -> str | None:
    if entry_path == "material-first" and material_availability == "existing":
        return "existing-material-first"
    if entry_path == "material-first" and material_availability == "partial":
        return "hybrid"
    if entry_path == "structure-first":
        return "story-first"
    return None


def _handoff_packet(entry_path: str) -> dict[str, Any]:
    if entry_path == "material-first":
        return {
            "owner": "material_map_lifecycle",
            "first_action": "material_map_quick_inventory",
            "required_inputs": ["project_brief.json or brief.json", "materials/raw or user material paths"],
            "expected_outputs": ["project_material_map.json", "material_delta.json"],
            "return_to": "Video Intent Planner / type planner after material facts reduce ambiguity",
        }
    if entry_path == "structure-first":
        return {
            "owner": "upstream_structure_route",
            "first_action": "story_soul_blueprint",
            "required_inputs": ["project_brief.json or brief.json", "text/article/outline/script/story"],
            "expected_outputs": ["story_soul_blueprint.json", "material_needs.json", "initial material_delta.json"],
            "return_to": "material_generation_fallback when material delta shows missing/thin needs",
        }
    return {
        "owner": "Video Intent Planner",
        "first_action": "ask_followup_questions",
        "required_inputs": ["required_followup_questions"],
        "expected_outputs": ["updated project_brief.json or video_intent.json"],
        "return_to": "Video Intent Planner",
    }


def _later_planner(video_type: str | None) -> str | None:
    mapping = {
        "teaching": "teaching-structure-planner",
        "storybook": "story-soul-blueprint",
        "fiction": "story-soul-blueprint",
        "personal-memory": "memory-story-planner",
        "graduation-event": "event-recap-planner",
        "event": "event-recap-planner",
        "brand-product": "brand-short-planner",
    }
    return mapping.get(video_type or "")


def _questions(
    brief: dict[str, Any],
    video_type: str | None,
    material_availability: str | None,
    text_availability: str,
) -> list[str]:
    questions: list[str] = []
    if not video_type:
        questions.append("What kind of video is this: teaching, event recap, story, brand short, personal memory, or other?")
    if not _clean(brief.get("audience")):
        questions.append("Who is the main audience?")
    if not _clean(brief.get("goal")):
        questions.append("What is the main goal or desired audience effect?")
    if not material_availability:
        questions.append("Do you already have material? Is it complete, partial, or uncertain quality?")
    if material_availability == "none" and text_availability in {"none", "unknown", ""}:
        questions.append("Do you have an article, outline, script, story, or only a loose idea?")
    if not _clean(brief.get("target_length")):
        questions.append("Roughly how long should the final video be?")
    if not _clean(brief.get("tone") or brief.get("style")):
        questions.append("Should the style feel documentary, energetic, warm, story-driven, MV-like, or clearly instructional?")
    return questions


def plan_video_intent(brief: dict[str, Any]) -> dict[str, Any]:
    """Create the canonical Stage 0 route artifact without running later stages."""
    video_type = _detect_video_type(brief)
    material_availability = _detect_material_availability(brief)
    text_availability = _detect_text_availability(brief)
    input_state = _input_state(material_availability, text_availability)
    questions = _questions(brief, video_type, material_availability, text_availability)
    entry_path = _entry_path_for(input_state, questions)
    legacy_route = _legacy_route_for(material_availability, entry_path)
    generation_allowed = bool(brief.get("generation_allowed", False))
    needs_generated = entry_path == "structure-first" and (
        material_availability == "none" or bool(brief.get("generation_allowed"))
    )

    if entry_path == "structure-first":
        handoff_to = "upstream_structure_route"
    elif entry_path == "material-first":
        handoff_to = "material_map_lifecycle"
    else:
        handoff_to = "ask_followup"

    next_steps: list[str] = []
    gap_strategy = "unknown"
    if entry_path == "material-first":
        next_steps.append("run material map lifecycle before structure/template work")
        next_steps.append("use material map findings to reduce ambiguity before writing structure")
        gap_strategy = "pending_material_delta"
    elif entry_path == "structure-first":
        next_steps.append("run upstream structure route")
        if needs_generated:
            next_steps.append("run initial material delta before generated material fallback")
            gap_strategy = "generated_fallback_possible"
    elif entry_path == "needs-context":
        next_steps.append("ask follow-up questions before selecting a handoff")

    return {
        "artifact_role": "video_intent",
        "version": 1,
        "stage": "Video Intent Planner",
        "video_type": video_type,
        "audience": brief.get("audience"),
        "goal": brief.get("goal"),
        "target_length": brief.get("target_length"),
        "tone": brief.get("tone") or brief.get("style"),
        "input_state": input_state,
        "material_availability": material_availability,
        "text_availability": text_availability,
        "material_quality": brief.get("material_quality"),
        "entry_path": entry_path,
        "route": entry_path,
        "legacy_route": legacy_route,
        "gap_strategy": gap_strategy,
        "needs_material_map_first": entry_path == "material-first",
        "needs_generated_material_fallback": needs_generated,
        "generation_allowed": generation_allowed,
        "required_followup_questions": questions,
        "assumptions": list(brief.get("assumptions", [])) if isinstance(brief.get("assumptions", []), list) else [],
        "handoff_to": handoff_to,
        "handoff_packet": _handoff_packet(entry_path),
        "later_planner": _later_planner(video_type),
        "next_steps": next_steps,
    }
