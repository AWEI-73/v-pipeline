---
name: video-pipeline
description: Use when producing, editing, reviewing, or repairing video. Locate the repository-local Hermes runtime, enter through its runbook, and route bounded work to the existing local skills and tools.
---

# Video Pipeline Runtime Launcher

Use this skill as a launcher and method router. The repository is the runtime,
truth store, registry, and test surface; this installed bundle contains no
runtime implementation or project state.

## Workspace discovery

1. Check the current directory first. Accept it only when `RUNBOOK.md` exists
   there; otherwise walk up the current directory's parents and accept the first
   workspace containing `RUNBOOK.md`.
2. If no current-directory workspace is found, read `VIDEO_PIPELINE_HOME` and
   accept it only when it names a directory containing `RUNBOOK.md`.
3. If neither location resolves to a workspace, fail closed: report that the
   runtime was not found and ask for a workspace path. Do not create files,
   install dependencies, or guess a repository.

## Entry and routing

After discovery, read `RUNBOOK.md` as the only first read. Read
`HANDOFF_CURRENT.md` second for live or IDLE state. Load
`docs/START_HERE_VIDEO_PIPELINE.md` only when route vocabulary is needed, then
load one repo-local skill or tool on demand for the requested operation.

Keep the repository-local runtime authoritative. Do not copy
`video_pipeline_core/**`, `tools/**`, route registries, Stage logic, schemas,
historical evidence, binaries, or project state into this skill.

## Bounded Agent freedom

Fuzzy/new whole-video work still enters Stage 0 and canonical BUILD. An existing
reviewed candidate with explicit locked and dirty layers may use the
Brownfield/finishing loop; the orchestrating agent may select existing
registered capabilities inside that bounded contract. Only dirty layers rerun,
then the result returns to Verify and Owner verdict. No direct whole-video hand
stitching, protected-truth mutation, or delivery promotion is allowed.

Do not install this skill globally, publish a package, push changes, or claim
creative approval or final delivery from launcher navigation alone.
