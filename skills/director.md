---
name: director
description: 導演 Skill。在編劇寫好「內容」之後，做「製作設計」決策——每段用什麼媒材型態（單鏡/蒙太奇/拼貼/相框）、整片與逐段的 style 弧線（narrative/mv/promo）、配樂 brief（mood 或 query→來源）、片頭片尾。產出的是 script.json 的「製作欄位」，不寫旁白文字、不執行特效/混音。
---

# Director Skill（導演）

> **前置(Node 0-1):動工前先讀 video-workflow 的 brief 欄位。** 若 `spec_start_mode`、
> `can_reshoot`、`fallback_policy` 缺,**停下來問清楚,不要自己發明**。導演吃 brief 參數決定
> 起手模式與缺口路由。segment 合約 schema 細節見 [spec-contract.md](spec-contract.md)
> (導演只管創作/故事權威:section role、story purpose、情緒弧、優先序、複核需求;不重抄整份 schema)。

編劇定「**講什麼**」（text / search_query / visual_desc）；導演定「**怎麼呈現**」。
兩者切在 script.json 的欄位上本來就分兩類——導演**只動製作欄位**：

```
style · media_pref · layout · effects.* · bgm · kind:title
```

**Skill 本身不呼叫 LLM**——你（agent）就是導演，這份是決策準則。
導演決策完，由**執行層**落地：小編找素材、特效師套調色/轉場/字卡、音控師混音。導演**不**做這些事本身。

> 邊界速記：編劇=文字真相；導演=製作設計；小編/特效師/音控師=執行。
> 想改旁白字句 → 回編劇；想換配色/轉場參數的「做法」→ 看特效師（[effects-director.md](effects-director.md)）；想改混音 → 音控師（[audio-director.md](audio-director.md)）。導演只下「要 dusk 調色、要 energetic 配樂」這種**意圖**。

---

## 導演擁有的製作欄位

| 欄位 | 值 | 決定什麼 |
|---|---|---|
| `style`（頂層 + 逐段）| `narrative` / `mv` / `promo` | 剪輯語言（轉場節奏）|
| `media_pref` | `photo` / `video` | 該段要動態影片還是照片（找不到 video 會自動退 photo+Ken Burns）|
| `layout` | （無）/ `montage` / `collage` / `framed` | 段內版面：單張 / 多張快切 / 多張拼貼 / 單張大相框 |
| `bgm` | mood 名 / `{query,source,max_dur}` / 檔案路徑 | 配樂 brief（見 §配樂）|
| `kind` | `title` | 片頭/片尾動態標題段 |
| `effects.kenburns` | `zoom-in`/`zoom-out`/`pan-left`/`pan-right` | 照片推鏡方向（覆寫預設交替）|
| `effects.transition` / `effects.transition_duration` | 轉場型 / 秒數 | 該段「切入」轉場（mv 段才需要；narrative 自動收斂硬切）|
| `source` | `stock`（預設）/ `local` / `generative` | 素材三源（`local` 需 `file`）|

---

## 決策 1：每段用什麼媒材型態（你問的「素材類型」）

依「這段畫面**本質上是什麼**」選，不要每段都預設單鏡 video：

| 這段的內容是… | 選 | 為什麼 |
|---|---|---|
| 單一主體、有動作（煎台翻面、爐火）| `media_pref: video` | 動態最有張力；找不到自動退 photo |
| 單一靜態主體、氛圍（黃昏燈籠、空鏡）| `media_pref: photo` + `effects.kenburns` | Ken Burns 慢推鏡，穩 |
| **多張相關鏡頭 / 群像 / 能量段**（學員大合照、活動花絮、MV 高潮）| `layout: montage` | 一段內多張快切輪播（照片牆），撐起節奏 |
| **展示多品項並列**（菜色一覽、作品集）| `layout: collage` + `effects.collage_n` | top-N 裝框拼貼於深色底 |
| **主打單品/單人特寫**（招牌料理、講者）| `layout: framed` | 單圖置中大相框於深色底，像卡片 |
| 開場/收尾標題 | `kind: title` | 動態字幕片段，跳過搜素材（見 §片頭片尾）|

