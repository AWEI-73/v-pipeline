---
name: video-workflow
description: SPEC 最上游的「互動式模糊消除」技能。把模糊的影片委託(「幫我做個結訓影片」)透過引導式提問收斂成可執行的結構化 brief,再分流給導演(production SPEC)與編劇(文字層)。架構優先,不從隨機素材拼貼開始。
---

# Video Workflow — 互動式模糊消除(SPEC 最上游 / Node 0)

這是 **SPEC 最上游(Node 0)**。整條鏈的編排入口是 `video-pipeline` 技能;當需求模糊時,
`video-pipeline` 會先把你導到這裡。職責:把「想拍什麼」(vague 需求)變成「可執行 SPEC」。

> **這是大模型(Agent 層)的活,不是 ollama、也不是編劇。** 模糊消除靠判斷/品味/語言,
> 是最值錢的能力。坐 SPEC 最上游,輸出 brief 分流給:`director`(製作 SPEC 主力)↘ `writer`(螢幕文字層)。

核心原則:

> **架構優先。不要從隨機素材拼貼開始。先問清楚、收斂成結構,再往下做。**

---

## Interactive Brief Gate(進任何工作前的第一道閘)

> **在進 director / writer / material-map / build 任何工作前,必須先收齊 brief 欄位。** 這是正式工作步驟,不是可選聊天。沒收齊就停下來問,不要憑空假設。

第一個判斷是 **material availability**。先問使用者是否有特定素材、人物、
活動紀錄、教學畫面、品牌素材或可補拍來源,再決定是
`existing-material-first`、`story-first`、還是 `hybrid`。

- `existing-material-first`:先跑 material-map。現有素材是故事來源與限制,再由互動填補用途、受眾、順序、口白和教學重點。適合 teaching、personal video、活動回顧、品牌素材整理。
- `story-first`:沒有素材或明確要生成故事/繪本/漫畫。先做角色/故事/教學結構,再派生 material_needs 和生成/補拍需求。
- `hybrid`:有部分素材,缺口由 material_delta 決定補拍、生成、縮短、改寫、刪段或 waiver。

原則: **generation is fallback** for existing-material-first teaching /
personal video routes. It may create diagrams, chapter cards, symbolic inserts,
or non-proof bridges, but it must not replace real proof material.

**必收欄位(canonical = JSON,見 `examples/brief_graduation_mv.json`):**

| 欄位 | 值域 |
|---|---|
| `video_type` | graduation_mv / narration_video / event_recap / knowledge |
| `spec_start_mode` | script_first / material_first / hybrid |
| `material_availability` | existing-material-first / story-first / hybrid |
| `can_reshoot` | true / false |
| `fallback_policy` | reshoot_first / generated_first / stock_bridge / review |
| `review_level` | normal / high |
| `must_include` | [人/事/景…] |
| `target_length` | e.g. "3-5 minutes" — **必填**:缺了音樂長度會變成片長(soul-v5 教訓) |
| `audience` | 給誰看 |
| `tone` | 情緒/曲風方向 |
| `mode` | **顯式宣告** pacing mode:warm_documentary / story_documentary / training_recap / rhythmic_mv / promo。不填會從 video_type 推斷——`mv` 會推成 rhythmic_mv(max_hold 6s),沉穩內容會全掛 pacing gate(soul-v5 教訓) |
| `effect_direction` | optional: none / restrained / expressive / story_required;只描述故事功能與強度,不可寫 Remotion API |

**本專案預設**:`spec_start_mode=script_first` + `can_reshoot=true` + `fallback_policy=reshoot_first`(學員多半能補拍 → 別被現有素材池綁死;缺口優先補拍而非降級故事)。

