---
title: Hermes Video Pipeline — Canonical Roadmap
type: project
status: active
updated: 2026-06-12
tags: [project, video, pipeline, roadmap, agent-workflow]
---

# Hermes Video Pipeline — Canonical Roadmap

> 本文件是專案唯一長期 roadmap。過去的 `REVIEW_REPORT*`、`video_pipeline_architect_review.md`
> 與 `HANDOFF_NEXT_SESSION.md` 的有效結論已整合到這裡；後續 agent 優先讀本檔、
> `HANDOFF_CURRENT.md`、`RUNBOOK.md`、`README.md`。

---

## 2026-06-12 Active Direction: Sensory Phase(感官層攻堅,S1-S4)

**現況診斷(SYSTEM-DESIGN.md + 外部評析裁決後)**:結構層(soul/選材/宏觀節奏
~70-80%)已接近水準;**感官層(畫面內表現力 ~40%、微節奏 ~45%、音訊質感 ~50%)**
是觀眾直接感受的缺口。目標:S1-S3 完成並真片驗收後跨過「看不出自動生成」線。
本節**取代原 E2「配方庫」定義**——驗收問句從「有沒有特效」改成「簡報感偵測器
還響不響」。每項附:改哪裡、用什麼現成零件、完成判準。

### S1 反簡報感引擎(最優先;雙態:計畫期預防 + 渲染後審計)

```text
S1a presentation_feel_audit.py(新模組,確定性,Node 12 audit 家族)
    六個偵測器(全可機械判):
      static_photo_too_long      靜照單窗 > max_still_hold(editing_policy 已有此值)
      no_foreground_motion       畫面動能低:幀差 RMS——改裝 filter_static_windows
                                 (mv_cut)的現成幀差機具,對 timeline 各 clip 抽測
      centered_caption_card      字卡置中且文字框佔幅 > 25%:從 ASS 樣式/字卡
                                 參數推算(subtitle_presentation/motion_graphics)
      repeated_push_in           連續 >=3 個同向運鏡:讀 timeline 的 still_treatment
                                 / zoompan mode 序列(P5 已記錄 mode)
      text_blocks_dominate       同屏文字行數/佔幅超限
      single_layer_composition   連續 >=N clip 無任何 overlay/text/效果層
    輸出 presentation_feel_audit.json{findings, score},接 dashboard Node 12,
    跟 visual_fatigue 同款接線(edit_artifacts/dashboard_state 照抄它的 wiring)。
S1b 計畫期預防(Node 9,edit_artifacts/_resolve_seg_treatment 一帶):
    偵測條件在排程時就換補救,優先用現成零件:
      靜照過長        → P5 照片多幕拆 2-3 個 crop 拍點(_windows_from_clip 照片支)
      置中字卡        → lower-third 配方(E2 文字配方已有)
      連續同向運鏡    → 運鏡輪替盤:slow_push/pan_left/pan_right/hold 輪換
                        (P5 的 modes 表已存在,改成「不重複上一段」即可)
    完成判準:city-lite 重跑,S1a 偵測器 0 fail;對照舊片至少 3 個偵測器原本會響。
```

S1a status (2026-06-12): COMPLETE. Deterministic audit, Node 12 wiring,
dual-baseline real renders, sensory review, and full regression are verified.
See `docs/decisions/2026-06-12-s1a-presentation-feel-audit.md`. Next: S1b.

S1b status (2026-06-12): COMPLETE. Node 9 now emits deterministic
anti-presentation plans for long still rotation and centered narrative
lower-thirds; the directives reach both the base renderer and light-effects
motion-graphics path. Dual-baseline real renders, sensory review, 0-fail S1a
audits, and full regression are verified. See
`docs/decisions/2026-06-12-s1b-anti-presentation-planning.md`. Next: S2.

### S2 微節奏(cut-on-motion / J-L cut / 口白呼吸)

```text
S2a cut-on-motion:切點吸附「動作峰值」。現有 _snap_to_scene_cut(edit_artifacts)
    只吸場景邊界;新增 motion-peak 偵測(幀差能量序列的局部極大,同 S1a 機具),
    建 timeline 時 scene-cut 與 motion-peak 雙吸附(scene 優先,峰值次之)。
S2b J/L cut(narrative 鏈):轉場處音訊先行/延後 0.3-0.7s。落點在 narrative 渲染
    的段間接縫(video_pipeline xfade/concat 段),純 timeline 位移,不碰素材。
S2c 口白呼吸:句尾後留 0.3-0.5s 再切。TTS timing(audio/tts_timing.json)已有
    句界;在段長計算時加 tail padding。
    完成判準:city-lite 級口白片重跑,抽 3 個轉場人眼/耳驗收(agent 讀波形+幀)。
```

S2a status (2026-06-12): COMPLETE. Deterministic frame-difference motion peaks,
scene-first/motion-second snap precedence, pre-render concrete-plan snapping,
source-duration safety, Node 10 trace, dual-baseline real renders, and sensory
review are verified. See
`docs/decisions/2026-06-12-s2a-cut-on-motion.md`. Next: S2b.

S2b status (2026-06-12): COMPLETE. Narrative renders now alternate deterministic
0.5s J/L visual seams around unchanged TTS boundaries, persist the plan in
timing/edit artifacts, budget chained-xfade tail correctly, and trim to the
voice duration. City-lite narrative true render, three seam waveform/frame A/B
checks, and full regression are verified. See
`docs/decisions/2026-06-12-s2b-narrative-jl-cuts.md`. Next: S2c.

### S3 音訊感官層(SFX 標點 + 音樂結構對位)

```text
S3a SFX 標點:小型本地音效庫(assets/sfx/,whoosh/hit/riser 各 2-3 支,CC0)。
    確定性落點:章節轉場=whoosh、字卡進場=hit;混進 final_audio(vt_audio,
    與 BGM 同一 amix 圖,音量 ~0.15)。
S3b 音樂結構對位:消費 music_structure.sections(欄位早就有、render 不讀):
    最低版=BGM 從最近的結構點起播(offset),高潮段(climax role)對到能量段。
    多軌換曲不在本階段(backlog 不變)。
    完成判準:同一支片 A/B(有無 S3)各渲一次,agent 聽感複核記錄差異。
```

### S4 裁決體系收尾(採納外部評析 A + creative_exception)

```text
S4a VISUAL_JUDGE 升一級節點:進 node_registry(建議 node id "10.5" 字串,
    NODE_ORDER 插在 10 與 11 之間),verify_fn 讀 visual_review_request/verdict
    存在性與狀態;dashboard 自然顯示。E6 機具不動,只是掛牌。
S4b verdict 增加 needs_patch 裁決(現只有 accept/reject):
    {action:"needs_patch", patch:{type:"window|crop|treatment", hint:{...}}}
    引擎消費:window→改 extract 窗重建;crop→改 crop_center;treatment→改
    still_treatment。visual_review.py 的 validate/consume 兩端同步擴。
S4c creative_exception 統一欄位(segment 級):
    {"creative_exception":{"rule_bent":"...","reason":"...","risk":"...",
     "requires_review":true}}
    消費端:spec_review/pacing_review/visual_fatigue/presentation_feel 遇到
    違規但該段有對應 exception → 降為 warn-with-ack(進 review 清單,不 block)。
    把現有零星豁免(allow_long_hold_when/hold_reason)歸一到這個語法之下
    (向後相容保留舊欄位)。
```

### 執行紀律(防彎路,給 Codex)

```text
1. 順序固定 S1a→S1b→S2→S3→S4,每個子項獨立 commit + 測試;不要並行開兩項。
2. 每項「完成」= 真片重渲 + agent 讀圖/聽感複核 + 確定性測試,三者缺一不可
   (PlayRes 教訓:單元測試看不到感官缺陷)。
3. 新偵測器/補救一律走既有 wiring 模式(visual_fatigue 是範本),不發明新接線。
4. 不碰:多軌換曲、雲端 API、NLE UI、remotion/blender(non-goals 不變)。
5. 基準片:city-lite(口白)+ skill-smoke(MV)雙基準,改前改後都要有對照。
```

---

## 🔄 2026-06-12(被 Sensory Phase 取代/吸收): Effects Phase(特效區)

前一階段(P1-P6 + city-lite 合併驗證)已收;本階段在 Codex 鋪好的 motion_graphics
鷹架上**填表現力內容**,不再搭地基。

### Backend 階梯(build_profile.motion_graphics_backend)

```text
ffmpeg_libass   ✅ 已實作(ASS 疊加+render plan+實渲 smoke)— 本階段主力
                字卡動畫 / lower-thirds / 進度標籤 / 強調字
html_playwright ✅ MVP 已走通:HTML/CSS/JS 動畫(web 是最豐富的 2D motion
                語彙:字體/easing/SVG/canvas)→ Playwright 無頭截幀/錄製
                → ffmpeg overlay。適合資訊圖形:動態圖表/infobox/計數器。
remotion / mlt / blender  ❄️ enum 已留位,非本階段目標(重武器,等需求證明)。
```

