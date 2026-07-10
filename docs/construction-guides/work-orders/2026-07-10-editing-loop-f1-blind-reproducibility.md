# Editing Loop f1 Blind Reproducibility Forward-Test

Status: READY FOR TERRA PHASE A

## Goal And Experiment Question

Use a **fresh TERRA session** to test whether
`skills/editing-loop-director.md` can carry the Canon 67 story spine and prior
L0/L1 decisions into one bounded L1 revision without leaking the evaluator's
expected clip or replacement answer.

The experiment question is:

> Can a new agent read only the Skill, the four carried-context inputs, and the
> raw f1 finding; independently locate the cause, propose a defensible picture
> replacement, wait for the owner gate, apply exactly one stable-ID picture
> diff, and preserve all unaffected layers with evidence?

This is a Skill reproducibility test, not a helper construction task. A cleanly
reported inability to execute with existing capabilities is a valid FAIL and
must not be hidden by building new infrastructure during the test.

## Raw Finding Given To The Worker

`f1` — class: `taste`; owner capability: `picture/L1`.

> 樂章三收尾的連續畫面來自過度相近的場地／構圖，觀看時有重複感。
> 請保留「三樂章收攏」與最後圓陣落點，但改善進入最終落點前的重複感。

No expected stable clip ID, current select code, replacement select code, or
evaluator conclusion is supplied. TERRA must derive them from visual and
timeline evidence.

## Required Read Order And Context

Read only these doctrine/context documents before inspecting executable APIs:

1. `AGENTS.md`
2. this work order
3. `skills/pipeline-boundary.md`
4. `skills/editing-loop-director.md`
5. approved story spine:
   `docs/pilots/2026-07-10-opening-0044-script-v1.md`
6. selects context:
   `.tmp/loop_pilot_0044/selects_manifest.json` and
   `.tmp/loop_pilot_0044/selects_*.png`
7. run provenance:
   `.tmp/loop_pilot_0044/candidate_v1/source_provenance.json`
8. candidate context:
   `.tmp/loop_pilot_0044/candidate_v1/**`

TERRA may read the following implementation surfaces only to call existing
public capabilities; all are read-only:

- `video_pipeline_core/beat_cut_composer.py`
- `video_pipeline_core/edit_decision_plan.py`
- `video_pipeline_core/edit_decision_renderer.py`
- `video_pipeline_core/opening_sequence.py`
- `video_pipeline_core/timeline_patch.py`
- `video_pipeline_core/graduation_opening_slice.py`
- `video_pipeline_core/rendered_product_qa.py`
- `tools/verify_beat_cut_alignment.py`
- `tools/rendered_product_qa.py`
- `video_tools.py` command help for named verification commands

## Owner Zone

TERRA may write only:

- `.tmp/loop_f1_blind_reproducibility/**`

Allowed artifacts include proposal evidence, before/after contact sheets,
owner-verdict record, a pilot-only session driver or command log, `candidate_v2`,
machine reports, decision/provenance records, and the final worker report.

No git commit is required. The output directory is experimental evidence, not
a new production surface.

## Blindness And Forbidden Zone

Do not read, search, quote, or infer an answer from:

- `docs/pilots/pilot-driver-v1-usage-log.py`
- `docs/pilots/2026-07-10-loop-pilot-evidence-for-sol.md`
- `docs/decisions/**`
- Fable/SOL/TERRA prior conversation transcripts or evaluator notes
- git history/diffs whose purpose is to discover an f1 solution
- any file added after this work order that claims an expected f1 answer

Read-only and never editable:

- all `skills/**`, `video_pipeline_core/**`, `tools/**`, tests, docs, examples,
  registries, dictionaries, `AGENTS.md`, `RUNBOOK.md`, and `video_tools.py`
- `.tmp/loop_pilot_0044/**`
- every other pre-existing `.tmp/**` run
- `C:\Users\user\Downloads\微電影素材\_整理後\**`
- `AGENTS.md`, `skills/INDEX.md`, `r`, and `supply_review.json`

