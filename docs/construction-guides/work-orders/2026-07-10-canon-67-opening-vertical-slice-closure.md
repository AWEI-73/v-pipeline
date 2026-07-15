# Canon 67 Opening Vertical Slice Closure

Status: READY FOR TERRA

## Goal And Decision

Close the prior Canon 67 opening-slice construction as a reproducible technical
baseline. This closure is valuable only as a fixed control for later comparison
with the evidence-carrying editing-loop Skill. It is not authorization to extend
the old route, improve its taste, or make it the new editing front door.

Context sources:

- `docs/construction-guides/work-orders/2026-07-10-canon-67-opening-vertical-slice.md`
- `docs/construction-guides/work-orders/2026-07-10-canon-67-opening-vertical-slice-report.md`
- commits `fdbe086f`, `2545b07d`, `c6f1a317`, and `a7d0bb33`
- the current working-tree residuals in the owner zone below

The starting evidence is intentionally red:

- `render_handoff.json` is absent from the product artifact dictionary;
- `tools/run_graduation_opening_slice.py` and
  `tools/verify_beat_cut_alignment.py` are unowned by Skill Tool Contracts;
- the prior full suite reported 2599 tests with those two failures.

The candidate remains a technical control:
`human_creative_approval=false` and `final_delivery_claimed=false`.

## Owner Zone

TERRA may edit only these paths:

- `docs/interface-contracts/pipeline-product-artifact-dictionary.json`
- `skills/video-pipeline-route.md`
- `skills/verify.md`
- `video_pipeline_core/edit_decision_plan.py`
- `video_pipeline_core/edit_decision_renderer.py`
- `video_pipeline_core/graduation_opening_slice.py`
- `tests/test_compile_edit_decision_plan.py`
- `tests/test_edit_decision_renderer.py`
- `tests/test_graduation_opening_slice.py`
- `tools/run_graduation_opening_slice.py`
- `docs/construction-guides/work-orders/2026-07-10-canon-67-opening-vertical-slice-closure-report.md`
- `.tmp/canon_67_opening_slice_closure/**` (fresh outputs only)

`tools/verify_beat_cut_alignment.py` is read-only implementation evidence in
this closure. Its ownership is declared by editing `skills/verify.md`.

Use exact pathspecs when staging. Never use `git add -A` or stage unrelated
working-tree changes.

## Forbidden Zone

Read-only even if it appears relevant:

- `AGENTS.md`, `RUNBOOK.md`, `video_tools.py`
- `skills/INDEX.md`
- `skills/editing-loop-director.md`
- `docs/pilots/**`, `docs/decisions/**`
- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
- `docs/construction-guides/2026-07-10-canon-67th-film-gap-table.md`
- `r`, `supply_review.json`
- every pre-existing `.tmp/**` run
- `C:\Users\user\Downloads\微電影素材\_整理後\**`
- all paths not named in the Owner Zone

Do not delete or clean unrelated files, amend existing commits, push, open a
PR, promote a delivery, run f1, reveal any evaluator-side f1 expected answer,
or build a helper/driver/orchestrator in this closure.

## Required Pieces

### Piece 1 - Capture The Known Red Baseline

Before editing contracts, run the two focused tests below and record their exit
codes and failure excerpts in the closure report. Expected starting state is
FAIL for exactly the three known missing registrations named above. If the red
shape differs, stop before editing and report the contradiction.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_registry_integrity.BranchRegistryIntegrityTest.test_stage_artifacts_in_dictionary -v
C:\Users\user\miniconda3\python.exe -m unittest tests.test_skill_tool_contracts.SkillToolContractsTest.test_audit_reports_clean_skill_tool_contracts -v
```

### Piece 2 - Close Artifact And Tool Ownership Contracts

Make the smallest contract-only repair:

1. Add `render_handoff.json` to the product artifact dictionary with
   `owner_branch=main-pipeline`. Its purpose must say that it is a render-ready
   composition handoff, not delivery approval. Its parameters must expose
   readiness/owner state, timeline or source refs, output settings, and the
   `final_delivery_claimed` boundary. Its consumers must include the bounded
   renderer and downstream verification/review.
2. Register `tools/run_graduation_opening_slice.py` as a **supporting tool** in
   `skills/video-pipeline-route.md`. Describe it as a legacy Canon 67 0-44
   technical acceptance/control replay, not the editing-loop front door.
3. Register `tools/verify_beat_cut_alignment.py` as a **supporting tool** in
   `skills/verify.md`. It objectively verifies intended cut boundaries against
   the declared beat grid; it does not judge montage taste.

Do not add a route, next-action vocabulary, INDEX row, new artifact type, or
new ownership layer.

Commit only the three contract files:
`Close opening slice ownership contracts`.

### Piece 3 - Finish The Existing Uncommitted Slice, Without Redesign

Audit the current residual diff before touching it. Preserve the already-built
architecture and make only repairs required by focused acceptance:

- carry opening `settings` into `edit_decision_plan.json`;
- enforce final rendered duration within one frame at 30 fps;
- keep `human_creative_approval=false` and
  `final_delivery_claimed=false`;
- keep the product-specific runner bounded to technical acceptance.

The files `video_pipeline_core/graduation_opening_slice.py`,
`tests/test_graduation_opening_slice.py`, and
`tools/run_graduation_opening_slice.py` currently exist as untracked prior-work
residuals. Review them; do not regenerate them from scratch merely because they
are untracked. Do not alter selection taste, title/poem copy, timing design,
or the old route architecture.

After focused acceptance passes, commit only the owner-zone code/test/runner
files needed to preserve the vertical slice:
`Close reproducible Canon 67 opening slice`.

### Piece 4 - Reproduce The Fixed Technical Control

Render into the fresh closure output root. Do not overwrite the earlier
acceptance run.

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_opening_slice.py --seed-run .tmp\real_graduation_render_handoff_construction_20260709-005405\run --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --request examples\graduation_opening_slice_request.json --out .tmp\canon_67_opening_slice_closure --json
```

