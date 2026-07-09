# Work Order: Perception Layer Field Repairs (Ear Truncation, Gap Fill, Wall Pagination, Single-Pass Decode)

Date: 2026-07-10
Background: field test of the perception chain on the real graduation film
(`C:\Users\user\Downloads\微電影素材\_整理後\67期結訓影片-終.mp4`, 564s,
172 shots) — artifacts in `.tmp/perception_field_test_20260710/`. The chain
ran end to end and fail-closed correctly, but exposed five defects that
synthetic fixtures cannot catch. This stage repairs them. Perception stays
observation-only: no quality judgment, no asset promotion, declared
limitations (pattern: `material_understanding_matrix.py` docstring).

Field findings being repaired:

1. `beat_times` stop at 185.8s on a 564s track (plus an arbitrary `[:128]`
   cap in `_sampling_anchors`) — the back 2/3 of the film had zero audio
   anchors, causing all 14 coverage gaps (worst: two 33s holes inside a
   66.8s ceremony long take).
2. `energy_peaks`/`energy_drops` are always empty: threshold is absolute
   `relative_energy >= 0.75` but the field track's maximum is 0.606.
3. Duplicate wall cells: dedup key includes `reason`, so the same timestamp
   appears once per reason (two 6.30s cells), and 0.01s-apart samples
   survive (4.57s + 4.58s).
4. Wall not cloud-consumable: 668 cells rendered one 3360x29584 px, 23.2 MB
   image; the montage-wall cost model requires bounded pages.
5. Planning took 394s and wall render 129s because `_sharpest_timestamp`
   and cell extraction seek+decode the video once per sample (668 opens).

## Goal

On the field video, one command produces a passing coverage report and a
paginated wall, with the whole chain fast enough for interactive review.
Visible capability: `video_tools.py perception-field-check <video> --out DIR`
exits 0 on the graduation film, writing plan, coverage (pass=true), paginated
wall pages, sidecar, and a field metrics report.

## Owner Zone

- `video_pipeline_core/sampling_planner.py`
- `video_pipeline_core/sampling_coverage.py`
- `video_pipeline_core/montage_wall.py`
- `video_pipeline_core/soundtrack_probe.py`
- `video_tools.py` (new subcommand + classification)
- `tests/`
- `docs/construction-guides/work-orders/2026-07-10-perception-layer-field-repairs-report.md`

## Forbidden Zone

- `runtime.py`, `video_pipeline_core/delivery_gate.py`,
  `video_pipeline_core/next_action_vocabulary.py`,
  `video_pipeline_core/reviewer_registry.py`
