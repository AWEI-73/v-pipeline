# Docs Index — canonical map (2026-06-08)

One page that says what is current and what is historical, so old/new no longer mix.

## Start here (entry points, in order)

1. `README.md` — what this project is.
2. `roadmap.md` — canonical current roadmap and navigation index. Long history
   now lives in `docs/roadmap-history/`.
3. `HANDOFF_CURRENT.md` — clean resume anchor for the next agent.
4. `RUNBOOK.md` — how to run the pipeline on Windows.

## Editorial "soul" layer (front of pipeline)

- `docs/story-soul-blueprint-skills.md` — planned upstream creative skill layer:
  story world, narrative device, screenplay beats, director shot/material prompt
  compiler. This is the next consolidation target before more runtime features.
- Skill: `skills/story-soul-blueprint.md` — SSB1 executable baseline that
  compiles project briefs into story_world, creative_concept, screenplay_beats,
  director_shot_plan, material_needs, generation_manifest, and review checklist.
- Skill: `skills/material-generation-fallback.md` — MGF1 rescue layer that turns
  fresh `material_delta` missing/thin needs into provider-neutral generation jobs;
  generated assets return through material-map review as candidates.
- Skill: `skills/generated-material-producer.md` — executes MGF1 jobs into
  generated files, manifests, candidate material maps, quality review, and
  explicit candidate promotion review.
- Harness: `tools/generated_material_flow_acceptance.py` — replays two
  generated comic-style cases from empty material through candidate material maps
  and quality review.
- Harness: `tools/story_to_generated_material_e2e.py` — runs project brief
  through SSB1, generated fallback, generated material production, explicit
  review, and fresh delta coverage.
- `docs/editorial-layer.md` — **read first**; consolidated conceptual map.
- `docs/narrative-blueprint-spec.md` — WHY: prose thesis + ordered beats (gate).
- `docs/editing-intent-sequence-grammar-spec.md` — HOW-structure: cut/hold reasons, shot_slots.
- `docs/material-treatment-grammar-spec.md` — HOW-material: content_pattern → treatment → count → lanes.
- `docs/imagery-to-edit-lexicon-spec.md` — the deterministic 意象→enum translation table.
- Skill: `skills/blueprint-interview.md` (elicit soulful blueprint).
- Code: `video_pipeline_core/blueprint_to_contract.py` (compile decisions.json → contract);
  CLI `video_tools.py blueprint-to-contract`. Gold example: `examples/blueprint_gold_66/`.

## Build / runtime / infra (current)

- `docs/material-map-lifecycle.md` — canonical summary of the completed
  M6 material-map lifecycle: needs, satisfies edges, delta, revision, lifecycle
  stage machine, build handoff, and current boundaries.
- `docs/build-tool-runner-spec.md` — BUILD runner tool selection + P1 audit pack.
- `docs/video-autopilot-tool-integration-spec.md` — editing/VERIFY tool integration.
- `docs/capcut-pipeline-integration-design.md` — optional CapCut finishing backend.
- `docs/dashboard-node-skill-output-spec.md` — dashboard / node / output contract.
- `docs/windows-native-migration-spec.md` — Windows migration record (migration complete).
- `docs/SYSTEM-DESIGN.md` — self-contained node/skill/tool architecture brief
  (honest status grading: proven / thin / scaffold / known gaps). Share-ready.
- `docs/reference-repos-map.md` — external reference repos: what to take, license limits,
  integration triggers (ai-media-generator / NarratoAI). Do not re-evaluate; read this.
- `docs/decisions/2026-06-16-native-preview-engine.md` — Workbench preview/edit
  middle layer: material-composition preview, draft patch artifacts, contract
  sync boundary, and Dashboard/Workbench separation.
- `docs/decisions/2026-06-17-frontend-stability-and-modularization.md` --
  Workbench stabilization pass: smoke coverage, module boundary, and draft-only
  frontend responsibility.
