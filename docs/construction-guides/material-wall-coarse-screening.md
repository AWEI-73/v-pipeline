# Material Wall Coarse Screening

Date: 2026-06-22
Status: active construction guide

## Purpose

Material wall is a cheap first-pass review layer before detailed material-map
review.

It answers:

- which assets are worth keeping;
- which assets are duplicates;
- which assets are weak or unusable;
- which visual roles the assets may serve.
- which same-folder siblings were compared before one candidate was kept.

It does not answer:

- which scene satisfies a specific `material_needs.need_id`;
- whether the project is ready for BUILD.
- exactly how long a selected clip should be trimmed in the final timeline.

Need-level decisions still belong to `material-map-review-apply`.
Fine trim decisions belong to a future clip-selection/editing layer.

## Commands

Build the wall request:

```powershell
python video_tools.py material-wall-build `
  --db materials_db.json `
  --out-dir verify/material_wall `
  --out verify/material_wall/material_wall_request.json `
  --photo-batch-size 60 `
  --video-batch-size 10
```

Apply the reviewer result:

```powershell
python video_tools.py material-wall-review-apply `
  --db materials_db.json `
  --verdict verify/material_wall/material_wall_review_verdict.json `
  --out materials_db.reviewed.json
```

## Visual Policy

Photos:

- one photo is one cell;
- default max is 60 photos per wall image;
- large sets are split into `photo_wall_01`, `photo_wall_02`, etc.

Videos:

- one video is one horizontal strip;
- a strip contains multiple frames, not just one thumbnail;
- default max is 10 video strips per wall image.

Frame budget:

| Duration | Frames |
|---|---:|
| 0-15s | 3 |
| 15-60s | 6 |
| 60-300s | 9 |
| 300s+ | 12 |

If ingest produced fewer keyframes than the budget, `material-wall-build`
extracts wall-only frames with ffmpeg. This is mechanical and does not call a
model.

## Review Verdict

```json
{
  "artifact_role": "material_wall_review_verdict",
  "version": 1,
  "reviewer": "agent:director",
  "at": "2026-06-22T12:00:00+08:00",
  "assets": [
    {
      "asset_id": "f0001",
      "coarse_status": "keep",
      "visual_role": ["opening", "people"],
      "quality": "usable",
      "visual_evidence": [
        "trainees are visible entering the training center",
        "location is recognizable"
      ],
      "duplicate_of": null,
      "usable_ranges": [
        {"start": 20.0, "end": 45.0, "reason": "clear group activity"}
      ],
      "why_not_selected": null,
      "notes": "wide opening and activity scenes"
    }
  ]
}
```

Allowed `coarse_status` values:

- `keep`
- `maybe`
- `reject`
- `duplicate`

`keep` and `maybe` set `selected_for_material_map=true` in the reviewed
materials DB. `reject` and `duplicate` do not.

Hard boundaries:

- Every visual asset in the DB must have one wall decision before apply.
- `keep` and `maybe` require non-empty `visual_evidence`.
- `reject` and `duplicate` require `why_not_selected`.
- `duplicate` requires `duplicate_of` to reference an existing asset.
- Folder names and source paths are hints only; they cannot replace visual
  evidence.

The request includes `candidate_groups` and each asset includes
`sibling_asset_ids`. Reviewers must compare same-folder siblings before keeping
a single representative. For example, if a `leader_encouragement` folder has ten
videos, keeping the first one because the folder name matches is not valid.

## Route Position

Recommended flow:

```text
ingest-meta
  -> material-wall-build
  -> bounded material-wall review
  -> material-wall-review-apply
  -> caption-meta / material-map only for selected candidates
  -> material-map-review-apply
  -> material-delta / lifecycle
  -> BUILD
```

For existing runs that have already passed `caption-meta`, material wall can
still be generated as a reviewer aid, but it should not overwrite existing maps
unless the operator intentionally reruns selection.

## Deferred Editing Layer

Material wall and material map do not decide final clip timing. The later
editing layer must decide:

- exact in/out points;
- whether long speech should be preserved, shortened, or split;
- whether photos need push/pan/crop/background treatment;
- duplicate-use limits;
- target duration enforcement.

Until that layer exists, BUILD must not treat material-map coverage as a license
to keep long speech ranges or auto-insert extra cards beyond the declared target.
