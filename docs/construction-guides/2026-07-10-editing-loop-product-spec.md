# Hermes 剪片迴圈產品規格（Editing Loop Product Spec）

日期：2026-07-10

狀態：**ACCEPTED — 唯一權威產品規格**

適用範圍：Hermes 的 agent-driven 剪輯前門

前置裁決：既有 route/orchestrator 凍結運作、不拆除、不再擴建為剪輯前門

## 0. 文件權威與證據層級

本文件回答「產品要成為什麼」並作為 Editing Loop 的唯一權威規格。

1. 本文件：目前產品方向、成熟度、建設順序與硬化觸發。
2. `skills/editing-loop-director.md`：agent 實際執行 L0–L5 的操作 doctrine。
3. `docs/decisions/**`：保留方向形成原因、被修正方案與取捨。
4. `docs/pilots/**`：保存實跑結果、限制與可核驗證據。
5. `.tmp/**`：可重建的實驗／render 產物，不是長期真相來源。

若內容衝突，以較新的 owner 裁決與本文件為準；不得另建第二份平行
Product Spec。Skill 若落後，應更新 Skill 的成熟度或操作段落，而不是讓
執行者猜哪份文件有效。

## 1. 產品定位：LOOP 驅動 V Pipeline

Editing Loop 是**導演／控制層**；V Pipeline 是**能力與執行層**。

```text
approved intent / script / canon
            ↓
Editing Loop Director Skill＋當班 agent
  判斷目前問題、提出方案、引用證據、等待 owner gate
            ↓
V Pipeline capability library
  perception / material / compose / render / effects / audio / text / verify
            ↓
candidate＋fresh evidence＋semantic diff
            ↓
owner verdict＋carry-forward → 下一 LOOP 或回到指定 LOOP
```

LOOP 不重做 renderer、ASR、effect factory、soundtrack、subtitle 或 QA；它
只以有證據的順序呼叫現有 public capabilities。八支線及主線繼續提供
能力，但不負責全局創意編排。

### 責任邊界

| 元件 | 擁有 | 不得擁有 |
|---|---|---|
| `editing-loop-director` Skill | 迴圈形狀、品味 doctrine、證據要求、能力呼叫順序、ASK/SHOW/DECIDE | durable state、隱藏寫入、交付批准 |
| 當班 agent | 感知、提案、經授權的創意決策、組裝與證據解讀 | 越過 owner gate、自主連跑多輪 |
| V Pipeline capabilities | 確定性轉換、compose、render、audit、verify | 全局品味、偷偷選 route |
| 薄 helper／adapter | 經實證反覆出現的確定性機械工作 | 流程、品味、新狀態機 |
| Owner | 劇本真相、picture lock、品味 verdict、創意與交付批准 | 例行資料處理 |

## 2. 核心形狀：增量、可攜的局部閉環

每個 LOOP 都是局部閉環，但不是自我封閉的島：

```text
carried context＋relevant evidence
  → agent proposal（理由＋盲區）
  → owner verdict（approve / revise / delegate）
  → apply approved delta（只動本層與目標範圍）
  → focused machine verify
  → preview / rendered evidence
  → confirmed delta＋findings＋carry-forward
```

每輪必須保留六欄最小決策紀錄：

```jsonc
{
  "proposal_by": "agent",
  "verdict_by": "owner",
  "delegation_scope": "本輪明文授權範圍",
  "evidence_refs": ["path#time_range|cell_id|check_id"],
  "applied_diff": "stable segment/clip/layer ID 與實際變更",
  "carry_forward": ["後續不得遺失的決策、限制、finding"]
}
```

同時記錄三項遙測：owner 裁決輪數、每輪耗時、想調但沒有把手的清單。

### 現行 timeline 事實

正式 `edit_decision_plan` 目前是 **v1 flat composition contract**，包含
`cuts`、`overlays`、`audio`、`effects`、`subtitles`、`transitions`；它尚非
分層 segment timeline v2。

因此現階段使用 stable IDs、candidate 版本、semantic diff、provenance 與
六欄紀錄表達增量。不得在文件中把尚未實作的 `layer_state/dirty matrix`
寫成現有能力。只有觸發 §8 的可觀測事件後，才評估 v2／dirty propagation。

## 3. 六個 LOOP 與目前成熟度

成熟度定義：

