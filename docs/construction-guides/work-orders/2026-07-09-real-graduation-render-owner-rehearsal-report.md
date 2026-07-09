[WORKER REPORT - REVIEW MODE]

# Real Graduation Render Owner Rehearsal Report

## Summary

This run produced a fresh render-owner rehearsal candidate, but it is not a delivery candidate and did not clear rendered-product QA.

- Output root: `.tmp/real_graduation_render_owner_rehearsal_20260709-061555`
- Fresh run: `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/run`
- Final rehearsal video: `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/run/final.mp4`
- Current blocker: `rendered_product_qa` failed on `title_effect_evidence_missing`
- No delivery gate was run.
- No story, transcript, legal/music approval, or delivery package artifact was written.

## Prior Boundary Verification

The prior render-handoff run was verified before render-owner work:

- Source evidence run: `.tmp/real_graduation_render_handoff_construction_20260709-005405/run`
- Precheck artifact: `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/prior_render_boundary_precheck.json`
- `render_handoff.json`: `ok=true`
- No-render harness: `pass=true`
- Harness next action: `ready_for_render_rehearsal`

## Input Resolution

Input resolution artifact:

- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/render_owner_input_resolution.json`

Resolved inputs:

- Visual inputs: 7 selected clips copied into the owner root under `render_inputs/`
- Audio input: Jamendo rehearsal BGM copied into `render_inputs/music.mp3`
- Subtitle input: run-local `subtitles.srt` copied into `render_inputs/subtitles.srt`
- Effect input: run-local `effect_handoff.json`
- Render handoff input: run-local `render_handoff.json`
- Missing input errors: none

Music/legal limitation remains explicit: the music metadata is rehearsal evidence only and is not legal approval.

## Render Output

Render driver:

- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/render_owner_execute.py`

Render report:

- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/render_owner_rehearsal_report.json`

Render status:

- `status=rendered`
- Command count: `10`
- Errors: none
- `final_delivery_claimed=false`

Output:

- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/run/final.mp4`

ffprobe summary:

- Video stream: present, H.264, 1280x720
- Audio stream: present, AAC stereo
- Subtitle stream: present, mov_text
- Format duration: `41.000000` seconds

ffprobe artifact:

- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/ffprobe_final.json`

## Rendered QA

Rendered QA command ran and failed truthfully:

- QA output: `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/rendered_qa/rendered_product_qa.json`
- Contact sheet: `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/rendered_qa/rendered_product_qa_contact_sheet.jpg`
- Result: `pass=false`
- Blocking rule: `title_effect_evidence_missing`
- Message: `title/effect lifecycle QA exists but lacks rendered frame evidence`
- Blocking artifact: `title_effect_lifecycle_qa.json`

This is the stop-loss blocker for this round.

## Harness Render-Rehearsal

Harness output:

- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/harness_render/graduation_product_route_harness_result.json`
- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/harness_render/pipeline_execution_trace.json`

Harness result:

- `pass=false`
- Stop gate: `rendered_product_qa`
- Stop reason: `rendered product QA failed`
- Trace depth: `10`
- Stage order:
  1. `pipeline_home`
  2. `film_canon_route_artifact_check`
  3. `film_canon_readiness`
  4. `product_route_review_decision`
  5. `shot_level_material_proof`
  6. `visual_selection_gate`
  7. `effect_handoff`
  8. `music_subtitle_profile`
  9. `compose_render_handoff`
  10. `rendered_product_qa`

No-skip status:

- Not reached.
- Reason: harness stopped at `rendered_product_qa`.

## Eye / Ear / Brain Packet

Review packet:

- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/eye_ear_brain_review_packet.md`

It records:

- eye: rendered video stream and rendered QA contact sheet path
- ear: AAC stereo audio stream and rehearsal BGM source
- brain: technical rehearsal status, QA blocker, and remaining approval limitations

## Final Artifact Check

Artifact:

- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/final_artifact_check.json`

Result:

- `status=ok`
- `ffprobe_has_video=true`
- `ffprobe_has_audio=true`
- `duration_sec=41.0`
- `rendered_product_qa_pass=false`
- `harness_stop_gate=rendered_product_qa`
- `harness_stop_reason=rendered product QA failed`
- `no_skip_reached=false`

## Commands And Exit Codes

- `C:\Users\user\miniconda3\python.exe <precheck/copy command>`: exit `0`
- `C:\Users\user\miniconda3\python.exe -c <initial multiline render attempt>`: exit `1`
  - Packaging failure: PowerShell quoting caused a Python `SyntaxError`; no render result was claimed from this attempt.
- `C:\Users\user\miniconda3\python.exe .tmp\real_graduation_render_owner_rehearsal_20260709-061555\render_owner_execute.py`: exit `0`
- `ffprobe -v error -show_entries format=duration -show_streams -of json .tmp\real_graduation_render_owner_rehearsal_20260709-061555\run\final.mp4`: exit `0`
- `C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run .tmp\real_graduation_render_owner_rehearsal_20260709-061555\run --out-dir .tmp\real_graduation_render_owner_rehearsal_20260709-061555\rendered_qa --json`: exit `1`
- `C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run .tmp\real_graduation_render_owner_rehearsal_20260709-061555\run --source-root <real-source-root> --mode render-rehearsal --out-dir .tmp\real_graduation_render_owner_rehearsal_20260709-061555\harness_render --json`: exit `0`
- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace`: exit `0`
- `C:\Users\user\miniconda3\python.exe -c <final artifact check assertion>`: exit `0`
- `C:\Users\user\miniconda3\python.exe -c <first UTF-8 artifact check attempt>`: exit `1`
  - Packaging failure: inline newline escaping caused a Python `SyntaxError`; no artifact corruption was reported from this attempt.
- `C:\Users\user\miniconda3\python.exe - <UTF-8 artifact check script>`: exit `0`
  - Checked 52 generated JSON/Markdown/SRT/text/script artifacts.
- `git diff --check`: exit `0`
  - Existing CRLF warnings were printed for unrelated dirty-tree files.

The rendered QA acceptance command did not meet the work-order expected exit code because the candidate failed QA. This is reported as a real blocker, not bypassed.

## Deviations And Blockers

Deviations:

- A first inline PowerShell/Python render attempt failed due command quoting. The successful render used a run-local owner-root script to avoid command packaging ambiguity.
- The candidate duration is about 41 seconds. The work order delegated shortening/simplification if execution required it, with duration recorded.

Blockers:

- `rendered_product_qa` blocks on missing rendered frame evidence for title/effect lifecycle QA.
- Harness render-rehearsal stops at the same `rendered_product_qa` gate.
- No-skip was not reached.
- Product-level approvals remain absent: story/material, transcript, legal/music, and delivery approval.

## Advisory Next Work

Next likely work is a bounded title/effect evidence repair round:

- produce rendered frame evidence that demonstrates title/effect lifecycle enter, hold, and exit behavior against the actual candidate frames
- rerun `tools/rendered_product_qa.py`
- rerun harness render-rehearsal
- only if rendered QA passes, allow the route to reach no-skip evidence

Do not run delivery gate or package delivery until rendered QA and no-skip are both satisfied and the separate human/legal/story approval blockers are intentionally resolved.

## Final output prompt

You are reviewing unverified worker evidence for Real Graduation Render Owner Rehearsal. Verify the claims and artifacts before accepting conclusions.

Report path:
- `docs/construction-guides/work-orders/2026-07-09-real-graduation-render-owner-rehearsal-report.md`

Must-read artifacts:
- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/render_owner_input_resolution.json`
- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/render_owner_rehearsal_report.json`
- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/ffprobe_final.json`
- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/rendered_qa/rendered_product_qa.json`
- `.tmp/real_graduation_render_owner_rehearsal_20260709-061555/harness_render/pipeline_execution_trace.json`

Key claims to verify:
- A fresh `final.mp4` was rendered under the owner root and was not copied from a prior final.
- ffprobe shows video and audio streams with about 41 seconds duration.
- Rendered product QA failed on `title_effect_evidence_missing`.
- Harness render-rehearsal reached `rendered_product_qa` and stopped there.
- No-skip was not reached and no delivery gate/package/approval artifact was written.

Current blocker:
- Missing rendered frame evidence for title/effect lifecycle QA.

Product-level objective:
- Advance the graduation product route from render rehearsal toward verified, no-skip, reviewable production evidence without claiming delivery approval.

Scope and stop-loss:
- Do not modify prior runs, Downloads, deliveries, provider/runtime code, or approvals. Do not waive rendered QA. Do not run delivery packaging.

Next likely work:
- Run a bounded title/effect rendered-evidence repair, then rerun rendered product QA and harness render-rehearsal. Only proceed to no-skip if rendered QA passes.
