# Work Order: Stock Semantic-Fit Honesty Layer

Date: 2026-07-05
Status: design / next-round construction plan

## Background

The 2026-07-04 probe repair round parked the stock semantic-fit honesty layer.
The pipeline can now produce the storybook stock video and can fail closed on
provider, material intake, delivery, and dotenv visibility problems. One gap
remains: a stock provider returning candidates does not prove those candidates
semantically fit the story beat. The mini stress probes showed that hard or odd
queries can still return plausible-looking provider results; result count alone
is not an honesty gate.

This work order designs the next implementation pass. It must not be bundled
with provider repair, stock ranking changes, or VLM integration.

## Goal

Create a lightweight, reviewable semantic-fit layer for stock-backed clips so a
run can distinguish on-topic stock, loosely related B-roll, and off-topic
material before final QA treats the build as honest.

## Non-Goals

- Do not change provider APIs or credentials.
- Do not rewrite stock retrieval ranking.
- Do not add a real VLM or paid model dependency in this work order.
- Do not block current stock routes by default on day one.
- Do not replace material-map review or generated-material review.

## Concepts To Design

### Hard Query Relevance

Define a deterministic baseline score from existing metadata:

- query tokens and normalized prompt text;
- provider title / URL slug / tags when available;
- segment need text, beat role, and shot reason;
- explicit mismatch tokens for unrelated finance, abstract architecture,
  random sports, or generic business footage when the story beat asks for a
  concrete place/action/emotion.

The score should produce a confidence band, not a fake yes/no truth claim.

### Fit Grades

Use three primary grades:

- `on_topic`: material directly matches the need or beat.
- `loosely_related`: acceptable atmosphere, transition, or generic B-roll only.
- `off_topic`: no clear relationship to the need; must not satisfy a must-have
  story beat without waiver.

Record a separate `usage_intent`:

- `proof`: used as evidence of a real event/person/place.
- `support`: supports an idea or scene without proving it.
- `transition`: rhythm/texture only.

Stock defaults to `support` or `transition`; it should not become `proof`
without explicit reviewed provenance.

### Reviewer Override / Waiver

Allow reviewers to override a weak automated grade, but require fields:

- `waiver_id`
- `reviewer`
- `accepted_grade`
- `reason`
- `scope`: clip, segment, or whole route
- `expires_on_route_change`: default true

Waivers should be visible in final QA and should not silently mutate source
truth.

### Final QA Policy

Start in warn-only mode:

- `off_topic` on must-have needs: warning plus reviewer-visible report.
- unresolved `off_topic` with block mode enabled: hard block.
- `loosely_related` on non-must-have B-roll: allowed with visible note.
- waived findings: allowed but listed in final QA limitations.

Block mode must be controlled by an explicit gate, not inferred from normal
route execution.

## Artifact Contract Draft

Write `semantic_fit_report.json` with:

```json
{
  "artifact_role": "semantic_fit_report",
  "version": 1,
  "mode": "warn_only | block",
  "ok": true,
  "summary": {
    "clip_count": 0,
    "on_topic": 0,
    "loosely_related": 0,
    "off_topic": 0,
    "waived": 0
  },
  "clips": [
    {
      "clip_id": "segment-1-shot-0",
      "segment": 1,
      "need_id": "need_city_dawn",
      "source_path": "mvstock_1.mp4",
      "query": "quiet city dawn",
      "provider": "pexels",
      "provider_url": "https://...",
      "source_lineage": {
        "search_report": "search/query_01.json",
        "candidate_id": "4121893"
      },
      "evidence": {
        "need_text": "city wakes at dawn",
        "shot_reason": "available local stock contains a dawn city clip",
        "matched_terms": ["city", "dawn"],
        "mismatch_terms": []
      },
      "grade": "on_topic",
      "usage_intent": "support",
      "confidence": 0.82,
      "finding": null,
      "waiver": null
    }
  ],
  "findings": [],
  "next_action": null
}
```

Required per-clip evidence:

- query/source lineage;
- need or segment text used for comparison;
- provider candidate identity when available;
- matched and mismatched terms;
- grade, usage intent, confidence, and waiver fields.

## Test Strategy

Add deterministic fixtures:

- on-topic: city dawn query matched to city dawn provider metadata.
- loosely related: quiet office B-roll supporting a general work beat.
- off-topic: hard/odd query returning unrelated finance or abstract stock.

Focused tests:

- report schema and summary counts;
- must-have off-topic finding is warning in warn-only mode;
- must-have off-topic finding is blocking in block mode;
- reviewer waiver downgrades block while preserving limitation evidence;
- source lineage is required for every accepted stock clip.

Acceptance hook:

- add `python video_tools.py semantic-fit-audit ...` only after fixtures and
  unit tests exist; or
- extend `replay-acceptance --scenario probe-repair-20260704` with a
  `semantic_fit_warn_only` check once the report exists.

## Phased Rollout

1. Warn-only baseline: write `semantic_fit_report.json` from existing timeline,
   search reports, and segment contract metadata. Do not block builds.
2. Reviewer-visible report: surface weak matches in final QA / dashboard review
   and require explicit waiver fields for accepted off-topic clips.
3. Explicit block mode: block unresolved off-topic must-have clips only when a
   route or delivery requirement enables the semantic-fit gate.

## Deferred

- Real VLM judgment and provider cost management.
- New provider search strategies or ranking changes.
- Multi-provider re-query loops.
- Rewriting stock retrieval ranking.
- Treating stock clips as proof of real people/events without provenance.

## Acceptance For This Design Work Order

- This file exists and names the non-goals, artifact contract, tests, rollout,
  and deferred items above.
- `python video_tools.py interface-audit` exits 0.
- `python video_tools.py acceptance-contract --out .tmp/acceptance_contract.json`
  exits 0.
- `python -m unittest tests.test_video_tools_command_catalog -v` exits 0.
