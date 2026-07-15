# 差距表：67期結訓影片 vs Hermes Pipeline 現況

日期：2026-07-10
目的：以真實參考片（學員製作的《67期結訓影片》，9.4 分鐘、172 鏡頭）為靶，
逐段落類型盤點 pipeline 今日產能與差距，作為各支線深挖的工單來源。
本表供多方（人類 owner ＋ 多個 AI agent）討論修訂。

北極星：自動初剪達到本片 1/2 品質。策略依據：薄基建＋有界垂直模板
（見 repo 戰略記錄）；「結訓/活動回顧片」為第一個垂直模板家族。

## 證據基礎

- 感知層實測產物：`.tmp/perception_field_repair_check3/`（32 頁蒙太奇牆、
  sampling plan 722 格、coverage PASS、soundtrack probe）
- 全片結構化解讀：本 session 的感知報告（三幕：儀式→技藝→情感；
  能量三高潮 138–150s / 258–278s / 466–518s；章節卡系統；班導接力名冊）
- Pipeline 能力證據：video_tools 子命令面、branch registry 8 支線、
  全套件 2589 tests green

## 成熟度標記

- ✅ 可用：今天就能產出可接受的結果
- 🟡 有零件缺整合：模組存在，但沒有串成該段落型態的一鍵路徑
- 🔴 缺：沒有對應產線能力
- 🤝 人工 gate：短期交給人（CapCut）處理，pipeline 只負責交接

## 差距表

| # | 段落類型 | 參考片做法（座標） | 現況 | 差距 | 建議作法 |
|---|---|---|---|---|---|
| 1 | 開場空拍＋逐字標題 | 大門空拍疊打字機標題（0–11s, shot_002–004） | 🟡 | `title-sequence`/`title-card` 存在；「疊在實拍畫面上的逐字動畫」需 effect factory 路徑，未驗證過此組合 | 用 remotion 模板做「footage + typewriter title」一個固定 composition；驗收＝effect-render-verification 現有 gate |
| 2 | 詩卡（黑底逐字文案） | 三行詩逐字浮現（11–18s, shot_006） | ✅/🟡 | `title-card` 可出靜態卡；逐字動畫同上走 remotion | 同 #1 共用 typewriter 元件；文案來源接 story_soul_blueprint 的 intent 欄位 |
| 3 | 拍點快剪蒙太奇 | 15+ 合照卡 beat 連發（18–44s） | 🟡 | beats 已有（soundtrack probe）、`match-mv`/beat_sequence/`jumpcut-plan` 存在；缺「素材池→按拍點自動排片」的一鍵整合，且 target_length 未強制（E2E 已知問題） | 新工單：beat-cut composer——輸入素材清單＋拍點錨，輸出 contract 片段；驗收＝beat-vs-cut 數值對齊儀器（新 verify，時間差 ≤1 幀比例） |
| 4 | 章節字卡系統 | 「不畏風雨 穩定供電-配電班」等，全片風格統一（84s, 199s…） | 🟡 | 單卡可做；「系統一致性」無人管——每卡各做各的 | 把章卡定義為 blueprint 的 chapter 欄位，一個模板多次實例化；審查 rubric 加「章卡一致性」題 |
| 5 | 紀實作業快剪（B-roll＋作業名字幕） | 各班訓練鏡頭＋角落字幕（84–286s 主體） | 🟡 | assemble/subtitle/burnsub 可用；**素材選擇**過去靠檔名，現在感知層可看畫面 | 感知層→material map 的鏡頭級標籤（誰/什麼作業/構圖），供 curator 選片；這是感知層接進生產線的第一個消費者 |
| 6 | 訪談＋cutaway | 主任致詞疊訓練場 B-roll，字幕全程（346–411s） | 🔴 | 關鍵缺口：A-roll 語音持續、畫面切 B-roll 的 pattern 無路徑；ASR 未接入產線 | 兩件：(a) ASR 產線化（faster-whisper 逐詞時間戳→srt→burnsub 已有）；(b) contract 支援「audio 持續、video 換軌」segment 型態（keep_audio/audio_role 已有雛形，需驗證此用法） |
| 7 | 動態名片卡（接力訪談） | 配一→輸三班導，單位＋口頭禪 motion graphics（462–554s，全片最高製作投資） | 🤝 | remotion 理論可做但成本高、品質難達標 | 短期：pipeline 出「名冊資料 JSON＋素材時間碼」交接包，CapCut 人工 gate 完成；長期再評估 remotion 模板化 |
| 8 | 轉場特效（分割畫面/白框拼貼/zoom-blur） | shot_034 99s 白框、shot_076 分割、156s zoom-blur | 🟡 | `collage`、vt_effects、remotion transitions 有對應零件；未成「轉場語彙表」 | 從本片提取轉場清單入 effect dictionary（已有 promote 機制），每個轉場一個已驗收的配方 |
| 9 | 團康/生活段選材 | 手持生活鏡頭快剪（289–343s） | 🟡 | 與 #5 同根：選材靠感知；生活素材雜訊多 | 同 #5，外加 visual_fatigue/diversity 儀器把關重複感（儀器已存在） |
| 10 | 情緒段編排（感謝/離別/沉澱） | 能量谷設計、離別三連（412–461s） | 🔴 | 這是「靈魂」本體：節奏與情緒的宏觀配置無自動能力 | 不直接自動化。做法：blueprint 記錄本片的能量弧為模板（低開→三峰遞進→谷→終曲→淡出），初剪照弧線配樂配段，人做最終品味 pass |
| 11 | 音樂設計（選曲/換曲/高潮對位/語音下鋪樂） | 至少 2 首、三高潮遞進、致詞段壓樂（能量曲線證據） | 🟡/🔴 | soundtrack-arrange/mix-audio/audio handoff 存在；缺：切歌邊界偵測、段落描述子、「情緒→選曲」判斷 | 耳朵強化三件套：(a) 自相似切歌；(b) 每段 BPM/能量/亮度/打點密度→文字描述子；(c) reviewer 拿描述子對 blueprint 判適配。選曲短期人工/曲庫 tags，CLAP 語意搜歌列未來項 |
| 12 | 片尾名冊＋logo 收尾 | 「謝謝老師」大合照＋台電 logo 白卡（554–564s） | ✅ | title-card + 靜態收尾，現有能力 | 無需新建 |
| 13 | 調色 | 全片色調統一（訓練場暖色系） | 🟡 | `grade` 子命令存在，未驗證整片一致性流程 | 低優先；先一個 LUT 全片套用＋首尾抽格比對即可 |
| 14 | 三幕宏觀結構 | 儀式→技藝→情感；點名首尾呼應 | 🟡 | story_soul_blueprint/video-intent-plan 骨架在；缺「結訓片」具體模板 | 把本片感知報告固化為第一個 film-canon blueprint 實例（章節、弧線、字卡系統、名冊收尾全部欄位化）；之後同家族片直接實例化 |

