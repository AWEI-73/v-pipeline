---
title: Hermes Video Pipeline — Canonical Roadmap
type: project
status: active
updated: 2026-06-14
tags: [project, video, pipeline, roadmap, agent-workflow]
---

# Hermes Video Pipeline — Canonical Roadmap

> 本文件是專案唯一長期 roadmap。過去的 `REVIEW_REPORT*`、`video_pipeline_architect_review.md`
> 與 `HANDOFF_NEXT_SESSION.md` 的有效結論已整合到這裡；後續 agent 優先讀本檔、
> `HANDOFF_CURRENT.md`、`RUNBOOK.md`、`README.md`。

---

## 2026-06-14 Executive Status

**Current accepted baseline:** M0-M4 material-aware planning and the M5 true
render are stable enough to pause. The 67th result is accepted as a
material-limited baseline, not as proof of human-edit-quality parity.

**M6a contract layer COMPLETE** (2026-06-14, evidence: 791 tests OK at round 3).
VD0 shallow-label storage also complete.

**MM1 COMPLETE** + **BA1 COMPLETE** (2026-06-14, Codex re-review passed). BA1
motion_graphics consumer corrected to the `contract_adapter` build path (Node 14
is scaffold/flow-grouping only).

**BR1 Opening / Hook Sequence Builder implemented** (this round, pending review):
`opening_sequence.py` compiles an approved recipe (hook → context montage →
sound-punctuation cue → title reveal → story entry) into render-plan clips that
are **prepended to the plan and reindexed**, so it changes both timeline and
true render (real-render test proves it). Graceful fallback drops beats with no
material. Consumed via `script["opening_recipe"]` in `run_mv`.

**Do not start:** M6a lineage integration, `material_delta`, the complete Visual
Diversity Guard. Do not expand the MM1 contract further.

**Do not start yet:** M5c designed sequences, M5d human-vs-agent automation,
M5e rerender, effects expansion, CLIP hard dependency, or further 67th-specific
sensory tuning.

**Gate policy:**

- Tier 1 blocks objective invalid delivery: unsupported capability, unresolved
  required-material gap, script overreach, wrong proof material, technical
  VERIFY failure, and unreadable/defective render.
- Tier 2 provides quality evidence: perceptual composition repetition, action
  progression, pacing, designed-sequence quality, and human sensory judgment.
- A tier-2 proxy is not promoted to tier 1 from unit tests or one case.

External review handoff:
`docs/decisions/2026-06-14-roadmap-course-correction.md`.

## 2026-06-13 Active Direction: Material Phase(真素材精剪攻堅,M0-M4)

**現況與根據**:Sensory S1-S4 + bakery 整合驗收已收。2026-06-13 真實學員素材
案例(同素材人剪對照,見 `docs/reviews/2026-06-13-student-vs-agent-montage-review.md`
與 `…-spec-weight-assessment.md`)判定:結構與流程有進步,**剪輯品質 VERIFY 不通過**。
關鍵發現:幾乎每個失敗點系統裡都已有訊號在響(broll_audit 重複 fail、素材地圖 GAP、
零分匹配),**但沒有任何訊號有決策權**;且劇本在供給評估前就承諾片長,逼出
「重複素材硬補時間」。

**因此本階段的優先序是:先給訊號決策權(M0)、再給供給算術(M1)、然後才是
新剪輯機具(M2/M3)。** 階段成功標準(取自評估報告,逐字):

```text
即使影片變短,也不使用錯誤素材。
即使章節減少,也不重複素材硬補時間。
即使故事較簡單,也確保每個段落都有正確且足夠的視覺證據。
```

參考 OpenMontage(reference repo)**僅借概念**(corpus 掃一次離線查、CLIP 排序、
silence jump-cut)——**AGPL v3,一行碼都不可抄、不可 import**,全部 clean-room 自寫。

### M0 規格決策權(最優先;全部是執法,不寫新剪輯能力)

```text
M0a capability_manifest.json(生成物,絕不手寫):
    `python video_tools.py capability-manifest` 從程式碼常數彙編:
      transitions      = video_pipeline.ALLOWED_TRANSITIONS
      still_treatments = edit_artifacts._STILL_TREATMENT_MODES
      sfx_cues         = sfx.ASSET_COUNTS keys(whoosh/hit/riser)
      patch_types      = visual_review 的 window/crop/treatment
      audio_policies   = duck/music(+M2d 後的 source_speech)
      render_profiles / providers(stock|local|generated + 誠實規則摘要)
      judge_modes      = agent|ollama|none
      unsupported      = multi_track_music, arbitrary_effects, full_nle_ui,
                         cloud_vlm_default, remotion_backend(機器可讀邊界)
    skills/spec-contract.md 增「能力字典」節指向 manifest(不重複維護清單);
    director/writer skill 各加一行「寫 SPEC 前先讀 manifest」。
M0b spec_review 新規則 B5(out_of_capability):合約要求 manifest 沒有的能力
    → blocking,附 manifest 路徑與最近合法值。字典不攔人就只是會腐爛的文件。
M0c 規格三層化(評估報告的分層,編進規則 metadata,不是散文):
      tier1 不可違反:語意正確/來源誠實/proof 不錯配/零分不得用/GAP 不得繞/
                      不得重複硬補片長/VERIFY 阻擋不得交付
      tier2 品質目標:故事結構/鏡頭功能/節奏變化/每刀新資訊
      tier3 風格偏好:目標片長/特效/字幕風格/轉場/音樂/聲線
    鐵則:tier3 不得壓 tier2,tier2 不得壓 tier1。**target_length 自此降為
    tier3**——它讓步給 max_honest_duration(M1),不再是硬要求。
M0d 交付硬閘(本次案例的直接修復;全部是「給既有訊號決策權」):
      broll_audit fail(max_source_repeats/unique_source_ratio)→ 不得
        complete_review_final,next_action 維持 fix 路由(dashboard waterfall 消費)
      零分/無 caption/無匹配理由的 local 窗 → planner 拒收(stock 鏈
        _STOCK_OFF_TOPIC_FLOOR 的 local 等價物)
      素材地圖標 GAP 的段 → 只能 await_material / 縮短 / 重寫,不得以
        重複其他來源無聲填補
      editorial_qa / 剪輯品質 VERIFY fail → 同上,不得標 complete
      黑幀/近空白幀檢測(技術缺陷級,tier1):✅ 已實作 black_frame_audit.py
        (ffmpeg signalstats 抽樣 YMIN/YMAX/YAVG → black: avg≤16;
        blank: avg≥235 且 range≤12;run≥0.4s 才 fail)。接 delivery_gate
        HARD_AUDITS + dashboard node 12;CLI `video_tools.py black-frame-audit`。
        真渲驗證:黑+白測試片各被抓出,彩條乾淨。無法解碼或無法取樣時
        fail-closed。限制:目前尚未支援「刻意黑場/白色設計卡」允許區間，
        所以保留 tier1 前必須由 SPEC 或 timeline 提供顯式例外，不能靠猜測。
      proof/identity/testimony 段(core.proof_critical / identity_sensitive)
        → 強制走 node 10.5 judge,沒有 accept verdict 的素材不得進 timeline
        (wrong-proof-material 的執法機制;活線錯配就是這條的案例)
M0e 既有 SPEC 欄位普查(評估報告「保留/合併/降級/移除」落地,一次性):
    對 spec_contract schema + 實案合約逐欄位答三問(誰消費決策/誰驗證/
    違反時流程做什麼),三問皆空 → 移除或併欄;產出欄位清冊
    docs/decisions/spec-field-census.md,之後新欄位入冊才准進 SPEC。
完成判準:用 2026-06-13 案例的 run artifacts 回放——當時交付的那支片,在 M0d
之後必須走不到 complete(被哪個閘攔下要寫進測試);欄位清冊覆蓋 100% 現有欄位。
```

M0 status (2026-06-13): COMPLETE. `capability_manifest.json` is generated
from runtime constants; `spec_review` B5 blocks unsupported required
capabilities and emits tier metadata; target length is documented as tier 3;
failed existing audits and unresolved material GAPs now block delivery through
`delivery_gate`; zero-score local matches remain honest GAPs; SPEC field census
is recorded in `docs/decisions/2026-06-13-spec-field-census.md`.

