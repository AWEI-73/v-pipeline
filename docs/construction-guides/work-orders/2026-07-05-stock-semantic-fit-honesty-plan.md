# Work Order: Stock Semantic-Fit Honesty Layer

Date: 2026-07-05
Status: tightened design / ready for next-round construction

## Background

The 2026-07-04 probe repair round parked the stock semantic-fit honesty layer.
The pipeline can now produce the storybook stock video and can fail closed on
provider, material intake, delivery, and dotenv visibility problems. One gap
remains: a stock provider returning candidates does not prove those candidates
semantically fit the story beat. The mini stress probes showed that hard or odd
queries can still return plausible-looking provider results; result count alone
is not an honesty gate.

This work order designs the next implementation pass. It must not be bundled
with provider repair, stock ranking changes, provider re-query loops, or VLM
integration.

## Goal

Create a lightweight, deterministic, reviewable semantic-fit layer for
stock-backed clips so a run can distinguish on-topic stock, loosely related
B-roll, and off-topic material before final QA treats the build as honest.

The layer must also prevent a stock clip from silently satisfying proof of a
real event/person/place without reviewed provenance.

## Non-Goals

- Do not change provider APIs or credentials.
- Do not rewrite stock retrieval ranking.
- Do not add a real VLM or paid model dependency in this work order.
- Do not add provider re-query loops.
- Do not block current stock routes by default on day one.
- Do not replace material-map review or generated-material review.
- Do not treat stock clips as proof of real people/events without provenance.
- Do not add `video_tools.py semantic-fit-audit` before fixtures and unit tests
  exist.

## Definitions / Decision Model

The implementation must keep automated grading, reviewer decisions, and final
effective decisions separate.

### Fit Grades

- `on_topic`: provider metadata and source lineage directly match the requested
  need or beat. A city-dawn need matched to a city skyline at sunrise is
  `on_topic`.
- `loosely_related`: provider metadata shares atmosphere, setting, texture, or
  generic concept with the need, but misses a concrete required subject, action,
  person, place, or emotion. It can support a non-proof B-roll or transition
  use, but it cannot satisfy proof or a concrete must-have story beat.
- `off_topic`: provider metadata has no clear relationship to the need or has
  explicit mismatch terms. Finance charts for a child-courage story beat are
  `off_topic`.

### Usage Intent

- `proof`: used as evidence that a real event/person/place/action happened.
- `support`: supports an idea or scene without proving it.
- `transition`: rhythm, texture, visual punctuation, or bridge only.
- `illustrative`: conceptual illustration that is not evidence of the real
  subject.

Stock clips default to `support`, `transition`, or `illustrative`. A stock clip
must not become `proof` unless reviewed provenance proves it is the actual
event/person/place/action.

### Truth Requirement

- `proof_required`: the need must be satisfied by real, proven material. Stock
  without reviewed provenance is not enough.
- `support_ok`: the need may be satisfied by semantically matching support or
  illustrative stock.
- `atmosphere_only`: the need only requires mood, rhythm, or transition texture.

### Required Fields

- `must_have`: boolean. True means the need is required for the story, route, or
  delivery promise.
- `automated_grade`: the current deterministic classifier output.
- `original_grade`: immutable copy of the first automated grade for this
  source/need pairing.
- `original_finding`: immutable finding produced by the first automated grade.
- `reviewer_decision`: reviewer response or waiver decision. It is separate
  from automated/original grade.
- `effective_decision`: final machine-readable decision after policy and
  reviewer waiver rules are applied.

`original_grade` and `original_finding` must never be overwritten by a waiver,
rerun patch, or reviewer edit. Reviewers may only add `reviewer_decision` and
`waiver` fields. Final QA must display both the original finding and reviewer
decision whenever a finding is waived or accepted with limitation.

## Hard Rules

1. Stock clips are not proof by default.
2. If `truth_requirement=proof_required`, a stock clip must include reviewed
   provenance before it can satisfy the need as proof. Without provenance it is
   at least a warning in `warn_only` mode and a block in `block` mode.
3. `loosely_related` can satisfy only `support`, `transition`, or
   `illustrative` usage, and only when `truth_requirement` is `support_ok` or
   `atmosphere_only`.
4. `loosely_related` cannot satisfy `proof_required`.
5. `must_have=true` and `automated_grade=off_topic` is a warning in
   `warn_only` mode and a block in `block` mode unless a complete waiver
   accepts it as support or transition.
