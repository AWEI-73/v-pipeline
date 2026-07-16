# Work Order: Comparative Semantic Reviewer MVP

Date: 2026-07-15
Status: IMPLEMENTED — Phase A and binding closure PASS; maturity remains experimental
Recommended worker: Luna, high/maximum reasoning
Estimated size: medium-small, bounded workflow/tool work
Integrator: SOL / Codex

## 1. Goal

Add the smallest useful semantic-review layer to Hermes without creating a new
orchestrator or pretending that an LLM can certify creative quality.

The MVP must let a fresh reviewer compare two neutralized editorial variants
against a narrow rubric, cite concrete evidence, and return adversarial
`flag_only` findings for a Human owner. It must also be able to prepare, but not
apply, a Human-approved delta for the existing immutable
`global_editorial_state` chain.

This work order builds and tests the bounded mechanism. It does not approve a
Canon 67 variant, mutate canonical editorial state, render a film, or claim
delivery.

## 2. Authority model already decided

These are product decisions, not questions for the worker:

1. Mechanical Verify owns objective facts such as hashes, durations, bindings,
   decode health, and contract equality.
2. The semantic reviewer owns no PASS/FAIL authority. It may only emit
   `structural_candidate` and `taste` flags.
3. The Human owner alone decides which option is preferred, whether neither is
   acceptable, and whether canonical state may change.
4. The reviewer compares A/B variants; it does not assign a universal soul,
   taste, or quality score.
5. The reviewer is adversarial: find where a variant weakens or violates the
   approved proposition. Do not reward polish merely because it looks smooth.
6. Questions are narrow and rubric-specific. Every non-UNKNOWN observation
   requires a stable ID, time range, review cell, or source reference.
7. The maker and semantic reviewer must be separate contexts. The blind
   reviewer must not receive maker rationale, previous verdicts, backend name,
   chronology, or the owner-only slot key.
8. Stage owns lifecycle. Editing Loop supplies the method. Existing
   `global_editorial_state` remains canonical state; this MVP is not a second
   state engine.
9. No worker may set `human_creative_approval=true` or
   `final_delivery_claimed=true`.

## 3. Scope

### 3.1 New production surfaces

- `video_pipeline_core/editorial_comparison.py`
- `tools/editorial_comparison.py`
- `tests/test_editorial_comparison.py`

### 3.2 Bounded existing-file edits

- `skills/editing-loop-director.md`
  - add one concise comparative semantic review subsection;
  - describe the blind A/B method, authority boundary, evidence rules, and
    Human handoff;
  - add or extend the existing tool-ownership contract so
    `tools/editorial_comparison.py` is owned by this Skill;
  - preserve the existing capability-consumer block and Stage/L0-L5 mapping.
- Skill/tool contract tests only if the real ownership audit requires a narrow
  fixture update.

### 3.3 Experimental artifacts

All first-of-kind artifacts remain below:

`.tmp/comparative_semantic_review_mvp/**`

Do not add them to a canonical artifact dictionary in this work order.

## 4. Forbidden zone

Do not modify:

- `video_pipeline_core/global_editorial_state.py`;
- `tools/global_editorial_state.py`;
- Material Map, retrieval/ranking, picture-plan, segment-contract, ASR,
  subtitle, audio, render, Remotion, CapCut, delivery, or Verify logic;
- branch/route registries, `pipeline_home.py`, reviewer registry, dashboard,
  next-action vocabulary, or accountability engine;
- accepted Canon 67 state revisions, receipts, L1 plans, owner verdicts, media,
  or historical evidence;
- `HANDOFF_CURRENT.md` or active campaign pointers during Phase A;
- unrelated dirty/untracked files.

Do not create:

- a new route runner, orchestrator, workflow engine, state daemon, event bus,
  database, dashboard, or background service;
- a second director Skill;
- a global creative score, automatic winner, creative approval gate, or
  automatic state mutation;
- a new Capability Card unless an existing audit makes ownership impossible
  through the bounded Skill tool contract. If that occurs, classify it as
  STRUCTURAL and stop rather than widening scope.

## 5. Artifact contract