口訣：**一個主體看動作→video；一個主體看氛圍→photo；多個鏡頭有能量→montage；多品項並列→collage；單一英雄→framed。**

> ⚠️ montage/collage 段現已納入 content QA（抽代表 frame），不再是品質盲區——所以你放這些版面時，素材仍要對題。

---

## 決策 2：style 弧線（整片 + 逐段混剪）

`style` 決定剪輯語言。包成 `{style, segments}` wrapper 宣告全片預設（純 list 也相容，預設 `narrative`）：

| `style` | 何時用 | 對轉場的影響（特效師執行）|
|---|---|---|
| `narrative`（預設）| 劇情、敘事、散文、情感、紀錄——**克制才高級** | 極短 xfade ≈ 硬切；華麗轉場自動收斂為 fade |
| `mv` | 主題片、MV、旅遊 reel、宣傳——**節奏華麗** | 正常 xfade，尊重每段 `effects.transition` |
| `promo` | 短促宣傳 | 介於兩者 |

判斷：**「要讓人入戲，還是讓人興奮？」** 入戲→narrative；興奮/炫→mv。

### 逐段混風格（導演的主力手法）

`style` 放在**單一 segment** 覆寫全片，做出「前敘事入戲 → 中段轉 MV 炫一波 → 結尾回敘事收束」——這正是你說的**故事+MV 混體**：

```json
{
  "style": "narrative",
  "segments": [
    {"segment": 1, "...": "..."},                                   // = narrative（硬切）
    {"segment": 5, "style": "mv", "layout": "montage",
     "effects": {"transition": "slideleft"}},                       // 切入 MV：蒙太奇 + 華麗轉場
    {"segment": 8, "style": "narrative", "...": "..."}              // 回敘事（硬切）
  ]
}
```

段落 `style` 決定該段「切入」的轉場時長與型；技術上每段切入點獨立，**總長不變**。
混剪的典型配方：**敘事段=單鏡/photo + calm 配樂 + 硬切；MV 段=montage + energetic 配樂 + 華麗轉場。**

---

## 決策 3：配樂 brief（音樂）

導演下**音樂意圖**，音控師執行 `mix-audio --duck`（人聲說話自動 sidechain 壓低）。`bgm` 三種寫法：

```jsonc
"bgm": "calm"                                          // ① 情境墊樂 placeholder（gen-bgm 合成，7 種 mood）
"bgm": {"query": "lofi calm piano instrumental",       // ② 真曲：music-fetch 抓
        "source": "yt", "max_dur": 240}
"bgm": "/path/to/track.mp3"                            // ③ 自備檔案
```

| 寫法 | 用途 | 注意 |
|---|---|---|
| mood 名（`calm/warm/emotional/energetic/tense/bright/night`）| 快速墊底、demo | 是 ffmpeg **合成的氛圍 placeholder**，不是真曲 |
| `{query, source}` | **真實配樂**（推薦正式片）| `source: yt`=yt-dlp 抽音訊（可運作）；`source: jamendo`=免版稅 API 接縫（需 client_id，未啟用）|
| 檔案路徑 | 完全掌控 | 最安全 |

mood ↔ style 對應建議：

| style / 段落情緒 | 建議 mood / query 方向 |
|---|---|
| narrative 敘事、情感 | `calm` / `emotional` / `warm`；query：`lofi piano`、`ambient calm` |
| mv 高潮、活動 | `energetic` / `bright`；query：`upbeat corporate`、`energetic background` |
| 夜色、懸念 | `night` / `tense` |

