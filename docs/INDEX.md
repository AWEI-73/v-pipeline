<!-- DOCUMENT_ROLE: MAP -->

# Docs Index —canonical map (2026-06-25)

One page that says what is current and what is historical, so old/new no longer mix.

## Document Map

This file is a document map, not the operator entrypoint.

Single operator entry:

- `RUNBOOK.md` -- start here for all operational work.

Top-level project references:

- `README.md` -- what this project is.
- `roadmap.md` -- optional owner-facing product direction summary; not agent
  run state or execution authority.
- `HANDOFF_CURRENT.md` -- clean resume anchor for the next agent.
- `docs/hermes-v-pipeline-honest-capability-map.md` -- evidence-backed snapshot
  of Hermes architecture, real capabilities, maturity, limits, and technical
  debt; descriptive only, not a route authority.

Current document layers:

| Layer | File or folder | Purpose |
|---|---|---|
| Single operator entry | `RUNBOOK.md` | What to do next, what to read, which skill/tool to use, and when to stop. |
| Concept orientation | `docs/START_HERE_VIDEO_PIPELINE.md` | Overall route vocabulary and conceptual map. |
| Decision tree | `docs/pipeline-decision-tree.md` | On-demand route diagnosis: branch choice, insertion points, stop gates, and return route. Do not preload. |
| Branch contracts | `docs/branch-contract-registry.md`, `docs/branch-contract-registry.json` | Human and machine-readable branch ownership, allowed artifacts, stop gates, forbidden writes, and return routes. |
| Stage/tool map | `docs/video-pipeline-operating-map.md` | On-demand Stage-to-skill/tool/artifact lookup. Do not preload. |
| Closure hygiene | `tools/route_closure_integrity.py`, `tools/doc_reference_hygiene.py`, `tools/factory_improvement_loop.py` | Machine checks for route registration, top-level docs/reference classification, and structured improvement-loop backlog items. |
| Canonical route | `docs/canonical-video-pipeline-route.md` | Official stage names, route semantics, and delivery requirements. |
| Skill/tool ownership | `docs/stage-tool-simplification.md` | Skill ownership of Python tools and audit command. |
| API contract | `docs/api-surface-map.md` | API Surface Manifest contract, allowed/forbidden writes, and endpoint audit rules. |
| Interface contracts | `docs/interface-contracts/README.md` | Pipeline branch interface API dictionary, product artifact dictionary, audit, and soft discovery instructions. |
| Bootstrap setup | `docs/setup/setup-and-first-run.md` | Windows-first install, env setup, verification, and first agent-run walkthrough. |
| Distribution | `docs/setup/distribution-manifest.md` | Release include/exclude manifest plus pending packaging and license decisions. |
| Code memory helper | `docs/codebase-memory-mcp-handoff.md` | Optional low-token local code graph for new-session handoff and code review; not a route truth source. |
| Agent ops | `docs/agent-ops/work-order-sop.md`, `docs/agent-ops/orchestrator-system-prompt.md` | Work-order operating system for multi-agent construction, and the orchestrator system prompt that drives it. |
| Branch routes | `docs/material-map-lifecycle.md`, `docs/effect-factory-route.md`, `docs/soundtrack-arranger-route.md`, `docs/upstream-story-route.md`, `docs/workbench-dashboard-integration.md` | Detailed branch-specific behavior. |
| Construction guides | `docs/construction-guides/` | Implementation plans and migration notes; use only when changing that area. |
| Generated maps | `docs/generated/` | Local machine-generated route maps and audits. Ignored by Git; regenerate when needed. |
| Historical archive | `docs/archive/` | Decision history and old roadmap evidence; not a current source unless linked by a current doc. |

## Retained history boundary

The following folders are intentionally retained for reproducibility, but are
not live route authority:

- `docs/construction-guides/work-orders/` — work-order and execution history;
  keep it searchable and do not treat an old stop state as current status.
- `docs/decisions/`, `docs/pilots/`, and `docs/superpowers/` — design decisions,
  pilot evidence, and implementation plans. A current route must be anchored by
  `RUNBOOK.md`, `HANDOFF_CURRENT.md`, or a current contract before using them.
