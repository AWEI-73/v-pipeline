# Work Order: Source-Root Music Discovery Policy

Date: 2026-07-06

## Goal

Generalize the successful approved delivery run's music behavior into a
source-root-scoped music discovery policy.

The visible capability to prove: when a future source folder contains usable
music or audio under that same source root, the soundtrack branch can discover
and prefer it using source-relative evidence. If source-root music is absent or
fails probe, the branch can still fall back to sourceable external download
routes such as Jamendo or yt-dlp without hard-coding this run's absolute path.

This turns the approved run into a reusable happy-path pattern instead of a
one-off reference to `66期學長音樂檔\1片頭.mp4`.

## Owner Zone

- `video_pipeline_core/` soundtrack/source-music discovery modules as needed
- `tools/` soundtrack/source-music helper or CLI surfaces as needed
- `tests/` focused soundtrack/source-root music discovery tests
- `docs/soundtrack-arranger-route.md`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/construction-guides/work-orders/2026-07-06-source-root-music-discovery-policy-report.md`

## Forbidden Zone

- Render pipeline implementation
- VoxCPM / voiceover provider implementation
- Delivery gate semantics, unless only adding tests that prove existing
  artifacts remain accepted
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs
- `deliveries/`
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Required Policy

Implement or document the route so the soundtrack branch prefers music in this
order:

1. Source-root-scoped music candidates from the current run's source root.
2. Sourceable external provider/download candidates such as Jamendo or yt-dlp.
3. Synthetic/generated beds are not valid for formal delivery unless a future
   explicit agentic music provider writes source/license/generation evidence.

Source-root discovery must:

- Never hard-code a user's absolute source path.
- Search within the active `source_root` only.
- Preserve both absolute path evidence and source-relative path evidence.
- Recognize likely music folders or files using general signals such as:
  - folder names containing `音樂`, `配樂`, `music`, `bgm`, `sound`, or `audio`
  - file names containing `片頭`, `片尾`, `配樂`, `music`, `bgm`, or `theme`
  - media type audio, or video with extractable audio
- Mark selected candidates with `source_type=source_folder_audio` or an
  equivalent existing value.
- Keep music-use/legal review as a caveat, not a pass/fail legal conclusion.

## Red-First Requirements

Before implementation, add failing tests that prove:

- A fixture source root with a nested music folder is selected without
  hard-coded absolute paths.
- The selected artifact records `source_relative_path`.
- If source-root music exists, external provider fallback is not selected first.
- If source-root music is absent, the route exposes or requests the external
  fallback path rather than failing as if no music source exists.
- The output does not claim legal/license approval merely because the audio came
  from the source folder.

## Acceptance Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_arranger tests.test_soundtrack_flow_acceptance tests.test_delivery_gate tests.test_pipeline_home
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
git diff --check
```

Also run a fresh `.tmp/` smoke with a synthetic fixture source root, not the
user's Downloads folder:

- Case A: nested source-root music exists and is selected first.
- Case B: no source-root music exists and fallback intent/result is recorded.
- Print selected source type, source-relative path, and license/legal caveat.

## Stop-Loss

Stop and report without broad patching if:

- Existing soundtrack artifacts have no place to record source-relative path.
- Implementing this requires changing render, delivery gate semantics, VoxCPM,
  or provider runtime.
- The route would need to inspect or mutate the user's Downloads folder.
- The tests can only pass by hard-coding this run's folder name or audio file.
- The implementation would claim legal approval from source-folder presence
  alone.

## Delegated Decisions

- Choose the exact module/helper placement based on current soundtrack code.
- Choose whether the source-root discovery is a helper, CLI option, or branch
  planning field.
- Choose the exact candidate scoring, as long as source-root candidates are
  preferred before external fallback.
- Choose the exact artifact names/fields, as long as `source_relative_path` or
  equivalent is recorded.
- Choose the minimal docs updates needed to make the route discoverable.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-source-root-music-discovery-policy-report.md`

The report must include:

- Files changed
- Red-first evidence
- Implemented source-root discovery behavior
- Fixture smoke output root
- Case A and Case B results
- How source-relative path is recorded
- How external fallback remains available
- Legal/music-use caveat behavior
- Commands and exit codes
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this round

