# Endgame Spec: Three Parallel Streams to Product-Ready

Date: 2026-07-03
Deadline context: project close-out target 2026-07-07.
Mode: THREE agents run in parallel on the same master working tree, NO
branches. This works only because the file fences below are absolute and
file-level exclusive — the model was proven by the V2/Agent-B parallel run.

## Global rules (all three streams)

1. Read first: `docs/START_HERE_VIDEO_PIPELINE.md` (Rule Zero + Tier 1),
   then your own stream section ONLY. Do not execute another stream's tasks.
2. File exclusivity is the law. Each stream has an OWNER ZONE (only you may
   modify those paths) and everything not in your zone is read-only. If a
   task seems to need a file outside your zone, record it in your report and
   skip that item. No exceptions, no "small harmless edits".
3. Tests: miniconda python only —
   `"%USERPROFILE%\miniconda3\python.exe" -m unittest discover -s tests`.
   Full suite green before EVERY commit.
4. Parallel-suite artifact: if a full-suite failure looks like a temp-file
   or port collision (another agent is running suites too), re-run the
   failing module focused, then the full suite once more, before treating it
   as real. Never "fix" another stream's zone to make your suite pass.
5. Code navigation helper (optional): a codebase-memory MCP index exists
   (project `C-Users-user-Desktop-video_pipeline`, ~9.3k nodes). Usage and
   limits: `docs/codebase-memory-mcp-handoff.md`. It is for LOCATING code
   only — route truth stays in the registry/docs/tests.
6. Contradictions: record, skip, continue. TDD: red evidence before fix
   where a behavior changes. No debris files at repo root on finish.
7. Reports: append `## Report` to the END of your own stream section in
   THIS file (each stream appends only inside its own section — this file
   is shared, so append-only, never reflow other sections). Report commits,
   test tails, contradictions, skipped items.

## Shared-file ownership table (the collision map)

| File/zone | Owner |
|---|---|
| `video_pipeline_core/**`, `video_tools.py`, `tool_command_catalog` | S1 |
| `tests/**` except the two files below | S1 |
| `tests/test_preflight.py` (new) | S2 |
| `tests/test_dashboard_server.py`, `tests/dashboard_spa_render_smoke.mjs` | S3 |
| `examples/**` | S1 |
| root: `requirements.txt`(new), `.env.example`, `README.md`, `AGENTS.md`(new), `CLAUDE.md` | S2 |
| `tools/preflight.py` (new) | S2 |
| `docs/INDEX.md`, new setup docs | S2 |
| `dashboard/**`, `tools/dashboard_server.py`, `tools/workbench_server.py` | S3 |
| root debris files (see S3 list), `RUNBOOK.md` | S3 |
| `docs/START_HERE_VIDEO_PIPELINE.md`, `skills/**`, `runtime.py`, `video_pipeline.py`, `docs/branch-contract-registry.json` | FROZEN — nobody touches |

---

# Stream S1 — Asset Store (path discipline retrofit)

Goal: artifacts persist run-relative asset refs; absolute paths are resolved
only at point of use; an audit instrument enforces it. This is THE
architectural prerequisite for anyone cloning the repo.

Owner zone: `video_pipeline_core/**`, `video_tools.py`,
`video_pipeline_core/tool_command_catalog.py`, `tests/**` (minus S2/S3
files), `examples/**`.

Behavior contract that protects the other streams (hard rule): all
SERVING/projection surfaces (`preview_timeline` projection, `/media`
allow-list inputs, anything the workbench frontend consumes) continue to
receive RESOLVED ABSOLUTE paths exactly as today. Only persisted artifact
JSON content changes to relative refs. If you cannot keep that true for a
family, stop that family and record why.

## S1 pieces (sequential, one commit each minimum)

1. **Resolver + audit (warn mode).** New `video_pipeline_core/asset_paths.py`:
   - `to_asset_ref(run_dir, path)` — relativize when under run_dir, else
     return unchanged with a `portable=False` marker available;
   - `resolve_asset_ref(run_dir, ref)` — join relative refs, pass through
     absolute; no filesystem writes.
   New CLI `python video_tools.py asset-path-audit <run_dir>`: scans the
   run's artifact JSONs for absolute-path patterns (Windows drive-letter and
   POSIX-root regexes), groups findings by artifact family using
   `docs/interface-contracts/pipeline-product-artifact-dictionary.json` +
   `pipeline-api-dictionary.json` names, prints counts. Warn mode default
   (exit 0); `--strict` exits 1 on any finding in families listed in
   `STRICT_FAMILIES` (starts empty). Classify the command in the catalog.
   Tests: unit tests for both functions incl. Windows/POSIX cases
   (PureWindowsPath/PurePosixPath), audit pass/fail seeded cases.
   Commit: `Add asset path resolver and portability audit`.
