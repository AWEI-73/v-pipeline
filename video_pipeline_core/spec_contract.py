"""spec_contract.py — SPEC 合約層的程式面(canonical = normalized JSON)。

對應 skills/spec-contract.md。提供純函式 validator,只檢查必要欄位、**不發明會改變
意圖的預設**(BUILD 工具消費 normalized JSON,不重解釋 SPEC)。

第一階段(Node 0-1):brief gate validator。Node 3 的 segment_contract validator
後續加在此檔。"""
import json

BRIEF_VIDEO_TYPES = ("graduation_mv", "narration_video", "event_recap", "knowledge")
BRIEF_START_MODES = ("script_first", "material_first", "hybrid")
BRIEF_FALLBACK = ("reshoot_first", "generated_first", "stock_bridge", "review")
BRIEF_REVIEW = ("normal", "high")

# 本專案預設(學員多半能補拍 → 不被素材池綁死)
BRIEF_DEFAULTS = {"spec_start_mode": "script_first", "can_reshoot": True,
                  "fallback_policy": "reshoot_first", "review_level": "normal"}


def validate_brief(brief):
    """純函式:驗 Node 0-1 brief(JSON dict)。回 {ok, errors, warnings}。
    不補預設、不改值;只報缺漏/非法值,讓上游 agent 補齊(SPEC 是互動步驟)。"""
    errors, warnings = [], []
    if not isinstance(brief, dict):
        return {"ok": False, "errors": ["brief 必須是 JSON 物件"], "warnings": []}

    required = ("video_type", "spec_start_mode", "can_reshoot", "fallback_policy")
    for f in required:
        if brief.get(f) in (None, ""):
            errors.append(f"缺必填欄位 {f}(SPEC 互動步驟:應問清楚,勿假設)")

    def _enum(field, allowed):
        v = brief.get(field)
        if v is not None and v not in allowed:
            errors.append(f"{field}='{v}' 非法(可:{'/'.join(allowed)})")

    _enum("video_type", BRIEF_VIDEO_TYPES)
    _enum("spec_start_mode", BRIEF_START_MODES)
    _enum("fallback_policy", BRIEF_FALLBACK)
    _enum("review_level", BRIEF_REVIEW)
    if "can_reshoot" in brief and not isinstance(brief["can_reshoot"], bool):
        errors.append("can_reshoot 必須是 true/false")

    # 軟提醒(不擋):品質欄位缺會讓下游 SPEC 變猜測
    for f in ("must_include", "target_length", "audience", "tone", "review_level"):
        if brief.get(f) in (None, "", []):
            warnings.append(f"建議補 {f}(缺則下游 SPEC 易變猜測)")
    return {"ok": not errors, "errors": errors, "warnings": warnings}


# ── Node 3: segment contract(core + facets,canonical normalized JSON)──────────
TIMELINE_SOURCES = ("beat", "tts", "fixed")
AUDIO_ROLES = ("music", "duck", "diegetic")
# Node 7 editing_grammar 列舉
EDIT_ROLES = ("hero", "proof", "support", "bridge", "mood", "filler")
BEAT_ALIGNMENTS = ("none", "music", "speech", "action", "emotion", "chronology", "thematic")
COMPRESSIBILITY = ("locked", "flexible", "expendable")
# 需強制人工複核的段(section_role 命中 → review_required 應為 true)
REVIEW_ROLES = ("opening", "closing", "title")


def _seg_id(seg, i):
    return (seg.get("core") or {}).get("section_role") or seg.get("segment") or f"#{i}"


def load_material_categories(path):
    """(I/O) 讀地圖規範詞彙(examples/material_categories.json)→ {id: category} dict。"""
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return {c["id"]: c for c in data.get("categories", [])}


