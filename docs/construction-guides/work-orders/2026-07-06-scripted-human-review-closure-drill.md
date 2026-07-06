# Work Order: Scripted Human Review Closure Drill

Date: 2026-07-06

## Goal

Run an end-to-end closure drill for the scripted story delivery path after the
human story review decision gate landed on `master`.

The visible capability to prove: a scripted technical candidate that contains
agent-filled story-to-material choices must stay at `WAITING /
human_story_review` until a human review decision exists; a human approval must
move it to `DONE`, while `revision_requested` and `rejected` must route to
repair.

This is a drill of the existing pipeline behavior, not a new gate design round.

## Owner Zone

- New output directory under `.tmp/`
- `docs/construction-guides/work-orders/2026-07-06-scripted-human-review-closure-drill-report.md`

## Forbidden Zone

- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs, except read-only inspection and copying lightweight
  JSON/media evidence into the new output directory
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Source Candidate

Prefer this read-only source run if it still exists:

`.tmp/scripted_real_material_production_run_20260706-131200/run`

If it no longer contains enough artifacts because old heavy run-local assets
were cleaned, do not recreate a full render. Build lightweight closure fixtures
inside your new output directory from the surviving `delivery_gate.json`,
`story_contract.json`, `story_to_material_map.json`, `final.mp4`, and any other
small evidence needed to exercise `pipeline_home.py`.

## Ordered Pieces

1. Preflight the source candidate.
   - Record whether `final.mp4`, `delivery_gate.json`, `story_contract.json`,
     `story_to_material_map.json`, and `story_human_review_decision.json` exist.
   - Confirm the no-decision source state with `tools/pipeline_home.py --json`.

2. Build three new drill cases under the new output directory:
   - `approved/run`
   - `revision_requested/run`
   - `rejected/run`

3. For each case, create or copy only the minimal run artifacts needed for
   `pipeline_home.py` and `write_delivery_gate_report.py` to evaluate the
   delivery state.

4. Add `story_human_review_decision.json` for each case:
   - `approved`: `decision=approved`, `reviewer=human`, and
     `approved_beat_ids` covering every required story beat.
   - `revision_requested`: `decision=revision_requested`,
     `reviewer_type=human`, and concrete revision notes.
   - `rejected`: `decision=rejected`, `reviewer=human`, and rejected beat
     evidence or notes.

5. Run `pipeline_home.py --json` for all four states:
   - source/no decision
   - approved
   - revision_requested
   - rejected

6. Run `write_delivery_gate_report.py --json` for the three drill cases and
   record whether the gate passes, blocks, or warns.

7. Write the final report.

## Acceptance Commands

Run and report exit codes for:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<source-run>" --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<out-root>\approved\run" --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<out-root>\revision_requested\run" --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<out-root>\rejected\run" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<out-root>\approved\run" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<out-root>\revision_requested\run" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<out-root>\rejected\run" --json
```

Also run a final artifact check that prints:

- output root
- missing required drill files
- source state
- approved state
- revision_requested state
- rejected state

Expected results:

- Source/no decision: `WAITING / human_story_review`
- Approved: `DONE / complete`
- Revision requested: `REPAIR / human_story_review`, next
  `revise_story_material_mapping`
- Rejected: `REPAIR / human_story_review`, next
  `repair_rejected_story_material_mapping`

## Stop-Loss

Stop and report without patching code if:

- The expected states fail.
- The source run is missing enough artifacts and no lightweight fixture can be
  built from surviving small evidence.
- Any command requires changing code, tests, tools, environment, provider
  runtime, or source media.
- Any path would require writing into Downloads or an existing `.tmp` run.

## Delegated Decisions

- Choose the new output root name under `.tmp/`.
- Choose whether to copy `final.mp4` into each drill case or use minimal fake
  media only if the existing gate artifact makes that sufficient for the
  specific command being exercised.
- Choose the exact revision/rejection notes, as long as they are concrete and
  recorded.
- Choose additional read-only inspection commands needed to explain failures.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-scripted-human-review-closure-drill-report.md`

The report must include:

- Output root and per-case run paths
- Source candidate preflight table
- Commands and exit codes
- `pipeline_home` state for all four states
- Delivery gate result for the three decision cases
- Whether `story_human_review_decision.json` was consumed
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this drill