- `docs/archive/` — superseded or pruned material. The archive index explains
  why an item moved and what, if anything, replaced it.

Generated maps under `docs/generated/` are machine-owned and ignored by Git;
they are outputs, not navigation entries.

## Historical Continuation Links

- Current Editing Loop continuation (historical campaign map link only):
  `docs/construction-guides/work-orders/2026-07-11-editing-loop-anchor-health-integrated-longform-campaign.md`.
  Keep it as map context, not a current authority surface; use the RUNBOOK →
  HANDOFF chain for live work and stop at the declared owner gate.

## Entry Notes

1. `RUNBOOK.md` —sole operational entry and task router.
2. `HANDOFF_CURRENT.md` —current machine-readable resume anchor.
3. The relevant skill/contract selected by the runbook.
4. `README.md`, `roadmap.md`, and this index are optional human orientation;
   they are not agent boot order or live run authority.

## Editorial "soul" layer (front of pipeline)

- Skill: `skills/video-intent-planner.md` -- VIP0 Stage 0 route decision layer:
  writes `video_intent.json`, asks route-changing follow-up questions, and hands
  off to material-map lifecycle or upstream story route without starting
  type-specific templates.

- `docs/story-soul-blueprint-skills.md` —planned upstream creative skill layer:
  story world, narrative device, screenplay beats, director shot/material prompt
  compiler. This is the next consolidation target before more runtime features.
- Skill: `skills/story-soul-blueprint.md` —SSB1 executable baseline that
  compiles project briefs into story_world, creative_concept, screenplay_beats,
  director_shot_plan, material_needs, generation_manifest, and review checklist.
- Skill: `skills/material-generation-fallback.md` —MGF1 rescue layer that turns
  fresh `material_delta` missing/thin needs into provider-neutral generation jobs;
  generated assets return through material-map review as candidates.
- Skill: `skills/curator.md` -- material curator support skill. It adds
  scene-level visual family, angle/scale, duplicate/reject, and diversity review
  evidence before material delta and rough-cut decisions.
- Skill: `skills/generated-material-producer.md` —executes MGF1 jobs into
  generated files, manifests, candidate material maps, quality review, and
  explicit candidate promotion review.
- Skill: `skills/shooting-brief.md` -- material gap brief route. It converts
  `material_delta.json` missing/thin needs into `material_gap_brief.json`,
  `shooting_brief.md`, generated-material jobs, stock retrieval jobs, rewrite
  tasks, or waiver tasks before material-map re-review.
- Harness: `tools/generated_material_flow_acceptance.py` —replays two
  generated comic-style cases from empty material through candidate material maps
  and quality review.
- Harness: `tools/story_to_generated_material_e2e.py` —runs project brief
  through SSB1, generated fallback, generated material production, explicit
  review, and fresh delta coverage.
- `docs/editorial-layer.md` —**read first**; consolidated conceptual map.
- `docs/narrative-blueprint-spec.md` —WHY: prose thesis + ordered beats (gate).
- `docs/editing-intent-sequence-grammar-spec.md` —HOW-structure: cut/hold reasons, shot_slots.
- `docs/material-treatment-grammar-spec.md` —HOW-material: content_pattern —treatment —count —lanes.
- `docs/imagery-to-edit-lexicon-spec.md` —the deterministic imagery→enum translation table.
- Skill: `skills/blueprint-interview.md` (elicit soulful blueprint).
- Code: `video_pipeline_core/blueprint_to_contract.py` (compile decisions.json —contract);
  CLI `video_tools.py blueprint-to-contract`. Gold example: `examples/blueprint_gold_66/`.

## Build / runtime / infra (current)

- `docs/START_HERE_VIDEO_PIPELINE.md` -- canonical operator entrypoint for
  agents and humans: which document to read, which route to choose, and what not
  to treat as truth.
- `docs/pipeline-decision-tree.md` -- operator decision tree for the main
  Stage 0-10 route, Material Map branch, Effect Factory branch, Audio
  Communication branch, and Review / Verify / Delivery Gate cross-cutting
  branch.
