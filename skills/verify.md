---
name: verify
description: Use when running or reviewing Hermes VERIFY and delivery gates: QA reports, visual/content audits, reviewer artifacts, final review smoke, fail-closed delivery evidence, stale artifact checks, or repair targets after BUILD.
---

# Verify Skill

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "verify",
  "stage_owner": "verify_delivery_gate",
  "triggers": [
    "需要驗證成品、review report、delivery gate、orphan process、或 fail-closed 行為",
    "BUILD 後或 no-render campaign 後需要 reviewer/verify evidence"
  ],
  "canonical_tools": [
    {
      "tool": "tools/no_skip_execution_trace.py",
      "when": "seal strict no-skip execution trace and validate the accountable receipt lineage before Stage 10",
      "inputs": [
        "committed execution companion",
        "accountability run folder"
      ],
      "outputs": [
        "pipeline_execution_trace.json",
        "no_skip_contract_decision.json",
        "strict_accountability_closure_audit.json"
      ],
      "stop_if": [
        "execution trace is missing, stale, self-authored, or has a broken receipt edge",
        "a parent receipt was substituted or hash-drifted"
      ],
      "capability_id": "cap.verify.no-skip-execution-trace.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": ["L5"],
      "maturity": "bounded",
      "certified_scope": "strict receipt lineage closure; no creative approval or delivery claim"
    },
    {
      "tool": "tools/stage5_final_review_smoke.py",
      "when": "驗證 final review / delivery gate 邊界，不重跑完整 render",
      "inputs": [
        "stage5 fixture or run folder"
      ],
      "outputs": [
        "stage5_final_review_smoke_report.json"
      ],
      "stop_if": [
        "delivery evidence missing or hard gate fails"
      ],
      "capability_id": "cap.verify.stage5-final-review-smoke.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/reviewer_flow_acceptance.py",
      "when": "驗證 reviewer flow 是否會 fail-closed 並回報正確 route",
      "inputs": [
        "review fixture or run folder"
      ],
      "outputs": [
        "reviewer_flow_acceptance_report.json"
      ],
      "stop_if": [
        "reviewer blocks or missing review artifact"
      ],
      "capability_id": "cap.verify.reviewer-flow-acceptance.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/write_delivery_gate_report.py",
      "when": "write delivery_gate.json from current run artifacts so verify_result.pass=true cannot be mistaken for delivery readiness",
      "inputs": [
        "run folder with verify/material/audio/subtitle/effect evidence"
      ],
      "outputs": [
        "delivery_gate.json"
      ],
      "stop_if": [
        "delivery gate blocks or required evidence is missing"
      ],
      "capability_id": "cap.verify.write-delivery-gate-report.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/final_product_verify.py",
      "when": "build complete-video eye/ear evidence for a final or draft candidate before delivery or Brownfield repair",
      "inputs": [
        "final.mp4 or draft candidate video"
      ],
      "outputs": [
        "final_product_verify_bundle.json",
        "keyframe_grid.jpg",
        "visual_audit.json",
        "final_audio.wav",
        "soundtrack_probe_report.json"
      ],
      "stop_if": [
        "video cannot be sampled",
        "audio cannot be extracted",
        "visual or audio evidence fails"
      ],
      "capability_id": "cap.verify.final-product-verify.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/timeline_review_packet.py",
      "when": "after a rough cut/rendered candidate exists, or when analyzing a finished reference film, build dense whole-timeline visual evidence and bind optional soundtrack/subtitle context for agent or human story review",
      "inputs": [
        "rendered rough cut, candidate, or reference film",
        "review_subject_type: current_candidate | reference_film",
        "optional decision context JSON with locked_truth and declared finishing_contract/audio_policy",
        "optional soundtrack_probe_report.json",
        "optional subtitles.srt",
        "text_authority whenever SRT is supplied: asr_draft | owner_approved | reference_transcript | ocr_inferred"
      ],
      "outputs": [
        "timeline_review_packet.json",
        "editorial_evidence_manifest.json",
        "reviewer_write_contract.json",
        "wall_index.json",
        "walls/wall_30s_*.jpg",
        "editorial_review.template.json",
        "timeline_crop_request.template.json"
      ],
      "stop_if": [
        "video duration cannot be probed",
        "review subject type is missing or invalid",
        "SRT is supplied without explicit text authority, or text authority is supplied without SRT",
        "uniform wall coverage or page count mismatches",
        "bound soundtrack artifact has the wrong contract",
        "bound soundtrack duration does not match the reviewed video",
        "the output root already contains prior timeline-review evidence"
      ],
      "capability_id": "cap.verify.uniform-timeline-review.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L5"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/orphan_audit.py",
      "when": "檢查是否有孤兒 render / ffmpeg / long-running process",
      "inputs": [
        "optional process filters"
      ],
      "outputs": [
        "orphan audit report"
      ],
      "stop_if": [
        "unsafe long-running process is found"
      ]
    },
    {
      "tool": "tools/test_tiers.py",
      "when": "列出或執行測試分層，用於 focused/full regression 決策",
      "inputs": [
        "test tier name"
      ],
      "outputs": [
        "test tier command/report"
      ],
      "stop_if": [
        "requested tier is unknown"
      ]
    },
    {
      "tool": "tools/agent_transcript_repair.py",
      "when": "Draft agent transcript repair suggestions from ASR/subtitle evidence",
      "inputs": [
        "subtitle draft",
        "ASR transcript"
      ],
      "outputs": [
        "agent transcript repair suggestions"
      ],
      "stop_if": [
        "source transcript evidence is missing"
      ]
    },
    {
      "tool": "tools/effect_director_review.py",
      "when": "Review effect output evidence before Verify accepts an effect claim",
      "inputs": [
        "effect artifacts",
        "frame evidence"
      ],
      "outputs": [
        "effect director review report"
      ],
      "stop_if": [
        "visual evidence is missing or blocking findings exist"
      ]
    },
    {
      "tool": "tools/independent_voiceover_asr_qa.py",
      "when": "Run independent ASR QA on generated voiceover output",
      "inputs": [
        "voiceover audio",
        "expected narration"
      ],
      "outputs": [
        "independent voiceover ASR QA report"
      ],
      "stop_if": [
        "ASR evidence is missing or mismatched"
      ]
    },
    {
      "tool": "tools/montage_design_review.py",
      "when": "Review montage structure and story hook/payoff evidence",
      "inputs": [
        "render candidate",
        "contact sheet or frame evidence"
      ],
      "outputs": [
        "montage design review report"
      ],
      "stop_if": [
        "plain-title opener, static shot, or missing payoff is found"
      ]
    },
    {
      "tool": "tools/rendered_product_qa.py",
      "when": "Run rendered product QA against frame/contact-sheet evidence",
      "inputs": [
        "rendered candidate",
        "review evidence"
      ],
      "outputs": [
        "rendered product QA report"
      ],
      "stop_if": [
        "frame or contact-sheet evidence is missing"
      ]
    },
    {
      "tool": "tools/source_speech_subtitle_qa.py",
      "when": "Check source-speech subtitle coverage and route gaps to human review",
      "inputs": [
        "source media",
        "subtitle file",
        "speech evidence"
      ],
      "outputs": [
        "source speech subtitle QA report"
      ],
      "stop_if": [
        "later speech coverage is missing without human review route"
      ]
    },
    {
      "tool": "tools/title_effect_lifecycle_qa.py",
      "when": "Check title/effect lifecycle timing, overlap, and persistence evidence",
      "inputs": [
        "render candidate",
        "effect timing metadata"
      ],
      "outputs": [
        "title effect lifecycle QA report"
      ],
      "stop_if": [
        "persistent cards, overlap, or missing timing evidence is found"
      ]
    },
    {
      "tool": "tools/voiceover_leadin_qa.py",
      "when": "Detect extra spoken lead-in tokens before expected narration",
      "inputs": [
        "voiceover audio",
        "expected narration"
      ],
      "outputs": [
        "voiceover lead-in QA report"
      ],
      "stop_if": [
        "unexpected lead-in speech is detected"
      ]
    },
    {
      "tool": "tools/voiceover_output_qa.py",
      "when": "Check generated voiceover output for style/control leakage and content evidence",
      "inputs": [
        "voiceover audio",
        "expected narration",
        "provider metadata"
      ],
      "outputs": [
        "voiceover output QA report"
      ],
      "stop_if": [
        "style leakage or missing content evidence is detected"
      ]
    },
    {
      "tool": "tools/voxcpm_leadin_diagnostic.py",
      "when": "Classify VoxCPM lead-in behavior and whether safe postprocess exists",
      "inputs": [
        "VoxCPM output audio",
        "expected narration"
      ],
      "outputs": [
        "VoxCPM lead-in diagnostic report"
      ],
      "stop_if": [
        "provider is blocked with no safe fix"
      ]
    },
    {
      "tool": "tools/write_human_transcript_review_decision.py",
      "when": "Write the human transcript review decision that closes ASR-derived subtitle repair",
      "inputs": [
        "reviewer decision",
        "repair suggestions"
      ],
      "outputs": [
        "human_transcript_review_decision.json"
      ],
      "stop_if": [
        "reviewer is non-human or decision is incomplete"
      ]
    },
    {
      "tool": "tools/write_story_human_review_decision.py",
      "when": "Write the human story review decision that closes story-human-review waiting states",
      "inputs": [
        "reviewer decision",
        "story review packet"
      ],
      "outputs": [
        "story_human_review_decision.json"
      ],
      "stop_if": [
        "reviewer is non-human or decision is incomplete"
      ]
    },
    {
      "tool": "tools/verify_beat_cut_alignment.py",
      "when": "Objectively verify intended cut boundaries against the declared beat grid; it does not judge montage taste",
      "inputs": [
        "timeline_build.json",
        "declared beat grid",
        "output window and fps"
      ],
      "outputs": [
        "beat_cut_alignment_report.json"
      ],
      "stop_if": [
        "an intended cut boundary exceeds one frame from a beat anchor",
        "alignment report is not pass"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not use local VLM for VERIFY unless explicitly opted into legacy experiment",
    "Do not call a video passed when delivery evidence is missing",
    "Do not confuse warning-only diagnostics with hard gate pass"
  ],
  "capability_namespace": "cap.verify.*",
  "capability_lookup_owner": "verify"
}
<!-- TOOL_CONTRACT_END -->

## Uniform Timeline Review（橫向 Reviewer 支線）

`tools/timeline_review_packet.py` 在 rough cut／rendered candidate 產生後，或要拆解
finished reference film 時，
以預設每 `0.5` 秒一格、每 `30` 秒一頁建立全片均勻時間牆。這是 S7/L5
的主要「故事導航」證據面，可被章節預覽、整片候選與 Brownfield 修訂共同
呼叫；它不擁有 Stage cursor、canonical render 或 delivery。

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" tools\timeline_review_packet.py `
  --video RUN_DIR\final.mp4 `
  --out-dir RUN_DIR\timeline_review `
  --review-subject-type current_candidate `
  --context RUN_DIR\decision_context.json `
  --soundtrack-probe RUN_DIR\soundtrack_probe_report.json `
  --srt RUN_DIR\subtitles.srt `
  --text-authority owner_approved `
  --json
```

Agent 必須查看 `wall_index.json` 列出的全部牆，再寫入由 template 衍生的
findings。牆負責全片故事結構、活動家族、非相鄰語意重複、字卡／字幕
生命週期與影音大方向；低信心位置進 `timeline_crop_request`，回原始影格、
連續片段、ASR 或專用 QA 確認。

`review_subject_type=current_candidate` 的輸出權限固定為
`candidate_findings_only`；`reference_film` 固定為
`reference_observations_only`，不得把參考片觀察升成本片 FAIL 或 canonical
mutation。LLM finding 可分成
`objective / structural_candidate / taste`，但本支線不得把語意觀察轉成
technical PASS、creative approval 或 delivery claim。沒有綁定 soundtrack
probe 或 SRT 時，也不得宣稱音樂／字幕方向正確。

綁定 SRT 時必填 `text_authority`，避免把 `asr_draft`、`owner_approved`、
`reference_transcript` 或 `ocr_inferred` 混成同一種文字真相。Reviewer 看到
的特效只能寫成 `effect_observations[]`；Owner／Integrator 另行裁決並建立
effect contract 後，才准形成 Effect Factory request 或 handoff。

## V Pipeline Editorial Reviewer entry

For the unified editorial surface, read `skills/editorial-reviewer.md`. It is
one `editorial_reviewer` identity using existing reviewer roles as rubric
lenses; it does not dispatch one agent per lens. The reviewer consumes the
persisted timeline packet and its `editorial_evidence_manifest.json` before
requesting new evidence, and emits `editorial_review` findings/proposals only.

The reviewer may record strengths, evidence gaps, or no material findings. It
must bind material findings to subject hash, evidence-item hash, capability,
and bounded time window. It may recommend one existing route/capability and at
most one fallback, but never executes repair, mutates canonical state, grants
creative approval, or claims delivery. `human_creative_approval=false` and
`final_delivery_claimed=false` are mandatory.
`full_context` reviews read bound locks before proposing fixes; `cold_start`
reviews observe from the audience perspective first and classify against locks
last. Wall inspection runs in one fresh/disposable reviewer context; the parent
only validates and routes the immutable finding artifact.


## Current visual-judgment policy

VERIFY technical checks remain deterministic and local where possible, but
visual/content judgment is **agent/cloud review by default**. Do not start
Ollama/qwen for VERIFY unless the run explicitly opted into a legacy local-VLM
experiment. When visual judgment is needed, produce or consume the canonical
review artifacts (`visual_review_request.json`, `visual_review_verdict.json`,
or `material_visual_review_*`) and let the route pause at the corresponding
`await_*visual_review` action.

## Soundtrack Probe Gate

VERIFY does not create music understanding artifacts. `soundtrack-arranger`
owns `tools/soundtrack_probe.py` and writes `soundtrack_probe_report.json`.
VERIFY only consumes that report through `tools/write_delivery_gate_report.py`.

If `delivery_requirements.json` sets `requires_soundtrack_probe=true`, delivery
must fail closed when `soundtrack_probe_report.json` is missing, `pass` is not
true, or `features`, `sections`, `editing_fit`, or `section_fit` are empty.
This keeps music analysis as a Soundtrack Arranger responsibility while still
making final delivery accountable.

## Final Product Minimum Visual Evidence

`final-product-verify` is the complete-video evidence bundle for drafts and
final candidates. For static, interview, lecture, podcast, or low-motion
sources, do not accept a verify bundle that only sampled one or two frames when
a higher sample count was requested. Sparse scene detection is not proof that
the video has no visual issues.

When scene-change sampling returns too few points, `keyframe-grid` should use
its sparse scene fallback and add evenly spaced samples until the requested
minimum visual evidence is present. Treat this as evidence coverage only: a
larger keyframe grid proves the reviewer had enough frames to inspect, not that
the semantic edit is automatically correct.
> ## Continuous Verify / QA Contract(Node 12 — 不只終點,是貫穿控制閘)
> **VERIFY 是貫穿全流程的控制閘,尤其在「昂貴 render 之前」**,不只最後一站。
> `verify_result`:`status ∈ pass / warn / fail / blocked` + `findings`[層級/節點/原因/建議路由] + `next_route`。
> **兩層檢查(對齊兩層模型):** 機械檢查先跑(便宜、deterministic:規格/時長/字幕/音量/EDL trace/
> 必放有無/fallback 是否被靜默替換)→ **小模型 VLM(qwen3-vl 等,參數化後端非硬寫)只在
> 視覺/語意/主觀檢查 deterministic 解不了時觸發** → human 只在需判斷/identity-proof 核可/主觀驗收時 targeted。
> **AI editor(Node 11)≠ verify**:editor 提修法/編輯路由;**verify 給正式 pass/warn/fail/block 閘**。
> 鐵則:blocker 不可進 ready/approved/render;fallback 被靜默替換 → fail;timeline item 無 trace → fail。

VERIFY 是 pipeline 的終點品管站。
**核心原則**：腳本是 ground truth，VERIFY 對照腳本檢查所有產出是否一致。
不通過時不只說「失敗」，要明確指出**哪個 Skill 要修**（fix_target）。

---

## 工具位置

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

```bash
python3 video_tools.py verify \
  --script script.json \
  --timing tts_timing.json \
  --edit-log rough_cut_edit_log.json \
  --srt subtitles.srt \
  --video final.mp4 \
  [--threshold 80] [--out qa_report.json]
```

---

## 對應命令
* `[[cmd_verify]]` - 對成片做 5 維度評分，並輸出加權總分與 fix_target 路由指示。
* `[[cmd_validate]]` - 在影片生成前，對劇本 (script.json) 進行模糊消除與格式健全檢查。

---

## 5 個評分維度

| 維度 | 權重 | 來源 | 通過條件 |
|------|------|------|---------|
| script_coverage | 25% | script.json + edit_log | 每個 script segment 都有對應影片 |
| duration_fit | 25% | tts_timing + edit_log | 每段影片 vs TTS 差 < 300ms |
| subtitle_accuracy | 20% | script.json + srt | 字元重疊率 ≥ 90% |
| audio_levels | 15% | ffmpeg volumedetect | mean -25~-12dB, max ≤ -6dB |
| technical_quality | 15% | ffprobe | 1920x1080 @ 30fps + 有 audio/video stream |

### 加權公式
```
total_score = sum(dimension_score × weight)
pass = total_score >= threshold (預設 80)
```

### 第 6 維：content_alignment（VLM 內容對題，由 content_qa.py 注入）

技術 5 維只驗「格式對不對」，不驗「畫面對不對題」。`content_qa.py` 用 VLM（qwen3-vl:4b）
逐段對成片縮圖打分，注入 qa_report 成為 content_alignment 維度（預設權重 0.30，其餘 5 維等比縮放）。

**關鍵原則：驗證一律用中文，且比對 `visual_desc`（畫面描述），不是 keyword、不是旁白。**
- 4b 對「英文 prompt 模板裡塞中文 keyword」判斷很差（會把對的圖判成 no）；用**中文問句**才準。
- 比對標的用 `visual_desc`（純畫面事實），不要用 `text` 旁白（文學語氣，太苛/太模糊）。
- 問法是「這張圖適不適合當這段畫面描述的配圖？是/否/部分」，對映 primary/related → 分數。

**D1 嚴格逐段 gate**：任一段 content score < 60 即整體 fail（不靠平均稀釋），觸發該段 repick；
fix_target = `curator`（小編重挑素材）。

---

## fix_target 路由

每個維度若不及格（< 80），會標記要修哪個 Skill：

| 維度失敗 | fix_target | 該 Skill 要做什麼 |
|---------|-----------|------------------|
| script_coverage | editor | 剪輯師缺段，補 assemble 漏掉的 segment |
| duration_fit | editor | 剪輯師時長對不上，重新剪該段 |
| subtitle_accuracy | subtitle | 字幕師檔案有問題，重 srt |
| audio_levels | audio | 音控師音量爆/過小，重 mix-audio |
| technical_quality | editor | 解析度或 stream 缺，重 assemble + merge-final |

上層 orchestrator 讀 `qa_report.json.issues[].fix_target` 即可決定要重跑哪個 Skill。

---

## qa_report.json 範例

```json
{
  "video": "/workspace/final.mp4",
  "timestamp": "2026-05-24T23:03:20",
  "score": 98.5,
  "pass": true,
  "threshold": 80,
  "dimensions": {
    "script_coverage":   { "score": 100, "weight": 0.25, "note": "all segments present", "fix_target": null },
    "duration_fit":      { "score": 100, "weight": 0.25, "note": "4/4 segments within 300ms", "fix_target": null, "issues": [] },
    "subtitle_accuracy": { "score": 100, "weight": 0.20, "note": "overlap 320/320 chars (100.0%)", "fix_target": null },
    "audio_levels":      { "score":  90, "weight": 0.15, "note": "max -5.8dB 接近爆音", "fix_target": null, "mean_db": -22.3, "max_db": -5.8 },
    "technical_quality": { "score": 100, "weight": 0.15, "note": "streams OK, 1920x1080 30fps", "fix_target": null }
  },
  "issues": []
}
```

不通過時：
```json
{
  "score": 64,
  "pass": false,
  "issues": [
    { "dimension": "duration_fit", "segment": 2, "score": 50, "fix_target": "editor",
      "detail": "seg2 actual 23.8s vs tts 22.0s (1800ms diff)" }
  ]
}
```

---

## 各維度設計細節

### 1. script_coverage
- 比對 `script.json` 的 segment 數 vs `edit_log.json` 的 segment 數
- 缺一段就扣 100/N 分
- **fix_target = editor**（因為剪輯師沒輸出該段）

### 2. duration_fit
- 對每個 segment 算 `|edit_log.actual_sec - tts_timing.duration_sec|`
- 預設閾值 300ms（路線 A 對影片配旁白要求嚴）
- 超過閾值的段落會被列入 `issues`
- **fix_target = editor**（剪輯師沒剪準）

### 3. subtitle_accuracy
- 把 SRT 所有字幕文字串起來
- 跟 `script.json` 所有 text 串起來比對
- 用 Counter 算字元層級的多重集合交集（去標點/空白）
- 比率 = `overlap / len(script_clean)`
- < 90% → fix_target = subtitle

### 4. audio_levels
- 跑 `ffmpeg -af volumedetect` 取 mean/max dB
- 規則（依坑 #21 + 一般 broadcast 標準）：
  - max > -3 → 扣 30（爆音風險）
  - max > -6 → 扣 10（接近爆音）
  - mean < -30 → 扣 30（太小聲）
  - mean > -12 → 扣 20（偏大聲）
- < 80 → fix_target = audio

### 5. technical_quality
- 解析度必須 1920x1080
- 必須有 video + audio stream
- framerate 30fps ±1
- < 80 → fix_target = editor

---

## 已知限制與未實作

### 未實作（v1 不做）
- **黑幀偵測**：純黑畫面超過某秒數應該扣分，但本實作沒做
- **音訊斷點偵測**：concat 接縫的爆音（坑 #29），未實作自動偵測
- **多段 BGM 音量分段檢查**：依坑 #21，語音段 vs 純畫面段該不同 BGM 音量，本實作只看整體
- **字幕時長合理性**：太短（< 0.5s）或太長（> 6s）該扣，未實作

這些等到實際出問題再補。

### threshold 預設 80 的根據
- 5 個維度，4 個拿 100、1 個拿 80 → 加權 96
- 5 個維度，3 個拿 100、2 個拿 80 → 加權 92
- 5 個維度，2 個拿 100、3 個拿 80 → 加權 88
- 拿 80 = pipeline 出了實質問題但勉強能看，threshold 設這個強迫修

---

## 與其他 Skill 的銜接

### 上游（VERIFY 讀什麼）
- `編劇 Skill` → `script.json`
- `音控師 Skill` → `tts_timing.json`
- `字幕師 Skill` → `subtitles.srt`
- `剪輯師 Skill` → `rough_cut_edit_log.json` + `final.mp4`

### 下游（誰用 VERIFY 結果）
- **手動模式**：直接看 qa_report，自己決定要不要重跑
- **orchestrator 模式**：讀 `issues[].fix_target` 自動觸發重跑

---

## 實測結果（2026-05-24）

對 `v3_skill_final.mp4` 跑 verify：

| 維度 | 分數 | 備註 |
|------|------|------|
| script_coverage | 100 | 4/4 segments |
| duration_fit | 100 | 全部 < 300ms |
| subtitle_accuracy | 100 | 320/320 字元 |
| audio_levels | 90 | max -5.8dB（剛好踩到接近爆音閾值）|
| technical_quality | 100 | 1920x1080 30fps |
| **加權總分** | **98.5** | ✅ pass |

audio_levels 沒拿滿分提醒了實際的細節：第一支 SKILL 全自動成片就在 -5.8dB 邊緣，未來 BGM 音量再上調容易爆。這正是 VERIFY 該做的事——**沒事先警告，有事直接點名**。

---

## 對應的 vault 文件
- `projects/video-agent-pipeline/roadmap.md` Phase 4
- `projects/video-agent-pipeline/skill-interface-contracts.md` — qa_report.json 格式
- `projects/video-agent-pipeline/ffmpeg-pitfalls-reference.md` — #21（音量）/ #29（音訊斷點）
