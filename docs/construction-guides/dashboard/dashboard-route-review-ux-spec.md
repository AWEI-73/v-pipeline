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
