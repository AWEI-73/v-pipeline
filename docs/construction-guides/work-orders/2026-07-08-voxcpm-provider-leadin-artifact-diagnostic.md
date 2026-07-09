# 2026-07-08 VoxCPM Provider Lead-In Artifact Diagnostic

## Goal

Diagnose and harden the VoxCPM voiceover path for the repeated lead-in artifact seen after V6 regeneration. The current failure is `provider_integration_audio_leadin_artifact`: regenerated voiceover WAVs pass broad independent ASR QA, but `tools/voiceover_leadin_qa.py` still blocks because segments begin with extra tokens such as `\u6297`, `\u5eb7`, or `\u770b\u6211\u5011` before the intended script text.

This round is diagnostic and contract-hardening only. Do not assemble final media or claim a delivery candidate.

## Background Evidence

- Previous run: `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run`
- Previous report: `docs/construction-guides/work-orders/2026-07-07-v6-voiceover-regeneration-leadin-gate-report.md`
- Observed blocker: `voiceover_leadin_qa.json` pass false after VoxCPM regenerated four WAV files.
- Important limitation: `seg01` began with a suspicious `\u5eb7`-like leading sound but was not yet classified as blocking. This round must close that gap.

## Owner Zone

Editable paths:

- `video_pipeline_core/voiceover_leadin_qa.py`
- `video_pipeline_core/*voxcpm*leadin*.py`
- `video_pipeline_core/*voiceover*leadin*.py`
- `tools/*voxcpm*leadin*.py`
- `tools/*voiceover*leadin*.py`
- `tests/test_voiceover_leadin_qa.py`
- `tests/test_*voxcpm*leadin*.py`
- `tests/test_*voiceover*leadin*.py`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-voxcpm-provider-leadin-artifact-diagnostic-report.md`
- New diagnostic output root under `.tmp\voxcpm_provider_leadin_artifact_diagnostic_*`

## Forbidden Zone

Read-only paths:

- `.tmp\v6_voiceover_regeneration_leadin_gate_20260707-234956\run`
- `.tmp\graduation_v6_transcript_repair_leadin_qa_20260707-212257\run`
- `.tmp\graduation_v5_content_verify_effect_montage_20260707-200659\run`
- Any existing `.tmp\graduation_v*` or `.tmp\v6_*` run
- `Downloads\`
- `deliveries\`
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Render/final assembly tools unless only read for evidence
- Delivery gate semantics
- Git branch/commit/push operations

## Required Pieces

1. Read the previous V6 regeneration report and the current `voiceover_leadin_qa.json` from the forbidden run as evidence only.
2. Add or update red-first tests so `\u5eb7`, `\u6297`, and `\u770b\u6211\u5011` are all blocking lead-ins when they appear before the expected script start. Do not loosen existing forbidden style/control leakage checks.
3. Build a provider-level diagnostic matrix in a fresh `.tmp\voxcpm_provider_leadin_artifact_diagnostic_*` root. The matrix must test short Chinese scripts with exact expected starts, including at least:
   - text beginning with `\u9019\u4e00\u5929`
   - text beginning with `\u57fa\u672c\u8a13\u7df4`
   - punctuation variants: no punctuation, leading punctuation removed, Chinese punctuation, newline/no-newline
   - style variants: blank/minimal/neutral/calm, without known leaking phrases such as `clear narration`
   - single-segment and multi-segment inputs
   - ASCII-only output path and normal run-local output path
   - at least two repeat attempts for one failing-looking variant, to classify transient vs deterministic behavior
4. For every generated WAV, capture independent ASR transcript, first-token/first-800ms analysis, provider plan metadata, return code, device used, file size, duration, and output path.
5. Add a trim probe. Create non-destructive copied snippets trimmed by several small offsets such as 100/200/300/500 ms, then rerun lead-in checks and verify whether the expected first script word is damaged. Record this in `lead_in_trim_probe.json`.
6. Write diagnostic artifacts:
   - `voxcpm_provider_leadin_diagnostic.json`
   - `lead_in_trim_probe.json`
   - `provider_leadin_classification.json`
   - small audio snippets for human listening review, if generated
7. Classification must be one of:
   - `actual_audio_leadin_artifact`
   - `asr_false_positive_likely`
   - `prompt_or_style_leak`
   - `segmentation_or_punctuation_sensitive`
   - `transient_provider_process_issue`
   - `safe_trim_postprocess_available`
   - `provider_blocked_no_safe_fix`
   - `insufficient_evidence`
8. If a safe postprocess trim route is proposed, prove it with tests and artifacts. It must not pass by deleting the intended first syllable.
9. Write the final report with a concise matrix table, generated file paths, ASR snippets, trim outcome, classification, deviations, and the next recommended production route.

## Red-First Verification

Before implementation, run a targeted test command that fails for the missing hardening/diagnostic behavior. At minimum, prove one of these gaps red:

- `\u5eb7` before the expected text is not blocked by lead-in QA.
- A diagnostic classifier/helper does not exist.
- A trim helper cannot yet prove whether the intended first word survives.

Use only:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voxcpm_leadin_diagnostic
```

