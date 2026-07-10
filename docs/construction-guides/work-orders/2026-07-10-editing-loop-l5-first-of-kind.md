# Editing Loop L5 Review First-of-Kind Work Order

Status: **READY FOR PHASE A**

## Goal And Source

Certify whether a fresh agent can use `skills/editing-loop-director.md` to run
one complete **L5 review-only LOOP** over the certified Canon 67 44-second
`candidate_v2`:

```text
four carried-context sources
→ existing V Pipeline review/verify capabilities
→ coordinate-backed objective/taste findings
→ owner review gate
```

The accepted product direction is defined by:

1. `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
2. `docs/superpowers/plans/2026-07-10-editing-loop-l5-first-of-kind.md`
3. `docs/pilots/2026-07-10-editing-loop-f1-forward-test-evidence.md`

This work order is the sole execution basis. The product plan is rationale and
detail, not permission to expand scope.

## Experiment Boundary

This is a Skill reproducibility and evidence-carrying test. It is not a request
to improve the film, fix a finding, build a helper, or certify delivery.

Known immutable candidate:

- video: `.tmp/loop_f1_blind_reproducibility/candidate_v2/run/final.mp4`
- expected SHA-256:
  `EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6`
- source L1 classification: `PASS_F1_RESOLVED`
- `human_creative_approval=false`
- `final_delivery_claimed=false`

L1 PASS must not be generalized into L5 PASS. Phase A must produce evidence and
stop; only the owner can judge whether the L5 review was useful and reproducible.

## Required Read Order

Read in this order before calling tools:

1. `AGENTS.md`
2. this work order
3. `skills/pipeline-boundary.md`
4. `skills/editing-loop-director.md`
5. `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
6. `docs/pilots/2026-07-10-editing-loop-f1-forward-test-evidence.md`
7. `docs/pilots/2026-07-10-opening-0044-script-v1.md`
8. `.tmp/loop_pilot_0044/selects_manifest.json`
9. `.tmp/loop_f1_blind_reproducibility/candidate_v2/source_provenance.json`
10. `.tmp/loop_f1_blind_reproducibility/candidate_v2/run/**`
11. `.tmp/loop_f1_blind_reproducibility/candidate_v2/f1_final_taste_verdict_waiting.json`

The worker may inspect `--help` and existing public implementation surfaces only
to call the commands named below. Do not use prior Fable/SOL/TERRA conversations
or expected-answer notes to invent a review conclusion.

## Environment

- repo: `C:\Users\user\Desktop\video_pipeline`
- Python: `C:\Users\user\miniconda3\python.exe`
- shell: PowerShell
- media tools: repo-configured `ffmpeg` / `ffprobe`

Do not install dependencies or change environment configuration.

## Owner Zone

### Phase A writes

The worker may write only:

- `.tmp/editing_loop_l5_first_of_kind/**`

Required output areas:

- `input_freeze.json`
- `audit_applicability.json`
- `objective/**`
- `perception/**`
- `review/l5_review_packet_v1.json`
- `review/l5_review_report.md`
- `phase_a_worker_report.md`

### Phase B writes（only after an explicit owner verdict in the same/new session）

