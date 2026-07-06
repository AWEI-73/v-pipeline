# Material-First Render Video Input Support Report

Date: 2026-07-06

## Summary

- Real-material render smoke output root: `.tmp/material_first_render_video_input_support_20260706-063649`
- Render run path: `.tmp/material_first_render_video_input_support_20260706-063649/run`
- Rendered video path: `.tmp/material_first_render_video_input_support_20260706-063649/run/final.mp4`
- Render result: `ok=true`
- ffprobe video evidence: 1 h264 video stream, 320x180, duration `12.000000`
- pipeline_home status: `REPAIR`, command `define_delivery_requirements`
- delivery gate status: blocked, `pass=false`

The renderer failure `Option loop not found` was reproduced red-first and fixed
by keeping `-loop 1` only for still-image inputs. Video inputs now render
without `-loop 1` and use `start_sec` / `duration_sec` from
`render_handoff.json`.

## Files Changed

- `video_pipeline_core/material_first_render.py`
- `tests/test_material_first_review_promotion.py`
- `docs/construction-guides/work-orders/2026-07-06-material-first-render-video-input-support-report.md`

Note: `tests/test_material_first_review_promotion.py` already contained
uncommitted review-promotion changes from earlier work. This round added the
video fixture helper and the video render handoff regression test without
reverting those existing edits.

## Red-First Failure

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion.MaterialFirstReviewPromotionTest.test_render_handoff_execution_supports_run_local_video_refs_with_timing
```

Valid red-first exit code: `1`

Failure tail:

```text
AssertionError: False is not true : {
  'artifact_role': 'material_first_final_artifact_acceptance',
  'route': 'material-first',
  'ok': False,
  'next_action': 'blocked',
  'blocking': [{
    'rule': 'ffmpeg_render_failed',
    'message': 'ffmpeg failed to render material-first final.mp4',
    'error': 'Option loop not found.'
  }]
}
```

Before that valid red, the first fixture attempt failed because the generated
test video used an odd height for x264. The fixture was corrected to an even
height before production code was changed.

## Implementation

- Still images keep the looped image path: `-loop 1 -t <duration> -i <path>`.
- Video inputs use `-ss <start_sec> -t <duration_sec> -i <path>` and do not use
  `-loop 1`.
- The filter graph normalizes each input with `setpts=PTS-STARTPTS` before
  concat.
- Existing run-local validation remains in place: absolute refs, non
  `assets/materials/...` refs, and missing copied files still block before
  render.
- `material_first_final_artifact_acceptance.json` still records
  `final_delivery_claimed=false`.

## Verification Commands

### Focused Regression After Fix

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion.MaterialFirstReviewPromotionTest.test_render_handoff_execution_supports_run_local_video_refs_with_timing
```

Exit code: `0`

Stdout tail:

```text
Ran 1 test in 0.248s

OK
```

### Target Test Command

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion
```

Exit code: `0`

Stdout tail:

```text
Ran 10 tests in 3.175s

OK
```

### Fresh Real-Material Copy

Command: work-order pinned fresh-copy command.

Exit code: `0`

Stdout tail:

```text
source_exists: True
target: C:\Users\user\Desktop\video_pipeline\.tmp\material_first_render_video_input_support_20260706-063649\run
copied: True
```

### Fresh Real-Material Render Smoke

Command: work-order pinned `render_material_first_handoff` command.

Exit code: `0`

Stdout tail:

```json
{
  "ok": true,
  "next_action": "ready_for_delivery_gate",
  "final_delivery_claimed": false,
  "final_mp4_ref": "final.mp4",
  "input_refs": [
    "assets/materials/real_0006.mp4",
    "assets/materials/real_0002.mov",
    "assets/materials/real_0003.mp4"
  ],
  "ffprobe": {
    "ok": true,
    "streams": [
      {
        "codec_name": "h264",
        "codec_type": "video",
        "width": 320,
        "height": 180,
        "duration": "12.000000"
      }
    ],
    "video_stream_count": 1
  },
  "blocking": []
}
```

### Bounded Simulated Drill Boundary

The previous simulated drill folder was not edited in place. Its simulation
artifacts were copied into the fresh render run:

- `interaction_log.md`
- `decision_trace.json`
- `simulated_client_brief.json`
- `simulation_notice.json`

Copy command exit code: `0`

### pipeline_home

```powershell
C:\Users\user\miniconda3\python.exe tools/pipeline_home.py --run "$env:RENDER_RUN" --json
```

Latest exit code: `0`

Stdout tail:

```json
{
  "mode": "repair",
  "cursor": "stage5_final_review",
  "next": "define_delivery_requirements",
  "next_action_class": "repair_stop",
  "owner": "verify_delivery",
  "status": "REPAIR",
  "command": "define_delivery_requirements",
  "source": "delivery_gate.json"
}
```

### delivery gate

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run "$env:RENDER_RUN" --json
```

Latest exit code: `1`

Status: blocked, `pass=false`

Blocking rules:

- `missing_delivery_requirements`
- `missing_audio_stream`
- `missing_narration_manifest`
- `missing_music_manifest`
- `missing_audio_mix_report`
- `missing_subtitles`
- `missing_frame_evidence`

This is not a renderer failure. The rendered `final.mp4` has a video stream but
does not satisfy complete delivery requirements.

### Full Work-Order Unittest Acceptance

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_material_first_review_promotion tests.test_material_first_golden_path tests.test_material_first_source_intake tests.test_material_first_boundary_acceptance tests.test_material_first_landing_case tests.test_material_first_real_source_probe
```

Exit code: `0`

Stdout tail:

```text
Ran 32 tests in 11.131s

OK
```

### git diff check

```powershell
git diff --check
```

Exit code: `0`

Stdout/stderr tail: only pre-existing CRLF conversion warnings were printed.

## Deviations, Skips, And Blockers

- Delivery gate blocked after successful render, so no delivery bypass or
  waiver work was attempted.
- The previous simulated drill was not rerun as an interactive conversation;
  its preserved simulation artifacts were reused by copying them into the
  fresh render run to keep the simulation boundary visible.
- No preview package or formal delivery promotion was created.
- Blocker for delivery: complete delivery requirements are missing after render,
  especially audio, narration, music, subtitles, frame evidence, and
  `delivery_requirements.json`.

## Next Recommended Work

Starting from
`.tmp/material_first_render_video_input_support_20260706-063649/run`, define
real delivery requirements and complete the missing audio/narration/music/
subtitle/frame-evidence artifacts, then rerun delivery gate without changing
the renderer.
