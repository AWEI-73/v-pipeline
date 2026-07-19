# Work Order: V Pipeline Editorial Reviewer core closure

Date: 2026-07-19
Owner profile: bounded implementation worker (LUNA high/xhigh or equivalent)
Starting HEAD: `a2c0f9f553aa5b429df94eab02f610920b8b39cb`
Target state: `WAITING_INTEGRATOR_EDITORIAL_REVIEWER_CORE_CLOSURE_REVIEW`

## Goal

Close the correctness findings from the Editorial Reviewer review without
blocking the reviewer on the currently unavailable picture elementary-stream
fingerprint capability.

The picture fingerprint gap is explicitly deferred. When picture fingerprint is
unknown, the system must fail closed and refuse visual evidence reuse. Do not
add a new adapter, private ffmpeg command, renderer, Stage, route runner,
cache, LLM runtime, or repair authority.

## Scope

Implement and test only these four items:

1. evidence `source_binding.subject_sha256` must equal the manifest subject;
2. bound fingerprints must be valid hexadecimal SHA-256 values, while unbound
   fingerprints require an explicit reason;
3. a bounded picture change must regenerate `wall_index` whenever a wall page
   is invalidated, and combined audio+subtitle changes must take the correct
   combined branch;
4. the registered reviewer validator must expose an executable reference to
   the existing public `video_tools.py reviewer-policy --validate-review`
   surface, without modifying `video_tools.py` or adding a new tool.

Do not claim that picture fingerprint reuse is implemented. Preserve the
explicit `picture_stream_probe_not_supplied` boundary and fail closed.

## Read first

Read `AGENTS.md`, `RUNBOOK.md`, `HANDOFF_CURRENT.md`, the previous convergence
and operational-closure reports, this work order, and the current reviewer and
timeline implementations. Use codebase-memory-mcp first for discovery.

## Owner zone

May edit only:

- `video_pipeline_core/reviewer_registry.py`
- `video_pipeline_core/timeline_review_packet.py`
- `skills/editorial-reviewer.md`
- `tests/test_reviewer_registry.py`
- `tests/test_timeline_review_packet.py`
- `tests/test_reviewer_flow_acceptance.py`
- `.tmp/editorial_reviewer_core_closure/**`
- this work order append-only for the final stop report

Forbidden: all nine S9 dirty files, `RUNBOOK.md`, `HANDOFF_CURRENT.md`,
`video_tools.py`, production render/audio/subtitle/effect code, source media,
accepted Canon 67 artifacts, registry files outside the listed skill contract,
git history, and any new adapter/tool/stage.

## Ordered tasks

### 1. Source binding and fingerprint validation

Write RED tests first. A bound evidence item's
`source_binding.subject_sha256` must exactly equal the top-level
`subject.sha256`. Any mismatched binding must fail closed. Bound fingerprint
values must match 64 hexadecimal characters; unbound values must include a
reason. Keep version-1 review compatibility.

### 2. Bounded reuse correctness

Write RED tests first. If a changed picture window intersects any
`timeline_wall`, invalidate/regenerate the intersecting walls and
`timeline_wall_index`. Add a combined audio+subtitle change test; it must
regenerate both audio and subtitle evidence rather than taking the audio-only
branch.

Unknown picture fingerprint must continue to reject reuse with the existing
fail-closed error. Do not convert an unknown value into a guessed hash.

### 3. Executable capability reference

Keep one canonical reviewer capability and no duplicate owner. Update only the
skill contract so the capability points to the existing public
`video_tools.py reviewer-policy --validate-review` command surface. Verify that
`dispatch-capabilities --id cap.editorial-reviewer.structured-review-validation.v1 --json`
returns a non-empty executable reference. If the current capability executor
cannot represent this without modifying a forbidden file or adding a tool,
stop as `STRUCTURAL_REVIEWER_COMMAND_SURFACE_GAP`.

## Acceptance

Run RED before each behavior change, then:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_reviewer_registry `
  tests.test_reviewer_flow_acceptance `
  tests.test_timeline_review_packet `
  tests.test_skill_index `
  tests.test_skill_tool_contracts `
  tests.test_pipeline_skill_boundaries -v

C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --json
C:\Users\user\miniconda3\python.exe video_tools.py dispatch-capabilities --id cap.editorial-reviewer.structured-review-validation.v1 --json
C:\Users\user\miniconda3\python.exe video_tools.py reviewer-flow-acceptance --level deep --scenario all --artifact-dir .tmp/editorial_reviewer_core_closure/flow --out .tmp/editorial_reviewer_core_closure/reviewer_flow_acceptance.json
git diff --check
```

After all focused checks pass, run the full suite exactly once. Do not alter
unrelated failures. The packet must include negative source-binding evidence,
invalid fingerprint evidence, stale-index evidence, combined-delta evidence,
and the dispatch query showing the non-empty command reference.

## Stop-loss

Stop at the last green state after one LOCAL correction if the same failure
class recurs, if any forbidden file must change, if version-1 behavior breaks,
or if a new adapter/tool/stage is required. Preserve all stop evidence. Do not
create hand-written PASS artifacts or bypass the public route.

## Report

Write `.tmp/editorial_reviewer_core_closure/final/worker_report.md` with
pre/post status, exact files, RED/GREEN exits, focused/full-suite results,
dispatch output, negative evidence paths and hashes, deviations, skips,
unknowns, and confirmation that all nine S9 dirty files are byte-for-byte
unchanged. Keep `human_creative_approval=false` and
`final_delivery_claimed=false`.
