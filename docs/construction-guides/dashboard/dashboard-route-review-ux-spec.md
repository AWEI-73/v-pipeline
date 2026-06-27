# Dashboard Route Review UX Spec

Status: draft for frontend implementation
Updated: 2026-06-21

## Purpose

Hermes Dashboard should become the clean review surface for the video pipeline.
It should show where the run is, what important artifacts were produced, why the
agent paused, and what the user can review or accept next.

This dashboard is not a timeline editor. It is a route/status/review surface.
Interactive editing remains in Workbench, and canonical pipeline artifacts remain
backend-owned.

## Existing UI References

Use these existing files as references:

- `video_pipeline_core/dashboard.html`
  - Current self-contained dashboard template.
  - Good reference for the white theme, header, next action banner, badges, node
    detail panel, and artifact/status layout.
- `dashboard/dashboard_v1.css`
  - Good reference for light theme tokens, status badges, header structure,
    next-action-card styling, and compact operational UI.
- `dashboard/README.md`
  - Defines the Dashboard / Workbench responsibility split.
- `docs/workbench-dashboard-integration.md`
  - Defines the canonical boundary: Dashboard reads and reviews; Workbench drafts;
    backend owns official render and canonical truth.
- `video_pipeline_core/dashboard_state.py`
  - Current backend state collector and artifact loading source.

Avoid using `dashboard/dashboard_v1.html` as a text/content source because some
Chinese text is currently mojibake. Its broad layout can be referenced, but not
its copy.

## Product Model

The dashboard should feel like:

```text
Pipeline route map + artifact review desk + agent pause control
```

It should answer five questions quickly:

1. What mode is this run in?
2. Which important stage are we at?
3. Which important files exist?
4. Why did the agent stop?
5. What should the user review, accept, revise, or provide next?

## Main Layout

Use a clean white operational layout.

```text
Header
Run Facts / Mode / Agent State

Review Stop Banner / Next Action

Main Area
  Left: vertical route rail
  Right: selected stage detail + important artifact cards + artifact viewer
```

The page should prioritize structure and clarity over decoration. Use white
background, subtle borders, restrained shadows, and high-signal highlights.

## Route Rail

The left rail is the main navigation. It should be a vertical line with circular
nodes.

Example:

```text
○ Video Intent Planner
│
○ Material Understanding
│
○ Story / Structure Planning
│
○ Material Map
│
○ Generated Material Fallback
│
○ Contract / Segment Plan
│
○ Build / Timeline
│
○ Reviewer Gates
│
○ Render / Verify
```

The visible node labels should use user-facing workflow names, not internal node
numbers. Internal node ids can still exist in the data model.

### Node Shape

Each node should include:

- circular status marker;
- short stage label;
- one-line summary;
- small status badge;
- count of important artifacts;
- optional review-required indicator.

## Greenfield And Brownfield Modes

The dashboard should support two main route modes.

### Greenfield

Use when the user has no existing media, or starts from an idea, article, story,
teaching goal, or script-like input.

Primary path:

```text
Video Intent Planner
-> Story / Structure Planning
-> Material Needs
-> Generated Material Fallback
-> Generated Provider Review
-> Contract / Build / Verify
```

Greenfield emphasis:

- story structure;
- script/scene intent;
- material needs;
- generated material provider;
- review before treating generated media as accepted.

### Brownfield

Use when the user has existing media. This usually means the user already has an
implicit intent, and the pipeline should first reduce ambiguity and understand
the material.

Primary path:

```text
Video Intent Planner
-> Material Ingest
-> Material Map
-> Material Gap / Delta
-> Structure From Material
-> Contract / Build / Verify
```

Brownfield emphasis:

- material map;
- usable scenes;
- gaps and missing evidence;
- structure from real material;
- user review of material choices.

## Material Map View

Material Map should be a dedicated visualization surface inside Dashboard, not a
timeline editor.

Boundary:

```text
Material Map = evidence and understanding
Workbench = timeline operation and draft editing
```

The Material Map view is important because it bridges user intent and buildable
video evidence. In brownfield runs, it is often the main place where the system
discovers what the user actually meant. In greenfield or hybrid runs, it is also
where generated material returns as candidate evidence before acceptance.

### Material Map Purpose

The Material Map view should answer:

