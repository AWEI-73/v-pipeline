# Decision: D5 Chinese-First Sourcing & visual_desc Verification

Date: 2026-05-29
Status: verified
Scope: video_pipeline.py / content_qa.py / video_tools.py / run_with_ollama.sh / skills(writer,curator,verify) / nightmarket
Superpowers phase: execute
Supersedes: D2 approach A's "search_query must be English visual concept" premise

## SPEC

### Requirement
1. **中文優先搜尋**：D2 原本主張「Pexels 以英文索引，search_query 要寫英文視覺概念」。
   實測推翻——Pexels/Pixabay 帶 `zh-TW` locale 對中文命中良好（`胡椒餅`/`鐵板料理` 直接搜就有對的素材）。
   `search_query` 改成**中文核心關鍵字**（料理名／場景名，1–2 詞）。
2. **驗證用 visual_desc，不是 keyword、不是旁白**：VLM（qwen3-vl:4b）對「英文 prompt 模板塞中文
   keyword」判斷極差（連對的圖都判 no）；對「文學旁白」判斷則太苛/模糊。新增 `visual_desc`
   欄位——純畫面事實的中文描述——prepick gate 與 content_qa 都改用它，且用中文問句。
3. **4b-only retry**：8b retry 模型與 4b 同時常駐時在本機 100% HTTPError（VRAM 不足），
   retry gate 等於全盲。預設改用 4b。

### Why
- 4b 看圖能力沒問題（人工驗證：丟胡椒餅圖問「這張是什麼」，4b 精準答出「中式煎餅/餡餅、撒芝麻」）。
  失敗純粹是 prompt 把中文 token 塞進英文模板 → 跨語言橋接失敗。
- 三欄職責本來就該分開：search（找素材）/ visual_desc（驗證+補拍）/ text（配音）。

### Direction
- `search_query` = 中文關鍵字（1–2 詞最準；≥3 詞會稀釋，validate 發 warning）。
- 所有 VLM 判斷用中文問句比對 `visual_desc`（fallback：visual_desc → text → keyword）。
- 問法「這張圖適不適合當以下畫面描述的配圖？是/否/部分」對映 rubric。
- `_parse_yn`/`yn` 看懂中文 是/否/部分，且負面詞優先（修「不符合」被誤判 yes）。
- retry 模型預設 4b；`--vlm-model-retry` 仍可指定 8b（需自備 VRAM）。

---

## DO

### Files
- `video_pipeline.py`：新增 `_parse_yn`；`_vlm_check_one`/`prepick_vlm_filter`/`pick_or_load`/
  `repick_segment` 串接 `verify_desc`；retry 預設 4b。
- `content_qa.py`：`score_segment` 改 visual_desc 中文問句；`yn` 支援中文。
- `video_tools.py`：`validate` 中文 search_query 不再誤判 <2 詞 error，≥3 詞 warning（稀釋）。
- `run_with_ollama.sh`：移除 8b 預熱（retry 用 4b）；失敗也收尾。
- `skills/writer.md`、`skills/curator.md`、`skills/verify.md`：全面改中文優先 + 三欄分工。
- `nightmarket/script.json`：search_query 改中文、每段補 `visual_desc`、seg5/6/10 標 cultural_specificity。

---

## VERIFY

### nightmarket 真實 E2E（run5，4b、Chinese search、visual_desc）
- 逐段最終：seg2/3/7/8/9/11=100、seg1/seg10=60、**seg4/5/6=10（unfixable）**。
- content_alignment **68.2**，總分 90.5，輸出三段中文補拍指引後 **exit 0**（material gap warnings）。
- **零 HTTPError**（4b retry 正常運作）。
- seg3「鐵板料理」prepick 直接 `yes`（中文搜成功）；seg10「將散未散」abstract→photo fallback 救到 60。

### visual_desc 是誠實裁判（對照三版 content_alignment）
| 版本 | 驗證標的 | content_alignment | 問題 |
|---|---|---|---|
| run1 | keyword（英文）| 92.7 | 灌水：圖沾邊就 100 |
| run3 | 旁白（文學）| 56.4 | 過嚴：整句文學描述難全符 |
| **run5** | **visual_desc（畫面）** | **68.2** | **誠實：對題的給 100、不對題的給 10** |

### 殘留＝素材源問題（非機制問題）
seg4/5/6（藥燉排骨/胡椒餅/刈包）unfixable，因 Pexels **拆字/部分比對**：胡椒餅→胡椒粒、刈包→甜麵包。
屬 D2-C（更好的中文素材源 / 生成式），機制本身（驗證+路由+unfixable 指引）運作正確。

### 回歸
- `PYTHONPATH=. .venv/bin/pytest`（hermes-control-panel）：114 passed。
- `_parse_yn`/`yn` 9/9 case（含「不符合」負面詞）；`validate` 中文 query 0 error。

---

## Decision Notes

### Accepted because
- 中文搜尋實測可行且更自然；visual_desc 讓 4b 發揮（中文比對中文）。
- 三版對照證明 visual_desc 是三者中最誠實的對題訊號。
- 4b-only 消除 retry 的 100% HTTPError，retry 真正有效。

### Tradeoffs
- visual_desc 要寫稿者多寫一欄（純視覺描述）——但這欄同時也是學員補拍指引，一魚兩吃。
- 中文搜尋會拆字（胡椒餅→胡椒）——靠 visual_desc 驗證擋下 + cultural_specificity 路由 + unfixable 指引兜底。

### Open / Deferred
- D2-C：胡椒餅/刈包/藥燉排骨 這類台灣專有食物，Pexels 弱；需更好中文素材源或生成式（重要性低，邊界壓測）。
- D4：60 分這層（related-yes 非 primary）是否要再 repick 搏 primary。

---

## Git / Retrieval
- Related commit: `8afca43`（feat(verify): D5 Chinese-first sourcing + visual_desc verification）
- Search tags: decision-log, d5, chinese-first, visual-desc, verify-by-visual, parse-yn-chinese,
  4b-only-retry, content-alignment, three-field-split, search-query-chinese, unfixable-guidance
