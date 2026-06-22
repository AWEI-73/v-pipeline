# Decision: D2 Chinese-Aware Material Sourcing & D3 Rubric + Subtitle Aesthetics

Date: 2026-05-29
Status: verified
Scope: skills/writer.md / video_tools.py / video_pipeline.py / content_qa.py
Superpowers phase: execute

## SPEC

### Requirement

**D2 — 中文劇本對應英文 stock 庫的素材策略（approach A）**
中文旁白沒問題，但素材搜尋打 Pexels/Pixabay（英文索引）時，中文 `search_query`
（如 `胡椒餅 炭烤 夜市`）命中率極低，字面翻譯也一樣 miss。要把「寫稿語言」與
「搜尋查詢生成」拆開：寫稿中文優先，查詢改成英文**視覺概念**（場景/動作/物件），
並對「在地/抽象」主題標記，讓 pipeline 別硬搜西方 stock。

**D3 — 評分準則修訂 + 字幕美學升級**
content_qa 的 primary/related → 分數對應太粗，且 `unknown`(30) 竟高於明確 `no`(10)，
等於獎勵 VLM 雜訊。字幕樣式（描邊白字）偏陽春，結訓影片要更有質感。

### Why

- 西方 stock 庫以英文索引，用中文搜永遠輸；正解是「中文意圖 → 英文視覺概念」，
  而非字面翻譯（`胡椒餅` → `grilled flatbread clay oven street food`）。
- seg5「胡椒餅 炭烤」屬可救（stock 有近似視覺）；seg10「將散未散」屬抽象 Stock Ceiling
  （任何語言都無對應），兩者要靠 `cultural_specificity` 區分路由。
- 評分把模糊輸出排在明確否定之上是邏輯瑕疵；模糊應保守給低分。

### Direction

- `search_query` 契約升級為英文視覺概念；新增 `query_zh`（中文意圖）、
  `cultural_specificity`（universal / local / abstract）欄位。
- `validate` 對含中文的 `search_query` 發 warning（不阻塞）。
- `_simplify_query` 對中文 query 改用 whitespace token / 字元 bigram 退化，不再產生亂切。
- 重試迴圈：`local`/`abstract` 段落跳過西方 video stock 重挑，直接走 photo fallback（接 D1）。
- content_qa 評分抽成純函式 `rubric_score(primary, related)`；新增 `primary=somewhat→75`，
  `unknown` 由 30 降到 15（門檻仍 60，pass 路徑不放寬）。
- 字幕：加粗、字級 36→38、加 50% 半透明黑投影（BackColour `&H80000000`+Shadow 1.5）、
  描邊 3→2、MarginV 80→90、Spacing 0.5。merge-final 與 burnsub 一致。

---

## DO

### Files / modules

- `skills/writer.md`：欄位表新增 media_pref/query_zh/cultural_specificity；
  「search_query 要英文視覺概念」整節改寫（含中→視覺概念對照表與 2b 在地/抽象節）；
  寫作流程 step 3c/3d、validate 檢查項目補 CJK warning。
- `video_tools.py`：`cmd_validate` 加 CJK `search_query` warning；
  `cmd_merge_final` 與 `cmd_burnsub` force_style 升級。
- `video_pipeline.py`：新增 `_has_cjk()`；`_simplify_query` CJK-safe；
  `pick_or_load` 候選 metadata 帶 `cultural_specificity`；
  retry loop 加 `skip_video` 短路（local/abstract → 直接 photo fallback）。
- `content_qa.py`：抽出 `rubric_score()` 純函式並精煉映射。

---

## VERIFY

### 單元 / 行為驗證
- 三檔 `ast.parse` 全 OK。
- `_simplify_query`：
  * 英文不變：`"sizzling griddle street food fire flame cooking close up"`
    → `['cooking close up', 'sizzling griddle']`
  * 中文含空白：`"胡椒餅 炭烤 夜市"` → `['胡椒餅','炭烤','夜市']`
  * 中文無空白：`"胡椒餅炭烤夜市"` → `['胡椒','夜市']`（字元 bigram）
- `validate nightmarket/script.json` → status=warning，seg5/seg6 中文 query 各發一條 warning。
- `rubric_score`：yes/no=100、somewhat/yes=75、no/yes=60、no/somewhat=40、no/no=10、
  unknown/unknown=15；斷言 `unknown>=no` 且不再高於 somewhat。

### 字幕美學（實渲）
- 用 nightmarket `polished_visual.mp4` + `subtitles.srt` 跑 ffmpeg force_style 抽幀
  `/tmp/d3_subtitle_proof.jpg`：RENDER_OK，加粗白字 + 柔和投影，在燈籠雜亂背景上清晰可讀。

### 回歸
- `PYTHONPATH=. .venv/bin/pytest`（hermes-control-panel）：**114 passed**，零回歸。

---

## Decision Notes

### Accepted because
- approach A（契約 + 程式健壯化）投報率最高，直接修 seg5 類中文 miss，無需在 pipeline 內接 LLM。
- `rubric_score` 抽純函式 → 可被單元測試，並修掉 unknown>no 的邏輯瑕疵。
- 字幕投影是低風險、視覺上明確的質感提升。

### Tradeoffs
- D2 仍依賴**寫稿者（agent）**把中文意圖轉成英文視覺概念；尚未做 pipeline 內自動 zh→en
  視覺翻譯（approach B，deferred）。
- `cultural_specificity` 為選填，舊腳本無此欄位 → 預設 `universal`，行為不變（向後相容）。
- rubric 新增 `primary=somewhat→75` 會讓「主體大致出現」的邊界段落 pass；視為合理放行而非放寬門檻。

### Open questions / Deferred
- D2 approach B：pipeline 內用 Ollama 自動把 `query_zh` 轉英文視覺概念。
- D2 approach C：接中文索引素材源（攝圖網/包圖，需付費 API）。
- D3 其餘美學：title-card 字卡、BGM 情境庫、蒙太奇快切、轉場特效（避 xfade 黑幕）。

---

## Git / Retrieval

### Related files
- `skills/writer.md`, `video_tools.py` (`cmd_validate`/`cmd_merge_final`/`cmd_burnsub`),
  `video_pipeline.py` (`_has_cjk`/`_simplify_query`/`pick_or_load`/retry loop),
  `content_qa.py` (`rubric_score`)

### Graphify anchors
- Community 5：`seg5 烤爐火紅 (Chinese-query miss)`、`seg10 將散未散 (stock ceiling)`、
  `D2 — 中文劇本 + 中文素材`、`P2-1 Multi-source`
- 接續 Hyperedge「D1 single-segment gate + photo fallback routing」（cultural_specificity → photo fallback）

### Search tags
decision-log, d2, d3, chinese-sourcing, visual-concept-query, query-zh, cultural-specificity,
simplify-query-cjk, validate-cjk-warning, rubric-score, content-qa, subtitle-aesthetics, force-style, ken-burns