2. **Material family conversion.** Writers of material map / inventory /
   ingest artifacts persist refs via `to_asset_ref`; their consumers resolve
   via `resolve_asset_ref`. Locate writers by scanning for path-bearing
   fields of that family (the dictionaries name the artifacts; grep +
   codebase-memory locate the code). Old runs with absolute paths keep
   working (resolver passthrough). Add `material` to `STRICT_FAMILIES`.
   Red test first: a fixture run written by the new writer contains no
   absolute paths and still dry-builds.
   Commit: `Persist material artifacts with run-relative asset refs`.
3. **Timeline/build family conversion.** Same treatment for timeline build /
   contract adapter / build handoff artifacts. ffmpeg and subprocess calls
   keep receiving absolute paths (resolve at call site). Add family to
   strict. Commit: `Persist build artifacts with run-relative asset refs`.
4. **Audio + effects families conversion.** Same. Add to strict.
   Commit: `Persist audio and effect artifacts with run-relative asset refs`.
5. **Ingest + GC.** `python video_tools.py ingest-assets <run_dir> --from <dir>`:
   bring external materials into `<run_dir>/assets/` (hardlink when
   same-volume, copy otherwise), register/update refs through the material
   map path (do NOT bypass map resolution). `python video_tools.py gc-assets
   <run_dir>`: list assets unreferenced by any live artifact, `--delete` to
   remove, always print a size report. Both classified in the catalog, both
   fail-closed on ambiguity. Tests for hardlink/copy/gc-orphan cases.
   Commit: `Add asset ingest and garbage collection commands`.

Per-piece acceptance: focused tests green; full suite green; BOTH e2e-smoke
cases exit 0; `registry-audit` exit 0. Final acceptance additionally: run
`asset-path-audit --strict` on a fresh smoke-produced run dir → exit 0.

---

# Stream S2 — Bootstrap & Packaging

Goal: a stranger (or a fresh agent) can clone, install, verify, and start —
without archaeology.

Owner zone: root `requirements.txt`(new), `.env.example`, `README.md`,
`AGENTS.md`(new), `CLAUDE.md`; `tools/preflight.py`(new);
`tests/test_preflight.py`(new); `docs/INDEX.md`; new docs under
`docs/setup/`.

## S2 tasks

1. **Dependency manifest + preflight doctor.**
   - `requirements.txt`: pin the top-level Python deps the code actually
     imports (derive by scanning imports across `video_pipeline_core/`,
     `tools/`, `video_tools.py`, `tests/`; verify each against the miniconda
     env versions). Node-side deps documented, not pinned here.
   - `tools/preflight.py` (standalone, NO video_tools.py edits — that file
     belongs to another stream): checks python version, importability of
     required modules, ffmpeg on PATH + version, node on PATH, presence (not
     values) of API keys named in `.env.example`, and writes a JSON +
     human-readable capability summary. Exit 0 with warnings allowed;
     `--strict` exits 1 on missing hard requirements.
   - `tests/test_preflight.py` with mocked environments.
   Commit: `Add dependency manifest and preflight doctor`.
2. **Setup guide + entry files.**
   - `docs/setup/setup-and-first-run.md`: Windows-first install steps
     (miniconda, ffmpeg, node), `.env` setup, then VERIFICATION =
     `python tools/preflight.py` + the two e2e-smoke commands + full suite.
     First-run walkthrough: point your coding agent at
     `docs/START_HERE_VIDEO_PIPELINE.md` and ask for a video.
   - `.env.example` completeness pass: grep the codebase for
     `os.environ`/`getenv` keys; every key referenced in code appears with a
     comment; no secrets values.
   - `AGENTS.md` (root, tiny, OpenMontage-style): "Read
     docs/START_HERE_VIDEO_PIPELINE.md before acting. All instructions live
     there." `CLAUDE.md`: only add a pointer line to the setup guide if it
     lacks one; change nothing else.
   - `README.md` rewrite: what this is (agent-first video pipeline), quick
     start (5 lines), verification commands, storybook section as a
     placeholder skeleton (owner will fill demo videos/costs), pointer to
     START_HERE for agents. `docs/INDEX.md` rows for the new docs.
   Commit: `Add setup guide, agents entry, and README quick start`.
