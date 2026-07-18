# Work Order: Canon 67 Stage 4 closure and Stage 5 layered compile

Date: 2026-07-18  
Status: READY FOR WORKER  
Owner decision: `ACCEPT_STAGE4_PICTURE_WITH_FINISHING_FINDINGS`  
Target stop: `WAITING_INTEGRATOR_CANON67_STAGE5_LAYERED_COMPILE_REVIEW`

## 0. Outcome and authority

Close the owner-approved Canon 67 Stage 4 instance, then compile that locked
paper edit into a truthful Stage 5 decision package with four coordinated
layers: picture, effects, audio, and text.

This order freezes **one Canon 67 instance**. It does not turn Canon 67 story
content, chapter names, source choices, or durations into global rules.

Only these reusable policies may flow back into generic capability behavior:

1. rendered pixels outrank metadata when reviewing visual truth;
2. source and proxy use remains bound to exact source SHA-256;
3. major chapter cards consume explicit timeline duration;
4. unit labels are timed overlays unless an owner explicitly grants standalone
   card time;
5. empty bridges are real transition primitives, never blank-text sentinels;
6. Stage 5 finishing decisions cannot silently reopen the accepted story.

This order ends after Stage 5. It does not authorize a Stage 6 canonical
render, CapCut execution, Stage 7–8 review, Stage 9 repair, delivery, upload,
commit, push, or creative approval.

## 1. Read first and freeze

Read completely, in order:

1. `AGENTS.md`
2. `RUNBOOK.md`, especially **Stage And Editing Loop Authority**
3. `HANDOFF_CURRENT.md`
4. `skills/video-pipeline-route.md`
5. `skills/editing-loop-director.md`
6. `skills/editor.md`
7. `skills/soundtrack-arranger.md`
8. `skills/video-effect-factory.md`
9. `skills/subtitle-director.md`
10. `skills/capcut-assisted-finishing.md` only for backend boundary truth

Freeze and hash-check these exact inputs before creating any output:

| Artifact | SHA-256 |
|---|---|
| `.tmp/canon67_editorial_reconstruction_v2/accepted/accepted_editorial_state_v2.json` | `2041e6b9c879aa7737defa0f3d86198836822860a2345b16d2742bf219af25e7` |
| `.tmp/canon67_editorial_reconstruction_v2/accepted/accepted_story_revision_v4.json` | `eb4b04cebeace082907aca77b1cc128d4f086731379ba1f9c7db9cd2bac6fba6` |
| `.tmp/canon67_editorial_reconstruction_v2/accepted/project_material_map_v3.json` | `704a1fed801218530d206665bf906f67a60ad28f216e3c954ee195b23775962c` |
| `.tmp/canon67_editorial_reconstruction_v2/stage2_ambiguity_v2/segment_story_contract.json` | `694dd73736645736c4f2e4cb0b031d60294c312f6de4ed143c48f38e5d171735` |
| `.tmp/canon67_editorial_reconstruction_v2/stage4_role_bound_paper_edit_v1/contract/resolved_segment_contract.stage4.json` | `f6220ad3094f37b99a32372861d63488d44fcbfae4c2ad568c5c7a2c8493ec6d` |
| `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v3/candidate/canon67_stage4_storyboard_v3.mp4` | `6bc0b7b1676171e6743bbc8a9b97ce25a844e6bed105f2144247a7e48ab50c78` |
| `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v3/candidate/storyboard_timeline_v3.json` | `3a2bb3c3c0a9b9e5518b70951b052ac2d6310b83d4b7359a7482d06433857c8c` |
| `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v3/candidate/shifted_approved_subtitles_v3.srt` | `ebb3b9cbf36e38087bace9e6ce0b2503e33d894d64913438c04b3c14dcd0803f` |
| `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v3/candidate/storyboard_build_report_v3.json` | `4f129b948ce35d25c831174998916dfae609472a59130ce0f6acab5e38e0219b` |
| `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v3/review/owner_correction_closure.json` | `1509abddef431b2bf1656a823470ef2615f618152631bfdb4345f88471f343a7` |
| `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v3/review/timeline_review_v3/timeline_review_packet.json` | `516c87bfdc412a488eed5164061625b02ca0ba9c016c677f8b86195d325b6d90` |
| `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v3/review/final_product_verify/final_product_verify_bundle.json` | `bebd853ebd7d691f388daf75ac24de23ca0912abeadd9a8453caf1cdaa142d30` |

