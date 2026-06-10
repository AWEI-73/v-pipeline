# Reference Repos Map(外部參考庫:可取什麼、不可取什麼)

> 兩個已下載的外部 repo 放在 `reference repo/`(**untracked,不入 git**)。
> 本頁是唯一的評估結論——之後的 agent 不要重新評估,直接查這頁。
> 共同原則:**techniques referenced, no code copied**(同 `THIRD_PARTY_NOTICES.md`
> 對 video-autopilot-kit 的模式)。知識會隨上游版本過時,取用前自行判斷時效。

## 1. `reference repo/ai-media-generator-main`(生成式 AI 提示詞 skill)

- **定性**:跨 14+ 平台(Veo/Kling/Seedance/Suno…)的生成提示詞庫 + 瀏覽器自動化。
  經兩輪 head-to-head benchmark 校準。MIT 授權。
- **與本專案的關係**:可插拔的外部 `generated` provider 素材;**不是**剪輯/組裝引擎。

| 可取 | 去處 | 狀態 |
|---|---|---|
| 高訊號提示詞彙(焦段/光源/底片/分級)+ Hard Rule(禁 generic 廢詞) | `skills/generative-director.md` §3 | ✅ 已收割(commit `ac83d64`) |
| 分模型 negative bank、平台 selector | generative-director §3.4 指標 | ✅ 指標已留 |
| grade look 清單(teal-orange 等) | 未來翻成 ffmpeg 數值進 `GRADE_PRESETS` | ⏸ 等實測後、有 keyframe_grid 可對照時 |
| site-profiles 瀏覽器自動化 | 未來真要驅動外部生成平台時 | ⏸ opt-in,掛 Material Source Contract 後面 |

**不取**:導演名簽名層(平台相依,部分模型會 strip)、整檔搬入(會過時)。

## 2. `reference repo/NarratoAI-main`(影視解說自動剪輯,9k+ stars)

- **定性**:解說**既有長片**(影片→LLM 解說詞→從原片裁剪→TTS+字幕)。
  方向與本專案相反(我們=從素材組裝新片)。**授權:Modified MIT 僅限非商用
  → 嚴禁複製程式碼,只能讀懂後自行重寫。**
- **圖譜**:`.understand-anything/`(1048 nodes / 2906 edges,2026-06-10 掃)。

| 可取(依價值排序) | 對應我們的缺口 | 觸發時機 |
|---|---|---|
| 🥇 `app/services/jianying_draft_builder.py` + `jianying_task.py` + 測試:**從零生成式 .draft 序列化**(自建 template、video+audio+**字幕 text 軌**(顏色/字級/位置)、ffprobe 時長 clamp、素材登錄) | 我們的 CapCut 路線**已通**(`capcut_backend` 骨架克隆式,E2E 2026-06-08 驗證)但**只重建 video 軌**;字幕/BGM 目前是匯出後由 `capcut-finalize` 用 ffmpeg 補。它的價值=把 text/audio 軌**做進 draft 內**,讓人在 CapCut 裡能直接改字幕/配樂 | 要升級 CapCut draft 含字幕/BGM 軌時(v4 之後) |
| 🥈 `app/services/documentary/frame_analysis_service.py`:抽幀→快取→視覺並發的長片理解鏈 | curator 對學員上傳長素材找可用片段(現只有粗的 detect_shots+VLM) | 收斂後的素材理解升級 |
| 🥉 `subtitle_corrector.py` / `subtitle_merger.py` / `script_subtitle.py`:ASR 結果對腳本的字幕**校正**(我們只評分不修) | Node 14 subtitle auto-fix route | 未來修字幕迴圈時 |
| `app/utils/ffmpeg_utils.py`:量產級 ffmpeg 配方 | 補 `design/ffmpeg-pitfalls-reference.md` | 隨時,便宜 |
| `voice.py`:多 TTS provider(騰訊雲/IndexTTS 克隆/Fun-ASR) | audio-director 的 provider 選項目錄 | 低優先 |

**不取**:Streamlit WebUI(我們 agent/CLI 驅動)、它的 task/state 編排(比我們的
node 狀態機簡單)、LLM provider 管理(已有 model_routing)、影視解說 prompts(文體不同)。

## 整合紀律(為什麼「先地圖、後整合」)

1. 整合必須有**驗證閘**:draft 軌道擴充落在 Node 13,每次改動都要實際在 CapCut GUI
   載入驗證(人/CU 閘),不是只看 JSON 長得像。
2. 收斂期非目標:主鏈(ai-video v4)未確認質變前,不開後端擴充工作。
3. 非商用授權 → 重寫是獨立工作項(讀懂欄位語意→自己的實作+測試),不是貼上。
