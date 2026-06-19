"""contract_adapter.py — canonical-first runtime adapter(see roadmap.md).

公開 SPEC 輸入 = `segment_contract.json`(core+facets,normalized JSON)。本檔把它
**validate → 轉成現有出片鏈吃的 flat MV script(execution payload)**,再交給
mv_cut.mv_chain/run_mv 執行。**不改 run chain**;legacy flat script 只是「生成的執行載荷」,
不是 SPEC。每段帶 `_from_contract` trace,保持可追溯。

流程:
  segment_contract.json → validate_segment_contract → contract_to_mv_script(adapter)
  → mv_cut.mv_chain(既有鏈執行)
"""
import argparse
import hashlib
import json
import os
from pathlib import Path

from . import spec_contract


def _seg_weight(core, eg):
    """從 editing_grammar / section_role 推 pacing weight(對應 allocate_segments)。
    hero/locked/high → 重;opening/closing → 偏重;filler/expendable → 輕。"""
    role = (eg or {}).get("role")
    prio = (eg or {}).get("priority")
    comp = (eg or {}).get("compressibility")
    sect = (core or {}).get("section_role")
    if role in ("hero", "proof") or comp == "locked" or prio == "high":
        return 1.6
    if sect in ("opening", "closing"):
        return 1.3
    if role == "filler" or comp == "expendable" or prio == "low":
        return 0.7
    return 1.0


def contract_to_mv_script(contract):
    """純函式:segment_contract(core+facets normalized JSON)→ 現有鏈吃的 flat MV script。
    映射規則(SPEC→execution),不創造新意圖,只翻譯。回 flat script dict。"""
    segs_in = contract.get("segments", []) if isinstance(contract, dict) else (contract or [])
    out_segs = []
    for i, seg in enumerate(segs_in):
        core = seg.get("core") or {}
        mat = seg.get("material_fit") or {}
        aud = seg.get("audio") or {}
        vis = seg.get("visual_style") or {}
        eg = seg.get("editing_grammar") or {}
        txt = seg.get("text_layer")

        section = core.get("section_role")
        layout = vis.get("layout")
        pace_in = vis.get("pace")
        role_arole = aud.get("role")

        flat = {
            "segment": seg.get("segment", i + 1),
            "_from_contract": seg.get("segment", core.get("section_role") or i + 1),  # trace
            "visual_desc": mat.get("visual_desc", ""),
            "needs_review": bool(core.get("review_required")),
            "weight": _seg_weight(core, eg),
        }
        if seg.get("source"):
            flat["source"] = seg["source"]
        if seg.get("file"):
            flat["file"] = seg["file"]
        # kind:只對 mv_cut 特殊處理的 bookend/title 設;montage 交給 layout/pace
        if section in ("opening", "closing", "title"):
            flat["kind"] = section
        # WHY/treatment passthrough(opt-in):把 content_pattern / 顯式 treatment /
        # section_role 帶到 BUILD,讓 Node 9 能解析素材處理文法。無宣告則完全不帶。
        if seg.get("editing_intent"):
            flat["editing_intent"] = seg["editing_intent"]
        if seg.get("material_treatment"):
            flat["material_treatment"] = seg["material_treatment"]
        if seg.get("sequence_grammar"):
            flat["sequence_grammar"] = seg["sequence_grammar"]
        if seg.get("pacing"):
            flat["pacing"] = seg["pacing"]
        if seg.get("requested_duration_sec") is not None:
            flat["requested_duration_sec"] = seg["requested_duration_sec"]
        if seg.get("still_image_policy"):
            flat["still_image_policy"] = seg["still_image_policy"]
        if seg.get("creative_exception"):
            flat["creative_exception"] = seg["creative_exception"]
        if section:
            flat["section_role"] = section
        # 來源 / 媒材
        if seg.get("source"):
            flat["source"] = seg["source"]
        if mat.get("material_hint"):
            flat["material_hint"] = mat["material_hint"]
        if mat.get("search_query"):
            flat["search_query"] = mat["search_query"]
        if mat.get("must_include"):
            flat["must_include"] = mat["must_include"]
        if mat.get("media"):
            flat["media"] = mat["media"]
        # layout:MV 只認 montage/collage/framed;single 等 → 省略
        if layout in ("montage", "collage", "framed"):
            flat["layout"] = layout
        # pace:MV 只認 fast/hold
        flat["pace"] = "fast" if (pace_in == "fast" or layout == "montage") else "hold"
        if flat["pace"] == "hold":
            flat["hold"] = True
        # 音訊
        if role_arole:
            flat["audio_role"] = role_arole
        if role_arole in ("duck", "diegetic", "source_speech"):
            flat["keep_audio"] = True
        # 文字層(text_layer == "none" → 不上字)
        if isinstance(txt, dict):
            for k in ("label", "narrative", "subtitle", "name_super"):
                if txt.get(k):
                    flat[k] = txt[k]
            flat["text"] = txt.get("narrative") or txt.get("subtitle") or ""
        else:
            flat["text"] = ""
        flat["raw_audio"] = aud
        flat["raw_visual_style"] = vis
        flat["raw_text_layer"] = txt
        flat["material_fit"] = mat
        flat["editing_grammar"] = eg
        if eg.get("beat_alignment"):
            flat["beat_alignment"] = eg["beat_alignment"]
        flat["visual_style"] = vis
        flat["text_layer"] = txt
        out_segs.append(flat)

    script = {"style": contract.get("style", "mv") if isinstance(contract, dict) else "mv",
              "segments": out_segs}
    if isinstance(contract, dict) and contract.get("music"):
        script["music"] = contract["music"]
    return script


def _narration_text(seg, audio, text_layer, core):
    narration = seg.get("narration")
    if isinstance(narration, str):
        return narration
    if isinstance(narration, dict):
        for key in ("text", "script", "narrative"):
            if narration.get(key):
                return narration[key]
    for key in ("narration", "voiceover_text", "text"):
        if audio.get(key):
            return audio[key]
    if isinstance(text_layer, dict):
        for key in ("narrative", "label"):
            if text_layer.get(key):
                return text_layer[key]
    return core.get("story_purpose", "")


def contract_to_narrative_script(contract):
    """Adapt a canonical contract to the flat payload consumed by video_pipeline.py."""
    segs_in = contract.get("segments", []) if isinstance(contract, dict) else (contract or [])
    out_segs = []
    for i, seg in enumerate(segs_in):
        core = seg.get("core") or {}
        mat = seg.get("material_fit") or {}
        audio = seg.get("audio") or {}
        visual = seg.get("visual_style") or {}
        text_layer = seg.get("text_layer")
        narration = seg.get("narration")
        source = seg.get("source")

        media_pref = mat.get("media")
        if media_pref not in ("photo", "video"):
            media_pref = "video" if source == "local" else "photo"

        title = core.get("section_role") or f"Segment {i + 1}"
        if isinstance(text_layer, dict):
            title = text_layer.get("label") or title

        effects = {}
        transition = visual.get("transition")
        grade = visual.get("color_grade") or visual.get("grade")
        if transition:
            effects["transition"] = transition
        if grade:
            effects["grade"] = grade
        for key in ("kenburns", "transition_duration", "title_card", "collage_n", "montage_n"):
            if visual.get(key) is not None:
                effects[key] = visual[key]

        flat = {
            "segment": seg.get("segment", i + 1),
            "_from_contract": seg.get("segment", core.get("section_role") or i + 1),
            "title": title,
            "text": _narration_text(seg, audio, text_layer, core),
            "visual_desc": mat.get("visual_desc", ""),
            "search_query": mat.get("search_query") or mat.get("material_hint") or mat.get("visual_desc", ""),
            "media_pref": media_pref,
            "style": "narrative",
            "raw_narration": narration,
            "raw_audio": audio,
            "raw_visual_style": visual,
            "raw_text_layer": text_layer,
            "material_fit": mat,
            "visual_style": visual,
            "text_layer": text_layer,
        }
        if effects:
            flat["effects"] = effects
        for key in ("source", "file", "material_hint", "must_include"):
            value = seg.get(key) if key in ("source", "file") else mat.get(key)
            if value:
                flat[key] = value
        out_segs.append(flat)

    script = {"style": "narrative", "segments": out_segs}
    if isinstance(contract, dict):
        if contract.get("bgm"):
            script["bgm"] = contract["bgm"]
        elif contract.get("music"):
            script["bgm"] = contract["music"]
    return script


def _read_contract(contract):
    if isinstance(contract, (str, os.PathLike)):
        path = Path(contract)
        with path.open(encoding="utf-8") as f:
            return json.load(f), str(path), _hash_file(path)
    return contract, None, _hash_json(contract)