- `docs/video-pipeline-end-to-end-line.md` -- one-page narrative line from
  Video Intent Planner through material truth, BUILD, verify, Workbench /
  Brownfield return loops, and delivery.
- `docs/canonical-video-pipeline-route.md` —canonical end-to-end route map:
  stable stage order, skill-to-tool mapping, artifact ownership, gates, legacy
  node aliases, and template-route plan. Read this before changing flow or node
  names.
- `docs/upstream-story-route.md` -- upstream creative route from Role /
  Literary Lens through Blueprint Interview, Story Soul Package, Director Shot
  Plan, Contract Compile, and Material-Ready Handoff.
- `docs/video-pipeline-operating-map.md` -- full operator manual linking every
  stable stage to skills, Python/JS tools, artifacts, gates, and return routes.
- `docs/construction-guides/stage0-10-route-alignment-plan.md` -- active
  construction guide for keeping the Stage 0-10 main spine, Material Map,
  Soundtrack/Audio, Effect Factory, and Subtitle/Voiceover child contracts
  aligned without creating competing routes.
- `docs/stage-tool-simplification.md` -- compact skill/tool contract map:
  stage-to-skill ownership, Python tool visibility, stop/pass rules, and the
  audit command that checks `skills/*.md` tool contracts against `tools/*.py`.
- `docs/route-orchestrator-harness.md` -- runner-neutral multi-agent task
  packet and fail-closed acceptance harness (`route-task-next`,
  `route-task-accept`, `route-orchestrator-report`).
- `docs/route-agent-runner-protocol.md` -- worker-facing protocol and prompt
  template for Codex/Claude/Gemini/human agents consuming route task packets.
- `docs/artifact-reviewer-map.md` -- lightweight reviewer policy (`light`,
  `normal`, `deep`) that keeps creative review separate from technical verify.
- `docs/archive/decisions/2026-06-20-canonical-route-solidification-review.md` --
  acceptance report for the route map, operator skill, static harness, and
  subagent cold-read review.
- `docs/archive/decisions/2026-06-20-upstream-story-route-consolidation.md` --
  decision record for the Role/Literary Lens through Material-Ready Handoff
  upstream line and subagent cold-start validation.
- `docs/archive/decisions/2026-06-20-reviewer-registry-and-eval-principles.md` --
  deterministic reviewer role registry, policy packet, and eval principle
  contract.
- `docs/archive/decisions/2026-06-20-reviewer-flow-acceptance.md` -- deterministic
  reviewer policy smoke harness for normal route, upstream story, and
  effects/brownfield reviewer coverage.
- `docs/archive/decisions/2026-06-20-soul-passthrough-build-ranking.md` -- story-soul
  passthrough into contract, soft BUILD ranking consumption, and bad-window
  least-bad fallback boundary.
- `docs/archive/decisions/2026-06-21-vip0-video-intent-planner-artifact.md` --
  Stage 0 `video_intent.json` ownership: `input_state`, `entry_path`,
  material-first, structure-first, needs-context, legacy compatibility, and
  generated-material fallback boundaries.
- `docs/material-map-lifecycle.md` —canonical summary of the completed
  M6 material-map lifecycle: needs, satisfies edges, delta, revision, lifecycle
  stage machine, build handoff, and current boundaries.
- `docs/effect-factory-route.md` -- designed-effects side branch. The main
  route calls it when brownfield/material-first or greenfield/structure-first
  work needs an opening, transition, title card, lower third, emotional overlay,
  photo-wall treatment, or stylized effect asset. It integrates
  `skills/video-effect-factory.md` with `skills/remotion-effect-worker.md`
  without replacing the worker or owning `final.mp4`.
- `docs/build-tool-runner-spec.md` —BUILD runner tool selection + P1 audit pack.
- `docs/video-autopilot-tool-integration-spec.md` —editing/VERIFY tool integration.
- `docs/capcut-pipeline-integration-design.md` —optional CapCut finishing backend.
- Skill: `skills/capcut-assisted-finishing.md` -- verified bounded CapCut
  effect/music/export route that returns every candidate to Stage 7 Verify.
