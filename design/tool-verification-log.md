---
title: Tool Verification Log
created: 2026-05-24
updated: 2026-05-24
type: reference
tags: [verification, tools, test, log]
sources:
  - /tmp/tts_test/ verification scripts
related:
  - [[roadmap]]
  - [[skill-interface-contracts]]
---

# Tool Verification Log

每個外部工具在採用前的實測紀錄。星星數高 ≠ 在這個環境能跑，必須實測。

---

## 2026-05-24 | edge-tts + 切句方案

### 工具
- `edge-tts` 7.2.8（pip install）⭐11k
- Python stdlib（re, asyncio）
- ffmpeg 靜態 binary（已安裝）

### 驗證項目

#### Test 1：單句切句 → TTS → SRT
**腳本**：`/tmp/tts_test/test_subtitle_pipeline.py`

```
原始: 人工智慧從圖靈測試到深度學習，走過七十年的演進歷程。

切句結果（按「，。」切）:
  人工智慧從圖靈測試到深度學習，
  走過七十年的演進歷程。

TTS 時長:
  phrase_1: 4.056s
  phrase_2: 2.952s
  累加:    7.008s
  合併後實際: 7.008s
  差距:     0.0ms  ✅
```

#### Test 2：完整 4 段腳本（ai_script.json）
**腳本**：`/tmp/tts_test/test_full_script.py`

```
Seg  Target  Actual    Diff
1    18s     7.01s    -10.99s
2    22s     7.13s    -14.87s
3    20s     7.08s    -12.92s
4    16s     6.70s     -9.30s
TOTAL 76s    27.91s   -48.09s

合併音訊 vs 累加 cursor: 0.0ms 差距 ✅
```

#### Test 3：SRT 燒進影片
```
ffmpeg + WQY Microhei 字型 burnsub:
  輸出: 28.3s, H264+AAC, 526KB
  字幕渲染: ✅
```

### 結論

| 項目 | 狀態 |
|------|------|
| edge-tts 可在 WSL 跑 | ✅ |
| zh-TW 三個聲音都可用 | ✅（HsiaoChen / HsiaoYu / YunJhe）|
| 中文 word-level timing | ❌ 沒有（Microsoft 限制）|
| 按標點切句方案 | ✅ 零誤差 |
| ffmpeg burnsub 整合 | ✅ |

### 副發現（重要）
**現有 ai_script.json 的 text 字數不足以撐 duration_sec**：
- 平均要 4 字/秒（中文 TTS 速度）
- 18 秒應有 ~72 字，實際只有 19 字
- 4 段腳本總長度應 ~304 字，實際只有 73 字 → 影片只能撐 27.9 秒（vs 設計 76 秒）

**對 Roadmap 的影響**：
- 編劇 Skill 必須加「字數 vs duration_sec」合理性驗證
- 或改成 text-driven 設計（影片配旁白，duration_sec 為建議）

---

## 2026-05-24 | stable-ts（備援，未進主流程）

### 工具
- `stable-ts` 2.19.1（pip install --break-system-packages）⭐2.3k
- 整合：`load_faster_whisper('tiny', device='cpu', compute_type='int8')`

### 驗證項目

```python
import stable_whisper
model = stable_whisper.load_faster_whisper('tiny', device='cpu', compute_type='int8')
result = model.transcribe('/tmp/test_tts.mp3', language='zh')
for seg in result.segments:
    for word in seg.words:
        print(word.word, word.start, word.end)
```

### 結論
- ✅ CPU mode 可動（要設 `device='cpu', compute_type='int8'`，否則找 libcublas.so.12 失敗）
- ✅ 中文每個字都有獨立 timestamp
- ⚠️ `tiny` 模型轉譯準確度太差（「圖靈測試」→「徒林測試」）
- ⚠️ 主流程不需要它（切句方案已零誤差）
- 📌 保留作 VERIFY Skill 的選用驗證工具

---

## 2026-05-24 | 已排除的工具

### WhisperX（22k⭐）
- ❌ 排除原因：中文 word-level alignment 模型未明確支援
- 文件提到的 alignment model 預設只有 `{en, fr, de, es, it}`
- 中文需自行找 wav2vec2 alignment 模型，風險高

### Piper TTS（11k⭐，原 rhasspy/piper）
- ❌ 排除原因：repo 已封存（2025-10）
- 接手版本 OHF-Voice/piper1-gpl ⭐4.2k 正在找維護者
- 中文聲音資源不明確

### auto-editor（4.3k⭐）
- ⚠️ 暫不採用：核心用 Nim 寫，非 Python lib
- 可作為前處理 CLI 工具（去靜音），但不進主 pipeline

---

## 環境設定備忘

### Python 環境
- WSL Ubuntu 24.04，Python 3.12 系統環境
- 安裝套件需加 `--break-system-packages`（PEP 668）

### ffmpeg / ffprobe
- 路徑：`/home/lio730309/.local/bin/`
- 必須加到 PATH，否則 stable-ts 等工具會找不到

### 已安裝套件
```
edge-tts        7.2.8
stable-ts       2.19.1
faster-whisper  1.2.1
```

### 中文字型
- `/home/lio730309/.local/share/fonts/wqy-microhei.ttc`
- ffmpeg subtitles filter 用 `fontsdir=/home/lio730309/.local/share/fonts`
- force_style 用 `FontName=WenQuanYi Micro Hei`

---

## 驗證模板（給後續工具）

新工具上線前的標準驗證流程：

```
1. 安裝 → 驗證版本可顯示
2. 最小範例跑通（一個句子 / 一個檔案）
3. 中文場景測試（如適用）
4. WSL/CPU 環境相容性測試
5. 跟現有工具整合測試
6. 寫入本文件
```
