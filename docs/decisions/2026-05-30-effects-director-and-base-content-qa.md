# Decision: Effects Director (特效師) + content_qa on Base Footage + 15-Segment Milestone

Date: 2026-05-30
Status: verified
Scope: video_tools.py / video_pipeline.py / skills/effects-director.md / nightmarket
Superpowers phase: execute

## SPEC

### Requirement
1. **特效師（effects-director）新角色**：把 Phase 8d「結訓特化」的美學工作收進一個專職 Skill +
   圖譜節點——色彩分級（情境調色）、開場/分段字卡、段間進階轉場。
2. **content_qa 改評「特效前的基底原片」**：特效跑完後，content_qa 若評成片（grade+字卡+字幕）
   會被美學調色干擾（dusk 把畫面變紅 → 跟 visual_desc「藍紫色天空」打架 → 誤判 10）。
3. **TOOLS 漂移修復**：pipeline 的 `run_tool` 一直呼叫工作區的**舊 video_tools.py 快照**，
   靜默吃掉 D3 字幕與特效。改指向 repo 副本（單一真相源）。
4. **15 段里程碑**：把 nightmarket 從 11 段擴到 15 段，驗證 pipeline 規模與特效多樣性。

### Why
- 4b 看圖能力足夠（D5 已證），但「驗內容」與「美學調色」是兩件事，不該混在同一張縮圖評分。
- 工作區/repo 雙副本是長期漂移源（handoff 一直在提醒「更新 snapshot」）——根治就是只留一份。

### Direction
- 新 `video_tools.py` 指令：`grade`（dusk/night/fire/warm/cool/neutral，eq+colorbalance）、
  `title-card`（drawtext 疊字，淡入→hold→淡出，可副標）。保留 1920x1080/30fps/bt709 與時長。
- `video_pipeline.py`：`apply_effects()`（render 後套 grade→title）；`build_filter_chain` 支援
  每段 xfade 轉場（安全白名單 `ALLOWED_TRANSITIONS`，排除 fadeblack 黑幕坑）；`effects_log.json`。
- `script.json` 每段選填 `effects: {grade, title_card, transition}`。
- content_qa thumbnails 改從 `materials/seg{n}.mp4`（基底）抽，非 final.mp4。
- `TOOLS`/`CONTENT_QA` 用 `__file__` 解析到 repo 自身副本。

---

## DO
- `video_tools.py`：`cmd_grade` + `cmd_title_card`（default size 96）+ argparse/dispatch。
- `video_pipeline.py`：`apply_effects`、`ALLOWED_TRANSITIONS`、`build_filter_chain(transitions)`、
  compose_and_qa 傳 transitions、`[9] thumbnails` 改抽基底、`effects_log.json`、TOOLS→repo。
- `skills/effects-director.md`：新角色契約（grade 預設表、轉場白名單、pipeline 整合、與各 Skill 銜接）。
- `nightmarket/script.json`：11→15 段（新增 炭烤串/珍珠奶茶/炸物/霓虹銀河），逐段 grade + 12 種轉場 + 開場字卡。

---

## VERIFY

### 單元
- grade + title-card 單獨渲染（截圖確認）：暖調燈籠 + 置中字卡，1920x1080/30 保留。
- `apply_effects` 經 pipeline `run_tool`（repo video_tools）成功；`build_filter_chain` 轉場/未知退 fade。
- 114 control-panel tests pass（每次改動後）。

### 15 段真實 E2E（nightmarket_e2e_15）
- 15 段、223s、score **93.0**、exit 0、precompose gate 15 段全過、零 HTTPError。
- content_alignment **76.7**（run5 68.2 → 11段含特效 63.6 → 15段 76.7，最誠實且最高）。
- **seg1 60→10→100**：base-thumbnail 修復生效，grade 不再污染內容評分。
- 新段命中：炭烤串 100、珍珠奶茶 100、霓虹銀河 100、炸物 60（鹹酥雞偏 local）。
- 只剩 seg4/5/6（藥燉排骨/胡椒餅/刈包）誠實 unfixable + 中文補拍指引（屬 D2-C 素材源，非機制）。
- 字卡/grade/12 種轉場/D3 字幕（首次真套）全部成片確認。

---

## Decision Notes

### Accepted because
- 特效師讓美學處理有專職契約與軌跡（effects_log），且 grade/title/transition 都不改時長規格。
- content_qa 評基底徹底解掉「美學 vs 對題」衝突——是這版 content_alignment 拉高的主因之一。
- TOOLS→repo 根治雙副本漂移（連帶讓 D3 字幕第一次真正生效）。

### Tradeoffs
- 每段多 1–2 次 ffmpeg pass（grade/title），整體渲染時間增加；但都是 fast filter，可接受。
- content_qa 評基底 = 不看字幕/特效；若未來想驗「字幕沒擋住主體」需另開維度。

### Open / Deferred（下一步候選）
- **特效作法寫進腳本**：effects 欄位可擴成「動畫配方」（如字卡進出動畫、kenburns 方向、轉場時長），讓配特效更精準。
- **片頭/片尾動畫**：開場 logo/標題動畫、結尾感謝名單，可能當獨立「片頭片尾」段或新 effect 類型。
- **換主題壓測**：用非夜市主題（科技/旅遊/結訓）驗證 pipeline 與特效泛化。

## Git / Retrieval
- Related commits: `6b191df`（effects-director + TOOLS fix）、`5910eb5`（content_qa base + 15-seg + title size）
- Search tags: decision-log, effects-director, 特效師, grade, color-grade, title-card, xfade-transitions,
  content-qa-base-footage, tools-drift-fix, 15-segment, effects-log, premium-aesthetics