### 工作順序

```text
E1 基準片開燈:city-lite / skill-smoke 以 render_profile=light_effects 重跑,
   逼出現有 effects 鏈在真片上的視覺問題(同 city-lite 字幕 PlayRes 教訓:
   單元測試看不到視覺缺陷,每個配方都要真渲+看圖)。
E2 ffmpeg_libass 配方庫:title card 進出場動畫、lower-third、段落標籤、
   強調字卡——全部走 editorial_design.effects_strategy 宣告,服務段落功能
   (鐵則:特效服務功能,非裝飾;effects-director 擁有品味)。
E3 P2 分配端補完:BUILD 切刀消費 attention_budget。✅ 2026-06-12 完成,
   特效節奏與注意力預算同源。
E4 html_playwright MVP:一個配方(動態數字/infobox)走通。✅ 2026-06-12 完成
   HTML→Playwright→序列幀→overlay 全鏈,建立第二 backend 的 verify 模式。
E5 P4 收尾:CapCut GUI 載入驗證(人工閘)。✅ 2026-06-12 完成
E6 agent-as-visual-judge V1:stock 選窗改成 evidence → await_visual_review
   → agent verdict → resume；保留 ollama/none 降級模式。🚧 施工中
E7 素材蒙太奇理解:每支長素材先產生場景中點+時間戳 montage，由 agent
   寫回可重用語意地圖，取代逐窗弱模型誤殺。
E8 agent-judge 擴展:將 E6 模式延伸到 narrative prepick 與 Node 12
   content/editorial QA，整個 run 合併成單次人工/agent gate。

每個 E 完成判準:真渲輸出 + keyframe 人眼複核 + P1 audits 通過 + 測試。
```

### 2026-06-11 E1 執行狀態

E1 已完成 `skill-smoke` 真實 light-effects baseline：

- real render 與 VERIFY 通過：91.5；
- timeline/caption/broll/visual P1 audits 通過，keyframe grid 已人眼複核；
- 新增 `light_effects_baseline_review.json` 與 dashboard Node 14 gap 顯示；
- 實測結果：7 planned effects、0 rendered effects、0% effect coverage。

E2 優先順序因此確定為：先接通 title card / section label /
lower-third 等文字型 ffmpeg/libass 配方，再處理 xfade 與 Ken Burns。
證據與決策見
`docs/decisions/2026-06-11-effects-baseline-and-recipe-order.md`。

### 2026-06-11 E2 文字配方執行狀態

E2 第一段已完成並通過真實影片驗證：

- title sequence、section label、lower-third 共 3 個 ffmpeg/libass 配方已真正合成；
- renderer ownership 已明確化：light-effects / motion-graphics profile 保留文字 trace，
  但由 motion-graphics compositor 單獨負責可見文字，避免 base drawtext 重複燒入；
- real render、VERIFY 91.5、P1 audits 與 keyframe 人眼複核皆通過；
- effects contract 語意已修正：hold video 不等於 Ken Burns，beat/direct cut 不等於
  xfade；photo Ken Burns 則會從 MV renderer 回寫真實 evidence；
- 修正後 real baseline 為 3 planned / 3 composited / 0 gaps / PASS。

E2 explicit xfade 已完成：專用 fixture 只在明確宣告 `transition: xfade`
時接通 ffmpeg `xfade` / `acrossfade`，timeline 將宣告時長建模為 intentional
overlap；不可由 montage/fast 隱式推斷。

真實驗證：
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260611-effects-e2-explicit-xfade-v6`

- VERIFY 92.5 PASS；duration/subtitle/technical quality 均 100；
- light-effects baseline 4 planned / 4 rendered / 0 gaps / PASS；
- timeline/caption/broll/visual audits 全部 PASS；
- xfade boundary grid 確認 0.5 秒 crossfade 實際可見；
- caption SRT 只包含 narrative/subtitle，不再把 label/name super 當字幕。

E2 ffmpeg/libass light-effects baseline 已關閉；下一步依 roadmap 進入 E3
attention budget / pacing enforcement。

### 2026-06-12 E3 attention-budget BUILD allocation

E3 已完成 Node 9 → BUILD → Node 10 接線：

- `contract_adapter` 在 render 前用 Node 9 assembly plan 回填每段
  `attention_budget`；
- 修正 `audio.role: music` 被誤判為 narration mode 的語意錯誤；
- 純音樂一般段使用 `[1.5, 4.0]`，高能音樂使用 `[0.8, 2.0]`；
- music/visual owner 會覆寫 generic hold / 舊慢 pacing，opening/closing/title
  與 narration-owned hold 保留；
- render plan 與 `timeline_build` 保留實際消費的 attention-budget trace。

真實驗證：
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-e3-attention-budget-v2`

- seg2：6 → 8 shots，median 3.532s → 2.649s；
- seg3：8 → 12 shots，median 4.238s → 2.825s；
- total cuts：16 → 22；opening/closing 仍各 1 shot；
- VERIFY 92.5 PASS，所有 P1 audits 與 light-effects baseline PASS。

E3 關閉。

### 2026-06-12 E4 html_playwright MVP

E4 已完成第二個可實渲 motion-graphics backend：

- `info_card` 會產生 deterministic HTML，透過 Python Playwright 與系統
  Chrome 逐幀截取透明 PNG；
- 序列幀由 ffmpeg 編成 alpha qtrle MOV，再依宣告的 `start_sec`
  疊加回主影片；
- manifest 保留 HTML、frames、overlay、frame count 與 composited 狀態；
- safe backend dispatcher 固定先處理 `ffmpeg_libass`，再處理
  `html_playwright`；
- 1080p info card 最低寬度 620px，主數字 150px、副標 40px，避免真片不可讀。

