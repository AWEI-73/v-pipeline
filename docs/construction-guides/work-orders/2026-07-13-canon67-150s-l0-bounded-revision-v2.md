# Work Order: Canon 67 150-Second L0 Bounded Revision v2

Date: 2026-07-13
Owner: integrator / main-pipeline
Worker: one fresh Luna session, single writer
Target state: `WAITING_INTEGRATOR_150S_L0_V2_REVIEW`

## Goal

Resolve only the three open findings in the integrator verdict for the existing
150-second L0 picture proposal. Preserve the complete v1 packet as immutable
evidence. Produce a sibling v2 proposal; do not enter L1 or render video.

Read in order:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `HANDOFF_CURRENT.md`
4. `docs/superpowers/specs/2026-07-13-canon67-150s-picture-first-longform-design.md`
5. `docs/superpowers/plans/2026-07-13-canon67-150s-picture-first-l0-plan.md`
6. `.tmp/canon67_150s_picture_first_longform/l0/review/integrator_verdict.json`
7. this work order and its execution companion
8. the L0/L1 portions of `skills/editing-loop-director.md` and relevant
   capability/SOP portions of `skills/material-map.md`

The integrator verdict controls the revision. It authorizes no production-code,
schema, Skill, registry, renderer, audio, subtitle, effect, or L1 change.

## Execution Shape And Boundaries

- Work in `C:/Users/user/Desktop/video_pipeline`; one writer, no subagents or
  worktree.
- Treat `.tmp/canon67_150s_picture_first_longform/l0/**` as frozen read-only v1.
- Write current-run artifacts only under
  `.tmp/canon67_150s_picture_first_longform/l0_revision_v2/**`, plus the final
  machine-state update in `campaign_status.json` and `HANDOFF_CURRENT.md`.
- Use the committed execution companion and public `capability-run` entry.
- Reuse the v1 inventory, 79-item candidate pool, source hashes, matrices,
  contact sheets, and evidence for unchanged selections by exact hash.
- Do not rescan or semantically rereview all 306 files. The accountable
  inventory step is only a mechanical current-source read-back.
- For a replacement or changed video window, personally inspect new
  multi-timepoint evidence. For a replacement still, inspect real pixels.
- Do not stage, reset, stash, rebase, amend, push, upload, or clean user files.

## Required Revision

Resolve all three findings without broadening scope:

1. **Orientation:** replace `asset-4af29a43745b0750`, or record an existing
   public orientation-normalization treatment. Prefer replacement at L0.
2. **Identity:** retain source-hash-derived `asset_id`, and add a deterministic
   `clip_id` used as sequence identity. Video `clip_id` binds source SHA-256 and
   canonical in/out milliseconds; still `clip_id` binds source SHA-256 and
   planned-duration milliseconds. Audit existing helpers first. If no helper
   exists, record the deterministic formula in v2 rather than adding a new
   production tool.
3. **Sequential diversity:** reorder and, only when necessary, replace selected
   material so no more than two consecutive selections share one source
   category or reviewed visual family. More than three selections from one
   category inside a section requires an explicit intentional-motif rationale.
   In particular, break the covered-court pair, the cable-dragging block, the
   pole-replacement block, the three-tower ending, and the birthday opening.

Keep exactly the three existing sections, each 45-55 seconds, total
`150.0 +/- 0.5` seconds, and 40-60 distinct clip IDs. Do not hide weak picture
selection with effects, generated assets, text, audio, or transitions.

## Accountability Commands

Initialize exactly once:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --initialize --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l0-bounded-revision-v2.execution.json --json
```

Execute exactly once:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py capability-run --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l0-bounded-revision-v2.execution.json --step-id L0R.revalidate-pool-inventory --json
```

Require a PASS receipt. Do not copy or fabricate a v1 receipt. Write the
run-bound agent attestation required by the companion only after reviewing the
final v2 evidence and semantic diff.

Run strict closure:

```powershell
C:/Users/user/miniconda3/python.exe tools/no_skip_execution_trace.py --run .tmp/canon67_150s_picture_first_longform/l0_revision_v2 --contract docs/construction-guides/work-orders/2026-07-13-canon67-150s-l0-bounded-revision-v2.execution.json --out-dir .tmp/canon67_150s_picture_first_longform/l0_revision_v2/final/strict_closure --json
```

## Required Artifacts

Write at minimum:

- `proposal/l0_selects_proposal_v2.json`;
- `proposal/semantic_diff_v1_to_v2.json`;
- `proposal/sequence_summary_v2.md`;
- `proposal/coverage_summary_v2.json`;
- `perception/review_access_ledger_v2.json` distinguishing reused and fresh
  evidence by exact path/hash;
- `review/owner_review_index_v2.md` with sequence, category, visual-family,
  duration, v1/v2 change reason, and evidence links;
- `review/integrator_verdict_template_v2.json` with unset decision;
- `accountability/attestations/L0R.selection-revision-review.json`;
- `final/worker_report.md` and `final/command_log.json`.

The semantic diff must prove v1 bytes/hashes stayed unchanged and identify each
reorder, replacement, changed window, and new `clip_id`. It must also report
the longest consecutive category run, longest reviewed visual-family run, and
per-section category counts.

## Validation

Run the same 54 focused tests from the v1 plan, plus:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_doc_reference_hygiene -v
```

Also run `video_tools.py registry-audit --json`, strict closure, UTF-8/JSON/path
and source-hash read-back, frozen v1 hash read-back, and `git diff --check`.
Do not run the full suite; no production code changes are authorized.

## Stop-Loss

Stop at the last valid state if a protected v1 hash drifts; a production/public
interface change is required; accountability initialization or execution is
nonzero; a replacement cannot be truthfully reviewed; the same failure class
recurs after one LOCAL correction; or focused/strict validation stays nonzero.
Do not repair symptoms after a STRUCTURAL classification and do not create an
unaccountable sibling run.

## Final State

On success, update the campaign pointer and Handoff to
`WAITING_INTEGRATOR_150S_L0_V2_REVIEW`. Keep
`human_creative_approval=false` and `final_delivery_claimed=false`. The worker
must not authorize L1; the integrator independently decides whether v2 is ready.
