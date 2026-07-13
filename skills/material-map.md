---
name: material-map
description: 素材地圖生命週期 Skill。把討論/現有素材/補拍需求收斂成 material_needs → 盤點 → delta → 人工決策 → revised contract → BUILD handoff。M6d orchestration 層,只定義方法與決策責任;確定性的 validate/join/gate/revision 一律交給 Python 工具。
---

# Material Map Lifecycle Skill

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "material-map",
  "stage_owner": "stage2_material_map",
  "triggers": [
    "使用者已有素材、素材不足、需要素材地圖、素材牆、粗剪供給判斷",
    "material-first route 需要證明素材與劇本需求是否對得上"
  ],
  "canonical_tools": [
    {
      "tool": "tools/material_quick_inventory.py",
      "when": "run Stage 0 material_scan_decision quick inventory over all materials or a user-specified folder/file scope before deep Material Map review",
      "inputs": [
        "source folder",
        "video_intent.json or standalone material_scan_decision"
      ],
      "outputs": [
        "material_inventory_summary.json"
      ],
      "stop_if": [
        "source folder is missing",
        "summary has zero usable files and user did not intend an empty scan"
      ],
      "capability_id": "cap.material-map.material-quick-inventory.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/material_understanding_matrix.py",
      "when": "multi-material runs need frame/audio/path evidence before a reviewer writes material_wall_review_verdict.json; run after quick inventory or materials_db ingest and before rough cut/BUILD",
      "inputs": [
        "materials_db.json",
        "optional bounded max-assets/frame-budget"
      ],
      "outputs": [
        "material_understanding_matrix.json",
        "material_understanding_contact_sheet.jpg",
        "material_understanding_frames/*"
      ],
      "stop_if": [
        "materials_db.json is missing",
        "matrix has zero assets",
        "agent treats role_hints as accepted material truth instead of review hints"
      ],
      "capability_id": "cap.material-map.material-understanding-matrix.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/material_wall_verdict_draft.py",
      "when": "a material_understanding_matrix exists and the agent needs a conservative first draft of material_wall_review_verdict.json before human/agent review",
      "inputs": [
        "material_understanding_matrix.json",
        "required visual roles such as opening/training/closing"
      ],
      "outputs": [
        "material_wall_review_verdict.draft.json with one primary keep per required role and alternates separated"
      ],
      "stop_if": [
        "matrix is missing",
        "required roles have no primary candidate",
        "draft is treated as final material truth without review"
      ],
      "capability_id": "cap.material-map.material-wall-verdict-draft.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/material_first_happy_path.py",
      "when": "operator needs the full no-render material-first happy path before attempting 60-90s or 5min editing",
      "inputs": [
        "source folder",
        "max-assets",
        "frame-budget",
        "required visual roles"
      ],
      "outputs": [
        "materials_db.source_candidates.json",
        "material_understanding_matrix.json",
        "material_wall_review_verdict.draft.json",
        "preview_rough_cut_plan.json",
        "material_first_boundary_acceptance_report.json",
        "rough_cut_plan.json"
      ],
      "stop_if": [
        "ok=false",
        "failed_stage is not null",
        "final.mp4 exists",
        "operator treats the 12s smoke rough cut as the finished highlight"
      ],
      "capability_id": "cap.material-map.material-first-happy-path.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/material_first_preview_plan.py",
      "when": "matrix plus wall verdict draft are ready and the operator needs a 60-90 second reviewable rough cut proposal before render",
      "inputs": [
        "material_understanding_matrix.json",
        "material_wall_review_verdict.draft.json",
        "target/min/max duration"
      ],
      "outputs": [
        "preview_rough_cut_plan.json"
      ],
      "stop_if": [
        "preview plan is treated as canonical timeline",
        "preview has gaps",
        "preview is rendered before review"
      ],
      "capability_id": "cap.material-map.material-first-preview-plan.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/rough_cut_storyboard_preview.py",
      "when": "preview_rough_cut_plan.json needs a fast reviewable video but source clips are too large to decode for motion preview",
      "inputs": [
        "material_understanding_matrix.json with durable keyframe paths",
        "preview_rough_cut_plan.json"
      ],
      "outputs": [
        "rough_cut_storyboard_preview_report.json",
        "storyboard preview mp4"
      ],
      "stop_if": [
        "matrix keyframes are missing",
        "storyboard preview is treated as final render",
        "motion quality is being judged from still frames"
      ],
      "capability_id": "cap.material-map.rough-cut-storyboard-preview.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/material_first_boundary_acceptance.py",
      "when": "驗證 material-first 邊界，不跑 contract-run、不 render",
      "inputs": [
        "source folder",
        "video_intent.json or brief assumptions",
        "optional material_wall_review_verdict.json"
      ],
      "outputs": [
        "material_first_boundary_acceptance_report.json"
      ],
      "stop_if": [
        "ok=false",
        "failed_stage is not null",
        "await_map_review without reviewed edges"
      ],
      "capability_id": "cap.material-map.material-first-boundary-acceptance.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/material_first_stage2_3_smoke.py",
      "when": "小步驗證素材地圖與 review apply 邊界",
      "inputs": [
        "stage2/stage3 fixture or run folder"
      ],
      "outputs": [
        "stage2_3 smoke report"
      ],
      "stop_if": [
        "lifecycle does not reach expected review/build-ready state"
      ],
      "capability_id": "cap.material-map.material-first-stage2-3-smoke.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/material_rough_cut.py",
      "when": "根據素材地圖、review verdict、usable ranges 產生可審查粗剪計畫",
      "inputs": [
        "materials_db.json",
        "material map/review artifacts",
        "segment needs"
      ],
      "outputs": [
        "rough_cut_plan.json"
      ],
      "stop_if": [
        "reject/duplicate material is still selected",
        "usable ranges are ignored"
      ],
      "capability_id": "cap.material-map.material-rough-cut.v1",
      "execution_class": "hybrid",
      "capability_role": "operation",
      "loops": [
        "L1"
      ],
      "maturity": "bounded",
      "certified_scope": "Canon 67 39s Material Map diversity forward plan"
    },
    {
      "tool": "tools/source_highlight_plan.py",
      "when": "single long source video needs a 60-90s highlight and the request is about practical/training/event highlights rather than a full multi-asset material map",
      "inputs": [
        "one source video",
        "optional soundtrack_probe_report.json",
        "brief intent such as internship highlights, ending, or music refill"
      ],
      "outputs": [
        "source_timeline_map.json",
        "highlight_selection_plan.json",
        "rough_cut_plan.json"
      ],
      "stop_if": [
        "source video duration cannot be probed",
        "rough_cut_plan has no clips",
        "content-critical selection has no human/VLM review evidence"
      ],
      "capability_id": "cap.material-map.source-highlight-plan.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/source_section_map.py",
      "when": "one long source video needs structural understanding before highlight selection; use this first to split the source into big visual/audio sections",
      "inputs": [
        "one source video",
        "optional source_soundtrack_probe_report.json"
      ],
      "outputs": [
        "source_section_map.json"
      ],
      "stop_if": [
        "source video duration cannot be probed",
        "section map has no sections",
        "section boundaries are treated as semantic labels without review"
      ],
      "capability_id": "cap.material-map.source-section-map.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/source_motion_profile.py",
      "when": "one long source video needs edit-point or transition evidence; use after source_section_map for scoped high-motion or quiet-boundary scans",
      "inputs": [
        "one source video",
        "optional source_soundtrack_probe_report.json",
        "optional start/end scope"
      ],
      "outputs": [
        "source_motion_profile.json",
        "source_motion_points.jpg",
        "motion_frames/*.jpg"
      ],
      "stop_if": [
        "source video duration cannot be probed",
        "ranked edit points are used as semantic truth without matrix/review evidence"
      ],
      "capability_id": "cap.material-map.source-motion-profile.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/source_dialogue_script.py",
      "when": "one long source video is dialogue/podcast/interview-driven; import correct subtitles or ASR and expand rough picks to complete sentence-safe clips before cutting",
      "inputs": [
        "yt-dlp json3 subtitle or reviewed ASR transcript",
        "optional rough dialogue windows",
        "soft target duration"
      ],
      "outputs": [
        "source_transcript.json",
        "dialogue_edit_script.json",
        "dialogue_highlight_windows.json"
      ],
      "stop_if": [
        "transcript source is missing or low-confidence",
        "selected clips cut half sentences",
        "exact target duration is forced over speech flow"
      ],
      "capability_id": "cap.material-map.source-dialogue-script.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/source_material_matrix.py",
      "when": "one long source video must be understood before highlight selection; build window-level visual keyframes plus audio evidence before deciding clips",
      "inputs": [
        "one source video",
        "optional source_material_matrix_review.json",
        "optional precomputed source_soundtrack_probe_report.json with ASR"
      ],
      "outputs": [
        "source_material_matrix.json",
        "source_material_matrix_contact_sheet.jpg",
        "source_audio.wav",
        "source_soundtrack_probe_report.json",
        "source_matrix_frames/*.jpg"
      ],
      "stop_if": [
        "source video/audio cannot be probed",
        "content-critical windows remain unreviewed",
        "requested ending/practice/music decisions are not backed by matrix evidence"
      ],
      "capability_id": "cap.material-map.source-material-matrix.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/safe_highlight_cut.py",
      "when": "material-first or Workbench highlight cut has accepted time windows and needs a stable playable MP4; use for yt-dlp, VP9/Opus, non-keyframe, or stutter-prone sources",
      "inputs": [
        "rough_cut_plan.json for single-source highlights, or source video plus windows JSON from Workbench selection",
        "output mp4 path",
        "highlight_cut_report.json path"
      ],
      "outputs": [
        "stable H.264/AAC highlight mp4",
        "highlight_cut_report.json"
      ],
      "stop_if": [
        "windows are empty or invalid",
        "rough_cut_plan has multiple source videos",
        "ffmpeg re-encode fails",
        "output probe is missing H.264 video",
        "audio source exists but output AAC audio is missing"
      ],
      "capability_id": "cap.material-map.safe-highlight-cut.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/rough_cut_plan_execute.py",
      "when": "an accepted material rough_cut_plan.json needs a bounded review video candidate before canonical BUILD/render",
      "inputs": [
        "rough_cut_plan.json",
        "approved source clips",
        "optional approved audio"
      ],
      "outputs": [
        "review video candidate",
        "rough_cut_preview_report.json"
      ],
      "stop_if": [
        "rough_cut_plan is unreviewed",
        "selected source clips are missing",
        "rough_cut_preview_report.json ok=false",
        "operator treats the preview as final.mp4"
      ],
      "capability_id": "cap.material-map.rough-cut-plan-execute.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/package_verified_preview.py",
      "when": "a single-source highlight or dialogue preview has passed final-product-verify and delivery gate but must remain a reviewable candidate before final promotion",
      "inputs": [
        "delivery_gate.json pass=true",
        "final_product_verify_bundle.json pass=true",
        "highlight_cut_report.json with playable output"
      ],
      "outputs": [
        "verified_preview_package.json",
        "delivery_candidate.mp4"
      ],
      "stop_if": [
        "delivery gate failed",
        "final-product-verify failed",
        "candidate video is missing",
        "operator expects this to create final.mp4"
      ],
      "capability_id": "cap.material-map.package-verified-preview.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/verified_preview_review_decision.py",
      "when": "operator has reviewed delivery_candidate.mp4 and needs to record accept/promote, Workbench revision, motion-preview rebuild, or rejection without mutating video artifacts",
      "inputs": [
        "verified_preview_package.json",
        "delivery_candidate.mp4",
        "explicit operator decision"
      ],
      "outputs": [
        "verified_preview_review_decision.json",
        "workbench_revision_request.json when decision=revise_workbench"
      ],
      "stop_if": [
        "verified_preview_package.json is missing",
        "decision is not explicit",
        "operator expects this tool to create final.mp4"
      ],
      "capability_id": "cap.material-map.verified-preview-review-decision.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/promote_verified_preview.py",
      "when": "operator explicitly accepts delivery_candidate.mp4 and wants to promote it to canonical final.mp4",
      "inputs": [
        "verified_preview_package.json",
        "delivery_candidate.mp4",
        "operator/reviewer identity"
      ],
      "outputs": [
        "final.mp4",
        "final_promotion_report.json",
        "delivery_requirements.json if missing",
        "audio_mix_report.json if missing"
      ],
      "stop_if": [
        "package is not ready_for_operator_delivery_review",
        "final.mp4 already exists and overwrite is not explicit",
        "operator has not reviewed the candidate"
      ],
      "capability_id": "cap.material-map.promote-verified-preview.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L1"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/material_first_landing_case.py",
      "when": "產生或驗證 material-first landing case fixture",
      "inputs": [
        "source folder or fixture"
      ],
      "outputs": [
        "landing case report"
      ],
      "stop_if": [
        "case cannot produce material-first artifacts"
      ]
    },
    {
      "tool": "tools/material_gap_brief.py",
      "when": "把 material_delta 缺口轉成補拍、生成、縮剪或 waiver 討論用 brief",
      "inputs": [
        "material_delta.json"
      ],
      "outputs": [
        "material_gap_brief.json or md"
      ],
      "stop_if": [
        "gap evidence is missing or ambiguous"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not treat filenames as verified visual truth",
    "Do not mark material needs covered without review evidence",
    "Do not jump from inventory directly to final render"
  ],
  "capability_namespace": "cap.material-map.*",
  "capability_lookup_owner": "material-map"
}
<!-- TOOL_CONTRACT_END -->

Shared hard boundary: read `skills/pipeline-boundary.md`. Stage 0 entry lock
must be resolved before Material Map is treated as a BUILD handoff. Do not
direct-cut from a fuzzy request; Material Map owns material truth/coverage, not
whole-video intent guessing.

把「需求(劇本要什麼)」與「實際素材(手上有什麼)」對齊,並決定下一步:
盤點、補拍、縮短、改寫、刪段、等待,或交付 BUILD。

**核心心法**:這不是兩條互斥流程。`existing-material-first`、`story-first`
(`script-first`)、`partial/hybrid` 只是不同入口;**目前 stage 由現存 artifact 決定**,不由你宣稱。
素材量決定劇本——缺素材就誠實輸出 delta / 補拍需求 / revision route,
**絕不默默用不符合 need 的素材**,也不為了宣稱成功而硬 BUILD。

## Quick Inventory From Stage 0

When `video_intent.json.material_scan_decision.needed=true`, run quick
inventory before deep Material Map review:

```powershell
python tools\material_quick_inventory.py `
  --source-dir PATH\to\materials `
  --video-intent RUN_DIR\video_intent.json `
  --out RUN_DIR\material_inventory_summary.json `
  --json
```

This is a cheap observation step, not visual truth. It reads filesystem
metadata, extensions, folder grouping, rough duplicate signals, and candidate
video/audio presence. Use it to ask better questions and decide whether the
next Material Map pass should scan all materials or only a reviewed subset. Do
not mark needs covered from this summary alone.

## Material Understanding Matrix

For multi-material runs, quick inventory is not enough and filenames are not
truth. Before writing `material_wall_review_verdict.json`, build a review aid:

```powershell
python tools\material_understanding_matrix.py `
  --materials-db RUN_DIR\materials_db.json `
  --out-dir RUN_DIR\material_understanding `
  --max-assets 24 `
  --frame-budget 3 `
  --json
```

This writes:

- `material_understanding_matrix.json`
- `material_understanding_contact_sheet.jpg`
- `material_understanding_frames/*`

Use it to inspect frames, rough role hints, audio unknowns, duplicate/final
export risks, and decide keep/maybe/reject/duplicate. Do not treat
`role_hints` as `material_needs` coverage. BUILD still requires Material Wall /
Material Map review and accepted scene-to-need evidence.

When a bounded run needs a first pass, draft the wall verdict from the matrix
and then review it before applying:

```powershell
python tools\material_wall_verdict_draft.py `
  --matrix RUN_DIR\material_understanding\material_understanding_matrix.json `
  --out RUN_DIR\material_wall_review_verdict.draft.json `
  --roles opening,training,closing `
  --json
```

The draft intentionally selects one `keep` primary per required role and moves
other plausible footage into `alternate_candidates`. This prevents backup
footage from silently entering BUILD as a formal `maybe`. If the selected
primary is visually weaker than an alternate, edit the verdict; do not loosen
the gate by promoting every plausible asset.

Primary ranking is intentionally shallow and explainable. It uses role hints,
risk flags, and small role preference dictionaries. For example, `training`
prefers practical operation / hands-on footage over meeting or briefing
footage when both match the same role. This is only an initial reviewer aid; if
the contact sheet shows a better take, update the draft verdict explicitly.

## Material-First Happy Path Wrapper

Before asking the pipeline to cut a 60-90 second preview or a 5 minute film,
run the no-render happy path once:

```powershell
python tools\material_first_happy_path.py `
  --out RUN_DIR `
  --source-dir MATERIAL_SOURCE_DIR `
  --video-intent RUN_DIR\video_intent.json `
  --max-assets 12 `
  --frame-budget 3 `
  --json
```

This wraps source scanning, material understanding matrix, wall verdict draft,
60-90 second `preview_rough_cut_plan.json`, and material-first boundary
acceptance. It intentionally stops at reviewable artifacts. The canonical
`rough_cut_plan.json` is still a short smoke handoff; use
`preview_rough_cut_plan.json` for human/Workbench review before render.
The preview planner should prefer unique accepted assets and extend their
bounded clip duration before repeating the same asset. Repetition is reserved
for cases where unique reviewed material cannot reach the minimum preview
length.
When Stage 0 contracts already exist, pass `--video-intent` so soundtrack,
effect, and subtitle/voiceover handoffs remain visible after material-first
acceptance.

If source clips are large or slow to decode, create a fast storyboard preview
from matrix keyframes instead of forcing a motion concat:

```powershell
python tools\rough_cut_storyboard_preview.py `
  --matrix RUN_DIR\material_understanding\material_understanding_matrix.json `
  --rough-cut-plan RUN_DIR\preview_rough_cut_plan.json `
  --out RUN_DIR\multi_material_storyboard_preview.mp4 `
  --report RUN_DIR\rough_cut_storyboard_preview_report.json `
  --json
```

This proves material choice and order for review. It does not prove motion
timing or final render quality.

Only after the storyboard/material order is accepted, create a bounded motion
preview. The motion preview must write `rough_cut_preview_report.json`; if
ffmpeg times out or fails, stop and follow the report's `next_action` instead
of keeping a partial mp4:

```powershell
python tools\rough_cut_plan_execute.py `
  --rough-cut-plan RUN_DIR\preview_rough_cut_plan.json `
  --out RUN_DIR\material_first_review_candidate.mp4 `
  --report RUN_DIR\rough_cut_preview_report.json `
  --timeout-sec 300
```

## Material Availability Route Boundary

- **existing-material-first**: material-map is the story source and constraint.
  Scan/curate actual footage first, then help the writer/director assemble a
  teaching, personal video, event recap, or brand story from what exists.
  Generation is fallback only for non-proof support such as diagrams, chapter
  cards, symbolic inserts, or missing bridge visuals.
- **story-first**: story/design intent leads first because no material exists
  or the route is explicitly generated/storybook. Material-map becomes the
  validation and handoff layer: it receives `material_needs.json`, generated or
  captured candidates, then proves coverage through delta before BUILD.
- **hybrid**: material-map runs early and again after generation/reshoot. It
  decides which needs are covered, thin, missing, accepted, rejected, waived, or
  revised.

## Cut Strategy Presets

Material Map can expose multiple cutting strategies over time, but each
strategy must be backed by a Python tool in this skill contract.

- `tools/material_rough_cut.py`: creates `rough_cut_plan.json` from material-map
  truth, review verdicts, and usable ranges. It decides source windows and
  segment alignment.
- `tools/safe_highlight_cut.py`: renders accepted windows into a stable
  H.264/AAC MP4 and writes `highlight_cut_report.json`. Use it for yt-dlp,
  VP9/Opus, non-keyframe, or stutter-prone sources. Prefer
  `--rough-cut-plan RUN_DIR/rough_cut_plan.json` for material-first
  single-source highlight runs; use `--source + --windows` only for explicit
  human/Workbench window selections.

Future presets may add faster draft copy modes, but they must declare their
limits and report artifacts before agents use them.

Single-source highlight is not source diversity. It remains one source with
multiple accepted time windows. In that mode, judge temporal diversity and
explicit anchor coverage instead of repeated source count. If an edit repeats
the same moment for emphasis, the rough cut must carry an intentional repeat
policy with a reason such as `emphasis`, `rhythm_hit`, or `dramatic_replay`.
Unmarked repetition remains a fatigue/material-shortage signal.

## One Long Source / Dialogue Highlight

Use this path when a user gives one long video and asks for a shorter highlight,
especially interviews, podcasts, lectures, conversations, or speech-first
recaps. Do not use `source-highlight-plan` alone for dialogue content. That tool
can propose windows, but it cannot replace transcript-level meaning review.

The required reasoning layers are eye / ear / head:

- eye: `source-section-map`, `source-motion-profile`, and
  `source-material-matrix` expose visual sections, motion points, keyframes,
  and source-level evidence.
- ear: a correct subtitle or manual caption is preferred. Reviewed ASR is the
  fallback. A low-confidence transcript is a stop gate.
- head: `source-dialogue-script` turns rough picks into
  `dialogue_edit_script.json` and complete sentence-safe
  `dialogue_highlight_windows.json`.

For speech-first highlight edits, review `dialogue_edit_script.json` before
cutting. Keep the original speech audio by default. Add music only when the
user asks for overlay/replacement/ducking and the audio branch can verify the
mix.

## 唯一入口:lifecycle runner(不要手動拼工具)

```
python video_tools.py material-map-lifecycle --out-dir DIR \
  [--needs material_needs.json] \
  [--maps-dir DIR | --project-map project_material_map.json | --material-db materials_db.json] \
  [--contract segment_contract.json] \
  [--decisions revision_decisions.json] \
  [--categories material_categories.json]
```

它**只**做:嚴格解析當前 artifact → 呼叫 canonical 工具 → 判定 stage → 輸出
`material_map_lifecycle.json`(refs + 摘要的 projection,**不是第二套真相**)→
`build_ready` 時才產 BUILD handoff。它**從不** render、**從不**自己實作第二套
delta/gate/revision 規則、**從不**繞過 `run_contract` 的 M6b/M6c gate。

底層 canonical 真相來源(不可繞過、不可複製):
- required → `material_needs.json`(`validate-needs`)
- actual → per-asset `*.map.json` / `project_material_map.json`(`project-material-map`)
- diff → `material_delta.json`(`material-delta`)
- revision → `material_revision.json` + `revised_segment_contract.json`(`material-revision`)

## Stage 是怎麼判定的(每次 fresh 計算,不信任舊報告)

| stage | 意義 | 你該做什麼 |
|---|---|---|
| `await_requirements_discussion` | 有素材、無 needs | 對著盤點和使用者討論劇本,產 `material_needs.json` |
| `await_map_review` | 有 needs、有素材但尚未 review/連結(無 satisfies),或素材夠但缺 contract | 做 caption/agent review 把 scene 連到 need;或補上 contract |
| `await_material` | must_have 缺料且無合法 fallback | 產/交付 shooting brief,等補拍或既有素材交回 |
| `await_revision_decision` | delta 有缺口、需人工決定如何處理(或已有 decisions 但尚未 accepted) | 由導演/人工選 route 並 **accept** |
| `revision_blocked` | 已套用 accepted decisions 但仍有未解 tier-1 缺口 | 補 explicit waiver、補料,或改決策 |
| `build_ready` | 全部 covered 或 tier-1 缺口已被 canonical waiver 解除 | 交付 BUILD handoff |
| `invalid` | 輸入損壞 / dangling need / 重複 asset / 矛盾 | 修素材地圖或需求契約,**不得 BUILD** |

## 怎麼產 material_needs.json(從討論)

對話出每個「需求」的八件事(見 `shooting-brief` skill):拍什麼、幾個人、什麼動作、
場景、鏡位、時長、補哪一段、為什麼。每個 need 至少:`category / type / purpose /
count / must_have / fallback_tier`(可選 `fallback_options`)。寫好後一律先:

```
python video_tools.py validate-needs needs.json --migrate --out material_needs.json
```

`--migrate` 配發穩定 `need_id`(內容雜湊**初值**,一旦配發即永久;改用途不換 id)。
**不要**自己編 need_id,**不要**手改 join key。

## 三個入口的標準動作

- **只有素材**:`--maps-dir`/`--material-db` → runner 聚合 `project_material_map.json`、
  回報影片/照片/場景數與 caption 覆蓋率。**不要發明 requirements、不要跑 delta**。
  stage=`await_requirements_discussion`,然後你和使用者討論劇本。
- **只有劇本需求**:`--needs` → runner 產 `shooting_brief.json`;must_have 缺料時
  stage=`await_material`、`can_build=false`。把 brief 交給拍攝者,**不要硬 BUILD**。
- **partial/hybrid**:`--needs` + 部分 maps → runner 算 fresh delta。covered 可留;
  thin/missing/excess 留 evidence。有阻擋缺口 → `await_material`/`await_revision_decision`;
  全滿足或有 canonical waiver → `build_ready`。

## 人工決策(accepted decisions)怎麼用

`revision_decisions.json` 是**人/導演**明確接受的處理方式,M6c 只執行 `accepted`:

- `collect_material` / `reshoot`:不改劇本,維持阻擋,輸出 `await_material`。
- `dashboard_review`:不改劇本,輸出 `await_review`。
- `shorten_or_merge`:只縮短**指定 target_segment**(保留 need_refs)。
- `script_rewrite`:只套用決策內**明確提供**的 patch(**不得**由 agent 生成內容,
  不得改 segment identity / need_refs / need_id)。
- `drop_segment`:只刪指定 segment;**must_have / tier-1 需逐一帶 explicit waiver**
  (`reviewer + reason`),否則 fail。

每筆 decision:`decision_id`(唯一)、`need_id`(須在當前 delta)、`route`(須與該
delta outcome 相容)、`status: accepted|rejected`、視 route 帶 `target_segment` /
`patch` / `waiver`、`lineage{reviewer,reason,at}`(呼叫者提供,無隱藏時鐘)。

runner 套用後**重跑 `gate_from_delta`(帶 canonical waivers)**:通過才
`build_ready`。`rejected`/未 accept 的決策**不會**被套用。

## 何時可以交 BUILD,何時必須停

`build_ready` 是**有牙齒的**:只有以下全部成立才會出現,否則維持 await/invalid:

- **actual-side source 只能有一個**(`--project-map` / `--maps-dir` / `--material-db`
  三選一;同時給多個 → `invalid`,不靜默挑優先序)。
- **`--material-db` 是唯一可 BUILD 的來源**;`--maps-dir` / `--project-map` 只能盤點,
  即使算出 covered 也**不會** build_ready(避免「用 A 算 covered 卻交 B 給 BUILD」)。
- contract 通過 `spec_contract.validate_segment_contract`。
- contract 必須宣告 `material_needs_ref`,且 strict resolve(相對 contract 目錄)到
  **與 lifecycle 同一個** needs 檔;未宣告 / 指向不同 needs → `invalid`。
- 有 revision 時,contract 還必須宣告 `revision_decisions_ref` 綁定到同一份 decisions,
  讓 `run_contract` **重跑 M6c**、重新推導 waivers。
- handoff `{contract_ref, material_db_ref, material_needs_ref, revision_waivers,
  ready_for_build}` 的每個 ref 都必須是**真實存在**的檔案。

handoff `contract_ref` 一律指向**原 contract**(它綁定了 needs 與 decisions);
`run_contract` 收到後**重跑 fresh M6b/M6c gate**——無 revision 時直接過 gate;
有 revision 時重套 accepted decisions、重推 waivers、再過 gate,並 BUILD revised 結果。
`revised_segment_contract.json` 仍寫出,記在 `refs.revised_contract` 作為證據/預覽。
M6d **不繞過、不取代** runtime gate。(把 standalone revised contract + 外部 waiver
注入直接交 BUILD 的捷徑,留待 M6e。)
- **可以只完成一個階段就停**:只盤點、只產 brief、停在等料/等決策/等 revision 都算成功。
  **不得**為了宣稱成功而 BUILD/render 或硬湊 `final.mp4`。

## 何時必須回 `invalid`(fail-closed,交回 Python 工具判定)

needs 損壞 / dangling need_id / 重複 asset identity / 損壞的 map 或 DB /
stale/unknown decision need_id / revision 與 gate 矛盾 / revised contract 無效 /
handoff ref 不存在。這些都由 runner 確定性判定——**你不要自己 override 或猜測**。

## 與其他 Skill 的銜接
- 上游:`gap-analyzer`(產 needs 草稿)、`shooting-brief`(把 need 翻成拍攝任務)。
- 下游:`video-pipeline`(吃 build handoff,跑 SPEC→BUILD→VERIFY)。
- 真實案例端到端驗收(真渲 + 學員素材回放)= **M6e**,尚未完成。

---

## ISF1 Material-Map Handoff

Material-map 在 ISF1 裡只負責素材真相與 BUILD handoff，不負責寫故事、產圖、或接受 Workbench draft。

| 來源 | material-map 怎麼接 | 邊界 |
|---|---|---|
| `story-soul-blueprint` | 接 `material_needs.json` / director shot plan，驗證需求與素材覆蓋 | 不替故事補靈魂、不發明 need |
| 既有素材 | 接 per-asset map / `project_material_map.json` / `material_db.json` | 不移動 source file；folder 只是 projection |
| `generated-material-producer` | generated asset 回來後只成為 `candidate satisfies` evidence | 未 review 前不得當 covered |
| `storyboard_panel_locked=true` | comic/photo/storybook narration 要一個 panel 對一個 beat | 拉長 panel 或生成更多；不要用同 need 其他 panel 自動補滿 |
| Workbench | 讀 draft patch / contract patch 作 review 線索 | Workbench must not overwrite canonical needs/maps/delta/handoff |

回傳規則：

- 缺素材且允許生成 → `material-generation-fallback` / `generated-material-producer`。
- 缺素材但不能生成 → `await_material` 或 `revision_decisions.json`。
- 人工修剪 timeline → Workbench draft 交 agent review；若影響需求或素材身份，回 material-map / revision，不直接改 canonical。
- 可以 BUILD 只代表 material truth 通過；正式輸出仍必須由 `video-pipeline` / `contract-run` 重新 gate。