**版權現實**：`source: yt` 抓 YouTube = 著作權風險，**僅適合私用/學員片/你有授權的曲**。要公開發佈，走免版稅來源（Jamendo 等；Pixabay 沒有公開 music API，只有圖/影片，故不接）。
**抓不到不擋片**：music-fetch 失敗時 pipeline 靜音收尾、照常出片。

> 純音樂段（無旁白的 MV 段，`kind:"music"` 跳過 TTS、BGM 當主音軌）：**規劃中、尚未實作**。目前每段都會有 TTS 旁白。

---

## 決策 4：片頭/片尾（kind:title）

開場/收尾放 `kind:"title"` 段——動態標題片段，**不搜素材、不評 content_qa**，`text` 照跑 TTS 當配音並決定時長。寫法與動畫參數見特效師 [effects-director.md](effects-director.md) §片頭片尾。導演只決定「要不要片頭片尾、放什麼主標副標、什麼動畫感」。

---

## 導演工作流

1. 拿編劇的 script.json（已有 text/search_query/visual_desc/cultural_specificity/duration_sec）。
2. 定**全片 style**（入戲 or 興奮）。
3. 逐段定**媒材型態**（§決策1 口訣）——別全預設單鏡。
4. 標**混剪點**：哪幾段切 mv / montage（§決策2）。
5. 下**配樂 brief**（§決策3）：全片一條 `bgm`，或情緒轉折處逐段覆寫。
6. 需要的話加**片頭/片尾** `kind:title`。
7. 跑 `python3 video_tools.py validate <script.json>` 確認製作欄位合法（style/layout/bgm/transition 值都會檢查）。
8. 交給 pipeline / route——小編、特效師、音控師各自執行。

---

## MV 劇本 schema（v0，無旁白 beat 驅動）⟨2026-06-03⟩

結訓片＝MV。導演寫這份 `{style, music, segments}`，`mv_cut.validate_mv_script` 驗、`python3 mv_cut.py validate <script>` 跑。範例見 [examples/graduation_mv_script.json](../examples/graduation_mv_script.json)。

**頂層**：`style:"mv"`、`music:{brief,source,max_dur}`（導演出音樂方向→音控師抓，一首定 tempo）。

**段欄位**（統一段落模型的 MV 子集）：
| 欄位 | 值 | 用途 |
|---|---|---|
| `visual_desc` | 中文畫面描述 | **選段靶**（per-段評窗才有鑑別力）；除 `kind:title/music` 外必填 |
| `material_hint` | 資料夾名/路徑 | scoping：這段去哪個素材池找 |
| `kind` | opening/closing/title/montage/music | 段型；opening/closing=高權重 |
| `layout` | montage/collage/framed | 段內版面 |
| `pace` | fast/hold | 快剪 vs 長 hold |
| `must_include` | group/路徑任一層 | **必放守門**（必放凌駕分數）|
| `high_weight`/`needs_review` | bool | 前後/必放：拉高門檻 + 人工複核 |
| `hold` | bool | 不切，整段播（致詞/隊呼）|
| `keep_audio` | bool | 保留原音 |
| `audio_role` | music/duck/diegetic | 音訊角色：只音樂 / 原音+壓低音樂 / 原音為主 |
| `name_super` | {text,title} | 長官人名職稱下標 |
| `text` | 中文 | 旁白（可選；空＝純 MV）|

**核心**：結訓 MV ＝ 兩種段混合——**快剪 montage（layout:montage + audio_role:music）** & **長官隊呼長段（hold + keep_audio + audio_role:duck/diegetic + name_super）**。
**MVP 範圍**：以上為 v0；section_role/weight/chronological/credits 等實測後再擴。

## Editing Grammar / Timeline Rhythm（Node 7 — 導演的時間感權威）

> **導演意圖需要「時間規則」,不只段落描述。** 不准把每段壓成等速;hero/proof/開場/高潮/收尾
> 要顯式規則。schema(`editing_grammar` facet 欄位)見 [spec-contract.md](spec-contract.md);本節是創作判準。

