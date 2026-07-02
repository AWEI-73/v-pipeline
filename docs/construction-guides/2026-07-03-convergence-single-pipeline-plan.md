# Convergence Plan: One Pipeline, One Entry, One Instrument

Date: 2026-07-03
Status: proposed construction plan
Owner: main-pipeline
Review loop: each phase is one reviewable piece (implement -> Codex review -> fix). TDD green is the only accepted completion evidence per piece.

## Problem

The runtime layer is already converged: `runtime.py` + `state.json` + delivery
gates + 1656 tests form a closed loop. The knowledge layer is not:

- `docs/` holds 166 files; `docs/START_HERE_VIDEO_PIPELINE.md` lists 20
  required-reading items.
- `skills/` holds 28 flat files with visible overlap (`route.md` belongs to the
  retired `route.py` era; `video-workflow.md` overlaps `spec-contract.md` and
  `video-intent-planner.md`).
- Route truth is split across prose (`docs/pipeline-decision-tree.md`), data
  (`docs/branch-contract-registry.json`), and maps
  (`docs/video-pipeline-operating-map.md`) with no automated consistency check
  between them.

Result: the loop closes, but every new session pays a long onboarding path and
every doc edit risks silent drift from the code. "Slow and circuitous" is a
knowledge-layer problem, not a runtime problem.

## Reference Findings: OpenMontage

Source: `reference repo/OpenMontage-main` (agent-first video production repo).

### Adopt these patterns

1. **Tiny platform files, one contract.** Their `CLAUDE.md` is ~400 bytes and
   says only "read AGENT_GUIDE.md first". `CODEX.md`, `CURSOR.md`, `COPILOT.md`
   all point to one shared `PROJECT_CONTEXT.md` instead of duplicating content.
2. **Declarative pipeline manifest as route truth.** Each pipeline is one YAML
   file listing stages, and each stage declares: owning skill, artifacts in,
   artifacts out, tools available, checkpoint policy, review focus, success
   criteria. The decision tree lives in data; prose explains it, never
   contradicts it.
3. **Namespaced skills plus a skill index.** Skills live under
   `skills/pipelines/<pipeline>/<stage>-director.md` and `skills/meta/`, with
   `skills/INDEX.md` mapping ownership.
4. **Canonical artifacts with JSON schemas.** Every stage output is a named
   artifact validated against `schemas/artifacts/*.json`.
5. **Rule Zero stated once, up front.** "Every production request goes through
   the pipeline, no exceptions" is the first operational rule an agent reads.

### Do NOT adopt these

1. **"No Python orchestrator."** OpenMontage lets the agent drive the state
   machine from checkpoint files and instructions. Our `runtime.py` +
   `state.json` `next_action` machine is strictly stronger: deterministic,
   resumable, testable. Resumability has already saved a full E2E run here.
   Keep the Python driver; converge the docs around it.
2. **38KB monolithic agent guide.** Their `AGENT_GUIDE.md` is a per-session
   context tax. Our tiered START_HERE approach is right; it just needs pruning.
3. **Prose "HARD RULE" governance.** Their gates are paragraphs an agent must
   remember to obey. Our gates are tests and delivery-gate code. Falsifiable
   instruments beat obedience; do not convert any test-backed gate into prose.
4. **12-pipeline breadth.** Their verification per pipeline is a prose
   checklist. We stay bounded-vertical: fewer routes, each with executable
   gates.

## Target End State

- **One entry:** any video request -> `skills/video-pipeline.md` ->
  `runtime.py`. Required reading for a new agent: at most 6 documents.
- **One route truth:** `docs/branch-contract-registry.json` extended to a full
  manifest (stages, artifacts, gates, skills), enforced by an integrity test.
  Prose decision tree is audited against it, never edited independently.
- **One skill map:** namespaced `skills/` tree with an ownership index; dead
  skills retired.
- **One instrument:** a single-command golden-path smoke that proves the chain
  brief -> SPEC -> dry build -> verify -> next_action never stalls.

## Convergence Freeze Rule

Until Phase 4's instrument is green, no new branches, routes, or capability
features. Bug fixes and the phases below only.

## Phases

Order: 1 -> 2 -> 4 -> 3 -> 5. Phase 2 must land before Phase 3 because the
registry integrity test is what makes skill-file moves safe.

### Phase 1 - Entry contract slimming (docs only, ~0.5 day)

1. Restructure `docs/START_HERE_VIDEO_PIPELINE.md` into three tiers:
   - **Rule Zero** (top of file): all video requests go through
     `skills/video-pipeline.md` -> `runtime.py`; never hand-run ffmpeg or
     stitch materials directly.
   - **Route truth core** (required reading, max 6): `RUNBOOK.md`,
     `docs/pipeline-decision-tree.md`, `docs/branch-contract-registry.json`,
     `docs/interface-contracts/README.md`,
     `docs/video-pipeline-operating-map.md`, `docs/INDEX.md`.
   - **Optional helpers** (read on demand, linked via INDEX): everything else
     currently in items 1-20, including `codebase-memory-mcp-handoff.md`.
2. Shrink root platform files to pointers. `CODEX.md` is already pointer-sized
   (~0.6KB); the real target is `HANDOFF_CURRENT.md` (~11KB), which must not
   duplicate route content — it points at START_HERE plus the current handoff
   delta only. `CLAUDE.md` keeps only the skill-forcing rule and the "key
   facts" block.
3. Acceptance:
   - START_HERE required-reading count <= 6.
   - `git grep` finds no route-decision prose duplicated across root files.
