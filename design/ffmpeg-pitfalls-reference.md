---
title: FFmpeg Pitfalls Reference
created: 2026-05-23
updated: 2026-05-23
type: reference
tags: [ffmpeg, pitfalls, video, skill, reference]
sources:
  - https://github.com/znyupup/ai-video-editing-skill
related:
  - [[roadmap]]
  - [[skill-interface-contracts]]
---

# FFmpeg Pitfalls Reference

來源：vlog-auto-edit SKILL.md（30 條已知陷阱），按 Skill 分類整理。

---

## 小編 Skill 相關

| # | 問題 | 說明 | 解法 |
|---|------|------|------|
| 3 | Whisper 模型選擇 | base 中文效果差，large 太慢 | 用 medium |
| 10 | Whisper 幻覺 | 純音樂/環境音段落會生造文字 | 音量 < -40dB 段落跳過 |
| 11 | 直橫比混搭 | 9:16 素材混入 16:9 專案 | ingest 時過濾或標記 |
| 25 | FunASR 缺依賴 | pip install 不夠 | 補裝 torchaudio |
| 26 | FunASR timestamp 粒度 | 回傳字元級，非句子級 | 按標點聚合 |
| 27 | FunASR 幻覺比 Whisper 低 | 靜音仍回傳空字串 | 仍需音量二次過濾 |

---

## 剪輯師 Skill 相關

| # | 問題 | 說明 | 解法 |
|---|------|------|------|
| 5 | codec 不一致 | concat 時音視頻跑掉 | probe 確認後統一 codec |
| 12 | PNG overlay shortest=1 | 單幀 overlay 提前截斷影片 | 移除 shortest=1，改用 loop |
| 16 | Non-monotonic DTS | concat 時出現警告 | 可忽略，不影響播放 |
| 17 | 無聲段過長 | > 6 秒觀感拖沓 | 壓縮到 5–8 秒 |
| 18 | **xfade 串接黑幕** | 多個 xfade 鏈接 → 第二段變黑 | **改用 concat demuxer** |
| 19 | 測試先用短片 | 全片跑才發現問題 | 先用 5–8s 片段測 pipeline |
| 20 | 幀數驗證 | 輸出幀數可能不符預期 | `ffmpeg -i out.mp4 -f null -` |
| 30 | 相容性輸出參數 | Premiere/CapCut 可能無法讀 | `-r 30 -vsync cfr -x264-params "bframes=0" -ar 48000 -ac 2` |

---

## 音控師 Skill 相關

| # | 問題 | 說明 | 解法 |
|---|------|------|------|
| 21 | BGM 音量 | 有人聲段 BGM 太大會蓋掉語音 | 語音段 8–12%，純畫面段 30–40% |
| 22 | BGM 銜接 | 換曲目 BPM 差距大會感覺跳 | BPM 差 ≤ 20 |
| 23 | 原始素材音量不一致 | 不同來源音量基線差很多 | 混音前先 normalize，成品再試聽 |
| 28 | **atempo 音視頻漂移** | 加速後每段累積 0.4–0.8s 偏移 | 驗證 audio/video 長度差 < 0.05s，用 apad 補 |
| 29 | **concat copy 音訊斷點** | 時間戳不連續 → 喀喀聲 | 抽成 WAV → apad → concat filter（非 demuxer）→ 重接 |

---

## 字幕師 Skill 相關

| # | 問題 | 說明 | 解法 |
|---|------|------|------|
| 9 | 字幕句子中間切斷 | LLM 產的字幕可能在詞中切 | 加句子邊界驗證，切點必須在標點後 |
| 26 | FunASR timestamp 粒度 | 字元級 → 需轉句子級 | 按句號/逗號聚合 timestamps |

---

## VERIFY Skill 相關

| # | 問題 | 說明 | 解法 |
|---|------|------|------|
| 20 | 幀數驗證 | 輸出和預期不符 | `ffmpeg -i output.mp4 -f null -` 確認幀數 |
| 30 | 輸出相容性 | 解析度/音訊規格不一 | 強制 `-r 30 -vsync cfr -ar 48000 -ac 2` |

---

## 通用 / 環境相關

| # | 問題 | 說明 | 解法 |
|---|------|------|------|
| 2 | API endpoint 混用 | Vision 與 text model endpoint 不同 | 每個 provider 確認各自 endpoint |
| 6 | Vision API rate limit | 尖峰時段被 throttle | 加 retry + sleep(指數退避) |
| 14 | ffmpeg 缺 freetype | macOS Homebrew 版沒編 freetype | WSL 靜態 binary 已包含；字幕改用 Pillow PNG |
| 15 | HEVC decode 警告 | "Error constructing the frame RPS" | 非致命，可忽略 |
| 24 | 依賴安裝污染 | 重複建 venv 或裝已存在套件 | 先確認再裝 |

---

## 本環境已踩過的坑（補充）

以下是在這個專案實際遇過的問題，不在原始列表內：

| 問題 | 情境 | 解法 |
|------|------|------|
| yt-dlp 找不到 ffmpeg | `--download-sections` 需要 ffmpeg | 加 `--ffmpeg-location ~/.local/bin/` |
| PowerShell 傳 `-c:v libx264` 被誤解析 | WSL 指令含冒號 | 寫成 shell script 再 `bash script.sh` 執行 |
| 解析度不一致無法 concat | 不同來源影片解析度不同 | concat 前自動偵測，scale 到最大解析度 |
| 中文字幕亂碼 | NotoSansSC.otf 實為 HTML 頁面 | 改用 wqy-microhei.ttc，加 magic bytes 驗證 |
| NotoSansSC GitHub LFS 問題 | 下載到 HTML 而非字型 | 從 Ubuntu .deb 提取真實字型 |
