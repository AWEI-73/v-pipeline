---
name: gap-analyzer
description: 缺口分析 Skill。讀腳本 + 段落功能，反推每段需要哪些素材（影片/照片/字卡/空景），標明 fallback tier，產出 material_needs.json + 給人看的 .md。這份輸出獨立於素材是否到手，可作為拍攝指令的依據。
---

# Gap Analyzer Skill

> ## Gap Route / Fallback Decision Contract(Node 8)
> **覆蓋偵測 ≠ fallback 決策。** 小編/material-map 報「有沒有/弱不弱」(coverage);本節決定
> 「缺了該怎麼辦」。canonical 路由(`vt_core.FALLBACK_ROUTES`):
> `none / collect_material / reshoot / generated / stock_bridge / text_bridge / script_rewrite / drop_segment / dashboard_review`。
>
> **路由選擇規則(程式版:`spec_contract.suggest_fallback_route`):**
> - 素材尚未收集 → `collect_material`(由 segment contract 產生預期需求,**不算失敗缺口**)。
> - identity-sensitive + 缺 → 預設 `reshoot`(不能補拍則 `dashboard_review`);**reject stock_bridge/generated**。
> - proof-critical + 弱/缺 → `reshoot` / `script_rewrite` / `dashboard_review`。
> - mood/bridge + 缺 → 可 `stock_bridge` / `generated` / `text_bridge` / `drop`。
> - filler + 缺 → 優先 `drop_segment`(別生不必要素材)。
> - opening/climax/closing + 弱/缺 → `dashboard_review`,除非 fallback 已明確允許。
>
> **鐵則:任何 fallback 不得假裝成真實事件素材。** identity/proof 缺口預設走補拍或人工複核。
> 邊界:`curator`=報 coverage;`director`=決定保留原意/改寫/停下複核;`writer`=寫 text_bridge/rewrite_note(路由選定後才寫);`effects`=可視覺標示 generated/stock,但**不能讓它看起來像真實事件證據**。

**核心原則（vault § 6）**：影片不一定要先有素材，但一定要先知道每一段在做什麼。  
腳本確定後，反推每段需要哪些畫面，這份清單就是「素材缺口表」。

不只結訓影片用——任何「先寫劇本後找素材」的專案都適用。

---

## 工具位置

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

主要不是用工具，是 agent 照 SKILL.md 產出 `material_needs.json`。  
驗證用：
```bash
python3 video_tools.py validate-needs material_needs.json   # 待加，目前手動 check
```

---

## 整套流程在大圖裡的位置

```
[編劇 Skill]            script.json
       │
       ▼
[gap-analyzer]          material_needs.json  ← 本 Skill
       │
       ▼
[shooting-brief]        shooting_brief.md（給學員看的）
       │
       ▼
[學員拍攝 / 蒐集]        交回 /materials/
       │
       ▼
[curator ingest]        materials_db.json
       │
       ▼
[curator rank-local]    clip_list.json
       │
       ▼
[後續 5 個 Skill]        成片
```

---

## 缺口分類（vault § 5.2 直接拿來）

每段腳本可能有以下類型的素材缺口：

| 類別 | 說明 | 範例 |
|------|------|------|
| **動作鏡頭** | 學員/人物在做特定動作 | 學員跑步、教官操作器材 |
| **情境鏡頭** | 表現某個場景氛圍 | 教室、操場、結訓典禮 |
| **空景/過場** | 環境鏡頭，銜接用 | 校園空景、走廊、招牌 |
| **特定表情** | 情緒特寫 | 結訓學員的笑容、專注眼神 |
| **字幕對應** | 純文字 / 標題 / 數據 | 「66 期養成班」、「16 週訓練」 |
| **靜態照片** | 歷史影像或無法重拍的場景 | 往期合照、老照片 |
| **音樂情緒** | 純音樂段（無需畫面）| ⚠️ 歸音控師，不在本表 |

---

## Fallback Tier（vault § 7 直接拿來）

每個缺口要標明可接受的最低 fallback 等級：

| Tier | 說明 | 範例 |
|------|------|------|
| **1** | 最理想素材 | 66 期實拍的訓練畫面 |
| **2** | 替代素材 | 65 期同類訓練畫面 |
| **3** | 補洞素材 | 照片、字卡、空景 |
| **4** | 情緒承接 | 純音樂段、慢動作、淡入淡出 |

寫缺口時要想：「如果學員拍不到 Tier 1，能接受 Tier 幾？」

---

## material_needs.json 格式

