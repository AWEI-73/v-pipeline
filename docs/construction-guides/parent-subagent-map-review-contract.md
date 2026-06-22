# Parent/Subagent Map Review Contract

Date: 2026-06-22
Status: active construction guide

## Why This Exists

The video pipeline is a state machine. The parent agent owns the run folder and
state transitions. Subagents are bounded workers that produce one artifact for
one gate, then stop.

For `material-map-lifecycle`, the common blocking point is:

```text
stage = await_map_review
next_action = await_map_review
```

This means the project has `material_needs.json` and material maps, but no
reviewed scene-to-need links. The pipeline must not jump to BUILD from here.

## Parent Agent Loop

1. Read `material_map_lifecycle.json`.
2. If `next_action=await_map_review`, issue a bounded review task packet.
3. The subagent reads only the declared maps, needs, and context files.
4. The subagent writes `material_map_review_verdict.json`.
5. The parent applies the verdict with `material-map-review-apply`.
6. The parent reruns `project-material-map`, `material-delta`, and
   `material-map-lifecycle`.
7. If the lifecycle reaches `build_ready`, the parent continues to BUILD.

Long render/build jobs stay parent-owned. Reviewer subagents do not background
render work.

## Subagent Output

The review worker writes:

```json
{
  "artifact_role": "material_map_review_verdict",
  "version": 1,
  "reviewer": "agent:director",
  "at": "2026-06-22T12:00:00+08:00",
  "decisions": [
    {
      "asset_id": "clip-a",
      "scene_index": 0,
      "need_id": "nd_opening",
      "status": "accepted",
      "visual_evidence": [
        "trainees are visible entering the training center",
        "the shot clearly establishes the cohort and location"
      ],
      "evidence_basis": "visual_wall_and_map",
      "note": "clear establishing shot"
    }
  ]
}
```

Allowed `status` values are `candidate`, `accepted`, and `rejected`.

For `status=accepted`, `visual_evidence` is required. Folder names, file names,
and source-path labels are weak hints only. They cannot be the sole basis for an
accepted edge. If the visual evidence only proves a looser concept, write
`candidate` or choose the looser matching need instead.

Example: a file under a `leader_encouragement` folder that only shows a group
assembly must not be accepted as `leader_encouragement` unless the reviewer can
cite visible leader/speaker evidence from the frames.

If same-folder siblings exist, the reviewer should prefer the visually strongest
matching sibling. A previously selected representative is not automatically the
best match; the selected asset can be downgraded to `candidate` or `rejected`
when the visual evidence does not meet the need contract.

## Parent Apply Command

```powershell
python video_tools.py material-map-review-apply `
  --maps-dir maps `
  --needs material_needs.json `
  --verdict material_map_review_verdict.json `
  --out project_material_map.json
```

The command updates the matching per-asset `*.map.json` files with scene-level
`satisfies` edges and writes a reviewed `project_material_map.json`.

It fails closed on:

- unknown `asset_id`
- invalid `scene_index`
- unknown `need_id`
- invalid status
- missing `*.map.json`

## Route Task Packet Shape

Use a packet like this when the parent dispatches a real subagent:

```json
{
  "artifact_role": "route_subagent_task",
  "stage": "await_map_review",
  "role": "material-map-reviewer",
  "objective": "Link reviewed material-map scenes to canonical material_needs need_id values.",
  "read_only_inputs": [
    "material_needs.json",
    "maps/*.map.json",
    "material_map_lifecycle.json"
  ],
  "allowed_outputs": [
    "material_map_review_verdict.json",
    "route_subagent_result.json"
  ],
  "must_not_touch": [
    "segment_contract.json",
    "final.mp4",
    "materials/raw/materials_db.json"
  ],
  "success_criteria": [
    "Every accepted decision references an existing asset_id and scene_index.",
    "Every accepted decision references a canonical need_id.",
    "Every accepted decision includes visual_evidence from the frames/map, not only source path.",
    "The verdict explains why the scene satisfies or does not satisfy the need.",
    "No BUILD, render, or source material files are modified."
  ]
}
```

## Practical Rule

Parent agents dispatch judgment. Parent agents apply state transitions.
Subagents do not own the full route.
