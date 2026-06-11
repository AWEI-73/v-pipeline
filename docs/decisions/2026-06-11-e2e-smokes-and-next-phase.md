# 2026-06-11 — 真實 E2E 雙煙霧測試、本週修復總結、下一階段優先序

## 背景

收斂期(roadmap C0-C6)收尾後,以「真的跑兩支片」取代紙上驗收:
一支走 MV 鏈(skill-smoke)、一支走 narrative 鏈(city-day,口白+音樂+5 分鐘)。
邊跑邊修,所有發現即時落地(各自獨立 commit,本文是索引與裁決記錄)。

## E2E 結果

```text
skill-smoke(MV 鏈,4 段 35s 手沖咖啡,stock_first):
  final.mp4 34.4s vs 目標 35s;verify 91.5 PASS;editorial_qa 94 PASS;
  fatigue/treatment PASS;spec_review ready;VLM 評窗/候選重試/target-cap 全程實戰現身。

city-day(narrative 鏈,21 段 ~5min 口白+BGM):
  v2:297.6s、qa 88.6、誠實 qa_fail(content_alignment 62,3 段判補拍)——
  流程行為正確,失分主因是 4b 對多子句描述的 false negative(D5)。
  修復(171ed01)後 v3 重跑(口白加長 +17s)。
```

## 本週修復索引(細節在各 commit message)

```text
43f0002  stock 相關性排序(時長只當資格門檻)——機器人跳舞根因
4015b51  多窗消費 slots + pacing 對齊 allocation——一鏡到底根因
4a9337f  soul 守門員警報(pacing_conflict / editing_policy inactive)
30cbb27  brief target_length cap timeline——123s 膨脹根因
cec1fa6  VLM 內容驅動裁剪(stock 評窗)
88852cc  spec_review pre-BUILD gate(B1-B4/W1-W8 含敷衍偵測)
7b496c5  perfunctory-SPEC 偵測 + text_layer:"none" 豁免
4fe6870  E2E 發現:editorial_design 複製、蒸餾救援、候選重試、off-topic floor
171ed01  D5 兩段式評分下沉到 content_qa.score_segment(兩鏈共用)
```

## 對外部回饋的裁決(Gemini 專案評析,2026-06-11)

| 痛點/建議 | 裁決 |
|---|---|
| CapCut 橋只造一半(draft 缺 text/audio 軌) | ✅ 採納 → P4 |
| SPEC→BUILD 意圖漂移(渲染表現力天花板) | ✅ 診斷採納;「無法消化」過時(結構層已消化)→ P6 |
| 入口破碎 | ⏳ 已大半完成(route.py 退役、skill 強制入口);殘餘=兩鏈不對稱 → P3 |
| 廢棄 video_pipeline.py | ❌ 修正:它是 narrative 引擎本體,正解是 contract→narrative adapter(P3) |
| VLM 改雲端 API | ❌ 修正:local-first 不變;rubric 工程已恢復精度(蒸餾救援實證);雲端=model_routes opt-in 仲裁 |
| 語意/物理審計解耦 | 已存在(P1 audits 獨立、--no-vlm-gate) |

## 使用者方向(2026-06-11 討論)→ 編入 roadmap

1. 字幕:中下置中、去標點、加大 → P1。
2. 照片節奏校準值(動 1-2s、堆疊 1s/2 張=快)→ P2 注意力預算。
3. 「感受」法則:口白+故事可拉長素材;純音樂必須快剪;非動作影片長 take 感受差
   → P2 的核心原則:「哪個通道在說故事,哪個通道就拿時間」。
4. 一張照片多幕(省素材、好 review)→ P5。
5. UI 方向:不做 NLE,做「審查+補丁面板」(dashboard + 寫回:換候選/調窗/
   結構修剪,全部映射到既有 CLI 與 Node 14 revision loop)。

## 結論

收斂宣告完成;下一階段主軸從「正確性」轉向「表現力與感受」,
優先序 P1-P6 見 roadmap.md 2026-06-11 節。
