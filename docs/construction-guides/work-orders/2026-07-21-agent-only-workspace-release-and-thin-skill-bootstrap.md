<!-- DOCUMENT_ROLE: WORK_ORDER -->
<!-- STATUS: READY_FOR_WORKER -->

# Work Order — Agent-only Workspace Release and Thin Skill Bootstrap

Date: 2026-07-21

## Goal and source

Prepare the repository as a private **Agent-only Technical Preview v1** that a
capable coding agent can enter from one obvious surface, bootstrap on a clean
Windows workspace, and verify without relying on this machine's ignored
`.tmp` state.

Also produce a thin installable Codex skill bundle that locates and enters the
workspace runtime on demand. The skill is a launcher and method router; the
repository remains the runtime, truth store, tool registry, and test surface.

This order follows the 2026-07-21 integrator audit:

- registry audit: 8 branches, 17 stages, 0 findings;
- Codebase Memory index: 15,638 nodes / 48,820 edges, ready;
- tracked tree clean, but local `master` is 27 commits ahead of origin;
- `python tools/preflight.py --strict` currently fails before argument parsing
  with `ModuleNotFoundError: video_pipeline_core`;
- `HANDOFF_CURRENT.md` points into excluded `.tmp` Canon 67 state;
- source-only packaging and license choice remain incomplete;
- recent Reviewer production commits have focused evidence but no current-HEAD
  full-suite evidence.

## Product decision

The release shape is deliberately hybrid:

```text
thin installable skill
  -> locate VIDEO_PIPELINE_HOME or current video-pipeline workspace
  -> read RUNBOOK.md
  -> invoke repo-local skills and registered tools on demand
  -> write per-project artifacts outside the installed skill
```

The thin skill must not contain copies of `video_pipeline_core/**`, `tools/**`,
route registries, Stage logic, or live project state. Do not convert the
repository into one giant skill and do not create a plugin or MCP server in
this order.

The successful bounded-finishing operating rule is now explicit: Pipeline
artifacts lock intent, protected truth, and acceptance boundaries; inside a
bounded Brownfield/finishing change, the orchestrating agent may choose any
existing registered capability that respects those boundaries. This is not
permission to hand-stitch a new whole-video route or bypass canonical BUILD.

## Non-goals

- No GUI/Workbench completion or redesign.
- No new Stage, route, orchestrator, adapter, renderer, reviewer, or registry.
- No CapCut/OpenMontage implementation change.
- No deletion or migration of historical docs in this order.
- No public release, push, package publication, or global skill installation.
- No license selection; absence of a license must remain explicit.
- No mutation of source media or ignored candidate artifacts.
- No claim that creative quality is automatic or final delivery is certified.

## Owner zone (exhaustive)

Bootstrap and release implementation:

- `tools/preflight.py`
- `tools/package_agent_only_release.py` (new)
- `tests/test_preflight.py`
- `tests/test_agent_only_release.py` (new)

Entry, distribution, and current-state surfaces:

- `README.md`
- `RUNBOOK.md`
- `HANDOFF_CURRENT.md`
- `docs/START_HERE_VIDEO_PIPELINE.md`
- `docs/setup/setup-and-first-run.md`
- `docs/setup/distribution-manifest.md`
- `docs/pilots/2026-07-21-science-outing-second-case-closure.md` (new)
- `skills/video-pipeline.md`
- `tests/test_pipeline_skill_boundaries.py`

Thin skill bundle:

- `distribution/agent-skill/video-pipeline/**` (new)
- `tests/test_agent_only_skill_bundle.py` (new)

Final worker evidence only:

- `.tmp/agent_only_release_v1/**`

Dispatch authority:

- `docs/construction-guides/work-orders/2026-07-21-agent-only-workspace-release-and-thin-skill-bootstrap.md`
  may be staged and committed byte-for-byte before P0, but must not be edited by
  the worker.

All other tracked paths are forbidden for modification. Do not create an
execution companion; this is a bounded source/distribution task, not a video
campaign run.

## Ordered pieces

### P0 — freeze and RED evidence

