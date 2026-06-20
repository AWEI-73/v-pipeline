# Artifact Reviewer Map

Date: 2026-06-20
Status: lightweight route policy / not a new hard-gate system

This document defines the reviewer layer for Hermes Video Pipeline. It does not
mean every artifact must always be reviewed. Route policy chooses a light,
normal, or deep review set based on project risk and user intent.

## Principle

`VERIFY` should not absorb every kind of judgment.

Use this split:

```text
Reviewer Layer
  -> Creative Review
  -> Contract / Material Review
  -> Build / Timeline Review
  -> Technical Verify
  -> Delivery Review
```

`VERIFY` remains the deterministic technical/delivery subset: black frames,
caption timing, audio levels, material gates, timeline invariants, and final
delivery readiness.

Creative reviewers exist earlier so the pipeline does not faithfully build a
weak story.

## Review Policy Levels

Route/template config may declare:

```json
{
  "review_policy": {
    "level": "normal"
  }
}
```

### `light`

Use for smoke tests, internal demos, or fast iteration.

Enabled reviewers:

- `material_producer`
- `technical_verify`

### `normal`

Use for most user-facing videos.

Enabled reviewers:

- `story_director`
- `material_producer`
- `editorial_timeline`
- `technical_verify`

### `deep`

Use for formal story videos, children's stories, important event films, or
generated-material-heavy routes.

Enabled reviewers:

- `literary_editor`
- `story_director`
- `material_producer`
- `generated_material_art_director`
- `editorial_timeline`
- `audio_subtitle_reviewer`
- `effect_reviewer`
- `technical_verify`

## Core Reviewers

| Reviewer | Review type | Input artifacts | Output artifact | Gate strength | Typical next action |
|---|---|---|---|---|---|
| `literary_editor` | creative review | `literary_role_lens.json`, `longform_source.md` | `literary_master_review.json` | revise | `revise_longform` / `ready_for_story_soul` |
| `story_director` | creative review | `story_soul_blueprint.json`, `screenplay_beats.json`, `director_shot_plan.json` | `story_director_review.json` | revise | `revise_story_soul` / `revise_shot_plan` |
| `material_producer` | contract/material review | `material_needs.json`, `project_material_map.json`, `material_delta.json` | existing `material_delta.json` plus optional `material_producer_review.json` | hard gate when coverage is broken | `await_material` / `generate_material` / `revise_contract` |
| `editorial_timeline` | build/timeline review | `timeline_build.json`, `preview_timeline.json`, contact sheet | `editorial_timeline_review.json` | revise/advisory | `workbench_draft_review` / `brownfield_edit` |
| `technical_verify` | technical verify | `final.mp4`, `subtitles.srt`, `timeline_build.json`, manifests | `verify_result.json`, audit reports | delivery gate | `fix_technical_issue` / `delivery_ready` |

## Optional Reviewers

| Reviewer | When enabled | Input artifacts | Gate strength |
|---|---|---|---|
| `generated_material_art_director` | generated images/video are used | `generated_material_quality_review.json`, generated manifest, reviewed map | revise; may block candidate acceptance |
| `audio_subtitle_reviewer` | voiceover/subtitles are important | `subtitles.srt`, audio mix, cue plan | revise |
| `effect_reviewer` | effects or Remotion adapter used | `effect_intent_plan.json`, `remotion_effect_review.json`, draft composite | revise/advisory unless route marks effect required |
| `delivery_reviewer` | formal handoff | final artifacts, report, limitations | delivery gate |

## Suggested Review Artifacts

Review artifacts should share this simple shape:

```json
{
  "artifact_role": "artifact_review",
  "version": 1,
  "reviewer_role": "story_director",
  "review_type": "creative_review",
  "input_artifact_role": "story_soul_blueprint",
  "decision": "pass | revise | block | advisory",
  "gate_strength": "advisory | revise | hard_gate | delivery_gate",
  "scores": {
    "narrative_device": 4,
    "emotional_arc": 5
  },
  "findings": [],
  "next_action": "revise_story_soul"
}
```

Do not make this a new canonical truth source. Reviews guide route decisions;
the owned artifact remains the source of truth.

## Route Placement

Recommended route:

```text
Intake
  -> Literary / Role Lens
  -> Literary Review (optional normal/deep)
  -> Story Soul Blueprint
  -> Story Director Review (normal/deep)
  -> Director Shot Plan
  -> Material Truth
  -> Material Producer Review / Delta Gate
  -> BUILD
  -> Editorial Timeline Review
  -> Technical Verify
  -> Brownfield / Delivery
```

## What Stays Out Of Scope For Now

- No global reviewer runtime.
- No automatic LLM reviewer invocation in `contract-run`.
- No new hard gate for literary or director review.
- No delivery blocking from advisory creative scores.
- No replacement of existing `material_delta` or `verify` gates.

The first implementation should only let route/template configs declare a review
policy and let agents decide which already-existing review tools or manual
review prompts to run.