def _hash_file(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return "sha256:" + h.hexdigest()


def _hash_json(data):
    raw = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def _load_category_ids(categories_path):
    if not categories_path:
        return None
    return set(spec_contract.load_material_categories(categories_path))


def _with_payload_metadata(script, *, generated_from, contract_hash):
    out = dict(script)
    out["_artifact_role"] = "legacy_runtime_payload"
    out["_generated_from"] = generated_from
    out["_contract_hash"] = contract_hash
    out["_adapter"] = "contract_adapter.py"
    return out


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _apply_stock_first_if_enabled(contract):
    if not isinstance(contract, dict):
        return contract, None
    cfg = contract.get("run_config") or {}
    if contract.get("material_source_mode") != "stock_first" and cfg.get("material_source_mode") != "stock_first":
        return contract, None
    from . import stock_first  # noqa: PLC0415
    routed = stock_first.apply_stock_first_route(contract)
    return routed, routed.get("stock_first_route")


def adapt_contract_file(contract_path, *, out_path=None, categories_path=None):
    """Validate canonical contract and optionally write traceable generated MV payload."""
    contract, source, contract_hash = _read_contract(contract_path)
    v = spec_contract.validate_segment_contract(contract, categories=_load_category_ids(categories_path))
    if not v["ok"]:
        return {"ok": False, "errors": v["errors"], "warnings": v["warnings"],
                "stage": "validate_contract", "contract_hash": contract_hash}
    contract, _stock_route = _apply_stock_first_if_enabled(contract)
    script = contract_to_mv_script(contract)
    payload = _with_payload_metadata(script, generated_from=source, contract_hash=contract_hash)

    from . import mv_cut  # noqa: PLC0415 — lazy(避免非執行情境載入 librosa)
    mvv = mv_cut.validate_mv_script(payload)
    if not mvv.get("can_run", True):
        return {"ok": False, "errors": mvv.get("issues"), "warnings": v["warnings"],
                "stage": "validate_mv_script", "contract_hash": contract_hash,
                "generated_script": payload}

    result = {"ok": True, "errors": [], "warnings": v["warnings"], "stage": "adapt",
              "contract_hash": contract_hash, "generated_script": payload}
    if out_path:
        result["generated_payload"] = str(_write_json(out_path, payload))
    return result


def adapt_narrative_contract_file(contract_path, *, out_path=None, categories_path=None):
    """Validate canonical contract and optionally write a traceable narrative payload."""
    contract, source, contract_hash = _read_contract(contract_path)
    validation = spec_contract.validate_segment_contract(
        contract, categories=_load_category_ids(categories_path)
    )
    if not validation["ok"]:
        return {
            "ok": False,
            "errors": validation["errors"],
            "warnings": validation["warnings"],
            "stage": "validate_contract",
            "contract_hash": contract_hash,
        }

    contract, _stock_route = _apply_stock_first_if_enabled(contract)
    script = contract_to_narrative_script(contract)
    payload = _with_payload_metadata(script, generated_from=source, contract_hash=contract_hash)
    result = {
        "ok": True,
        "errors": [],
        "warnings": validation["warnings"],
        "stage": "adapt",
        "contract_hash": contract_hash,
        "generated_script": payload,
    }
    if out_path:
        result["generated_payload"] = str(_write_json(out_path, payload))
    return result


def _manifest(*, canonical_contract, contract_hash, generated_payload, material_db,
              music, music_structure, model_routes, build_profile,
              stock_first_route, generated_asset_requests,
              generated_asset_manifest=None,
              light_effects_plan=None,
              light_effects_manifest=None,
              light_effects_baseline_review=None,
              motion_graphics_contract=None,
              motion_graphics_render_plan=None,
              motion_graphics_manifest=None,
              assembly_plan, timeline_build,
              editor_review, final, state, verify_result=None,
              revision_plan=None, brief=None,
              timeline_invariants=None, broll_audit=None, caption_audit=None,
              keyframe_grid=None, visual_audit=None, verify_evidence_bundle=None,
              presentation_feel_audit=None,
              creator_profile=None, creator_profile_applied=None,
              capcut_draft_manifest=None, capcut_export_manifest=None,
              editorial_design=None, editorial_qa=None, spec_review=None):
    return {
        "artifact_role": "artifact_manifest",
        "artifact_manifest_version": 1,
        "canonical_contract": canonical_contract,
        "contract_hash": contract_hash,
        "brief": str(brief) if brief else None,
        "generated_payload": generated_payload,
        "material_db": str(material_db) if material_db is not None else None,
        "music": str(music) if music is not None else None,
        "music_structure": str(music_structure) if music_structure else None,
        "model_routes": str(model_routes) if model_routes else None,
        "build_profile": str(build_profile) if build_profile else None,
        "stock_first_route": str(stock_first_route) if stock_first_route else None,
        "generated_asset_requests": str(generated_asset_requests) if generated_asset_requests else None,
        "generated_asset_manifest": str(generated_asset_manifest) if generated_asset_manifest else None,
        "light_effects_plan": str(light_effects_plan) if light_effects_plan else None,
        "light_effects_manifest": str(light_effects_manifest) if light_effects_manifest else None,
        "light_effects_baseline_review": str(light_effects_baseline_review) if light_effects_baseline_review else None,
        "motion_graphics_contract": str(motion_graphics_contract) if motion_graphics_contract else None,
        "motion_graphics_render_plan": str(motion_graphics_render_plan) if motion_graphics_render_plan else None,
        "motion_graphics_manifest": str(motion_graphics_manifest) if motion_graphics_manifest else None,
        "assembly_plan": str(assembly_plan) if assembly_plan else None,
        "timeline_build": str(timeline_build) if timeline_build else None,
        "editor_review": str(editor_review) if editor_review else None,
        "final": str(final),
        "state": str(state),
        "verify_result": str(verify_result) if verify_result else None,
        "revision_plan": str(revision_plan) if revision_plan else None,
        "timeline_invariants": str(timeline_invariants) if timeline_invariants else None,
        "broll_audit": str(broll_audit) if broll_audit else None,
        "caption_audit": str(caption_audit) if caption_audit else None,
        "keyframe_grid": str(keyframe_grid) if keyframe_grid else None,
        "visual_audit": str(visual_audit) if visual_audit else None,
        "verify_evidence_bundle": str(verify_evidence_bundle) if verify_evidence_bundle else None,
        "presentation_feel_audit": str(presentation_feel_audit) if presentation_feel_audit else None,
        "creator_profile": str(creator_profile) if creator_profile else None,
        "creator_profile_applied": str(creator_profile_applied) if creator_profile_applied else None,
        "capcut_draft_manifest": str(capcut_draft_manifest) if capcut_draft_manifest else None,
        "capcut_export_manifest": str(capcut_export_manifest) if capcut_export_manifest else None,
        "editorial_design": str(editorial_design) if editorial_design else None,
        "editorial_qa": str(editorial_qa) if editorial_qa else None,
        "spec_review": str(spec_review) if spec_review else None,
    }


def _write_p1_audits(out_dir, build_profile_payload, *, timeline_build_path=None,
                     srt_path=None, final_video=None, contract_obj=None, verbose=True):
    """Generate enabled P1 verification artifacts after build/render.

    Gated entirely by ``build_profile.verification_tools`` (default all OFF), so a
    standard run produces nothing here and behaves exactly as before. Returns a
    dict of {artifact_role: path} for the artifacts actually written.
    """
    from . import build_profile as _bp  # noqa: PLC0415
    tools = _bp.verification_tools(build_profile_payload)
    if not any(tools.values()):
        return {}

    out_dir = Path(out_dir)
    written = {}

    timeline = None
    if timeline_build_path and Path(timeline_build_path).exists():
        try:
            with open(timeline_build_path, encoding="utf-8") as f:
                timeline = json.load(f)
        except Exception:
            timeline = None

    segments = []
    if isinstance(contract_obj, dict):
        segments = contract_obj.get("segments") or []
    elif isinstance(contract_obj, list):
        segments = contract_obj
    must_include = [s.get("segment") for s in segments
                    if isinstance(s, dict) and s.get("must_include")]

    if tools["timeline_invariants"] and timeline is not None:
        from . import timeline_invariants  # noqa: PLC0415
        p = out_dir / "timeline_invariants.json"
        timeline_invariants.write_timeline_invariants(
            timeline, p, must_include_segments=must_include or None)
        written["timeline_invariants"] = str(p)

    if tools["broll_audit"] and timeline is not None:
        from . import broll_audit  # noqa: PLC0415
        policy = build_profile_payload.get("broll_policy") or {}
        p = out_dir / "broll_audit.json"
        broll_audit.write_broll_audit(
            timeline, p,
            target_ratio=policy.get("target_ratio"),
            max_source_repeats=policy.get("max_source_repeats"))
        written["broll_audit"] = str(p)

    if tools["caption_audit"] and srt_path and Path(srt_path).exists():
        from . import caption_audit  # noqa: PLC0415
        try:
            events = caption_audit.parse_srt(Path(srt_path).read_text(encoding="utf-8"))
            p = out_dir / "caption_audit.json"
            caption_audit.write_caption_audit(events, p)
            written["caption_audit"] = str(p)
        except Exception as e:
            if verbose:
                print(f"[audit] caption_audit skipped: {e}")

    if tools["presentation_feel_audit"] and timeline is not None:
        assembly_path = out_dir / "assembly_plan.json"
        if assembly_path.exists():
            try:
                from . import presentation_feel_audit  # noqa: PLC0415
                with assembly_path.open(encoding="utf-8") as f:
                    assembly = json.load(f)
                p = out_dir / "presentation_feel_audit.json"
                presentation_feel_audit.write_presentation_feel_audit(
                    assembly,
                    timeline,
                    p,
                    editing_policy=build_profile_payload.get("editing_policy"),
                )
                written["presentation_feel_audit"] = str(p)
            except Exception as e:
                if verbose:
                    print(f"[audit] presentation_feel_audit skipped: {e}")

    if (tools["keyframe_grid"] or tools["visual_audit"]) and final_video and Path(final_video).exists():
        from . import keyframe_grid as _kg  # noqa: PLC0415
        kg_policy = build_profile_payload.get("keyframe_grid") or {}
        grid_path = out_dir / "keyframe_grid.jpg"
        try:
            meta = _kg.generate_keyframe_grid(
                str(final_video), str(grid_path),
                sample_count=kg_policy.get("sample_count", 12),
                columns=kg_policy.get("columns", 4))
            if tools["keyframe_grid"] and meta.get("sample_count", 0) > 0:
                written["keyframe_grid"] = str(grid_path)
            if tools["visual_audit"]:
                from . import visual_audit  # noqa: PLC0415
                p = out_dir / "visual_audit.json"
                visual_audit.write_visual_audit(meta, p)
                written["visual_audit"] = str(p)
        except Exception as e:
            if verbose:
                print(f"[audit] keyframe_grid/visual_audit skipped: {e}")

    if tools["verify_evidence"] and timeline is not None and final_video and Path(final_video).exists():
        try:
            from . import verify_evidence  # noqa: PLC0415
            evidence_dir = out_dir / "verify_evidence"
            verify_evidence.write_verify_evidence(final_video, timeline, evidence_dir)
            written["verify_evidence_bundle"] = str(
                evidence_dir / "verify_evidence_bundle.json")
        except Exception as e:
            if verbose:
                print(f"[audit] verify_evidence skipped: {e}")

    return written


def _timeline_caption_entries(clips):
    """Return reading-track captions from timeline clips.

    Labels and name supers are visual decoration, so they must not leak into the
    generated SRT or caption audit.
    """
    entries = []
    for clip in clips or []:
        text_overlay = clip.get("text_overlay")
        if isinstance(text_overlay, dict):
            text = (text_overlay.get("narrative") or text_overlay.get("subtitle") or "").strip()
        elif isinstance(text_overlay, str) and text_overlay.strip().lower() != "none":
            text = text_overlay.strip()
        else:
            text = ""
        if not text:
            continue
        t_in = clip.get("timeline_in_sec", 0.0)
        t_out = clip.get("timeline_out_sec", 0.0)
        if entries and entries[-1]["text"] == text:
            entries[-1]["t_out"] = max(entries[-1]["t_out"], t_out)
        else:
            entries.append({"t_in": t_in, "t_out": t_out, "text": text})
    return entries


def _attach_attention_budgets(payload, *, music_structure=None, editing_policy=None):
    """Attach Node 9 attention budgets to the flat runtime payload in place."""
    from . import edit_artifacts  # noqa: PLC0415

    assembly = edit_artifacts.build_assembly_plan(
        payload,
        music_structure=music_structure,
        editing_policy=editing_policy,
    )
    budgets = {
        segment.get("segment"): segment.get("attention_budget")
        for segment in assembly.get("segments") or []
        if segment.get("segment") is not None and segment.get("attention_budget")
    }
    anti_plans = {
        segment.get("segment"): segment.get("anti_presentation_plan")
        for segment in assembly.get("segments") or []
        if segment.get("segment") is not None and segment.get("anti_presentation_plan")
    }
    for segment in payload.get("segments") or []:
        budget = budgets.get(segment.get("segment"))
        if budget:
            segment["attention_budget"] = budget
        anti_plan = anti_plans.get(segment.get("segment"))
        if anti_plan:
            segment["anti_presentation_plan"] = anti_plan
            if anti_plan.get("text_placement"):
                segment["text_placement"] = anti_plan["text_placement"]
    return payload


def _apply_creator_profile(out_dir, creator_profile_path, brief_dict, build_profile_payload, verbose=True):
    """Apply creator-profile defaults (P2) and record what was applied.

    brief always overrides creator defaults. Creator editing defaults fill build
    profile policy only where it left them null. Writes creator_profile.json (copy)
    and creator_profile_applied.json. Returns {creator_profile, creator_profile_applied}.
    """
    from . import creator_profile as _cp  # noqa: PLC0415
    profile = _cp.load_creator_profile(creator_profile_path)
    resolved = _cp.resolve_defaults(profile, brief_dict or {})

    # Fill build_profile broll policy nulls from resolved editing defaults.
    policy = build_profile_payload.setdefault("broll_policy", {"target_ratio": None, "max_source_repeats": None})
    if policy.get("target_ratio") is None and resolved["resolved"].get("broll_ratio_target") is not None:
        policy["target_ratio"] = resolved["resolved"]["broll_ratio_target"]
    if policy.get("max_source_repeats") is None and resolved["resolved"].get("max_source_repeats") is not None:
        policy["max_source_repeats"] = resolved["resolved"]["max_source_repeats"]

    out_dir = Path(out_dir)
    cp_path = out_dir / "creator_profile.json"
    _cp.write_creator_profile(cp_path, profile)
    applied_path = out_dir / "creator_profile_applied.json"
    _write_json(applied_path, {
        "artifact_role": "creator_profile_applied",
        "version": 1,
        "resolved": resolved["resolved"],
        "sources": resolved["sources"],
        "applied": resolved["applied"],
    })
    if verbose:
        print(f"[creator_profile] applied defaults: {resolved['applied']}")
    return {"creator_profile": str(cp_path), "creator_profile_applied": str(applied_path)}


def _resolve_declared_ref(ref, source):
    """STRICT resolution of a declared ref (material_needs_ref / revision_decisions_ref).
    Returns (path, error): an absolute ref resolves to itself; a relative ref
    resolves ONLY against the contract file's directory — never the process cwd
    or examples/. A relative ref with no file-based contract (inline dict, no
    `source`) is an explicit error rather than a cwd guess. Missing → fail-closed."""
    path = Path(ref)
    if path.is_absolute():
        return (path, None) if path.exists() else (None, f"declared ref not found: {ref}")
    if not source:
        return None, (f"relative ref {ref!r} cannot be resolved: the contract was provided "
                      f"inline with no base directory — pass a file-based contract or an "
                      f"absolute ref (refusing to guess the process cwd)")
    candidate = Path(source).parent / ref
    if candidate.exists():
        return candidate, None
    return None, f"declared ref {ref!r} not found next to the contract: {candidate}"


def _load_material_db_strict(material_db):
    """Strict materials_db.json load — delegates to the single canonical loader
    (project_material_map.load_material_db) so there is ONE rule."""
    from .project_material_map import load_material_db  # noqa: PLC0415
    return load_material_db(material_db)


def _quarantine_stale_final(out_path):
    """When the gate blocks and a previous build's final exists at out_path, move
    it aside so it can't masquerade as this run's output. NEVER deletes or
    overwrites an already-quarantined stale final: it picks the first unused,
    deterministic name (`stale_previous_final.mp4`, then `_2`, `_3`, ...).
    Returns (stale_path | None, error | None). On a move/rename failure the path
    is None and an error string is returned so the caller can keep the block and
    must NOT claim the canonical final was cleared."""
    out_path = Path(out_path)
    if not out_path.exists():
        return None, None
    parent = out_path.parent
    candidate = parent / "stale_previous_final.mp4"
    index = 2
    while candidate.exists():                 # never clobber a prior quarantine
        candidate = parent / f"stale_previous_final_{index}.mp4"
        index += 1
    try:
        out_path.replace(candidate)           # atomic move of the OLD final
        return str(candidate), None
    except OSError as exc:
        return None, f"failed to quarantine previous final {out_path}: {exc}"


def _load_current_material_maps(material_db_payload, db_dir):
    """Per-asset maps from a db payload — delegates to the single canonical loader
    (project_material_map.material_maps_from_db_payload): relative `material_map`
    resolves against db_dir (never cwd), declared-but-bad maps are fail-closed,
    absent keys skipped, loaded maps canonically normalized. One rule."""
    from .project_material_map import material_maps_from_db_payload  # noqa: PLC0415
    return material_maps_from_db_payload(material_db_payload, db_dir)


def _resolve_material_inputs(contract_obj, source, material_db, material_db_payload):
    """Resolve the CURRENT material_needs + per-asset maps for a contract that
    declares `material_needs_ref`. Returns (needs, maps, error). `error` is set
    (fail-closed) when the ref is malformed / missing / unparseable or a declared
    map is missing/corrupt. needs is None with error=None only when the contract
    does not declare material_needs_ref at all (caller decides skip)."""
    if "material_needs_ref" not in contract_obj:
        return None, None, None
    needs_ref = contract_obj.get("material_needs_ref")
    if not isinstance(needs_ref, str) or not needs_ref.strip():
        return None, None, f"material_needs_ref must be a non-empty string, got {needs_ref!r}"
    needs_file, ref_error = _resolve_declared_ref(needs_ref.strip(), source)
    if ref_error:
        return None, None, ref_error
    try:
        with needs_file.open(encoding="utf-8-sig") as handle:
            needs = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, None, f"material_needs could not be parsed ({needs_file}): {exc}"
    db_dir = Path(material_db).parent if material_db else Path(".")
    maps, map_error = _load_current_material_maps(material_db_payload, db_dir)
    if map_error:
        return None, None, map_error
    return needs, maps, None


def _resolve_effect_intent_plan(contract_obj, source):
    """Resolve optional FX1 neutral effect intent plan for effects-enabled builds.

    The ref is intentionally opt-in. When declared and the caller asks for an
    effects build, it must resolve and validate cleanly; otherwise BUILD stops
    before render instead of silently dropping requested effects.
    """
    if "effect_intent_plan_ref" not in contract_obj:
        return None, None
    ref = contract_obj.get("effect_intent_plan_ref")
    if not isinstance(ref, str) or not ref.strip():
        return None, f"effect_intent_plan_ref must be a non-empty string, got {ref!r}"
    effect_file, ref_error = _resolve_declared_ref(ref.strip(), source)
    if ref_error:
        return None, ref_error
    try:
        with effect_file.open(encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except (OSError, ValueError) as exc:
        return None, f"effect_intent_plan could not be parsed ({effect_file}): {exc}"
    try:
        from .effect_contract import validate_effect_intent_plan  # noqa: PLC0415
        validate_effect_intent_plan(payload)
    except ValueError as exc:
        return None, f"effect_intent_plan invalid ({effect_file}): {exc}"
    return payload, None


def _run_material_delta_gate(contract_obj, source, out_dir, material_db, material_db_payload,
                             *, waivers=None):
    """M6b pre-BUILD gate. Runs ONLY when the project explicitly declares the
    `material_needs_ref` key (existing-material-first projects omit it → skip,
    backward compatible). A declared-but-malformed ref is fail-closed, never a
    crash. The verdict is computed FRESH from the current needs + current
    per-asset maps via material_delta.material_delta_gate (never a stale
    material_delta.json), honoring any canonical `waivers`. Returns the gate
    verdict, or None to skip."""
    from . import material_delta as _md  # noqa: PLC0415
    delta_path = Path(out_dir) / "material_delta.json"
    needs, maps, error = _resolve_material_inputs(
        contract_obj, source, material_db, material_db_payload)
    if needs is None and error is None:
        return None
    if error:
        return _md.material_delta_gate(
            None, None, material_delta_path=str(delta_path), resolution_error=error)
    gate = _md.material_delta_gate(needs, maps, waivers=waivers,
                                   material_delta_path=str(delta_path))
    if gate.get("delta") is not None:   # write fresh evidence (never trust stale)
        _write_json(delta_path, gate["delta"])
    return gate


def _run_material_revision(contract_obj, source, out_dir, material_db, *, categories=None):
    """M6c runtime plumbing. Runs ONLY when the contract declares the
    `revision_decisions_ref` key (omit → skip, backward compatible). Strictly
    loads the current material_db, computes a FRESH material_delta from current
    needs+maps, applies ONLY accepted decisions via the single
    material_revision.apply_revisions, writes revised_segment_contract.json +
    material_revision.json atomically, and re-runs gate_from_delta with the
    canonical waivers. Trusts no stale artifact.

    Returns a dict: {status: skip|applied|block, revised, waivers, reason,
    next_action, material_revision (path), revised_contract (path), errors}."""
    from . import material_delta as _md  # noqa: PLC0415
    from . import material_revision as _mr  # noqa: PLC0415

    if "revision_decisions_ref" not in contract_obj:
        return {"status": "skip"}
    out_dir = Path(out_dir)
    revised_path = out_dir / "revised_segment_contract.json"
    revision_path = out_dir / "material_revision.json"

    def block(reason, next_action="revise:material(material_revision)", errors=None):
        return {"status": "block", "revised": None, "waivers": [], "reason": reason,
                "next_action": next_action, "errors": errors or [reason],
                "material_revision": None, "revised_contract": None}

    ref = contract_obj.get("revision_decisions_ref")
    if not isinstance(ref, str) or not ref.strip():
        return block(f"revision_decisions_ref must be a non-empty string, got {ref!r}")
    decisions_file, ref_error = _resolve_declared_ref(ref.strip(), source)
    if ref_error:
        return block(ref_error)
    try:
        with decisions_file.open(encoding="utf-8-sig") as handle:
            decisions = json.load(handle)
    except (OSError, ValueError) as exc:
        return block(f"revision_decisions could not be parsed ({decisions_file}): {exc}")

    # the material_db must load cleanly before a revision; a corrupt/invalid DB is
    # fail-closed, never silently treated as zero material.
    material_db_payload, db_error = _load_material_db_strict(material_db)
    if db_error:
        return block(db_error, next_action="revise:material(material_delta)")

    # a revision is defined against a material_delta, which needs canonical needs
    needs, maps, error = _resolve_material_inputs(
        contract_obj, source, material_db, material_db_payload)
    if error:
        return block(error, next_action="revise:material(material_delta)")
    if needs is None:
        return block("revision_decisions_ref declared but the contract declares no "
                     "material_needs_ref (a revision needs a delta to act on)",
                     next_action="revise:material(material_delta)")

    fresh_delta = _md.compute_material_delta(needs, maps)   # never trust a stale delta
    report, revised = _mr.apply_revisions(contract_obj, fresh_delta, decisions,
                                          categories=categories)
    if not report["ok"]:
        return block("revision engine rejected the decisions: "
                     + "; ".join(report["errors"]), errors=report["errors"])

    # re-run the SAME gate the BUILD gate uses, with the canonical waivers
    gate = _md.gate_from_delta(fresh_delta, waivers=report["waivers"])
    if (gate["status"] == "pass") != bool(report["ready_for_build"]):
        return block("revision/gate disagreement: report.ready_for_build="
                     f"{report['ready_for_build']} but gate.status={gate['status']}")

    # write evidence atomically (revised contract is a NEW file; source untouched)
    try:
        _mr.write_revision_artifacts(revised, report, revised_path, revision_path)
    except (ValueError, OSError, RuntimeError) as exc:
        return block(f"could not write revision artifacts: {exc}")

    if not report["ready_for_build"] or report["next_action"] is not None:
        # pending await (collect/reshoot/review) or unresolved tier-1 -> stop
        return {"status": "block", "revised": None, "waivers": report["waivers"],
                "reason": f"revision applied but build is not ready "
                          f"(next_action={report['next_action']})",
                "next_action": report["next_action"] or "await_material",
                "errors": [], "material_revision": str(revision_path),
                "revised_contract": str(revised_path)}
    return {"status": "applied", "revised": revised, "waivers": report["waivers"],
            "reason": "accepted revision decisions applied; gate passes",
            "next_action": None, "errors": [],
            "material_revision": str(revision_path),
            "revised_contract": str(revised_path)}


def run_contract(contract, material_db, out_path, music_path=None, mat_dir=None, verbose=True,
                 categories_path=None, generated_payload_path=None, manifest_path=None,
                 music_structure_path=None, every_n_beats=4, model_routes_path=None,
                 model_routes_config_path=None, build_profile_path=None,
                 build_profile_config_path=None, generated_asset_requests_path=None,
                 creator_profile_path=None, skip_render=False, enforce_supply_gate=False):
    """(I/O) canonical-first 入口:驗 contract → 轉 flat → 既有 mv_chain 執行。
    contract 可為 dict 或 .json 路徑。回 {ok, errors, result?}。**不改 run chain**。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if mat_dir is None:
        from .platform_tools import resolve_temp_dir
        mat_dir = resolve_temp_dir()
    generated_payload_path = Path(generated_payload_path) if generated_payload_path else out_path.parent / "generated_mv_script.json"
    manifest_path = Path(manifest_path) if manifest_path else out_path.parent / "artifact_manifest.json"
    music_structure_path = Path(music_structure_path) if music_structure_path else out_path.parent / "music_structure.json"
    model_routes_path = Path(model_routes_path) if model_routes_path else out_path.parent / "model_routes.json"
    build_profile_path = Path(build_profile_path) if build_profile_path else out_path.parent / "build_profile.json"
    generated_asset_requests_path = (
        Path(generated_asset_requests_path)
        if generated_asset_requests_path else out_path.parent / "generated_asset_requests.json"
    )
    stock_first_route_path = out_path.parent / "stock_first_route.json"

    contract_obj, source, contract_hash = _read_contract(contract)
    v = spec_contract.validate_segment_contract(contract_obj, categories=_load_category_ids(categories_path))
    if not v["ok"]:
        return {"ok": False, "errors": v["errors"], "warnings": v["warnings"],
                "stage": "validate_contract", "contract_hash": contract_hash}

    # M6c runtime plumbing: when the contract declares accepted revision decisions,
    # transform it BEFORE script generation so the whole downstream pipeline
    # (script, supply, spec_review, M6b gate, render) uses the revised contract.
    # Computed fresh from current needs+maps; the original input file is never
    # written. A blocked revision stops before any render (stale final quarantined).
    revision_waivers = None
    if "revision_decisions_ref" in contract_obj:
        revision = _run_material_revision(
            contract_obj, source, out_path.parent, material_db,
            categories=_load_category_ids(categories_path))
        if revision["status"] == "block":
            stale_final_path, quarantine_error = _quarantine_stale_final(out_path)
            canonical_final_cleared = quarantine_error is None and stale_final_path is not None
            _write_json(out_path.parent / "state.json", {
                "pass": False, "final": None, "next_action": revision["next_action"],
                "blocking": revision.get("errors") or [revision["reason"]],
                "material_revision_gate": revision["reason"],
                "stale_final_path": stale_final_path,
                "quarantine_error": quarantine_error,
                "canonical_final_cleared": canonical_final_cleared})
            if verbose:
                print(f"[material-revision] BLOCK — {revision['reason']}")
            return {"ok": False, "stage": "material_revision",
                    "errors": revision.get("errors") or [revision["reason"]],
                    "reason": revision["reason"], "next_action": revision["next_action"],
                    "material_revision": revision.get("material_revision"),
                    "revised_contract": revision.get("revised_contract"),
                    "stale_final_path": stale_final_path,
                    "quarantine_error": quarantine_error,
                    "canonical_final_cleared": canonical_final_cleared,
                    "contract_hash": contract_hash}
        if revision["status"] == "applied":
            contract_obj = revision["revised"]            # BUILD uses the revised contract
            revision_waivers = revision["waivers"]
            contract_hash = _hash_json(contract_obj)
            if verbose:
                print("[material-revision] applied; building on revised contract")

    contract_obj, stock_route = _apply_stock_first_if_enabled(contract_obj)
    if stock_route:
        _write_json(stock_first_route_path, stock_route)
    script = contract_to_mv_script(contract_obj)
    payload = _with_payload_metadata(script, generated_from=source, contract_hash=contract_hash)
    from . import mv_cut  # noqa: PLC0415 — lazy(避免非執行情境載入 librosa)
    mvv = mv_cut.validate_mv_script(payload)
    if not mvv.get("can_run", True):
        return {"ok": False, "errors": mvv.get("issues"), "stage": "validate_mv_script",
                "contract_hash": contract_hash, "generated_script": payload}
    _write_json(generated_payload_path, payload)
    from . import model_routing  # noqa: PLC0415
    model_routes = model_routing.load_model_routes(model_routes_config_path)
    model_routing.write_model_routes(model_routes_path, model_routes)
    from . import build_profile  # noqa: PLC0415
    build_profile_payload = build_profile.load_build_profile(build_profile_config_path)

    editorial_design_path = None
    editorial_design_payload = None
    ed_path_dest = out_path.parent / "editorial_design.json"
    if ed_path_dest.exists():
        try:
            with ed_path_dest.open(encoding="utf-8") as f:
                editorial_design_payload = json.load(f)
            editorial_design_path = ed_path_dest
        except Exception:
            pass
    if not editorial_design_payload and source:
        ed_path_src = Path(source).parent / "editorial_design.json"
        if ed_path_src.exists():
            try:
                with ed_path_src.open(encoding="utf-8") as f:
                    editorial_design_payload = json.load(f)
                import shutil
                shutil.copy2(ed_path_src, ed_path_dest)
                editorial_design_path = ed_path_dest
            except Exception:
                pass

    if editorial_design_payload:
        from .editorial_design import derive_editing_policy
        build_profile_payload["editing_policy"] = derive_editing_policy(editorial_design_payload)
    creator_profile_paths = {}
    if creator_profile_path and Path(creator_profile_path).exists():
        brief_dict = None
        brief_candidate = out_path.parent / "brief.json"
        if brief_candidate.exists():
            try:
                with brief_candidate.open(encoding="utf-8") as bf:
                    brief_dict = json.load(bf)
            except Exception:
                brief_dict = None
        creator_profile_paths = _apply_creator_profile(
            out_path.parent, creator_profile_path, brief_dict, build_profile_payload, verbose=verbose)
    build_profile.write_build_profile(build_profile_path, build_profile_payload)
    from . import generated_assets  # noqa: PLC0415
    generated_assets.write_generated_asset_requests(
        contract_obj,
        generated_asset_requests_path,
        provider_priority=build_profile_payload.get("provider_priority"),
    )
    light_effects_paths = {}
    if (build_profile_payload.get("render_profile") == "light_effects"
            or build_profile_payload.get("effects_enabled")):
        effect_intent_plan, effect_intent_error = _resolve_effect_intent_plan(
            contract_obj, source)
        if effect_intent_error:
            stale_final_path, quarantine_error = _quarantine_stale_final(out_path)
            canonical_final_cleared = quarantine_error is None and stale_final_path is not None
            _write_json(out_path.parent / "state.json", {
                "pass": False,
                "final": None,
                "next_action": "revise:effects(effect_intent_plan)",
                "blocking": [effect_intent_error],
                "effect_intent_plan_gate": effect_intent_error,
                "stale_final_path": stale_final_path,
                "quarantine_error": quarantine_error,
                "canonical_final_cleared": canonical_final_cleared,
            })
            if verbose:
                print(f"[effect-intent] BLOCK -- {effect_intent_error}")
            return {"ok": False, "stage": "effect_intent_plan",
                    "errors": [effect_intent_error],
                    "reason": effect_intent_error,
                    "next_action": "revise:effects(effect_intent_plan)",
                    "stale_final_path": stale_final_path,
                    "quarantine_error": quarantine_error,
                    "canonical_final_cleared": canonical_final_cleared,
                    "contract_hash": contract_hash}
        from . import light_effects  # noqa: PLC0415
        light_effects_paths = light_effects.write_light_effects_artifacts(
            contract_obj,
            build_profile_payload,
            out_path.parent,
            effect_intent_plan=effect_intent_plan,
        )
    # Copy canonical contract to run workspace
    segment_contract_path = out_path.parent / "segment_contract.json"
    _write_json(segment_contract_path, contract_obj)
    if source and Path(source).exists():
        try:
            import shutil
            shutil.copy2(source, out_path.parent / Path(source).name)
        except Exception:
            pass

    # Copy brief to run workspace if referenced
    brief_ref = contract_obj.get("brief_ref")
    brief_path = None
    if brief_ref:
        brief_file = None
        if source:
            candidate = Path(source).parent / brief_ref
            if candidate.exists():
                brief_file = candidate
        if not brief_file:
            for prefix in (Path("."), Path("examples")):
                candidate = prefix / brief_ref
                if candidate.exists():
                    brief_file = candidate
                    break
        if brief_file:
            try:
                import shutil
                shutil.copy2(brief_file, out_path.parent / "brief.json")
                brief_path = out_path.parent / "brief.json"
            except Exception:
                pass

    # Pre-BUILD whole-SPEC review gate (roadmap C0): cross-check brief+contract
    # against the battle-tested failure modes and write the standing report.
    # Blocking findings stop the run BEFORE any material/render cost is paid.
    brief_dict_for_review = {}
    brief_for_target = out_path.parent / "brief.json"
    if brief_for_target.exists():
        try:
            with brief_for_target.open(encoding="utf-8") as bf:
                brief_dict_for_review = json.load(bf)
        except Exception:
            brief_dict_for_review = {}

    # Node 2 + M1: direct contract-run must materialize the same coverage and
    # supply evidence as runtime_orchestrator before the SPEC/render gate. Maps
    # load through the SAME canonical loader the gate + BUILD use (db-relative,
    # fail-closed) so supply judgement and BUILD see identical maps.
    from .project_material_map import (  # noqa: PLC0415
        load_material_db, material_maps_from_db_payload)
    material_db_payload, _db_err = load_material_db(material_db)
    if _db_err:
        state_path = out_path.parent / "state.json"
        _write_json(state_path, {"pass": False, "final": None,
                                 "next_action": "revise:material(material_delta)",
                                 "blocking": [_db_err]})
        return {"ok": False, "stage": "material_db", "errors": [_db_err],
                "next_action": "revise:material(material_delta)", "contract_hash": contract_hash}
    from .curator import build_material_coverage  # noqa: PLC0415
    coverage = build_material_coverage(payload.get("segments") or [],
                                       material_db_payload.get("files") or [])
    material_coverage_path = out_path.parent / "material_coverage_map.json"
    _write_json(material_coverage_path, coverage)
    material_maps, _map_err = material_maps_from_db_payload(
        material_db_payload, Path(material_db).parent)
    if _map_err:
        state_path = out_path.parent / "state.json"
        _write_json(state_path, {"pass": False, "final": None,
                                 "next_action": "revise:material(material_delta)",
                                 "blocking": [_map_err]})
        return {"ok": False, "stage": "material_map", "errors": [_map_err],
                "next_action": "revise:material(material_delta)", "contract_hash": contract_hash}
    from .supply_review import fallback_maps_from_coverage, review_supply  # noqa: PLC0415
    known_sources = {str(item.get("source") or "").lower() for item in material_maps}
    material_maps.extend(
        item for item in fallback_maps_from_coverage(coverage)
        if str(item.get("source") or "").lower() not in known_sources
    )
    try:
        from .editorial_qa import _parse_target_sec  # noqa: PLC0415
        supply_target_sec = _parse_target_sec(brief_dict_for_review.get("target_length"))
    except Exception:
        supply_target_sec = None
    supply = review_supply(
        contract_obj, material_maps, coverage_map=coverage,
        target_duration_sec=supply_target_sec)
    supply_review_path = out_path.parent / "supply_review.json"
    _write_json(supply_review_path, supply)

    from . import spec_review as _spec_review  # noqa: PLC0415
    review = _spec_review.review_spec(
        contract_obj, brief_dict_for_review,
        has_editorial_design=bool(editorial_design_payload),
        supply_review=supply if enforce_supply_gate else None)
    spec_review_path = out_path.parent / "spec_review.json"
    _write_json(spec_review_path, review)
    if not review["ready_for_build"]:
        state_path = out_path.parent / "state.json"
        _write_json(state_path, {"pass": False, "next_action": review["next_action"],
                                 "blocking": review["blocking"]})
        if verbose:
            print(f"[spec-review] NOT ready_for_build — {len(review['blocking'])} blocking:")
            for b in review["blocking"]:
                print(f"  - {b['message']}")
        return {"ok": False, "stage": "spec_review", "errors": review["blocking"],
                "warnings": review["warnings"], "next_action": review["next_action"],
                "spec_review": str(spec_review_path), "contract_hash": contract_hash}
    if verbose and review["warnings"]:
        for w in review["warnings"]:
            print(f"[spec-review] warn: {w['message']}")

    # M6b pre-BUILD material-delta gate (only when canonical material_needs is
    # explicitly declared). Fail-closed and computed fresh from current inputs;
    # runs BEFORE any music/timeline/render so a blocked build never produces or
    # overwrites a final video. delivery_gate stays a backstop, not this gate.
    delta_gate = _run_material_delta_gate(
        contract_obj, source, out_path.parent, material_db, material_db_payload,
        waivers=revision_waivers)
    if delta_gate and delta_gate["status"] == "block":
        # A previous build's final must not keep representing this (now-blocked)
        # run: move it aside with a traceable, collision-free lineage. If the
        # move fails we keep the block and do NOT claim the canonical final was
        # cleared.
        stale_final_path, quarantine_error = _quarantine_stale_final(out_path)
        canonical_final_cleared = quarantine_error is None and stale_final_path is not None
        state_path = out_path.parent / "state.json"
        _write_json(state_path, {
            "pass": False, "final": None, "next_action": delta_gate["next_action"],
            "blocking": delta_gate["blocking_need_ids"],
            "material_delta_gate": delta_gate["reason"],
            "stale_final_path": stale_final_path,
            "quarantine_error": quarantine_error,
            "canonical_final_cleared": canonical_final_cleared})
        if verbose:
            print(f"[material-delta] BLOCK — {delta_gate['reason']}")
            if stale_final_path:
                print(f"[material-delta] previous final moved to {stale_final_path}")
            elif quarantine_error:
                print(f"[material-delta] quarantine FAILED: {quarantine_error}")
        return {"ok": False, "stage": "material_delta",
                "errors": [delta_gate["reason"]],
                "blocking_need_ids": delta_gate["blocking_need_ids"],
                "route": delta_gate["route"], "next_action": delta_gate["next_action"],
                "ready_for_build": delta_gate["ready_for_build"],
                "delta_ok": delta_gate["ok"],
                "material_delta": delta_gate["material_delta"],
                "stale_final_path": stale_final_path,
                "quarantine_error": quarantine_error,
                "canonical_final_cleared": canonical_final_cleared,
                "contract_hash": contract_hash}
    if verbose and delta_gate:
        print(f"[material-delta] {delta_gate['status']} — {delta_gate['reason']}")

    music_struct = None
    if music_path:
        from . import music_structure  # noqa: PLC0415
        music_struct = music_structure.write_music_structure(
            music_path, music_structure_path, every_n_beats=every_n_beats)

    # brief.target_length caps the timeline: music length sets the rhythm, the
    # brief sets the runtime. Without this a 123s track stretches a 45s film to
    # 123s and every pacing gate downstream fails (ai-video soul-v5).
    target_sec = None
    try:
        from .editorial_qa import _parse_target_sec  # noqa: PLC0415
        target_sec = _parse_target_sec(brief_dict_for_review.get("target_length"))
    except Exception:
        target_sec = None

    effective_skip_render = skip_render or (build_profile_payload.get("render_backend") == "capcut_draft")
    burn_base_text = build_profile_payload.get("render_profile") not in {"light_effects", "motion_graphics"}
    _attach_attention_budgets(
        payload,
        music_structure=(music_struct or {}).get("structure"),
        editing_policy=(build_profile_payload or {}).get("editing_policy"),
    )
    _write_json(generated_payload_path, payload)
    res = mv_cut.mv_chain(payload, material_db, str(out_path), music_path=music_path,
                          mat_dir=mat_dir, verbose=verbose, skip_render=effective_skip_render,
                          target_sec=target_sec, burn_text=burn_base_text,
                          visual_judge=build_profile_payload.get("visual_judge", "agent"))
    if (build_profile_payload.get("render_profile") == "light_effects"
            and light_effects_paths.get("plan")
            and light_effects_paths.get("manifest")):
        from . import light_effects  # noqa: PLC0415
        with open(light_effects_paths["plan"], encoding="utf-8") as f:
            light_plan_payload = json.load(f)
        with open(light_effects_paths["manifest"], encoding="utf-8") as f:
            light_manifest_payload = json.load(f)
        light_effects.record_mv_render_outputs(
            light_plan_payload,
            light_manifest_payload,
            res.get("plan"),
            final_video=out_path if out_path.exists() else None,
        )
        _write_json(light_effects_paths["manifest"], light_manifest_payload)
    from . import edit_artifacts  # noqa: PLC0415
    edit_paths = edit_artifacts.write_edit_artifacts(
        payload,
        out_dir=out_path.parent,
        music_structure=(music_struct or {}).get("structure"),
        render_plan=res.get("plan") if isinstance(res, dict) else None,
        editing_policy=(build_profile_payload or {}).get("editing_policy"),
    )
    editor_review_path = None
    if edit_paths.get("timeline_build"):
        with open(edit_paths["timeline_build"], encoding="utf-8") as f:
            timeline = json.load(f)
        from . import editor_review  # noqa: PLC0415
        editor_review_path = out_path.parent / "editor_review.json"
        editor_review.write_editor_review(timeline, editor_review_path)
    motion_graphics_paths = {}
    if (build_profile_payload.get("render_profile") in {"motion_graphics", "light_effects"}
            and edit_paths.get("timeline_build")):
        from . import motion_graphics  # noqa: PLC0415
        with open(edit_paths["timeline_build"], encoding="utf-8") as f:
            motion_timeline = json.load(f)
        motion_contract = motion_graphics.contract_from_timeline(
            contract_obj,
            motion_timeline,
            backend=build_profile_payload.get("motion_graphics_backend", "ffmpeg_libass"),
            contract_hash=contract_hash,
        )
        if motion_contract["items"]:
            motion_graphics_paths = motion_graphics.write_motion_graphics_artifacts(
                motion_contract,
                out_path.parent,
                backend_policy={
                    "default_backend": build_profile_payload.get("motion_graphics_backend", "ffmpeg_libass"),
                    "fallback_backend": "ffmpeg_libass",
                    "allow_heavy_backend": False,
                },
            )
            with open(motion_graphics_paths["manifest"], encoding="utf-8") as f:
                motion_manifest_payload = json.load(f)
            if out_path.exists():
                composite_result = motion_graphics.composite_motion_graphics_outputs(
                    out_path,
                    motion_manifest_payload.get("render_outputs"),
                )
                motion_manifest_payload["composite_result"] = {
                    key: value for key, value in composite_result.items()
                    if key not in {"outputs", "stderr"}
                }
                if composite_result.get("stderr"):
                    motion_manifest_payload["composite_result"]["stderr"] = composite_result["stderr"][-2000:]
                _write_json(motion_graphics_paths["manifest"], motion_manifest_payload)
            if (build_profile_payload.get("render_profile") == "light_effects"
                    and light_effects_paths.get("plan")
                    and light_effects_paths.get("manifest")):
                from . import light_effects  # noqa: PLC0415
                with open(light_effects_paths["plan"], encoding="utf-8") as f:
                    light_plan_payload = json.load(f)
                with open(light_effects_paths["manifest"], encoding="utf-8") as f:
                    light_manifest_payload = json.load(f)
                light_effects.record_motion_graphics_outputs(
                    light_plan_payload,
                    light_manifest_payload,
                    motion_manifest_payload.get("render_outputs"),
                )
                _write_json(light_effects_paths["manifest"], light_manifest_payload)
    state_path = out_path.parent / "state.json"

    # Ensure subtitles.srt exists (needed for verify_result)
    srt_path = out_path.parent / "subtitles.srt"
    written_srt = False
    timeline_build_file = edit_paths.get("timeline_build")
    if timeline_build_file and os.path.exists(timeline_build_file):
        try:
            with open(timeline_build_file, encoding="utf-8") as f:
                tb_data = json.load(f)
            clips = tb_data.get("clips", [])
            merged_entries = _timeline_caption_entries(clips)

            def _fmt_ts(sec):
                h = int(sec // 3600)
                m = int((sec % 3600) // 60)
                s = int(sec % 60)
                ms = int(round((sec - int(sec)) * 1000))
                return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

            lines = []
            for idx, entry in enumerate(merged_entries, 1):
                lines.append(str(idx))
                lines.append(f"{_fmt_ts(entry['t_in'])} --> {_fmt_ts(entry['t_out'])}")
                lines.append(entry["text"])
                lines.append("")

            if lines:
                with open(srt_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(lines))
                written_srt = True
                print(f"[runtime] Generated subtitles.srt from timeline_build ({len(merged_entries)} entries)")
        except Exception as e:
            print(f"[runtime] Warning: failed to build subtitles.srt: {e}", file=sys.stderr)
            
    if not written_srt and not srt_path.exists():
        with srt_path.open("w", encoding="utf-8") as f:
            f.write("1\n00:00:00,000 --> 00:00:01,000\n[Music]\n")

    # Run verify automatically
    edit_log_path = edit_paths.get("timeline_build")
    verify_report_path = out_path.parent / "verify_result.json"
    if edit_log_path and out_path.exists():
        class VerifyArgs:
            script = str(generated_payload_path)
            timing = str(music_structure_path)
            edit_log = str(edit_log_path)
            srt = str(srt_path)
            video = str(out_path)
            out = str(verify_report_path)
            threshold = 80.0

        try:
            from . import vt_verify
            vt_verify.cmd_verify(VerifyArgs)
        except Exception as e:
            if verbose:
                print(f"[verify] Automatic verification failed: {e}")

    # P1 verification tool pack (gated by build_profile.verification_tools; OFF by
    # default so this is inert for standard runs). Written before dashboard state
    # so Node 11/12 surface the evidence in the same run.
    audit_paths = _write_p1_audits(
        out_path.parent, build_profile_payload,
        timeline_build_path=edit_paths.get("timeline_build"),
        srt_path=srt_path,
        final_video=out_path if out_path.exists() else None,
        contract_obj=contract_obj,
        verbose=verbose,
    )
    light_effects_baseline_review_path = None
    if light_effects_paths.get("plan") and light_effects_paths.get("manifest"):
        try:
            from . import light_effects  # noqa: PLC0415
            with open(light_effects_paths["plan"], encoding="utf-8") as f:
                light_effects_plan_payload = json.load(f)
            with open(light_effects_paths["manifest"], encoding="utf-8") as f:
                light_effects_manifest_payload = json.load(f)
            light_effects_baseline_review_path = light_effects.write_light_effects_baseline_review(
                light_effects_plan_payload,
                light_effects_manifest_payload,
                out_path.parent / "light_effects_baseline_review.json",
                final_video=out_path if out_path.exists() else None,
                audit_paths=audit_paths,
            )
        except Exception as e:
            if verbose:
                print(f"[light-effects] baseline review failed: {e}")

    # Reload / update editorial_qa.json if editing_policy is active to incorporate final verify_result/audits
    editorial_qa_path = edit_paths.get("editorial_qa")
    if build_profile_payload.get("editing_policy"):
        try:
            from . import edit_artifacts
            editorial_qa_path = edit_artifacts.write_editorial_qa(out_path.parent, build_profile_payload["editing_policy"])
        except Exception as e:
            if verbose:
                print(f"[editorial_qa] failed to update editorial_qa: {e}")

    # P3 optional CapCut backend: only when explicitly selected. ffmpeg stays the
    # canonical unattended path, so this is inert by default. Writes a
    # provider-neutral draft manifest; the real .draft + GUI export are a
    # human/Computer-Use step recorded separately and verified by Node 12.
    capcut_paths = {}
    if build_profile_payload.get("render_backend") == "capcut_draft" and edit_paths.get("timeline_build"):
        try:
            with open(edit_paths["timeline_build"], encoding="utf-8") as f:
                _tl = json.load(f)
            if music_path:
                total_duration = sum(float(c.get("duration_sec") or 0) for c in _tl.get("clips", []))
                _tl.setdefault("audio_tracks", []).append({
                    "role": "bgm",
                    "source_path": str(music_path),
                    "source_in_sec": 0,
                    "timeline_in_sec": 0,
                    "duration_sec": round(total_duration, 3),
                    "volume": 0.35,
                })
            from . import capcut_backend  # noqa: PLC0415
            cc_path = out_path.parent / "capcut_draft_manifest.json"
            capcut_backend.write_draft_manifest(_tl, cc_path, project_name=out_path.parent.name)
            capcut_paths["capcut_draft_manifest"] = str(cc_path)
            if verbose:
                print("[capcut] wrote provider-neutral draft manifest (GUI export remains a human/CU gate)")
            
            # Wire real CapCut draft writer using sanitized repo skeleton
            skeleton_path = Path(__file__).parent / "templates" / "0608" / "draft_content.json"
            if skeleton_path.exists():
                capcut_draft_root = Path.home() / "AppData" / "Local" / "CapCut" / "User Data" / "Projects" / "com.lveditor.draft"
                capcut_project_dir = capcut_draft_root / out_path.parent.name
                cc_res = capcut_backend.write_capcut_draft(
                    str(skeleton_path), _tl, str(capcut_project_dir), project_name=out_path.parent.name
                )
                if cc_res.get("ok") and verbose:
                    print(f"[capcut] wrote real CapCut draft folder to {capcut_project_dir}")
            else:
                if verbose:
                    print(f"[capcut] warning: skeleton template not found at {skeleton_path}")
        except Exception as e:
            if verbose:
                print(f"[capcut] draft manifest/folder generation skipped: {e}")

    # Compile the final dashboard state and overwrite state.json
    from . import dashboard_state
    dash_state = dashboard_state.load_dashboard_state(str(out_path.parent))

    state_json_data = {}
    if state_path.exists():
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state_json_data = json.load(f)
        except Exception:
            pass

    # Ensure segments providers are updated in state.json segments list
    state_segments = state_json_data.get("segments", [])
    dash_segments_map = {seg["segment"]: seg for seg in dash_state.get("segments", [])}
    for seg_data in state_segments:
        sid = seg_data.get("segment")
        if sid in dash_segments_map:
            prov = dash_segments_map[sid].get("build", {}).get("provider") or dash_segments_map[sid].get("provider")
            if prov:
                seg_data["provider"] = prov

    state_json_data["pass"] = dash_state["run"]["pass"]
    state_json_data["next_action"] = dash_state["run"]["next_action"]
    _write_json(state_path, state_json_data)

    manifest = _manifest(canonical_contract=source, contract_hash=contract_hash,
                         brief=str(brief_path) if brief_path else None,
                         generated_payload=str(generated_payload_path),
                         material_db=material_db, music=music_path,
                         music_structure=str(music_structure_path) if music_path else None,
                         model_routes=model_routes_path,
                         build_profile=build_profile_path,
                         stock_first_route=stock_first_route_path if stock_route else None,
                         generated_asset_requests=generated_asset_requests_path,
                         light_effects_plan=light_effects_paths.get("plan"),
                         light_effects_manifest=light_effects_paths.get("manifest"),
                         light_effects_baseline_review=light_effects_baseline_review_path,
                         motion_graphics_contract=motion_graphics_paths.get("contract"),
                         motion_graphics_render_plan=motion_graphics_paths.get("render_plan"),
                         motion_graphics_manifest=motion_graphics_paths.get("manifest"),
                         assembly_plan=edit_paths.get("assembly_plan"),
                         timeline_build=edit_paths.get("timeline_build"),
                         editor_review=editor_review_path,
                         final=str(out_path),
                         state=str(state_path),
                         verify_result=str(verify_report_path) if verify_report_path.exists() else None,
                         timeline_invariants=audit_paths.get("timeline_invariants"),
                         broll_audit=audit_paths.get("broll_audit"),
                         caption_audit=audit_paths.get("caption_audit"),
                         keyframe_grid=audit_paths.get("keyframe_grid"),
                         visual_audit=audit_paths.get("visual_audit"),
                         verify_evidence_bundle=audit_paths.get("verify_evidence_bundle"),
                          presentation_feel_audit=audit_paths.get("presentation_feel_audit"),
                         creator_profile=creator_profile_paths.get("creator_profile"),
                         creator_profile_applied=creator_profile_paths.get("creator_profile_applied"),
                         capcut_draft_manifest=capcut_paths.get("capcut_draft_manifest"),
                         editorial_design=str(editorial_design_path) if editorial_design_path else None,
                         editorial_qa=editorial_qa_path,
                         spec_review=spec_review_path)
    _write_json(manifest_path, manifest)

    # Return structured results
    render_ok = out_path.exists()
    
    verify_ok = False
    if verify_report_path.exists():
        try:
            with open(verify_report_path, "r", encoding="utf-8") as f:
                v_res = json.load(f)
                verify_ok = bool(v_res.get("pass"))
        except Exception:
            pass

    workflow_ok = render_ok and verify_ok
    next_action = dash_state["run"]["next_action"]

    return {
        "ok": workflow_ok,
        "render_ok": render_ok,
        "verify_ok": verify_ok,
        "workflow_ok": workflow_ok,
        "next_action": next_action,
        "errors": [],
        "warnings": v["warnings"],
        "stage": "run",
        "result": res,
        "generated_script": payload,
        "generated_payload": str(generated_payload_path),
        "manifest": str(manifest_path),
        "contract_hash": contract_hash
    }


def _synth_render_plan(payload, *, total_duration_sec=60.0):
    """Synthesize a *planned* (offline) render_plan from the generated MV payload.

    One clip per segment, with weight-proportioned durations (mirroring the
    allocation in ``edit_artifacts.build_assembly_plan``) and placeholder sources.
    Every clip is tagged ``provider="dry"`` / ``source="dry://segment-N"`` so it is
    never mistaken for a real selected/downloaded asset. Used only by
    :func:`dry_build` to materialize ``timeline_build.json`` without selecting,
    downloading, or rendering any material."""
    segs = payload.get("segments", []) if isinstance(payload, dict) else []
    weights = [max(0.1, float(s["weight"])) if s.get("weight") is not None else 1.0
               for s in segs]
    wsum = sum(weights) or 1.0
    plan = []
    cursor = 0.0
    for seg, w in zip(segs, weights):
        budget = round(float(total_duration_sec) * w / wsum, 3)
        seg_id = seg.get("segment")
        plan.append({
            "segment": seg_id,
            "provider": "dry",
            "source": f"dry://segment-{seg_id}",
            "extract_start": 0.0,
            "extract_dur": budget,
            "slot_dur": budget,
            "timeline_in": round(cursor, 3),
            "transition": "cut",
            "text": seg.get("subtitle") or "none",
            "audio_policy": "duck" if seg.get("keep_audio") else "music",
            "creative_exception": seg.get("creative_exception"),
        })
        cursor += budget
    return plan


def dry_build(contract, out_dir, *, categories_path=None, build_profile_config_path=None,
              total_duration_sec=60.0, verbose=True):
    """(I/O) Render-free **dry build** — materialize the Node 8/9/10/11 BUILD
    artifacts from a canonical ``segment_contract`` with NO material selection,
    download, ffmpeg, provider, or network call.

    Closes the convergence gap (see roadmap "Converge One Complete Pipeline" and
    the 2026-06-08 dry-run findings) where ``build_profile.json`` /
    ``assembly_plan.json`` / ``timeline_build.json`` could only be produced inside
    ``run_contract``, which renders. With this, ``runtime.py status`` can walk the
    full ``NODE_ORDER`` and exercise every chaining gate
    (``verify_profile`` / ``verify_assembly`` / ``verify_timeline`` /
    ``verify_editor_review``) offline.

    It deliberately does NOT render or verify: ``final.mp4`` and
    ``verify_result.json`` stay absent, so Node 12/13 correctly report ``missing``
    (only a real render can produce a verifiable video). Returns
    ``{ok, stage, dry_run, artifacts, contract_hash}``.
    """
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    contract_obj, source, contract_hash = _read_contract(contract)
    v = spec_contract.validate_segment_contract(
        contract_obj, categories=_load_category_ids(categories_path))
    if not v["ok"]:
        return {"ok": False, "errors": v["errors"], "warnings": v["warnings"],
                "stage": "validate_contract", "contract_hash": contract_hash}
    contract_obj, stock_route = _apply_stock_first_if_enabled(contract_obj)
    if stock_route:
        _write_json(out_dir / "stock_first_route.json", stock_route)

    script = contract_to_mv_script(contract_obj)
    payload = _with_payload_metadata(script, generated_from=source, contract_hash=contract_hash)
    from . import mv_cut  # noqa: PLC0415 — validate_mv_script is pure (no librosa)
    mvv = mv_cut.validate_mv_script(payload)
    if not mvv.get("can_run", True):
        return {"ok": False, "errors": mvv.get("issues"), "warnings": v["warnings"],
                "stage": "validate_mv_script", "contract_hash": contract_hash,
                "generated_script": payload}
    generated_payload_path = out_dir / "generated_mv_script.json"
    _write_json(generated_payload_path, payload)

    # Node 8: build_profile (+ editing_policy when an editorial_design is present).
    from . import build_profile  # noqa: PLC0415
    build_profile_payload = build_profile.load_build_profile(build_profile_config_path)
    editorial_design_path = None
    for cand in (out_dir / "editorial_design.json",
                 Path(source).parent / "editorial_design.json" if source else None):
        if cand and cand.exists():
            try:
                with cand.open(encoding="utf-8") as f:
                    ed_payload = json.load(f)
                from .editorial_design import derive_editing_policy  # noqa: PLC0415
                build_profile_payload["editing_policy"] = derive_editing_policy(ed_payload)
                editorial_design_path = cand
            except Exception:
                pass
            break
    build_profile_path = out_dir / "build_profile.json"
    build_profile.write_build_profile(build_profile_path, build_profile_payload)

    from . import generated_assets  # noqa: PLC0415
    gen_requests_path = out_dir / "generated_asset_requests.json"
    generated_assets.write_generated_asset_requests(
        contract_obj, gen_requests_path,
        provider_priority=build_profile_payload.get("provider_priority"))

    # Node 9/10: assembly_plan + timeline_build from a synthetic (offline) render plan.
    render_plan = _synth_render_plan(payload, total_duration_sec=total_duration_sec)
    from . import edit_artifacts  # noqa: PLC0415
    edit_paths = edit_artifacts.write_edit_artifacts(
        payload, out_dir=out_dir, music_structure=None, render_plan=render_plan,
        editing_policy=(build_profile_payload or {}).get("editing_policy"))

    # Node 11: editor_review over the timeline.
    editor_review_path = None
    if edit_paths.get("timeline_build"):
        with open(edit_paths["timeline_build"], encoding="utf-8") as f:
            timeline = json.load(f)
        from . import editor_review  # noqa: PLC0415
        editor_review_path = out_dir / "editor_review.json"
        editor_review.write_editor_review(timeline, editor_review_path)

    # Canonical contract into the workspace so dashboard/status can resolve facets.
    _write_json(out_dir / "segment_contract.json", contract_obj)

    # Copy the referenced brief so the Node 0 gate resolves and the chain walk
    # reaches the BUILD nodes (mirrors run_contract's brief_ref handling).
    brief_dest = out_dir / "brief.json"
    brief_ref = contract_obj.get("brief_ref") if isinstance(contract_obj, dict) else None
    if not brief_dest.exists():
        candidates = []
        if source:
            src_parent = Path(source).parent
            candidates.append(src_parent / "brief.json")
            if brief_ref:
                candidates.append(src_parent / brief_ref)
        if brief_ref:
            candidates += [Path(".") / brief_ref, Path("examples") / brief_ref]
        for cand in candidates:
            if cand and cand.exists():
                try:
                    import shutil  # noqa: PLC0415
                    shutil.copy2(cand, brief_dest)
                except Exception:
                    pass
                break

    # Pre-BUILD whole-SPEC review report (roadmap C0). dry-build never early-
    # returns — it exists for inspection — but the report and the dashboard
    # finding make a not-ready SPEC visible before any real run.
    brief_dict = {}
    if brief_dest.exists():
        try:
            with brief_dest.open(encoding="utf-8") as bf:
                brief_dict = json.load(bf)
        except Exception:
            brief_dict = {}
    from . import spec_review as _spec_review  # noqa: PLC0415
    review = _spec_review.review_spec(
        contract_obj, brief_dict,
        has_editorial_design=editorial_design_path is not None)
    spec_review_path = out_dir / "spec_review.json"
    _write_json(spec_review_path, review)
    if verbose and not review["ready_for_build"]:
        print(f"[dry-build] spec_review: NOT ready_for_build "
              f"({len(review['blocking'])} blocking)")

    # Dry-build marker (so nothing mistakes these artifacts for a real render).
    dry_marker_path = out_dir / "dry_build.json"
    _write_json(dry_marker_path, {
        "artifact_role": "dry_build",
        "version": 1,
        "dry_run": True,
        "contract_hash": contract_hash,
        "total_duration_sec": total_duration_sec,
        "materialized_nodes": ["8", "9", "10", "11"],
        "not_materialized": ["12", "13"],
        "note": "render-free chain validation; no material/ffmpeg/network. "
                "final.mp4 and verify_result.json are intentionally absent.",
    })

    state_path = out_dir / "state.json"
    manifest_path = out_dir / "artifact_manifest.json"
    manifest = _manifest(
        canonical_contract=source, contract_hash=contract_hash,
        generated_payload=str(generated_payload_path), material_db=None,
        music=None, music_structure=None, model_routes=None,
        build_profile=build_profile_path,
        stock_first_route=(out_dir / "stock_first_route.json") if stock_route else None,
        generated_asset_requests=gen_requests_path,
        assembly_plan=edit_paths.get("assembly_plan"),
        timeline_build=edit_paths.get("timeline_build"),
        editor_review=editor_review_path,
        final=out_dir / "final.mp4", state=state_path,
        editorial_design=editorial_design_path,
        editorial_qa=edit_paths.get("editorial_qa"),
        spec_review=spec_review_path)
    _write_json(manifest_path, manifest)

    # Compute the chain walk (next_action/pass) and persist state.json.
    from . import dashboard_state  # noqa: PLC0415
    dash_state = dashboard_state.load_dashboard_state(str(out_dir))
    _write_json(state_path, {
        "dry_run": True,
        "pass": dash_state["run"]["pass"],
        "next_action": dash_state["run"]["next_action"],
    })

    if verbose:
        print(f"[dry-build] materialized BUILD artifacts (no render) in {out_dir}")
        print(f"[dry-build] next_action = {dash_state['run']['next_action']}")

    return {
        "ok": True, "dry_run": True, "stage": "dry_build",
        "errors": [], "warnings": v["warnings"],
        "next_action": dash_state["run"]["next_action"],
        "contract_hash": contract_hash,
        "ready_for_build": review["ready_for_build"],
        "artifacts": {
            "generated_payload": str(generated_payload_path),
            "build_profile": str(build_profile_path),
            "generated_asset_requests": str(gen_requests_path),
            "assembly_plan": edit_paths.get("assembly_plan"),
            "timeline_build": edit_paths.get("timeline_build"),
            "editor_review": str(editor_review_path) if editor_review_path else None,
            "spec_review": str(spec_review_path),
            "dry_build": str(dry_marker_path),
            "manifest": str(manifest_path),
            "state": str(state_path),
        },
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="contract_adapter — canonical segment_contract runner")
    sub = ap.add_subparsers(dest="cmd")

    adapt = sub.add_parser("adapt")
    adapt.add_argument("contract")
    adapt.add_argument("--out")
    adapt.add_argument("--categories")

    dry = sub.add_parser("dry-build")
    dry.add_argument("contract")
    dry.add_argument("--out-dir", required=True)
    dry.add_argument("--categories")
    dry.add_argument("--build-profile")
    dry.add_argument("--total-duration", type=float, default=60.0)

    run = sub.add_parser("run")
    run.add_argument("contract")
    run.add_argument("--categories")
    run.add_argument("--material-db", required=True)
    run.add_argument("--music", required=True)
    run.add_argument("--out", required=True)
    run.add_argument("--mat-dir")
    run.add_argument("--model-routes")
    run.add_argument("--build-profile")
    run.add_argument("--quiet", action="store_true")

    args = ap.parse_args()
    if args.cmd == "adapt":
        r = adapt_contract_file(args.contract, out_path=args.out, categories_path=args.categories)
    elif args.cmd == "dry-build":
        r = dry_build(args.contract, out_dir=args.out_dir, categories_path=args.categories,
                      build_profile_config_path=args.build_profile,
                      total_duration_sec=args.total_duration)
    elif args.cmd == "run":
        out = Path(args.out)
        r = run_contract(args.contract, material_db=args.material_db, out_path=out,
                         music_path=args.music, mat_dir=args.mat_dir or out.parent,
                         verbose=not args.quiet, categories_path=args.categories,
                         model_routes_config_path=args.model_routes,
                         build_profile_config_path=args.build_profile,
                         enforce_supply_gate=True)
    else:
        ap.print_help()
        raise SystemExit(2)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    raise SystemExit(0 if r.get("ok") else 1)
