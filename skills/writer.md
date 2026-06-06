---
name: writer
description: 編劇 Skill。給定主題 + 受眾 + 風格，agent 產出 script.json（pipeline 源頭）。內含腳本架構準則、字數規則、search_query 規範。寫完後用 validate 指令檢查通過再交下去。
---

# Writer Skill

> **Facet 擁有權(Node 3,見 [spec-contract.md](spec-contract.md)):編劇擁有 `text_layer` facet。**
> 邊界:`director` 決定「這段要不要文字、為什麼」;**`writer` 寫實際字句**;`effects` 決定文字怎麼視覺呈現;`audio` 決定人聲/音樂/原音怎麼混。
> text_layer 欄位:`label` / `narrative` / `subtitle` / `name_super` / `reason`;**無文字時明確標 `text_layer: "none"`**(留白是顯式設計)。

編劇是整條 pipeline 的源頭。  
**Skill 本身不直接呼叫 LLM**——agent (你) 就是 LLM，這份 SKILL.md 是給你看的劇本撰寫規範。

寫完 script.json 後，用 `validate` 指令檢查是否合格。合格後才能交給後續 Skill。

---

## ⚠️ 兩種模式:旁白片 vs MV(2026-06-03 看真片校正)

編劇有**兩種產出**,別搞混:

### A) 旁白單位片 → voiceover（傳統,本文件下半部）
`text` 旁白 → TTS 配音 + 字幕。

### B) 結訓 MV → **螢幕文字層**（不是 voiceover!）
看 66 期真片:MV 沒旁白,但有**大量螢幕文字,而且選擇性上**——沒有它紀實畫面看不懂。**MV 的編劇 = 設計螢幕文字層**:

| 文字類型 | 欄位 | 用在 | 誰寫 |
|---|---|---|---|
| **標籤/標題** | `label` | 紀實活動段標「這在幹嘛」(礙子拆線作業) | 編劇(看 caption 寫) |
| **敘事字卡** | `narrative` | 故事/轉場精神標語(傳承精技 篤學不倦) | 編劇 |
| **演講字幕** | `subtitle:"auto"` | 有人講話 → 字幕原音 | **ASR(whisper)轉錄** |
| **人名下標** | `name_super` | 標這是誰(配五班 鍾峻松 老師) | 導演宣告 |

**邊界 = 選擇性,逐段設計(不是全上)**:
```
講話段       → subtitle(ASR)
紀實活動段   → label
故事/轉場節點 → narrative
有特定人物   → name_super(導演)
純快剪 montage → 留白(不上)
```
→ 哪段上哪種、哪段留白,是編劇要**設計評估**的核心。**沒有文字層,結訓紀實片觀眾看不懂在拍什麼。**

---

## 工具位置

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

只用一個指令：
```bash
python3 video_tools.py validate <script.json>
```

---

## 寫腳本前先想清楚 3 件事

來自 vault `video-editing-workflow-architecture-first-fallback.md`：

1. **影片主題**：要傳達什麼 1 句話能概括？
2. **目標受眾**：是技術人？一般大眾？資深從業者？
3. **預計長度**：30 秒（短訊息）/ 90 秒（知識普及）/ 3 分鐘（深入分析）

**沒想清楚就寫腳本 = 浪費後面所有 Skill 的時間**。

---

## 腳本架構：3-4 段最穩

| 段數 | 適用 | 結構 |
|------|------|------|
| 3 段 | 60–90s 短片 | 開頭 → 核心 → 收尾 |
| 4 段 | 90–120s 普及 | 背景 → 機制 → 應用 → 展望 |
| 5+ 段 | 3 分鐘以上 | 加分支或對比 |

每段功能要明確：
- **開頭**：建立背景 / 引出問題 / 用亮點抓注意力
- **中段**：核心內容（怎麼運作 / 為什麼這樣 / 有什麼影響）
- **收尾**：總結 / 留下記憶點 / 提出展望

---

## script.json 格式（嚴守）

```json
[
  {
    "segment": 1,
    "title": "開頭",
    "media_pref": "video",
    "search_query": "胡椒餅",
    "visual_desc": "炭火爐前，金黃酥脆的圓形烤餅貼在高溫爐壁上，爐口透出橘紅火光",
    "cultural_specificity": "local",
    "duration_sec": 18,
    "text": "胡椒餅在炭火甕裡烤得焦黃，師傅赤手伸進高溫的爐口，貼上一塊麵團，又取出一塊酥脆金黃的成品。"
  }
]
```