1. What material exists?
2. What scenes or usable fragments exist inside each material?
3. Which needs does each scene support?
4. Which needs are covered, thin, missing, or excessive?
5. Which scenes are candidate, accepted, or rejected?
6. What did reviewer roles say about this scene or need?
7. Which usable source window or rough-cut timing is already known?

The Material Map view should translate machine fields into human-readable
decision rows:

- `scene.satisfies[]` -> adopted/candidate/rejected need relationship;
- `scene.usable_range` or `scene.start/end` -> 可用區間;
- `scene.start_sec + scene.duration_sec` -> 粗剪切點;
- `asset_id + scene_index` -> handoff target for Workbench.

These timing fields are read-only in Dashboard. If the user wants to trim,
replace, reorder, or preview the edit, route the selected `asset_id +
scene_index` to Workbench. Workbench writes draft patches; backend review/apply
owns canonical timeline and ffmpeg inputs.

### Material Map Layout

Recommended layout:

```text
Left: asset list
Center: scene cards / visual evidence board
Right: needs, coverage, reviewer notes, and decision actions
```

The scene is the core unit. Every scene card should be visually inspectable and
should preserve traceability back to the asset and need.

Scene card fields:

```json
{
  "asset_id": "asset_001",
  "scene_index": 0,
  "time_range": "00:12.0-00:18.5",
  "usable_range": {"start": 12.0, "end": 18.5},
  "start_sec": 12.0,
  "duration_sec": 6.5,
  "thumbnail": "thumbs/asset_001_s000.jpg",
  "caption": "Students receiving certificates on stage",
  "transcript": "optional speech/transcript excerpt",
  "visual_family": "ceremony",
  "angle_scale": "medium",
  "action_family": "award_receiving",
  "subject": "students and teacher",
  "satisfies": [
    {
      "need_id": "nd_closing_ceremony",
      "status": "candidate",
      "reason": "Shows award moment but lacks wide crowd context."
    }
  ],
  "reviewer_notes": [
    {
      "role": "story_director",
      "decision": "usable_with_caution",
      "note": "Good emotional setup, too static for climax."
    }
  ]
}
```

### Material Map Actions

Dashboard may allow review and classification actions:

- accept scene for a need;
- reject scene for a need;
- mark scene as thin evidence;
- request more material;
- allow generated fallback for a missing need;
- add reviewer note;
- send selected `asset_id + scene_index` to Workbench.

Dashboard should not allow timeline operations here:

- no clip trimming;
- no timeline placement;
- no final ordering;
- no canonical timeline rewrite.

If the user wants to trim, replace, reorder, or preview an edit, route them to
Workbench. Workbench writes draft patches only.

### Director Review In Material Map

Director review can appear in Material Map because each scene has narrative and
emotional meaning, not only evidence value.

The distinction is:

```text
Material curator asks: does this scene support the need?
Director asks: does this scene work emotionally and narratively?
Editor asks: can this scene work in rhythm and sequence?
```

These notes can be attached to the same scene card, but they should not turn the
Material Map into a timeline editor. The view remains an evidence board with
review notes.

### Hybrid

Hybrid does not need to become a third primary rail at first. Show it as a badge
on either route:

```text
Brownfield with generated fallback
Greenfield with reference material
```

## Suggested Stage List

Use this as the first version of the stage map.

| Stage Id | Label | Applies To | Purpose |
|---|---|---|---|
| `video_intent_planner` | Video Intent Planner | both | Decide goal, audience, material availability, route, and next handoff. |
| `material_ingest` | Material Ingest | brownfield | Register existing media or documents. |
| `material_map` | Material Map | brownfield / hybrid | Map material to usable scenes and needs. |
| `story_structure` | Story / Structure Planning | greenfield / hybrid | Produce story, teaching, recap, or script structure. |
| `material_needs` | Material Needs | both | Declare what visual/audio/text evidence is required. |
| `material_delta` | Material Gap / Delta | both | Identify covered, thin, missing, and excess material. |
| `generated_fallback` | Generated Material Fallback | greenfield / hybrid | Plan generated image/video candidates for missing material. |
| `provider_review` | Provider Review | greenfield / hybrid | Review generated provider outputs before accepting them. |
| `contract_plan` | Contract / Segment Plan | both | Compile route decisions into segment contract. |
| `build_timeline` | Build / Timeline | both | Produce assembly/timeline artifacts and draft render path. |
| `reviewer_gates` | Reviewer Gates | both | Director, material producer, editor, spec, and supply reviews. |
| `render_verify` | Render / Verify | both | Produce final video and verification artifacts. |

