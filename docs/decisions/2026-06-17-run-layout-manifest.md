# Run Layout Manifest

Date: 2026-06-17
Status: accepted

## Decision

New project runs created by `video_pipeline_core.project_workspace.create_run_dir`
write a `run_layout.json` file at the run root.

The file is a machine-readable layout manifest for agents and frontend shells.
It records:

- folder roles;
- canonical artifact names;
- Workbench draft artifact names;
- derived cache directories;
- workspace policy flags.

## Why

The repository now has several valid entry points: runtime resume, contract-run,
Dashboard, Control Index, and Workbench. Humans can read the docs, but agents and
future frontend shells need a small artifact that says where to look without
guessing from folder names.

This also helps keep the repo as engine/source while project data stays outside
the repo under the project workspace.

## Boundary

`run_layout.json` is not a video contract and not a delivery gate artifact.

It does not replace:

- `segment_contract.json`;
- material maps;
- `state.json`;
- `artifact_manifest.json`;
- delivery or verification gate artifacts.

Workbench remains draft-only. Official render remains backend-owned.

## Verification

- `python -m unittest tests.test_project_workspace tests.test_runtime -q`
- `python -m unittest discover -s tests -q`
