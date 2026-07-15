# Canon 67｜39 秒訪談 L0–L5 完整修訂輪設計

Date: 2026-07-11
Status: approved design; implementation pending
Scope: Canon 67 主任訪談 internal-review candidate

## 1. 目標

把既有 22 秒訪談試片延長到約 39.34 秒，完整保留「回首入訓、忐忑如幼苗、經師長照顧、成長為大樹」的語意段落，並在同一候選片上真實執行：

```text
L0 素材沉浸與語意草稿
→ owner 核准逐字稿
→ L1 畫面編排
→ L2 紀錄片式開場 lower third
→ L3 原聲＋BGM ducking
→ L4 核准字幕
→ L5 全片 review
```

這是 internal-review first-of-kind，不是最終交付、音樂授權、完整長片或 creative approval。

## 2. 已核准的產品決定

1. 片長目標為主任原始講話 `0.00–39.34s` 附近的自然語意邊界，不再硬切於 22 秒。
2. 既有 `0.00–19.34s` 畫面方向可沿用；新建 `19.34–39.34s` 的增量編排。
3. L2 必須實際產生效果，不再用 no-op 代表完成。
4. 開場採紀錄片式 lower third：實拍不中斷，左下顯示「主任勉勵」，白字、暖黃色細線、輕滑入與淡出，約 `0.60–3.20s`。
5. L4 必須實際渲染字幕；ASR 只能作草稿，owner 核准文字才是唯一字幕來源。
6. 現有 Ed Napoli〈Endless song Instrumental〉只允許 internal preview；`preview_only=true`、`delivery_allowed=false` 保持不變。
7. `human_creative_approval=false`、`final_delivery_claimed=false` 全程不翻動。

## 3. L0 與 L4 的責任邊界

L0／Material Map 應一次完成並攜帶：

- source hash 與 `0.00–39.34s` 時間窗；
- 原聲抽取與 ASR 草稿；
- cue 時間碼、不確定詞與完整上下文；
- 人物、動作、景別、作業類型與故事功能標籤；
- 對 `19.34–39.34s` 新增 cutaway 的候選與證據座標。

這些資料以 source hash＋時間窗復用，避免 L1–L5 重複辨識與重複花費 token。

L4 只負責：

- 讀取 L0 草稿；
- 接收 owner 核准的每個 cue 文字；
- 由核准文本編譯字幕；
- 驗證同步、可讀性、缺字、亂碼與 cue coverage。

L0 的「理解內容」不能冒充 L4 的「核准文字」。

## 4. 39 秒 timeline 設計

### 既有範圍 `0.00–19.34s`

- 保留主任開場 talking head 與既有訓練 cutaway 的大方向。
- 允許為自然句點與字幕同步做 frame-level 邊界修正，但不得無證據重選整段。
- lower third 與第一段字幕必須分層避讓。

### 新增範圍 `19.34–39.34s`

以語意 beat 選片，不按 catalog 順序取前 N：

| 語意 beat | 約略時間 | 畫面功能 |
| --- | ---: | --- |
| 回首剛進中心 | 19.34–22.34 | 主任或入訓／初到場景，建立回憶轉軸 |
| 忐忑不安 | 22.34–26.34 | 新學員、集合、等待或初次練習 |
| 像小樹苗 | 26.34–29.34 | 人物較近、尚在學習／被帶領的畫面 |
| 師長細心照顧 | 29.34–32.34 | 師徒指導、手把手教學 |
| 不斷呵護、深耕 | 32.34–36.34 | 重複訓練、協作、技能細節 |
| 成為一棵棵大樹 | 36.34–39.34 | 集體、成果或有力量的收束畫面 |

Agent 可在既有 Material Map 與原始素材中選擇最符合的 stable asset/window，但必須攜帶實際像素／時間座標、selection reason 與 blind spots；參考成片與前期音樂資料夾仍禁止作素材。

## 5. L2 效果設計

效果角色：speaker-segment opening／lower third。
故事功能：讓觀眾立即知道這是「主任勉勵」，不搶語音與字幕。
Backend：既有 ffmpeg/libass light-effect 路徑；不使用 Remotion。

視覺與動作：

- 左下安全區；白色主字「主任勉勵」；
- 暖黃色細線作識別，不加入未驗證姓名或職稱；
- 約 8–12 frame 輕滑入、短 hold、約 8–12 frame 淡出；
- lower third 位於字幕區上方，兩層不得重疊；
- 禁止全螢幕章節卡、粒子、炫光、彈跳、重型轉場與遮住講者臉部。

Effect Factory 需產出 bounded effect design map、contract、render evidence、review 與 handoff；final assembly 仍屬正式 V Pipeline。

## 6. L3 與 L4 呈現

### Audio

- 主任原聲連續且優先；不得因 cutaway 中斷或重排語音。
- BGM 在語音下自動 ducking，沿用 internal-preview policy。
- 驗證 39.34 秒完整 speech continuity、音量與結尾，不把技術 PASS 當授權 PASS。

