---
name: verify
description: VERIFY Skill。對成片做 5 維度自動評分（腳本覆蓋、時長吻合、字幕準確、音量合規、技術品質），輸出加權總分 + 失敗項的 fix_target 路由指示，讓上游 Skill 知道要修哪段。
---

# Verify Skill

> ## Continuous Verify / QA Contract(Node 12 — 不只終點,是貫穿控制閘)
> **VERIFY 是貫穿全流程的控制閘,尤其在「昂貴 render 之前」**,不只最後一站。
> `verify_result`:`status ∈ pass / warn / fail / blocked` + `findings`[層級/節點/原因/建議路由] + `next_route`。
> **兩層檢查(對齊兩層模型):** 機械檢查先跑(便宜、deterministic:規格/時長/字幕/音量/EDL trace/
> 必放有無/fallback 是否被靜默替換)→ **小模型 VLM(qwen3-vl 等,參數化後端非硬寫)只在
> 視覺/語意/主觀檢查 deterministic 解不了時觸發** → human 只在需判斷/identity-proof 核可/主觀驗收時 targeted。
> **AI editor(Node 11)≠ verify**:editor 提修法/編輯路由;**verify 給正式 pass/warn/fail/block 閘**。
> 鐵則:blocker 不可進 ready/approved/render;fallback 被靜默替換 → fail;timeline item 無 trace → fail。

VERIFY 是 pipeline 的終點品管站。  
**核心原則**：腳本是 ground truth，VERIFY 對照腳本檢查所有產出是否一致。  
不通過時不只說「失敗」，要明確指出**哪個 Skill 要修**（fix_target）。

---

## 工具位置

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

```bash
python3 video_tools.py verify \
  --script script.json \
  --timing tts_timing.json \
  --edit-log rough_cut_edit_log.json \
  --srt subtitles.srt \
  --video final.mp4 \
  [--threshold 80] [--out qa_report.json]
```

---

## 對應命令
* `[[cmd_verify]]` - 對成片做 5 維度評分，並輸出加權總分與 fix_target 路由指示。
* `[[cmd_validate]]` - 在影片生成前，對劇本 (script.json) 進行模糊消除與格式健全檢查。

---

## 5 個評分維度

| 維度 | 權重 | 來源 | 通過條件 |
|------|------|------|---------|
| script_coverage | 25% | script.json + edit_log | 每個 script segment 都有對應影片 |
| duration_fit | 25% | tts_timing + edit_log | 每段影片 vs TTS 差 < 300ms |
| subtitle_accuracy | 20% | script.json + srt | 字元重疊率 ≥ 90% |
| audio_levels | 15% | ffmpeg volumedetect | mean -25~-12dB, max ≤ -6dB |
| technical_quality | 15% | ffprobe | 1920x1080 @ 30fps + 有 audio/video stream |

### 加權公式
```
total_score = sum(dimension_score × weight)
pass = total_score >= threshold (預設 80)
```

### 第 6 維：content_alignment（VLM 內容對題，由 content_qa.py 注入）

技術 5 維只驗「格式對不對」，不驗「畫面對不對題」。`content_qa.py` 用 VLM（qwen3-vl:4b）
逐段對成片縮圖打分，注入 qa_report 成為 content_alignment 維度（預設權重 0.30，其餘 5 維等比縮放）。

**關鍵原則：驗證一律用中文，且比對 `visual_desc`（畫面描述），不是 keyword、不是旁白。**
- 4b 對「英文 prompt 模板裡塞中文 keyword」判斷很差（會把對的圖判成 no）；用**中文問句**才準。
- 比對標的用 `visual_desc`（純畫面事實），不要用 `text` 旁白（文學語氣，太苛/太模糊）。
- 問法是「這張圖適不適合當這段畫面描述的配圖？是/否/部分」，對映 primary/related → 分數。

**D1 嚴格逐段 gate**：任一段 content score < 60 即整體 fail（不靠平均稀釋），觸發該段 repick；
fix_target = `curator`（小編重挑素材）。

---

## fix_target 路由

每個維度若不及格（< 80），會標記要修哪個 Skill：

| 維度失敗 | fix_target | 該 Skill 要做什麼 |
|---------|-----------|------------------|
| script_coverage | editor | 剪輯師缺段，補 assemble 漏掉的 segment |
| duration_fit | editor | 剪輯師時長對不上，重新剪該段 |
| subtitle_accuracy | subtitle | 字幕師檔案有問題，重 srt |
| audio_levels | audio | 音控師音量爆/過小，重 mix-audio |
| technical_quality | editor | 解析度或 stream 缺，重 assemble + merge-final |

上層 orchestrator 讀 `qa_report.json.issues[].fix_target` 即可決定要重跑哪個 Skill。

---

## qa_report.json 範例