## Stage Status

Each stage should use a normalized status.

```json
{
  "status": "not_started | running | review_required | blocked | accepted | completed | skipped"
}
```

Visual mapping:

| Status | Visual |
|---|---|
| `not_started` | gray hollow circle |
| `running` | blue circle with subtle pulse |
| `review_required` | amber circle and highlighted row |
| `blocked` | red circle and strong warning badge |
| `accepted` | deep green circle |
| `completed` | green circle |
| `skipped` | gray muted circle |

## Review Stop Banner

When the agent pauses for review, show a prominent but calm banner near the top.

Example:

```text
Agent paused for review
Stage: Generated Provider Review
Reason: 2 generated candidates require acceptance before build.
Recommended action: Review and accept, or request revision.
```

Suggested actions:

- `Accept and Continue`
- `Request Revision`
- `Ask Agent`
- `Open Artifact`
- `Copy Run Folder`

Important rule: accepting in Dashboard should write a review decision artifact.
It should not silently mutate canonical pipeline truth.

## Important Artifact Cards

Each stage should show important artifacts as cards. Do not list every file by
default. Show only high-signal documents for the selected stage.

Artifact card fields:

```json
{
  "label": "video_intent.json",
  "path": "video_intent.json",
  "role": "intent | material_map | generated_provider | contract | review | render",
  "status": "missing | produced | review_required | accepted | rejected",
  "summary": "Route: brownfield, next: material map",
  "highlights": [
    "route = existing-material-first",
    "material_availability = partial",
    "required_followup_questions = 2"
  ],
  "actions": ["open", "copy_path", "accept", "request_revision"]
}
```

Visual style:

- white card;
- 1px subtle border;
- 6px to 8px border radius;
- thin colored left border by artifact role;
- highlighted key-value pills for important fields;
- compact summary first;
- raw JSON hidden behind expand/drawer.

Do not render raw JSON as the primary view. The primary view should be summaries,
important keys, findings, and next actions.

## Decision Data Presentation

The dashboard should show decision-making data, not every mechanical file.
Internal artifact names and JSON keys stay in English because they are the
pipeline contract. User-facing labels, summaries, status text, and action copy
should be Chinese.

Rule:

```text
English artifact/key = stable machine contract
Chinese label/summary = user-facing review layer
Raw JSON = debug drawer, not the default view
```

### Artifact Visibility Levels

Use three visibility levels.

| Level | UI Name | Meaning | Default UI |
|---|---|---|---|
| `decision` | 決策產物 | Changes route, review, approval, repair, render eligibility, or user choice. | Always show as cards. |
| `evidence` | 證據產物 | Visual/audio/text evidence for a decision. | Show visually or as compact proof links. |
| `debug` | 串接產物 | Mechanical handoff, manifests, raw worker outputs, generated indexes. | Collapse under debug/details. |

### Stage Decision Data

Each stage detail panel should render these normalized fields:

```json
{
  "stage_id": "material_map",
  "label_zh": "素材地圖",
  "status": "review_required",
  "summary_zh": "已有素材完成粗篩，等待確認哪些片段可支撐需求。",
  "decision_zh": "需要確認素材與需求的對應是否可接受。",
  "next_action_zh": "請審核素材地圖，接受、退回或標記缺口。",
  "blocking_reason_zh": null,
  "primary_artifacts": [],
  "evidence_artifacts": [],
  "debug_artifacts": []
}
```

The frontend may receive this from a backend API later. Until then, it can map
from existing artifacts using the dictionaries below.

### Stage Dictionary