def validate_segment_contract(contract, categories=None):
    """純函式:驗 Node 3 segment contract(core+facets normalized JSON)。
    contract = {segments:[...]} 或 [segment,...]。**只查必填、不發明會改意圖的預設**。
    categories(選配):合法 category id 集合(來自地圖規範詞彙)→ 驗 material_fit.category。
    回 {ok, errors, warnings}。"""
    cat_ids = set(categories) if categories else None
    if isinstance(contract, dict):
        segs = contract.get("segments", [])
        _cfg = contract.get("run_config") or {}
        stock_first = (contract.get("material_source_mode") == "stock_first"
                       or _cfg.get("material_source_mode") == "stock_first")
    elif isinstance(contract, list):
        segs = contract
        stock_first = False
    else:
        return {"ok": False, "errors": ["contract 必須是 {segments:[...]} 或 list"], "warnings": []}
    errors, warnings = [], []
    if not segs:
        errors.append("contract 至少要 1 段")

    for i, seg in enumerate(segs):
        sid = _seg_id(seg, i)
        core = seg.get("core") or {}
        mat = seg.get("material_fit") or {}
        aud = seg.get("audio") or {}
        vis = seg.get("visual_style") or {}
        txt = seg.get("text_layer")

        def err(msg):
            errors.append(f"[{sid}] {msg}")

        creative_exception = seg.get("creative_exception")
        if creative_exception is not None:
            from .creative_exception import validation_errors
            for issue in validation_errors(creative_exception):
                err(f"creative_exception {issue}")

        # core
        if not core.get("story_purpose"):
            err("core.story_purpose 必填(這段為什麼存在)")
        ts = core.get("timeline_source")
        if not ts:
            err("core.timeline_source 必填(beat/tts/fixed)")
        elif ts not in TIMELINE_SOURCES:
            err(f"core.timeline_source='{ts}' 非法(可:{'/'.join(TIMELINE_SOURCES)})")

        # blueprint_ref(選配,WHY 層追溯):有就驗形狀(str 或 list[str]);
        # 真正的「ref 是否指到存在的 beat / beat 是否被實現」由 blueprint.beat_coverage 跨檔守門
        bref = core.get("blueprint_ref")
        if bref is not None:
            ok_shape = (isinstance(bref, str) and bref.strip()) or (
                isinstance(bref, list) and bref
                and all(isinstance(r, str) and r.strip() for r in bref))
            if not ok_shape:
                err("core.blueprint_ref 形狀非法(應為非空 beat id 字串或字串陣列)")

        # material_fit(素材撐的視覺段需 visual_desc+reason;純文字/title 段可 material_fit:none)
        if mat:
            if not mat.get("visual_desc"):
                err("material_fit.visual_desc 必填(素材撐的視覺段)")
            if not mat.get("reason"):
                err("material_fit.reason 必填")
            # 地圖規範:category 對照詞彙(有提供 vocab 才驗)
            if cat_ids is not None and mat.get("category") and mat["category"] not in cat_ids:
                err(f"material_fit.category='{mat['category']}' 不在地圖規範詞彙")
            # 必放/缺料會走補拍 → 建議有 collection_instructions(=給學員的拍攝指引)
            if mat.get("must_include") and not mat.get("collection_instructions"):
                warnings.append(f"[{sid}] must_include 段建議補 collection_instructions(缺料即補拍指引)")
            # stock-first 守門:可走 stock 的段缺 search_query → 會 fallback 用中文 visual_desc,Pexels 命中差
            stockable = not (mat.get("must_include") or core.get("identity_sensitive")
                             or core.get("proof_critical"))
            if stock_first and stockable and not mat.get("search_query"):
                warnings.append(f"[{sid}] stock_first 但缺 material_fit.search_query(英文)"
                                "→ 會 fallback 用中文 visual_desc 抓 Pexels,命中差;請補")
        elif core.get("section_role") not in ("title",):
            warnings.append(f"[{sid}] 無 material_fit;若非純文字段,應補(或明確標 none)")

        # audio
        role = aud.get("role")
        if not role:
            err("audio.role 必填(music/duck/diegetic)")
        elif role not in AUDIO_ROLES:
            err(f"audio.role='{role}' 非法(可:{'/'.join(AUDIO_ROLES)})")
        if aud and not aud.get("reason"):
            err("audio.reason 必填")

        # visual_style
        if not vis.get("layout"):
            err("visual_style.layout 必填")
        if not vis.get("pace"):
            err("visual_style.pace 必填")
        if not vis.get("reason"):
            err("visual_style.reason 必填")

        # text_layer:有字 → 要 reason;無字 → 要明確 none
        if txt in (None,):
            warnings.append(f"[{sid}] text_layer 未明確;無字幕請標 \"none\"(留白是顯式設計)")
        elif txt != "none" and isinstance(txt, dict):
            has_text = any(txt.get(k) for k in ("label", "narrative", "subtitle", "name_super"))
            if has_text and not txt.get("reason"):
                err("text_layer 有字但缺 reason(為什麼要這段文字)")

        # editing_grammar(Node 7,選配:有就驗列舉 + compressibility=locked 應 review)
        eg = seg.get("editing_grammar")
        if isinstance(eg, dict):
            if eg.get("role") and eg["role"] not in EDIT_ROLES:
                err(f"editing_grammar.role='{eg['role']}' 非法(可:{'/'.join(EDIT_ROLES)})")
            if eg.get("beat_alignment") and eg["beat_alignment"] not in BEAT_ALIGNMENTS:
                err(f"editing_grammar.beat_alignment 非法(可:{'/'.join(BEAT_ALIGNMENTS)})")
            if eg.get("compressibility") and eg["compressibility"] not in COMPRESSIBILITY:
                err(f"editing_grammar.compressibility 非法(可:{'/'.join(COMPRESSIBILITY)})")
            if not eg.get("reason"):
                warnings.append(f"[{sid}] editing_grammar 建議補 reason")

        # review_required 守門:高權重/必放段應為 true
        needs_review = (core.get("section_role") in REVIEW_ROLES or mat.get("must_include")
                        or core.get("identity_sensitive") or seg.get("source") == "generated"
                        or aud.get("role") == "diegetic")
        if needs_review and not core.get("review_required"):
            warnings.append(f"[{sid}] 高權重/必放/原音段建議 core.review_required=true")

    return {"ok": not errors, "errors": errors, "warnings": warnings}


