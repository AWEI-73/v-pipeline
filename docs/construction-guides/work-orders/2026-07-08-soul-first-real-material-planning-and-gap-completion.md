# 2026-07-08 Soul-First Real-Material Planning And Production-Line Completion

## Goal

Build a no-render, real-material planning route that starts from the film's "soul" and ends with a render-facing plan plus production-line completion map. This is not another mid-pipeline timing test. It must prove whether the pipeline can reason like an editor: form a story hypothesis, understand available material, discover what the material can honestly support, rewrite or reorder the story around that evidence, and decide whether to fill gaps through source search, generated support material, reshoot/collection brief, subtitle/title design, or script revision.

This round must use the real graduation source folder as read-only input:

`C:\Users\user\Downloads\微電影素材\_整理後`

No final video is expected in this round.

## User Context To Preserve

The user described real editing as an iterative creative process, not a linear asset lookup:

- A story may begin from a fuzzy directive or supervisor idea.
- The editor often discovers the actual structure only after inspecting source material.
- Missing pieces are filled by finding overlooked source material, asking for supplemental material, generating non-proof support visuals, or rewriting the story.
- Repeated material is acceptable only when it has a deliberate payoff, contrast, callback, or rhythm function.
- Opener and closer are usually designed, not passively found.
- For the graduation product, the core shape remains: opening story, training MV, supervisor/source speech, teacher/class intro, closing payoff. But the internal order may change according to the story theme.

## Current Evidence

V7 five-minute rehearsal produced a timing/module plan but did not contain the upstream happy-path artifacts needed for a real film route:

- Missing `story_contract.json`
- Missing `story_shell.json`
- Missing `director_shot_plan.json`
- Missing `material_needs.json`
- Missing `story_to_material_map.json`
- Missing `material_delta.json`
- Missing render-facing shot list
- Missing creative gap strategy

Therefore V7 was a useful engineering stop-loss, not a complete soul-first product route.

## Owner Zone

Editable paths:

- New output root under `.tmp\soul_first_real_material_planning_*`
- Run-local artifacts inside that fresh output root
- `video_pipeline_core/*story*soul*.py`
- `video_pipeline_core/*film*canon*.py`
- `video_pipeline_core/*material*planning*.py`
- `video_pipeline_core/*material*gap*.py`
- `video_pipeline_core/*story*material*.py`
- `video_pipeline_core/*shot*plan*.py`
- `video_pipeline_core/*effect*intent*.py`
- `video_pipeline_core/*source*material*matrix*.py`
- `tools/*story*soul*.py`
- `tools/*film*canon*.py`
- `tools/*material*planning*.py`
- `tools/*material*gap*.py`
- `tools/*story*material*.py`
- `tools/*shot*plan*.py`
- `tools/*effect*intent*.py`
- `tools/*source*material*matrix*.py`
- Relevant tests under `tests/`
- `docs/branch-contract-registry.md`
- `docs/branch-contract-registry.json`
- `docs/video-pipeline-operating-map.md`
- `docs/pipeline-decision-tree.md`
- `docs/construction-guides/work-orders/2026-07-08-soul-first-real-material-planning-and-gap-completion-report.md`

## Forbidden Zone

Read-only paths:

- `C:\Users\user\Downloads\微電影素材\_整理後`
- Existing `.tmp\graduation_v*` runs
- Existing `.tmp\v6_*` runs
- Existing `.tmp\voxcpm_provider_leadin_artifact_diagnostic_*` runs
- `deliveries\`
- `.env`, `.env.*`
- `.venv_voxcpm\`
- `reference repo\`
- VoxCPM reference/source repository
- Existing final media artifacts
- `story_human_review_decision.json` in any run
- Git branch/commit/push operations

## Required Pieces

1. Create a fresh no-render output root. Do not copy or mutate existing V-runs as the basis for truth.
2. Run a real source preflight and write `source_preflight.json`: source exists, file count, media count, video/image/audio counts, folder grouping, old compilation/source-folder music risk flags, and known supervisor/source speech candidates.
3. Produce `film_intent_brief.json` from the user context above. It must state audience, product type, target future length bands, default no-narration route, optional narration route, music/subtitle role, and unresolved human decisions.
4. Produce a soul-first package:
   - `story_contract.json`
   - `story_shell.json`
   - `creative_concept.json`
   - `screenplay_beats.json`
   - `director_shot_plan.json`
   - `review_checklist.md`
5. The story contract must include:
   - one-sentence thesis
   - emotional spine
   - opener question or promise
   - training MV story logic
   - supervisor/source speech function
   - teacher/class intro function
   - closing callback/payoff
   - rejected generic structure notes
6. Build or reuse material-understanding evidence from the real source folder. At minimum produce a matrix/planning artifact that separates:
   - source files that are raw footage/photos
   - old compiled videos
   - source-folder music
   - supervisor/source speech
   - teacher/class intro
   - opener/closer candidates
   - training module candidates
7. Produce `material_needs.json` from the story beats. Needs must include count/duration estimates, fallback options, and proof vs support classification.
8. Produce `story_to_material_map.json` and `story_material_negotiation.json`. These must show how the story changed after seeing material evidence. A useful output includes accepted mappings, thin mappings, missing mappings, substitutions, reordered beats, shortened beats, and intentional repeats.
9. Produce `material_delta.json` or an equivalent gap-completion delta. It must not treat token/folder names as proof. It must classify each need as covered, thin, missing, generated_support_candidate, reshoot_or_collect, rewrite, shorten, or waive_required_human_decision.
10. Produce `creative_gap_strategy.json` with concrete next actions:
    - source search within the real folder
    - generated support material allowed only for non-proof bridges, opener/closer, chapter cards, symbolic inserts, or motion graphics
    - reshoot/collection brief where real proof is missing
    - script rewrite or shortening when material cannot support the planned duration
    - rejected fake-completion paths
11. Produce opener/closer/effect planning:
    - `opening_design_brief.json`
    - `closing_design_brief.json`
    - `effect_intent_plan.json`
    - `title_subtitle_strategy.json`
    The opener and closer must be story functions, not just title cards.
12. Produce `render_facing_shot_plan.json` for a future 5-minute draft and a future 10-minute version. It must include section, beat id, material refs, intended duration, shot function, proof/support role, repeat policy, effect/title/subtitle needs, audio role, and fallback if thin.
13. Produce `no_render_review_packet.md` for human review. It must be written for a person judging the story and edit plan, not only for a programmer reading artifacts.
14. Produce `pipeline_readiness.json` with:
    - `ready_for_render`: false unless all required planning artifacts exist and no tier-1 gap remains unhandled
    - `next_owner`
    - `next_action`
    - blocking gaps
    - optional branches, including VoxCPM health-check branch
15. Produce `production_line_completion_map.json`. This is the main integration artifact for this round. It must map the route from soul-first planning to future render and name each node as `ready`, `partial`, `blocked`, or `missing`. It must cover at least:
    - user brief / film intent
    - story soul / story contract
    - material needs
    - material understanding
    - story-material negotiation
    - gap completion
    - opener/closer/effect intent
    - title/subtitle strategy
    - music strategy
    - source speech / transcript review
    - optional narration / VoxCPM health check
    - render-facing shot plan
    - no-render human review packet
    - next render rehearsal entry point
16. If adding or changing tools, tests must be red-first and then green. If no code changes are needed, still write an executable artifact check proving the required files and fields exist.

## Red-First Verification

Before implementation, capture one failing evidence path proving the current route is incomplete. Acceptable red-first evidence:

- A V7 run lacks `story_contract.json` / `story_to_material_map.json`.
- A new planning artifact validator fails because required soul-first artifacts do not exist.
- A material-gap validator fails because token/folder coverage lacks proof/support classification.

Use pinned interpreter:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest <focused_tests_for_changed_modules>
```