| `stage_id` | Chinese Label | Purpose | Decision Artifacts |
|---|---|---|---|
| `video_intent_planner` | 影片意圖 | Decide video type, audience, goal, material/text state, entry route, and handoff. | `video_intent.json`, `project_brief.json`, `project_brief.md` |
| `material_ingest` | 素材匯入 | Register existing media and candidate source folders. | `materials_db.json`, `material_wall_request.json` |
| `material_wall_review` | 素材粗篩 | Coarse-screen keep/maybe/reject/duplicate and visual role. | `material_wall_review_verdict.json`, `material_wall_handoff_report.json` |
| `material_map` | 素材地圖 | Map assets/scenes to needs and reviewer decisions. | `project_material_map.json`, `material_map_review_apply_result.json` |
| `material_delta` | 覆蓋差異 | Decide covered/thin/missing/excess and whether BUILD can continue. | `material_delta.json`, `material_map_lifecycle.json`, `material_gap_brief.json` |
| `story_structure` | 故事結構 | Produce story world, beats, and material needs for story-first routes. | `story_world.json`, `screenplay_beats.json`, `story_soul_blueprint.json`, `material_needs.json` |
| `generated_fallback` | 生成素材補位 | Plan and review generated candidates for missing needs. | `material_generation_fallback.json`, `generated_material_review.json`, `reviewed_project_material_map.json` |
| `effect_factory` | 特效工廠 | Convert fuzzy effect intent into reviewed parameters and bounded effect assets. | `visual_technique_plan.json`, `visual_technique_review.json`, `visual_technique_plan.confirmed.json`, `effect_review.json`, `effect_handoff.json` |
| `contract_plan` | 段落契約 | Compile intent/material/story into buildable segment contract. | `segment_contract.json`, `spec_review.json`, `supply_review.json` |
| `build_timeline` | 時間線 | Build rough/final timeline and editor decisions. | `rough_cut_plan.json`, `assembly_plan.json`, `timeline_build.json`, `editor_review.json` |
| `verify_delivery` | 驗證交付 | Verify final/draft output and route failures to owners. | `verify_result.json`, `caption_audit.json`, `visual_audit.json`, `delivery_requirements.json` |
| `workbench` | 剪輯工作台 | Draft-only edits for timing, source windows, subtitle/audio/effect patches. | `workbench_review_report.json`, `workbench_handoff.json`, `timeline_patch.json` |

### Artifact Dictionary

Use this dictionary to translate artifact roles into user-facing cards.

| Artifact | UI Label | Visibility | Primary Fields To Show |
|---|---|---|---|
| `video_intent.json` | 影片意圖判斷 | `decision` | `video_type`, `audience`, `goal`, `input_state`, `entry_path`, `route`, `handoff_to`, `required_followup_questions`, `assumptions` |
| `project_brief.md` | 使用者需求摘要 | `decision` | markdown summary, target length, audience, constraints |
| `material_wall_review_verdict.json` | 素材粗篩結果 | `decision` | keep/maybe/reject/duplicate counts, visual roles, reviewer notes |
| `project_material_map.json` | 素材地圖 | `decision` | asset count, scene count, satisfies edges, accepted/candidate/rejected coverage |
| `material_delta.json` | 素材覆蓋差異 | `decision` | `ready_for_build`, covered/thin/missing/excess counts, blocking needs |
| `material_gap_brief.json` | 缺口補強清單 | `decision` | missing/thin needs, reshoot/generated/stock jobs, next route |
| `rough_cut_plan.json` | 粗剪計畫 | `decision` | selected clips, rejected/duplicate exclusions, usable ranges, gaps |
| `visual_technique_plan.json` | 特效參數候選 | `decision` | `style_family`, `effect_role`, `candidate_options`, `visual_primitives`, `motion_primitives`, `controls`, `negative_rules`, `handoff_to` |
| `visual_technique_review.json` | 特效參數選擇 | `decision` | `decision`, `selected_option`, `control_overrides`, add/remove rules, reviewer note |
| `visual_technique_plan.confirmed.json` | 特效參數確認版 | `decision` | selected option, revised controls, worker handoff readiness |
| `effect_review.json` | 特效審核 | `decision` | pass/revise/fail, intent match, readability, evidence refs, next action |
| `timeline_build.json` | 時間線建置 | `decision` | segment/clip links, source path, source window, duration, text/audio/effect markers |
| `editor_review.json` | 剪輯審核 | `decision` | decision, findings, rerender/block/human-review reason |
| `verify_result.json` | 成片驗證 | `decision` | pass, score, dimensions, issues, next action |
| `caption_audit.json` | 字幕可讀性 | `decision` | overflow/readability findings, affected segments, next route |
| `visual_audit.json` | 視覺審核 | `decision` | content alignment, black frames, repeated visuals, visual fatigue |
| `keyframe_grid.jpg` | 關鍵畫面格 | `evidence` | visual image grid |
| `contact_sheet.jpg` | 素材/生成檢視牆 | `evidence` | visual image grid |
| `final.mp4` | 最終影片 | `evidence` | player, duration, verify state |
| `artifact_manifest.json` | 產物索引 | `debug` | path refs only |
| `run_layout.json` | Run Folder 結構 | `debug` | folder roles |
| `route_subagent_task.json` | Agent 任務包 | `debug` | task owner, required outputs, protected refs |
| `route_subagent_result.json` | Agent 回報包 | `debug` | status, produced artifacts |
| `remotion_worker_outputs.json` | Remotion Worker 原始輸出 | `debug` | job count, output refs; summarize through `effect_review.json` first |

