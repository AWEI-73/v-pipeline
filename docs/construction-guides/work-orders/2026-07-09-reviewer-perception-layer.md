# Work Order: Reviewer Perception Layer (Canonical Eye + Ear Anchors + Coverage Verify)

Date: 2026-07-09
Background: review-architecture discussion 2026-07-09. The reviewer role
(reviewer_registry.py) has no standard perception executor. Contact-sheet
rendering is duplicated in at least 6 places; frame sampling is uniform
(time-driven) instead of event-driven; there is no machine-verifiable
statement of what a wall did or did not cover. This stage builds the
deterministic perception layer that the future reviewer skill will consume.
It contains NO LLM calls and NO creative-quality judgment.

Design principle (pinned): perception modules are observation layers. They
must not judge quality, must not promote assets, and must declare their own
limitations, following the existing pattern in
`video_pipeline_core/material_understanding_matrix.py` module docstring.

## Goal

One canonical, contract-emitting perception chain:

shot list + audio anchors -> event-driven sampling plan -> coverage verify
report -> montage wall image(s) + machine-readable cell index.

Visible capability: one command chain on a fixture video produces
`sampling_plan.json`, `sampling_coverage_report.json`, wall PNG(s), and
`montage_wall.json`, all cross-referencing each other, with existing
contact-sheet call sites migrated to the canonical renderer.

## Owner Zone

- `video_pipeline_core/sampling_planner.py` (new)
- `video_pipeline_core/sampling_coverage.py` (new)
- `video_pipeline_core/montage_wall.py` (new)
- `video_pipeline_core/soundtrack_probe.py`
- `video_pipeline_core/material_understanding_matrix.py`
- `video_pipeline_core/source_material_matrix.py`
- `video_pipeline_core/remotion_acceptance.py`
- `video_tools.py` (new subcommands only)
- `tools/generated_material_flow_acceptance.py`
- `tools/story_to_generated_material_e2e.py`
- `tools/srp_real67_review_demo.py`
- `tests/` (new and updated tests)
- `docs/construction-guides/work-orders/2026-07-09-reviewer-perception-layer-report.md`

## Forbidden Zone

