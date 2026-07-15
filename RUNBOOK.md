<!-- OPERATIONAL_ENTRY: RUNBOOK -->
<!-- CURRENT_HANDOFF_POINTER: HANDOFF_CURRENT.md -->

# Hermes Video Pipeline Runbook

Date: 2026-07-03
Status: Windows-local operator runbook

Run commands from `C:\Users\user\Desktop\video_pipeline`. Use the miniconda
Python explicitly for Python commands; do not rely on whichever `python` appears
first on PATH.

## Single Operator Entry

`RUNBOOK.md` is the sole operational entry surface. Read
`docs/START_HERE_VIDEO_PIPELINE.md` for route vocabulary and conceptual
orientation, then use this runbook for operator routing and
`HANDOFF_CURRENT.md` for the current bounded work order and machine-readable
state pointer.

The active branch contract registry is `docs/branch-contract-registry.json`; it
defines each branch owner, handoff artifacts, forbidden actions, and return
route. Stage 0-10 alignment construction links back to
`docs/construction-guides/stage0-10-route-alignment-plan.md`.

## Current Work Pointer

For any live campaign, resume, or stop/go decision, read `HANDOFF_CURRENT.md`.
That handoff document names the active work order, the runtime state artifact,
bounded next actions, and explicit do-not-do items. Historical campaign links
may remain elsewhere in the docs, but this runbook stays stable and does not
carry live state tokens or current campaign payloads.

## Task-to-Document Router

Document roles:

| Need | Read | Why |
|---|---|---|
| Concept orientation | `docs/START_HERE_VIDEO_PIPELINE.md` | Route vocabulary and Rule Zero. |
| Decision tree | `docs/pipeline-decision-tree.md` | Branch owner, stop gate, and return route. |
| Stage/tool map | `docs/video-pipeline-operating-map.md` | Stage-level tools and artifacts. |
| Skill/tool ownership | `docs/stage-tool-simplification.md` | Tool ownership and entry precedence. |
| Route-specific operator runbooks | `docs/runbooks/` | Focused happy-path commands and current route state. |
| Non-UI consolidation | `docs/construction-guides/repo-consolidation-non-ui-plan.md` | Non-UI route consolidation. |
| Historical archive | `docs/archive/` | History only, unless linked from a current doc. |

## Semantic Entry Router

Stage 0 package: `project_brief.json`, `interaction_log.md`, and
`video_intent.json`. If the user gives a target duration, `target_length` must
be captured in Stage 0 instead of being guessed later. If
`required_followup_questions` is non-empty, stop and ask before entering branch
work.

User says routing stays semantic: a fuzzy whole-video request starts at Stage 0;
footage/photos start material-first; draft patch requests start
Workbench/Brownfield; bounded music intent starts Soundtrack Arranger; bounded
effect intent starts Effect Factory.

Entry skill selection follows the same router: whole-video requests use the
video pipeline route skill first, material-first work uses Material Map through
the route, and draft edits use the Workbench/Brownfield path.

## Stage And Editing Loop Authority

**Stage owns lifecycle; Loop owns editing method.** The Stage 0-10 spine is the
only authority for the current cursor, BUILD eligibility, canonical render,
Verify, Brownfield return, and Delivery. `editing-loop-director` is a method
overlay used by the orchestrating agent after the required upstream truth is
available; it never advances the Stage cursor or promotes delivery by itself.

| Stage hook | Editing method |
|---|---|
| S0-S2 | Fix intent, story spine, and director/segment contract before whole-video composition. |
| S3 | Use L0 for material immersion and evidence-backed selects. |
| S4 | Use L0 findings at the coverage/decision gate. |
| S5 | Compile L1 picture, L2 effects, L3 audio, and L4 text decisions without claiming a canonical render. |
| S6 | The registered factory performs the only canonical render. |
| S7-S8 | Use L5 for objective Verify plus agent/human review. |
| S9 | Route a finding to its targeted L0-L4 method, then return through S5-S7. |
| S10 | Delivery remains an owner and delivery-gate decision. |

Stage 6 is the only canonical render owner. S6 consumes the compiled picture,
effects, audio, and text decisions; an editing loop may create bounded previews
for judgment, but it cannot promote them to the canonical candidate.

When a reviewed candidate needs an interactive high-quality effect/music pass,
use `skills/capcut-assisted-finishing.md` as the optional Stage 6 backend or
Stage 9 finishing route. It must return the exported candidate to Stage 7
Verify; CapCut does not own story, picture, text, legal approval, or delivery.

`dispatch-capabilities --loop L0..L5` is a method lookup, not a Stage router.
Capabilities with no Editing Loop role keep an empty `loops` list and remain
discoverable by capability ID, owner, or query.

Router table fields are: User says, Entry skill, First safe action, and
Stop condition.

Entry Precedence:

- Resume existing run state before starting new branch work.
- Whole-video requests win over side-branch keywords and enter Stage 0 before
  side branches.
- Side-branch keywords are child intents. A bounded music/song/BGM intent may
  route to Soundtrack Arranger after the route context is known.
- Subtitle or volume repair is not Soundtrack Arranger. A whole-video subtitle
  intent is a Stage 0 child intent; subtitle repair on an existing draft belongs
  to Brownfield/Workbench or Subtitle Director.
  Exact route phrase: whole-video subtitle intent.
- Existing draft edits go through Workbench/Brownfield.
- Generated candidate fallback is not the first move.

Examples: "help me cut a video" starts Stage 0; "I already have footage" starts
material-first inspection; "I need an opening effect" starts bounded Effect
Factory routing only when it is not a whole-video request; "export the final
video" starts delivery-gate inspection.
Exact user phrase: export the final video.