6. `off_topic` cannot satisfy `must_have=true` with
   `truth_requirement=proof_required`.
7. A waiver can change only `effective_decision`; it cannot delete findings,
   rewrite `automated_grade`, rewrite `original_grade`, or convert
   `off_topic` into `on_topic`.
8. A waiver cannot convert `support`, `transition`, or `illustrative` stock into
   `proof`.
9. Abstract transition use may be waived, but the waiver must have
   `scope=clip` or `scope=segment`, a concrete reason, and final QA limitation
   visibility.
10. `ok=true` in `warn_only` mode does not mean no semantic risk exists. It
    means no active block exists. Warnings and waivers must still be listed in
    summary counts, findings, and final QA limitations.

## Hard Query Relevance

Define a deterministic baseline score from existing metadata:

- query tokens and normalized prompt text;
- provider title, URL slug, tags, and description when available;
- segment need text, beat text, beat role, and shot reason;
- declared `must_have`, `truth_requirement`, and `usage_intent`;
- explicit mismatch tokens for unrelated finance, abstract architecture,
  random sports, generic business footage, or any domain unrelated to the story
  beat when the need asks for a concrete place/action/emotion.

The score should produce a confidence band and a grade. It must not pretend to
be visual truth. The report should state which text evidence caused the grade.

## Artifact Contract

Write `semantic_fit_report.json`.

```json
{
  "artifact_role": "semantic_fit_report",
  "version": 1,
  "mode": "warn_only | block",
  "ok": true,
  "summary": {
    "clip_count": 0,
    "on_topic_count": 0,
    "loosely_related_count": 0,
    "off_topic_count": 0,
    "proof_required_count": 0,
    "must_have_off_topic_count": 0,
    "waived_count": 0,
    "blocked_count": 0,
    "warning_count": 0
  },
  "clips": [
    {
      "clip_id": "segment-1-shot-0",
      "segment_id": "seg-1",
      "segment_index": 1,
      "need_id": "need_city_dawn",
      "source_path": "mvstock_1.mp4",
      "must_have": false,
      "truth_requirement": "support_ok",
      "usage_intent": "support",
      "source_truth": "stock",
      "query": "quiet city dawn",
      "provider": "pexels",
      "provider_asset_id": "4121893",
      "provider_url": "https://...",
      "source_lineage": {
        "search_report": "search/query_01.json",
        "candidate_id": "4121893",
        "search_query": "quiet city dawn",
        "selected_by": "stock_provider_candidate"
      },
      "evidence": {
        "need_text": "city wakes at dawn",
        "beat_text": "quiet city dawn opening beat",
        "shot_reason": "available local stock contains a dawn city clip",
        "matched_terms": ["city", "dawn"],
        "mismatch_terms": [],
        "provider_title": "City skyline at sunrise",
        "provider_tags": ["city", "sunrise", "skyline"],
        "provider_slug": "city-skyline-at-sunrise"
      },
      "confidence": 0.82,
      "automated_grade": "on_topic",
      "original_grade": "on_topic",
      "original_finding": null,
      "reviewer_decision": null,
      "waiver": null,
      "effective_decision": {
        "status": "accepted",
        "reason": "on_topic_support",
        "blocks_delivery": false,
        "warns_final_qa": false
      },
      "final_qa_visibility": {
        "show_original_finding": false,
        "show_reviewer_decision": false,
        "limitation": null
      }
    }
  ],
  "findings": [],
  "next_action": null
}
```

Required per-clip fields:

- `clip_id`
- `segment_id` or `segment_index`
- `need_id`
- `must_have`
- `truth_requirement`
- `usage_intent`
- `source_truth`
- `query`
- `provider`
- `provider_asset_id` and/or `provider_url` when available
- `source_lineage`
- `evidence.need_text`
- `evidence.beat_text`
- `evidence.shot_reason`
- `evidence.matched_terms`
- `evidence.mismatch_terms`
- provider title/tags/slug when available
- `automated_grade`
- `original_grade`
- `original_finding`
- `reviewer_decision`
- `waiver`
- `effective_decision`
- `final_qa_visibility`

Required summary counts:

- `on_topic_count`
- `loosely_related_count`
- `off_topic_count`
- `proof_required_count`
- `must_have_off_topic_count`
- `waived_count`
- `blocked_count`
- `warning_count`