The exact internal Python types are a bounded worker decision. The serialized
shape must preserve these concepts.

### 5.1 Blind packet

`build-packet` writes a new immutable run directory containing:

- `reviewer/comparison_packet.json`
- `reviewer/inputs/slot_1.<ext>`
- `reviewer/inputs/slot_2.<ext>`
- `reviewer/editorial_comparison_flags.template.json`
- `owner/comparison_key.json`
- `owner/owner_verdict.template.json`
- `manifest.json`

The reviewer packet contains:

- `artifact_role=editorial_comparison_packet`
- `schema_version=1`
- `decision_id`
- `decision_mode=ab_comparison`
- `authority=flag_only`
- proposition/thesis text supplied by the caller;
- narrow rubric items with stable IDs;
- permitted evidence references;
- neutral slot paths and their SHA-256 hashes;
- packet payload hash;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

The owner-only key contains the original variant IDs/paths/hashes and their
randomized slot assignment. It must not be referenced by the reviewer packet.

### 5.2 Rubric requirements

Each rubric item asks one bounded question. Suitable question families are:

1. Which slot makes this proposition more concrete, or is the result tied or
   UNKNOWN?
2. At what coordinate does either slot dilute or contradict the proposition?
3. Which slot adds new information rather than repeating an already established
   event family?
4. Does the ending fulfill a promise established earlier in the supplied
   evidence?

Do not ask broad questions such as “Does it have soul?” or “How good is this
film?”. Do not use numeric creative scores.

### 5.3 Reviewer flags

`validate-flags` accepts a reviewer result only when:

- `artifact_role=editorial_comparison_flags`;
- it is bound to the exact packet file SHA-256;
- `authority=flag_only`;
- every rubric answer is one of
  `slot_1 | slot_2 | tie | unknown`;
- every finding class is `structural_candidate | taste`;
- every non-UNKNOWN claim cites permitted coordinates/evidence;
- there is no global winner field;
- owner verdict remains absent or `PENDING`;
- both approval flags remain false;
- no field or value claims PASS, FAIL, approved, rejected, delivery, canonical
  promotion, or state mutation.

The validator must reject semantic attempts to smuggle authority through
alternative field names, not only one exact forbidden key.

### 5.4 Human verdict and proposed state delta

`build-owner-delta` may run only from:

- the current pinned global editorial state path/hash;
- the owner-only comparison key;
- validated reviewer flags;
- an explicit Human verdict file.

The Human verdict supports:

- `select_variant` with one original variant ID;
- `revise_both`;
- `tie_keep_current`.

It must include `reviewer_role=human_owner`, rationale, and explicit references
to the reviewed packet/flags. The helper writes only a proposed delta artifact.
It must not call `global_editorial_state apply-delta`, modify a revision, update
campaign pointers, or set either approval flag.

The proposed delta records the decision under:

`operational_state.comparative_decisions.<decision_id>`

and includes packet, key, flags, verdict, variant, and base-state hashes. The
existing `tools/global_editorial_state.py apply-delta` remains the sole state
application path after separate Human/integrator authorization.

## 6. CLI behavior

`tools/editorial_comparison.py` is a thin adapter over the core module and must
provide equivalent commands:

### `build-packet`

Inputs:

- decision ID;
- proposition/rubric JSON;
- exactly two variant IDs/files;
- output directory;
- optional deterministic seed for tests.

Behavior:

- require regular readable input files;
- hash the original inputs;
- randomize and neutralize them as `slot_1` and `slot_2`;
- materialize reviewer inputs without mutating the originals;
- keep original IDs and paths only in the owner key;
- fail if the output path already contains artifacts;
- emit stable JSON output and machine-readable error codes.

For this MVP, inputs are bounded review artifacts such as JSON, Markdown,
images, contact sheets, or short review-only MP4 files. Do not build a renderer.

### `validate-flags`

Validate the flag-only authority, packet binding, allowed classifications,
evidence references, answer vocabulary, and false approval flags.

### `build-owner-delta`

Validate an explicit Human verdict and write only a proposed state delta. Never
apply it.

Required error codes include at least:

