---
name: editing-loop-director
description: Use when an approved Hermes intent or script, material evidence, and an existing or new candidate run are ready for 剪片迴圈、LOOP、開場切片、素材圈選、picture lock、初剪、成片審查，或既有候選片修訂。Do not use for fuzzy requests before Stage 0 approval.
---

# Editing Loop Director — 剪輯迴圈導演

## Entry boundary 與適用範圍

先讀 `skills/pipeline-boundary.md`。**Stage 0 entry lock 適用；Do not
direct-cut from a fuzzy request。Stage owns lifecycle; Loop owns editing method。**
本 skill 不選 Stage、不推進 `next_action`，只在 Orchestrator 已
確認 Stage 與本輪授權後，提供 L0–L5 的剪輯方法。

依 entry shape 套用不同門檻：

- **greenfield whole-video or long-form**：進 L1 前必須同時解析並核准
  `video_intent.json`、`story_soul_blueprint.json`、
  `director_shot_plan.json` 與 `segment_contract.json`。Intent 不能代替故事，
  素材分類不能代替導演劇本。
- **material-first L0 exception**：Stage 0 已固定素材範圍時，可先用 L0
  建立素材真相；如果目標是全片或長片，must return to S1 / S2 before L1，
  不得從 inventory／selects 直接跳進畫面組裝。
- **brownfield entry**：只有既有 candidate、可追溯上游契約與 review
  context 齊全時，才從 S8 / L5 找 finding，再由 S9 回派目標 L0–L4。

## Stage 0–10 整合對照

**Stage 6 is the only canonical render owner；L1 does not own canonical render。**
固定映射如下：

| Pipeline hook | Editing Loop responsibility |
|---|---|
| S0–S2 | Intent、story spine、director/segment contract；不進 picture compose |
| S3 → L0 | 素材沉浸、感知證據、selects |
| S4 → L0 | coverage gap 與 build/revise/drop/waive 提案 |
| S5 → L1 / L2 / L3 / L4 | 編譯 picture/effects/audio/text decisions；出口為 `COMPILED / NOT_RENDERED` |
| S6 | 工廠依已接受 handoff 執行 canonical render；不屬於 LOOP 自主權限 |
| S7 / S8 → L5 | fresh render 的 objective Verify、agent review、owner verdict |
| S9 → finding-targeted L0–L4 | 只修 finding 指向的層與 stable scope，再回 S5–S7 |
| S10 | owner＋delivery gate；Skill 不得批准交付 |

以下正文是通用 doctrine；標成 **Canon 67 profile** 的路徑、門檻與數字
只是 2026-07-10 首航（0:00–0:44、172 鏡頭素材池）的 worked example，
不得自動套用到訪談片、產品片或其他模板家族。

本 skill 固化已觀察到的流程。**事實來源**：
`docs/pilots/pilot-driver-v1-usage-log.py`
（driver 全程手稿）、`docs/pilots/2026-07-10-loop-pilot-evidence-for-sol.md`
（證據包）、`docs/decisions/2026-07-10-evidence-carrying-editing-loop-fable-reply.md`
（邊界裁決）。凡本文與實跑紀錄矛盾，以實跑紀錄為準並回報修正本文。

成熟度申報（fail-closed）：**L0 已認證，但僅限 Canon 67 訪談素材的
clean-blind 沉浸與 selects 提案；L1 的有界單一 picture 修訂已通過
fresh-agent reproducibility；L2 已認證，但僅限 Canon 67
`candidate_l2`／44 秒／`opening_title_text` lifecycle first-of-kind；L5 已
認證，但僅限 Canon 67 `candidate_v2`／44 秒／review-only；L3–L4 為 doctrine
級**（沿用
`docs/construction-guides/2026-07-10-editing-loop-product-spec.md`）。未認證
模式首次執行時視同 first-of-kind 試航，須加倍申報偏差；L0、L1、L2 或 L5
的 PASS 都不得外推為完整影片或其他 layer 的 creative approval。

## 0. 迴圈形狀（六層通用，每輪必走）