Verification: focused M0 suite passed; full suite `672 tests OK`; replay of
`20260612-232948-story-mv` resolves to `pass=false`, `next_action=curator`,
blocked by failed `broll_audit` and unresolved live-line segment 7 GAP.
M1 status (2026-06-13): COMPLETE. Deterministic material maps now record
per-asset scenes, speech/silence runs, motion peaks, optional scene captions /
bridge labels, and opt-in transcript text. `supply_review.json` estimates
effective shots, unique sources, function coverage, and
`max_honest_duration_sec`; its conservative fallback counts each positive
unscanned coverage pick as one useful window and rejects zero-score picks.
`spec_review` B6 blocks script duration above evidenced supply.

Verification: focused M1 suite passed; full suite `685 tests OK`; replay of the
11-minute `20260612-232948-story-mv` run marked segment 7 and the old zero-score
segment 8 as GAP, all remaining segments as thin, and B6 emitted 20 tier-1
`script_overreach` blockers with `ready_for_build=false`.

Next: M2.

### M1 素材供需帳(supply-before-script:供給決定承諾)

```text
基底(不重做):caption-meta + E7 agent 蒙太奇複核、detect_shots(PySceneDetect)、
keyframe_grid、filter_static_windows 幀差機具、capcut_backend._parse_silencedetect
(搬共用,別寫第二份)、broll_audit(來源重複統計已存在)。
M1a `video_tools.py material-map <src>`(確定性,新模組 material_map.py):
      scenes[]  start/end/midpoint thumb(detect_shots)
      speech[]  silencedetect 反推 talk/silence runs
      motion[]  每 scene 幀差能量摘要(S1a/S2a 機具)
    輸出 materials/maps/<asset_id>.map.json;materials_db 記 map 路徑;冪等。
M1b 逐 scene caption:沿用 E7 兩模式(本地 VLM 預設 / agent 親看),寫回
    map.scenes[].caption;agent 複核時可加 bridge 標記(見 M3c)。
M1c 供需帳(supply_review.json,劇本定稿前的 blocking 節點):
    每章節/段落計算(評估報告的 schema 照收):
      required_effective_shots = requested_duration / target_shot_sec
      estimated_effective_shots(map.scenes 合格鏡頭;照片經 P5 多幕展開
        最多算 2;同一來源的多窗**不算多樣性**,unique source 另計)
      required_functions 覆蓋(establish/action/detail/result/reaction
        ——以 caption 關鍵詞+動能粗分類,不求精準,求缺口可見)
      max_honest_duration_sec、feasibility(ok|thin|gap)、
      recommended_action(ok|shorten_or_merge|reshoot|await_material)
M1d spec_review 新規則 B6(script_overreach):章節承諾秒數 > max_honest_duration
    → blocking;導演只能縮短/合併/列補拍清單。劇本承諾自此由供給決定。
M1e (opt-in)transcript:faster-whisper(已在字幕路徑)對 speech runs 帶時間戳
    轉寫,寫 map.speech[].text——sound-bite 檢索地基;未安裝 map 仍完整。
完成判準:對 2026-06-13 案例素材重算供需帳,它必須報出「活線=gap、生活段=thin、
建議縮短」;故意餵 30s 章節+2 支影片 3 張照,B6 攔下並給出 max_honest_duration。
```

### M2 窗口級檢索 + 新資訊審計(裁剪核心第一半)

```text
基底(不重做):_plan_matched_segment/_windows_from_clip、content_qa.score_segment
(蒸餾救援)、visual judge node 10.5 + needs_patch、broll_audit。
M2a 候選窗從 map.scenes 出(取代均勻盲切):每 scene 依 pace 出 0-2 窗。
M2b 確定性排序器(material_retrieval.py):關鍵詞分(caption/transcript ×
    visual_desc)+ 動能 fit + 時長 fit;分數與理由寫進候選(給 judge 的
    montage 附帶,可解釋)。無 caption/零分 → 不出候選(M0d 閘的上游版)。
M2c (opt-in)CLIP 重排:本地 clip-vit-base-patch32 對 top-K cosine 重排,
    掛 model_routes "ranker";未安裝退 M2b。**ranker 只排序,judge 才裁決**。
M2d sound-bite:segment 宣告 audio.role=source_speech(keep_audio)→ 候選窗
    只能出自 speech runs,端點吸附句界(有 transcript 用句界,無則 silence 邊界)。
M2e new_visual_information 審計(評估報告指標落地,擴充 visual_fatigue/
    broll_audit,不另起爐灶):
      同來源相鄰窗必須跨 scene 或幀差 > 閾值(同 scene 重切 ≠ 新鏡頭)
      new_visual_information_ratio / repeated_visual_hold_sec 進 audit 輸出
      fail → M0d 閘消費(不得 complete)
完成判準:同一 visual_desc「均勻盲切 vs map 檢索」A/B montage 給 judge 裁決;
2026-06-13 案例的「同源 23 次」在 M2e 下必須 fail 並被閘攔。
```

M2 status (2026-06-13): COMPLETE. Scene-level retrieval now ranks material-map
scenes by caption relevance, sequence function, pace/motion fit, and an optional
external ranker that may rerank but cannot admit zero-evidence scenes. The
matched planner automatically loads maps recorded in `materials_db`, selects
ranked scene windows, and emits `scene_id` plus retrieval score. `source_speech`
segments preserve audio and select mapped speech runs, preferring transcript
evidence. `new_visual_information_audit.json` measures new-visual ratio and
repeated visual hold, appears in dashboard/editor review, and blocks delivery.

Verification: focused M2 suites passed; full suite `699 tests OK`; replay of
`20260612-232948-story-mv` failed M2e with
`new_visual_information_ratio=0.4781` and
`repeated_visual_hold_sec=331.531`, exposing the repeated photos and repeated
source-time windows behind the unnatural edit.

Next: M3.

### M3 頓點裁刀(裁剪核心第二半:語音 + 動作 + 既有橋段)

```text
M3a snap 優先序擴充(edit_artifacts.snap_to_edit_point 既有機具):
    keep_audio 窗 → speech 邊界 > scene cut > motion peak;非 keep_audio 不變。
M3b jump-cut(講話長段瘦身):`jumpcut-plan <src>` 讀 map.speech 產
    jumpcut_plan.json(mark 模式只標不剪)→ agent 核可(沿用 verdict 的
    accept/needs_patch 語彙)→ `jumpcut-apply` 產 materials/processed/<id>.mp4
    記 lineage。speed_up 模式進 backlog。
M3c 動作頓點與既有橋段(評估報告的「人類式局部判斷」最小可行版):
      動作相位:map.motion 能量曲線分 rise/peak/settle;M2a 出窗時
        cut-in 對 rise、cut-out 對 settle 之後(S2a 峰值吸附的前後擴展)
      既有橋段:M1b agent 複核時標 scene 為 bridge(素材內已做好的
        特效/字卡/橋段)→ 該 scene 只能整段用或不用,不得攔腰切
    不做:跨素材的動作銜接學習、人物反應理解(誠實標註為下階段)。
完成判準:真實講話素材直剪 vs jump-cut A/B 聽感複核;課程段落 A/B
(固定秒數 vs 頓點對位)由 judge 用高密度 montage 裁決。
```

M3 status (2026-06-13): COMPLETE. Render planning now treats mapped speech,
scene boundaries, and motion peaks as ordered edit-point evidence. Clips with
`keep_audio` expand to complete intersecting speech runs and are protected from
later generic motion snapping. Action-aligned scenes use mapped
rise/peak/settle phases, while scenes reviewed as `bridge` are excluded from
primary action phase selection.

`jumpcut-plan`, `jumpcut-review`, and `jumpcut-apply` provide a review-gated
workflow with processed-material lineage. A jump-cut is never applied without
an accepted verdict, and material with no qualifying silence remains uncut.

Verification: actual action material `換桿/IMG_8346.MOV` (15.865s) produced
6 motion peaks and 6 rise/peak/settle phases. Actual speech material
`主任勉勵/IMG_2118.MOV` (70.817s) produced one continuous speech run and zero
qualifying long-silence candidates, correctly marking jump-cut as not
applicable. An 8-frame fixed-window vs motion-phase A/B showed the phase window
preserving a complete foreground walk-in action instead of an arbitrary crane
exit. This improves action continuity but does not yet identify which action is
semantically most important. Focused M3 suites and full regression passed:
`715 tests OK`.

