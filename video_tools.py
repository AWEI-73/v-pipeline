#!/usr/bin/env python3
"""
video_tools.py — video_director agent 工具腳本
用法: python3 video_tools.py <command> [options]

Commands:
  search      <query> [--limit N]              搜尋 YouTube，回傳 JSON 清單
  meta        <url>                            取得單支影片 metadata JSON
  download    <url> [--start HH:MM:SS] [--end HH:MM:SS] [--out filename]
  probe       <file>                           取得本地影片資訊 JSON
  cut         <file> --start HH:MM:SS --end HH:MM:SS --out output.mp4
  concat      <file1> <file2> ... --out output.mp4
  subtitle    <file> [--language zh] [--out output.srt]   語音轉字幕
  mksrt       <script.json> [--out output.srt]            從劇本 JSON 生成中文 .srt
  burnsub     <video> <srt> [--out output.mp4]            把 .srt 燒進影片
              [--subtitle-text-policy polish|exact]
  script-run  <script.json> [--out output.mp4]            劇本驅動全自動剪片
  title       <file> --text "標題文字" [--out output.mp4]
  tts         <script.json> [--voice ZH-VOICE] [--outdir DIR]
              按標點切句 → 每句獨立 TTS → 累加時長 → 合併 + tts_timing.json
  mix-audio   --voice voice.mp3 [--bgm bgm.mp3] [--bgm-vol 0.10] [--out final_audio.wav]
              人聲 + BGM 混音（BGM 自動 ducking + 淡入淡出）
  music-fetch <query> [--source yt] [--max-dur N] [--out music.mp3]
              抓真實背景音樂（yt-dlp 抽音訊；royalty-free API 留 provider 接縫）
  srt         <tts_timing.json> [--out subtitles.srt]
              從 tts_timing.json 生成 phrase-level 時間同步 SRT
  assemble    --clips clip_list.json --timing tts_timing.json [--out rough_cut.mp4]
              剪輯師：依 TTS 時長剪每段素材 → scale 1920x1080 → concat
  merge-final --visual VIDEO --audio AUDIO --subs SRT [--out final.mp4]
              [--subtitle-text-policy polish|exact]
              剪輯師最終組合：把音軌+字幕套到無音軌的視覺上
  verify      --script S --timing T --edit-log E --srt SRT --video V [--out qa.json]
              VERIFY：5 維度評分 + fix_target 路由
  analyze     <video> --query "keywords" [--target-sec N] [--model MODEL]
              小編：Whisper 轉譯影片 → 找最匹配關鍵字的時間窗口
  curate      --script S --timing T [--workdir DIR] [--top-n N] [--out clip_list.json]
              小編全自動：search + download + analyze + 選最佳 → clip_list.json
  state       <workdir> [--project NAME] [--out state.json]
              Dashboard：掃 workdir 產出 state.json（節點狀態 + 檔案 + 分數）
  serve       <workdir> [--port 8765]
              啟動本地 HTTP server 服務 dashboard.html + workspace 檔案
  dashboard   <workdir> [--out file.html]
              產 self-contained dashboard（state 內嵌）→ 直接開檔即可看，免 server
  ingest-meta <dir> [--out materials_db.json]
              小編：掃本地素材庫，提取 EXIF/ffprobe/keyframe + classify(機械歸類)，輸出 materials_db.json
  caption-meta <db> [--model M] [--limit N] [--visual-review-dir DIR]
              小編語意歸類：對素材跑本地 VLM 填 vlm_caption(實際內容)
  material-map <db> [--out map.md]
              人看得懂的素材地圖（依資料夾分群 + 可用/caption）
  match-mv <script> <db> [--out clip_list.json]
              需求×供給比對：MV 劇本 × materials_db → 每段配 clip + 缺口
              （vision 評分由 agent 看圖填入，不在此處呼叫 API）
  rank-local  --db materials_db.json --needs material_needs.json [--out clip_list.json]
              小編：用 agent 評過分的 db 配對 material_needs，輸出 clip_list.json
  kenburns    <photo.jpg> --duration N [--direction MODE] [--out video.mp4]
              照片動畫：把 jpg/png 變成有 Ken Burns 慢推鏡的 1080p 影片
  pexels-search <query> --type photo|video [--limit N] [--out json]
              小編擴充：從 Pexels 搜尋照片/影片（需 PEXELS_API_KEY 環境變數）
  pexels-download <url> [--out file]
              下載 Pexels 直連 URL（從 pexels-search 結果拿）
  project-init <name> [--root DIR]
              建立外部 project workspace，並更新 repo/.project/active.json
  project-new-run [--project DIR] [--label LABEL]
              在 active project 建立一次 run 目錄，並更新 active_run
  contract-adapt <segment_contract.json> [--out generated_mv_script.json]
              canonical SPEC → legacy runtime payload
  contract-dry-build <segment_contract.json> --out-dir DIR
              render-free chain validation: SPEC → build_profile/assembly_plan/
              timeline_build/editor_review (Node 8/9/10/11) with no material/ffmpeg/network
  contract-run <segment_contract.json> --material-db DB --music MP3 --out final.mp4
              canonical SPEC → adapter → mv_chain → manifest/state artifacts
  generated-manifest <generated_asset_requests.json> --outputs outputs.json --out generated_asset_manifest.json
              validate external generated assets and write provider-neutral manifest
  effect-intent-plan <director_shot_plan.json> --out-plan effect_intent_plan.json --out-spec effect_asset_spec.json
              compile upstream effect intent into neutral effects contract artifacts
  light-effects-plan <segment_contract.json> --build-profile build_profile.json --out-dir DIR
              write ffmpeg-safe light effects plan and manifest
  effect-capability-review --request "..." --out effect_capability_review.json
              decide whether an effect can enter the bounded Remotion worker route
  effect-dictionary-promote --request promotion_request.json --dictionary effect_dictionary.json --out effect_dictionary.promoted.json
              promote reviewed GenericRemotionEffect graph into the effect dictionary
"""

import sys
import json
import subprocess
import argparse
import os
import re
import shutil
import tempfile
from pathlib import Path

from video_pipeline_core.env_loader import apply_dotenv

apply_dotenv()

if sys.platform == "win32":
    import io
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except (AttributeError, io.UnsupportedOperation):
        pass

from video_pipeline_core.vt_core import YTDLP, FFMPEG, FFPROBE, run, ToolError, _audio_duration


# ── helpers ──────────────────────────────────────────────────────────────────



def die(msg: str):
    print(json.dumps({"error": msg}), file=sys.stderr)
    sys.exit(1)


def _dispatch_python_tools(tools_dir: Path) -> set[str]:
    if not tools_dir.exists():
        return set()
    return {
        str(path.relative_to(tools_dir.parent)).replace("\\", "/")
        for path in tools_dir.glob("*.py")
        if path.name != "__init__.py"
    }


def _capability_human_text(result: dict) -> str:
    lines = []
    fields = ("owner", "stage_owner", "kind", "loops", "certified_scope", "tool", "when", "inputs", "outputs", "stop_if", "source_skill")
    for card in result.get("results") or []:
        lines.append(f"{card.get('capability_id')} [{card.get('maturity')}]")
        for field in fields:
            value = card.get(field)
            if isinstance(value, list):
                value = json.dumps(value, ensure_ascii=False, separators=(",", ":"))
            lines.append(f"{field}: {value if value is not None else ''}")
        lines.append("---")
    return "\n".join(lines[:-1] if lines and lines[-1] == "---" else lines)


def run_dispatch_capabilities_query(
    args,
    *,
    skills_dir: Path,
    tools_dir: Path,
    dispatch_commands: set[str],
    catalog_commands: set[str],
) -> int:
    from video_pipeline_core.capability_catalog import build_catalog, query_catalog
    from video_pipeline_core.skill_tool_contract import audit_repository_contracts, load_contracts

    selected = [("id", args.id), ("owner", args.owner), ("loop", args.loop), ("query", args.query)]
    selected = [(kind, value) for kind, value in selected if value is not None]
    if len(selected) != 1:
        print("exactly one of --id, --owner, --loop, or --query is required", file=sys.stderr)
        return 2
    selector, value = selected[0]
    if selector == "loop" and str(value).upper() not in {f"L{i}" for i in range(6)}:
        print("--loop must be one of L0..L5", file=sys.stderr)
        return 2
    contracts, parse_errors = load_contracts(skills_dir)
    repository_errors = audit_repository_contracts(
        contracts,
        python_tools=_dispatch_python_tools(tools_dir),
        dispatch_commands=dispatch_commands,
        catalog_commands=catalog_commands,
        capability_consumers=(),
    )
    catalog = build_catalog(contracts, validation_errors=[*parse_errors, *repository_errors])
    result = query_catalog(catalog, selector=selector, value=value)
    if args.json or args.out:
        payload = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(payload, encoding="utf-8")
        if args.json:
            print(payload, end="")
    elif result.get("ok"):
        print(_capability_human_text(result))
    else:
        code = (result.get("error") or {}).get("code")
        print(
            "capability query: live catalog invalid" if code == "invalid_catalog" else "capability query: no matches",
            file=sys.stderr,
        )
    if result.get("ok"):
        return 0
    if (result.get("error") or {}).get("code") == "invalid_catalog":
        return 2
    return 1


def cmd_dispatch_capabilities(args):
    commands = {f"video_tools.py {name}" for name in VIDEO_TOOLS_DISPATCH}
    return run_dispatch_capabilities_query(
        args,
        skills_dir=Path(getattr(args, "skills_dir", "skills")),
        tools_dir=Path(getattr(args, "tools_dir", "tools")),
        dispatch_commands=commands,
        catalog_commands=commands,
    )


# ── commands ─────────────────────────────────────────────────────────────────

