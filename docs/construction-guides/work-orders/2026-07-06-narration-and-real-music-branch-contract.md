# Work Order: Narration And Real Music Branch Contract

Date: 2026-07-06
Status: ready for execution

## Background

The parent delivery cut technically passed delivery gate:

- Run: `.tmp/parent_agent_delivery_cut_20260706-065345/run`
- `final.mp4`: video + audio stream
- `delivery_gate.json`: `pass=true`

Director review exposed a contract gap:

- user heard no meaningful music;
- the run used `generated_bgm.wav`, a local synthetic tone/bed;
- `requires_narration=false`;
- there was no `narration_manifest.json`;
- no VoxCPM voiceover branch was invoked.

The user's updated requirements are now hard delivery rules:

1. Voiceover/narration sections are required.
2. Music must not be self-synthesized by the parent/worker. It must come from
   a real/sourceable music branch, a user-provided/source-folder asset, a
   licensed/provider source, or an explicit agentic music-generation tool/model.
3. VoxCPM-main is the default voiceover route when narration is required.

## Goal

Close the contract gap so a parent production agent cannot pass delivery with
no narration and a locally synthesized music placeholder, and prove that the
parent/subagent path can dispatch through narration and music branches until it
either connects to valid outputs or blocks with actionable reasons.

## User-Visible Desired State

When the user asks for a complete real-material cut:

- `requires_narration=true` is enforced;
- VoxCPM-main is the default voiceover provider;
- `narration_manifest.json` must point to usable voiceover audio;
- `audio_mix_report.json` must show narration included;
- `requires_music=true` cannot be satisfied by local synthetic tone/bed;
- the music branch must record real source/provider/license/generation-tool
  evidence;
- parent/subagent dispatch records show whether narration and music branches
  connected or blocked.

## Non-Goals

- Do not make a formal final film in this round.
- Do not download unlicensed music.
- Do not invent a license.
- Do not use delivery waivers to hide missing narration/music.
- Do not modify `C:/Users/user/Downloads/`.
- Do not silently fallback from VoxCPM to another TTS provider.

## Owner Zone

The worker may edit only:

- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/voiceover_provider.py`
- `video_pipeline_core/subtitle_voiceover_handoff.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `video_pipeline_core/run_artifact_index.py` if new artifacts need indexing
- `tools/voxcpm_voiceover_provider.py`
- `tools/voxcpm_runtime_check.py`
- `tools/subtitle_voiceover_handoff_accept.py`
- `tools/soundtrack_arranger.py`
- `tools/soundtrack_flow_acceptance.py`
- `tools/soundtrack_probe.py`
- `tests/test_delivery_gate.py`
- `tests/test_audio_handoff_acceptance.py`
- `tests/test_subtitle_voiceover_handoff.py`
- `tests/test_voiceover_provider.py`
- `tests/test_soundtrack_arranger.py`
- `tests/test_soundtrack_flow_acceptance.py`
- `tests/test_parent_agent_delivery_contract.py` if a new focused test is cleaner
- `.tmp/narration_real_music_branch_contract_*/`
- `docs/construction-guides/work-orders/2026-07-06-narration-and-real-music-branch-contract-report.md`

## Forbidden Zone

These paths are read-only:

- `C:/Users/user/Downloads/`
- `.tmp/parent_agent_delivery_cut_20260706-065345/`
- `.tmp/material_first_render_video_input_support_20260706-063649/`
- `.tmp/render_readiness_asset_audit_scope_20260705-235822/`
- `reference repo/VoxCPM-main/`
- `skills/`
- `runs/`
- `examples/`

## Required Contract Changes

### Narration

For complete real-material delivery, the default requirement is:

- `requires_narration=true`
- `preferred_voiceover_provider=voxcpm`
- `fallback_allowed=false` unless an explicit artifact says otherwise

Delivery must block when:

- `delivery_requirements.json` disables narration without an explicit
  user-approved no-narration artifact;
