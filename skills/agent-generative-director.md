---
name: agent-generative-director
description: AI Agent 專屬生成美術 Skill。讀取 state/manifest 與 generated_asset_requests，使用 assistant_imagegen/codex_imagegen 生成高品質 fallback image，寫入 generated_asset_manifest 或 student_uploads，並由 route.py 或 canonical run 接續重渲。
---

# Agent Generative Director Skill (AI Agent 生成美術)

本 Skill 是 pipeline 的 **AI 協同生成後備方案（Agent-in-the-loop Material Fallback）**。
當本地素材與 Stock 素材皆枯竭，且 Node 8 明確允許 generated fallback 時，利用 AI Coding Agent
的原生繪圖能力作為 `assistant_imagegen` / `codex_imagegen` provider。ComfyUI 已降為
deprecated/disabled provider，除非使用者明確要求，不再作為 fallback 首選。

---

## 1. 職責與工作流程

當執行 `route.py` 或 `video_pipeline.py` 且 `state.json` 回傳 `await_material` 狀態時，AI Agent 將執行以下步驟：

### 步驟 1：偵測缺口段落 (Detect Gaps)
讀取輸出目錄中的 `state.json` 或觀察控制台的 `⏳ 等待學員素材（補拍指引）` 輸出，找出哪些段落處於 `blocking` 狀態。
* 範例 `state.json` 內容：
  ```json
  "blocking": [
    {
      "segment": 6,
      "reason": "天快亮了: 已暫用後備畫面。建議補拍：雨後 街道特寫/空鏡，中景，時長 14 秒，命名為 seg6_user.mp4"
    }
  ]
  ```

### 步驟 2：解析畫面描述 (Parse Prompt)
讀取 `script.json`（或 `script_routed.json`），找到對應 segment 的 `visual_desc`。
* 範例 `script.json` 段落：
  ```json
  {
    "segment": 6,
    "title": "天快亮了",
    "visual_desc": "雨後清晨的城市街道，天空微亮，地面仍有積水反光",
    "duration_sec": 14
  }
  ```

### 步驟 3：調用繪圖工具生成 (Generate Image)
使用 Agent 的原生 image generation 工具生成符合 `visual_desc` 的高品質圖片。
* **工具呼叫範例**：
  ```json
  {
    "Prompt": "雨後清晨的城市街道，天空微亮，地面仍有積水反光, photorealistic, 8k resolution, cinematic lighting, highly detailed",
    "ImageName": "seg6_user"
  }
  ```

### 步驟 4：保存並重渲 (Deploy & Resume)
1. 將生成的圖片保存至學員素材目錄：
   `student_uploads/seg{n}_user.png` (或 `.jpg`)
2. 重新執行 `route.py` 命令。編排器會自動偵測到新素材、將其 source 設為 `local` 並重新渲染該段落：
   ```bash
   python3 route.py examples/story_mv_smoke_script.json \
     --out /tmp/video_route_story_mv \
     --material-dir student_uploads \
     --verbose
   ```

---

## 2. 優勢與邊界

* **零程式修改**：完全複用 `route.py` 已有的 `await_material` 與 `source=local` 剪輯邏輯。
* **高畫質**：直接利用 Agent 底層 image generation provider，畫質與語意理解能力通常遠高於目前本地 ComfyUI/SD1.5 fallback。
* **按需生成**：僅在 Stock 搜尋無效且進入 fallback 時觸發，節省時間與算力。