Record pre-work HEAD, branch, `git status --short`, and SHA-256 for every
existing owner-zone file. Preserve these in
`.tmp/agent_only_release_v1/preflight/`.

Capture RED evidence for both observed distribution failures:

1. direct execution of `tools/preflight.py` cannot import the repo package;
2. a source-only release handoff cannot reference `.tmp`, `runs`, an absolute
   local path, or a missing authoritative artifact.

### P1 — executable bootstrap

Repair `tools/preflight.py` so the documented direct invocation works from the
repository root without requiring `PYTHONPATH`. Preserve module import use in
tests and existing strict/lenient semantics.

The clean-clone base command is lenient:

```powershell
C:\Users\user\miniconda3\python.exe tools\preflight.py
```

Missing optional provider credentials may warn but must not fail the base
Agent-only bootstrap. `--strict` remains available for operators who require
all configured provider capabilities.

### P2 — one real entry and an IDLE release handoff

Align the documents so all paths state the same order:

1. `RUNBOOK.md` is the sole operational entry.
2. `HANDOFF_CURRENT.md` is read second for live or IDLE state.
3. `docs/START_HERE_VIDEO_PIPELINE.md` is optional orientation loaded only
   when the route vocabulary is needed.
4. Route-specific docs and skills are loaded on demand.

Update the source handoff to an IDLE Agent-only Technical Preview state. It
must contain no authoritative pointer into `.tmp`, `runs`, local absolute
paths, or absent artifacts. Preserve Canon 67 and the science-outing trial as
durable historical evidence links, not active campaigns.

Write the compact science-outing closure note from already observed evidence:

- Variant A selected after A/B paper edit;
- final accepted internal candidate duration 75 seconds;
- accepted candidate SHA-256
  `ec9e992da35d3d9417fa07312adacf902753308404342bc16ac7c88cf1145430`;
- original ambience removed, existing sourced BGM retained;
- bounded ending text revision only;
- Rendered QA and Final Verify passed;
- owner accepted the simple style;
- no final-delivery or public music-license claim.

Do not require the ignored media file to exist in a distributed clone.

### P3 — bounded Agent freedom without a second route

Update `RUNBOOK.md` and `skills/video-pipeline.md` with one concise rule:

- fuzzy/new whole-video work still enters Stage 0 and canonical BUILD;
- an existing reviewed candidate with explicit locked and dirty layers may use
  the Brownfield/finishing loop;
- the orchestrating agent may select existing registered capabilities inside
  that bounded contract;
- only dirty layers rerun;
- the result must return to Verify and Owner verdict;
- no direct whole-video hand stitching, protected-truth mutation, or delivery
  promotion is allowed.

Pin this distinction in `tests/test_pipeline_skill_boundaries.py`. Do not add a
new stage, capability ID, or dispatch layer.

### P4 — reproducible private preview package

Add `tools/package_agent_only_release.py` with a deterministic source-directory
output and optional zip output. It must:

- package tracked release content according to
  `docs/setup/distribution-manifest.md`;
- exclude `.git`, `.tmp`, `runs`, `reference repo`, `archive`,
  `docs/archive`, virtual environments, caches, `.env`, generated media, and
  secrets;
- include tests required for release verification;
- include an IDLE `HANDOFF_CURRENT.md`;
- emit `release_manifest.json` with source HEAD, included file hashes,
  exclusions, release status, platform assumptions, and
  `license_status: owner_decision_pending`;
- refuse to package an active handoff that depends on an excluded artifact;
- never install, publish, push, or overwrite an existing non-empty output.

The tool may package the current working tree only for tests. The final
acceptance package must be generated from a clean committed HEAD.

### P5 — thin installable skill bundle

Create `distribution/agent-skill/video-pipeline/` using the Skill Creator
initializer, then reduce it to:

- `SKILL.md`;
- `agents/openai.yaml`.

The skill must be under 250 lines and contain only:

1. trigger description for producing, editing, reviewing, or repairing video;
2. workspace discovery: current directory first, then
   `VIDEO_PIPELINE_HOME`;
