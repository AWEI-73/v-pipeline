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
    if any(k in text for k in ("graduation", "event recap", "結訓", "畢業", "典禮")):
        return "graduation-event"
    if any(k in text for k in ("brand", "product")):
        return "brand-product"
    if any(k in text for k in ("memory", "personal")):
        return "personal-memory"
    return None


def _detect_semantic_route_hint(brief: dict[str, Any]) -> str | None:
    explicit = _clean(
        brief.get("semantic_route_hint")
        or brief.get("specialized_route")
        or brief.get("handoff_branch")
        or brief.get("route_hint")
    )
    if explicit:
        return explicit.replace("_", "-").lower()
    text = _lower_text(brief.get("request"), brief.get("goal"), brief.get("task"))
    if any(k in text for k in ("effect only", "opening effect", "transition effect", "lower third", "特效", "轉場", "開場特效")):
        return "effect-factory"
    if any(k in text for k in ("rough cut", "draft edit", "brownfield", "workbench", "修改粗剪", "草稿剪輯")):
        return "brownfield-edit"
    if any(k in text for k in ("review final", "existing final", "verify final", "delivery review", "審片", "成片 review", "檢查成片")):
        return "final-review"
    return None


def _detect_music_role(brief: dict[str, Any]) -> str:
    explicit = _clean(
        brief.get("music_role")
        or brief.get("soundtrack_role")
        or brief.get("audio_role")
    ).lower()
    if explicit in {"song", "bgm", "mixed", "none", "silence", "unsure"}:
        return "none" if explicit == "silence" else explicit
    text = _lower_text(
        brief.get("request"),
        brief.get("goal"),
        brief.get("tone"),
        brief.get("style"),
        brief.get("style_direction"),
        brief.get("soundtrack"),
        brief.get("music"),
    )
    if any(k in text for k in ("no music", "without music", "silent")):
        return "none"
    wants_song = any(k in text for k in ("song", "vocal", "pop", "lyrics", "singing"))
    wants_bgm = any(k in text for k in ("bgm", "background music", "instrumental", "score", "soundtrack", "music"))
    if wants_song and wants_bgm:
        return "mixed"
    if wants_song:
        return "song"
    if wants_bgm:
        return "bgm"
    return "unsure"


def _detect_energy_intent(text: str) -> str:
    has_warm = any(k in text for k in ("warm", "emotional", "moving", "soft", "gentle", "感人", "溫馨"))
    has_high = any(k in text for k in ("hot-blooded", "energetic", "high energy", "mv", "climax", "熱血", "澎湃"))
    if has_warm and has_high:
        return "warm_to_high"
    if has_high:
        return "high"
    if has_warm:
        return "warm"
    return "unspecified"


def _detect_speech_preservation(text: str) -> tuple[str, str]:
    if any(k in text for k in ("director speech", "speech", "interview", "voiceover", "keep voice", "preserve speech", "長官", "主任", "致詞", "口白")):
        return "required", "duck_under_voice"
    return "preserve_if_detected", "duck_under_voice"