| 欄位 | 規則 |
|------|------|
| `segment` | int，從 1 連續編號 |
| `title` | 中文短字串，給 agent 自己看用，不會出現在成片 |
| `media_pref` | `"video"` 或 `"photo"`；找不到影片時 pipeline 會自動退到 photo + Ken Burns |
| `search_query` | **中文核心關鍵字**（料理名／場景名，1–2 個詞最準），如『胡椒餅』『鐵板料理』『夜市 人潮』。Pexels/Pixabay 已加 `zh-TW` locale，中文命中良好（見下節）|
| `visual_desc` | **中文「畫面描述／分鏡」**——這一段畫面上「看得到什麼」（場景+主體+動作），純視覺、不要文學情緒。**VLM 用它驗證圖片**，也是學員補拍依據（見 §2c）|
| `cultural_specificity` | `universal`（預設）/ `local`（在地專有，stock 命中率低）/ `abstract`（抽象詩意，stock 無對應）|
| `duration_sec` | 12–60 之間最佳；路線 A 下這是 hint，TTS 實際時長為準 |
| `text` | 中文旁白；會用標點切句後做 TTS 與字幕 |

---

## 三條寫得好的標準

### 1. text 字數要對得上 duration_sec

中文 TTS 速度約 **4 字/秒**：

| duration_sec | 字數目標 | 範圍 |
|-------------|---------|------|
| 12s | 48 字 | 36–60 |
| 18s | 72 字 | 54–90 |
| 22s | 88 字 | 66–110 |
| 30s | 120 字 | 90–150 |

**字太少**：影片比 hint 短很多（可接受，但內容單薄）  
**字太多** (cps > 8)：TTS 唸太快，字幕來不及讀（validate 會擋）

### 2. search_query 用「中文核心關鍵字」（D2 修訂：中文優先）

⚠️ **舊版說「要寫英文視覺概念」是錯的。** Pexels/Pixabay 後端帶 `zh-TW` locale，
中文搜尋命中良好且更自然——`胡椒餅`、`鐵板料理`、`刈包` 直接搜就有對的素材。
**不要再繞英文翻譯。**

寫法準則：

| 原則 | 例 |
|------|----|
| 用**料理名／場景名**本身 | `胡椒餅`、`鐵板料理`、`藥燉排骨`、`刈包` |
| **1–2 個核心詞**最準 | ✅ `夜市 人潮`　❌ `胡椒餅 炭烤 夜市`（詞太多反而稀釋） |
| 抽象段落用**具體場景**詞 | 「將散未散」→ `夜市 收攤 深夜` |

> 注意：`search_query` 是**找素材**用的大標關鍵字；它**不負責驗證**——驗證交給 `visual_desc`（見 §2c）。

### 2c. 三欄各司其職：搜尋用關鍵字、驗證用畫面描述、配音用旁白（D5 重點）

| 欄位 | 例（胡椒餅那段）| 給誰用 |
|---|---|---|
| `search_query`（中文關鍵字）| `胡椒餅` | 丟 Pexels/Pixabay **找素材** |
| `visual_desc`（中文畫面描述）| 「炭火爐前，金黃酥脆的圓形烤餅貼在高溫爐壁，爐口透出橘紅火光」| VLM **驗證圖片** / 學員補拍 |
| `text`（中文旁白）| 「胡椒餅在炭火甕裡烤得焦黃。師傅赤手伸進高溫的爐口…」| **TTS / 字幕** |

為什麼分開：
- **旁白 `text`** 是**文學語氣**（混了情緒、修辭），拿去問 VLM「這張圖符不符合」會太苛或太模糊。
- **關鍵字 `search_query`** 又太粗，不足以判斷一張圖對不對。
- **`visual_desc`** 是**純畫面事實**——場景、主體、動作、顏色、光線——VLM（qwen3-vl:4b）拿它判斷最準。

寫 `visual_desc` 的原則：只描述「鏡頭裡看得到的」，不要寫抽象情緒
（「將散未散的氣息」→ 改寫成「攤販拉下鐵門、街道燈光昏暗冷清」）。

