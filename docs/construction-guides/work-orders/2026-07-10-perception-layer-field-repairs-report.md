[WORKER REPORT - REVIEW MODE]

## Summary

Implemented the five ordered Perception Layer Field Repairs pieces through
unit-level green evidence and local commits. The real field-check command still
fails after two repair rounds, so stop-loss is triggered.

What improved on the field video:

- Field coverage gaps went from 14 in the original evidence to 0 in the latest
  field-check report.
- The wall now paginates into bounded page images instead of one huge image.
- `perception-field-check` writes shots, soundtrack probe, sampling plan,
  coverage, wall sidecar, wall pages, and `perception_field_report.json`.

Remaining blocker:

- Coverage still reports `pass=false` because 19 `anchor_within_tolerance`
  checks miss the 0.35s tolerance. The failures are audio/energy anchor
  proximity misses, not unsampled shot gaps.

## Files Changed

- `video_pipeline_core/soundtrack_probe.py`
- `video_pipeline_core/sampling_planner.py`
- `video_pipeline_core/montage_wall.py`
- `video_tools.py`
- `tests/test_perception_chain.py`
- `docs/construction-guides/work-orders/2026-07-10-perception-layer-field-repairs-report.md`

## Field-Check Metrics

Original field evidence from work order:

- Video duration: 564s
- Shot count: 172
- Coverage gaps: 14
- Sampling plan time: about 394s
- Wall render time: about 129s
- Wall output: one 3360x29584 px, 23.2 MB image

Latest field-check report:

- Command output: `.tmp/perception_field_repair_check/perception_field_report.json`
- Exit code: 1
- Shot count: 172
- Sample count: 699
- Reason counts: baseline 580, motion_peak 22, audio_beat 226, energy_event 36
- Coverage pass: false
- Coverage gap count: 0
- Failed coverage checks: 19 anchor tolerance checks
- Wall page count: 31
- Wall page violations: 0
- Stage seconds:
  - shot_detection: 63.752
  - soundtrack_probe: 8.131
  - sampling_plan: 393.562
  - sampling_coverage: 0.094
  - montage_wall: 88.258

The wall pagination repair reduced the wall stage from about 129s to 88.258s
and bounded page heights. Planning remains about 393s on this machine, so the
advisory plan+wall target under 150s is not met.

## Commands And Exit Codes

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_soundtrack_anchors_use_distribution_relative_energy_and_density_cap -v` -> exit 0 after red/green
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_sampling_plan_gap_fills_long_shots_and_merges_near_duplicate_reasons -v` -> exit 0 after red/green and repairs
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_montage_wall_paginates_bounded_pages_and_sidecar_cells -v` -> exit 0 after red/green
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_planner_and_wall_use_bounded_video_opens_with_same_reason_counts -v` -> exit 0 after red/green
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain.PerceptionChainSmokeTest.test_perception_field_check_command_writes_report_and_classifies_command -v` -> exit 0 after red/green
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain -v` -> exit 0, Ran 9 tests
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_video_tools_command_catalog -v` -> exit 0, Ran 6 tests
- `C:\Users\user\miniconda3\python.exe video_tools.py perception-field-check "C:\Users\user\Downloads\微電影素材\_整理後\67期結訓影片-終.mp4" --out .tmp/perception_field_repair_check` -> exit 1, `coverage_failed`

## Acceptance Results

- Full suite acceptance was not run after stop-loss, because the real
  field-check acceptance command failed.
- `tests.test_perception_chain -v` passed before the stop-loss report.
- Real `perception-field-check` did not pass.

## Blockers / Stop-Loss

Stop-loss triggered: the same real field-check coverage failure remained after
two repair rounds.

Repair round 1 changed gap-fill spacing from exact 4.0s to a 3.5s safety step.
Result: field coverage gaps became 0, but coverage still failed anchor
tolerance checks.

Repair round 2 prevented same-reason audio anchors from being merged away when
their target times differ beyond the merge window. Result: audio beat sample
count rose to 226 and gaps stayed 0, but 19 anchor tolerance checks still fail.

The latest failures are observable in
`.tmp/perception_field_repair_check/sampling_coverage_report.json`.

## Deviations

- Two additional repair commits used the Piece 2 commit message after the real
  field command exposed field-only coverage failures.
- Full acceptance was not completed because the real field-check command failed
  and stop-loss triggered.
- The work-order doc remained untracked as found; it was read as construction
  basis but not edited or committed in this stage.

## Advisory Next Work

- Decide whether anchor coverage should verify `target_timestamp_sec` for
  audio/energy anchors while wall cells display `timestamp_sec`, or whether the
  planner should keep anchor samples unshifted and use sharpness only for frame
  extraction.
- Investigate why planning remains about 393s despite bounded video opens; the
  expensive portion may now be ordered seeks/Laplacian scoring rather than open
  overhead.
- Consider adding width bounds for material wall pages if cloud consumers also
  constrain image width; this work order only pinned cell count and height.

## Local Commits

- `c297329c Repair soundtrack anchors for full-track coverage`
- `8088c4a8 Guarantee sampling gap fill and merge near-duplicate samples`
- `0a1d5229 Paginate montage walls for bounded review images`
- `aaaf0d0a Extract frames in a single pass for planner and wall`
- `57e2af75 Add perception field check command`
- `9dabc182 Guarantee sampling gap fill and merge near-duplicate samples`
- `0bd927d8 Guarantee sampling gap fill and merge near-duplicate samples`

## Final Output Prompt (Unverified Evidence)

Unverified evidence for owner review: read this report and
`.tmp/perception_field_repair_check/perception_field_report.json`,
`.tmp/perception_field_repair_check/sampling_coverage_report.json`, and
`.tmp/perception_field_repair_check/montage_wall.json`. Key claims: field gaps
are now 0, wall pagination produces 31 bounded pages, and the command writes
the requested artifact set. Blocker: real field-check still exits 1 because 19
anchor-tolerance checks miss 0.35s, so acceptance is not complete. Product
objective remains observation-only reviewer perception evidence for the
graduation field video. Scope/stop-loss: continue only in the owner zone unless
the owner changes the anchor coverage contract. Next likely work is to align
audio/energy anchor coverage with sharpness-adjusted visual sample timestamps
without turning perception into quality judgment or asset promotion.