真實驗證：
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-e4-html-playwright-v2`

- Playwright 實際截取 30 幀，alpha overlay 與最終影片皆成功產生；
- manifest output 為 `composited`；
- contact sheet 與 1080p midpoint 已人眼複核：淡入/停留/淡出正常，
  lower-third 字卡清楚且無裁切。

E4 關閉；下一步依 roadmap 進入 E5 CapCut GUI 載入人工閘。

### 2026-06-12 E5 CapCut GUI gate 執行狀態

已建立待驗專案：
`C:\Users\user\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\20260612-e5-text-audio-gate`

- draft JSON 含 2 個 video segments、2 個 editable text segments、1 個 audio
  segment；
- video/audio 素材路徑有效；
- smoke 證據位於
  `C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-e5-capcut-gui-gate-v1`。

CapCut 8.7.0.3685 GUI 載入驗證已通過：

- 實際開啟 `20260612-e5-text-audio-gate`，無載入錯誤；
- 時間軸顯示兩段 editable text：`E5 TEXT TRACK`、`AUDIO + TEXT LOADED`；
- 時間軸顯示一條 audio 軌與兩段 video 軌；
- 預覽畫面成功顯示文字覆蓋。

E5 關閉；P4 CapCut text/audio draft bridge 已完成 JSON 與 GUI 雙層驗證。

### 2026-06-12 H2 music resolver hygiene

- `_resolve_music_path` 不再掃描 repo root 或 project root 的任意音訊；
- 自動解析只接受明確 `args.music`、`run_dir/bgm.*`、`project/input/*`，
  否則依 contract `music.query` 抓取；
- repo-root 流浪 mp3 已搬至
  `C:\Users\user\Desktop\video_project\recovered_media\stray_repo_audio`。

H2 關閉；下一步依 E6 實作 agent-as-visual-judge V1。

---

## ✅ 2026-06-11: Expressiveness & Chain Merge — 已執行(P1-P6)

> 狀態:P1 ✅(含 city-lite 視覺驗證後的 PlayRes/斷行修正 `4d08a88`)、
> P2 🟡(審計端完成;BUILD 分配端 → 特效區 E3)、P3 ✅(city-lite canonical
> contract→narrative E2E,qa 97)、P4 🟡(draft JSON 完成;GUI 載入閘 → E5)、
> P5 ✅、P6 ✅(鷹架+smoke)。合併驗證與合約寫法教訓見
> `docs/decisions/2026-06-11-e2e-smokes-and-next-phase.md` 與 skills/spec-contract.md。

### 原計畫(留供追溯)


**收斂(下節 C0-C6)已達成 DoD**:統一 driver(route.py 退役)、spec_review
pre-BUILD gate、render-free dry-build、兩支真實 E2E 通過
(skill-smoke MV 35s → verify 91.5 PASS / editorial_qa 94;
city-day narrative 5min 21 段 → 全鏈含 TTS 口白+BGM+VLM gate 跑通)、516 tests OK。
證據:git log 2026-06-10/11 + `docs/decisions/2026-06-11-e2e-smokes-and-next-phase.md`。

下一階段的核心不是更多 gate,是**「感受」**:結構層(切什麼/切多快)已被消化,
表現層(畫面內動態/合成/字幕美感)是新的天花板。優先序:

```text
P1 字幕 polish(確定性,~1 天)
   中下置中、標點清洗(換全形空格)、字級隨解析度、單行 14-16 全形字、最多兩行。
   進 editorial_design.subtitle_strategy 預設 + subtitle-director 燒錄工具。
P2 注意力預算 pacing(把使用者校準值編碼進規格)
   「哪個通道在說故事,哪個通道就拿時間」:segment 級 hold 預算 =
   f(口白有無, 素材動態程度, 音樂能量)。靜照無特效 1-2s、堆疊 1s/2 張=快、
   口白段可 hold 長、純音樂段必須快剪。升級 pacing_review / visual_fatigue。
P3 canonical contract → narrative 鏈合流(根治入口不對稱)
   contract 加 narration facet → 一份 SPEC 餵兩條鏈;video_pipeline.py 變成
   runtime 底下的 narrative runner(不是廢棄——它是引擎,缺的是 adapter)。
   順帶把 spec_review/soul 層帶給口白片。
P4 CapCut draft 補 text/audio 軌(Half-baked Bridge 補完)
   BGM/字幕/outro 直接進 draft,讓人在剪映裡能調,而非匯出後 ffmpeg 強行 finalize。
   參考 NarratoAI jianying_draft_builder(僅技法,非商用授權禁複製,
   見 docs/reference-repos-map.md)。
P5 照片多幕展開器(一張照片 → 多個 crop/push 鏡頭)
   同 multi-window 的「素材是庫」原則用在靜照;crop 座標+zoom 路徑純確定性,
   VLM 挑焦點。省素材、好 review。
P6 表現層/motion_graphics backend(「PPT 感」天花板)
   light_effects → motion_graphics 的實作期;effects-director 接 Node 14。

Opt-in(非預設):雲端 VLM 仲裁走 model_routes(local-first 政策不變;
4b 蒸餾救援後仍判離題的段才升級仲裁)。

Non-goals 延續:不做完整 NLE UI(用 dashboard + 寫回按鈕做「審查+補丁面板」:
換候選→only-seg 重渲、拖 in/out→改窗重渲、結構調整→Node 14 revision);
不預設雲端 API。
```

---

### 2026-06-11 執行證據(Codex 批次)

The current P1-P6 implementation direction is complete:

- P1 subtitle polish: shared presentation policy, punctuation/line wrapping, bottom-center styling.
- P2 attention-budget pacing: narration/music/visual ownership and visual-fatigue integration (audit-side; BUILD allocation does not consume it yet).
- P3 canonical contract to narrative chain: traceable narrative adapter and runtime routing.
- P4 CapCut text/audio tracks: editable text tracks and explicit BGM/audio tracks in real drafts (JSON-level done; CapCut GUI load verification is a pending human/CU gate).
- P5 photo multi-shot expander: one photo expands into distinct push/pan/detail shots with timeline trace.
- P6 motion graphics backend: canonical timeline to Node 14 contract/plan and rendered ffmpeg/libass overlays.

Verification evidence:

- Full suite: `python -m unittest discover -s tests` -> 541 tests OK.
- P5 real ffmpeg smoke: one photo rendered as slow-push, pan-right, and detail-push shots.
- P6 real ffmpeg/libass smoke: generated ASS overlay rendered into a playable 2-second MP4.

Dashboard Build Control Surface is complete:

- dashboard state exposes a read-only `controls` contract for profile, generated
  asset status, and route/next-action;
- every node exposes absolute links for artifacts that actually exist;
- self-contained dashboard/story-map output embeds the control contract.

C6 hygiene is complete:

- `.understand-anything/` remains ignored local exploration output;
- `graphify-out/` remains the accepted project map;
- `.graphifyignore` keeps external reference repositories, generated media, and
  run outputs outside the formal project map;
- `HANDOFF_CURRENT.md` and `RUNBOOK.md` point to the current Windows state.

Graphify was refreshed once after P1-P6 stabilized: 104 code files produced
1,734 nodes and 2,575 edges. The clean source-only rebuild contains the new
attention-budget, subtitle-presentation, motion-graphics, photo multi-shot, and
dashboard-state modules; retired `route.py` and `reference repo/` have zero
source nodes.

---

## ✅ 2026-06-08(已完成 2026-06-11): Converge One Complete Pipeline

The next work is **pipeline convergence**, not more tool expansion. Treat this
section as the current source of truth for Claude/Hermes/Codex implementation.
Older roadmap sections are historical context unless they directly support this
convergence work.

Both render paths have passed E2E:

```text
ffmpeg canonical path:
  SPEC -> contract-run/runtime -> final.mp4 -> VERIFY/P1 audits -> PASS

CapCut optional finishing path:
  SPEC -> contract-run/runtime -> real CapCut draft -> human/CU GUI export
  -> capcut-finalize -> final video -> VERIFY/P1 audits -> PASS
```

The remaining problem is not whether the tools can work. The problem is that the
workflow is still spread across too many partially connected entrypoints. The
goal is one coherent, repeatable run chain from SPEC to final verified output.

### Target MVP Flow

```text
Node 0  Brief / interactive SPEC
-> Node 3  segment_contract.json
-> Node 2  material coverage / material requirements
-> Node 4-7 contract facets: story, sound, effects, subtitles
-> Node 8  build_profile.json
-> Node 9  assembly_plan.json
-> Node 10 timeline_build.json
-> Node 11 editor_review + deterministic audits
-> Node 13 render candidate
   -> ffmpeg path: final.mp4
   -> CapCut path: draft folder -> capcut_exported.mp4 -> capcut-finalize
-> Node 12 verify_result + P1 audit pack
-> Node 14 revision only when verify/audit fails
```

### Priority Order For Claude / Agents

Do these in order. Do not start Remotion, HTML/Playwright, Blender, or new
provider work before this list is complete.

#### C0. SPEC Entry And Execution-Readiness Gate

Review:
The canonical public SPEC is `segment_contract.json`, but the complete route must
start from an interactive brief and remove ambiguity before BUILD. Runtime must
not silently invent missing story/material/audio/effects/subtitle decisions.
The editing-quality contract for this step is
`docs/editing-intent-sequence-grammar-spec.md`.
That spec also defines Node 12 `editorial_qa.json`, reviewed by the main flow
agent/strong model rather than a subagent.

Build:
- Define one supported greenfield entry:

```text
interactive brief
-> editorial_design.json
-> brief.json
-> segment_contract.json
-> contract validation
-> material requirements / coverage
-> build_profile.json
-> ready_for_build
```

- Keep `segment_contract.json` provider/backend neutral.
- Record unresolved questions and required human decisions explicitly.
- Convert Pre-SPEC editorial choices into BUILD-consumable plans, not just
  descriptive prose.
- Produce an execution-readiness result before runtime enters BUILD:

```text
ready_for_build = true | false
blocking = [...]
next_action = revise:director | await_material | ready
```

- Ensure each segment has enough executable intent:
  - story purpose / content;
  - required or acceptable material;
  - text/subtitle/narration intent;
  - audio intent;
  - effects intent or explicit `none`;
  - fallback policy;
  - verification-sensitive requirements.

Verify:
- One general SPEC example reaches `ready_for_build=true`.
- One intentionally ambiguous example is blocked with actionable questions.
- Contract validation remains independent of ffmpeg/CapCut/provider selection.

#### C1. Runtime Route Unification

Review:
Runtime can resume, rerun, compile, verify, and handle some material/generated
provider waits. CapCut export/finalize must become a first-class route instead
of a hidden manual step.

Build:
- Add a route for `render_backend=capcut_draft`.
- After `contract-run` writes the CapCut draft, runtime should pause clearly:

```text
next_action = await_capcut_export
expected artifact = capcut_exported.mp4
instruction = open CapCut, export to this run folder, then resume
```

- On resume, if `capcut_exported.mp4` exists:
  - write/update `capcut_export_manifest.json`;
  - run `video_tools.py capcut-finalize`;
  - produce the canonical post-CapCut final artifact;
  - continue to Node 12 verify.

Verify:
- Unit test `await_capcut_export` with and without `capcut_exported.mp4`.
- Regression test that the default ffmpeg path is unchanged.
- Focused smoke on the `coffee` run.

#### C2. Artifact Contract Cleanup

Review:
Artifacts exist, but final naming must be strict across ffmpeg and CapCut so
agents do not guess which file is final.

Build:
Define one run artifact contract:

```text
final.mp4                  canonical accepted final candidate
capcut_exported.mp4        raw GUI export, never accepted directly
capcut_finalized.mp4       optional post-CapCut intermediate if needed
capcut_export_manifest.json
artifact_manifest.json     indexes all of the above
state.json                 carries pass/next_action
```

If `capcut-finalize` writes a different name today, either standardize it or
record it explicitly in `artifact_manifest.json` and dashboard state.

Verify:
- Manifest tests assert both render paths expose the same final artifact surface.
- Dashboard state shows which backend produced the final.

#### C3. Node / Skill / Runtime Alignment

Review:
Node registry is good enough, but CapCut introduced a human/CU gate that should
be visible as a controlled Node 13 route.

Build:
- Keep Node 13 as `Render Candidate`.
- Treat CapCut GUI export as a Node 13 sub-state, not a new core node unless
  absolutely necessary.
- Make dashboard/runtime show:

```text
Node 13: Render Candidate
  backend: ffmpeg | capcut_draft
  status: running | awaiting_export | exported | finalized
  artifacts: capcut_draft_manifest, capcut_export_manifest, final.mp4
```

Verify:
- `runtime.py status --project coffee` makes the next action obvious.
- No hidden manual step should be required outside the status text/runbook.

#### C4. One Runbook

Review:
The project has many historical documents. Claude and Hermes need one current
runbook for the MVP, not a search exercise.

Build:
Update `RUNBOOK.md` with exactly these flows:

```text
Flow A: ffmpeg default
  project-init -> project-new-run -> runtime resume -> verify

Flow B: CapCut finishing
  build_profile.render_backend=capcut_draft
  runtime resume -> open CapCut -> export capcut_exported.mp4
  runtime resume -> capcut-finalize -> verify

Flow C: rerun / revision
  rerun node -> verify failed -> fix smallest affected node -> resume
```

Verify:
- Commands are copy/pasteable on Windows PowerShell.
- Do not use WSL paths except as reference notes.

#### C5. Dashboard Minimum Control Surface

Review:
Dashboard should remain read-first. This is not a cinematic director UI.

Build:
Add only controls/status needed for the converged MVP:

```text
current project/run
active backend
node status
next_action
open key artifacts
CapCut export instruction when awaiting_export
verify score and audit findings
editorial_qa summary and routed findings
```

Do not add cinematic shot controls, Remotion controls, Blender controls, or
large parameter panels.

Verify:
- Dashboard generated from ffmpeg run and CapCut run.
- Text makes the next action clear without reading JSON.

#### C6. Graphify / Understand Anything Hygiene

Review:
Graphify is the project map; Understand Anything is useful exploration output.
Neither should pollute the canonical source tree unless intentionally curated.

Build:
- Keep `graphify-out/` only as the accepted project map.
- Decide whether `.understand-anything/` is ignored local exploration output or
  curated into stable docs.
- Do not commit UA cache/intermediate files by default.

Verify:
- `git status --short` should not show accidental knowledge-cache output.
- If graphify is stale after convergence changes, update it once after code is
  stable.

### Explicit Non-Goals During Convergence

```text
Remotion backend
HTML/Playwright render backend
Blender / AE / heavy 3D effects
new cinematic director UI
new provider-specific SPEC fields
new generated-image provider architecture
large dashboard redesign
```

### Definition Of Done

Convergence is complete when:

```text
1. A new project can start from SPEC and reach PASS via ffmpeg.
2. The same or representative project can reach PASS via CapCut finishing.
3. runtime.py status/resume/rerun explains every next_action.
4. artifact_manifest.json is complete for both paths.
5. dashboard shows backend, artifacts, verify, and next action.
6. RUNBOOK.md has copy/paste Windows commands.
7. Full unit suite passes.
8. HANDOFF_CURRENT.md points to this convergence state.
```

## ✅ 2026-06-06(已完成): Windows Native Migration

The active development project has moved to Windows:

```text
Primary development project:
  C:\Users\user\Desktop\video_pipeline

Windows project/output root:
  C:\Users\user\Desktop\video_project

Example project:
  C:\Users\user\Desktop\video_project\coffee

WSL reference implementation:
  \\wsl$\Ubuntu-24.04\home\lio730309\video_pipeline
```

Windows is now the primary development target. The WSL project remains a
reference implementation and regression comparison source during migration. Do
not continue feature development independently in both copies.

Migration must be seamless and incremental:

```text
preserve canonical SPEC/artifact contracts
-> replace one Linux assumption at a time
-> run focused Windows verification
-> compare behavior with WSL when relevant
-> run broader Windows regression tests
-> continue to the next migration step
```

The implementation source for this migration is:

```text
docs/windows-native-migration-spec.md
```

Current Windows baseline:

```text
Python 3.10.16
video_tools.py --help: pass
All Windows unit tests: 255 tests pass (100% success)
Windows project_workspace focused verification: pass (paths normalized to POSIX style)
Full native video runtime: verified (W5 canonical no-effects E2E completed successfully)
Dashboard, state, and story-map monitoring: verified (W6 completed successfully)
Graphify: rebuilt successfully on Windows (W7 completed successfully)
```

Migration priority:

```text
W0 establish Windows source/output boundaries -> [Completed]
W1 add cross-platform tool/path resolver -> [Completed]
W2 remove hardcoded WSL/Linux paths -> [Completed]
W3 replace bash-only orchestration with Python runtime -> [Completed]
W4 verify ffmpeg/ffprobe/yt-dlp/Ollama on Windows -> [Completed]
W5 run canonical no-effects E2E on Windows -> [Completed]
W6 verify route/dashboard/project monitoring -> [Completed]
W7 rebuild Graphify from the stable Windows source tree -> [Completed]
```

Do not rebuild Graphify before the Windows runtime boundaries stabilize. The
existing WSL graph remains a historical architecture reference, not the current
Windows source-of-truth graph.

## ✅ 2026-06-07(已完成): Editing and VERIFY Tool Pack

Approved integration reference:

```text
https://github.com/Hao0321/video-autopilot-kit
```

The external MIT-licensed repository is a technique/tool reference, not a new
workflow owner. The canonical implementation spec and execution plan are:

```text
docs/video-autopilot-tool-integration-spec.md
docs/superpowers/plans/2026-06-07-video-autopilot-tool-integration.md
```

Implementation order:

```text
P1-A deterministic audits                                         [Completed 2026-06-07]
  timeline invariants      -> timeline_invariants.json (Node 11)
  B-roll ratio/repetition  -> broll_audit.json (Node 11)
  caption gap/overlap      -> caption_audit.json (Node 11/12)

P1-B visual evidence                                              [Completed 2026-06-07]
  keyframe grid/contact sheet     -> keyframe_grid.jpg (Node 12, ffmpeg)
  optional configured VLM audit   -> visual_audit.json (Node 12, mechanical + optional VLM)

P2 creator_profile.json                                          [Completed 2026-06-08]
  creator_profile.py + creator-profile CLI; brief always overrides creator
  defaults; contract-run --creator-profile fills build_profile broll policy and
  writes creator_profile_applied.json lineage (indexed in manifest)

P3 optional CapCut draft backend                                 [Scaffolding 2026-06-08]
  version-independent framework built (build_profile.render_backend,
  capcut_backend.py: provider-neutral draft manifest + export-as-render-candidate,
  human/CU gate, Node 12 verify required). Real proprietary .draft serialization
  deferred — CapCut not installed; see docs/decisions/2026-06-08-p3-capcut-optional-backend.md.
  ffmpeg remains canonical; never a core dependency.
```

P1 status: implemented as focused `video_pipeline_core` modules with thin
`video_tools.py` CLI shims (`timeline-audit`, `broll-audit`, `caption-audit`,
`keyframe-grid`, `visual-audit`), optional `artifact_manifest.json` keys,
Node 11/12 dashboard evidence, and a pure `runtime_orchestrator.resolve_audit_route`
consumer. Mechanical-only verify works without Ollama; policy is parameterized
(no creator keyword map baked in). Graphify rebuild intentionally deferred until
P1 boundaries settle. See `docs/build-tool-runner-spec.md` P1 section.

P1.5 (auto-wire, 2026-06-07): `contract-run` now auto-produces the enabled audit
artifacts in a single build pass, gated by `build_profile.verification_tools`
(default OFF, so existing runs are unchanged). `caption-audit` reads a real
`subtitles.srt`; `keyframe-grid` fails loudly on empty output. This closes the
Codex review's main gap ("the canonical build chain should self-produce audit
evidence"). Full Windows suite: 320 tests OK. Remaining P2-level follow-up:
future-proof `timeline_invariants` for non-`clips` timeline shapes.

Graphify rebuilt 2026-06-08 (source-only) after P1/P1.5 settled: 1346 nodes,
1992 edges, 115 communities from 121 source files; the P1 verification tool pack
and its Node 11/12 integration are captured (dedicated hyperedge present).
Outputs in `graphify-out/`. Next milestone: P2 creator_profile.json.

Constraints:

```text
Node 11/12 own P1 evidence and findings
all outputs are explicit artifacts indexed by artifact_manifest.json
segment_contract.json remains provider/backend neutral
CapCut and Computer Use remain optional
mechanical-only Verify must work without Ollama
do not copy author-specific keyword maps or creator preferences
```

## 🗄 2026-06-05 Canonical State(歷史快照,現況以 HANDOFF_CURRENT.md 為準)

### 一句話版本

這套系統已從舊的 `script.json` flat workflow，收斂成 **canonical contract-led video workflow**：

```text
brief / interactive spec
-> segment_contract.json
-> contract_adapter.py
-> generated_mv_script.json
-> mv_chain / render
-> artifact_manifest.json + state.json + verify artifacts
```

現在的核心不是再擴 SPEC，而是讓同一份 SPEC 可以透過不同 BUILD profile 跑出不同品質/成本/速度的影片。

### Source Of Truth

```text
segment_contract.json
  public canonical SPEC。描述段落目的、素材需求、聲音、文字、視覺風格與 fallback 誠實邊界。

generated_mv_script.json
  legacy runtime payload。由 contract_adapter 產生，只供既有 mv_cut/video runtime 消費。

artifact_manifest.json / state.json
  BUILD + VERIFY 執行真相。給 agent/dashboard/operator 判讀。

build_profile.json
  BUILD provider/profile artifact。決定本次 run 使用 no_effects/light_effects/
  motion_graphics、fallback provider、motion graphics backend、model routes。

generated_asset_requests.json
  generated fallback 的 provider-neutral 請求清單。只由 contract 允許的段落產生；
  identity/proof/must_include 不可生成替代。
```

舊版 `script.json` 仍可視為 runtime/legacy layer，不再作為公開 SPEC 方向。

### Current Graphify Architecture

最新 Graphify 輸出位於 `graphify-out/`。2026-06-05 已用 source-only graphify skill
程序重跑，排除 run output、素材/media、archive 類資料，只掃 engine、skills、docs、
examples 與 tests：

```text
120 files · ~82,119 words
1188 nodes
1561 edges
122 communities
95% EXTRACTED / 5% INFERRED / 0% AMBIGUOUS
Import cycles: none
Edge diagnostic: no dangling / duplicate / endpoint-collapsed edges
```

主要社群與架構意義：

```text
contract_adapter.py cluster
  canonical SPEC -> legacy runtime payload -> manifest/run artifacts。

spec_contract.py / FallbackRouteTest cluster
  brief、segment contract、fallback route、Node 9-14 詞彙守門。

mv_cut.py / run_mv cluster
  beat-driven MV runtime，含 stock/local/live 三分支、render plan、audio/text layer。

edit_artifacts.py cluster
  Node 9 assembly_plan 與 Node 10 timeline_build，將意圖和時間戳拆開。

editor_review.py cluster
  Node 11/12 deterministic clip review。

music_structure.py cluster
  music_structure.json，將 beat/grid/section 變成可引用 artifact。

model_routing.py cluster
  model_routes.json，將 verify/content_qa/asr/agent model 變成 BUILD artifact。

stock_first.py / vt_stock.py cluster
  stock-first conceptual MVP route，Pexels first + Pixabay fallback。

motion_graphics.py cluster
  optional motion graphics contract/render_plan/manifest scaffold；dashboard 以 Node 14
  Revision 呈現，effects 不是 Node 14 本體。

Generated provider cluster
  build_profile / generated_asset_requests 將 generated fallback 保持 provider-neutral。
  ComfyUI 已是 deprecated provider，不作為 active default；目前 fallback image 品質以
  Antigravity / assistant_imagegen / codex_imagegen 優先。
```

Graphify 顯示的 god nodes 仍有 `ToolError`、`run()`、`pipeline()`、`_audio_duration()`、
`run_tool()`、`compose_and_qa()`。2026-06-05 已先修正兩個實際對齊點：

```text
video_pipeline.py fix_class -> fix_target now aliases video_pipeline_core.vt_core.FIX_TARGET.
run_content_qa() now invokes python3 -m video_pipeline_core.content_qa instead of a removed root content_qa.py.
```

長線仍要降低舊 `video_pipeline.py` 與 CLI facade 的中心性；但短期 MVP 已可由
canonical adapter + package module 路線操作。

### Completed Runtime Readiness

目前 V3/P7 實作狀態：

```text
P0 canonical run CLI + manifest: done
P1 music_structure.json: done
P2 assembly_plan/timeline_build split: done
P3 editor_review.json deterministic checks: done
P4 scene-cut snapping/crop metadata: done
P5 model_routes.json: done
P6 motion_graphics contract scaffold: done
P7 stock-first connectivity + Pexels/Pixabay fallback: done
P8 build_profile.json + generated_asset_requests.json: done
P9 package/module entrypoint alignment: done
```

已驗證：

```text
python3 -m unittest discover -s tests -v
Ran 222 tests
OK
```

實跑 stock-first conceptual MV：

```text
examples/stock_first_concept_mv.json
-> stock_first_route.json
-> generated_mv_script.json(source=stock)
-> Pexels/Pixabay stock fetch
-> timeline_build/editor_review
-> stock_first_run/final.mp4
```

結果：

```text
final.mp4 duration: ~60s
stock segments: 3/3 fetched
editor_review: pass
state pass: true
blocking: []
```

### SPEC Layer Decision

SPEC 層目前夠用，不再優先擴 schema。後續只做小型補強與驗證守門：

```text
保留互動式消歧
保留段落目的與敘事理由
保留 fallback 誠實性
禁止 must_include / identity_sensitive / proof_critical 被 stock/generated 偷換
```

真正的上游風險是「沒有敘事脊椎、影片流於形式」。因此 V4 的有效結論不是把 SPEC 變胖，
而是加入/強化 narrative spine 作為頂層架構：

```text
narrative.thesis
narrative.arc / 起承轉合
narrative.big_story
narrative.breakdown
narrative.mode_plan
segments[].core.story_purpose ladder 回 arc
```

這是下一個 SPEC/VERIFY 小改，不是 engine 重構。

### BUILD Layer Decision

BUILD 層要補的是工具設定，不是 SPEC。建議導入 run/tool profile：

```json
{
  "render_profile": "no_effects | light_effects | motion_graphics | debug",
  "fallback_visual_provider": "pexels | pixabay | antigravity | assistant_imagegen | gemini_veo",
  "fallback_visual_mode": "stock_video | generated_image | generated_video | text_bridge",
  "effects_enabled": false,
  "motion_graphics_backend": "ffmpeg_libass | html_playwright | remotion | blender",
  "model_routes": "model_routes.json",
  "quality_baseline": "connectivity | no_effects_quality | final_review"
}
```

原則：

```text
SPEC 決定可不可以 fallback、哪些段不能替代、段落需要什麼功能。
BUILD profile 決定實際用哪個 provider / renderer / model / effects backend。
```

已落地：

```text
build_profile.py
  default/load/validate/write build_profile.json；ComfyUI 不能成為 active provider。

generated_assets.py
  從 segment_contract 產 generated_asset_requests.json；只抽取 generated-capable provider，
  stock provider(Pexels/Pixabay)留給 stock-first，不混用。

contract_adapter.py run
  每次 canonical run 寫 build_profile.json、generated_asset_requests.json，
  並放進 artifact_manifest.json。
```

### BUILD Runner Strengthening

BUILD 補強不再把重點放在擴張 SPEC，而是把 tool selection 與 runner
execution 拆清楚。後續施工入口是：

```text
docs/build-tool-runner-spec.md
```

施工模型：

```text
Policy artifacts
  build_profile.json
  model_routes.json

Request artifacts
  generated_asset_requests.json
  motion_graphics_render_plan.json
  assembly_plan.json
  timeline_build.json

Runners
  stock runner
  generated asset runner
  motion graphics runner
  mv_chain render runner
  verify/editor-review runner
```

目前狀態：

```text
wired:
  contract_adapter.run_contract
  stock runner via Pexels/Pixabay
  local material ingest/match
  mv_chain render runner
  editor_review runner
  dashboard/story-map reader

request/plan only:
  generated asset runner
  motion graphics runner

next priority:
  P1 artifact_manifest completeness: implemented
  P2 generated_asset_manifest/manual provider adapter: implemented
  P3 light effects runner: implemented as ffmpeg-safe operation planner
  P4 motion graphics backend runner
  P5 dashboard build control surface
```

驗收原則：

```text
每個 BUILD runner 都必須有 input artifact、output artifact、manifest entry、
dashboard node status、focused unit test。不能只靠 prompt 或口頭約定。
```

### Antigravity Feedback

人工回饋：

```text
純無特效版本(no_effects)
fallback 圖片由 Antigravity 產生
輸出 final / final_etf
品質明顯優於純 stock-first
```

結論：目前品質瓶頸不一定是剪輯結構或 SPEC 不足，而是 fallback 素材品質。Antigravity
應納入 BUILD provider，但不得寫進 segment_contract 成為硬依賴。

適用：

```text
symbolic cutaway
chapter/card background
conceptual process illustration
stock 不好命中的抽象/在地/專業場景
no_effects baseline 的高品質 fallback image
```

禁止：

```text
指定人物
真實場地證據
主任致詞
學員本人
大合照
must_include / proof_critical / identity_sensitive 段落
```

### Testing Baselines

測試分三層，不要每次都跑重型影片：

```text
1. Contract/artifact unit tests
   快速、無網路、無大型影片。驗 canonical -> payload -> manifest -> artifacts。

2. Stock-first connectivity E2E
   用 Pexels/Pixabay。驗節點連結、provider、manifest、final.mp4 是否產出。
   不拿來評畫面品質。

3. No-effects quality baseline
   用 Antigravity fallback image + no_effects render。
   final / final_etf 作為人工 review baseline。

4. True-material regression E2E
   用 66 期等真素材，只在里程碑跑。驗 must_include、原音、字幕、節奏、review route。
```

影片輸出不應留在 repo root。repo 是 engine/source；真實 project 與 run output
預設放在 repo 外：

```text
<project-root>/<project>/
  input/materials/
  runs/<timestamp>-<case>/
    spec/
    build/
    verify/
    materials/
      raw/
      selected/
      generated/
      stock/
    nodes/
    thumbs/
    logs/
    brownfield/
```

偵測原則:

```text
run root = 唯一 output truth source
spec = 正式 SPEC layer 產物位置;先定位置,不要先寫死 node schema
build = BUILD layer 產物位置;等 build contract 確認後再細分
verify = VERIFY layer 產物位置
materials/raw = 候選素材
materials/selected = 已挑選/剪輯可直接消費素材
materials/generated = generated fallback 輸出
nodes = node 專屬中間 artifact;node 編號/名稱等 contract 確認後再建
brownfield = 小步快跑 SPEC/DO/VERIFY 修正紀錄
```

repo 內只保留 `.project/active.json` 作為 repo-relative local pointer：

```bash
python3 video_tools.py project-init "ETF Demo"
python3 video_tools.py project-new-run --label baseline
```

Git 只保留小型 artifacts：

```text
artifact_manifest.json
state.json
editor_review.json
contact_sheet.jpg
```

### Active Roadmap

```text
P0: 保持 canonical SPEC 穩定，不再大幅加 schema。
P1: BUILD layer run/tool profile 參數化。✅ build_profile.json 已落地。
P2: Antigravity / assistant_imagegen fallback image 納入 generated_asset provider。✅ generated_asset_requests.json 已落地；實際外部 provider runner 待接。
P3: no_effects quality baseline 固定化(final/final_etf)。
P4: narrative architect / narrative spine：thesis、起承轉合、big_story、mode_plan、verify check。
P5: dashboard 顯示 manifest + baseline outputs + provider decisions。
P6: light effects only：fade / xfade / Ken Burns / lower third / subtitle style。
P7: motion graphics backend：html_playwright 或 Remotion。
P8: narration+MV mixed engine：tts story segments + beat MV segments in one contract run。
```

### Agent Rules

```text
不要重寫 SPEC 主體。
不要把 Antigravity / assistant_imagegen / ComfyUI 寫成 segment_contract 硬依賴。
不要讓 generated image 假裝真素材。
不要把 heavy effects 當 MVP 前置條件。
每次出片都寫 artifact_manifest 與 provider decisions。
ComfyUI 預設 disabled/deprecated；除非使用者明確要求實驗,不要選它當 provider。
優先修 BUILD profile / dashboard / verify，而不是再開新 workflow。
```

---

## Historical Notes Below

以下保留舊 roadmap 的歷史脈絡與已完成細節。若和上方 Current Canonical State 衝突，
以上方為準。

## 一句話版本
> 一套可複製、可移植的 **Video Route Skill Project**:用 `script.json` 描述影片、deterministic pipeline 產物 + `state.json` 當單一真相、`route.py` 派工下一步、dashboard 做人機 review。ComfyUI 只作未來外部 `generated` 素材 provider,不進核心。
> 2026-06-05 更新:ComfyUI 已降為 deprecated/disabled；generated 實務優先 Antigravity / assistant_imagegen / Codex 圖。

---

## 北極星:統一段落模型(Unified Segment Model)

> **一個段落由「資訊/意圖」定義;不同影片類型(結訓 MV / 慶生會 / 旁白片 / 知識片)只是同一段落模型的「輸出頻道 + 時間軸來源」的不同組合。** 一套系統吃多種片,而非維護多條 pipeline。

舊系統隱性假設「旁白驅動」(時間軸吃 TTS)。但**主產品結訓片是 MV、無旁白**;旁白是未來單位片的可選能力。正解:三種片收斂到「同一段落模型 + 可插拔輸出/時間軸」。

**段落 = 結構化意圖 + 可選輸出頻道 + 時間軸來源**

意圖分欄保留(同意圖、不同消費者要不同措辭。教訓 D5:旁白文字做 VLM 過嚴 56.4,`visual_desc` 才誠實 68.2):

| 欄位 | 消費者 | MV 用法 |
|---|---|---|
| `visual_desc` | VLM 選素材 + 導演情緒 | **主 SPEC**(選素材+情緒) |
| `search_query`/`material_hint` | 找素材 | 本地素材夾/來源提示 |
| `text`(旁白) | 耳朵(TTS) | 空=純 MV;有=橋段才 TTS |
| `caption`/`title`(字幕) | 螢幕 | 標題卡/人名/歌詞 |
| `must_include`(必放) | VERIFY 守門 | **關鍵**:所長/特定人必放 |

兩個輸出 toggle(後果不同):字幕/標題=純表現層**不影響時間軸**(化妝);旁白聲音(TTS)=**影響時間軸**+多一條音軌(動骨架)。

時間軸來源(可插拔,吃 MV 的關鍵):`tts`(旁白長度→actual_dur)/ `beat`(librosa→cut_grid,結訓 MV)/ `fixed`(卡片/片頭尾)。三者都輸出共同介面「每段時長/切點」,下游 render/concat/QA/state/dashboard ~70% 共用,只在「時間軸來源 + 選段模型」分叉。

**落地待辦**(讓模型真成立):① 時間軸來源插拔化(目前 `actual_dur` 貫穿全部,真 refactor)② `text` 變可選(空則跳 TTS)③ 字幕來源解耦(非旁白路徑:標題/人名/歌詞)④ MV script schema(✅ 已落地,見下)⑤ MV 語境導演 >> 編劇。
> ⚠️ 先鎖抽象 → 再做最小真實切片,**別為抽象優雅延後唯一硬能力(選好片段+對拍)**。

---

## 兩層模型分工(關鍵架構原則)
> **大模型管判斷/SPEC/route;ollama 管大量看圖;機械層管純算。**

| 層 | 誰 | 做什麼 |
|---|---|---|
| **Agent(大模型)** | Hermes/Codex/Claude | **模糊消除**(vague→引導 prompt→結構化 SPEC)、固化導演 YML/風格、**ROUTE 派工**、讀 caption 決定素材歸類/分群/必放。有品味/判斷的活 |
| **Tool(本地 VLM)** | ollama qwen3-vl | 逐圖 caption、逐窗評分。便宜高量看圖苦工,**不做歸類決策** |
| **機械** | ffmpeg/librosa/scenedetect | 抽幀/拍點/拆鏡/渲染,零判斷 |

- **模糊消除(最重要)** = Agent 層:`需求(故事)→ video-workflow 引導建架構 → 導演固化 YML/風格`。把「想拍什麼」變「可執行 SPEC」。
- **素材語意歸類 = 兩層合作**:ollama 看圖答「是什麼」+ 大模型讀 caption 判「怎麼分群/哪些必放/故事怎麼接」。ollama 只供事實,判斷在大模型。

**SPEC 三角色**:`video-workflow`(釐清/腦暴,坐最上游,輸出 brief 分流)→ `director`(製作 SPEC:分段/必放/音樂/選素材,MV 主力)↘ `writer`(MV=螢幕文字層:標籤/敘事字卡/演講字幕;非「不用」是重新定位)。
> ⚠️ 模糊消除屬 video-workflow(現 30 行,待升級互動釐清),**不是編劇的事**。

**建置原則:機械 vs 判斷**(決定哪裡造輪子,不是用前段/後段切):
- **機械=到處用 lib**(不造不抄 repo):beat=librosa(ISC)、shot=PySceneDetect(BSD)、render=ffmpeg。
- **判斷=自己做**(護城河):語意分類/可用性、選哪幾段、**必放守門**、對題、誠實缺口、整個 SPEC。
- **參考(讀配方不抄碼)**:CutClaw「拆解→caption→對拍→選段→審查」順序與避坑。CutClaw 無授權→只學做法、自己重寫。montage-ai(noncommercial)/OpenMontage(AGPL)同理只讀不用。

---

## MV-cut 現況(✅ 端到端可跑出片)

`mv_cut.py` 是 MV 引擎。增量全綠(93 測):
- **① beat→cut_grid** ✅:`beats_to_cut_grid`/`grid_durations`/`detect_beats`(librosa lazy)。
- **② 長片開窗** ✅:`detect_shots`(PySceneDetect,連續鏡頭 fallback)+ **`fixed_windows`(raw 素材真用的開窗原語)**。**實測:真實學員素材是連續長鏡頭,ContentDetector 對 raw 無效 → 改 fixed_windows。**
- **③ 候選窗評分選段** ✅:`select_windows`(**必放守門:必放凌駕 min_score**、缺料→unfilled→VERIFY 缺口)+ `score_windows`(抽 midpoint 幀→`content_qa.score_segment` VLM)。
- **④ renderer** ✅:`plan_mv`(選窗→beat 時槽)+ `render_mv`/`render_mv_audio`(抽段→1920x1080→硬切→鋪音樂)。
- **run_mv**(劇本驅動全鏈) ✅:stock(Pexels resilient→GAP)/ clip_list(吃 match-mv)/ live 三分支。**鑑別力出現**:per-段 visual_desc 給真分數(班級日常 vs「專注上課」=全 10 被丟、拖拉電纜=100/60),解掉先前全 100。`min_score=60`(必放 override)。
- **接線** ✅:`run_mv(clip_list=)` 吃 match-mv 已配 clip 不 live 重評;`mv_chain(script,material_db,out,music)` 單一入口串 match→render。
- **文字層** ✅:`label`(底標籤)+ `name_super`(左下人名)+ **ASR 演講字幕**(faster-whisper,`subtitle:"auto"`→轉錄原音→燒 CJK)。實幀/SRT 驗證(「礙子拆線作業」+「鍾峻松 老師」+ ASR「陳宏比 花蓮區營業部」)。
- **音訊** ✅ v0:逐段 `audio_role`(music/duck/diegetic),v0 固定低音量(非 sidechain)。
- **schema** ✅:`validate_mv_script` + `python3 mv_cut.py validate <script>`。欄位 visual_desc/material_hint/kind/layout/pace/must_include/high_weight/needs_review/hold/keep_audio/audio_role/name_super/text + 頂層 style/music。範例 `examples/graduation_mv_*.json`。
- **dashboard 橋接** ✅:`build_mv_state` 寫 dashboard 相容 state.json(segments+SPEC+status+blocking+next_action,mode="mv")。

**curator/素材地基** ✅:`cmd_ingest_meta`(+`classify_asset` 機械:橫直/解析度/時長/usable)+ `caption-meta`(本地 VLM 填實際內容)+ `material-map`(人可讀地圖)+ `match-mv`(需求×供給 CJK bigram 比對→clip_list+缺口,不跑 VLM)。**真驗證:VLM 把「所長看填志願」caption 成「會議室聆聽/培訓」(比亂猜的『致詞』準)→ garbage-in 解掉。**

### ⭐ 對照組 gold standard(可量測目標)
人工剪好的 `~/.hermes/profiles/video_director/vault/66期養成班-高訓結訓影片全OK.mp4`:**13.4 分鐘、368 shot、中位 1.47s、27.5 cuts/分**;<1s×113/1-3s×197/3-6s×41/>6s×17。= 快剪 montage(多數)+ 必放長 hold(17 段 >6s)並存。校準:`every_n_beats` 預設太慢,調 `≈2 + min_seg≈0.6` 對齊 1.5s。**評估法**:mv-cut 出片 → 比 66 期(長度/節奏/必放放對沒)。

---

## 🎯 待補強清單(依 Codex review 確認的優先序)

> Codex 校準的方向:**①先穩素材地圖(地基,不追剪輯花招)②MV 走「人可控草稿」70-80 分→人補開場/收尾/必放/人名到 90,非全自動完美 ③route 從旁白線升級到 MV chain(state 描述 gap/missing photo/must_include unfilled/opening-ending review)④node-timeline dashboard 是關鍵產品=工作台,非裝飾 ⑤CutClaw 只當 recipe。** 護城河:中文活動影片、必放守門、素材地圖、人補接力、route state。

1. **素材地圖穩固(地基,最高優先)** ✅ ⟨2026-06-04⟩:真跑全池 `C:\Users\user\Downloads\微電影素材`——`ingest-meta`(302 檔:88 影片+214 照片,264 keyframe,104 HEIC 轉檔)→ `caption-meta`(qwen3-vl:4b,**302/302 caption、0 error**)→ `material-map`(301 行人可讀地圖)。**garbage-in 解掉的實證**:VLM 正確讀懂電力訓練(鐵塔高空維修/拖拉電纜/捐血活動/主任演講),甚至讀出橫幅字「養成訓練 卓越台電」「捐血救人」。**剩(agent 判斷步)**:大模型讀 caption 決定分群 → stage 集中。**雞生蛋:人看 material_map.md 寫務實劇本 → 再 match。** 〔db/map 在 `_fullpool/`(gitignored)〕
2. **node-timeline dashboard(關鍵產品=工作台)** ✅ ⟨2026-06-03⟩:`build_mv_state` 每段加料(visual_desc/layout/audio_role/must_include/name_super/label/subtitle + BUILD:picked_clips/n_slots + 時間軸 start/dur + 頂層 total_dur,plan slots 推算)+ `dashboard.html` `renderTimeline()`:每節點狀態點 + 比例時長條 + SPEC→BUILD→VERIFY 三層(SPEC layout/audio_role/★必放/人名/標籤/字幕、BUILD 選了哪支 clip×slot 或 GAP+fix、VERIFY status/score/必放✓),表格留作摺疊細節。headless render 驗證 + self-contained 產生器相容。94 測綠。**剩(人補互動)**:dashboard 上點選節點覆寫選段/補開場收尾/補必放(目前唯讀呈現,人補仍走 `--only-seg`/route)。**素材候選縮圖**:state 尚未帶 thumb 路徑。
3. **video-workflow 互動式模糊消除**:需求(故事)→ 引導 prompt → 產出導演 MV YML 劇本。整條入口(SPEC 最上游)。
4. **bookend 照片處理 + pacing** ✅ 照片 ⟨2026-06-03⟩:`find_photos`+`_is_image`+`_photo_vf`(kenburns 緩推/hold);run_mv 吃 photo(media=photo / opening|closing|title / 無影片只有照片 → still slots);match-mv 配到照片 → 1 張=1 still;render `-loop 1`+kenburns+靜音(⚠️`-t` 放 filter 後)。實 ffmpeg smoke 時長精準。**剩**:pacing 調勻(montage 快 1.5s vs hold 長)。
5. **audio-director sidechain** ✅ ⟨2026-06-03⟩:`_mv_music_mix` 取代固定低音量——有原音段(duck/diegetic)用 `sidechaincompress` 讓音樂在致詞/隊呼時自動讓位,全 montage 音樂當主音軌。music_vol 0.35→0.7。實 smoke 兩分支出片。**剩**:配音師 skill 升級成「讀 audio_role+原音+意圖 的混音計畫」(現是引擎層自動)。
6. **verify 音訊搭配維度** ✅ ⟨2026-06-03⟩:`audio_qa` 抓 subtitle:auto 卻沒保留原音(字幕沒聲源/音樂蓋過)、diegetic 沒原音;寫進 state.qa.audio_pairing + dashboard 維度顯示。
7. **route↔MV 整合** ✅ ⟨2026-06-03⟩:`route.py --mv`(--material-db+--music)驅動 mv_chain;state 描述 MV 缺口(must_include unfilled 點名必放、bookend 缺口標最重要、`review_points` opening/closing/title 高權重+needs_review);`_route_mv` surface 人工複核點(人在迴圈接點)。**剩**:旁白線 route 消費 `revise:director`、legacy top-text fallback 改誠實 route。
8. **比 66 期 gold standard 收品質**(里程碑)✅ ⟨2026-06-04⟩:`mv_chain` 真跑全池 captioned db + 真音樂 → `graduation_66_auto.mp4`(99.9s/1920x1080/26 cut,state pass=True/audio_pairing=100)。**match 準**(拖拉電纜 0.929、換桿 0.7、主任勉勵 0.625、班級日常 0.5、空拍 0.583、大合照 0.5)。`shot_stats` vs 66 期:**中位 cut 1.5s vs 1.47s(ratio 1.02,逐 cut 節奏對上)**,但 **cuts/min 10.8 vs 27.5(ratio 0.39=太慢)**——4 個長 hold(空拍/主任勉勵/字卡/大合照)拉低整體;結論:montage 段需更密 or holds 縮短(`weight`/劇本可調的旋鈕,已具備)。修了 concat 相對路徑雙重前綴 bug。**剩(迭代)**:montage-heavy 劇本再跑逼近 27 cuts/min。
9. **graphify 重建**(收尾)✅ ⟨2026-06-04⟩:scoped 重建(59 檔 source-only,排除 _fullpool/素材/artifact)→ **484 節點/732 邊/52 社群,99% EXTRACTED**(舊圖 270 節點)。god nodes:ToolError(40)/run()/pipeline()/run_tool()/**run_mv()(15)**/compose_and_qa()。社群涵蓋新 MV-cut(MV-cut Engine、run_mv、build_mv_state、score_windows、render_mv_audio、filter_static_windows + PhotoHandling/AudioQa/StaticPrefilter/ShotStats/MusicMix 測試群)。圖譜啟示同舊:`pipeline()`/`run()`/`ToolError` 仍是跨社群 god nodes、Pipeline Core cohesion 低(0.05)→ 收斂 Project Kit 仍是長線方向。outputs 更新於 `graphify-out/`。〔AST(code)層;doc 語意層此輪略過避免大量 subagent fan-out〕