## Waiver Semantics

Reviewer waivers must use this shape:

```json
{
  "waiver_id": "waiver-semfit-001",
  "reviewer": "director",
  "decision": "accept_as_support | accept_as_transition | accept_with_limitation | reject",
  "reason": "Accepted as abstract transition texture, not as story evidence.",
  "scope": "clip | segment | route",
  "expires_on_route_change": true,
  "created_at": "2026-07-05T00:00:00Z",
  "original_grade_snapshot": "off_topic",
  "original_finding_snapshot": {
    "rule": "off_topic_stock",
    "message": "Provider metadata did not match the story need."
  }
}
```

Rules:

- The waiver must preserve `original_grade_snapshot` and
  `original_finding_snapshot`.
- The waiver must not rewrite `original_grade`, `original_finding`, or
  `automated_grade`.
- The waiver must not convert `off_topic` into `on_topic`.
- The waiver must not convert `support`, `transition`, or `illustrative` stock
  into `proof`.
- `decision=reject` keeps or creates a block when the finding would block under
  the current mode.
- `accept_as_support`, `accept_as_transition`, and `accept_with_limitation`
  may change `effective_decision.status`, but final QA must still list a
  limitation and show the original finding.
- A route-scope waiver is allowed only for repeated non-proof background
  texture; it must not waive a `proof_required` mismatch.

## Final QA Policy

Start in `warn_only` mode:

- `off_topic` on `must_have=true`: warning plus reviewer-visible report.
- unresolved `off_topic` with `mode=block`: block.
- `loosely_related` on non-must-have support/transition/illustrative usage:
  allowed with visible note.
- `proof_required` without reviewed provenance: warning in `warn_only`; block
  in `block`.
- waived findings: allowed only according to waiver rules and still listed in
  final QA limitations.

Block mode must be controlled by an explicit gate or delivery requirement. It
must not be inferred from normal route execution.

## Deterministic Acceptance Fixture Matrix

The next implementation must add deterministic fixtures covering at least these
cases. Fixtures should use small JSON payloads only; no live provider calls.

| Case | Purpose | Query / Need | Provider Metadata | Inputs | Expected Automated Grade | Expected Decision |
|---|---|---|---|---|---|---|
| 1 | on-topic support | query `quiet city dawn`; need `city wakes at dawn` | `city skyline at sunrise` | `must_have=false`, `truth_requirement=support_ok`, `usage_intent=support` | `on_topic` | pass / accepted |
| 2 | loosely-related transition | query `lonely student studying` | `quiet office desk and laptop` | `must_have=false`, `truth_requirement=atmosphere_only` or `support_ok`, `usage_intent=transition` or `support` | `loosely_related` | pass or warning only for support/transition; never proof |
| 3 | off-topic must-have | query `child learning courage` | `stock market finance chart` | `must_have=true`, `truth_requirement=support_ok` or `proof_required` | `off_topic` | warning in `warn_only`; block in `block` |
| 4 | proof-required mismatch | user need `real footage of actual graduation ceremony` | `generic graduation stock clip` | `must_have=true`, `truth_requirement=proof_required`, no reviewed provenance | `loosely_related` or `off_topic`, but not proof | not proof; warning in `warn_only`; block in `block` unless reviewed provenance exists |
| 5 | waiver abstract transition | off-topic metadata accepted only as texture | unrelated abstract/business clip | complete waiver with `decision=accept_as_transition`, `scope=clip` or `segment` | original stays `off_topic` | `effective_decision=accepted_with_limitation`; final QA lists waiver |
| 6 | invalid waiver attempt | reviewer tries to convert off-topic to on-topic/proof | unrelated clip | waiver says `accepted_grade=on_topic` or proof conversion | original stays `off_topic` | schema/test rejects waiver |

Additional acceptance tests should include:

- source lineage required for every accepted stock clip;
- missing `reviewer`, `reason`, `scope`, `waiver_id`, or original snapshots
  rejects a waiver;
- same office-desk fixture is `off_topic` when the need explicitly requires a
  visible student as `must_have=true`;
- final QA/report limitations include waived findings and original findings.

## Next Implementation Pieces

### Piece 1: Schema / Data Model

Goal: define report construction and validation without grading logic.

- Red-first test idea: minimal valid `semantic_fit_report.json` passes schema;
  missing `original_grade`, `truth_requirement`, or `source_lineage` fails.