This remains a technical PASS only. A visually weak but technically conforming
candidate is valid control evidence and must not be "improved" in this closure.

### Piece 5 - Write The Closure Report

Write the owner-zone closure report. Do not modify the original report or this
work order. The report must distinguish technical PASS from creative UNKNOWN.
Commit it separately as `Report Canon 67 opening slice closure` only after all
required acceptance commands pass.

## Acceptance Commands

Run from `C:\Users\user\Desktop\video_pipeline` with the pinned Python.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_branch_registry_integrity.BranchRegistryIntegrityTest.test_stage_artifacts_in_dictionary tests.test_skill_tool_contracts.SkillToolContractsTest.test_audit_reports_clean_skill_tool_contracts -v
```

Expected exit code: `0`.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_beat_cut_composer tests.test_edit_decision_renderer tests.test_graduation_opening_slice tests.test_compile_edit_decision_plan tests.test_edit_artifacts tests.test_opening_sequence tests.test_motion_graphics tests.test_graduation_product_route_runner tests.test_graduation_route_registry_consistency -v
```

Expected exit code: `0`.

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py registry-audit --json
C:\Users\user\miniconda3\python.exe video_tools.py interface-audit
C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --json
```

Expected exit code: `0` for each command; the skill audit has no unowned tools.

```powershell
C:\Users\user\miniconda3\python.exe tools\verify_beat_cut_alignment.py --timeline .tmp\canon_67_opening_slice_closure\run\timeline_build.json --beats .tmp\canon_67_opening_slice_closure\run\soundtrack_probe_report.json --window-start 18 --window-end 44 --fps 30 --out .tmp\canon_67_opening_slice_closure\beat_cut_alignment_report.json --json
ffprobe -v error -show_entries format=duration -show_entries stream=codec_type,codec_name,width,height -of json .tmp\canon_67_opening_slice_closure\run\final.mp4
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run .tmp\canon_67_opening_slice_closure\run --out-dir .tmp\canon_67_opening_slice_closure\rendered_qa --json
C:\Users\user\miniconda3\python.exe video_tools.py asset-path-audit .tmp\canon_67_opening_slice_closure\run --strict --json
```

Expected exit code: `0` for each command. Evidence must show video and audio,
duration within one frame of 44 seconds, `within_one_frame_ratio=1.0`, rendered
QA pass, at least 15 distinct montage assets, no reference-film footage,
`human_creative_approval=false`, and `final_delivery_claimed=false`.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests
git diff --check
```

Expected exit code: `0` for each command. Full-suite success closes the previous
Stop-Loss; do not substitute a focused suite for this final gate.

## Stop-Loss

- One repair attempt per failure class. On recurrence, classify LOCAL or
  STRUCTURAL and stop at the last green commit.
- Stop if any required fix is outside the Owner Zone or changes public route,
  Skill-loop behavior, product taste, selection decisions, dependencies,
  schemas beyond the one dictionary entry, or delivery state.
- Stop if the two red-first failures have a different starting shape.
- Stop on any new full-suite failure outside the touched closure scope; report
  it rather than changing another owner's files.
- Preserve unrelated dirty-tree changes exactly. Their presence is not a
  closure failure and must not be "cleaned".

## Delegated Decisions

TERRA may decide JSON insertion position, test fixture details, and whether an
existing residual requires a local formatting repair. TERRA may not decide to
redesign the slice, reassign owners differently, remove old surfaces, claim
creative approval, or proceed into helper/f1 work.

## Report Evidence Required

Start with `[WORKER REPORT - REVIEW MODE]` and include:

- commits and exact files in each commit;
- red-first commands, exit codes, and failure excerpts;
- every acceptance command, exit code, and final tail line;
- output root and required artifact paths;
- ffprobe duration/stream evidence, beat ratio, montage distinct count, and
  rendered QA status;
- confirmation that the reference film was not used as footage;
- `human_creative_approval` and `final_delivery_claimed` values;
- exact final `git status --short`, separating pre-existing unrelated changes;
- deviations, skips, blockers, and the literal words `No deviations` when true;
- final classification: technical baseline CLOSED or NOT CLOSED; creative
  quality remains UNKNOWN unless the human owner separately approves it.