- `narration_manifest.json` is missing, empty, or has no usable audio refs;
- `audio_mix_report.json` says `narration_included=false`;
- VoxCPM was requested but provider/runtime evidence is missing and fallback is
  not explicitly allowed.

VoxCPM-main must remain the default route:

- default repo: `reference repo/VoxCPM-main`
- default wrapper: `tools/voxcpm_voiceover_provider.py`
- runtime check: `tools/voxcpm_runtime_check.py`

### Music

For complete delivery, `requires_music=true` cannot be satisfied by local
synthetic placeholder audio.

Block if selected delivery music is any of:

- `source_type=synthetic_generated_audio_bed`
- `source_type=placeholder`
- `source_type=reference_only`
- a file named like `generated_bgm.wav` without explicit external/agentic
  generation-tool evidence;
- missing license/source metadata;
- missing `soundtrack_probe_report.json` when music is required for delivery.

Allowed music source classes:

- `user_provided`
- `source_folder_audio`
- `licensed_library`
- `youtube_audio_library`
- `pixabay_music`
- `jamendo_song`
- `suno_udio_external`
- another explicit agentic music-generation tool/model with tool name, prompt,
  output file, and usage/license notes.

If no valid source is available, the music branch must block as
`music_source_unavailable` or equivalent. Do not generate a local tone to pass.

## Required Pieces

### Piece 1: Red-First Contract Tests

Use the bad-but-currently-passing run as the behavioral reference:

`.tmp/parent_agent_delivery_cut_20260706-065345/run`

Add red-first tests proving the current system wrongly allows:

- no-narration delivery requirements for this complete real-material route;
- `generated_bgm.wav` / `synthetic_generated_audio_bed` satisfying music;
- `audio_mix_report.narration_included=false` with complete delivery pass;
- parent/subagent dispatch records that stop at artifact shape instead of
  connecting to VoxCPM and a valid music source/probe.

Run the relevant red command before implementation and record its failing
assertion in the report.

Pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_audio_handoff_acceptance tests.test_subtitle_voiceover_handoff tests.test_voiceover_provider tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance
```

If a new test file is added, include it in all commands.

### Piece 2: Contract Enforcement

Implement the minimum code changes so the red tests fail closed correctly.

Expected new or tightened blocking rules should be specific enough to route
work, for example:

- `narration_required_for_complete_real_material_delivery`
- `missing_voxcpm_runtime_check`
- `voiceover_provider_unavailable`
- `narration_not_mixed`
- `synthetic_music_not_delivery_allowed`
- `music_source_unavailable`
- `missing_soundtrack_probe_report`

Do not break existing explicit video-only waiver behavior; that waiver is a
separate route and must not silently apply here.

### Piece 3: Parent/Subagent Continuation Probe

Create a fresh scratch run:

```powershell
$STAMP = Get-Date -Format "yyyyMMdd-HHmmss"
$OUT = ".tmp/narration_real_music_branch_contract_$STAMP"
$env:SOURCE_RUN = [System.IO.Path]::GetFullPath(".tmp/parent_agent_delivery_cut_20260706-065345/run")
$env:CONTRACT_RUN = [System.IO.Path]::GetFullPath("$OUT/run")
@'
import os
import shutil
from pathlib import Path
source = Path(os.environ["SOURCE_RUN"])
target = Path(os.environ["CONTRACT_RUN"])
print("source_exists:", source.is_dir())
print("target:", target)
if not source.is_dir():
    raise SystemExit(2)
target.parent.mkdir(parents=True, exist_ok=True)
shutil.copytree(source, target)
print("copied:", target.is_dir())
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

Then run a parent/subagent dispatch probe inside this scratch run. It must
attempt, with records under `subagent_dispatches/`:

- `voiceover_voxcpm` branch: write/repair script or narration text, run
  `voxcpm_runtime_check`, then run `voxcpm_voiceover_provider` when possible;
- `subtitle_voiceover_handoff` branch: accept or block voiceover/subtitle
  evidence;
- `music_source_editor` branch: search approved local/user/provider/tool music
  sources and write source/license/probe artifacts, or block;
- `audio_mix` branch: continue only if voiceover and music branches are valid.

