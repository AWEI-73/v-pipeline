# Handoff: Hermes Video Pipeline v2 — Video Route Skill Project 收斂

> 目前方向：把既有 video direct flow 收斂成一套可複製、可移植、可給 Hermes 或其他 agent 平台使用的
> **Video Route Skill Project**。生成素材只保留 `source=generated` provider 介面；
> ComfyUI 目前降為 deprecated/disabled provider，實務優先 Antigravity / assistant imagegen，
> 避免低品質生成污染 route skill core。

## 開場先做

- `graphify`：用 `graphify-out/`（最新 735 節點/1034 邊/64 社群）當專案地圖。
- `decision-log`：只有當需求/架構/schema/來源政策/驗證策略改變才寫。
- 驗證（零回歸關卡）：WSL 內 `cd ~/video_pipeline && python3 -m unittest tests.test_content_qa tests.test_video_pipeline_state tests.test_video_tools_state -v`。

## Start Here（依序讀）

1. [design/video-route-skill-project.md](file:///wsl.localhost/Ubuntu-24.04/home/lio730309/video_pipeline/design/video-route-skill-project.md) — 新的總設計錨點：portable route skill project、material source contract、generated provider 邊界、dashboard 接法。
2. [roadmap.md](file:///wsl.localhost/Ubuntu-24.04/home/lio730309/video_pipeline/roadmap.md) — canonical roadmap；已整合 review reports、Graphify 架構、BUILD tool profile、Antigravity baseline 與 active roadmap。
3. [docs/superpowers/plans/2026-06-01-video-route-skill-project.md](file:///wsl.localhost/Ubuntu-24.04/home/lio730309/video_pipeline/docs/superpowers/plans/2026-06-01-video-route-skill-project.md) — 後續實作任務分解。
4. [skills/route.md](file:///wsl.localhost/Ubuntu-24.04/home/lio730309/video_pipeline/skills/route.md) — 派工 skill 契約（含 `needs_generated` 與 material source contract）。
5. [docs/decisions/2026-05-31-orchestration-state-json.md](file:///wsl.localhost/Ubuntu-24.04/home/lio730309/video_pipeline/docs/decisions/2026-05-31-orchestration-state-json.md) — 編排層三步 ADR（state.json / --only-seg / route.py）。
6. [graphify-out/GRAPH_REPORT.md](file:///wsl.localhost/Ubuntu-24.04/home/lio730309/video_pipeline/graphify-out/GRAPH_REPORT.md) — 圖譜報告。
7. Live code：`video_pipeline.py`（orchestrator）、`route.py`（dispatcher）、`video_tools.py`（ffmpeg 後端）、`content_qa.py`（VERIFY）。

## 架構：兩條正交的軸（route.md 已完整切清楚）

**軸 D — SPEC 合約層(2026-06-04 起，見 `roadmap.md` canonical roadmap):**
- **canonical = JSON**(ADR `2026-06-04-spec-canonical-json.md`);HITL 看 dashboard;YAML 降選配未做。
- **`skills/spec-contract.md`(新)** 擁有 Node 3 core+facets segment contract(每 facet 帶 `reason`)。
  facet 擁有權:director=core / writer=text_layer / audio-director=audio / effects-director=visual_style /
  curator=material_fit / director+editor=editing_grammar(Node 7)。
- **`spec_contract.py`(新,純函式 validator)**:`validate_brief`(Node 0-1)、`validate_segment_contract`
  (Node 3+7)、`suggest_fallback_route`(Node 8 誠實性守門:identity/proof 不靜默 stock/generated)+
  canonical 詞彙(FALLBACK_ROUTES 在 vt_core;EXECUTION_ROUTE_STATUS/TIMELINE_TRACKS/EDITOR_DECISIONS/
  VERIFY_STATUS/RENDER_MODES 在 spec_contract)。examples:`brief_graduation_mv.json`、`segment_contract_graduation_mv.json`。
- BUILD 層契約寫進 owning skill:editor(Node 9 assembly / 10 EDL / 13 render)、verify(Node 12 連續閘)、
  dashboard(Node 11 AI-editor review/override)、route(Node 14 revision delta)。
- **全 additive**:出片熱路徑(mv_cut/run_mv)未動,只加 SPEC 合約 + validator + skill 契約。
- **✅ Canonical-first 強連結(2026-06-04 起，見 `roadmap.md`)**:`contract_adapter.py` = canonical-first 轉接——
  `segment_contract.json`(canonical SPEC)→ `validate_segment_contract` → `contract_to_mv_script`
  (core+facets → 既有 flat MV script execution payload,每段帶 `_from_contract` trace)→ `mv_chain`(既有鏈)。
  **live 實證**:`run_contract(範例 contract, _fullpool db, music)` → mp4 8 cut、ok=True、trace[1-5] 保留。
  legacy flat script 降為「生成執行載荷」,SPEC=segment_contract.json。video-workflow.md 擁有 Node 0-14 flow
  + Light Route Contract;editor/route 標 canonical-first。**run chain 未改**。163 測綠。
  〔下一步由使用者主導:dashboard 互動編輯、Node 9-13 真實 artifact 輸出(目前是 skill 契約)、video_pipeline._FIX_TARGET 收斂。〕

**軸 A — 實作堆疊：**
- **工具層(2026-06-04 健康化:video_tools god module 3258 行→1088,degree 73→16,拆成對應 SKILL 的模組)**:
  `vt_core.py`(共用原語 FFMPEG/FFPROBE/run/YTDLP/ToolError/_audio_duration + **錯誤分類單一真相** FIX_CLASSES/FIX_TARGET/GAP)、`curator.py`(=curator:ingest/caption/material-map/match-mv)、`vt_audio.py`(=audio/subtitle-director:tts/mix/bgm/music-fetch/srt)、`vt_effects.py`(=effects-director:grade/title/kenburns/collage/montage)、`vt_verify.py`(=verify:5維QA)、`vt_dashboard.py`(=dashboard:state/serve)、`vt_editor.py`(=editor:assemble/merge)、`vt_stock.py`(Pexels 素材源)、`vt_curate_legacy.py`(舊小編,待淘汰)。`video_tools.py` 現為薄 CLI 派工層 + 基礎媒體 op,re-export 所有上述 → 呼叫點/CLI 全不變。
  - **錯誤模型對齊**:`ToolError(msg, fix_class=)` 可選分類(material/spec/human→fix_target),與 `video_pipeline.RecoverableBuildError` 同一組 key;mv_cut 已改吃 vt_core(GAP 常數 + ToolError,無 bare RuntimeError/魔術字串)。**唯一未收斂**:`video_pipeline.py`(你的 WIP)仍自帶 `_FIX_TARGET`——收斂時改 `from vt_core import FIX_TARGET` 即統一(已有對齊測試 `test_build_recoverable.FixTaxonomyAlignmentTest` 鎖住,divergence 會紅)。130 測綠。
- **skill 契約** `skills/*.md`：帶品味的角色。⟨2026-06-02 切分：編劇只寫**內容**欄位；新增**導演** `skills/director.md` 擁有**製作設計**欄位 style/media_pref/layout/bgm/effects/kind——媒材型態決策 + 配樂 brief 的新家。writer.md 已減重留指標。⟩
- **編排** `route.py`（pipeline **外**）：讀 `state.json.next_action` 派工；pipeline 維持單次確定性引擎。

**軸 C — 兩層模型分工（2026-06-03 關鍵，詳見 roadmap「兩層模型分工」）：** **大模型(Hermes/Codex/Claude)管判斷/SPEC/route**——尤其**編劇/導演的模糊消除**(vague 需求→引導 prompt→結構化架構→導演固化 YML/風格)、讀 caption 決定素材歸類/必放;**ollama qwen3-vl 只管大量看圖**(逐圖 caption、逐窗評分,不做歸類決策);機械層(ffmpeg/librosa/scenedetect)純算。素材語意歸類=兩層合作(ollama 供事實、大模型下判斷)。

**軸 B — 功能分層（2026-06-02 釐清，詳見 `skills/route.md`）：** 各 skill 落在 **SPEC**（編劇/導演/video-workflow/gap-analyzer/shooting-brief → `script.json`）/ **BUILD**（小編/剪輯/特效/音控/字幕/generative + pipeline → `final.mp4`）/ **VERIFY**（VERIFY/content_qa/precompose_gate → qa 報告）三層；`state.json` + `decision_log.json` 是**貫穿三層的稽核軌**（=DECISION LOG layer）。**route 不屬於任何功能層**，是架在三層上、讀 VERIFY 結論（經 state）決定「回哪一層、跑哪幾段」的**控制迴圈**；dashboard 是同一條稽核軌的人類讀者。**已知缺角**：route 目前只會回 BUILD 或升級人工，**不會自動回 SPEC**（叫編劇/導演改寫）——SPEC-level 修正暫走 `review`。未來可加 `revise:director/writer` fix 類別。

## 關鍵執行方式

```bash
# 完整 build（自啟/關 ollama、預熱 qwen3-vl:4b）
bash run_with_ollama.sh <script.json> --out <OUT> --verbose

# 只重渲某段（吃改過的 effects/layout，其餘段沿用上一輪渲染檔）—— 解「改一段重跑全部」
bash run_with_ollama.sh <script.json> --out <OUT> --only-seg 5 --verbose

# 派工層：學員素材到位自動接力（seg{n}_user.jpg → source=local → --only-seg n）
python3 route.py <script.json> --out <OUT> --material-dir <學員素材夾> --verbose
```

- 環境：WSL Ubuntu-24.04，home=`lio730309`，repo=`~/video_pipeline`。
- Bash 工具走 Windows → 用 `wsl -d Ubuntu-24.04 -- bash -lc "..."`；**shell 引號/變數常被吃掉**→ 複雜指令寫成 .sh 用 Write 工具落地再跑。
- ffmpeg/ffprobe 在 `/home/lio730309/.local/bin/`；ollama 在 `~/.local/ollama/bin/ollama`。
- VLM：`qwen3-vl:4b-instruct`（gate + content_qa）；8b 與 4b 共存 100% HTTPError，retry 已預設 4b。

## state.json（執行單一真相）

pipeline 末尾 `build_state()` 寫出。`script.json`=要做什麼；`state.json`=做到哪。
欄位：`pass / qa / stages[] / segments[{status(done/low/unfixable),score,fix_target,block_reason}] / blocking[] / next_action`。
`next_action ∈ null | await_material | retry:curator(seg=[…]) | review`；**blocking 優先於 pass**（帶缺口出片仍給 await_material）。

## 現況定位（中肯）

紮實、可靠、誠實的**自動中文旁白影片產生器**（幻燈片/蒙太奇模型），非影片剪輯器。
score 93-97 加權、content_alignment 74-90。stock 拍不到「特定那群人」是本質天花板
→ 由 route 的學員素材接力（source=local）補足。

## 最新長片壓測（2026-06-01）

- 腳本：`examples/graduation_5min_story_mv_script.json`，25 段結訓 story+MV。
- 產物：`/tmp/video_route_graduation_5min/final.mp4`，333.6 秒（約 5 分 34 秒），101 MB。
- 結果：pipeline exit 0、technical QA 100、qa_score 91.0，但 content_alignment 70.0；`state.next_action=await_material`。
- 素材缺口：seg6 小組討論、seg7 示範操作、seg13 成果準備、seg16 觀眾與回饋、seg19 掌聲。這些已出補拍指引並標 unfixable。
- 重要發現：如果 5 分鐘腳本使用 `media_pref=video`，現有素材挑選用腳本 `duration_sec`，不是 TTS 真實時長，會因 stock video 短於 `actual_dur + transition` hard fail。下一步應補 Longform Duration Policy：用 TTS actual duration 過濾候選，短影片自動換候選/loop/pad/photo fallback/await_material。

## 🎬 鏈現況（端到端,2026-06-03 — ⚠️ 零件齊但「尚未接成一條」）

> **接線進度(2026-06-03)**:
> - ✅ **斷點1 修好**:`run_mv(clip_list=...)` 吃 match-mv 已配 clip(caption 理解+人複核驅動),不再 live 重評。
> - ✅ **斷點3 修好**:`mv_cut.mv_chain(script, material_db, out, music)` = 單一入口,串 match-mv → render。實證:連接鏈 demo(無 live VLM)→ 93s/29cut 出片。
> - ⬜ **斷點2 仍在**:`route.py` 還是不驅動 MV(`mv_chain` 是目前的 MV 入口;route↔MV 整合優先度較低)。
> - ⚠️ tuning:match-mv 每段只挑 1 支 → montage 把 1 clip 切成多刀(該挑多支)。
> 前置:`mv_chain` 需先 `ingest-meta` + `caption-meta` 建好 material_db。

結訓 MV 各零件,標明**哪一層做 + 狀態**(✅零件可跑 / 🟡渲染待補 / ⬜待做;⛔=未接線):

```
需求(故事)
  └[大模型] video-workflow 模糊消除:引導 prompt → 架構           🟡 待升級互動式
  └[大模型] director 固化 MV YML(style/媒材/layout/必放/bgm/audio_role) ✅ schema+validate
  └[大模型] writer 設計螢幕文字層(label/narrative/subtitle/留白,選擇性)  🟡 契約✅ 渲染⬜
素材側
  └[ollama] curator ingest classify(橫直/解析度/時長) + caption(看懂每支) ✅
  └[大模型] curator 讀 caption 歸類 →(stage 集中資料夾)            🟡 stage⬜
  └ material-map 人可讀地圖                                        ✅(dashboard 待 node 化)
比對
  └ match-mv 需求×供給 → clip_list + 缺口(必放守門)               ✅ 但 ⛔clip_list 沒被 render 用
製作 BUILD
  └[機械] 音樂先 music-fetch → librosa beat → cut_grid            ✅
  └[ollama/機械] run_mv:現場 find_clips+score_windows 選段 → 必放 → plan_mv → render  ✅ 但 ⛔繞過上面 match-mv(自己又 live 評一次)
  └ 三源:stock(Pexels 橋段)/local(學員)/generated(Antigravity/assistant imagegen 外部)  ✅ stock+local / generated 你平行做
  └[機械] effects 調色轉場 / audio_role 混音 / **文字層燒入(label+name_super+ASR字幕)** ✅文字層(實幀驗證)/ 🟡混音簡化·narrative字卡⬜
VERIFY
  └ verify 5 維 QA + content_qa 對題 + 必放守門                   ✅(音訊維度⬜)
控制/檢視
  └ dashboard 人 review(run_mv 寫 state.json + build_mv_state 加料 ✅)     ✅ node-timeline 前端(SPEC→BUILD→VERIFY+段落時間),點選互動覆寫待做
  └ route ⛔不驅動 MV(只驅動舊旁白 pipeline);run_mv 目前直接呼叫
```
**已真跑出片(但走的是斷開的 run_mv 半,非接好的整鏈)**:`mv_e2e_auto.mp4` 111.8s(Pexels 開場+紀實+激勵樂+必放+鑑別力,run_mv live 評分)。模組 `mv_cut.py`、`video_tools` curator;**86 測綠**。

## Continue From（下一步）⟨2026-06-03 大改寫⟩

### ⟨2026-06-03 最新⟩ Codex review 校準 + 兩件落地
- **Codex review 確認方向**(已成 roadmap「待補強清單」優先序):①先穩**素材地圖**(地基,不追剪輯花招)②MV 走「**人可控草稿**」70-80 分→人補開場/收尾/必放/人名到 90 ③route 旁白線→MV chain ④**node-timeline dashboard=關鍵產品/工作台** ⑤CutClaw 只當 recipe。護城河:中文活動影片、必放守門、素材地圖、人補接力、route state。
- ✅ **roadmap 壓縮** 347→165 行(`00eef8d`):~15 個重疊 06-03 段收斂成北極星+兩層模型+MV-cut 現況+優先 待補強清單,P1/D 系列已完成壓成一行索引。
- ✅ **node-timeline dashboard**(`aa6ff13`,優先 #2):`build_mv_state(plan=)` 每段加料(start/dur/picked_clips/n_slots/must_include/total_dur)+ `dashboard.html` `renderTimeline()` 三層節點(SPEC/BUILD/VERIFY)+ 比例時長條,表格留摺疊。headless 驗證,94 測綠。
- ✅ **roadmap 純 dev 項目一輪掃完**(commit 5063b97→ec09c0b,113 測綠):#4 bookend 照片(find_photos/_photo_vf kenburns,run_mv 吃 photo,實 smoke 時長準)、#5 audio sidechain ducking(_mv_music_mix:duck/diegetic 讓音樂讓位)、narrative 全屏字卡、music-fetch ytsearchN+時長窗、static-window 預篩(freezedetect 無 VLM)、#6 verify audio_pairing 維度(audio_qa)、#7 route↔MV(route.py --mv 驅動 mv_chain + state 描述 must_include/bookend/review_points)。每項 TDD+實 ffmpeg smoke+個別 commit。
- ✅ **roadmap 全項目補全**(2026-06-04 接續):#3 video-workflow 互動模糊消除 skill、配音師 audio-director MV 混音計畫 skill、pacing weights、ASR 可調模型(`MV_ASR_MODEL`)、shot_stats/compare_to_gold 工具。
- ✅ **#1 素材地圖跑全池(真 live)**:ingest 302 檔 → caption **302/302 0-error**(qwen3-vl:4b)→ material-map 301 行。VLM 正確讀懂電力訓練+橫幅字 → garbage-in 解掉。db/map 在 `_fullpool/`(gitignored)。
- ✅ **#8 比 66 期(真 live)**:`mv_chain` 全池→`graduation_66_auto.mp4`(99.9s,pass=True)。**中位 cut 1.5s≈66 期 1.47s**,但 cuts/min 10.8 vs 27.5=太慢(長 hold 拉低,可用 weight/劇本調)。修了 concat 相對路徑雙重前綴 bug(早期 smoke 用絕對 /tmp 沒抓到)。
- **基礎設施**:ollama serve 必須 harness-tracked 背景跑(launching shell 退出會殺掉它,跟 nohup 同坑)。`bash _start_ollama.sh` 之類會死;用背景 runner。
- **剩(全部非阻塞 nice-to-have)**:#9 graphify 重建(現已穩定可跑 `/graphify`);montage-heavy 劇本逼近 27 cuts/min;dashboard 點選互動覆寫;curator caption→分群 stage;旁白線 route 消費 `revise:director`。

### 本 session 已完成並 commit（詳見 roadmap「已完成」+ git log）
- 旁白 pipeline 強化：Longform Duration Policy、music-fetch(真 BGM)、BUILD 可恢復化+VERIFY `fix_class`、route-state dashboard、編劇/導演拆分、SPEC/BUILD/VERIFY 分層。commit `e59834e`/`0a3e613`。
- **架構北極星：統一段落模型**（roadmap 有詳節）——段落=結構化意圖 + 可選輸出頻道(字幕=化妝/旁白聲=動時間軸) + 可插拔時間軸來源(tts/beat/fixed)。結訓=MV(無旁白)、未來單位片=旁白,**同一模型不同 toggle**。
- **MV-cut 模組 `mv_cut.py`**（commit `147d948`/`0daf6c7`/`24c9c74`）:① `beats_to_cut_grid`(librosa 拍點→切點,timeline:beat) ② `detect_shots`/`fixed_windows`(長片開窗) ③ `select_windows`(**必放守門**:必放凌駕分數、缺料回報缺口)。**46→54 測**。
- **素材入庫 `video_tools.classify_asset`**（commit `43e35f4`）:純函式漏斗 Stage1(方向/解析度/時長→usable+reasons),通用引擎+結訓預設政策。

### ⭐ 關鍵真實發現（比程式值錢，下個 session 必讀）
1. **raw 學員素材=連續長鏡頭** → 剪接偵測(ContentDetector)對它無效(預設門檻全 0、降門檻雜訊) → 用 **`fixed_windows` 開窗 + VLM 選段**,不是 shot detection。
2. **過濾只砍 16%**(88 影片→74 usable);直式是非問題(只 2)。**真瓶頸是選段(110 分鐘→5 分鐘)**,不是過濾。
3. **必要性凌駕品質/分數**:所長(score 低)必放、隊呼(720p)若必放就不能被 res 過濾誤殺 → 機械過濾只「標記」,排除決定權在選段層。這條原則貫穿 `select_windows` + `classify_asset`。

### ⭐ 對照組（gold standard，評估 auto-MV 用）
`~/.hermes/profiles/video_director/vault/66期養成班-高訓結訓影片全OK.mp4` = **人工剪好的 66 期結訓片**(同事件同素材池)。比 CutClaw 更適合當品質基準。`detect_shots` 在這支(剪過的)會 work → 可量出人工版的剪輯節奏(shot 數/平均長度/cuts per min)當我們的目標。素材原始檔在 `C:\Users\user\Downloads\微電影素材`(15GB/88 影片/214 照片/136 資料夾,8 個 Takeout 分卷)。

### 路線決策（已定）
- **用 permissive lib 自己重寫,不抄 repo**:CutClaw(無授權)/montage-ai(非商用)/OpenMontage(AGPL)都不適合當地基。lib:librosa(ISC)/PySceneDetect(BSD)。**CutClaw 只在做選段時讀核心 ~5 檔當「配方參考」**,不抄碼。
- 依賴:**librosa 0.11 + scenedetect 已裝**於 `~/.local`(Ubuntu 24.04 PEP668 → `pip install --user --break-system-packages`)。

### 剩餘待辦（依優先）
- **MV-cut v0 機制完成 ①②③④**(`mv_cut.py`,61 測):raw→開窗→真 VLM 選段→必放守門→對拍 renderer,第一支自動剪 MV 出片(11.8s/8cut/~1.5s per cut 對上 66 期)。**但 v0 smoke 沒劇本→全 100 分→沒鑑別力**(見 roadmap「v0 smoke 誠實檢討」)。
  - **下一步(優先於 ⑤)= 劇本驅動測試**:寫真 MV 劇本(段×visual_desc×must_include×音樂brief×style)→ per-段 desc 評窗才有鑑別力 → 比 66 期。
  - **音樂先定**(MV 專屬):導演出音樂 brief→音控師 music-fetch+mix;音樂 tempo 定 cut_grid,要最先選(結訓要熱血,非鋼琴 placeholder)。
  - 選段現在=對題 gate 非 best-moment ranker → 待接動態/銳利度預篩。
  - ⑤ 必放 VERIFY 整合(把 select_windows 的 unfilled 接成缺口報告/await_material)。
- **素材漏斗**:① classify_asset 接進 `cmd_ingest_meta`(產 material_db,輸出指定 repo 非 Downloads) ② window 動態/銳利度預篩(ffmpeg 無 VLM,clean-but-abundant 的真便宜過濾器) ③ 資料夾→劇本需求 scoping(rank-local)。
- **旁白線收尾**:route.py 消費 `revise:director`(但 spec 分類器尚無觸發源)、全候選 reject 的 legacy top-text fallback 改誠實 route、純音樂段 `kind:"music"`、Jamendo client_id。
- **graphify**:等 MV-cut v0(①~⑤)穩定再重建(現在 mid-build,圖會即時過時;roadmap/HANDOFF 是當前更新的地圖)。
- **後期**:高特效 layer(Remotion/AE)等核心穩定後。

## Do Not Do

- 別把 `comfy_client.py`/`test_comfy.py`/`install_comfy.ps1`/`txt2img_workflow.json` 掃進 commit（使用者的 ComfyUI WIP，現已 deprecated/disabled，應獨立成另一個 project）。
- 別 commit `*_out/`、`materials/`、`student_uploads/`、`bgm/*.mp3`、`raw/` 等產物（graphify 也只吃 git-tracked 原始碼）。
- 公開 push 前：API key 雖已改 `.env` loader，但**仍在 git 歷史**，需先 rotate/rewrite。
- 別強制無限 retry；靠 `unfixable` 逃生輸出補拍指引、exit 0。
- 別用 `--mode deep` 或對整個 repo 跑 graphify（會掃進 1900+ 素材檔）；scope 限 git-tracked source。

## 最近 commit（git log）

```
0f3b3a4 chore(graphify): re-converge knowledge graph with orchestration layer
51068e3 feat(orchestration): route.py state-driven dispatcher (step 3/3)
aba8f4d feat(orchestration): --only-seg targeted re-render (step 2/3)
f18fb57 feat(orchestration): state.json single-truth (observation-first, step 1/3)
0aaffe3 fix(montage): trim concat to exact target duration
39e31a5 feat(montage): 快切蒙太奇 layout
```
