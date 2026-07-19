# Work Order: V Pipeline Editorial Reviewer real-use closure

Date: 2026-07-19
Owner profile: bounded implementation worker (LUNA high/xhigh or equivalent)
Starting HEAD: `a2c0f9f553aa5b429df94eab02f610920b8b39cb`
Target state: `WAITING_INTEGRATOR_EDITORIAL_REVIEWER_REAL_USE_CLOSURE_REVIEW`

## Goal

Close the gap found by the first real Editorial Reviewer run: the reviewer can
understand the film and produce useful findings, but the packet omits active
decision locks and its native findings template is not a valid
`editorial_review` v2 artifact.

After this work, one fresh reviewer context must be able to consume a generated
packet, understand what is locked, discover the write contract without reading
Python source, record chapter progression, write a valid review artifact, and
route or explicitly decline a route without inventing a tool or Stage.

This is not a new reviewer, Stage, orchestrator, renderer, or LLM runtime.

## Read first

Read `AGENTS.md`, `RUNBOOK.md`, `HANDOFF_CURRENT.md`, the three prior Editorial
Reviewer work orders and reports, this work order, and the current packet,
registry, reviewer skill, Verify skill, CLI, and focused tests. Use
codebase-memory-mcp first for discovery and impact tracing.

Read-only real-shape references:

- `.tmp/canon67_editorial_reconstruction_v2/stage5_layered_compile_v1/continuation_v2_stage4_micro_role/stage9_brownfield_revision_v2/capcut_finishing_handoff.json`
- `.tmp/canon67_uniform_timeline_review_forward_v1/timeline_review_packet.json`
- `.tmp/canon67_uniform_timeline_review_forward_v1/timeline_reviewer_findings.template.json`

## Owner zone

May edit only:

- `video_pipeline_core/timeline_review_packet.py`
- `video_pipeline_core/reviewer_registry.py`
- `tools/timeline_review_packet.py`
- `skills/editorial-reviewer.md`
- `skills/verify.md`
- `docs/artifact-reviewer-map.md`
- `docs/interface-contracts/pipeline-product-artifact-dictionary.json`
- `tests/test_timeline_review_packet.py`
- `tests/test_reviewer_registry.py`
- `tests/test_reviewer_flow_acceptance.py`
- `.tmp/editorial_reviewer_real_use_closure/**`
- this work order append-only for the final stop report

Forbidden: all nine S9 dirty files, `RUNBOOK.md`, `HANDOFF_CURRENT.md`,
`video_tools.py`, source media, Canon 67 accepted artifacts, production
render/audio/subtitle/effect code, git history, and any new adapter/tool/Stage.

## Design decisions

### 1. Decision locks are bound input, not inferred state

Extend the existing timeline packet builder/CLI with one optional JSON context
input. It may bind an existing artifact containing `locked_truth` and optional
`finishing_contract`/`audio_policy`. The packet copies only those declared
blocks plus a source reference with exact path, artifact role, and SHA-256.

Do not make the packet scrape Stage 9 directories or import a CapCut-specific
schema. Missing context is explicit `unbound`, not guessed.

Full-context review reads locks before proposing fixes. Cold-start review first
records audience-visible findings without using the locks, then classifies each
finding against the locks before final output. Every finding records
`requires_reopen: true|false`; a lock conflict is not deleted or silently
downgraded.

### 2. One generated write contract, no second truth source

Generate `reviewer_write_contract.json` from the live reviewer registry and
live capability catalog at packet-build time. It includes allowed enums,
registered capability IDs needed for routing, authority limits, validator
capability ID, and one minimal valid example. The packet binds its path and
SHA-256.

It must not duplicate enums as hand-maintained constants outside the existing
registry. If the live registry/catalog is unavailable, packet creation fails
closed.

### 3. Replace the invalid native output template

Stop generating the invalid `timeline_reviewer_findings.template.json` as the
canonical output. Generate `editorial_review.template.json` whose payload is a
valid `editorial_review` v2 artifact and passes the public reviewer validator
before any finding is added. Update current references and tests. Do not keep
two active templates that can drift.

Historical `.tmp` artifacts and archived work orders remain untouched.

### 4. Preserve routing discipline without suppressing findings

`proposed_fix` remains the normal path. For a finding with no existing route,
the same field uses `route=no_existing_route`, `capability_id=null`, and a
required non-empty `no_route_reason`. In that case do not require fake rerun
gates or a fabricated expected implementation. Exactly one primary resolution
record remains required; at most one fallback remains allowed.

### 5. Progression is explicit evidence

An optional `chapter_candidates[]` block on `editorial_review` v2 is validated
when present. Each chapter candidate requires a stable ID, bounded timeline
window, `opens_with`, `ends_with`, `information_gain`, and evidence references.
Identical opening/ending descriptions are allowed only when accompanied by an
explicit no-progression observation/finding; do not auto-FAIL taste.

