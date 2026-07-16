# Work Order: Canon 67 editorial reconstruction v2 — Stage 3 through Stage 8

Date: 2026-07-17  
Status: READY FOR WORKER  
Owner decision: `A_WITH_B_CAUSAL_RULES`  
Target stop: `WAITING_INTEGRATOR_CANON67_RECONSTRUCTION_V2_REVIEW`

## 0. Outcome

Build one new Canon 67 review candidate from the accepted Stage 0–2 editorial
state. The candidate is an institutional training-outcome report with clear
story progression, not a random activity catalogue and not a restyled copy of
the prior 385-second picture plan.

The worker executes Stage 3–8 through registered Hermes public capabilities:

1. Stage 3 — evidence-backed retrieval and source windows;
2. Stage 4 — coverage and story-completeness gate;
3. Stage 5 — picture/effects/audio/text decision compile;
4. Stage 6 — the only canonical candidate render;
5. Stage 7–8 — objective Verify plus whole-film eye/ear/heart review packet.

This order does not authorize Stage 9 delivery finishing or Stage 10 delivery.

## 1. Read first and freeze

Read completely, in order:

1. `AGENTS.md`
2. `RUNBOOK.md`, especially **Stage And Editing Loop Authority**
3. `skills/video-pipeline-route.md`
4. `skills/editing-loop-director.md`
5. `.tmp/canon67_editorial_reconstruction_v2/accepted/accepted_editorial_state_v2.json`
   — SHA-256 `2041e6b9c879aa7737defa0f3d86198836822860a2345b16d2742bf219af25e7`
6. `.tmp/canon67_editorial_reconstruction_v2/accepted/owner_acceptance_receipt.json`
   — SHA-256 `bc22cd73d973adf881387e074d4d88b7450d040d4caea0a0c34fe2e3ef0668aa`
7. `.tmp/canon67_editorial_reconstruction_v2/review/owner_verdict.json`
   — SHA-256 `69abd7efe701ad8e062ef71fbf471ccfc4bfdb8bddb9bee5d0c4bbb143a56e02`
8. `.tmp/canon67_editorial_reconstruction_v2/stage0/material_truth.json`
   — SHA-256 `319d8db407b6b86e93440134bf2f0b50e2d92b19f5ea0d2f67f08481d9898143`
9. `.tmp/canon67_editorial_reconstruction_v2/stage0/coverage_ledger.json`
   — SHA-256 `023001021e70ab3ea0592a88115b8a77bb9fc4068f617a56840db063ae34db0f`
10. `.tmp/canon67_editorial_reconstruction_v2/stage1/ab_story_options.json`
    — SHA-256 `96a705bb49809c8ea046128693ee9c083fde08a6fe22414e04b9d0838228c497`
11. `.tmp/canon67_540s_route_acceptance/stage3/project_material_map_l0_v1.json`
    — SHA-256 `9dcb970b7a8c9bbb053567c35ab4ea259630e21514a9309e320d33ee1c10f6b2`
12. `.tmp/editing_loop_39s_integrated_campaign/wave_p/human_transcript_review_decision.json`
    — SHA-256 `5d40c6ed1555fe9e08e51fa398295fef16f28496efa76e671287ff1efc5dc046`

Also read as negative/reference calibration only:

- `.tmp/canon67_540s_route_acceptance/stage6/multimodal_candidate_v1/review/timeline_reviewer_findings.json`
- `.tmp/canon67_reference_timeline_boundary_v2/timeline_review_packet.json`
- all 19 reference walls under
  `.tmp/canon67_reference_timeline_boundary_v2/walls/`

The reference film and Canon 66 media are never candidate source material.

Before any work, validate every frozen SHA-256, record branch/HEAD/status, and
write `stage3/preflight/frozen_input_audit.json`. Stop on drift.

## 2. Fixed editorial contract

### 2.1 Product identity

- Product: `成果報告式結訓影片`
- Collective protagonist: `第67期學員`
- Thesis: `時代不斷向前，而每一度穩定的電，都從有人願意學會承擔開始。`
- Tone: steady, sincere, human, not grandiose.
- Story spine: ritual/foundation → training results → people/witness/future.
- Duration: evidence-supported `380–425` seconds; `540` is a ceiling, never a quota.

### 2.2 Accepted segment skeleton