3. fail-closed behavior when no workspace is found;
4. `RUNBOOK.md` as the only first read;
5. routing to repo-local skills/tools after workspace discovery;
6. the bounded Agent-freedom rule from P3;
7. no copied Stage map, registry, schemas, historical evidence, binaries, or
   project state.

Do not install the skill globally. Validate the bundle using the Skill Creator
`quick_validate.py` and a repository test that confirms it does not contain
duplicated runtime files or local absolute paths.

### P6 — clean-package forward acceptance

Generate the final package only after P0-P5 focused checks pass and the source
changes are committed. Hydrate a new sibling directory from that package,
without copying `.env`, `.tmp`, `runs`, or local caches. In the sibling:

1. confirm `RUNBOOK.md -> HANDOFF_CURRENT.md` resolves to IDLE;
2. run lenient preflight by the documented command;
3. run registry and interface audits;
4. run both existing E2E smokes;
5. validate the thin skill bundle;
6. prove no packaged text file contains this source workspace's absolute path;
7. prove excluded roots and secrets are absent.

The skill forward test is navigation-only: give a fresh agent the packaged
skill and a request to locate the runtime and state the first safe action. It
must not render media, write a project, or receive the expected answer.

### P7 — final regression and evidence

Run the full suite exactly once after the clean-package acceptance is green.
If it fails, follow the repository's focused-then-one-rerun policy; do not hide
or relabel failures.

Create `.tmp/agent_only_release_v1/final/worker_report.md` and a machine-readable
`acceptance.json`. Do not push or publish.

## Acceptance commands

Focused bootstrap and release:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_preflight tests.test_agent_only_release tests.test_agent_only_skill_bundle tests.test_pipeline_skill_boundaries -v
```

Expected exit code: `0`.

Direct entry commands:

```powershell
C:\Users\user\miniconda3\python.exe tools\preflight.py
C:\Users\user\miniconda3\python.exe video_tools.py registry-audit --json
C:\Users\user\miniconda3\python.exe video_tools.py interface-audit
```

Expected exit code: `0` for all three.

Clean-package commands:

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py e2e-smoke --case stock_story
C:\Users\user\miniconda3\python.exe video_tools.py e2e-smoke --case single_long_highlight
```

Expected exit code: `0` in the hydrated package.

Final regression:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests
git diff --check
```

Expected exit code: `0` for both. Full suite should run once at P7 unless the
documented repository retry rule is triggered.

## Commit boundaries

0. This work order byte-for-byte, if it is still untracked at dispatch.
1. Bootstrap/entry semantics and tests.
2. Package tool/distribution contract and tests.
3. Thin skill bundle and validation tests.
4. Final IDLE handoff and durable second-case note, if not already included in
   the first commit.

Each commit must contain only owner-zone files. The final tracked tree must be
clean. Do not push.

## Stop-loss

- Any required edit outside the owner zone: STRUCTURAL STOP.
- Any need for a new Stage, route, registry, executor, plugin, MCP server, or
  duplicated runtime inside the skill: STRUCTURAL STOP.
- A license choice, public publication, global install, push, or destructive
  cleanup requires Owner direction and must not be inferred.
- The same failure class after one local correction: stop at the last green
  commit and report the structural cause.
- If the clean package requires `.tmp`, `.env`, an absolute source path, or an
  active campaign artifact, fail closed; do not add an allowlist.
- Do not relax tests or reduce the package checks to make acceptance pass.

## Required report

Report:

- final state:
  `WAITING_INTEGRATOR_AGENT_ONLY_TECHNICAL_PREVIEW_V1_REVIEW` or the exact stop
  state;
- commits and exact changed files;
- RED/GREEN commands, exit codes, focused/full test counts;
- package directory/zip paths, SHA-256, file count, and release-manifest hash;
- hydrated sibling path and acceptance results;
- thin skill path and `quick_validate.py` result;
- preflight, registry, interface, E2E, absolute-path, secret/exclusion results;
- deviations, skips, blockers, and exact pre/post git status;
- `human_creative_approval=false` and `final_delivery_claimed=false` for the
  release process.
