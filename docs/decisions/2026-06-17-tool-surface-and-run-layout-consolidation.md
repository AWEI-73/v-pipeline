# Tool Surface And Run Layout Consolidation

Date: 2026-06-17
Status: accepted

## Context

The repository now has several surfaces that need to agree on ownership:

- `video_tools.py` is the large canonical CLI entrypoint.
- `tools/dashboard_server.py` serves the Control Index and read-only Dashboard.
- Workbench writes draft artifacts only.
- project runs now carry `run_layout.json` to describe canonical, draft, and
  cache artifact ownership.

The tempting refactor is to split `video_tools.py` and runtime orchestration
immediately. That is risky because the CLI remains the compatibility surface for
old scripts, current tests, and external agents.

## Decision

Do not split `video_tools.py` or `runtime.py` in this increment.

Instead:

1. Add a machine-readable command catalog for `video_tools.py`.
2. Use one `VIDEO_TOOLS_DISPATCH` registry for command dispatch and manifest
   generation.
3. Expose `video_tools.py commands-manifest [--out FILE]`.
4. Let Control Index / Dashboard APIs read `run_layout.json` as read-only
   navigation metadata.
5. Keep canonical artifacts protected. Frontend surfaces may display layout and
   draft readiness but must not infer ownership from folder names alone.

## Boundaries

`run_layout.json` is not a second source of truth. It describes where artifacts
live and which class owns them. It does not replace:

- `segment_contract.json`
- material maps
- `state.json`
- gate artifacts
- Workbench patch artifacts

The command catalog is also not a new plugin framework. It is a registry and
classification manifest for the existing CLI.

## Split Criteria

Split `video_tools.py` only after one of these is true:

- a command group gains enough independent change pressure to justify its own
  module-level parser and focused tests;
- the command catalog shows repeated ownership churn in one group;
- a consumer needs a stable subset CLI that cannot safely depend on the full
  entrypoint.

When splitting, keep `video_tools.py` as a compatibility facade first. Do not
move command behavior and change user-facing flags in the same increment.

## Verification

- Command catalog focused tests must prove all dispatch commands are classified.
- Dashboard server tests must prove `run_layout.json` is exposed when present,
  missing when absent, and structured as an error when malformed.
- Full regression remains the integration proof that the compatibility facade
  still works.
