# Decision: Upstream editorial discovery boundary

Date: 2026-07-15
Status: accepted (architecture; implementation pending)
Scope: material evidence, Stage 2/5 editorial discovery, global editorial state
Superpowers phase: review

## SPEC

Requirement:

Make the source-material ceiling, owner decisions, abandoned story intent, and
high-impact editorial comparisons machine-readable before long-form rendering.

Why:

Canon67 currently uses material that was pre-curated by another editor and has
no capture-intent notes. Missing establishing shots, alternate takes, B-roll,
and semantic annotations may therefore be input limitations rather than Hermes
capability failures. Deterministic layers received many cheap Agent iterations,
while story/taste layers received little signal until the recent paper-edit A/B
comparison. Mature effects and music also embody external, accumulated taste;
rebuilding them locally combines engineering risk with taste risk.

Direction:

- Record material origin and annotation state as separate evidence dimensions.
- Carry accepted global editorial state as immutable, hash-bound revisions.
- Use paper-edit A/B comparison by default for high-impact, ambiguous Stage 2
  or Stage 5 decisions; do not require A/B for factual or low-impact choices.
- Record material-deferred and intentionally retired story intents explicitly.
- Build canonical intent/truth capabilities; buy or integrate taste-crystallized
  libraries first, with bounded custom work only when the project is unique.

Non-goals:

- Do not add another orchestrator, live state engine, registry, or delivery gate.
- Do not force two rendered candidates for every decision; A/B should remain a
  cheap paper-edit/storyboard comparison unless render evidence is necessary.
- Do not claim that better source material proves better pipeline capability.
- Do not retrofit all existing Capability cards before a real proposal uses the
  new classification.

## DO

Files / modules:

- `docs/hermes-v-pipeline-honest-capability-map.md`: publish the causal model and
  current architecture boundary.
- Future bounded implementation: Material Map/evidence schema, global editorial
  state schema/validator, Stage 2/5 decision packet, campaign status, candidate
  backend provenance, and run metrics.
- `skills/capcut-assisted-finishing.md`: retain CapCut as a bounded external
  finishing provider after Hermes truth is reviewed.

Function-level plan:

1. Add orthogonal source fields instead of a closed combined enum:
   - `material_origin`: `raw | curated | generated | reference`
   - `annotation_state`: `intent_annotated | metadata_only | unannotated`
   `raw_annotated`, `raw_unannotated`, and `curated_unannotated` remain useful
   derived evidence classes.
2. Define the optional minimum capture-intent note: event family, people/roster,
   activity, shot scale, capture intent, intended use, rights/consent status,
   and one-line operator note.
3. Version `global_editorial_state` immutably. A worker pins
   `base_state_sha256`, emits a delta, and the orchestrator creates the next
   state only after accepted review. Receipt binds old state, delta, and new
   state hashes.
4. Add `decision_mode: single | ab_comparison | delegated`. Default to
   `ab_comparison` when a structural choice is high-impact, ambiguous, and
   materially different alternatives exist. Record the trigger, option refs,
   owner verdict, and rejected/sacrificed story lines.
5. Add `deferred_due_to_material` with a reason:
   `not_found | not_present | present_unusable | excluded_by_policy`. Owner must
   distinguish an actual material ceiling from a retrieval failure.
6. Store intentionally abandoned directions under `retired_story_intents` with
   `reconsider_if`, not as unresolved `open_story_risks`.
7. For new capability proposals, record:
   - `capability_nature`: `intent_bearing | taste_crystallized | hybrid`
   - `sourcing_strategy`: `build | buy_or_integrate | hybrid`
   Avoid the name `provenance_class`, which is already needed for material and
   candidate lineage.
8. Keep operations telemetry separate in `run_metrics.json`: wall-clock,
   render count/time, Agent turns, tool calls, Human review minutes, and blast
   radius. Record tokens only when the harness exposes them reliably.

Data / interface changes:

- Evidence and maturity reports must state source provenance so an input ceiling
  is not silently scored as a system ceiling.
- Transfer tests should compare provenance strata. Prefer a matched or at least
  explicitly stratified comparison between `curated_unannotated` and
  `raw + intent_annotated`; merely choosing a different project does not isolate
  the variable.
- Stage 5 segment review checks decision completeness, not creative quality:
  unique factual purpose, story contribution, entry/exit state, family reuse
  reason, coverage status, review caption, and open questions.

Migration / compatibility:

Existing Canon67 artifacts remain valid historical evidence and are classified
as `curated + unannotated` where applicable. New fields begin as optional and
become fail-closed only after one real segment pilot, one schema correction
window, and a frozen v1 contract. Existing Capability cards are not mass-edited.

## VERIFY

Pre-checks:

- Current operational authority remains RUNBOOK → current handoff/run state.
- Canon67 source policy and owner all-or-none teacher decision remain unchanged.
- No production schema, Stage cursor, BUILD flag, or delivery flag changes in
  this documentation pass.

Tests:

- Documentation UTF-8 and anchor checks.
- Existing pipeline boundary tests and `git diff --check`.
- Future implementation tests: material-provenance validation, stale
  `base_state_sha256` rejection, immutable state receipt binding, A/B decision
  packet validation, and material-defer reason validation.

Manual checks:

- Another AI can distinguish source limitations from pipeline limitations.
- A segment worker can know global material-family/coverage state without reading
  the full conversation history.
- A rejected A/B story direction cannot silently return in a later loop.
- A generic effect/music request routes to mature external assets before a new
  bespoke renderer is proposed.

Regression risks:

- Mandatory A/B on small decisions would double process cost and produce fake
  alternatives; keep the trigger high-impact and paper-edit-first.
- A stale mutable editorial-state document would duplicate the handoff problem;
  use immutable revisions and content hashes.
- A detector may confuse structural candidates with objective defects; retain
  the `objective | structural_candidate | taste` finding classes.
- `deferred_due_to_material` may hide retrieval failure unless owner-confirmed.
- Better-source transfer tests can overstate pipeline improvement unless source
  provenance is explicit.

## Decision Notes

Accepted because:

It explains why deterministic governance matured faster than creative quality
and adds upstream signal without building a new engine. It also formalizes the
successful Canon67 paper-edit A/B discovery and the CapCut build/buy boundary.

Tradeoffs:

The route adds a few fields and one immutable state chain. It deliberately keeps
Human judgment at major structural and taste decisions, and it does not promise
that annotated material alone produces a good film.

Open questions:

- Which two Canon67 segments should calibrate the v0 → v1 editorial-state schema?
- What minimum evidence makes two A/B options materially distinct rather than
  cosmetic variants?
- Which future raw annotated dataset can serve as a matched provenance transfer
  test?

## Git / Retrieval

Related files:

- `docs/hermes-v-pipeline-honest-capability-map.md`
- `docs/decisions/2026-07-15-canon67-outcome-report-soul-integration.md`
- `docs/decisions/2026-07-15-capcut-assisted-finishing-forward-test.md`
- `skills/editing-loop-director.md`
- `skills/capcut-assisted-finishing.md`

Related commits:

- None yet.

Graphify anchors:

material provenance, curated unannotated, editorial state, paper-edit A/B,
deferred story intent, build versus buy, taste-crystallized capability

Search tags:

decision-log, spec-do-verify, material-provenance, editorial-state,
ab-comparison, build-buy, capcut-finishing, longform