- `comparison_requires_exactly_two_variants`
- `comparison_input_missing`
- `comparison_output_exists`
- `comparison_packet_hash_mismatch`
- `comparison_blindness_leak`
- `comparison_invalid_authority`
- `comparison_forbidden_verdict`
- `comparison_invalid_finding_class`
- `comparison_evidence_required`
- `comparison_invalid_answer`
- `comparison_owner_key_mismatch`
- `comparison_human_verdict_required`
- `comparison_base_state_hash_mismatch`

## 7. Editing Loop Skill update

Add the smallest section that lets another Agent execute this method without
turning the Skill into a specification archive.

The section must say:

1. Trigger only for high-leverage editorial choices: thesis, macro structure,
   segment order, material-family choice, ending, or a major revision.
2. Default to blind A/B. A single proposal requires explicit Human waiver.
3. Maker produces variants; a fresh reviewer receives only neutral slots,
   proposition, rubric, and permitted evidence.
4. Reviewer performs adversarial, narrow, coordinate-backed comparison.
5. Reviewer emits flags only. Human verdict owns the decision.
6. The accepted decision may become a proposed editorial-state delta, but only
   the existing canonical state path may apply it.
7. Do not use this mechanism for every clip or every Loop; excessive comparison
   is process tax.

Keep prose concise and link to this formal work order only as first-of-kind
construction evidence, not as permanent runtime authority.

## 8. Ordered execution

### Phase A — Construction worker

#### Task 0 — Freeze and inspect

- Record branch, HEAD, `git status --short`, and hashes of every bounded
  existing file.
- Read `AGENTS.md`, `RUNBOOK.md`, this entire work order, the relevant
  `editing-loop-director` sections, existing Skill tool-contract conventions,
  and current global-editorial-state validation behavior.
- Locate one real Canon 67 A/B pair suitable for the forward test, preferably
  the bounded seg10 ending v2/v3 review artifacts.
- Do not read an owner verdict to choose the answer. If only labeled evidence
  is available, the builder may use it to construct the packet but must not be
  the Phase B reviewer.

#### Task 1 — RED tests

Write failing tests before implementation for:

- deterministic/random slot assignment and exact two-variant enforcement;
- reviewer packet blindness: no original IDs, paths, chronology, backend,
  maker rationale, key path, or prior verdict;
- immutable output/no overwrite;
- packet/input/key hash binding;
- valid flag-only result;
- rejection of PASS/FAIL/winner/approved/rejected/delivery/state-mutation
  authority, including aliases;
- rejection of missing evidence for non-UNKNOWN claims;
- allowed UNKNOWN/tie behavior;
- Human-verdict requirement and base-state hash binding;
- proposed-delta-only behavior;
- UTF-8 Chinese proposition/rubric round-trip;
- both approval flags fixed false.

Run the new tests and preserve genuine RED evidence.

#### Task 2 — GREEN core and CLI

Implement only enough to pass the contract above. Keep core logic in
`video_pipeline_core/`; keep CLI code thin. Do not add dependencies unless the
standard library and existing repo utilities are objectively insufficient.

#### Task 3 — Skill ownership and guidance

Update `skills/editing-loop-director.md` within scope. Run the real Skill/tool
ownership and boundary audits. If the audit requires a new route, registry,
dashboard, or capability migration, classify STRUCTURAL and stop.

#### Task 4 — Fixture owner-delta proof

Using test fixtures only, prove:

- a valid Human verdict can create a proposed delta;
- missing/non-Human verdicts are rejected;
- wrong base-state, key, packet, or flags hashes are rejected;
- the existing global editorial state is not changed.

Do not apply a real Canon 67 delta.

#### Task 5 — Real blind packet forward setup

Create one real Canon 67 blind packet below:

`.tmp/comparative_semantic_review_mvp/canon67_seg10_ending/**`

Requirements:

- exactly two credible existing review variants;
- neutralized reviewer filenames;
- an approved narrow rubric derived from existing Canon 67 proposition and
  ending intent, not invented production facts;
