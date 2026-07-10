# Decision: Evidence-Carrying Incremental Editing Loops

Date: 2026-07-10
Status: accepted
Scope: Hermes editing front door, loop context, timeline, evidence lineage
Superpowers phase: brainstorm

## SPEC

Requirement:

Hermes needs an editing front door where an agent can make creative editing
decisions, the owner remains an approval gate, and each LOOP completes its local
question while carrying confirmed results, evidence, findings, and invalidation
into later LOOPs.

### Size judgment

The answer depends on scope. This section began as the original sizing proposal;
the accepted direction was later reduced by Fable review and f1 evidence:

- **Complete L0–L5 product:** a large, multi-stage product program.
- **Accepted P0:** small and Skill-first, using existing artifacts and
  capabilities; no persistent loop driver or new context engine.
- **Complete L0–L5 product:** still a multi-stage product program, constructed
  one first-of-kind pattern at a time.

The main risk is shared-contract correctness and cross-layer invalidation, not
raw code volume. Implementing all six LOOPs in one task would make it a large
project and recreate the orchestration problem.

Why:

The TERRA 0–44 second slice proved that existing composition/render capability
can create a technically valid candidate. The LOOP pilot produced a visibly
better candidate by making evidence-backed creative decisions before rendering.

Pilot ground truth is **agent-generated, human-approved**:

- Fable proposed the script, selected and arranged the material, assembled the
  candidate, and interpreted the result.
- The owner approved or requested revision but did not replace the agent's
  creative choices.

The missing capability is therefore not another route. It is **horizontal
semantic continuity** across existing APIs:

- source intent and story function remain visible across L0–L5;
- an agent proposal retains the evidence that supported it;
- an owner verdict binds to the exact proposal reviewed;
- the applied delta records what it supersedes and which layers become dirty;
- the next LOOP receives relevant portable context instead of every run JSON.

Direction:

Use **one editorial Skill plus existing V Pipeline capabilities**. Add a thin
deterministic helper only after an observed repeated manual transformation or
failure proves it is needed:

| Component | Owns | Must not own |
|---|---|---|
| `editing-loop-director` Skill | interpretation, taste, story, continuity, evidence-backed proposals, owner dialogue | durable state, hidden writes, delivery approval |
| Executing agent | resolve carried context, propose, call existing capabilities, apply the owner-approved bounded delta, collect fresh evidence | hidden durable state, autonomous multi-round execution, owner override |
| Triggered helper/adapter | one repeated deterministic transformation proven by a pilot | workflow, creative judgment, route decisions |
| Existing branches | material/effect/audio/text/render/verify capabilities | global orchestration |
| Owner | approve/revise/block and final creative approval | routine execution |

The current route orchestrator stays frozen and is not the new editing front
door. No persistent `loop_driver` is part of accepted P0; “driver” describes
the agent session rather than a new runtime product surface.

### Incremental LOOP definition

A LOOP is a **portable local closure**, not a self-contained island:

```text
carried context + relevant evidence
  -> agent proposal
  -> owner verdict
  -> apply approved delta
  -> cheap preflight
  -> segment preview / render
  -> verify
  -> confirmed delta + evidence + findings + dirty scope carried forward
```

The next LOOP does not restart project understanding and does not discard
upstream intent or decision history.

### Layer model

Four kinds of layering must be distinct.

#### 1. Global context — carried by all LOOPs

- immutable/versioned source intent;
- canon and story blueprint references;
- north star, emotional arc, and invariants;
- approved script reference where text is production truth.

Later summaries may compress this context but may not rewrite its source.

#### 2. Workflow LOOPs

| LOOP | Primary responsibility | Output |
|---|---|---|
| L0 Material immersion | perception, labels, selects, uncertainty | evidence/material pool |
| L1 Picture | story, shot choice, order, duration, rhythm | picture delta and lock |
| L2 Effects | transitions, overlays, graphic treatment | effects delta |
| L3 Audio | music, production audio, SFX, mix | audio delta |
| L4 Text | titles, subtitles, textual correctness | text delta |
| L5 Review | objective/perception/taste review | findings and verdicts |

L0 is an evidence/candidate layer, not a render track. L5 emits findings and
verdicts; it must not secretly edit the timeline.

#### 3. Segment timeline layers

```jsonc
{
  "segment_id": "seg_012",
  "story_beat_refs": ["beat_skill_growth"],
  "picture": {},
  "effects": [],
  "audio": {},
  "text": [],
  "layer_state": {
    "picture": "locked",
    "effects": "dirty",
    "audio": "review",
    "text": "dirty"
  }
}
```

