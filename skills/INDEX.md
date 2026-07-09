# Skills Index

This index is the ownership map for the flat `skills/*.md` surface. Owners are
branch ids from `docs/branch-contract-registry.json`, plus `shared` and
`archive` for cross-branch or retired material.

| skill path | owner | segment | role (one line) |
|---|---|---|---|
| `skills/audio-director.md` | soundtrack-arranger, subtitle-voiceover | audio / voice shared | Designs audio, voiceover, ducking, and narration handoff decisions. |
| `skills/blueprint-interview.md` | main-pipeline | upstream story | Elicits story/world/character structure before contract compile. |
| `skills/brownfield-edit.md` | workbench-brownfield | workbench patch | Handles bounded edits to drafts without rewriting canonical truth. |
| `skills/curator.md` | material-map | material curation | Selects and reviews material candidates for segment needs. |
| `skills/dashboard.md` | workbench-brownfield | dashboard/workbench | Presents run state, artifacts, and review surfaces for operators. |
| `skills/director.md` | film-canon-product-route | production SPEC | Owns production intent, segment logic, and director-level revisions. |
| `skills/editor.md` | main-pipeline | build/edit | Converts approved contracts into edit/timeline decisions. |
| `skills/effects-director.md` | effect-factory | effect direction | Translates desired visual mood into effect direction and constraints. |
| `skills/gap-analyzer.md` | main-pipeline | upstream story | Identifies narrative/material gaps before build handoff. |
| `skills/generated-material-producer.md` | material-map | generated material | Produces and imports reviewed generated material candidates. |
| `skills/generative-director.md` | material-map | generated provider | Plans generated-provider prompts and visual fallback direction. |
| `skills/material-generation-fallback.md` | material-map | generated fallback | Routes missing material needs to bounded generated-material fallback. |
| `skills/material-map.md` | material-map | material truth | Builds material maps, deltas, review apply, and material-first truth. |
| `skills/pipeline-boundary.md` | shared | boundary charter (all skills) | Defines cross-skill boundaries and fail-closed ownership rules. |
| `skills/remotion-effect-worker.md` | effect-factory | effect worker | Builds bounded Remotion effect assets from approved effect specs. |
| `skills/archive/route.md` | archive | retired route.py dispatcher | Retired state/route dispatcher contract from the route.py era. |
| `skills/shooting-brief.md` | main-pipeline | upstream story | Converts gaps into reshoot or missing-material briefs. |
| `skills/soundtrack-arranger.md` | soundtrack-arranger | soundtrack branch | Plans, sources, probes, and hands off music/BGM choices. |
| `skills/spec-contract.md` | main-pipeline | contract compile | Compiles Stage 0/story/material intent into `segment_contract.json`. |
| `skills/story-soul-blueprint.md` | film-canon-product-route | upstream story | Captures story soul, tone, and narrative structure before build. |
| `skills/subtitle-director.md` | subtitle-voiceover | subtitle/voiceover | Owns subtitle, narration, and voiceover handoff requirements. |
| `skills/verify.md` | verify-delivery | final verify | Verifies delivery evidence, gates, audits, and final handoff readiness. |
| `skills/video-effect-factory.md` | effect-factory | effect planning | Plans effect contracts, capability translation, and worker handoff. |
| `skills/video-intent-planner.md` | main-pipeline | stage0 / node 0 | Produces `video_intent.json` and route-changing follow-up questions. |
| `skills/video-pipeline-route.md` | main-pipeline | route coordinator | Coordinates canonical route, branch handoffs, and next-action behavior. |
| `skills/video-pipeline.md` | main-pipeline | entry orchestrator | Top-level entry skill for every video production request. |
| `skills/video-workflow.md` | main-pipeline | stage0 / node 0 | Legacy workflow-oriented Stage 0 planner and run setup guide. |
| `skills/writer.md` | main-pipeline | text layer | Writes narration, captions, and on-screen text for the contract. |

Known tension: `video-workflow.md` and `video-intent-planner.md` overlap at Stage 0; merge evaluation deferred.