- `docs/dashboard-node-skill-output-spec.md` —dashboard / node / output contract.
- `docs/windows-native-migration-spec.md` —Windows migration record (migration complete).
- `docs/SYSTEM-DESIGN.md` —self-contained node/skill/tool architecture brief
  (honest status grading: proven / thin / scaffold / known gaps). Share-ready.
- `docs/reference-repos-map.md` —external reference repos: what to take, license limits,
  integration triggers (ai-media-generator / NarratoAI). Do not re-evaluate; read this.
- `docs/archive/decisions/2026-06-16-native-preview-engine.md` —Workbench preview/edit
  middle layer: material-composition preview, draft patch artifacts, contract
  sync boundary, and Dashboard/Workbench separation.
- `docs/archive/decisions/2026-06-17-frontend-stability-and-modularization.md` --
  Workbench stabilization pass: smoke coverage, module boundary, and draft-only
  frontend responsibility.
- `docs/archive/decisions/2026-06-17-frontend-api-contract-hardening.md` --
  Control Index / Workbench health response-shape lock for future frontend
  integration.
- `docs/archive/decisions/2026-06-17-run-layout-manifest.md` --
  machine-readable run folder/artifact ownership manifest for agents and
  frontend shells.
- `docs/archive/decisions/2026-06-18-material-generation-fallback.md` -- MGF1
  delta-to-generated-job bridge and generated-material honesty boundary.
- `docs/archive/decisions/2026-06-18-generated-material-producer.md` -- GMP1
  generated-job execution into files, manifests, candidate maps, provider-output
  intake, provider packet handoff, style/character lock, and review.
- `docs/archive/decisions/2026-06-19-story-soul-blueprint.md` -- SSB1 upstream
  creative scaffold: story world, concept, beats, shot plan, material needs, and
  review checklist.
- `docs/archive/decisions/2026-06-19-storyboard-panel-lock.md` -- generated comic /
  picture-book panel-lock policy: stretch panel duration or generate more panels
  instead of auto-filling long narration with other accepted panels.
- `docs/archive/decisions/2026-06-20-snow-white-generated-storybook-e2e.md` -- Snow
  White generated storybook E2E: verifies the route from generated panels
  through material-map review, delta coverage, BUILD, Chinese subtitles, and
  route-template guidance.
- `docs/archive/decisions/2026-06-19-interactive-skill-flow.md` -- ISF1 process
  solidification: interactive brief, story soul, material map, generated
  fallback, Workbench draft, and verify/delivery handoff boundaries.
- `docs/archive/decisions/2026-06-19-material-map-relation-review.md` -- material-map
  relation review: no new runtime layer, generated assets remain candidates,
  and Workbench drafts are not material truth.
- `docs/archive/decisions/2026-06-19-effects-node14-roadmap-alignment.md` -- next
  effects direction: effect asset spec, ffmpeg-backed effect build, Brownfield
  Edit / Node14 revision orchestration, and optional Remotion prompt-driven
  effect adapter artifacts, optional worker smoke, and non-canonical draft
  composite.
- Skill: `skills/brownfield-edit.md` -- fast local patch route after review or
  verify gaps; Node14 remains a compatibility implementation node inside this
  route, including Remotion prompt packs, worker output review, and draft
  composite for adapter-route effect gaps.
- Skill: `skills/video-effect-factory.md` -- side-branch route for designed
  effects: design map, effect contract, backend choice, worker handoff, review,
  and bounded handoff. Calls `skills/remotion-effect-worker.md` when Remotion is
  appropriate.
- `docs/archive/decisions/2026-06-17-tool-surface-and-run-layout-consolidation.md` --
  video_tools command catalog, run_layout read-only frontend consumption, and
  split criteria for future backend cleanup.
- `docs/workbench-dashboard-integration.md` -- current Dashboard/Workbench
  integration contract: Dashboard is read/review, Workbench is write-limited
  draft patching, backend remains official renderer.
- `docs/archive/roadmap-snapshots/2026-06-17-repository-consolidation-map.md` --
  archived repo-wide orientation snapshot; historical only.
