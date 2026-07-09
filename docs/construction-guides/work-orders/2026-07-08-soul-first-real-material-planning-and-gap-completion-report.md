# 2026-07-08 Soul-First Real-Material Planning And Gap Completion Report

## Summary

- Output root: `.tmp\soul_first_real_material_planning_20260708-060509`
- Render/final media: not created
- `story_human_review_decision.json`: not written
- Pipeline readiness: `ready_for_render=false`
- Next owner: `human_story_material_review`
- Main package artifact: `.tmp\soul_first_real_material_planning_20260708-060509\production_line_completion_map.json`
- Review packet: `.tmp\soul_first_real_material_planning_20260708-060509\no_render_review_packet.md`

This round produced a no-render soul-first planning package. It does not claim final approval, legal music approval, transcript approval, or render readiness.

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe - <precheck missing V7 upstream artifacts>
```

Exit code: `1`

Result:

```json
{
  "red_first": "v7_missing_upstream_soul_first_artifacts",
  "run": ".tmp\\graduation_v7_five_minute_production_rehearsal_20260708-051809\\run",
  "missing": [
    "story_contract.json",
    "story_shell.json",
    "director_shot_plan.json",
    "material_needs.json",
    "story_to_material_map.json",
    "material_delta.json",
    "render_facing_shot_plan.json",
    "creative_gap_strategy.json"
  ]
}
```

This proves the previous V7 route had useful engineering stop-loss evidence but lacked the upstream soul-first production line.

## Source Preflight

Artifact: `.tmp\soul_first_real_material_planning_20260708-060509\source_preflight.json`

- source root: `C:\Users\user\Downloads\微電影素材\_整理後`
- exists: true
- is_dir: true
- file_count: 306
- media_count: 198
- video_count: 88
- image_count: 110
- audio_count: 0
- old compilation risk count: 9
- source-folder music risk count: 8

Known supervisor/source speech candidates were recorded separately from old compiled videos and source-folder music.

## Story Thesis

One-sentence thesis:

> A class becomes trusted field workers by turning repeated safety discipline into shared confidence and gratitude.

Emotional spine:

- uncertainty
- pressure
- mutual support
- recognition
- gratitude
- departure with responsibility

Opener promise:

- What changed between the first gathering and the moment they are ready to carry power-work responsibility?

Closing payoff:

- Return to the opening promise: disciplined movements become people who can be trusted outside the training field.

Rejected generic structures:

- Do not simply list courses in folder order.
- Do not fill time with old compiled finals as primary footage.
- Do not use generated support as proof of training.

## Structure Summaries

Five-minute view:

- Opening story / memory-wall: 30s
- Training MV body: 175s
- Supervisor source speech: 35s
- Teacher/class intro: 30s
- Closing story/payoff: 30s
- Total target: 300s

Ten-minute view:

- Same story arc, expanded with longer training submodules and more class/support context.
- Total planned band: 540-660s, represented in `render_facing_shot_plan.json`.

Artifacts:

- `story_contract.json`
- `story_shell.json`
- `creative_concept.json`
- `screenplay_beats.json`
- `director_shot_plan.json`
- `render_facing_shot_plan.json`

## Material Understanding

Artifact: `.tmp\soul_first_real_material_planning_20260708-060509\real_material_understanding.json`

The material understanding separates:

- raw footage/photos
- old compiled videos
- source-folder music
- supervisor/source speech
- teacher/class intro
- opener/closer candidates
- training module candidates

Key source groups:

- safety/basic: `工安早會`, `工安體感`
- advanced pressure: `拖拉電纜`, `換桿`, `活線作業`
- supervisor/source speech: `主任勉勵`
- teacher/class intro: `感謝導師`, `各班團體照&導師`
- opener/closer: aerials, entry, graduation/thank-you material
- risk/reference only: old compiled videos and `66期學長音樂檔`

## Material-Driven Story Changes

Artifact: `.tmp\soul_first_real_material_planning_20260708-060509\story_material_negotiation.json`

Material changed the story in these ways:

- Start training body with safety-experience footage because source is abundant.
- Merge cable/pole/live-line as progressive pressure instead of a flat course catalog.
- Treat certification/check as thin unless raw proof is found.
- Move activity/belonging before supervisor speech so the speech becomes recognition, not an interruption.
- Use aerial/entry material as opener/closer callback, not filler.

Intentional repeat:

- Aerial opener returns in closing as callback.

Shortened beat:

- certification/check, pending better raw proof.

## Gap Decisions

Artifacts:

- `material_delta.json`
- `creative_gap_strategy.json`

Current decisions:

- covered: opener, safety/basic, advanced training, activity/belonging, teacher intro, closing
- thin: certification/check raw proof
- thin/blocking: supervisor/source speech transcript review
- blocked: optional narration / VoxCPM health-check branch before narration can be used
- generated support: allowed only for memory-wall opener/closer, chapter cards, symbolic inserts, motion graphics
- reshoot/collect: collect raw certification/check proof if ten-minute route needs that beat
- rewrite/shorten: shorten certification in five-minute route if proof stays thin

Rejected fake-completion paths:

- old compiled videos as primary raw proof
- generated support as training proof
- legal/music approval inferred from metadata
- repetition without callback, contrast, or rhythm function

## Opener / Closer / Effect / Title / Subtitle

Artifacts:

- `opening_design_brief.json`
- `closing_design_brief.json`
- `effect_intent_plan.json`
- `title_subtitle_strategy.json`

Summary:

- Opener: memory-wall/aerial/entry montage that asks the transformation question.
- Closer: callback to aerial/memory-wall language, showing responsibility and gratitude.
- Effects: proof-preserving chapter transitions and title treatments.
- Titles: brief chapter treatments with enter/hold/exit lifecycle.
- Subtitles: source speech and narration require ASR repair plus human transcript review.

## Render-Facing Shot Plan

Artifact: `.tmp\soul_first_real_material_planning_20260708-060509\render_facing_shot_plan.json`

The plan includes both:

- `five_minute`
- `ten_minute`

Each row records section, beat id, material refs, intended duration, shot function, proof/support role, repeat policy, effect/title/subtitle needs, audio role, and fallback if thin.

## Human Review Packet

Artifact: `.tmp\soul_first_real_material_planning_20260708-060509\no_render_review_packet.md`

The packet is written for story/edit review, not programmer-only inspection. It asks the human reviewer to confirm:

- emotional spine
- certification shortening strategy
- supervisor speech take/transcript route
- generated support boundaries for opener/closer

## Pipeline Readiness

Artifact: `.tmp\soul_first_real_material_planning_20260708-060509\pipeline_readiness.json`

- ready_for_render: false
- next_owner: `human_story_material_review`
- next_action: `review_no_render_packet_then_run_material_gap_completion`

Blocking gaps:

- human story/material review not approved
- human transcript review required
- certification/check raw proof thin
- optional VoxCPM branch requires lead-in health check before narration

Optional branches:

- VoxCPM health-check branch
- music legal review
- effect asset spec
- source search for certification

## Production-Line Completion Map

Artifact: `.tmp\soul_first_real_material_planning_20260708-060509\production_line_completion_map.json`

Ready nodes:

- user brief / film intent
- story soul / story contract
- material needs
- opener/closer/effect intent
- no-render human review packet

Partial nodes:

- material understanding
- story-material negotiation
- gap completion
- title/subtitle strategy
- music strategy
- render-facing shot plan

Blocked nodes:

- source speech / transcript review
- optional narration / VoxCPM health check
- next render rehearsal entry point

Missing nodes:

- none recorded

Next render rehearsal entry point:

- after human story/material review, transcript approval plan, certification gap decision, and VoxCPM lead-in repair branch.

## Commands And Exit Codes

| Command | Exit | Result |
| --- | ---: | --- |
| pinned Python V7 missing-artifact precheck | 1 | red-first missing upstream soul artifacts |
| create `.tmp\soul_first_real_material_planning_20260708-060509` | 0 | fresh output root |
| pinned Python no-render artifact generator | 0 | 22 artifacts written |
| pinned Python final artifact check | 0 | required artifacts present, no final media, UTF-8 OK |
| `git diff --check` | 0 | whitespace check passed; CRLF warnings only |

No code/tests were changed in this round, so the work-order code-change unittest path was not applicable.

## Final Artifact Check

Artifact: `.tmp\soul_first_real_material_planning_20260708-060509\final_artifact_check.json`

Key results:

- fresh_output_root_exists: true
- no_rendered_final_media: true
- required_artifacts_exist: true
- pipeline_ready_for_render: false
- production_line_completion_map_exists: true
- render_plan_has_5min: true
- render_plan_has_10min: true
- negotiation_has_material_driven_decision: true
- gap_strategy_has_required_routes: true
- existing_runs_modified: false
- UTF-8/no-corruption: true

## Deviations / Blockers

- Deviation: no code or reusable CLI was added; this was a run-local no-render planning package with an executable artifact check.
- Blocker: render readiness is intentionally false until human story/material review, human transcript review, certification/check gap decision, and optional VoxCPM health-check branch are resolved.
- Blocker: legal/music approval remains unresolved.
- No render/final media was created.
- No final human approval was written.

## Next Recommended Work

Have a human reviewer evaluate `no_render_review_packet.md` and approve or revise the soul/story-material direction. Then run a bounded material gap completion pass for certification/check proof and supervisor transcript review. Only after those are resolved should the next render rehearsal start from `render_facing_shot_plan.json`.
