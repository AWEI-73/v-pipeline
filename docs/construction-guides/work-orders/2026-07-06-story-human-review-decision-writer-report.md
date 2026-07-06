# Story Human Review Decision Writer Report

Date: 2026-07-06

## Files changed

- `tools/write_story_human_review_decision.py`
- `tests/test_write_story_human_review_decision.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-06-story-human-review-decision-writer-report.md`

No `video_pipeline_core/`, provider/runtime, render, media, VoxCPM, music, subtitle branch, `.env`, `.venv_voxcpm`, reference repo, Downloads, or existing `.tmp` run files were modified.

## CLI examples

Approved:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_story_human_review_decision.py --run RUN_DIR --decision approved --reviewer human --approve-all --json
```

Revision requested:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_story_human_review_decision.py --run RUN_DIR --decision revision_requested --reviewer human --note "Revise inferred training-process beat before delivery." --json
```

Rejected:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_story_human_review_decision.py --run RUN_DIR --decision rejected --reviewer human --rejected-beat-id training_process_detail --note "Human reviewer rejected the inferred training sequence." --json
```

## Red-first evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision
```

Exit code: 1.

Expected red failure:

`can't open file 'C:\Users\user\Desktop\video_pipeline\tools\write_story_human_review_decision.py': [Errno 2] No such file or directory`

The failing tests covered:

- approved all beats should write the artifact and make `pipeline_home` return `DONE / complete`
- partial approval must fail without writing an artifact
- non-human reviewer must fail closed
- revision_requested requires notes and routes to `REPAIR / human_story_review`
- rejected requires notes or rejected beat evidence and routes to `REPAIR / human_story_review`
- UTF-8 artifact contains no replacement character or repeated question-mark placeholder

## Acceptance

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision
```

Exit code: 0.

Tail:

`Ran 6 tests in 1.222s`

`OK`

Integrator follow-up before commit:

- Added run-local validation for `--out-name`; path-like or absolute values now
  fail closed and do not write outside the run directory.
- Added `test_out_name_must_stay_run_local`.
- Re-ran `C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision`: exit code 0, `Ran 7 tests`, `OK`.
- Re-ran `C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision tests.test_delivery_gate tests.test_pipeline_home`: exit code 0, `Ran 152 tests`, `OK`.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_write_story_human_review_decision tests.test_delivery_gate tests.test_pipeline_home
```

Exit code: 0.

Tail:

`Ran 151 tests in 12.778s`

`OK`

```powershell
C:\Users\user\miniconda3\python.exe tools\write_story_human_review_decision.py --help
```

Exit code: 0.

Help showed `--run`, `--decision {approved,revision_requested,rejected}`, `--reviewer`, `--approve-all`, `--approved-beat-id`, `--note`, `--rejected-beat-id`, `--created-at`, `--out-name`, and `--json`.

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Exit code: 0.

Output: `json ok`

```powershell
git diff --check
```

Exit code: 0.

Tail: line-ending warnings only; no whitespace errors.

## Smoke

Smoke output root:

`C:\Users\user\Desktop\video_pipeline\.tmp\story_human_review_decision_writer_smoke_20260706-180335`

Smoke command:

```powershell
@' ... '@ | C:\Users\user\miniconda3\python.exe -
```

Exit code: 0.

Per-case states:

| Case | Tool exit | pipeline_home exit | Mode | Cursor | Status | Next |
|---|---:|---:|---|---|---|---|
| approved | 0 | 0 | done | complete | DONE | null |
| revision_requested | 0 | 0 | repair | human_story_review | REPAIR | revise_story_material_mapping |
| rejected | 0 | 0 | repair | human_story_review | REPAIR | repair_rejected_story_material_mapping |

## UTF-8 / no-corruption check

All smoke-generated `story_human_review_decision.json` files were read with explicit UTF-8.

Results:

- approved: no `\ufffd`, no question-mark placeholder runs
- revision_requested: no `\ufffd`, no question-mark placeholder runs
- rejected: no `\ufffd`, no question-mark placeholder runs

The focused UTF-8 unit test also wrote a Chinese note using Unicode escapes and confirmed the generated JSON preserved it without replacement characters or question-mark placeholders.

## Deviations

- The CLI prints JSON by default; `--json` is accepted and prints a compact summary. This follows the work order's delegated decision allowing JSON stdout by default or with `--json`.
- `--reviewer` must be exactly `human` for delivery decisions. No non-human dry artifact mode was added.

## Blockers

No stop-loss blocker was hit. The implementation did not require delivery gate semantic changes, provider/runtime/render/media changes, or a Python interpreter other than `C:\Users\user\miniconda3\python.exe`.

## Next recommended work

Add this command to the operator runbook for scripted delivery closeout so a human reviewer can copy/paste the approved, revision_requested, or rejected command immediately after reviewing `story_to_material_map.json`.