### 6. Wall inspection uses one fresh reviewer context

Add an operating rule to `skills/editorial-reviewer.md`: inspect timeline walls
in a disposable/fresh subagent context and return only the immutable review
artifact to the parent/orchestrator. This is one reviewer identity, not a
multi-reviewer consensus system. The parent does not rewrite findings; it only
validates and routes them.

### 7. Fingerprint language stays honest

The current soundtrack probe JSON hash is an artifact fingerprint, not an
audio elementary-stream fingerprint. Store it under an artifact-accurate field.
When no real audio-stream fingerprint exists, keep
`audio_stream_fingerprint` explicitly unbound and fail closed on reuse. Keep
the picture fingerprint unknown/fail-closed boundary unchanged.

## Red-first evidence

Before implementation, prove all of these fail:

1. the generated native findings template fails the public validator;
2. a packet cannot bind/read back real-shape `locked_truth`;
3. a reviewer must inspect Python source to discover enums/capability IDs;
4. `no_existing_route` cannot be represented without fake fix fields;
5. progression fields are absent/unvalidated;
6. soundtrack probe artifact hash is mislabeled as a stream fingerprint.

## Acceptance

Run the focused reviewer/timeline/skill suites, capability ownership audit,
deep reviewer-flow acceptance, and `git diff --check`.

Create a fresh immutable acceptance root:

`.tmp/editorial_reviewer_real_use_closure/roundtrip_v1/`

Using a small existing media fixture and a real-shape lock-context fixture,
prove this complete public round trip:

```text
timeline packet build
-> locked truth + context hash read-back
-> reviewer_write_contract read-back
-> editorial_review.template.json
-> add strengths, one progression chapter, one routed finding, and one
   no_existing_route finding
-> public reviewer-policy validator exit 0
-> locked conflict marked requires_reopen=true
-> unknown picture/audio stream fingerprints remain fail-closed for reuse
```

The acceptance packet must contain paths/hashes and command exits. After all
focused and round-trip checks pass, run the full suite exactly once. Do not
modify unrelated failures.

## Stop-loss

Stop at the last green state after one LOCAL correction if the same failure
class recurs, if any forbidden file must change, if a second active template or
hand-maintained enum source would be required, if version-1 review compatibility
breaks, or if a new adapter/tool/Stage is needed. Do not hand-write PASS output
or bypass the public validator.

## Report

Write `.tmp/editorial_reviewer_real_use_closure/final/worker_report.md` with
pre/post status, exact changed files, RED/GREEN commands and exits, round-trip
artifact paths/hashes, focused/full-suite results, deviations, skips, unknowns,
and confirmation that S9, RUNBOOK, HANDOFF, and `video_tools.py` are unchanged.
Keep `human_creative_approval=false` and `final_delivery_claimed=false`.

## Worker Stop Report — 2026-07-19

Status: `PASS` / `WAITING_INTEGRATOR_EDITORIAL_REVIEWER_REAL_USE_CLOSURE_REVIEW`

The requested real Reviewer round-trip is complete. The immutable acceptance
record is `.tmp/editorial_reviewer_real_use_closure/roundtrip_v1/acceptance_packet.json`
with status `PASS`: real-shape `locked_truth` and context SHA-256 read-back,
live-generated `reviewer_write_contract.json`, public-valid
`editorial_review.template.json`, progression chapter, routed finding,
`no_existing_route` finding with `capability_id=null` and `no_route_reason`,
public validator exit `0`, and locked conflict `requires_reopen=true`.

Validation evidence:

- RED evidence saved at `.tmp/editorial_reviewer_real_use_closure/red/red_evidence.json`;
  the pre-implementation probe exited `1`.
- Focused reviewer/timeline/skill/boundary suite: exit `0`, `65` tests.
- Skill ownership audit: exit `0`, `114/114` owned, no unowned tools.
- Registry audit: exit `0`, findings `[]`.
- Deep reviewer-flow acceptance: exit `0`, `ok=true`, errors `[]`.
- UTF-8/JSON checks and `git diff --check`: exit `0`.
- Full suite ran exactly once after all prior checks: exit `0`, `2923` tests,
  `1` skip.

Final report with exact changed files, commands/exits, artifact SHA-256 values,
deviations, unknowns, and protected-file verification:
`.tmp/editorial_reviewer_real_use_closure/final/worker_report.md`.

Protected files were preserved: all nine S9 SHA-256 values match the preceding
operational-closure worker report, and `RUNBOOK.md`, `HANDOFF_CURRENT.md`, and
`video_tools.py` each returned exit `0` from `git diff --quiet`. No human
creative approval or final delivery claim was made.