- `runtime.py`
- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/next_action_vocabulary.py` (Piece 6 adds a test only;
  this file stays read-only)
- `video_pipeline_core/reviewer_registry.py`
- `skills/`, `dashboard/`, `docs/` (except this order's report file)
- `.env`, `.venv_voxcpm/`, `reference repo/`, `Downloads/`, existing `.tmp/` runs
- Git push, branch, PR operations. Local commits per piece are required.

## Required Interpreter

`C:\Users\user\miniconda3\python.exe` for every Python command. Do not use
bare `python` or `pytest`. Follow repo `AGENTS.md` for UTF-8 handling.

## Ordered Pieces

### Piece 1 - Event-driven sampling planner

`video_pipeline_core/sampling_planner.py`. Input: video path, shot list
(same shot representation `keyframe_grid.py` consumes), optional audio
anchors mapping. Behavior:

- Per-shot baseline: first / middle / last timestamps always included.
- Motion curve from downscaled grayscale frame differencing; add sample
  points at motion peaks and direction changes above a threshold.
- Sharpness (Laplacian variance) picks the sharpest frame within a small
  window around each target timestamp.
- Audio anchors (beat times, energy peaks, speech starts), when provided,
  become additional sample points.
- Output artifact `sampling_plan.json`: `artifact_role`
  `"sampling_plan"`, `version`, per-sample entries carrying `shot_id`,
  `timestamp_sec`, and a `reason` tag from
  `{baseline, motion_peak, audio_beat, energy_event, speech_start}`.

Commit: `Add event-driven sampling planner for reviewer perception`

### Piece 2 - Sampling coverage verify report

`video_pipeline_core/sampling_coverage.py`. Pure function + CLI subcommand
`sampling-coverage` in `video_tools.py`. Checks a sampling plan against the
shot list and anchors: every shot has >=1 sample; every motion peak and
audio anchor has a sample within a tolerance window; maximum unsampled gap
below a threshold (thresholds are parameters with defaults). Output
`sampling_coverage_report.json` with `pass`, per-check results, and a
`gaps` list of unseen time windows. Fail-closed: missing inputs produce a
failing report with a named reason, never a silent pass.

Commit: `Add sampling coverage verify report`

### Piece 3 - Canonical montage wall renderer

`video_pipeline_core/montage_wall.py` + CLI subcommand `montage-wall` in
`video_tools.py`. Three profiles, one renderer:

- `material_wall`: one row per shot, time left to right, cell density from
  the sampling plan.
- `timeline_wall`: one row per final-cut segment with an aligned
  energy/motion sparkline strip under each row.
- `segment_strip`: dense strip for one shot/segment window.

Every cell burns in `shot_id` + timestamp. Sidecar `montage_wall.json`:
`artifact_role` `"montage_wall"`, `version`, `profile`, cell index mapping
each cell to `shot_id`/`timestamp_sec`/source path, and a reference to the
coverage report path. Fail-closed: if the coverage report is missing or
failing, the wall artifact must carry a non-empty `limitations` list saying
whole-video judgment is not supported; it must not silently claim full
coverage.

Commit: `Add canonical montage wall renderer with cell index`

### Piece 4 - Ear anchors and spectrogram in soundtrack probe

Extend `video_pipeline_core/soundtrack_probe.py`: emit a
`sampling_anchors` block (beat subset, energy peaks/drops, speech segment
starts when ASR ran) shaped for Piece 1 consumption, and an optional
mel-spectrogram PNG export flag. Existing report consumers must keep
passing; extend, do not rename existing fields.

Commit: `Extend soundtrack probe with sampling anchors and spectrogram`

### Piece 5 - Migrate contact-sheet call sites

Replace the duplicated contact-sheet implementations with calls into
`montage_wall.py`: `material_understanding_matrix._contact_sheet`,
`source_material_matrix._make_contact_sheet`,
`remotion_acceptance.write_contact_sheet`, and the three `tools/` scripts
in the owner zone. Core modules must call the canonical renderer directly;
standalone demo scripts may use a thin wrapper. Delete the superseded
implementations; keep their existing tests passing (updating assertions to
the new artifact shape is allowed and expected).

Commit: `Migrate contact sheet call sites to canonical montage wall`

### Piece 6 - Freeze compound verify-review vocabulary

New test (own file under `tests/`): collect every `next_action` in
`next_action_vocabulary.py` containing `_or_` that joins a verify-type and
a review-type token; freeze the current offenders in an explicit
grandfather allowlist inside the test; any NEW compound of that kind fails
the test with a message pointing to the verify/review separation rule. Do
not modify the vocabulary itself.

Commit: `Freeze compound verify-review next_action vocabulary`

## Red-First Verification

Every piece with new behavior starts from a failing test. Fixture videos
are synthesized with ffmpeg in-test (follow the existing pattern in
`tests/test_video_tools_audits.py` / `tests/test_keyframe_grid.py`), max
10 seconds duration.

Add `tests/test_perception_chain.py`: one smoke test that chains
planner -> coverage -> wall on a synthesized fixture and asserts all four
artifacts exist, cross-reference each other, and carry the required
contract fields.

## Acceptance Commands

- `C:\Users\user\miniconda3\python.exe -m unittest discover -s tests` -> exit 0
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_perception_chain -v` -> exit 0

## Stop-Loss Limits

- If migrating a call site would require touching `delivery_gate.py`,
  `runtime.py`, or verdict schemas: stop that call site, record it in the
  report, continue with the rest.
- Same test class failing after 2 repair rounds: stop, report.
- A needed capability requires a new pip dependency (current stack: PIL,
  opencv, librosa, faster-whisper, numpy, scenedetect): stop, report.
- No renders beyond short synthesized fixtures.

## Delegated Decisions

- Internal module layout, function decomposition, dataclass vs dict internals.
- Motion metric (frame-diff vs optical flow) and all threshold defaults.
- Grid geometry, pixel sizes, fonts, sparkline drawing details.
- JSON field names beyond the pinned contract fields named above.
- Adapter design for the `tools/` demo scripts in Piece 5.
- Spectrogram rendering parameters.
- Version handling in the soundtrack probe report.

## Report

Write `docs/construction-guides/work-orders/2026-07-09-reviewer-perception-layer-report.md`.
Start with `[WORKER REPORT - REVIEW MODE]`. Sections: summary; files
changed; artifacts created (with paths); commands and exit codes;
acceptance results; blockers/stop-loss events; deviations; advisory next
work; final output prompt (index style: report path, must-read artifacts,
key claims to verify, current blocker, product-level objective, scope and
stop-loss, next likely work; frame the report as unverified evidence).
