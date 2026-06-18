---
name: material-generation-fallback
description: 缺素材時的生成式素材補救 Skill。讀 material_delta + 上游故事/導演資訊，產 provider-neutral 生成任務；生成品必須回到 material-map 複核，不得直接當真實素材或繞過 M6 gate。
---

# Material Generation Fallback Skill

本 skill 負責把 `material_delta.json` 裡的 `missing` / `thin` 需求，轉成可交給
Antigravity、Gemini、assistant_imagegen、Codex imagegen 或其他 provider 的
`material_generation_fallback.json`。

它不是生成 provider，也不是素材地圖第二套 schema。

## 何時使用

使用條件：

- M6 `material_delta.json` 已 fresh 計算且 `ok=true`
- 某些 need 是 `missing` 或 `thin`
- 劇本/導演設計允許該 need 用 generated image/video、symbolic insert、
  reenactment、chapter bridge 或 title/background 補足

不可使用：

- `material_delta.ok=false`
- dangling reference / asset identity 壞掉
- real person proof、official speech、身份關鍵、活動證據需要真素材
- 使用生成圖假裝實拍

## 唯一工具入口

```powershell
python video_tools.py material-generation-fallback material_delta.json `
  --needs material_needs.json `
  --creative-concept creative_concept.json `
  --director-shot-plan director_shot_plan.json `
  --out material_generation_fallback.json
```

可選上下文：

- `story_world.json`
- `creative_concept.json`
- `screenplay_beats.json`
- `director_shot_plan.json`

## 輸出邊界

`generation_jobs[]` 每筆都必須：

- 帶 `need_id`
- 帶 `source_type: generated`
- 帶 `status: planned`
- 帶 prompt / negative_prompt / review_criteria
- 宣告回素材地圖時只能先用 `candidate` satisfies edge
- 宣告 `must_not_claim_real_event: true`

生成完成後流程：

```text
generation job
  -> provider 產圖片/影片
  -> ingest / material-map
  -> reviewer 建 satisfies(candidate)
  -> material_delta fresh 重算
  -> reviewer accept 或 revision
  -> BUILD
```

任何生成素材都不得直接讓 BUILD ready。

## 導演判斷規則

生成素材適合：

- 記憶框架、象徵畫面、章節橋、空景、抽象情緒、漫畫/照片故事 panel
- 沒有真實身份壓力的手部/物件/背影/空間重演

生成素材不適合：

- 真實主任/老師致詞
- 學員具名反應
- 實際課程證據
- 官方 Logo / 證書 / 名牌 / 場地招牌
- 任何會讓觀眾以為「這就是當天拍到」的畫面

## Prompt 原則

延用 `skills/generative-director.md` 的高訊號 prompt 規則：

- 主體清楚
- 焦段 / 構圖 / 光源 / 質感 / 色調明確
- 不寫 generic 廢詞
- negative prompt 要短而精
- 圖中文字、Logo、真名、證件、官方標誌預設禁用

## Review Checklist

每張生成素材進 material-map 前要檢查：

- 是否真的服務該 need 的 story function
- 是否和 `visual_family` / `angle_scale` / `action_family` 一致
- 是否有假證據、假 Logo、可讀假文字
- 是否誤導為真實紀錄素材
- 是否能以 `candidate` 狀態掛回正確 need_id