If no code changes are made, run a pinned Python precheck that prints the missing V7 upstream artifacts and exits non-zero, then record that as red evidence.

## Acceptance Commands

Use `C:\Users\user\miniconda3\python.exe` for every Python command. Do not use bare `python` or `pytest`.

If code/tests are changed, expected exit code `0`:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_story_soul_blueprint tests.test_graduation_film_blueprint_catalog tests.test_pipeline_home
```

Also run any new focused test file explicitly with expected exit code `0`.

Run the no-render route or artifact generator with pinned Python. The exact command is delegated, but it must write all required artifacts under the fresh `.tmp\soul_first_real_material_planning_*` root and exit `0` unless a real stop-loss is reached.

Registry parse, if registry JSON is edited:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; json.load(open('docs/branch-contract-registry.json', encoding='utf-8')); print('json ok')"
```

Expected exit code `0`:

```powershell
git diff --check
```

Final artifact check, run with pinned Python, must verify:

- Fresh output root exists.
- `final.mp4`, `final_v7.mp4`, or any new rendered final media does not exist.
- Required artifacts listed in Required Pieces exist.
- `pipeline_readiness.json` exists and is not a fake render pass.
- `production_line_completion_map.json` exists and clearly separates ready/partial/blocked/missing route nodes.
- `render_facing_shot_plan.json` contains both 5-minute and 10-minute planning views.
- `story_material_negotiation.json` records at least one material-driven story decision, substitution, shortening, or gap strategy.
- `creative_gap_strategy.json` includes generated support, source search, reshoot/collect, and rewrite/shorten routes.
- Existing V-runs and diagnostic runs were not modified.
- Generated JSON/Markdown/SRT text decodes with UTF-8 and contains no `\ufffd` or suspicious repeated literal question-mark runs.

## Stop-Loss Limits

- If the real source folder is missing, stop after source preflight.
- If the worker cannot produce a story thesis and emotional spine from the user context plus source evidence, stop and report `story_soul_unformed`.
- If material evidence is too thin for a 5-minute or 10-minute plan, do not inflate duration; write a gap/shorten/rewrite strategy.
- If the output only classifies folders or filenames without proof/support roles, stop as `material_understanding_too_shallow`.
- Do not render.
- Do not write `story_human_review_decision.json`.
- Do not claim legal/music approval.
- Do not treat generated support material as proof footage.
- Do not silently use old compiled videos as primary raw footage; label them as compiled-source candidates and state risk.

## Delegated Decisions

- Exact implementation route: compose existing tools, add a small planner, or write run-local artifacts with tests.
- Exact schema field names beyond the required artifact names and required concepts.
- Exact story theme, as long as it is grounded in user context and material evidence.
- Exact 5-minute and 10-minute section timings.
- Exact generated support concepts for opener/closer or bridge visuals.
- Whether code changes are necessary. If not, the executable artifact check must carry the acceptance burden.

## Final Report Requirements

Write `docs/construction-guides/work-orders/2026-07-08-soul-first-real-material-planning-and-gap-completion-report.md` with:

- Output root and command/exit-code table.
- Red-first evidence.
- Source preflight summary.
- Story thesis, emotional spine, opener promise, closing payoff.
- 5-minute and 10-minute structure summaries.
- Material understanding summary and key source folders/files.
- Material-driven story changes.
- Covered/thin/missing/generated-support/reshoot/rewrite/shorten decisions.
- Opener/closer/effect/title/subtitle plan summary.
- Render-facing shot plan path.
- Human review packet path.
- Pipeline readiness result and next owner.
- Production-line completion map summary: ready nodes, partial nodes, blocked nodes, missing nodes, and next render rehearsal entry point.
- Confirmation that no render/final media or final approval was written.
- Deviations, blockers, and next recommended work.
