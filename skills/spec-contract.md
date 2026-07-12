---
name: spec-contract
description: 擁有 Node 3「正規化 segment contract(core + facets)」、合約 bundle 規則、互動設計規則、欄位→執行對映。video SPEC 是合約不是鬆散 prompt;canonical = normalized JSON(segment_contract.json)。導演/編劇/音控/特效/小編各自擁有一個 facet,別把整份 schema 塞進 director.md。
---

# Spec-Contract Skill — Segment Contract / Production Facets

> **video SPEC 是合約,不是鬆散 prompt。** 太模糊 → BUILD 亂猜;太大又扁 → 不可維護。
> 用「**小 core + 專業 facets**」。每個 facet 帶 `reason`(機器可讀、可稽核、verify 可查)。

## Canonical 與 bundle 交接(roadmap.md canonical roadmap)

### M0 capability 與規格優先級

在撰寫能力要求前，先執行：

```powershell
python video_tools.py capability-manifest --out capability_manifest.json
```

`required_capabilities` 只能引用 manifest 已公開的能力。未公開或列在
`unsupported` 的能力會由 `spec_review` 規則 `B5 out_of_capability` 阻擋。

規格優先級：

- `tier1`：素材誠實、語意正確、proof/identity/testimony、GAP、VERIFY 交付閘。
- `tier2`：故事、鏡頭功能、節奏與品質目標。
- `tier3`：片長、特效、字幕、轉場、音樂等風格偏好。

低層規格不得破壞高層規格；`target_length` 屬於 `tier3`，後續必須讓步給
素材供給計算出的 `max_honest_duration_sec`。
- **`segment_contract.json` 是 canonical SPEC 輸入**;adapter(`contract_adapter.py`)生成的
  legacy flat script 只是「執行載荷」,不是 SPEC、不可當真相。
- **Node 1-8 contract bundle → Node 9 assembly plan**:本 skill 擁有 Node 3 合約語意 +
  Node 1-8→Node 9 的對映規則(每個重要欄位都要對映到 BUILD 輸出 / validation / review gate)。
- **BUILD provider 不寫死在 SPEC**:`segment_contract.json` 只說 fallback 是否允許、哪些段不可替代；
  `build_profile.json` 決定 Antigravity / assistant_imagegen / Pexels / effects backend 等本次 run 的工具選擇。
  `contract_adapter.py run` 會把 `build_profile.json` 與 `generated_asset_requests.json` 寫入 manifest。

## 素材來源模式(stock-first / 頂層 block)
若整支用 stock(Pexels)等概念素材(非真實事件),contract **頂層**要宣告(否則不會真的走 stock):
```json
{ "material_source_mode": "stock_first", "story_truth_level": "conceptual", ... }
```
- `material_source_mode: stock_first` + `story_truth_level: conceptual` → 非 must_include/identity/proof 的段
  自動 route 成 `source:stock` 並用 `material_fit.search_query`(英文)抓 Pexels(見 `stock_first.py`)。
- **必放/identity/proof 段不受此影響**(仍走補拍/複核,不靜默 stock)。
- ⚠️ 三個 load-bearing key(`material_source_mode` / `story_truth_level` / `search_query`)缺了,contract 仍
  validate 過、但**不會真的 Pexels-sourced** → stock-first 專案務必補齊。

## 格式決策(見 ADR 2026-06-04)
- **canonical / tool-facing = normalized JSON**(例 `segment_contract.json`)。BUILD/VERIFY/
  dashboard/state 只讀它,**只消費、不重解釋意圖**。
- SPEC 來源可為 agent / dashboard / YAML / JSON,但都收斂到 normalized JSON。
- **dashboard 是未來人類複核/編輯的首選介面**;YAML 只是選配 bootstrap,非必要人類 UX。
- Node 1-8 的輸出組成 **contract bundle**,由 Node 9(assembly)消費。

## core + facets 模型

