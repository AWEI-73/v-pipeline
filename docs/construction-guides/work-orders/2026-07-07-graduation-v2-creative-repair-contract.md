# Work Order: Graduation V2 Creative Repair Contract

Date: 2026-07-07

## Goal

Turn the user's six V1 review findings into a V2 creative repair contract and,
where current tools allow, produce a V2 review candidate from a fresh repair
run.

This is not a new product-route discovery round. Use the existing V1 technical
delivery candidate as source evidence, but do not overwrite it.

## User Review Findings To Repair

1. Narration feels like settings/labels mixed into voiceover. It should be
   story narration, not a spoken configuration sheet.
2. The newcomer section used supervisor/director imagery and felt wrong.
3. Title rail treatment stayed on the side and looked awkward. Title cards
   should be better designed, shorter, and theme-matched.
4. Music direction is acceptable if lively, but should feel more energetic and
   intentional where the training MV needs momentum.
5. Opening and closing should be self-made designed segments, not just existing
   footage plus text.
6. Supervisor speech must use the actual supervisor talking-head/source-speech
   clip, preserve its original audio, avoid narration over it, and include
   subtitles/intelligibility/mix evidence.

## Current Inputs

Read-only V1 run:

`.tmp\real_graduation_production_candidate_v1_20260707-062900\run`

Read-only source material root:

`C:\Users\user\Downloads\微電影素材\_整理後`

Read these V1 artifacts first:

- `selected_visual_clips.json`
- `module_sequence_plan.json`
- `mv_title_treatment_plan.json`
- `narration_manifest.json`
- `audio_mix_report.json`
- `music_manifest.json`
- `delivery_gate.json`
- `review_artifacts_manifest.json`

## Owner Zone

- Fresh output root under `.tmp\graduation_v2_creative_repair_<timestamp>\`
- Fresh repair run under that output root
- Fresh review artifacts under that repair run
- `docs/construction-guides/work-orders/2026-07-07-graduation-v2-creative-repair-contract-report.md`

## Forbidden Zone

- Existing V1 run contents under `.tmp\real_graduation_production_candidate_v1_20260707-062900\run`
- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `docs/` except the required report path
- `deliveries/`
- `Downloads/` writes
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Required Repair Artifacts

Inside the fresh repair run, produce:

- `v2_review_findings_input.json`
- `v2_repair_contract.json`
- `v2_story_to_material_repair_plan.json`
- `v2_narration_rewrite_plan.json`
- `v2_voice_variant_plan.json`
- `v2_supervisor_source_speech_plan.json`
- `v2_title_treatment_repair_plan.json`
- `v2_opener_closer_design_plan.json`
- `v2_music_direction_plan.json`
- `v2_effect_handoff.json` if current renderer cannot honestly render the
  requested opener/closer/title treatment
- `source_speech_preservation_report.json` if supervisor source speech is used
- `subtitle_audio_alignment_report.json` if supervisor source speech is used
- `audio_mix_report.json` if any V2 media is rendered/mixed
- `final_v2.mp4` if all repair preconditions pass
- `v2_review_packet.md`
- `v2_review_artifacts_manifest.json`

## Repair Requirements

### 1. Narration Rewrite

- Rewrite narration as story narration.
- Do not speak section labels, configuration, or production intent.
- Narration should be sparse and tied to visible moments.
- Do not narrate over the supervisor source-speech section.
- Test only two voice styles/variants, no more:
  - Variant A: warm clear Mandarin narrator
  - Variant B: firmer documentary Mandarin narrator
- Record the selected voice style and why the other variant was rejected or not
  selected.

### 2. Newcomer Material Repick

- The newcomer/opening section must use learner/training-start material, such as
  trainees, training yard, morning roll call, first operation, safety practice,
  or group preparation.
- It must not use supervisor still photos, director portrait shots, unrelated
  factory/yard B-roll, or supervisor speech material as the primary newcomer
  visual.
- If no acceptable source exists, stop with `needs_material_repick`.

### 3. MV Title Treatment Repair

- Do not keep a title rail constantly pinned on the side.
- Titles should appear briefly as a chapter intro, motion label, lower third, or
  short side-card treatment and then leave.
- Each major module needs display text, timing, placement, style, and
  implementation route.
- Plain subtitles and white cards do not satisfy this requirement.

### 4. Music Direction Repair

- Keep old source-folder music excluded as final BGM.
- Keep the V1 Jamendo track only if it fits the revised music direction; otherwise
  source a replacement with download/import/probe/license metadata.
- Desired direction: lively, energetic, training-momentum, not generic light
  background music.
- Supervisor source-speech section must duck BGM very low or use no BGM.
- Legal/music-use review remains required.

### 5. Designed Opener / Closer

- Opening should be a self-made 6-10 second designed story segment.
- Closing should be a self-made 8-12 second designed story segment.
- They may use source footage, but must be edited/designed as distinct sections,
  not plain footage plus static text.
- If current renderer cannot honestly create them, produce
  `v2_effect_handoff.json` and stop before claiming V2 render completion.

### 6. Supervisor Source-Audio Repair

- Supervisor speech section must use the supervisor's actual talking-head/source
  speech video as primary material.
- Preserve original source audio in that section.
- Do not place VoxCPM narration over that section.
- Add subtitles and intelligibility/alignment evidence.
- If the correct supervisor talking-head source cannot be identified or audio is
  unusable, stop with `supervisor_source_speech_repick_required`.

## V2 Render Permission

Render `final_v2.mp4` only if all six repair branches have either:

- a completed implementation artifact, or
- a truthful stop/handoff artifact that explains why rendering would be fake.

If V2 is rendered, keep V1 intact and write V2 outputs only in the fresh repair
run.

## Acceptance Commands

Run and report exit codes when applicable:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<v2-run>" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<v2-run>" --json
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json "<v2-run>\final_v2.mp4"
git status --short --branch --untracked-files=all
git diff --check
```