If the final test file name differs, record the delegated name in the report and keep the pinned interpreter.

## Acceptance Commands

Expected exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voxcpm_leadin_diagnostic
```

Expected: `0`.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voiceover_output_qa tests.test_source_speech_transcript_repair tests.test_pipeline_home
```

Expected: `0`.

```powershell
C:\Users\user\miniconda3\python.exe tools\<diagnostic_cli_name>.py --out-dir ".tmp\<fresh_voxcpm_leadin_diag>" --json
```

Expected: `0` if VoxCPM runtime is available. If runtime is unavailable, expected non-zero is acceptable only with a written `provider_leadin_classification.json` or report section that classifies the environment blocker and proves no final media was assembled.

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Expected: `0` if registry JSON is edited.

```powershell
git diff --check
```

Expected: `0` except existing CRLF warnings.

Final artifact check, run with pinned Python, must verify:

- Fresh diagnostic output root exists.
- `voxcpm_provider_leadin_diagnostic.json` exists.
- `lead_in_trim_probe.json` exists.
- `provider_leadin_classification.json` exists.
- No `final_v6.mp4`, `final_v7.mp4`, or new final media was assembled in the fresh diagnostic root.
- Existing V5/V6/V6-regeneration run paths were not modified.
- Generated JSON/Markdown/SRT text decodes with UTF-8 and contains no `\ufffd` or suspicious repeated literal question-mark runs.

## Stop-Loss Limits

- If VoxCPM runtime is unavailable, stop after environment evidence. Do not switch providers or synthesize fake proof.
- If VoxCPM crashes repeatedly, classify the runtime/process blocker and stop.
- If lead-in persists and no safe trim/prompt/segmentation route is proven, classify `provider_blocked_no_safe_fix`; do not assemble final media.
- Do not change QA so `\u6297`, `\u5eb7`, or `\u770b\u6211\u5011` can pass as acceptable lead-ins.
- Do not edit existing V5/V6/V6-regeneration runs to make unchanged proof easier.
- Do not write `story_human_review_decision.json`.
- Do not claim legal/music/story approval.

## Delegated Decisions

- Exact names for the new diagnostic module, CLI, and test file.
- Exact number of repeat attempts beyond the minimum.
- Exact trim durations beyond the required small-offset set.
- Choice of independent ASR model, as long as it is recorded and the command is reproducible.
- Whether to recommend prompt/style repair, punctuation/segmentation repair, safe trim postprocess, provider retry policy, or provider block, based only on evidence.
- Whether to update registry/operator docs, if a reusable diagnostic contract is introduced.

## Final Report Requirements

Write `docs/construction-guides/work-orders/2026-07-08-voxcpm-provider-leadin-artifact-diagnostic-report.md` with:

- Commands and exit codes.
- Red-first failure evidence.
- Diagnostic matrix summary.
- ASR first-token findings for each generated WAV.
- Trim probe results and whether the intended first syllable survived.
- Final classification.
- Paths to all diagnostic artifacts.
- Confirmation that no final media was assembled.
- Confirmation that V5/V6/V6-regeneration source runs were not modified.
- Deviations, blockers, and next recommended work.
