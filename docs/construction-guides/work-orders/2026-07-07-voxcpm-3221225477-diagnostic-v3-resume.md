# Work Order: VoxCPM 3221225477 Diagnostic And V3 Resume

Date: 2026-07-07

## Goal

Diagnose the VoxCPM voice generation crash that blocked Graduation V3, then
resume only the V3 narration branch if the crash is resolved.

This is a focused repair. Do not re-run product routing, visual selection,
music selection, or story structure.

## Context Sources

- V3 run:
  `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run`
- V3 report:
  `docs/construction-guides/work-orders/2026-07-07-graduation-v3-visual-reviewed-creative-repair-report.md`
- V3 visual review artifacts already exist and passed:
  - `visual_selection_review.json`
  - `visual_selection_gate.json`
  - `visual_selection_gate_check\visual_selection_gate.json`
- V3 blocker:
  - VoxCPM runtime check passed
  - Variant A generation failed with return code `3221225477`
  - Variant B generation failed with return code `3221225477`
  - CPU retry also returned `3221225477`

## Owner Zone

- Fresh diagnostic output root under `.tmp\voxcpm_3221225477_diagnostic_v3_resume_*`
- Run-local continuation artifacts inside:
  `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run`
- `docs/construction-guides/work-orders/2026-07-07-voxcpm-3221225477-diagnostic-v3-resume-report.md`

## Forbidden Zone

- V1 run: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run`
- V2 run: `.tmp\graduation_v2_creative_repair_20260707-122858\run`
- V3 visual-selection artifacts:
  - `visual_selection_candidates.json`
  - `visual_selection_review.json`
  - `visual_selection_gate.json`
  - `visual_selection_repick_decisions.json`
  - `candidate_frames/`
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `Downloads/`
- `deliveries/`
- `.env*`
- `.venv*`
- `reference repo/`
- Git branch, commit, push, or PR operations

## Required Environment

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe
```

Use the existing VoxCPM route and runtime checks. Do not use bare `python` or
`pytest`.

## Required Diagnostic Matrix

Run probes from smallest to production-sized. Record command, exit code, output
folder, and whether a usable wav was produced.

1. Runtime check:
   - `tools\voxcpm_runtime_check.py`
   - record Python path, `ok_to_execute`, device/GPU, missing modules.
2. Minimal ASCII text:
   - one very short English sentence
   - ASCII-only output path
   - CUDA/auto first, CPU retry only if needed.
3. Minimal Chinese text:
   - one very short Chinese sentence written with UTF-8-safe method
   - ASCII-only output path.
4. V3 clean short variant A text:
   - same text intent as V3 sample, but ASCII-only output path.
5. V3 clean short variant B text:
   - same text intent as V3 sample, but ASCII-only output path.
6. Path sensitivity check:
   - compare ASCII-only temp output path versus V3 run-local output path.
7. Length sensitivity check:
   - if short text passes but V3 sample fails, test shorter split segments.
8. Device sensitivity check:
   - if CUDA/auto fails, record CPU result; if CPU fails too, stop and classify.

Do not hide failures by changing narration to meaningless text. Diagnostic text
can be short, but V3 resume must use clean audience-facing V3 narration.

## Resume Conditions

Resume V3 narration only if the diagnostic proves VoxCPM can generate clean
usable wav files for both required short variants.

If resume is allowed:

1. Generate exactly two short voice variants for V3.
2. Select one variant and generate the final V3 narration set.
3. Verify narration text/manifests/subtitles do not include setup/style words:
   - `普通話`
   - `設定`
   - `參數`
   - `voice`
   - `style`
   - `prompt`
   - `Mandarin narrator`
4. Assemble V3 final media from the existing V3 visual-selection artifacts.
5. Preserve supervisor source speech original audio; do not put VoxCPM over the
   supervisor speech section.
6. Produce `final_v3.mp4`.
7. Run `pipeline_home.py`, `write_delivery_gate_report.py`, ffprobe, and final
   artifact checks.
8. Do not write `story_human_review_decision.json`.

## Stop-Loss Limits

Stop and report without final assembly if:

- minimal ASCII text fails with `3221225477`
- minimal Chinese text fails after ASCII passes
- both CUDA/auto and CPU fail for the same minimal case
- only meaningless text can generate but V3 clean narration cannot
- passing requires editing repo code/tools/tests/provider/runtime files
- passing requires modifying V3 visual-selection artifacts
- supervisor source audio cannot be preserved

## Acceptance Commands

Expected exit code is `0` unless the work-order stop-loss says the command is
expected to fail and must be reported.

```powershell
C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out "<DIAG_OUT>\voxcpm_runtime_check.json"
C:\Users\user\miniconda3\python.exe tools\visual_selection_gate.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --out-dir "<DIAG_OUT>\v3_visual_gate_readonly" --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --json
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\final_v3.mp4"
git diff --check
```

Add a final artifact check command using the pinned Python interpreter that
prints:

- diagnostic output root
- diagnostic matrix results
- crash classification
- V3 visual-selection artifacts unchanged true/false
- two voice variants generated true/false
- clean narration text/manifests/subtitles true/false
- supervisor source audio preserved true/false
- `final_v3.mp4` exists true/false
- final video/audio stream check true/false
- `story_human_review_decision.json` exists true/false
- UTF-8/no-corruption true/false

## Delegated Decisions

- Exact diagnostic output folder name.
- Exact short diagnostic sentences, provided they are UTF-8 safe and recorded.
- Exact CPU/CUDA retry order after the required first probes.
- Exact V3 narration splitting if length sensitivity requires shorter segments.
- Whether to proceed to final assembly after diagnostics, strictly under the
  resume conditions above.

## Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-07-voxcpm-3221225477-diagnostic-v3-resume-report.md
```

Include:

- diagnostic output root
- V3 run path
- commands and exit codes
- diagnostic matrix table
- crash classification
- whether V3 resume happened
- voice variant artifacts if generated
- clean narration check
- supervisor source-audio preservation evidence if final assembly happened
- ffprobe summary if `final_v3.mp4` exists
- pipeline_home and delivery gate results
- V3 visual-selection unchanged proof
- UTF-8/no-corruption result
- deviations/blockers
- next recommended work

