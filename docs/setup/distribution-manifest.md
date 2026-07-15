# Distribution Manifest

This document describes release contents. The packaging mechanism itself is a
pending owner decision: pip package, zip archive, template repository, or another
format.

## Include

- `README.md`
- `AGENTS.md`
- `CLAUDE.md`
- `requirements.txt`
- `.env.example`
- `runtime.py`
- `video_pipeline.py`
- `video_tools.py`
- `video_pipeline_core/**`
- `tools/**`
- `skills/**`
- `docs/**`, excluding archived docs listed below
- `dashboard/**`
- `examples/**`
- `THIRD_PARTY_NOTICES.md`

## Operational Entry Surfaces

The packaged repository must preserve the existing entry hierarchy:

1. `AGENTS.md` provides repository operating rules and points to `RUNBOOK.md`.
2. `RUNBOOK.md` is the sole operational entry.
3. `docs/START_HERE_VIDEO_PIPELINE.md` is orientation after the runbook.
4. `HANDOFF_CURRENT.md` is the only live current-task pointer.
5. `docs/INDEX.md` is discovery, not a competing operational entry.

`roadmap.md` remains the current-state roadmap; it is not a replacement for
the runbook or the live handoff.

## Active State and Source-Only Packaging

An active `HANDOFF_CURRENT.md` may refer to ignored project state under
`.tmp/` or another local materialization root; that state is intentionally not
part of the source-controlled distribution.

A packaged or source-only release must provide an `IDLE` handoff template or
a project-import/materialization mechanism before it claims to run an active
campaign. This cleanup documents that boundary but does not implement the
packaging mechanism.

## Exclude

- `runs/`
- `reference repo/`
- `.tmp/`
- `graphify-out/`
- `archive/`
- `docs/archive/`
- `.env`
- `.env.*`
- virtual environments and local caches
- generated media outputs not intentionally promoted as examples

## Pending Owner Decisions

- Packaging mechanism.
- License selection. Do not create or choose a `LICENSE` file until the owner
  decides.

## Known Local Tooling Requirements

- Browser verification that uses Node scripts requires Node-side Playwright to
  be resolvable from the clean clone environment. Python Playwright is installed
  through `requirements.txt`, but Node Playwright is a separate runtime
  dependency for `node` / `node_repl` browser probes and should be installed or
  otherwise provided by the operator environment.
