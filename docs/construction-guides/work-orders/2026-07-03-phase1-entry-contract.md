# Work Order: Phase 1 - Entry Contract Slimming

Date: 2026-07-03
Parent plan: `docs/construction-guides/2026-07-03-convergence-single-pipeline-plan.md`
Scope: documentation files only. No Python, no tests, no skills files.
Estimated effort: 0.5 day.

## Files you may modify

- `docs/START_HERE_VIDEO_PIPELINE.md`
- `HANDOFF_CURRENT.md`
- `CLAUDE.md`
- `docs/INDEX.md` (only if a moved item needs a new index row)

## Files you must NOT modify

Everything else. In particular: `runtime.py`, `video_tools.py`,
`video_pipeline_core/`, `skills/`, `tests/`, `RUNBOOK.md`,
`docs/pipeline-decision-tree.md`, `docs/branch-contract-registry.json`,
`CODEX.md` (already pointer-sized at ~0.6KB — leave as is unless it duplicates
route prose, in which case delete only the duplicated lines).

## Task 1 - Restructure START_HERE Read Order into three tiers

Replace the current flat 20-item "Read Order" section with:

### Tier 0 - Rule Zero (new, at the very top of the file, before Read Order)

A short section stating, in this order:

1. Every video production request enters through `skills/video-pipeline.md`,
   which drives `runtime.py` (resume / status / rerun) and the
   `state.json.next_action` state machine.
2. Never hand-run ffmpeg, `video_tools.py` subcommands, or manual material
   stitching as a substitute for the pipeline.
3. Existing run state wins: inspect the run folder before writing.

Keep it under 15 lines. Do not restate branch details here.

### Tier 1 - Required reading (exactly these 6, this order)

1. `docs/START_HERE_VIDEO_PIPELINE.md` (this file)
2. `RUNBOOK.md`
3. `docs/pipeline-decision-tree.md`
4. `docs/video-pipeline-operating-map.md`
5. `docs/branch-contract-registry.json` (note: currently missing from the
   list entirely — add it with a one-line description: machine-readable
   branch ownership contracts; route truth alongside the decision tree)
6. `docs/interface-contracts/README.md`

### Tier 2 - Read on demand (one line each, grouped by topic)

Move the remaining current items here, grouped:

- **Route detail:** `docs/video-pipeline-end-to-end-line.md`,
  `docs/canonical-video-pipeline-route.md`, `docs/upstream-story-route.md`
- **Branch routes:** `docs/material-map-lifecycle.md`,
  `docs/effect-factory-route.md`, `docs/soundtrack-arranger-route.md`,
  `docs/stage-boundary-matrix.md`
- **Review/gates:** `docs/artifact-reviewer-map.md`,
  `docs/build-capability-alignment.md`, `docs/api-surface-map.md`
- **Multi-agent:** `docs/route-orchestrator-harness.md`,
  `docs/route-agent-runner-protocol.md`
- **Construction:** `docs/construction-guides/stage0-10-route-alignment-plan.md`
- **Helpers:** `docs/codebase-memory-mcp-handoff.md` (optional, not route truth)
- **Index:** `docs/INDEX.md`

Do not delete any descriptions; compress them to one line each.

## Task 2 - Slim HANDOFF_CURRENT.md (~11KB today)

Reduce to at most ~2KB:

1. First line: pointer to `docs/START_HERE_VIDEO_PIPELINE.md` as the entry
   contract.
2. Keep only: current work-in-flight summary, open blockers, and the next
   pending action. Everything that describes stable route/architecture must
   be deleted, not moved — it already lives in the Tier 1 docs. If you find a
   fact in HANDOFF_CURRENT.md that exists nowhere else, move it to the one
   correct Tier 1/Tier 2 doc and cite that doc from the handoff.

## Task 3 - CLAUDE.md check

Keep only: the skill-forcing rule block and the key-facts block (both already
exist). Delete any line that restates content now covered by Tier 0/Tier 1.
If nothing qualifies, make no change.

## Acceptance (all must pass)

1. Tier 1 list in START_HERE has exactly 6 items.
2. `docs/branch-contract-registry.json` appears in Tier 1.
3. Every path referenced in the new Read Order exists:
   spot-check with `git ls-files <path>`.
4. `(Get-Item HANDOFF_CURRENT.md).Length` <= 2500 bytes.
5. No content deleted from Tier 2 docs themselves — this order only touches
   the four files listed above.
6. `python -m unittest discover -s tests` still green (docs-only change; run
   it anyway to prove nothing imports these files).

## Evidence to hand back

- Diff of the four files.
- Test-run tail showing OK count.