- `docs/material-organization-policy.md` -- material-map-first policy for
  folders, projections, Workbench material browsing, and source-file movement.
- `dashboard/README.md` -- operator-facing frontend entrypoints, safety rules,
  and local Workbench commands.

## Construction guides (implementation / migration work)

`docs/construction-guides/` keeps implementation plans, migration specs, and
frontend handoff documents. These are not default reference docs for route
execution; read them only when the current roadmap, a skill, a test, or a task
explicitly points to that construction area.

- `docs/construction-guides/dashboard/` -- Dashboard, Route Review, and
  Workbench frontend implementation / migration specs.
- `docs/construction-guides/agent-orchestration/` -- external runner feedback,
  node/phase dispatch hardening, and integrated E2E review action plans.
- `docs/construction-guides/superpowers/` -- work-session plans and
  implementation specs produced during Superpowers-style execution.
- `docs/construction-guides/remotion-effect-build-api-plan.md` -- Remotion
  effect contract hardening, including `skills/remotion-effect-worker.md`,
  `tools/remotion_material_first_memory_acceptance.py`,
  `remotion_material_first_memory_acceptance_report.json`,
  `remotion_effect_handoff.json`, and the material-first `MemoryPhotoWall`
  boundary. This is **not final delivery**.
- `docs/construction-guides/effects_spec_build_contract.md` -- Effect Factory /
  Remotion build contract construction notes. Use the active route docs first.
- `docs/construction-guides/boundary-convergence-plan.md` -- active construction
  plan for route-map, material gap, curator/rough-cut, effect-factory, and E2E
  boundary convergence. Effect Factory boundary checks use
  `tools/effect_factory_boundary_acceptance.py`.
- `docs/generated/pipeline_map.md` -- local generated MVP route map for human review.
  Regenerate with `python tools/pipeline_map.py --build-corpus`; do not commit generated output.

## Working conventions (read before contributing)

- `docs/archive/decisions/2026-06-14-working-loop-and-tdd-evidence.md` —the
  Claude↔Codex loop, the TDD-green-is-the-only-evidence rule, and validator
  discipline. Shared source of truth for how work is done here.

## Decision log (append-only history)

`docs/archive/decisions/` —one file per significant decision. Most recent:
`2026-06-21-video-intent-material-availability-split.md`,
`2026-06-20-soul-passthrough-build-ranking.md`,
`2026-06-20-canonical-route-solidification-review.md`,
`2026-06-20-snow-white-generated-storybook-e2e.md`,
`2026-06-19-effects-node14-roadmap-alignment.md`,
`2026-06-19-interactive-skill-flow.md`,
`2026-06-19-material-map-relation-review.md`,
`2026-06-19-storyboard-panel-lock.md`,
`2026-06-19-story-soul-blueprint.md`,
`2026-06-18-generated-material-producer.md`,
`2026-06-18-material-generation-fallback.md`,
`2026-06-17-tool-surface-and-run-layout-consolidation.md`,
`2026-06-17-run-layout-manifest.md`,
`2026-06-17-frontend-api-contract-hardening.md`,
`2026-06-17-frontend-stability-and-modularization.md`,
`2026-06-17-dashboard-workbench-integration-cleanup.md`,
`2026-06-14-working-loop-and-tdd-evidence.md`,
`2026-06-14-m6a-review-response.md`,
`2026-06-13-m5-real-render-sensory-acceptance.md`,
`2026-06-13-spec-field-census.md`.
Material-map current summary lives in `docs/material-map-lifecycle.md`.
Pre-split roadmap snapshots are local history only and are not part of the public MVP tree.

## Design notes (still referenced by skills —keep)

`design/ffmpeg-pitfalls-reference.md`, `design/skill-interface-contracts.md`,
`design/tool-verification-log.md`,
`design/video-editing-workflow-architecture-first-fallback.md`,
`design/video-editing-workflow-brainstorming-to-material-direction.md`.

## Historical (moved out, not deleted)

- `docs/archive/` -- historical decision logs, review evidence, and roadmap
  history. Do not treat as current unless a current doc links to it.