```yaml
segment:
  core:
    section_role:        # opening / montage / hold / closing / title …
    story_purpose:       # 這段為什麼存在(故事功能)
    timeline_source:     # beat / tts / fixed
    review_required:     # 開場/收尾/必放/identity/generated/原音段 → true

  material_fit:          # curator 消費(= 地圖規範:導演定類別,小編照此找/歸類/評分)
    category:            # ← 引用 examples/material_categories.json 的 id(地圖規範核心)
    visual_desc:         # 中文畫面描述(VLM 對題用)
    search_query:        # ★stock/Pexels 的英文查詢字(stock_first 必填,否則會 fallback 用中文 visual_desc 命中差)
    material_hint:       # 本地素材夾/路徑提示
    required_traits:
    reject_traits:
    must_include:
    collection_instructions:  # 找/補拍素材的說明(給學員聚焦 + 給小編對題);缺料時=拍攝指引
    source_link:         # 選配:已知現有素材的連結/路徑(直接給小編用)
    fallback_policy:
    reason:

  audio:                 # audio-director 消費
    role:                # music / duck / diegetic
    music_intent:
    original_audio_policy:
    voiceover_policy:
    reason:

  text_layer:            # writer 寫字 / effects 渲染。無字幕→明確 text_layer: none
    label:
    narrative:
    subtitle:
    name_super:
    reason:

  visual_style:          # effects-director 消費
    layout:
    pace:
    transition:
    color_grade:
    effects:
    reason:

  editing_grammar:       # director/editor 消費(Node 7 時間感合約)
    role:                # hero / proof / support / bridge / mood / filler
    priority:            # high / medium / low
    pacing:              # slow / medium / fast / variable
    beat_alignment:      # none / music / speech / action / emotion / chronology / thematic
    min_duration_sec:
    max_duration_sec:
    hold_required:       # {required, reason}
    breathing_room:      # {required, before_sec, after_sec, reason}
    compressibility:     # locked / flexible / expendable
    must_not_cut:
    review_required:
    reason:
```

`editing_grammar` 列舉值:role∈hero/proof/support/bridge/mood/filler;
beat_alignment∈none/music/speech/action/emotion/chronology/thematic;
compressibility∈locked(不可縮/丟/重排,需 review)/flexible(min-max 內可縮)/expendable(先丟)。
**鐵則:timeline agent 可優化 runtime,但不得靜默降級 hero/proof/identity 段或移除 breathing room → 要 route 到 review。**

## 第一階段最小必填(其餘可為 null,但要「明確 none」)
- `core.story_purpose`、`core.timeline_source`
- `material_fit.visual_desc`(素材撐的視覺段)、`material_fit.reason`
- `audio.role`、`audio.reason`
- `visual_style.layout`、`visual_style.pace`、`visual_style.reason`
- 有文字時 `text_layer.reason`;否則明確 `text_layer: none`
- `core.review_required=true` 給:opening / closing / must_include / identity-sensitive /
  generated / original-audio-critical 段

## 設計鐵則
- 故事功能 > 好看畫面。
- must-include 凌駕分數。
- 開場/收尾 > 中段 montage 打磨。
- 原音高潮(隊呼/掌聲/演講)凌駕背景音樂。
- 文字只在幫助理解時出現;**留白也是顯式設計**,要寫明 `text_layer: none`。
- 特效/轉場服務段落功能,非裝飾。
- 缺素材依政策路由 reshoot/generated/review;**不靜默用泛用 stock 填 identity 缺口**。

## 🔴 踩過的坑(BUILD 前由 spec_review gate 機器強制,blocking 會擋 run)

合約寫完後 `contract-run`/`contract-dry-build` 會先跑 **spec-review**
(`video_tools.py spec-review <contract> --brief brief.json` 可單獨驗),
`ready_for_build=false` 就停在 SPEC、route `revise:director`,不浪費 render。
規則全是真實事故,不是理論:

| 規則 | 事故 | 怎麼避 |
|---|---|---|
| **B2** `must_include` × stock 段 | stock_first 拒收 must_include → 該段拿不到素材被**靜默丟掉** → script_coverage fail | 概念段不要寫 must_include;真必放 → `source: local/generated` 附素材 |
| **B3** `subtitle:"auto"` 配無人聲段 | ASR 跑該段「原始音訊」;靜音 stock 沒人聲 → subtitle_accuracy 0 | 只在 `audio.role: duck/diegetic`(真人聲)段用 auto;其餘給明文或 none |
| **B1** content_pattern 與 pacing 矛盾 | develop 段填 `establishing` → single_hold 一鏡到底,撞 `preferred_shot_sec=[4,8]` | 多鏡段用 process/enumeration/action/bridge(見 director.md 詞彙陷阱) |
| **W2** brief 缺 `target_length` | 音樂長度變成總長(122.9s 音樂把 45s 片撐成 123s) | brief 必填 target_length |
| **W3** `video_type: mv` + 紀錄片節奏 | 被推成 rhythmic_mv(max_hold 6s),hold 全掛 | brief 顯式宣告 `mode`(如 warm_documentary) |
| **B4/W5-W8 敷衍偵測** | soul-v3/v5 是複製貼上合約:5 段 pacing 全同、desc/query 重複、reason 填 "r" —— facet gate 只數欄位存在,照樣全過 | 每段**差異化**:pacing 依 section_role(開收尾 hold 長、中段快)、visual_desc/search_query 段段具體、reason 寫真實設計依據。單一訊號 warn;**≥3 訊號共現直接 blocking(perfunctory_spec)**——模板填充過不了 gate |

## 口白片(narrative style)的合約寫法(2026-06-11,city-lite 實測)

- 頂層 `"style": "narrative"` → runtime 走 narrative 鏈(contract_to_narrative_script adapter)。
- **口白意圖放 `narration` facet**:`"narration": {"text": "口白文字", "mode": "voiceover"}`。
  `audio.role` 仍然只能是 music/duck/diegetic——口白段填 `music`(BGM 墊底,
  voiceover 由 narrative 鏈 TTS+混音自己處理)。填 `voiceover` 會被驗證擋下。
- 全 stock 素材記得頂層 `"material_source_mode": "stock_first"`,否則 Node 2 停下要本地素材。
- BGM:頂層 `"bgm": "<絕對路徑>"`(narrative 分支不吃 --music 參數,靠這個欄位映射)。
- 字幕 `text_layer.subtitle: "auto"` 在口白段合法(口白就是真人聲來源,B3 不擋)。

## Interactive Design Rules(SPEC 是互動步驟,非一次性填表)
先定全局方向,再只對「高風險段」深問;低風險 montage 用文件預設。

**全局問題(先問):**
```text
1. 整片情緒弧是什麼?
2. 開場要做什麼:正式鋪陳 / 熱血 hook / 紀實脈絡 / 最強畫面先上?
3. 收尾要做什麼:大合照 / 祝福 / 隊呼 / 學長致詞 / 成果總結 / 安靜情緒收?
4. 哪些段必須保留原音?
5. 哪些段觀眾需要文字才看得懂?
```
**高風險段問題:**
```text
1. 這段為什麼存在於故事裡?
2. 該呈現什麼確切視覺證據?
3. 即使視覺相似,什麼東西不能拿來替代它?
4. 原音在情緒/資訊上重不重要?
5. 觀眾需要 label / subtitle / narrative card / name_super 嗎?
6. dashboard 是否該要求這段人工複核?
```
**預設規則:** 不對每段問每題。只對 opening/closing/must_include/identity-sensitive/
generated/原音關鍵/弱覆蓋段深問;低風險 montage 用記錄在案的預設。

## Contract bundle 與欄位→執行對映
- **facet 擁有權**:`director`=core(section role/story purpose/弧/優先/複核);`writer`=text_layer;
  `audio-director`=audio;`effects-director`=visual_style;`curator`=material_fit;
  `gap-analyzer`/`route`=material_fit.fallback_policy 的執行路由(見 Node 8)。
- **每個重要欄位都應對映到**:BUILD 輸出 / validation / 或 review gate(否則該欄位是死的)。
- 工具面 validator:`spec_contract.validate_segment_contract()`(只檢查必填、不發明改意圖的預設)。

## 與其他 skill 的邊界
- `director.md` = 創作/故事權威 + 段落意圖;**不重抄整份 schema**,cross-ref 本檔。
- 各 facet skill 擁有自己那欄的「怎麼填、為什麼」。
- BUILD(editor/mv_cut)與 VERIFY 讀 normalized JSON,不改 SPEC 意圖。
## Material supply before script

Before finalizing segment duration, generate per-asset material maps and a
`supply_review.json`. The supply review is authoritative for
`max_honest_duration_sec`: each video contributes at most two useful windows,
each photo at most one, and zero-score or missing material contributes nothing.
`spec_review` rule B6 (`script_overreach`) is tier-1 blocking whenever promised
segment duration exceeds that evidenced maximum. Shorten/merge, await material,
or request a reshoot instead of padding the edit.

