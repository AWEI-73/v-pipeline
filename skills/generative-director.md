---
name: generative-director
description: AI 生成美術 Skill。管理 generated image/video fallback 的誠實邊界與 provider request。主 provider 建議 Antigravity / assistant_imagegen；ComfyUI 已降為 deprecated/disabled provider，僅保留歷史參考。
---

# Generative Director Skill (AI 生成美術)

AI 生成美術是 pipeline 中的 **AI 概念後備方案（AI Material Fallback）**。
當本地素材與 stock 素材皆不適合，且 fallback route 明確允許 generated image/video 時，
本 skill 產生 `generated_asset_requests.json`，交由 BUILD profile 指定的 provider 執行。
`contract_adapter.py run` 目前會自動依 `build_profile.json.provider_priority` 寫出
`generated_asset_requests.json`，外部 provider 完成後再寫 `generated_asset_manifest.json`。

目前 provider 優先序：

```text
1. antigravity
2. assistant_imagegen / codex_imagegen
3. gemini_veo(僅 video fallback 或明確要求)
```

ComfyUI 因目前實測品質明顯低於 Antigravity 與 agent native imagegen，預設不再作為推薦來源。
除非使用者明確要求獨立實驗，後續 agent 不應自動選用 ComfyUI；本 skill 不提供 ComfyUI 執行 recipe。

---

## 1. 職責邊界

1. **Fallback 誠實性守門**：只處理 `stock_bridge/generated/text_bridge` 等被 Node 8 明確允許的段落。
   `must_include`、`identity_sensitive`、`proof_critical` 不可生成替代。
2. **Provider request 產物**：將段落需求轉成 `generated_asset_requests.json`，而不是直接把 provider 寫死在 SPEC。
3. **Prompt 擴充**：將 `visual_desc` / `search_query` 擴寫為 provider 可用 prompt，保留 `reason`、用途與禁止事項。
4. **Manifest 交付**：provider 完成後寫 `generated_asset_manifest.json`，標明 provider、prompt、output、trace、不可假裝真素材。

工具實作：

```text
build_profile.py      load/validate/write build_profile.json
generated_assets.py   build/write generated_asset_requests + generated_asset_manifest
contract_adapter.py   canonical run 自動把 build_profile/generated requests 掛進 artifact_manifest
```

建議 request 形狀：

```json
{
  "generated_asset_requests_version": 1,
  "provider_priority": ["antigravity", "assistant_imagegen"],
  "items": [
    {
      "segment": 6,
      "asset_role": "symbolic_cutaway | chapter_background | conceptual_process",
      "provider": "antigravity",
      "prompt": "photorealistic clean bright workspace, cinematic lighting",
      "negative_prompt": "text, watermark, distorted hands, low quality",
      "reason": "stock 不好命中的概念補圖",
      "forbidden_as_truth": true
    }
  ]
}
```

---

## 2. Deprecated Provider Policy

> Status: deprecated / disabled by default.
>
> ComfyUI 已從 active tool source 移除。若未來要重啟，必須另開 isolated project/agent，
> 並只透過 `source=generated` + metadata 回到本 pipeline。此 skill 不保存 ComfyUI
> client、workflow API、模型安裝、WebSocket 或本地 GPU 操作細節，避免後續 agent 誤觸。

---

## 3. 劇本中文描述之 AI 擴充規範 (Prompt Expansion)

為確保 Antigravity / assistant_imagegen / Codex 圖像 provider 能生成可用的寫實素材，生成美術必須根據劇本的中文 `visual_desc` 進行 Prompt 擴充，嚴格遵循以下黃金公式：

### 提示詞擴充公式
```
[核心主體主詞(英文)], [環境與背景細節], [相機鏡頭、構圖與拍攝角度], [光影氛圍(如溫暖夕陽、微光)], [底片顆粒、超寫實渲染詞]
```

### 實體對照示範表

| 劇本中文畫面描述 (`visual_desc`) | 擴充後正向提示詞 (Positive Prompt) |
| :--- | :--- |
| **胡椒餅炭烤特寫** | `Extreme close-up shot of a Taiwanese Pepper Bun (Hujiao Bing) baking inside a glowing traditional charcoal clay oven. Crispy golden sesame-crusted pastry, embers burning red in the dark background, steam gently rising, cinematic shallow depth of field, 8k resolution, raw photography.` |
| **藥燉排骨蒸氣升騰** | `A steaming hot bowl of Taiwanese herbal pork ribs soup (Yao Dun Pai Gu) on a dark wooden table. Swirling hot steam rising, rich dark broth with traditional Chinese medicine herbs visible, cinematic lighting, moody atmospheric background, photorealistic.` |
| **台灣夜市喧囂街景** | `Bustling Taiwan night market at evening, crowded street with glowing colorful neon light signs, rows of traditional food stalls, bokeh background, warm retro mood, shot on 35mm lens, cinematic film look.` |

* **預設負向提示詞 (Negative Prompt)**：
  `cartoon, anime, 3d render, sketch, blurry, low quality, deformed, mutated hands, bad anatomy, text, watermark, signature.`

---

## 4. 與其他 Skill 的編排對接 (Integration Flow)

```
[curator] 檢查段落 ──► 若 stock 枯竭/不及格且 fallback route 允許 generated
                             │
                             ▼
                    [generative-director] 
                             │
                             ├─ 1. 產 generated_asset_requests.json
                             ├─ 2. 依 build_profile 選 provider(Antigravity / assistant_imagegen)
                             ├─ 3. provider 輸出至 materials/generated/seg{n}.png
                             ├─ 4. 寫 generated_asset_manifest.json
                             │
                             ▼
                    [editor] 呼叫 kenburns 將 jpg 渲染為 mp4 轉場片段
                             │
                             ▼
                    [verify] 照常進行 technical & VLM 審核
```

這套 Skill 提供標準化、低耦合的 **AI 生成素材底座**。provider 可替換，但所有輸出都必須
留下 manifest，且不得假裝為真實拍攝素材。