- **CERTIFIED**：已由新 agent 在不洩漏答案下完成 first-of-kind 閉環。
- **PILOTED**：有真實案例，但尚未完成獨立可重現認證。
- **DOCTRINE**：既有能力可供組合，但該 LOOP 尚未完整實跑。

| LOOP | 責任 | 驅動的既有 V Pipeline 能力 | 成熟度 |
|---|---|---|---|
| L0 素材沉浸 | 感知、標籤、selects、盲區 | perception-field、material wall/map、ASR、visual diversity | PILOTED |
| L1 Picture | 選材、順序、時長、節奏、picture lock | beat-cut composer、opening sequence、edit decision compile/render | **CERTIFIED（f1）** |
| L2 Effects | 標題、章卡、轉場、圖像處理 | effect factory、Remotion worker、motion graphics、lifecycle QA | DOCTRINE |
| L3 Audio | 音樂、原音、SFX、ducking、混音 | soundtrack、mix-audio、sfx-mix、loudness/audio handoff | DOCTRINE |
| L4 Text | approved text、字幕、字卡正確性 | subtitle chain、caption audit、title cards、ASR draft | DOCTRINE |
| L5 Review | 客觀檢查、感知審查、品味 finding、owner verdict | rendered QA、final verify、black frame、fatigue、caption、perception、blueprint checklist | DOCTRINE；儀器可用 |

L1 的 CERTIFIED 僅表示「有界、單一 picture 修訂」的 Skill
reproducibility 已通過；不等於完整影片、其他 LOOP 或 creative delivery
已批准。

## 4. 跨 LOOP 的可攜 context

P0 不建立新的 `loop_context` envelope。每輪從四類既有來源重建需要的
context：

1. approved intent／story spine／script reference；
2. selects manifest 或素材證據；
3. run provenance（含六欄決策紀錄）；
4. candidate run dir（plan、timeline、handoff、QA、render）。

Evidence ref 的最小形狀：

```jsonc
{
  "path": "run-relative/or/repo-relative/path",
  "anchor": {"time_range": [40.867, 42.562], "cell_id": null, "check_id": null},
  "produced_by": "named capability or agent judgment"
}
```

機器證據、agent 語意判讀與 owner 品味裁決必須分開標示。取樣 coverage
只能證明看過哪些位置，不能冒充「好看」或「視覺家族數」的 machine PASS。

## 5. L5 Review Loop 的最小設計

L5 第一版不建立新 reviewer engine；它組合現有能力：

```text
fresh rendered candidate
  → 客觀儀器（stream/duration/black frame/beat/loudness/caption/lifecycle）
  → 全片低密度牆
  → 可疑時間窗的 segment strip／動態對照
  → blueprint/canon checklist 逐題作答（附座標）
  → objective/taste findings
  → owner final taste verdict
```

第一次試航可在 `.tmp` 寫實驗型 review packet，不先登記新正式 artifact。
最小 finding 欄位為：

```jsonc
{
  "finding_id": "f6",
  "scope": {"stable_ids": ["montage_014"], "time_range": [40.867, 42.562]},
  "class": "objective | taste",
  "statement": "可否證的一句話問題",
  "evidence_refs": [],
  "owner_capability": "material | picture | effects | audio | text | compose",
  "proposed_next_loop": "L0 | L1 | L2 | L3 | L4",
  "owner_verdict_required": true,
  "status": "open | resolved | waived_by_owner"
}
```

L5 只產生 findings 與 verdict，不得偷偷修改 timeline。是否需要正式
normalizer adapter，必須由一次真實 L5 試航的格式摩擦證明。

## 6. First-of-kind 認證與日常執行

### 新 LOOP／新模式首次出現

每種新模式只做一次輕量 first-of-kind 認證：

1. 新 agent 只讀 Skill、四類 context 與原始 finding／任務。
2. 自行定位問題並提出附證據方案，不洩漏預期答案。
3. 停在 owner gate；不得把沉默當批准。
4. 只改 owner 批准的 stable ID／layer／時間範圍。
5. 產出 fresh semantic diff、render/preview 與該層 focused gates。
6. 六欄決策、三項遙測與後續限制可被下一 LOOP 讀回。
7. owner 查看前後證據後，判定 PASS／FAIL／UNKNOWN。

### 已認證模式的日常修訂