```json
{
  "video": "/workspace/final.mp4",
  "timestamp": "2026-05-24T23:03:20",
  "score": 98.5,
  "pass": true,
  "threshold": 80,
  "dimensions": {
    "script_coverage":   { "score": 100, "weight": 0.25, "note": "all segments present", "fix_target": null },
    "duration_fit":      { "score": 100, "weight": 0.25, "note": "4/4 segments within 300ms", "fix_target": null, "issues": [] },
    "subtitle_accuracy": { "score": 100, "weight": 0.20, "note": "overlap 320/320 chars (100.0%)", "fix_target": null },
    "audio_levels":      { "score":  90, "weight": 0.15, "note": "max -5.8dB 接近爆音", "fix_target": null, "mean_db": -22.3, "max_db": -5.8 },
    "technical_quality": { "score": 100, "weight": 0.15, "note": "streams OK, 1920x1080 30fps", "fix_target": null }
  },
  "issues": []
}
```

不通過時：
```json
{
  "score": 64,
  "pass": false,
  "issues": [
    { "dimension": "duration_fit", "segment": 2, "score": 50, "fix_target": "editor",
      "detail": "seg2 actual 23.8s vs tts 22.0s (1800ms diff)" }
  ]
}
```

---

## 各維度設計細節

### 1. script_coverage
- 比對 `script.json` 的 segment 數 vs `edit_log.json` 的 segment 數
- 缺一段就扣 100/N 分
- **fix_target = editor**（因為剪輯師沒輸出該段）

### 2. duration_fit
- 對每個 segment 算 `|edit_log.actual_sec - tts_timing.duration_sec|`
- 預設閾值 300ms（路線 A 對影片配旁白要求嚴）
- 超過閾值的段落會被列入 `issues`
- **fix_target = editor**（剪輯師沒剪準）

### 3. subtitle_accuracy
- 把 SRT 所有字幕文字串起來
- 跟 `script.json` 所有 text 串起來比對
- 用 Counter 算字元層級的多重集合交集（去標點/空白）
- 比率 = `overlap / len(script_clean)`
- < 90% → fix_target = subtitle

### 4. audio_levels
- 跑 `ffmpeg -af volumedetect` 取 mean/max dB
- 規則（依坑 #21 + 一般 broadcast 標準）：
  - max > -3 → 扣 30（爆音風險）
  - max > -6 → 扣 10（接近爆音）
  - mean < -30 → 扣 30（太小聲）
  - mean > -12 → 扣 20（偏大聲）
- < 80 → fix_target = audio

### 5. technical_quality
- 解析度必須 1920x1080
- 必須有 video + audio stream
- framerate 30fps ±1
- < 80 → fix_target = editor

---

## 已知限制與未實作

### 未實作（v1 不做）
- **黑幀偵測**：純黑畫面超過某秒數應該扣分，但本實作沒做
- **音訊斷點偵測**：concat 接縫的爆音（坑 #29），未實作自動偵測
- **多段 BGM 音量分段檢查**：依坑 #21，語音段 vs 純畫面段該不同 BGM 音量，本實作只看整體
- **字幕時長合理性**：太短（< 0.5s）或太長（> 6s）該扣，未實作

這些等到實際出問題再補。

### threshold 預設 80 的根據
- 5 個維度，4 個拿 100、1 個拿 80 → 加權 96
- 5 個維度，3 個拿 100、2 個拿 80 → 加權 92
- 5 個維度，2 個拿 100、3 個拿 80 → 加權 88
- 拿 80 = pipeline 出了實質問題但勉強能看，threshold 設這個強迫修

---

## 與其他 Skill 的銜接

### 上游（VERIFY 讀什麼）
- `編劇 Skill` → `script.json`
- `音控師 Skill` → `tts_timing.json`
- `字幕師 Skill` → `subtitles.srt`
- `剪輯師 Skill` → `rough_cut_edit_log.json` + `final.mp4`

### 下游（誰用 VERIFY 結果）
- **手動模式**：直接看 qa_report，自己決定要不要重跑
- **orchestrator 模式**：讀 `issues[].fix_target` 自動觸發重跑

---

## 實測結果（2026-05-24）

對 `v3_skill_final.mp4` 跑 verify：

| 維度 | 分數 | 備註 |
|------|------|------|
| script_coverage | 100 | 4/4 segments |
| duration_fit | 100 | 全部 < 300ms |
| subtitle_accuracy | 100 | 320/320 字元 |
| audio_levels | 90 | max -5.8dB（剛好踩到接近爆音閾值）|
| technical_quality | 100 | 1920x1080 30fps |
| **加權總分** | **98.5** | ✅ pass |

audio_levels 沒拿滿分提醒了實際的細節：第一支 SKILL 全自動成片就在 -5.8dB 邊緣，未來 BGM 音量再上調容易爆。這正是 VERIFY 該做的事——**沒事先警告，有事直接點名**。

---

## 對應的 vault 文件
- `projects/video-agent-pipeline/roadmap.md` Phase 4
- `projects/video-agent-pipeline/skill-interface-contracts.md` — qa_report.json 格式
- `projects/video-agent-pipeline/ffmpeg-pitfalls-reference.md` — #21（音量）/ #29（音訊斷點）
