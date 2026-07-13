# Canon 67 150-Second Picture-First Longform Design

Date: 2026-07-13
Status: OWNER-APPROVED DESIGN; written-spec review pending
Owner: user
Integrator: SOL / Codex
Intended worker: a fresh Luna high-capability session

## 1. Goal

Prove that the existing Hermes Editing Loop and V Pipeline can turn a large,
heterogeneous pool of real Canon 67 source media into a coherent 150-second
picture-first candidate whose selections are driven by material evidence rather
than filename or catalog order.

This is the first long-duration test of complex material editing. It is not a
story-generation, narration, subtitle, effects, or delivery campaign.

## 2. Why This Test Is Next

The 39/44-second Canon 67 work certified bounded L0, L1, L2, and L5 shapes but
did not prove sustained selection quality. The earlier five-minute rehearsal
targeted a story/voiceover route and stopped before final assembly on
`voiceover_leadin_qa`; it therefore did not prove long picture composition.

The current source root contains 198 discovered media items at design time:
88 videos and 110 images. The control plane is now converged around one entry,
registered Capabilities, accountable execution, and integrator review. The
next useful uncertainty is whether Material Map evidence can sustain a longer,
less repetitive cut.

## 3. Approved Approach And Rejected Alternatives

### Approved: 150-second picture-first vertical slice

Build three approximately 50-second sections from real source material, with a
full-pool inventory followed by bounded deep perception and evidence-backed
selection. Use current flat `edit_decision_plan` v1, stable IDs, provenance,
and public render/verify Capabilities.

This duration is long enough to expose repetition, category imbalance, weak
transitions, and visual fatigue while remaining cheap enough for one owner
revision.

### Rejected for this campaign: direct five-to-ten-minute build

It mixes material-selection uncertainty with narration, subtitles, audio,
effects, and full-film structure. A failure would not identify which layer is
responsible and would repeat the old five-minute rehearsal's scope problem.

### Rejected for this campaign: 60-to-90-second montage

It is cheaper but too close to the already proven short slices. It would not
materially test category balance or sustained duplicate suppression.

## 4. Source Boundary

Canonical read-only source root:

`C:\Users\user\Downloads\微電影素材\_整理後`

The worker must inventory the complete discovered media pool and freeze source
paths plus SHA-256 hashes before selection. Original files must not be moved,
renamed, modified, or copied back into the source root.

The following are excluded from picture selection:

- the Canon 67 reference/final film, including any copy of
  `67期結訓影片-終.mp4`;
- `66期學長音樂檔/**`;
- `66期學長空拍影片/**`;
- generated or synthetic material;
- prior rendered candidates, contact sheets, thumbnails, and proxies;
- dialogue-led `主任勉勵/**` and `感謝導師/**` sources during this
  picture-first campaign.

Existing verified perception artifacts may be reused only when their recorded
source SHA-256 matches the frozen source. Reuse must be declared; stale or
path-only evidence is invalid.

## 5. Narrative Shape Without Generated Story Material

The candidate has exactly three stable sections:

1. `discipline_and_arrival`: safety assembly, morning discipline, group
   preparation, and physical training;
2. `technical_craft`: cable work, pole work, live-line work, equipment,
   climbing, and coordinated technical action;
3. `life_and_bonds`: class life, birthday/activity material, sports,
   volunteering, and a restrained emotional landing.

Each section targets 45-55 seconds. Total rendered duration is
150.0 seconds with a tolerance of plus or minus 0.5 seconds.

This is a functional arrangement, not a claim that filenames prove story
meaning. Every selected scene must separately record observed content and its
assigned story function.

## 6. Material Understanding And Selection

The complete pool receives deterministic inventory, media identity, source
hash, media type, and folder/category evidence. Deep visual or temporal review
may be bounded to a stratified candidate pool, but it must:

- cover at least six source categories and all three target sections;
- include both motion and still-image candidates when usable;
- avoid catalog-first or filename-first `first N` selection;
- inspect real pixels for every final still and temporal evidence for every
  final video window;
- record `observed_content`, `assigned_story_function`, evidence references,
  media window, shot scale when observable, motion/action, and source category;
- record exact duplicate and near-duplicate relationships as evidence or agent
  judgment without presenting semantic judgment as a machine metric;
- mark reference exclusion and perception-evidence reuse explicitly.

The final proposal targets 40-60 distinct stable clip IDs and at least six
source categories. A raw asset may appear only once unless the proposal marks
an intentional repeated motif and the integrator approves it. Known duplicate
or rejected material cannot enter the render-facing plan.

## 7. Loop And Human Boundaries

