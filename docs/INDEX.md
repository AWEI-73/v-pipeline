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

## Working conventions (read before contributing)

- `docs/decisions/2026-06-14-working-loop-and-tdd-evidence.md` — the
  Claude↔Codex loop, the TDD-green-is-the-only-evidence rule, and validator
  discipline. Shared source of truth for how work is done here.

## Decision log (append-only history)

`docs/decisions/` — one file per significant decision. Most recent:
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