- `docs/decisions/2026-06-17-frontend-api-contract-hardening.md` --
  Control Index / Workbench health response-shape lock for future frontend
  integration.
- `docs/decisions/2026-06-17-run-layout-manifest.md` --
  machine-readable run folder/artifact ownership manifest for agents and
  frontend shells.
- `docs/decisions/2026-06-18-material-generation-fallback.md` -- MGF1
  delta-to-generated-job bridge and generated-material honesty boundary.
- `docs/decisions/2026-06-18-generated-material-producer.md` -- GMP1
  generated-job execution into files, manifests, candidate maps, provider-output
  intake, provider packet handoff, style/character lock, and review.
- `docs/decisions/2026-06-19-story-soul-blueprint.md` -- SSB1 upstream
  creative scaffold: story world, concept, beats, shot plan, material needs, and
  review checklist.
- `docs/decisions/2026-06-19-storyboard-panel-lock.md` -- generated comic /
  picture-book panel-lock policy: stretch panel duration or generate more panels
  instead of auto-filling long narration with other accepted panels.
- `docs/decisions/2026-06-19-interactive-skill-flow.md` -- ISF1 process
  solidification: interactive brief, story soul, material map, generated
  fallback, Workbench draft, and verify/delivery handoff boundaries.
- `docs/decisions/2026-06-17-tool-surface-and-run-layout-consolidation.md` --
  video_tools command catalog, run_layout read-only frontend consumption, and
  split criteria for future backend cleanup.
- `docs/workbench-dashboard-integration.md` -- current Dashboard/Workbench
  integration contract: Dashboard is read/review, Workbench is write-limited
  draft patching, backend remains official renderer.
- `docs/repository-consolidation-map.md` -- repo-wide orientation map for
  product surfaces, backend domains, artifact ownership, test families, and safe
  consolidation order.
- `docs/material-organization-policy.md` -- material-map-first policy for
  folders, projections, Workbench material browsing, and source-file movement.
- `dashboard/README.md` -- operator-facing frontend entrypoints, safety rules,
  and local Workbench commands.

## Working conventions (read before contributing)

- `docs/decisions/2026-06-14-working-loop-and-tdd-evidence.md` — the
  Claude↔Codex loop, the TDD-green-is-the-only-evidence rule, and validator
  discipline. Shared source of truth for how work is done here.

## Decision log (append-only history)

`docs/decisions/` — one file per significant decision. Most recent:
`2026-06-19-interactive-skill-flow.md`,
`2026-06-19-storyboard-panel-lock.md`,
`2026-06-19-story-soul-blueprint.md`,
`2026-06-18-generated-material-producer.md`,
`2026-06-18-material-generation-fallback.md`,
`2026-06-17-tool-surface-and-run-layout-consolidation.md`,
`2026-06-17-run-layout-manifest.md`,
`2026-06-17-frontend-api-contract-hardening.md`,
`2026-06-17-frontend-stability-and-modularization.md`,
`2026-06-17-dashboard-workbench-integration-cleanup.md`,
`2026-06-14-working-loop-and-tdd-evidence.md`,
`2026-06-14-m6a-review-response.md`,
`2026-06-13-m5-real-render-sensory-acceptance.md`,
`2026-06-13-spec-field-census.md`.
Material-map current summary lives in `docs/material-map-lifecycle.md`; full
pre-split roadmap evidence lives in `docs/roadmap-history/2026-06-18-roadmap-pre-split.md`.

## Design notes (still referenced by skills — keep)

`design/ffmpeg-pitfalls-reference.md`, `design/skill-interface-contracts.md`,
`design/tool-verification-log.md`,
`design/video-editing-workflow-architecture-first-fallback.md`,
`design/video-editing-workflow-brainstorming-to-material-direction.md`.

## Historical (moved out, not deleted)

- `docs/roadmap-history/` — long-form roadmap history moved out of the active
  roadmap. Do not treat as current unless a current doc links to it.
- `archive/` — superseded handoffs and early design/plan notes; see `archive/README.md`.
  Do not treat as current.
