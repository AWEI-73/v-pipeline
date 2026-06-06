---
name: effects-director
description: 特效師 Skill。負責成片的視覺特效升級——色彩分級（情境調色）、開場/分段字卡、段間進階轉場。讀 script.json 每段的 effects 欄位，pipeline 在 render 後自動套用，保留 1920x1080/30fps/bt709 規格與時長。
---

# Effects Director Skill（特效師）

> **Facet 擁有權(Node 3,見 [spec-contract.md](spec-contract.md)):特效師擁有 `visual_style` facet。**
> 欄位:`layout` / `pace` / `transition` / `color_grade` / `effects` / 文字渲染風格 / `reason`。
> 原則:**特效與轉場必須服務段落功能,不是裝飾**。

特效師是「結訓特化（Phase 8d）」的專職角色，把過去散落的美學處理（Ken Burns 在剪輯、字幕在 merge）之外的**視覺特效**收進一個契約。

**邊界**：特效師只做「不改內容、不改時長」的視覺加工（調色、疊字、轉場）。
不挑素材（小編）、不剪檔（剪輯師）、不評分（VERIFY）。

---

## 工具位置

```
~/video_pipeline/video_tools.py
```

兩個指令 + 一個 pipeline 內建轉場：

```bash
# 色彩分級（情境調色）
python3 video_tools.py grade <in.mp4> --preset dusk --out <out.mp4>

# 字卡（開頭疊主標 + 可選副標，淡入→hold→淡出）
python3 video_tools.py title-card <in.mp4> --text "夜市人生" --subtitle "高雄六合夜市" \
  [--hold 2.5] [--size 96] --out <out.mp4>

# 片頭/片尾：獨立動態標題片段（文字滑入→hold→淡出，深色底+暈影）
python3 video_tools.py title-sequence --text "城市漫遊" --subtitle "A CITY IN 24 HOURS" \
  --duration 6 [--anim slide-up|fade] [--size 120] [--bg 0x0d0d1a] --out <out.mp4>
```

### 片頭/片尾段（kind=title）

在 script.json 放一個 `"kind": "title"` 的段，就是片頭或片尾：

```json
{
  "segment": 1,
  "title": "片頭",
  "kind": "title",
  "title_sequence": {"text": "城市漫遊", "subtitle": "A CITY IN 24 HOURS", "anim": "slide-up"},
  "duration_sec": 6,
  "text": "清晨五點，城市還在沉睡……"
}
```

- **不搜素材、不評 content_qa**（pipeline 自動跳過）；用 `render_title()` 生成動態標題片段。
- `text`（旁白）照常跑 TTS → 當片頭配音 + 決定片段時長；字幕也會燒上去。
- 放陣列開頭 = 片頭，放結尾 = 片尾；可加 `effects.transition` 做切入轉場。

轉場（`transition`）不需指令——pipeline 的 `build_filter_chain` 會在 xfade concat 時套用。

---

## 多圖拼貼（collage）

`layout:"collage"` 段把該段 top-N 照片裝白框、排成一列、置於深色底 + 暈影（像結訓片的群像/對比段）。
段落需 `media_pref:"photo"`、`collage_n`（預設 3）。不評 content_qa（拼貼是設計版面）。

```bash
python3 video_tools.py collage --images a.jpg b.jpg c.jpg --duration 5 --out collage.mp4
```
pipeline：`render_collage` 下載 top-N 照片候選→組拼貼→套 grade/轉場。

**單圖相框（`layout:"framed"`）**：單張照片置中裝大相框於深色底（非全屏，像參考片卡片）。
用該段單一 pick，照常評 content_qa。`collage` 工具給 1 張圖即此效果。

> 進階（未做）：相框背景換動態粒子/星空（需粒子素材）。

## BGM 情境庫（背景音樂）

script **頂層** `bgm` 宣告情境，pipeline 解析成 `bgm/<情境>.mp3` 墊在人聲下
（`mix-audio` 自動 loop 到全片長、降到 vol 0.10、淡入淡出、不壓低人聲）。

```json
{ "style": "narrative", "bgm": "emotional", "segments": [ ... ] }
```

情境（`gen-bgm` 用 ffmpeg 合成，**placeholder 可換真曲**）：
`calm` / `warm` / `emotional` / `energetic` / `tense` / `bright` / `night`

```bash
python3 video_tools.py gen-bgm --mood emotional [--duration 60] [--out bgm/emotional.mp3]
```

- **換真曲**：把 royalty-free mp3 直接覆蓋 `bgm/<情境>.mp3` 即可（Pixabay/Incompetech/FMA 等）。
- CLI `--bgm <path>` 覆寫 script 宣告；無 bgm 則純人聲。
- 合成墊樂是氛圍 pad（和弦+tremolo+lowpass+echo），質感有限，正式片建議換真曲。
- **sidechain ducking** ✅：pipeline 預設 `mix-audio --duck`——人聲說話時自動壓低音樂、停頓時音樂浮現（比固定音量專業）。BGM 基準音量可大些（0.28）。
- 進階（未做）：per-section BGM（不同段落不同曲）。

## 多圖拼貼（layout: collage）

某段想做「群像／多樣性／對比」（像結訓片把多張訓練中心照片並排），用 `layout: "collage"`：

```json
{
  "segment": 11, "title": "水果之島",
  "media_pref": "photo",
  "search_query": "水果攤 熱帶水果",
  "layout": "collage", "collage_n": 3,
  "duration_sec": 18, "text": "..."
}
```

- 拿該段 **top-N 照片候選**（`collage_n`，預設 3，最多 4）裝白框、排成一列、深色底 + 暈影。
- **不評 content_qa**（拼貼是設計版面，非單圖對題）；旁白照常配音。
- 仍吃 `effects.grade` 與切入 `transition`。
- 工具：`python3 video_tools.py collage --images a.jpg b.jpg c.jpg --duration 5 --out x.mp4`

