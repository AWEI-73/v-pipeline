# Work Order: Canon 67 Stage 4 storyboard review revision v2

Date: 2026-07-18  
Owner: `main-pipeline` integrator  
Worker profile: one bounded picture-edit execution worker  
Target state: `WAITING_INTEGRATOR_CANON67_STAGE4_STORYBOARD_V2_REVIEW`

## 0. Goal and authority

Turn the accepted findings from the 315-second six-chapter storyboard into one
revised, review-only candidate. This closes the case-level path:

```text
timeline review findings
-> finding disposition
-> accepted repair-basis story revision
-> revised paper edit
-> rendered storyboard
-> fresh horizontal Reviewer packet
```

The owner has authorized the five structural findings as revision inputs. This
is not creative approval, finishing approval, or final delivery. Do not create
a new route, renderer, review engine, registry entry, capability card, or gate.

## 1. Read and freeze

Read completely, in order:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. `HANDOFF_CURRENT.md`
4. this work order
5. `skills/editing-loop-director.md` — L1 and L5 only
6. `skills/verify.md` — whole-timeline review only
7. `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v1/timeline_review_v1/integrator_story_findings.md`
8. `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v1/timeline_review_v1/timeline_reviewer_findings.json`

Freeze these inputs in `preflight/frozen_input_audit.json`:

| Input | SHA-256 |
|---|---|
| accepted story revision v3 | `230432997756b877f7046133a049cddfa3f0cfa8b79472bf9864975217428e6e` |
| paper edit v1 | `16ea1d52d7e3174e82b62e560bc48e50e23858a54c6c2fd56db262fe3781cbb1` |
| storyboard v1 | `79157e99d9d8f5aa31db30a861665ac37e8acb347346c937003141b36ffa54ea` |
| timeline review packet v1 | `3a581d812616fd79ad829c94eacdee50c2cb141f1966ef8028b298390e601379` |
| machine findings v1 | `26f10f46d946938f88ce9825bd4ea79d624463abaaf275ba1af004d999afea0d` |
| integrator findings v1 | `bfa595ad654ef735eb094163f8fe9fc64635bff346341731729f2cac39f05325` |
| approved speech WAV | `c29a891e8ac670efaed4d6d47d9a17ef1d10a574876db628a46759f376af396d` |
| approved source SRT | `d7bb03cecf49d42d242a307b6aa08fd97b157e3991ec6b93c7afef65c8b3042c` |

Stop on any mismatch.

## 2. Owner zone

Editable:

- `.tmp/canon67_editorial_reconstruction_v2/stage4_storyboard_v2/**`
- `.tmp/canon67_editorial_reconstruction_v2/accepted/reviewer_finding_disposition_v1.json`
- `.tmp/canon67_editorial_reconstruction_v2/accepted/accepted_story_revision_v4.json`

Read-only:

- all source media;
- Stage 3 Material Maps and accepted story revision v3;
- storyboard v1 and its review packet;
- production code, tools, tests, skills, registry, docs, Git history/index;
- `HANDOFF_CURRENT.md` and campaign state.

A run-local driver may exist only below the v2 output root. It is evidence
orchestration for this candidate, not a reusable tool or new pipeline surface.

## 3. Finding disposition and revision v4

Create `reviewer_finding_disposition_v1.json` with exact source finding IDs and:

| Finding | Disposition |
|---|---|
| F01 first chapter title missing | `ACCEPTED_FOR_REVISION` |
| F02 internal training units invisible | `ACCEPTED_FOR_REVISION` |
| F03 apparent training shot in group life | `VERIFY_AND_LABEL_FIRST`; the bound source family is `捐血相關`, so do not move it merely from wall appearance |
| F04 ending callback lacks meaning | `ACCEPTED_FOR_REVISION` |
| F05 final hold lacks landing | `ACCEPTED_FOR_REVISION` |
| F06 placeholder finishing quality | `DEFERRED_TO_FINISHING` |

Create immutable `accepted_story_revision_v4.json`, based on v3 and bound to
both findings hashes. Its acceptance scope is `repair_basis_only`; it must keep
`human_creative_approval=false` and `final_delivery_claimed=false`.

## 4. Revise the paper edit

Create `paper_edit/stage4_paper_edit_v2.proposed.json`. Preserve six chapters,
the approved 39.34-second supervisor talking head, all 12 approved subtitle
texts/timings, and a truthful total duration. Do not add BGM.

Required repairs:

1. The opening card still identifies the film, but chapter one must visibly
   resolve to `紀律與工安` before its material begins.
