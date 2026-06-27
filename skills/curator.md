---
name: curator
description: Material curator skill. Use during material-map review to add coarse visual labels, diversity evidence, and scene-level review notes before material coverage, rough cut, or visual fatigue checks.
---

# Curator Skill

This skill reviews existing or generated material before it is trusted by the
material map. It is a material-map support skill, not a downloader, renderer, or
story writer.

## Route Position

```text
materials / generated candidates / stock candidates
  -> per-asset map
  -> curator review
  -> project_material_map.json with reviewed scene labels
  -> material_delta.json
  -> rough cut / BUILD only after gate passes
```

## Responsibilities

- Add shallow scene labels for visual diversity and review.
- Distinguish useful, duplicate, weak, rejected, and unreviewed material.
- Keep review evidence separate from canonical material truth until a
  deterministic apply step writes reviewed map output.
- Preserve uncertainty. Missing labels mean `unreviewed`, not pass.

## Scene Review Labels

Record project-local labels on reviewed material-map scenes:

- `visual_family`: project-defined coarse family, such as
  `outdoor_muster_wide`; do not use a global hardcoded family list.
- `angle_scale`: `wide | medium | close` when confidently visible.
- `action_family`: project-defined repeated action, when applicable.
- `subject`: short project-local subject label, when applicable.

`media_type` comes from the material map asset `asset_type`; do not duplicate it
on each scene.

## Review Artifact

Write a separate review artifact and let deterministic tooling apply it. Do not
mutate `project_material_map.json` by hand.

```json
{
  "artifact_role": "visual_diversity_review",
  "version": 1,
  "reviewer": "agent-or-human-id",
  "at": "caller-supplied timestamp",
  "scenes": [
    {
      "asset_id": "asset-a",
      "scene_index": 0,
      "visual_family": "project-local-family",
      "angle_scale": "wide",
      "action_family": "optional-project-local-action",
      "subject": "optional-project-local-subject",
      "verdict": "keep | maybe | duplicate | reject | unreviewed",
      "note": "short evidence note"
    }
  ]
}
```

Apply it with:

```text
python video_tools.py visual-diversity-review PROJECT_MAP --review REVIEW.json --out REVIEWED_PROJECT_MAP.json
python video_tools.py visual-diversity-coverage REVIEWED_PROJECT_MAP.json --out visual_diversity_coverage.json
```

Unknown scene references, duplicate scene references, and malformed labels fail
closed.

## Visual Family Vocabulary

When more than one agent reviews the same material pool, establish a
project-local `visual_family_vocabulary.json` before checking consistency.

Rules:

- The vocabulary is local to the project.
- It is not a global genre taxonomy.
- Normalization is deterministic alias mapping, not fuzzy semantic matching.
- VD2 soft-ranking remains blocked until normalized independent review evidence
  reaches the required consistency threshold.

## Handoff Rules

- Curator labels support material-map review, visual fatigue review, and rough
  cut selection.
- Curator labels do not satisfy `material_needs` by themselves.
- A `keep` verdict is still only evidence; material-map coverage must be
  recalculated.
- A `duplicate` or `reject` verdict should remove material from rough-cut
  candidates unless a human explicitly overrides it.

## Upstream / Downstream

Upstream:

- `skills/material-map.md`
- `materials_db.json`
- per-asset `*.map.json`
- `project_material_map.json`
- `material_wall_review_verdict.json`

Downstream:

- `visual_diversity_review.json`
- `visual_diversity_coverage.json`
- `project_material_map.json` reviewed projection
- `material_delta.json`
- `rough_cut_plan.json`
