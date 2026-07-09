# VoxCPM 3221225477 Diagnostic And V3 Resume Report

Date: 2026-07-07

## Summary

- Diagnostic output root: `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818`
- V3 run path: `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run`
- Resume happened: yes
- Final media: `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\final_v3.mp4`
- Delivery gate: pass, with `story_human_review_required` warning
- Pipeline home: `WAITING / human_story_review`
- `story_human_review_decision.json`: not written

## Crash Classification

The original V3 failure remains recorded in:

- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voice_variant_A\voiceover_provider_plan.json`
- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voice_variant_B\voiceover_provider_plan.json`

Both original variants recorded VoxCPM return code `3221225477`, including CPU retry evidence.

The rerun diagnostic classified the failure as a transient VoxCPM/provider process crash in the original V3 run. Runtime, minimal ASCII, minimal Chinese, V3 A/B short variants, path sensitivity, length sensitivity, and final narration generation all succeeded sequentially without repo/provider edits.

## Diagnostic Matrix

| Probe | Exit | Output | Usable wav |
| --- | ---: | --- | --- |
| runtime_check | 0 | `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\voxcpm_runtime_check.json` | n/a |
| minimal_ascii_auto | 0 | `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\probes\minimal_ascii_auto` | yes, 3.28s |
| minimal_chinese_auto | 0 | `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\probes\minimal_chinese_auto` | yes, 3.12s |
| v3_variant_a_ascii_path | 0 | `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\probes\v3_variant_a_ascii_path` | yes, 7.92s |
| v3_variant_b_ascii_path | 0 | `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\probes\v3_variant_b_ascii_path` | yes, 7.36s |
| path_sensitivity_v3_run_ascii_script | 0 | `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voice_variant_A_retry_ascii_script` | yes, 7.68s |
| v3_short_split_auto | 0 | `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\probes\v3_short_split_auto` | yes, 5.68s |
| final_v3_narration_auto | 0 | `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voiceover` | yes, 4 segments |

Detailed machine-readable summary:

- `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\diagnostic_matrix_summary.json`
- `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\final_artifact_check.json`

## Voice Artifacts

Two short V3 voice variants were generated successfully:

- Variant A: `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\probes\v3_variant_a_ascii_path\voiceover\seg01.wav`
- Variant B: `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\probes\v3_variant_b_ascii_path\voiceover\seg01.wav`

Selected final V3 narration was generated into:

- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voiceover\seg01.wav`
- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voiceover\seg02.wav`
- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voiceover\seg03.wav`
- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voiceover\seg04.wav`

Clean narration check: pass. Audible narration text, `narration_manifest.json`, and `subtitles.srt` do not include the forbidden setup/style words from the work order.

## Final Assembly Evidence

Final media:

- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\final_v3.mp4`
- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\final.mp4`

ffprobe summary:

- video: `h264`, duration `59.066992`
- audio: `aac`, duration `59.001995`

Supervisor source speech preservation:

- Source speech preserved: true
- Evidence:
  - `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\source_speech_preservation_report.json`
  - `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\audio_mix_report.json`
- The supervisor source-speech window uses original source audio and no VoxCPM narration overlap.

## Pipeline And Gate

`pipeline_home.py` result:

- status: `WAITING`
- cursor: `human_story_review`
- next: `human_review_story_to_material_map`
- reason: delivery gate passed and final video exists, but story-to-material mapping still includes agent-filled or inferred choices.

`write_delivery_gate_report.py` result:

- pass: true
- blocking: none
- warning: `story_human_review_required`
- waivers applied: none
- summary: video stream present true, audio stream present true, requires narration/music/subtitles true.

## Commands

| Command | Exit | Key result |
| --- | ---: | --- |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_runtime_check.py --out ".tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\voxcpm_runtime_check.json"` | 0 | `ok_to_execute=true`, CUDA RTX 4060 available |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ... minimal_ascii.json --device auto --execute --timeout-sec 1200` | 0 | usable wav produced |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ... minimal_chinese.json --device auto --execute --timeout-sec 1200` | 0 | usable wav produced |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ... v3_variant_a.json --device auto --execute --timeout-sec 1200` | 0 | usable wav produced |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ... v3_variant_b.json --device auto --execute --timeout-sec 1200` | 0 | usable wav produced |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ... --out-dir ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\voice_variant_A_retry_ascii_script" ...` | 0 | V3 run-local output path succeeded |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ... v3_short_split.json --device auto --execute --timeout-sec 1200` | 0 | usable wav produced |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_voiceover_provider.py ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\v3_narration_script.json" --out-dir ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --voice-style "firm documentary delivery" --device auto --execute --timeout-sec 1200` | 0 | final 4 narration wavs produced |
| pinned Python run-local assembly script | 0 | `final_v3.mp4` and `final.mp4` written |
| `C:\Users\user\miniconda3\python.exe tools\visual_selection_gate.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --out-dir ".tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\v3_visual_gate_readonly_acceptance" --json` | 0 | `pass=true`, accepted visual evidence count 3 |
| `C:\Users\user\miniconda3\python.exe tools\visual_selection_gate.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --out-dir ".tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\v3_visual_gate_readonly" --json` | 0 | work-order exact out-dir, `pass=true` |
| `C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --json` | 0 | `WAITING / human_story_review` |
| `C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run" --json` | 0 | delivery gate pass with story human review warning |
| `ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json ".tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\final_v3.mp4"` | 0 | h264 video + aac audio |
| pinned Python final artifact check | 0 | final check JSON written |
| `git diff --check` | 0 | whitespace check passed; line-ending warnings only |
| `git status --short --branch --untracked-files=all` | 0 | working tree already contains unrelated modified/untracked repo files from earlier rounds |

## Visual-Selection Unchanged Proof

Result: `UNKNOWN`, not pass.

The diagnostic pre-snapshot intended to prove V3 visual-selection artifacts were unchanged, but it recorded only protected file paths and did not record pre-resume hashes. Therefore content-level unchanged proof cannot be reconstructed after the fact.

What is still known:

- The protected V3 visual-selection artifacts still exist.
- The visual-selection gate acceptance command passed against the V3 run.
- No product routing, visual selection, music selection, or story structure rerun was performed.

This is a reporting deviation, not a claimed pass.

## UTF-8 / No Corruption

Explicit UTF-8 reads passed for:

- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\v3_narration_script.json`
- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\narration_manifest.json`
- `.tmp\graduation_v3_visual_reviewed_creative_repair_20260707-161251\run\subtitles.srt`
- `.tmp\voxcpm_3221225477_diagnostic_v3_resume_20260707-163818\diagnostic_matrix_summary.json`

No replacement characters or suspicious repeated question-mark runs were found in those checked artifacts.

## Deviations / Blockers

- Deviation: One attempted PowerShell heredoc command used invalid shell syntax and timed out before writing artifacts. It was not used as evidence.
- Deviation: Initial final assembly command hit PowerShell parsing on ffmpeg filter syntax before Python execution. Assembly was rerun using a PowerShell-native here-string into the pinned interpreter, with no raw Chinese literals in the shell script.
- Deviation: V3 visual-selection unchanged proof is `UNKNOWN` because the pre-snapshot did not capture hashes.
- Blockers: none for V3 technical candidate assembly. Human story review is still required before delivery approval.

## Next Recommended Work

Run human story-to-material review on the V3 technical candidate and, if approved by a real human reviewer, write the appropriate human review decision artifact in the existing approved-review flow. Do not treat this V3 technical gate pass as final creative approval.
