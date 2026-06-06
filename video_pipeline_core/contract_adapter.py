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
        # kind:只對 mv_cut 特殊處理的 bookend/title 設;montage 交給 layout/pace
        if section in ("opening", "closing", "title"):
            flat["kind"] = section
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
        if role_arole in ("duck", "diegetic"):
            flat["keep_audio"] = True
        # 文字層(text_layer == "none" → 不上字)
        if isinstance(txt, dict):
            for k in ("label", "narrative", "subtitle", "name_super"):
                if txt.get(k):
                    flat[k] = txt[k]
        out_segs.append(flat)

    script = {"style": contract.get("style", "mv") if isinstance(contract, dict) else "mv",
              "segments": out_segs}
    if isinstance(contract, dict) and contract.get("music"):
        script["music"] = contract["music"]
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


def _manifest(*, canonical_contract, contract_hash, generated_payload, material_db,
              music, music_structure, model_routes, build_profile,
              stock_first_route, generated_asset_requests,
              generated_asset_manifest=None,
              light_effects_plan=None,
              light_effects_manifest=None,
              motion_graphics_contract=None,
              motion_graphics_render_plan=None,
              motion_graphics_manifest=None,
              assembly_plan, timeline_build,
              editor_review, final, state, verify_result=None,
              revision_plan=None):
    return {
        "artifact_role": "artifact_manifest",
        "artifact_manifest_version": 1,
        "canonical_contract": canonical_contract,
        "contract_hash": contract_hash,
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
    }


def run_contract(contract, material_db, out_path, music_path=None, mat_dir="/tmp", verbose=True,
                 categories_path=None, generated_payload_path=None, manifest_path=None,
                 music_structure_path=None, every_n_beats=4, model_routes_path=None,
                 model_routes_config_path=None, build_profile_path=None,
                 build_profile_config_path=None, generated_asset_requests_path=None):
    """(I/O) canonical-first 入口:驗 contract → 轉 flat → 既有 mv_chain 執行。
    contract 可為 dict 或 .json 路徑。回 {ok, errors, result?}。**不改 run chain**。"""
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
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
        from . import light_effects  # noqa: PLC0415
        light_effects_paths = light_effects.write_light_effects_artifacts(
            contract_obj,
            build_profile_payload,
            out_path.parent,
        )
    music_struct = None
    if music_path:
        from . import music_structure  # noqa: PLC0415
        music_struct = music_structure.write_music_structure(
            music_path, music_structure_path, every_n_beats=every_n_beats)
    res = mv_cut.mv_chain(payload, material_db, str(out_path), music_path=music_path,
                          mat_dir=mat_dir, verbose=verbose)
    from . import edit_artifacts  # noqa: PLC0415
    edit_paths = edit_artifacts.write_edit_artifacts(
        payload,
        out_dir=out_path.parent,
        music_structure=(music_struct or {}).get("structure"),
        render_plan=res.get("plan") if isinstance(res, dict) else None,
    )
    editor_review_path = None
    if edit_paths.get("timeline_build"):
        with open(edit_paths["timeline_build"], encoding="utf-8") as f:
            timeline = json.load(f)
        from . import editor_review  # noqa: PLC0415
        editor_review_path = out_path.parent / "editor_review.json"
        editor_review.write_editor_review(timeline, editor_review_path)
    state_path = out_path.parent / "state.json"
    manifest = _manifest(canonical_contract=source, contract_hash=contract_hash,
                         generated_payload=str(generated_payload_path),
                         material_db=material_db, music=music_path,
                         music_structure=str(music_structure_path) if music_path else None,
                         model_routes=model_routes_path,
                         build_profile=build_profile_path,
                         stock_first_route=stock_first_route_path if stock_route else None,
                         generated_asset_requests=generated_asset_requests_path,
                         light_effects_plan=light_effects_paths.get("plan"),
                         light_effects_manifest=light_effects_paths.get("manifest"),
                         assembly_plan=edit_paths.get("assembly_plan"),
                         timeline_build=edit_paths.get("timeline_build"),
                         editor_review=editor_review_path,
                         final=str(out_path),
                         state=str(state_path),
                         verify_result=out_path.parent / "verify_result.json")
    _write_json(manifest_path, manifest)
    return {"ok": True, "errors": [], "warnings": v["warnings"], "stage": "run",
            "result": res, "generated_script": payload, "generated_payload": str(generated_payload_path),
            "manifest": str(manifest_path), "contract_hash": contract_hash}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="contract_adapter — canonical segment_contract runner")
    sub = ap.add_subparsers(dest="cmd")

    adapt = sub.add_parser("adapt")
    adapt.add_argument("contract")
    adapt.add_argument("--out")
    adapt.add_argument("--categories")

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
    elif args.cmd == "run":
        out = Path(args.out)
        r = run_contract(args.contract, material_db=args.material_db, out_path=out,
                         music_path=args.music, mat_dir=args.mat_dir or out.parent,
                         verbose=not args.quiet, categories_path=args.categories,
                         model_routes_config_path=args.model_routes,
                         build_profile_config_path=args.build_profile)
    else:
        ap.print_help()
        raise SystemExit(2)
    print(json.dumps(r, ensure_ascii=False, indent=2))
    raise SystemExit(0 if r.get("ok") else 1)