4. Detailed work order: `work-orders/2026-07-03-phase1-entry-contract.md`.

### Phase 2 - Registry becomes the executable manifest (~1 day)

1. Extend each entry in `docs/branch-contract-registry.json` `branches[]` with
   a `stages[]` array, OpenMontage-manifest style:

   ```json
   {
     "stage": "spec",
     "skill": "skills/spec-contract.md",
     "artifacts_in": ["project_brief.json"],
     "artifacts_out": ["segment_contract.json"],
     "gate": "spec-review",
     "next_actions_on_pass": ["build"],
     "next_actions_on_fail": ["revise:spec"]
   }
   ```

2. Create `video_pipeline_core/next_action_vocabulary.py` exporting one frozen
   set: the canonical `next_action` vocabulary. Seed it from the literals
   `video_pipeline_core/dashboard_state.py` actually assigns (mixed style is a
   fact: kebab-case route actions like `soundtrack-arrange` and snake_case
   task actions like `fix_timeline_or_assembly`; do NOT normalize the style in
   this phase) plus the registry's `next_actions` values.
3. Add `tests/test_branch_registry_integrity.py` asserting:
   - every `skills[]` and `stages[].skill` path exists on disk;
   - every `stages[].artifacts_out` name appears in
     `docs/interface-contracts/pipeline-product-artifact-dictionary.json`;
   - every registry `next_actions` value is a member of the vocabulary set
     (containment, one direction);
   - every `next_action = "..."` literal in `dashboard_state.py` (regex scrape
     of the source) is a member of the vocabulary set;
   - every branch's `docs[]` paths exist.
   Note: containment, not bidirectional equality — dashboard_state emits many
   in-run task actions that are deliberately not registry route actions.
4. Add an audit command (`python video_tools.py registry-audit` or a
   generated report under `docs/generated/`) that diffs the prose decision
   tree's branch/gate names against the registry and fails on drift.
5. Acceptance: new tests green in `python -m unittest discover -s tests`;
   audit command exits non-zero on a deliberately seeded drift.
6. Detailed work order: `work-orders/2026-07-03-phase2-registry-manifest.md`.

### Phase 3 - Skills reorganization and retirement (~1 day)

1. Namespace the tree:
   - `skills/main/` - video-pipeline, video-pipeline-route,
     video-intent-planner, spec-contract, director, writer, curator, editor,
     verify, dashboard.
   - `skills/branches/<branch>/` - soundtrack-arranger, audio-director,
     effects-director, video-effect-factory, remotion-effect-worker,
     material-map, brownfield-edit, subtitle-director, etc., grouped by the
     `branch_id` that owns them in the registry.
   - `skills/meta/` - pipeline-boundary, gap-analyzer, blueprint-interview,
     story-soul-blueprint, shooting-brief.
2. Retire dead skills to `skills/archive/`: `route.md` (retired `route.py`
   dispatcher). Evaluate merging `video-workflow.md` into `spec-contract.md` /
   `video-intent-planner.md`; archive whichever loses.
3. Create `skills/INDEX.md`: one line per skill - owning branch, stage,
   triggering `next_action` values.
4. Update registry skill paths; the Phase 2 integrity test catches any miss.
5. Acceptance: integrity test green; `git grep -l "skills/route.md"` returns
   only archive/changelog references; CLAUDE.md skill list updated.

### Phase 4 - Golden-path convergence smoke (~1-2 days, can start after Phase 2)

1. One command, no network, no render:

   ```
   python video_tools.py e2e-smoke --case stock_story
   ```

   Chain: fixture brief -> spec-review -> contract-dry-build -> simulated
   verify -> assert `state.json` reaches a terminal `next_action` without
   stalling. Reuse the existing fixture at
   `examples/genre_tests/stock_story_e2e/` (brief.json, blueprint.json,
   segment_contract.json, material_categories.json).
2. Fold in the known chain defects so the smoke pins them:
   - `target_length` must be enforced (currently unenforced end to end);
   - render output landing outside the canonical artifact path must not stall
     `next_action`;
   - `revise:director` dead-end must route through the supply-revision path.
3. Wire it as a standard unittest (marked slow if needed) so the 1656-test
   baseline includes the chain, not only the units.
4. Acceptance: command exits 0 from a clean checkout; deliberately breaking
   any one node in the chain makes it exit non-zero with the stalled
   `next_action` named.

### Phase 5 - Doc pruning (~0.5 day, then continuous)

1. Any `docs/` file not reachable from START_HERE core, INDEX layers, or the
   registry `docs[]` fields moves to `docs/archive/` (keep history, drop from
   the live map).
2. INDEX "Current document layers" table may only reference living documents;
   add this check to the registry audit if cheap.
3. Acceptance: INDEX table has no dead or archived links; live doc count
   trending down, not up.

## Risks

- **Skill moves break hidden references.** `next_action` strings, tests, or
  state files may embed old skill paths. Mitigation: Phase 2's integrity test
  lands first; move files with `git mv` and run the full suite per move batch.
- **Registry schema creep.** Keep `stages[]` minimal (the seven fields above);
  richer per-stage guidance belongs in the skill file, not the manifest.
- **Prose/data double maintenance during transition.** Until the audit exists,
  freeze edits to `docs/pipeline-decision-tree.md` except through this plan.

## Out of Scope

- New render backends, new branches, CapCut automation changes.
- Rewriting any delivery-gate logic; this plan only maps and enforces what
  exists.