Next: M4.

### M4 VERIFY 證據升級 + 整合驗收(用同一支案例回考)

```text
M4a 高密度蒙太奇 VERIFY(評估報告四層證據制度化;全部是 keyframe_grid
    既有機具改採樣密度 + 一個節奏條渲染器):
      全片鳥瞰 36-48 格 / 逐章 12-16 格 / 關鍵段 24-40 格 / 節奏條(全鏡頭
      長度分佈)。輸出進 verify artifacts,judge 複核以此為證據基準。
M4b 回考:**同一批 2026-06-13 學員素材重跑全鏈**。及格線:
      三行成功標準全中(可變短、可減章、不重複硬補)
      M0d/M1d/M2e 所有閘 0 繞過;judge verdict 全程留痕
      量化對照上次:2 秒內鏡頭比例、unique_source_ratio、
      max_source_repeats、新資訊比、action_phase_coverage(M1c 功能
      分類在成片 timeline 上的覆蓋)——逐項記進 decision log
      sound-bite >=1 段、jump-cut >=1 段(若該素材適用)
完成判準 = 上述全中 + 全迴歸綠 + decision log(與 2026-06-13 review 同格式,
好壞都寫)。
```

M4 status (2026-06-13): COMPLETE. M4a provides the four-layer evidence bundle.
M4b first failed and correctly routed to `revise:director(spec_review)`, then
passed after a material-aware director revision reduced the contract from 20
chapters / 660s to 15 chapters / 180.5s while preserving all must-include beats.

The replay exposed and fixed three BUILD gaps: matched candidates were consumed
from the first source instead of interleaved, `requested_duration_sec` was lost
before allocation, and an explicit director `file` choice did not override
automatic matching. The final planning replay uses distinct opening/closing
aerials and passes formal supply, timeline, b-roll, new-visual-information, and
judge-lineage gates.

Final replay metrics:
`shot_le_2s_ratio=0.0192`, `unique_source_ratio=1.0`,
`max_source_repeats=1`, `new_visual_information_ratio=1.0`,
`repeated_visual_hold_sec=0.0`, `action_phase_coverage=0.0`,
sound bites `=2`, jump-cut not applicable. Duration adaptation and chapter
adaptation both pass. See
`docs/decisions/2026-06-13-m4-material-aware-replay.md`.

Verification: M4 replay acceptance passed; full regression `731 tests OK`;
`py_compile` and `git diff --check` passed. The run is planning-only
(`--skip-render`), so final video delivery remains outside M4b acceptance.

Next: begin the post-M4 roadmap. Preserve the new rule that material supply and
explicit director duration/source choices constrain BUILD rather than merely
informing SPEC review.

### M5 True Render And Sensory Acceptance

M5 status (2026-06-13): TRUE RENDER COMPLETE; SENSORY ACCEPTANCE FAILED.

The M0-M4 material-aware plan was rendered as a real 180.5-second candidate:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260613-m5-real-render\final.mp4`.
Technical VERIFY passed at 98.7, and the four-layer montage evidence completed.
However, dense visual review against the student edit proves that the current
acceptance model still confuses file-level novelty with viewer-perceived
editing quality.

Observed gaps:

- Different source files still produce long runs of perceptually similar
  classroom, group, and ceremony compositions.
- Motion-peak snapping can show no visible setup/execution/result progression.
- Opening, course transitions, and ending lack designed sequence grammar.
- Technical VERIFY passes while story tension and human-edit feel do not.

M5 scope decision (2026-06-14):

- The 180.5-second result is accepted as the current material-limited baseline,
  not as a human-edit-quality reference.
- Freeze M0-M4 behavior. Do not keep tuning the 67th case to manufacture a
  sensory pass from limited material.
- M5a and M5b remain tier-2 review evidence. They are not delivery-authorizing
  truth and must not be promoted into `HARD_AUDITS` without broader validation.
- M5c/M5d/M5e are deferred until a case with richer, intentionally collected
  material is available. They are not the immediate active roadmap.

M5 component status:

1. M5a perceptual composition novelty audit. ✅ 機制已實作，維持 tier-2 證據
   `semantic_novelty_audit.py`:dHash 感知雜湊(純 PIL,無模型)+ 貪婪聚類;
   fail 條件 distinct_composition_ratio<0.5 或同構連續段>6s。接 dashboard
   node 11 + CLI `semantic-novelty-audit`，不列入 delivery_gate HARD_AUDITS。
   dHash 是構圖近似代理指標，不宣稱真正語義理解。67th 真渲抓到 10s
   近似構圖連續段；CLIP 仍為 opt-in。
2. M5b action setup-execution-result progression audit. 🟨 機制已實作，整合未完成
   `action_progression.py`:確定性雙語 caption+動能 `classify_function`(填補
   action_phase_coverage=0.0 的根因——功能標註過去只靠 agent 複核);掛進
   material_retrieval 讓候選窗自帶 function,流進 timeline。audit 對宣告
   required_functions 的段檢查 establish→action→result spine 覆蓋與順序。
   接 dashboard node 11 + CLI `action-progression-audit`，不列入 HARD_AUDITS。
   67th 現有 contract/timeline 未宣告 required_functions，實測結果為
   `no_required_functions`，因此不能宣稱此案例 action coverage 已通過；
   後續仍需把 contract grammar 與 timeline clips 組成可審 segment。
3. M5c designed sequence grammar for opener, course transitions, and ending.
   ⬜ 未做(tier-2;開場/課程轉場/結尾的可執行結構)。
4. M5d high-density human-vs-agent critical-section comparison. ⬜ 未做
   (M4a 四層蒙太奇機具已在,缺的是與學員片關鍵段的並排比對流程)。
5. M5e rerender; require both technical and sensory acceptance. ⬜ 未做
   (deferred; do not rerender the limited 67th case merely to raise proxy
   metrics. Resume only with a richer comparison case and explicit acceptance
   rubric.)

### M5a/M5b 重新定位:Visual Diversity Guard(2026-06-14,務實化)

使用者方向(取代 M5a/M5b 原本的偵測雄心):**目標不是理解畫面語義或動作故事,
而是「避免觀眾連續看到相似素材造成視覺疲乏」**。素材挑選仍由人工/Agent 候選排序
完成,系統只阻止明顯重複。比目前 M5a/M5b 更務實、更可靠 Agent 化。

主線:
```
人工／Agent 挑選候選素材
→ ingest 時粗分類視覺家族(coarse,不是像素偵測)
→ BUILD soft-ranking:正確性優先,多樣性加分(不是硬跳過)
→ 缺素材時標缺口,允許人工挑選或合成
→ VERIFY:未解決的視覺疲乏顯示為 tier-2 warning(不擋交付)
```

**核心修正(2026-06-14,採納 Codex 反駁,推翻先前硬規則寫法):多樣性是
soft-ranking 的加分項,永遠不得凌駕素材正確性。** 先前「禁止同 family 連續/
冷卻內就跳過」是硬規則,素材不足時會逼出更嚴重的錯誤(為換畫面用無關素材、
跳過唯一能證明事件的關鍵鏡頭、影片優先害關鍵照片永不被選)。改為下列順序:

```
選片優先序(BUILD,前項永遠壓後項):
1. must_have / proof / identity / need 滿足   ← tier-1 正確性,不可被多樣性犧牲
2. 故事與段落相關性
3. 已核准(judge accepted)素材
4. media_type 弱偏好(影片略優於照片——弱 prior,非硬規則;
   照片若是最佳/唯一證據仍勝出)
