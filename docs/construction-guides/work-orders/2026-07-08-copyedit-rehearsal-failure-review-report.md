# 2026-07-08 Copyedit Rehearsal Failure Review Report

## Verdict

The rehearsal produced a technically playable MP4, but it failed as a product-quality pipeline rehearsal.

This should not be promoted to `final.mp4` or a verified preview candidate.

The failure mode is not ffmpeg anymore. The failure mode is gate weakness: several quality gates were represented by run-local JSON claims instead of visual/product verification against the reference standard.

## Evidence Reviewed

- Final media: `.tmp/copyedit_rehearsal_title_overlay_repair_20260708-181934/run/final_copyedit_rehearsal.mp4`
- Contact sheet: `.tmp/copyedit_rehearsal_failure_review_20260708-183000/contact_sheet_10s.jpg`
- Artifact summary: `.tmp/copyedit_rehearsal_failure_review_20260708-183000/artifact_summary.json`
- Run artifacts under `.tmp/copyedit_rehearsal_title_overlay_repair_20260708-181934/run`

## Gate Findings

| Gate / Claim | Result | Evidence | Finding |
| --- | --- | --- | --- |
| Media render | PASS | ffprobe shows h264 video + aac audio, 214s | Technical MP4 exists. |
| Delivery gate | FAIL | `delivery_gate.json` blocks `missing_video_candidate` | Correctly not a delivery candidate. |
| Story approval | PASS as not claimed | no `story_human_review_decision.json` | No fake human approval. |
| Transcript/source speech approval | PASS as not claimed | no `human_transcript_review_decision.json` | No fake transcript approval. |
| Music legal approval | PASS as not claimed | `legal_approval_claimed=false` | Internal-use basis only. |
| Visual selection gate | WEAK / FAIL PRODUCT | `visual_selection_review.json` reviewer is `agent_rehearsal_visual_evidence_not_human_approval` | This is not enough for product-quality visual acceptance. |
| Effect/title lifecycle | WEAK / FAIL PRODUCT | `title_effect_lifecycle_qa.json` checks timing only | It confirms enter/hold/exit timing, not visual design quality. |
| Effect factory integration | FAIL PRODUCT | final uses simple PNG overlays, not a verified effect-factory motion output | The reference-level opener/closer/effect lane was not actually exercised. |
| Reference standard alignment | FAIL / UNKNOWN | no scored comparison against reference teardown | No gate compared this render against the reference film structure, density, opener/closer, or title treatment. |
| Shot repetition / pacing | FAIL PRODUCT | contact sheet shows repeated similar shots and static sections | MP4 assembled, but edit rhythm and shot variety are weak. |
| Subtitle/title design | FAIL PRODUCT | contact sheet shows large persistent-looking bottom bands and plain text cards | This does not match the intended polished title/effect treatment. |
| Render candidate contract | FAIL | no `final.mp4`, no verified preview candidate contract | Correctly blocked by pipeline_home/delivery gate. |

## Visible Quality Problems

From the 10-second contact sheet:

- The opening is still mostly literal footage plus overlay text, not a strong designed opener.
- Several training sections repeat the same or similar scenes for too long.
- Title/subtitle treatment is utilitarian and flat; it does not look like the reference standard.
- There is a plain white text-card moment around the people/context section, which violates the direction to avoid flat card-like filler.
- The bottom caption band appears across the film and reads more like a debug overlay than designed subtitles.
- Effect factory output is not visible as a meaningful motion/effect layer.
- The story is present in text, but the edit does not visually prove the story.

## Root Cause

The work order allowed a render to proceed once run-local artifacts claimed:

- visual selections were accepted;
- title lifecycle existed;
- effect handoff existed;
- music/subtitle route was valid.

But the final candidate was not required to pass a product-level visual verification gate after render.

The pipeline currently distinguishes "artifact exists" from "artifact is product-quality" too weakly for this route.

## What Was Skipped Or Underenforced

1. Reference-standard comparison after render.
   - No check asked whether this cut resembles the benchmark in opener, pacing, title design, transitions, ending, or density.

2. Real effect-factory integration.
   - The run used simple PNG overlays to avoid ffmpeg errors.
   - That solved rendering, but did not prove the effect line.

3. Director visual review on rendered frames.
   - Visual selection accepted source evidence, but not the final edited result.
   - The final rendered composition still looks poor.

4. Subtitle/title design QA.
   - QA checked lifecycle timing, not layout quality, readability style, proportion, or whether the text treatment feels like a finished film.

5. Montage/pacing QA.
   - No gate measured repetition, static shots, dead sections, or mismatch between story beat and visual energy.

6. Verified preview candidate contract.
   - The delivery gate correctly stopped because the file was not registered as `final.mp4` or a verified preview candidate.

## Required Next Fix

Do not promote this render.

The next work should be a pipeline hardening round, not another blind render:

1. Add a rendered-frame product verification gate for rehearsal candidates.
2. Require contact-sheet review against the reference standard.
3. Require effect/title visual QA to inspect actual rendered frames, not only timing metadata.
4. Require montage/pacing QA for repeated shots and static sections.
5. Require explicit pass/fail before any `final_copyedit_rehearsal.mp4` can be promoted to verified preview candidate.

## Recommended Next Work Order Shape

Title:

```text
2026-07-08-rendered-product-quality-gate-hardening.md
```

Scope:

- Add or run a no-code/manual product verification first against this failed render.
- Then harden the pipeline route so future rehearsal renders must produce:
  - rendered contact sheet;
  - reference alignment scorecard;
  - director visual QA;
  - effect/title visual QA;
  - montage pacing QA;
  - explicit `verified_preview_candidate=false` when any of those fail.

This should happen before any new render/promotion attempt.