**固定提問樣板:**
```text
1. 這支影片給誰看?
2. 主要目的:紀念 / 宣傳 / 成果展示 / 教學 / 正式匯報 / 其他?
3. script-first、material-first、還是 hybrid 起手?
4. 現在有沒有指定素材資料夾、現有影片/照片、人物/場景/品牌素材?
5. 這是 teaching、personal video、活動回顧、品牌片、還是 storybook/comic?
6. 團隊能不能補拍缺的素材?
7. 缺素材時優先:補拍 / 生成 / stock 橋接 / 人工複核?
8. 哪些人/場景/時刻是必放(must-include)?
9. 哪些段要人工複核?(通常:開場/收尾/必放/identity-sensitive/原音段)
10. 目標長度、節奏、語氣、配樂方向?
11. 特效是否有敘事功能?例如 opening hook、章節轉場、記憶框架、資訊標示、漫畫格線；若只是裝飾則先標 none/restrained。
```

**三種起手模式(同一 workflow 依 brief 參數分支,不是三條 pipeline):**
```text
script_first :  brief → 草稿/導演 SPEC → material-map 覆蓋率 → gap route
material_first: material-map → 受可用素材約束的 SPEC
hybrid       :  粗概念 → material-map → 最終 SPEC
```

---

## 第一步永遠是:模糊消除(clarifying questions)

收到委託先別動手。先用**引導式提問**把這些不確定變確定(一次問 3–5 個關鍵的,不要逼問):

| 維度 | 要問出來的 | 為什麼關鍵 |
|---|---|---|
| **影片類型** | 結訓 MV(無旁白、音樂驅動)/ 旁白單位片 / 慶生會 / 知識片? | 決定時間軸來源(beat/tts/fixed)= 整個 pipeline 分叉點 |
| **長度 + 情緒** | 幾分鐘?熱血激昂 / 溫馨回顧 / 莊重? | 決定音樂 brief、剪輯節奏(快剪 vs 長 hold) |
| **必放(must-include)** | 一定要出現的人/事(所長、隊呼、大合照)? | **必放凌駕分數**——守門的依據,漏了就是失敗 |
| **素材現況** | 有哪些素材?先看 `material-map`(人可讀地圖) | 雞生蛋:不知道池子有什麼就寫不出務實劇本 |
| **開場/收尾** | 怎麼開、怎麼收?有沒有指定照片(大合照)? | 高權重 slot,弱開場/收尾差很多,常是照片 |

> ⚠️ **雞生蛋鐵則**:先請小編產 `material-map`(`python3 video_tools.py material-map <db> --out map.md`),
> 人/你看著地圖寫**務實**劇本(不要求池子沒有的)→ 再 match。別憑空寫了一堆池子裡沒有的段。

---

## 收斂流程(8 步,架構優先)

1. **模糊消除**(上面那張表)→ 確認 類型/受眾/長度/情緒/必放/素材現況。
2. Brainstorm 2–3 個劇本方向(不同切入:時間線 / 主題 / 人物群像)。
3. 推薦一個方向 + tradeoffs(讓委託人選)。
4. 建段落結構:開場 → 中段(紀實主體)→ 後段(成果/傳承)→ 收尾。
5. 從選定劇本**推素材缺口**(對照 material-map:哪些有、哪些要補拍/補抓)。
6. 缺口 → 具體拍攝指令(交 shooting-brief)或 stock/generated 補洞。
7. 規劃字幕/旁白/音樂/fallback(分流:文字層→編劇、配樂 brief→導演/音控)。
8. 收斂成 **director MV 劇本**(下節格式)→ 交導演固化。

---

## 輸出:director MV 劇本 brief(分流的交接物)

模糊消除的產物是一份可被 `director` 接手固化的 MV 劇本骨架(統一段落模型,MV 模式):

```json
{
  "style": "mv",
  "music": {"brief": "熱血激昂、進行曲感", "query": "inspirational orchestral", "source": "yt"},
  "segments": [
    {"segment": 1, "kind": "opening", "visual_desc": "校門/晨光空拍",
     "media": "photo", "weight": 1.2, "needs_review": true},
    {"segment": 2, "layout": "montage", "pace": "fast",
     "visual_desc": "拖拉電纜實作", "material_hint": "拖拉電纜", "label": "電纜作業"},
    {"segment": 3, "hold": true, "audio_role": "diegetic", "weight": 2.0,
     "visual_desc": "隊呼", "material_hint": "隊呼", "must_include": "隊呼", "keep_audio": true},
    {"segment": 4, "visual_desc": "傳承精神", "narrative": "傳承精技\n篤學不倦"},
    {"segment": 5, "kind": "closing", "media": "photo",
     "visual_desc": "大合照", "material_hint": "大合照", "must_include": "大合照", "weight": 1.3}
  ]
}
```