Record branch, HEAD, `git status --short`, all frozen hashes, and current
full-suite trust boundary in:

`.tmp/canon67_editorial_reconstruction_v2/stage5_layered_compile_v1/preflight/frozen_input_audit.json`

The current full-suite state is `STALE` after the bounded rendered-review
source-truth patch. Do not copy an older suite PASS into this run.

Stop before Task 1 if any frozen hash drifts.

## 2. Owner and forbidden zones

### 2.1 Owner zone

The worker may create or modify only:

- `.tmp/canon67_editorial_reconstruction_v2/stage5_layered_compile_v1/**`
- `video_pipeline_core/edit_decision_plan.py`, only if Task 5 proves a bounded
  true-shape representation or readiness defect in the public Stage 5 compiler
- `tests/test_compile_edit_decision_plan.py`, only with the same bounded defect
- `tools/compile_edit_decision_plan.py`, only if the public CLI itself prevents
  the bounded fix and a red test proves it

### 2.2 Forbidden zone

Do not modify:

- accepted Stage 0–4 artifacts or the Stage 4 v3 candidate;
- source media, reference media, Material Map truth, story contracts, approved
  transcript, or approved SRT;
- Stage 6 renderer, Remotion bridge, CapCut bridge, effect renderer, audio
  renderer, subtitle renderer, registry, Skills, `RUNBOOK.md`,
  `HANDOFF_CURRENT.md`, campaign status, or delivery flags;
- git history, git index, branches, worktrees, or unrelated dirty files.

Do not use private ffmpeg assembly, private JSON substitutes, or a run-local
renderer to bypass a missing public contract. Do not use `python -c`, shell
embedded f-strings, or shell-transmitted Chinese literals; use registered CLIs,
`apply_patch`, or UTF-8 files.

## 3. Task 1 — close the Stage 4 instance

Create:

`stage4_closure/stage4_owner_verdict.json`

The artifact must faithfully encode this owner decision without upgrading it:

- verdict: `ACCEPT_STAGE4_PICTURE_WITH_FINISHING_FINDINGS`;
- accepted scope: Canon 67 narrative structure, chapter order, material family
  grouping, corrected source choices, protected speech placement, and final
  group-photo landing;
- canonical semantic duration: `315.0` seconds;
- picture/story order is locked for forward compile;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

Open finishing findings:

1. `objective`: a square/tofu glyph appeared before major units;
2. `structural_candidate`: unit labels should fade over material instead of
   consuming standalone card time;
3. `objective`: major chapter-card duration must remain counted in the timeline;
4. `taste`: final typography, effects, music, and mix remain pending.

Bind the verdict to the exact Stage 4 timeline, candidate, review packet, and
owner-correction hashes. Do not call it a delivery or final creative verdict.

## 4. Task 2 — build the locked picture layer

Create a canonical Stage 5 run root at:

`.tmp/canon67_editorial_reconstruction_v2/stage5_layered_compile_v1/run`

Translate Stage 4 v3 into the public rough-cut/picture-plan shapes required by
the Stage 5 compiler and retrieval gate.

Picture invariants:

- preserve the six accepted chapter boundaries and their causal order;
- preserve material clip order, asset IDs, source hashes, source-window order,
  protected-speech placement, and final group landing;
- keep the semantic total exactly `315.0` seconds;
- keep major chapter cards as real picture items: C01 uses 5.0 seconds and
  C02–C06 use 3.0 seconds each; their fades happen inside these windows;
