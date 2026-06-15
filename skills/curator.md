---
name: curator
description: 小編 Skill。搜尋 YouTube、下載素材、Whisper 轉譯找最匹配段、產出 clip_list.json 給剪輯師。包辦所有「內容理解」相關工作，剪輯師只負責檔案層級操作。
---

# Curator Skill

## Scene Review Shallow Labels

During ingest/caption review, record coarse visual-diversity labels on each
reviewed material-map scene:

- `visual_family`: project-defined coarse family, such as
  `outdoor_muster_wide`; do not use a global hardcoded family list.
- `angle_scale`: `wide | medium | close` when confidently visible.
- `action_family`: project-defined coarse repeated action, when applicable.
- `subject`: short project-local subject label, when applicable.

`media_type` is derived from the material map's existing `asset_type`; do not
duplicate it on each scene. These labels support later tier-2 visual-diversity
review. Missing labels mean `unreviewed`, not pass and not tier-1 failure.

For a project-level Agent review, write a separate verdict artifact and let the
deterministic tool apply it; do not mutate `project_material_map.json` by hand:

```json
{
  "artifact_role": "visual_diversity_review",
  "version": 1,
  "reviewer": "agent-or-human-id",
  "at": "caller-supplied timestamp",
  "scenes": [
    {
      "asset_id": "asset-a",
      "scene_index": 0,
      "visual_family": "project-local-family",
      "angle_scale": "wide",
      "action_family": "optional-project-local-action",
      "subject": "optional-project-local-subject"
    }
  ]
}
```

Apply it with `video_tools.py visual-diversity-review PROJECT_MAP --review
REVIEW.json --out REVIEWED_PROJECT_MAP.json`, then run
`visual-diversity-coverage`. Unknown/duplicate scene references and malformed
labels fail closed. One review can establish coverage but **cannot** satisfy the
independent-consistency prerequisite for VD2.

### Visual Family Vocabulary Contract (VD1.1)

To ensure different review Agents agree on `visual_family` tag granularity, establish a project-local vocabulary contract (`visual_family_vocabulary.json`) before checking review consistency:
1. **Project-Local Contract**: The vocabulary is a project-local contract that different Agents use to align their family definitions before review.
2. **Not Core Engine Words**: The vocabulary does NOT represent generic built-in genre vocabulary in the core video pipeline engine.
3. **Deterministic Mapping**: Normalization (via `python video_tools.py visual-family-normalize`) is a deterministic mapping of aliases to canonical families, NOT semantic or fuzzy understanding.
4. **VD2 Precondition**: VD2 soft-ranking remains blocked by default. The block can only be released after normalization and re-measuring consistency, where the visual family and angle scale consistency metrics pass.

> **Facet 擁有權(Node 3,見 [spec-contract.md](spec-contract.md)):小編消費 `material_fit` facet。**
> 欄位:`visual_desc` / `material_hint` / `required_traits` / `reject_traits` / `must_include` / `fallback_policy` / `reason`。
> 缺口路由(reshoot/generated/stock_bridge/text_bridge/…)見 Node 8 與 [gap-analyzer.md](gap-analyzer.md);**不靜默用泛用 stock 填 identity 缺口**。
>
> **Coverage 輸出(餵 Node 8 fallback 決策):** 小編只報「實際覆蓋」,不自己決定 fallback。
> ```yaml
> coverage:
>   status: covered | weak | missing | blocked
>   confidence:
>   evidence: {source_paths:, captions:, human_notes:}
>   missing_reason:
>   identity_sensitive:   # 真實人物/特定那群人 → true
>   proof_critical:       # 成果/證據性畫面 → true
>   suggested_routes:     # 參考,最終由 gap-analyzer/route 決定
>   review_required:
> ```

小編是 pipeline 裡唯一做「內容理解」的 Skill。
**方案 A 邊界（2026-05-24）**：小編包辦 search / download / Whisper analyze / 評分，剪輯師只剪檔案。

