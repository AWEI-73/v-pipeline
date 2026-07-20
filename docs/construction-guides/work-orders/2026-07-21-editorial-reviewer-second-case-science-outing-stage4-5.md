# Work Order: Editorial Reviewer Second-Case Science-Outing Stage 4/5 A/B

Date: 2026-07-21
Status: READY
Recommended worker: Luna, maximum reasoning, fresh session
Integrator / final reviewer: SOL / Codex
Estimated size: medium, evidence-heavy; no production implementation

## 1. Goal

Run the first real transfer case for the Editorial Reviewer and the
coarse-to-deep Material Map method on a different, raw, unannotated source
pool. Produce two credible 60–90 second paper edits and silent storyboard
previews, then package them for an independent A/B editorial review.

This is a product experiment, not another infrastructure build. It asks:

1. Can the existing Stage 0–5 surfaces turn weak filenames into bounded,
   inspectable material truth without deep-reviewing every second?
2. Can two genuinely different editorial structures be made from the same
   evidence instead of producing cosmetic variants?
3. Can a fresh Reviewer identify which structure communicates progression
   more clearly before an expensive motion render?

The worker prepares evidence and candidates. The worker does not review its
own work, select a winner, mutate canonical state, or claim creative approval.

## 2. Frozen inputs

Source pool, read-only:

`C:\Users\user\Downloads\Photos-1-001`

Known inventory prior (must be independently read back):

- 71 MP4 videos;
- 8 JPG images;
- timestamp-style filenames are chronology priors, not semantic truth;
- source imagery includes children/family activity and must remain local;
- no upload, cloud copy, sharing, or external API submission is authorized.

Existing discovery aids may be reused only as coarse evidence after their
hashes are verified:

- `.tmp/reviewer_second_case_discovery/photos_1_001_v2/summary.json`
  - SHA-256 `0B1DA4FEFF41180DC2280E203856EBDB40ADBE9F84F4351BDB4942D4373971F6`
- `.tmp/reviewer_second_case_discovery/photos_1_001_v2/all_video_representative_wall.jpg`
  - SHA-256 `C249F00F78070F2FFD0BD00EEAE15AE8615FB131ABA257B76D8BA8F1FA90ED75`

The representative wall samples one frame per video. It can propose families
and exception queues; it cannot prove action progression, exact windows,
speech, identities, or final selection quality.

## 3. Required instructions and public surfaces

Read before work:

- `AGENTS.md`
- `RUNBOOK.md`
- `skills/material-map.md`, especially Quick Inventory, Large-Pool
  Coarse-to-Deep, Material Understanding Matrix, retrieval evidence, and
  storyboard preview;
- `skills/editing-loop-director.md`, especially L0 and L1;
- `skills/editorial-reviewer.md`, especially the review contract and Stage
  placement.

Prefer existing public surfaces where their contracts fit:

- `tools/material_quick_inventory.py`
- `tools/material_understanding_matrix.py`
- `tools/material_wall_verdict_draft.py`
- existing Material Map persistence/review surfaces
- existing retrieval/ranking report surface
- `tools/rough_cut_storyboard_preview.py`
- `tools/timeline_review_packet.py`
- `tools/editorial_comparison.py build-packet`

Do not add a private route runner or hide one-off production behavior in an
inline script. Small run-local inspection or report-assembly scripts may exist
only under the run root and must be disclosed with their hash; they may not
replace a fitting public capability.

## 4. Owner zone and forbidden zone

Fresh run root:

`.tmp/editorial_reviewer_second_case_science_outing_v1/`

All generated evidence, plans, previews, logs, and reports must stay below the
fresh run root.

Do not modify:

- production code, tests, Skills, registries, RUNBOOK, HANDOFF, campaign state,
  or Git history;
- source media or the existing discovery aids;
- Canon 67 artifacts or accepted Reviewer v1.1 artifacts.

Do not run the full suite. Do not commit, push, upload, install dependencies,
or call an external media/AI service.

## 5. Authority and truth rules

1. The folder and filename are priors only.
2. Do not infer names, relationships, venue identity, event ownership, or
   private facts not visible in the pixels or audible in inspected source.
3. Separate `observed_content` from `assigned_story_function` for every
   selected window.
4. A selected video window requires temporal evidence, not a single thumbnail.
5. ASR is targeted: use it only when a likely speech clip could materially
   anchor selection. Do not run full-pool ASR.
6. If the pool cannot support a proposed beat, record a `story_or_material_gap`
   and revise/defer it. Do not fill time with redundant footage.
7. The worker may make reversible editorial proposals. It may not set
   `human_creative_approval=true` or `final_delivery_claimed=true`.
8. The independent Reviewer, integrator, and Owner remain separate roles.

## 6. Provisional editorial brief

This is deliberately a weak hypothesis to be tested against material truth:

> A one-day exploration outing moves from first curiosity, through hands-on
> discovery and physical challenge, toward making/creative participation and
> a small closing memory.

Audience: a viewer who was not present and needs to understand what changed
across the outing, not merely see a folder chronology.

Prepare two credible variants, nominally 75 seconds each and always within
60–90 seconds:

- **Variant A — chronological progression**: arrival/first curiosity →
  exhibits → experiments → active challenge/play → making/quiet participation
  → closing memory.
- **Variant B — thematic progression**: observe → touch/test → challenge →
  create → remember. It may reorder chronology only when the image evidence
  makes the thematic progression clearer.

These are not cosmetic alternatives. Each must state what it opens with, what
new information each chapter adds, and how it ends differently from its start.
If either direction lacks material support, replace it with the strongest
evidence-supported alternative and record the deviation. Do not force five or
six chapters solely to match this brief.

