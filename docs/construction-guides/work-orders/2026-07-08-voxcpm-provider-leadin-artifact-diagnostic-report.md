# 2026-07-08 VoxCPM Provider Lead-In Artifact Diagnostic Report

## Summary

- Final diagnostic output root: `.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547`
- Earlier discarded diagnostic root: `.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-003746`
- Classification: `safe_trim_postprocess_available`
- Generated WAV count: 12
- Matrix cases: 11
- Final media assembled: no
- Existing V5/V6/V6-regeneration source runs modified: false
- UTF-8/no-corruption: true

The first diagnostic run exposed that the trim probe only covered one blocking case. I corrected the diagnostic helper so all blocking cases are trimmed before a safe-trim classification can be made, then reran the full diagnostic into the final root above.

## Changed Files

- `video_pipeline_core\voiceover_leadin_qa.py`
- `video_pipeline_core\voxcpm_leadin_diagnostic.py`
- `tools\voxcpm_leadin_diagnostic.py`
- `tests\test_voiceover_leadin_qa.py`
- `tests\test_voxcpm_leadin_diagnostic.py`
- `docs\branch-contract-registry.json`
- `docs\branch-contract-registry.md`
- `docs\pipeline-decision-tree.md`
- `docs\video-pipeline-operating-map.md`
- `docs\construction-guides\work-orders\2026-07-08-voxcpm-provider-leadin-artifact-diagnostic-report.md`

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voxcpm_leadin_diagnostic
```

Exit code: `1`

Failure:

- `ModuleNotFoundError: No module named 'video_pipeline_core.voxcpm_leadin_diagnostic'`

The new `康` lead-in test was added at the same time. Existing generic prefix matching already blocked that fixture, but `康` is now explicit in `EXTRA_LEADIN_TOKENS` so the contract no longer depends on indirect matching.

## Diagnostic Artifacts

- Diagnostic matrix: `.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547\voxcpm_provider_leadin_diagnostic.json`
- Trim probe: `.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547\lead_in_trim_probe.json`
- Classification: `.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547\provider_leadin_classification.json`
- Final artifact check: `.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547\final_artifact_check.json`
- Human listening snippets: `.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547\snippets\*.wav`

## Matrix Summary

| Label | Return | Lead-In QA | Detected | First token | ASR snippet |
| --- | ---: | --- | --- | --- | --- |
| `starts_zhe_yi_tian_calm_ascii_path` | 0 | fail | `康` | `康` | `康这天我们开始` |
| `starts_zhe_yi_tian_blank_style` | 0 | pass | none | `這` | `這一天我們開始` |
| `starts_zhe_yi_tian_neutral_style` | 0 | fail | `牛蟲` | `牛` | `牛蟲 这一天我们开始` |
| `starts_basic_training_blank_style` | 0 | pass | none | `時` | `時間肯定開始` |
| `starts_basic_training_calm_style` | 0 | pass | none | `空` | `空基本顺练开始` |
| `starts_basic_training_no_punctuation` | 0 | pass | none | `今` | `今本順練開始` |
| `starts_basic_training_chinese_punctuation` | 0 | pass | none | `看` | `看基本顺练 開始` |
| `starts_basic_training_newline` | 0 | fail | `抗` | `抗` | `抗基本顺脸开始` |
| `starts_basic_training_repeat_1` | 0 | pass | none | `尼` | `尼虫 基本顺练开始` |
| `starts_basic_training_repeat_2` | 0 | pass | none | `尼` | `尼丑 基本遜练开始` |
| `multi_segment_basic_training` | 0 | pass | none | `空` | `空基本顺鏈開始` |

Interpretation:

- VoxCPM runtime was available and generated all planned WAVs.
- The artifact is repeatable enough to require a provider-level repair path: multiple cases produced extra first tokens before intended text.
- Current lead-in QA now blocks the required explicit tokens `抗`, `康`, and `看我們`.
- Some suspicious first tokens such as `空`, `看`, and `尼` are visible in ASR first-token analysis but not all are blocked by the current token/prefix gate. This remains a hardening gap before production use.

## Trim Probe

The corrected trim probe tested every blocking case with 100/200/300/500ms offsets.

Safe-by-label:

- `starts_zhe_yi_tian_calm_ascii_path`: true
- `starts_zhe_yi_tian_neutral_style`: true
- `starts_basic_training_newline`: true

Representative results:

| Source label | Offset | Lead-In QA | Intended first survives | ASR snippet |
| --- | ---: | --- | --- | --- |
| `starts_zhe_yi_tian_calm_ascii_path` | 100ms | pass | false | `從這天我們開始` |
| `starts_zhe_yi_tian_calm_ascii_path` | 200ms | pass | true | `这一天我们开始` |
| `starts_zhe_yi_tian_calm_ascii_path` | 300ms | pass | true | `这一天我们开始` |
| `starts_zhe_yi_tian_calm_ascii_path` | 500ms | pass | false | `今天我們開始` |
| `starts_zhe_yi_tian_neutral_style` | 100ms | fail | false | `尼索,这一天我们开始` |
| `starts_zhe_yi_tian_neutral_style` | 200ms | fail | false | `牛蟲 这一天我们开始` |
| `starts_zhe_yi_tian_neutral_style` | 300ms | fail | false | `尿蠢 这一天我们开始` |
| `starts_zhe_yi_tian_neutral_style` | 500ms | pass | true | `这一天我们开始` |
| `starts_basic_training_newline` | 100ms | fail | false | `抗基本顺量开始` |
| `starts_basic_training_newline` | 200ms | fail | false | `抗基本顺免开始` |
| `starts_basic_training_newline` | 300ms | fail | false | `抗基本顺量开始` |
| `starts_basic_training_newline` | 500ms | pass | true | `基本顺量开始` |

Trim outcome:

- `lead_in_trim_probe.json` reports `safe_trim_available=true`.
- The evidence supports a candidate postprocess route, but it is not yet production-integrated.
- No final media was assembled from this diagnostic.

## Classification

`provider_leadin_classification.json`:

- classification: `safe_trim_postprocess_available`
- safe_for_production: true in the diagnostic schema
- matrix_count: 11
- blocking_count: 3
- next_action: `prove_postprocess_in_pipeline_before_final`

Operational reading:

- Treat this as a diagnostic finding, not permission to ship.
- A production route must add a postprocess/QA stage that applies trim conservatively, reruns independent ASR, reruns `voiceover_leadin_qa.py`, and proves intended first syllables survived for every segment.

## Commands And Exit Codes

| Command | Exit | Result |
| --- | ---: | --- |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voxcpm_leadin_diagnostic` | 1 | red-first missing diagnostic module |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voxcpm_leadin_diagnostic` | 0 | 8 tests OK |
| `C:\Users\user\miniconda3\python.exe -m unittest tests.test_voiceover_leadin_qa tests.test_voiceover_output_qa tests.test_source_speech_transcript_repair tests.test_pipeline_home` | 0 | 98 tests OK |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_leadin_diagnostic.py --out-dir ".tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-003746" --json` | 0 | first diagnostic; exposed narrow trim coverage |
| `C:\Users\user\miniconda3\python.exe tools\voxcpm_leadin_diagnostic.py --out-dir ".tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547" --json` | 0 | final diagnostic evidence |
| `C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"` | 0 | `json ok` |
| pinned Python final artifact check | 0 | final check written |
| `git diff --check` | 0 | whitespace check passed; CRLF warnings only |

## Final Artifact Check

`.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547\final_artifact_check.json`:

- fresh_diagnostic_output_root_exists: true
- `voxcpm_provider_leadin_diagnostic.json` exists: true
- `lead_in_trim_probe.json` exists: true
- `provider_leadin_classification.json` exists: true
- no final media assembled: true
- existing V5/V6/V6-regeneration runs modified: false
- UTF-8/no-corruption: true

## Deviations / Blockers

- Deviation: the first diagnostic root is superseded because the trim probe originally covered only one blocking case. The final root is `.tmp\voxcpm_provider_leadin_artifact_diagnostic_20260708-004547`.
- Blocker: current lead-in QA still does not block every suspicious ASR first token; it explicitly covers the required `抗`, `康`, and `看我們` cases.
- Blocker: safe trim is diagnostic-only. No production postprocess integration or final assembly was performed.
- Blocker: some pass cases have ASR first tokens that differ from expected first text, so human/provider review is still required before trusting the route.

## Next Recommended Work

Implement a bounded voiceover postprocess repair branch that trims only when a segment fails lead-in QA, then reruns independent ASR and `voiceover_leadin_qa.py` on every segment. The branch must prove the expected first syllable survives per segment before any V6/V7 final assembly is allowed.
