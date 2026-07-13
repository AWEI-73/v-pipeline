# Canon 67 150-Second Hero Cut Distillation Design

Date: 2026-07-14  
Status: approved for a first-of-kind director sandbox pilot  
Owner: human creative owner  
Integrator: main-pipeline

## 1. Goal

Measure the creative ceiling of one strong director agent before asking the
factory to reproduce it. The pilot must create a materially better 150-second
edit from the same 42 accepted Canon 67 assets, preserve a frozen factory
baseline, and leave enough evidence to explain which successful decisions
could later become a Tool, Skill, Canon default, or one-off example.

The pilot is successful only when the human owner prefers the Hero Cut after
review. Technical QA, agent confidence, and reference similarity cannot grant
creative approval.

## 2. Why This Experiment Is Separate From Factory Construction

The existing pipeline has proven accountable selection, picture rendering,
still motion, subtitle binding, audio preview, and bounded L5 review. It also
limits creative execution to concepts already represented by public tools and
contracts. Building more speculative capabilities before seeing a stronger
target cut risks optimizing infrastructure that does not improve the film.

This pilot reverses the order:

```text
frozen factory baseline
-> bounded reference research
-> free but traceable director sandbox
-> human creative verdict
-> later capability distillation
```

The Hero Cut is research evidence, not a replacement production route.

## 3. Frozen Comparison Boundary

The immutable baseline is:

- candidate:
  `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/final.mp4`;
- candidate SHA-256:
  `cd4be611fe9f36916475c89ba3c5efb1dc3f73076f7cb6567093c54f8f451619`;
- accepted picture plan:
  `.tmp/canon67_150s_picture_first_longform/l1_picture_candidate/inputs/combined_rough_cut_plan.json`;
- plan SHA-256:
  `8a4dadf40dd13b74ea0f39724e61fd15eb2e7fbe304aa94467177ae839dc2c0d`.

The Hero Cut must use exactly the same 42 asset IDs. It may change source
windows within those assets, order, duration, framing, speed, transition,
still treatment, text, effects, source-audio treatment, music, and sound
design. It may not introduce another visual asset or omit an accepted asset.
Total duration remains `150.0 +/- 0.5` seconds.

## 4. Director Sandbox Boundary

One strongest-available reasoning/vision agent owns the complete creative
session from reference research through the final self-review. It may use
existing registered tools, Workbench, FFmpeg, and the repo's installed Remotion
runtime. If those surfaces cannot express a decision, it may create one-off
scripts only under:

`.tmp/canon67_150s_hero_cut/director_sandbox/**`

The agent may not modify production code, tests, Skills, registries, route
runners, factory contracts, the baseline run, or raw source media. Sandbox
scripts are not capabilities and must not be copied into production during
this pilot.

No subagent or parallel editor is allowed. Creative continuity belongs to the
single director. A cheaper worker may be used only in the later, separately
authorized distillation phase.

## 5. Bounded Internet Reference Research

Before editing, the director may inspect at most five public reference videos.
The frozen `reference_brief.json` and `reference_brief.md` must record for each:

- public URL and title;
- inspection date;
- relevant timecodes;
- observed editing technique;
- intended Canon 67 application;
- whether the resulting decision was adopted, adapted, or rejected.

References supply techniques, not media. The director may not download or
reuse reference footage, graphics, fonts, dialogue, or music.

After the brief is frozen, the director may not continue open-ended reference
search during editing. A later search is permitted only to replace an invalid
music-license candidate, and the deviation must be recorded.

## 6. Online Music Acquisition And Rights Evidence

The director may download music because the repository's current local catalog
is too narrow for a meaningful creative-ceiling test. Music must come directly
from an official library or rights-holder surface with a readable license.

Preferred sources:

1. Pixabay Music, with the track page and Pixabay Content License preserved;
2. YouTube Audio Library, with its displayed license type and copied
   attribution text when required;
3. Mixkit Music only when its stated use restrictions fit the intended review
   context.

