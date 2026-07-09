# Real Graduation Render Owner Rehearsal

## Goal

Use the render-ready graduation run as read-only input, produce a fresh rehearsal video candidate inside a new owner root, then verify it with rendered product QA, the graduation route harness in render-rehearsal mode, and no-skip evidence. This is the first real render rehearsal after the product-route, visual, effect, music/subtitle, and render-handoff gates reached `ready_for_render_rehearsal`.

This is not delivery, final creative approval, story/material approval, transcript approval, legal/music approval, or package approval.

## Owner Zone

- `.tmp/real_graduation_render_owner_rehearsal_*`
- `docs/construction-guides/work-orders/2026-07-09-real-graduation-render-owner-rehearsal-report.md`

## Forbidden Zone

- `.tmp/real_graduation_render_handoff_construction_20260709-005405/**`
- any existing `.tmp/**` run outside the fresh owner root
- `C:\Users\user\Downloads\微電影素材\_整理後/**`
- `deliveries/**`
- `video_pipeline_core/**`
- `tools/**`
- `tests/**`
- `skills/**`
- `.env`
- `.venv_voxcpm/**`
- `reference repo/**`

## Required Pieces

1. Verify the prior run is at render boundary from:
   - `docs/construction-guides/work-orders/2026-07-09-real-graduation-render-handoff-construction-report.md`
   - `.tmp/real_graduation_render_handoff_construction_20260709-005405/no_render_out/graduation_product_route_harness_result.json`
   - `.tmp/real_graduation_render_handoff_construction_20260709-005405/no_render_out/pipeline_execution_trace.json`
   - `.tmp/real_graduation_render_handoff_construction_20260709-005405/run/render_handoff.json`
2. Create a fresh owner root and fresh run copy from `.tmp/real_graduation_render_handoff_construction_20260709-005405/run`.
3. Resolve render-facing inputs from the fresh run:
   - `render_handoff.json`
   - `selected_visual_clips.json`
   - `subtitles.srt`
   - `music_manifest.json`
   - `soundtrack_probe_report.json`
   - `effect_handoff.json`
   - `title_effect_lifecycle_qa.json`
   - `deliverable_safe_script.json`
4. Write `render_owner_input_resolution.json` listing each source visual/audio/subtitle/effect input, whether it exists, whether it is copied into the fresh owner root, and why it is used.
5. Produce a run-local rehearsal video candidate named `final.mp4` in the fresh run. It must have video and audio streams. It must not be copied from a prior final or delivery candidate.
6. Write `render_owner_rehearsal_report.json` with the render command, source inputs, output path, ffprobe summary, limitations, and `final_delivery_claimed=false`.
7. Run `tools/rendered_product_qa.py --run "<fresh-run>" --out-dir "<fresh-out>\rendered_qa" --json`.
8. Run `tools/run_graduation_product_route.py --mode render-rehearsal` against the fresh run and record the resulting trace/result.
9. If the harness reaches no-skip, verify `no_skip_contract_decision.json`; if not reached, classify the stop gate.
10. Write `eye_ear_brain_review_packet.md` with concrete rehearsal observations from rendered QA/frames/ffprobe: visible structure, audio presence, subtitle/effect evidence, and remaining product-quality risks.
11. Write `final_artifact_check.json` covering prior-run immutability, candidate existence, ffprobe streams/duration, rendered QA status, harness trace depth/stage order, no-skip status, and absence of approval/delivery artifacts.

## Red-First Verification

- First run a read-only precheck proving the prior run has `render_handoff.json` with `ok=true` and harness no-render `pass=true`.
- If that cannot be proven, stop and report `prior_render_boundary_not_reproducible`.

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe`; do not use bare `python` or `pytest`.

- `C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace` expected exit code `0`
- `ffprobe -v error -show_entries format=duration -show_streams -of json "<fresh-run>\final.mp4"` expected exit code `0`
- `C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run "<fresh-run>" --out-dir "<fresh-out>\rendered_qa" --json` expected exit code `0`
- `C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run "<fresh-run>" --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --mode render-rehearsal --out-dir "<fresh-out>\harness_render" --json` expected exit code `0`; result may be pass or a truthful downstream stop, but rendered QA must be reached if `final.mp4` exists
- `C:\Users\user\miniconda3\python.exe -c "<UTF-8 artifact check for generated JSON/Markdown>"` expected exit code `0`
- `git diff --check` expected exit code `0`; existing CRLF warnings may be reported

## Stop-Loss Limits

- If source visual/audio files cannot be resolved or copied into the owner root, stop before render and report missing inputs.
- If the render command fails, stop and report the exact command, exit code, and stderr; do not write a fake candidate.
- If `final.mp4` lacks video or audio, stop before no-skip and report ffprobe evidence.
- If rendered QA fails, stop and classify; do not run delivery gate.
- If no-skip fails, report the blocking rules; do not patch no-skip or harness semantics.
- Do not write `story_human_review_decision.json`, `human_transcript_review_decision.json`, legal/music approval artifacts, delivery packages, or any statement that delivery is approved.
- Do not run `tools/write_delivery_gate_report.py` in this round unless the work order is explicitly amended later.

## Delegated Decisions

- The worker may choose the exact ffmpeg/render assembly method, as long as all inputs are traceable and the output is a fresh rehearsal candidate.
- The worker may shorten or simplify the rehearsal render if needed for execution time, but must preserve the route structure and record the duration.
- The worker may use music/subtitle-only profile and must not require VoxCPM.
- The worker may stop after truthful harness/no-skip blocker evidence instead of repairing product-quality issues in this round.

## Report Format

Start with `[WORKER REPORT - REVIEW MODE]`.

Include:

- output root and fresh run path
- prior render-boundary verification
- input resolution summary
- render command and output summary
- ffprobe video/audio/duration
- rendered QA status
- harness render-rehearsal result, trace depth, stage order, stop gate, and stop reason
- no-skip status if reached
- eye/ear/brain packet path
- commands and exit codes
- deviations and stop-loss blockers
- advisory next recommended work
- `Final output prompt`: concise index only, not a report copy. Include report path, 3-5 must-read artifacts, 4-6 key claims, current blocker, product-level objective, scope/stop-loss, and next likely work. It must frame this report as unverified evidence and require claim/artifact verification.