5. visual_family / angle_scale / action_family 多樣性加分(tiebreaker)
6. 照片與允許的 fallback
```

規則(粗粒度,全部可機械判,tier-2 品質;**全為加分/警示,非阻擋**):
- 連續同 `visual_family` → **降分,不是禁止**(集合廣角→集合廣角即使不同檔案
  也算同家族——這是 67th 單調根因,但解法是降權重排,不是 veto)。
- `angle_scale`(遠/中/近)、人物/場景/視角交替 → 加分。
- 相同來源冷卻(已有,見下「重用」)。
- 單一動作疲乏 = `action_family` 連續 → 降分,併入本守門,不另立 M5b 大系統。

落地原則(給 Codex):
- **重用 `visual_fatigue_audit`,不要另建平行系統**——它已有 source 冷卻、最少鏡頭、
  reuse 上限;VERIFY 端的守門 = 讓它再消費 `visual_family` / `angle_scale` /
  `action_family`,**以 warning 呈現**(連續同家族、單調)。不 fail、不擋交付。
- **dHash 降為輔助**:只可靠抓「近乎相同畫面」(字面近重複),作為 backstop,
  **不主導選片**;`semantic_novelty_audit` 留著當這個窄用途,別讓它驅動。
- M5b 的 establish→action→result spine 雄心**收掉**;只保留 `action_family`
  連續疲乏這一條併入守門(action_phase_coverage 不再是驗收門檻)。
- **視覺家族是 per-project 詞彙,不可寫死**:範例(戶外集合廣角/課堂教學/講師正面/
  學員團體照/高空作業/工具操作特寫/人物反應/校園空拍)是結訓片專屬;通用的只有
  **軸**(`media_type` 沿用 asset_type、`angle_scale` wide|medium|close、subject),
  家族清單由 Agent 在 ingest/caption 複核時依專案填,系統只認軸 + 專案家族表。
- **未標註素材必須優雅降級**:soft-ranker 遇到沒有 `visual_family` 的素材,
  退回現行行為(只用相關性/核准/媒體型別),不得因缺標籤而排除素材或中止 BUILD。

#### VD 實作順序(soft-ranking 在標籤覆蓋率有證據之後才寫)

```
VD0  淺標籤契約 + lineage              ✅ 已完成(見下)
VD1  標籤覆蓋率驗證(開工前的閘):    ✅ 契約完成;真實素材證據已產生
       在真實素材上量:標註覆蓋率%、未標比例、
       同素材跨 Agent 分類一致性(粗粒度,不要求完全一致);
       覆蓋率/一致性達標才值得寫 ranker,否則 ranker 多數時間沒資料。
VD2  BUILD soft-ranking(editor 端)   ⬜ blocked:真實素材 VD0 覆蓋率 0%,無一致性證據
VD3  VERIFY tier-2 warning backstop    ⬜ 擴充 visual_fatigue 吃家族,只警示
```

承載輸入是 ingest 時的淺標籤——**沒標 soft-ranker 就只能退回現行行為**,所以
VD1 的覆蓋率證據是 VD2 的前置閘。M1b/E7 的 agent 複核點就是寫這些欄位的地方。
本守門獨立於 M6 delta。

**通用 skill 的粒度(回應「想做通用 SKILL」+ Codex 審慎):現在先寫成一份
通用的 Visual Diversity contract/policy**(通用軸 `media_type`/`angle_scale`/
`subject` + 粗分類方法 + soft-ranking 原則),由 curator(標)/ editor(排)/
verify(警示)三個角色技能共同引用,**不另起第 4 套執行流程**。等 VD2 在 editor
端真的消費標籤、跑通一個非結訓案例後,再決定是否包裝成可獨立啟動的 Skill——
否則現在做會是一個多數時間沒資料、責任模糊的空殼。家族詞彙永遠 per-project。

#### VD0 Shallow-label contract ✅ complete (bounded)

- `apply_scene_review_verdict` 保存四個淺標籤；`curator.md` 明定複核責任。
- 標籤缺失代表 `unreviewed`，不是 pass，也不是 tier-1 fail。
- 驗收只證明標籤能從 review verdict 寫入 material-map scene 並保留 lineage。
- 非目標：此階段不寫 family cooldown、不改選片、不宣稱品質提升。
- Evidence: scene-review lineage test plus dashboard/runtime tier-2
  nonblocking tests; full regression `760 tests OK` on 2026-06-14.

Decision log:
`docs/decisions/2026-06-13-m5-real-render-sensory-acceptance.md`、
`docs/decisions/2026-06-14-m6a-review-response.md`。
M5a/M5b 實作見 commit(semantic_novelty_audit / action_progression)。

### Next After VD0: M6 Material-Map Lifecycle

**Product decision:** default editing remains actual-material-first. A
script-first workflow is supported as a pre-production planning mode, but every
final edit must be revised against actual material evidence before BUILD.

Do not invent duplicate schemas. Canonicalize the existing artifacts:

| Lifecycle concept | Canonical artifact | Current state |
|---|---|---|
| Required material map | `material_needs.json` + `shooting_brief.md` | Existing Skill flow; weak runtime integration |
| Actual material map | per-asset `*.map.json` + `supply_review.json` | Implemented and enforced before BUILD |
| Requirement-vs-actual delta | `material_delta.json` | Missing |
| Revised executable story | revised `segment_contract.json` | Exists, but not yet driven by a canonical delta |

#### M6a Canonical contracts ✅ contract layer complete (2026-06-14)

> Codex re-review passed after hardening rounds 1-3.
> round 2(`c810ab3`):`fallback_tier` 嚴格型別(拒 boolean `True`/字串/float
> ——`True in (1,2,3,4)` 在 Python 為 True 的陷阱)+ CLI 驗證失敗回非零 exit code。
> round 3(本輪):`apply_satisfaction_verdict` 強制 `valid_need_ids`(未提供即
> ValueError,堵住 unchecked 寫入路徑);`need_id` 僅接受非空字串(canonical 與
> verdict 兩端);`fallback_options` 僅接受 list[str](移除靜默 `list()` 轉型);
> 移除 permissive satisfaction 測試。**全套件 791 tests OK**。


實作 `material_needs.py` + `validate-needs` CLI + `tests/test_material_needs.py`。
M6a-hardening 已修正契約 review 抓到的 4 個問題(F1-F4):
- **F1 身分穩定(關鍵)**:三件事分離——`migrate_material_needs`(配置/遷移,
  只給缺 id 的 need 配 id,content-hash 僅為**首次配置初值**)、`validate_material_needs`
  (嚴格驗證,**不配置、不改 join key、不靜默轉型**)、編輯(改 purpose/type/
  category 永不改 id)。canonical need 一旦有 id 即永久保留;改用途不再換 id。
- **F2 重複 id**:明確重複 `need_id` → validation **error**(不再靜默加 _2 後綴);
  自動配置只在遷移缺 id 時發生,且 content-identical 衝突會加註 migration_notes。
- **F3 reference integrity**:`apply_satisfaction_verdict(..., valid_need_ids=...)`
  **強制**白名單(round 3:未提供即 ValueError),對不存在/非字串 need_id **raise**
  (typo 不再形成幽靈 edge);`need_ids()` 提供白名單。
- **F4 嚴格型別**:`must_have` 只接受 boolean(`"false"` → error)、`count` 只接受
  正整數(0/負/字串/float/bool → error,不再「treated as 1」卻沒改值)。
- **穩定 project-local `need_id`**,與 segment 編號無關;章節 renumber 不改 id;
  legacy `id` 僅保留為 `display_id`,segment 降為 advisory `segment_hint`。
- **scene-level `satisfies` edge**:status = candidate|accepted|rejected + lineage
  (轉換記 `previous_status`,timestamp 由 verdict 提供,無隱藏時鐘)。
- `summarize_satisfaction` 是 scene→need 唯讀反查(**非 delta**)。
- 向後相容:無 needs / 無 satisfies 的純既有素材流程不受影響;legacy 巢狀與 flat
  皆可輸入;未碰 supply_review / rank-local。**全套件 791 tests OK(round 3)**。

#### M6a Lineage Integration ✅ reference chain complete (2026-06-14)

The end-to-end `need_id` reference chain now joins every artifact, with NO
`material_delta` decision (that boundary is M6b):

```
need_id (material_needs)
  → shooting-brief requirement (shooting_brief.requirements[].need_id)
  → scene satisfies edge        (material_map.scenes[].satisfies[].need_id)
  → revised segment_contract    (segment.material_fit.need_refs[])
