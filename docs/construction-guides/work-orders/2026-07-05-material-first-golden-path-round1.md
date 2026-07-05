# Material-First Golden Path Stabilization Round 1

Date: 2026-07-05
Status: pass - boundary/build-ready golden path, not final delivery

## Goal

Stabilize a clean-checkout material-first golden path for a user brief plus
material folder route:

```text
tracked fixture recipe
  -> runtime generated tiny material folder
  -> material wall verdict
  -> material-first boundary acceptance
  -> project_material_map.json
  -> material_delta.json
  -> Stage 4 build smoke
  -> Stage 5 final-review smoke
  -> replay acceptance report
```

This round intentionally stops at boundary/build-ready acceptance. It does not
claim `final.mp4` delivery.

## Phase 0 Inventory

- Official local material-first entry before this round:
  `tools/material_first_boundary_acceptance.py --out RUN_DIR --source-dir MATERIAL_SOURCE_DIR --wall-verdict material_wall_review_verdict.json --json`.
- Existing tests already proved the boundary script can run with disposable temp
  media, but there was no tracked cold-start fixture/replay entry for a reviewer
  or new agent.
- `video_tools.py replay-acceptance --scenario material-first-golden-path` did
  not exist before this round and failed with `unknown replay acceptance scenario`.
- Final delivery validation remains out of scope. The useful minimum for this
  round is material map, delta, rough timeline, Stage 4/5 reports, and an honest
  next action.

Mini-plan used:

1. Add a tracked deterministic fixture manifest plus runtime media generation.
2. Wrap existing material-first boundary acceptance with a golden-path report.
3. Wire one replay acceptance scenario for cold-start reruns.
4. Run mini cold-start validation and patch only instruction friction.
5. Record this report after focused and full verification.

## Commits

- `18422b92 Add material-first golden path fixture`
- `7687c43e Add material-first golden path acceptance`
- `311961ab Clarify material-first golden path replay entry`

Final report commit is this document.

## Fixture Location

- `tests/fixtures/material_first_golden/fixture_manifest.json`
- `tests/fixtures/material_first_golden/README.md`

The fixture tracks a small JSON recipe, not large media. Runtime generation
writes three tiny JPEGs under `.tmp/material_first_golden_path/source` and a
matching `material_wall_review_verdict.json`.

## Official Acceptance Command

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp/material_first_golden_replay.json
```

Latest observed report:

- path: `.tmp/material_first_golden_replay.json`
- `ok=true`
- `blocked=false`
- `next_action=ready_for_render_or_human_review`
- `fixture_source=tracked_manifest_runtime_generated_media`
- `final_mp4_absent=true`

## Produced Artifacts

Replay report artifacts include:

- `.tmp/material_first_golden_path/brief.json`
- `.tmp/material_first_golden_path/material_wall_review_verdict.json`
- `.tmp/material_first_golden_path/source`
- `.tmp/material_first_golden_path/run/project_material_map.json`
- `.tmp/material_first_golden_path/run/material_delta.json`
- `.tmp/material_first_golden_path/run/material_map_lifecycle.json`
- `.tmp/material_first_golden_path/run/rough_cut_plan.json`
- `.tmp/material_first_golden_path/run/timeline_build.json`
- `.tmp/material_first_golden_path/run/material_first_boundary_acceptance_report.json`
- `.tmp/material_first_golden_path/run/stage4_build_smoke_report.json`
- `.tmp/material_first_golden_path/run/stage5_final_review_smoke_report.json`

`final.mp4` is intentionally absent.

## Mini Cold-Run Validation

Round 1:

- Result: pass, but identified ambiguity between the generic boundary script and
  the new golden fixture replay command.
- Report outcome: `ok=true`, `blocked=false`,
  `next_action=ready_for_render_or_human_review`.
- Action taken: added a small `START_HERE` note naming the replay scenario as
  the self-contained golden path regression.

Round 2:

- Result: pass.
- Mini selected the replay command from `START_HERE` and the fixture README,
  not the manual boundary script.
- Report outcome: `ok=true`, `blocked=false`,
  `next_action=ready_for_render_or_human_review`.
- Confirmed `.tmp/material_first_golden_path/run/final.mp4` absent.

## Tests Run

- `& "$env:USERPROFILE\miniconda3\python.exe" -m unittest tests.test_material_first_boundary_acceptance tests.test_material_first_landing_case tests.test_material_first_stage2_3_smoke -v`
  - `Ran 18 tests in 6.615s`
  - `OK`
- `& "$env:USERPROFILE\miniconda3\python.exe" -m unittest tests.test_material_first_golden_path -v`
  - latest: `Ran 2 tests in 1.692s`
  - `OK`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py replay-acceptance --scenario material-first-golden-path --out .tmp/material_first_golden_replay.json`
  - exit 0
  - `ok=true`, `blocked=false`,
    `next_action=ready_for_render_or_human_review`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py interface-audit`
  - `ok=true`
  - `missing_commands=[]`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py acceptance-contract --out .tmp/material_first_acceptance_contract.json`
  - exit 0
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py registry-audit`
  - `Registry Audit: OK (7 branches, 14 stages)`
- `& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py test-tiers --tier work-order-acceptance --dry-run`
  - `ok=true`
  - `command_count=4`
- `git diff --check`
  - exit 0
- `& "$env:USERPROFILE\miniconda3\python.exe" -m unittest discover -s tests`
  - `Ran 2406 tests in 627.426s`
  - `OK`

## Blockers / Deferred

No blocker remains for this round's success criteria.

Deferred:

- final render and complete-video delivery gate;
- user-specific material folder UX beyond the generic boundary script;
- stock semantic-fit implementation;
- provider/network behavior;
- generated storybook route;
- Dashboard/Workbench UI work;
- Remotion or Effect Factory changes.

## Next Recommended Work Order

Suggested title:

```text
Material-First Golden Path Round 2: User Source Folder Fail-Closed UX
```

Scope:

- keep the current replay fixture as regression;
- add a focused acceptance path for an operator-provided source folder;
- improve needs-context/blocking messages for missing/too-thin/corrupt folders;
- do not render final delivery unless complete-video evidence is explicitly in
  scope.

## Capability Statement

This round is final for boundary/build-ready golden-path stabilization. It is
not final delivery capable: no `final.mp4`, complete-video validation, audio,
subtitle, or final promotion evidence is produced.
