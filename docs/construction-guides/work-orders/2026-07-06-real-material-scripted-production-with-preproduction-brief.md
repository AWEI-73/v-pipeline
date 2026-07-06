# Work Order: Real-Material Scripted Production With Preproduction Brief

Date: 2026-07-06

## Goal

Run a real-material scripted production candidate from the user's source folder,
using a preproduction human brief artifact to constrain the agent's creative
choices before production starts.

The visible capability to prove: the pipeline can make a more intentional
scripted technical candidate from real materials while preserving the true human
approval boundary. The run must end with review evidence and `pipeline_home.py`
at `WAITING / human_story_review`, not with a fabricated human approval.

## Owner Zone

- New output directory under `.tmp/`
- `docs/construction-guides/work-orders/2026-07-06-real-material-scripted-production-with-preproduction-brief-report.md`

## Forbidden Zone

- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs except read-only inspection
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Source Folder

Use this real source folder:

`C:\Users\user\Downloads\微電影素材\_整理後`

Preflight it first. If it is missing or has no usable media, stop and report.

## Required Preproduction Brief

Before production, write this run-local artifact:

`human_preproduction_brief.json`

It must encode these human-provided constraints:

- Primary language is Chinese.
- Do not produce mixed Chinese/English narration unless the source material
  itself requires it.
- Do not fabricate speech for a real on-camera person such as a director,
  instructor, or participant.
- Preserve real source speech when it exists and is usable.
- Use generated narration only to bridge narrative gaps or introduce context.
- Use real/sourceable music only; do not use a synthetic generated music bed.
- Mark any agent-filled story/material choice with `agent_filled=true` or
  equivalent evidence and `needs_human_confirmation=true`.
- Final human approval is reserved for the user after watching the candidate.

The brief is preproduction guidance, not `story_human_review_decision.json`.

## Required Production Shape

Create a fresh run under `.tmp/` and produce:

- `human_preproduction_brief.json`
- `story_contract.json`
- `story_to_material_map.json`
- `story_to_final_alignment_report.json`
- source speech preservation/rejection evidence if real speech is used or
  detected
- narration manifest and voiceover artifacts if narration is used
- subtitles and subtitle/audio alignment evidence
- real/sourceable music evidence, license/source metadata, and soundtrack probe
- audio mix report
- `final.mp4`
- review artifacts, including a 0.5s contact sheet or equivalent visual review
  evidence
- a concise operator review packet that summarizes:
  - story beats
  - selected source material per beat
  - agent-filled choices
  - source speech usage
  - narration lines
  - music source/license summary
  - known review risks

Do not write `story_human_review_decision.json`.

## Expected End State

After candidate creation:

- `write_delivery_gate_report.py --run <run> --json` may technically pass, but
  must include `story_human_review_required` if the story map contains
  agent-filled or inferred choices.
- `pipeline_home.py --run <run> --json` must report:
  - `WAITING`
  - `human_story_review`
  - next action `human_review_story_to_material_map`

If the candidate cannot be produced, stop at the first real blocker and report
the blocker. Do not patch code.

## Required Commands

Run and report exit codes for commands actually applicable to the chosen route,
including:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run "<run>" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run "<run>" --json
```

Also run explicit final checks that print:

- source preflight result
- output root
- final.mp4 existence and ffprobe audio/video streams if final exists
- presence/absence of `story_human_review_decision.json`
- `pipeline_home` mode/cursor/next
- `delivery_gate` pass/blocking/warnings
- review packet path
- report path

## Stop-Loss

Stop and report without patching code if:

- Source folder is missing or unreadable.
- VoxCPM, music download/probe, render, subtitle, or mix branch hits a real
  blocker.
- Any step requires writing a fake human approval.
- Any step requires modifying code, tests, tools, skills, environment, provider
  runtime, Downloads, or an existing `.tmp` run.
- The run can only pass by using synthetic music or fabricated on-camera speech.

## Delegated Decisions

- Choose the scripted story angle and beat structure, constrained by the source
  material and the preproduction brief.
- Choose clip selection, duration target, and pacing.
- Choose where generated narration is appropriate.
- Choose real/sourceable music sources and fallback order.
- Choose the exact review packet file names and layout.
- Choose whether the candidate should be 30-60s or slightly longer if the
  material requires it.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-real-material-scripted-production-with-preproduction-brief-report.md`

The report must include:

- Output root and run path
- Source preflight
- Preproduction brief path and summary
- Story/script summary
- Final video path, duration, and stream evidence
- Source speech preservation/rejection summary
- Narration summary
- Music source/license/probe summary
- Review packet path
- `pipeline_home` result
- Delivery gate result
- Confirmation that no `story_human_review_decision.json` was written
- Commands and exit codes
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this run

