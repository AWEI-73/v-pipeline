# Dashboard Frontend Implementation Plan

## Purpose

This plan defines the next frontend phase for the Hermes video pipeline dashboard.

The immediate goal is not to add more visual experiments. The goal is to turn the dashboard into a clean review and handoff surface for real pipeline runs, using the two current baseline cases:

- `standard_brownfield_training_20260621`
- `baseline_greenfield_story_generated_material_20260621`

The frontend should help a Chinese-speaking user understand and review the pipeline without reading raw JSON first.

## Current Boundary

Do not continue prototype-driven UI work until the backend pipeline has been tested end to end against the two baseline runs.

For now, frontend work should stay as a plan/spec only. Implementation should resume after the pipeline test pass/fail picture is clear.

## Product Direction

The dashboard should become a route review workbench.

The first screen should show:

- Which run is selected.
- Whether this is greenfield or brownfield.
- Which major pipeline nodes are complete, blocked, or waiting for review.
- The important human-readable information inside each node.
- The key artifacts behind each node for agent handoff and debugging.

The UI should not treat JSON filenames as the primary user experience. JSON is the contract layer; the dashboard should translate it into reviewable cards, status summaries, and guided next actions.

## Main Views

### 1. Route Overview

This is the primary dashboard view.

It should show a vertical pipeline rail with major nodes:

- Intent
- Material Ingest
- Material Map
- Coverage Delta
- Structure
- Contract
- Timeline
- Review Gates
- Verify

Each node should show:

- Chinese title.
- Short human-readable summary.
- Status pill: `已有資料`, `可進行`, `缺資料`, `待處理`, or `阻塞`.
- Current important artifact, visible only as supporting detail.

Clicking a node should show a structured detail panel, not raw JSON.

### 2. Intent Review

This should visualize `video_intent.json` as an opening decision card.

Show:

- Video type.
- Audience.
- Goal.
- Material availability.
- Text availability.
- Input state.
- Entry path.
- Route.
- Gap strategy.
- Handoff target.
- Required follow-up questions.
- Assumptions.
- Expected outputs.

The user should be able to review this as a launch brief.

Future edit model:

- Do not directly overwrite `video_intent.json`.
- Create `video_intent_patch.json` or a draft change packet.
- Agent/user review can then accept or reject the patch.

### 3. Material Map Review

This should stay visually separate from the route overview because material map can become complex.

Show:

- Asset list.
- Scene list per asset.
- Need coverage.
- Accepted/candidate/rejected mapping.
- Coverage delta.
- Missing or thin needs.

The UI should focus on visual evidence and decision support, not raw tables.

Material map is important enough to deserve its own detailed review surface. Do not merge all details into the route rail.

### 4. Workbench

Workbench should stay inside the dashboard shell, but its write behavior must remain draft-only.

Show:

- Whether preview is available.
- Draft artifact status.
- Handoff readiness.
- Review report status.
- Timeline/subtitle/audio/effect patch counts.

Future migration:

- Keep iframe containment until native modules are stable.
- Later extract workbench modules into SPA-native components.

### 5. Verify / Delivery

This view should show whether the run is actually deliverable.

Show:

- Final video presence.
- Verify result.
- Delivery gate.
- Evidence bundle.
- Contact sheet / visual proof if available.
- Known risks or unresolved findings.

## Data Contract

The frontend should use structured API payloads, not parse arbitrary JSON files directly.

Required APIs:

- `/api/projects`
- `/api/control/status`
- `/api/material-map-view`
- `/api/artifacts`
- `/api/workbench/health`

Recommended normalized frontend fields:

- `materialMap.intent`
- `materialMap.stages`
- `materialMap.stats`
- `materialMap.delta_summary`
- `materialMap.assets`
- `materialMap.needs`
- `artifacts.workbench.draft_summary`
- `artifacts.final_video_url`
- `artifacts.run_layout`

If a field is important for UI review, normalize it in the backend API first. Avoid making frontend components know too much about raw artifact shapes.

## Visual Style

Keep the current white dashboard direction.

Use:

- Clean white background.
- Restrained borders.
- Small radius, max 8px.
- Green/brown route mode indicators.
- Clear status pills.
- Dense but readable information.
- Highlighted evidence cards for important files or decisions.

Avoid:

- Big marketing hero sections.
- Decorative gradient blobs.
- Mock/prototype pages as production routes.
- Large raw JSON panels as the primary user view.
- Overly thick headings where concise labels would work better.

## Greenfield / Brownfield Modes

The dashboard should make route mode obvious.

Brownfield:

- User has existing material.
- Main path starts with material ingest and material map.
- UX emphasis: disambiguate, classify, map, find gaps, build.

Greenfield:

- User has no visual material or starts from story/text.
- Main path starts with intent, structure, story blueprint, generated material fallback.
- UX emphasis: clarify story, generate/collect missing material, then material map.

The same pipeline rail can be used, but the selected mode should affect node summaries and priority.

## Review And Update Model

Every editable decision should use a draft/patch model.

Examples:

- `video_intent_patch.json`
- `material_map_review_decision.json`
- `timeline_patch.json`
- `workbench_handoff.json`

The dashboard should support review first, write later.

Do not let frontend directly mutate canonical artifacts without a clear handoff packet.

## Implementation Order

### Phase 0: Pipeline Verification First

Before more frontend work:

- Run brownfield baseline from intent through material map, timeline, workbench handoff, verify.
- Run greenfield baseline from intent through story blueprint, generated material, material map, timeline, verify.
- Record missing artifacts and broken assumptions.

Frontend implementation should wait for this pass/fail report.

### Phase 1: Route Overview Cleanup

- Ensure `/dashboard` serves only SPA.
- Remove production dependency on prototype/mock HTML.
- Make route rail status derive from real artifacts.
- Make node summaries human-readable.
- Keep artifact filenames as supporting detail.

### Phase 2: Intent Review Card

- Render `materialMap.intent` as a Chinese opening brief.
- Add review-only UI for assumptions, questions, and expected outputs.
- Add draft patch spec for future edit.

### Phase 3: Material Map Review Surface

- Improve asset/scene/need visualization.
- Add evidence drawer.
- Add coverage decision cards.
- Keep data dense and scannable.

### Phase 4: Workbench Integration

- Keep iframe if stable.
- Move health/draft/handoff summary into SPA-native panels.
- Only then consider replacing iframe composition.

### Phase 5: Edit And Save Flow

- Add patch generation.
- Add user review stop.
- Add agent handoff packet.
- Add accept/apply mechanism only after patch schema is stable.

## Acceptance Criteria

Frontend is acceptable when:

- A Chinese user can understand the selected run without opening raw JSON.
- The two baseline runs show different route modes clearly.
- Every major node has a visible status and meaningful summary.
- Important artifacts are visible but not the primary prose.
- The dashboard does not list stale `.tmp` or old `video_project` cases.
- Workbench remains draft-only.
- No production route serves mock/prototype UI.
- Browser smoke test passes.
- Backend API tests pass.

## Deferred

Do not do these before pipeline verification:

- Full native Workbench rewrite.
- Complex material drag timeline editor.
- OAuth/login/runtime packaging.
- Renderer changes.
- Node14/Remotion changes.
- BUILD ranking changes.
- Large visual redesign unrelated to route review.