Do not build a helper, route runner, schema, next-action vocabulary, Skill
patch, product code, test, or reusable engine. Do not use the reference film as
footage. Do not stage, commit, clean, delete, push, or open a PR.

## Phase A - Blind Proposal And Mandatory Owner Gate

### Piece A1 - Freeze The Before State

Before proposing a change:

1. Record `git status --short` without modifying the dirty tree.
2. Record SHA-256 hashes for candidate v1's `opening_sequence.json`,
   `edit_decision_plan.json`, `timeline_build.json`, `source_provenance.json`,
   and `final.mp4`.
3. Produce a review image that makes the final three montage pictures and their
   stable clip IDs readable. Do not use ordinal position as the only identity.
4. Record the raw f1 finding as the observed RED/taste evidence; do not turn a
   machine gate green by redefining the finding.

Write under `.tmp/loop_f1_blind_reproducibility/before/`.

### Piece A2 - Inspect And Propose

Inspect candidate v1, the approved story spine, the selects manifest, and the
indexed candidate sheets. Write:

`proposal/f1_picture_revision_proposal.json`

It must include:

- `finding_id`, `proposal_by`, and `selection_mode`;
- target stable clip ID and the current asset/select identity TERRA discovered;
- one proposed replacement asset/select identity;
- evidence refs to before frames, candidate-sheet cells, timeline coordinates,
  and story-spine requirements;
- why the proposal reduces repetition while preserving the final round/formation
  landing and three-movement story;
- declared blind spots and at least one rejected alternative with reason;
- predicted semantic diff and confirmation that duration/cut boundaries are
  intended to remain unchanged;
- per-layer prediction for picture, effects, audio, and text:
  `dirty`, `review`, or `clean`, each with a dependency reason;
- `owner_verdict_required=true`.

Also write `proposal/f1_picture_revision_proposal.md` with the current frame,
proposed candidate frame, relevant ending context, and a direct approve/revise
question for the owner.

### Piece A3 - Stop

After the proposal is written, stop with:

`WAITING_OWNER_PICTURE_REVISION_VERDICT`

Do not create candidate v2, render, or treat silence as approval. The owner's
approval is limited to this picture revision; it does not set
`human_creative_approval=true` and does not approve delivery.

## Phase B - Apply Only After Explicit Owner Approval

Phase B begins only after the owner replies in the fresh TERRA session with an
explicit approve or revise decision. TERRA must save the owner's exact decision
text and the approved stable IDs to:

`owner_gate/f1_picture_revision_verdict.json`

If revised, return to Phase A2 once. Do not enter an autonomous multi-round loop.

### Piece B1 - Apply One Stable Picture Diff

Build a fresh `.tmp/loop_f1_blind_reproducibility/candidate_v2/` using existing
repo-owned composition/render capabilities. A pilot-only session driver may be
saved inside the Owner Zone for auditability, but it must not become a repo
tool, helper, or renderer.

Requirements:

- replace only the owner-approved stable picture clip;
- preserve that clip's timeline in/out, duration, and cut boundaries;
- preserve title/poem/closing-note text exactly from the approved script;
- preserve audio choice and timing;
- preserve all other picture assets and their order;
- keep `human_creative_approval=false` and
  `final_delivery_claimed=false`;
- write fresh artifacts and QA; do not copy stale PASS reports as evidence.

### Piece B2 - Write Semantic Diff And Carried Decision

Write `candidate_v2/f1_semantic_diff.json` proving:

- exactly one stable picture clip changed its source/asset/lineage fields;
- every timeline timing field is unchanged;
- `audio`, `overlays/text`, settings, and unaffected transitions/effects are
  semantically unchanged, or explicitly marked `review` with a reason;
- candidate v1 hashes remain identical to Piece A1.

Append the Skill's six minimum decision fields to candidate v2 provenance:

- `proposal_by`
- `verdict_by`
- `delegation_scope`
- `evidence_refs`
- `applied_diff`
- `carry_forward`

Record the three telemetry values: owner decision rounds, minutes per round,
and missing-handle findings.

### Piece B3 - Render And Verify

Run from `C:\Users\user\Desktop\video_pipeline` with
`C:\Users\user\miniconda3\python.exe`.

```powershell
C:\Users\user\miniconda3\python.exe tools\verify_beat_cut_alignment.py --timeline .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --beats .tmp\loop_f1_blind_reproducibility\candidate_v2\run\soundtrack_probe_report.json --window-start 18 --window-end 44 --fps 30 --out .tmp\loop_f1_blind_reproducibility\candidate_v2\beat_cut_alignment_report.json --json
```

Expected exit code: `0`, `pass=true`, and
`within_one_frame_ratio=1.0`.

```powershell
ffprobe -v error -show_entries format=duration -show_entries stream=codec_type,codec_name,width,height -of json .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run .tmp\loop_f1_blind_reproducibility\candidate_v2\run --out-dir .tmp\loop_f1_blind_reproducibility\candidate_v2\rendered_qa --json
```

Expected exit code: `0` for each. Evidence must show H.264 1920x1080 plus
audio, duration within one frame of candidate v1, and rendered QA `pass=true`.

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py perception-field-check .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --out .tmp\loop_f1_blind_reproducibility\candidate_v2_perception
git diff --check
```

Expected exit code: `0`. Perception coverage is sampling evidence only; it does
not prove that f1 is aesthetically fixed.

Produce an after/before ending strip or contact sheet with stable clip IDs. The
owner must give a final f1 taste verdict after viewing it. Machine gates cannot
substitute for this verdict.

## Success Classification

Reproducibility is **PASS** only when all are true:

1. TERRA reached an owner-approved proposal without answer leakage.
2. Exactly one stable-ID picture diff was applied.
3. Story spine, final round/formation landing, duration, beat boundaries,
   approved text, and audio were preserved.
4. Objective verification passed on fresh artifacts.
5. The owner viewed before/after evidence and marked f1 resolved.
6. The six decision fields and three telemetry values were carried forward.
7. No source/Skill/helper/route change was made.

Reproducibility is **FAIL** when the Skill/context is insufficient, an answer
must be leaked, a source edit/helper is required, the wrong layer changes, the
agent bypasses the owner gate, or the owner rejects the result after the one
allowed revision.

Reproducibility remains **UNKNOWN** while waiting for either owner gate or when
required evidence cannot be produced for an external reason.

## Stop-Loss

- Phase A must stop at the owner gate. No autonomous continuation.
- One owner revision round and one implementation repair per failure class.
- Stop before any write outside the Owner Zone.
- Stop rather than reading a forbidden answer source.
- Stop if a new helper, dependency, source-code edit, route change, threshold
  relaxation, reference-film use, or delivery/creative approval is required.
- Preserve candidate v1 and all pre-existing dirty-tree files byte-for-byte.
- A repo-wide full suite is not part of this taste-loop experiment. Run only
  the named focused artifact gates; unrelated live-provider instability must
  not consume this test.

## Final Report Required

Write:

`.tmp/loop_f1_blind_reproducibility/f1_blind_reproducibility_report.md`

Start with `[WORKER REPORT - REVIEW MODE]` and include:

- Phase A proposal paths and `WAITING_OWNER` evidence;
- owner verdict quoted verbatim;
- stable-ID semantic diff without ordinal-only identification;
- commands, exit codes, and material output lines;
- before/after visual evidence paths;
- candidate v1 hash preservation;
- six decision fields and three telemetry values;
- exact final `git status --short` and diff-scope statement;
- deviations, skips, blockers, and literal `No deviations` when true;
- final `PASS`, `FAIL`, or `UNKNOWN` classification;
- explicit confirmation that this result does not approve creative delivery and
  both approval/delivery flags remain false.