- `skills/`, `dashboard/`, `docs/` (except this order's report)
- `.env`, `reference repo/`, existing `.tmp/` runs (read-only)
- `C:\Users\user\Downloads\**` is READ-ONLY input; never write there.
- Git push, branch, PR. Local commit per piece is required.

## Required Interpreter

`C:\Users\user\miniconda3\python.exe` for every Python command. Follow repo
`AGENTS.md` UTF-8 rules (the field video path contains Chinese characters —
handle paths with `pathlib`, never shell-interpolated Chinese strings).

## Ordered Pieces

### Piece 1 - Ear repair: full-track beats + distribution-relative energy

In `soundtrack_probe.py`:

- Diagnose why beat tracking stops at ~186s on the field track (load
  duration limit, analysis window, or genuine music end). If the truncation
  is artificial, fix it so beats cover the full track; if the music truly
  ends there, that fact must be visible in the report (e.g. an analysis
  window / music-presence note), not silent.
- Replace the absolute `relative_energy >= 0.75` peak rule with a
  distribution-relative rule (percentile of this track's energy curve, with
  a floor to avoid firing on silence). Emit drops symmetrically.
- Reconsider the `[:128]`/`[:64]` anchor caps: cap density (anchors per
  minute) rather than absolute count, or raise caps; keep output fields
  backward compatible (extend, do not rename).

Commit: `Repair soundtrack anchors for full-track coverage`

### Piece 2 - Planner gap fill + cross-reason merge

In `sampling_planner.py`:

- Baseline targets must include periodic gap-fill samples inside long
  shots so that no unsampled span exceeds a `gap_fill_sec` parameter
  (default aligned with sampling_coverage `max_gap_sec` default 4.0).
  Coverage pass becomes guaranteed by construction, anchors or not.
- Merge samples closer than a `merge_window_sec` parameter (default ~0.3s)
  across reasons: one sample carries `reasons` as a list (keep `reason` as
  the primary for backward compatibility if consumers need it).

Commit: `Guarantee sampling gap fill and merge near-duplicate samples`

### Piece 3 - Wall pagination

In `montage_wall.py`:

- Paginate every profile: `max_cells_per_page` (default 96) and
  `max_page_height_px` (default 4096); a wall render outputs page images
  `<stem>_p01.png`, `<stem>_p02.png`, ... plus one sidecar whose cell index
  carries the page number and per-page image path list.
- CLI `montage-wall` gains the pagination params; existing single-image
  consumers in tests must be updated to the paginated shape.
- Fail-closed limitation behavior (coverage failing/missing) is unchanged.

Commit: `Paginate montage walls for bounded review images`

### Piece 4 - Single-pass decode

- Replace per-sample open/seek in `sampling_planner._sharpest_timestamp`
  and in wall cell extraction with a single sequential decode pass (or
  batched ordered seeks) per video. Output artifacts must stay semantically
  identical (same fields; timestamps may shift within the sharpness window).
- Prove equivalence with a fixture test comparing sample counts/reasons.

Commit: `Extract frames in a single pass for planner and wall`

### Piece 5 - Field-check subcommand (the acceptance instrument)

New `video_tools.py` subcommand `perception-field-check <video> --out DIR`:

- Runs shots (mv_cut.detect_shots) -> soundtrack probe -> plan -> coverage
  -> material wall, writing all artifacts plus
  `perception_field_report.json` with stage wall-clock seconds, sample/
  reason counts, gap list, page count/sizes.
- Exit 0 only if: coverage `pass` is true AND every wall page respects the
  pagination limits. Otherwise exit 1 with the failing reason in the
  report. Classify the command in the command manifest (as done for
  `montage-wall` in commit c650244d).
- Unit test with a synthesized fixture; the real-video run is executed as
  an acceptance command, not inside the unit suite.

Commit: `Add perception field check command`

## Red-First Verification

Each behavioral piece starts from a failing test. Synthesized fixtures only
in unit tests (<=10s, ffmpeg-generated, existing patterns in
`tests/test_perception_chain.py`).

## Acceptance Commands

- `C:\Users\user\miniconda3\python.exe -m unittest discover -s tests` -> exit 0
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain -v` -> exit 0
- `C:\Users\user\miniconda3\python.exe video_tools.py perception-field-check "C:\Users\user\Downloads\微電影素材\_整理後\67期結訓影片-終.mp4" --out .tmp/perception_field_repair_check` -> exit 0

Performance is reported, not gated: the field report must include per-stage
timings; the target (advisory) is plan+wall combined under ~150s on this
machine. Record the achieved numbers in the report.

## Stop-Loss Limits

- Same test class failing after 2 repair rounds: stop, report.
- If coverage still fails on the field video after Pieces 1-2 (should be
  impossible by construction): stop, attach the coverage JSON, report.
- A needed capability requires a new pip dependency: stop, report.
- Never write outside the repo and `.tmp/`; the Downloads video is input only.

## Delegated Decisions

- Percentile/floor values for energy peaks and drops; anchors-per-minute cap.
- `gap_fill_sec`, `merge_window_sec`, pagination defaults beyond the pinned
  96 cells / 4096 px.
- Single-pass decode implementation (opencv sequential read vs batched
  ffmpeg extraction) and buffering strategy.
- Field report JSON field names beyond stage timings, counts, gaps, pages.
- How `reasons` list coexists with legacy `reason`.

## Report

Write `docs/construction-guides/work-orders/2026-07-10-perception-layer-field-repairs-report.md`.
Start with `[WORKER REPORT - REVIEW MODE]`. Sections: summary; files changed;
field-check metrics (timings before/after where measurable, gap count, page
count/sizes); commands and exit codes; acceptance results; blockers/stop-loss;
deviations; advisory next work; final output prompt framed as unverified
evidence (index style: report path, must-read artifacts, key claims, blocker,
product objective, scope/stop-loss, next likely work).
