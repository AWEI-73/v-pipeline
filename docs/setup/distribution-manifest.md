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