> **⚠️ 中文優先（2026-05-29 修訂，現行 Pexels/Pixabay 流程）**
> - **搜尋用中文 `search_query`**（料理名／場景名，1–2 詞，如『胡椒餅』『鐵板料理』）。
>   Pexels/Pixabay 後端帶 `zh-TW` locale，中文命中良好——**不要繞英文翻譯**（舊文件的「英文索引」說法已作廢）。
> - **VLM 驗證／評分一律用中文，且比對 `visual_desc`（畫面描述）**，不是 keyword、不是旁白。
>   4b 對「英文模板塞中文 keyword」判斷差；用中文問「這張圖適不適合當這段畫面描述的配圖」才準。
> - 以下 YouTube + Whisper 段落是舊路徑（仍保留參考）；現行 pipeline 走 `pexels-search` 直接抓 stock。
>
> **素材三源（2026-06-01 收斂）**：`clip_list.json` / material source contract 抽象不在乎來源，
> 段落 `source` 決定路徑——① `stock`（Pexels/Pixabay zh-TW，預設）
> ② `local`（學員自有檔，給 `file`，走 render_local）
> ③ `generated`（外部生成素材 provider 補 stock ceiling，優先 Antigravity / assistant_imagegen，核心 repo 只接成品）。
> `ingest-meta`/`rank-local` 是 local 源的批次整理工具。

> **🔴 search_query 撰寫規範(2026-06-10,ai-video 實案教訓)**
> stock 搜尋吃**具體物理場景的名詞**,抽象詞是 CG-bait——`hologram` / `abstract` /
> `data stream` / `digital network` 這類詞回傳的多是黑底發光線條的 3D 渲染動畫,
> 整段會黑壓壓,與「溫暖/真摯」類 tone 直接打架。規則:
> 1. **寫看得見的東西**:人、動作、場所、物件(`bright office team discussion`、
>    `hands typing laptop warm light`),不寫概念(`innovation`、`future technology`)。
> 2. **把 tone 塞進 query**:亮度/時段/情緒詞(`bright`、`warm`、`sunlit`、`golden hour`)
>    對 stock 庫有效,能直接過濾暗沉素材。
> 3. **抽象概念段落**先想「這個概念的物理代理畫面是什麼」再下 query;真的沒有物理代理
>    → 走 `generated`(交 generative-director),不要硬搜 stock。
> 4. 引擎已改為**相關性優先**(API 排序),時長只是資格門檻——但 query 歪了,
>    再好的排序也救不回來;query 品質是小編的責任。

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

四個指令：
```bash
# YouTube 模式（自動搜尋）
python3 video_tools.py analyze <video> --query "keywords" [--target-sec N] [--language en|zh]
python3 video_tools.py curate --script S --timing T [--workdir DIR] [--top-n N] [--out clip_list.json]

# 本地素材模式（學員上傳素材）
python3 video_tools.py ingest-meta <materials_dir> [--out materials_db.json]
python3 video_tools.py rank-local --db materials_db.json --needs material_needs.json [--out clip_list.json]
```

---

## 對應命令
* `[[cmd_analyze]]` - 小編：Whisper 轉譯影片，找最匹配關鍵字的時間窗口。
* `[[cmd_curate]]` - 小編全自動：對每段 script.json，執行搜尋、下載、轉譯分析並評分，最後產生 clip_list.json。
* `[[cmd_ingest_meta]]` - 掃本地素材庫，提取 metadata 並抽取 keyframe，產生 materials_db.json。
* `[[cmd_rank_local]]` - 用 vision_score 配對 material_needs，產出 clip_list.json。
* `[[cmd_pexels_search]]` - 搜尋 Pexels 素材庫的影片/照片。
* `[[cmd_pexels_download]]` - 下載 Pexels 素材。

---

## 流程

```
script.json + tts_timing.json
   │
   ▼
[curate]
   │
   ├─ 對每段：
   │   1. _search_candidates    YouTube ytsearch 10 個
   │   2. _filter_candidates    過濾 < 60s / > 600s / news / shorts / interview
   │   3. download              下載中段 max(180, target × 6) 秒
   │   4. _whisper_transcribe   faster-whisper base int8 CPU
   │   5. _find_best_window     滑動窗口 + 邊界保護
   │
   ▼
clip_list.json (給剪輯師)
```

---

## Material Source Contract