#### 4. Evidence and decision history — append-only

- proposal, rationale, and declared blind spots;
- evidence references;
- owner verdict;
- applied delta and verification;
- findings, waivers, and `supersedes` relationships.

Current timeline state is render truth. History must not be overwritten to make
the newest result appear inevitable.

### Ownership and invalidation

Every LOOP declares:

```text
owns_layers
reads_layers
required_context_refs
may_dirty_layers
verification_gates
output_delta
carry_forward
```

Normal construction moves L0 -> L1 -> L2 -> L3 -> L4 -> L5, but dependency is
not strictly one-way:

- picture replacement dirties effects/text and places audio under review;
- music or beat-structure change can reopen picture beat alignment and effect
  synchronization;
- text length/placement can reopen effect/composition collision review;
- new L0 material does not dirty the timeline until selected;
- L5 routes a finding to the affected segment/layer instead of restarting the
  whole route.

### Portable `loop_context`（deferred hardening design）

The following envelope is preserved as a hardening design, not an implemented
P0 artifact. P0 reconstructs context from the approved script, selects manifest,
run provenance, and candidate run directory:

```jsonc
{
  "run_id": "...",
  "revision": 3,
  "source_intent": {
    "ref": "...",
    "sha256": "...",
    "north_star": "...",
    "invariant_refs": []
  },
  "focus": {
    "loop": "L1",
    "segment_ids": ["seg_012"],
    "layer": "picture"
  },
  "agent_proposal": {
    "proposal_id": "p_0012",
    "proposal_by": "agent",
    "rationale": "...",
    "evidence_refs": []
  },
  "owner_verdict": {
    "verdict": "approve",
    "verdict_by": "owner",
    "owner_modified_decision": false,
    "proposal_hash": "..."
  },
  "applied_delta_ref": "...",
  "dirty_layers": [],
  "open_findings": [],
  "verification_refs": [],
  "supersedes": []
}
```

One user prompt may invoke the Skill. The prompt is an entry point, not the
source of truth; the Skill resolves relevant context and expands evidence only
when needed.

### Portable evidence reference

Absolute local paths alone are insufficient. Evidence should include:

```jsonc
{
  "evidence_id": "ev_0042",
  "artifact_role": "montage_wall",
  "uri": "run-relative/path/to/artifact",
  "sha256": "...",
  "anchor": {
    "time_range": [27.2, 29.0],
    "frame": null,
    "cell_id": "cell_0031",
    "check_id": null
  },
  "produced_by": "perception-field",
  "revision": 3
}
```

Full evidence remains in the original artifact. The contract carries minimal
summary plus stable IDs, hashes, and anchors for progressive disclosure.

### Verification placement

Before render, run cheap deterministic checks:

- approved text equality and overlay non-overlap;
- asset existence and orientation;
- diversity/repetition constraints;
- planned edit boundaries and duration;
- provenance and evidence resolution.

After render, verify:

- actual video/audio streams and duration;
- visible effect/text lifecycle;
- black frames, beat alignment, subtitle synchronization;
- perception review and owner taste gate.

Non-goals:

- no new route runner, `next_action` state machine, or duplicate registry;
- no autonomous owner-gate override;
- no full-context copy in every prompt;
- no full L0–L5 implementation in P0;
- no removal of the current route system in P0;
- no measured-cost claim from qualitative token impressions.

## DO

Files / modules:

Accepted anchors are:

- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
- `docs/pilots/2026-07-10-loop-pilot-evidence-for-sol.md`
- `docs/pilots/2026-07-10-editing-loop-f1-forward-test-evidence.md`
- `docs/pilots/pilot-driver-v1-usage-log.py`
- `video_pipeline_core/edit_decision_plan.py`
- `video_pipeline_core/material_lineage.py`
- `video_pipeline_core/artifact_manifest.py`
- `docs/branch-contract-registry.json`
- `skills/**`

Function-level plan:

Construction sequence after owner acceptance:

1. Make the Product Spec canonical and align Skill maturity with actual evidence.
2. Preserve the f1 PASS as a compact durable evidence summary.
3. Run L5 first-of-kind on Canon 67 candidate_v2 by composing existing review
   capabilities; use an experimental packet and stop at the owner taste gate.
4. Let the first real L5 finding select the next bounded L2/L3/L4 certification.
5. Add a helper or contract only when the Product Spec's observable hardening
   trigger occurs.