欄位語意 → 見 `skills/director.md`(production SPEC)與 `mv_cut.validate_mv_script`。
- 分流:`visual_desc/material_hint/kind/layout/pace/must_include/media/weight/audio_role` = **導演**;
  `label/narrative/subtitle/name_super` = **編劇**(螢幕文字層,選擇性逐段)。
- 驗證:`python3 mv_cut.py validate <script.json>`。

---

## 鏈位置

```
需求(故事)
  └ video-workflow 模糊消除(本技能)→ brief
        ↘ director  固化 production SPEC(分段/必放/音樂/媒材)  ← 主力
        ↘ writer    螢幕文字層(label/narrative/subtitle,選擇性)
  → curator(ingest/caption/material-map/match-mv)→ run_mv/mv_chain → verify → dashboard 人複核
```

## Node 0-14 Operating Flow(agent 操作流 — 本檔擁有,見 roadmap.md)

> **canonical SPEC 輸入 = `segment_contract.json`(normalized JSON)。** legacy flat script
> 只是 adapter 生成的「執行載荷」,不是 SPEC、不可當真相(見 `contract_adapter.py`、ADR 2026-06-04)。

每個 node 必須產出能驅動下一棒的**產物**(只描述意圖、不出檔/狀態/路由 = 未達 MVP):

> **順序(demand-first,2026-06-04 定):導演劇本先出,Node 2 在 Node 3 之後。**
> 「地圖」= 導演在 segment_contract 定的**素材類別規範**(`material_fit.category`,引用
> `examples/material_categories.json`)+ 每段 `collection_instructions`(找/補拍說明)。小編**照地圖**
> 把現有素材(本地池或 `source_link` 連結)找/歸類/評分 → coverage;缺的 → 補拍(說明即拍攝指引)。
> 地圖的用途:讓 BUILD 更明確 + 能請學員依類別聚焦補拍。

| Node | 層 | owning skill | 產物 | 下一棒 / route signal |
|---|---|---|---|---|
| 0-1 Brief | SPEC | video-workflow / shooting-brief | `brief.json` | → Node 3 segment_contract |
| 3 Segment Contract(地圖規範) | SPEC | spec-contract / director | `segment_contract.json`(material_fit.category + collection_instructions) | valid/needs_clarify/blocked |
| 2 Material intake/coverage(照地圖找+歸類+評分) | BUILD-facing | curator / gap-analyzer | `material_coverage_map.json`(現有素材 vs 地圖類別 + fit 分) | covered/weak/missing/blocked → 缺則補拍 |
| 4-7 Facets | SPEC | writer / audio / effects / director | 嵌入 segment_contract 各 facet | facet_status ready/needs_review |
| 8 Fallback Route | SPEC | gap-analyzer / route | `fallback_route.json` | selected_route |
| 9 Assembly Plan | BUILD-facing | editor | `assembly_plan.json` | execution_route.status |
| 10 Timeline/EDL | BUILD | editor | `timeline_build.json` | ready/needs_fix/needs_review/blocked |
| 11 AI Editor Review | REVIEW | editor / dashboard | `editor_review.json` | approve/auto_fix/route_change/human_review/block/rerender |
| 12 Continuous Verify | VERIFY | verify | `verify_result.json` | pass/warn/fail/blocked + next_route |
| 13 Render/Export | DELIVERY | editor / verify / dashboard | `artifact_manifest.json` + 影片 | pending/complete/failed/blocked |
| 14 Revision Loop | ITERATION | route / editor / verify / dashboard | `revision_plan.json` | 最小受影響節點 |