Curator 的長期輸出要收斂到同一個素材來源格式，讓 editor、route、dashboard 不需要知道來源細節：

```json
{
  "segment": 6,
  "source": "stock | local | generated",
  "provider": "pexels | pixabay | user_upload | antigravity | assistant_imagegen | codex_imagegen | gemini_veo | manual",
  "file": "/absolute/path/to/material",
  "status": "candidate | selected | rejected | needs_review",
  "score": 0.0,
  "visual_desc": "中文畫面描述，供 VLM QA 使用",
  "metadata": {}
}
```

### `stock`

```json
{
  "segment": 2,
  "source": "stock",
  "provider": "pexels",
  "file": "/tmp/run/materials/seg2_raw.mp4",
  "status": "selected",
  "score": 100.0,
  "visual_desc": "夜晚下雨的城市街道，路面反光，車燈與霓虹在雨水中閃爍",
  "metadata": {
    "query": "雨夜 街道",
    "asset_id": "pexels:12345"
  }
}
```

### `local`

```json
{
  "segment": 6,
  "source": "local",
  "provider": "user_upload",
  "file": "/home/user/student_uploads/seg6_user.mp4",
  "status": "selected",
  "score": null,
  "visual_desc": "雨後清晨的城市街道，天空微亮，地面仍有積水反光",
  "metadata": {
    "route": "await_material",
    "original_name": "seg6_user.mp4"
  }
}
```

### `generated`

```json
{
  "segment": 6,
  "source": "generated",
  "provider": "assistant_imagegen",
  "file": "/tmp/run/materials/generated/seg6.jpg",
  "status": "selected",
  "score": null,
  "visual_desc": "雨後清晨的城市街道，天空微亮，地面仍有積水反光",
  "metadata": {
    "prompt_file": "/tmp/run/materials/generated/seg6.json",
    "external_provider": true
  }
}
```

Generated provider 的實作不屬於 curator/route core。外部 Antigravity / assistant_imagegen / Codex 圖像 agent 只要交付標準檔案與 metadata，curator/route 就能把它當素材來源接回 pipeline。ComfyUI 目前 deprecated/disabled，不再當預設 provider。

---

## 指令 1：analyze

### 用法
```bash
python3 video_tools.py analyze /materials/seg2.mp4 \
  --query "large language model GPT" \
  --target-sec 24 \
  --language en
```

### 做什麼
1. Whisper 轉譯整段影片（faster-whisper `base` 模型，CPU + int8 量化）
2. 對 transcript 的每個 segment 算 keyword overlap（去停用詞後做集合交集）
3. 用滑動窗口找累積分數最高的 `target_sec` 區間
4. **邊界保護**：best_start 不會超過 `total_dur - target_sec`，避免下游剪不到完整段

### 輸出
```json
{
  "best_start_sec": 12.3,
  "best_end_sec": 30.85,
  "score": 7,
  "excerpt": "Let's now talk about how large language models...",
  "cache_path": ".transcripts/seg2.mp4.json"
}
```

### Cache 機制
- 轉譯結果存到 `dirname(video)/.transcripts/{basename}.json`
- 第二次跑同一支影片直接讀 cache，幾乎瞬間返回
- 在迭代調 query 或測試 pipeline 時非常省時

---

## 指令 2：curate

### 用法
```bash
python3 video_tools.py curate \
  --script /workspace/script.json \
  --timing /workspace/audio_out/tts_timing.json \
  --workdir /workspace/materials \
  --top-n 1 \
  --out /workspace/clip_list.json
```

### 參數
- `--top-n`：每段下載並分析 N 個候選，取分數最高者。預設 1（最快）。設 3 可提升品質但 Whisper 跑 3 倍時間。
- `--workdir`：素材與 transcript cache 都放這

### 輸出 clip_list.json
```json
{
  "segments": [
    {
      "segment": 1,
      "file": "/workspace/materials/seg1_VIDEO_ID.mp4",
      "cut_start_sec": 12.3,
      "cut_end_sec": 30.85,
      "metadata": {
        "url": "https://www.youtube.com/watch?v=...",
        "title": "Dartmouth Conference - The Birthplace of A.I.",
        "score": 7,
        "excerpt": "..."
      }
    }
  ]
}
```