| Segment | Target | Required story job |
|---|---:|---|
| A01 opening | 12s | Enter the training world and pose responsibility. |
| A02 collective identity | 28s | Dispersed individuals become one cohort. |
| A03 discipline/safety | 40s | Reliability first becomes rules and safety. |
| A04 ground/cable teamwork | 55s | Complete ground-work micro-story. |
| A05 pole/live-line | 60s | Move from force to precision and higher risk. |
| A06 height/scale | 50s | Technical visual peak; stills may punctuate, not pad. |
| A07 technical detail | 0–35s | Scale contrast only if retrieval proves unique information. |
| A08 life/bonds | 50s | Event-grouped breadth montage creates belonging. |
| A09 supervisor witness | 39.34s | Complete source speech and 12/12 approved subtitles. |
| A10 placement preference | 25s | Training results begin to affect the next destination. |
| A11 collective landing | 30.66s | Memories converge to one group photo; symbolic landing. |

Targets are planning values, not padding rights. A07 must shorten or merge if
its ranked windows do not add unique information. Other segments may shorten
when evidence is insufficient, but the causal order and owner facts are fixed.

### 2.3 B causal rules applied to A

- Every segment adds at least one unique new piece of information.
- Keep the same event family contiguous before changing to another family.
- Identical source-window reuse is forbidden.
- Cross-segment family reuse requires a machine-readable `callback_reason`.
- Life montage groups each event into a short readable unit; no one-shot list.
- Interview cutaways must be sentence-relevant or add unseen visual information.
- Stills cannot use long holds to pretend an action or event progressed.
- Missing evidence means shorten, merge, or defer — never irrelevant B-roll,
  duplicate footage, text essays, or repeated music cycles.

### 2.4 Immutable truth boundaries

- Keep the complete 39.34-second supervisor source speech.
- Burn/overlay exactly the 12 owner-approved subtitle cues; no polishing.
- Placement sequence means trainees fill future work-unit preferences in
  training-score order. Do not identify the director and do not claim final
  distribution results.
- Teacher/adviser roster remains deferred until all 13 are approved.
- No source proves literal departure. Ending may symbolize a next step but may
  not state that the image shows the cohort leaving.
- No invented first-person trainee voiceover.

## 3. Owner and frozen zones

Worker may create only:

- `.tmp/canon67_editorial_reconstruction_v2/stage3/**`
- `.tmp/canon67_editorial_reconstruction_v2/stage4/**`
- `.tmp/canon67_editorial_reconstruction_v2/stage5/**`
- `.tmp/canon67_editorial_reconstruction_v2/stage6/**`
- `.tmp/canon67_editorial_reconstruction_v2/stage7/**`
- `.tmp/canon67_editorial_reconstruction_v2/stage8/**`
- `.tmp/canon67_editorial_reconstruction_v2/final/**`

Read-only:

- Stage 0–2 and `accepted/**` under this campaign;
- all earlier Canon 67 campaign artifacts and candidates;
- source media and Material Map;
- production code, tools, tests, Skills, registry, RUNBOOK, HANDOFF, docs;
- git index and history.

No commit, stage, push, upload, cleanup, reset, source mutation, private helper,
handwritten ffmpeg bypass, new route runner, or replacement JSON compiler.

If an existing public capability cannot express a required contract, write a
factory-gap packet and stop. A gap is not permission to patch production code.

## 4. Ordered execution

### Task 0 — Resume and accountability preflight

1. Freeze all input hashes and source hashes.
2. Create a fresh run accountability root and immutable command ledger using
   the existing registered route/accountability surfaces.
3. Record `verification_state.full_suite=STALE_NO_CODE_CHANGE`.
4. Confirm old picture order, old source-window order, and old BGM placement
   are retired and cannot be imported as defaults.

PASS evidence: frozen audit, run metadata, clean owner-zone check.  
On drift: stop `STOPPED_FROZEN_INPUT_DRIFT`.

### Task 1 — Stage 3 material retrieval and ranked windows

Use the persistent Material Map as truth. Filename/folder meaning is a prior,
never ground truth. Use existing registered material/retrieval capabilities,
including the public surfaces represented by:

- `tools/material_pool_map.py`
- `tools/picture_plan_retrieval_report.py`
- `video_pipeline_core.material_retrieval`

For every accepted segment:

1. enumerate candidate assets/windows from the approved source families;
2. bind canonical asset ID, path, source SHA-256, in/out window, observed
   content, assigned story function, evidence class, ranking reasons and score;