### Field Label Dictionary

Field labels should be centralized so UI copy can change without touching
artifact parsing code.

```json
{
  "video_type": "影片類型",
  "audience": "主要觀眾",
  "goal": "影片目的",
  "input_state": "輸入狀態",
  "entry_path": "進入路線",
  "route": "路線",
  "material_availability": "素材狀態",
  "required_followup_questions": "需要追問",
  "assumptions": "目前假設",
  "handoff_to": "交接給",
  "ready_for_build": "可進入 BUILD",
  "covered": "已覆蓋",
  "thin": "薄弱",
  "missing": "缺少",
  "excess": "多餘",
  "style_family": "風格家族",
  "effect_role": "特效角色",
  "candidate_options": "可選方向",
  "visual_primitives": "視覺元素",
  "motion_primitives": "動態元素",
  "controls": "控制參數",
  "negative_rules": "避免事項",
  "selected_option": "選擇方向",
  "control_overrides": "參數覆寫",
  "source_path": "來源檔案",
  "start_sec": "起始秒數",
  "duration_sec": "持續秒數",
  "next_action": "下一步",
  "blocking_reason": "阻擋原因"
}
```

### Status Label Dictionary

```json
{
  "not_started": "尚未開始",
  "running": "執行中",
  "review_required": "等待審核",
  "blocked": "已阻擋",
  "accepted": "已接受",
  "completed": "已完成",
  "skipped": "已略過",
  "missing": "缺少",
  "produced": "已產出",
  "rejected": "已退回",
  "repair": "需修正",
  "run": "可繼續",
  "done": "完成"
}
```

### Route Label Dictionary

```json
{
  "material-first": "素材優先",
  "existing-material-first": "既有素材優先",
  "structure-first": "結構優先",
  "story-first": "故事優先",
  "hybrid": "混合路線",
  "needs-context": "需要補充資訊",
  "effect_factory_parameter_review": "特效參數待審核",
  "effect_factory_parameter_review_apply": "特效參數待套用",
  "effect_factory_contract": "特效契約階段",
  "stage2_material_map": "素材地圖階段",
  "stage3_review_apply": "素材審核套用",
  "stage4_dry_build": "BUILD 規劃",
  "stage5_final_review": "最終審核"
}
```

### Recommended Frontend Module Boundary

Keep mapping logic separate from components:

```text
dashboard/src/domain/pipelineDictionary.js
  stageLabels
  artifactLabels
  fieldLabels
  statusLabels
  routeLabels

dashboard/src/domain/artifactImportance.js
  classifyArtifact(path, payload) -> decision | evidence | debug
  pickPrimaryFields(artifactName, payload) -> key/value highlights

dashboard/src/domain/stageViewModel.js
  buildStageViewModel(pipelineHome, artifacts) -> stages[]
```

The first implementation can be plain JavaScript. Do not hard-code Chinese
labels inside view components when a dictionary key can be used instead.

## Artifact Highlighting

Important fields should be visually highlighted.

Examples:

For `video_intent.json`:

- `route`
- `entry_path`
- `material_availability`
- `required_followup_questions`
- `handoff_to`

For `material_delta.json`:

- `ready_for_build`
- `covered`
- `thin`
- `missing`
- `blocks_ready_for_build`

For `generated_provider_outputs.json`:

- `provider`
- `copied_count`
- `source_session`
- `file`