2. Add review-only unit labels at the first visual of each supported family:
   - C01: `工安早會`, `工安體感`
   - C02: `拖拉電纜`, `電纜布線體驗`
   - C03: `換桿作業`, `洗礙子`
   - C04: `換桿作業`, `洗礙子`, `活線作業`
   - C05: `捐血活動紀實`, `班級慶生`, `選填志願活動紀實`
3. Every label must be `text_status=proposed_owner_review`, cite exact asset
   and Material Map evidence, and carry `delivery_graphic=false`. Folder names
   are retrieval priors, not official course truth.
4. C03 and C04 share visual families. Write
   `review/chapter_separation_report.json` explaining the different story job
   (practice/precision versus integrated scale/team execution). If the picture
   order cannot make that distinction visible, report `UNKNOWN`; do not hide it
   with labels.
5. Verify the 205–209 second source continuously. It is bound to `捐血相關`;
   label it before deciding whether it is misplaced. If pixels contradict the
   accepted family, stop with `material_truth_conflict`.
6. Reallocate the 39.66-second ending without changing its total:
   approximately 12 seconds life callback, 12 seconds technical callback, and
   15.66 seconds final group photograph. Callback sections need visible
   review-only labels; the final hold must land on the group photo rather than
   repeat the film title for 25 seconds.
7. Exact source-window duplication remains forbidden. Deliberate family reuse
   requires `callback_reason`.

Delegated choices: exact label animation, label duration between 1.5 and 3.0
seconds, and small clip trims that preserve the six chapter durations. These
are reversible and will be caught by the fresh storyboard review.

## 5. Render the review-only storyboard

Use existing public surfaces only:

- `tools/rough_cut_plan_execute.py`
- `video_tools.py title-sequence` / `title-card` / `concat` / `burnsub`
- `tools/audio_mix_plan_execute.py`
- `tools/final_av_assemble.py`

The audio plan must use the approved speech at its revised timeline position,
`silence_padding_policy=pad_to_target_duration`, no music, and exact subtitle
text policy. Preserve the talking head continuously with no cutaway.

Output:

- `candidate/canon67_stage4_storyboard_v2.mp4`
- `candidate/storyboard_timeline_v2.json`
- `candidate/shifted_approved_subtitles_v2.srt`
- command logs and build reports

This is a review candidate, not Stage 9 finishing.

## 6. Fresh Reviewer pass

Run `tools/timeline_review_packet.py` on v2 with 0.5-second sampling and
30-second pages, binding the shifted SRT as `owner_approved`. Inspect every wall
page and create:

- `review/timeline_review_packet.json`
- `review/timeline_reviewer_findings.json`
- `review/finding_resolution_matrix.json`
- `review/owner_review_index.md`
- `review/owner_verdict_template.json` with every decision `PENDING`

The resolution matrix must evaluate F01–F06 separately. Do not mark a finding
resolved from JSON alone; cite visible wall cells and exact timeline ranges.

## 7. Acceptance

Run:

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py final-product-verify `
  .tmp\canon67_editorial_reconstruction_v2\stage4_storyboard_v2\candidate\canon67_stage4_storyboard_v2.mp4 `
  --out-dir .tmp\canon67_editorial_reconstruction_v2\stage4_storyboard_v2\verify `
  --samples 36

C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_timeline_review_packet `
  tests.test_audio_mix_plan_executor `
  tests.test_final_av_assemble -v

git diff --check
```

Required read-back:

- candidate and timeline duration agree within 0.05 seconds;
- complete 0.5-second wall coverage, zero sampling gaps;
- first chapter name visible;
- all supported unit labels appear in their intended family windows;
- 205–209 source is continuously inspected and truthfully classified;
- supervisor speech is continuous, waveform check passes, 12/12 subtitle text
  equality passes;
- no BGM and no finishing approval;
- no exact source-window duplicate;
- v1 inputs remain hash-identical;
- no tracked file or Git state changed.

Full suite is not required because production code is read-only.

## 8. Stop-loss and report

One LOCAL correction per failure class. On recurrence, write the evidence,
classify STRUCTURAL, and stop at the last green state. Never modify a public
tool, registry, skill, test, accepted v3 artifact, or source media to pass this
work order.

Write `final/worker_report.md` with PASS/FAIL/UNKNOWN, exact commands and exit
codes, artifact SHA-256 values, deviations, skips, and blind spots.

Legal success state:

`WAITING_INTEGRATOR_CANON67_STAGE4_STORYBOARD_V2_REVIEW`