3. review the actual pixels/temporal evidence for every final select;
4. reject misleading filename priors explicitly;
5. record Top-K and selection reason, including why rejected alternatives lost;
6. audit same-window reuse, non-adjacent semantic repetition, event-family
   grouping, and interview-cutaway novelty.

Required artifacts:

- `stage3/retrieval/retrieval_ranking_report.json`
- `stage3/retrieval/source_window_plan.json`
- `stage3/retrieval/selection_rejection_ledger.json`
- `stage3/retrieval/repetition_and_family_audit.json`
- evidence contact sheets/temporal strips for selected assets

No hand-selected clip enters Stage 4 without a ranking-report record. If A07
cannot prove unique information, propose a bounded merge/shortening delta now.

### Task 2 — Stage 4 coverage and story gate

Build `stage4/story_coverage_gate.json` and one silent captioned storyboard.
The storyboard uses real selected keyframes/windows, no source audio, and shows
at each segment start:

- chapter number;
- observable title;
- one-line story job.

Review captions are reviewer aids, not final delivery graphics.

Gate each segment as PASS / FAIL / UNKNOWN on:

1. factual purpose is source-window backed;
2. story function follows from the preceding segment;
3. unique new information is present;
4. entry/exit state advances;
5. event families are contiguous;
6. repeated family/window use has an explicit reason;
7. source capacity supports planned duration without fake holds.

Also produce:

- `stage4/coverage_ledger_applied.json`
- `stage4/global_story_state_readback.json`
- `stage4/storyboard_preview.mp4`
- `stage4/owner_review_index.md`

The worker may apply only the already-authorized A07 shorten/merge rule. Any
other story-order change is a proposed delta and remains non-canonical.

### Task 3 — Stage 5 layered edit decisions

Compile a new plan through existing registered public surfaces. The public
compile gate represented by `tools/compile_edit_decision_plan.py` must read the
new plan; do not handwrite a renderer-only substitute.

#### L1 picture

- Start from Stage 3 ranked windows, not the old 385-second order.
- Give each technical chapter an internal micro-story: establish → action →
  response/result.
- Enforce source-window allocation and no duplicate windows.
- Use subject-aware still motion. Movement must converge toward people/action,
  not empty sky or irrelevant borders.
- Chapter boundaries must be visually and temporally legible without relying
  on music alone.

#### L2 effects

- Use effects only for opening, chapter entry/transition, approved subtitles,
  and the memory-to-group-photo landing.
- Effects cannot replace missing event evidence.
- Prefer mature registered/CapCut finishing only after picture/text lock;
  otherwise use the registered local Effect Factory.
- Record backend provenance on every effect asset.

#### L3 audio

- Build a chapter-aware energy arc rather than restarting one BGM loop three
  times.
- Use only media with recorded source/license/delivery status.
- Preview-only audio remains preview-only and blocks delivery.
- Duck music to quiet background under every speech window.
- Preserve complete supervisor speech continuity.
- Use existing registered Soundtrack Arranger and audio-mix public surfaces,
  represented by `tools/soundtrack_arranger.py` and the public audio mix plan
  executor. Do not perform a private mux as the canonical plan.

#### L4 text

- Keep chapter titles factual and short.
- Preserve exact 12/12 approved supervisor subtitles and source/timing binding.
- Final ending copy must stay within the truthful symbolic boundary.
- Review captions are removed or clearly isolated from the candidate delivery
  graphics lane.

Required artifacts:

- `stage5/l1_picture_plan.json`
- `stage5/l2_effect_plan.json`
- `stage5/l3_audio_plan.json`
- `stage5/l4_text_plan.json`
- `stage5/edit_decision_plan.json`
- `stage5/compile_gate.json`
- semantic diff against the accepted state and proof old order was not reused

Compile must be `ok=true`, `rendered=false`. Stage 5 cannot claim a canonical
candidate.

### Task 4 — Stage 6 canonical candidate render

1. Render bounded chapter previews first through registered public factory
   surfaces and verify their duration, source binding and chapter boundary.
2. If all chapter previews are technically valid, render exactly one new full
   review candidate from the compiled Stage 5 plan.
3. Stage 6 owns this render. Editing Loop previews cannot be promoted by file
   copy or rename.
