---
title: Skill Interface Contracts
created: 2026-05-23
updated: 2026-05-23
type: reference
tags: [skill, interface, json, contract, pipeline]
sources: []
related:
  - [[roadmap]]
  - [[ffmpeg-pitfalls-reference]]
---

# Skill Interface Contracts

各 Skill 的 I/O 格式定義。這份文件是整條 pipeline 的邊界合約，任何 Skill 的 SKILL.md 都必須遵守這裡定義的格式。

---

## 資料流總覽

路線 A（text-driven）：音控師先跑，剪輯師依 TTS 時長剪素材。

```
主題/需求
  ↓
[編劇 Skill]
  ↓ script.json
[音控師 Skill]
  ↓ tts/ + tts_timing.json + final_audio.wav
[小編 Skill]
  ↓ material_manifest.json （素材選用，目標時長 = tts_timing 段落時長）
[剪輯師 Skill]
  ↓ rough_cut.mp4 + edit_log.json（影片時長 = TTS 時長）
[字幕師 Skill]
  ↓ subtitles.srt（時間軸對齊 tts_timing.json）
[最終組合（剪輯師 v2）]
  ↓ final_noQC.mp4（影片 + final_audio + subtitles）
[VERIFY Skill]
  ↓ qa_report.json
pass → final.mp4 / fail → 路由到 fix_target skill
```

---

## script.json（編劇輸出）

整條 pipeline 的源頭。所有後續 Skill 都以此為基準。

```json
[
  {
    "segment": 1,
    "title": "開頭",
    "function": "establish_background",
    "material_type": "b-roll_context",
    "fallback_tier": 2,
    "search_query": "artificial intelligence history evolution timeline",
    "duration_sec": 18,
    "text": "人工智慧從圖靈測試到深度學習，走過七十年演進歷程。",
    "style": "calm_informative"
  }
]
```

| 欄位 | 型別 | 說明 |
|------|------|------|
| `segment` | int | 段落序號，從 1 開始 |
| `title` | string | 段落標題（供 Agent 理解用） |
| `function` | string | 段落功能：`establish_background` / `introduce_problem` / `show_method` / `show_result` / `conclusion` |
| `material_type` | string | 期望素材類型：`b-roll_context` / `talking_head` / `screen_demo` / `animation` / `title_card` |
| `fallback_tier` | int 1–4 | 可接受的最低素材等級（1=最理想，4=純音效/字卡） |
| `search_query` | string | YouTube 搜尋關鍵字（英文效果較好） |
| `duration_sec` | int | **hint 而已**（路線 A）— 實際時長由 TTS 決定，此欄供編劇粗估 |
| `text` | string | 腳本文字，同時作為 TTS 輸入與字幕基準（路線 A 下這個是 ground truth） |
| `style` | string | 情緒/風格，供編劇與音控師參考 |

---

## material_manifest.json（小編輸出 → 剪輯師輸入）

**方案 A 決策（2026-05-24）**：小編全包「找對段落」（search / download / analyze），剪輯師只做檔案層級操作（cut / scale / concat）。

### 小編內部完整格式（含所有候選 + 評分）
```json
[
  {
    "segment": 1,
    "candidates": [
      {
        "source": "youtube",
        "url": "https://www.youtube.com/watch?v=XXXX",
        "title": "AI History Explained",
        "start": "00:01:20",
        "end": "00:01:38",
        "score": 0.82,
        "tier": 1,
        "match_reason": "transcript: 'turing test deep learning history'"
      },
      {
        "source": "materials/",
        "path": "materials/ai_evolution.mp4",
        "start": "00:00:05",
        "end": "00:00:23",
        "score": 0.65,
        "tier": 2,
        "match_reason": "filename + whisper: 'artificial intelligence'"
      }
    ],
    "selected": 0,
    "fallback": null
  }
]
```

### 給剪輯師的精簡版（clip_list.json）
```json
{
  "segments": [
    {
      "segment": 1,
      "file": "/workspace/materials/seg1_raw.mp4",
      "cut_start_sec": 95.0,
      "cut_end_sec": null,
      "metadata": {
        "url": "https://...",
        "title": "Dartmouth Conference",
        "tier": 1
      }
    }
  ]
}
```

**剪輯師讀此檔的規則**：
- `cut_start_sec` 不給 → 從 0 開始剪
- `cut_end_sec` 不給 → 剪到 `cut_start_sec + tts_timing[segment].duration_sec`
- 兩個都給 → 用給的（精剪模式）