- convert all 14 standalone 1.5-second unit/callback label cards to overlays on
  the first following material shot; they consume `0.0` additional seconds;
- redistribute the reclaimed 21.0 seconds only within the same chapter by
  extending already accepted material windows when source capacity permits;
- never use duplicated source windows, irrelevant padding, artificial freezes,
  or cross-chapter borrowing to restore duration;
- if exact 315.0-second reallocation cannot be supported, stop with a bounded
  capacity report instead of padding or changing story order;
- represent bridges as no-text fades or cuts. U+2003, whitespace-only copy,
  placeholder glyphs, and blank title videos are forbidden.

Produce a fresh `stage5/l1_picture_plan.json`, segment contract copy with frozen
hash binding, Material Map reference, and retrieval ranking report through the
registered public retrieval capability. Manual picture plans without a fresh
passing ranking report are invalid.

## 5. Task 3 — define the effects and text layers

Create public handoffs that truthfully express:

### 5.1 Major chapter cards

- six chapter cards, using the accepted Stage 4 copy and ordering;
- fade-in/fade-out lifecycle inside each already-budgeted card window;
- no extra title duration and no hidden picture-track extension;
- explicit CJK-capable font and fallback policy.

### 5.2 Unit and callback labels

- all 14 accepted labels preserved exactly;
- overlay on the first following material shot for 1.5 seconds;
- simple fade lifecycle, recommended 0.35 seconds in and 0.35 seconds out;
- readable safe-area placement and no collision with approved subtitles;
- `delivery_graphic=false` until visual review.

### 5.3 Ending

- preserve the accepted single group-photo landing;
- preserve exact ending copy `從訓練走向責任`;
- do not reopen MemoryPhotoWall or invent a teacher roster.

Run a bounded text/effect preflight, not a full candidate render. Produce a
contact sheet or short probes covering every unique Chinese string and all
three lifecycle types: chapter card, unit overlay, ending copy. Pixel evidence
must demonstrate readable CJK glyphs and absence of tofu squares; metadata-only
evidence is insufficient.

## 6. Task 4 — define the audio layer

Create an audio intent/handoff with three macro music roles:

1. `0.00–96.00`: foundation, discipline, and basic skill;
2. `96.00–233.00`: advanced/integrated training and group life;
3. `233.00–315.00`: witness, reflection, and responsibility landing.

These are editorial roles, not permission to invent licensed files. Prefer a
registered, delivery-compatible local source if one exists and its license
truth is explicit. Otherwise set the relevant source status to
`owner_or_provider_pending` and keep build readiness false.

Protected speech requirements:

- source asset SHA-256:
  `85baeafce7d3d7fbeb56c1a354b9edaf2ee500ab4285bf56893b906c49f9cfcb`;
- timeline start `236.00`, complete duration `39.34` seconds;
- original speech remains continuous and uncut;
- music ducks to a quiet background under speech; encode the starting proposal
  as `-20 dB relative to music program level`, explicitly marked for owner
  listening verdict rather than objective PASS;
- no music may mask or replace the speech.

CapCut may later realize accepted audio/effect intent, but it does not own the
intent, license truth, picture lock, or approval. Record intended backend
provenance without invoking CapCut in this order.

## 7. Task 5 — bind the approved subtitle layer

Bind the exact 12/12 approved subtitle cues from the frozen SRT to the protected
speech window. Preserve every approved character and cue time. Do not polish,
rewrite, split, merge, or move transcript text.

The text decision layer must distinguish:

- approved speech subtitles;
- accepted chapter-card copy;
- accepted unit/callback overlay copy;
- accepted ending copy;
- unresolved finishing typography.

Produce an equality audit for 12/12 subtitles and a collision-risk report for
the protected speech interval.

## 8. Task 6 — compile through the public Stage 5 entry

Run the existing public compiler first:

```powershell
C:\Users\user\miniconda3\python.exe tools\compile_edit_decision_plan.py --run .tmp\canon67_editorial_reconstruction_v2\stage5_layered_compile_v1\run --json
```