```
carried context（見 §2 四檔）
  → agent 提案（附感知證據＋理由＋自申盲區）
  → owner 裁決（accept / revise / delegate）
  → 套用（只動本層、只動目標段落）
  → 機器驗證（本層儀器，見各節）
  → 預覽交 owner → 下一輪或 loop-exit
每輪記遙測三數字：裁決輪數、每輪分鐘、想調而無把手清單（f 編號入帳）
```

鐵律：**每輪必有人裁決才能前進**。Owner 可在工單中預先委任同一 LOOP
內的可逆、客觀步驟，但 agent 不得以該委任自行越過 story、picture lock、
文本真相、品味或 final delivery gate，也不得自主切換到下一 LOOP。

每輪在既有 provenance 或 evidence 文件追加以下最小決策紀錄；這是記錄
欄位，不是新 envelope 或 journal 引擎：

```jsonc
{
  "proposal_by": "agent",
  "verdict_by": "owner",
  "delegation_scope": "本輪 owner 明文授權範圍",
  "evidence_refs": ["path#time_range|cell_id|check_id"],
  "applied_diff": "實際改動的 stable segment/clip/layer ID",
  "carry_forward": ["下一輪必須保留的決策、證據、finding"]
}
```

## 1. 授權映射（ASK / SHOW / DECIDE）

| 決策 | 門 | 說明 |
|---|---|---|
| 劇本文字（詩卡/標題/字幕的每一個字） | ASK | owner 批准的劇本檔是唯一文本源 |
| 成片品味 verdict、picture lock、交付 | ASK | 永遠是 owner 的 |
| 素材提名與排列 | SHOW→可 DECIDE | 先出帶索引候選表給 owner 圈；owner 可整批委任（首航先例），委任後 agent 定案並在 provenance 記 `selection_mode` |
| 資料準備（records、EXIF 轉正、排程、呼叫序） | DECIDE | agent 全權，事後可稽核 |
| 客觀儀器門檻（卡點、QA；有標籤時才含 diversity coverage） | 不可協商 | 任何人不得為過關而放寬；無標籤的語意判讀不得冒充儀器 PASS |

## 2. Context 契約（四檔，跨輪攜帶，不新建 envelope）

1. **approved intent／story spine**：依 entry shape 套用本 skill 入口門檻。
   greenfield whole-video／long-form 必須同時攜帶 Stage 0 intent、Stage 1
   story blueprint、Stage 2 director shot plan／segment contract；material-first
   L0 可先帶 intent＋素材範圍，但進 L1 前必須補齊 S1/S2；brownfield 必須
   帶既有 candidate 與其 canonical upstream context。**Canon 67 profile**
   使用 `docs/pilots/*-script-*.md`，檔頭標 `APPROVED`＋owner 裁決紀錄。
2. **selects manifest**：候選代號→素材相對路徑（JSON）。
3. **run provenance**：`selection_mode`、`script_source`、逐張
   `orientation_corrected`、reference-film 排除聲明，以及 §0 六欄最小紀錄。
4. **candidate run dir**：解析目前 run 內的 plan/timeline/handoff/QA；
   **Canon 67 profile** 路徑為 `.tmp/loop_pilot_*/candidate_vN/`。

歷史＝run dir 版本命名（v1/v2…）＋session log＋git。
新契約（hash 綁定、journal 引擎、loop_context envelope、dirty 矩陣）
**一律先查觸發清單**（fable-reply §觸發式硬化清單），無觸發不建。

## 3. L0 素材沉浸【CERTIFIED：Canon 67／訪談 selects／clean-blind first-of-kind】

1. 影片素材：`video_tools.py perception-field-check <video> --out DIR`
   → 分頁牆＋coverage＋聲軌 probe。
2. 照片池：出**帶索引代號的候選表**（每格燒代號，附 manifest）。
   作法見 usage-log 的 build_select_sheets 段。**必須套 EXIF 轉正**
   （finding f4：未轉正曾致編號錯位＋渲染側倒）。
3. 池子按資料夾/語意分組（如 AER 空拍、TWR 塔、ACT 作業…）。
4. Owner 圈 selects 或整批委任；結果記入 manifest。
5. 影片/照片混池注意：縮圖看不出動靜，record 建立時以副檔名分流
   （影片須 probe `media_duration_sec`）。