---

## 已修的兩個重要 bug（2026-05-25）

### Bug 1：`_find_best_window` 沒做邊界保護
**症狀**：Whisper 找到的 best_start 太靠後，導致 `best_start + target_sec` 超出素材長度，剪輯師剪出來的段比 TTS 短。
**後果**：VERIFY 的 duration_fit 維度扣分（diff > 300ms 就 fail）。
**修法**：計算 `max_start = total_dur - target_sec`，跳過任何 anchor.start > max_start 的 segment。
**實測**：Seg 3 從 -1352ms 漂移 → 0ms。

### Bug 2：curate 下載長度固定 90s 太短
**症狀**：素材只下 90s，若 Whisper 在後段找到匹配（如 64s），加上 target 27s 就 > 90s 邊界。
**修法**：下載長度改成 `max(180, target_sec × 6)`，給 Whisper 更大選擇空間。
**實測**：Seg 3 Whisper 從 64.4s 選到 127.6s（更精準的內容匹配，且不破壞邊界）。

---

---

## 本地素材模式（學員上傳）

YouTube 模式是「找不到對的素材」的 fallback。
真正的結訓影片場景：學員按 `shooting_brief.md` 拍，上傳到 `/materials/`，由本模式處理。

### 流程

```
shooting_brief.md  ──► 學員拍攝 / 上傳 / 你人工過濾
                              │
                              ▼
                    /materials/67th/{班別}/...
                              │
                              ▼
                  [ingest-meta]   掃資料夾 → materials_db.json
                              │
                              ▼
                  [agent vision]  agent 看 keyframe + needs → 填 vision_score
                              │
                              ▼
                  [rank-local]    score 配對 needs → clip_list.json
                              │
                              ▼
                  剪輯師 assemble + merge-final
```

### 指令 3：ingest-meta

```bash
python3 video_tools.py ingest-meta /materials/67th/ \
  --out /materials/67th/materials_db.json
```

做的事：
1. 掃資料夾（遞迴），辨識照片（jpg/png/heic/heif）與影片（mp4/mov/m4v/avi/mkv）
2. **HEIC 自動轉 JPG**（pillow-heif，原檔留著）
3. 照片：讀 EXIF（datetime / camera / 解析度 / GPS 存在與否）
4. 影片：ffprobe metadata + 抽 3 張 keyframe（20%/50%/80% 處）
5. 把資料夾路徑當 tags（例如 `配三班` 自動標記）
6. 輸出 materials_db.json，含每個檔案的 metadata + keyframes 路徑 + `vision_score: null`

**vision_score 留空，等下一步 agent 看圖填**。

### 指令 4：agent 看圖打分（內建在 hermes / 不需外部 API）

這步**沒有對應的 CLI 指令**——agent 自己讀 materials_db.json 與 material_needs.json，逐個檔案看 keyframe 或照片，填入 `vision_score`。

**評分準則**：對每個 need.id，0-10 分：
- 9-10：完美對應該 need 的 type 與 purpose
- 7-8：符合但稍偏（例如 need 要清晨體能，素材是傍晚體能）
- 5-6：勉強可用（fallback tier 2-3 可接受）
- 1-4：勉強有關但建議跳過
- 0：完全不對

**vision_score 結構**：
```json
"vision_score": {
  "description": "簡短描述畫面內容（≤80 字）",
  "best_need": "2.3",
  "by_need": {
    "1.1": 0, "1.2": 0, "2.3": 9, "2.5": 7, ...   各 need 的 0-10 分
  },
  "quality_flags": ["high_quality", "action_shot", "no_text_overlay"]
}
```

**quality_flags 可用標籤**：
- `high_quality` / `low_quality` — 整體可用度
- `action_shot` / `static_shot` — 有沒有動作
- `close_up` / `group_shot` / `wide_shot` — 鏡頭距離
- `has_text_overlay` — 有畫面字幕（剪輯可能要避開）
- `talking_head` — 純人講話特寫
- `no_people` / `with_people`
- `outdoor` / `indoor`
- `bright` / `dark`

