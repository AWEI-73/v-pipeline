# Work Order: Scripted Delivery / Verify Gates Hardening

Date: 2026-07-06

## Goal

Turn the failures found during the scripted real-material production run into formal delivery/verify gate behavior. The next scripted run must not pass merely because it has video, audio, subtitles, music, and probes; it must also fail closed on corrupted Chinese text, subtitle/audio mismatch, missing source-speech preservation evidence, and unreviewed story-to-material inference.

This is a long task, but it is one gate-hardening round. Do not build new provider branches or run a new production cut except for focused fixtures/smokes required by acceptance.

## Background Evidence

- Broken scripted run: `.tmp/scripted_real_material_production_run_20260706-131200/run`
  - Delivery gate blocked `corrupt_narration_manifest` and `corrupt_subtitles`.
  - `script.json`, `narration_manifest.json`, and `subtitles.srt` contained repeated literal `?`.
- Repair continuation: same run after UTF-8 repair
  - `delivery_gate.json` passed.
  - `source_speech_preservation_report.json` preserved `source_speech_director.wav`.
  - `subtitle_audio_alignment_report.json` passed after text repair.
  - Several story-to-material entries remained `agent_inferred` or `needs_human_confirmation=true`, so final status should stay technical/human-review-required rather than full creative approval.
- Repo instruction was updated in `AGENTS.md` to avoid raw Chinese through PowerShell and to check both `\ufffd` and repeated `?`.

## Owner Zone

- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/final_product_verify.py`
- `tools/final_product_verify.py`
- `tools/write_delivery_gate_report.py`
- `tools/pipeline_home.py`
- `tests/test_delivery_gate.py`
- `tests/test_delivery_gate_report.py`
- `tests/test_pipeline_home.py`
- `tests/test_final_product_verify.py`
- New focused tests under `tests/` if needed
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/construction-guides/work-orders/2026-07-06-scripted-delivery-verify-gates-hardening-report.md`

## Forbidden Zone

- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs except read-only fixture inspection
- `video_pipeline_core/voiceover_provider.py`
- `video_pipeline_core/soundtrack_arranger.py`
- Music/VoxCPM provider implementation
- Git commit, branch, push, or PR operations

## Runtime

Use only:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another interpreter.

## Ordered Nodes

### Node 1: UTF-8 / CJK Artifact Gate

Add/complete delivery gate checks so Chinese-bearing artifacts fail closed when they contain repeated literal `?`, `\ufffd`, or no CJK where Chinese text is expected.

Required artifacts to cover:

- `script.json`
- `narration_manifest.json`
- `subtitles.srt`
- `subtitle_audio_alignment_report.json` where it carries subtitle/narration text

Red-first:

- Add a test fixture where `script.json`, `narration_manifest.json`, and `subtitles.srt` contain `????` but other delivery evidence is present. Confirm the current gate misses at least the script/alignment side or does not report all required blocking rules.

Expected blocking rules:

- `corrupt_script_text`
- `corrupt_narration_manifest`
- `corrupt_subtitles`
- `corrupt_subtitle_alignment`

### Node 2: Subtitle / Audio Alignment Gate

Delivery must not treat `subtitles.srt` as sufficient when subtitle text does not match the audible narration/source-speech evidence.

Add fail-closed logic using existing artifacts:

- `subtitle_audio_alignment_report.json`
- `narration_manifest.json`
- `source_speech_preservation_report.json`
- `subtitles.srt`

Required behavior:

- Missing alignment report blocks when subtitles are required and narration/source speech exists.
- Alignment report `ok=false` blocks.
- Alignment report `ok=true` still blocks if text artifacts contain corruption.
- If subtitle entries are editorial captions, they must be labeled; unlabeled generic subtitles should block or warn according to existing severity style.

Red-first:

- Add tests for missing alignment report and false alignment with generic subtitle text.

Expected blocking rules:

- `missing_subtitle_audio_alignment_report`
- `subtitle_audio_alignment_failed`
- `unlabeled_editorial_subtitles`

### Node 3: Source-Speech Preservation Gate

When a story contract or material map requires visible speaker / director / instructor speech, delivery must require either preserved source speech or a rejection report.

Required inputs:

- `story_contract.json`
- `story_to_material_map.json`
- `source_speech_preservation_report.json`
- `source_speech_rejection_report.json`
- `audio_mix_report.json`

