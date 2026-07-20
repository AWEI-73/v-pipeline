<!-- DOCUMENT_ROLE: WORK_ORDER -->
<!-- STATUS: READY_FOR_WORKER -->

# Work Order — Editorial Reviewer v1.1 Minimal Binding Slice

Date: 2026-07-21

## Goal and source

Repair the three failures proven by the Canon 67 reviewer trial without
building the deferred reviewer-lineage platform:

1. a review must identify the exact candidate bytes it inspected and cannot
   silently claim applicability to a different candidate;
2. a soundtrack probe must identify the exact file bytes it analyzed, and a
   review packet must not call that audio evidence candidate-bound when the
   hashes do not match;
3. every SHA-256 binding added by this slice must name its hashing method.

This order supersedes the construction scope in
`.tmp/editorial_reviewer_v1_1_design_r3/implementation_work_order_final.md`.
The r2/r3 design remains read-only deferred-hardening reference, not an
implementation requirement.

## Product decision

Reviewer v1.1-minimal is **exact-subject-only**:

- Any candidate file change makes the previous review stale.
- The reviewer must run again for the changed candidate.
- There is no carry-forward, delta review, lineage family, or partial reuse in
  this slice.

This deliberately trades a future repeated review for much less machinery
now. Reuse is reconsidered only after a real second-case post-review revision
shows that re-review cost is material.

## Non-goals

- No `review_lineage_id` or applicability state machine.
- No `delta_review_record`, changed-window union, or reuse persistence.
- No five-lens three-state formalization or maturity scoring.
- No benchmark runner, new Stage, route, adapter, capability, or registry.
- No elementary-stream comparison across candidate versions.
- No bounded wall regeneration.
- No Canon 67 artifact mutation or closure reopen.
- No second-case creative judgment in this coding order.

## Owner zone (exhaustive)

Production and skill:

- `video_pipeline_core/soundtrack_probe.py`
- `video_pipeline_core/timeline_review_packet.py`
- `video_pipeline_core/reviewer_registry.py`
- `skills/editorial-reviewer.md`

Tests:

- `tests/test_soundtrack_probe.py`
- `tests/test_timeline_review_packet.py`
- `tests/test_reviewer_registry.py`
- `tests/test_skill_tool_contracts.py`

This work order itself is read-only during construction. All other repo paths,
including `video_tools.py`, `tools/**`, registries, RUNBOOK, HANDOFF, S9 files,
Canon 67 evidence, and r2/r3 design artifacts are forbidden for modification.
Do not create an execution companion; this is a bounded coding task, not a
pipeline run.

## Ordered pieces

### P0 — source-hash provenance in soundtrack probes

Add an additive block to every successful `soundtrack_probe_report`, including
the no-audio-stream result:

```json
"source_binding": {
  "path": "<the analyzed path>",
  "sha256": "<SHA-256 of exact file bytes>",
  "hash_method": "sha256_file_bytes_v1"
}
```

Existing fields and version remain compatible. Capture RED tests before the
implementation. A changed source byte must change the binding digest.

### P1 — packet-level exact audio binding

The review subject/manifest records
`hash_method: "sha256_file_bytes_v1"` next to its existing file SHA-256.

When a soundtrack probe is supplied, packet construction compares
`probe.source_binding.sha256` with the packet candidate file SHA-256. Preserve
the existing audio analysis fields, but add an explicit deterministic binding
result to the packet audio track:

- `bound_exact_candidate`
- `unbound_probe_source_binding_missing`
- `unbound_probe_source_mismatch`
- `unbound_not_supplied`

Use one stable field name chosen in production and pinned by tests. Duration
agreement must never upgrade a missing or mismatched source hash to bound.
The packet's reviewer contract must state that mix, ducking, and music claims
require `bound_exact_candidate`.

Legacy probe JSON remains readable and becomes unbound, not invalid.

### P2 — exact-subject-only editorial review binding

Keep `editorial_review` version 2. Add an opt-in top-level block identified by
`binding_contract_version: 1` with these required fields:

```json
"reviewed_subject_sha256": "<subject.sha256>",
"applies_to_candidate_sha256": "<same exact SHA-256>",
"subject_hash_method": "sha256_file_bytes_v1"
```

For binding contract version 1, validation must fail closed when:

- either SHA-256 is missing or malformed;
- `reviewed_subject_sha256 != subject.sha256`;
- `applies_to_candidate_sha256 != reviewed_subject_sha256`;
- `subject_hash_method` has any other value.

There is no legal drift or carry-forward state in this slice. Reviews without
`binding_contract_version` retain legacy v2 behavior.

Update `build_reviewer_write_contract()` and the packet-generated
`editorial_review.template.json` so a reviewer can produce a valid bound review
without reading Python source.

`write_editorial_review_receipt()` must copy the exact-subject binding fields
into its receipt after the existing material subject/packet rechecks. It does
not create or infer a different applicability state.

### P3 — skill closure

Only after P0–P2 are green, update `skills/editorial-reviewer.md` to state:

- review is exact-candidate-bound;
- candidate SHA drift makes the old review stale and requires a fresh review;
- audio/mix/ducking findings require `bound_exact_candidate`;
- v1.1-minimal has no carry-forward or delta reuse;
- the reviewer still has finding/proposal authority only and never repairs.

Do not document deferred r3 behavior as implemented.

## RED/GREEN evidence

Before each behavior change, preserve a failing focused test proving the old
gap. The final focused suite is:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_soundtrack_probe tests.test_timeline_review_packet tests.test_reviewer_registry tests.test_skill_tool_contracts -v
```

Expected final exit code: `0`.

Required negative cases:

1. changed probe source bytes change `source_binding.sha256`;
2. legacy probe without source binding produces unbound packet audio evidence;
3. mismatched probe/candidate hash produces unbound packet audio evidence;
4. duration match alone does not bind audio;
5. missing/malformed reviewed or applicable SHA fails v1 binding;
6. reviewed SHA different from subject SHA fails;
7. applicable SHA different from reviewed SHA fails;
8. unsupported hash method fails;
9. legacy v2 review without the opt-in marker still validates;
10. receipt and generated template preserve the exact-subject binding.

Also run:

```powershell
C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --json
git diff --check
```

Expected exit code for both: `0`.

Do not run the full suite in this slice. The most recent repository full-suite
baseline is already green; run one full suite only after the second-case
Reviewer forward test, when product usefulness and integration are tested
together.

## Commit boundary

After all acceptance commands are green, create one commit containing only the
eight owner-zone implementation/test files. Do not include this work order or
unrelated changes in the worker commit.

Suggested subject: `fix: bind editorial reviews to exact candidates`

## Stop-loss

- Any required edit outside the owner zone: STRUCTURAL STOP.
- Any need for lineage IDs, delta records, carry-forward, a new CLI, Stage,
  adapter, capability, or registry: STRUCTURAL STOP.
- The same failure class after one local correction: stop at the last green
  state and report the structural cause.
- An unrelated test regression is not authority to modify its owner.
- Never weaken legacy validation merely to make the new fixtures pass.

## Required report

Report:

- final state: `WAITING_INTEGRATOR_EDITORIAL_REVIEWER_V1_1_MINIMAL_BINDING_REVIEW`
  or the exact stop state;
- commit hash and exact changed files;
- RED and GREEN commands with exit codes;
- focused test count, skill audit, and `git diff --check` result;
- one generated packet/template/receipt read-back showing the bindings;
- deviations, skips, blockers, and exact pre/post git status;
- `human_creative_approval=false` and `final_delivery_claimed=false`.