## 7. Task sequence

### Task 0 — Preflight and frozen source manifest

1. Record branch, HEAD, `git status --short --branch`, tool versions, start
   time, and exact commands.
2. Build a complete source manifest with relative path, media type, byte size,
   duration/dimensions where applicable, timestamp prior, and SHA-256.
3. Verify the two discovery-aid hashes above. If either drifts, do not trust it;
   regenerate an equivalent coarse aid under the fresh run root.
4. Record privacy boundary `local_only_children_or_family_imagery=true`.

### Task 1 — Coarse-to-deep Material Map evidence

1. Run the existing quick inventory.
2. Inspect all 79 assets at the bounded coarse level. Reuse the verified wall
   for videos and inspect all eight still images at actual pixel level.
3. Create apparent visual/activity families, but keep them provisional until
   temporal evidence confirms them.
4. Select 15–24 high-value, conflicting, story-critical, or outlier videos for
   deep review. For each, inspect at least three spread temporal samples; use
   five where action changes or source-window choice is ambiguous.
5. Deep-review additional assets only when needed to resolve a concrete gap or
   duplicate ambiguity. Do not deep-review the complete 30-minute pool by
   default.
6. Persist a bounded project/material map with controlled fields:
   `asset_id`, source path/hash, `observed_content`, shot scale, action phase,
   confidence, evidence refs, review state, and any assigned story function.
7. Account for every asset as reviewed, provisional, deferred, duplicate, or
   excluded. No provisional label may satisfy a story beat.

### Task 2 — Two evidence-bound paper edits

1. Write one shared experimental story contract plus one segment/picture-plan
   package for each variant.
2. Select exact source windows; every window must be within source bounds and
   cite temporal evidence.
3. Prefer unique information. Reuse a source only when the second use adds a
   different action phase or story meaning, and write the reason.
4. Do not use near-duplicate activity families as separate chapters merely to
   fill duration.
5. For every chapter record:
   - factual purpose;
   - `opens_with` and `ends_with`;
   - information gain;
   - selected visual family;
   - source windows and evidence refs;
   - remaining uncertainty or material gap.
6. Run the existing retrieval/ranking gate. A manual override is allowed only
   through the existing declared override contract with reason and evidence;
   otherwise fail closed.

### Task 3 — Review-only storyboards

1. Build one silent storyboard preview per variant through the existing public
   storyboard capability.
2. Each preview must be playable, 60–90 seconds, and use review captions that
   expose chapter/clip role without asserting unverified identities.
3. The previews are paper-edit evidence, not motion-timing or render-quality
   proof. Mark them non-canonical and review-only.
4. Produce a storyboard report and a compact contact sheet/index for each.

### Task 4 — Exact-subject review packets and blind A/B packet

1. Build one `timeline_review_packet` for each storyboard with 0.5-second
   interval and 30-second wall pages.
2. Bind each packet to the exact storyboard SHA-256. Audio must remain honestly
   absent/unbound; do not synthesize or reuse unrelated soundtrack evidence.
3. Create a narrow A/B rubric asking only:
   - which variant communicates progression more clearly;
   - which has less semantic repetition;
   - which ending better fulfills the opening promise;
   - where evidence is too weak to decide.
4. Build a blinded `editorial_comparison` packet. Do not expose backend,
   maker rationale, chronology label, or which slot is A/B to the future
   Reviewer.
5. Do not fill Reviewer flags and do not select a winner in this worker run.

### Task 5 — Validation and handoff

Validate:

- 79/79 source assets accounted for and source hashes readable;
- every selected source window is in bounds and temporally evidenced;
- two distinct credible plans and playable 60–90 second storyboards exist;
- no silent hand-authored selection bypasses retrieval evidence;
- both timeline packets are exact-subject bound;
- audio evidence is absent/unbound, not falsely candidate-bound;
- blind packet contains two decodable variants and no slot leakage;
- JSON/Markdown is valid UTF-8 with no replacement characters or suspicious
  runs of four question marks where Chinese text is expected;
- `git diff --check` and final Git status show no repo mutation.

Write:

- `final/worker_report.md`
- `final/command_log.json`
- `final/artifact_sha256.json`
- `owner_review/owner_review_index.md`

The review index should open the two storyboards first, then the comparative
rubric, then Material Map evidence and gaps. Do not make the Owner read logs to
understand the editorial choice.

## 8. Stop-loss

Classify and stop on the last green state when:

- a required public surface cannot accept the existing artifact shape without
  production-code, Skill, registry, or Stage changes;
- the same failure class recurs after one LOCAL correction;
- source identity/hash cannot be established;
- privacy would require upload or an external service;
- either variant can reach 60 seconds only through unjustified repetition;
- a requested claim cannot be supported by inspected evidence.

A structural stop is a valid experiment result. Report the missing capability
or material truth; do not create a private workaround.

## 9. Legal end states

Success:

`WAITING_INTEGRATOR_SECOND_CASE_STAGE4_5_AB_REVIEW`

Otherwise use an explicit last-green stop state and name the structural cause.

Always preserve:

- `human_creative_approval=false`
- `final_delivery_claimed=false`

## 10. Integrator follow-up (not worker scope)

After the worker stops successfully, a fresh independent Reviewer context will
inspect the blinded packet and produce finding-only output. The integrator will
validate the artifact and compare Reviewer usefulness against the Owner's
verdict. No Reviewer v1.1 expansion is authorized until this product test shows
a real benefit.