If the worker session has real subagent tools, use them. If not, parent-side
fallback is allowed only for the probe record, not as a way to bypass branch
requirements.

Required probe artifacts:

- `parent_branch_dispatch_probe.json`
- `subagent_dispatches/voiceover_voxcpm_prompt.md`
- `subagent_dispatches/voiceover_voxcpm_result.json`
- `subagent_dispatches/music_source_editor_prompt.md`
- `subagent_dispatches/music_source_editor_result.json`
- `subagent_dispatches/audio_mix_result.json` or an explicit not-run record

The probe passes if it either:

- reaches valid voiceover + valid music source + audio mix handoff; or
- blocks with specific missing-runtime/source reasons and no delivery pass.

### Piece 4: Re-run Gate On Scratch Run

Run:

```powershell
C:\Users\user\miniconda3\python.exe tools/write_delivery_gate_report.py --run "$env:CONTRACT_RUN" --json
```

Expected after this contract round: the old synthetic/no-narration run should
not pass unless valid narration and valid music-source evidence were actually
produced.

### Piece 5: Report

Write:

`docs/construction-guides/work-orders/2026-07-06-narration-and-real-music-branch-contract-report.md`

Include:

- files changed;
- red-first failures;
- green commands and exit codes;
- whether VoxCPM-main runtime was found/usable;
- exact VoxCPM command attempted or why it was not run;
- music source discovery result;
- whether music connected to a valid source/probe or blocked;
- parent/subagent dispatch records;
- delivery gate result on the scratch run;
- deviations/skips/blockers.

## Acceptance Commands

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_delivery_gate tests.test_audio_handoff_acceptance tests.test_subtitle_voiceover_handoff tests.test_voiceover_provider tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance
```

Expected: exit code 0.

If a new focused parent contract test file was added, run it too:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_parent_agent_delivery_contract
```

Expected: exit code 0 if the file exists.

Run:

```powershell
git diff --check
```

Expected: exit code 0, except unchanged pre-existing CRLF warnings may be
recorded.

Run this content check:

```powershell
$env:REPORT_PATH = "docs/construction-guides/work-orders/2026-07-06-narration-and-real-music-branch-contract-report.md"
@'
import os
from pathlib import Path
p = Path(os.environ["REPORT_PATH"])
text = p.read_text(encoding="utf-8")
required = ["VoxCPM", "requires_narration", "synthetic", "music_source", "subagent_dispatches", "delivery gate"]
missing = [item for item in required if item not in text]
print("report_exists:", p.exists())
print("missing:", missing)
raise SystemExit(1 if missing else 0)
'@ | C:\Users\user\miniconda3\python.exe -
```

Expected: exit code 0.

## Stop-Loss Limits

Stop and report if:

- a required fix would need editing outside owner zone;
- VoxCPM-main is missing or runtime check fails and no explicit fallback is
  allowed;
- no valid music source/provider/tool is available;
- music source would require unlicensed download or unclear rights;
- subagent dispatch cannot be recorded;
- delivery gate still passes the old synthetic/no-narration run.

## Delegated Decisions

The worker may decide:

- exact test file placement;
- exact rule names, if they are specific and routeable;
- how to structure `parent_branch_dispatch_probe.json`;
- the exact narration text used for probe scripts;
- which existing local/provider music discovery path to try first;
- whether to use real subagents or parent-side fallback for the probe when
  subagent tools are unavailable.

The worker must not decide:

- to keep no-narration as the default complete-delivery route;
- to use local synthetic tone/bed as delivery music;
- to silently fallback away from VoxCPM;
- to use unlicensed/reference-only music as delivery music;
- to claim formal delivery pass by waiver.

## Final Report Requirements

The worker's final message must include:

- changed files;
- commands with exit codes;
- red-first failure summary;
- VoxCPM-main runtime/check status;
- voiceover branch status;
- music source/editor branch status;
- subagent dispatch records;
- delivery gate result;
- explicit remaining blocker list if not fully connected;
- next recommended work grounded only in this run.
