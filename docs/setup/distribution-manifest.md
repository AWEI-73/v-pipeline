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

After extraction, the packaged repository must preserve this order:

1. `RUNBOOK.md` is the sole operational entry.
2. `HANDOFF_CURRENT.md` is read second for live or IDLE state.
3. `docs/START_HERE_VIDEO_PIPELINE.md` is optional orientation when route vocabulary is needed.
4. Route-specific docs and skills are loaded on demand.
5. `docs/INDEX.md` is discovery, not a competing operational entry.

`AGENTS.md` provides repository operating rules and points to `RUNBOOK.md`; it
does not replace the operational order above.

`roadmap.md` remains the current-state roadmap; it is not a replacement for
the runbook or the live handoff.

## Active State and Source-Only Packaging

The packaged source must carry an `IDLE` `HANDOFF_CURRENT.md` that does not
depend on ignored project state, local absolute paths, or absent artifacts.
Active project state is materialized outside the source distribution when an
operator starts a bounded run.

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