### 指令 5：rank-local

```bash
python3 video_tools.py rank-local \
  --db materials_db.json \
  --needs material_needs_66th.json \
  --out clip_list.json
```

做的事：
1. 讀 materials_db（必須含 vision_score）
2. 把 material_needs 攤平排序：**must_have 優先，再依 fallback_tier 1 → 4**
3. 對每個 need 找最高分材料（門檻 ≥ 5）
4. 已用過的材料不重複分配（除非該照片明確標記可多用）
5. 輸出 clip_list.json，含每 need 對應的 picks + 缺口列表

### 不匹配的處理

`rank-local` 會誠實標出：
- `matched`: 成功配對的 need 數
- `unmatched`: 沒有合格材料的 need 數
- `must_have_missing`: 沒配到且為 must-have 的（**會擋下游**）

範例（demo 測過）：
```json
{"matched": 0, "unmatched": 17, "must_have_missing": 15}
```
→ 表示「素材幾乎完全不對主題」，要回頭請學員補拍或修改 material_needs。

---

## 已知限制

### 1. 評分粗（keyword overlap）
目前只算英文 stem 的集合交集，沒做：
- TF-IDF（沒做 corpus 統計）
- Semantic similarity（沒用 embedding）
- Phrase matching（"large language model" 應該整片組合更值錢）

**未來改進**：用 sentence-transformers 算 embedding cosine 相似度，或 BM25。

### 2. 沒過濾 talking head
標題過濾只擋了「interview / podcast」這類關鍵字，但很多 talking-head 影片標題不含這些詞。
**症狀**：可能選到「人臉特寫不換鏡頭」的段落（v2 測試的 Seg 3 案例）。
**未來改進**：下載後做 frame sampling + 簡單畫面變化偵測，動態太低的窗口扣分。

### 3. 沒過濾自帶字幕/CG 標題
新聞素材常有跑馬燈、台標、字幕條，跟我們燒的中文字幕打架（v1 軍事素材測試的問題）。
**未來改進**：sample 數幀 + OCR 偵測畫面文字，文字密度過高扣分。

### 4. Whisper 中文表現
- query 多為英文 → 沒問題
- 但若素材有中文配音，`base` 模型轉譯品質差（坑 #3：base 中文準度差）
- 若要做中文素材庫，需切到 `medium` 模型（慢約 3 倍）

---

## 與其他 Skill 的銜接

### 上游
- **編劇 Skill**：產 `script.json`，每段含 `search_query`
- **音控師 Skill**：產 `tts_timing.json`，提供每段 target 時長

### 下游
- **剪輯師 Skill**：吃 `clip_list.json`，照 `cut_start_sec` / `cut_end_sec` 剪
- **VERIFY Skill**：透過 `duration_fit` 維度驗證剪輯師是否剪準（間接驗證小編產出對不對）

---

## 實測結果（2026-05-25）

對 ai_script_v2（89.5s 4 段）跑全自動 curate：

| Seg | search_query | 選中 | Whisper start | score |
|-----|-------------|------|--------------|-------|
| 1 | artificial intelligence history 1956 Dartmouth | Dartmouth Conference | 12.3s | 2 |
| 2 | large language model GPT explained | How Large Language Models Work | 0.0s | 3 |
| 3 | AI applications healthcare medical imaging | How AI is Revolutionizing Medicine | 127.6s | 7 |
| 4 | future artificial general intelligence AGI | AI2027 BBC | 17.7s | 1 |

下游 VERIFY 結果：**98.5 分**（跟手寫 clip_list 同分），duration_fit 100。
首支「100% 由正式 Skill 全自動產出（含 search / download / 內容理解）」的影片：`workspace/v4_auto_final.mp4`。

---

## 對應的 vault 文件
- `projects/video-agent-pipeline/roadmap.md` Phase 5
- `projects/video-agent-pipeline/skill-interface-contracts.md` — clip_list.json 格式
- `projects/video-agent-pipeline/tool-verification-log.md` — faster-whisper 驗證
- `projects/video-agent-pipeline/ffmpeg-pitfalls-reference.md` — #3（Whisper 模型選擇）
