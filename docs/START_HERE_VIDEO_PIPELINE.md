# Start Here: Hermes Video Pipeline

Date: 2026-06-20
Status: canonical entrypoint for agents and operators

Read this first when you need to run, debug, or extend the video pipeline.

## What This Project Is

Hermes is a contract-first video pipeline:

```text
Video Intent Planner
  -> material availability
  -> story/design contract
  -> material truth
  -> BUILD
  -> verify/review
  -> draft edit or delivery
```

Do not treat generated files, Workbench patches, stale reports, or old final
videos as truth. They must re-enter the route through their owning artifacts.

## Read Order

1. `docs/START_HERE_VIDEO_PIPELINE.md` -- this file.
2. `docs/video-pipeline-end-to-end-line.md` -- one-page line from intent to
   delivery, including material availability and return loops.
3. `docs/video-pipeline-operating-map.md` -- stage-by-stage operating manual:
   skills, tools, artifacts, gates, return routes.
4. `docs/canonical-video-pipeline-route.md` -- canonical stage definitions and
   legacy alias mapping.
5. `docs/upstream-story-route.md` -- full upstream line from role/literary lens
   through blueprint, Story Soul, Director Shot Plan, contract compile, and
   material-ready handoff.
6. `docs/artifact-reviewer-map.md` -- lightweight reviewer policy:
   `light / normal / deep` and reviewer roles.
7. `docs/material-map-lifecycle.md` -- material needs, maps, delta, revision,
   lifecycle stages, and build handoff.
8. `docs/build-capability-alignment.md` -- which capabilities truly affect
   BUILD/render today.
9. `docs/route-orchestrator-harness.md` -- optional multi-agent task packet
   and fail-closed acceptance harness.
10. `docs/route-agent-runner-protocol.md` -- how Codex/Claude/Gemini or a
   human worker should consume `route_subagent_task.json`.
11. `RUNBOOK.md` -- local command examples and Windows execution notes.
12. `docs/INDEX.md` -- broader documentation index and historical links.

## Main Skill Entry

Use:

```text
skills/video-pipeline-route.md
```

That is the operator skill for the full route.

Other skills are role-specific:

- story: `story-soul-blueprint.md`, `writer.md`, `director.md`
- material: `material-map.md`, `curator.md`, `material-generation-fallback.md`,
  `generated-material-producer.md`
- build: `editor.md`, `audio-director.md`, `subtitle-director.md`,
  `effects-director.md`
- review: `verify.md`, `dashboard.md`, `brownfield-edit.md`

## Choose The Route

Stage 0 is **Video Intent Planner**. It is the upstream role that asks what kind
of video this is, who it is for, what material exists, and whether generation is
allowed. It may behave like a storybook writer, teacher, event director,
personal-memory editor, or brand editor depending on the brief.

First decide **material availability** before deciding how much story invention
is allowed. This is the top-level split:

```text
Video Intent Planner
  -> material availability
  -> existing-material-first | story-first | hybrid
  -> route-specific story/design/material work
```

- **existing-material-first**: the user has footage/photos. Run material-map
  early, let the available material become the story source and constraint, and
  fill missing intent through interaction. For teaching or personal video work,
  generation is fallback only: chapter cards, diagrams, symbolic bridges, or
  missing non-proof visuals.
- **story-first**: the user has no material or explicitly wants a generated /
  storybook route. Build the literary/story/teaching intent first, then derive
  material needs and use generated/captured material as evidence candidates.
- **hybrid**: some material exists, but gaps may require reshoot, generation,
  shortening, rewrite, or waiver. Material-map and material-delta decide which.

If the project starts from a story, essay, life experience, fairy tale, or
emotion-heavy event brief, use `docs/upstream-story-route.md` before Material
Truth. The upstream line is:

```text
Role / Literary Lens
  -> Blueprint Interview
  -> Story Soul Package
  -> Director Shot Plan
  -> Contract Compile
  -> Material-Ready Handoff
```

### Existing material

Use when the user already has real footage/images.

```text
Video Intent Planner
  -> Material Map quick inventory
  -> story/design skeleton constrained by the map
  -> Material Map review / need satisfies edges
  -> Material Delta
  -> BUILD
  -> Verify
  -> Workbench/Brownfield if needed
```

Do not route to generated storybook only because the style is comic, picture
book, or illustrated. If real material exists, inspect it first and let
material-delta decide which beats still need generation.

### Generated material

Use for comics, picture books, synthetic story videos, or missing footage.

```text
Video Intent Planner
  -> Literary / Role Lens if story quality matters
  -> Story Soul Blueprint
  -> Material Needs
  -> Material Generation Fallback
  -> Generated Provider Packet
  -> Generated Material Import
  -> Generated Material Review
  -> Fresh Delta
  -> BUILD
```

### Hybrid material

Use when some real material exists and some needs require generation/reshoot.

```text
Project Material Map + Generated Candidates
  -> Explicit Review
  -> Fresh Material Delta
  -> Revision or BUILD
```

### Workbench / Brownfield

Use after a render or review when the user wants bounded local changes.

```text
Workbench draft patch
  -> backend handoff
  -> Brownfield edit / rerender
  -> Verify
```

## Review Policy

The route may declare:

```json
{
  "review_policy": {
    "level": "light | normal | deep"
  }
}
```

- `light`: material producer + technical verify.
- `normal`: story director + material producer + timeline + technical verify.
- `deep`: adds literary editor, generated art director, audio/subtitle, effects,
  and delivery review.

See `docs/artifact-reviewer-map.md`.

Do not turn every review into a hard gate. Gate strength depends on reviewer
role and artifact.

## Core Commands

List commands:

```powershell
python video_tools.py --help
python video_tools.py commands-manifest
python video_tools.py workflow-manifest
```

Common official render:

```powershell
python video_tools.py contract-run segment_contract.json `
  --material-db materials_db.json `
  --music bgm.mp3 `
  --out final.mp4 `
  --mat-dir run
```

Multi-agent route packet:

```powershell
python video_tools.py route-task-next RUN_DIR --out route_subagent_task.json
python video_tools.py route-task-accept `
  --task route_subagent_task.json `
  --result route_subagent_result.json `
  --state-out route_orchestrator_state.json
python video_tools.py route-orchestrator-acceptance RUN_DIR `
  --route existing-material-first `
  --stage-count 4 `
  --out route_orchestrator_acceptance.json
```

Material lifecycle:

```powershell
python video_tools.py material-map-lifecycle --out-dir run `
  --needs material_needs.json `
  --material-db materials_db.json `
  --contract segment_contract.json
```

Generated material handoff:

```powershell
python video_tools.py material-generation-fallback ...
python video_tools.py generated-image-provider-packet ...
python video_tools.py generated-material-import ...
python video_tools.py generated-material-review ...
```

Workbench:

```powershell
python tools/workbench_server.py --artifact-root RUN_DIR --port 8770
```

## Before You Claim Success

Check:

- current run wrote `final.mp4`;
- material delta / revision gates were fresh;
- generated candidates were explicitly reviewed;
- Workbench patches did not overwrite canonical artifacts;
- verify/audit evidence exists;
- unresolved limitations are stated.

If a failure is creative, go back to Story Soul / reviewer layer.
If a failure is material, go back to material map / delta.
If a failure is finishing, use Workbench / Brownfield.
If a failure is technical delivery, use Verify / render fix.
