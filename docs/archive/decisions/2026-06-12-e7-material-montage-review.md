# Decision: E7 Material Montage Review

Date: 2026-06-12
Status: verified
Scope: long local-material ingest and agent-authored captions

## SPEC

Keep local VLM captioning as the default. When `caption-meta` receives
`--visual-review-dir`, use an explicit two-run agent review protocol:

1. Write timestamped montage evidence and
   `material_visual_review_request.json`.
2. Return `next_action=await_material_visual_review`.
3. After `material_visual_review_verdict.json` exists, rerun the same command
   to apply captions and lineage.

## DO

- Connected the existing request builder and verdict consumer to `caption-meta`.
- Require the verdict to cover every pending asset.
- Preserve `caption_source=agent_visual_review` and agent notes.
- Accept Windows UTF-8 BOM verdict files.
- Fixed root-level ingest files being skipped because `"."` was treated as a
  hidden directory.
- Return success instead of a false wait when no assets need captions.

## VERIFY

- TDD covered await/resume, partial verdict rejection, root-level ingest,
  no-pending completion, and BOM verdicts.
- Real evidence run:
  `C:\Users\user\Desktop\video_project\e7-material-review\20260612-e7-v2`
- Agent reviewed timestamped frames at `00:05`, `00:20`, and `00:33`, then the
  rerun applied the caption and lineage to `materials_db.json`.
- Full regression: 657 tests PASS.

## Decision Notes

The agent review mode is explicit and opt-in. It does not silently replace the
existing local VLM caption path.

Search tags: `e7`, `caption-meta`, `material-montage`, `await-resume`
