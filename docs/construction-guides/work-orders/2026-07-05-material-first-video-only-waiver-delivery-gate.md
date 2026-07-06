# Work Order: Material-First Video-Only Delivery Waiver

Date: 2026-07-05
Status: ready for construction

## Background

Material-first runs can already prove material truth and reach a delivery gate,
but soundtrack, audio, subtitle, or license blocks can still prevent delivery
even when the operator only wants to hand off a reviewed video-only candidate.
The current code has canonical waivers for material delta and generated quality,
but there is no explicit video-only delivery waiver that says "ship the picture
with declared limitations" while preserving all visual, material, semantic,
effect, and duration gates.

Today's behavior was checked with:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_delivery_gate_report tests.test_pipeline_home.PipelineHomeTest.test_soundtrack_blocks_override_material_first_ready_summary tests.test_pipeline_home.PipelineHomeTest.test_soundtrack_handoff_blocks_route_when_license_missing
```

Expected current result: exit code 0. The tests confirm soundtrack/license
blocks can override material-first readiness, and delivery reporting already
fails closed for missing video candidates and short previews.

## Goal

Implement an explicit video-only delivery waiver path for material-first runs so
a reviewed video candidate can pass delivery with visible limitations when only
non-video obligations are waived.

## User-Visible Desired State

An operator can place a canonical `video_only_delivery_waiver.json` in a run
folder, run the delivery gate report, and see a passing delivery gate for a
video-only handoff if the run has a real video candidate and all non-waived
video/material/semantic/duration requirements pass.

## Non-Goals

- Do not weaken material-map lifecycle, material delta, project material map, or
  timeline material contract checks.
- Do not waive missing video candidates, failed final-product verify bundles,
  target-length mismatches, semantic material mismatch, or required rendered
  effect evidence.
- Do not replace or reuse material-delta waivers for delivery-only obligations.
- Do not promote soundtrack reference tracks into deliverable audio.
- Do not add a provider, renderer, VLM, or long-running real-material probe in
  this implementation round.
- Do not rename existing delivery artifacts.

## Owner Zone

The worker may edit only these paths:

- `video_pipeline_core/delivery_gate.py`
- `tools/write_delivery_gate_report.py`
- `tools/pipeline_home.py`
- `video_pipeline_core/run_artifact_index.py`
- `tests/test_delivery_gate.py`
- `tests/test_delivery_gate_report.py`
- `tests/test_pipeline_home.py`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`

## Forbidden Zone

These paths are read-only for this work order:

- `video_pipeline_core/material_delta.py`
- `video_pipeline_core/material_revision.py`
- `video_pipeline_core/material_map_lifecycle.py`
- `video_pipeline_core/generated_material_review.py`
- `video_pipeline_core/soundtrack_arranger.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `video_pipeline_core/verified_preview_package.py`
- `skills/`
- `examples/`
- `runs/`
- `Downloads/`
- `C:/Users/user/Downloads/`

## Artifact Contract

Create support for this run-folder artifact:

```json
{
  "artifact_role": "video_only_delivery_waiver",
  "version": 1,
  "scope": "video_only_delivery",
  "reviewer": "operator name or id",
  "reason": "why delivery is intentionally video-only",
  "at": "2026-07-05T00:00:00+08:00",
  "waives": [
    "audio",
    "music",
    "subtitle",
    "narration",
    "soundtrack_license"
  ],
  "limitations": [
    "Video-only handoff; no deliverable soundtrack, narration, or subtitles."
  ]
}
```

Canonical validation:

- `artifact_role` must be `video_only_delivery_waiver`.
- `version` must be `1`.
- `scope` must be `video_only_delivery`.
- `reviewer`, `reason`, and `at` must be non-empty strings.
- `waives` may contain only `audio`, `music`, `subtitle`, `narration`, and
  `soundtrack_license`.
- `limitations` must contain at least one non-empty string.

Invalid or missing waiver artifacts release nothing and must be visible in the
delivery report as a warning or block reason when relevant.

## Ordered Pieces

### Piece 1: Delivery-Gate Waiver Semantics

Outcome: complete-video delivery evaluation can consume a canonical waiver and
convert only non-video delivery obligations into visible limitations.

Red-first tests:

- A complete-video delivery run requiring music/audio/subtitles fails without a
  waiver.
- The same run passes with a canonical `video_only_delivery_waiver.json` when
  video probe/evidence requirements pass.
- A waiver missing `reviewer`, `reason`, `at`, or `limitations` does not pass.
- A waiver that includes an unknown waived item does not pass.
- Missing video stream or missing frame evidence still blocks even with waiver.

Implementation notes:

- Prefer small helpers in `video_pipeline_core/delivery_gate.py` for loading and
  validating the waiver from the run folder.
- The gate report must preserve the original non-video block as a limitation or
  waived finding; do not delete evidence.
- The final result must include enough machine-readable data for dashboard
  summary, for example `waivers_applied` and `limitations`.

### Piece 2: Preview / Dashboard Delivery Report Path

Outcome: `tools/write_delivery_gate_report.py` can pass a material-first preview
candidate under the same waiver when the dashboard gate is otherwise blocked
only by waived non-video obligations.

Red-first tests:

- Material-first ready plus soundtrack/license block plus canonical waiver plus
  preview candidate produces `delivery_gate.json` with `pass=true`.
- The report includes `report_source`, `generated_by`, `waivers_applied`, and
  `limitations`.
- `missing_video_candidate` still blocks with a canonical waiver.
- `preview_duration_below_stage0_target` still blocks with a canonical waiver.
- Timeline/material mismatch still blocks with a canonical waiver.

Implementation notes:

- Keep the existing fail-closed checks in `write_delivery_gate_report.py` after
  applying any waiver logic.
- Do not let a waiver convert a failed visual/material gate into pass.

### Piece 3: Pipeline Home Visibility

Outcome: `tools/pipeline_home.py` surfaces a video-only passed gate as delivery
ready and names the limitation, instead of routing back to soundtrack review.

Red-first tests:

- A passing delivery gate with `video_only_delivery_waiver` and no `final.mp4`
  still routes to preview promotion/review as current preview behavior requires.
- A promoted final or packaged preview with a passing video-only gate is
  complete or operator-review ready, and the summary reason mentions video-only
  limitations.
- A soundtrack block without waiver still routes to `soundtrack_review`.

### Piece 4: Artifact Index and Docs

Outcome: operators and future workers can discover the waiver artifact without
reading tests.

Required updates:

- Add `video_only_delivery_waiver.json` to the run artifact index if that index
  is the local source of known run-folder artifacts.
- Update only the smallest relevant sections of delivery-gate docs to say this
  waiver is a delivery limitation declaration, not a material or quality waiver.

## Acceptance Commands

Run these from `C:/Users/user/Desktop/video_pipeline`.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_delivery_gate_report tests.test_pipeline_home
```

Expected: exit code 0.

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run <fixture-created-by-tests-or-temp-run> --json
```

Expected for the video-only fixture: exit code 0, JSON has `pass=true`, includes
`waivers_applied`, and lists video-only limitations.

If the second command uses a temporary fixture, report the exact temp fixture
shape in the final report. Do not require the user to keep the temp folder.

## Stop-Loss Limits

Stop and report before continuing if any of these occur:

- The implementation needs edits outside the owner zone.
- More than one existing delivery artifact name would need to be renamed.
- The code needs to weaken material delta, material lifecycle, timeline
  material contract, frame evidence, target-length, or effect-render checks.
- A second class of waiver semantics is needed beyond video-only delivery
  obligations.
- Unit tests require a real media render or probe to pass.

## Delegated Decisions

The worker may decide:

- Helper function names and exact report field names for waiver details, as
  long as tests prove limitations are machine-readable.
- Whether waiver validation warnings live under `warnings`, `limitations`, or a
  small dedicated field, as long as invalid waivers do not release blocks.
- The smallest fixture structure needed for tests.
- Which of the allowed docs receives the concise operator note.

The worker must not decide:

- Expanding the waiver beyond audio/music/subtitle/narration/soundtrack license.
- Treating waiver as proof that audio, subtitles, or music are present.
- Reordering the next recommended work away from the real-material probe listed
  in the final report requirements.

## Suggested Commit Messages

- `test: cover video-only delivery waiver boundaries`
- `feat: add video-only delivery waiver gate`
- `docs: document video-only delivery limitations`

## Final Report Requirements

The final report must include:

- Files changed.
- Acceptance commands run, exit codes, and the important pass/fail lines.
- Whether `pytest` was unavailable and `unittest` was used instead.
- A short list of waiver limitations that remain visible in the generated gate.
- Any deviations from this work order.
- **Next recommended work:** run today's complete material-first path on the
  real material folder `C:/Users/user/Downloads/微電影素材/_整理後` and record the
  breakpoint list. This next work is not optional and must not be displaced by
  another internal cleanup, schema, dashboard, or planning topic in the next
  round.