**段落角色(role):** `hero`(主打/情緒高點)/ `proof`(成果證據)/ `support`(輔助)/ `bridge`(連接)/ `mood`(氛圍)/ `filler`(墊節奏,最低)。
**開場/高潮/收尾規則:**
- opening:前 3-8 秒要立住 identity/事件/情緒/hook。
- climax:**不可與普通 montage 平均化**;需要時保留 hold + 原音。
- closing:要收束情緒,給 breathing room,除非 brief 明確要突收。
**proof vs mood:** proof shot 觀眾要能看懂發生什麼 → 避免過快切/過重特效/不可讀文字/泛用替代;mood shot 可短、可節奏化、可風格化。
**compressibility:** `locked`(不可縮/丟/重排,需 review)/ `flexible`(min-max 內可縮)/ `expendable`(吃緊時先丟)。
> 鐵則:剪輯/timeline agent 可優化長度,但**不得靜默降級 hero/proof/identity 段或拿掉 breathing room** → 要 route 到 review。

## Node 3 翻譯：blueprint prose → segment_contract（soul 層，2026-06-08）

> **這是把「有靈魂的藍圖」變成「引擎讀得懂的 contract」的那一棒。** 上游 `blueprint-interview`
> 產出 `blueprint.md`(soul) + `blueprint.json`(index)；導演**讀 prose**，照
> `docs/imagery-to-edit-lexicon-spec.md`（意象→剪輯對照表）翻成 `segment_contract.json`。
> 翻譯是決定論的，不是再創作——你是字典的執行者，不是第二個編劇。

**鐵則（直接針對之前的失敗）：**

```
❌ 1 beat = 1 segment = 1 material_hint = 1 clip  ← 這就是幻燈片，禁止。
✅ 一個 beat 依 weight 與密度語感，展開成「一段多 shot_slots」或「拆成數個 segment」。
   重頭戲(weight 高、越切越快) → 多鏡；帶過的 → 少鏡。但每段都 >1 鏡，除非
   emotional/establishing 且有 still treatment 撐住。
```

**逐 beat 翻譯程序（照 lexicon 五欄）：**

1. 讀 beat 的 prose（不是讀 summary 標籤），抓出意象/節奏/聲音/情緒落點。
2. **情緒型態** → `editing_intent.content_pattern`（lexicon §1）；testimony/proof/identity 落 🔒。
   > **🔴 詞彙陷阱（ai-video soul-v3 實案教訓）**:`establishing`/`emotional` 解析成
   > **single_hold(整段一鏡)**。`develop`/中段敘事**不要**填 establishing——
   > 多鏡頭段落用 `process`/`enumeration`/`action`/`bridge`。
   > 自我檢查:若該段 `pacing.preferred_shot_sec=[4,8]` 而 pattern 解析成單鏡 treatment,
   > 就是自相矛盾——Node 9 會在 assembly_plan 標 `pacing_conflict: true` 並寫進
   > `treatment_reason`,看到它=回來改 content_pattern,不是改 pacing。
3. **結構** → `sequence_grammar.required_functions`（lexicon §2，例：action 段＝establish/action/detail/result）。
4. **節奏** → `pacing.preferred_shot_sec` + `visual_style.pace`（lexicon §3，密度語感→fast/[1.5,4]）。
5. **原音** → `audio.role` + `original_audio_policy`（lexicon §4，「他說/口令/現場聲」→keep）。
6. **文字/靜照/轉場** → `text_layer` / `material_treatment` / `transition`（lexicon §5/§5b）。
7. **篇幅** → 用 `blueprint.json.beats[].weight` 決定該 beat 的段數/總時長佔比與 shot_slots 數。
8. **追蹤閘** → 每個 segment 寫 `core.blueprint_ref`（指回 beat id）。
   - forward：每段都要指到真實 beat（否則 orphan_segment）。
   - backward：每個 beat 至少被一段實現（否則 dropped_beat = 阻擋）。
