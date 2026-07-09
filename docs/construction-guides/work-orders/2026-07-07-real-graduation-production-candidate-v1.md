# Work Order: Real Graduation Production Candidate V1

Date: 2026-07-07

## Goal

Produce a real graduation training film candidate from the approved
product-route handoff, with three product corrections:

1. Replace the old source-folder music path instead of reusing the existing
   `66期學長音樂檔` BGM.
2. Make the training MV module order story-driven, not fixed to the catalog
   listing order.
3. Add designed module title treatments, such as side title cards or chapter
   treatments, styled to match the story theme.

The visible capability to prove: the pipeline can use the film-canon product
route to create a reviewable `final.mp4` candidate or stop at a truthful
branch blocker without silently falling back to the old test-video behavior.

## Current Inputs

Read-only source material root:

`C:\Users\user\Downloads\微電影素材\_整理後`

Read-only approved product-route handoff root:

`.tmp\product_route_review_writer_20260707-061959\graduation_approved`

Required handoff file:

`.tmp\product_route_review_writer_20260707-061959\graduation_approved\production_worker_handoff_prompt.md`

PowerShell may display Chinese text as mojibake. Validate text artifacts with
explicit UTF-8 reads before declaring corruption.

## Owner Zone

- Fresh output root under `.tmp\real_graduation_production_candidate_v1_<timestamp>\`
- Fresh run folder under that output root
- Fresh subagent / branch records under that run folder
- Fresh review artifacts under that run folder
- `docs/construction-guides/work-orders/2026-07-07-real-graduation-production-candidate-v1-report.md`

## Forbidden Zone

- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `docs/` except the required final report path
- `deliveries/`
- Existing `.tmp/` runs, including the product-route handoff root
- `Downloads/` writes
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Required Production Artifacts

Inside the fresh run, produce or explicitly stop before claiming them:

- `source_preflight.json`
- `product_route_handoff_utf8_check.json`
- `story_theme_selection.json`
- `module_sequence_plan.json`
- `story_to_material_map.json`
- `mv_title_treatment_plan.json`
- `opener_closer_design_plan.json`
- `music_source_policy.json`
- `music_source_candidates.json`
- `sound_license_manifest.json`
- `soundtrack_probe_report.json`
- `source_speech_preservation_report.json` if preserving source speech
- `subtitle_audio_alignment_report.json` if subtitles/narration/source speech are used
- `audio_mix_report.json`
- `final.mp4` if all preconditions pass
- `final_media_ffprobe.json`
- `review_artifacts_manifest.json`
- `frame_evidence.json`
- `delivery_gate.json` or delivery-gate report output if final candidate exists

## Music Replacement Rule

Do not use `66期學長音樂檔` or old source-folder music as final BGM.

Allowed:

- Treat old source-folder music as reference only.
- Select external/sourceable music through the music branch, such as Jamendo,
  Pixabay, or yt-dlp fallback if supported by the current repo environment.
- Use a newly downloaded/imported/probed track only if license/source metadata is
  recorded and the soundtrack probe passes.

Stop before final mix/render if no valid replacement music is available. Do not
silently fall back to old source-folder BGM or synthetic generated bed.

## Story-Driven MV Sequence Rule

The catalog modules are a material pool, not a fixed edit order.

`module_sequence_plan.json` must state:

- selected story theme
- selected sequence model, for example growth line, memory line, challenge-first
  line, day-in-life line, or another justified structure
- ordered module groups
- rationale for ordering
- which modules are merged, weakened, optional, or used as callbacks
- where supervisor speech, teacher/class introduction, and closing story fit

The worker may reorder training modules if the story logic explains it.

## Designed Module Title Treatment Rule

`mv_title_treatment_plan.json` must cover each major MV module used in the
sequence.

For each title treatment include:

- module id
- display text, for example `基本技能`, `進階訓練`, `體能活動`
- placement, such as side rail, lower third, full-screen transition, or
  motion-card chapter break
- style tied to the selected story theme
- duration / timing target
- readability constraints
- implementation route: current renderer, Effect Factory/Remotion handoff, or
  explicit stop-loss if the effect cannot be represented honestly

Do not satisfy this requirement with plain subtitles or white title cards.

## Production Rules

- Use the approved product-route handoff as pre-render basis, but validate it
  with explicit UTF-8 before use.
- Preserve source speech only when useful and intelligible; preserved speech
  requires subtitles and mix ducking evidence.
- The opening and closing must be designed story sections, not plain white cards.
- Final delivery/story approval is still reserved for the real user after
  review. Do not write `story_human_review_decision.json`.
- Legal/music-use review remains required before external publishing.

## Stop-Loss

Stop and report without pretending success if:

- The approved product-route handoff cannot be read cleanly as UTF-8.
- Valid replacement music cannot be downloaded/imported/probed.
- The renderer cannot honestly represent the required title treatments and no
  effect handoff is produced.
- Source speech is preserved but subtitle/alignment evidence cannot be produced.
- `final.mp4` cannot be produced with video and audio streams.
- Delivery gate blocks the candidate.
- Any step would require code/tool/test edits.

## Acceptance Commands

Run and report exit codes, replacing paths as needed:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<run>" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<run>" --json
ffprobe -v error -show_entries stream=codec_type,codec_name,duration -of json "<run>\final.mp4"
git status --short --branch --untracked-files=all
git diff --check
```

If a stop-loss happens before `final.mp4`, do not run the final-media or
delivery-gate command as a success claim. Instead run artifact checks proving
the blocker and absence of forbidden outputs.

Also run a final artifact check that prints:

- output root and run path
- source preflight summary
- selected story theme and sequence model
- module sequence summary
- title treatment summary
- replacement music source, download/import evidence, and probe result
- final media streams/duration if final exists
- delivery gate pass/block status if reached
- `story_human_review_decision.json` exists false
- old `66期學長音樂檔` selected as final BGM false
- UTF-8/no-corruption result

## Delegated Decisions

- Exact story theme and sequence model.
- Exact module order and which optional modules are weakened or omitted.
- Exact title treatment visual style, as long as it is not plain subtitles or
  white cards.
- Exact external music source/provider and track choice, as long as evidence is
  recorded and old source-folder BGM is not used.
- Whether to stop with an Effect Factory handoff or render a supported basic
  title treatment if the current renderer cannot produce richer motion graphics.
- Exact fresh output root name.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-07-real-graduation-production-candidate-v1-report.md`

The report must include:

- Output root and run path
- Commands and exit codes
- Whether final candidate exists
- Music replacement evidence and confirmation that old source-folder BGM was
  not used as final BGM
- Story theme and module sequence
- Title treatment plan and implementation/effect handoff status
- Source speech/subtitle/audio mix evidence
- Delivery gate status if reached
- Review artifact paths
- Deviations / blockers
- Next recommended work based only on this run

