# 2026-07-08 Human-Declared Music Use Policy

## Goal

Change the music branch policy so internal production, rehearsal, and review candidates can proceed when a human declares a music source usable for the project context.

The pipeline must record the human-declared basis and source evidence, but it must not claim legal approval unless a separate explicit rights artifact exists.

This is a policy/contract hardening task. Do not render media or download music.

## Background

The user clarified:

- For internal review/rehearsal, music from the source folder or user-specified music should be usable by default when the human says it is usable.
- The pipeline should not repeatedly block on legal/music rights research.
- If the user later wants to upload or publish externally, they will run or request a separate rights review/change-music step.
- Provider fallback search/download should run only when the human asks for music or no usable source/user music is available.

## Owner Zone

Editable paths:

- `video_pipeline_core/soundtrack_arranger.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `tools/soundtrack_arranger.py`
- `tools/soundtrack_flow_acceptance.py`
- `tools/video_tools.py`
- `tests/test_soundtrack_arranger.py`
- `tests/test_audio_handoff_acceptance.py`
- `tests/test_soundtrack_flow_acceptance.py`
- `docs/soundtrack-arranger-route.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-music-subtitle-only-five-minute-render-rehearsal.md`
- `docs/construction-guides/work-orders/2026-07-08-human-declared-music-use-policy-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- `deliveries\`
- Existing `.tmp\` runs
- Existing final media artifacts
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Render code and render outputs unrelated to soundtrack policy
- Story, visual-selection, transcript, VoxCPM, and effect-factory code unless a directly failing soundtrack-policy test proves the dependency
- Git branch/commit/push operations

## Required Pieces

1. Add a human-declared music-use basis to the soundtrack contract.
   - It must support source-folder audio and user/manual music.
   - It must distinguish internal/rehearsal use from external publication.
   - It must record that pipeline legal search was not performed unless it actually was.

2. Update source-root music behavior.
   - Source-root music may become internally usable when a human-declared basis is present.
   - Source-root music still needs path/source-relative evidence and soundtrack probe when mixed.
   - It must not become `license_approved=true` without explicit rights evidence.

3. Update Audio Director handoff acceptance.
   - `human_declared_allowed`, `user_asserted`, or equivalent internally allowed statuses should not block internal/rehearsal handoff.
   - `reference_only`, `provider_unavailable`, and explicit denied/not-allowed statuses must still block.
   - Missing probe, vocal conflict, missing file, and section mismatch must still block.

4. Update CLI/docs so the operator can express the policy.
   - Add or document the operator-facing field/flag/note for human-declared internal music use.
   - Keep provider fallback optional and not required when source/user music is available.

5. Update the five-minute rehearsal work order language.
   - It should require `music_use_basis` recording, not legal approval.
   - It should say external upload/publication rights review is a later human/operator step.

## Red-First Verification

Before implementation, add or run a failing test proving at least one current wrong behavior:

- Source-folder or user-provided music with a human-declared internal-use basis still blocks handoff because legal review is missing; or
- The generated soundtrack plan still marks source-folder audio as unavailable for internal rehearsal despite human declaration.

Record the failing command and failure in the report.

## Acceptance Commands

Use the pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance
```

Expected exit code: `0`.

Run the broader branch-impact set:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance tests.test_delivery_gate tests.test_pipeline_home
```

Expected exit code: `0`.

Validate registry JSON:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Expected exit code: `0`.

Run:

```powershell
git diff --check
```

Expected exit code: `0`, except existing CRLF warnings may be reported if already present.

## Stop-Loss Limits

Stop and report instead of broadening if:

- The change would require rendering, downloading music, or editing prior runs.
- The only way to pass is to mark legal approval as complete without explicit evidence.
- The change would allow `reference_only` or missing audio files into the audio mix.
- Probe/vocal-conflict gates would be bypassed.
- Source folder path is needed and cannot be verified without touching Downloads.

## Delegated Decisions

- Exact enum names for the human-declared basis, as long as they are explicit and tested.
- Whether the policy is stored in `soundtrack_plan`, `sound_license_manifest`, selected audio items, or all of them, as long as Audio Director handoff can enforce it.
- Exact CLI flag names, as long as docs and tests cover them.
- Whether existing `user_asserted` is reused or a clearer `human_declared_allowed` status is added.

## Final Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-08-human-declared-music-use-policy-report.md
```

Include:

- Files changed.
- Red-first command and failure.
- Acceptance commands and exit codes.
- The final policy fields/statuses.
- A before/after example for source-folder or user-provided music.
- Confirmation that legal approval is not claimed by pipeline unless explicit evidence exists.
- Confirmation that external publication/upload still requires human/operator rights review.
- Confirmation that no render, download, prior run edit, `.env`, Downloads, or delivery package was touched.
- Deviations, blockers, and next recommended work.