- `.tmp/editing_loop_l5_first_of_kind/**`
- `docs/pilots/2026-07-10-editing-loop-l5-first-of-kind-evidence.md`
- maturity/result paragraphs only in:
  - `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
  - `skills/editing-loop-director.md`

Phase B is not authorized by the Phase A prompt. It requires the owner's exact
verdict text and a new explicit continuation instruction.

## Forbidden And Read-Only Zone

Never modify:

- `.tmp/loop_f1_blind_reproducibility/**`
- `.tmp/loop_pilot_0044/**`
- every other pre-existing `.tmp/**`
- `video_pipeline_core/**`, `tools/**`, `tests/**`, `video_tools.py`
- `AGENTS.md`, `skills/INDEX.md`, `skills/pipeline-boundary.md`
- registries, artifact dictionaries, reviewer/delivery semantics
- raw source material or reference-film footage
- unrelated dirty-tree files: `r`, `supply_review.json`, existing Canon work orders

Do not stage, commit, clean, delete, reset, push, open a PR, or overwrite the
candidate. Do not create a route runner, driver, formal schema/artifact,
normalizer, helper, journal, timeline v2, dirty matrix or automatic reroute.

Legacy audit outputs may contain `next_action` or branch suggestions. Preserve
them as source metadata only; never execute them as routing instructions.

## Delegated Decisions

The worker may decide:

- which existing wall/verify image best supports a rubric answer;
- whether an additional focused strip/dynamic is necessary inside the Owner Zone;
- finding wording, stable scope and proposed next LOOP when directly supported
  by evidence;
- which audit is `not_applicable` or `unavailable`, with an explicit input-based
  reason.

The worker may not decide:

- final taste, whole-film quality, creative approval or delivery;
- whether an open finding is accepted/resolved/waived;
- whether a helper/adapter should be built;
- whether to modify any timeline/media/product source.

## Phase A Ordered Pieces

### Piece A1 — Freeze Input And Git State

1. Record `git status --short` without changing it.
2. SHA-256 the candidate and compare to the pinned value.
3. Strictly read the approved script as UTF-8 and parse candidate JSON context.
4. Write `input_freeze.json` with candidate/hash, four context refs, source L1
   verdict and both false approval flags.

If the hash differs or a required context source is missing/corrupt, stop as
`UNKNOWN_INPUT_DRIFT_OR_MISSING_CONTEXT` before running review tools.

### Piece A2 — Declare Audit Applicability

Before running audits, write `audit_applicability.json` with
`applicable | not_applicable | unavailable` and a reason for:

- rendered product QA
- final product verify
- black-frame audit
- timeline invariants
- new-visual audit
- beat alignment
- verify evidence
- perception field
- caption audit
- visual fatigue

Expected evidence-based boundary:

- caption audit is not applicable unless a real subtitle/caption input exists;
- visual fatigue is unavailable unless a compatible assembly plan exists;
- an omitted input must not be synthesized to manufacture PASS.

### Piece A3 — Produce Fresh Objective Evidence

Run exactly these commands from the repo root:

```powershell
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run .tmp\loop_f1_blind_reproducibility\candidate_v2\run --out-dir .tmp\editing_loop_l5_first_of_kind\objective\rendered_qa --json

C:\Users\user\miniconda3\python.exe video_tools.py final-product-verify .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --out-dir .tmp\editing_loop_l5_first_of_kind\objective\final_verify --samples 16

C:\Users\user\miniconda3\python.exe video_tools.py black-frame-audit .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --out .tmp\editing_loop_l5_first_of_kind\objective\black_frame_audit.json

C:\Users\user\miniconda3\python.exe video_tools.py timeline-audit .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --expected-duration 44 --out .tmp\editing_loop_l5_first_of_kind\objective\timeline_invariants.json

C:\Users\user\miniconda3\python.exe video_tools.py new-visual-audit .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --out .tmp\editing_loop_l5_first_of_kind\objective\new_visual_information_audit.json

C:\Users\user\miniconda3\python.exe tools\verify_beat_cut_alignment.py --timeline .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --beats .tmp\loop_f1_blind_reproducibility\candidate_v2\run\soundtrack_probe_report.json --window-start 18 --window-end 44 --fps 30 --out .tmp\editing_loop_l5_first_of_kind\objective\beat_cut_alignment_report.json --json

C:\Users\user\miniconda3\python.exe video_tools.py verify-evidence .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --timeline .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --out-dir .tmp\editing_loop_l5_first_of_kind\objective\verify_evidence

C:\Users\user\miniconda3\python.exe video_tools.py perception-field-check .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --out .tmp\editing_loop_l5_first_of_kind\perception
```

Expected command exits for the known candidate: `0`. A nonzero audit caused by
a real detected defect is evidence, not permission to relax thresholds. A
command/environment failure gets one LOCAL repair attempt for that failure
class; record the first failure before retrying.

Parse and preserve each source report's own PASS/warn/fail semantics. Coverage
PASS proves sampling coverage only, never taste.

### Piece A4 — Perform Agent L5 Review

Read the fresh evidence and answer, with stable IDs/time/cell/check coordinates:

1. Does 0–11s establish place and identity before decorative text dominates?
2. Is title text exact and readable through its intended lifecycle?
3. Are poem lines exact, ordered, non-overlapping and readable long enough?
4. Does 18–44s progress rather than repeat beat-perfect material?
5. Does the ending preserve collective convergence and a clear final landing?
6. What can the soundtrack evidence actually establish about picture rhythm?
7. Which observations are objective, agent judgment, or owner taste?

Write `review/l5_review_report.md` with rubric answers and blind spots. At
minimum declare: no speech-content review, no caption claim without caption
input, no whole-film emotional-arc claim, and no legal/music/delivery approval.

### Piece A5 — Write Experimental Findings Packet

Write `review/l5_review_packet_v1.json`. It is experimental and must not be
registered as a production artifact.

Each finding needs:

- stable ID and time-range scope;
- `class: objective | taste`;
- one falsifiable statement;
- source severity unchanged;
- evidence refs with path＋anchor＋producer;
- owner capability and proposed L0–L4 LOOP;
- `owner_verdict_required=true` and `status=open`.

Include the six Skill decision fields. Set
`applied_diff="none; L5 is review-only"`. If there are no actionable findings,
write an empty list with completed rubric and limitations; never invent a defect.

Strictly re-read JSON/Markdown as UTF-8, verify every evidence path resolves,
and re-hash candidate_v2.

### Piece A6 — Stop At Owner Gate

Create `phase_a_worker_report.md`, then stop with exactly:

`WAITING_OWNER_L5_REVIEW_VERDICT`

Do not create an owner-verdict artifact. Do not edit/rerender the candidate,
route a finding, update maturity, touch durable docs, stage or commit.

## Phase A Acceptance

The worker must run and report:

```powershell
Get-FileHash -Algorithm SHA256 .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4
git diff --check
git status --short
```

Material acceptance:

- candidate SHA-256 remains the pinned value;
- all applicable audit artifacts are fresh and parseable;
- applicability, rubric, packet and report exist;
- no writes occurred outside the Phase A Owner Zone;
- no source severity or agent/taste classification was promoted;
- both approval flags remain false;
- final state is `WAITING_OWNER_L5_REVIEW_VERDICT`.

`git diff --check` may show pre-existing line-ending notices but must not show a
new whitespace error. Existing dirty-tree entries must be byte-preserved.

## Phase B Outline（Not Authorized Yet）

After the owner provides an exact verdict:

1. save it verbatim to `owner_gate/l5_owner_verdict.json`;
2. preserve original agent findings and record accepted/revised/rejected/waived
   IDs separately;
3. classify L5 reproducibility `PASS | FAIL | UNKNOWN`;
4. re-hash the unchanged candidate; never rerender;
5. record every Product Spec §8 hardening trigger as observed/not observed;
6. write the compact durable evidence summary;
7. upgrade L5 maturity only for owner-certified scope;
8. run focused doc/Skill tests and stop for integrator review without staging or
   committing.

Phase B must not implement the selected finding or a hardening mechanism. Those
require a new bounded plan/work order.

## Stop-Loss

- One repair attempt per LOCAL command/evidence-generation failure class.
- Stop immediately on an owner-zone conflict or required out-of-zone edit.
- Stop instead of installing dependencies, changing thresholds, synthesizing
  missing inputs, or reading a leaked expected answer.
- A second occurrence of the same failure class is STRUCTURAL for this task;
  preserve the last verified state and report `UNKNOWN` or `FAIL` as appropriate.
- Preserve candidate_v2 and every pre-existing dirty-tree file byte-for-byte.

## Required Phase A Report

`phase_a_worker_report.md` must contain:

- exact final state and classification (`UNKNOWN` while awaiting owner);
- input hash and four context refs;
- audit applicability table;
- every command, exit code and material output summary;
- review report and findings packet paths;
- objective vs agent-judgment vs owner-taste separation;
- candidate re-hash and write-scope evidence;
- exact `git status --short`;
- deviations, skips, repairs, unresolved blind spots;
- literal `No deviations` when true;
- confirmation that no production code, timeline, media, approval flag, stage or
  commit was changed.