def _soundtrack_contract(brief: dict[str, Any]) -> dict[str, Any]:
    music_role = _detect_music_role(brief)
    text = _lower_text(
        brief.get("request"),
        brief.get("goal"),
        brief.get("tone"),
        brief.get("style"),
        brief.get("style_direction"),
        brief.get("soundtrack"),
        brief.get("music"),
    )
    if music_role == "song":
        vocal_policy = "vocal_ok"
    elif music_role in {"bgm", "mixed"} and any(k in text for k in ("instrumental", "no vocal", "no vocals")):
        vocal_policy = "instrumental_preferred"
    elif music_role == "mixed":
        vocal_policy = "section_dependent"
    elif music_role == "none":
        vocal_policy = "none"
    else:
        vocal_policy = "unknown"

    requested = music_role != "unsure" or any(
        k in text for k in ("music", "soundtrack", "bgm", "song", "mv")
    )
    followups: list[str] = []
    if requested and music_role == "unsure":
        followups.append("Should the soundtrack use songs with vocals, instrumental BGM, mixed sections, or no music?")
    if music_role in {"song", "mixed"}:
        followups.append("Are vocals/songs allowed in the final delivery, or are they reference-only?")
    speech_preservation, ducking_policy = _detect_speech_preservation(text)
    return {
        "artifact_role": "stage0_soundtrack_intent",
        "status": "requested" if requested else "unspecified",
        "music_role": music_role,
        "vocal_policy": vocal_policy,
        "energy_intent": _detect_energy_intent(text),
        "speech_preservation": speech_preservation,
        "ducking_policy": ducking_policy,
        "fallback_policy": {
            "provider_fallback": ["jamendo_song", "pixabay_music", "manual_import", "reference_only"]
            if music_role in {"song", "mixed"}
            else ["pixabay_music", "manual_import", "reference_only"],
            "role_fallback": "song_to_bgm_requires_review" if music_role in {"song", "mixed"} else "bgm_to_silence_requires_review",
            "brownfield_fallback": "workbench_replace_or_retime_after_review",
        },
        "section_strategy": "section_based" if music_role in {"mixed", "song", "bgm"} else "unknown",
        "handoff_to": "soundtrack-arranger" if requested and music_role != "none" else "none",
        "required_followup_questions": followups,
    }


def _effect_policy(brief: dict[str, Any], semantic_route_hint: str | None) -> dict[str, Any]:
    text = _lower_text(
        brief.get("request"),
        brief.get("goal"),
        brief.get("tone"),
        brief.get("style"),
        brief.get("style_direction"),
        brief.get("effect"),
        brief.get("effects"),
    )
    effect_terms = (
        "effect",
        "transition",
        "opening",
        "title intro",
        "lower third",
        "highlight",
        "overlay",
        "sakura",
        "lightning",
        "fire",
        "heart",
        "photo wall",
        "memory wall",
    )
    requested = semantic_route_hint == "effect-factory" or any(k in text for k in effect_terms)
    bounded_only = semantic_route_hint == "effect-factory" and not any(
        k in text for k in ("whole video", "full video", "recap", "film", "story")
    )
    if bounded_only:
        activation = "route_to_effect_factory"
        handoff_to = "video-effect-factory"
        required_now = True
    elif requested:
        activation = "defer_to_brownfield_or_segment_review"
        handoff_to = "video-effect-factory_when_segment_requires_effect"
        required_now = False
    else:
        activation = "none"
        handoff_to = "none"
        required_now = False
    return {
        "artifact_role": "stage0_effect_policy",
        "status": "requested" if requested else "unspecified",
        "activation": activation,
        "required_now": required_now,
        "handoff_to": handoff_to,
        "boundary": "Stage 0 records effect intent only; Effect Factory/Remotion is not launched from fuzzy whole-video intake.",
        "required_followup_questions": [
            "Which section needs the effect, and what story function should it serve?"
        ] if requested and not bounded_only else [],
    }