Expected Stage 5 outputs include picture, audio, effect, subtitle/text decision
plans and a build handoff. Preserve all dynamic input hashes.

`ready_for_build` may be true only if every required handoff is actually ready,
delivery-compatible source/license truth is present, and no owner/provider
decision remains pending. A file's mere presence never creates readiness.

If the existing compiler cannot truthfully represent timed generic overlays,
multiple music sections/ducking, or incomplete-handoff readiness:

1. classify the exact gap;
2. add a true-shape failing test first;
3. make one bounded compiler-only patch inside the Owner Zone;
4. rerun focused and adjacent compiler tests;
5. keep Stage 6 renderer and all backends untouched.

If the required fix expands beyond those bounded Stage 5 fields or repeats the
same failure class after one local correction, stop as STRUCTURAL with evidence.

## 9. Task 7 — integrator packet

Create:

- `final/owner_review_index.md`
- `final/layered_compile_summary.json`
- `final/verification_state.json`
- `final/worker_report.md`
- `final/artifact_sha256.json`
- `final/command_log.json`

The review index must answer, in plain language:

1. what Stage 4 facts are now locked;
2. how the 21 seconds reclaimed from label cards were reallocated;
3. where each of the 6 chapter cards and 14 unit overlays appears;
4. whether all Chinese text passed pixel review;
5. which music sources are selected or still pending;
6. whether build readiness is true or false, and why;
7. what Stage 6 will receive without reopening story choices.

Use PASS / FAIL / UNKNOWN. Keep taste and owner/provider decisions UNKNOWN.

## 10. Acceptance

Required evidence:

1. frozen-hash audit: exit 0, all exact matches;
2. public retrieval/ranking report: exit 0, `ok=true`, `errors=[]`;
3. picture math: exactly 315.0 semantic seconds, 6 chapter cards, 14 overlays,
   zero standalone unit-label duration, zero duplicate source windows;
4. no U+2003, whitespace-only text, tofu placeholder, or blank title artifact;
5. text/effect pixel preflight: all unique Chinese strings visibly readable;
6. protected speech binding: 39.34 seconds, exact source hash, uninterrupted;
7. approved subtitle equality: 12/12;
8. public Stage 5 compile: exit 0 and dynamic hash read-back PASS;
9. `ready_for_build` agrees with actual audio/license/owner state;
10. focused compiler, retrieval, text/effect, subtitle, and skill-boundary tests:
    exit 0;
11. ownership/registry audit: exit 0 if production code changed;
12. UTF-8/JSON/path/hash read-back: exit 0;
13. `git diff --check`: exit 0;
14. no Stage 6 candidate, `final.mp4`, upload, delivery, or approval claim.

Do not run the full suite. If production code changes, record
`full_suite.status=STALE`, the last known verified HEAD if available, and the
exact focused coverage used here. This order intentionally pays only for
change-scope verification.

## 11. Stop-loss

- One LOCAL correction is allowed per failure class.
- On the second occurrence of the same class, stop at the last green state and
  classify it STRUCTURAL.
- Stop immediately on frozen-hash drift, source/proxy binding drift, story-order
  drift, source-window duplication, subtitle mutation, speech truncation,
  unlicensed delivery claim, or an out-of-zone required change.
- A missing music source is not permission to fabricate one. Preserve the
  complete Stage 5 decision package with readiness false and report the owner
  or provider handoff.
- Do not use a gate waiver, run-local renderer, private ffmpeg path, or hand-made
  JSON to turn a real failure into PASS.

## 12. Legal final states

Success:

`WAITING_INTEGRATOR_CANON67_STAGE5_LAYERED_COMPILE_REVIEW`

This success state permits either:

- a truthful ready Stage 5 package; or
- a complete reviewable Stage 5 package with `ready_for_build=false` solely
  because named music/license/owner choices remain pending.

Failure:

`STOPPED_AT_LAST_GREEN_CANON67_STAGE5_<CLASS>`

Both legal states must retain:

```json
{
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
```