3. **Distribution manifest (doc only).**
   `docs/setup/distribution-manifest.md`: what a release EXCLUDES
   (`runs/`, `reference repo/`, `.tmp/`, `graphify-out/`, `archive/`,
   `docs/archive/`, local env files) and what it must include; note that the
   packaging mechanism itself (pip/zip/template repo) is a pending owner
   decision. LICENSE: do NOT create or choose one — record in your report
   that license selection is an owner decision.
   Commit: `Add distribution manifest`.

Acceptance: full suite green per commit; `python tools/preflight.py` exit 0
on this machine; every command written into the setup guide has been
actually executed by you and its real output quoted in the report.

---

# Stream S3 — Legacy Archival & Facade Hygiene

Goal: what a newcomer sees is only the living product.

Owner zone: `dashboard/**`, `tools/dashboard_server.py`,
`tools/workbench_server.py`, `tests/test_dashboard_server.py`,
`tests/dashboard_spa_render_smoke.mjs`, `RUNBOOK.md`, root debris list
below.

Guards you must keep green (run after every commit):
`node tools\workbench_browser_layout_smoke.mjs --artifact-root .tmp\wb_accept_fixture`
(set `PYTHON` env to miniconda python) and
`python tools\workbench_frontend_smoke.py --artifact-root .tmp\wb_accept_fixture --exercise-replace`.

## S3 tasks

1. **Legacy dashboard page archival.** Move to `dashboard/archive/`:
   `dashboard_v1.html/.css/.js`, `design_mockup.html`,
   `style_a_studio_dark.html`, `style_b_soft_light.html`,
   `style_c_vivid_sidebar.html`, `material_map_canvas.html`,
   `material_map_canvas_3d.html`, `material_map_canvas_physics.html`,
   `route_review_mockup.html`. KEEP LIVE: `material_map_review.*`
   (pipeline-wired), `workbench_first_template.html` (design reference,
   spec-linked), everything under `workbench_native/` and `src/`.
   Update `tools/dashboard_server.py` routes and
   `tests/test_dashboard_server.py` assertions accordingly — archived pages
   return 404 or are served from an explicit `/archive/` route (your call;
   record it). `dashboard/README.md` updated.
   Commit: `Archive legacy dashboard pages`.
2. **Root debris audit (move-only, conservative).** For each of:
   `bgm.webm`, `mock_script.json`, `mock_script_exhausted.json`,
   `show_vlm_log.py`, `run_with_ollama.py`, `run_with_ollama.sh`,
   `setup_mock.py`, `HANDOFF_CURRENT.md`, `roadmap.md` —
   `git grep` references; unreferenced (or referenced only by archived docs)
   → `git mv` to `archive/root-2026-07/`. Referenced by live code/tests/docs
   → leave in place and list as candidate with the referencing files.
   NEVER touch: `video_pipeline.py`, `runtime.py`, `video_tools.py`,
   `CLAUDE.md`, `CODEX.md`, `README.md`, `THIRD_PARTY_NOTICES.md`, `.env*`.
   Commit: `Archive unreferenced root files`.
3. **RUNBOOK refresh (execute-then-write).** Every command currently in
   `RUNBOOK.md` gets actually run; dead ones fixed or removed; add sections
   for: single-document workbench home (`tools/dashboard_server.py` +
   browser URL), both e2e-smoke cases, `registry-audit`, the two frontend
   guards, and the miniconda rule. You may REFERENCE S2's
   `tools/preflight.py` by name in prose (do not depend on its existence for
   your acceptance). Every command in the final RUNBOOK must have been
   executed by you with real output.
   Commit: `Refresh runbook against live commands`.

Acceptance: both guards + full suite green per commit; a fresh browser load
of `/` still shows the workbench with zero console errors after Task 1.

---

## Order of dispatch

All three can start simultaneously in fresh sessions. No prior warm-up run
is required; the codebase-memory index is already built and optional. If
only sequencing matters to the owner: S1 is the longest — start it first.
