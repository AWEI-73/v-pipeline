# Work Order: V Pipeline Editorial Reviewer operational closure

Date: 2026-07-19
Owner profile: bounded implementation worker (LUNA high/xhigh or equivalent)
Starting HEAD: `a2c0f9f553aa5b429df94eab02f610920b8b39cb`
Target state: `WAITING_INTEGRATOR_EDITORIAL_REVIEWER_OPERATIONAL_CLOSURE_REVIEW`

## Goal

Close the four findings from the Editorial Reviewer convergence review so the
existing reviewer surface is both discoverable and operationally trustworthy:

1. evidence `source_binding.subject_sha256` must equal the manifest subject;
2. real timeline packets must bind a picture fingerprint when the existing
   public probe can provide one;
3. a bounded picture change must regenerate the wall index whenever any wall
   page is invalidated;
4. the registered reviewer validator must have an executable existing public
   command surface.

This is a bounded closure. Do not add a Stage, route runner, adapter, renderer,
cache service, LLM runtime, or repair authority.

## Read first

Read `AGENTS.md`, `RUNBOOK.md`, `HANDOFF_CURRENT.md`, the prior convergence
work order and report, this work order, and the current implementations of:

- `video_pipeline_core/reviewer_registry.py`
- `video_pipeline_core/timeline_review_packet.py`
- `skills/editorial-reviewer.md`
- `video_tools.py` reviewer-policy and capability-dispatch surfaces
- the focused reviewer and timeline tests

Use codebase-memory-mcp first for symbol and impact discovery. Keep it enabled.

## Owner zone

May edit only:

- `video_pipeline_core/reviewer_registry.py`
- `video_pipeline_core/timeline_review_packet.py`
- `skills/editorial-reviewer.md`
- `tests/test_reviewer_registry.py`
- `tests/test_timeline_review_packet.py`
- `tests/test_reviewer_flow_acceptance.py`
- `.tmp/editorial_reviewer_operational_closure/**`
- this work order append-only for the final stop report

Forbidden: the nine pre-existing S9 dirty files, `RUNBOOK.md`,
`HANDOFF_CURRENT.md`, `video_tools.py`, render/audio/subtitle/effect code,
source media, accepted Canon 67 artifacts, registries outside the listed skill
contract, git history, and any new adapter/tool/stage.

## Ordered tasks

### 1. Source binding and fingerprint validation

Write RED tests first. A bound evidence item must fail closed unless its
`source_binding.subject_sha256` exactly equals the top-level subject SHA-256.
Bound stream fingerprints must be valid 64-character hexadecimal SHA-256 values.
Unbound fingerprints must carry an explicit reason. Preserve version-1 review
compatibility.

Do not silently reinterpret an artifact hash as an elementary stream hash.
`audio_stream_fingerprint` may only be bound when an existing public probe
actually supplies the stream fingerprint; otherwise keep it explicitly unbound
or use a clearly named probe-artifact fingerprint field.

### 2. Real picture fingerprint binding

Trace the existing public timeline-review/probe path. Extend it only if the
existing public surface can provide a deterministic picture/elementary-stream
fingerprint. The resulting real packet must be usable by `plan_evidence_reuse`
for an unchanged-picture case.

If no existing public probe can provide this without inventing a new adapter,
stop as `STRUCTURAL_PICTURE_FINGERPRINT_PUBLIC_GAP`; do not hash arbitrary
JSON, use a private ffmpeg command, or fake a bound value.

### 3. Bounded picture reuse

When a changed picture window intersects any `timeline_wall`, regenerate the
`wall_index` as well as the intersecting wall pages. Add a regression test for
the observed stale-index case. Add one combined audio+subtitle change test so
the planner does not incorrectly take the audio-only branch when both changed.

### 4. Executable capability registration

Keep one canonical reviewer capability and no duplicate owner. Bind it to the
existing public `video_tools.py reviewer-policy --validate-review` surface (or
an already registered equivalent). `dispatch-capabilities --id
cap.editorial-reviewer.structured-review-validation.v1 --json` must return a
non-empty executable command/reference, and the capability must remain within
the existing reviewer authority boundary.

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
C:\Users\user\miniconda3\python.exe video_tools.py reviewer-flow-acceptance --level deep --scenario all --artifact-dir .tmp/editorial_reviewer_operational_closure/flow --out .tmp/editorial_reviewer_operational_closure/reviewer_flow_acceptance.json
git diff --check
```

The acceptance packet must include one real public timeline packet showing a
bound picture fingerprint and a reuse plan for unchanged picture, plus the
negative source-binding and stale-index cases. Run the full suite exactly once
after all focused checks pass; do not edit unrelated failures.

## Stop-loss

Stop at the last green state if the same failure class recurs after one LOCAL
correction, if the public picture probe is absent, if any forbidden file must
change, if version-1 behavior would break, or if a new adapter/tool/stage is
needed. Do not create hand-written PASS artifacts or bypass the public route.

## Report

Write `.tmp/editorial_reviewer_operational_closure/final/worker_report.md`
with pre/post status, exact files, RED/GREEN exits, focused/full-suite result,
dispatch output, real-packet reuse evidence, hashes, deviations, skips,
unknowns, and confirmation that all nine S9 dirty files are byte-for-byte
unchanged. Keep `human_creative_approval=false` and
`final_delivery_claimed=false`.

## Worker Stop Report — 2026-07-19

Status: `STRUCTURAL_PICTURE_FINGERPRINT_PUBLIC_GAP`.

The worker wrote and ran RED coverage for source-binding mismatch, invalid or
unreasoned fingerprints, stale wall-index reuse, and combined audio+subtitle
change. All four probes failed against the current implementation as expected.
The RED tests were then reverted to preserve the last green implementation
state; command evidence is retained at
`.tmp/editorial_reviewer_operational_closure/red/red_evidence.json`.

The public timeline entry `tools/timeline_review_packet.py` delegates to the
existing core builder and exposes no picture fingerprint input. The public
`video_tools.py probe` surface returns codec/size/rate/duration metadata only;
`video_pipeline.py::probe_video` likewise returns pixel format, color range,
rate, size, and duration only. The core packet therefore still emits
`picture_stream_fingerprint` as explicitly unbound. No existing public probe
can provide the required deterministic picture elementary-stream fingerprint.

Per stop-loss, no validator, planner, skill, capability, adapter, ffmpeg
command, packet, or full-suite implementation was applied after this finding.
The required real bound-picture packet and reuse proof are `UNKNOWN`/blocked.
