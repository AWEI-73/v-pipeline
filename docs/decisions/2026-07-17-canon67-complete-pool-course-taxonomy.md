# Decision: Canon 67 complete-pool course taxonomy

Date: 2026-07-17  
Status: verified for owner review  
Scope: Canon 67 Stage 2 taxonomy correction and Stage 3 material handoff

## SPEC

Make the results-report film legible to an external audience by naming the
training subjects shown on screen. Preserve the existing causal story, but use
formal chapter cards and course labels in the delivered picture; keep plain
language story-job captions review-only.

Correct the material-pool premise before Stage 3. The existing 81-asset Project
Material Map is a reviewed subset, not the complete source pool. The source
inventory contains 306 files: 214 images, 88 videos and 4 non-media files. After
19 reference-only media exclusions, 283 candidate media remain; 202 of those
are outside the reviewed subset.

Folder names are retrieval priors, not ground truth. A formal course label may
be emitted only after visual evidence confirms the activity. An empty folder
cannot prove that a course was filmed.

Non-goals:

- Do not change the accepted causal story or target duration.
- Do not render, choose source windows or approve creative quality in Stage 2.
- Do not infer the complete course catalogue from folder names or seven sampled
  HEIC frames.
- Do not turn the technical act back into a one-shot-per-category checklist;
  every selected course unit still needs an establish/action/result structure.

## DO

- Extend image inventory recognition to `.heic` and `.heif`.
- Preserve the 81-asset reviewed subset while recording the 283-media complete
  candidate pool and 202 pending-review media.
- Use three visible-information layers:
  1. act/chapter card for the story level;
  2. formal course label at a visually confirmed unit entry;
  3. plain review caption only in silent storyboard/review artifacts.
- Add confirmed or reviewable units for safety morning briefing, safety
  experience, cable pulling, cable-laying experience, pole assembly, pole
  replacement, live-line work, tower integrated training, insulator cleaning,
  selected life-event units and placement preference.
- Add a distinct evidence need for the cable-laying experience family.
- Keep empty folder names as unresolved retrieval hints; never treat them as
  evidence.
- Extend the existing Material Map Skill with a large-pool coarse-to-deep
  profile: 24-asset bounded batches, representative-family review, an exception
  queue, provisional labels, hash-based reuse and ASR only for speech candidates.
- Convert HEIC/HEIF to a JPEG review proxy inside the understanding matrix while
  retaining the original source path and identity as material truth.

## VERIFY

- Real inventory read-back reports 306 total files, 214 images, 88 videos and 4
  other files.
- HEIC/HEIF regression test fails before the patch and passes after it.
- A real Canon 67 HEIC forward test produces a readable contact sheet through
  `material_understanding_matrix.py` with `proxy_kind=heic_review_jpeg`, no
  `photo_proxy_failed` risk and the original `source_photo` preserved.
- `editorial_ambiguity.py validate` returns `ok=true`, 11 segments and 47
  evidence needs with no cross-artifact errors.
- UTF-8/JSON/hash read-back passes for the Stage 2 v2 package.
- Focused tests and `git diff --check` pass.
- Owner creative approval and final delivery remain false.

## Decision Notes

The user-facing correction is not merely more labels. It restores the proper
order of operations: complete-pool inventory → material immersion → verified
course family → structured micro-story → formal label. This lets an external
viewer understand what trainees learned without allowing folder organization
to manufacture facts.

The sampled Pingtung HEIC sequence supports a bounded claim that trainees are
laying/pulling cable around a roadside manhole. It does not certify every image
or every course name in that folder, so the unit remains pending full-family
review before a formal delivery label is locked.

## Git Retrieval

- Core inventory: `video_pipeline_core/material_inventory_summary.py`
- Regression test: `tests/test_material_inventory_summary.py`
- Stage 2 package:
  `.tmp/canon67_editorial_reconstruction_v2/stage2_ambiguity_v2/`
- Search tags: Canon67, complete material pool, HEIC, course taxonomy, external
  audience labels, Stage 2, Stage 3 handoff