6. 在既有 selects proposal／provenance 的每個候選列分開記：
   - `observed_content`：證據直接支持的場景、人物關係與動作；
   - `assigned_story_function`：剪輯上希望它承擔的故事用途；
   - `direct_story_evidence`：是否直接證明該必要故事節點。
   禁止因某個故事槽仍空著，就把畫面重新命名成那個故事。每個 approved
   story beat 至少要有一顆 `direct_story_evidence=true`；否則明列 coverage
   gap，回到 ASK／SHOW，不得以隱喻覆蓋冒充完成。
7. 遇到 support／gratitude 類節點時，在同一列補 `support_subtype`：
   `mentorship`、`operational_teamwork`、`backstage_care` 或 `other`，並明列
   brief 要求而本輪未覆蓋的 subtype。作業協作不得自動等同幕後照顧。
   以上只是既有提案列的語意欄位，不建立新 envelope、registry 或 validator。

**2026-07-11 clean-blind first-of-kind：`L0_CLEAN_BLIND_CERTIFIED`。**Fresh
agent 在封印前只讀允許的 doctrine、完整 inventory、原始素材與新生成感知證據，
獨立提出一段訪談與五顆 cutaway；封印後才讀舊 manifest。新舊答案功能相近、
訪談來源不同，六個 selected raw hashes 與封印鏈均由 integrator 複驗通過。
此認證只證明有界 L0 程序可重現，不是 picture lock、語音真實性、素材授權、
creative approval 或 delivery。Durable evidence:
`docs/pilots/2026-07-11-editing-loop-l0-clean-blind-first-of-kind-evidence.md`。

## 4. L1 剪【已實戰】——投資重心，全片品質七成

前置：先判定控制 picture 節奏的聲音基礎。beat-driven montage 先鎖定
音樂／beat；訪談片先鎖定 approved dialogue／ASR 時間軸；無主導聲軌的
片型才由 picture rhythm 起剪。**Canon 67 profile** 是 beat-driven，beat
錨來自 soundtrack probe（`sampling_anchors.beat_times`），對照實驗沿用
同一音軌。

組裝序（usage-log 為準）：
1. selects → 帶 lineage 的 asset records（photo/video 分流、EXIF
   轉正拷貝、`_asset_id` 沿用 sha1 慣例）。
2. `compose_beat_cut_montage(records, beats, window, fps, min_distinct)`
   ——選擇權在呼叫端；**嚴禁 catalog 順序取前 N**（對照組敗因）。
3. **Canon 67 pilot-only** 曾手排 `opening_sequence.json`（clips＋overlays＋
   hard-cut 表）；不得把手排 JSON 當通用 doctrine。helper 開單前先稽核
   `opening_sequence.compile_opening_sequence`、`timeline_patch.apply_patch`、
   asset store 與 beat-cut composer，優先 adapter／既有 public API，只有
   確認缺口後才收編新 helper。完成後由 public helper 產生序列。
   **overlay 鐵律：文字卡窗口必須首尾相接、不得重疊。**
4. 在 S5 只呼叫 public compiler（例如 `write_product_artifacts(run)`／
   `compile-edit-decision-plan`）產生帶 stable IDs 與 lineage 的 picture
   decision；出口寫 `COMPILED / NOT_RENDERED`。禁止以 L1 名義直接建立
   canonical `final.mp4`。
5. L1 preflight 只驗 plan semantics、時長、source bounds、重複／疲勞風險、
   beat/dialogue anchors 與 handoff 完整性。S6 明確獲准後才由 repo-owned
   renderer 執行；若 S8/S9 明文要求 draft proxy，只能走註冊的 preview
   capability，並標示 non-canonical。rendered QA、contact sheet、
   `perception-field-check` 與 lifecycle evidence 屬 S7/L5；其中 QA 只驗
   「有字」不保證「字對」，且 perception coverage 不判斷畫面好壞。