## script.json 的 effects 欄位（每段選填）

```json
{
  "segment": 1,
  "title": "暮色降臨",
  "media_pref": "photo",
  "search_query": "夜市 紅燈籠 黃昏",
  "visual_desc": "...",
  "text": "...",
  "effects": {
    "grade": "dusk",
    "title_card": {"text": "夜市人生", "subtitle": "高雄六合夜市"},
    "transition": "fade"
  }
}
```

| 欄位 | 值 | 說明 |
|------|----|------|
| `grade` | `dusk` / `night` / `fire` / `warm` / `cool` / `neutral` | 情境調色預設；無則不調色 |
| `title_card` | 字串 或 `{text, subtitle}` | 在該段開頭疊字卡（淡入淡出）；通常只放開場段 |
| `transition` | `fade`(預設) / `slideleft` / `slideright` / `wipeleft` / `wiperight` / `dissolve` / `circleopen` ... | 這段**切入**時的轉場 |

`effects` 整個欄位可省略（向後相容）；省略 = 不調色、無字卡、fade 轉場。

---

## 色彩分級預設（grade）

| preset | 情境 | 效果 |
|--------|------|------|
| `dusk` | 暮色 / 黃昏 | 暖橘、微提亮、飽和 +18% |
| `night` | 深夜 / 冷清 | 偏藍、壓暗、飽和 −5% |
| `fire` | 火光 / 炭烤 | 強暖橘、高對比、飽和 +28% |
| `warm` | 一般暖食 | 溫和暖調 |
| `cool` | 一般冷調 | 溫和冷調 |
| `neutral` | 鮮豔主體（水果）| 輕微對比/飽和，不偏色 |

實作：`GRADE_PRESETS`（`video_tools.py`）用 `eq` + `colorbalance`，re-encode 保留 bt709 規格。

## 風格 → 轉場政策（style，編劇宣告、特效師執行）

轉場是**類型語言**，不是每片都要：劇情/敘事片用硬切才高級，MV/主題片才適合華麗轉場。
編劇在 script **頂層**宣告 `style`，特效師據此給每段「預設轉場」，段落 `effects.transition` 可覆寫。

| `style` | 預設 xfade | 轉場政策 | 適用 |
|---|---|---|---|
| `narrative`（預設）| **0.12s（≈硬切）** | 只允許 `fade`/`dissolve`；slide/wipe/circle **自動收斂為 fade** | 劇情、敘事、散文、情感、紀錄 |
| `mv` | 0.40s | **尊重**每段 `transition`（slide/wipe/circle/radial…節奏感）| 主題片、MV、旅遊 reel、宣傳 |
| `promo` | 0.30s | 同 mv（介於兩者）| 短促宣傳 |

- `effects.transition: "cut"`（硬切）→ 以 fade 呈現（narrative 的 xfade 已極短，視覺等同硬切）。
- CLI `--style` / `--xfade` 可覆寫 script 內宣告。
- 實作：`STYLE_XFADE` / `resolve_transition()` / `build_filter_chain(durations=...)`（`video_pipeline.py`）。
- 經驗：夜市散文 = `narrative`（克制）；城市/旅遊 reel = `mv`（華麗）。

### 逐段混風格（前敘事→中 MV→後敘事）

`style` 可放單一 segment 覆寫全片：**每個邊界用「切入段」的 style 決定 xfade 時長 + 轉場型**。
關鍵性質：xfade 的 offset 只跟前段 TTS 累加有關、**與時長無關**，所以混不同時長不影響總長。
pipeline 統一以「最大邊界時長」渲染每段尾巴，concat 時各邊界取各自時長 → precompose gate 照過。
例：seg2 narrative(0.12 硬切) → seg5 mv(0.4 slideleft) → seg8 narrative(0.12 硬切)，無縫混剪。

## 轉場白名單（避黑幕坑）

`ALLOWED_TRANSITIONS`（`video_pipeline.py`）：fade / wipe{left,right,up,down} / slide{left,right,up,down} /
circle{open,close} / dissolve / smooth{left,right} / radial / diag{tl,tr,bl,br}。
**刻意排除 `fadeblack`/`fadewhite`**（會在轉場中間出現黑/白幕，與成片調性衝突）。未知值自動退回 `fade`。

---

## Pipeline 整合

```
render_segment（基底）→ apply_effects（grade → title_card）→ 段檔
                                                              ↓
                         build_filter_chain（每段 transition）→ xfade concat
```

- `apply_effects()` 在 `render_one` 內、每段渲染後自動跑（初次與 retry 都套）。
- 產物：`effects_log.json`（逐段 grade/title_card/transition_in 軌跡）。
- 規格保證：grade/title 不改時長與 1920x1080/30fps/bt709 → precompose gate 照過。

---

## 與其他 Skill 的銜接

### 上游
- **編劇 Skill**：在 script.json 填 `effects`（依每段情緒選 grade、決定哪段放字卡、要不要花俏轉場）。
- **剪輯師 Skill**：產出基底段檔（特效師在其上加工）。

### 下游
- **字幕師 / merge-final**：字幕在特效之後燒（字卡置中、字幕置底，不打架）。
- **VERIFY**：technical_quality 維度確認特效後規格仍合格。

---

## 已知注意事項
- 字卡與字幕可能在開場段同時出現（字卡置中、字幕 MarginV=90 置底，不重疊）；若嫌busy，可把字卡放在旁白較空的段。
- `fire` 調色較強，避免整片都用（會膩）；建議只在炭烤/火光段點綴。
- 轉場 duration 沿用 pipeline 的 `--xfade`（預設 0.4s）。