The first worker run stops at
`WAITING_INTEGRATOR_150S_L0_SELECTS_REVIEW` after producing the complete L0
proposal packet. It must not render the 150-second candidate before the
integrator accepts or revises the proposal.

After integrator approval, a continuation run may:

1. compile three stable section plans and one combined flat
   `edit_decision_plan` v1;
2. render section previews and the 150-second candidate through registered
   public Capabilities;
3. perform L1 and bounded L5 review;
4. stop at `WAITING_OWNER_150S_FINAL_PICTURE_VERDICT`.

Luna may decide deterministic data preparation and propose selection/order. It
may not grant picture lock, human creative approval, or final delivery.

## 8. Picture And Scratch-Audio Contract

Picture is the only creative layer under test. Original source audio is muted
in the combined candidate. A registered, preview-only scratch-music input may
be used at a deliberately low review level to make pacing observable.

The scratch input must not come from the excluded 66th-class music folder. Its
lineage, delivery restriction, and hash must be recorded. No scratch audio can
be promoted to delivery evidence. This campaign does not certify ducking,
dialogue continuity, music choice, licensing, or final mix.

No new title, subtitle, lower-third, transition family, or generated effect is
required. Existing neutral hard cuts or already registered minimal transitions
may be used only when they do not become the subject of the test.

## 9. Required Evidence

### L0 proposal packet

- frozen complete-pool inventory and exclusion report;
- reused-versus-fresh perception evidence ledger;
- candidate pool with stable IDs and source hashes;
- proposed 40-60 clip sequence grouped into the three sections;
- per-selection observed content, story function, evidence reference, source
  category, source window, and duplicate status;
- rejected and duplicate candidates with reasons;
- category, media-type, and section coverage summaries;
- contact sheets plus temporal strips for proposed video windows;
- six-field editing-loop decision record and declared blind spots.

### L1 candidate packet after approval

- approved L0 verdict copied verbatim;
- three section plans and one combined public edit-decision plan;
- render report and exact candidate SHA-256;
- actual duration, stream, decode, black-frame, and audio-policy evidence;
- distinct-clip, repeated-asset, category-balance, shot-duration, and visual
  fatigue reports;
- full-film low-density perception wall and dense strips for suspicious windows;
- stable-ID findings split into objective versus taste;
- six-field carry-forward record and final owner-verdict template.

## 10. Acceptance

### Technical PASS

- every selected source is within the canonical root and none matches an
  exclusion;
- 40-60 distinct stable clip IDs are render-facing;
- at least six source categories and all three sections are represented;
- no known duplicate/rejected asset is rendered and no raw asset repeats
  without an approved motif;
- total duration is 150.0 plus or minus 0.5 seconds and each section is within
  45-55 seconds;
- render, stream, decode, black-frame, final-product, and perception coverage
  checks pass;
- the registered Capability command, receipt, trace, and evidence lineage can
  be read back;
- `human_creative_approval=false` and `final_delivery_claimed=false`.

### Creative status

Technical PASS leaves picture quality `UNKNOWN` until the owner watches the
candidate. The owner may accept, request one bounded L1 revision, or stop the
campaign. Machine coverage and agent judgment cannot become creative approval.

## 11. Testing And Change Policy

The campaign first uses existing public Capabilities. Run existing focused
material-map, rough-cut, edit-decision, renderer, and verification checks that
touch the executed path. Do not run the full repository suite for a creative
run with no production-code change.

If a real structural gap blocks the approved flow:

1. stop without a run-local workaround;
2. identify the missing public interface and its owner;
3. obtain a bounded continuation authorization;
4. implement red-first with focused and adjacent tests;
5. run the full suite once, only after all production-code changes are complete.

One LOCAL correction is allowed per failure class. Recurrence is STRUCTURAL
and stops the affected phase.

## 12. Non-Goals

- full 9.4-minute film construction;
- story-first or generated-material fallback;
- narration, interviews, ASR, subtitles, or transcript approval;
- final music selection, dialogue ducking, SFX, or delivery audio;
- new effects, title systems, or CapCut automation;
- layered timeline v2, dirty matrix, segment rerender engine, new orchestrator,
  route runner, registry, journal, or finding engine;
- source-file relocation, deletion, or duplicate cleanup;
- human creative approval or final delivery.

## 13. Successor Decision

If the owner accepts the 150-second candidate, the next campaign adds one
dialogue/cutaway section plus ducking and approved subtitles, then extends the
accepted picture grammar toward a five-to-ten-minute three-act candidate.

If the candidate fails primarily on repetition or weak material meaning, the
next work remains in L0/L1 and deepens Material Map evidence. It must not escape
into generated story material or effects to hide the picture-selection defect.
