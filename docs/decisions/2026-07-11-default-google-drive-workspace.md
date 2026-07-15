# Decision: Default Google Drive workspace

Date: 2026-07-11
Status: accepted
Scope: video_pipeline / cloud review handoff
Superpowers phase: review

## SPEC

Requirement: Use the owner's designated Google Drive folder as the default cloud workspace for review handoffs.

Why: Review media must remain easy to find across sessions without asking for the destination repeatedly.

Direction: Default to folder ID `1dCNkMOYtxUlJraumLPY8-ZIB7aoJX-fb` (`https://drive.google.com/drive/folders/1dCNkMOYtxUlJraumLPY8-ZIB7aoJX-fb`). Create a clearly named per-review subfolder unless the owner names another destination.

Non-goals: This does not authorize public sharing, delivery approval, deletion, moving existing files, or uploading unrelated artifacts.

## DO

Files / modules: This decision note only; upload artifacts remain in Google Drive and local `.tmp` handoff folders.

Function-level plan: Ground the target folder, upload only the requested review package, and read the destination folder back before reporting links.

Data / interface changes: Adds one persistent project convention: the default Drive folder URL and ID.

Migration / compatibility: Explicit folder instructions in a future request override this default.

## VERIFY

Pre-checks: Confirm the folder can be listed by the connected Google Drive account.

Tests: None; this is an external workspace convention.

Manual checks: List the created review subfolder and confirm every uploaded filename and Drive URL.

Regression risks: Uploading to Drive root, changing sharing permissions, or treating review upload as final delivery.

## Decision Notes

Accepted because: The owner explicitly designated this folder as the default cloud workspace.

Tradeoffs: A stable default improves continuity, but each upload still requires scope and write authorization.

Open questions: None.

## Git / Retrieval

Related files: `docs/decisions/2026-07-11-default-google-drive-workspace.md`

Related commits: None.

Graphify anchors: default Google Drive workspace; cloud review handoff.

Search tags: `decision-log`, `google-drive`, `cloud-workspace`, `review-handoff`, `video-pipeline`
