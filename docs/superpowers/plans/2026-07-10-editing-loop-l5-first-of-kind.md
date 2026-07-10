# Editing Loop L5 First-of-Kind Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Certify the first L5 Rendered Review Loop on the existing Canon 67 candidate_v2 by composing current V Pipeline review/verify capabilities, producing coordinate-backed findings, and stopping at an owner taste gate without adding a new orchestrator, driver, schema, or production helper.

**Architecture:** `editing-loop-director` is the control doctrine; the executing agent reads four carried-context sources and calls existing public V Pipeline CLIs. All experiment writes stay under one `.tmp` Owner Zone until the owner verdict. L5 emits findings and verdict evidence only; it never edits or rerenders the timeline. Any demonstrated need for a finding adapter becomes a separate TDD plan after this pilot.

**Tech Stack:** Python 3, existing `video_tools.py` commands, existing `tools/rendered_product_qa.py` and `tools/verify_beat_cut_alignment.py`, ffprobe/ffmpeg evidence, JSON/Markdown artifacts, Git, `unittest`.

**Execution context:** Run this evidence pilot in the current workspace rather than a new worktree because its immutable input is the existing `.tmp/loop_f1_blind_reproducibility/candidate_v2`. Before the owner verdict, writes are forbidden outside `.tmp/editing_loop_l5_first_of_kind/**`. This is a bounded exception to normal feature-work isolation; no production code is authorized by this plan.

**Required doctrine:** Read `AGENTS.md`, `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`, `skills/pipeline-boundary.md`, `skills/editing-loop-director.md`, and `docs/pilots/2026-07-10-editing-loop-f1-forward-test-evidence.md` before execution. Use @project-handoff to restore context and @superpowers:verification-before-completion before any PASS claim.

---

## File Map

Experiment Owner Zone（create during execution）:

- `.tmp/editing_loop_l5_first_of_kind/input_freeze.json` — immutable input identities, hashes, flags and context refs.
- `.tmp/editing_loop_l5_first_of_kind/audit_applicability.json` — which existing audits apply, do not apply, or are unavailable, with reasons.
- `.tmp/editing_loop_l5_first_of_kind/objective/**` — fresh machine audit outputs.
- `.tmp/editing_loop_l5_first_of_kind/perception/**` — fresh wall/coverage/evidence pyramid.
- `.tmp/editing_loop_l5_first_of_kind/review/l5_review_packet_v1.json` — experimental normalized findings; not a registered production artifact.
- `.tmp/editing_loop_l5_first_of_kind/review/l5_review_report.md` — agent review, rubric answers, coordinates and blind spots.
- `.tmp/editing_loop_l5_first_of_kind/owner_gate/l5_owner_verdict.json` — exact owner verdict; created only after owner response.
- `.tmp/editing_loop_l5_first_of_kind/l5_first_of_kind_report.md` — final PASS/FAIL/UNKNOWN evidence report.

Durable repo files（modify only after final owner verdict）:

- `docs/pilots/2026-07-10-editing-loop-l5-first-of-kind-evidence.md` — compact evidence summary; no raw media.
- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md` — update L5 maturity and next bounded task only if owner certifies L5.
- `skills/editing-loop-director.md` — record the certified L5 scope and observed limitations only if owner certifies L5.

Explicitly not created or modified:

- no `video_pipeline_core/**`, `tools/**`, `video_tools.py`, tests, registries, artifact dictionaries or route code;
- no formal finding schema, normalizer adapter, loop driver, journal, timeline v2 or dirty matrix;
- no candidate_v2 mutation, copy-over, render or approval-flag change.

---

## Chunk 1: Freeze And Objective Evidence

### Task 1: Freeze The Four Carried-Context Inputs

**Files:**
- Read: `docs/pilots/2026-07-10-opening-0044-script-v1.md`
- Read: `.tmp/loop_pilot_0044/selects_manifest.json`
- Read: `.tmp/loop_f1_blind_reproducibility/candidate_v2/source_provenance.json`
- Read: `.tmp/loop_f1_blind_reproducibility/candidate_v2/run/edit_decision_plan.json`
- Read: `.tmp/loop_f1_blind_reproducibility/candidate_v2/run/timeline_build.json`
- Read: `.tmp/loop_f1_blind_reproducibility/candidate_v2/f1_final_taste_verdict_waiting.json`
- Create: `.tmp/editing_loop_l5_first_of_kind/input_freeze.json`

- [ ] **Step 1: Confirm candidate_v2 is the certified f1 output**

Run:

```powershell
Get-FileHash -Algorithm SHA256 .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4
```

Expected: hash equals
`EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6`.
If it differs, classify L5 as `UNKNOWN_INPUT_DRIFT` and stop before audits.

- [ ] **Step 2: Confirm all carried-context sources parse or read as UTF-8**

Run a read-only Python command that parses the JSON inputs and decodes the
approved script as UTF-8. Expected: exit `0`, no `U+FFFD`, and both approval
flags read as `false`.

- [ ] **Step 3: Write the freeze record**

Use `apply_patch` to create `input_freeze.json` with:

```json
{
  "artifact_role": "experimental_l5_input_freeze",
  "version": 1,
  "candidate": ".tmp/loop_f1_blind_reproducibility/candidate_v2/run/final.mp4",
  "candidate_sha256": "EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6",
  "approved_script_ref": "docs/pilots/2026-07-10-opening-0044-script-v1.md",
  "selects_manifest_ref": ".tmp/loop_pilot_0044/selects_manifest.json",
  "provenance_ref": ".tmp/loop_f1_blind_reproducibility/candidate_v2/source_provenance.json",
  "run_dir": ".tmp/loop_f1_blind_reproducibility/candidate_v2/run",
  "source_l1_verdict_ref": ".tmp/loop_f1_blind_reproducibility/candidate_v2/f1_final_taste_verdict_waiting.json",
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
```

- [ ] **Step 4: Re-read the freeze record**

Expected: valid JSON, paths resolve, hash matches Step 1, flags remain false.

### Task 2: Declare Audit Applicability Before Running Tools

**Files:**
- Create: `.tmp/editing_loop_l5_first_of_kind/audit_applicability.json`

- [ ] **Step 1: Inspect candidate artifacts without inventing missing inputs**

Check whether candidate_v2 has a subtitle SRT/caption event source, assembly
plan, audio stream, beat report inputs and canonical timeline.

- [ ] **Step 2: Record the applicability matrix**

Use `apply_patch` to record one of `applicable`, `not_applicable`, or
`unavailable` for each audit. Initial expected decisions:

| Audit | Expected state | Reason |
|---|---|---|
| rendered product QA | applicable | canonical run and rendered candidate exist |
| final product verify | applicable | video＋audio candidate exists |
| black-frame audit | applicable | rendered video exists |
| timeline invariants | applicable | `timeline_build.json` exists |
| new-visual audit | applicable | timeline clips exist |
| beat alignment | applicable | timeline and soundtrack probe exist |
| verify evidence | applicable | candidate and timeline exist |
| perception field | applicable | rendered candidate exists |
| caption audit | not_applicable unless real subtitle input exists | overlay title/poem text is not automatically a caption track |
| visual fatigue | unavailable unless a compatible assembly plan exists | do not synthesize an assembly plan for a PASS |

- [ ] **Step 3: Verify no threshold is added or relaxed**

Expected: the matrix only selects valid tools; it does not modify tool defaults,
reinterpret `not_applicable` as PASS, or create synthetic evidence.

### Task 3: Run Fresh Objective Audits

**Files:**
- Create: `.tmp/editing_loop_l5_first_of_kind/objective/**`

- [ ] **Step 1: Run rendered product QA**

```powershell
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run .tmp\loop_f1_blind_reproducibility\candidate_v2\run --out-dir .tmp\editing_loop_l5_first_of_kind\objective\rendered_qa --json
```

Record exit code and output. Do not require PASS in advance; any fresh failure
becomes an objective finding.

- [ ] **Step 2: Run final product verify**

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py final-product-verify .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --out-dir .tmp\editing_loop_l5_first_of_kind\objective\final_verify --samples 16
```

Expected output set: verify bundle, keyframe grid, visual audit, soundtrack
probe and extracted audio or explicit no-audio classification.

- [ ] **Step 3: Run black/blank-frame audit**

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py black-frame-audit .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --out .tmp\editing_loop_l5_first_of_kind\objective\black_frame_audit.json
```

- [ ] **Step 4: Run timeline invariants**

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py timeline-audit .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --expected-duration 44 --out .tmp\editing_loop_l5_first_of_kind\objective\timeline_invariants.json
```

- [ ] **Step 5: Run new-visual-information audit**

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py new-visual-audit .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --out .tmp\editing_loop_l5_first_of_kind\objective\new_visual_information_audit.json
```

- [ ] **Step 6: Run beat alignment with the certified window**

```powershell
C:\Users\user\miniconda3\python.exe tools\verify_beat_cut_alignment.py --timeline .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --beats .tmp\loop_f1_blind_reproducibility\candidate_v2\run\soundtrack_probe_report.json --window-start 18 --window-end 44 --fps 30 --out .tmp\editing_loop_l5_first_of_kind\objective\beat_cut_alignment_report.json --json
```

- [ ] **Step 7: Read back every objective output**

Expected: all JSON parses; each report retains its own `pass`/finding semantics.
Build no aggregate PASS yet. Record objective failures and warnings verbatim for
normalization in Chunk 2.

### Task 4: Build Fresh Perception Evidence

**Files:**
- Create: `.tmp/editing_loop_l5_first_of_kind/objective/verify_evidence/**`
- Create: `.tmp/editing_loop_l5_first_of_kind/perception/**`

- [ ] **Step 1: Generate the existing four-layer verify evidence**

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py verify-evidence .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --timeline .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --out-dir .tmp\editing_loop_l5_first_of_kind\objective\verify_evidence
```

- [ ] **Step 2: Generate a fresh perception field**

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py perception-field-check .tmp\loop_f1_blind_reproducibility\candidate_v2\run\final.mp4 --out .tmp\editing_loop_l5_first_of_kind\perception
```

- [ ] **Step 3: Read coverage before interpreting taste**

Expected: record shot count, sample count and gaps. Coverage PASS means only
that the planned visual field was sampled; it is not a creative-quality PASS.

- [ ] **Step 4: Verify candidate immutability**

Re-run `Get-FileHash` on candidate_v2. Expected: the same SHA-256 as Task 1.

---

## Chunk 2: Agent Review And Owner Gate

### Task 5: Answer The Canon 67 L5 Rubric With Coordinates

**Files:**
- Read: `docs/pilots/2026-07-10-opening-0044-script-v1.md`
- Read: `.tmp/editing_loop_l5_first_of_kind/objective/**`
- Read: `.tmp/editing_loop_l5_first_of_kind/perception/**`
- Create: `.tmp/editing_loop_l5_first_of_kind/review/l5_review_report.md`

- [ ] **Step 1: Review the candidate in story order**

Answer these questions separately; each answer must cite a stable clip/overlay
ID, time range, wall cell or machine check:

1. Does 0–11s establish place and identity before decorative text dominates?
2. Does the title match the approved script and remain readable through its
   intended lifecycle?
3. Do the three poem lines appear in the approved order without overlap,
   corruption or insufficient reading time?
4. Does 18–44s progress rather than merely repeat beat-perfect photographs?
5. Does the ending preserve collective convergence and a clear final landing?
6. Does soundtrack energy support the picture rhythm, within what the probe can
   actually establish?
7. Which observations are objective, which are agent judgment, and which remain
   owner taste?

- [ ] **Step 2: Declare blind spots**

At minimum declare: no speech-content judgment for this music-led slice; no
caption audit without subtitle input; no whole-film emotional-arc claim; no
delivery or legal/music approval.

- [ ] **Step 3: Identify suspicious windows only from evidence**

If a question is not confidently answered, cite the exact time window and
existing wall/verify evidence. Create a focused strip or dynamic comparison
inside the Owner Zone only when the existing pyramid is insufficient. Record
the command in the report; do not create a reusable tool.

### Task 6: Write The Experimental L5 Findings Packet

**Files:**
- Create: `.tmp/editing_loop_l5_first_of_kind/review/l5_review_packet_v1.json`

- [ ] **Step 1: Normalize without erasing source semantics**

For every finding, write:

```json
{
  "finding_id": "l5_f001",
  "scope": {"stable_ids": [], "time_range": [0.0, 0.0]},
  "class": "objective",
  "statement": "One falsifiable problem statement",
  "evidence_refs": [
    {"path": "relative/path", "anchor": {"time_range": [0.0, 0.0], "cell_id": null, "check_id": "source_check"}, "produced_by": "source capability"}
  ],
  "source_severity": "fail|warn|agent_judgment",
  "owner_capability": "picture",
  "proposed_next_loop": "L1",
  "owner_verdict_required": true,
  "status": "open"
}
```

Preserve the original source report path and severity. Do not convert warnings
to failures or agent taste to objective findings. Existing reports may contain
legacy `next_action`/branch suggestions; retain them only as quoted source
metadata and never execute them as routing instructions in this LOOP.

- [ ] **Step 2: Include zero-finding evidence honestly**

If no actionable finding exists, write `findings: []` plus completed rubric,
limitations and evidence refs. Do not invent a defect merely to exercise
routing.

- [ ] **Step 3: Carry the six minimum decision fields**

At proposal time: `proposal_by=agent`, `verdict_by=null`, exact
`delegation_scope`, evidence refs, `applied_diff="none; L5 is review-only"`, and
carry-forward limitations/flags.

- [ ] **Step 4: Run JSON and UTF-8 read-back**

Expected: valid JSON, no `U+FFFD`, no suspicious repeated `?`, all evidence paths
resolve, and both approval flags remain false.

### Task 7: Stop At The Owner Taste Gate

**Files:**
- Do not create yet: `.tmp/editing_loop_l5_first_of_kind/owner_gate/l5_owner_verdict.json`

- [ ] **Step 1: Present the review packet**

Show the owner:

- objective failures/warnings separately from taste findings;
- each finding's time range and clickable visual evidence;
- blind spots and `not_applicable` audits;
- proposed next LOOP for each finding;
- a direct request to approve/revise the findings and separately judge L5
  reproducibility.

- [ ] **Step 2: Stop with an explicit state**

Output `WAITING_OWNER_L5_REVIEW_VERDICT`. Do not modify the candidate, do not
route or implement a finding, and do not treat silence as approval.

---

## Chunk 3: Verdict, Certification And Handoff

### Task 8: Record The Owner Verdict Without Rerendering

**Files:**
- Create: `.tmp/editing_loop_l5_first_of_kind/owner_gate/l5_owner_verdict.json`
- Modify: `.tmp/editing_loop_l5_first_of_kind/review/l5_review_packet_v1.json`

- [ ] **Step 1: Save the exact owner response**

The verdict must separately state:

- accepted, revised, rejected or waived finding IDs;
- L5 Skill reproducibility: `PASS`, `FAIL`, or `UNKNOWN`;
- selected first next LOOP/finding, if any;
- unchanged creative/delivery flags.

- [ ] **Step 2: Update statuses only within verdict scope**

Do not erase rejected proposals. Record owner changes and retain agent-original
statements for auditability.

- [ ] **Step 3: Verify candidate hash remains unchanged**

Expected: still
`EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6`.

### Task 9: Classify The L5 First-of-Kind

**Files:**
- Create: `.tmp/editing_loop_l5_first_of_kind/l5_first_of_kind_report.md`

- [ ] **Step 1: Apply the classification rules**

`PASS` only when:

1. all four context sources resolved;
2. applicable audits produced fresh readable evidence;
3. the agent answered the rubric with coordinates and blind spots;
4. finding normalization preserved source semantics;
5. L5 made no timeline/media change;
6. the owner accepted the review process as reproducible;
7. the candidate hash and both approval flags stayed unchanged.

Use `FAIL` for an in-scope process failure. Use `UNKNOWN` when external input or
the owner verdict is missing. Machine gates alone cannot create PASS.

- [ ] **Step 2: Evaluate hardening triggers**

Record each Product Spec §8 trigger as `not_observed` or `observed` with evidence.
In particular, note whether inconsistent source finding shapes caused an actual
loss or unreliable manual conversion. Observation authorizes a separate plan;
it does not authorize adapter code in this task.

- [ ] **Step 3: Write exact commands, exits, deviations and limitations**

Include any LOCAL repair attempts. Do not claim full-film, L2/L3/L4, creative,
delivery, legal or music approval.

### Task 10: Persist Only The Durable Result

**Files:**
- Create: `docs/pilots/2026-07-10-editing-loop-l5-first-of-kind-evidence.md`
- Modify: `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
- Modify: `skills/editing-loop-director.md`

- [ ] **Step 1: Write the compact evidence summary**

Include the candidate hash, applicable audit results, accepted findings, owner
verdict, reproducibility scope, raw `.tmp` pointers and hardening-trigger result.
Do not add raw video or duplicate full reports to Git.

- [ ] **Step 2: Update maturity only if the owner verdict is PASS**

Change L5 from `DOCTRINE` to `CERTIFIED` with explicit scope
`Canon 67 / 44s / review-only`. If verdict is FAIL or UNKNOWN, keep L5 doctrine
and record the result/limitation without upgrading maturity.

- [ ] **Step 3: Run focused document and Skill verification**

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_skill_index tests.test_pipeline_skill_boundaries tests.test_doc_reference_hygiene
git diff --check
```

Expected: 17 tests, `OK`, exit `0`; no whitespace errors.

- [ ] **Step 4: Re-read Chinese artifacts as strict UTF-8**

Expected: no decode error, no `U+FFFD`, no suspicious repeated literal `?`.

- [ ] **Step 5: Commit the durable evidence only**

```powershell
git add -- docs/pilots/2026-07-10-editing-loop-l5-first-of-kind-evidence.md docs/construction-guides/2026-07-10-editing-loop-product-spec.md skills/editing-loop-director.md
git diff --cached --check
git commit -m "Certify editing loop L5 review"
```

Do not stage unrelated dirty-tree files or `.tmp` media.

### Task 11: Open The Next Bounded Plan, Not An Engine

**Files:**
- Create only after owner selection: `docs/superpowers/plans/YYYY-MM-DD-editing-loop-<next-loop>-<finding>.md`

- [ ] **Step 1: Select from accepted evidence**

Use the owner-selected accepted finding. If no actionable finding exists, do
not fabricate one; choose a separate known gap only through a new owner decision.

- [ ] **Step 2: Keep the next plan layer-bounded**

The next plan may certify one L2, L3 or L4 pattern. It must not implement the
whole remaining L0–L5 program.

- [ ] **Step 3: If a hardening trigger fired, plan it separately with TDD**

Write a focused failing test and minimal adapter/helper plan. Do not combine
architecture hardening with the creative finding repair.
