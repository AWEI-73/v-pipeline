# Work Order: Graduation V3 Visual-Reviewed Creative Repair

Date: 2026-07-07

## Goal

Produce a fresh Graduation V3 technical review candidate that repairs the V2
creative issues reported by the user, using the new visual-selection review
branch before render-facing selection.

V3 must not overwrite V1 or V2. It is a new technical review candidate, not
final delivery approval.

## Context Sources

- V2 run:
  `.tmp\graduation_v2_creative_repair_20260707-122858\run`
- V2 report:
  `docs/construction-guides/work-orders/2026-07-07-graduation-v2-creative-repair-contract-report.md`
- Visual-selection gate report:
  `docs/construction-guides/work-orders/2026-07-07-visual-selection-gate-token-candidates-report.md`
- Visual-selection review writer report:
  `docs/construction-guides/work-orders/2026-07-07-visual-selection-review-writer-report.md`

User-observed V2 issues to repair:

1. Voiceover still speaks setup/style text before actual narration.
2. Newcomer/basic-skill visuals still look like director/supervisor photos.
3. Title treatment is improved but still looks awkward when pinned beside the
   image; module titles should be brief designed treatments, not persistent
   side rails.
4. Music is lively and broadly acceptable, but should be used deliberately:
   training MV can carry music, supervisor speech must be clean source audio,
   and opener/closer should not feel like generic music-only padding.
5. Opening/closing should be self-edited story sections, not plain source
   montage or plain cards.
6. Supervisor speech section must use the personal talking-head/source-speech
   material and original source audio; do not cover it with VoxCPM narration.

Known V2 problem candidates to explicitly review instead of silently accept:

- `newcomer_training_start`: `工安早會/IMG_2120.JPG`
- `basic_training`: `工安早會/IMG_2124.JPG`
- `supervisor_source_speech`: `主任勉勵/IMG_2141.MOV`

If the first two are still used in V3, the review artifact must explain why
they are not supervisor/director/portrait-primary visuals. If that cannot be
proven from frame evidence, mark them `needs_repick` or `rejected`.

## Owner Zone

- New fresh output root under `.tmp\graduation_v3_visual_reviewed_creative_repair_*`
- New run folder under that output root
- Run-local artifacts inside the new V3 run
- `docs/construction-guides/work-orders/2026-07-07-graduation-v3-visual-reviewed-creative-repair-report.md`

## Forbidden Zone

- V1 run: `.tmp\real_graduation_production_candidate_v1_20260707-062900\run`
- V2 run: `.tmp\graduation_v2_creative_repair_20260707-122858\run`
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

Do not use bare `python` or `pytest`.

## Required Pieces

### 1. Fresh V3 Setup

- Create a new output root and V3 run folder.
- Copy only the V2 run artifacts needed as inputs; do not modify V2.
- Record a V2 snapshot before and after to prove unchanged.
- Preserve the original source-root provenance:
  `C:\Users\user\Downloads\微電影素材\_整理後`

### 2. Visual Selection Review Before Render

- Build `visual_selection_candidates.json` for V3.
- Use `tools\write_visual_selection_review.py` or equivalent run-local JSON to
  create `visual_selection_review.json`.
- Run `tools\visual_selection_gate.py` or equivalent evaluation before render.
- Newcomer and basic-training selections must not be token-only and must not
  use supervisor/director/portrait as primary visual.
- If V2's newcomer/basic candidates are rejected, record them as
  `rejected` or `needs_repick`, then add accepted replacements with explicit
  frame/contact-sheet evidence.
- Supervisor source speech must have video, audio, and speech evidence.

### 3. Narration Repair

- Rewrite narration script so spoken text contains only audience-facing
  narration.
- Do not put voice/style/provider instructions inside script text.
- Generate exactly two short voice test variants, then one selected final
  voiceover set.
- Check generated narration manifest and subtitles for forbidden setup words,
  including: `普通話`, `設定`, `參數`, `voice`, `style`, `prompt`, `Mandarin narrator`.
- If any generated voiceover audibly or textually includes setup/style text,
  stop and report; do not hide it with mix volume.

### 4. Supervisor Speech Repair

- Supervisor speech must use the personal talking-head/source-speech clip with
  original source audio.
- No VoxCPM narration over supervisor speech.
- BGM must be muted or ducked enough for speech intelligibility.
- Subtitle/alignment evidence must be present and marked as requiring human
  transcript review if ASR-derived.

### 5. Title, Opener, Closer Repair

- Titles must be short designed treatments that appear only when needed.
- Do not use a persistent side rail for module labels.
- Do not use plain white title cards as the main opener/closer.
- Opening and closing must be self-edited story sections with visible design
  intent and story continuity.

### 6. Final V3 Assembly And Review Artifacts

- Produce `final_v3.mp4` in the V3 run.
- Keep or create `final.mp4` alias only if existing tools require it.
- Produce review artifacts:
  - 0.5s contact sheet or equivalent frame evidence
  - final ffprobe JSON
  - audio mix evidence
  - visual selection gate JSON
  - review packet markdown/json
- Do not write `story_human_review_decision.json`.

## Required Stop Conditions

Stop and report instead of forcing a pass if:

- visual-selection gate does not pass for accepted V3 selections
- clean narration cannot be generated without spoken setup/style text
- supervisor source speech cannot preserve original audio
- final media lacks video or audio stream
- delivery gate still blocks after honest V3 assembly
- passing requires changing repo code/tools/tests/provider logic

## Acceptance Commands

Expected exit code is `0` unless stated otherwise.

```powershell
C:\Users\user\miniconda3\python.exe tools\visual_selection_gate.py --run "<V3_RUN>" --out-dir "<V3_RUN>\visual_selection_gate_check" --json
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<V3_RUN>" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<V3_RUN>" --json
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json "<V3_RUN>\final_v3.mp4"
git diff --check
```

Add a final artifact check command using the pinned Python interpreter that
prints:

- V3 output root
- V2 unchanged true/false
- `visual_selection_review.json` exists true/false
- visual-selection gate pass true/false
- clean narration text check true/false
- supervisor source audio preserved true/false
- final video/audio stream check true/false
- `story_human_review_decision.json` exists true/false
- UTF-8/no-corruption true/false

## Delegated Decisions

- Exact V3 folder timestamp/name.
- Exact replacement clips for newcomer/basic, provided visual review evidence
  records why the selection is valid.
- Exact title animation style within the no-persistent-side-rail rule.
- Exact opener/closer composition, provided it is self-edited and not a plain
  card.
- Whether `final.mp4` aliases `final_v3.mp4` for tool compatibility.
- Whether delivery gate pass is achieved; if not, report the honest blockers.

## Report Requirements

Write:

```text
docs/construction-guides/work-orders/2026-07-07-graduation-v3-visual-reviewed-creative-repair-report.md
```

Include:

- output root and V3 run path
- changed files/artifacts
- V2 unchanged proof
- visual-selection review/gate results
- newcomer/basic repick decisions and evidence
- narration cleanliness check and voice variant result
- supervisor speech source-audio evidence
- title/opener/closer repair summary
- final media ffprobe summary
- pipeline_home and delivery gate results
- command exit codes
- deviations/blockers
- next recommended work