| 欄位 | 說明 |
|------|------|
| `candidates` | 候選素材列表，依 score 降序排列 |
| `source` | `youtube` / `materials/` / `generated` |
| `score` | 0–1，綜合評分（關鍵字重疊 × 時長契合） |
| `tier` | 1=直接對應 / 2=類似情境 / 3=補洞 / 4=情緒承接 |
| `selected` | candidates 陣列的 index，剪輯師用這個 |
| `fallback` | 若 score 過低：`gencard`（生成字卡）/ `null` |

---

## edit_log.json（剪輯師 v1 輸出）

```json
{
  "output": "rough_cut.mp4",
  "total_duration_sec": 76.4,
  "segments": [
    {
      "segment": 1,
      "source_file": "seg1_download.mp4",
      "cut_start": "00:01:20",
      "cut_end": "00:01:38",
      "actual_duration_sec": 18.0,
      "resolution": "1920x1080",
      "has_audio": true
    }
  ]
}
```

---

## tts_timing.json（音控師輸出）

字幕師的直接輸入，定義每個 segment 的 TTS 實際時間軸。

```json
{
  "voice": "zh-TW-HsiaoChenNeural",
  "segments": [
    {
      "segment": 1,
      "audio_file": "tts/seg1.mp3",
      "duration_sec": 6.4,
      "words": [
        { "word": "人工智慧", "start_ms": 0,    "end_ms": 680  },
        { "word": "從",       "start_ms": 680,  "end_ms": 820  },
        { "word": "圖靈測試", "start_ms": 820,  "end_ms": 1540 }
      ]
    }
  ]
}
```

---

## subtitles.srt（字幕師輸出）

標準 SRT 格式，時間軸對齊 tts_timing.json，句子切分點必須在標點後。

```
1
00:00:00,000 --> 00:00:03,200
人工智慧從圖靈測試到深度學習，

2
00:00:03,200 --> 00:00:06,400
走過七十年的演進歷程。
```

---

## pipeline_state.json（監控用）

Dashboard 讀取，各 Skill 執行前後寫入。

```json
{
  "project": "ai_intro",
  "updated": "2026-05-23T14:30:00",
  "nodes": {
    "writer":   { "status": "done",    "ts": "14:10", "summary": "4 segments, 76s total" },
    "curator":  { "status": "running", "ts": "14:22", "summary": "searching seg 2/4" },
    "editor":   { "status": "pending", "ts": null,    "summary": null },
    "audio":    { "status": "pending", "ts": null,    "summary": null },
    "subtitle": { "status": "pending", "ts": null,    "summary": null },
    "verify":   { "status": "pending", "ts": null,    "summary": null }
  },
  "verify_score": null
}
```

`status` 值：`pending` / `running` / `done` / `error`

---

## qa_report.json（VERIFY 輸出）

```json
{
  "project": "ai_intro",
  "timestamp": "2026-05-23T15:10:00",
  "score": 74,
  "pass": false,
  "threshold": 80,
  "dimensions": {
    "script_coverage":   { "score": 100, "weight": 0.25, "note": "all 4 segments present" },
    "duration_fit":      { "score": 60,  "weight": 0.25, "note": "seg2 off by 1.8s (> 0.5s threshold)" },
    "subtitle_accuracy": { "score": 95,  "weight": 0.20, "note": "" },
    "audio_levels":      { "score": 55,  "weight": 0.15, "note": "BGM at -8dB during speech in seg3" },
    "technical_quality": { "score": 80,  "weight": 0.15, "note": "resolution consistent, no black frames" }
  },
  "issues": [
    {
      "dimension": "duration_fit",
      "segment": 2,
      "detail": "expected 22s, got 23.8s",
      "fix_target": "editor",
      "fix_action": "re-cut segment 2 to match tts duration"
    },
    {
      "dimension": "audio_levels",
      "segment": 3,
      "detail": "BGM too loud during speech",
      "fix_target": "audio",
      "fix_action": "reduce BGM to 8-12% in speech segments"
    }
  ]
}
```

### 評分維度說明

| 維度 | 權重 | 計算方式 | 通過條件 |
|------|------|---------|---------|
| `script_coverage` | 25% | 有對應影片的 segment 數 / 總 segment 數 | 100% |
| `duration_fit` | 25% | 影片段落時長 ≈ TTS 時長（差值 < 0.3s）— 路線 A 下不再對照 script.duration_sec | 每段都在閾值內 |
| `subtitle_accuracy` | 20% | SRT 文字 vs script.text 的字元重疊率 | ≥ 90% |
| `audio_levels` | 15% | 語音段 BGM dB 是否在 -20dB 以下 | 全段合規 |
| `technical_quality` | 15% | 解析度一致、無黑幀、無音訊斷點 | 全過 |