### 2b. 在地/抽象主題：標 cultural_specificity，別硬搜 stock

有些主題 stock 庫天生沒有對應素材：

- `local`：在地專有（胡椒餅、特定廟會）——西方 stock 命中率低，可能要靠視覺概念近似或本地素材。
- `abstract`：抽象詩意（「將散未散」「無人深空」）——stock 完全無對應，屬 Stock Ceiling。

標上後，pipeline 重試時會**跳過西方 video stock 重挑、直接走 photo fallback（Ken Burns）**，
最終仍找不到就輸出中文補拍指引並 exit 0（見 D1 photo fallback 決策）。`universal` 主題不受影響。

### 3. text 要用中文標點

`split_by_punct` 切句靠 `，。；！？、` 這幾個標點。  
**沒有標點 = 整段變一條字幕，觀眾來不及讀**。

寫腳本時自然斷句即可：

```
✅ 大型語言模型透過數十億個參數，從網路上的海量文本中學習語言的規律。
✅ 在醫療領域，AI 協助醫師判讀影像、發現早期病灶。
❌ 大型語言模型透過數十億個參數從網路上的海量文本中學習語言的規律
```

每個標點之間（一個 phrase）建議 **8–20 字** 最舒服。

---

## 製作設計欄位交給導演（style / media_pref / layout / bgm / effects / kind）

> ⚠️ **職責分工（2026-06 切分）**：編劇只寫**內容**——`text` / `search_query` / `visual_desc` / `cultural_specificity` / `duration_sec`，以及「這段傾向動態還是靜態」這個粗略 `media_pref` 提示。
>
> **「怎麼呈現」的製作設計決策**——全片與逐段 `style`（narrative/mv/promo）、媒材型態 `layout`（montage/collage/framed）、配樂 `bgm`、片頭片尾 `kind:title`、`effects.*`、素材源 `source`——**全部交給導演** [director.md](director.md)。
>
> 編劇不需要在腳本裡填這些；導演會在你交稿後補上。你只要把**字和畫面意義**寫對。

（如果是你一個人從頭包到尾，就先戴編劇帽寫內容、再戴導演帽讀 [director.md](director.md) 補製作欄位。）

## 完整寫作流程（編劇段）

1. 確認主題、受眾、長度
2. 列出 3–5 段的功能（背景/機制/應用/展望/收尾）
3. 為每段：
   a. 想中文要說什麼（字數對齊 duration × 4）
   b. 自然標點切句（每句 8–20 字）
   c. 填 search_query：這段的中文核心關鍵字（料理名／場景名，1–2 詞）
   d. 填 visual_desc：這段「畫面上看得到什麼」的純視覺中文描述（給 VLM 驗證用）
   e. 判斷 cultural_specificity（universal / local / abstract）
   f.（粗略）media_pref：這段傾向動態 video 還是靜態 photo——細部媒材/版面由導演定
4. 寫成 script.json
5. 跑 `validate` 確認通過
6. 交給**導演** [director.md](director.md) 補製作設計，再進 pipeline / route

---

## validate 指令

```bash
python3 video_tools.py validate /workspace/script.json
```

輸出 JSON：
```json
{
  "status": "ok" | "warning" | "error",
  "can_run": true | false,
  "segments_total": 4,
  "errors": 0,
  "warnings": 2,
  "issues": [
    {
      "segment": 2,
      "field": "text",
      "level": "warning",
      "message": "字幕閱讀速度 5.2 字/秒，偏快",
      "suggestion": "中文字幕舒適速度為 3–5 字/秒"
    }
  ],
  "summary": "..."
}
```

`can_run = false` 表示有 error，**必須修完才能進 pipeline**。  
`can_run = true` 但有 warning：可進 pipeline，但建議檢查。

### 檢查項目（複習）
- `search_query < 2 詞` → error
- `search_query` 中文單一關鍵字 OK（中文沒空白，不再判 <2 詞 error）；詞數 ≥3 → warning（稀釋命中）
- `search_query` 兩段完全相同 → error
- `duration_sec < 5s` → error
- 字幕閱讀速度 > 8 字/秒 → error
- 字幕速度 5–8 字/秒 → warning
- text 欄位空白 → warning
- 總段落數 < 2 → error