不重跑完整盲測或 A/B 實驗，只需：

- 使用已認證 Skill 形狀；
- 走 owner gate；
- 跑受影響層的 focused gates 與 semantic diff；
- 若改 production code，再跑該模組測試與相稱回歸；
- 技術 PASS 不得翻動 creative/delivery flags。

## 7. 建設順序

### Phase 0 — 文件與證據收斂

- 本文件成為唯一 Product Spec。
- Skill 更新實際成熟度。
- f1 只封存精簡 verdict、diff、hash、限制；大量媒體留在可重建 run。
- 保留舊 decision 作歷史，不讓舊 driver/v2 提案繼續冒充現況。

### Phase 1 — L5 first-of-kind

以 Canon 67 `candidate_v2` 為輸入，使用現有 QA、感知牆與 blueprint
checklist 產生第一份有座標的 review findings，交 owner 裁決。

### Phase 2 — 由真實 finding 開挖對應 LOOP

不先製造假缺口：L5 的第一個有效 finding 屬於哪層，就先認證哪層。
Picture 已認證；Effects、Audio、Text 各需一次 first-of-kind。

### Phase 3 — 44 秒整合飛行

在同一 Canon 67 沙盒完成：

```text
L0 → L1 → L2 → L3（音樂型最小範圍）→ L4 → L5
```

證明前一層輸出、證據與限制可水平攜帶，且 L5 finding 能回到指定層，
不用啟動 route runner。

### Phase 4 — 訪談／cutaway 垂直切片

以含語音片段認證 L3 的 dialogue continuity、ducking 與 L4 的
ASR-draft→owner-approved-script→caption 流程；44 秒純音樂切片不能替代
這項證據。

### Phase 5 — 完整 9.4 分鐘候選片

最後才擴至三幕能量弧、章節卡、訓練／生活選材、主任訪談、感謝／離別、
班導名冊。CapCut 保持 finishing/manual gate，不投資 GUI 自動化。

## 8. 觸發式硬化清單

以下機構不是 P0 預設建設；發生可觀測事件才立項：

| 機構 | 建造觸發 |
|---|---|
| deterministic helper | 同一手工轉換在獨立 LOOP 重複出現，或再次需要 pilot-only 臨時 JSON |
| finding normalizer adapter | 一次 L5 實跑證明既有 finding 形狀無法可靠攜帶 |
| proposal hash 綁 verdict | 多 agent 並行，或一次「批 A、套 B」事故 |
| append-only journal engine | 決策遺失、覆寫或爭議事件 |
| `loop_context` envelope | 一次跨 session 無法由四類 context 重建 |
| evidence hash | 證據漂移或跨機器不一致事件 |
| layered timeline v2／dirty matrix | 跨層修訂無法由 semantic diff 表達，或完整重渲染成本超出 owner 可接受預算 |
| segment rerender | 完整影片尺度的重渲染時間實測成為主要迴圈成本 |

新機構必須取代對應 pilot-only 做法，不得讓兩套永久並存。

## 9. 無技術債建設規則

「無技術債」在本產品的可驗證定義：

1. 優先使用既有 public API；新增 helper 前先稽核重複能力。
2. 新 production behavior 先寫 focused failing test，再做最小實作。
3. 新 tool/artifact 與 dictionary、Skill ownership、contract 宣告同單完成。
4. experimental packet 留在 owner zone；證明有長期消費者後才升正式契約。
5. stable ID 優先，禁止以「第 N 顆」作唯一 identity。
6. 只接受 fresh verification；禁止複製舊 PASS 報告。
7. 客觀 PASS、agent judgment、owner taste verdict 三者不得互相冒充。
8. 不修改 `human_creative_approval`／`final_delivery_claimed`，除非 owner 明文授權。
9. 不為 creative run 無差別跑 full suite；production code 變更才依風險跑 focused＋回歸。
10. 每完成一種新模式，更新本文件成熟度與 durable evidence link。

## 10. 目前下一步

下一個 bounded task 是 **L5 Review Loop first-of-kind**：只讀已封存的
Canon 67 context 與 `candidate_v2`，組合既有 review/verify capabilities，
寫實驗型 findings packet，停在 owner taste gate。

這一步不建立 orchestrator、常駐 driver、timeline v2、journal、正式
finding registry 或自動回派引擎。