```

- `material_lineage.build_shooting_brief(needs)` projects each **strict-validated**
  canonical need into a brief requirement carrying its `need_id` (the join key
  the human-authored prose brief must preserve). It is a projection, not a second
  required-map format; invalid/un-migrated needs raise.
- `segment_contract` gains optional `material_fit.need_refs` (list of need_id).
  `spec_contract.validate_segment_contract` validates **shape only** (non-empty
  string array); the cross-file join is enforced by the linker — same split as
  `blueprint_ref`.
- `material_lineage.link_lineage(needs, shooting_brief, material_maps, contract)`
  produces a neutral join view (`chain[need_id] = {in_brief, satisfied_by,
  contract_segments}`) and fails (`ok=False`) only on a **dangling reference** —
  any brief/satisfies/contract hop pointing at a need_id absent from canonical
  needs. It makes NO covered/thin/missing verdict: a need with zero satisfying
  scenes is reported as-is, never flagged missing.
- CLI `lineage-link [--build-brief] [--brief] [--project-map] [--contract]`.
  Reuses `summarize_satisfaction` (scene→need inversion) and
  `expand_project_material_map` (MR1 loader). Backward compatible: needs-only or
  no-need_refs flows stay `ok`.

Falsification tests `tests/test_material_lineage.py` (brief carries need_id;
invalid needs cannot build a brief; need_refs shape; need_id survives all four
artifacts; dangling at each hop fails; no-delta boundary asserts no
coverage/route/status keys leak): 11 tests. Full regression: **900 tests OK**.
M6b `material_delta` stays deferred — it now has a join to diff over.

M6a lineage hardening (2026-06-14): (1) `contract_need_refs` returns ordered
records `[{segment_ref, segment_index, need_refs}]` instead of a dict keyed by
`section_role` — a repeated role no longer overwrites a sibling's references, so
a dangling ref on the first of two same-role segments is caught. (2) `link_lineage`
now shape-validates every supplied artifact reference (brief requirement = object
with non-empty-string need_id; contract need_refs = non-empty list of need_id
strings, no silent filtering; satisfies edge = object with non-empty-string
need_id and candidate/accepted/rejected status, reusing material_needs'
`VALID_STATUSES`). Malformed input returns `ok=False` + errors without crashing
(satisfaction inversion is now built crash-safe inline rather than via
`summarize_satisfaction` on unvalidated data). Reverse tests: repeated-role
dangling, brief missing/non-string need_id, contract `[123]`/`[]`/non-list,
satisfies non-object/non-string/illegal-status, legal four-link still ok. Focused:
16 tests OK; full regression: **905 tests OK**.

M6a lineage final hardening (2026-06-14): `chain.contract_segments` now
preserves both display `segment_ref` and artifact-local `segment_index`, so
same-role segments remain individually addressable by downstream M6b/M6c.
`segment_index` is intentionally only an identity inside the current contract
artifact; it is not claimed stable after contract reordering. Supplied
shooting-brief and contract top-level shapes now fail safely (`ok=False` +
errors) instead of crashing or silently passing. Reverse tests cover duplicate
display roles and malformed top-level brief/contract inputs. Focused:
18 tests OK; full regression: **907 tests OK**.

Original design goals (all met by the above):

- Model one lifecycle with existing-material and planned-capture entry points;
  partial material availability is first-class, not a third branch.
- Validate and canonicalize existing `material_needs.json` before downstream use.
- Add the load-bearing `satisfies: [need_id]` edge on reviewed assets/scenes.
- Reconcile requirement-purpose vocabulary before any delta implementation.
- Specify stable IDs linking requirement → shooting brief → actual asset/scene
  → revised contract segment.
- Reuse `material_needs.json`; do not create a second required-map format.
- Acceptance: the same requirement ID survives through every artifact, and
  every entry point converges on actual-material review before BUILD.

#### M6b Material delta

- Produce `material_delta.json` by comparing requirements with actual supply.
- Required outcomes: `covered`, `thin`, `missing`, `wrong_semantics`,
  `insufficient_action_phases`, and `excess/unplanned`.
- Each delta must carry evidence and one explicit route:
  `collect_material`, `reshoot`, `shorten_or_merge`, `script_rewrite`,
  `drop_segment`, or `dashboard_review`.
- Acceptance: no requested beat silently becomes an unrelated clip.

##### M6b increment 1 ✅ coverage-based outcomes (2026-06-15)

Bounded first increment, built ONLY on the validated M6a join
(`material_needs → satisfies edges → link_lineage`). `material_delta.py`
`compute_material_delta(needs, material_maps)` emits a deterministic per-need
outcome — `covered | thin | missing | excess` — each with `tier`, `route`,
`reason`, and `evidence` (the counts it decided from), plus a machine-readable
`blocks_ready_for_build` and a top-level `ready_for_build`.

- Deterministic thresholds: `usable = accepted + candidate`. `usable==0` →
  `missing`; `accepted > count` → `excess`; `accepted >= count` → `covered`;
  else → `thin` (candidate-only material is thin, never missing).
- **Only tier-1 case this increment**: a `must_have` need with no usable
  material AND no permitted `fallback_options` → `tier=1`, route `reshoot`,
  `blocks_ready_for_build=true`. `must_have` WITH a permitted fallback, and all
  optional misses, are `tier=2` and do not block.
- **Broken join ≠ missing**: an invalid `material_needs` or a dangling/malformed
  satisfies edge makes the whole delta `ok=False` with `errors` and zero deltas
  — it is never silently classified as `missing`.
- CLI `material-delta <needs> [--project-map] [--out]`. Reuses
  `expand_project_material_map` + `link_lineage`; exits non-zero only on `ok=False`.

Deferred to a later batch (confirmed): `wrong_semantics` /
`insufficient_action_phases` (need the F2 canonical shot-function vocabulary; no
`action_progression` dependency taken here), and wiring `blocks_ready_for_build`
into the pre-BUILD gate (`delivery_gate` stays a backstop only, not the primary
block site). No BUILD ranking / script / timeline change.

Falsification tests `tests/test_material_delta.py` (covered/thin/excess/missing
thresholds incl. candidate-only=thin and rejected-only=missing; must_have+no-
fallback+missing → tier-1 blocks; legal fallback → not tier-1; optional miss
does not block; the minimal one-must_have-zero-material disproof; dangling/
malformed/invalid → fail-not-missing; no-semantic-field boundary; multi-need
summary): 14 tests. Full regression: **921 tests OK**. F2 stays deferred until a
real case proves semantic function classification is needed.

M6b increment-1 hardening (2026-06-15): coverage now counts only BUILD-usable
evidence. (1) A satisfying scene is counted only if its source is a non-empty
string and its start/end are valid numbers with `end > start`; unrenderable
evidence is recorded in `evidence.dropped_evidence` (reason
`missing_source`/`invalid_bounds`/`non_positive_length`) and never makes a need
`covered` — so a zero-length or sourceless accepted scene cannot flip a must_have
need to `ready_for_build`. (2) `fallback_options` items must be trimmed non-empty
strings; `[""]`/`["   "]` now fail validation (→ `ok=False`) and therefore cannot
relieve a tier-1 block. (3) Evidence is deduped by `(need_id, asset_id,
scene_index)` at its strongest status, so a duplicated accepted scene cannot
inflate `covered`/`excess`. Future pre-BUILD gate MUST require
`delta.ok is True AND delta.ready_for_build is True` (not `blocks_ready_for_build`
alone) — documented in `material_delta` module. Reverse tests: zero-length /
missing-source / invalid-bounds accepted dropped; duplicate accepted counted
once; `[""]`/`["   "]` fallback fails. Focused: 19 tests OK; full regression:
**926 tests OK**.

M6b increment-1 identity hardening (2026-06-15): `compute_material_delta` now
requires every input material map to carry a non-empty-string `asset_id` that is
unique across the input — `asset_id` is the identity half of the
`(asset_id, scene_index)` evidence key, so a missing/blank/non-string or
duplicate id makes evidence resolution ambiguous and order-dependent. Such input
is a hard failure (`ok=False`, `ready_for_build=False`, `deltas=[]`), never
silently resolved into covered/missing. Reverse tests: duplicate asset_id fails
in both map orders (no order-dependent verdict); missing/blank/non-string id
fails; unique ids still pass. Focused: 22 tests OK; full regression:
**929 tests OK**.

##### M6b pre-BUILD gate ✅ integrated (2026-06-15)

`material_delta` is now a real BUILD-blocking dependency. `material_delta.material_delta_gate`
is a fail-closed verdict built ONLY on `compute_material_delta` (no second delta
logic): a build may proceed iff `delta.ok is True AND delta.ready_for_build is
True` — `blocks_ready_for_build` alone is insufficient.

- **Lifecycle position**: `contract_adapter.run_contract`, AFTER the `spec_review`
  `ready_for_build` gate and BEFORE music/timeline/`mv_chain` render. A blocked
  build returns `{ok:False, stage:"material_delta", ...}` and never renders a new
  final. If a previous build's `final.mp4` already exists, it is **moved aside**
  to `stale_previous_final.mp4` (never silently deleted) so it cannot masquerade
  as this run's output; `state.json`/result record `final: null` and
  `stale_final_path`. `delivery_gate.HARD_AUDITS` is untouched (backstop only).
- **Existing-material-first skip**: the gate runs only when the contract declares
  `material_needs_ref`. No declaration → skipped → existing flow unchanged
  (backward compatible). Declared-but-missing / unparseable needs, or a
  declared-but-missing/corrupt per-asset map, are hard blocks (fail-closed),
  never a silent skip or "treated as zero material".
- **Freshness**: the verdict is computed fresh from the current `material_needs`
  + current per-asset maps every run; a stale `material_delta.json` is never
  trusted (it is overwritten with the truth). No second delta judgment path.
- **Diagnostics on block**: `state.json` + return carry `stage`, `next_action`
  (`await_material` for tier-1 missing, `revise:material(material_delta)` for
  broken/invalid), `route` (`await_material` | `fix_material_map_or_needs`),
  `blocking_need_ids`, `reason`, and the `material_delta.json` evidence path.
  Non-blocking thin / optional-missing pass with the delta artifact as warning.

Falsification tests `tests/test_material_delta_gate.py` (A no-needs runs existing
flow; B covered passes; C must_have+no-fallback blocks; D must_have+fallback does
not tier-1 block; E broken satisfies → fix-route block not missing; F declared
needs file missing → fail-closed; G corrupt map / invalid asset identity blocks;
H stale artifact ignored, recomputed and overwritten; I tier-1 block stops before
render — `mv_chain` not called, no final video; J gate-pass lets render run):
13 tests. Full regression: **942 tests OK**.

M6b gate final hardening (2026-06-15): (1) on block, a pre-existing `final.mp4`
is quarantined to `stale_previous_final.mp4` (atomic move, preserved not
deleted); `state.json`/result carry `final: null` + `stale_final_path`, so a
stale render can never be reported as this run's success. (2) `material_needs_ref`
is strictly validated — only an ABSENT key skips (existing-material-first); a
present-but-malformed value (`""`/`"   "`/non-string/`[]`/`{}`) is a fail-closed
verdict, never a crash. (3) Relative `material_map` paths resolve against the
`material_db.json` directory (not the process cwd); declared-but-unresolvable
maps block. Reverse tests: stale-final quarantine + lineage; malformed ref
fail-closed; cwd-independent relative-map resolution; unresolvable relative map
blocks; absent key still skips. Focused: 18 tests OK; full regression:
**947 tests OK**.

**Next step: M6c delta-driven script revision** (convert accepted delta decisions
into a revised `segment_contract.json`; preserve director decisions; record
revision lineage). The M6b gate stays the objective tier-1 block; M6c is a
separate batch. F2 / `wrong_semantics` / `insufficient_action_phases` remain
deferred.

#### M6c Delta-driven script revision

- Convert accepted delta decisions into a revised `segment_contract.json`.
- Preserve human/director decisions and record revision lineage.
- BUILD remains blocked only by objective tier-1 gaps; aesthetic tier-2
  findings remain review evidence.
- Acceptance: a missing requirement either changes the script, requests
  material, or is explicitly waived. It is never hidden by repetition.

#### M6d Independent Material Map Skill

- Expose the lifecycle as an independently runnable Skill/template:
  discussion → required map → shooting brief → ingest actual material →
  actual map → delta → revised script.
- It must also support starting from existing material, skipping required-map
  generation until the user chooses to discuss or request missing shots.
- Acceptance: the Skill can stop after planning/collection guidance without
  forcing a video render.

#### M6e Validation

- Validate with two cases, not only 67th:
  1. existing-material-only case with honest shortening;
  2. script-first case where requested shots are collected, missed, and revised.
- Do not promote new proxy metrics to tier-1 based only on unit tests.
- Completion requires artifact lineage, route correctness, and human review of
  whether the revised script matches actual supply.

**Explicit non-goals for M6:** effects expansion, CLIP as a hard dependency,
automatic claim of semantic understanding, forced ten-minute duration, and
further 67th-specific sensory tuning.

M6a must not revive the deprecated M5b `establish → action → result` acceptance
spine. Requirement-purpose vocabulary and Visual Diversity labels solve
different problems and must remain separate.

Review handoff:
`docs/decisions/2026-06-14-roadmap-course-correction.md`.

### MM1 Project Material Map V1 — COMPLETE (2026-06-14, Codex review passed)

`project_material_map.py` + `project-material-map` CLI + `tests/test_project_material_map.py`
(14 tests). 6 acceptance criteria + hardening:
- deterministic aggregate (sorted by asset_id); CLI writes `project_material_map.json`.
- **reference integrity**: every satisfies edge validated (object / non-empty
  string need_id / status in candidate|accepted|rejected / known need_id);
  unknown need_id fails when needs present; **a satisfies edge with no canonical
  needs fails** (phantom-edge bypass closed).
- **asset_id** must be a unique non-empty string (duplicate / empty / non-string fail).
- **needs_path** explicitly provided but missing → fail (not silently treated as needs-less).
- **metrics renamed for honesty**: `captioned_scene_ratio` (scenes with a caption)
  and `vd0_labeled_scene_ratio` (scenes with ≥1 VD0 label) — no longer overclaim
  "reviewed" / full "label coverage".
- projects without needs stay valid; non-goals held (no delta/decision, BUILD, UI).

**Goal:** aggregate the existing per-asset `*.map.json` evidence into one
project-level material map that can be consumed by agents, BUILD, and a future
UI without creating another source of truth.

Canonical output: `project_material_map.json`.

Minimum contract:

```json
{
  "artifact_role": "project_material_map",
  "version": 1,
  "assets": [],
  "needs": [],
  "satisfaction_summary": {},
  "metrics": {
    "asset_count": 0,
    "scene_count": 0,
    "captioned_scene_ratio": 0,
    "vd0_labeled_scene_ratio": 0
  }
}
```

Required behavior:

- Aggregate asset and scene identity, caption, speech, motion evidence, VD0
  shallow labels, and validated scene-level `satisfies` edges.
- When canonical material needs exist, include the validated needs and a
  read-only satisfaction summary.
- When no material needs exist, remain useful as an existing-material-first
  library.
- Preserve source evidence and lineage; do not silently invent labels or edges.
- Produce deterministic output for identical inputs.

Explicit non-goals:

- No `covered` / `thin` / `missing` decision and no `material_delta`.
- No script revision, BUILD ranking, Dashboard/UI, Node 14, or effects work.
- Do not replace per-asset maps; the project map is their validated aggregate.

Acceptance:

1. Multiple per-asset maps aggregate into one deterministic project map.
2. Unknown or invalid `satisfies.need_id` references fail.
3. Projects without material needs remain valid.
4. Metrics truthfully report asset/scene count and review/label coverage.
5. A CLI produces `project_material_map.json`.
6. Focused tests and the full regression pass.

### BA1 BUILD Alignment Audit — COMPLETE (2026-06-14, Codex review passed)

`docs/build-capability-alignment.md`: split into A) pre-BUILD gates B) BUILD
capabilities C) VERIFY audits. motion_graphics BUILD consumer corrected to the
`contract_adapter` build path (Node 14 = scaffold only, not a consumer). Key
finding — render-time grammar is `active` in BUILD; the material-evidence layer
(needs/satisfies/MM1/VD0) is `declared_only`; M2 retrieval is `partial`.
Smallest high-value gap = BR1 opening/hook. Documentation only, no feature.

### BR1 Opening / Hook Sequence Builder — implemented + hardened (2026-06-14), pending Codex review

BR1-hardening: `sound_punctuation` cues resolved AFTER clips, only emit when the
`title_reveal` anchor exists (else `anchor_missing:title_reveal`).

BR1 duration contract (2026-06-14): **`shot.dur` = approved window length, so
available = dur (start is the window's position, NOT a deduction)**; video clip =
`min(design_dur, dur)`. Video shots with missing / non-numeric / ≤0 dur are
**dropped** (`invalid_video_dur`), never rendered at a guessed design length.
Photos keep their design length (loop). 18 tests incl. two real renders +
opening_pool_from_plan→clip extract integration. 823 full regression OK.


`opening_sequence.py` + `run_mv` integration + `tests/test_opening_sequence.py`
(10 tests incl. real render). Compiles an approved recipe into render-plan clips
(hook slow-push / context montage / title-reveal card / sound-punctuation cue /
story-entry marker), `prepend_opening_to_plan` reindexes slot_index across the
whole plan. **Changes timeline AND true render** (real-render test renders the
compiled opening, incl. title overlay, to a video of expected duration).
Graceful fallback: beats with no material are dropped and recorded; no recipe →
plan unchanged. Consumed via `script["opening_recipe"]`. sound_punctuation is a
cue only (audio wiring is BR3). No VERIFY-only behavior — it is a BUILD change.

**Goal:** identify which existing dictionaries, Skills, and tools actually
change BUILD output before adding more BUILD features.

Required output: `docs/build-capability-alignment.md`.

Required table:

| Capability | Declared source | Existing tool | BUILD consumer | Timeline evidence | Render evidence | Status |
|---|---|---|---|---|---|---|

Allowed status values:

```text
active | partial | declared_only | missing | deprecated
```

Acceptance:

- Every capability claimed as `active` names a real BUILD consumer and
  timeline/render evidence.
- Declared-only policies and unused tools are listed rather than treated as
  implemented.
- The audit identifies the smallest high-value BUILD gaps.
- This is a bounded documentation audit: no new feature, no new quality audit,
  and no renderer rewrite.

### Tool And Responsibility Boundary

Use this boundary for MM1, BA1, and later BUILD work:

```text
Agent / Skill
  chooses creative intent, project vocabulary, and a supported recipe

