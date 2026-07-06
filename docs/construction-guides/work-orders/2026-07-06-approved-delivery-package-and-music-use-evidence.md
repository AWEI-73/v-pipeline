# Work Order: Approved Delivery Package And Music-Use Evidence

Date: 2026-07-06

## Goal

Package the human-approved scripted real-material candidate into a stable
delivery folder and collect music-use evidence for human/legal review.

The visible capability to prove: the approved candidate can be preserved outside
the scratch run with final media, gate evidence, human approval evidence, review
packet, checksums, and a clear music-source evidence note. This is packaging and
evidence collection only.

## Source Run

Read only:

`.tmp/real_material_scripted_preproduction_20260706-185346/run`

Required source artifacts:

- `final.mp4`
- `delivery_gate.json`
- `story_human_review_decision.json`
- `operator_review_packet.md`
- `operator_review_packet.json`
- `review_contact_sheet.jpg`
- music/source evidence artifacts present in the run

## Owner Zone

- New delivery package folder under `deliveries/`
- New output/check folder under `.tmp/`
- `docs/construction-guides/work-orders/2026-07-06-approved-delivery-package-and-music-use-evidence-report.md`

## Forbidden Zone

- `video_pipeline_core/`
- `tools/`
- `tests/`
- `skills/`
- `.env`
- `.venv_voxcpm/`
- `reference repo/`
- `Downloads/`
- Existing `.tmp/` runs, including the source run, except read-only inspection
- Existing delivery folders
- Git commit, branch, push, or PR operations

## Required Interpreter

Use this interpreter for every Python command:

`C:\Users\user\miniconda3\python.exe`

Do not use bare `python`, `pytest`, or another environment.

## Required Package Contents

Create a new timestamped delivery folder under `deliveries/`, then copy, do not
move:

- `final.mp4`
- `delivery_gate.json`
- `story_human_review_decision.json`
- `operator_review_packet.md`
- `operator_review_packet.json`
- `review_contact_sheet.jpg`
- `frame_evidence.json` if present
- `human_preproduction_brief.json` if present
- music evidence files or a copied subset sufficient to identify the source

Also create in the delivery folder:

- `DELIVERY_README.md`
- `checksums.sha256`
- `ffprobe_final.json`
- `music_use_evidence.md`
- `package_manifest.json`

## Required Evidence

`DELIVERY_README.md` must state:

- final video path
- duration and stream summary
- human approval artifact path
- delivery gate pass/blocking/warnings summary
- remaining external-delivery caveat: music-use/legal review is still human
  responsibility

`music_use_evidence.md` must state:

- the music/audio source path as recorded by the run
- whether it came from source-folder material, external download, or generated
- whether the pipeline treated it as non-synthetic
- what evidence exists
- what remains unknown for legal/use rights

Do not make a legal conclusion. Do not write "license approved" unless the run
contains explicit license approval evidence.

`package_manifest.json` must include:

- source run path
- package created time
- copied files
- checksums
- ffprobe summary
- delivery gate summary
- human approval summary
- music evidence summary

## Required Commands

Run and report exit codes:

```powershell
C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\real_material_scripted_preproduction_20260706-185346\run" --json
C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\real_material_scripted_preproduction_20260706-185346\run" --json
```

Also run final package checks that print:

- package folder
- copied required files
- missing files
- `final.mp4` sha256
- ffprobe video/audio stream summary
- delivery gate pass/blocking/warnings
- story human approval decision/reviewer
- music evidence source and remaining review caveat

## Stop-Loss

Stop and report without modifying code if:

- `final.mp4` is missing.
- `story_human_review_decision.json` is missing or is not `decision=approved`
  with `reviewer=human`.
- Delivery gate no longer passes.
- `pipeline_home.py` no longer reports `DONE / complete`.
- Music evidence cannot be found in the source run.
- Any step would require editing the source run, re-rendering, changing
  approval, or making a legal conclusion.

## Delegated Decisions

- Choose the timestamped delivery folder name.
- Choose whether to copy all music evidence files or a minimal evidence subset.
- Choose the exact manifest schema.
- Choose whether checksums include every file or only package files.
- Choose the exact wording of the music-use caveat, as long as it does not make
  a legal approval claim.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-06-approved-delivery-package-and-music-use-evidence-report.md`

The report must include:

- Delivery package path
- Source run path
- Commands and exit codes
- Copied files and missing files
- Final media ffprobe summary
- Checksums path
- Delivery gate result
- Human approval result
- Music-use evidence summary and caveat
- Confirmation that no render, code edit, approval edit, or source-run edit was
  performed
- Deviations, if any
- Stop-loss reason, if stopped
- Next recommended work grounded only in this package

