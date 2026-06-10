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

為確保 Antigravity / assistant_imagegen / Codex 圖像 provider 能生成可用的寫實素材，生成美術必須根據劇本的中文 `visual_desc` 進行 Prompt 擴充，嚴格遵循以下 Hard Rule 與 token-stack 公式：

### 🔴 Hard Rule:高訊號 token,禁 generic 廢詞

每個 prompt 必須含 **5-8 個高訊號技術 token**(焦段/光源/底片質感/構圖/分級方向),
並**禁用** `cinematic, 8k, beautiful, masterpiece, high detail, realistic` 這類
generic 詞——它們只觸發「AI 圖庫感」,稀釋訊號(跨平台 benchmark 實證,見 §3.4 詞彙來源)。

### 提示詞擴充公式(token stack)
```
[核心主體主詞(英文)] + [環境/背景細節] +
[焦段與構圖](如 85mm portrait / 35mm humanist / 100mm macro extreme close-up) +
[光源設計](如 single tungsten practical / golden hour backlit / overcast diffused) +
[底片/質感](如 Kodak Vision3 emulation / 35mm film grain / shallow depth of field) +
[分級方向](如 warm amber grade / teal-orange / desaturated cool)
```

通用訊號層(焦段/光/底片/構圖)對所有 provider 有效;**導演/DP 名字屬平台相依層**
(部分模型會 strip),provider-neutral request 預設不用,只在明確知道目標平台吃它時加。

### 實體對照示範表

| 劇本中文畫面描述 (`visual_desc`) | 擴充後正向提示詞 (Positive Prompt) |
| :--- | :--- |
| **胡椒餅炭烤特寫** | `Extreme close-up of a Taiwanese pepper bun (Hujiao Bing) baking inside a glowing charcoal clay oven, crispy golden sesame crust, embers burning red in the dark background, steam rising, 100mm macro lens, single-source ember glow with deep shadows, Kodak Vision3 500T emulation, shallow depth of field, warm amber grade` |
| **藥燉排骨蒸氣升騰** | `A steaming bowl of Taiwanese herbal pork-rib soup (Yao Dun Pai Gu) on a dark wooden table, swirling steam backlit by a low practical lamp, dark broth with visible Chinese herbs, 85mm portrait lens, low-key tungsten warmth, 35mm film grain, moody dark-background food photography` |
| **台灣夜市喧囂街景** | `Bustling Taiwan night market at dusk, crowded lane of food stalls under layered neon signage, 35mm humanist lens at eye level, practical neon bokeh in rain-damp reflections, warm-cool color collision of red signage against blue dusk, handheld documentary energy, 35mm film grain` |

* **預設負向提示詞 (Negative Prompt)**：
  依段落媒材分類挑用,**短而精(5-15 個)**比長列表有效:

```text
基底(必帶):     text, watermark, signature, logo, subtitle, UI elements
寫實照片段:     cartoon, anime, 3d render, illustration, plastic skin, airbrushed
人物段:         deformed face, asymmetrical eyes, extra fingers, fused fingers,
                bad anatomy, uncanny valley
video 生成段:   jittery camera, frame stutter, choppy motion, morphing body parts,
                melting geometry, impossible physics, inconsistent shadows
```

### §3.4 詞彙來源(活的參考,不複製進 repo)

完整的焦段×情緒對應、光源/底片/分級語彙、各平台 prompt signature 與分模型
negative bank,參考外部庫(知識會隨平台版本過時,用前自行判斷時效):

```text
reference repo/ai-media-generator-main/references/cinematic-direction.md   # 詞彙主庫(導演/DP/焦段/光/分級)
reference repo/ai-media-generator-main/references/camera-language.md       # 運鏡語言
reference repo/ai-media-generator-main/templates/negative-bank.md          # 分模型負向庫
reference repo/ai-media-generator-main/references/selector.md              # 平台選擇(若走外部生成平台)
```

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
