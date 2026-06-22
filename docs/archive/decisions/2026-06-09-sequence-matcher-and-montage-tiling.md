# Decision: SequenceMatcher 字幕比對 + Montage 多幀 Tiling QA

**Date**: 2026-06-09
**Status**: Implemented
**Scope**: `video_pipeline_core/vt_verify.py`, `video_pipeline.py`

## Context

兩個已知 QA 盲區需要同步修復：

1. **字幕比對算法失準**：原先 `_verify_subtitle_accuracy` 使用 `collections.Counter`
   字元頻率重疊率，無法偵測字詞順序錯誤（例如「早安你好」與「你好早安」會得到 100% 分數），
   導致字幕錯位/重複字詞等問題漏檢。

2. **Montage/Collage 快切畫面 QA 盲區**：`compose_and_qa` 原先只從每段取一張中間點
   截圖（`final_frame_{n}.jpg`），快速輪播的 montage 段落只看到首幾張圖就交給 VLM，
   無法判斷整段素材是否連貫或有重複/黑畫面。

## Decision

### 1. SequenceMatcher 替換 Counter

- 使用 `difflib.SequenceMatcher().ratio()` 取代 Counter 字元重疊率
- 零額外依賴（Python 標準庫）
- 對字詞順序、重複、插入敏感，能捕捉：
  - 字詞亂序（「早安你好」vs「你好早安」→ ratio < 1.0）
  - 部分重複（「AAABBB」vs「AABB」→ ratio < 1.0）
  - 完全不同文字（score 會極低）

### 2. Montage/Collage 多幀 Tiling

- 新增 `extract_tiled_frames(src, duration, out_path, num_samples, start_offset)` helper
- 在 `compose_and_qa` 的 thumbnail 迴圈中，偵測 segment 的 `layout` 欄位
- 若為 `"montage"` 或 `"collage"`：
  - 段長 ≥ 8 秒抽 5 格，否則抽 3 格
  - 使用 FFmpeg 逐張縮小至 480×270，拼成 Nx1 水平長圖
  - 寫入同一 `final_frame_{n}.jpg` 路徑（不改下游 content_qa API）
- 若 tiling 失敗，自動 fallback 到原始單張中間點截圖

## Consequences

- **正面**：VLM 在 montage 段落可看到前/中/後代表畫面，偵測黑畫面、重複素材、不連貫轉場
- **正面**：字幕錯位/亂序可被 SequenceMatcher 正確偵測
- **風險極低**：兩項修改都有 fallback 機制，不影響非 montage 段落的既有行為

## Verification

- 464 unit tests 全部通過，無迴歸
