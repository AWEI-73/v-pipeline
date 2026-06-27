---
name: shooting-brief
description: Material gap brief skill. Use after material_delta.json or material_map_lifecycle.json identifies missing/thin needs and the route must produce reshoot, generated-material, stock retrieval, text bridge, rewrite, or waiver tasks before BUILD.
---

# Shooting Brief / Material Gap Brief Skill

This skill converts material-map gaps into executable follow-up tasks. It is not
a standalone route and must not bypass material-map lifecycle gates.

## Route Position

```text
material_needs.json
  -> project_material_map.json
  -> material_delta.json
  -> material_gap_brief.json / shooting_brief.md
  -> generated-material / stock retrieval / reshoot / rewrite / waiver
  -> material-map review
  -> fresh material_delta.json
  -> BUILD only after gate passes
```

Use this skill when:

- `material_delta.json` has `missing` or `thin` needs;
- `material_map_lifecycle.json` is `await_material`,
  `await_revision_decision`, or `revision_blocked`;
- the user needs a practical list of what to collect, reshoot, generate,
  retrieve, rewrite, or waive.

Do not use this skill to invent coverage. Every task remains a proposal until
the resulting material returns through material-map review as evidence.

## Canonical Outputs

Write these artifacts in the run folder:

- `material_gap_brief.json`: machine-readable gap task packet.
- `shooting_brief.md`: human-readable reshoot / collection brief.
- `generated_material_jobs.json`: generated-material jobs, when generation is
  allowed.
- `stock_retrieval_jobs.json`: stock/search jobs, when stock bridge is allowed.

`shooting_brief.md` may be empty or minimal when all gaps are generation,
retrieval, rewrite, or waiver tasks. The canonical machine artifact is
`material_gap_brief.json`.

## material_gap_brief.json Schema

```json
{
  "artifact_role": "material_gap_brief",
  "version": 1,
  "source_refs": {
    "material_needs": "material_needs.json",
    "material_delta": "material_delta.json",
    "material_map_lifecycle": "material_map_lifecycle.json"
  },
  "route": "material-first | structure-first | hybrid",
  "tasks": [
    {
      "task_id": "gap-task-001",
      "need_id": "need_training_opening_wide",
      "delta_status": "missing | thin",
      "recommended_route": "collect_existing | reshoot | generated_material | stock_retrieval | text_bridge | script_rewrite | waiver",
      "priority": "must_have | important | optional",
      "segment_refs": ["seg_01"],
      "visual_intent": "wide training opening shot with class context",
      "acceptance_criteria": [
        "shows the requested subject clearly",
        "has enough usable duration for the target segment",
        "can be mapped to this need_id with review evidence"
      ],
      "constraints": {
        "proof_sensitive": true,
        "identity_sensitive": false,
        "generation_allowed": false
      },
      "notes": "Use real footage if this need is proof-sensitive."
    }
  ],
  "handoff": {
    "shooting_brief": "shooting_brief.md",
    "generated_material_jobs": "generated_material_jobs.json",
    "stock_retrieval_jobs": "stock_retrieval_jobs.json"
  }
}
```

## Route Policy

- `collect_existing`: ask the user to provide or point to existing files.
- `reshoot`: produce concrete shot requests with framing, duration, subject,
  location/context, and naming convention.
- `generated_material`: allowed only when the need is not proof-sensitive or the
  user explicitly accepts illustrative/generated truth.
- `stock_retrieval`: allowed for non-identity, non-proof bridge visuals.
- `text_bridge`: allowed for chapter cards, title cards, diagrams, and context
  labels.
- `script_rewrite`: use when the material gap means the segment should change
  rather than be faked.
- `waiver`: explicit human decision with reviewer and reason; never silent.

## Human Shooting Brief

`shooting_brief.md` should be concise and actionable:

```markdown
# Shooting Brief

Source: material_delta.json

## Must Have

### need_training_opening_wide
- Purpose: establish the class and training setting.
- Shot: 1 wide shot, 8-12 seconds usable.
- Framing: horizontal 16:9, stable, no fast pan.
- Acceptance: subject is clear and can be mapped to need_id.
- File naming: need_training_opening_wide_take1.mp4
```

## Handoff Rules

- A task is not coverage.
- A generated image existing on disk is not coverage.
- A stock clip downloaded to `materials/stock/` is not coverage.
- A reshot clip in `materials/raw/` is not coverage.
- All follow-up material must return through `project-material-map`,
  review/apply, and fresh `material_delta.json`.

## Upstream / Downstream

Upstream:

- `skills/material-map.md`
- `skills/gap-analyzer.md`
- `material_needs.json`
- `material_delta.json`
- `material_map_lifecycle.json`

Downstream:

- `skills/material-generation-fallback.md`
- `skills/generated-material-producer.md`
- `skills/material-map.md`
- `revision_decisions.json`
- `revised_segment_contract.json`