For `generated_material_review.json`:

- `reviewer`
- `accepted`
- `rejected`
- `decisions`

For `reviewer_aggregation.json`:

- `overall_decision`
- `next_action`
- `blocking_roles`
- `finding_count`

## Interaction Model

Minimum interactions:

1. Select stage on rail.
2. Show stage detail on the right.
3. Click artifact card to open summary + raw JSON drawer.
4. User can write a review decision.
5. Dashboard saves the decision as a new artifact.

Optional later interactions:

- compare before/after artifact;
- show image/video thumbnail for generated or rendered material;
- show command to continue agent route;
- show agent handoff packet;
- link to Workbench for draft edits.

## Persisted Review Decision

Dashboard review actions should write a separate decision artifact.

Suggested filename:

```text
dashboard_review_decision.json
```

Example:

```json
{
  "artifact_role": "dashboard_review_decision",
  "version": 1,
  "stage_id": "generated_provider_review",
  "reviewer": "user",
  "decision": "accepted",
  "notes": "The generated panels are consistent enough to continue.",
  "accepted_artifacts": [
    "generated_provider_outputs.json",
    "generated_material_review.json",
    "reviewed_project_material_map.json"
  ],
  "next_action": "continue_pipeline",
  "created_at": "2026-06-21T13:00:00+08:00"
}
```

Supported decisions:

```text
accepted
request_revision
provide_more_material
blocked
skip_optional
```

## Recommended View Model

Frontend should not infer the whole route by scanning random files. Prefer a
backend-produced view model.

Suggested artifact:

```text
dashboard_route_view.json
```

Schema draft:

```json
{
  "artifact_role": "dashboard_route_view",
  "version": 1,
  "run_id": "story_real_imagegen_smoke_20260621",
  "mode": "greenfield",
  "hybrid_badges": ["generated_fallback"],
  "current_stage": "provider_review",
  "agent_state": "paused_for_review",
  "next_action": "review_generated_material",
  "run_folder": ".tmp/story_real_imagegen_smoke_20260621",
  "stages": [
    {
      "id": "video_intent_planner",
      "label": "Video Intent Planner",
      "status": "completed",
      "summary": "Greenfield story route; generated fallback required.",
      "artifacts": [
        {
          "label": "video_intent.json",
          "path": "video_intent.json",
          "role": "intent",
          "status": "produced",
          "summary": "Route: story-first",
          "highlights": [
            "material_availability = none",
            "handoff_to = story_structure"
          ]
        }
      ]
    }
  ]
}
```

## Boundary Rules

Dashboard may:

- read run state;
- show important artifacts;
- show summaries and highlights;
- save review decision artifacts;
- link to Workbench;
- show commands or next actions for the agent/backend.

Dashboard must not:

- overwrite `final.mp4`;
- rewrite canonical contract files directly;
- silently accept generated material without explicit review decision;
- become a timeline editor;
- treat Workbench draft artifacts as canonical truth.

## Visual Direction

Use the existing white theme. Keep it friendly and focused.

Recommended style:

- white / slate background;
- thin gray borders;
- restrained shadows;
- green for completed/accepted;
- amber for review-required;
- red for blocked;
- blue for running/current;
- role-based artifact accent colors;
- dense but readable spacing.

Avoid:

- decorative gradients;
- oversized marketing hero layout;
- excessive cards inside cards;
- large raw JSON blocks as default content;
- too many colors competing at once.

## Implementation Order

1. Static prototype
   - Build the white layout, vertical rail, stage detail, artifact cards, and
     review banner with mocked data.

2. View model integration
   - Load `dashboard_route_view.json` or an equivalent API response.

3. Artifact drawer
   - Add artifact summary, highlighted fields, raw JSON toggle, and copy path.

4. Review decision writer
   - Save `dashboard_review_decision.json`.

5. Agent/backend continuation
   - Let the agent/backend consume review decisions and continue, revise, or
     block the route.

## Acceptance Criteria

- User can identify mode, current stage, and next action within five seconds.
- Important artifacts are visible without opening the file browser.
- Review-required stages are visually obvious but not visually noisy.
- Generated material cannot become accepted without an explicit decision artifact.
- Dashboard stays read/review oriented and does not become a timeline editor.
- The layout remains usable on desktop and narrow laptop widths.
