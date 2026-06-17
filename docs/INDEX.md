# Docs Index — canonical map (2026-06-08)

One page that says what is current and what is historical, so old/new no longer mix.

## Start here (entry points, in order)

1. `README.md` — what this project is.
2. `roadmap.md` — canonical long-term roadmap (current direction at top, history below).
3. `HANDOFF_CURRENT.md` — clean resume anchor for the next agent.
4. `RUNBOOK.md` — how to run the pipeline on Windows.

## Editorial "soul" layer (front of pipeline)

- `docs/editorial-layer.md` — **read first**; consolidated conceptual map.
- `docs/narrative-blueprint-spec.md` — WHY: prose thesis + ordered beats (gate).
- `docs/editing-intent-sequence-grammar-spec.md` — HOW-structure: cut/hold reasons, shot_slots.
- `docs/material-treatment-grammar-spec.md` — HOW-material: content_pattern → treatment → count → lanes.
- `docs/imagery-to-edit-lexicon-spec.md` — the deterministic 意象→enum translation table.
- Skill: `skills/blueprint-interview.md` (elicit soulful blueprint).
- Code: `video_pipeline_core/blueprint_to_contract.py` (compile decisions.json → contract);
  CLI `video_tools.py blueprint-to-contract`. Gold example: `examples/blueprint_gold_66/`.

## Build / runtime / infra (current)

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
`2026-06-17-run-layout-manifest.md`,
`2026-06-17-frontend-api-contract-hardening.md`,
`2026-06-17-frontend-stability-and-modularization.md`,
`2026-06-17-dashboard-workbench-integration-cleanup.md`,
`2026-06-14-working-loop-and-tdd-evidence.md`,
`2026-06-14-m6a-review-response.md`,
`2026-06-13-m5-real-render-sensory-acceptance.md`,
`2026-06-13-spec-field-census.md`.
Material Phase (M0-M6a) lives in `roadmap.md` top section + these decision files.

## Design notes (still referenced by skills — keep)

`design/ffmpeg-pitfalls-reference.md`, `design/skill-interface-contracts.md`,
`design/tool-verification-log.md`,
`design/video-editing-workflow-architecture-first-fallback.md`,
`design/video-editing-workflow-brainstorming-to-material-direction.md`.

## Historical (moved out, not deleted)

`archive/` — superseded handoffs and early design/plan notes; see `archive/README.md`.
Do not treat as current.