6. 蒙太奇選材驗收：若 `project_material_map.json` 已有可靠標籤，跑
   `python video_tools.py visual-diversity-coverage PROJECT_MAP --out REPORT`
   並引用報告；若無標籤，由 agent 讀牆做語意判讀，附 cell／秒座標與
   盲區，明文標為 agent judgment，禁止稱為 machine PASS。
   **Canon 67 profile** 劇本門檻為 ≥12/15，且場地×景別×隊形至少一軸變化。
7. picture plan 在進入 S5 handoff 前，必須附
   `retrieval_evidence.project_material_map_ref`、其 hash，以及
   `retrieval_evidence.ranking_report_ref`；由
   `tools/picture_plan_retrieval_report.py` 重播既有 ranker，逐 clip 寫入
   candidate、rank position、scene ID 與 source-hash 結果。未帶 report 的手排
   plan 直接 fail-closed；超出 top-K 只能用 `agent_override`／
   `owner_directed_override`，並附 reason＋evidence。檔名／資料夾只作 prior，
   不得單獨充當畫面真相。
出口：owner 下 picture verdict；lock 後才進 L2–L4。

## 5. L2 效【CERTIFIED：Canon 67／44s／opening_title_text lifecycle／first-of-kind】

鎖畫面後作用於 timeline 段落。字卡/轉場走 effect factory 既有路徑；
**「廣場邊框論」（finding f5）：字卡系統是靈魂載體，投資模板家族而
非單卡手作**。目前 overlay 僅支援 progressive_typewriter＋hard cut；
已知缺把手：打字節奏 hold（f2）、小字/角落樣式（f3）。

**2026-07-11 first-of-kind 結果：PASS（scope 僅限 Canon 67
`candidate_l2`／44 秒／stable overlay `opening_title_text`）。**Owner 已查看
左舊右新的 dynamic，通過 `3.5s` 開始、`9.0s` 完整、`11.0s` 結束的 lifecycle。
新 render 的 semantic diff、lifecycle QA、rendered QA 與 final verify 均通過。
此結果只解決 `l5_f01`；它不認證其他 effect、picture lock、audio/text、
candidate creative quality、creative approval 或 delivery。Durable evidence:
`docs/pilots/2026-07-11-editing-loop-l2-first-of-kind-evidence.md`。

## 6. L3 音【doctrine】

混音層（音量曲線、語音下鋪樂 ducking、SFX）；L1 已先固定該片型的
主導聲音基礎（music、dialogue 或 picture-led）。
能力庫：mix-audio / sfx-mix / audio handoff acceptance / 響度 gate。

## 7. L4 字【doctrine】

文本 fail-closed：**唯一來源＝owner 批准的劇本檔**；感知轉錄、OCR、
生成文本一律禁止直接進渲染（對照組錯字敗因）。ASR 產出僅作草稿，
人校後併入劇本檔才生效。

## 8. L5 審【CERTIFIED：Canon 67／44s／review-only】

L5 只在 fresh rendered candidate 存在後成立；no-render plan preflight
不能宣稱 L5 PASS。L5 是 V Pipeline 既有 review／verify capabilities 的組合，不是新的
reviewer engine：客觀儀器（rendered QA/final verify/卡點/黑幀/響度/
caption/lifecycle/fatigue）→ 全片低密度牆 → 可疑窗 `segment_strip`
密集條 → 對 blueprint rubric 逐題作答（每題附 stable ID/秒座標）→
owner 品味 gate。

首次試航的 findings packet 只能寫在 `.tmp` Owner Zone；在一次實跑證明
格式摩擦前，不新增正式 artifact、normalizer、registry 或自動回派工具。
Findings 最少記：`f<N>`、scope（stable IDs/time range）、class
（objective|taste）、statement、evidence refs、owner_capability、
proposed next LOOP、owner-verdict-required 與 status。L5 只提 finding，
不得偷偷改 timeline；回派＝下一輪讀取該 finding，不是狀態機。

**2026-07-11 first-of-kind 結果：PASS（scope 僅限 Canon 67
`candidate_v2`／44 秒／review-only）。**Fresh worker 以四類 carried context
和既有 review/verify capabilities 產生 evidence-backed packet；owner/integrator
接受 v2。這只認證 L5 Skill reproducibility，不認證 candidate creative
quality（仍為 UNKNOWN）、整片品味、creative approval 或 delivery；
`human_creative_approval=false`、`final_delivery_claimed=false`。