def cmd_contract_adapt(args):
    from video_pipeline_core import contract_adapter
    result = contract_adapter.adapt_contract_file(
        args.contract,
        out_path=args.out,
        categories_path=args.categories,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


def cmd_spec_review(args):
    from video_pipeline_core import spec_review
    brief = {}
    supply_review = None
    if args.brief and Path(args.brief).exists():
        brief = _load_json(args.brief)
    contract = _load_json(args.contract)
    if getattr(args, "supply_review", None):
        supply_review = _load_json(args.supply_review)
    result = spec_review.review_spec(
        contract, brief,
        has_editorial_design=bool(args.editorial_design and Path(args.editorial_design).exists()),
        supply_review=supply_review)
    if args.out:
        with open(args.out, "w", encoding="utf-8") as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ready_for_build"):
        raise SystemExit(1)


def cmd_capability_manifest(args):
    from video_pipeline_core import capability_manifest
    out = capability_manifest.write_capability_manifest(args.out)
    print(json.dumps({"ok": True, "capability_manifest": out}, ensure_ascii=False, indent=2))


def cmd_supply_review(args):
    from video_pipeline_core.supply_review import fallback_maps_from_coverage, review_supply
    contract = _load_json(args.contract)
    maps = []
    for path in Path(args.maps_dir).glob("*.map.json"):
        maps.append(_load_json(path))
    coverage_map = None
    if args.coverage_map:
        coverage_map = _load_json(args.coverage_map)
        known_sources = {str(item.get("source") or "").lower() for item in maps}
        maps.extend(
            item for item in fallback_maps_from_coverage(coverage_map)
            if str(item.get("source") or "").lower() not in known_sources
        )
    result = review_supply(
        contract,
        maps,
        coverage_map=coverage_map,
        target_duration_sec=args.target_duration,
    )
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_director_supply_revise(args):
    from video_pipeline_core import director_supply_revision
    result = director_supply_revision.revise_contract_file(
        args.contract,
        args.supply_review,
        args.out_contract,
        args.out_report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_contract_dry_build(args):
    from video_pipeline_core import contract_adapter
    result = contract_adapter.dry_build(
        args.contract,
        out_dir=args.out_dir,
        categories_path=args.categories,
        build_profile_config_path=args.build_profile,
        total_duration_sec=args.total_duration,
        verbose=not args.quiet,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


def cmd_contract_run(args):
    from video_pipeline_core import contract_adapter
    result = contract_adapter.run_contract(
        args.contract,
        material_db=args.material_db,
        out_path=args.out,
        music_path=args.music,
        mat_dir=args.mat_dir or str(Path(args.out).parent),
        verbose=not args.quiet,
        categories_path=args.categories,
        model_routes_config_path=args.model_routes,
        build_profile_config_path=args.build_profile,
        creator_profile_path=getattr(args, "creator_profile", None),
        skip_render=getattr(args, "skip_render", False),
        enforce_supply_gate=True,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise SystemExit(1)


def cmd_generated_manifest(args):
    from video_pipeline_core import generated_assets
    manifest = generated_assets.write_generated_asset_manifest_from_outputs(
        args.requests,
        args.outputs,
        args.out,
        require_files=not args.no_require_files,
    )
    artifact_manifest = None
    if args.artifact_manifest:
        artifact_manifest = generated_assets.attach_generated_manifest_to_artifact_manifest(
            args.artifact_manifest,
            manifest,
        )
    print(json.dumps({"ok": True, "generated_asset_manifest": manifest,
                      "artifact_manifest": artifact_manifest},
                     ensure_ascii=False, indent=2))


def cmd_light_effects_plan(args):
    from video_pipeline_core import build_profile, light_effects
    with Path(args.contract).open(encoding="utf-8") as f:
        contract = json.load(f)
    effect_intent_plan = None
    if getattr(args, "effect_intent_plan", None):
        with Path(args.effect_intent_plan).open(encoding="utf-8") as f:
            effect_intent_plan = json.load(f)
    profile = build_profile.load_build_profile(args.build_profile)
    result = light_effects.write_light_effects_artifacts(
        contract,
        profile,
        args.out_dir,
        effect_intent_plan=effect_intent_plan,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_effect_intent_plan(args):
    from video_pipeline_core.effect_contract import compile_effect_contract_file
    result = compile_effect_contract_file(
        args.director_shot_plan,
        out_plan=args.out_plan,
        out_spec=args.out_spec,
    )
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


def cmd_visual_technique_plan(args):
    from video_pipeline_core.visual_technique_plan import plan_visual_technique
    brief = {
        "request": args.request,
        "effect_role": args.effect_role,
        "duration_sec": args.duration_sec,
        "material_state": args.material_state,
    }
    if getattr(args, "confirmed", False):
        brief["confirmed_style_family"] = True
    result = plan_visual_technique(brief)
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": True, "visual_technique_plan": args.out, **result}, ensure_ascii=False, indent=2))


def cmd_effect_design_concept(args):
    from video_pipeline_core.effect_design_concept import write_effect_design_concept_chain
    request = getattr(args, "request", None) or ""
    request_file = getattr(args, "request_file", None) or ""
    if request_file:
        request = Path(request_file).read_text(encoding="utf-8-sig")
    try:
        result = write_effect_design_concept_chain(
            args.out_dir,
            request=request,
            effect_role=args.effect_role,
            duration_sec=args.duration_sec,
            material_context=getattr(args, "material_context", "reviewed_or_local_material_refs"),
            preferred_concept_id=(getattr(args, "preferred_concept_id", "") or None),
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect design concept failed: {exc}") from exc
    print(json.dumps({"ok": True, **result}, ensure_ascii=False, indent=2))


def cmd_effect_design_review(args):
    from video_pipeline_core.effect_design_concept import write_effect_design_review
    try:
        result = write_effect_design_review(
            args.selection,
            args.render_report,
            args.out,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect design review failed: {exc}") from exc
    print(json.dumps({"ok": True, "effect_design_review": args.out, **result}, ensure_ascii=False, indent=2))


def cmd_effect_capability_review(args):
    from video_pipeline_core.effect_capability_review import write_effect_capability_review
    payload = {}
    if getattr(args, "input", None):
        with Path(args.input).open(encoding="utf-8-sig") as f:
            payload = json.load(f)
    if not isinstance(payload, dict):
        raise ToolError("effect capability input must be a JSON object")
    payload.update({
        "request": args.request or payload.get("request", ""),
        "effect_role": args.effect_role or payload.get("effect_role", ""),
    })
    if getattr(args, "duration_sec", None) is not None:
        payload["duration_sec"] = args.duration_sec
    try:
        result = write_effect_capability_review(payload, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect capability review failed: {exc}") from exc
    print(json.dumps({"ok": True, "effect_capability_review": args.out, **result}, ensure_ascii=False, indent=2))


def cmd_effect_dictionary_promote(args):
    from video_pipeline_core.effect_dictionary_promotion import promote_effect_dictionary_entry
    try:
        with Path(args.request).open(encoding="utf-8-sig") as f:
            request = json.load(f)
        result = promote_effect_dictionary_entry(request, args.dictionary, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect dictionary promotion failed: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_soundtrack_arrange(args):
    from video_pipeline_core.soundtrack_arranger import write_soundtrack_artifacts
    with open(args.input, encoding="utf-8-sig") as f:
        payload = json.load(f)
    artifacts = write_soundtrack_artifacts(payload, args.out_dir)
    print(json.dumps({
        "ok": True,
        "out_dir": args.out_dir,
        "ready_for_audio_director": artifacts["audio_director_handoff"]["ready_for_audio_director"],
        "blocks": artifacts["audio_director_handoff"]["blocks"],
        "artifacts": [
            "soundtrack_plan.json",
            "music_source_candidates.json",
            "sound_license_manifest.json",
            "audio_director_handoff.json",
        ],
    }, ensure_ascii=False, indent=2))


def cmd_soundtrack_provider_search(args):
    from video_pipeline_core.soundtrack_providers import write_provider_candidates
    with open(args.plan, encoding="utf-8-sig") as f:
        plan = json.load(f)
    providers = [item.strip() for item in str(args.providers).split(",") if item.strip()]
    result = write_provider_candidates(
        plan,
        args.out,
        providers=providers,
        limit=args.limit,
    )
    print(json.dumps({
        "ok": True,
        "music_source_candidates": args.out,
        "provider_status": result.get("provider_status") or {},
        "candidate_count": len(result.get("candidates") or []),
    }, ensure_ascii=False, indent=2))


def cmd_soundtrack_provider_download(args):
    from video_pipeline_core.soundtrack_providers import download_candidate, load_candidate_by_id
    candidate = load_candidate_by_id(args.candidates, args.candidate_id)
    result = download_candidate(candidate, args.out_dir)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_soundtrack_import_url(args):
    from video_pipeline_core.soundtrack_providers import import_url_with_ytdlp
    result = import_url_with_ytdlp(
        args.url,
        args.out_dir,
        section_id=args.section_id,
        source_type=args.source_type,
        usage_scope=args.usage_scope,
        license_note=args.license_note or "",
        license_url=args.license_url or "",
        ytdlp_path=args.ytdlp_path,
        audio_format=args.audio_format,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_soundtrack_audio_handoff_accept(args):
    from video_pipeline_core.audio_handoff_acceptance import accept_audio_handoff_files
    result = accept_audio_handoff_files(
        args.handoff,
        out_dir=args.out_dir,
        soundtrack_plan_path=args.soundtrack_plan,
        license_manifest_path=args.license_manifest,
        soundtrack_probe_report_path=args.soundtrack_probe_report,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_voiceover_provider_plan(args):
    from video_pipeline_core.voiceover_provider import (
        VoiceoverProviderError,
        build_voiceover_provider_plan,
        write_voiceover_provider_artifacts,
    )

    try:
        payload = build_voiceover_provider_plan(
            script_path=args.script,
            out_dir=args.out_dir,
            provider=args.provider,
            voice_style=args.voice_style,
            model_id=args.model_id,
            reference_audio=args.reference_audio,
            device=args.device,
            local_files_only=args.local_files_only,
            inference_timesteps=args.inference_timesteps,
            cfg_value=args.cfg_value,
            execute=args.execute,
            allow_fallback=not args.no_fallback,
            execute_fallback=args.execute_fallback,
            fallback_voice=args.fallback_voice,
            voxcpm_bin=args.voxcpm_bin,
            voxcpm_repo=args.voxcpm_repo,
            voxcpm_python=args.voxcpm_python,
            timeout_sec=args.timeout_sec,
        )
    except VoiceoverProviderError as exc:
        raise ToolError(str(exc)) from exc
    written = write_voiceover_provider_artifacts(payload, args.out_dir)
    print(json.dumps({
        "ok": not bool(payload["plan"].get("errors")),
        "selected_provider": payload["plan"].get("selected_provider"),
        "provider_available": payload["plan"].get("provider_available"),
        "provider_entry_type": payload["plan"].get("provider_entry_type"),
        "provider_repo": payload["plan"].get("provider_repo"),
        "provider_python": payload["plan"].get("provider_python"),
        "voiceover_ready": payload["handoff"].get("voiceover_ready"),
        "artifacts": written,
        "error_count": len(payload["plan"].get("errors") or []),
    }, ensure_ascii=False, indent=2))


def cmd_visual_technique_review_apply(args):
    from video_pipeline_core.visual_technique_plan import apply_visual_technique_review_file
    try:
        result = apply_visual_technique_review_file(args.plan, args.review, args.out)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"visual technique review apply failed: {exc}") from exc
    print(json.dumps({"ok": True, "visual_technique_plan": args.out, **result}, ensure_ascii=False, indent=2))


def cmd_effect_revision_request(args):
    from video_pipeline_core.effect_revision import write_effect_revision_request
    try:
        result = write_effect_revision_request(
            args.baseline_review,
            args.out,
            light_effects_plan_path=args.light_effects_plan,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect revision request failed: {exc}") from exc
    print(json.dumps({"ok": True, "effect_revision_request": args.out, **result},
                     ensure_ascii=False, indent=2))


def cmd_effect_revision_draft(args):
    from video_pipeline_core.effect_revision import write_effect_revision_draft
    try:
        result = write_effect_revision_draft(
            args.request,
            args.out_patch,
            effect_intent_plan_path=args.effect_intent_plan,
            out_intent_draft_path=args.out_intent_draft,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect revision draft failed: {exc}") from exc
    print(json.dumps({
        "ok": True,
        "effect_recipe_patch": result["effect_recipe_patch"],
        "revised_effect_intent_plan_draft": result["revised_effect_intent_plan_draft"],
        "patch_status": result["patch"]["status"],
    }, ensure_ascii=False, indent=2))


def cmd_effect_revision_apply(args):
    from video_pipeline_core.effect_revision import write_revised_effect_intent_plan
    try:
        result = write_revised_effect_intent_plan(
            args.draft,
            args.out,
            accept=args.accept,
            reviewer=args.reviewer,
            reason=args.reason,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect revision apply failed: {exc}") from exc
    print(json.dumps({
        "ok": True,
        "effect_intent_plan": args.out,
        "effect_count": len(result.get("effects") or []),
        "reviewer": result.get("node14_apply_lineage", {}).get("reviewer"),
    }, ensure_ascii=False, indent=2))


def _load_json(path):
    with Path(path).open(encoding="utf-8-sig") as f:
        return json.load(f)


def cmd_timeline_audit(args):
    """P1 Node 11: deterministic timeline_build invariants audit."""
    from video_pipeline_core import timeline_invariants
    timeline = _load_json(args.timeline)
    kwargs = {}
    if getattr(args, "expected_duration", None) is not None:
        kwargs["expected_duration_sec"] = args.expected_duration
    if getattr(args, "must_include", None):
        kwargs["must_include_segments"] = list(args.must_include)
    result = timeline_invariants.write_timeline_invariants(timeline, args.out, **kwargs)
    print(json.dumps(result["result"], ensure_ascii=False, indent=2))


def cmd_broll_audit(args):
    """P1 Node 11: B-roll ratio / repeated-source audit."""
    from video_pipeline_core import broll_audit
    timeline = _load_json(args.timeline)
    kwargs = {}
    if getattr(args, "target_ratio", None) is not None:
        kwargs["target_ratio"] = args.target_ratio
    if getattr(args, "max_source_repeats", None) is not None:
        kwargs["max_source_repeats"] = args.max_source_repeats
    result = broll_audit.write_broll_audit(timeline, args.out, **kwargs)
    print(json.dumps(result["result"], ensure_ascii=False, indent=2))


def cmd_new_visual_information_audit(args):
    """M2 Node 11: repeated-scene and new-visual-information audit."""
    from video_pipeline_core import new_visual_information_audit
    timeline = _load_json(args.timeline)
    result = new_visual_information_audit.write_new_visual_information_audit(
        timeline,
        args.out,
        min_new_visual_ratio=args.min_new_visual_ratio,
        max_repeated_hold_sec=args.max_repeated_hold_sec,
    )
    print(json.dumps(result["result"], ensure_ascii=False, indent=2))


def cmd_black_frame_audit(args):
    """M0d Node 12: tier-1 black/blank-frame defect gate over a rendered video."""
    from video_pipeline_core import black_frame_audit
    result = black_frame_audit.write_black_frame_audit(
        args.video,
        args.out,
        fps=args.fps,
        min_run_sec=args.min_run_sec,
    )
    print(json.dumps(result["result"], ensure_ascii=False, indent=2))


def cmd_validate_needs(args):
    """M6a: strict-validate material_needs; --migrate allocates stable need_ids."""
    from video_pipeline_core import material_needs
    raw = _load_json(args.needs)
    canonical = material_needs.migrate_material_needs(raw) if args.migrate else None
    result = material_needs.validate_material_needs(
        canonical if canonical is not None else raw)
    if result["ok"] and args.out:
        obj = canonical if canonical is not None else {
            "artifact_role": "material_needs", "version": 1,
            "project": result["project"], "needs": result["needs"],
        }
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(obj, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": result["ok"],
        "migrated": bool(args.migrate),
        "errors": result["errors"],
        "warnings": result["warnings"],
        "need_count": len(result["needs"]),
    }, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError(f"material_needs validation failed: {len(result['errors'])} error(s)")


def cmd_project_material_map(args):
    """MM1: aggregate per-asset *.map.json into project_material_map.json."""
    from video_pipeline_core import project_material_map
    result = project_material_map.write_project_material_map(
        args.maps_dir, args.out, needs_path=args.needs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_material_map_review_apply(args):
    """Apply agent/director map-review decisions as scene-level satisfies edges."""
    from video_pipeline_core import material_map_review_apply
    result = material_map_review_apply.apply_review_to_maps(
        args.maps_dir,
        args.needs,
        args.verdict,
        args.out,
        material_db_path=getattr(args, "material_db", None),
        skipped_policy=getattr(args, "skipped_policy", None),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_source_highlight_plan(args):
    """Plan source timeline windows and rough cut for one long source video."""
    from video_pipeline_core.source_highlight_planner import write_source_highlight_plan

    result = write_source_highlight_plan(
        args.source,
        out_dir=args.out_dir,
        soundtrack_probe_path=args.soundtrack_probe,
        intent=args.intent or "",
        target_sec=args.target_sec,
        window_sec=args.window_sec,
        clip_sec=args.clip_sec,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_source_material_matrix(args):
    """Build window-level eye/ear evidence for one long source video."""
    from video_pipeline_core.source_material_matrix import build_source_material_matrix

    visual_review = None
    if getattr(args, "visual_review", None):
        visual_review = json.loads(Path(args.visual_review).read_text(encoding="utf-8-sig"))
    result = build_source_material_matrix(
        args.source,
        out_dir=args.out_dir,
        window_sec=args.window_sec,
        visual_review=visual_review,
        soundtrack_probe_path=getattr(args, "soundtrack_probe", None),
    )
    print(json.dumps({
        "artifact_role": result["artifact_role"],
        "source_material_matrix": str(Path(args.out_dir) / "source_material_matrix.json"),
        "window_count": len(result.get("windows") or []),
        "next_action": result.get("next_action"),
    }, ensure_ascii=False, indent=2))
    return result


def cmd_source_section_map(args):
    """Build section-level source structure from visual cuts and audio energy."""
    from video_pipeline_core.keyframe_grid import probe_duration
    from video_pipeline_core.mv_cut import detect_shots
    from video_pipeline_core.source_section_map import write_source_section_map

    energy_curve = []
    if getattr(args, "soundtrack_probe", None):
        probe = json.loads(Path(args.soundtrack_probe).read_text(encoding="utf-8-sig"))
        features = probe.get("features") if isinstance(probe, dict) else {}
        curve = features.get("energy_curve") if isinstance(features, dict) else []
        energy_curve = curve if isinstance(curve, list) else []
    result = write_source_section_map(
        args.out,
        duration_sec=probe_duration(args.video),
        energy_curve=energy_curve,
        shots=detect_shots(args.video),
        target_section_sec=args.target_section_sec,
        min_section_sec=args.min_section_sec,
    )
    print(json.dumps({
        "artifact_role": result["artifact_role"],
        "source_section_map": str(Path(args.out)),
        "section_count": len(result.get("sections") or []),
        "boundary_count": len(result.get("boundaries") or []),
    }, ensure_ascii=False, indent=2))
    return result


def cmd_source_motion_profile(args):
    """Build edit-point motion/transition evidence for one long source video."""
    from video_pipeline_core.mv_cut import detect_shots
    from video_pipeline_core.source_motion_profile import build_source_motion_profile

    energy_curve = []
    if getattr(args, "soundtrack_probe", None):
        probe = json.loads(Path(args.soundtrack_probe).read_text(encoding="utf-8-sig"))
        features = probe.get("features") if isinstance(probe, dict) else {}
        curve = features.get("energy_curve") if isinstance(features, dict) else []
        energy_curve = curve if isinstance(curve, list) else []
    shot_boundaries = set()
    for start, end in detect_shots(args.video):
        if end > start:
            shot_boundaries.add(round(float(start), 3))
            shot_boundaries.add(round(float(end), 3))
    result = build_source_motion_profile(
        args.video,
        out_dir=args.out_dir,
        audio_curve=energy_curve,
        shot_boundaries=sorted(shot_boundaries),
        start_sec=args.start_sec,
        end_sec=args.end_sec,
        sample_sec=args.sample_sec,
    )
    print(json.dumps({
        "artifact_role": result["artifact_role"],
        "source_motion_profile": str(Path(args.out_dir) / "source_motion_profile.json"),
        "sample_count": result.get("sample_count"),
        "ranked_edit_point_count": len(result.get("ranked_edit_points") or []),
        "motion_points_sheet": str(Path(args.out_dir) / "source_motion_points.jpg"),
    }, ensure_ascii=False, indent=2))
    return result


def cmd_source_dialogue_script(args):
    """Build transcript-safe dialogue edit script from subtitle cues."""
    from video_pipeline_core.source_dialogue_script import write_dialogue_edit_script

    result = write_dialogue_edit_script(
        args.json3,
        out_dir=args.out_dir,
        rough_windows_path=args.rough_windows,
        target_sec=args.target_sec,
    )
    print(json.dumps({
        "artifact_role": result["artifact_role"],
        "dialogue_edit_script": str(Path(args.out_dir) / "dialogue_edit_script.json"),
        "source_transcript": str(Path(args.out_dir) / "source_transcript.json"),
        "dialogue_highlight_windows": str(Path(args.out_dir) / "dialogue_highlight_windows.json"),
        "planned_duration_sec": result.get("planned_duration_sec"),
        "clip_count": result.get("clip_count"),
        "next_action": result.get("next_action"),
    }, ensure_ascii=False, indent=2))
    return result


def cmd_material_wall_build(args):
    """Build a coarse material montage wall request for bounded review."""
    from video_pipeline_core import material_wall
    result = material_wall.write_material_wall_request(
        args.db,
        args.out_dir,
        args.out,
        photo_batch_size=args.photo_batch_size,
        video_batch_size=args.video_batch_size,
        limit=getattr(args, "limit", None),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_material_wall_review_apply(args):
    """Apply coarse material wall review decisions back to materials_db.json."""
    from video_pipeline_core import material_wall
    result = material_wall.apply_material_wall_review_file(
        args.db, args.verdict, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_material_db_slice_from_wall(args):
    """Create a bounded materials_db containing only assets shown in a wall request."""
    from video_pipeline_core import material_wall
    result = material_wall.slice_material_db_from_wall_request_file(
        args.db, args.wall_request, args.out)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_lineage_link(args):
    """M6a lineage: build the shooting-brief projection and/or link the need_id
    reference chain (needs -> brief -> satisfies -> contract). Reports dangling
    references only; makes NO coverage/delta decision."""
    from video_pipeline_core import material_lineage, project_material_map
    needs = _load_json(args.needs)
    if args.build_brief:
        brief = material_lineage.build_shooting_brief(needs)
        if args.out:
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(
                json.dumps(brief, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({"ok": True, "artifact": "shooting_brief",
                          "requirement_count": len(brief["requirements"])},
                         ensure_ascii=False, indent=2))
        return
    brief = _load_json(args.brief) if args.brief else None
    contract = _load_json(args.contract) if args.contract else None
    material_maps = None
    if args.project_map:
        material_maps = project_material_map.expand_project_material_map(
            _load_json(args.project_map))
    result = material_lineage.link_lineage(
        needs, shooting_brief=brief, material_maps=material_maps, contract=contract)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "errors": result["errors"],
                      "dangling": result["dangling"],
                      "need_count": len(result["chain"])},
                     ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError(f"lineage has {len(result['errors'])} dangling reference(s)")


def cmd_material_delta(args):
    """M6b: coverage delta (covered/thin/missing/excess) over the lineage join.
    Broken reference chain / invalid needs fail; never misread as missing."""
    from video_pipeline_core import material_delta, project_material_map
    needs = _load_json(args.needs)
    material_maps = None
    if args.project_map:
        material_maps = project_material_map.expand_project_material_map(
            _load_json(args.project_map))
    result = material_delta.compute_material_delta(needs, material_maps)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "errors": result["errors"],
                      "ready_for_build": result["ready_for_build"],
                      "blocks_ready_for_build": result["blocks_ready_for_build"],
                      "summary": result["summary"]}, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError(
            f"material_delta failed: {len(result['errors'])} reference/validation error(s)")


def cmd_material_generation_fallback(args):
    """MGF1: turn material_delta missing/thin needs into provider-neutral
    generated-asset requests. Output is a planning artifact only; generated
    assets still must return through material-map review as candidate evidence."""
    from video_pipeline_core import material_generation_fallback
    delta = _load_json(args.delta)
    result = material_generation_fallback.plan_material_generation_fallback(
        delta,
        material_needs=_load_json(args.needs) if args.needs else None,
        story_world=_load_json(args.story_world) if args.story_world else None,
        creative_concept=_load_json(args.creative_concept) if args.creative_concept else None,
        screenplay_beats=_load_json(args.screenplay_beats) if args.screenplay_beats else None,
        director_shot_plan=_load_json(args.director_shot_plan)
        if args.director_shot_plan else None,
    )
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"ok": result["ok"], "errors": result["errors"],
                      "summary": result["summary"]}, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("material generation fallback failed: "
                        + "; ".join(result["errors"]))


def cmd_generated_material_produce(args):
    """GMP1: produce generated material files from MGF1 jobs, then write generated
    manifest + material-map candidate evidence. The built-in renderer is a
    deterministic test renderer; real providers can write the same output shape."""
    from video_pipeline_core import generated_material_producer
    style_profile = _load_json(args.style_profile) if args.style_profile else None
    result = generated_material_producer.produce_generated_materials(
        _load_json(args.fallback),
        args.out_dir,
        material_needs=_load_json(args.needs) if args.needs else None,
        style_profile=style_profile,
        provider=args.provider,
        renderer=args.renderer,
        allow_test_renderer=args.allow_test_renderer,
    )
    print(json.dumps({"ok": result["ok"], "errors": result.get("errors", []),
                      "quality_gate": result.get("quality_gate"),
                      "summary": result["summary"]}, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("generated material production failed: "
                        + "; ".join(result.get("errors") or []))


def cmd_generated_material_import(args):
    """GMP2: import externally generated provider image files into the GMP
    artifact shape. This validates files and style anchors before writing
    candidate material-map evidence."""
    from video_pipeline_core import generated_material_producer
    style_profile = _load_json(args.style_profile) if args.style_profile else None
    provider_outputs = _load_json(args.provider_outputs)
    if isinstance(provider_outputs, dict):
        provider_outputs = dict(provider_outputs)
        provider_outputs["_path"] = args.provider_outputs
    result = generated_material_producer.produce_generated_materials_from_provider_outputs(
        _load_json(args.fallback),
        provider_outputs,
        args.out_dir,
        material_needs=_load_json(args.needs) if args.needs else None,
        style_profile=style_profile,
    )
    print(json.dumps({"ok": result["ok"], "errors": result.get("errors", []),
                      "quality_gate": result.get("quality_gate"),
                      "summary": result["summary"]}, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("generated material import failed: "
                        + "; ".join(result.get("errors") or []))


def cmd_generated_image_provider_packet(args):
    """GMP provider handoff: write executable prompts, target filenames, and
    provider-output import template for real image-generation tools."""
    from video_pipeline_core import generated_image_provider_packet
    style_profile = _load_json(args.style_profile) if args.style_profile else None
    result = generated_image_provider_packet.build_generated_image_provider_packet(
        _load_json(args.fallback),
        args.out_dir,
        style_profile=style_profile,
        providers=args.providers,
    )
    print(json.dumps({"ok": result["ok"], "errors": result.get("errors", []),
                      "refs": result.get("refs", {}),
                      "summary": result["summary"]}, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("generated image provider packet failed: "
                        + "; ".join(result.get("errors") or []))


def cmd_codex_imagegen_provider_fill(args):
    """Copy already-generated Codex imagegen files into a provider packet and
    write generated_provider_outputs.json for generated-material-import."""
    from video_pipeline_core import generated_image_provider_packet
    result = generated_image_provider_packet.fill_provider_outputs_from_codex_images(
        args.packet,
        image_files=args.image_files,
        generated_root=args.generated_root,
        out_path=args.out,
        provider=args.provider,
    )
    print(json.dumps({"ok": result["ok"], "errors": result.get("errors", []),
                      "refs": result.get("refs", {}),
                      "summary": result.get("summary", {})},
                     ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("codex imagegen provider fill failed: "
                        + "; ".join(result.get("errors") or []))


def cmd_image_agent_prompt_handoff(args):
    """Write a bounded prompt packet for an image-capable agent."""
    from video_pipeline_core import generated_image_provider_packet
    result = generated_image_provider_packet.build_image_agent_prompt_handoff(
        args.packet,
        out_dir=args.out_dir,
        max_items=args.max_items,
    )
    print(json.dumps({"ok": result["ok"], "errors": result.get("errors", []),
                      "refs": result.get("refs", {}),
                      "summary": result.get("summary", {})},
                     ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("image agent prompt handoff failed: "
                        + "; ".join(result.get("errors") or []))


def cmd_generated_material_review(args):
    """GMP4: apply explicit reviewer decisions to generated candidate material
    map edges, producing a reviewed project_material_map."""
    from video_pipeline_core import generated_material_review
    result = generated_material_review.apply_generated_material_review(
        _load_json(args.project_map),
        _load_json(args.verdict),
        _load_json(args.needs),
        quality_review=_load_json(args.quality_review) if args.quality_review else None,
    )
    print(json.dumps({"ok": result["ok"], "errors": result.get("errors", []),
                      "summary": result.get("summary")},
                     ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("generated material review failed: "
                        + "; ".join(result.get("errors") or []))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result["project_material_map"],
                                   ensure_ascii=False, indent=2),
                        encoding="utf-8")


def cmd_story_soul_blueprint(args):
    """SSB1: compile a high-level brief into story-world, concept, beats,
    director shot plan, material needs, generation manifest, and checklist."""
    from video_pipeline_core import story_soul_blueprint
    result = story_soul_blueprint.write_story_soul_blueprint(
        _load_json(args.brief),
        args.out_dir,
    )
    print(json.dumps({"ok": result["ok"], "errors": result.get("errors", []),
                      "refs": result.get("refs", {})},
                     ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("story soul blueprint failed: "
                        + "; ".join(result.get("errors") or []))


def cmd_story_soul_to_contract(args):
    """SSB2: compile story-soul-blueprint artifacts into segment_contract.json."""
    from video_pipeline_core import blueprint_to_contract as b2c
    from video_pipeline_core import spec_contract

    story_dir = Path(args.story_dir)
    if not story_dir.is_dir():
        raise ToolError(f"story dir not found: {story_dir}")

    def read_required(name):
        path = story_dir / name
        if not path.is_file():
            raise ToolError(f"missing story soul artifact: {path}")
        return _load_json(str(path))

    story = {
        "ok": True,
        "story_world": read_required("story_world.json"),
        "creative_concept": read_required("creative_concept.json"),
        "screenplay_beats": read_required("screenplay_beats.json"),
        "director_shot_plan": read_required("director_shot_plan.json"),
        "material_needs": read_required("material_needs.json"),
        "generation_manifest": read_required("generation_manifest.json"),
    }
    child_contracts = story["director_shot_plan"].get("stage0_child_contracts")
    if child_contracts:
        story["stage0_child_contracts"] = child_contracts

    contract = b2c.compile_story_soul_contract(story)
    validation = spec_contract.validate_segment_contract(contract)
    if not validation.get("ok"):
        raise ToolError("compiled story soul contract failed validation: "
                        + "; ".join(validation.get("errors") or []))
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({
        "ok": True,
        "out": str(out_path),
        "segments": len(contract.get("segments") or []),
    }, ensure_ascii=False, indent=2))


def cmd_video_intent_plan(args):
    """VIP0: write canonical Stage 0 video_intent.json without running later stages."""
    from video_pipeline_core.video_intent_planner import plan_video_intent
    payload = plan_video_intent(_load_json(args.brief))
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def cmd_video_intent_acceptance(args):
    from tools.video_intent_acceptance import run_video_intent_acceptance
    report = run_video_intent_acceptance()
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if not report.get("ok"):
        raise ToolError(f"video intent acceptance failed: {report.get('errors', ['unknown'])[0]}")


def cmd_material_map_lifecycle(args):
    """M6d: orchestrate the material-map lifecycle from whatever artifacts exist;
    emit the current stage + next action (+ a BUILD handoff only when build_ready).
    Reuses the canonical M6a-M6c tools; never renders."""
    from video_pipeline_core import material_map_lifecycle
    report = material_map_lifecycle.run_lifecycle(
        out_dir=args.out_dir, needs_ref=args.needs, maps_dir=args.maps_dir,
        project_map_ref=args.project_map, material_db_ref=args.material_db,
        contract_ref=args.contract, decisions_ref=args.decisions,
        categories_path=args.categories)
    Path(args.out_dir).mkdir(parents=True, exist_ok=True)
    (Path(args.out_dir) / "material_map_lifecycle.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"stage": report["stage"], "can_build": report["can_build"],
                      "entry_point": report["entry_point"],
                      "next_action": report["next_action"],
                      "blocking": report["blocking"]}, ensure_ascii=False, indent=2))
    if report["stage"] == "invalid":
        raise ToolError("material-map lifecycle is invalid: "
                        + "; ".join(report["blocking"]))


def cmd_material_revision(args):
    """M6c: apply ACCEPTED human delta decisions to a revised segment_contract.
    Writes both artifacts only on success; invalid input exits non-zero and
    writes no half-baked artifact."""
    from video_pipeline_core import material_revision
    contract = _load_json(args.contract)
    delta = _load_json(args.delta)
    decisions = _load_json(args.decisions)
    categories = None
    if getattr(args, "categories", None):
        from video_pipeline_core.spec_contract import load_material_categories
        categories = set(load_material_categories(args.categories))
    report, revised = material_revision.apply_revisions(
        contract, delta, decisions, categories=categories)
    if not report["ok"]:
        print(json.dumps({"ok": False, "errors": report["errors"]},
                         ensure_ascii=False, indent=2))
        raise ToolError(f"material_revision failed: {len(report['errors'])} error(s)")
    report["revised_contract"] = str(args.out_contract)
    try:
        material_revision.write_revision_artifacts(
            revised, report, args.out_contract, args.out_revision)
    except (ValueError, OSError, RuntimeError) as exc:
        raise ToolError(f"material_revision could not write artifacts: {exc}")
    print(json.dumps({"ok": True, "no_op": report["no_op"],
                      "ready_for_build": report["ready_for_build"],
                      "next_action": report["next_action"],
                      "unresolved_blocking_needs": report["unresolved_blocking_needs"],
                      "revised_contract": str(args.out_contract),
                      "material_revision": str(args.out_revision)},
                     ensure_ascii=False, indent=2))


def cmd_effect_collage_refs(args):
    """Convert reviewed material-map/Workbench still evidence into Remotion collage refs."""
    from video_pipeline_core.effect_collage_refs import write_collage_media_refs
    try:
        result = write_collage_media_refs(
            args.project_map,
            args.out,
            material_wall_review_verdict_path=args.wall_verdict,
            workbench_thumbnails_path=args.workbench_thumbnails,
            material_wall_request_path=args.wall_request,
            max_refs=args.max_refs,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect collage refs failed: {exc}") from exc
    print(json.dumps({
        "ok": result.get("ok"),
        "effect_collage_media_refs": str(args.out),
        "selected_count": result.get("diagnostics", {}).get("selected_count", 0),
        "next_action": result.get("next_action"),
    }, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise ToolError("effect collage refs produced no usable reviewed media refs")


def cmd_remotion_template_manifest(args):
    """Write the Remotion effect template capability/support manifest."""
    from video_pipeline_core.remotion_template_manifest import write_remotion_template_manifest
    try:
        manifest = write_remotion_template_manifest(
            args.out,
            dictionary_path=args.dictionary,
            reference_review_path=args.reference_review,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"remotion template manifest failed: {exc}") from exc
    print(json.dumps({
        "ok": True,
        "remotion_effect_capability_manifest": str(args.out),
        "summary": manifest.get("summary", {}),
    }, ensure_ascii=False, indent=2))


def cmd_remotion_prompt_pack(args):
    """FX4a: convert Brownfield adapter-route effect gaps into Remotion worker
    prompt jobs. This writes an artifact only; it does not run Remotion."""
    from video_pipeline_core import remotion_effects
    try:
        pack = remotion_effects.write_remotion_prompt_pack(
            args.request,
            args.effect_intent_plan,
            args.out,
            timeline_path=args.timeline,
            output_dir=args.output_dir,
            collage_refs_path=args.collage_refs,
        )
    except (OSError, ValueError) as exc:
        raise ToolError(f"remotion prompt pack failed: {exc}")
    print(json.dumps({
        "ok": True,
        "status": pack["status"],
        "summary": pack["summary"],
        "remotion_prompt_pack": str(args.out),
    }, ensure_ascii=False, indent=2))


def cmd_remotion_worker_outputs(args):
    """FX4b: validate Remotion worker output files against a prompt pack and
    write a Workbench-review artifact only when the outputs are valid."""
    from video_pipeline_core import remotion_effects
    try:
        result = remotion_effects.write_remotion_worker_review(
            args.prompt_pack,
            args.worker_outputs,
            args.out_review,
        )
    except (OSError, ValueError) as exc:
        raise ToolError(f"remotion worker output validation failed: {exc}")
    print(json.dumps({
        "ok": result["ok"],
        "errors": result.get("errors", []),
        "summary": result.get("summary", {}),
        "remotion_effect_review": str(args.out_review) if result["ok"] else None,
    }, ensure_ascii=False, indent=2))
    if not result["ok"]:
        raise ToolError("remotion worker outputs invalid: " + "; ".join(result.get("errors") or []))


def cmd_effect_render_verification(args):
    """FX4e: convert accepted Remotion review evidence into delivery-gate
    effect_render_verification.json. This does not render or composite."""
    from video_pipeline_core.effect_render_verification import write_effect_render_verification
    try:
        verification = write_effect_render_verification(
            args.effect_intent_plan,
            args.remotion_review,
            args.out,
            root=args.root,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"effect render verification failed: {exc}") from exc
    print(json.dumps({
        "ok": verification.get("pass"),
        "summary": verification.get("summary", {}),
        "effect_render_verification": str(args.out),
        "next_action": verification.get("next_action"),
    }, ensure_ascii=False, indent=2))
    if verification.get("pass") is not True:
        raise ToolError("effect render verification did not pass")


def cmd_remotion_worker_smoke(args):
    """FX4c: optionally run a Remotion-capable worker command over a prompt
    pack. --dry-run is deterministic and test-only; --command can call a real
    Remotion wrapper in a configured environment."""
    from video_pipeline_core import remotion_effects
    try:
        result = remotion_effects.write_remotion_worker_smoke(
            args.prompt_pack,
            args.out_worker_outputs,
            args.out_dir,
            dry_run=bool(args.dry_run),
            command_template=args.renderer_command,
        )
    except (OSError, ValueError) as exc:
        raise ToolError(f"remotion worker smoke failed: {exc}")
    print(json.dumps({
        "ok": result.get("status") == "rendered",
        "status": result.get("status"),
        "summary": result.get("summary", {}),
        "remotion_worker_outputs": str(args.out_worker_outputs),
    }, ensure_ascii=False, indent=2))
    if result.get("status") != "rendered":
        raise ToolError("remotion worker smoke did not render all jobs")


def cmd_remotion_composite_draft(args):
    """FX4d: composite reviewed/accepted Remotion outputs into a non-canonical
    draft video. Refuses final.mp4 and other canonical outputs."""
    from video_pipeline_core import remotion_effects
    try:
        result = remotion_effects.write_remotion_composite_draft(
            args.review,
            args.base_video,
            args.out,
            args.report_out,
            ffmpeg=args.ffmpeg,
            dry_run=bool(args.dry_run),
        )
    except (OSError, ValueError, RuntimeError) as exc:
        raise ToolError(f"remotion composite draft failed: {exc}")
    print(json.dumps({
        "ok": result.get("ok"),
        "status": result.get("status"),
        "applied_count": result.get("applied_count"),
        "out": result.get("out"),
        "report": str(args.report_out) if args.report_out else None,
    }, ensure_ascii=False, indent=2))


def cmd_visual_diversity_coverage(args):
    """VD1: report real project-map VD0 label coverage; never rank material."""
    from video_pipeline_core import visual_diversity_coverage
    result = visual_diversity_coverage.write_visual_diversity_coverage(
        args.project_map,
        args.out,
        min_visual_family_coverage=args.min_visual_family_coverage,
        min_angle_scale_coverage=args.min_angle_scale_coverage,
        consistency_review_paths=args.consistency_review,
        min_consistency_ratio=args.min_consistency_ratio,
        min_consistency_scenes=args.min_consistency_scenes,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_visual_diversity_review(args):
    """VD1: apply an Agent-authored shallow-label review to a project map."""
    from video_pipeline_core import visual_diversity_review
    try:
        result = visual_diversity_review.write_visual_diversity_review(
            args.project_map, args.review, args.out)
    except (OSError, ValueError) as exc:
        raise ToolError(f"visual diversity review failed: {exc}")
    print(json.dumps({
        "ok": True,
        "applied_scene_count": result["applied_scene_count"],
        "project_material_map": str(args.out),
    }, ensure_ascii=False, indent=2))


def cmd_visual_family_normalize(args):
    """VD1.1: normalize a visual diversity review against a vocabulary contract."""
    from video_pipeline_core import visual_family_vocabulary
    try:
        result = visual_family_vocabulary.write_normalized_review(
            args.review, args.vocabulary, args.out
        )
    except (OSError, ValueError) as exc:
        raise ToolError(f"visual family normalization failed: {exc}")
    print(json.dumps({
        "ok": True,
        "normalized_review": str(args.out),
    }, ensure_ascii=False, indent=2))


def cmd_semantic_novelty_audit(args):
    """M5a Node 11: perceptual de-duplication of timeline compositions."""
    from video_pipeline_core import semantic_novelty_audit
    timeline = _load_json(args.timeline)
    result = semantic_novelty_audit.write_semantic_novelty_audit(
        timeline,
        args.out,
        video_path=args.video,
        max_distance=args.max_distance,
        min_distinct_ratio=args.min_distinct_ratio,
        max_similar_run_sec=args.max_similar_run_sec,
    )
    print(json.dumps(result["result"], ensure_ascii=False, indent=2))


def cmd_action_progression_audit(args):
    """M5b Node 11: action-phase coverage over segments declaring required_functions."""
    from video_pipeline_core import action_progression
    segments = _load_json(args.segments)
    if isinstance(segments, dict):
        segments = segments.get("segments") or []
    result = action_progression.write_action_progression_audit(
        segments,
        args.out,
        min_coverage=args.min_coverage,
    )
    print(json.dumps(result["result"], ensure_ascii=False, indent=2))


def cmd_jumpcut_plan(args):
    from video_pipeline_core.jumpcut import write_jumpcut_plan
    material_map = _load_json(args.material_map)
    result = write_jumpcut_plan(
        material_map, args.out, min_remove_silence_sec=args.min_silence,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_jumpcut_apply(args):
    from video_pipeline_core.jumpcut import apply_jumpcut
    result = apply_jumpcut(_load_json(args.plan), args.out)
    Path(args.lineage).parent.mkdir(parents=True, exist_ok=True)
    Path(args.lineage).write_text(
        json.dumps(result["lineage"], ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_jumpcut_review(args):
    from video_pipeline_core.jumpcut import apply_jumpcut_verdict
    result = apply_jumpcut_verdict(_load_json(args.plan), _load_json(args.verdict))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.out).write_text(
        json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8",
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_caption_audit(args):
    """P1 Node 11/12: caption gap/overlap/reading-speed audit."""
    from video_pipeline_core import caption_audit
    srt = getattr(args, "srt", None)
    captions_path = getattr(args, "captions", None)
    if srt:
        captions = caption_audit.parse_srt(Path(srt).read_text(encoding="utf-8"))
    elif captions_path:
        data = _load_json(captions_path)
        captions = data.get("captions") if isinstance(data, dict) else data
    else:
        raise ToolError("caption-audit requires a captions JSON path or --srt")
    kwargs = {}
    if getattr(args, "max_gap_sec", None) is not None:
        kwargs["max_gap_sec"] = args.max_gap_sec
    if getattr(args, "max_cps", None) is not None:
        kwargs["max_chars_per_sec"] = args.max_cps
    result = caption_audit.write_caption_audit(captions or [], args.out, **kwargs)
    print(json.dumps(result["result"], ensure_ascii=False, indent=2))


def cmd_keyframe_grid(args):
    """P1 Node 12: deterministic keyframe grid / contact sheet."""
    from video_pipeline_core import keyframe_grid
    meta = keyframe_grid.generate_keyframe_grid(
        args.video, args.out,
        sample_count=getattr(args, "samples", None) or 12,
        columns=getattr(args, "columns", None) or 4,
    )
    print(json.dumps(meta, ensure_ascii=False, indent=2))
    out = Path(args.out)
    if meta.get("sample_count", 0) <= 0 or not out.exists() or out.stat().st_size == 0:
        raise ToolError(
            f"keyframe-grid produced no usable frames from {args.video} "
            "(unreadable/zero-duration video?)")


def cmd_sampling_coverage(args):
    """Reviewer perception sampling coverage verification."""
    from video_pipeline_core.sampling_coverage import write_sampling_coverage_report

    result = write_sampling_coverage_report(
        args.sampling_plan,
        args.shots,
        args.out,
        audio_anchors=getattr(args, "anchors", None),
        tolerance_sec=getattr(args, "tolerance_sec", None) or 0.35,
        max_gap_sec=getattr(args, "max_gap_sec", None) or 4.0,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_montage_wall(args):
    """Canonical reviewer montage wall renderer."""
    from video_pipeline_core.montage_wall import write_montage_wall

    result = write_montage_wall(
        args.video,
        args.sampling_plan,
        args.coverage_report,
        args.out,
        args.sidecar,
        profile=getattr(args, "profile", None) or "material_wall",
        max_cells_per_page=getattr(args, "max_cells_per_page", None) or 96,
        max_page_height_px=getattr(args, "max_page_height_px", None) or 4096,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_perception_field_check(args):
    """Run the observation-only perception chain and write field metrics."""
    import time

    from video_pipeline_core import mv_cut
    from video_pipeline_core.montage_wall import write_montage_wall
    from video_pipeline_core.sampling_coverage import write_sampling_coverage_report
    from video_pipeline_core.sampling_planner import write_sampling_plan
    from video_pipeline_core.soundtrack_probe import write_soundtrack_probe

    video = Path(args.video)
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)
    max_cells_per_page = int(getattr(args, "max_cells_per_page", None) or 96)
    max_page_height_px = int(getattr(args, "max_page_height_px", None) or 4096)
    stage_seconds: dict[str, float] = {}

    def timed(stage: str, fn):
        start = time.perf_counter()
        result = fn()
        stage_seconds[stage] = round(time.perf_counter() - start, 3)
        return result

    shots_path = out_dir / "shots.json"
    probe_path = out_dir / "soundtrack_probe.json"
    plan_path = out_dir / "sampling_plan.json"
    coverage_path = out_dir / "sampling_coverage_report.json"
    wall_path = out_dir / "montage_wall.png"
    sidecar_path = out_dir / "montage_wall.json"
    report_path = out_dir / "perception_field_report.json"

    shots_raw = timed("shot_detection", lambda: mv_cut.detect_shots(str(video)))
    shots = [
        {"shot_id": f"shot_{index:03d}", "start_sec": round(float(start), 3), "end_sec": round(float(end), 3)}
        for index, (start, end) in enumerate(shots_raw, start=1)
    ]
    shots_path.write_text(json.dumps(shots, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    probe = timed("soundtrack_probe", lambda: write_soundtrack_probe(video, probe_path))
    anchors = probe.get("sampling_anchors") if isinstance(probe.get("sampling_anchors"), dict) else {}
    tolerance_sec = float(getattr(args, "tolerance_sec", None) or 0.35)
    plan = timed(
        "sampling_plan",
        lambda: write_sampling_plan(
            video,
            shots,
            plan_path,
            audio_anchors=anchors,
            anchor_drift_budget_sec=tolerance_sec,
        ),
    )
    coverage = timed(
        "sampling_coverage",
        lambda: write_sampling_coverage_report(
            plan_path,
            shots_path,
            coverage_path,
            audio_anchors=anchors,
            tolerance_sec=tolerance_sec,
        ),
    )
    wall = timed(
        "montage_wall",
        lambda: write_montage_wall(
            video,
            plan_path,
            coverage_path,
            wall_path,
            sidecar_path,
            profile="material_wall",
            max_cells_per_page=max_cells_per_page,
            max_page_height_px=max_page_height_px,
        ),
    )

    reason_counts: dict[str, int] = {}
    for sample in plan.get("samples") or []:
        if not isinstance(sample, dict):
            continue
        for reason in sample.get("reasons") or [sample.get("reason")]:
            if reason:
                reason_counts[str(reason)] = reason_counts.get(str(reason), 0) + 1
    page_violations = [
        page for page in wall.get("pages") or []
        if int(page.get("cell_count") or 0) > max_cells_per_page
        or int(page.get("height_px") or 0) > max_page_height_px
    ]
    ok = bool(coverage.get("pass")) and not page_violations
    fail_reason = None
    if not coverage.get("pass"):
        fail_reason = "coverage_failed"
    elif page_violations:
        fail_reason = "wall_page_limit_exceeded"
    report = {
        "artifact_role": "perception_field_report",
        "version": 1,
        "ok": ok,
        "source_video": str(video),
        "artifacts": {
            "shots": str(shots_path),
            "soundtrack_probe": str(probe_path),
            "sampling_plan": str(plan_path),
            "sampling_coverage_report": str(coverage_path),
            "montage_wall": str(sidecar_path),
        },
        "stage_seconds": stage_seconds,
        "shot_count": len(shots),
        "sample_count": len(plan.get("samples") or []),
        "reason_counts": reason_counts,
        "coverage": {
            "pass": bool(coverage.get("pass")),
            "gap_count": len(coverage.get("gaps") or []),
            "gaps": coverage.get("gaps") or [],
        },
        "wall": {
            "page_count": len(wall.get("pages") or []),
            "page_image_paths": wall.get("page_image_paths") or [],
            "pages": wall.get("pages") or [],
            "page_violations": page_violations,
        },
        "fail_reason": fail_reason,
        "limitations": [
            "Perception field check observes coverage, anchors, and wall bounds only; it does not judge visual quality.",
            "Passing coverage does not promote any asset or approve final delivery.",
        ],
    }
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not ok:
        raise ToolError(f"perception field check failed: {fail_reason}")


def cmd_visual_audit(args):
    """P1 Node 12: keyframe-grid generation + mechanical visual audit."""
    from video_pipeline_core import keyframe_grid, visual_audit
    grid_path = getattr(args, "grid", None) or str(Path(args.out).with_name("keyframe_grid.jpg"))
    meta = keyframe_grid.generate_keyframe_grid(
        args.video, grid_path,
        sample_count=getattr(args, "samples", None) or 12,
        columns=getattr(args, "columns", None) or 4,
    )
    result = visual_audit.write_visual_audit(meta, args.out)
    print(json.dumps(result["result"], ensure_ascii=False, indent=2))


def cmd_verify_evidence(args):
    from video_pipeline_core.verify_evidence import write_verify_evidence
    result = write_verify_evidence(
        args.video, _load_json(args.timeline), args.out_dir,
        overview_samples=getattr(args, "overview_samples", 48),
        chapter_samples=getattr(args, "chapter_samples", 16),
        critical_samples=getattr(args, "critical_samples", 32),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_final_product_verify(args):
    """Build final product eye/ear verify bundle."""
    from video_pipeline_core.final_product_verify import build_final_product_verify_bundle

    result = build_final_product_verify_bundle(
        args.video,
        out_dir=args.out_dir,
        sample_count=getattr(args, "samples", None) or 12,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


def cmd_replay_acceptance(args):
    from video_pipeline_core.replay_acceptance import (
        write_material_first_golden_path_report,
        write_probe_repair_replay_report,
        write_replay_report,
    )
    if getattr(args, "scenario", None):
        if args.scenario == "probe-repair-20260704":
            result = write_probe_repair_replay_report(args.out)
        elif args.scenario == "material-first-golden-path":
            result = write_material_first_golden_path_report(args.out)
        else:
            raise ToolError(f"unknown replay acceptance scenario: {args.scenario}")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        if not result.get("ok"):
            raise ToolError(f"replay acceptance scenario failed: {args.scenario}")
        return
    if not (getattr(args, "timeline", None) and getattr(args, "gates", None) and getattr(args, "verdicts", None)):
        raise ToolError("replay-acceptance requires timeline, --gates, and --verdicts unless --scenario is used")
    kwargs = {
        "gate_artifacts": _load_json(args.gates),
        "judge_verdicts": _load_json(args.verdicts),
    }
    if getattr(args, "jumpcut_plan", None):
        kwargs["jumpcut_plan"] = _load_json(args.jumpcut_plan)
    if getattr(args, "new_visual_audit", None):
        kwargs["new_visual_audit"] = _load_json(args.new_visual_audit)
    if getattr(args, "adaptation", None):
        kwargs["adaptation_decisions"] = _load_json(args.adaptation)
    result = write_replay_report(_load_json(args.timeline), args.out, **kwargs)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_capcut_draft(args):
    """P3 (optional): write a provider-neutral CapCut draft manifest from a timeline."""
    from video_pipeline_core import capcut_backend
    timeline = _load_json(args.timeline)
    res = capcut_backend.write_draft_manifest(
        timeline, args.out, project_name=getattr(args, "project", None))
    print(json.dumps(res["manifest"], ensure_ascii=False, indent=2))


def cmd_capcut_finalize(args):
    """P3: finalize CapCut exported video by mixing BGM and adding outro card."""
    from video_pipeline_core import capcut_backend
    stats = capcut_backend.finalize_export(
        capcut_export_mp4=args.video,
        final_mp4=args.out,
        bgm_path=args.bgm,
        outro_title=args.outro_title,
        outro_address=args.outro_address,
        outro_extra=getattr(args, "outro_extra", None),
        bgm_volume=args.bgm_vol if args.bgm_vol is not None else 0.25,
    )
    print(json.dumps({"ok": True, "stats": stats}, ensure_ascii=False, indent=2))



def cmd_blueprint_coverage(args):
    """WHY layer: two-way narrative blueprint gate (beats <-> segments).

    Exits non-zero when a beat is unrealized (dropped_beat) or a segment cites a
    missing beat (invalid_ref), so it can act as a build gate.
    """
    from video_pipeline_core import blueprint as bp_mod
    blueprint = _load_json(args.blueprint)
    contract = _load_json(args.contract)
    v = bp_mod.validate_blueprint(blueprint)
    if not v["ok"]:
        print(json.dumps({"ok": False, "stage": "validate_blueprint", **v},
                         ensure_ascii=False, indent=2))
        sys.exit(2)
    if args.out:
        result = bp_mod.write_blueprint_coverage(blueprint, contract, args.out)
    else:
        result = bp_mod.beat_coverage(blueprint, contract)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result["pass"]:
        sys.exit(1)


def cmd_blueprint_compile(args):
    """Compile a narrative blueprint markdown file into structured JSON."""
    src = Path(args.blueprint)
    if not src.exists():
        raise ToolError(f"找不到 blueprint 檔案：{args.blueprint}")
    from video_pipeline_core.blueprint_compile import compile_blueprint_md
    md_text = src.read_text(encoding="utf-8")
    try:
        blueprint_json = compile_blueprint_md(md_text)
    except Exception as e:
        raise ToolError(f"編譯 blueprint 失敗: {e}")
    out = args.out or src.with_suffix(".json").name
    Path(out).write_text(json.dumps(blueprint_json, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "file": out}))


def cmd_blueprint_to_contract(args):
    """Compile blueprint.json + per-beat decisions.json -> segment_contract.json.

    The director skill writes a compact decisions table (content_pattern + key
    imagery/pace per beat); this fills the mechanical lexicon half deterministically
    so weights/beat_ref/density fields are always wired correctly. Validates output
    and the two-way beat gate; exits non-zero on either failure.
    """
    from video_pipeline_core import blueprint_to_contract as b2c
    from video_pipeline_core import spec_contract, blueprint as bp_mod
    blueprint = _load_json(args.blueprint)
    decisions = _load_json(args.decisions)
    material_needs = _load_json(args.material_needs) if getattr(args, "material_needs", None) else None
    music = _load_json(args.music) if getattr(args, "music", None) else None
    try:
        contract = b2c.compile_contract(blueprint, decisions, material_needs=material_needs, music=music)
    except Exception as e:
        raise ToolError(f"編譯 contract 失敗: {e}")
    v = spec_contract.validate_segment_contract(contract)
    cov = bp_mod.beat_coverage(blueprint, contract)
    out = args.out or "segment_contract.json"
    Path(out).write_text(json.dumps(contract, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"status": "ok", "file": out, "segments": len(contract["segments"]),
                      "valid": v.get("ok", v.get("valid")), "beat_coverage_pass": cov["pass"],
                      "dropped": cov["dropped"], "invalid_refs": cov["invalid_refs"]},
                     ensure_ascii=False, indent=2))
    if not (v.get("ok", v.get("valid")) and cov["pass"]):
        sys.exit(1)



def cmd_creator_profile(args):
    """P2: manage creator_profile.json (stable creator/channel defaults)."""
    from video_pipeline_core import creator_profile
    if getattr(args, "init", False):
        path = creator_profile.write_creator_profile(args.out)
        print(json.dumps({"ok": True, "creator_profile": path}, ensure_ascii=False, indent=2))
        return
    profile = (creator_profile.load_creator_profile(args.profile)
               if getattr(args, "profile", None) else creator_profile.default_creator_profile())
    brief = _load_json(args.brief) if getattr(args, "brief", None) else {}
    result = creator_profile.resolve_defaults(profile, brief)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_search(args):
    """搜尋 YouTube，回傳影片清單"""
    limit = args.limit or 5
    query = f"ytsearch{limit}:{args.query}"
    result = run([YTDLP, query, "--dump-json", "--flat-playlist", "--no-warnings"])
    if result.returncode != 0:
        raise ToolError(f"yt-dlp search failed: {result.stderr}")
    items = []
    for line in result.stdout.strip().splitlines():
        if not line:
            continue
        try:
            d = json.loads(line)
            items.append({
                "id": d.get("id"),
                "title": d.get("title"),
                "url": d.get("url") or f"https://www.youtube.com/watch?v={d.get('id')}",
                "duration": d.get("duration"),
                "channel": d.get("channel") or d.get("uploader"),
                "view_count": d.get("view_count"),
                "description": (d.get("description") or "")[:200],
            })
        except json.JSONDecodeError:
            continue
    print(json.dumps(items, ensure_ascii=False, indent=2))


def cmd_meta(args):
    """取得單支影片 metadata"""
    result = run([YTDLP, args.url, "--dump-json", "--no-warnings", "--no-download"])
    if result.returncode != 0:
        raise ToolError(f"yt-dlp meta failed: {result.stderr}")
    d = json.loads(result.stdout)
    out = {
        "id": d.get("id"),
        "title": d.get("title"),
        "url": args.url,
        "duration": d.get("duration"),
        "channel": d.get("channel") or d.get("uploader"),
        "upload_date": d.get("upload_date"),
        "view_count": d.get("view_count"),
        "like_count": d.get("like_count"),
        "description": (d.get("description") or "")[:500],
        "tags": d.get("tags", [])[:10],
        "chapters": d.get("chapters") or [],
    }
    print(json.dumps(out, ensure_ascii=False, indent=2))


def cmd_download(args):
    """下載影片（可指定時間區間）"""
    out_path = args.out or "downloaded.mp4"
    cmd = [YTDLP, args.url, "-o", out_path, "--no-warnings", "--merge-output-format", "mp4",
           "--ffmpeg-location", str(Path(FFMPEG).parent)]

    if args.start or args.end:
        start = args.start or "0"
        end = args.end or "inf"
        cmd += ["--download-sections", f"*{start}-{end}"]
        cmd += ["--force-keyframes-at-cuts"]

    result = run(cmd, capture=False)
    if result.returncode != 0:
        raise ToolError("yt-dlp download failed")
    size = Path(out_path).stat().st_size if Path(out_path).exists() else 0
    print(json.dumps({"status": "ok", "file": out_path, "size_bytes": size}))


def cmd_probe(args):
    """取得本地影片資訊"""
    result = run([
        FFPROBE, "-v", "quiet", "-print_format", "json",
        "-show_format", "-show_streams", args.file
    ])
    if result.returncode != 0:
        raise ToolError(f"ffprobe failed: {result.stderr}")
    d = json.loads(result.stdout)
    fmt = d.get("format", {})
    streams = d.get("streams", [])
    video = next((s for s in streams if s.get("codec_type") == "video"), {})
    audio = next((s for s in streams if s.get("codec_type") == "audio"), {})
    print(json.dumps({
        "file": args.file,
        "duration_sec": float(fmt.get("duration", 0)),
        "size_bytes": int(fmt.get("size", 0)),
        "video": {
            "codec": video.get("codec_name"),
            "width": video.get("width"),
            "height": video.get("height"),
            "fps": video.get("r_frame_rate"),
        },
        "audio": {
            "codec": audio.get("codec_name"),
            "sample_rate": audio.get("sample_rate"),
            "channels": audio.get("channels"),
        },
    }, ensure_ascii=False, indent=2))


def cmd_cut(args):
    """裁剪影片片段"""
    out = args.out or "cut_output.mp4"
    cmd = [FFMPEG, "-y", "-i", args.file]
    if args.start:
        cmd += ["-ss", args.start]
    if args.end:
        cmd += ["-to", args.end]
    cmd += ["-c", "copy", out]
    result = run(cmd)
    if result.returncode != 0:
        raise ToolError(f"ffmpeg cut failed: {result.stderr}")
    print(json.dumps({"status": "ok", "file": out}))


def _get_resolution(fpath: str):
    """回傳 (width, height) 或 None"""
    r = run([FFPROBE, "-v", "quiet", "-print_format", "json", "-show_streams", fpath])
    if r.returncode != 0:
        return None
    d = json.loads(r.stdout)
    v = next((s for s in d.get("streams", []) if s.get("codec_type") == "video"), {})
    w, h = v.get("width"), v.get("height")
    return (w, h) if w and h else None


def cmd_concat(args):
    """串接多個影片（自動統一解析度至最大尺寸）"""
    out = args.out or "concat_output.mp4"

    # 偵測所有素材的解析度
    resolutions = [_get_resolution(f) for f in args.files]
    valid = [r for r in resolutions if r]
    target_w = max(r[0] for r in valid) if valid else 1920
    target_h = max(r[1] for r in valid) if valid else 1080
    need_scale = any(r != (target_w, target_h) for r in valid)

    files_to_concat = list(args.files)

    if need_scale:
        scaled = []
        for i, fpath in enumerate(args.files):
            res = resolutions[i]
            if res == (target_w, target_h):
                scaled.append(fpath)
            else:
                scaled_path = fpath.replace(".mp4", f"_scaled{target_w}x{target_h}.mp4")
                scale_cmd = [
                    FFMPEG, "-y", "-i", fpath,
                    "-vf", f"scale={target_w}:{target_h}",
                    "-c:v", "libx264", "-crf", "23", "-c:a", "copy",
                    scaled_path,
                ]
                r = run(scale_cmd)
                if r.returncode != 0:
                    raise ToolError(f"scale failed for {fpath}: {r.stderr}")
                scaled.append(scaled_path)
        files_to_concat = scaled

    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
        for fpath in files_to_concat:
            abs_path = str(Path(fpath).resolve()).replace('\\', '/')
            f.write(f"file '{abs_path}'\n")
        list_file = f.name

    cmd = [FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", list_file, "-c", "copy", out]
    result = run(cmd)
    os.unlink(list_file)

    # 清掉自動 scale 的暫存檔
    if need_scale:
        for fpath in files_to_concat:
            if "_scaled" in fpath and Path(fpath).exists():
                os.unlink(fpath)

    if result.returncode != 0:
        raise ToolError(f"ffmpeg concat failed: {result.stderr}")
    print(json.dumps({"status": "ok", "file": out, "resolution": f"{target_w}x{target_h}"}))


def cmd_subtitle(args):
    """用 faster-whisper 產生字幕 .srt"""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ToolError("faster-whisper 未安裝，請執行: pip3 install faster-whisper --break-system-packages")

    out = args.out or (Path(args.file).stem + ".srt")
    lang = args.language or None
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(args.file, language=lang, beam_size=5)

    def fmt_ts(seconds: float) -> str:
        h = int(seconds // 3600)
        m = int((seconds % 3600) // 60)
        s = seconds % 60
        return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")

    lines = []
    for i, seg in enumerate(segments, 1):
        lines.append(str(i))
        lines.append(f"{fmt_ts(seg.start)} --> {fmt_ts(seg.end)}")
        lines.append(seg.text.strip())
        lines.append("")

    Path(out).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "ok", "file": out, "language": info.language}))


def cmd_validate(args):
    """劇本模糊消除 — 在 script-run 之前檢查劇本品質

    檢查項目（阻塞 error / 警告 warning / 通過 ok）：
    ┌──────────────────────────────┬──────────┬─────────────────┐
    │ 項目                         │ error    │ warning         │
    ├──────────────────────────────┼──────────┼─────────────────┤
    │ search_query 詞數            │ < 2 詞   │ 2 詞            │
    │ search_query 過於泛用        │ 純單詞   │ 缺年份/地點限定  │
    │ duration_sec                 │ < 5s     │ 5–8s 或 > 90s  │
    │ 字幕閱讀速度（中文字/秒）    │ > 8 字/s │ 5–8 字/s       │
    │ text 欄位空白                │ —        │ 無字幕警告      │
    │ search_query 段落間重複      │ 完全同   │ —               │
    │ 總段落數                     │ < 2 段   │ —               │
    └──────────────────────────────┴──────────┴─────────────────┘

    輸出 JSON：
    {
      "status": "ok" | "warning" | "error",
      "can_run": true | false,
      "issues": [...],
      "summary": "..."
    }
    """
    src = Path(args.script)
    if not src.exists():
        raise ToolError(f"找不到劇本檔：{args.script}")
    raw = json.loads(src.read_text(encoding="utf-8"))
    # 支援 {style, segments} wrapper 或純 segments list
    segments = raw.get("segments", []) if isinstance(raw, dict) else raw
    top_bgm = raw.get("bgm") if isinstance(raw, dict) else None
    top_style = (raw.get("style") if isinstance(raw, dict) else None)

    issues = []

    def add(seg_idx, field, level, message, suggestion=""):
        issues.append({
            "segment": seg_idx,
            "field": field,
            "level": level,
            "message": message,
            "suggestion": suggestion,
        })

    # ── 整體結構 ──────────────────────────────────────────────
    if len(segments) < 2:
        add(0, "structure", "error",
            f"劇本只有 {len(segments)} 段，無法構成完整影片",
            "至少需要 2 段（開頭 + 結尾）")
    _GRADES = set(GRADE_PRESETS)
    _MOODS = set(BGM_MOODS)
    _TRANS = {"fade", "wipeleft", "wiperight", "wipeup", "wipedown", "slideleft",
              "slideright", "slideup", "slidedown", "circleopen", "circleclose",
              "dissolve", "smoothleft", "smoothright", "radial", "diagtl", "diagtr",
              "diagbl", "diagbr", "cut"}
    _STYLES = {"narrative", "mv", "promo"}
    if isinstance(top_bgm, dict):
        # 真曲抓取：{"query": "...", "source": "yt"} → music-fetch 解析
        if not (top_bgm.get("query") or top_bgm.get("mood")):
            add(0, "bgm", "error", "bgm 物件需要 query 或 mood 欄位",
                '例：{"query": "lofi calm piano", "source": "yt"}')
    elif top_bgm and top_bgm not in _MOODS and not Path(top_bgm).exists():
        add(0, "bgm", "error", f"未知 bgm 情境：「{top_bgm}」",
            f"請用 {'/'.join(sorted(_MOODS))}、檔案路徑、或 {{\"query\":...}} 抓真曲")
    if top_style and top_style not in _STYLES:
        add(0, "style", "error", f"未知 style：「{top_style}」", f"請用 {'/'.join(sorted(_STYLES))}")

    # 檢查 search_query 是否有重複
    queries = [s.get("search_query", "").strip().lower() for s in segments]
    for i, q in enumerate(queries):
        for j, q2 in enumerate(queries):
            if i < j and q and q == q2:
                add(i + 1, "search_query", "error",
                    f"段落 {i+1} 與段落 {j+1} 的 search_query 完全相同",
                    "請使用不同的搜尋詞，否則會下載到同一支影片")

    # ── 逐段檢查 ─────────────────────────────────────────────
    for i, seg in enumerate(segments):
        idx = seg.get("segment", i + 1)

        # effects/style 值域檢查（grade/transition/style 打錯字會讓 render 崩）
        fx = seg.get("effects") or {}
        if fx.get("grade") and fx["grade"] not in _GRADES:
            add(idx, "grade", "error", f"未知 grade：「{fx['grade']}」（別跟 bgm 情境搞混）",
                f"請用 {'/'.join(sorted(_GRADES))}")
        if fx.get("transition") and fx["transition"] not in _TRANS:
            add(idx, "transition", "error", f"未知 transition：「{fx['transition']}」",
                "見 ALLOWED_TRANSITIONS（fade/slide*/wipe*/circle*/dissolve/radial/cut…）")
        if seg.get("style") and seg["style"] not in _STYLES:
            add(idx, "style", "error", f"未知段落 style：「{seg['style']}」", f"請用 {'/'.join(sorted(_STYLES))}")
        if seg.get("layout") and seg["layout"] not in ("collage", "framed", "montage"):
            add(idx, "layout", "error", f"未知 layout：「{seg['layout']}」", "請用 collage / framed / montage")

        # 片頭/片尾段（kind=title）、學員自有素材（source=local）：不搜素材，跳過 search_query 檢查
        if seg.get("kind") == "title" or seg.get("source") == "local":
            if seg.get("source") == "local" and not seg.get("file") and not seg.get("local_file"):
                add(idx, "file", "error", "source=local 但缺 file 路徑", "請指定學員素材檔路徑")
            continue

        # search_query — 中文優先（Pexels/Pixabay 加 zh-TW locale 對中文命中良好）
        query = seg.get("search_query", "").strip()
        has_cjk = any("一" <= c <= "鿿" for c in query)
        if not query:
            add(idx, "search_query", "error",
                "search_query 欄位空白",
                "請填入搜尋關鍵字（中文料理／場景名最直接，如『胡椒餅』『鐵板料理』）")
        elif has_cjk:
            # 中文：以字數判斷，不用空白切詞（中文沒有詞邊界）
            cjk_chars = sum(1 for c in query if "一" <= c <= "鿿")
            if cjk_chars < 2:
                add(idx, "search_query", "warning",
                    f"search_query 過短：「{query}」",
                    "建議用具體的料理名或場景（如『鐵板料理』『夜市 人潮』）")
            # 詞太多會稀釋命中（如『胡椒餅 炭烤 夜市』反而搜不準）
            if len(query.split()) >= 3:
                add(idx, "search_query", "warning",
                    f"search_query 詞數偏多：「{query}」",
                    "中文搜尋用 1–2 個核心關鍵字最準，太多詞會稀釋結果")
        else:
            words = query.split()
            if len(words) < 2:
                add(idx, "search_query", "error",
                    f"search_query 只有 {len(words)} 個詞：「{query}」",
                    "英文過於泛用，請加入主題或限定詞；或改用中文關鍵字")
            vague_terms = {"ai", "video", "news", "latest", "new", "best", "top",
                           "technology", "tech", "world", "people", "life"}
            if set(w.lower() for w in words) <= vague_terms:
                add(idx, "search_query", "error",
                    f"search_query 全是泛用詞：「{query}」",
                    "請加入具體主題，或改用中文料理／場景關鍵字")

        # duration_sec
        duration = float(seg.get("duration_sec", 0))
        if duration < 5:
            add(idx, "duration_sec", "error",
                f"duration_sec = {duration}s，過短無法支撐段落",
                "建議最少 8 秒，一般段落 15–30 秒")
        elif duration <= 8:
            add(idx, "duration_sec", "warning",
                f"duration_sec = {duration}s，偏短",
                "建議至少 10 秒以讓觀眾看清楚字幕和畫面")
        elif duration > 90:
            add(idx, "duration_sec", "warning",
                f"duration_sec = {duration}s，單段超過 90 秒",
                "建議拆成多段，或確認 YouTube 素材有足夠長度")

        # 字幕閱讀速度
        text = seg.get("text", "").strip()
        if not text:
            add(idx, "text", "warning",
                "text 欄位空白，這段不會有中文字幕",
                "如果這段需要字幕，請填入旁白文字")
        else:
            # 中文字符數 / 秒（去除標點）
            import unicodedata
            zh_chars = sum(1 for c in text
                           if unicodedata.category(c).startswith("L")
                           and "一" <= c <= "鿿")
            if duration > 0:
                cps = zh_chars / duration  # chars per second
                if cps > 8:
                    add(idx, "text", "error",
                        f"字幕閱讀速度 {cps:.1f} 字/秒（{zh_chars} 字 / {duration}s），觀眾來不及讀",
                        "建議縮短文字到 {:.0f} 字以內，或延長 duration_sec".format(duration * 6))
                elif cps > 5:
                    add(idx, "text", "warning",
                        f"字幕閱讀速度 {cps:.1f} 字/秒，偏快",
                        "中文字幕舒適速度為 3–5 字/秒")

    # ── 統計 ─────────────────────────────────────────────────
    errors   = [x for x in issues if x["level"] == "error"]
    warnings = [x for x in issues if x["level"] == "warning"]
    can_run  = len(errors) == 0

    if not issues:
        overall = "ok"
        summary = f"✅ 全部 {len(segments)} 段通過，無問題"
    elif errors:
        overall = "error"
        summary = (f"❌ {len(errors)} 個阻塞問題、{len(warnings)} 個警告 — "
                   f"請修正後再執行 script-run")
    else:
        overall = "warning"
        summary = (f"⚠️  {len(warnings)} 個警告（不阻塞）— "
                   f"可直接執行 script-run，但建議確認")

    print(json.dumps({
        "status": overall,
        "can_run": can_run,
        "segments_total": len(segments),
        "errors": len(errors),
        "warnings": len(warnings),
        "issues": issues,
        "summary": summary,
    }, ensure_ascii=False, indent=2))


def _fmt_srt_ts(seconds: float) -> str:
    """秒數轉 SRT 時間戳格式 HH:MM:SS,mmm"""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = seconds % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


def cmd_mksrt(args):
    """從劇本 JSON 生成中文 .srt 字幕檔

    劇本 JSON 格式（陣列）：
    [
      {"start": 0,  "end": 15, "text": "台灣軍隊展開新式步槍訓練"},
      {"start": 15, "end": 45, "text": "艾布蘭戰車在竹北展開城市機動演練"},
      ...
    ]
    start/end 單位為秒。
    """
    src = Path(args.script)
    if not src.exists():
        raise ToolError(f"找不到劇本檔：{args.script}")
    segments = json.loads(src.read_text(encoding="utf-8"))
    out = args.out or src.with_suffix(".srt").name

    lines = []
    for i, seg in enumerate(segments, 1):
        start = float(seg.get("start", 0))
        end   = float(seg.get("end",   start + 3))
        text  = str(seg.get("text", "")).strip()
        if not text:
            continue
        lines.append(str(i))
        lines.append(f"{_fmt_srt_ts(start)} --> {_fmt_srt_ts(end)}")
        lines.append(text)
        lines.append("")

    Path(out).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({"status": "ok", "file": out, "count": len(segments)}))


def cmd_burnsub(args):
    """把 .srt 字幕燒進影片（支援中文，自動尋找 CJK 字型）

    優先使用系統已有的 CJK 字型，找不到就用預設字型（英文可正常顯示）。
    """
    from video_pipeline_core.platform_tools import resolve_font
    from video_pipeline_core.subtitle_presentation import (
        build_ass_style,
        probe_video_height,
        subtitle_srt_file,
    )
    out = args.out or Path(args.video).stem + "_subbed.mp4"
    font_path = resolve_font()

    # 用 fontsdir 讓 ffmpeg 找到字型，force_style 指定字型名稱
    font_dir    = str(Path(font_path).parent).replace("\\", "/").replace(":", "\\:")
    font_name   = Path(font_path).stem   # e.g. wqy-microhei or msjh
    # D3 字幕美學：加粗 + 半透明投影（與 merge-final 一致）
    style = build_ass_style(probe_video_height(args.video, FFPROBE))
    with subtitle_srt_file(
        args.srt,
        subtitle_text_policy=getattr(args, "subtitle_text_policy", "polish"),
    ) as render_srt:
        srt_escaped = str(Path(render_srt).resolve()).replace("\\", "\\\\").replace(":", "\\:")
        vf = f"subtitles='{srt_escaped}':fontsdir='{font_dir}':force_style='FontName={font_name},{style}'"
        cmd = [FFMPEG, "-y", "-i", args.video, "-vf", vf,
               "-c:v", "libx264", "-crf", "23", "-c:a", "copy", out]
        result = run(cmd)

    if result.returncode != 0:
        raise ToolError(f"burnsub failed: {result.stderr}")
    print(json.dumps({"status": "ok", "file": out, "font_used": font_path}))


def cmd_script_run(args):
    """劇本驅動全自動剪片

    劇本 JSON 格式（陣列，每段代表一個影片片段）：
    [
      {
        "segment": 1,
        "title": "開頭",
        "search_query": "taiwan rifle training",
        "duration_sec": 15,
        "text": "台灣軍隊展開新式步槍訓練計畫"
      },
      {
        "segment": 2,
        "title": "中段",
        "search_query": "taiwan abrams tank drill hsinchu",
        "duration_sec": 30,
        "text": "艾布蘭戰車在竹北展開黎明前城市機動演練"
      },
      ...
    ]

    執行步驟：
    1. 對每段 search_query 搜尋 YouTube，選第一個結果
    2. 下載前 duration_sec 秒
    3. Concat 所有片段
    4. 依 text 欄位生成中文 .srt（時間點由 duration_sec 累加計算）
    5. 燒進字幕
    6. 輸出成片
    """
    src = Path(args.script)
    if not src.exists():
        raise ToolError(f"找不到劇本檔：{args.script}")
    segments = json.loads(src.read_text(encoding="utf-8"))
    out = args.out or src.stem + "_final.mp4"
    workdir = src.parent

    # ── 模糊消除：先跑 validate，有 error 就擋 ────────────────
    import types as _types, io as _io
    val_args = _types.SimpleNamespace(script=str(src))
    _buf = _io.StringIO()
    _orig = sys.stdout
    sys.stdout = _buf
    cmd_validate(val_args)
    sys.stdout = _orig
    val_result = json.loads(_buf.getvalue())

    if val_result["errors"] > 0:
        print(json.dumps({
            "status": "blocked",
            "reason": "劇本模糊消除未通過，請修正以下問題再執行",
            "validation": val_result,
        }, ensure_ascii=False, indent=2))
        sys.exit(1)
    elif val_result["warnings"] > 0:
        print(f"[script-run] ⚠️  {val_result['warnings']} 個警告：{val_result['summary']}",
              file=sys.stderr)
    else:
        print(f"[script-run] ✅ 劇本驗證通過", file=sys.stderr)
    # ─────────────────────────────────────────────────────────

    print(f"[script-run] 開始執行劇本，共 {len(segments)} 段", file=sys.stderr)

    # ── Step 1-2：每段搜尋 + 下載 ───────────────────────────────────────────
    clip_files = []
    for seg in segments:
        idx      = seg.get("segment", len(clip_files) + 1)
        query    = seg.get("search_query", "")
        duration = float(seg.get("duration_sec", 15))
        end_ts   = f"00:00:{int(duration):02d}"

        print(f"[script-run] 段落 {idx}：搜尋 '{query}'", file=sys.stderr)

        # 搜尋，取第一個結果
        r = run([YTDLP, f"ytsearch1:{query}", "--dump-json", "--flat-playlist", "--no-warnings"])
        if r.returncode != 0 or not r.stdout.strip():
            raise ToolError(f"段落 {idx} 搜尋失敗：{query}")
        hit = json.loads(r.stdout.strip().splitlines()[0])
        vid_id  = hit.get("id")
        vid_url = hit.get("url") or f"https://www.youtube.com/watch?v={vid_id}"
        print(f"[script-run] 段落 {idx}：找到 [{hit.get('title')}]", file=sys.stderr)

        # 下載指定長度片段
        clip_path = str(workdir / f"_script_seg_{idx:02d}.mp4")
        dl_cmd = [
            YTDLP, vid_url,
            "-o", clip_path,
            "--no-warnings",
            "--merge-output-format", "mp4",
            "--ffmpeg-location", str(Path(FFMPEG).parent),
            "--download-sections", f"*0-{int(duration)}",
            "--force-keyframes-at-cuts",
        ]
        r = run(dl_cmd, capture=False)
        if r.returncode != 0:
            raise ToolError(f"段落 {idx} 下載失敗：{vid_url}")
        clip_files.append(clip_path)

    # ── Step 3：Concat ────────────────────────────────────────────────────────
    print("[script-run] 串接所有片段...", file=sys.stderr)
    concat_path = str(workdir / "_script_concat.mp4")

    # 解析度統一（複用 concat 邏輯）
    import types
    concat_args = types.SimpleNamespace(files=clip_files, out=concat_path)
    # 暫時重導向 stdout 避免 concat 的 JSON 輸出干擾
    import io
    old_stdout = sys.stdout
    sys.stdout = io.StringIO()
    cmd_concat(concat_args)
    sys.stdout = old_stdout

    # ── Step 4：生成中文 .srt ────────────────────────────────────────────────
    print("[script-run] 生成中文字幕...", file=sys.stderr)
    srt_data = []
    cursor = 0.0
    for seg in segments:
        duration = float(seg.get("duration_sec", 15))
        text     = seg.get("text", "").strip()
        if text:
            srt_data.append({"start": cursor, "end": cursor + duration, "text": text})
        cursor += duration

    srt_path = str(workdir / "_script_subtitles.srt")
    srt_lines = []
    for i, s in enumerate(srt_data, 1):
        srt_lines.append(str(i))
        srt_lines.append(f"{_fmt_srt_ts(s['start'])} --> {_fmt_srt_ts(s['end'])}")
        srt_lines.append(s["text"])
        srt_lines.append("")
    Path(srt_path).write_text("\n".join(srt_lines), encoding="utf-8")
    dest_srt = workdir / "subtitles.srt"
    Path(dest_srt).write_text("\n".join(srt_lines), encoding="utf-8")

    # ── Step 5：燒字幕 ────────────────────────────────────────────────────────
    print("[script-run] 燒進字幕...", file=sys.stderr)
    burnsub_args = types.SimpleNamespace(video=concat_path, srt=srt_path, out=out)
    sys.stdout = io.StringIO()
    cmd_burnsub(burnsub_args)
    sys.stdout = old_stdout

    # ── 清暫存 ────────────────────────────────────────────────────────────────
    for f in clip_files:
        if Path(f).exists():
            Path(f).unlink()
    for f in [concat_path, srt_path]:
        if Path(f).exists():
            Path(f).unlink()

    total_sec = sum(float(s.get("duration_sec", 15)) for s in segments)
    print(json.dumps({
        "status": "ok",
        "file": out,
        "segments": len(segments),
        "total_sec": total_sec,
        "subtitles": srt_path,
    }, ensure_ascii=False))


def cmd_title(args):
    """在影片上疊加標題文字"""
    out = args.out or "titled_output.mp4"
    text = args.text.replace("'", "\\'")
    vf = (
        f"drawtext=text='{text}'"
        ":fontsize=48"
        ":fontcolor=white"
        ":box=1:boxcolor=black@0.5:boxborderw=10"
        ":x=(w-text_w)/2:y=40"
    )
    cmd = [FFMPEG, "-y", "-i", args.file, "-vf", vf, "-c:a", "copy", out]
    result = run(cmd)
    if result.returncode != 0:
        raise ToolError(f"ffmpeg title overlay failed: {result.stderr}")
    print(json.dumps({"status": "ok", "file": out}))


# ── audio/subtitle 已解耦到 vt_audio.py;re-export 保持 video_tools.X + CLI 不變 ──
from video_pipeline_core.vt_audio import (  # noqa: F401,E402
    cmd_tts, cmd_mix_audio, cmd_mix_sfx, cmd_srt, cmd_gen_bgm, cmd_music_fetch, _music_ytdlp_cmd,
    BGM_MOODS,
)


# ── editor 已解耦到 vt_editor.py;re-export 保持 video_tools.X + CLI 不變 ──
from video_pipeline_core.vt_editor import cmd_assemble, cmd_merge_final  # noqa: F401,E402


# ── VERIFY 已解耦到 vt_verify.py;re-export 保持 video_tools.X + CLI 不變 ──
from video_pipeline_core.vt_verify import cmd_verify  # noqa: F401,E402


# ── 舊版小編已隔離到 vt_curate_legacy.py;re-export 保持 CLI 不變(legacy,待淘汰)──
from video_pipeline_core.vt_curate_legacy import cmd_analyze, cmd_curate, cmd_rank_local  # noqa: F401,E402


# ── dashboard 已解耦到 vt_dashboard.py;re-export 保持 video_tools.X + CLI 不變 ──
from video_pipeline_core.vt_dashboard import cmd_state, cmd_serve, cmd_dashboard, cmd_story_map  # noqa: F401,E402


# ── local materials ingest（小編擴充：本地素材庫）─────────────────────────

# ── 小編素材模組已解耦到 curator.py;re-export 保持 video_tools.X 與 CLI 不變 ──
from video_pipeline_core.curator import (  # noqa: F401,E402
    PHOTO_EXTS, VIDEO_EXTS, classify_asset, _parse_res, _classify_entry,
    caption_asset, format_material_map, match_script_to_material,
    _caption_match_score, _ingest_work_dirs,
    cmd_ingest_meta, cmd_caption_meta, cmd_material_map, cmd_match_mv,
)


# ── 特效師已解耦到 vt_effects.py;re-export 保持 video_tools.X 與 CLI 不變 ──
from video_pipeline_core.vt_effects import (  # noqa: F401,E402
    cmd_kenburns, cmd_grade, cmd_title_card, cmd_title_sequence,
    cmd_collage, cmd_montage, GRADE_PRESETS,
)


# ── stock 來源已解耦到 vt_stock.py;re-export 保持 video_tools.X(含 mv_cut 用的 fetch_stock_video)與 CLI 不變 ──
from video_pipeline_core.vt_stock import (  # noqa: F401,E402
    fetch_stock_video, cmd_pexels_search, cmd_pexels_download,
)


# ── project workspace（repo 外 project/run 整理）─────────────────────────────
from video_pipeline_core.project_workspace import cmd_project_init, cmd_project_new_run  # noqa: F401,E402
from video_pipeline_core.tool_command_catalog import (  # noqa: E402
    build_command_manifest,
    build_workflow_manifest,
)
from video_pipeline_core.acceptance_contract import build_acceptance_contract  # noqa: E402


# ── main ─────────────────────────────────────────────────────────────────────

def cmd_commands_manifest(args):
    payload = build_video_tools_command_manifest()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)


def cmd_workflow_manifest(args):
    payload = build_video_tools_workflow_manifest()
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)


def cmd_acceptance_contract(args):
    payload = build_acceptance_contract(VIDEO_TOOLS_DISPATCH.keys())
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        out = Path(args.out)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(text, encoding="utf-8")
    else:
        print(text)
    if not payload["ok"]:
        raise ToolError("acceptance contract failed: invalid command references")


def cmd_interface_audit(args):
    from video_pipeline_core.capability_manifest import build_capability_manifest

    commands = build_video_tools_command_manifest()
    workflows = build_video_tools_workflow_manifest()
    capabilities = build_capability_manifest()
    acceptance = build_acceptance_contract(VIDEO_TOOLS_DISPATCH.keys())
    missing_commands = list(commands.get("unclassified_commands") or [])
    missing_commands.extend(
        item.get("command")
        for item in workflows.get("missing_commands") or []
        if item.get("command")
    )
    missing_commands.extend(acceptance.get("missing_dispatch_commands") or [])
    missing_commands = sorted(set(missing_commands))
    payload = {
        "artifact_role": "video_tools_interface_audit",
        "version": 1,
        "ok": not missing_commands and acceptance.get("ok", False),
        "missing_commands": missing_commands,
        "checks": {
            "commands": {
                "command_count": commands.get("command_count"),
                "unclassified_commands": commands.get("unclassified_commands") or [],
                "commands": sorted(commands.get("commands") or {}),
            },
            "workflows": {
                "workflow_count": workflows.get("workflow_count"),
                "missing_commands": workflows.get("missing_commands") or [],
            },
            "capabilities": {
                "capability_count": sum(
                    len(items or [])
                    for items in (capabilities.get("capabilities") or {}).values()
                ),
                "unsupported": capabilities.get("unsupported") or [],
            },
            "acceptance_contract": {
                "command_count": len(acceptance.get("commands") or []),
                "missing_dispatch_commands": acceptance.get("missing_dispatch_commands") or [],
                "missing_test_tiers": acceptance.get("missing_test_tiers") or [],
                "invalid_command_refs": acceptance.get("invalid_command_refs") or [],
            },
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    if not payload["ok"]:
        raise ToolError("interface audit failed: missing or unclassified commands")


def cmd_test_tiers(args):
    from tools.test_tiers import build_test_tier_manifest, run_test_tier
    try:
        payload = (
            run_test_tier(args.tier, dry_run=bool(getattr(args, "dry_run", False)))
            if getattr(args, "tier", None)
            else build_test_tier_manifest()
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    if payload.get("ok") is False:
        raise ToolError(f"test tier failed: {payload.get('tier')} command {payload.get('failed_command_index')}")


def _registry_audit_normalize(text):
    return re.sub(r"[^a-z0-9]+", " ", str(text).lower()).strip()


def _registry_audit_branch_labels(branch):
    branch_id = branch.get("branch_id") or ""
    labels = {
        branch_id,
        branch_id.replace("-", " "),
        branch.get("name") or "",
    }
    labels.update({
        "main-pipeline": {"main pipeline", "main video pipeline"},
        "material-map": {"material map"},
        "soundtrack-arranger": {"soundtrack arranger", "audio communication"},
        "subtitle-voiceover": {"subtitle voiceover", "subtitle / voiceover", "audio communication"},
        "effect-factory": {"effect factory"},
        "workbench-brownfield": {"workbench brownfield", "workbench / brownfield"},
        "verify-delivery": {"verify delivery", "verify / delivery gate", "review verify delivery"},
    }.get(branch_id, set()))
    return {_registry_audit_normalize(label) for label in labels if label}


def _registry_audit_gate_in_tree(gate, tree_norm):
    gate_norm = _registry_audit_normalize(gate)
    if gate_norm and gate_norm in tree_norm:
        return True
    if "audio handoff acceptance" in gate_norm:
        return "audio director" in tree_norm and "handoff" in tree_norm
    return False


def _load_registry_audit(registry_path, tree_path):
    registry = json.loads(Path(registry_path).read_text(encoding="utf-8-sig"))
    tree_text = Path(tree_path).read_text(encoding="utf-8-sig")
    tree_norm = _registry_audit_normalize(tree_text)
    headings = []
    for line in tree_text.splitlines():
        match = re.match(r"^(#{1,6})\s+(.+?)\s*$", line)
        if match:
            headings.append(match.group(2).strip())
    return registry, tree_text, tree_norm, headings


def build_registry_audit(registry_path="docs/branch-contract-registry.json",
                         tree_path="docs/pipeline-decision-tree.md"):
    registry, _tree_text, tree_norm, headings = _load_registry_audit(registry_path, tree_path)
    findings = []
    branches = registry.get("branches") or []
    branch_labels = {
        branch.get("branch_id"): _registry_audit_branch_labels(branch)
        for branch in branches
    }

    for branch in branches:
        branch_id = branch.get("branch_id")
        labels = branch_labels.get(branch_id) or set()
        if not any(label and label in tree_norm for label in labels):
            findings.append(f"missing_branch_label: {branch_id}")
        for stage in branch.get("stages") or []:
            gate = stage.get("gate")
            if gate and not _registry_audit_gate_in_tree(gate, tree_norm):
                findings.append(f"missing_stage_gate: {branch_id}.{stage.get('stage')}: {gate}")

    for heading in headings:
        heading_norm = _registry_audit_normalize(heading)
        names_branch = (
            "branch decision tree" in heading_norm
            or heading_norm.startswith("main pipeline decision tree")
            or "delivery gate cross cutting decision tree" in heading_norm
        )
        if not names_branch:
            continue
        if not any(any(label and label in heading_norm for label in labels)
                   for labels in branch_labels.values()):
            findings.append(f"unmapped_tree_heading: {heading}")

    return {
        "ok": not findings,
        "registry": str(registry_path),
        "decision_tree": str(tree_path),
        "branch_count": len(branches),
        "stage_count": sum(len(branch.get("stages") or []) for branch in branches),
        "finding_count": len(findings),
        "findings": findings,
    }


def cmd_registry_audit(args):
    report = build_registry_audit(
        registry_path=getattr(args, "registry", "docs/branch-contract-registry.json"),
        tree_path=getattr(args, "decision_tree", "docs/pipeline-decision-tree.md"),
    )
    if getattr(args, "write_report", None):
        out_path = Path(args.write_report)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Registry Audit Report",
            "",
            f"- ok: {str(report['ok']).lower()}",
            f"- registry: `{report['registry']}`",
            f"- decision_tree: `{report['decision_tree']}`",
            f"- branch_count: {report['branch_count']}",
            f"- stage_count: {report['stage_count']}",
            f"- finding_count: {report['finding_count']}",
            "",
        ]
        if report["findings"]:
            lines.append("## Findings")
            lines.extend(f"- {finding}" for finding in report["findings"])
        else:
            lines.append("No findings.")
        out_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        report["written_report"] = str(out_path)
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
    elif report["ok"]:
        print(f"Registry Audit: OK ({report['branch_count']} branches, {report['stage_count']} stages)")
    else:
        print("Registry Audit: FAIL")
        for finding in report["findings"]:
            print(f"- {finding}")
    if not report["ok"]:
        raise ToolError(f"registry audit failed: {report['finding_count']} finding(s)")


def cmd_asset_path_audit(args):
    from video_pipeline_core.asset_paths import build_asset_path_audit
    report = build_asset_path_audit(args.run_dir, strict=bool(getattr(args, "strict", False)))
    if getattr(args, "json", False):
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        mode = "STRICT" if report["strict"] else "WARN"
        print(
            f"Asset Path Audit ({mode}): {report['finding_count']} absolute path finding(s); "
            f"{report['strict_finding_count']} strict finding(s)"
        )
        for family, bucket in sorted(report["families"].items()):
            print(f"- {family}: {bucket['finding_count']}")
    if not report.get("ok"):
        raise ToolError(f"asset path audit failed: {report['strict_finding_count']} strict finding(s)")


def cmd_ingest_assets(args):
    from video_pipeline_core.asset_store import ingest_assets
    try:
        result = ingest_assets(args.run_dir, args.from_dir)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"ingest-assets failed: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_gc_assets(args):
    from video_pipeline_core.asset_store import gc_assets
    try:
        result = gc_assets(args.run_dir, delete=bool(getattr(args, "delete", False)))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise ToolError(f"gc-assets failed: {exc}") from exc
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_e2e_smoke(args):
    from video_pipeline_core.e2e_smoke import run_e2e_smoke
    result = run_e2e_smoke(
        getattr(args, "case", "stock_story"),
        keep_dir=bool(getattr(args, "keep_dir", False)),
        base_dir=getattr(args, "out_dir", None),
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if not result.get("ok"):
        raise ToolError(f"e2e smoke stalled: {result.get('stalled_action')}")


def cmd_run_layout_validate(args):
    from video_pipeline_core.project_workspace import validate_run_layout
    report = validate_run_layout(args.run_dir)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    if not report.get("ok"):
        raise ToolError(f"run_layout validation failed: {len(report.get('errors') or [])} error(s)")


def cmd_workbench_handoff_validate(args):
    from tools.workbench_handoff import validate_handoff
    report = validate_handoff(args.artifact_root)
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    if not report.get("ok"):
        raise ToolError(f"workbench handoff validation failed: {len(report.get('errors') or [])} error(s)")


def cmd_workbench_draft_rerender(args):
    from tools.workbench_draft_rerender import rerender_from_handoff
    injected_renderer = getattr(args, "renderer", None)
    injected_effect_renderer = getattr(args, "effect_renderer", None)
    extra = {}
    if injected_renderer is not None:
        extra["renderer"] = injected_renderer
    if injected_effect_renderer is not None:
        extra["effect_renderer"] = injected_effect_renderer
    try:
        report = rerender_from_handoff(
            args.artifact_root,
            out=getattr(args, "out", "workbench_rerender.mp4"),
            report_out=getattr(args, "report_out", None),
            music=getattr(args, "music", None),
            render_effects=bool(getattr(args, "effects", False)),
            **extra,
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    print(json.dumps(report, ensure_ascii=False, indent=2))


def cmd_operator_flow_acceptance(args):
    from tools.operator_flow_acceptance import run_operator_flow_acceptance
    injected_renderer = getattr(args, "renderer", None)
    extra = {}
    if injected_renderer is not None:
        extra["renderer"] = injected_renderer
    report = run_operator_flow_acceptance(
        args.artifact_root,
        report_out=getattr(args, "out", None),
        rerender_out=getattr(args, "rerender_out", "operator_flow_rerender.mp4"),
        rerender_report_out=getattr(args, "rerender_report_out", "operator_flow_rerender_report.json"),
        render_effects=bool(getattr(args, "effects", False)),
        init_demo_package=bool(getattr(args, "init_demo_package", False)),
        require_build_ready=bool(getattr(args, "require_build_ready", False)),
        **extra,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    if not report.get("ok"):
        raise ToolError(f"operator flow acceptance failed: {report.get('stage')}")


def cmd_reviewer_policy(args):
    from video_pipeline_core import reviewer_registry
    try:
        if getattr(args, "validate_review", None):
            review = _load_json(args.validate_review)
            result = reviewer_registry.validate_review_artifact(review)
            text = json.dumps(result, ensure_ascii=False, indent=2)
            if getattr(args, "out", None):
                Path(args.out).write_text(text, encoding="utf-8")
            else:
                print(text)
            if not result.get("ok"):
                raise ToolError(f"review artifact validation failed: {len(result.get('errors') or [])} error(s)")
            return
        if getattr(args, "registry", False):
            payload = reviewer_registry.build_reviewer_registry()
        else:
            payload = reviewer_registry.build_policy_packet(args.level)
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if getattr(args, "out", None):
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text, encoding="utf-8")
        else:
            print(text)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def cmd_reviewer_flow_acceptance(args):
    from tools.reviewer_flow_acceptance import run_acceptance

    payload = run_acceptance(
        level=args.level,
        scenario=args.scenario,
        artifact_dir=args.artifact_dir,
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    if not payload.get("ok"):
        raise ToolError("reviewer flow acceptance failed")


def cmd_reviewer_role_review(args):
    from video_pipeline_core import reviewer_registry
    from video_pipeline_core.reviewer_role_runner import review_artifacts

    try:
        payload = review_artifacts(
            args.role,
            {
                "project_brief": getattr(args, "project_brief", None),
                "screenplay_beats": getattr(args, "screenplay_beats", None),
                "material_needs": getattr(args, "material_needs", None),
                "project_material_map": getattr(args, "project_map", None),
                "material_delta": getattr(args, "material_delta", None),
            },
        )
        validation = reviewer_registry.validate_review_artifact(payload)
        if not validation.get("ok"):
            raise ToolError(f"review artifact validation failed: {len(validation.get('errors') or [])} error(s)")
        text = json.dumps(payload, ensure_ascii=False, indent=2)
        if getattr(args, "out", None):
            Path(args.out).parent.mkdir(parents=True, exist_ok=True)
            Path(args.out).write_text(text + "\n", encoding="utf-8")
        else:
            print(text)
    except ValueError as exc:
        raise ToolError(str(exc)) from exc


def cmd_reviewer_aggregate(args):
    from video_pipeline_core.reviewer_aggregation import aggregate_review_files

    payload = aggregate_review_files(args.review)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if payload.get("errors"):
        raise ToolError(f"review aggregation failed: {payload['errors'][0]}")


def cmd_route_task_next(args):
    from video_pipeline_core.route_orchestrator import write_next_task

    try:
        payload = write_next_task(
            args.run_dir,
            args.out,
            state=getattr(args, "state", None),
            now_epoch=getattr(args, "now_epoch", None),
            clear_allowed_outputs=not bool(getattr(args, "keep_existing_allowed", False)),
        )
    except ValueError as exc:
        raise ToolError(str(exc)) from exc
    print(json.dumps(payload, ensure_ascii=False, indent=2))


def cmd_route_task_accept(args):
    from video_pipeline_core.route_orchestrator import accept_task_result

    payload = accept_task_result(args.task, args.result, state_out=args.state_out)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    if not payload.get("ok"):
        raise ToolError(f"route task rejected: {payload.get('errors', ['unknown'])[0]}")


def cmd_route_orchestrator_report(args):
    from video_pipeline_core.route_orchestrator import build_orchestrator_report

    payload = build_orchestrator_report(args.state)
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)


def cmd_route_orchestrator_acceptance(args):
    from tools.route_orchestrator_acceptance import run_route_orchestrator_acceptance

    payload = run_route_orchestrator_acceptance(
        args.run_dir,
        route=args.route,
        stage_count=args.stage_count,
        inject_bad_stage=getattr(args, "inject_bad_stage", None),
        base_epoch=getattr(args, "base_epoch", 1000.0),
    )
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if getattr(args, "out", None):
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    else:
        print(text)
    if not payload.get("ok"):
        raise ToolError(f"route orchestrator acceptance failed: {payload.get('errors', ['unknown'])[0]}")


def _build_video_tools_dispatch():
    return {
        "search":      cmd_search,
        "meta":        cmd_meta,
        "download":    cmd_download,
        "probe":       cmd_probe,
        "cut":         cmd_cut,
        "concat":      cmd_concat,
        "subtitle":    cmd_subtitle,
        "mksrt":       cmd_mksrt,
        "burnsub":     cmd_burnsub,
        "validate":    cmd_validate,
        "script-run":  cmd_script_run,
        "title":       cmd_title,
        "tts":         cmd_tts,
        "mix-audio":   cmd_mix_audio,
        "sfx-mix":     cmd_mix_sfx,
        "srt":         cmd_srt,
        "assemble":    cmd_assemble,
        "merge-final": cmd_merge_final,
        "verify":      cmd_verify,
        "analyze":     cmd_analyze,
        "curate":      cmd_curate,
        "state":       cmd_state,
        "serve":       cmd_serve,
        "dashboard":   cmd_dashboard,
        "story-map":   cmd_story_map,
        "ingest-meta": cmd_ingest_meta,
        "caption-meta": cmd_caption_meta,
        "material-map": cmd_material_map,
        "match-mv":     cmd_match_mv,
        "rank-local":  cmd_rank_local,
        "kenburns":      cmd_kenburns,
        "pexels-search": cmd_pexels_search,
        "pexels-download": cmd_pexels_download,
        "grade":         cmd_grade,
        "title-card":    cmd_title_card,
        "title-sequence": cmd_title_sequence,
        "gen-bgm":       cmd_gen_bgm,
        "music-fetch":   cmd_music_fetch,
        "collage":       cmd_collage,
        "montage":       cmd_montage,
        "project-init":   cmd_project_init,
        "project-new-run": cmd_project_new_run,
        "video-intent-plan": cmd_video_intent_plan,
        "video-intent-acceptance": cmd_video_intent_acceptance,
        "commands-manifest": cmd_commands_manifest,
        "dispatch-capabilities": cmd_dispatch_capabilities,
        "workflow-manifest": cmd_workflow_manifest,
        "acceptance-contract": cmd_acceptance_contract,
        "test-tiers": cmd_test_tiers,
        "registry-audit": cmd_registry_audit,
        "asset-path-audit": cmd_asset_path_audit,
        "interface-audit": cmd_interface_audit,
        "ingest-assets": cmd_ingest_assets,
        "gc-assets": cmd_gc_assets,
        "e2e-smoke": cmd_e2e_smoke,
        "run-layout-validate": cmd_run_layout_validate,
        "workbench-handoff-validate": cmd_workbench_handoff_validate,
        "workbench-draft-rerender": cmd_workbench_draft_rerender,
        "operator-flow-acceptance": cmd_operator_flow_acceptance,
        "reviewer-policy": cmd_reviewer_policy,
        "reviewer-flow-acceptance": cmd_reviewer_flow_acceptance,
        "reviewer-role-review": cmd_reviewer_role_review,
        "reviewer-aggregate": cmd_reviewer_aggregate,
        "route-task-next": cmd_route_task_next,
        "route-task-accept": cmd_route_task_accept,
        "route-orchestrator-report": cmd_route_orchestrator_report,
        "route-orchestrator-acceptance": cmd_route_orchestrator_acceptance,
        "contract-adapt": cmd_contract_adapt,
        "spec-review": cmd_spec_review,
        "capability-manifest": cmd_capability_manifest,
        "supply-review": cmd_supply_review,
        "director-supply-revise": cmd_director_supply_revise,
        "contract-dry-build": cmd_contract_dry_build,
        "contract-run":   cmd_contract_run,
        "generated-manifest": cmd_generated_manifest,
        "generated-image-provider-packet": cmd_generated_image_provider_packet,
        "image-agent-prompt-handoff": cmd_image_agent_prompt_handoff,
        "codex-imagegen-provider-fill": cmd_codex_imagegen_provider_fill,
        "generated-material-import": cmd_generated_material_import,
        "generated-material-produce": cmd_generated_material_produce,
        "generated-material-review": cmd_generated_material_review,
        "soundtrack-arrange": cmd_soundtrack_arrange,
        "soundtrack-provider-search": cmd_soundtrack_provider_search,
        "soundtrack-provider-download": cmd_soundtrack_provider_download,
        "soundtrack-import-url": cmd_soundtrack_import_url,
        "soundtrack-audio-handoff-accept": cmd_soundtrack_audio_handoff_accept,
        "voiceover-provider-plan": cmd_voiceover_provider_plan,
        "visual-technique-plan": cmd_visual_technique_plan,
        "visual-technique-review-apply": cmd_visual_technique_review_apply,
        "effect-design-concept": cmd_effect_design_concept,
        "effect-design-review": cmd_effect_design_review,
        "effect-capability-review": cmd_effect_capability_review,
        "effect-dictionary-promote": cmd_effect_dictionary_promote,
        "effect-intent-plan": cmd_effect_intent_plan,
        "story-soul-blueprint": cmd_story_soul_blueprint,
        "story-soul-to-contract": cmd_story_soul_to_contract,
        "light-effects-plan": cmd_light_effects_plan,
        "effect-revision-request": cmd_effect_revision_request,
        "effect-revision-draft": cmd_effect_revision_draft,
        "effect-revision-apply": cmd_effect_revision_apply,
        "effect-collage-refs": cmd_effect_collage_refs,
        "remotion-template-manifest": cmd_remotion_template_manifest,
        "remotion-prompt-pack": cmd_remotion_prompt_pack,
        "remotion-worker-outputs": cmd_remotion_worker_outputs,
        "effect-render-verification": cmd_effect_render_verification,
        "remotion-worker-smoke": cmd_remotion_worker_smoke,
        "remotion-composite-draft": cmd_remotion_composite_draft,
        "timeline-audit": cmd_timeline_audit,
        "broll-audit":     cmd_broll_audit,
        "new-visual-audit": cmd_new_visual_information_audit,
        "black-frame-audit": cmd_black_frame_audit,
        "validate-needs": cmd_validate_needs,
        "lineage-link": cmd_lineage_link,
        "material-delta": cmd_material_delta,
        "material-generation-fallback": cmd_material_generation_fallback,
        "material-revision": cmd_material_revision,
        "material-map-lifecycle": cmd_material_map_lifecycle,
        "material-map-review-apply": cmd_material_map_review_apply,
        "material-wall-build": cmd_material_wall_build,
        "material-wall-review-apply": cmd_material_wall_review_apply,
        "material-db-slice-from-wall": cmd_material_db_slice_from_wall,
        "project-material-map": cmd_project_material_map,
        "source-highlight-plan": cmd_source_highlight_plan,
        "source-material-matrix": cmd_source_material_matrix,
        "source-section-map": cmd_source_section_map,
        "source-motion-profile": cmd_source_motion_profile,
        "source-dialogue-script": cmd_source_dialogue_script,
        "visual-diversity-coverage": cmd_visual_diversity_coverage,
        "visual-diversity-review": cmd_visual_diversity_review,
        "visual-family-normalize": cmd_visual_family_normalize,
        "semantic-novelty-audit": cmd_semantic_novelty_audit,
        "action-progression-audit": cmd_action_progression_audit,
        "jumpcut-plan":     cmd_jumpcut_plan,
        "jumpcut-apply":    cmd_jumpcut_apply,
        "jumpcut-review":   cmd_jumpcut_review,
        "caption-audit":   cmd_caption_audit,
        "keyframe-grid":   cmd_keyframe_grid,
        "sampling-coverage": cmd_sampling_coverage,
        "montage-wall": cmd_montage_wall,
        "perception-field-check": cmd_perception_field_check,
        "visual-audit":    cmd_visual_audit,
        "verify-evidence": cmd_verify_evidence,
        "final-product-verify": cmd_final_product_verify,
        "replay-acceptance": cmd_replay_acceptance,
        "creator-profile": cmd_creator_profile,
        "blueprint-coverage": cmd_blueprint_coverage,
        "blueprint-compile": cmd_blueprint_compile,
        "blueprint-to-contract": cmd_blueprint_to_contract,
        "capcut-draft":    cmd_capcut_draft,
        "capcut-finalize": cmd_capcut_finalize,
    }


VIDEO_TOOLS_DISPATCH = _build_video_tools_dispatch()


def build_video_tools_command_manifest():
    manifest = build_command_manifest(VIDEO_TOOLS_DISPATCH.keys())
    local_groups = {
        "sampling-coverage": "verify",
        "montage-wall": "verify",
        "perception-field-check": "verify",
    }
    unclassified = set(manifest.get("unclassified_commands") or [])
    for command, group in local_groups.items():
        if command not in manifest.get("commands", {}):
            continue
        old_group = manifest["commands"][command].get("group")
        if old_group in manifest.get("groups", {}) and command in manifest["groups"][old_group].get("commands", []):
            manifest["groups"][old_group]["commands"].remove(command)
        manifest["commands"][command]["group"] = group
        manifest.setdefault("groups", {}).setdefault(group, {"description": "", "commands": []})
        if command not in manifest["groups"][group]["commands"]:
            manifest["groups"][group]["commands"].append(command)
        unclassified.discard(command)
    if "unclassified" in manifest.get("groups", {}) and not manifest["groups"]["unclassified"].get("commands"):
        del manifest["groups"]["unclassified"]
    manifest["unclassified_commands"] = sorted(unclassified)
    manifest["group_count"] = len(manifest.get("groups") or {})
    return manifest


def build_video_tools_workflow_manifest():
    return build_workflow_manifest(VIDEO_TOOLS_DISPATCH.keys())


def main():
    parser = argparse.ArgumentParser(description="video_tools — agent 影片工具")
    sub = parser.add_subparsers(dest="command")

    p_search = sub.add_parser("search")
    p_search.add_argument("query")
    p_search.add_argument("--limit", type=int, default=5)

    p_meta = sub.add_parser("meta")
    p_meta.add_argument("url")

    p_dl = sub.add_parser("download")
    p_dl.add_argument("url")
    p_dl.add_argument("--start")
    p_dl.add_argument("--end")
    p_dl.add_argument("--out")

    p_probe = sub.add_parser("probe")
    p_probe.add_argument("file")

    p_cut = sub.add_parser("cut")
    p_cut.add_argument("file")
    p_cut.add_argument("--start")
    p_cut.add_argument("--end")
    p_cut.add_argument("--out")

    p_concat = sub.add_parser("concat")
    p_concat.add_argument("files", nargs="+")
    p_concat.add_argument("--out")

    p_sub = sub.add_parser("subtitle")
    p_sub.add_argument("file")
    p_sub.add_argument("--language")
    p_sub.add_argument("--out")

    p_title = sub.add_parser("title")
    p_title.add_argument("file")
    p_title.add_argument("--text", required=True)
    p_title.add_argument("--out")

    p_mksrt = sub.add_parser("mksrt")
    p_mksrt.add_argument("script", help="劇本 JSON 路徑")
    p_mksrt.add_argument("--out")

    p_burnsub = sub.add_parser("burnsub")
    p_burnsub.add_argument("video")
    p_burnsub.add_argument("srt")
    p_burnsub.add_argument("--out")
    p_burnsub.add_argument(
        "--subtitle-text-policy",
        choices=["polish", "exact"],
        default="polish",
        dest="subtitle_text_policy",
    )

    p_validate = sub.add_parser("validate")
    p_validate.add_argument("script", help="劇本 JSON 路徑")

    p_script_run = sub.add_parser("script-run")
    p_script_run.add_argument("script", help="劇本 JSON 路徑")
    p_script_run.add_argument("--out")

    p_tts = sub.add_parser("tts")
    p_tts.add_argument("script", help="劇本 JSON 路徑")
    p_tts.add_argument("--voice", help="預設 zh-TW-HsiaoChenNeural")
    p_tts.add_argument("--outdir", help="輸出目錄，預設 tts_out")

    p_vop = sub.add_parser("voiceover-provider-plan")
    p_vop.add_argument("script", help="script JSON or segment_contract.json with narration/text")
    p_vop.add_argument("--out-dir", required=True, dest="out_dir",
                       help="write voiceover_provider_plan.json and subtitle_voiceover_build_handoff.json here")
    p_vop.add_argument("--provider", default="voxcpm", choices=["voxcpm", "legacy_edge_tts"],
                       help="preferred provider; default voxcpm")
    p_vop.add_argument("--voice-style", default="warm, clear Mandarin narrator",
                       help="VoxCPM control text, e.g. warm clear Mandarin narrator")
    p_vop.add_argument("--model-id", help="VoxCPM Hugging Face model id; env VOXCPM_MODEL_ID or openbmb/VoxCPM-0.5B by default")
    p_vop.add_argument("--reference-audio", help="optional reference audio for VoxCPM clone mode")
    p_vop.add_argument("--device", default="auto", help="VoxCPM device: auto/cuda/cpu/cuda:0")
    p_vop.add_argument("--local-files-only", action="store_true",
                       help="VoxCPM should only use already cached model files")
    p_vop.add_argument("--inference-timesteps", type=int, default=10)
    p_vop.add_argument("--cfg-value", type=float, default=2.0)
    p_vop.add_argument("--execute", action="store_true",
                       help="execute the selected provider; omitted means plan-only")
    p_vop.add_argument("--execute-fallback", action="store_true",
                       help="when VoxCPM is unavailable, execute legacy edge-tts fallback instead of only planning it")
    p_vop.add_argument("--no-fallback", action="store_true",
                       help="fail the plan if the preferred provider is unavailable")
    p_vop.add_argument("--fallback-voice", help="legacy edge-tts fallback voice")
    p_vop.add_argument("--voxcpm-bin", help="voxcpm executable path; env VOXCPM_BIN also supported")
    p_vop.add_argument("--voxcpm-repo", help="local VoxCPM repo path; env VOXCPM_REPO or reference repo\\VoxCPM-main by default")
    p_vop.add_argument("--voxcpm-python", help="Python executable for local VoxCPM repo; env VOXCPM_PYTHON also supported")
    p_vop.add_argument("--timeout-sec", type=int, default=1200)

    p_mix = sub.add_parser("mix-audio")
    p_mix.add_argument("--voice", required=True, help="人聲檔案（mp3/wav）")
    p_mix.add_argument("--bgm", help="背景音樂檔案（可選）")
    p_mix.add_argument("--bgm-vol", type=float, dest="bgm_vol",
                       help="BGM 音量 0.0~1.0，預設 0.10（--duck 時 0.28）")
    p_mix.add_argument("--bgm-offset", type=float, default=0.0,
                       help="BGM 從結構點起播的秒數")
    p_mix.add_argument("--duck", action="store_true",
                       help="sidechain ducking：人聲說話時自動壓低音樂（比固定音量專業）")
    p_mix.add_argument("--out", help="輸出檔案，預設 final_audio.wav")

    p_sfx_mix = sub.add_parser("sfx-mix")
    p_sfx_mix.add_argument("--base", required=True, help="既有人聲/BGM 混音")
    p_sfx_mix.add_argument("--plan", required=True, help="sfx_plan.json")
    p_sfx_mix.add_argument("--out", help="輸出檔案，預設 final_audio.wav")

    p_srt = sub.add_parser("srt")
    p_srt.add_argument("timing", help="tts_timing.json 路徑（音控師 tts 指令輸出）")
    p_srt.add_argument("--out", help="輸出 SRT 路徑，預設 subtitles.srt")

    p_asm = sub.add_parser("assemble")
    p_asm.add_argument("--clips", required=True, help="clip_list.json 路徑（小編輸出）")
    p_asm.add_argument("--timing", required=True, help="tts_timing.json 路徑")
    p_asm.add_argument("--out", help="輸出影片，預設 rough_cut.mp4")

    p_mf = sub.add_parser("merge-final")
    p_mf.add_argument("--visual", required=True, help="無音軌的視覺影片（assemble 輸出）")
    p_mf.add_argument("--audio", required=True, help="最終音軌（mix-audio 輸出）")
    p_mf.add_argument("--subs", required=True, help="字幕 SRT（srt 輸出）")
    p_mf.add_argument("--out", help="輸出最終影片，預設 final.mp4")
    p_mf.add_argument(
        "--subtitle-text-policy",
        choices=["polish", "exact"],
        default="polish",
        dest="subtitle_text_policy",
    )

    p_vrf = sub.add_parser("verify")
    p_vrf.add_argument("--script", required=True, help="script.json")
    p_vrf.add_argument("--timing", required=True, help="tts_timing.json")
    p_vrf.add_argument("--edit-log", required=True, dest="edit_log",
                       help="rough_cut_edit_log.json（assemble 輸出）")
    p_vrf.add_argument("--srt", required=True, help="subtitles.srt")
    p_vrf.add_argument("--video", required=True, help="成片 final.mp4")
    p_vrf.add_argument("--threshold", type=float, help="通過分數，預設 80")
    p_vrf.add_argument("--out", help="輸出 qa_report.json")

    p_vrf.add_argument("--brief", default=None, help="optional brief/project_brief.json for target duration QA")
    p_vrf.add_argument("--content-alignment", default=None, dest="content_alignment",
                       help="optional content/VLM alignment artifact for semantic QA")

    p_anz = sub.add_parser("analyze")
    p_anz.add_argument("video", help="影片檔路徑")
    p_anz.add_argument("--query", required=True, help="關鍵字（英文效果較好）")
    p_anz.add_argument("--target-sec", type=float, dest="target_sec",
                       help="目標窗口長度（秒），預設 20")
    p_anz.add_argument("--language", help="hint：en / zh，省略則自動偵測")
    p_anz.add_argument("--model", help="Whisper 模型，預設 base")

    p_cur = sub.add_parser("curate")
    p_cur.add_argument("--script", required=True, help="script.json")
    p_cur.add_argument("--timing", required=True, help="tts_timing.json")
    p_cur.add_argument("--workdir", help="工作目錄，預設 curate_out")
    p_cur.add_argument("--top-n", type=int, dest="top_n",
                       help="每段分析 N 個候選取最佳，預設 1")
    p_cur.add_argument("--out", help="輸出 clip_list.json")

    p_st = sub.add_parser("state")
    p_st.add_argument("workdir", help="掃描的工作目錄")
    p_st.add_argument("--project", help="專案名稱（預設 workdir 名）")
    p_st.add_argument("--out", help="輸出 state.json 路徑（預設 workdir/state.json）")

    p_db = sub.add_parser("dashboard")
    p_db.add_argument("workdir", help="含 state.json 的輸出目錄")
    p_db.add_argument("--out", help="輸出 HTML 路徑（預設 workdir/dashboard_view.html）")

    p_sm = sub.add_parser("story-map")
    p_sm.add_argument("workdir", help="含 state.json 的輸出目錄")
    p_sm.add_argument("--out", help="輸出 HTML 路徑（預設 workdir/story_map_view.html）")

    p_sv = sub.add_parser("serve")
    p_sv.add_argument("workdir", help="要服務的工作目錄")
    p_sv.add_argument("--port", type=int, help="HTTP port，預設 8765")

    p_ig = sub.add_parser("ingest-meta")
    p_ig.add_argument("src", help="本地素材根目錄")
    p_ig.add_argument("--out", help="輸出 materials_db.json 路徑")
    p_ig.add_argument("--work-dir", dest="work_dir",
                      help="衍生檔(.converted/.keyframes)目錄;預設=db 所在目錄(不污染來源)")

    p_cm = sub.add_parser("caption-meta")
    p_cm.add_argument("db", help="materials_db.json")
    p_cm.add_argument("--model", help="local VLM model; only used with --local-vlm")
    p_cm.add_argument("--limit", type=int, help="最多 caption 幾個（測試用）")
    p_cm.add_argument(
        "--local-vlm",
        action="store_true",
        help="explicitly use local VLM captioning instead of agent material visual review",
    )

    p_cm.add_argument(
        "--visual-review-dir",
        help="write material montage review request here, then consume verdict on rerun",
    )

    p_mm = sub.add_parser("material-map")
    p_mm.add_argument("db", help="materials_db.json")
    p_mm.add_argument("--maps-dir", dest="maps_dir",
                      help="write deterministic per-asset *.map.json files")
    p_mm.add_argument("--update-db", dest="update_db",
                      help="write materials_db with material_map paths")
    p_mm.add_argument("--out", help="輸出地圖 .md 路徑")

    p_mm.add_argument("--limit", type=int,
                      help="only map the first N files for bounded operator passes")
    p_mm.add_argument("--selected-only", action="store_true", dest="selected_only",
                      help="only map files marked selected_for_material_map=true")
    p_mm.add_argument("--asset-timeout-sec", type=float, dest="asset_timeout_sec",
                      help="skip one asset and continue if material-map extraction exceeds this many seconds")
    p_mm.add_argument("--fast", action="store_true",
                      help="write coarse duration-based maps without expensive video detectors")

    p_mv = sub.add_parser("match-mv")
    p_mv.add_argument("script", help="MV 劇本 json")
    p_mv.add_argument("db", help="materials_db.json")
    p_mv.add_argument("--out", help="輸出 clip_list.json")

    p_rl = sub.add_parser("rank-local")
    p_rl.add_argument("--db", required=True, help="materials_db.json")
    p_rl.add_argument("--needs", required=True, help="material_needs.json")
    p_rl.add_argument("--out", help="輸出 clip_list.json")

    p_kb = sub.add_parser("kenburns")
    p_kb.add_argument("photo", help="輸入照片 jpg/png")
    p_kb.add_argument("--duration", type=float, required=True, help="輸出影片時長秒")
    p_kb.add_argument("--direction",
                      help="zoom-in / zoom-out / pan-left / pan-right / random，預設 zoom-in")
    p_kb.add_argument("--out", help="輸出影片路徑")

    p_psr = sub.add_parser("pexels-search")
    p_psr.add_argument("query", help="搜尋關鍵字（英文較佳）")
    p_psr.add_argument("--type", required=True, choices=['photo', 'video'])
    p_psr.add_argument("--limit", type=int, help="預設 10")
    p_psr.add_argument("--out", help="輸出 JSON 路徑（可選）")

    p_pdl = sub.add_parser("pexels-download")
    p_pdl.add_argument("url", help="download_url（從 pexels-search 拿）")
    p_pdl.add_argument("--out", help="輸出檔案路徑")

    p_grade = sub.add_parser("grade")
    p_grade.add_argument("input", help="輸入影片")
    p_grade.add_argument("--preset", help="dusk/night/fire/warm/cool/neutral")
    p_grade.add_argument("--out", help="輸出影片路徑")

    p_tc = sub.add_parser("title-card")
    p_tc.add_argument("input", help="輸入影片（疊字卡於開頭）")
    p_tc.add_argument("--text", required=True, help="主標題")
    p_tc.add_argument("--subtitle", help="副標題（可選）")
    p_tc.add_argument("--hold", type=float, help="標題停留秒數（預設 2.5）")
    p_tc.add_argument("--size", type=int, help="主標字級（預設 96）")
    p_tc.add_argument("--out", help="輸出影片路徑")

    p_ts = sub.add_parser("title-sequence")
    p_ts.add_argument("--text", required=True, help="主標題")
    p_ts.add_argument("--subtitle", help="副標題（可選）")
    p_ts.add_argument("--duration", type=float, required=True, help="片段時長秒")
    p_ts.add_argument("--anim", help="slide-up（預設）/ fade")
    p_ts.add_argument("--size", type=int, help="主標字級（預設 120）")
    p_ts.add_argument("--bg", help="底色 hex（預設 0x0d0d1a 深藍黑）")
    p_ts.add_argument("--out", help="輸出影片路徑")

    p_gb = sub.add_parser("gen-bgm")
    p_gb.add_argument("--mood", help="calm/warm/emotional/energetic/tense/bright/night")
    p_gb.add_argument("--duration", type=float, help="秒數（預設 60，會被 loop）")
    p_gb.add_argument("--out", help="輸出路徑（預設 bgm/<mood>.mp3）")

    p_mu = sub.add_parser("music-fetch")
    p_mu.add_argument("query", help="音樂搜尋詞，如「lofi calm piano instrumental」")
    p_mu.add_argument("--source", help="yt（預設，yt-dlp 抽音訊）/ jamendo（需 client_id，未啟用）")
    p_mu.add_argument("--max-dur", type=float, dest="max_dur",
                      help="只接受短於此秒數的結果（避免抓到 1 小時混音）")
    p_mu.add_argument("--out", help="輸出 mp3 路徑（預設 music_<source>.mp3）")

    p_col = sub.add_parser("collage")
    p_col.add_argument("--images", nargs="+", required=True, help="2-4 張照片路徑")
    p_col.add_argument("--duration", type=float, required=True, help="時長秒")
    p_col.add_argument("--bg", help="底色 hex（預設 0x0d0d1a）")
    p_col.add_argument("--out", help="輸出影片路徑")

    p_mon = sub.add_parser("montage")
    p_mon.add_argument("--images", nargs="+", required=True, help="2-8 張照片路徑（快切輪播）")
    p_mon.add_argument("--duration", type=float, required=True, help="總時長秒")
    p_mon.add_argument("--out", help="輸出影片路徑")

    p_prj = sub.add_parser("project-init")
    p_prj.add_argument("name", help="專案名稱，會轉成 slug 作為外部資料夾名")
    p_prj.add_argument("--root", help="外部 project root，預設 ~/video_pipeline_projects")

    p_run = sub.add_parser("project-new-run")
    p_run.add_argument("--project", help="project 目錄；省略則讀 repo/.project/active.json")
    p_run.add_argument("--label", help="run 名稱後綴，如 first-cut / baseline")

    p_vip = sub.add_parser("video-intent-plan")
    p_vip.add_argument("brief", help="project brief JSON for Stage 0 Video Intent Planner")
    p_vip.add_argument("--out", help="write canonical video_intent.json")

    p_via = sub.add_parser("video-intent-acceptance")
    p_via.add_argument("--out", help="write video_intent_acceptance.json")

    p_cmdm = sub.add_parser("commands-manifest")
    p_cmdm.add_argument("--out", help="write video_tools command manifest JSON")

    p_dispatch = sub.add_parser("dispatch-capabilities")
    selector = p_dispatch.add_mutually_exclusive_group(required=True)
    selector.add_argument("--id")
    selector.add_argument("--owner")
    selector.add_argument("--loop", choices=[f"L{i}" for i in range(6)])
    selector.add_argument("--query")
    p_dispatch.add_argument("--json", action="store_true")
    p_dispatch.add_argument("--out")
    p_dispatch.add_argument("--skills-dir", default="skills")
    p_dispatch.add_argument("--tools-dir", default="tools")

    p_wfm = sub.add_parser("workflow-manifest")
    p_wfm.add_argument("--out", help="write video_tools workflow manifest JSON")

    p_acc = sub.add_parser("acceptance-contract")
    p_acc.add_argument("--out", help="write acceptance command contract JSON")

    p_tt = sub.add_parser("test-tiers")
    p_tt.add_argument("--tier", help="test tier to run; omit to print tier manifest")
    p_tt.add_argument("--dry-run", action="store_true", help="print commands without executing")
    p_tt.add_argument("--out", help="write test tier JSON")

    p_raudit = sub.add_parser("registry-audit")
    p_raudit.add_argument("--registry", default="docs/branch-contract-registry.json",
                          help="branch contract registry JSON")
    p_raudit.add_argument("--decision-tree", default="docs/pipeline-decision-tree.md",
                          help="pipeline decision tree markdown")
    p_raudit.add_argument("--write-report", help="optional markdown report path")
    p_raudit.add_argument("--json", action="store_true", help="print JSON report")

    p_apath = sub.add_parser("asset-path-audit")
    p_apath.add_argument("run_dir", help="run directory containing artifact JSON files")
    p_apath.add_argument("--strict", action="store_true", help="exit non-zero for strict-family findings")
    p_apath.add_argument("--json", action="store_true", help="print JSON report")

    p_iaudit = sub.add_parser("interface-audit")
    p_iaudit.add_argument("--out", help="write interface audit JSON")

    p_ingest_assets = sub.add_parser("ingest-assets")
    p_ingest_assets.add_argument("run_dir", help="run directory whose assets/ store will receive files")
    p_ingest_assets.add_argument("--from", dest="from_dir", required=True, help="directory of external assets")

    p_gc_assets = sub.add_parser("gc-assets")
    p_gc_assets.add_argument("run_dir", help="run directory whose assets/ store will be scanned")
    p_gc_assets.add_argument("--delete", action="store_true", help="delete unreferenced assets after reporting")

    p_e2e = sub.add_parser("e2e-smoke")
    p_e2e.add_argument("--case", default="stock_story", choices=["stock_story", "single_long_highlight"])
    p_e2e.add_argument("--keep-dir", action="store_true")
    p_e2e.add_argument("--out-dir", help="optional temp/run directory for smoke artifacts")

    p_rlv = sub.add_parser("run-layout-validate")
    p_rlv.add_argument("run_dir", help="project run directory containing run_layout.json")
    p_rlv.add_argument("--out", help="write run_layout_validation.json")

    p_whv = sub.add_parser("workbench-handoff-validate")
    p_whv.add_argument("artifact_root", help="run/artifact root containing workbench_handoff.json")
    p_whv.add_argument("--out", help="write workbench_handoff_validation.json")

    p_wdr = sub.add_parser("workbench-draft-rerender")
    p_wdr.add_argument("artifact_root", help="run/artifact root containing validated Workbench draft artifacts")
    p_wdr.add_argument("--out", default="workbench_rerender.mp4", help="non-canonical output video name/path")
    p_wdr.add_argument("--report-out", help="write workbench_rerender_report.json elsewhere")
    p_wdr.add_argument("--music", help="override music path")
    p_wdr.add_argument("--effects", action="store_true", help="apply supported effect_patch.json overlays")

    p_ofa = sub.add_parser("operator-flow-acceptance")
    p_ofa.add_argument("artifact_root", help="run/artifact root to validate as a bounded operator replay package")
    p_ofa.add_argument("--out", default=None,
                       help="operator flow acceptance report")
    p_ofa.add_argument("--rerender-out", default="operator_flow_rerender.mp4",
                       help="non-canonical rerender output video")
    p_ofa.add_argument("--rerender-report-out", default="operator_flow_rerender_report.json",
                       help="non-canonical rerender report")
    p_ofa.add_argument("--effects", action="store_true",
                       help="apply supported Workbench effect_patch overlays during draft rerender")
    p_ofa.add_argument("--init-demo-package", action="store_true",
                       help="initialize a deterministic complete demo package under artifact_root before validating")
    p_ofa.add_argument("--require-build-ready", action="store_true",
                       help="fail unless material-map lifecycle reaches build_ready")

    p_rp = sub.add_parser("reviewer-policy")
    p_rp.add_argument("--level", default="normal", choices=["light", "normal", "deep"],
                      help="review policy level to expand into reviewer roles")
    p_rp.add_argument("--registry", action="store_true",
                      help="write the full reviewer registry instead of one policy packet")
    p_rp.add_argument("--validate-review", default=None, dest="validate_review",
                      help="validate an artifact_review JSON file")
    p_rp.add_argument("--out", default=None, help="optional JSON output path")

    p_rfa = sub.add_parser("reviewer-flow-acceptance")
    p_rfa.add_argument("--level", default="deep", choices=["light", "normal", "deep"],
                       help="review policy level to expand")
    p_rfa.add_argument("--scenario", default="all",
                       choices=["route_smoke", "upstream_story", "effects_brownfield", "all"],
                       help="reviewer scenario to prove")
    p_rfa.add_argument("--artifact-dir", default=None,
                       help="optional directory for reviewer_policy_packet and artifact_review samples")
    p_rfa.add_argument("--out", default=None, help="optional JSON report path")

    p_rrr = sub.add_parser("reviewer-role-review")
    p_rrr.add_argument("--role", required=True,
                       help="reviewer role to run, such as story_director")
    p_rrr.add_argument("--project-brief", default=None, dest="project_brief",
                       help="optional project_brief JSON")
    p_rrr.add_argument("--screenplay-beats", default=None, dest="screenplay_beats",
                       help="optional screenplay_beats JSON")
    p_rrr.add_argument("--material-needs", default=None, dest="material_needs",
                       help="optional material_needs JSON")
    p_rrr.add_argument("--project-map", default=None, dest="project_map",
                       help="optional project_material_map or reviewed_project_material_map JSON")
    p_rrr.add_argument("--material-delta", default=None, dest="material_delta",
                       help="optional material_delta JSON")
    p_rrr.add_argument("--out", default=None, help="optional artifact_review JSON output path")

    p_rag = sub.add_parser("reviewer-aggregate")
    p_rag.add_argument("--review", action="append", required=True,
                       help="artifact_review JSON path; repeat for multiple reviewers")
    p_rag.add_argument("--out", default=None, help="optional reviewer_aggregation JSON output path")

    p_rtn = sub.add_parser("route-task-next")
    p_rtn.add_argument("run_dir", help="run directory for the route task packet")
    p_rtn.add_argument("--out", required=True, help="write route_subagent_task JSON")
    p_rtn.add_argument("--state", default=None, help="existing route_orchestrator_state JSON")
    p_rtn.add_argument("--now-epoch", type=float, default=None,
                       help="deterministic issued_at_epoch for tests")
    p_rtn.add_argument("--keep-existing-allowed", action="store_true",
                       help="do not clear stale allowed outputs before issuing the task")

    p_rta = sub.add_parser("route-task-accept")
    p_rta.add_argument("--task", required=True, help="route_subagent_task JSON")
    p_rta.add_argument("--result", required=True, help="route_subagent_result JSON")
    p_rta.add_argument("--state-out", required=True, help="write updated route_orchestrator_state JSON")

    p_ror = sub.add_parser("route-orchestrator-report")
    p_ror.add_argument("--state", required=True, help="route_orchestrator_state JSON")
    p_ror.add_argument("--out", default=None, help="optional report JSON output")

    p_roa = sub.add_parser("route-orchestrator-acceptance")
    p_roa.add_argument("run_dir", help="run directory for deterministic orchestrator replay")
    p_roa.add_argument("--route", required=True,
                       choices=["existing-material-first", "hybrid", "story-first"],
                       help="material route to stamp into fake worker outputs")
    p_roa.add_argument("--stage-count", type=int, default=4,
                       help="number of stages to replay")
    p_roa.add_argument("--inject-bad-stage", type=int, default=None,
                       help="mutate a protected artifact at this stage to prove fail-closed rejection")
    p_roa.add_argument("--base-epoch", type=float, default=1000.0,
                       help="deterministic base issued_at_epoch for tests")
    p_roa.add_argument("--out", default=None, help="optional JSON report path")

    p_ca = sub.add_parser("contract-adapt")
    p_ca.add_argument("contract", help="canonical segment_contract.json")
    p_ca.add_argument("--out", help="輸出 generated_mv_script.json")
    p_ca.add_argument("--categories", help="material categories JSON")

    p_sr = sub.add_parser("spec-review")
    p_sr.add_argument("contract", help="canonical segment_contract.json")
    p_sr.add_argument("--brief", help="brief.json (target_length/mode checks)")
    p_sr.add_argument("--editorial-design", dest="editorial_design",
                      help="editorial_design.json (soul-guard check)")
    p_sr.add_argument("--out", help="write spec_review.json here")
    p_sr.add_argument("--supply-review", dest="supply_review",
                      help="supply_review.json used by B6 script-overreach gate")

    p_cap = sub.add_parser("capability-manifest")
    p_cap.add_argument("--out", default="capability_manifest.json",
                       help="generated capability manifest output")

    p_supply = sub.add_parser("supply-review")
    p_supply.add_argument("contract", help="canonical segment_contract.json")
    p_supply.add_argument("--maps-dir", required=True, dest="maps_dir",
                          help="directory containing *.map.json")
    p_supply.add_argument("--out", default="supply_review.json",
                          help="supply review output")
    p_supply.add_argument("--coverage-map", dest="coverage_map",
                          help="material_coverage_map.json with segment assignments")
    p_supply.add_argument("--target-duration", type=float, dest="target_duration",
                          help="allocate requested segment duration by contract weight")

    p_dsr = sub.add_parser("director-supply-revise")
    p_dsr.add_argument("contract", help="segment_contract.json")
    p_dsr.add_argument("--supply-review", required=True, dest="supply_review",
                       help="supply_review.json with script_overreach evidence")
    p_dsr.add_argument("--out-contract", required=True, dest="out_contract",
                       help="revised segment_contract.json output")
    p_dsr.add_argument("--out-report", required=True, dest="out_report",
                       help="director_supply_revision.json output")

    p_cd = sub.add_parser("contract-dry-build")
    p_cd.add_argument("contract", help="canonical segment_contract.json")
    p_cd.add_argument("--out-dir", required=True, dest="out_dir",
                      help="run dir for the render-free BUILD artifacts")
    p_cd.add_argument("--categories", help="material categories JSON")
    p_cd.add_argument("--build-profile", help="build profile override JSON")
    p_cd.add_argument("--total-duration", type=float, default=60.0, dest="total_duration",
                      help="nominal total duration (sec) to allocate across segments")
    p_cd.add_argument("--quiet", action="store_true")

    p_cr = sub.add_parser("contract-run")
    p_cr.add_argument("contract", help="canonical segment_contract.json")
    p_cr.add_argument("--categories", help="material categories JSON")
    p_cr.add_argument("--material-db", required=True, help="materials_db.json")
    p_cr.add_argument("--music", required=True, help="music/audio path")
    p_cr.add_argument("--out", required=True, help="輸出 final.mp4")
    p_cr.add_argument("--mat-dir", help="material/render work dir")
    p_cr.add_argument("--model-routes", help="model routes override JSON")
    p_cr.add_argument("--build-profile", help="build profile override JSON")
    p_cr.add_argument("--creator-profile", dest="creator_profile",
                      help="creator_profile.json — fills build defaults (brief overrides)")
    p_cr.add_argument("--quiet", action="store_true")
    p_cr.add_argument("--skip-render", action="store_true", dest="skip_render",
                      help="Skip the ffmpeg rendering step (e.g. for capcut_draft backend)")

    p_gm = sub.add_parser("generated-manifest")
    p_gm.add_argument("requests", help="generated_asset_requests.json")
    p_gm.add_argument("--outputs", required=True, help="provider/manual generated outputs JSON")
    p_gm.add_argument("--out", required=True, help="output generated_asset_manifest.json")
    p_gm.add_argument("--artifact-manifest", help="artifact_manifest.json to update")
    p_gm.add_argument("--no-require-files", action="store_true",
                      help="do not require output files to exist")

    p_gmp = sub.add_parser("generated-material-produce")
    p_gmp.add_argument("fallback", help="material_generation_fallback.json")
    p_gmp.add_argument("--needs", required=True, help="material_needs.json")
    p_gmp.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for generated files, manifest, maps, and review")
    p_gmp.add_argument("--style-profile", default=None, dest="style_profile",
                       help="optional style_profile.json with palette/look/aspect_ratio")
    p_gmp.add_argument("--provider", default="codex_imagegen",
                       help="provider label recorded in generated manifest")
    p_gmp.add_argument("--renderer", default="test_pil",
                       help="renderer adapter; test_pil is test-only and requires --allow-test-renderer")
    p_gmp.add_argument("--allow-test-renderer", action="store_true",
                       help=("allow test_pil placeholder images for bounded acceptance tests; "
                             "omit for real E2E so missing image provider fails closed"))

    p_gipp = sub.add_parser("generated-image-provider-packet")
    p_gipp.add_argument("fallback", help="material_generation_fallback.json")
    p_gipp.add_argument("--out-dir", required=True, dest="out_dir",
                        help="directory for provider prompts, target files, and import template")
    p_gipp.add_argument("--style-profile", default=None, dest="style_profile",
                        help="optional style_profile.json with style/character anchors")
    p_gipp.add_argument("--providers", default="codex_imagegen,gemini,antigravity",
                        help="comma-separated real image provider candidates")

    p_cig = sub.add_parser("codex-imagegen-provider-fill")
    p_cig.add_argument("packet", help="generated_provider_packet.json")
    p_cig.add_argument("--image-files", nargs="+", default=None,
                       help="explicit Codex imagegen output files, in packet item order")
    p_cig.add_argument("--generated-root", default=None,
                       help="Codex generated_images root; defaults to ~/.codex/generated_images")
    p_cig.add_argument("--out", default=None,
                       help="write generated_provider_outputs.json here")
    p_cig.add_argument("--provider", default="codex_imagegen",
                       help="provider label written into generated_provider_outputs.json")

    p_iaph = sub.add_parser("image-agent-prompt-handoff")
    p_iaph.add_argument("packet", help="generated_provider_packet.json")
    p_iaph.add_argument("--out-dir", default=None, dest="out_dir",
                        help="directory for image_agent_prompt_handoff.json and prompt markdown")
    p_iaph.add_argument("--max-items", type=int, default=None,
                        help="optional bounded item count for probe runs")

    p_gmi = sub.add_parser("generated-material-import")
    p_gmi.add_argument("fallback", help="material_generation_fallback.json")
    p_gmi.add_argument("--needs", required=True, help="material_needs.json")
    p_gmi.add_argument("--provider-outputs", required=True, dest="provider_outputs",
                       help="provider output JSON with items[].job_id/file/provider/style anchors")
    p_gmi.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for imported generated files, manifest, maps, and review")
    p_gmi.add_argument("--style-profile", default=None, dest="style_profile",
                       help="optional style_profile.json with style_anchors/character_anchors")

    p_gmr = sub.add_parser("generated-material-review")
    p_gmr.add_argument("project_map", help="project_material_map.json with generated candidate edges")
    p_gmr.add_argument("--needs", required=True, help="material_needs.json")
    p_gmr.add_argument("--verdict", required=True, help="generated_material_review.json")
    p_gmr.add_argument("--quality-review", default=None, dest="quality_review",
                       help="optional generated_material_quality_review.json to enforce quality gates")
    p_gmr.add_argument("--out", required=True, help="reviewed project_material_map.json")

    p_ssb = sub.add_parser("story-soul-blueprint")
    p_ssb.add_argument("brief", help="project brief JSON")
    p_ssb.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for SSB artifacts")

    p_ssb2 = sub.add_parser("story-soul-to-contract")
    p_ssb2.add_argument("--story-dir", required=True, dest="story_dir",
                        help="directory containing story-soul-blueprint artifacts")
    p_ssb2.add_argument("--out", required=True,
                        help="segment_contract.json output")

    p_fx = sub.add_parser("effect-intent-plan")
    p_fx.add_argument("director_shot_plan", help="director_shot_plan.json with effect_intent fields")
    p_fx.add_argument("--out-plan", required=True, dest="out_plan",
                      help="effect_intent_plan.json output")
    p_fx.add_argument("--out-spec", required=True, dest="out_spec",
                      help="effect_asset_spec.json output")

    p_vtp = sub.add_parser("visual-technique-plan")
    p_vtp.add_argument("--request", required=True,
                       help="fuzzy visual/effect request")
    p_vtp.add_argument("--effect-role", default="", dest="effect_role",
                       help="opening_title, transition, lower_third, montage_hit, closing_title, or outro")
    p_vtp.add_argument("--duration-sec", type=float, default=None, dest="duration_sec",
                       help="optional intended duration in seconds")
    p_vtp.add_argument("--material-state", default=None, dest="material_state",
                       help="optional material context, for example group_photo_available")
    p_vtp.add_argument("--confirmed", action="store_true",
                       help="mark the candidate direction as user/reviewer confirmed for downstream handoff")
    p_vtp.add_argument("--json", action="store_true",
                       help="accepted for compatibility; command always prints JSON")
    p_vtp.add_argument("--out", required=True,
                       help="visual_technique_plan.json output")

    p_edc = sub.add_parser("effect-design-concept")
    p_edc.add_argument("--request", default="",
                       help="fuzzy effect request to turn into design brief/options/selection")
    p_edc.add_argument("--request-file", default="", dest="request_file",
                       help="UTF-8 text file containing the fuzzy effect request; preferred on Windows for Chinese text")
    p_edc.add_argument("--effect-role", default="opening_title", dest="effect_role",
                       help="opening_title, transition, lower_third, montage_hit, closing_title, or outro")
    p_edc.add_argument("--duration-sec", type=float, default=4.0, dest="duration_sec",
                       help="intended effect duration in seconds")
    p_edc.add_argument("--material-context", default="reviewed_or_local_material_refs", dest="material_context",
                       help="material context for design assumptions")
    p_edc.add_argument("--preferred-concept-id", default="", dest="preferred_concept_id",
                       help="optional concept_id override such as quiet_memory_wall")
    p_edc.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for effect_design_brief/options/selection artifacts")

    p_edr = sub.add_parser("effect-design-review")
    p_edr.add_argument("--selection", required=True,
                       help="effect_concept_selection.json")
    p_edr.add_argument("--render-report", required=True, dest="render_report",
                       help="render probe report JSON with duration/copy/material evidence")
    p_edr.add_argument("--out", required=True,
                       help="effect_design_review.json output")

    p_ecrev = sub.add_parser("effect-capability-review")
    p_ecrev.add_argument("--input", default=None,
                         help="optional JSON payload with request/effect_build_spec")
    p_ecrev.add_argument("--request", default="",
                         help="fuzzy or confirmed effect request")
    p_ecrev.add_argument("--effect-role", default="", dest="effect_role",
                         help="opening_title, transition, lower_third, montage_hit, closing_title, or outro")
    p_ecrev.add_argument("--duration-sec", type=float, default=None, dest="duration_sec",
                         help="optional intended duration in seconds")
    p_ecrev.add_argument("--out", required=True,
                         help="effect_capability_review.json output")

    p_edprom = sub.add_parser("effect-dictionary-promote")
    p_edprom.add_argument("--request", required=True,
                          help="promotion request JSON with accepted review evidence")
    p_edprom.add_argument("--dictionary", required=True,
                          help="existing or new effect_factory_dictionary.json")
    p_edprom.add_argument("--out", required=True,
                          help="updated effect_factory_dictionary.json output")

    p_sta = sub.add_parser("soundtrack-arrange")
    p_sta.add_argument("input", help="brief/video_intent JSON input")
    p_sta.add_argument("--out-dir", required=True, dest="out_dir",
                       help="run folder for soundtrack artifacts")

    p_sts = sub.add_parser("soundtrack-provider-search")
    p_sts.add_argument("--plan", required=True, help="soundtrack_plan.json input")
    p_sts.add_argument("--out", required=True, help="music_source_candidates.json output")
    p_sts.add_argument("--providers", default="jamendo,pixabay",
                       help="comma-separated providers, default: jamendo,pixabay")
    p_sts.add_argument("--limit", type=int, default=3, help="max candidates per searched section")

    p_std = sub.add_parser("soundtrack-provider-download")
    p_std.add_argument("--candidates", required=True, help="music_source_candidates.json")
    p_std.add_argument("--candidate-id", required=True, dest="candidate_id", help="candidate_id to download")
    p_std.add_argument("--out-dir", required=True, dest="out_dir", help="run folder for audio/source and handoff artifacts")

    p_stu = sub.add_parser("soundtrack-import-url")
    p_stu.add_argument("--url", required=True, help="URL to import with yt-dlp")
    p_stu.add_argument("--section-id", required=True, dest="section_id", help="target soundtrack section id")
    p_stu.add_argument("--source-type", required=True, dest="source_type",
                       help="youtube_audio_library, licensed_library, user_provided, or suno_udio_external")
    p_stu.add_argument("--usage-scope", default="internal_only", dest="usage_scope",
                       help="internal_only, non_commercial, public_delivery, or commercial_delivery")
    p_stu.add_argument("--license-note", default="", dest="license_note",
                       help="manual license/use assertion; required unless --license-url is provided")
    p_stu.add_argument("--license-url", default="", dest="license_url",
                       help="license/source URL; required unless --license-note is provided")
    p_stu.add_argument("--ytdlp-path", default=YTDLP, dest="ytdlp_path", help="yt-dlp executable path")
    p_stu.add_argument("--audio-format", default="mp3", dest="audio_format", help="yt-dlp audio format, default mp3")
    p_stu.add_argument("--out-dir", required=True, dest="out_dir", help="run folder for audio/source and handoff artifacts")

    p_saha = sub.add_parser("soundtrack-audio-handoff-accept")
    p_saha.add_argument("--handoff", required=True, help="audio_director_handoff.json")
    p_saha.add_argument("--out-dir", required=True, dest="out_dir", help="run folder for audio_handoff_acceptance.json and audio_mix_plan.json")
    p_saha.add_argument("--soundtrack-plan", default=None, dest="soundtrack_plan", help="optional soundtrack_plan.json")
    p_saha.add_argument("--license-manifest", default=None, dest="license_manifest", help="optional sound_license_manifest.json")
    p_saha.add_argument("--soundtrack-probe-report", default=None, dest="soundtrack_probe_report", help="optional soundtrack_probe_report.json for selected music")

    p_vtra = sub.add_parser("visual-technique-review-apply")
    p_vtra.add_argument("--plan", required=True,
                        help="candidate visual_technique_plan.json")
    p_vtra.add_argument("--review", required=True,
                        help="visual_technique_review.json with decision and selected_option")
    p_vtra.add_argument("--out", required=True,
                       help="confirmed visual_technique_plan.json output")

    p_le = sub.add_parser("light-effects-plan")
    p_le.add_argument("contract", help="canonical segment_contract.json")
    p_le.add_argument("--build-profile", required=True, help="build_profile.json")
    p_le.add_argument("--effect-intent-plan", default=None, dest="effect_intent_plan",
                      help="optional neutral effect_intent_plan.json from FX1")
    p_le.add_argument("--out-dir", required=True, help="output directory for light effects artifacts")

    p_er = sub.add_parser("effect-revision-request")
    p_er.add_argument("--baseline-review", required=True, dest="baseline_review",
                      help="light_effects_baseline_review.json")
    p_er.add_argument("--light-effects-plan", default=None, dest="light_effects_plan",
                      help="optional light_effects_plan.json for source_effect_id and backend route evidence")
    p_er.add_argument("--out", required=True, help="effect_revision_request.json output")

    p_erd = sub.add_parser("effect-revision-draft")
    p_erd.add_argument("--request", required=True, help="effect_revision_request.json")
    p_erd.add_argument("--out-patch", required=True, dest="out_patch",
                       help="effect_recipe_patch.json draft output")
    p_erd.add_argument("--effect-intent-plan", default=None, dest="effect_intent_plan",
                       help="optional canonical effect_intent_plan.json source")
    p_erd.add_argument("--out-intent-draft", default=None, dest="out_intent_draft",
                       help="optional revised_effect_intent_plan.draft.json output")

    p_era = sub.add_parser("effect-revision-apply")
    p_era.add_argument("--draft", required=True, help="revised_effect_intent_plan.draft.json")
    p_era.add_argument("--out", required=True, help="reviewed effect_intent_plan.json output")
    p_era.add_argument("--reviewer", required=True, help="reviewer accepting this draft")
    p_era.add_argument("--reason", required=True, help="review reason for applying this draft")
    p_era.add_argument("--accept", action="store_true",
                       help="required explicit acceptance flag; without it the command fails closed")

    p_ecr = sub.add_parser("effect-collage-refs")
    p_ecr.add_argument("--project-map", required=True, dest="project_map",
                       help="project_material_map.json with reviewed material assets")
    p_ecr.add_argument("--wall-verdict", default=None, dest="wall_verdict",
                       help="material_wall_review_verdict.json with coarse keep/reject + visual_role")
    p_ecr.add_argument("--workbench-thumbnails", default=None, dest="workbench_thumbnails",
                       help="optional workbench_thumbnails.json for video still refs")
    p_ecr.add_argument("--wall-request", default=None, dest="wall_request",
                       help="optional material_wall_request.json for video keyframe refs")
    p_ecr.add_argument("--out", required=True,
                       help="effect_collage_media_refs.json output")
    p_ecr.add_argument("--max-refs", type=int, default=6, dest="max_refs",
                       help="maximum collage refs to emit")

    p_rtm = sub.add_parser("remotion-template-manifest")
    p_rtm.add_argument("--out", required=True,
                       help="remotion_effect_capability_manifest.json output")
    p_rtm.add_argument("--dictionary", default=None,
                       help="optional effect_template_dictionary.json path")
    p_rtm.add_argument("--reference-review", default=None, dest="reference_review",
                       help="optional effect_reference_*_review.json evidence artifact")

    p_rpp = sub.add_parser("remotion-prompt-pack")
    p_rpp.add_argument("--request", required=True, help="effect_revision_request.json")
    p_rpp.add_argument("--effect-intent-plan", required=True, dest="effect_intent_plan",
                       help="effect_intent_plan.json source for neutral effect intent")
    p_rpp.add_argument("--timeline", default=None, help="optional timeline_build.json for exact timing")
    p_rpp.add_argument("--collage-refs", default=None, dest="collage_refs",
                       help="optional effect_collage_media_refs.json to inject into training_opening_title jobs")
    p_rpp.add_argument("--out", required=True, help="remotion_prompt_pack.json output")
    p_rpp.add_argument("--output-dir", default="remotion_effects", dest="output_dir",
                       help="target directory hint for Remotion worker outputs")

    p_rwo = sub.add_parser("remotion-worker-outputs")
    p_rwo.add_argument("--prompt-pack", required=True, dest="prompt_pack",
                       help="remotion_prompt_pack.json")
    p_rwo.add_argument("--worker-outputs", required=True, dest="worker_outputs",
                       help="remotion_worker_outputs.json produced by a Remotion-capable worker")
    p_rwo.add_argument("--out-review", required=True, dest="out_review",
                       help="remotion_effect_review.json output for Workbench/Brownfield review")

    p_erv = sub.add_parser("effect-render-verification")
    p_erv.add_argument("--effect-intent-plan", required=True, dest="effect_intent_plan",
                       help="effect_intent_plan.json with planned effects")
    p_erv.add_argument("--remotion-review", required=True, dest="remotion_review",
                       help="accepted remotion_effect_review.json")
    p_erv.add_argument("--out", required=True,
                       help="effect_render_verification.json output")
    p_erv.add_argument("--root", default=None,
                       help="optional run root for resolving relative evidence refs")

    p_rws = sub.add_parser("remotion-worker-smoke")
    p_rws.add_argument("--prompt-pack", required=True, dest="prompt_pack",
                       help="remotion_prompt_pack.json")
    p_rws.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory where worker preview/rendered files should be written")
    p_rws.add_argument("--out-worker-outputs", required=True, dest="out_worker_outputs",
                       help="remotion_worker_outputs.json output")
    p_rws.add_argument("--dry-run", action="store_true",
                       help="write deterministic placeholder files for contract smoke tests")
    p_rws.add_argument("--command", default=None, dest="renderer_command",
                       help=("optional real worker command template; placeholders: "
                             "{job_json}, {job_id}, {preview_file}, {rendered_asset}, {duration_sec}"))

    p_rcd = sub.add_parser("remotion-composite-draft")
    p_rcd.add_argument("--review", required=True, help="accepted remotion_effect_review.json")
    p_rcd.add_argument("--base-video", required=True, dest="base_video",
                       help="base draft video to composite onto")
    p_rcd.add_argument("--out", required=True, help="non-canonical draft video output")
    p_rcd.add_argument("--report-out", default=None, dest="report_out",
                       help="optional remotion_composite_draft_report.json output")
    p_rcd.add_argument("--ffmpeg", default="ffmpeg", help="ffmpeg executable")
    p_rcd.add_argument("--dry-run", action="store_true",
                       help="write a deterministic draft/report without invoking ffmpeg")

    # --- P1 verification tool pack ---
    p_ta = sub.add_parser("timeline-audit")
    p_ta.add_argument("timeline", help="timeline_build.json")
    p_ta.add_argument("--out", required=True, help="timeline_invariants.json output")
    p_ta.add_argument("--expected-duration", type=float, dest="expected_duration",
                      default=None, help="expected timeline duration (sec) from brief/contract")
    p_ta.add_argument("--must-include", type=int, nargs="*", dest="must_include",
                      default=None, help="must-include segment ids")

    p_ba = sub.add_parser("broll-audit")
    p_ba.add_argument("timeline", help="timeline_build.json")
    p_ba.add_argument("--out", required=True, help="broll_audit.json output")
    p_ba.add_argument("--target-ratio", type=float, dest="target_ratio",
                      default=None, help="max acceptable b-roll ratio (policy)")
    p_ba.add_argument("--max-source-repeats", type=int, dest="max_source_repeats",
                      default=None, help="max reuse count for a single source (policy)")

    p_nvi = sub.add_parser("new-visual-audit")
    p_nvi.add_argument("timeline", help="timeline_build.json")
    p_nvi.add_argument("--out", required=True,
                       help="new_visual_information_audit.json output")
    p_nvi.add_argument("--min-new-visual-ratio", type=float, default=0.6,
                       dest="min_new_visual_ratio")
    p_nvi.add_argument("--max-repeated-hold-sec", type=float, default=3.0,
                       dest="max_repeated_hold_sec")

    p_bfa = sub.add_parser("black-frame-audit")
    p_bfa.add_argument("video", help="rendered video to scan for black/blank runs")
    p_bfa.add_argument("--out", required=True, help="black_frame_audit.json output")
    p_bfa.add_argument("--fps", type=float, default=2.0, help="luma sampling rate")
    p_bfa.add_argument("--min-run-sec", type=float, default=0.4, dest="min_run_sec")

    p_vn = sub.add_parser("validate-needs")
    p_vn.add_argument("needs", help="material_needs.json (legacy nested or flat)")
    p_vn.add_argument("--migrate", action="store_true",
                      help="allocate stable need_ids for needs that lack one (one-time)")
    p_vn.add_argument("--out", help="write canonical needs here if valid")

    p_ll = sub.add_parser("lineage-link")
    p_ll.add_argument("needs", help="canonical material_needs.json")
    p_ll.add_argument("--build-brief", action="store_true", dest="build_brief",
                      help="project needs into a shooting_brief skeleton (need_id-keyed)")
    p_ll.add_argument("--brief", default=None, help="shooting_brief.json to link")
    p_ll.add_argument("--project-map", default=None, dest="project_map",
                      help="project_material_map.json (satisfies edges)")
    p_ll.add_argument("--contract", default=None, help="segment_contract.json (need_refs)")
    p_ll.add_argument("--out", default=None, help="write the brief/lineage artifact here")

    p_md = sub.add_parser("material-delta")
    p_md.add_argument("needs", help="canonical material_needs.json")
    p_md.add_argument("--project-map", default=None, dest="project_map",
                      help="project_material_map.json (satisfies edges)")
    p_md.add_argument("--out", default=None, help="write material_delta.json here")

    p_mgf = sub.add_parser("material-generation-fallback")
    p_mgf.add_argument("delta", help="material_delta.json")
    p_mgf.add_argument("--needs", default=None, help="material_needs.json")
    p_mgf.add_argument("--story-world", default=None, dest="story_world",
                       help="story_world.json (optional prompt context)")
    p_mgf.add_argument("--creative-concept", default=None, dest="creative_concept",
                       help="creative_concept.json (optional prompt context)")
    p_mgf.add_argument("--screenplay-beats", default=None, dest="screenplay_beats",
                       help="screenplay_beats.json (optional prompt context)")
    p_mgf.add_argument("--director-shot-plan", default=None, dest="director_shot_plan",
                       help="director_shot_plan.json (optional prompt context)")
    p_mgf.add_argument("--out", default=None,
                       help="write material_generation_fallback.json here")

    p_mml = sub.add_parser("material-map-lifecycle")
    p_mml.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for lifecycle artifacts + report")
    p_mml.add_argument("--needs", default=None, help="material_needs.json (required side)")
    p_mml.add_argument("--maps-dir", default=None, dest="maps_dir",
                       help="directory of per-asset *.map.json")
    p_mml.add_argument("--project-map", default=None, dest="project_map",
                       help="project_material_map.json")
    p_mml.add_argument("--material-db", default=None, dest="material_db",
                       help="materials_db.json (alternative actual-side source)")
    p_mml.add_argument("--contract", default=None, help="segment_contract.json")
    p_mml.add_argument("--decisions", default=None, help="revision_decisions.json")
    p_mml.add_argument("--categories", default=None, help="material_categories.json (optional)")

    p_mmra = sub.add_parser("material-map-review-apply")
    p_mmra.add_argument("--maps-dir", required=True, dest="maps_dir",
                        help="directory of per-asset *.map.json files to update")
    p_mmra.add_argument("--needs", required=True,
                        help="canonical material_needs.json")
    p_mmra.add_argument("--verdict", required=True,
                        help="material_map_review_verdict.json from reviewer/subagent")
    p_mmra.add_argument("--out", required=True,
                        help="reviewed project_material_map.json output")
    p_mmra.add_argument("--material-db", default=None, dest="material_db",
                        help="mapped materials_db.json with material_map_status entries")
    p_mmra.add_argument("--skipped-policy", default=None, dest="skipped_policy",
                        choices=["ignore-with-report"],
                        help="handle decisions for timeout-skipped assets without fabricating edges")

    p_shp = sub.add_parser("source-highlight-plan")
    p_shp.add_argument("--source", required=True, help="single long source video")
    p_shp.add_argument("--out-dir", required=True, dest="out_dir",
                       help="run/output directory for source_timeline_map, highlight_selection_plan, and rough_cut_plan")
    p_shp.add_argument("--soundtrack-probe", default=None, dest="soundtrack_probe",
                       help="optional soundtrack_probe_report.json for source audio")
    p_shp.add_argument("--intent", default="",
                       help="brief selection intent such as internship highlights, ending, or music refill")
    p_shp.add_argument("--target-sec", type=float, default=90.0, dest="target_sec")
    p_shp.add_argument("--window-sec", type=float, default=12.0, dest="window_sec")
    p_shp.add_argument("--clip-sec", type=float, default=10.0, dest="clip_sec")

    p_smm = sub.add_parser("source-material-matrix")
    p_smm.add_argument("--source", required=True, help="single long source video")
    p_smm.add_argument("--out-dir", required=True, dest="out_dir",
                       help="run/output directory for source_material_matrix.json")
    p_smm.add_argument("--window-sec", type=float, default=12.0, dest="window_sec")
    p_smm.add_argument("--visual-review", default=None, dest="visual_review",
                       help="optional source_material_matrix_review.json")
    p_smm.add_argument("--soundtrack-probe", default=None, dest="soundtrack_probe",
                       help="optional precomputed source_soundtrack_probe_report.json")

    p_ssm = sub.add_parser("source-section-map")
    p_ssm.add_argument("--video", required=True, help="single long source video")
    p_ssm.add_argument("--out", required=True, help="source_section_map.json output")
    p_ssm.add_argument("--soundtrack-probe", default=None, dest="soundtrack_probe",
                       help="optional source_soundtrack_probe_report.json")
    p_ssm.add_argument("--target-section-sec", type=float, default=80.0, dest="target_section_sec")
    p_ssm.add_argument("--min-section-sec", type=float, default=24.0, dest="min_section_sec")

    p_smp = sub.add_parser("source-motion-profile")
    p_smp.add_argument("--video", required=True, help="single long source video")
    p_smp.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for source_motion_profile.json and source_motion_points.jpg")
    p_smp.add_argument("--soundtrack-probe", default=None, dest="soundtrack_probe",
                       help="optional source_soundtrack_probe_report.json")
    p_smp.add_argument("--start-sec", type=float, default=0.0, dest="start_sec")
    p_smp.add_argument("--end-sec", type=float, default=None, dest="end_sec")
    p_smp.add_argument("--sample-sec", type=float, default=1.0, dest="sample_sec")

    p_sds = sub.add_parser("source-dialogue-script")
    p_sds.add_argument("--json3", required=True, help="yt-dlp json3 subtitle file")
    p_sds.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for source_transcript.json and dialogue_edit_script.json")
    p_sds.add_argument("--rough-windows", default=None, dest="rough_windows",
                       help="optional rough dialogue_highlight_windows.json to expand to complete sentences")
    p_sds.add_argument("--target-sec", type=float, default=None, dest="target_sec",
                       help="soft target duration; sentence completeness wins over exact time")

    p_mwb = sub.add_parser("material-wall-build")
    p_mwb.add_argument("--db", required=True, help="materials_db.json")
    p_mwb.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for photo/video wall images")
    p_mwb.add_argument("--out", required=True, help="material_wall_request.json output")
    p_mwb.add_argument("--photo-batch-size", type=int, default=60, dest="photo_batch_size",
                       help="max photos per wall image")
    p_mwb.add_argument("--video-batch-size", type=int, default=10, dest="video_batch_size",
                       help="max video strips per wall image")

    p_mwb.add_argument("--limit", type=int,
                       help="only include the first N files for bounded operator passes")

    p_mwra = sub.add_parser("material-wall-review-apply")
    p_mwra.add_argument("--db", required=True, help="materials_db.json")
    p_mwra.add_argument("--verdict", required=True, help="material_wall_review_verdict.json")
    p_mwra.add_argument("--out", required=True, help="reviewed materials_db.json output")

    p_mdsfw = sub.add_parser("material-db-slice-from-wall")
    p_mdsfw.add_argument("--db", required=True, help="materials_db.json")
    p_mdsfw.add_argument("--wall-request", required=True, dest="wall_request",
                         help="material_wall_request.json used as bounded scope")
    p_mdsfw.add_argument("--out", required=True, help="bounded materials_db.json output")

    p_mr = sub.add_parser("material-revision")
    p_mr.add_argument("contract", help="segment_contract.json (not mutated)")
    p_mr.add_argument("--delta", required=True, help="material_delta.json")
    p_mr.add_argument("--decisions", required=True, help="revision_decisions.json")
    p_mr.add_argument("--out-contract", required=True, dest="out_contract",
                      help="revised_segment_contract.json output")
    p_mr.add_argument("--out-revision", required=True, dest="out_revision",
                      help="material_revision.json output")
    p_mr.add_argument("--categories", default=None, help="material_categories.json (optional)")

    p_pmm = sub.add_parser("project-material-map")
    p_pmm.add_argument("--maps-dir", required=True, dest="maps_dir",
                       help="directory of per-asset *.map.json files")
    p_pmm.add_argument("--needs", default=None,
                       help="optional canonical material_needs.json")
    p_pmm.add_argument("--out", required=True, help="project_material_map.json output")

    p_vdc = sub.add_parser("visual-diversity-coverage")
    p_vdc.add_argument("project_map", help="project_material_map.json")
    p_vdc.add_argument("--out", required=True, help="visual_diversity_coverage.json output")
    p_vdc.add_argument("--min-visual-family-coverage", type=float, default=0.7,
                       dest="min_visual_family_coverage",
                       help="minimum visual_family scene coverage required before VD2")
    p_vdc.add_argument("--min-angle-scale-coverage", type=float, default=0.6,
                       dest="min_angle_scale_coverage",
                       help="minimum angle_scale scene coverage required before VD2")
    p_vdc.add_argument("--consistency-review", action="append", default=[],
                       help="independent project_material_map review; repeatable")
    p_vdc.add_argument("--min-consistency-ratio", type=float, default=0.7,
                       dest="min_consistency_ratio",
                       help="minimum coarse-label agreement required before VD2")
    p_vdc.add_argument("--min-consistency-scenes", type=int, default=10,
                       dest="min_consistency_scenes",
                       help="minimum independently reviewed comparable scenes")

    p_vdr = sub.add_parser("visual-diversity-review")
    p_vdr.add_argument("project_map", help="project_material_map.json")
    p_vdr.add_argument("--review", required=True, help="visual_diversity_review.json")
    p_vdr.add_argument("--out", required=True, help="reviewed project_material_map.json")

    p_vfn = sub.add_parser("visual-family-normalize")
    p_vfn.add_argument("review", help="visual_diversity_review.json")
    p_vfn.add_argument("--vocabulary", required=True, help="visual_family_vocabulary.json")
    p_vfn.add_argument("--out", required=True, help="normalized visual_diversity_review.json output")

    p_sna = sub.add_parser("semantic-novelty-audit")
    p_sna.add_argument("timeline", help="timeline_build.json")
    p_sna.add_argument("--video", required=True, help="rendered video for perceptual hashing")
    p_sna.add_argument("--out", required=True, help="semantic_novelty_audit.json output")
    p_sna.add_argument("--max-distance", type=int, default=10, dest="max_distance")
    p_sna.add_argument("--min-distinct-ratio", type=float, default=0.5, dest="min_distinct_ratio")
    p_sna.add_argument("--max-similar-run-sec", type=float, default=6.0, dest="max_similar_run_sec")

    p_apa = sub.add_parser("action-progression-audit")
    p_apa.add_argument("segments", help="contract/segments JSON with clips + required_functions")
    p_apa.add_argument("--out", required=True, help="action_progression_audit.json output")
    p_apa.add_argument("--min-coverage", type=float, default=0.6, dest="min_coverage")

    p_jp = sub.add_parser("jumpcut-plan")
    p_jp.add_argument("material_map", help="per-asset material map JSON")
    p_jp.add_argument("--out", required=True, help="jumpcut_plan.json")
    p_jp.add_argument("--min-silence", type=float, default=1.0, dest="min_silence")

    p_ja = sub.add_parser("jumpcut-apply")
    p_ja.add_argument("plan", help="approved jumpcut_plan.json")
    p_ja.add_argument("--out", required=True, help="processed output video")
    p_ja.add_argument("--lineage", required=True, help="processed material lineage JSON")

    p_jr = sub.add_parser("jumpcut-review")
    p_jr.add_argument("plan", help="jumpcut_plan.json")
    p_jr.add_argument("--verdict", required=True, help="agent verdict JSON")
    p_jr.add_argument("--out", required=True, help="approved jumpcut plan JSON")

    p_capa = sub.add_parser("caption-audit")
    p_capa.add_argument("captions", nargs="?", default=None,
                        help="caption events JSON (list or {captions:[...]}); omit when using --srt")
    p_capa.add_argument("--srt", default=None, help="subtitles.srt to audit directly")
    p_capa.add_argument("--out", required=True, help="caption_audit.json output")
    p_capa.add_argument("--max-gap-sec", type=float, dest="max_gap_sec",
                        default=None, help="flag uncaptioned gaps over this many sec")
    p_capa.add_argument("--max-cps", type=float, dest="max_cps",
                        default=None, help="max reading speed in chars per second")

    p_kg = sub.add_parser("keyframe-grid")
    p_kg.add_argument("video", help="render candidate video")
    p_kg.add_argument("--out", required=True, help="keyframe_grid.jpg output")
    p_kg.add_argument("--samples", type=int, default=12, help="number of keyframes")
    p_kg.add_argument("--columns", type=int, default=4, help="grid columns")

    p_sc = sub.add_parser("sampling-coverage")
    p_sc.add_argument("sampling_plan", help="sampling_plan.json")
    p_sc.add_argument("--shots", required=True, help="shot list JSON")
    p_sc.add_argument("--anchors", default=None, help="optional audio anchors JSON")
    p_sc.add_argument("--out", required=True, help="sampling_coverage_report.json output")
    p_sc.add_argument("--tolerance-sec", type=float, default=0.35, dest="tolerance_sec")
    p_sc.add_argument("--max-gap-sec", type=float, default=4.0, dest="max_gap_sec")

    p_mw = sub.add_parser("montage-wall")
    p_mw.add_argument("video", help="source video")
    p_mw.add_argument("--sampling-plan", required=True, dest="sampling_plan")
    p_mw.add_argument("--coverage-report", required=True, dest="coverage_report")
    p_mw.add_argument("--out", required=True, help="wall PNG output")
    p_mw.add_argument("--sidecar", required=True, help="montage_wall.json output")
    p_mw.add_argument(
        "--profile",
        default="material_wall",
        choices=["material_wall", "timeline_wall", "segment_strip"],
    )
    p_mw.add_argument("--max-cells-per-page", type=int, default=96, dest="max_cells_per_page")
    p_mw.add_argument("--max-page-height-px", type=int, default=4096, dest="max_page_height_px")

    p_pfc = sub.add_parser("perception-field-check")
    p_pfc.add_argument("video", help="read-only source video")
    p_pfc.add_argument("--out", required=True, help="output directory for perception field artifacts")
    p_pfc.add_argument("--max-cells-per-page", type=int, default=96, dest="max_cells_per_page")
    p_pfc.add_argument("--max-page-height-px", type=int, default=4096, dest="max_page_height_px")
    p_pfc.add_argument(
        "--tolerance-sec",
        type=float,
        default=0.35,
        dest="tolerance_sec",
        help="single drift budget shared by the planner anchor clamp and coverage tolerance",
    )

    p_va = sub.add_parser("visual-audit")
    p_va.add_argument("video", help="render candidate video")
    p_va.add_argument("--out", required=True, help="visual_audit.json output")
    p_va.add_argument("--grid", default=None, help="keyframe_grid.jpg output path")
    p_va.add_argument("--samples", type=int, default=12, help="number of keyframes")
    p_va.add_argument("--columns", type=int, default=4, help="grid columns")

    p_ve = sub.add_parser("verify-evidence")
    p_ve.add_argument("video", help="render candidate video")
    p_ve.add_argument("--timeline", required=True, help="timeline_build.json")
    p_ve.add_argument("--out-dir", required=True, help="four-layer evidence output directory")
    p_ve.add_argument("--overview-samples", type=int, default=48)
    p_ve.add_argument("--chapter-samples", type=int, default=16)
    p_ve.add_argument("--critical-samples", type=int, default=32)

    p_fpv = sub.add_parser("final-product-verify")
    p_fpv.add_argument("video", help="final/draft video candidate")
    p_fpv.add_argument("--out-dir", required=True, dest="out_dir",
                       help="directory for keyframe_grid, visual_audit, final_audio, soundtrack_probe, and bundle")
    p_fpv.add_argument("--samples", type=int, default=12, help="number of keyframes")

    p_ra = sub.add_parser("replay-acceptance")
    p_ra.add_argument("timeline", nargs="?", help="timeline_build.json")
    p_ra.add_argument("--scenario", default=None, help="deterministic replay scenario id")
    p_ra.add_argument("--gates", help="JSON object of tier-1 gate artifacts")
    p_ra.add_argument("--verdicts", help="JSON list of judge verdicts")
    p_ra.add_argument("--jumpcut-plan", default=None)
    p_ra.add_argument("--new-visual-audit", default=None)
    p_ra.add_argument("--adaptation", default=None,
                      help="JSON evidence for duration/chapter adaptation decisions")
    p_ra.add_argument("--out", required=True, help="m4_replay_acceptance.json output")

    # --- P3 optional CapCut backend ---
    p_ccd = sub.add_parser("capcut-draft")
    p_ccd.add_argument("timeline", help="timeline_build.json")
    p_ccd.add_argument("--out", required=True, help="capcut_draft_manifest.json output")
    p_ccd.add_argument("--project", default=None, help="project name")

    p_ccf = sub.add_parser("capcut-finalize")
    p_ccf.add_argument("--video", required=True, help="CapCut exported video (capcut_exported.mp4)")
    p_ccf.add_argument("--out", required=True, help="output final video path (final.mp4)")
    p_ccf.add_argument("--bgm", required=True, help="BGM file path")
    p_ccf.add_argument("--outro-title", required=True, dest="outro_title", help="Outro card title line")
    p_ccf.add_argument("--outro-address", required=True, dest="outro_address", help="Outro card address line")
    p_ccf.add_argument("--outro-extra", dest="outro_extra", help="Outro card extra line (optional)")
    p_ccf.add_argument("--bgm-vol", type=float, dest="bgm_vol", default=0.25, help="BGM volume (default: 0.25)")


    # --- WHY layer: narrative blueprint gate ---
    p_bp = sub.add_parser("blueprint-coverage")
    p_bp.add_argument("blueprint", help="blueprint.json (thesis + beats[])")
    p_bp.add_argument("contract", help="segment_contract.json")
    p_bp.add_argument("--out", default=None, help="blueprint_coverage.json output (optional)")

    p_bpc = sub.add_parser("blueprint-compile")
    p_bpc.add_argument("blueprint", help="blueprint.md 路徑")
    p_bpc.add_argument("--out", help="輸出 JSON 路徑")

    p_b2c = sub.add_parser("blueprint-to-contract")
    p_b2c.add_argument("blueprint", help="blueprint.json (thesis + beats[])")
    p_b2c.add_argument("decisions", help="decisions.json (per-beat editorial decisions)")
    p_b2c.add_argument("--material-needs", default=None,
                       help="optional material_needs.json; maps need_ids to segments by beat order when decisions omit refs")
    p_b2c.add_argument("--music", default=None, help="music dict json (optional)")
    p_b2c.add_argument("--out", default="segment_contract.json", help="輸出 segment_contract.json")


    # --- P2 creator profile ---
    p_cp = sub.add_parser("creator-profile")
    p_cp.add_argument("profile", nargs="?", default=None,
                      help="creator_profile.json to resolve (omit with --init)")
    p_cp.add_argument("--init", action="store_true", help="write a default creator_profile.json")
    p_cp.add_argument("--out", default="creator_profile.json", help="output path for --init")
    p_cp.add_argument("--brief", default=None, help="brief.json to overlay (brief overrides profile)")

    args = parser.parse_args()

    dispatch = VIDEO_TOOLS_DISPATCH

    if not args.command or args.command not in dispatch:
        parser.print_help()
        sys.exit(1)

    try:
        dispatch[args.command](args)
    except ToolError as e:
        die(str(e))
    except Exception as e:
        import traceback
        print(traceback.format_exc(), file=sys.stderr)
        die(f"unexpected error: {str(e)}")


if __name__ == "__main__":
    main()