4. CapCut is optional only after picture/text lock. If used, store backend
   provenance, draft identity and export evidence, then return the export to
   Stage 7. Local registered factory is the fallback.

Output:

- `stage6/chapters/**`
- `stage6/candidate/final.mp4`
- `stage6/candidate/render_report.json`
- `stage6/candidate/backend_provenance.json`

This remains a review candidate. Set both approval flags false.

### Task 5 — Stage 7 objective Verify

Run the existing registered QA and Verify surfaces, including:

- `tools/rendered_product_qa.py`
- `tools/final_product_verify.py`
- subtitle exact-text/source/timing audit;
- speech continuity and ducking measurement;
- source-window/repetition/family audit read-back;
- media health, black/decode/frame/duration checks.

Required PASS/FAIL/UNKNOWN evidence:

- planned vs rendered total and chapter durations;
- every selected source hash/window;
- complete 39.34-second speech and 12/12 exact subtitles;
- no teacher roster or reference-film pixels;
- no identical duplicate source window;
- music provenance and preview/delivery status;
- chapter boundary evidence;
- subject-aware still treatment evidence where applicable.

Technical PASS must never be translated into creative approval.

### Task 6 — Stage 8 eye/ear/heart review packet

Run `tools/timeline_review_packet.py` on the complete candidate using:

- `--media-role current_candidate`
- `--interval-sec 0.5`
- `--wall-duration-sec 30`
- the final reviewed/draft SRT;
- soundtrack probe/audio evidence.

Review every generated wall. Do not merely generate them.

Create `stage8/timeline_reviewer_findings.json` with findings classified as:

- `objective`
- `structural_candidate`
- `taste`

For story/semantic review, use comparative and adversarial questions rather
than an absolute “is it good” score:

1. Does each chapter make the responsibility thesis clearer or dilute it?
2. Which exact segment repeats information already understood?
3. Are chapters readable as units, or do categories still spray randomly?
4. Does the technical arc visibly rise from foundation to precision/scale?
5. Does the life section create belonging before the supervisor witness?
6. Does the ending fulfill the opening promise without inventing departure?

Produce a blind A/B comparison against the prior 385-second candidate for the
three most important structural questions. The reviewer may flag and prefer;
it may not set owner creative approval.

Required Stage 8 artifacts:

- whole-film timeline review packet and all walls;
- eye/ear/heart review findings;
- comparative review packet and validated flags;
- owner review index with candidate, storyboard, chapter previews, captions,
  contact sheets and known blind spots.

### Task 7 — Final scoped validation and report

Run:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py test-tiers --tier work-order-acceptance
git diff --check
```

Run focused owner modules for every public tool actually invoked. Production
code is frozen, so do not run the large full suite solely for artifact work.
If any production/shared behavior changed contrary to this order, stop and
request a separate TDD work order; do not absorb that change here.

Write:

- `final/campaign_status.json`
- `final/worker_report.md`
- `final/command_log.json`
- `final/artifact_manifest.sha256.json`
- `final/integrator_review_index.md`

The report must include commands and exit codes, hashes, PASS/FAIL/UNKNOWN,
deviations, skipped work, blind spots, wall-clock, render count, agent turns if
available, tool-call count if available, owner-review minutes as UNKNOWN, and
revision blast radius.

## 5. Stop-loss

One LOCAL correction per failure class. A repeated class is STRUCTURAL.

Stop at the last green state on:

- frozen hash or source hash drift;
- missing registered public capability;
- required production-code, schema, Skill, registry, HANDOFF or docs change;
- workaround that bypasses retrieval, compile, render, audio, subtitle, Verify
  or accountability contracts;
- repeated source window used to reach duration;
- reference/Canon66 media entering the candidate;
- loss, rewrite or truncation of the approved supervisor speech/subtitles;
- teacher/adviser partial roster;
- unlicensed/preview-only audio promoted as delivery-safe;
- repeated failure class.

When stopped, report the smallest structural gap and the exact public surface
that cannot express the accepted contract. Do not write a speculative fix.

## 6. Legal completion state

Success is only:

`WAITING_INTEGRATOR_CANON67_RECONSTRUCTION_V2_REVIEW`

and all of the following remain true:

```text
human_creative_approval=false
final_delivery_claimed=false
```

The Integrator, not the worker, independently checks hashes, story-state
compliance, every 0.5-second wall, audio behavior, comparative flags and the
actual candidate before any owner verdict or Stage 9 work.
