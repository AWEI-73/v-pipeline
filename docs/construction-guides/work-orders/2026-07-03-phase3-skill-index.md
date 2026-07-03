# Work Order: Phase 3 - Skill Index and Ownership Closure

Date: 2026-07-03
Parent plan: `docs/construction-guides/2026-07-03-convergence-single-pipeline-plan.md`
Prerequisite: Phase 2.5 merged.
Estimated effort: 0.5 day, two pieces, sequential.
Note: this order supersedes the plan's original "namespace the tree" idea.
Do NOT move any skill file except `route.md`. No content edits to any skill.

## Files you may create

- `skills/INDEX.md`
- `skills/archive/` (directory, for route.md only)
- `tests/test_skill_index.py`

## Files you may modify

- `skills/route.md` (move only, via `git mv`, in Piece 2)
- Any file whose only change is updating a `skills/route.md` path reference

## Files you must NOT modify

- Every other `skills/*.md` — no renames, no moves, no content edits.
- `docs/branch-contract-registry.json` (Phase 2.5 owns it).

## Piece 1 - INDEX + closure test

1. Create `skills/INDEX.md`: a table with one row per `skills/*.md` file.
   Columns: `skill path | owner | segment | role (one line)`.
   Owner source, in priority order:
   - the registry branch whose `skills[]` or `stages[].skill` claims it
     (14 skills are claimed today; `audio-director.md` is claimed by both
     `soundtrack-arranger` and `subtitle-voiceover` — list both);
   - for the 14 unclaimed skills, use exactly this assignment:

   | skill | owner | segment |
   |---|---|---|
   | video-pipeline.md | main-pipeline | entry orchestrator |
   | video-workflow.md | main-pipeline | stage0 / node 0 |
   | spec-contract.md | main-pipeline | contract compile |
   | director.md | main-pipeline | production SPEC |
   | writer.md | main-pipeline | text layer |
   | editor.md | main-pipeline | build/edit |
   | blueprint-interview.md | main-pipeline | upstream story |
   | story-soul-blueprint.md | main-pipeline | upstream story |
   | gap-analyzer.md | main-pipeline | upstream story |
   | shooting-brief.md | main-pipeline | upstream story |
   | effects-director.md | effect-factory | effect direction |
   | generative-director.md | material-map | generated provider |
   | pipeline-boundary.md | shared | boundary charter (all skills) |
   | route.md | archive | retired route.py dispatcher |

2. Record one "known tension" line at the bottom of INDEX.md:
   `video-workflow.md` and `video-intent-planner.md` overlap at Stage 0;
   merge evaluation deferred.
3. Create `tests/test_skill_index.py`:
   - every `skills/*.md` file (excluding `skills/archive/`) has exactly one
     INDEX row, and every INDEX row points at an existing file;
   - every skill claimed by the registry appears in INDEX with the same
     owner branch;
   - INDEX owners are limited to the 7 registry branch_ids plus `shared`
     and `archive`.
4. Acceptance: focused test green; full suite green.
   Commit: `Add skill ownership index and closure test`.

## Piece 2 - Archive route.md

1. Before moving, verify preservation of route.md's unique content:
   - the Node 14 revision-loop / change-request contract
     (`spec_delta` / `build_delta` / `verify_delta`);
   - the two-axis layering explanation (implementation stack vs
     functional layers).
   Search the live docs (`docs/pipeline-decision-tree.md`,
   `docs/video-pipeline-operating-map.md`, `docs/canonical-video-pipeline-route.md`,
   `skills/video-pipeline-route.md`) for equivalent coverage. If either
   contract exists nowhere else, STOP this piece, record the gap in the
   execution report, and leave route.md in place — do not copy content
   yourself.
2. If preserved: `git mv skills/route.md skills/archive/route.md`, then
   `git grep -n "skills/route.md"` and update every live reference (tests,
   docs, skills, registry is off-limits — if the registry references it,
   stop and report). Update the INDEX row's path.
3. Acceptance: `git grep -l "skills/route.md"` returns only
   `skills/archive/` self-references, changelog-style history docs, and this
   work order; focused + full suite green.
   Commit: `Archive retired route dispatcher skill`.

## Evidence to hand back

- Diff per piece.
- Focused and full-suite tails.
- Execution report appended under `## Phase 3`, including the Piece 2
  preservation check result (found where / not found).
