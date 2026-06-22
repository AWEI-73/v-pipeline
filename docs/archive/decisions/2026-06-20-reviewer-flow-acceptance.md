# Reviewer Flow Acceptance

Date: 2026-06-20

## Decision

Add a deterministic reviewer-flow acceptance harness:

```powershell
python video_tools.py reviewer-flow-acceptance --level deep --scenario all --out reviewer_flow_acceptance.json
```

The harness expands `reviewer_policy_packet.json`, writes minimal
`artifact_review` samples when requested, and validates them through
`video_pipeline_core.reviewer_registry`.

## Why

The reviewer registry already defines roles and eval principles, but a registry
alone does not prove route usability. The pipeline needs a small smoke test that
confirms:

- normal route reviewers are covered;
- upstream story reviewers are covered;
- effects/brownfield reviewers are covered;
- disallowed gate strengths fail closed.

## Scenarios

| Scenario | Required reviewers |
|---|---|
| `route_smoke` | `story_director`, `material_producer`, `editorial_timeline`, `technical_verify` |
| `upstream_story` | `literary_editor`, `story_director`, `generated_material_art_director` |
| `effects_brownfield` | `editorial_timeline`, `audio_subtitle_reviewer`, `effect_reviewer`, `technical_verify` |
| `all` | union of the above |

## Boundary

This is not an automatic critique engine. It does not score actual creative
quality, inspect a video, or replace existing deterministic gates. It only proves
review policy coverage and artifact shape.

Actual quality review still needs a human or agent to produce meaningful
findings using the eval principles.

## Verification

```powershell
python -m unittest tests.test_reviewer_flow_acceptance tests.test_reviewer_registry -q
python video_tools.py reviewer-flow-acceptance --level deep --scenario all --artifact-dir .tmp/reviewer_flow_acceptance --out .tmp/reviewer_flow_acceptance.json
python -m unittest discover -s tests -q
```
