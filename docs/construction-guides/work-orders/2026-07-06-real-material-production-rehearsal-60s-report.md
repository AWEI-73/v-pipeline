# Real Material Production Rehearsal 60s Report

Date: 2026-07-06

## Output

- Output root: `.tmp/real_material_production_rehearsal_60s_20260706-115057`
- Run path: `.tmp/real_material_production_rehearsal_60s_20260706-115057/run`
- Source: `C:\Users\user\Downloads\微電影素材\_整理後`
- Final media: not produced because VoxCPM generation hit stop-loss.
- Silent visual candidate: `final_video_silent.mp4`

## Source Preflight

Command: work-order Unicode escape preflight.

Exit code: 0

Result:

- exists: true
- is_dir: true
- file_count: 306

## Subagent Records

Real subagents were used. Result records:

- `subagent_dispatches/timeline_intake_result.json`
- `subagent_dispatches/voiceover_voxcpm_result.json`
- `subagent_dispatches/music_source_result.json`
- `subagent_dispatches/delivery_review_result.json`

Each subagent wrote only its assigned result file under the fresh run.

## Material Intake And Timeline

Parent-side intake selected real source videos from the source folder and copied
them run-locally under `assets/materials/`.

Artifacts:

- `materials_db.json`
- `real_material_source_intake_report.json`
- `rough_cut_plan.json`
- `timeline_build.json`
- `render_handoff.json`

Timeline result:

- selected clip count: 8
- timeline duration: 40.0 seconds
- `render_handoff.timeline_refs`: 8
- render-critical refs: run-local `assets/materials/*`

Visual render:

```powershell
C:\Users\user\miniconda3\python.exe tools\rough_cut_plan_execute.py --rough-cut-plan "$env:RUN_DIR/rough_cut_plan.json" --out "$env:RUN_DIR/final_video_silent.mp4" --report "$env:RUN_DIR/rough_cut_preview_report.json" --timeout-sec 600 --fps 24
```

Exit code: 0

Result: `final_video_silent.mp4`, duration 40.0 seconds.

## VoxCPM Narration

Script:

- `script.json`
- segment count: 3
- UTF-8 check: no replacement char, question mark count 0

Runtime check:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out "$env:RUN_DIR/voxcpm_runtime_check.json"
```

Exit code: 0

Result:

- `ok_to_execute`: true
- Python: `.venv_voxcpm\Scripts\python.exe`
- missing modules: []

VoxCPM execute:

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py "$env:RUN_DIR/script.json" --out-dir "$env:RUN_DIR" --execute
```

Exit code: 1

Result:

- `voiceover_ready`: false
- rendered files: 2 of 3
- `voiceover/seg02.wav`: 378924 bytes
- `voiceover/seg03.wav`: 314924 bytes
- failed segment: `opening_context`
- provider return code: 3221225477
- stderr tail shows VoxCPM loaded model on cuda/bfloat16 and then the subprocess terminated before writing `seg01.wav`.

This is a real branch blocker under the work-order stop-loss rule: fewer than
three usable narration segments were produced.

## Music And Probe

Music branch was not executed because the VoxCPM branch stopped the run before
music source/download/probe could start.

Planned needs recorded in `parent_branch_dispatch_probe.json`:

- `opening_underlay`
- `training_momentum`

Downloads/imports:

- count: 0
- reason: not started due voiceover stop-loss

No `generated_bgm.wav`, local tone, placeholder, or reference-only music was
used.

## Pipeline Home And Gate

Pipeline home:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "$env:RUN_DIR" --json
```

Exit code: 0

Result:

- status: REPAIR
- cursor: `subtitle_voiceover_handoff`
- next: `subtitle-voiceover-handoff-accept`
- reason: subtitle/voiceover handoff artifacts are incomplete

Delivery gate command:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "$env:RUN_DIR" --json
```

Exit code: 0

Result caveat: the command wrote a dashboard-state preview gate with
`report_source=dashboard_state.artifacts.delivery_gate` and `pass=true`.
This is not a complete final delivery pass because `final.mp4` was not produced
and the run stopped at the VoxCPM branch.

## Acceptance Checks

Source/provenance/multiplicity check:

- exit code: 0
- missing: []
- script_segments: 3
- timeline_refs: 8

Final media duration/streams check:

- exit code: 0
- output: `final_exists: false`

Music downloads check:

- exit code: 1
- needs: 2
- downloads: 0
- bad: []
- reason: music branch did not start after VoxCPM stop-loss.

## Review Artifacts

Final review artifacts were not produced because final media does not exist.
The silent visual candidate and rough-cut preview report remain available for
visual-only inspection:

- `final_video_silent.mp4`
- `rough_cut_preview.mp4`
- `rough_cut_preview_report.json`

## Deviations, Skips, Blockers

- Deviation: existing material-first tooling was not used as a full black-box
  happy path because it is oriented to no-render/review handoff; parent built a
  fresh run-local 8-clip timeline and render handoff using real source media and
  existing renderer tooling only. No code was edited.
- Skip: music source/download/probe, subtitle handoff, audio mix, final AV
  assembly, and review artifacts were skipped after the VoxCPM stop-loss.
- Blocker: VoxCPM generation failed on the first narration segment with return
  code 3221225477, leaving only 2 usable narration files.

## Approval And Legal Review

Real user approval is still required. Legal/music-use review is still required.
No final delivery candidate was produced in this run.

## Next Recommended Work

Rerun only the blocked VoxCPM narration branch for this fresh run, starting with
the failed `opening_context` segment. If it fails again with return code
3221225477, capture a smaller/CPU or shorter-text VoxCPM diagnostic run before
starting music/download work.