If stop-loss happens before `final_v2.mp4`, do not run media/gate commands as a
success claim. Run artifact checks showing:

- which repair branch stopped
- no V2 final candidate is claimed
- V1 run was not modified
- forbidden outputs are absent

Also run a final artifact check that prints:

- output root and repair run path
- six repair branch statuses
- voice variants tested count, must be `2`
- selected voice style
- newcomer material decision
- supervisor source-speech clip decision
- title treatment implementation or effect handoff status
- opener/closer implementation or effect handoff status
- music direction/source decision
- final media status if rendered
- delivery gate status if reached
- `story_human_review_decision.json` exists false
- UTF-8/no-corruption result

## Stop-Loss

Stop and report if:

- A repair requires editing code/tools/tests.
- V1 run would need to be overwritten.
- Supervisor talking-head/source-speech material cannot be identified.
- Subtitle/alignment evidence for preserved supervisor speech cannot be
  produced.
- Title/opener/closer design would be fake without Effect Factory/Remotion.
- Replacement or retained music cannot be justified by the V2 music direction.
- More than two voice variants are needed to continue.

## Delegated Decisions

- Exact V2 output root name.
- Whether to render `final_v2.mp4` or stop at repair/effect handoff.
- Exact revised narration text.
- Which of the two voice variants is selected.
- Exact newcomer replacement clip.
- Exact supervisor source-speech clip, if evidence supports it.
- Exact title/opener/closer visual treatment style.
- Whether to retain the V1 Jamendo track or source a new track, if evidence
  supports the decision.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-07-graduation-v2-creative-repair-contract-report.md`

The report must include:

- Output root and repair run path
- Whether `final_v2.mp4` exists
- Six repair branch statuses
- Voice variants tested, selected voice, and generated voice artifacts if any
- Newcomer material repick evidence
- Supervisor source-speech preservation/subtitle evidence or stop reason
- Title/opener/closer treatment evidence or effect handoff
- Music direction/source evidence
- Commands and exit codes
- Confirmation that V1 run was not overwritten
- Confirmation that no `story_human_review_decision.json` was written
- Deviations / blockers
- Next recommended work based only on this V2 repair run