### Subtitles

- 預計約 12 個 cue；實際 cue 邊界由 39 秒 ASR review packet 提案、owner 核准。
- 底部中央、最多兩行、白字＋黑色描邊或半透明底。
- 1920×1080 安全區內，與 lower third 保持明確垂直間距。
- 不得把 ASR 的「節業、半夜、不擇不扣、為所遜」等草稿直接渲染為真值。
- 中文檔案必須明確 UTF-8 回讀，禁止 U+FFFD 與連續問號污染。

## 7. 執行波次與 gate

### Artifact 邊界

- 39 秒 first-of-kind 的唯一新 root 為 `.tmp/editing_loop_39s_integrated_campaign/`。
- `.tmp/editing_loop_certification_campaign/` 內既有 22 秒 closure、candidate 與 durable evidence 全部視為唯讀歷史證據；39 秒工作不得覆寫、搬移或宣稱取代它們。
- 39 秒候選片只有在 owner transcript gate、完整 L0–L5 客觀驗收與 integrator recheck 全部通過後，才可另行成為 current candidate；在那之前只稱 experimental campaign。

### 已驗證的 Wave P 前置缺口

2026-07-11 的 Wave P forward test 證明三個既有接縫尚未閉合：

1. `soundtrack_probe` 把 ASR cue 寫在 `features.vocal_analysis.segments`，但 transcript repair adapter 只讀頂層 cue，真實 20 cues 會被讀成 0。
2. human transcript decision v1 只保存 cue id，沒有綁定 source hash、時間窗與 owner-approved text。
3. source-speech subtitle QA 只驗 coverage／placeholder，未驗證核准文字與實際 SRT 相等。

這是受限的 production contract repair，不是新架構。必須先以 RED→GREEN 修補上述三點，才可恢復 Wave P；不得用 run-local 私有 script、手排 SRT 或表格繞過。

### Wave P — Transcript review packet

1. 從原始主任素材抽取 `0.00–39.34s` 原聲。
2. 只執行一次 ASR／agent repair，產生約 12 個 cue、時間碼與不確定處。
3. 上傳 39 秒原聲與 review table 到預設 Google Drive workspace。
4. 停在 owner transcript gate；不得先渲染字幕。

### Wave R — Full L0–L5 revision

只在 owner 逐 cue 核准後開始：

1. 凍結 owner verdict、輸入 hash 與既有候選片。
2. 完成 L0 增量標籤與 `19.34–39.34s` 選材。
3. 建構 L1 39 秒 picture timeline。
4. 經 Effect Factory 套用 L2 lower third。
5. 執行 L3 preview-only ducking mix。
6. 由 owner-approved text 執行 L4 字幕路徑。
7. 產生同一 candidate 的 fresh L5 evidence 與 owner review package。

任何 factory gap、逐字稿缺漏、參考素材污染、授權不明、production-code 必要修改或同類失敗重現，都在 last-green state 停止，不得用私有 script 繞過。

## 8. 驗收

客觀驗收至少包含：

- 片長與 source-speech continuity；
- picture／effects／audio／text semantic diff；
- lower-third lifecycle、可讀性與字幕碰撞檢查；
- 逐 cue approved-text equality 與時間 coverage；
- rendered QA、final-product verify、黑幀／stream／響度；
- 低密度全片牆與可疑時間窗密集條；
- frozen input hashes、UTF-8、JSON、evidence links；
- 受影響範圍 focused tests。

本次完整 L0–L5 first-of-kind 依 subordinate integrated-closure contract，在候選片與 durable evidence 完成後只跑一次 full suite；不得在 Wave P 或各 LOOP 間反覆跑全量測試。若 production code／tests 有變動，另先跑其 focused＋adjacent regression。

最終必須分開申報：objective PASS／FAIL、agent judgment、owner taste、music rights、creative approval 與 delivery。

## 9. 非目標

- 不建立新 orchestrator、route runner、journal、timeline v2 或 dirty-matrix engine。
- 不擴成 9.4 分鐘完整影片。
- 不以 CapCut GUI 自動化取代正式 pipeline。
- 不宣稱 Ed Napoli 音樂可正式發布。
- 不改寫歷史證據或原始 Downloads 素材。

## 10. 完成定義

本輪只有在以下條件同時成立時，才能稱為「39 秒 L0–L5 internal-review loop completed」：

1. owner 核准全部字幕 cue；
2. 同一 39 秒候選片含核准 picture、實際 lower third、ducked audio 與核准字幕；
3. fresh L5 客觀證據通過；
4. integrator 獨立重查 artifacts、hashes、diff 與 material acceptance commands；
5. candidate creative quality 仍由 owner 另行判定；
6. `human_creative_approval=false`、`final_delivery_claimed=false`。