## Scene retrieval and visual novelty

When material maps exist, matched editing must select ranked scenes rather than
opening files in path order. Rank using caption relevance, sequence function,
and pace/motion evidence; an optional model ranker may reorder evidenced scenes
but must not admit zero-evidence scenes. Use `audio.role=source_speech` for
sound bites that must preserve mapped speech. Delivery requires a passing
`new_visual_information_audit.json`; changing Ken Burns treatment does not make
the same photo new visual information.

## Meaningful edit points and jump-cuts

Render planning must consume material-map evidence instead of choosing arbitrary
fixed windows. For `keep_audio` or `audio.role=source_speech`, preserve complete
intersecting speech runs; later motion snapping must not move those boundaries.
For non-speech clips, edit-point evidence is ordered scene boundary before
motion peak.

Segments with `editing_grammar.beat_alignment=action` should use mapped
rise/peak/settle phases, cutting in at rise and out after settle. Scenes reviewed
as `bridge` are whole-scene bridge material and must not be selected as primary
action phases or cut through arbitrarily.

Jump-cut is conditional on actual mapped silence, not target duration. Produce a
reviewable `jumpcut_plan.json`; apply only after an `accept` verdict, and record
source, kept ranges, operation, and review lineage. When no qualifying silence
exists, report jump-cut as not applicable and leave the source intact.

## Dense VERIFY evidence and replay acceptance

VERIFY review must not rely on one low-density contact sheet. Produce four
evidence layers: a 36-48 frame full-film overview, 12-16 frame chapter grids,
24-40 frame critical-segment grids, and a proportional rhythm strip. Critical
segments include speech-safe, review-required, and edit-point-adjusted clips.

Replay acceptance must aggregate existing timeline, supply, audit, and judge
artifacts without inventing an aesthetic verdict. Missing duration-shortening
or chapter-reduction evidence is `unproven`, not pass. Jump-cut may be
`not_applicable` when mapped speech contains no qualifying silence.

Formal `contract-run` must write `material_coverage_map.json` and
`supply_review.json`, then pass supply evidence into the tier-1 B6 spec gate
before `mv_chain`. A script that exceeds evidenced material supply must route to
shorten/merge, await material, or reshoot before rendering.
## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "spec-contract",
  "stage_owner": "spec_build_contract_boundary",
  "triggers": [
    "需要驗證 segment contract、build profile、boundary fixture 或 no-render build smoke",
    "SPEC 到 BUILD 的契約邊界需要小步測試"
  ],
  "canonical_tools": [
    {
      "tool": "tools/boundary_smoke.py",
      "when": "用既有 verify_fn/lifecycle source of truth 跑單一邊界 smoke",
      "inputs": [
        "boundary fixture directory"
      ],
      "outputs": [
        "boundary_report.json"
      ],
      "stop_if": [
        "gate_status is fail or expected artifact is missing"
      ],
      "capability_id": "cap.spec-contract.boundary-smoke.v1",
      "loops": [
        "L0"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/stage4_build_smoke.py",
      "when": "驗證 BUILD stage no-render handoff、timeline/build invariants",
      "inputs": [
        "build-ready fixture or run folder"
      ],
      "outputs": [
        "stage4_build_smoke_report.json"
      ],
      "stop_if": [
        "timeline/build invariant fails"
      ],
      "capability_id": "cap.spec-contract.stage4-build-smoke.v1",
      "loops": [
        "L0"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/boundary_fixture_hub.py",
      "when": "管理或產生 boundary fixture hub index",
      "inputs": [
        "fixture root"
      ],
      "outputs": [
        "fixture hub report/index"
      ],
      "stop_if": [
        "fixture schema invalid"
      ]
    },
    {
      "tool": "tools/m6e_acceptance.py",
      "when": "驗證 M6e contract/build acceptance path",
      "inputs": [
        "M6e fixture"
      ],
      "outputs": [
        "M6e acceptance report"
      ],
      "stop_if": [
        "contract/build gate diverges"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not run final render from a boundary smoke",
    "Do not treat dry-build success as visual delivery success",
    "Do not bypass spec-review or supply-review findings"
  ],
  "capability_namespace": "cap.spec-contract.*",
  "capability_lookup_owner": "spec-contract"
}
<!-- TOOL_CONTRACT_END -->
