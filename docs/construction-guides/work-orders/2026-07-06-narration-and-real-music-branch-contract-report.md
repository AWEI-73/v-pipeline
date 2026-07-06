# Narration And Real Music Branch Contract Report

Date: 2026-07-06

## Summary

- Scratch output root: `.tmp/narration_real_music_branch_contract_20260706-083825`
- Scratch run: `.tmp/narration_real_music_branch_contract_20260706-083825/run`
- Source run copied from: `.tmp/parent_agent_delivery_cut_20260706-065345/run`
- Delivery gate result on scratch run: blocked, `pass=false`
- Contract result: old no-narration plus synthetic music delivery no longer passes
- Real subagents used: yes

The contract now fails closed for complete real-material delivery when
`requires_narration=false` is present without explicit real-user no-narration
approval, and when `music_manifest.json` relies on `generated_bgm.wav`,
`synthetic_generated_audio_bed`, placeholder, or reference-only music.

## Files Changed

- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/voiceover_provider.py`
- `tests/test_delivery_gate.py`
- `tests/test_voiceover_provider.py`
- `tests/test_parent_agent_delivery_contract.py`
- `docs/construction-guides/work-orders/2026-07-06-narration-and-real-music-branch-contract-report.md`

Note: the working tree already contained prior uncommitted delivery-gate and
test edits from earlier work orders. This round did not revert those changes.

## Red-First Failure

Command:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_audio_handoff_acceptance tests.test_subtitle_voiceover_handoff tests.test_voiceover_provider tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance tests.test_parent_agent_delivery_contract
```

Exit code: `1`

Failure summary:

```text
FAIL: test_old_parent_cut_no_narration_and_synthetic_music_blocks_delivery
AssertionError: True is not false
delivery gate pass=true on .tmp/parent_agent_delivery_cut_20260706-065345/run

FAIL: test_delivery_gate_blocks_synthetic_music_even_when_manifest_has_tracks
AssertionError: True is not false

FAIL: test_voxcpm_provider_does_not_fallback_by_default
AssertionError: 'legacy_edge_tts' != 'voxcpm'
```

## Contract Changes

- Complete real-material delivery now treats narration as required unless a
  real-user no-narration approval artifact or valid video-only waiver explicitly
  covers narration.
- VoxCPM is the default voiceover provider for required narration.
- VoxCPM runtime evidence is required through `voxcpm_runtime_check.json`.
- `voiceover_provider.py` no longer silently falls back by default; fallback
  must be explicitly requested.
- Delivery music must have an allowed source class and license/usage/tool
  evidence.
- `synthetic_generated_audio_bed`, `placeholder`, `reference_only`, and bare
  `generated_bgm.wav` do not satisfy delivery music.
- Music delivery requires `soundtrack_probe_report.json`.

## Green Commands

### Focused Parent Contract Tests

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_parent_agent_delivery_contract
```

Exit code: `0`

Stdout tail:

```text
Ran 3 tests in 0.210s

OK
```

### Work-Order Acceptance Tests

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_audio_handoff_acceptance tests.test_subtitle_voiceover_handoff tests.test_voiceover_provider tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance
```

Exit code: `0`

Stdout tail:

```text
Ran 89 tests in 6.391s

OK
```

### git diff check

```powershell
git diff --check
```

Exit code: `0`

Output: only pre-existing CRLF conversion warnings were printed.

## Scratch Probe

Fresh copy command exit code: `0`

Stdout tail:

```text
source_exists: True
target: C:\Users\user\Desktop\video_pipeline\.tmp\narration_real_music_branch_contract_20260706-083825\run
copied: True
```

Parent/subagent probe artifact:

- `parent_branch_dispatch_probe.json`

Subagent dispatch records:

- `subagent_dispatches/voiceover_voxcpm_prompt.md`
- `subagent_dispatches/voiceover_voxcpm_result.json`
- `subagent_dispatches/subtitle_voiceover_handoff_prompt.md`
- `subagent_dispatches/subtitle_voiceover_handoff_result.json`
- `subagent_dispatches/music_source_editor_prompt.md`
- `subagent_dispatches/music_source_editor_result.json`
- `subagent_dispatches/audio_mix_prompt.md`
- `subagent_dispatches/audio_mix_result.json`

## VoxCPM Runtime / Voiceover Branch

Runtime command:

```powershell
C:\Users\user\miniconda3\python.exe tools/voxcpm_runtime_check.py --out .tmp/narration_real_music_branch_contract_20260706-083825/run/voxcpm_runtime_check.json
```

Exit code: `1`

VoxCPM-main status:

- repo exists: `true`
- CLI exists: `true`
- GPU visible: `NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB, 576.02`
- `ok_to_execute`: `false`
- missing modules: `torch`, `torchaudio`, `transformers`

VoxCPM execute status:

- `tools/voxcpm_voiceover_provider.py` was not run.
- Reason: runtime check failed and fallback is not allowed.
- Planned command if ready was recorded in
  `subagent_dispatches/voiceover_voxcpm_result.json`.

Voiceover branch status: blocked, fail-closed.

## Subtitle / Voiceover Handoff Branch

Status: blocked.

The branch did not invoke `tools/subtitle_voiceover_handoff_accept.py` because
the scratch run lacked the correct subtitle/voiceover contract artifacts and
voiceover evidence:

- missing `subtitle_voiceover_contract.json`
- missing `caption_audit.json`
- missing `narration_manifest.json`
- missing `voiceover_provider_plan.json`
- `voxcpm_runtime_check.json` reported `ok_to_execute=false`
- `audio_mix_report.json` had `narration_included=false`

No narration audio was fabricated.

## Music Source Branch

Status: blocked.

The music source editor found no valid `user_provided`, `source_folder_audio`,
licensed/provider, or explicit agentic music-generation source. The only
run-local music evidence was `generated_bgm.wav` with
`source_type=synthetic_generated_audio_bed`.

Music branch blocker:

- `music_source_unavailable`

No local synthetic music was accepted as delivery music.

## Audio Mix Branch

Status: blocked / not mixed.

Reason: valid VoxCPM narration audio and valid delivery music source/probe were
not available. The branch did not mux a new delivery audio track.

Recorded blockers included:

- `voiceover_provider_unavailable`
- `synthetic_music_not_delivery_allowed`
- `missing_soundtrack_probe_report`
- missing/blocked music source editor evidence during the branch's read window

## Delivery Gate On Scratch Run

Command:

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run "$env:CONTRACT_RUN" --json
```

Exit code: `1`

Status: `pass=false`

Remaining blockers:

- `narration_required_for_complete_real_material_delivery`
- `voiceover_provider_unavailable`
- `missing_voiceover_provider_plan`
- `missing_narration_manifest`
- `synthetic_music_not_delivery_allowed`
- `music_source_unavailable`
- `music_source_missing_license_metadata`
- `missing_soundtrack_probe_report`
- `narration_not_mixed`

The scratch run delivery gate did not let the old synthetic/no-narration state
pass.

## Deviations, Skips, Blockers

- VoxCPM execute was skipped because the pinned runtime failed the check.
- No fallback TTS provider was used.
- No valid music source was found; no music was downloaded or fabricated.
- No delivery waiver was used.
- No code/tests/tools outside the owner zone were edited.
- `reference repo/VoxCPM-main`, `Downloads`, `skills`, and existing `.tmp` runs
  were not modified.

## Next Recommended Work

Install/connect a VoxCPM runtime for the pinned provider route, then supply or
select a valid delivery music source with license/source metadata and
soundtrack probe evidence. After those are available, rerun the parent/subagent
continuation from a fresh scratch copy and only then remix narration/music into
the delivery candidate.
