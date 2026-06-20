# Reviewer Registry And Eval Principles

Date: 2026-06-20
Status: accepted

## Decision

Add a deterministic reviewer registry and route policy packet:

```powershell
python video_tools.py reviewer-policy --registry --out reviewer_registry.json
python video_tools.py reviewer-policy --level deep --out reviewer_policy_packet.json
python video_tools.py reviewer-policy --validate-review story_director_review.json
```

Implementation:

- `video_pipeline_core/reviewer_registry.py`
- CLI: `video_tools.py reviewer-policy`
- Docs: `docs/artifact-reviewer-map.md`

## Why

The pipeline now has a clear upstream route and material/build gates. The next
risk is inconsistent review behavior: different agents may invent different
reviewer names, score meanings, or gate strengths.

This registry fixes the contract without turning reviews into a global LLM
runtime.

## Included Roles

Policy levels:

- `light`: `material_producer`, `technical_verify`
- `normal`: `story_director`, `material_producer`, `editorial_timeline`,
  `technical_verify`
- `deep`: `literary_editor`, `story_director`, `material_producer`,
  `generated_material_art_director`, `editorial_timeline`,
  `audio_subtitle_reviewer`, `effect_reviewer`, `technical_verify`

Additional available role:

- `delivery_reviewer`

Each role declares:

- input artifacts;
- output artifact;
- allowed gate strengths;
- typical next actions;
- eval principles.

## Eval Principle Contract

Each principle has:

```json
{
  "criterion": "what is judged",
  "evidence": "which artifact/media evidence supports it",
  "failure_route": "where the pipeline should return if it fails"
}
```

This makes review results actionable instead of vague scores.

## Boundaries

- No automatic LLM reviewer invocation in `contract-run`.
- No new delivery hard gate from creative/advisory reviews.
- No replacement for `material_delta` or `verify`.
- No subjective scores are treated as canonical truth.

Reviewer artifacts guide route decisions; the owned artifacts remain the source
of truth.

## Verification

Focused tests:

```powershell
python -m unittest tests.test_reviewer_registry tests.test_canonical_route_acceptance tests.test_upstream_route_alignment_docs -q
```

Acceptance:

```powershell
python tools\canonical_route_acceptance.py --out .tmp\canonical_route_acceptance.json
```

Result: tests pass and canonical route acceptance reports `ok: true`.