- original-to-slot mapping only in `owner/comparison_key.json`;
- no previous verdict or maker explanation in reviewer files;
- no render and no canonical-state mutation.

#### Task 6 — Phase A validation and stop

Run:

- new/focused unit tests;
- adjacent Skill/tool ownership and pipeline-boundary tests;
- registry/tool audit if required by existing repo policy;
- UTF-8, JSON, path, and hash read-back;
- `git diff --check`.

Do not run the full suite in Phase A. Do not commit, push, upload, stage, or
update Handoff/campaign pointers.

Write:

`.tmp/comparative_semantic_review_mvp/phase_a/final/worker_report.md`

Legal Phase A success state:

`WAITING_INTEGRATOR_COMPARATIVE_REVIEWER_MVP_PACKET_REVIEW`

### Phase B — Separate fresh-session reviewer

Phase B must be a new session after integrator review of Phase A. It is not part
of the Phase A worker prompt.

The fresh reviewer may read only:

- the reviewer-facing packet;
- the neutralized slot inputs;
- the relevant comparative-review subsection of
  `skills/editing-loop-director.md`;
- explicitly listed evidence paths from the packet.

The reviewer must not read:

- `owner/comparison_key.json`;
- Phase A maker rationale or worker report;
- previous v2/v3 owner/integrator verdicts;
- filenames or reports that reveal chronology/backend;
- canonical state fields that reveal the answer beyond the supplied rubric.

It writes `reviewer/editorial_comparison_flags.json`, runs `validate-flags`, and
stops at:

`WAITING_OWNER_CANON67_COMPARATIVE_REVIEW_VERDICT`

It must not identify a global winner, fill the owner verdict, build/apply a
state delta, render, or claim creative approval/delivery.

### Phase C — Later owner closure

Phase C is intentionally not authorized by this work order. After the Human
verdict, a separate bounded closure may:

1. validate the verdict;
2. build the proposed delta;
3. obtain integrator authorization;
4. apply it through the existing global-editorial-state CLI;
5. run final focused checks and, once only at final closure, the full suite if
   required.

## 9. Stop-loss

- A single LOCAL command/path/quoting mistake may be corrected once.
- If the same failure class recurs, classify STRUCTURAL and stop.
- Stop if success requires any Forbidden Zone edit.
- Stop if reviewer-facing files leak original variant identity, chronology,
  backend, owner key, maker rationale, or prior verdict.
- Stop if any output claims PASS/FAIL, a winner, creative approval, delivery,
  canonical promotion, or direct state mutation.
- Stop if real Canon inputs drift or cannot be hash-bound.
- Stop rather than replacing real evidence with synthetic/simplified evidence.
- Preserve unrelated dirty/untracked files. No reset, cleanup, worktree move,
  commit, push, upload, or staging.

## 10. Acceptance

### Phase A PASS

- New tests genuinely fail before implementation and pass after it.
- Blind packet contains two credible neutralized variants and no answer leak.
- Tool is owned by the existing Editing Loop Skill and all relevant audits pass.
- Reviewer outputs cannot claim authority beyond flags.
- Fixture proof creates a proposed delta without modifying canonical state.
- Real Canon packet is reproducible and hash-bound.
- UTF-8/JSON/hash/path read-back and `git diff --check` pass.
- Human creative approval and final delivery remain false.

### Phase A UNKNOWN

- Whether a fresh LLM reviewer can reliably find useful differences.
- Which Canon variant the Human prefers.
- Whether the Human verdict should enter canonical editorial state.
- Full-suite status after this change.

### Not a success claim

Passing Phase A proves the mechanism is bounded and reviewable. It does not
prove creative quality, semantic correctness, model independence, transfer to
another film family, or delivery readiness.

## 11. Required report

The Phase A worker report must include:

- exact pre/post branch, HEAD, and dirty-tree status;
- files changed and line/addition counts;
- RED/GREEN commands and exit codes;
- focused/adjacent audit commands and exit codes;
- artifact paths and SHA-256 hashes;
- explicit blind-packet leakage audit;
- proof that real state/media/accepted artifacts were not mutated;
- deviations, retries, skips, blind spots, and stop-loss classification;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.