**小剩**:✅ `narrative` 全屏字卡、✅ window 靜止窗預篩(freezedetect)、✅ music-fetch `ytsearchN`、✅ ASR 換大模型(`MV_ASR_MODEL` 可調)、✅ pacing weights(hold 可加權)。全數完成。

---

## Pipeline 實際流程(旁白線 `video_pipeline.py`→`pipeline()`)

```
[1]TTS→[2]SRT→[3]mix-audio
        ↓(與素材無關,迴圈外只跑一次)
┌─ 重試迴圈(P2-3,預設開,max_retries=2)──────────────┐
│ [4]gather+pick ← P1-1 prepick VLM gate + fallback 重搜   │
│ [5]render segments ← render_one(重試只重渲變動段)        │
│ [5b]precompose gate ← P1-2 規格/時長驗證                  │
│ [6]xfade concat→[8]merge-final→[9]thumbnails             │
│ [10]verify(技術 5 維)→[11]content_qa(0.30)            │
│  ↓ 不過: collect_fix_actions 依 fix_target 路由          │
└──────────────────────────────────────────────────────────┘
        ↓ decision_log.json(P1-3 逐輪軌跡)
```
產物:`final.mp4`·`qa_report.json`·`content_qa.json`·`decision_log.json`·`precompose_gate.json`·`edit_log.json`·`picks.json`

