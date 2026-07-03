# Work Order: Knowledge Migration, Smoke Case 2, Doc Pruning (Agent B)

Date: 2026-07-03
Parent plan: `docs/construction-guides/2026-07-03-convergence-single-pipeline-plan.md`
Context: closes Phase 3 Piece 2 (blocked on preservation), adds the
single-long-highlight smoke case, and executes Phase 5. Runs in PARALLEL
with another agent's frontend work — the collision fence below is absolute.

## Collision fence (another agent is working these files RIGHT NOW)

You must NOT touch, move, or archive ANY of:

- `dashboard/**`
- `tools/dashboard_server.py`, `tools/workbench_server.py`,
  `tools/workbench_browser_layout_smoke.mjs`, `tools/workbench_frontend_smoke.py`
- `tests/test_dashboard_server.py`
- `docs/construction-guides/dashboard/**`

If any task below seems to require touching these, record the conflict in
your report and skip that item.

## Task 1 - route.md knowledge migration + archive (closes Phase 3 Piece 2)

Background: `docs/construction-guides/work-orders/2026-07-03-phase3-skill-index.md`
Piece 2 stopped because `skills/route.md` holds knowledge preserved nowhere
else. Migrate it first, then archive.

1. Migrate, preserving semantics faithfully (Chinese text may stay Chinese;
   do not invent, weaken, or "improve" any rule):
   - The Node 14 Revision Loop / Change Request Contract (`spec_delta` /
     `build_delta` / `verify_delta`, version/rerender route, `--only-seg`,
     `state.json next_action` and dashboard-overwrite integration points)
     → new clearly-titled section in `docs/video-pipeline-operating-map.md`.
   - The two-axis layering explanation (implementation stack vs functional
     layers, `state/decision_log` as the DECISION LOG layer and the only
     VERIFY-to-route interface)
     → new clearly-titled section in `docs/canonical-video-pipeline-route.md`.
   If a target doc already covers part of it, merge into that section and
   note it; if a target doc CONTRADICTS route.md, stop that item and record
   the contradiction — do not pick a winner.
2. Then archive: `git mv skills/route.md skills/archive/route.md`; update the
   `skills/INDEX.md` row path; `git grep -n "skills/route.md"` and update
   every live reference (if `docs/branch-contract-registry.json` references
   it, stop and report — do not edit the registry).
3. Acceptance: focused `tests.test_skill_index` green; full suite green;
   `git grep -l "skills/route.md"` returns only archive self-references,
   history docs, and work orders.
   Commits: `Migrate route.md contracts into canonical route docs`,
   `Archive retired route dispatcher skill`.

## Task 2 - e2e-smoke case 2: single-long-highlight stage0 routing

Pins the gate-order fix (commit e7189cc0) at smoke level.

1. Create fixture `examples/genre_tests/single_long_highlight_e2e/` with a
   `video_intent.json` reproducing the accepted scenario: material-first
   entry, material_contract with quick-inventory-first scan decision, and a
   subtitle_voiceover_contract with `subtitle_required: true`. Derive the
   shape from the regression test added in `tests/test_pipeline_home.py`
   (test name contains `material_first_intent_with_required_subtitles`) —
   that test is the source of truth for expected values.
2. Extend `video_pipeline_core/e2e_smoke.py` with case
   `single_long_highlight` as a stage0-profile case: instead of the
   spec-review/dry-build chain, it copies the fixture into a temp run dir,
   calls `tools/pipeline_home.py`'s `summarize_run`, and passes when the
   summary cursor/next match the regression test's expected values
   (material map inventory first, NOT the subtitle repair gate). Keep the
   `stock_story` case behavior byte-identical. CLI:
   `python video_tools.py e2e-smoke --case single_long_highlight`.
3. Extend `tests/test_e2e_smoke.py` with the new case (happy assert + a
   seeded-failure variant if cheap).
4. Acceptance: both smoke cases exit 0 from CLI; focused + full suite green.
   Commit: `Add single-long-highlight stage0 case to e2e smoke`.

## Task 3 - Phase 5 doc pruning (move-only, conservative)

1. Compute the live set: every `docs/**` file reachable by path reference
   from any of these roots (transitively): `docs/START_HERE_VIDEO_PIPELINE.md`,
   `docs/INDEX.md`, `RUNBOOK.md`, `CLAUDE.md`, `docs/branch-contract-registry.json`
   `docs[]` fields, `docs/interface-contracts/**`, `skills/**`, `tests/**`,
   `video_pipeline_core/**`, `video_tools.py`, `runtime.py`, `tools/**`.
   A file referenced by ANY test or code file is live by definition.
2. Everything else under `docs/` moves (git mv, no deletion, no content
   edits) to `docs/archive/pruned-2026-07/`, EXCEPT:
   - the collision fence paths above;
   - `docs/generated/**` (machine-owned);
   - `docs/archive/**` (already archived);
   - anything you are less than certain about — when unsure, leave it and
     list it in the report as a candidate instead of moving it.
3. Acceptance: full suite green (tests that assert doc contents are the
   safety net); `docs/INDEX.md` has no links to moved files; report lists
   moved files and left-behind candidates separately.
   Commit: `Prune unreachable docs into archive`.

## General discipline

- miniconda python for all test runs.
- Full suite green before every commit; one task may span multiple commits
  but each commit is self-consistently green.
- Contradictions: record, skip, continue. No unilateral rulings.
- No debris files left at repo root when you finish.

## Evidence to hand back

Append `## Agent B Report` to this file: per-task commits, focused/full
test tails, the route.md migration destinations chosen, smoke case 2 trace
output, moved-docs list + not-moved candidates, all recorded contradictions.