Deterministic tool
  validates inputs and compiles the chosen recipe into artifacts/timeline

BUILD
  consumes approved material evidence and recipes to produce the edit

VERIFY
  checks the result; it does not create excitement or choose a replacement

Future UI
  submits review/change-request artifacts; it does not directly mutate
  canonical material maps, contracts, timeline, or route state
```

### BUILD Thickening Backlog

After MM1 and BA1 review, implement one bounded capability at a time in this
priority order:

#### BR1 Opening / Hook Sequence Builder — P0

Compile an approved opening recipe into a designed opening sequence:

```text
hook visual -> quick context montage -> sound punctuation
-> title reveal -> story entry
```

Acceptance must prove the recipe changes the timeline and true render. It must
gracefully fall back when the required material is unavailable.

#### BR2 Beat-to-Sequence Recipes — P0 — COMPLETE (2026-06-14)

`beat_sequence.py` + `run_mv` per-segment hook + `tests/test_beat_sequence.py`
(11 tests incl. real render). A segment opting into `beat_recipe` is compiled
into context → primary_action → detail_reaction → payoff and **replaces that
segment's render-plan slots** (real timeline change). Reuses BR1's approved-window
contract (`_usable_shot`/`_effective_dur`) so all video windows obey {start,dur}.
Graceful fallback drops beats with no material; no recipe → segment unchanged.
Optional payoff punctuation cue emitted only when the payoff clip exists.
Selectable recipe, NOT a universal action-spine gate.
BR2-hardening (2026-06-14): replaced slots inherit segment semantics —
keep_audio/audio_role, text/subtitle/narrative layer (every slot, mirroring
`_windows_from_clip`), and `anti_presentation_plan` (BR2 now runs before the
anti-presentation pass); trace metadata (attention_budget/creative_exception/
beat_alignment/reason) still applied by the slot loop. Reverse tests cover
keep_audio/audio_role + text placement.

```text
context -> primary action -> detail/reaction -> payoff
```

#### VD1 / VD2 Visual Diversity Evidence And Soft Ranking — P1

**VD1 evidence contract completed (2026-06-14); VD2 remains blocked.**
`visual_diversity_coverage.py` + `visual-diversity-coverage` CLI reads the
validated `project_material_map.json` and emits
`visual_diversity_coverage.json`: per-axis labeled/missing counts and scene
references, any/full-label ratios, and an explicit `ready_for_vd2` decision.
The default preconditions are `visual_family` coverage >= 0.70,
`angle_scale` coverage >= 0.60, and an independent coarse-label review with at
least 10 comparable scenes and >= 0.70 agreement **on each required axis**.
`action_family` and `subject` remain measured but do not universally block
because they may be inapplicable. The CLI accepts repeatable
`--consistency-review` project maps. It performs no ranking, selection, or map
mutation.

A reproducible evidence run used 12 real photo assets selected from distinct
folders under `_整理後`. The resulting project map had 12 scenes, but actual
VD0 coverage was 0% and no independent consistency review existed. Therefore
VD2 is truthfully blocked; writing the ranker now would produce a feature that
usually has no labels to consume. Generated evidence is kept under
`.tmp/vd1-real-evidence/` and is not a claimed review artifact.

After that evidence exists, labels may be used only as a soft tiebreaker after
correctness, relevance, and approved material.

#### BR3 Music / Sound Punctuation — COMPLETE (2026-06-14)

`punctuation.py` + `run_mv` post-render hook + `tests/test_punctuation.py`
(8 tests incl. real audio mix). Consumes BR1/BR2 valid cues: resolves each
anchor to a timeline timestamp (cumulative extract_dur of the matching produced
role, segment-scoped), maps cue type → CC0 sfx asset, and **remuxes the hits
into the rendered video's audio** via the loudness-preserving sfx filter (real
output change). Cues whose anchor is absent/dropped are dropped
(`anchor_missing:`). No cues → audio unchanged. Real-mix test proves a hit
raises audio energy at its anchor time vs the silent baseline.
BR3-hardening (2026-06-14): cue resolver computes anchor time with **xfade/
transition overlap** (a crossfading clip starts `transition_duration` earlier),
matching the render's `_build_transition_filter`. `apply_punctuation_to_video`
returns `{status, cues_mixed, error}`; a non-zero ffmpeg exit or missing output
raises `PunctuationMixError` (never reported as mixed). run_mv stays non-fatal
but records `status=failed`, `error`, `cues_mixed=0`. Reverse tests cover xfade
timing and remux failure.

BR3 final alignment (2026-06-14): cue timing now mirrors renderer
**contiguous-segment groups** and clamps overlap with
`min(transition_duration, accumulated_duration, incoming_group_duration)`.
Transitions declared inside one group do not shift time; oversized transitions
cannot produce negative cue timestamps. Focused BR1/BR2/BR3/VD1/MM1 suite:
61 tests OK; full regression: 852 tests OK.

#### BR4 Ending / Payoff Sequence — COMPLETE (2026-06-14)

`ending_sequence.py` compiles an approved script-level `ending_recipe` into
`callback -> payoff -> closing_title` clips and appends them to the real render
plan. Its default pool walks the story tail backward, all video windows reuse
BR1's approved `{start,dur}` contract, and an optional payoff cue flows into
BR3. Missing recipe/material leaves the existing plan unchanged; title and cue
anchors are emitted only when their visual beat exists. Focused tests include
plan integration, negative fallbacks, bookend composition, and a true ffmpeg
render. Focused BR1/BR2/BR3/BR4/VD1 suite: 64 tests OK; full regression:
869 tests OK.

#### MR1 Map-Based Window Retrieval — PARTIAL → ACTIVE (2026-06-14)

Promotes M2 map retrieval from a clip_list-gated path to the **default** local
selection path. Previously `plan_ranked_windows` only fired inside the matched
branch (i.e. after a `match-mv` clip_list existed); a direct `run_mv` with maps
but no clip_list fell through to live VLM scoring. Now:

- **Single loading entry** `project_material_map.expand_project_material_map`
  normalizes a `project_material_map` dict / per-asset list / single map into the
  per-asset maps retrieval consumes (verbatim — no second scene schema). Unknown
  `artifact_role`, sourceless project asset, and non-numeric scene bounds fail
  loudly; `run_mv` normalizes once at entry.
- **Default + fallback** `mv_cut._plan_local_segment`: map-ranked first whenever
  a valid map exists → **matched_fallback** (clip_list/explicit file picks) →
  **live_fallback** (VLM on material_root) → honest GAP only when nothing exists.
  A map with no evidence-fit scene for a segment never emits an empty/GAP segment
  on its own. Every per-seg entry records `retrieval_path ∈ {map_ranked,
  matched_fallback, matched, live_fallback, live}`.
- **Window/source honesty** `plan_ranked_windows`: sourceless and zero/negative
  length scenes never enter the timeline; the window is clamped strictly within
  the scene `[start,end]`; slots preserve `source/scene_id/extract_start/
  extract_dur/retrieval_score`. Existing caption/function/pace evidence scoring
  unchanged — no `visual_family`/diversity ranking, no VD2, no dHash/CLIP/VLM
  dependency added.
- Stock, photo_stack, and `source_speech` (`plan_sound_bite`) paths unchanged.

Falsification tests `tests/test_map_retrieval_wiring.py` (A map-ranked w/o
clip_list; B matched & live fallback; C no-map compat; D project-map expansion;
E malformed/sourceless/zero-length; F window-in-bounds; G **real ffmpeg
map-ranked render**; H stock/source_speech no-regression): 17 tests. Full
regression: **886 tests OK**.

MR1 hardening (2026-06-14): two correctness fixes after self/Codex review.
(1) `_plan_local_segment` fallback now keys on *actual usable slots*, not on
`clip_list is not None`: a segment with no picks (or whose matched picks yield
no window) continues to the live fallback instead of returning an empty
`matched_fallback`; honest GAP only when no `material_root` exists. (2)
`plan_ranked_windows` filters unrenderable candidates (no source / zero-or-
negative length) **before** applying `limit`, so an illegal top-ranked scene no
longer starves a valid lower-ranked window (ranking order preserved; rank_scenes
scoring untouched). Reverse tests added: empty-assignments→live, empty-matched→
live, illegal-rank-1+valid-rank-2 picks #2. Focused: 20 tests OK; full
regression: **889 tests OK**.

### Deferred Until After BUILD Alignment

- ~~M6a lineage integration: `need_id` through shooting brief and revised
  contract references.~~ DONE (2026-06-14) — see "M6a Lineage Integration" above.
- M6b `material_delta` and delta-driven script revision.
- Dashboard/UI, Node 14, effects expansion, and front/back-end separation.
- New aesthetic hard gates or further 67th-specific tuning.

### 執行紀律(防彎路,給 Codex)

```text
1. 順序固定 M0→M1→M2→M3→M4。M0/M1 是執法與算術,刻意排在新機具前——
   本階段的躍遷來自「給既有訊號決策權」,不是更多剪輯能力。