# ── Node 8: 缺口 fallback 路由選擇(誠實性合約)──────────────────────────────
from .vt_core import FALLBACK_ROUTES  # noqa: E402,F401


def suggest_fallback_route(coverage_status, *, identity_sensitive=False, proof_critical=False,
                           must_include=False, section_role=None, can_reshoot=True,
                           material_collected=True, explicitly_allowed=()):
    """純函式:依覆蓋狀態 + 段性質 → 建議 fallback 路由(Node 8)。
    鐵則:**must_include / identity-sensitive / proof-critical 缺口絕不靜默用泛用
    stock/generated 假裝真實**,預設補拍或人工複核。
    回 {selected_route, allowed_routes, rejected_routes, review_required, reason}。"""
    allow = set(explicitly_allowed or ())

    def out(selected, allowed, rejected, review, reason):
        return {"selected_route": selected, "allowed_routes": sorted(allowed),
                "rejected_routes": sorted(rejected), "review_required": review, "reason": reason}

    if not material_collected:
        return out("collect_material", {"collect_material"}, set(), False,
                   "素材尚未收集:由 segment contract 產生預期素材需求/收集任務,不算失敗缺口")
    if coverage_status == "covered":
        return out("none", {"none"}, set(), False, "覆蓋足夠")

    high = section_role in ("opening", "closing", "climax", "title")

    if must_include or identity_sensitive:
        route = "reshoot" if can_reshoot else "dashboard_review"
        why = "必放(must_include)" if must_include else "identity-sensitive"
        return out(route, {"reshoot", "dashboard_review"}, {"stock_bridge", "generated"}, True,
                   f"{why} 缺口:預設補拍或人工複核;不可用泛用 stock/generated 假裝真實事件")
    if proof_critical:
        route = "reshoot" if can_reshoot else "dashboard_review"
        return out(route, {"reshoot", "script_rewrite", "dashboard_review"}, {"stock_bridge"}, True,
                   "proof-critical 弱/缺:補拍 / 改寫 / 人工複核")
    if high and not (allow & {"stock_bridge", "generated", "text_bridge"}):
        return out("dashboard_review", {"dashboard_review", "reshoot"}, set(), True,
                   "開場/收尾/高潮段弱缺且未明確允許 fallback → 人工複核")
    # mood / bridge / filler 連接性段
    allowed = {"stock_bridge", "generated", "text_bridge", "script_rewrite", "drop_segment"}
    sel = "drop_segment" if section_role == "filler" else (
        "stock_bridge" if coverage_status == "missing" else "text_bridge")
    return out(sel, allowed, set(), False,
               "連接性/氛圍段:可 stock_bridge/generated/text_bridge/改寫;filler 缺優先 drop")


# ── BUILD 層(Node 9-14)canonical 詞彙(鎖住 skill 契約與未來程式一致)──────────
EXECUTION_ROUTE_STATUS = ("ready", "needs_fallback", "needs_collection",
                          "needs_reshoot", "needs_review", "blocked")          # Node 9
TIMELINE_TRACKS = ("video_main", "video_overlay", "audio_original", "audio_music",
                   "audio_voiceover", "text_overlay", "effects")               # Node 10
EDITOR_DECISIONS = ("approve", "auto_fix", "route_change", "human_review",
                    "block", "rerender")                                        # Node 11
VERIFY_STATUS = ("pass", "warn", "fail", "blocked")                          # Node 12
RENDER_MODES = ("preview", "review", "final", "segment_debug")              # Node 13