Required behavior:

- If a beat indicates visible speaker / source speech and no preservation or rejection report exists, block.
- If preservation report says `status=preserved`, audio mix must include a `source_speech` or `preserve_original_audio` track.
- If rejection report exists, it must state a concrete unusable reason; otherwise block.
- VoxCPM narration cannot be the only evidence for a required source-speech beat.

Red-first:

- Add tests where a story contract requires source speech, final media exists, VoxCPM narration exists, but source speech evidence is missing. It must fail.

Expected blocking rules:

- `missing_source_speech_preservation_evidence`
- `source_speech_not_mixed`
- `invalid_source_speech_rejection`

### Node 4: Story-To-Material Review Status Gate

The gate should distinguish technical delivery pass from creative/story approval.

Required inputs:

- `story_contract.json`
- `story_to_material_map.json`
- `story_to_final_alignment_report.json`
- Optional human review artifact if already present in repo patterns

Required behavior:

- Agent-filled or `needs_human_confirmation=true` story mappings may still allow a technical candidate only if all technical gates pass.
- Delivery output must surface a limitation or warning such as `story_human_review_required`.
- If every required beat is only `agent_inferred` or key required beats are missing, block.
- Pipeline home should not describe this state as unqualified creative approval.

Red-first:

- Add tests for a technically complete run with agent-inferred mappings. Confirm it passes technical delivery only with warning/limitation, not silent full approval.

Expected rule names:

- `story_human_review_required`
- `missing_story_to_material_map`
- `story_required_beats_uncovered`

## Integration Requirements

- Prefer small helpers in `delivery_gate.py` for text corruption, subtitle alignment, source speech, and story map checks.
- Keep `final_product_verify` aligned if it is the better place to produce the verify bundle; delivery gate may consume that bundle if repo style already supports it.
- Do not weaken existing audio/music/narration/subtitle checks.
- Do not require human approval to pass technical delivery unless the artifact explicitly claims final creative approval.
- The repaired run may remain a technical candidate with warning/limitation, not a hard block, when only human story review is outstanding.

## Acceptance Commands

Run from repo root and record command, exit code, and tail.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_delivery_gate_report tests.test_pipeline_home tests.test_final_product_verify
```

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate
```

```powershell
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run" --json
```

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "C:\Users\user\Desktop\video_pipeline\.tmp\scripted_real_material_production_run_20260706-131200\run" --json
```

```powershell
git diff --check
```

Report content check:

```powershell
@'
from pathlib import Path
import sys
p = Path("docs/construction-guides/work-orders/2026-07-06-scripted-delivery-verify-gates-hardening-report.md")
text = p.read_text(encoding="utf-8")
required = ["UTF-8 / CJK", "Subtitle", "Source speech", "Story-to-material", "Acceptance", "Deviations", "Next recommended work"]
missing = [x for x in required if x not in text]
print({"report_exists": p.exists(), "missing": missing})
sys.exit(0 if p.exists() and not missing else 1)
'@ | C:\Users\user\miniconda3\python.exe -
```

## Stop-Loss Rules

- If a node needs a product decision about what counts as creative approval, stop that node and implement the fail-visible warning/limitation only.
- If touching `voiceover_provider.py` or music provider code seems necessary, stop and report; that is outside this gate-hardening round.
- If the repaired scripted run starts failing for unrelated media/provider reasons, keep the unit tests as acceptance and report the smoke blocker separately.

## Delegated Decisions

- Exact helper names and internal decomposition in `delivery_gate.py`.
- Whether story human-review-required is represented as `warnings` or `limitations`, provided it is visible in `delivery_gate.json` and pipeline home does not imply creative approval.
- Exact fixture construction style in tests, provided the tests are red-first and do not depend on external media.
- Whether `final_product_verify` produces a bundle consumed by delivery gate or delivery gate reads artifacts directly, provided existing repo conventions are followed.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-scripted-delivery-verify-gates-hardening-report.md`

Include:

- Files changed.
- Red-first evidence for each node.
- Implemented rule names and whether each is blocking/warning/limitation.
- Acceptance commands and exit codes.
- Result of the repaired scripted run smoke.
- Deviations/skips/blockers.
- Whether any node was stopped for product decision.
- Next recommended work grounded in these gate-hardening results.
