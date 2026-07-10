---
name: editing-loop-director
description: Use when an approved Hermes intent or script, material evidence, and an existing or new candidate run are ready for 剪片迴圈、LOOP、開場切片、素材圈選、picture lock、初剪、成片審查，或既有候選片修訂。Do not use for fuzzy requests before Stage 0 approval.
---

# Editing Loop Director — 剪輯迴圈導演

## Entry boundary 與適用範圍

先讀 `skills/pipeline-boundary.md`。**Stage 0 entry lock 適用；Do not
direct-cut from a fuzzy request。**只有在 approved intent／script、素材證據
與 candidate run context 可解析時進入 LOOP；缺任一項時，回到
`video-pipeline-route` 補 Stage 0，不得以本 skill 猜測源頭精神。

以下正文是通用 doctrine；標成 **Canon 67 profile** 的路徑、門檻與數字
只是 2026-07-10 首航（0:00–0:44、172 鏡頭素材池）的 worked example，
不得自動套用到訪談片、產品片或其他模板家族。

本 skill 固化已觀察到的流程。**事實來源**：
`docs/pilots/pilot-driver-v1-usage-log.py`
（driver 全程手稿）、`docs/pilots/2026-07-10-loop-pilot-evidence-for-sol.md`
（證據包）、`docs/decisions/2026-07-10-evidence-carrying-editing-loop-fable-reply.md`
（邊界裁決）。凡本文與實跑紀錄矛盾，以實跑紀錄為準並回報修正本文。

成熟度申報（fail-closed）：**L0 已實戰試航；L1 的有界單一 picture
修訂已通過 fresh-agent reproducibility；L5 已認證，但僅限 Canon 67
`candidate_v2`／44 秒／review-only；L2–L4 為 doctrine 級**（沿用
`docs/construction-guides/2026-07-10-editing-loop-product-spec.md`）。未認證
模式首次執行時視同 first-of-kind 試航，須加倍申報偏差；L1 或 L5 的 PASS
都不得外推為完整影片或其他 layer 的 creative approval。

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

鐵律：**每輪必有人裁決才能前進**。agent 不得自主連跑多輪。

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

1. **approved intent／story spine**：解析既有 `video_intent`、canon／
   blueprint 或 approved script；至少一份須能固定源頭精神與文本真相。
   **Canon 67 profile** 使用 `docs/pilots/*-script-*.md`，檔頭標
   `APPROVED`＋owner 裁決紀錄。
2. **selects manifest**：候選代號→素材相對路徑（JSON）。
3. **run provenance**：`selection_mode`、`script_source`、逐張
   `orientation_corrected`、reference-film 排除聲明，以及 §0 六欄最小紀錄。
4. **candidate run dir**：解析目前 run 內的 plan/timeline/handoff/QA；
   **Canon 67 profile** 路徑為 `.tmp/loop_pilot_*/candidate_vN/`。

歷史＝run dir 版本命名（v1/v2…）＋session log＋git。
新契約（hash 綁定、journal 引擎、loop_context envelope、dirty 矩陣）
**一律先查觸發清單**（fable-reply §觸發式硬化清單），無觸發不建。

## 3. L0 素材沉浸【已實戰】

1. 影片素材：`video_tools.py perception-field-check <video> --out DIR`
   → 分頁牆＋coverage＋聲軌 probe。
2. 照片池：出**帶索引代號的候選表**（每格燒代號，附 manifest）。
   作法見 usage-log 的 build_select_sheets 段。**必須套 EXIF 轉正**
   （finding f4：未轉正曾致編號錯位＋渲染側倒）。
3. 池子按資料夾/語意分組（如 AER 空拍、TWR 塔、ACT 作業…）。
4. Owner 圈 selects 或整批委任；結果記入 manifest。
5. 影片/照片混池注意：縮圖看不出動靜，record 建立時以副檔名分流
   （影片須 probe `media_duration_sec`）。

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
4. `write_product_artifacts(run)` 編譯 → `render_edit_decision(...)`
   渲染（repo-owned code，禁止 run-local renderer）。
5. 驗證：`write_beat_cut_alignment_report`（within-1-frame 依劇本門檻）、
   lifecycle evidence（親眼讀 contact sheet 驗**字正確**，QA 只驗
   「有字」不驗「字對」——finding 教訓）、`write_rendered_product_qa`、
   `perception-field-check` 對 final.mp4 做取樣覆蓋與座標複驗；它**不判斷
   視覺家族數或畫面好壞**。
6. 蒙太奇選材驗收：若 `project_material_map.json` 已有可靠標籤，跑
   `python video_tools.py visual-diversity-coverage PROJECT_MAP --out REPORT`
   並引用報告；若無標籤，由 agent 讀牆做語意判讀，附 cell／秒座標與
   盲區，明文標為 agent judgment，禁止稱為 machine PASS。
   **Canon 67 profile** 劇本門檻為 ≥12/15，且場地×景別×隊形至少一軸變化。
出口：owner 下 picture verdict；lock 後才進 L2–L4。

## 5. L2 效【doctrine】

鎖畫面後作用於 timeline 段落。字卡/轉場走 effect factory 既有路徑；
**「廣場邊框論」（finding f5）：字卡系統是靈魂載體，投資模板家族而
非單卡手作**。目前 overlay 僅支援 progressive_typewriter＋hard cut；
已知缺把手：打字節奏 hold（f2）、小字/角落樣式（f3）。

## 6. L3 音【doctrine】

混音層（音量曲線、語音下鋪樂 ducking、SFX）；L1 已先固定該片型的
主導聲音基礎（music、dialogue 或 picture-led）。
能力庫：mix-audio / sfx-mix / audio handoff acceptance / 響度 gate。

## 7. L4 字【doctrine】

文本 fail-closed：**唯一來源＝owner 批准的劇本檔**；感知轉錄、OCR、
生成文本一律禁止直接進渲染（對照組錯字敗因）。ASR 產出僅作草稿，
人校後併入劇本檔才生效。

## 8. L5 審【CERTIFIED：Canon 67／44s／review-only】

L5 是 V Pipeline 既有 review／verify capabilities 的組合，不是新的
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

三個 findings 均保持 open：`l5_f01` 為 title lifecycle 的 objective
approved-script mismatch；`l5_f02` 為 0.18–0.19 秒完整詩行 dwell 的 open
taste finding（非客觀不可讀或必修）；`l5_f03` 為 final landing form/hold 的
objective approved-script mismatch。`h01`、`h02` 是被接受的 hardening
observations，不是影片 finding；兩者都需要新的 separate TDD plan，且不
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