**Light Route Contract**(route 只讀產物狀態派工,不重做 skill 推理):
```json
{"current_node":"node_9_assembly_plan","artifact":"assembly_plan.json",
 "status":"ready|needs_fix|needs_review|blocked","next_node":"node_10_timeline_build",
 "reason":"…","blocking":[],"review_required":false}
```
路由規則:brief 缺→0-1;coverage 缺/未收集→Node 8 collect_material 或 Node 2;contract 無效→Node 3/該 facet;fallback 衝突→8;assembly 無法執行→8/收集/review;timeline 無效→10;editor gate→11;verify blocker→`finding.next_route`;render 失敗→13;revision→14 分類後送最小受影響節點。

**Skill handoff 慣例**(每個 domain skill 應宣告):`Upstream`(吃什麼)/ `Owns`(可改什麼)/ `Downstream`(必須產出什麼)/ `VERIFY hooks`(怎麼驗)。

## Authority(vault 參考)

- `/home/lio730309/vaults/hermes-vault/video-editing-workflow-architecture-first-fallback.md`
- `/home/lio730309/vaults/hermes-vault/video-editing-workflow-brainstorming-to-material-direction.md`

不要給「讓它更有感情」這種空話——一定要落到具體鏡頭、段落功能、字幕用詞、剪輯決策。

---

## ISF1 Interactive Brief Contract

這個 skill 的交付物不是聊天紀錄，而是能推動下一個 skill 的互動式 artifact。缺資訊時要停下來問；資訊足夠時才往下交付。

### 必問分支

1. 這是 event/MV/訓練回顧，還是 comic/photo/storybook/panel narration？
2. 起手是 `script_first`、`material_first`、還是 `hybrid`？
3. 目前有素材、可補拍、可生成，還是三者混合？
4. 缺素材時優先補拍、生成、縮短、改寫、還是人工決策？
5. 是否需要 `storyboard_panel_locked`？
   - 漫畫、照片故事、繪本、口白 panel 片預設 `true`。
   - 活動 MV、課程 recap、真實素材 montage 預設 `false`。

### 互動式輸出

| Artifact | 內容 | 交給誰 |
|---|---|---|
| `project_brief.json` | video_type, audience, target_length, tone, start mode, fallback policy, must_include | `story-soul-blueprint` / `director` |
| `story_world.json` | 人物、場域、時間、情境、限制、真實/生成邊界 | `story-soul-blueprint` |
| `creative_concept.json` | 核心命題、敘事裝置、情緒弧線、hook | `writer` / `director` |
| `screenplay_beats.json` | 每段故事功能、口白/字幕方向、節奏、情緒轉折 | `writer` / `director` |
| `director_shot_plan.json` | 每 beat 需要的鏡頭語言、素材數量、媒材偏好、fallback | `material-map` |
| `material_needs.json` | canonical needs；必須能被 M6 validate-needs 驗證 | `material-map` lifecycle |
| `effect_intent_plan.json` / `effect_asset_spec.json` | 若 `director_shot_plan` 含 `effect_intent`,由 `effect-intent-plan` 編譯出的中立特效契約 | `effects-director` / Node14 |

### 停止條件

- 片長、受眾、用途、素材來源任一不明。
- `storyboard_panel_locked` 是否適用不明。
- must-have / 不能生成 / 不能替代的內容不明。
- 使用者要求的故事張力無法從目前資訊推得具體 beat。

### 下一步條件

- 若重點是故事靈魂不足：交 `story-soul-blueprint`。
- 若已有清楚故事和素材需求：交 `material-map`。
- 若 delta 顯示缺素材且允許生成：交 `material-generation-fallback` / `generated-material-producer`。
- 若素材與 contract 都可 build：交 `video-pipeline` / `runtime.py`。

### 不要做

- 不要把樣板當流程固化。樣板、故事集、多影片模式留到完整 pipeline 穩定後再做。
- 不要用「看起來像」的素材替代 must-have need。
- 不要把 generated asset 當真實事件證據。
