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
    n = len(beats)
    segments: list[dict] = []

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

        material_fit: dict[str, Any] = {
            "category": d.get("category") or "daily_life",
            "visual_desc": d.get("visual_desc") or summary,
            "reason": d.get("reason") or f"實現 {beat_role} beat：{summary}"[:60],
        }
        if d.get("material_hint"):
            material_fit["material_hint"] = d["material_hint"]
        if d.get("must_include"):
            material_fit["must_include"] = d["must_include"]
            material_fit["collection_instructions"] = (
                d.get("collection_instructions") or f"需收集本人原素材：{d['must_include']}（不可替代）")

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

        if d.get("effects_required"):
            seg["effects_required"] = list(d["effects_required"])
        if cp in _HONESTY_PATTERNS:
            seg["_honesty"] = "real_material_only"  # trace; engine enforces regardless

        segments.append(seg)

    contract: dict[str, Any] = {
        "brief_ref": brief_ref,
        "categories_ref": categories_ref,
        "style": "mv",
        "segments": segments,
    }
    if music:
        contract["music"] = music
    return contract