`route_judgment.json is not enough`: if `pipeline_home.py returns unknown`, the
run has not entered the pipeline. For footage-backed story requests,
`material-first remains the route`; the story skeleton follows material facts.
Material Delta is a gate before BUILD/render.

Use the Decision tree before work that could cross branch boundaries. Material
first work goes through Material Map and material delta. Existing draft edits go
through Workbench/Brownfield and write draft artifacts such as
`workbench_revision_request.json`; they do not overwrite canonical truth.

Dialogue or single-source highlight work is speech-first highlight work: build
source understanding, require correct subtitle evidence, preserve each
complete sentence boundary, and persist `source-dialogue-script` /
`dialogue_edit_script.json` before treating the cut as reviewable.

Soundtrack work belongs to `soundtrack-arranger` before Audio Director. Its
handoff artifacts are `soundtrack_plan.json`, `music_source_candidates.json`,
`sound_license_manifest.json`, and `audio_director_handoff.json`. Jamendo and
Pixabay are optional API layer sources; famous or unlicensed music remains
`reference_only` unless a license is proven. Default policy is
`HERMES_ALLOW_UNLICENSED_MUSIC=false`.

Effect Factory acceptance vocabulary: `tools\effect_factory_route_acceptance.py`,
`effect_factory_route_acceptance_report.json`,
`visual_technique_plan.confirmed.json`, `effect_capability_review.json`,
`remotion_prompt_pack.json`, `remotion_worker_outputs.json`,
`remotion_effect_review.json`, `effect_handoff.json`,
`ready_for_human_effect_review_or_pipeline_promotion`, and
`cursor=effect_factory_route_acceptance`. The phrase
`pipeline_home.py --run RUN_DIR --json` is a documented route-contract marker
from the broader docs, not a command example in this refreshed runbook.
`final.mp4 must remain absent` for these no-render acceptance paths.

Material-first verified preview vocabulary:
`package_verified_preview.py`, `verified_preview_review_decision.py`,
`promote_verified_preview.py`, and `workbench_revision_request.json`.
`tools\run_artifact_index.py` remains part of the non-UI consolidation map.

Material-first happy path operator runbook:
`docs/runbooks/material-first-happy-path.md`. Use it for the current
self-contained golden path replay and route state. Today that path is verified
through `render_handoff.json` and `ready_for_render`; it does not claim
`final.mp4` or complete-video delivery.

## Miniconda Rule

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" --version
```

Expected on this machine: `Python 3.10.16`.

## Single-Document Workbench Home

The merged Dashboard server serves the native Workbench at `/` and `/workbench`.
Dashboard review routes remain available under `/dashboard`, `/material-map`,
`/timeline`, `/verify`, and `/artifacts`.

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" tools\dashboard_server.py --artifact-root .tmp\wb_accept_fixture --port 8765
```

Open:

```text
http://localhost:8765/
http://localhost:8765/workbench
```

The home page should show the native Workbench monitor, playback controls, and
four timeline lanes. Browser console errors should be zero.

## Test Tiers

The large unittest suite stays as the final regression gate. Do not collapse it
into the development loop. Use tiered checks instead:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py test-tiers
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py test-tiers --tier dev
```

Use `dev` for routine command-surface and route-contract edits, then run the
owner-specific focused module for the code you touched. Use
`work-order-acceptance` before reviewer handoff after focused tests pass:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py test-tiers --tier work-order-acceptance
```

Run `full` before broad/shared behavior commits, final supervisor reports, and
CI-style signoff:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py test-tiers --tier full
```

## Workbench Tier

Use the focused Workbench tier before and after Dashboard/Workbench frontend
changes.

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" tools\test_tiers.py --tier workbench
```

This tier covers the SPA render/i18n smokes plus native Workbench API, core, and
material helper smokes. The tier runner isolates child-process temp state under
`.tmp/test-temp`.

## S3 Frontend Guards

Run both guards for S3 facade or archive work.

```powershell
$env:PYTHON="$env:USERPROFILE\miniconda3\python.exe"; node tools\workbench_browser_layout_smoke.mjs --artifact-root .tmp\wb_accept_fixture
```

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" tools\workbench_frontend_smoke.py --artifact-root .tmp\wb_accept_fixture --exercise-replace
```

`workbench_browser_layout_smoke.mjs` checks a real browser viewport for the
protected monitor, playback controls, and four lanes. The frontend smoke checks
draft writes while preserving canonical artifacts.

## Dashboard Smoke

```powershell
node tests\dashboard_spa_render_smoke.mjs
```

## Registry And E2E Smokes

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py registry-audit --json
```

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py e2e-smoke --case stock_story
```

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py e2e-smoke --case single_long_highlight
```

`registry-audit` should report zero findings. The two e2e smoke cases should
exit 0.

## Full Regression

Run the full suite before committing.

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest discover -s tests
```

If a failure looks like a temp-file or port collision, rerun the failing module
focused, then rerun the full suite once before treating it as real.

Focused example used for a confirmed non-S3 failure:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest tests.test_skill_tool_contracts -v
```

## S3 Focused Test

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest tests.test_dashboard_server -v
```

## Legacy Dashboard Archive

Legacy dashboard prototypes live under `dashboard/archive/` and are served only
through explicit `/archive/<file>` URLs. The live root-level compatibility
routes such as `/dashboard_v1.html`, `/dashboard/legacy`, `/3d`, and `/physics`
return 404 by design.