```json
{
  "project": "66期養成班-高訓結訓",
  "based_on_script": "/workspace/script_66th_graduation.json",
  "total_segments": 4,
  "generated_at": "2026-05-25",
  "segments": [
    {
      "segment": 1,
      "section": "開頭 — 歷史演進",
      "function": "establish_background",
      "duration_target_sec": 18,
      "narrative": "從往期傳承到 66 期，建立背景感",
      "needs": [
        {
          "id": "1.1",
          "category": "靜態照片",
          "type": "往期結訓合照",
          "count": 3,
          "duration_each": "3s Ken Burns",
          "purpose": "建立傳承感",
          "fallback_tier": 1,
          "fallback_options": ["66期班導照", "校史室翻拍"],
          "must_have": true
        },
        {
          "id": "1.2",
          "category": "字幕對應",
          "type": "標題卡：「66 期養成班」",
          "count": 1,
          "duration_each": "2s",
          "purpose": "明確開場主題",
          "fallback_tier": 3,
          "must_have": true
        }
      ]
    }
  ]
}
```

### 必填欄位（每個 need）
| 欄位 | 說明 |
|------|------|
| `id` | `<segment>.<seq>` 格式，便於後續拍攝指令引用 |
| `category` | 6 種分類擇一 |
| `type` | 具體類型（中文短描述）|
| `count` | 需要幾段／幾張 |
| `duration_each` | 每段預估時長（含特效類型）|
| `purpose` | 為什麼要這個素材（功能性說明）|
| `fallback_tier` | 1–4 |
| `must_have` | true = 沒有就無法成片，false = 有更好沒有也行 |

---

## 寫缺口的 3 條準則

### 1. 每段先寫「敘事功能」再列缺口
不是「我想要什麼漂亮畫面」，是「這段要傳達什麼，所以需要這些素材」。

```
✅ 段落功能：建立 66 期的傳承感
   → 需要往期合照（建立歷史感）+ 標題卡（明確主題）

❌ 段落功能：開頭要有氣勢
   → 需要 ???（沒有依據選素材）
```

### 2. 寫具體可拍的東西，不要寫抽象
```
✅ 3 位學員在走廊慢跑的中景，5 秒
❌ 一些學員的鏡頭
```

### 3. fallback tier 要誠實
- Tier 1 「66 期實拍合照」：寫得到，但學員拍不到怎辦？
- 標 fallback_tier=2（接受用 65 期類似畫面）或 tier=3（用集合照拼貼字卡）

**如果 must_have=true 但 tier=1 沒寫 fallback_options → 學員拍不到就死局**

---

## 結訓影片開頭的 6 種類型（vault § 9）

選定哪一種，缺口長相完全不同：

| 開頭類型 | 適用 | 主要缺口 |
|---------|------|----------|
| **歷史演進型** | 有傳承感、有制度演變 | 老照片 + 字卡 + 旁白 |
| **問題切入型** | 有明確痛點 | 痛點場景 + 對比畫面 |
| **任務啟動型** | 訓練/活動為主 | 任務開始畫面 + 出發鏡頭 |
| **師長訓勉型** | 有正式氛圍 | 師長講話特寫 + 全體聆聽 |
| **亮點先行型** | 有強畫面、想抓注意 | 最強動作鏡頭 + 標題卡 |
| **蒙太奇鋪陳型** | 有大量短鏡頭 | 5–10 個快切鏡頭 + 強節奏音樂 |

寫缺口前，先跟 reviewer 確認用哪一種開頭。

---

## 工作流程

1. 讀 script.json，逐段思考「這段在說什麼」
2. 對每段段落功能，列出需要的素材類型（6 種類別）
3. 每個 need 想清楚：用幾秒、幾個、做什麼、tier 多少
4. 標明 must_have 優先順序
5. 輸出 material_needs.json
6. 另出一份 material_needs.md（給 Reviewer 看，較好讀的版本）

---

## 與其他 Skill 的銜接

### 上游
- **編劇 Skill**：script.json + 段落功能定義
- **Reviewer（你）**：確認開頭類型

### 下游
- **shooting-brief Skill**：把缺口翻譯成學員看得懂的拍攝任務
- **curator (rank-local)**：學員交回素材後，依本表分類匹配

---

## Reviewer 通過標準

對著輸出的 material_needs.json/.md 問：
1. 每段缺口能否真正撐起「段落功能」？
2. fallback 是否合理（沒有 must_have+tier1+無 fallback 的死局）？
3. 缺口是否寫得夠具體（不是「來一些漂亮鏡頭」）？
4. 整體缺口數量是否現實（學員 1 週能拍完嗎）？

---

## 對應的 vault 文件
- `video-editing-workflow-brainstorming-to-material-direction.md` § 5（缺口分類 + 缺口表格式）
- `video-editing-workflow-architecture-first-fallback.md` § 6, 7（段落功能 + fallback 規則）
- `projects/video-agent-pipeline/roadmap.md` Phase 8a
