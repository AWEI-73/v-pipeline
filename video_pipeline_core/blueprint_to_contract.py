"""blueprint_to_contract.py — compile a blueprint + per-beat editorial decisions
into a full segment_contract.json.

Division of labour (see docs/imagery-to-edit-lexicon-spec.md):
  - The AGENT (director skill) supplies the JUDGMENT per beat: which content_pattern,
    the key imagery → required_functions, pace, audio, must_include, text.
  - This COMPILER applies the MECHANICAL half of the lexicon deterministically:
    content_pattern -> default functions / pace / preferred_shot_sec / treatment,
    emphasis -> editing_grammar.role (placed at the correct segment-level slot),
    honesty guard, blueprint_ref wiring, section_role, transition defaults.

This removes hand-authored-JSON mistakes (e.g. nesting editing_grammar inside core,
which silently drops segment weight) and guarantees every segment carries the
density fields the engine needs.

All functions pure (no I/O, no print). Provider/backend neutral.
"""
from __future__ import annotations

from typing import Any

# content_pattern -> sensible default required_functions (lexicon §2).
# action is intentionally rich (montage); the density-aware Node 9 then fills the
# time budget on top of these.
_DEFAULT_FUNCS: dict[str, list[str]] = {
    "establishing": ["detail", "establish"],
    "emotional": ["establish", "detail", "reaction"],
    "action": ["establish", "action", "detail", "action", "detail", "result"],
    "enumeration": ["action", "detail"],
    "process": ["establish", "action", "detail", "result"],
    "bridge": ["bridge"],
    "testimony": ["establish", "action", "result"],
    "proof": ["establish", "detail", "result"],
    "identity": ["establish", "detail"],
}

# content_pattern -> default pace (lexicon §3). Override per-beat with decisions.pace.
# THREE tiers: fast (montage), calm (still cutting ~6-8s, warm-doc), hold (freeze).
# Reserve hold for genuine continuous-speech / freeze payoff; calm sections must
# still cut, else a 60s "calm" beat renders as a 30s static hold.
_DEFAULT_PACE: dict[str, str] = {
    "establishing": "calm",
    "emotional": "calm",
    "action": "fast",
    "enumeration": "fast",
    "process": "fast",
    "bridge": "fast",
    "testimony": "hold",
    "proof": "hold",
    "identity": "calm",
}

# pace -> preferred_shot_sec band (lexicon §3 / mode presets).
_PACE_SHOT_SEC: dict[str, list[float]] = {
    "fast": [1.5, 4],
    "calm": [4, 8],
    "hold": [6, 12],
}

# patterns that MUST keep original audio / speech (honesty + lexicon §4).
_SPEECH_PATTERNS = frozenset({"testimony", "identity"})
_HONESTY_PATTERNS = frozenset({"testimony", "proof", "identity"})

# emphasis -> editing_grammar.role (drives weight via contract_adapter._seg_weight).
_VALID_ROLES = frozenset({"hero", "proof", "support", "bridge", "mood", "filler"})

_AUDIO_REASON = {
    "music": "音樂襯底為主",
    "duck": "保留現場原音，音樂讓位",
    "diegetic": "以現場原音為主",
}
_EMPHASIS_REASON = {
    "hero": "情緒/動作高點，給足篇幅",
    "proof": "成果證據段",
    "support": "輔助、墊節奏",
    "mood": "氛圍鋪陳",
    "bridge": "連接過場",
    "filler": "墊節奏",
}