---

## 與 vault 腦暴流程的關係

Vault 有兩份「腳本腦暴」工作流文件：
- `video-editing-workflow-brainstorming-to-material-direction.md`
- `video-editing-workflow-architecture-first-fallback.md`

那些文件針對「有人在前端拍片」的場景（學員補拍）。  
本 Skill 用於**全自動 pipeline**（素材來自 YouTube），所以簡化為：
- 不用反推「素材缺口」（小編會自動找）
- 不用寫「拍攝指令」（沒有人在拍）
- 但**段落功能、敘事結構**這兩件事完全沿用

如果未來要做訓練營實拍片，就走 vault 的完整流程；現在做知識型內容，走本 Skill 就夠。

---

## 範例：完整可用的腳本（中文優先三欄）

```json
[
  {
    "segment": 1,
    "title": "暮色降臨",
    "media_pref": "photo",
    "search_query": "夜市 紅燈籠 黃昏",
    "visual_desc": "傍晚藍紫色天空下，一排紅色或橘色燈籠在傳統市場街口亮起",
    "duration_sec": 18,
    "text": "傍晚六點，巷口的燈籠一盞一盞亮起。風裡開始有了食物的味道，那是夜市還沒醒，但已經在準備了的時間。"
  },
  {
    "segment": 2,
    "title": "鐵板火光",
    "media_pref": "video",
    "search_query": "鐵板料理",
    "visual_desc": "滾燙鐵板上煎著食材，滋滋冒煙，廚師用鏟子翻面、淋醬的特寫",
    "duration_sec": 22,
    "text": "煎台前的火光，麵糊在鐵板上吱吱作響，老闆翻面、加蛋、淋醬，動作流暢得像一段練過千百次的舞。"
  },
  {
    "segment": 3,
    "title": "烤爐火紅",
    "media_pref": "video",
    "search_query": "胡椒餅",
    "visual_desc": "炭火爐前，金黃酥脆的圓形烤餅貼在高溫爐壁上，爐口透出橘紅火光",
    "cultural_specificity": "local",
    "duration_sec": 22,
    "text": "胡椒餅在炭火甕裡烤得焦黃，師傅赤手伸進高溫的爐口，貼上麵團，又取出一塊酥脆金黃的成品。"
  }
]
```

實測（nightmarket 11 段全自動 E2E）：見最新 decision log。三欄分工是把 search/驗證/配音拆開的關鍵。

---

## 已知踩過的雷

### 字太少（v1 ai_script.json）
原版 19 字撐 18 秒 → TTS 實際只跑 7 秒 → 影片變 28 秒 → 內容速食。  
**修正**：照「字數 = duration × 4」寫，validate 不再放行字太少的腳本（待加強 warning）。

### search_query 太泛用（v1 軍事素材）
"artificial intelligence" 搜出來會看到 AP News 軍事訓練（演算法當時的熱門影片）。  
**修正**：加年份、加場景關鍵字。

### 無標點長句
整段沒有 `，。` → split_by_punct 切不出 phrase → 字幕變一條超長 → 無法閱讀。  
**修正**：寫腳本時自然斷句，每 8–20 字一個標點。

---

## 與其他 Skill 的銜接

### 下游（編劇的輸出餵給誰）
- `導演 Skill` [director.md](director.md)：吃內容稿 → 補製作設計欄位（style/layout/bgm/effects/kind）
- `音控師 Skill`：吃 text → 產 TTS
- `小編 Skill`：吃 search_query → 找素材
- `字幕師 Skill`：間接（透過 tts_timing）
- `VERIFY Skill`：字幕準確率維度回查 text

### 上游（編劇的輸入）
- 使用者口頭給的主題、受眾、長度
- 沒有結構化 JSON 輸入（手工/agent 直接寫）

---

## 對應的 vault 文件
- `projects/video-agent-pipeline/roadmap.md` Phase 6
- `projects/video-agent-pipeline/skill-interface-contracts.md` — script.json 格式
- `video-editing-workflow-brainstorming-to-material-direction.md` — 進階腦暴流程
- `video-editing-workflow-architecture-first-fallback.md` — 段落功能 / fallback 規則
