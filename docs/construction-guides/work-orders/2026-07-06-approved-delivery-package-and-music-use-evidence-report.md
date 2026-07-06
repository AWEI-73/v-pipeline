# Approved Delivery Package And Music-Use Evidence Report

Date: 2026-07-06

## Delivery Package

Package path:

`C:\Users\user\Desktop\video_pipeline\deliveries\real_material_scripted_approved_20260706-200007`

Source run:

`C:\Users\user\Desktop\video_pipeline\.tmp\real_material_scripted_preproduction_20260706-185346\run`

## Commands

`C:\Users\user\miniconda3\python.exe tools\pipeline_home.py --run ".tmp\real_material_scripted_preproduction_20260706-185346\run" --json`

Exit code: 0.

Result: `DONE / complete`.

`C:\Users\user\miniconda3\python.exe tools\write_delivery_gate_report.py --run ".tmp\real_material_scripted_preproduction_20260706-185346\run" --json`

Exit code: 0.

Result: delivery gate pass=true, blocking=[], warnings=[].

Package creation command:

`@' ... '@ | C:\Users\user\miniconda3\python.exe -`

Exit code: 0.

Final package check command:

`@' ... '@ | C:\Users\user\miniconda3\python.exe -`

Exit code: 0.

## Copied Files

Copied from source run:

- `final.mp4`
- `delivery_gate.json`
- `story_human_review_decision.json`
- `operator_review_packet.md`
- `operator_review_packet.json`
- `review_contact_sheet.jpg`
- `frame_evidence.json`
- `human_preproduction_brief.json`
- `music_manifest.json`
- `sound_license_manifest.json`
- `soundtrack_probe_report.json`
- `source_speech_preservation_report.json`
- `audio_mix_report.json`
- `final_acceptance_check.json`

Created in package:

- `DELIVERY_README.md`
- `checksums.sha256`
- `ffprobe_final.json`
- `music_use_evidence.md`
- `package_manifest.json`
- `package_final_check.json`

Missing required files: none.

## Final Media

Final video:

`C:\Users\user\Desktop\video_pipeline\deliveries\real_material_scripted_approved_20260706-200007\final.mp4`

ffprobe summary:

- duration: 48.156 seconds
- streams: video + audio

Checksum:

- path: `C:\Users\user\Desktop\video_pipeline\deliveries\real_material_scripted_approved_20260706-200007\checksums.sha256`
- final.mp4 sha256: `9eba1fda14447c927642c35239e7dee66fe761cfa20d3a43101d0ec6a85d9c8f`

## Delivery Gate

Gate source:

`delivery_gate.json`

Result:

- pass: true
- blocking: none
- warnings: none
- waivers: none

## Human Approval

Approval artifact:

`story_human_review_decision.json`

Result:

- decision: `approved`
- reviewer: `human`

`pipeline_home.py` result confirmed `DONE / complete`.

## Music-Use Evidence

Music evidence files:

- `music_manifest.json`
- `sound_license_manifest.json`
- `soundtrack_probe_report.json`
- `music_use_evidence.md`

Summary:

- recorded source path: `C:\Users\user\Downloads\微電影素材\_整理後\66期學長音樂檔\1片頭.mp4`
- source type: `source_folder_audio`
- pipeline treated it as non-synthetic
- synthetic generated bed was not used
- `sound_license_manifest.json` records `legal_review_required=true`

Caveat:

This package does not make a legal conclusion and does not state license approval. Human/legal music-use review remains required before external delivery.

## Confirmation

- No render was run.
- `final.mp4` was copied unchanged from the source run.
- `story_human_review_decision.json` was copied unchanged from the source run.
- The source run was not edited.
- No code, tests, tools, skills, env files, reference repo, Downloads, branch, commit, or push operation was performed.

## Deviations

None.

## Stop-Loss

No stop-loss condition was hit. Required final media, approved human decision, passing delivery gate, DONE pipeline home state, and music evidence were all present.

## Next Recommended Work

Hand off the delivery package folder to the human operator/legal reviewer for external-delivery approval, especially music-use rights confirmation. Do not publish externally until the package's music-use caveat is resolved by a human/legal decision.