def _nonempty_string(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _string_list(value: Any) -> list[str] | None:
    if not isinstance(value, list):
        return None
    out = [item.strip() for item in value if isinstance(item, str) and item.strip()]
    return out or None


def _story_soul(blueprint: dict) -> dict[str, Any]:
    concept = blueprint.get("creative_concept") if isinstance(blueprint.get("creative_concept"), dict) else {}
    out: dict[str, Any] = {}
    for key in ("narrative_device", "core_metaphor"):
        value = _nonempty_string(concept.get(key)) or _nonempty_string(blueprint.get(key))
        if value:
            out[key] = value
    arc = _string_list(concept.get("emotional_arc")) or _string_list(blueprint.get("emotional_arc"))
    if arc:
        out["emotional_arc"] = arc
    return out


def _beat_soul(beat: dict) -> dict[str, str]:
    out: dict[str, str] = {}
    for key in ("emotional_movement", "conflict_or_turn", "intended_viewer_feeling", "sensory_anchor"):
        value = _nonempty_string(beat.get(key))
        if value:
            out[key] = value
    return out


def _director_intent(decision: dict) -> dict[str, Any]:
    raw = decision.get("director_intent")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("composition", "camera_movement", "lighting", "emotion"):
        value = _nonempty_string(raw.get(key))
        if value:
            out[key] = value
    reqs = _string_list(raw.get("material_prompt_requirements"))
    if reqs:
        out["material_prompt_requirements"] = reqs
    return out


def _stage0_child_contracts(blueprint: dict) -> dict[str, Any]:
    raw = blueprint.get("stage0_child_contracts")
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key in ("material", "soundtrack", "effect", "subtitle_voiceover"):
        value = raw.get(key)
        if isinstance(value, dict) and value:
            out[key] = dict(value)
    return out


def _story_soul_content_pattern(beat: dict) -> str:
    mode = _nonempty_string(beat.get("narrative_mode")) or ""
    title = (_nonempty_string(beat.get("title")) or "").lower()
    function = (_nonempty_string(beat.get("story_function")) or "").lower()
    if mode == "interview" or "speech" in title or "encouragement" in title:
        return "testimony"
    if mode == "voiceover":
        return "emotional"
    if mode == "title_card":
        return "establishing"
    if any(token in function for token in ("process", "journey", "training", "course")):
        return "process"
    return "action" if mode == "mv" else "emotional"


def _story_soul_to_blueprint(story_soul: dict) -> dict[str, Any]:
    concept = story_soul.get("creative_concept") if isinstance(story_soul.get("creative_concept"), dict) else {}
    beats_payload = story_soul.get("screenplay_beats") if isinstance(story_soul.get("screenplay_beats"), dict) else {}
    beats = beats_payload.get("beats") if isinstance(beats_payload.get("beats"), list) else []
    converted = []
    for idx, beat in enumerate(beats):
        if not isinstance(beat, dict):
            continue
        beat_id = _nonempty_string(beat.get("beat_id")) or f"B{idx + 1}"
        if idx == 0:
            role = "setup"
        elif idx == len(beats) - 1:
            role = "resolve"
        elif "turn" in str(beat.get("conflict_or_turn") or "").lower():
            role = "turn"
        else:
            role = "develop"
        converted.append({
            "id": beat_id,
            "role": role,
            "summary": _nonempty_string(beat.get("story_function")) or _nonempty_string(beat.get("title")) or beat_id,
            "emotional_movement": beat.get("emotional_movement"),
            "conflict_or_turn": beat.get("conflict_or_turn"),
            "intended_viewer_feeling": beat.get("intended_viewer_feeling"),
            "sensory_anchor": beat.get("sensory_anchor"),
        })
    return {
        "artifact_role": "narrative_blueprint",
        "version": 1,
        "thesis": concept.get("logline") or concept.get("core_metaphor") or "story soul blueprint",
        "mode_hint": "story_soul",
        "creative_concept": concept,
        "stage0_child_contracts": story_soul.get("stage0_child_contracts") or (
            (story_soul.get("director_shot_plan") or {}).get("stage0_child_contracts")
            if isinstance(story_soul.get("director_shot_plan"), dict) else {}
        ),
        "beats": converted,
    }


def _story_soul_decisions(story_soul: dict) -> dict[str, dict[str, Any]]:
    beats_payload = story_soul.get("screenplay_beats") if isinstance(story_soul.get("screenplay_beats"), dict) else {}
    beats = [beat for beat in beats_payload.get("beats") or [] if isinstance(beat, dict)]
    director = story_soul.get("director_shot_plan") if isinstance(story_soul.get("director_shot_plan"), dict) else {}
    shots_by_beat = {
        str(shot.get("beat_id")): shot
        for shot in director.get("shots") or []
        if isinstance(shot, dict) and shot.get("beat_id")
    }
    decisions: dict[str, dict[str, Any]] = {}
    for beat in beats:
        beat_id = _nonempty_string(beat.get("beat_id"))
        if not beat_id:
            continue
        shot = shots_by_beat.get(beat_id) or {}
        raw_intent = shot.get("director_intent") if isinstance(shot.get("director_intent"), dict) else {}
        prompt_requirements = raw_intent.get("material_prompt_requirements")
        director_intent = {
            "composition": raw_intent.get("composition"),
            "camera_movement": raw_intent.get("camera_motion") or raw_intent.get("camera_movement"),
            "emotion": beat.get("intended_viewer_feeling"),
            "material_prompt_requirements": prompt_requirements,
        }
        decision = {
            "content_pattern": _story_soul_content_pattern(beat),
            "visual_desc": beat.get("story_function") or beat.get("visual_intent") or beat.get("title"),
            "material_hint": shot.get("visual_family") or shot.get("action_family") or beat.get("title"),
            "need_refs": [shot["need_id"]] if shot.get("need_id") else None,
            "director_intent": director_intent,
            "reason": beat.get("existence_test") or beat.get("story_function"),
        }
        if beat.get("narrative_mode") == "voiceover":
            decision["audio"] = {"role": "music", "voiceover_policy": "required"}
        if beat.get("narrative_mode") == "interview":
            decision["audio"] = {"role": "duck", "original_audio_policy": "keep"}
        decisions[beat_id] = {key: value for key, value in decision.items() if value is not None}
    return decisions


def compile_story_soul_contract(
    story_soul: dict,
    *,
    music: dict | None = None,
    categories_ref: str = "material_categories.json",
    brief_ref: str = "brief.json",
) -> dict:
    """Compile story-soul-blueprint output directly into segment_contract.

    This is the Stage 1/2 bridge: Story Soul remains the WHY layer, while this
    helper converts its screenplay/director/material-need artifacts into the
    existing Segment Contract compiler shape. It avoids a second hand-authored
    decisions schema between Story Soul and BUILD.
    """
    if not isinstance(story_soul, dict) or not story_soul.get("ok", True):
        raise ValueError("story_soul blueprint result must be an ok object")
    blueprint = _story_soul_to_blueprint(story_soul)
    decisions = _story_soul_decisions(story_soul)
    material_needs = story_soul.get("material_needs") if isinstance(story_soul.get("material_needs"), dict) else None
    return compile_contract(
        blueprint,
        decisions,
        material_needs=material_needs,
        music=music,
        categories_ref=categories_ref,
        brief_ref=brief_ref,
    )


def _section_role(beat_role: str, idx: int, n: int, content_pattern: str) -> str:
    if idx == 0:
        return "opening"
    if idx == n - 1:
        return "closing"
    if beat_role == "turn":
        return "climax"
    return beat_role or "develop"


def _default_emphasis(beat_role: str, content_pattern: str) -> str:
    if beat_role == "turn":
        return "hero"
    if content_pattern in ("testimony", "proof", "identity"):
        return "support"   # keep honest real-material holds, but don't over-weight by default
    if beat_role == "setup":
        return "mood"
    return "support"


def compile_contract(
    blueprint: dict,
    decisions: dict,
    *,
    material_needs: dict | None = None,
    music: dict | None = None,
    categories_ref: str = "material_categories.json",
    brief_ref: str = "brief.json",
) -> dict:
    """Compile blueprint.json + per-beat decisions -> segment_contract dict.

    blueprint: narrative_blueprint dict (beats[] with id/role/summary).
    decisions: { beat_id: {content_pattern, [pace], [functions], [audio], [items],
                 [steps], [must_include], [text_layer], [transition], [emphasis],
                 [material_hint], [visual_desc], [category], [layout], [effects_required]} }
                content_pattern is the only required field per beat.

    Raises ValueError if a beat has no decision or no content_pattern.
    """
    beats = blueprint.get("beats") or []
    needs = material_needs.get("needs") if isinstance(material_needs, dict) else []
    ordered_need_ids = [
        item.get("need_id")
        for item in needs
        if isinstance(item, dict) and _nonempty_string(item.get("need_id"))
    ]
    n = len(beats)
    segments: list[dict] = []
    story_soul = _story_soul(blueprint)
    stage0_child_contracts = _stage0_child_contracts(blueprint)

    for idx, beat in enumerate(beats):
        bid = str(beat.get("id") or "").strip()
        d = decisions.get(bid)
        if not d:
            raise ValueError(f"beat {bid!r} has no editorial decision")
        cp = d.get("content_pattern")
        if cp not in _DEFAULT_FUNCS:
            raise ValueError(f"beat {bid!r} needs a valid content_pattern (got {cp!r})")

        beat_role = beat.get("role") or "develop"
        section = _section_role(beat_role, idx, n, cp)
        pace = d.get("pace") or _DEFAULT_PACE[cp]   # fast | calm | hold
        # calm maps to a cutting pace (vis_pace=fast) with a slow band, so the
        # density rule fills the time at ~6-8s/shot instead of one long hold.
        vis_pace = "hold" if pace == "hold" else "fast"
        funcs = d.get("functions") or list(_DEFAULT_FUNCS[cp])
        layout = d.get("layout") or ("montage" if pace == "fast" else "single")

        emphasis = d.get("emphasis") or _default_emphasis(beat_role, cp)
        if emphasis not in _VALID_ROLES:
            emphasis = "support"

        # audio defaults (lexicon §4 + honesty)
        a = d.get("audio") or {}
        if cp in _SPEECH_PATTERNS:
            audio = {"role": a.get("role", "duck"),
                     "original_audio_policy": a.get("original_audio_policy", "keep")}
        else:
            audio = {"role": a.get("role", "music"),
                     "original_audio_policy": a.get("original_audio_policy", "drop")}
        audio["reason"] = a.get("reason") or _AUDIO_REASON.get(audio["role"], "音訊安排")

        # text layer (speech patterns auto-subtitle unless told otherwise)
        text_layer = dict(d.get("text_layer") or {})
        if cp in _SPEECH_PATTERNS and "subtitle" not in text_layer:
            text_layer["subtitle"] = "auto"
        if text_layer:
            text_layer.setdefault("reason", "段落文字標示")

        summary = beat.get("summary") or ""
        core = {
            "section_role": section,
            "story_purpose": d.get("visual_desc") or summary,
            "blueprint_ref": bid,
            "review_required": True,
            "timeline_source": "beat" if pace == "fast" else "fixed",
        }
        if story_soul.get("narrative_device"):
            core["narrative_device"] = story_soul["narrative_device"]
        core.update(_beat_soul(beat))

        material_fit: dict[str, Any] = {
            "category": d.get("category") or "daily_life",
            "visual_desc": d.get("visual_desc") or summary,
            "reason": d.get("reason") or f"實現 {beat_role} beat：{summary}"[:60],
        }
        if d.get("material_hint"):
            material_fit["material_hint"] = d["material_hint"]
        need_refs = _string_list(d.get("need_refs"))
        need_ref = _nonempty_string(d.get("need_ref"))
        if need_refs:
            material_fit["need_refs"] = need_refs
        elif need_ref:
            material_fit["need_refs"] = [need_ref]
        elif idx < len(ordered_need_ids):
            material_fit["need_refs"] = [ordered_need_ids[idx]]
        if d.get("search_query"):
            material_fit["search_query"] = d["search_query"]
        if d.get("must_include"):
            material_fit["must_include"] = d["must_include"]
            material_fit["collection_instructions"] = (
                d.get("collection_instructions") or f"需收集本人原素材：{d['must_include']}（不可替代）")

        director_intent = _director_intent(d)
        if director_intent.get("material_prompt_requirements"):
            material_fit["material_prompt_requirements"] = director_intent["material_prompt_requirements"]

        seg: dict[str, Any] = {
            "segment": idx + 1,
            "core": core,
            "material_fit": material_fit,
            "editing_intent": {"content_pattern": cp},
            "sequence_grammar": {"required_functions": funcs},
            "pacing": {"preferred_shot_sec": _PACE_SHOT_SEC.get(pace, [3, 6])},
            "audio": audio,
            "visual_style": {
                "layout": layout,
                "pace": vis_pace,
                "transition": d.get("transition") or ("beat_cut" if pace == "fast" else "direct_cut"),
                "reason": {"fast": "快剪堆疊出密度", "calm": "沉穩但持續切換，溫而不滯",
                           "hold": "留白長鏡，給情緒空間"}.get(pace, ""),
            },
            # SEGMENT-LEVEL (NOT nested in core — that silently drops weight)
            "editing_grammar": {"role": emphasis, "reason": _EMPHASIS_REASON.get(emphasis, "")},
        }
        if pace == "hold":
            seg["pacing"]["max_meaningful_shot_sec"] = 12
        if text_layer:
            seg["text_layer"] = text_layer

        if stage0_child_contracts:
            seg["stage0_child_contracts"] = stage0_child_contracts
            soundtrack = stage0_child_contracts.get("soundtrack") or {}
            subtitle_voiceover = stage0_child_contracts.get("subtitle_voiceover") or {}
            effect_policy = stage0_child_contracts.get("effect") or {}
            if soundtrack:
                audio["soundtrack_role"] = soundtrack.get("music_role") or "unspecified"
                audio["soundtrack_energy_intent"] = soundtrack.get("energy_intent") or "unspecified"
            if subtitle_voiceover:
                if subtitle_voiceover.get("subtitle_required") and "text_layer" not in seg:
                    seg["text_layer"] = {}
                if subtitle_voiceover.get("subtitle_required"):
                    seg["text_layer"]["subtitle"] = seg["text_layer"].get("subtitle") or "required"
                    seg["text_layer"]["language"] = subtitle_voiceover.get("language") or "unknown"
                    seg["text_layer"].setdefault("reason", "Stage 0 requested subtitles; BUILD must create readable subtitle evidence.")
                if subtitle_voiceover.get("voiceover_required"):
                    audio["voiceover_policy"] = "required"
                    audio["voiceover_language"] = subtitle_voiceover.get("language") or "unknown"
            if effect_policy:
                seg["effect_policy"] = effect_policy

        # explicit material_treatment for enumeration/process (carry items/steps)
        if cp == "enumeration" and d.get("items"):
            seg["material_treatment"] = {
                "treatment": "photo_stack_beat",
                "items": d["items"],
                "label_per_item": bool(d.get("label_per_item", True)),
            }
        elif cp == "process" and (d.get("steps") or d.get("items")):
            seg["material_treatment"] = {
                "treatment": "stepped_sequence",
                "steps": d.get("steps") or d.get("items"),
            }
        elif cp == "action" and (d.get("steps") or d.get("items")):
            seg["material_treatment"] = {
                "treatment": "stepped_sequence",
                "steps": d.get("steps") or d.get("items"),
            }

        if d.get("effects_required"):
            seg["effects_required"] = list(d["effects_required"])
        if cp in _HONESTY_PATTERNS:
            seg["_honesty"] = "real_material_only"  # trace; engine enforces regardless
        if director_intent:
            seg["director_intent"] = director_intent

        segments.append(seg)

    contract: dict[str, Any] = {
        "brief_ref": brief_ref,
        "categories_ref": categories_ref,
        "style": "mv",
        "segments": segments,
    }
    if music:
        contract["music"] = music
    if story_soul:
        contract["story_soul"] = story_soul
    if stage0_child_contracts:
        contract["stage0_child_contracts"] = stage0_child_contracts
    return contract
