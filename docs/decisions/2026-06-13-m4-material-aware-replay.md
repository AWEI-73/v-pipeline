# M4 Material-Aware Replay Decision Log

## Goal

Institutionalize dense visual VERIFY evidence, then replay the same
`67th-graduation-film` case through the material-aware M0-M3 pipeline without
allowing missing material or target duration to be hidden by repetition.

## Evidence Upgrade

M4a now produces four review layers:

- Full-film overview: 48 timestamped frames.
- Per-chapter evidence: 12-16 timestamped frames per segment.
- Critical edit evidence: 24-40 timestamped frames for speech-safe, reviewed,
  or adjusted clips.
- Rhythm strip: one proportional block per timeline clip.

Evidence bundle:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260612-232948-story-mv\m4_verify_evidence`

The dense evidence exposes issues hidden by the previous single-sheet review:

- The 48-frame overview visibly repeats multiple training, portrait, and group
  images.
- Chapter 7 uses only a few distinct shots across the chapter.
- Critical segment 5 shows almost the same group frame across all 24 samples.
  A motion snap is therefore not proof of meaningful action progression.

## Replay Results

First replay run:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260613-m4-replay`

The run planned 165 clips across 20 chapters before failing because direct
`contract-run` did not materialize `material_coverage_map.json`. Metrics:

| Metric | Result |
|---|---:|
| shots <= 2s ratio | 0.0242 |
| unique source ratio | 0.1273 |
| max source repeats | 23 |
| new visual information ratio | 0.4761 |
| repeated visual hold | 304.952s |
| action phase coverage | 0.0 |
| sound bites | 2 |
| jump-cuts | 0, not applicable |

Replay acceptance: **FAIL**. Tier-1 gate lineage, judge acceptance, duration
adaptation, chapter adaptation, and new-visual-information requirements were
not satisfied.

## Root Cause And Fix

`runtime_orchestrator` generated material coverage, but direct
`video_tools.py contract-run` did not. `run_contract` also called `spec_review`
without a `supply_review`, allowing script-overreach B6 to be bypassed.

The formal CLI path now:

1. Writes `material_coverage_map.json`.
2. Writes `supply_review.json`.
3. Passes supply evidence into `spec_review`.
4. Stops before `mv_chain` when material supply cannot support the script.

Gated replay:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260613-m4-replay-gated`

It stopped in about five seconds with 20 B6 `script_overreach` findings. Notable
examples:

- Segment 7, live-line work: requested 27.8873s, supported 0s.
- Segment 8, existing-course bridge: requested 43.3803s, supported 0s.
- Segment 5, pole installation: requested 27.8873s, supported 2s.

## Decision

M4a is complete. M4b is intentionally **not accepted**. The correct next route
is `revise:director(spec_review)`: shorten or merge chapters according to
`supply_review.json`, and request material for zero-supply segments. Rendering
another ten-minute candidate before resolving these findings would reproduce
the same human-vs-agent quality gap.

## Verification

- M4 focused suites passed.
- Full regression: `727 tests OK`.
- `py_compile` passed.
- `git diff --check` passed.

## Director Revision And Final Replay

The director route reduced the original 20 chapters / 660 seconds to 15
chapters / 180.5 seconds. It removed zero-supply live-line and bridge chapters,
low-information or duplicate chapters, preserved all must-include beats, and
assigned distinct aerial sources to the opening and closing.

The revision exposed three additional BUILD defects:

1. Matched montage candidates were consumed from the first source until all
   slots were full. Candidate windows now interleave before a source is reused.
2. `requested_duration_sec` passed the supply gate but was dropped by the
   adapter and ignored by allocation. Explicit durations now remain fixed while
   only the remaining duration is weight-allocated.
3. An explicit director `file` choice lost to automatic matched picks. Explicit
   files now override automatic matching.

Final planning replay:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260613-m4-final-replay-explicit-file`

| Metric | Initial replay | Final replay |
|---|---:|---:|
| target / actual duration | 660s | 180.5s |
| chapters | 20 | 15 |
| unique source ratio | 0.1273 | 1.0 |
| max source repeats | 23 | 1 |
| new visual information ratio | 0.4761 | 1.0 |
| repeated visual hold | 304.952s | 0.0s |
| sound bites | 2 | 2 |
| action phase coverage | 0.0 | 0.0 |

`m4_replay_acceptance.json` passes all implemented checks: tier-1 gates, judge
lineage, new visual information, duration adaptation, and chapter adaptation.
Jump-cut remains not applicable. This is a planning replay using
`--skip-render`; it does not claim final rendered-video delivery.

Final verification:

- Full regression: `731 tests OK`.
- `py_compile` passed.
- `git diff --check` passed.