Forbidden sources include arbitrary YouTube uploads, stream rips, reposts,
"no copyright" channels without a binding license, unverified mirrors, and
commercial songs without explicit written permission.

For every auditioned or selected track, preserve:

- title, artist, official track URL, library name, and download timestamp;
- original downloaded file and SHA-256;
- license URL and a local snapshot or screenshot of the applicable terms;
- attribution text and Content ID/certificate information when present;
- an agent assessment of allowed platforms, commercial use, attribution, and
  known restrictions.

Write `music_license_manifest.json`. A selected track remains
`delivery_allowed=false` unless the evidence explicitly covers the eventual
delivery use. Because that use is not fixed in this pilot, the Hero Cut is
review-only even when the source describes broad commercial permission.

The official guidance informing this policy is:

- YouTube Audio Library:
  `https://support.google.com/youtube/answer/3376882`;
- Pixabay Content License:
  `https://pixabay.com/service/license-summary/`;
- Mixkit License:
  `https://mixkit.co/license/`.

## 7. Creative Iteration

The director performs these bounded loops:

1. inspect the baseline and the source evidence;
2. write a baseline diagnosis and one director treatment;
3. build Hero v1;
4. inspect the rendered candidate, temporal evidence, and perception wall;
5. write stable-ID findings and build v2 only when findings justify it;
6. optionally build v3 as the final allowed revision.

Three complete Hero renders are the hard maximum. Failed technical renders do
not count as creative versions, but the same technical failure class may be
corrected only once before Stop-Loss.

The director is free to make taste decisions without a mid-loop owner gate.
Every material decision must still be recorded in
`creative_decision_trace.json` with:

- stable decision ID and affected timeline range;
- source condition and story purpose;
- before and after state;
- technique and parameters;
- reason and expected audience effect;
- evidence references;
- origin: reference-derived, agent-originated, or factory-reused;
- provisional distillation class: Tool, Skill, Canon, or one-off.

The provisional class is advisory until the owner approves the Hero Cut.

## 8. Review And Comparison

The final packet contains:

- baseline and Hero hashes;
- the Hero film and a dynamic comparison;
- a randomized owner-facing `candidate_X` / `candidate_Y` comparison;
- a sealed mapping between X/Y and baseline/Hero;
- reference brief and music-license manifest;
- creative decision trace;
- objective media-health evidence;
- director findings separated into objective and taste;
- an unset owner verdict template.

The owner first records a blind preference and comments, then the mapping may be
revealed. Possible results are:

- `HERO_PREFERRED`: proceed to a separate distillation design;
- `BASELINE_PREFERRED`: preserve findings but do not change the factory;
- `NO_CLEAR_PREFERENCE`: treat the experiment as inconclusive;
- `BOUNDED_HERO_REVISION_REQUESTED`: allow only a newly authorized focused
  revision, not an automatic fourth render.

## 9. Verification And Failure Handling

Objective verification covers input identity, exactly 42 asset IDs, duration,
decode, black frames, stream structure, source lineage, text equality where
text is used, audio levels, clipping, and music-license evidence completeness.
It does not score emotion or grant taste approval.

No full repository suite is required because the pilot must not modify
production code. Run only existing candidate/media QA and sandbox-specific
artifact validators. `git diff --check` and pre/post status must prove the repo
was not changed outside authorized new design/work-order documents.

Stop at the last green state on baseline/input drift, an unlicensed selected
track, a required production-code edit, a second occurrence of the same
technical failure class, a fourth creative render, missing decision lineage,
or inability to produce an owner-reviewable candidate.

## 10. Non-Goals

This pilot does not:

- register a new capability;
- update a Skill or Canon;
- prove transfer to different material;
- replace the formal factory route;
- claim human creative approval before owner review;
- claim final delivery or music clearance.

Capability distillation begins only after an explicit `HERO_PREFERRED` owner
verdict and receives its own design, plan, worker boundary, and transfer test.