`l5_f01` 已由上述 bounded L2 lifecycle repair 標記 RESOLVED。`l5_f02` 為
0.18–0.19 秒完整詩行 dwell 的 open taste finding（非客觀不可讀或必修）；
`l5_f03` 為 final landing form/hold 的 open objective approved-script mismatch。
`h01`、`h02` 是被接受的 hardening observations，不是影片 finding；兩者都需要新的 separate TDD plan，且不
授權 helper、normalizer、timeline v2、dirty matrix、curator route 或任何
自動回派。Durable evidence:
`docs/pilots/2026-07-10-editing-loop-l5-first-of-kind-evidence.md`。

## 9. 首次 forward-test：f1 reproducibility

讓另一個 agent 只讀本 skill、四項 context 與原始 finding 執行修訂；
不得提供 Fable 對話、預期 stable ID、替換答案或本次 review 結論。
Agent 必須自行：

1. 以證據定位重複感來源，提案替換並使用 stable clip/segment ID，禁止用
   易因插入而漂移的「第 N 顆」作唯一識別。
2. 等 owner approve／revise，再套用唯一 picture diff；維持原 duration
   與 cut boundary，除非 owner 核准改節奏。
3. 依時間窗與內容相依性判斷 audio/text/effects 是 clean、review 或 dirty；
   不得因本輪未修改它們就宣稱它們不存在。
4. 重跑 beat alignment、rendered QA、相關 lifecycle／視覺 review，並寫入
   §0 六欄最小紀錄。

只有當新 agent 不依賴洩漏答案仍能完成上述閉環，才把本 skill 的
reproducibility 從 UNKNOWN 升為 PASS。

**2026-07-10 實跑結果：PASS（scope 僅限 f1 與有界 L1 picture
replacement）。**TERRA 自行定位 `montage_014`，提議 `SPT10 → GA37`，
在兩次 owner gate 後只套用一個 picture diff；fresh beat/rendered QA/
perception 與 candidate-v1 hash preservation 均通過。Owner 判定 f1
RESOLVED，但 `human_creative_approval=false`、
`final_delivery_claimed=false`。Durable 摘要見
`docs/pilots/2026-07-10-editing-loop-f1-forward-test-evidence.md`。

## 10. 邊界（不得越過）

- 不新建 route runner / next_action 詞彙 / 註冊表；route 系統凍結。
- 不動 `delivery_gate`、reviewer_registry 語意。
- `human_creative_approval` / `final_delivery_claimed` 只有 owner 能翻。
- Downloads 素材唯讀；禁用參考成片作素材。
- 儀器綠≠好看：技術門檻全過仍必須過 owner 品味 gate（對照組教訓：
  卡點 1.0 的片可以爛得很整齊）。

<!-- CAPABILITY_CONSUMER_START -->
{
  "consumer": "editing-loop-director",
  "active_capability_ids": [
    "cap.audio-director.audio-mix-plan-execute.v1",
    "cap.brownfield-edit.workbench-handoff.v1",
    "cap.capcut-assisted-finishing.draft.v1",
    "cap.generated-material-producer.generated-material-flow-acceptance.v1",
    "cap.material-map.material-rough-cut.v1",
    "cap.soundtrack-arranger.soundtrack-arranger.v1",
    "cap.subtitle-director.subtitle-voiceover-handoff-accept.v1",
    "cap.video-effect-factory.effect-capability-review.v1",
    "cap.verify.final-product-verify.v1"
  ],
  "active_namespaces": [
    "cap.audio-director.*",
    "cap.brownfield-edit.*",
    "cap.capcut-assisted-finishing.*",
    "cap.generated-material-producer.*",
    "cap.material-map.*",
    "cap.soundtrack-arranger.*",
    "cap.subtitle-director.*",
    "cap.video-effect-factory.*",
    "cap.verify.*"
  ],
  "selection_rule": "Resolve active capability IDs and namespaces through dispatch-capabilities; do not duplicate tool ownership or create a private catalog.",
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
<!-- CAPABILITY_CONSUMER_END -->