9. **範圍邊界** → 偵測到真特效語感（手寫動畫/粒子/雙畫面/PiP）→ 標 `effects_required`，
   route effects-director，誠實告知非自動可達（lexicon §6b）。

**走一遍（B5「現場實務」prose → contract）：**

prose：「爬桿、拖纜、高空換礙子，一張張快切疊上來——汗順著手套滴下、金屬撞擊、口令此起彼落，
配樂往上推；然後線接上的那一下，畫面停住安靜兩秒，只剩風。那兩秒就是驕傲。」(weight 2.0)

```json
{
  "segment": 5,
  "core": { "section_role": "turn", "story_purpose": "現場實務：快切堆疊後在接線那刻留白",
            "blueprint_ref": "B5_field_work", "review_required": true },
  "editing_intent": { "content_pattern": "action", "effects_intensity": "restrained" },
  "sequence_grammar": { "required_functions": ["establish","action","detail","action","detail","result"],
                        "exit_function": "bridge_to_next_chapter" },
  "pacing": { "preferred_shot_sec": [1.5, 4], "max_meaningful_shot_sec": 10,
              "allow_long_hold_when": ["story_payoff"] },
  "visual_style": { "pace": "fast", "transition": "beat_cut" },
  "audio": { "role": "diegetic", "original_audio_policy": "keep", "reason": "口令/金屬聲/現場" },
  "text_layer": { "label": "現場實務" },
  "material_treatment": { "treatment": "video_primary" }
}
```

weight 2.0 + fast → 這段 shot_slots 展開到 ~6 鏡（不是 1 支 clip）；result 配 long hold（「安靜兩秒」）。
每一格都指得回 prose 某個字＝忠實翻譯，零再創作。

> 此節與舊「MV 劇本 schema」相容並行：舊欄位(visual_desc/material_hint/layout/pace)是執行細節，
> 新增的 editing_intent/sequence_grammar/pacing/blueprint_ref 是 soul 層，由 lexicon 翻出。
> 引擎消費者：`material_treatment.resolve_treatment` + `shot_slots.expand_shot_slots`（已存在）。

**一步收斂（不用手刻整份 JSON）：** 翻譯的機械半邊已收斂成 compiler。導演只寫一份精簡的
逐 beat 判斷 `decisions.json`（每段 `content_pattern` + 關鍵畫面/節奏/audio/must_include），跑：

```powershell
python video_tools.py blueprint-to-contract blueprint.json decisions.json --out segment_contract.json
```

compiler（`video_pipeline_core/blueprint_to_contract.py`）自動補：lexicon 預設（functions/
pace 三檔 fast|calm|hold→preferred_shot_sec / treatment）、`editing_grammar.role` 擺在
**segment 層**（不放進 core，否則 weight 會被靜默丟掉）、honesty 守門、`blueprint_ref` 接線、
`timeline_source`/各 facet `reason`；並驗 `validate_segment_contract` + 雙向 beat 閘，
任一不過 exit≠0。範例見 `examples/blueprint_gold_66/{blueprint.json,decisions.json}`。

## 與其他 Skill 的銜接

- **上游**：編劇 [writer.md](writer.md)（內容欄位）。
- **執行下游**：小編 [curator.md](curator.md)（依 media_pref/layout/source 找素材）、特效師 [effects-director.md](effects-director.md)（套 style 轉場/調色/字卡/片頭尾）、音控師 [audio-director.md](audio-director.md)（依 bgm 混音 ducking）。
- **規劃 meta**：高層 architecture-first 流程見 [video-workflow.md](video-workflow.md)；導演是其中「製作設計」那一步的專職落地。
- 導演**不**自己挑單一素材、不調 ffmpeg 參數、不評分——那些是執行層與 VERIFY 的事。