Data / interface changes:

- no new production schema in the documentation-convergence step;
- carry the six minimum decision fields in existing provenance/evidence files;
- use stable IDs plus path/anchor/producer evidence refs;
- preserve proposal hashes, journal, context envelope, dirty matrix, and
  evidence hashes as triggered hardening designs rather than P0 requirements.

Migration / compatibility:

- keep route runners and their green tests, but stop extending them for editing;
- adapt existing artifacts through readers before changing all producers;
- reuse material lineage, artifact manifest, edit decision plan, and branch
  ownership contracts where their semantics fit;
- report missing new fields in legacy runs as legacy/unknown, never invent them.

## VERIFY

Pre-checks:

- TERRA closure restores focused and full-suite baselines;
- route and LOOP v1 0–44 second candidates remain inspectable;
- accepted script, provenance, beat, rendered QA, and perception evidence resolve.

Tests:

Each first-of-kind implementation plan must cover:

- refusal to apply without owner verdict;
- stable-ID semantic diff and unrelated-field preservation;
- fresh layer-focused verification and evidence read-back;
- six decision fields and three telemetry values carried forward;
- absence of a new route runner, registry, hidden state, or threshold relaxation.

Manual checks:

Finding f1 was completed as the first acceptance:

1. A fresh TERRA session independently proposed one stable-ID replacement.
2. The owner approved Phase B and later marked f1 resolved after dynamic review.
3. Exactly one picture source changed; timing, audio, text, effects, settings,
   transitions, final landing, and candidate_v1 hashes remained unchanged.
4. Beat alignment, rendered QA, perception coverage, encoding, and provenance
   read-back passed on fresh artifacts.
5. Scope remained f1/L1 only; creative and delivery flags stayed false.

Record available cost telemetry: agent/owner iterations, model usage, tool calls,
render count/duration, target seconds rerendered, and proposal-to-verdict time.
Unavailable fields remain `unknown`.

Regression risks:

- Skill becomes a hidden state machine/source of truth;
- a helper gains product judgment and recreates a route orchestrator;
- timeline and decision journal conflict;
- carried context grows back into all-history overload;
- evidence works only in one absolute Windows directory;
- one-way invalidation misses audio/picture/effect interaction;
- local changes still trigger full-film recomposition;
- owner approval is not bound to the exact agent proposal.

## Decision Notes

Accepted because:

The owner accepted the Skill-first certification-ladder design after Fable's
review and the independent f1 forward-test. The test proved that an agent can
carry the story spine and evidence through a bounded L1 revision without a new
driver, schema, or route. Existing V Pipeline capabilities provide the execution
layer; LOOP provides the evidence-carrying control layer.

Tradeoffs:

- four-source derived context avoids duplicate truth but requires disciplined
  provenance and stable IDs;
- delaying hashes/journal/dirty propagation keeps P0 light but makes their
  observable triggers important;
- first-of-kind certification costs more once per pattern but prevents every
  ordinary creative revision from paying a full blind-test tax;
- retaining the route system temporarily leaves two front doors.

Open questions:

- Which real finding the L5 first-of-kind will surface first; that evidence will
  select the next L2/L3/L4 certification.
- Whether inconsistent existing finding shapes actually require a normalizer;
  no adapter is authorized until the L5 pilot demonstrates the gap.

## Git / Retrieval

Related files:

- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
- `docs/pilots/2026-07-10-loop-pilot-evidence-for-sol.md`
- `docs/pilots/2026-07-10-opening-0044-script-v1.md`
- `docs/pilots/pilot-driver-v1-usage-log.py`
- `video_pipeline_core/edit_decision_plan.py`
- `video_pipeline_core/material_lineage.py`
- `video_pipeline_core/artifact_manifest.py`
- `video_pipeline_core/route_orchestrator.py`

Related commits:

- `fdbe086f`, `2545b07d`, `c6f1a317`, `a7d0bb33`

Graphify anchors:

- `video_pipeline_core.material_lineage.link_lineage`
- `video_pipeline_core.artifact_manifest.register_handoff`
- `video_pipeline_core.edit_decision_plan.compile_edit_decision_plan`
- `video_pipeline_core.route_orchestrator.write_next_task`

Search tags:

`decision-log`, `spec-do-verify`, `editing-loop`, `evidence-carrying`,
`agent-generated-human-approved`, `loop-context`, `dirty-propagation`,
`editing-loop-director`, `loop-driver`, `canon-67-opening`
