"""SSB1 story-soul blueprint compiler.

This deterministic compiler turns a high-level project brief into upstream
creative artifacts that feed the existing writer/director/material-map flow.
It is not a replacement for a writer agent; it is a contract shape and baseline
story-logic scaffold.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Mapping


def _text(value: Any, default: str = "") -> str:
    return value.strip() if isinstance(value, str) and value.strip() else default


def _as_list(value: Any) -> list:
    return value if isinstance(value, list) else []


def _slug(value: str) -> str:
    chars = []
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
        elif chars and chars[-1] != "_":
            chars.append("_")
    return "".join(chars).strip("_") or "beat"


def _need_id(seed: str) -> str:
    return "nd_" + hashlib.sha1(seed.encode("utf-8")).hexdigest()[:8]


def _has_subject(brief: Mapping[str, Any]) -> bool:
    facts = brief.get("facts") if isinstance(brief.get("facts"), Mapping) else {}
    return bool(
        _text(facts.get("cohort"))
        or _text(facts.get("protagonist"))
        or _as_list(brief.get("known_material_categories"))
        or _text(brief.get("seed_device"))
    )


def _story_seed(brief: Mapping[str, Any]) -> Mapping[str, Any]:
    return brief.get("story_seed") if isinstance(brief.get("story_seed"), Mapping) else {}


def _protagonist_text(brief: Mapping[str, Any], default: str = "the protagonist") -> str:
    facts = brief.get("facts") if isinstance(brief.get("facts"), Mapping) else {}
    seed = _story_seed(brief)
    protagonists = _as_list(seed.get("protagonists"))
    return (
        _text(facts.get("protagonist"))
        or " and ".join(str(item) for item in protagonists if str(item).strip())
        or default
    )


def _setting_text(brief: Mapping[str, Any], default: str = "project-defined setting") -> str:
    facts = brief.get("facts") if isinstance(brief.get("facts"), Mapping) else {}
    seed = _story_seed(brief)
    return _text(facts.get("place")) or _text(seed.get("setting")) or default


def _story_motifs(brief: Mapping[str, Any]) -> list[str]:
    seed = _text(brief.get("seed_device"))
    values = []
    for value in [seed, *_as_list(brief.get("required_inclusions")), _setting_text(brief, "")]:
        value = str(value).strip()
        if value and value not in values:
            values.append(value)
    return values


def _stage0_child_contracts(brief: Mapping[str, Any]) -> dict:
    source = brief.get("stage0_child_contracts") if isinstance(brief.get("stage0_child_contracts"), Mapping) else {}
    video_intent = brief.get("video_intent") if isinstance(brief.get("video_intent"), Mapping) else {}
    material = (
        source.get("material")
        or video_intent.get("material_contract")
        or brief.get("material_contract")
        or {}
    )
    soundtrack = (
        source.get("soundtrack")
        or video_intent.get("soundtrack_contract")
        or brief.get("soundtrack_contract")
        or {}
    )
    effect = (
        source.get("effect")
        or video_intent.get("effect_policy")
        or brief.get("effect_policy")
        or {}
    )
    subtitle_voiceover = (
        source.get("subtitle_voiceover")
        or video_intent.get("subtitle_voiceover_contract")
        or brief.get("subtitle_voiceover_contract")
        or {}
    )
    contracts = {
        "material": dict(material) if isinstance(material, Mapping) else {},
        "soundtrack": dict(soundtrack) if isinstance(soundtrack, Mapping) else {},
        "effect": dict(effect) if isinstance(effect, Mapping) else {},
        "subtitle_voiceover": dict(subtitle_voiceover) if isinstance(subtitle_voiceover, Mapping) else {},
    }
    return {key: value for key, value in contracts.items() if value}


def _story_world(brief: Mapping[str, Any]) -> dict:
    facts = brief.get("facts") if isinstance(brief.get("facts"), Mapping) else {}
    story_seed = _story_seed(brief)
    return {
        "artifact_role": "story_world",
        "version": 1,
        "project_type": _text(brief.get("project_type"),),
        "audience": _text(brief.get("audience"), "general viewers"),
        "people": [
            value for value in (
                _text(facts.get("cohort")),
                _text(facts.get("protagonist")),
                "instructors" if "training" in _text(brief.get("project_type")) else "",
            ) if value
        ],
        "place": _text(facts.get("place"), "project-defined setting"),
        "time_span": _text(facts.get("time_span"), "one story period"),
        "institutional_context": _text(facts.get("cohort"), _text(brief.get("project_type"))),
        "key_events": _as_list(brief.get("known_material_categories")),
        "required_inclusions": _as_list(brief.get("required_inclusions")),
        "available_material_summary": _as_list(brief.get("known_material_categories")),
        "emotional_truths": [
            "time spent together changes how departure feels",
            "training is meaningful because people endure it together",
        ] if "training" in _text(brief.get("project_type")) else [
            _text(story_seed.get("moral"), "a small kindness can become a path"),
            "the way home becomes visible through care, courage, and wonder",
        ],
        "known_symbols": [
            _text(brief.get("seed_device")),
            "notebook",
            "uniform",
        ] if "training" in _text(brief.get("project_type")) else [
            value for value in _story_motifs(brief)
        ],
    }


def _creative_concept(brief: Mapping[str, Any], world: Mapping[str, Any]) -> dict:
    project_type = _text(brief.get("project_type"))
    seed = _text(brief.get("seed_device"))
    if "training" in project_type:
        metaphor = seed or "0.66% of life spent in training center"
        return {
            "artifact_role": "creative_concept",
            "version": 1,
            "core_metaphor": metaphor,
            "logline": "A trainee writes a final report and discovers that a small percentage of life became a lasting memory.",
            "narrative_device": "internship report writing becomes a memory frame",
            "memory_frame": "pen on report paper triggers morning-to-night recollection",
            "emotional_arc": ["pressure", "struggle", "companionship", "gratitude", "departure"],
            "visual_motifs": ["report paper", "helmet", "morning light", "training center gate"],
            "human_anchors": world.get("people") or [],
            "opening_question": "What can 0.66% of life change?",
            "closing_answer": "Enough to become a place people carry after leaving.",
            "why_this_is_not_a_course_list": "Courses appear as memories inside one report-writing frame, so each item must advance endurance, gratitude, or departure.",
        }
    subject = _protagonist_text(brief, "the story protagonist")
    place = _setting_text(brief)
    motifs = _story_motifs(brief) or [seed or subject]
    goal = _text(brief.get("goal"))
    if seed or _story_seed(brief) or _as_list(brief.get("required_inclusions")):
        return {
            "artifact_role": "creative_concept",
            "version": 1,
            "core_metaphor": seed or motifs[0],
            "logline": goal or f"{subject} move through {place} toward a warm resolution.",
            "narrative_device": f"{seed or motifs[0]} guides the story from being lost to finding the way",
            "memory_frame": f"each panel follows {subject} through {place}",
            "emotional_arc": ["lost", "noticed", "helped", "choice", "home"],
            "visual_motifs": motifs,
            "human_anchors": world.get("people") or [subject],
            "opening_question": f"Can {subject} find the way home?",
            "closing_answer": "Yes, because small kindness becomes a path.",
            "why_this_is_not_a_course_list": "The film follows the user's story seed and emotional turn instead of substituting a generic adventure template.",
        }
    metaphor = "one message crossing the city sky"
    return {
        "artifact_role": "creative_concept",
        "version": 1,
        "core_metaphor": metaphor,
        "logline": "A courier crosses the city to deliver a forgotten message before sunset.",
        "narrative_device": "a postcard becomes the thread connecting separate places",
        "memory_frame": "each panel follows the postcard's movement",
        "emotional_arc": ["curiosity", "effort", "risk", "connection", "relief"],
        "visual_motifs": ["postcard", "red scarf", "rooftop skyline", "warm sunset"],
        "human_anchors": world.get("people") or [],
        "opening_question": "Can one small message still arrive in time?",
        "closing_answer": "Yes, if someone chooses to carry it.",
        "why_this_is_not_a_course_list": "The film follows one emotional object spine instead of listing locations.",
    }


def _training_beats() -> list[dict]:
    rows = [
        ("frame_open", "Report page opens", "frame the film through the final report", "uncertainty to recall", "voiceover", 2, 3),
        ("morning", "Morning assembly", "establish the training center as a shared world", "sleepiness to focus", "mv", 3, 5),
        ("first_struggle", "First difficult course", "show that training is physically real", "focus to strain", "mv", 4, 6),
        ("teamwork", "Helping each other", "turn individual struggle into class identity", "strain to trust", "mv", 4, 6),
        ("director", "Director encouragement", "give the memory a spoken spiritual anchor", "effort to meaning", "interview", 2, 3),
        ("daily_life", "Daily life warmth", "show the human life around training", "pressure to warmth", "mv", 4, 6),
        ("activity", "Class activities", "expand the class beyond course footage", "warmth to fullness", "mv", 3, 5),
        ("completion", "Training completed", "close the memory with departure", "gratitude to departure", "voiceover", 3, 5),
    ]
    return [_beat(*row) for row in rows]


def _comic_beats() -> list[dict]:
    rows = [
        ("setup", "Message found", "introduce the postcard and courier", "curiosity to decision", "title_card", 4, 6),
        ("route", "Across the rooftops", "make the delivery feel like a journey", "decision to motion", "mv", 5, 8),
        ("obstacle", "The route narrows", "create visual tension before payoff", "motion to risk", "mv", 4, 6),
        ("choice", "Keep going", "show the protagonist choosing care over ease", "risk to resolve", "voiceover", 4, 6),
        ("payoff", "Postcard arrives", "release the story emotion", "resolve to warmth", "mv", 4, 6),
    ]
    return [_beat(*row) for row in rows]


def _seeded_story_beats(brief: Mapping[str, Any]) -> list[dict]:
    seed = _text(brief.get("seed_device"), "story seed")
    subject = _protagonist_text(brief)
    place = _setting_text(brief)
    rows = [
        ("setup", "Lost on the moonlit path",
         f"introduce {subject} in {place}", "comfort to concern", "title_card", 3, 5),
        ("guide", "The tiny lantern appears",
         f"show how {seed} offers gentle help", "concern to trust", "mv", 4, 6),
        ("journey", "Following the soft light",
         f"make the journey through {place} feel safe and magical", "trust to wonder", "mv", 4, 6),
        ("choice", "Sharing the lantern's kindness",
         "show that kindness grows when it is shared", "wonder to choice", "voiceover", 3, 5),
        ("home", "The moon bridge home",
         f"release the story with {seed} and a warm safe ending", "choice to home", "mv", 4, 6),
    ]
    return [_beat(*row) for row in rows]


def _beat(beat_id: str, title: str, function: str, emotion: str,
          mode: str, minimum: int, ideal: int) -> dict:
    feeling = emotion.split(" to ")[-1] if " to " in emotion else emotion
    return {
        "beat_id": beat_id,
        "title": title,
        "story_function": function,
        "emotional_movement": emotion,
        "conflict_or_turn": f"{title} changes the viewer from {emotion}",
        "sensory_anchor": f"let the audience feel {title.lower()} through light, texture, movement, and human reaction",
        "intended_viewer_feeling": feeling,
        "narrative_mode": mode,
        "voiceover_intent": f"state why '{title}' matters without explaining the obvious",
        "visual_intent": function,
        "required_actions": [title.lower()],
        "human_anchor": "shared class" if mode != "title_card" else "object spine",
        "transition_in": "motivated by previous emotional beat",
        "transition_out": "hands the emotion to the next beat",
        "existence_test": f"without this beat, the story loses: {function}",
        "minimum_material_count": minimum,
        "ideal_material_count": ideal,
        "fallback_if_missing": "generate symbolic/comic panels or shorten this beat honestly",
    }


def _screenplay_beats(brief: Mapping[str, Any]) -> dict:
    project_type = _text(brief.get("project_type"))
    if "training" in project_type:
        beats = _training_beats()
    elif _story_seed(brief) or _as_list(brief.get("required_inclusions")):
        beats = _seeded_story_beats(brief)
    else:
        beats = _comic_beats()
    return {"artifact_role": "screenplay_beats", "version": 1, "beats": beats}


def _shot_for(brief: Mapping[str, Any], concept: Mapping[str, Any], beat: Mapping[str, Any]) -> dict:
    project_type = _text(brief.get("project_type"))
    generated = "generated" in project_type or not _as_list(brief.get("known_material_categories"))
    family = f"{_slug(beat['beat_id'])}_panel" if generated else f"{_slug(beat['beat_id'])}_memory"
    subject = _protagonist_text(brief) if generated else "training class memory"
    need_id = _need_id(f"{project_type}|{beat['beat_id']}|{beat['story_function']}")
    desired_style = _text(brief.get("desired_style"))
    style_clause = f"{desired_style}; " if desired_style else ""
    motif_clause = ", ".join([str(m) for m in concept.get("visual_motifs") or [] if str(m).strip()])
    prompt = (
        f"{style_clause}{concept['core_metaphor']}; {beat['story_function']}; {subject}; "
        f"{family}; {beat['emotional_movement']}; 35mm cinematic composition"
    )
    if motif_clause:
        prompt += f"; visual motifs: {motif_clause}"
    director_intent = {
        "composition": f"{beat['title']} as {family}, composed around {subject}",
        "camera_motion": "slow push if reflective; quicker montage cut if action-driven",
        "edit_role": f"serve the beat turn: {beat['conflict_or_turn']}",
        "audio_subtitle_intent": beat["voiceover_intent"],
        "material_prompt_requirements": [
            concept["core_metaphor"],
            beat["story_function"],
            family,
            subject,
            beat["sensory_anchor"],
        ],
    }
    return {
        "need_id": need_id,
        "beat_id": beat["beat_id"],
        "story_function": beat["story_function"],
        "emotion": beat["emotional_movement"],
        "visual_family": family,
        "angle_scale": "wide" if beat["minimum_material_count"] >= 4 else "medium",
        "action_family": _slug(beat["title"]),
        "subject": subject,
        "director_intent": director_intent,
        "media_preference": "generated_image" if generated else "video",
        "panel_count_min": beat["minimum_material_count"],
        "panel_count_ideal": beat["ideal_material_count"],
        "prompt": prompt,
        "negative_prompt": "text, watermark, logo, distorted hands, fake documentary proof",
        "motion_treatment": "slow push / montage cut",
        "subtitle_or_title_card_intent": beat["voiceover_intent"],
        "fallback_route": "generated_image" if generated else "generated_material_fallback",
    }


def _director_and_needs(brief: Mapping[str, Any], concept: Mapping[str, Any],
                        beats_payload: Mapping[str, Any]) -> tuple[dict, dict, dict]:
    shots = [_shot_for(brief, concept, beat) for beat in beats_payload["beats"]]
    needs = []
    generation_items = []
    for shot in shots:
        needs.append({
            "need_id": shot["need_id"],
            "category": "story_beat",
            "type": "visual_material",
            "purpose": shot["story_function"],
            "count": shot["panel_count_min"],
            "must_have": True,
            "fallback_tier": 2,
            "fallback_options": [shot["fallback_route"]],
        })
        if shot["media_preference"].startswith("generated") or shot["fallback_route"].startswith("generated"):
            generation_items.append({
                "need_id": shot["need_id"],
                "beat_id": shot["beat_id"],
                "prompt": shot["prompt"],
                "panel_count": shot["panel_count_min"],
            })
    return (
        {"artifact_role": "director_shot_plan", "version": 1, "shots": shots},
        {"artifact_role": "material_needs", "version": 1,
         "project": _text(brief.get("project_type")), "needs": needs},
        {"artifact_role": "generation_manifest", "version": 1, "items": generation_items},
    )


def _review_checklist(concept: Mapping[str, Any], beats: Mapping[str, Any]) -> str:
    lines = [
        "# Story Soul Review Checklist",
        "",
        f"- Core metaphor: {concept['core_metaphor']}",
        f"- Narrative device: {concept['narrative_device']}",
        f"- Opening question: {concept['opening_question']}",
        f"- Closing answer: {concept['closing_answer']}",
        "",
        "Review each beat:",
    ]
    for beat in beats["beats"]:
        lines.append(f"- {beat['beat_id']}: {beat['existence_test']}")
    lines.extend([
        "",
        "Reject if the output becomes a course/location list without emotional movement.",
        "Reject if material count cannot support the promised duration.",
    ])
    return "\n".join(lines)


def build_story_soul_blueprint(brief: Mapping[str, Any]) -> dict:
    if not isinstance(brief, Mapping):
        return {"ok": False, "errors": ["brief must be an object"]}
    if not _has_subject(brief):
        return {"ok": False, "errors": ["story subject is missing; cannot build soulful blueprint"]}
    world = _story_world(brief)
    concept = _creative_concept(brief, world)
    beats = _screenplay_beats(brief)
    director, needs, generation = _director_and_needs(brief, concept, beats)
    child_contracts = _stage0_child_contracts(brief)
    if child_contracts:
        director["stage0_child_contracts"] = child_contracts
        if child_contracts.get("material"):
            needs["stage0_material_contract"] = child_contracts["material"]
        for shot in director.get("shots") or []:
            intent = shot.setdefault("director_intent", {})
            if child_contracts.get("soundtrack"):
                intent["soundtrack_intent"] = child_contracts["soundtrack"]
            if child_contracts.get("subtitle_voiceover"):
                intent["subtitle_voiceover_intent"] = child_contracts["subtitle_voiceover"]
            if child_contracts.get("effect"):
                intent["effect_policy"] = child_contracts["effect"]
    checklist = _review_checklist(concept, beats)
    result = {
        "ok": True,
        "errors": [],
        "story_world": world,
        "creative_concept": concept,
        "screenplay_beats": beats,
        "director_shot_plan": director,
        "material_needs": needs,
        "generation_manifest": generation,
        "review_checklist": checklist,
    }
    if child_contracts:
        result["stage0_child_contracts"] = child_contracts
    return result


def write_story_soul_blueprint(brief: Mapping[str, Any], out_dir: str | Path) -> dict:
    result = build_story_soul_blueprint(brief)
    if not result["ok"]:
        return result
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for key in (
        "story_world",
        "creative_concept",
        "screenplay_beats",
        "director_shot_plan",
        "material_needs",
        "generation_manifest",
    ):
        (out / f"{key}.json").write_text(
            json.dumps(result[key], ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "review_checklist.md").write_text(result["review_checklist"], encoding="utf-8")
    result["refs"] = {key: str(out / f"{key}.json") for key in (
        "story_world", "creative_concept", "screenplay_beats",
        "director_shot_plan", "material_needs", "generation_manifest")}
    result["refs"]["review_checklist"] = str(out / "review_checklist.md")
    return result