def _subtitle_voiceover_contract(brief: dict[str, Any]) -> dict[str, Any]:
    text = _lower_text(
        brief.get("request"),
        brief.get("goal"),
        brief.get("tone"),
        brief.get("style"),
        brief.get("language"),
        brief.get("subtitle"),
        brief.get("subtitles"),
        brief.get("voiceover"),
        brief.get("narration"),
    )
    explicit_language = _clean(
        brief.get("language")
        or brief.get("subtitle_language")
        or brief.get("narration_language")
    )
    if explicit_language:
        language = explicit_language
    elif any(k in text for k in ("zh-tw", "traditional chinese", "chinese", "中文", "繁體")):
        language = "zh-TW"
    elif any(k in text for k in ("english", "en-us")):
        language = "en"
    else:
        language = "unknown"

    explicit_subtitle = brief.get("subtitle_required")
    if explicit_subtitle is None:
        explicit_subtitle = brief.get("subtitles_required")
    if explicit_subtitle is None:
        subtitle_required = not any(k in text for k in ("no subtitle", "no subtitles", "without subtitle", "不要字幕"))
    else:
        subtitle_required = bool(explicit_subtitle)

    explicit_voiceover = brief.get("voiceover_required")
    if explicit_voiceover is None:
        explicit_voiceover = brief.get("narration_required")
    if explicit_voiceover is None:
        voiceover_required = any(k in text for k in ("voiceover", "narration", "narrator", "旁白", "口白"))
    else:
        voiceover_required = bool(explicit_voiceover)

    if voiceover_required:
        narration_policy = "required"
    elif any(k in text for k in ("no narration", "no voiceover", "不要旁白", "不要口白")):
        narration_policy = "none"
    else:
        narration_policy = "optional"

    if subtitle_required and voiceover_required:
        handoff_to = "subtitle-director+audio-director"
    elif subtitle_required:
        handoff_to = "subtitle-director"
    elif voiceover_required:
        handoff_to = "audio-director"
    else:
        handoff_to = "none"

    requested = (
        language != "unknown"
        or subtitle_required
        or voiceover_required
        or any(k in text for k in ("subtitle", "subtitles", "voiceover", "narration", "字幕", "旁白", "口白"))
    )
    return {
        "artifact_role": "stage0_subtitle_voiceover_intent",
        "status": "requested" if requested else "unspecified",
        "language": language,
        "subtitle_required": subtitle_required,
        "voiceover_required": voiceover_required,
        "narration_policy": narration_policy,
        "handoff_to": handoff_to,
        "boundary": "Stage 0 records language/subtitle/voiceover intent; execution belongs to Subtitle Director, Audio Director, BUILD, Verify, and Delivery.",
        "required_followup_questions": [
            "Which language should subtitles and narration use?"
        ] if language == "unknown" and (subtitle_required or voiceover_required) else [],
    }


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


def _material_contract(entry_path: str, material_availability: str | None, input_state: str) -> dict[str, Any]:
    if entry_path == "material-first":
        first_action = "material_map_quick_inventory"
        owner = "material_map_lifecycle"
    elif entry_path == "structure-first":
        first_action = "derive_material_needs_after_structure"
        owner = "upstream_structure_route"
    else:
        first_action = "ask_material_availability"
        owner = "Video Intent Planner"
    return {
        "artifact_role": "stage0_material_intent",
        "availability": material_availability or "unknown",
        "input_state": input_state,
        "owner": owner,
        "first_action": first_action,
        "gap_policy": "material_delta_decides_generate_reshoot_rewrite_drop_or_waiver",
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
    if (
        material_availability == "none"
        and text_availability in {"none", "unknown", ""}
        and not brief.get("generation_allowed")
    ):
        questions.append("Do you have an article, outline, script, story, or only a loose idea?")
    if not _clean(brief.get("target_length")):
        questions.append("Roughly how long should the final video be?")
    if not _clean(brief.get("tone") or brief.get("style")):
        questions.append("Should the style feel documentary, energetic, warm, story-driven, MV-like, or clearly instructional?")
    return questions


def plan_video_intent(brief: dict[str, Any]) -> dict[str, Any]:
    """Create the canonical Stage 0 route artifact without running later stages."""
    video_type = _detect_video_type(brief)
    semantic_route_hint = _detect_semantic_route_hint(brief)
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

    soundtrack_contract = _soundtrack_contract(brief)
    effect_policy = _effect_policy(brief, semantic_route_hint)
    material_contract = _material_contract(entry_path, material_availability, input_state)
    subtitle_voiceover_contract = _subtitle_voiceover_contract(brief)

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
        "semantic_route_hint": semantic_route_hint,
        "gap_strategy": gap_strategy,
        "material_contract": material_contract,
        "soundtrack_contract": soundtrack_contract,
        "effect_policy": effect_policy,
        "subtitle_voiceover_contract": subtitle_voiceover_contract,
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