## 建議的開挖順序（成本效益排序）

1. **#6a ASR 產線化**——最便宜、收益最大（同時餵給 reviewer 的耳朵）。
2. **#3 beat-cut composer ＋ beat-vs-cut verify 儀器**——第一個「有靈魂感」的自動能力，
   且開場合照快剪是全模板家族的共用段落。
3. **#5 感知層→素材標籤→curator**——感知層接進生產線的第一個消費者，
   解「選片靠檔名」的根本問題。
4. **#14 canon blueprint 固化**——把已有的解讀變成可實例化模板，成本極低。
5. **#11 耳朵三件套**——切歌/描述子/適配判斷。
6. **#1/#2/#4/#8 字卡與轉場語彙**——effect factory 的既有路徑，批量配方化。
7. **#7 名片卡**——維持人工 gate，先不投資。
8. **#10 情緒編排**——永久保留人的最終 pass，blueprint 只提供預設弧線。

## Reviewer 粗細兩層（相關前提，供討論）

- 粗層：低密度牆（每鏡頭 1–2 格）整片掃 → 標記可疑窗。
- 細層：`segment_strip` 對可疑窗出密集條；`montage_wall.json` cell index
  即「秒→頁→格」目錄，已實作。
- 待建：reviewer 的「點菜」迴路（輸出證據請求，harness 滿足後複審）、
  機器儀器先行原則（卡點/黑幀/響度/字幕同步不給 LLM 猜）、
  雙審 diff 定位密集預算、rubric 從 canon blueprint 生成。

## 開放問題（給多方討論）

1. #6b 的 contract 語意（audio 持續、video 換軌）應該進 segment_contract
   的哪個層級——segment 屬性還是新 track 概念？
2. #3 的 beat-cut composer 歸哪條支線 owner——soundtrack-arranger 還是
   main-pipeline？（涉及 branch registry 的 owner zone）
3. 名片卡（#7）的 CapCut 交接包格式，要不要進 branch contract 正式化？
4. 通用化時機：第二個模板家族（如企業年會）何時立案——
   建議在第一支「1/2 品質」成品交付之後，避免過早抽象。
