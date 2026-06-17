# Material Organization Policy

Date: 2026-06-17
Status: current

This document defines how Hermes should organize material files without creating
a second truth source beside the material map.

## Canonical Truth

The canonical material truth is the material-map data:

- `project_material_map.json`
- per-asset `*.map.json`
- `materials_db.json` references
- scene-level evidence such as `asset_id`, `source`, `scene_index`, windows,
  captions, satisfies edges, and visual labels

Physical folders are convenience views. They must not replace the material map.

## Default Rule

Do not move source files as part of normal pipeline operation.

Why:

- many maps and timelines reference absolute source paths;
- moving original files can break previously verified windows;
- duplicate physical copies make it unclear which file is canonical;
- UI filtering can be driven from material-map metadata without relocating files.

## Allowed Folder Projections

If a project needs a more human-readable library, create projection folders only.

Recommended projection names:

```text
materials/raw/          original incoming files
materials/selected/     copied or linked approved edit material
materials/generated/    generated fallback material
materials/rejected/     optional review convenience only
materials/proxies/      derived preview proxies
materials/thumbs/       derived thumbnails
```

Projection rules:

- keep original source files in place unless the user explicitly requests
  archival relocation;
- if copying to `selected/`, preserve the original source path in the material
  map lineage;
- never make a projection folder the only source of evidence;
- generated thumbnails/proxies are rebuildable cache, not source material;
- UI drag/drop should emit draft patch operations referencing material-map
  `asset_id` and `scene_index`, not raw folder positions.

## Workbench / Dashboard Boundary

Dashboard may show material-map coverage and draft status.

Workbench may browse material-map assets and draft `replace_clip` operations.

Neither surface should reorganize physical files by default. A future material
organizer may exist, but it must write a separate audit report and require
explicit user approval before moving or deleting source files.

## Agent Guidance

When asked to "organize material":

1. Prefer building or refreshing material maps.
2. If folders are messy, produce a proposed projection plan first.
3. Do not execute moves/deletes automatically.
4. If copies are made, include source lineage and hashes.
5. Keep `project_material_map.json` as the lookup contract for BUILD.

## Deferred

- Physical archival mover with dry-run/apply modes.
- Duplicate-file cleanup.
- Visual-family folder projection.
- Dashboard material-map coverage panel.