## 角色 Skill 契約(`skills/`)
| Skill | 角色 | I/O |
|---|---|---|
| video-workflow | 釐清/腦暴(SPEC 最上游) | 需求 → brief(待升級互動釐清) |
| director | 導演(MV 主力 SPEC) | 內容 → 製作設計(style/media_pref/layout/bgm/必放/MV schema) |
| writer | 編劇(MV=螢幕文字層) | 主題 → script 內容欄位 + MV 文字層(label/narrative/subtitle) |
| curator | 小編 | script → ingest/caption/material-map/match-mv → clip_list |
| editor | 剪輯師 | assemble + merge-final(檔案層級) |
| audio-director | 音控師 | edge-tts + BGM mix(待升級混音計畫) |
| subtitle-director | 字幕師 | tts_timing → subtitles.srt |
| verify | VERIFY | 5 維 QA → qa_report + fix_target |
| route | 派工 | 讀 state.next_action → 完成/await_material/retry/review |
| effects-director | 特效師 | grade/title/transition/montage policy |
| generative-director | 生成素材契約 | 外部 provider:`source=generated` |
| gap-analyzer | 缺口分析 | script → material_needs.json |
| dashboard | 監控 | 掃 workdir → HTML 狀態 |

共用後端:`video_tools.py`(tts/srt/mix-audio/merge-final/verify/kenburns/pexels-*/music-fetch/caption-meta/material-map/match-mv/dashboard)。