2. 每項動手前先列「基底(不重做)」清單並 grep 驗證——最大風險是重工:
   重複統計(broll_audit)/切窗/評分/judge/caption 全部已存在,新碼只填
   「閘、供需帳、地圖、檢索、頓點」。
3. 每項完成 = 真素材跑通 + agent 感官複核 + 確定性測試(Sensory 紀律不變)。
   M0/M1/M2e 另加「案例回放」:2026-06-13 那支片必須被正確攔下。
4. 不再新增同權重規格(評估報告結論):新規則一律標 tier,tier1 必須有
   閘消費者,答不出「誰消費/誰驗證/違反時做什麼」的欄位不准進 SPEC。
5. OpenMontage 是 AGPL v3:只看概念與資料結構;不抄碼、不 import、不 vendoring。
6. 不碰:多軌換曲、CLIP 之外的新模型依賴、雲端 API 預設、UI;CLIP 本身 opt-in。
7. ffmpeg 音訊鏈改動先在 4.3.1 實測響度(volumedetect 分聲道)再 commit
   (amix normalize / 聲道塌陷教訓)。
```

---

## ✅ 2026-06-12(已完成): Sensory Phase(感官層攻堅,S1-S4)

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

S2c status (2026-06-12): COMPLETE. Non-final narrative segments now carry a
real 0.3-0.5s speech-tail silence, explicit `speech_end_sec` /
`tail_padding_sec` timing, unchanged phrase subtitles, and audio-probed duration
truth. City-lite narrative true render and three sentence-tail waveform/frame
checks are verified. See
`docs/decisions/2026-06-12-s2c-speech-tail-breathing.md`. Next: S3a.

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

S3a status (2026-06-12): COMPLETE. Narrative runs now emit sparse deterministic
`sfx_plan.json` cues, rotate a six-file local synthetic CC0 library, and mix
chapter whooshes / explicit title-card hits into final audio without lowering
the base track. City-lite SFX A/B, true final render, audio-level VERIFY, and
full regression are verified. See
`docs/decisions/2026-06-12-s3a-sfx-punctuation.md`. Next: S3b.

S3b status (2026-06-12): COMPLETE. Narrative single-track BGM now consumes
energy-scored `music_structure.sections`, snaps source playback to the nearest
structural offset, and aligns a declared climax with the highest-energy music
section. City-lite offset-0/aligned A/B, true render, sensory waveform review,
technical VERIFY, and full regression are verified. See
`docs/decisions/2026-06-12-s3b-music-structure-alignment.md`. Next: S4a.

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

S4a status (2026-06-12): COMPLETE. The existing E6 visual-review gate is now
explicit Node `10.5 Visual Judge` between Timeline and Editor Review, with
optional/warn/done lifecycle verification, request/verdict artifact links, and
dashboard routing. City-lite and gen-smoke real-run dashboard states, montage
sensory review, and full regression are verified. See
`docs/decisions/2026-06-12-s4a-visual-judge-node.md`. Next: S4b.

S4b status (2026-06-12): COMPLETE. Visual verdicts now support bounded
`needs_patch` actions for window, crop, and treatment corrections while
preserving legacy accept/reject verdicts. Patches flow into concrete slots,
crop patches reach the MV ffmpeg renderer, and patched choices are traced as
`agent_patch`. Gen-smoke real-candidate patch smoke and full regression are
verified. See `docs/decisions/2026-06-12-s4b-needs-patch-verdict.md`. Next: S4c.

S4c status (2026-06-12): COMPLETE. Segment-level `creative_exception` now has
a validated reviewable schema, survives canonical/runtime/assembly/timeline
artifacts, and downgrades only the matching rule in spec, pacing, visual-fatigue,
and presentation-feel review to warn-with-ack. Legacy hold reasons remain
accepted but are normalized into visible acknowledged warnings. City-lite
real-video baseline review and full regression are verified. See
`docs/decisions/2026-06-12-s4c-creative-exception.md`. Next: E7 or next roadmap
priority.

Sensory integrated acceptance status (2026-06-12): COMPLETE for the
MV/local-material/light-effects branch. The fresh bakery v5 run passed true
render, technical VERIFY 100, editor review, treatment audit, editorial QA 85,
light-effects 5/5, agent keyframe sensory review, and 663-test regression.
Integration fixes covered missing source audio, photo-stack pacing, safe
motion-peak snapping, hold-reason trace, and rendered-timeline beat grids. See
`docs/decisions/2026-06-12-sensory-integrated-bakery-acceptance.md`.

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

E7 status (2026-06-12): COMPLETE. `caption-meta --visual-review-dir` now writes
a timestamped material montage request and returns
`await_material_visual_review`; rerunning after an agent-authored verdict
applies complete captions with explicit lineage. Partial verdicts are rejected,
UTF-8 BOM verdicts are accepted, root-level ingest files are no longer skipped,
and an empty pending set completes without a false wait. Real city-lite long
material await/resume and montage sensory review are verified. See
`docs/decisions/2026-06-12-e7-material-montage-review.md`. Next: integrated
fresh-film sensory acceptance, then E8.