- Files likely touched:
  - `video_pipeline_core/semantic_fit.py`
  - `tests/test_semantic_fit.py`
  - `tests/fixtures/semantic_fit/`
- Acceptance command:
  - `python -m unittest tests.test_semantic_fit -v`
- Commit message suggestion:
  - `Add semantic fit report schema`

### Piece 2: Deterministic Grading Baseline

Goal: classify on-topic, loosely-related, and off-topic cases from deterministic
metadata fixtures.

- Red-first test idea: fixture cases 1-4 produce the expected grade and summary
  counts.
- Files likely touched:
  - `video_pipeline_core/semantic_fit.py`
  - `tests/test_semantic_fit.py`
  - `tests/fixtures/semantic_fit/*.json`
- Acceptance command:
  - `python -m unittest tests.test_semantic_fit -v`
- Commit message suggestion:
  - `Classify stock semantic fit from deterministic metadata`

### Piece 3: Waiver / Effective Decision Logic

Goal: apply reviewer decisions without mutating original grade or finding.

- Red-first test idea: valid abstract-transition waiver changes only
  `effective_decision`; invalid waiver that converts off-topic to proof is
  rejected.
- Files likely touched:
  - `video_pipeline_core/semantic_fit.py`
  - `tests/test_semantic_fit.py`
- Acceptance command:
  - `python -m unittest tests.test_semantic_fit -v`
- Commit message suggestion:
  - `Preserve original semantic fit findings through waivers`

### Piece 4: Final QA / Report Visibility Integration

Goal: make final QA or delivery review surface semantic-fit warnings,
limitations, and blocks.

- Red-first test idea: waived off-topic transition appears in final QA
  limitations with original finding and reviewer decision; proof-required stock
  without provenance blocks in block mode.
- Files likely touched:
  - `video_pipeline_core/delivery_gate.py` or final QA/report module selected by
    current ownership
  - `video_pipeline_core/semantic_fit.py`
  - focused delivery/final QA tests
- Acceptance command:
  - focused final QA/delivery test command chosen by implementer
  - `python video_tools.py interface-audit`
- Commit message suggestion:
  - `Surface semantic fit limitations in final QA`

### Piece 5: Optional CLI / Acceptance Hook

Goal: expose the feature only after pieces 1-4 are tested.

- Red-first test idea: CLI writes `semantic_fit_report.json` from fixture
  timeline/search/contract inputs, exits nonzero on block-mode unresolved
  off-topic must-have, and is referenced by command catalog only after it
  exists.
- Files likely touched:
  - `video_tools.py`
  - `video_pipeline_core/tool_command_catalog.py`
  - `video_pipeline_core/acceptance_contract.py` only if promoted to standard
    acceptance
  - `video_pipeline_core/replay_acceptance.py` only if adding a replay hook
- Acceptance command:
  - `python -m unittest tests.test_semantic_fit -v`
  - `python video_tools.py interface-audit`
  - optional `python video_tools.py replay-acceptance --scenario probe-repair-20260704`
- Commit message suggestion:
  - `Expose semantic fit audit after deterministic fixtures`

## Phased Rollout

1. Warn-only baseline: write `semantic_fit_report.json` from existing timeline,
   search reports, provider metadata, and segment contract metadata. Do not
   block builds.
2. Reviewer-visible report: surface weak matches in final QA / dashboard review
   and require explicit waiver fields for accepted off-topic clips.
3. Explicit block mode: block unresolved off-topic must-have clips and
   proof-required clips without provenance only when a route or delivery
   requirement enables the semantic-fit gate.

## Deferred

- Real VLM judgment and provider cost management.
- New provider search strategies or ranking changes.
- Multi-provider re-query loops.
- Rewriting stock retrieval ranking.
- Treating stock clips as proof of real people/events without provenance.
- Automatically blocking current stock routes before an explicit block-mode
  gate exists.

## Acceptance For This Design Work Order

- This file defines the decision model, hard rules, artifact contract, waiver
  semantics, deterministic fixture matrix, implementation pieces, rollout, and
  deferred items above.
- `python video_tools.py interface-audit` exits 0.
- `python video_tools.py acceptance-contract --out .tmp/stock_semantic_fit_acceptance_contract.json`
  exits 0.
- `python -m unittest tests.test_acceptance_contract -v` exits 0.
- `git diff --check` reports no whitespace errors.