---

## 已完成檔案庫(旁白線,壓縮)
- **P1-1/P1-2/P1-3** ⟨05-29⟩:prepick VLM gate(全否決 fallback 重搜)、precompose gate(規格/時長 ±0.3s)、decision_log 統一逐輪軌跡。
- **P2-1/P2-3** ⟨05-29⟩:Pexels+Pixabay 雙源;self-reflection retry(依 fix_target 路由、換 survivor+8b 複核、耗盡標 unfixable、max_retries=2)。
- **content_qa 整合 + D1~D5** ⟨05-29⟩:content_alignment 注入 qa;單段 content gate(任一段<60 fail);中文素材策略(search_query 中文關鍵字 + `visual_desc` 作 VLM 標的 + `cultural_specificity`);rubric(somewhat→75);字幕美學。run5:8 段對題、3 段誠實 unfixable+補拍指引、零 HTTPError。
- **effects-director** ⟨05-30⟩:grade/title-card/12 轉場(白名單避黑幕);content_qa 抽基底原片(解 grade↔desc 打架);15 段全自動 score 93。
- **title-sequence + style 政策 + 逐段混風格** ⟨05-30⟩:文字動畫片頭尾 + `kind:title`;style(narrative/mv/promo)逐段覆寫。travel 主題 score 95.5/align 85(最高)。
- **BGM 情境庫 + collage** ⟨05-31⟩:`gen-bgm`(7 情境墊樂)+ script `bgm` 欄;`collage`(群像段)。
- **5 分鐘 story+MV 長片** ⟨06-01⟩:25 段 final 333.6s/QA 100/align 70/5 段誠實 unfixable。暴露 video stock 長片缺口(已修,見下)。
- **BUILD 可恢復化 + fix_class 三分類** ⟨06-02⟩:`RecoverableBuildError`(material/spec/human),4 個硬 raise 改可恢復(缺檔→block、候選不足→降級單圖、precompose 整片→gate_review),render loop 接 per-seg 失敗→placeholder 照常出片;`build_state` 每段標 fix_class + `revise:director` next_action。
- **music-fetch** ⟨06-02⟩:`music-fetch <q> --source yt`(yt-dlp 抽音訊 mp3,實證 lofi 68.2s);Pixabay 無 music API 故不接;script `bgm` dict→自動抓真曲→mix-audio --duck。
- **Longform Duration Policy** ⟨06-02⟩:`_seg_target_len`(單一真相)+ `_filter_video_candidates`+ `_video_fill_plan`;候選挑選改用 TTS `actual_dur+xfade`,太短改 `-stream_loop` 補滿不再 hard fail。
- **編排層 route→state.json→skill** ⟨05-31⟩:① `build_state()` 六份 artifact 收成單一真相(stages+segments+blocking+next_action)② `--only-seg N` 分段重渲(零重渲沿用)③ `route.py`+`skills/route.md` 派工層(無 state→build/null→出片/await_material→偵測 `seg{n}_user.*` 轉 local 重渲/retry/review)。學員素材接力實證:qa 92→97、align 74→90。
- **Dashboard 接入** ⟨06-02⟩:`dashboard.html` 讀 route state schema(banner/stages/QA/segments/blocking/final,auto-refresh 5s);`dashboard <outdir>` 產 self-contained `dashboard_view.html`(解 file:// 不能 fetch)。

### ⏳ Deferred(已知缺點)
- **D2-C 更好中文素材源**:Pexels 對台灣專有食物拆字(胡椒餅→胡椒粒)。需中文素材庫或生成式。優先低。
- **音樂進階**:純音樂段模式(`kind:music` 跳 TTS)、Jamendo client_id(公開發佈)、逐段/依 style 自動選曲。
- **特效進階**:相框+粒子背景、effects 擴成動畫配方、真甩鏡(需 Remotion/AE 級,等 project kit 穩)。
- **物理上限**:stock 庫沒有的台灣專有實體 → unfixable+補拍(D2-C/生成式);stock 拍不到「特定那群人」是本質天花板 → 靠學員素材腿。

---

## 產品定位(2026-05-31)
**一條紮實、可靠、誠實、可擴充的系統**,正從「自動中文旁白影片產生器」(1 旁白=1 clip 幻燈片模型)轉向「**結訓 MV 自動剪輯器**」(beat-driven 選段+對拍+必放+文字層+人補接力)。三源素材:① 學員自有(紀實主體 ~80%,最該補的腿)② stock(Pexels 泛概念)③ 生成式(Antigravity / assistant_imagegen / Codex 圖補 ceiling,做不出特定人,只當 B-roll)。策略:Route Skill Project 先收斂 → dashboard review → 再特化 → 平台無關移轉(Project Kit 後)。生成 provider 由另一 agent 獨立執行,本專案只定義 `source=generated` 介面；ComfyUI 已降為 deprecated/disabled。
## 2026-06-12 E6 Agent-As-Visual-Judge V1 Complete

E6 is verified:

- V1 stock candidates produce timestamped montage evidence in agent mode.
- One `visual_review_request.json` pauses the run at `await_visual_review`.
- A validated `visual_review_verdict.json` resumes deterministic window cutting/rendering.
- Dashboard/runtime route the single review gate.
- `ollama` and `none` remain supported build-profile modes.
- Focused E6 regression: 164 tests passed; full suite: 596 tests passed.

Next roadmap item: E7 material montage understanding. E8 narrative prepick and Node 12
agent-judge expansion remain deferred until E7 is stable.

### 2026-06-12 E7 Material Montage Understanding In Progress

First contract slice complete:

- `build_material_review_request` creates per-asset visual evidence without invoking a model.
- Videos use timestamped montage evidence; photos use their display image.
- `apply_material_review_verdict` writes agent-authored `vlm_caption` plus explicit lineage.

Next E7 step: connect this request/verdict contract to `caption-meta` await/resume CLI behavior.
