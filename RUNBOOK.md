# Hermes Video Pipeline Runbook

Date: 2026-06-25
Status: current operator runbook for Windows-native runs

This runbook is for agents and humans running Hermes locally.

## Single Operator Entry

Start here for all operational work. Do not begin by browsing random docs,
skills, or tools. Use this runbook to pick the route, then open only the
referenced document or skill needed for the current task.

Document roles:

| Need | Read | Why |
|---|---|---|
| Concept orientation | `docs/START_HERE_VIDEO_PIPELINE.md` | Explains the overall route and vocabulary. Do not use it as the command runner. |
| Decision tree | `docs/pipeline-decision-tree.md` | Decides the owner, branch, first safe action, stop gate, and return route. |
| Stage/tool map | `docs/video-pipeline-operating-map.md` | Maps stable stages to skills, tools, artifacts, gates, and return routes. |
| Canonical route definition | `docs/canonical-video-pipeline-route.md` | Defines official stage names, route semantics, and delivery gates. |
| Skill/tool ownership | `docs/stage-tool-simplification.md` | Shows which skill owns which Python tools and how to audit ownership. |
| Worker boundaries | `docs/stage-boundary-matrix.md` | Defines allowed writes, forbidden writes, done gates, and stop gates. |
| Main route construction plan | `docs/construction-guides/stage0-10-route-alignment-plan.md` | Use when changing how Stage 0-10 child contracts, branches, BUILD, and delivery line up. |
| Construction guides | `docs/construction-guides/` | Use only when actively changing implementation in that construction area. |
| Historical archive | `docs/archive/` | Decision history only; not an operational source unless a current doc links to it. |

## Task-to-Document Router

Use this table before opening any other document.

| Task | First document | First skill | First safe tool/action | Stop before |
|---|---|---|---|---|
| New or fuzzy whole-video request | `docs/pipeline-decision-tree.md` | `skills/video-pipeline-route.md` | Stage 0 package: `project_brief.json`, `interaction_log.md`, `video_intent.json` | branch work while `required_followup_questions` is non-empty |
| Continue or inspect an existing run | `docs/pipeline-decision-tree.md` | `skills/video-pipeline-route.md` | `python tools\pipeline_home.py --run RUN_DIR --json` | any write until cursor/next_action is known |
| Material-first / footage / photos | `docs/material-map-lifecycle.md` | `skills/material-map.md` | `material_scan_decision` then quick inventory or material-first acceptance | BUILD/render before delta/review gate |
| One long video / interview / podcast highlight | `docs/pipeline-decision-tree.md` | `skills/material-map.md` | source matrix, correct subtitle or ASR, then `source-dialogue-script` | cutting before transcript/script review |
| Story/article/idea without material | `docs/upstream-story-route.md` | `skills/video-pipeline-route.md` | structure-first Stage 0, material needs, generated fallback only after delta | generated assets without explicit review |
| Opening, transition, title, stylized effect | `docs/effect-factory-route.md` | `skills/video-effect-factory.md` | `visual_technique_plan.json` and parameter review | backend worker/render with unconfirmed parameters |
| Music, BGM, original speech, ducking | `docs/soundtrack-arranger-route.md` | `skills/soundtrack-arranger.md` / `skills/audio-director.md` | `soundtrack_plan.json`, source/license manifest, probe or Audio Director handoff | final mix when license/source/ducking is unresolved |
| Subtitle, narration, voiceover | `docs/pipeline-decision-tree.md` | `skills/subtitle-director.md` / `skills/audio-director.md` | subtitle/voiceover handoff acceptance | BUILD/delivery when language/readability evidence is missing |
| Draft, rough cut, local patch | `docs/workbench-dashboard-integration.md` | `skills/brownfield-edit.md` | validate draft patch and `workbench_handoff.json` | overwriting canonical artifacts |
| Verify final candidate / delivery | `docs/pipeline-decision-tree.md` | `skills/verify.md` | delivery gate / `write_delivery_gate_report.py` | accepting missing or stale evidence |

If a task spans multiple rows, use `docs/pipeline-decision-tree.md` first. It
defines branch insertion points and the return route.

## Architecture In One Page

Hermes has one main route, Stage 0 child contracts, and major side branches.

```text
Main route: Video Pipeline Route
  -> Stage 0 Video Intent Planner
  -> child contracts: material_contract, soundtrack_contract, effect_policy,
     subtitle_voiceover_contract
  -> story/design contract
  -> BUILD
  -> Verify
  -> Workbench/Brownfield
  -> Delivery

Side branch 1: Material Map
  -> material truth
  -> one-source eye/ear/head evidence when the material is a long source
  -> coverage/delta
  -> generated candidates or reshoot/rewrite/waiver

Side branch 2: Effect Factory
  -> effect design map
  -> effect contract
  -> remotion-effect-worker or light backend
  -> effect review
  -> bounded handoff

Side branch 3: Soundtrack Arranger
  -> section music / song / voice intent
  -> source candidates and license manifest
  -> audio-director handoff

Reserved child branch: Subtitle / Voiceover
  -> whole-video language, subtitle, narration, and voiceover intent
  -> subtitle-director / audio-director execution
  -> readability and narration evidence before delivery

Cross-cutting branch: Review / Verify / Delivery Gate
  -> route, material, contract, audio, effect, timeline, and final evidence
  -> fail closed on missing or stale proof
```

Do not jump directly to render. Do not treat `final.mp4`, generated files,
Workbench patches, or effect previews as truth unless the owning route has
accepted them.

## Semantic Entry Router

Use this table before browsing random docs or tools. It is the operator-facing
map from user language to route entry. If `RUN_DIR` already exists, run
`python tools\pipeline_home.py --run RUN_DIR --json` first, then combine that
state with the row below.

Stage 0 package means `project_brief.json`, `interaction_log.md`, and
`video_intent.json`. `video_intent.json` must record `target_length` when the
user gives one; if target length is unknown and affects route/build decisions,
put it in `required_followup_questions` instead of guessing.

### Entry Precedence

Use these tie-breakers before choosing a row:

1. **Resume existing run wins.** If the user says a run is stuck, asks to
   continue, review an existing run, or points to a run folder, first run
   `python tools\pipeline_home.py --run RUN_DIR --json`. The cursor decides the
   owning stage.
2. **Whole-video requests win over side-branch keywords.** If the request is
   about making or changing a whole video, go through Stage 0 even when it also
   says music, transition, subtitle, effect, warm, hot-blooded, story-like, or
   cinematic.
3. **Side-branch keywords are child intents.** Effect Factory and Soundtrack
   Arranger may be called after Stage 0 or from an existing run cursor. They are
   first owners only for a clearly bounded effect or music/song/BGM intent, not
   for a whole film.
4. **Existing draft edits go Brownfield/Workbench.** If the user refers to a
   draft, rough cut, existing final candidate, clip replacement, subtitle patch,
   or local finishing change, inspect the run first and keep edits draft-only.
5. **Subtitle or volume repair is not Soundtrack Arranger.** Soundtrack
   Arranger plans music/song/BGM source and license. whole-video subtitle intent
   is a child intent after Stage 0; subtitle repair on an existing draft belongs
   to Brownfield/Workbench or Subtitle Director. Volume repair, normalization,
   ducking, and speech preservation belong to Brownfield/Workbench or Audio
   Director after the run state is known.
6. **Generated candidate fallback is not the first move.** Story/article/idea
   routes first write intent/story/material needs, then use material delta to
   decide generated candidate fallback and review.

| User says | Entry skill | First safe action | Required artifacts | Stop condition |
|---|---|---|---|---|
| "this run is stuck", "continue this run", "resume", "接著跑" | `skills/video-pipeline-route.md` resume | read-only `pipeline_home.py` inspection | run folder, state/artifact cursor | unknown run, repair cursor, unresolved gate/review |
| "help me cut a video", "make a recap", "剪一支影片" | `skills/video-pipeline-route.md` | Stage 0 Video Intent Planner | `project_brief.json`, `video_intent.json`, `interaction_log.md` | `required_followup_questions` is non-empty |
| "I already have footage", "use this folder", "我有素材" | `skills/material-map.md` via main route | material-first boundary acceptance | `material_wall_review_verdict.json`, `material_first_boundary_acceptance_report.json` | report returns `repair:*` or missing/thin needs |
| "cut this 5-10 minute video into highlights", "interview clip", "podcast highlight" | `skills/material-map.md` via main route | one-source understanding: section map, motion/audio matrix, correct subtitle or ASR | `source_section_map.json`, `source_material_matrix.json`, `source_transcript.json`, `dialogue_edit_script.json` | transcript is low-confidence, clips cut half sentences, or script is unreviewed |
| "I only have a story/article/idea", "沒有素材" | `skills/video-pipeline-route.md` + upstream story route | structure-first, material needs, generated candidate fallback | `material_needs.json`, `material_generation_fallback.json`, generated review artifacts | generated candidates are not explicitly reviewed |
| "I need an opening effect", "transition", "特效/開場/轉場" | `skills/video-effect-factory.md` | visual technique plan and parameter review | `visual_technique_plan.json`, review/apply artifact, effect handoff | candidate parameters are unconfirmed |
| "edit this draft", "change the rough cut", "換素材" | `skills/brownfield-edit.md` / Workbench | validate draft patch; keep preview non-canonical | `preview_timeline.json`, `timeline_patch.json`, handoff report | patch would overwrite canonical truth |
| "export the final video", "render final.mp4", "輸出成片" | `skills/video-pipeline-route.md` delivery gate | inspect `pipeline_home.py`, then render only if gates are green | `segment_contract.json`, material DB/map, audio/subtitle/effect evidence, `verify_result.json` | any repair cursor, stale material, missing verify, or unresolved reviewer |

Do not treat this table as permission to execute heavy commands. It picks the
route and the next safe artifact. The owning gate decides whether the route may
continue.

Bounded music/song/BGM intent requests ("choose music", "find a song", "BGM",
"voiceover mood", or "do not cover the speech") enter
`skills/soundtrack-arranger.md`. The first safe artifacts are
`soundtrack_plan.json`, `music_source_candidates.json`,
`sound_license_manifest.json`, and `audio_director_handoff.json`. Stop if the
source/license is unknown, a famous song is only `reference_only`, or speech
ducking/preservation is not specified. Subtitle repair, subtitle burn-in fixes,
volume repair, and generic "make the whole video more emotional" requests do
not start here.

`route_judgment.json is not enough`. It may explain a decision, but it is not a
canonical pipeline artifact. If a worker only writes route judgment notes and
`pipeline_home.py returns unknown`, the run has not entered the pipeline. The
minimum Stage 0 package is `project_brief.json`, `interaction_log.md`, and
`video_intent.json`, or a clear `needs-context` stop with focused follow-up
questions.

For "I have footage but want a story-shaped film", `material-first remains the route`.
Do not jump to upstream story as the first owner. Build the `story skeleton follows material facts`
after the material map exposes usable scenes,
speeches, emotional moments, repeats, and gaps. Story can shape the edit, but
material truth still owns the first branch.

For material-only requests, `Material Delta is a gate`. It is not a forbidden
step; it is the decision point after maps/review edges exist. What is forbidden
is skipping from material inventory directly to BUILD/render without a fresh
delta/lifecycle decision.

Material-to-timeline rule: after Material Map review, accepted scene-to-need
edges and reviewed `usable_range` values must remain visible through
`rough_cut_plan.json` and `timeline_build.json`. A BUILD-facing timeline clip
should carry `scene_id`, `asset_id` or `material_map_id`, and `need_id`. Delivery
may block a clip when those direct fields, or the `scene_id` fallback through
`project_material_map.json`, do not match `segment_contract.material_map_ids`
or `material_fit.need_refs`. Long accepted material may be cut down to the
requested segment duration. Short accepted material must not be silently treated
as complete: `rough_cut_plan.json` must keep the selected short clip and also
write a `gaps[]` entry with `requested_duration_sec`,
`selected_duration_sec`, and `missing_duration_sec`; delivery blocks on that
gap until the segment is shortened, merged, waived, regenerated, or more
material is accepted. Still images/photos are different: they may hold for the
requested duration, but the timeline still needs `asset_id`/`need_id` trace so
Workbench and visual-fatigue review can see the hold.

## Windows Setup

```powershell
cd C:\Users\user\Desktop\video_pipeline
$env:PYTHONUTF8=1
python --version
python video_tools.py --help
```

Inspect command surfaces:

```powershell
python video_tools.py commands-manifest --out .tmp\video_tools_commands.json
python video_tools.py workflow-manifest --out .tmp\video_tools_workflows.json
python video_tools.py test-tiers --out .tmp\test_tiers.json
```

Use focused tiers while developing:

```powershell
python video_tools.py test-tiers --tier backend-smoke
python video_tools.py test-tiers --tier material-map
python video_tools.py test-tiers --tier workbench
```

Full regression is intentionally heavy because it includes render
characterization and replay tests. On the current Windows environment it can
take about 8 minutes:

```powershell
python -m unittest discover -s tests -q
```

Do not treat a short client timeout as a failed test run unless the command
returns a non-zero exit code or a specific failing test.

## Run Folder First

Use a run folder as the handoff unit. Before acting, inspect state:

```powershell
python tools\pipeline_home.py --run RUN_DIR --json
```

`pipeline_home.py` is read-only. It summarizes `mode`, `cursor`, `next`,
`source`, and relevant artifacts. It does not replace gates.

Validate run layout when needed:

```powershell
python video_tools.py run-layout-validate RUN_DIR --out RUN_DIR\run_layout_validation.json
```

## Happy Paths

These are example routes a new operator can run to see the pipeline shape.
They are intentionally bounded. The first three are acceptance/dry-run paths and
must not create `final.mp4`; official render is a separate final step after
gates pass.

### A. Existing Material / Material-First

Use this when the user already has photos or video and wants the pipeline to
coarse-screen, map, rough-cut, and reach a review/render handoff.

```text
brief + source folder
  -> video_intent.json: entry_path=material-first
  -> material_understanding_matrix.json / contact sheet
  -> optional material_wall_review_verdict.draft.json
  -> material wall review
  -> material map / review apply
  -> rough_cut_plan.json / timeline_build.json
  -> stage5 final review smoke
  -> ready_for_render_or_human_review
```

Minimal no-render acceptance:

Optional review aid before writing the wall verdict:

Fast operator wrapper:

```powershell
python tools\material_first_happy_path.py `
  --out RUN_DIR `
  --source-dir MATERIAL_SOURCE_DIR `
  --max-assets 12 `
  --frame-budget 3 `
  --json
```

This creates the matrix, contact sheet, conservative wall verdict draft,
60-90 second `preview_rough_cut_plan.json`, and material-first boundary
acceptance report in one run folder. It does not render. The canonical
`rough_cut_plan.json` remains a short smoke handoff; review
`preview_rough_cut_plan.json` before using it for render or Workbench changes.

For large source clips, use a storyboard preview built from matrix keyframes
before attempting motion preview:

```powershell
python tools\rough_cut_storyboard_preview.py `
  --matrix RUN_DIR\material_understanding\material_understanding_matrix.json `
  --rough-cut-plan RUN_DIR\preview_rough_cut_plan.json `
  --out RUN_DIR\multi_material_storyboard_preview.mp4 `
  --report RUN_DIR\rough_cut_storyboard_preview_report.json `
  --json
```

This is a review aid for material choice and order. It is not `final.mp4` and
does not verify motion timing.

Manual steps, when you need to inspect or override each artifact:

```powershell
python tools\material_understanding_matrix.py `
  --materials-db RUN_DIR\materials_db.json `
  --out-dir RUN_DIR\material_understanding `
  --max-assets 24 `
  --frame-budget 3 `
  --json
```

Use the contact sheet and matrix to write `material_wall_review_verdict.json`.
The matrix is observation only; it does not prove coverage or authorize BUILD.
For a bounded first pass, draft a conservative verdict with one primary keep
per role and alternates separated from formal keep/maybe:

```powershell
python tools\material_wall_verdict_draft.py `
  --matrix RUN_DIR\material_understanding\material_understanding_matrix.json `
  --out RUN_DIR\material_wall_review_verdict.draft.json `
  --roles opening,training,closing `
  --json
```

Review or edit the draft before using it as the `--wall-verdict` input. If an
alternate is better than the chosen primary, swap the statuses explicitly
instead of promoting every plausible asset.

To create only the preview proposal from existing matrix and draft verdict:

```powershell
python tools\material_first_preview_plan.py `
  --matrix RUN_DIR\material_understanding\material_understanding_matrix.json `
  --wall-verdict-draft RUN_DIR\material_wall_review_verdict.draft.json `
  --out RUN_DIR\preview_rough_cut_plan.json `
  --target-duration 72 `
  --json
```

```powershell
python tools\material_first_boundary_acceptance.py `
  --out RUN_DIR `
  --source-dir MATERIAL_SOURCE_DIR `
  --wall-verdict RUN_DIR\material_wall_review_verdict.json `
  --max-assets 12 `
  --json

python tools\pipeline_home.py --run RUN_DIR --json
```

Expected result:

```text
material_first_boundary_acceptance_report.json ok=true
pipeline_home source=material_first_boundary_acceptance_report.json
next=ready_for_render_or_human_review
final.mp4 absent
```

If this fails, repair the reported stage before BUILD. Do not render around a
failed material-first report.

### A2. One Long Source / Dialogue Highlight

Use this when the user gives one long source video, such as a 5-10 minute
finished clip, interview, podcast, lecture, or conversation, and asks for a
60-120 second highlight. This is still material-first. The source does not
become many independent materials; it becomes one source lineage with accepted
time windows.

The route is eye / ear / head:

```text
source video
  -> eyes: source-section-map + source-motion-profile + source-material-matrix
  -> ears: correct subtitle when available, otherwise reviewed ASR
  -> head: source-dialogue-script creates dialogue_edit_script.json
  -> human/agent reviews meaning and selected windows
  -> safe_highlight_cut creates a stable preview
  -> final-product-verify checks eye/ear evidence
```

For dialogue, the transcript is truthier than visual motion. Prefer a correct
subtitle or manual caption downloaded by `yt-dlp` over ASR. Use ASR only as a
fallback, and review it before using it as a semantic script. Do not force an
exact target duration by cutting half sentences; complete sentence flow is more
important than hitting 90 seconds exactly.

Typical commands:

```powershell
python tools\soundtrack_probe.py `
  --audio RUN_DIR\source\source.mp4 `
  --out RUN_DIR\source_soundtrack_probe_report.json `
  --enable-asr

python video_tools.py source-section-map `
  --video RUN_DIR\source\source.mp4 `
  --out RUN_DIR\source_section_map.json `
  --soundtrack-probe RUN_DIR\source_soundtrack_probe_report.json

python video_tools.py source-motion-profile `
  --video RUN_DIR\source\source.mp4 `
  --out-dir RUN_DIR\source_motion_profile

python video_tools.py source-material-matrix `
  --video RUN_DIR\source\source.mp4 `
  --out-dir RUN_DIR\source_matrix `
  --soundtrack-probe RUN_DIR\source_soundtrack_probe_report.json

yt-dlp --write-subs --write-auto-subs --sub-langs "en.*,zh.*" `
  --sub-format json3 --skip-download `
  --output RUN_DIR\source\subs.%(ext)s SOURCE_URL

python video_tools.py source-dialogue-script `
  --json3 RUN_DIR\source\subs.en.json3 `
  --out-dir RUN_DIR\dialogue_script `
  --rough-windows RUN_DIR\rough_dialogue_windows.json `
  --target-sec 90

python tools\safe_highlight_cut.py `
  --source RUN_DIR\source\source.mp4 `
  --windows RUN_DIR\dialogue_script\dialogue_highlight_windows.json `
  --out RUN_DIR\dialogue_highlight_cut.mp4 `
  --report RUN_DIR\highlight_cut_report.json

python video_tools.py final-product-verify `
  RUN_DIR\dialogue_highlight_cut.mp4 `
  --out-dir RUN_DIR\final_product_verify
```

Review `dialogue_edit_script.json` before cutting whenever the user's goal is
meaning, message, interview logic, or speech-first highlight. Keep original
speech audio unless the user explicitly asks for music overlay, replacement, or
ducking. If music is added under speech, route the mix through Soundtrack
Arranger / Audio Director and verify ducking.

### B. No Material / Story-First Generated Candidates

Use this when the user has a story idea or text but no usable visuals yet.

```text
brief
  -> story_soul_blueprint
  -> material_needs.json
  -> material_delta.json
  -> material_generation_fallback.json
  -> provider_packet/generated_provider_packet.json
  -> wait_for_generated_provider
  -> generated provider outputs
  -> generated-material-import
  -> generated_material_review.json
  -> reviewed project material map
  -> delta covered after review
```

Real-provider handoff wrapper:

```powershell
python tools\story_first_provider_happy_path.py `
  --out RUN_DIR `
  --title "月光森林裡迷路的小兔子" `
  --style "日式可愛繪本風格" `
  --target-duration 60 `
  --json
```

Expected `pipeline_home.py` result:

```text
mode=waiting
cursor=generated_image_provider
next=wait_for_generated_provider
final.mp4 absent
```

This is the correct stop point when no image-capable provider has written real
files yet. Do not substitute `test_pil` or text-card placeholders for final art.

Acceptance harness for shape-only regression:

```powershell
python tools\story_to_generated_material_e2e.py .tmp\story_to_generated_material_e2e
```

Expected result:

```text
ok=true
after_generation_delta missing=0 and thin>=1
after_review_delta covered=<need_count>
E2E_REVIEW.md and contact_sheet.jpg written
```

This proves the route shape and review promotion. It does not prove final art
quality because the harness uses deterministic storyboard cards. Real provider
outputs must still enter through `generated-material-import` and
`generated-material-review`.

### C. Designed Effects / Effect Factory

Use this when a segment needs a designed opening, transition, title card,
highlight, emotional overlay, or material-first finishing asset.

```text
fuzzy effect request
  -> visual_technique_plan.json
  -> visual_technique_review.json
  -> visual_technique_plan.confirmed.json
  -> effect contract / remotion prompt pack
  -> bounded worker output
  -> effect review / handoff
```

No-render semantic acceptance:

```powershell
python video_tools.py visual-technique-plan `
  --request "electric lightning opening with strong impact" `
  --effect-role opening_title `
  --duration-sec 6 `
  --out RUN_DIR\visual_technique_plan.json `
  --json

python tools\pipeline_home.py --run RUN_DIR --json
```

At this point `pipeline_home` should stop at
`effect_factory_parameter_review`. After a user/reviewer chooses an option:

```powershell
python video_tools.py visual-technique-review-apply `
  --plan RUN_DIR\visual_technique_plan.json `
  --review RUN_DIR\visual_technique_review.json `
  --out RUN_DIR\visual_technique_plan.confirmed.json

python tools\pipeline_home.py --run RUN_DIR --json
```

Expected result after apply:

```text
pipeline_home source=visual_technique_plan.confirmed.json
cursor=effect_factory_contract
next=effect_contract_or_remotion_prompt_pack
```

Broader no-render Effect Factory acceptance:

```powershell
python tools\effect_factory_boundary_acceptance.py --out RUN_DIR --json
```

Expected result:

```text
effect_factory_boundary_acceptance_report.json ok=true
multiple semantic families do not collapse into one generic template
final.mp4 absent
```

### D. Official Render / Delivery

Only run this after the current material/story/effect gates are green and
`pipeline_home.py` says the run is ready for BUILD/render or human review:

```powershell
python video_tools.py contract-run RUN_DIR\segment_contract.json `
  --material-db RUN_DIR\materials_db.json `
  --music RUN_DIR\bgm.mp3 `
  --out RUN_DIR\final.mp4 `
  --mat-dir RUN_DIR

python video_tools.py verify ...
python tools\validate_pipeline_run_folder.py RUN_DIR --complete-video
```

This is the point where a run can become a real video delivery. The acceptance
paths above are route proofs, not final videos.

## Stage 0: Video Intent Planner

Write or read `project_brief.json`, then create `video_intent.json`:

```powershell
python video_tools.py video-intent-plan RUN_DIR\project_brief.json --out RUN_DIR\video_intent.json
```

Stage 0 must decide:

- `input_state`: `material_available`, `text_available`, `idea_only`, or
  `unknown`;
- `entry_path`: `material-first`, `structure-first`, or `needs-context`;
- `video_type`, `audience`, `goal`;
- `target_length`, or a focused `required_followup_questions` item if unknown;
- material/text availability;
- generation permission;
- `material_contract`: the first material owner and gap policy;
- `soundtrack_contract`: `song`, `bgm`, `mixed`, `none`, or `unsure`, plus
  vocal policy and Soundtrack Arranger handoff if music is requested;
- `effect_policy`: whether a bounded effect routes to Effect Factory now or
  waits for Brownfield/segment review;
- `subtitle_voiceover_contract`: whole-video language, subtitle, narration,
  and voiceover intent. This is a reserved child contract; execution currently
  threads through Subtitle Director, Audio Director, BUILD, Verify, and
  Delivery;
- `handoff_to` and `handoff_packet`.

If route-changing information is missing, ask focused questions. Do not enter
Story Soul, Material Map, Effect Factory, or BUILD by guessing.

Soundtrack rule: Stage 0 only records the music choice. Songs with vocals,
instrumental BGM, mixed section music, and no-music are distinct values because
they change license, source, and ducking policy. Use Soundtrack Arranger after
Stage 0 for source candidates and license gates.

Soundtrack fallback rule: provider fallback is allowed, role fallback is not
silent. If a `song` or `mixed` contract cannot obtain a deliverable song,
Soundtrack Arranger may propose BGM/instrumental, but it must write
`role_fallback_requires_review` and stop before Audio Director. Workbench may
later replace or retime music after human/agent review. If Stage 0 marks
`speech_preservation=required`, BGM under speech-critical sections must duck
under voice or preserve original audio.

Effect rule: Stage 0 does not launch Remotion or an effect worker from fuzzy
whole-video language. It writes `effect_policy`; bounded effect requests may
route to Effect Factory, while whole-video transitions/highlights wait until
segment/Brownfield context exists.

Subtitle/voiceover rule: Stage 0 records whether subtitles, narration, or
voiceover matter, and what language they should use. It does not synthesize TTS
or burn subtitles. Missing language for required subtitle/voiceover work should
stay visible as a follow-up/gate item until Stage 2/5 expands it.

Downstream threading rule: `video_intent.json` child contracts must remain
visible after Stage 0. Material-first acceptance carries `stage0_contracts`
forward in `material_first_boundary_acceptance_report.json`. If that report
passes but `stage0_contracts.soundtrack.handoff_to=soundtrack-arranger`, the
next route is `soundtrack-arrange`, not render. Soundtrack/license/audio gates
must resolve before BUILD/delivery consumes final audio. `effect_policy` is
kept as a segment/Brownfield decision unless it is a bounded effect-only route.
`subtitle_voiceover_contract` stays visible for Stage 2/5/7/10. When subtitles
or voiceover are required, use `tools\subtitle_voiceover_handoff_accept.py` to
turn `subtitles.srt`, `caption_audit.json`, and `narration_manifest.json` into
`subtitle_voiceover_handoff_acceptance.json` and
`subtitle_voiceover_build_handoff.json` before BUILD/delivery treats the branch
as satisfied.

Stage 1/2 expansion rule: if a brief or blueprint carries
`stage0_child_contracts`, `story-soul-blueprint`, `story-soul-to-contract`, and
`blueprint-to-contract` must preserve them into `director_shot_plan`,
`material_needs`, and `segment_contract`. For Story Soul output, prefer the
direct bridge instead of hand-writing a parallel decisions file:

```powershell
python video_tools.py story-soul-blueprint RUN_DIR\project_brief.json --out-dir RUN_DIR\story_blueprint
python video_tools.py story-soul-to-contract --story-dir RUN_DIR\story_blueprint --out RUN_DIR\segment_contract.json
```

The expansion is informational and constraining: it gives BUILD/Verify visible
audio, subtitle, voiceover, material, and effect intent, but it does not satisfy
material coverage, license, effect review, or delivery evidence by itself.

Stage 5 handoff rule: `contract-adapt` / `contract-dry-build` must preserve
`stage0_child_contracts` into `generated_mv_script.json` / runtime payload.
That lets BUILD planning, Workbench, and reviewers see upstream soundtrack,
subtitle/voiceover, material, and effect intent. It still does not mean music
has been licensed, subtitles have been rendered, voiceover has been generated,
or effects have been reviewed. When accepted branch handoffs already exist in
the run folder, `contract-dry-build` and `contract-run` must also list them in
`artifact_manifest.json` so downstream agents do not need to rediscover branch
truth by filename scanning. At minimum this includes
`rough_cut_plan.json`, `audio_build_handoff.json`,
`subtitle_voiceover_build_handoff.json`, and `effect_handoff.json`.
`rough_cut_plan.json` is not re-authored by BUILD; it is listed so the final
timeline can be traced back to the material-first clip/window decision.

Subtitle/voiceover handoff rule: `subtitle_voiceover_build_handoff.json` is the
BUILD-facing evidence that required subtitles and/or voiceover have passed their
no-render checks. It can point to `subtitles.srt`, `caption_audit.json`, and
`narration_manifest.json`, but it does not burn subtitles or synthesize speech.
If `subtitle_voiceover_handoff_acceptance.json.ok=false`, repair this branch
before continuing to BUILD.

Stage 7/10 delivery evidence rule: `evaluate_delivery_gate()` reads
`stage0_child_contracts` from `segment_contract.json`, `generated_mv_script.json`,
or runtime payload. If Stage 0 required soundtrack, subtitles, voiceover, or a
required effect, delivery must have matching evidence or a branch handoff.
Accepted effect handoff evidence may be `effect_handoff.json` or
`remotion_effect_handoff.json`; rendered required effects should still produce
`effect_render_verification.json` before final delivery. This gate is allowed to
block even when `verify_result.pass=true`, because technical verify is not the
same as semantic delivery readiness. Deferred Brownfield effects do not block
until an effect contract or handoff makes them required.

## Material Map Branch

Use when real or partial media exists, or when generated candidates must be
reviewed before BUILD.

Material-first boundary acceptance:

```powershell
python tools\material_first_boundary_acceptance.py `
  --out RUN_DIR `
  --source-dir MATERIAL_SOURCE_DIR `
  --wall-verdict RUN_DIR\material_wall_review_verdict.json `
  --max-assets 12 `
  --json
```

Rules:

- Use the operator-provided `--source-dir` exactly.
- If the folder is missing, stop as blocked.
- Do not substitute a neighboring folder.
- Do not continue to render if
  `material_first_boundary_acceptance_report.json` returns `ok=false`.

Core material tools:

```powershell
python video_tools.py project-material-map --maps-dir RUN_DIR\maps --needs RUN_DIR\material_needs.json --out RUN_DIR\project_material_map.json
python video_tools.py material-map-lifecycle --out-dir RUN_DIR --needs RUN_DIR\material_needs.json --project-map RUN_DIR\project_material_map.json --contract RUN_DIR\segment_contract.json
python video_tools.py material-delta --needs RUN_DIR\material_needs.json --project-map RUN_DIR\project_material_map.json --out RUN_DIR\material_delta.json
python tools\material_gap_brief.py --delta RUN_DIR\material_delta.json --needs RUN_DIR\material_needs.json --out RUN_DIR\material_gap_brief.json --shooting-out RUN_DIR\shooting_brief.md
```

Cut strategy presets:

- `material_rough_cut.py`: creates the reviewable clip/window plan from
  material-map facts, review verdicts, and usable ranges. It decides what to
  cut, not how to encode it.
- `safe_highlight_cut.py`: turns accepted windows into a stable playable MP4 by
  re-encoding to H.264/AAC. Use this for yt-dlp, VP9/Opus, non-keyframe, or
  stutter-prone sources. It writes `highlight_cut_report.json`.

```powershell
python tools\safe_highlight_cut.py `
  --rough-cut-plan RUN_DIR\rough_cut_plan.json `
  --out RUN_DIR\final_safe_tool.mp4 `
  --report RUN_DIR\highlight_cut_report.json
```

Use `--source ... --windows ...` only when a human/Workbench has already
exported a standalone windows file. The `--rough-cut-plan` path is the default
material-first handoff because it preserves segment labels and source windows.

Single-source highlight policy:

- A single source does not become multi-material after cutting. It remains a
  single-source lineage with multiple accepted time windows.
- For `segment_contract.mode=single_source_highlight`, delivery may allow
  repeated source usage only when `highlight_cut_report.json` proves a safe
  re-encoded cut from `rough_cut_plan.json`.
- This route judges temporal diversity and required anchor coverage, not source
  diversity. Anchors such as a named person, ceremony moment, bridge shot,
  group photo, or required event must be explicit `material_needs`.
- Intentional replay or emphasis repetition must be marked in the rough cut with
  a repeat policy and reason. Unmarked repetition is treated as fatigue or
  material shortage, not design.

Generated candidate branch:

```powershell
python video_tools.py material-generation-fallback RUN_DIR\material_delta.json --needs RUN_DIR\material_needs.json --out RUN_DIR\material_generation_fallback.json
python video_tools.py generated-image-provider-packet RUN_DIR\material_generation_fallback.json --out-dir RUN_DIR\provider_packet
python video_tools.py generated-material-import ...
python video_tools.py generated-material-review ...
```

Generated files are candidates until explicit review accepts them.

## Effect Factory Branch

Use when a route needs designed effect assets:

- opening title or hook;
- transition;
- title card;
- lower third;
- emotional overlay;
- photo wall / memory plate;
- lightning, crack, heart, sakura, fire/legacy, magic, impact visuals.

Read:

```text
skills/video-effect-factory.md
docs/effect-factory-route.md
skills/remotion-effect-worker.md
```

Effect Factory owns:

```text
effect_design_map.json
effect_contract.json
effect_review.json
effect_handoff.json
```

Remotion worker owns bounded build outputs:

```text
remotion_prompt_pack.json
remotion_worker_outputs.json
remotion_effect_review.json
remotion_effect_handoff.json
```

Remotion is not the main renderer. It produces bounded effect assets for review.
Final assembly remains ffmpeg / `contract-run` unless a reviewed route promotes
a draft asset.

Effect Factory semantic contract acceptance:

```powershell
python video_tools.py visual-technique-plan `
  --request "electric lightning opening with strong impact" `
  --effect-role opening_title `
  --duration-sec 6 `
  --out RUN_DIR\visual_technique_plan.json `
  --json

python tools\effect_factory_boundary_acceptance.py --out RUN_DIR --json
```

Use this before a real E2E when changing effect vocabulary, style-family
translation, prompt parameters, or handoff rules. It checks that different
semantic families such as lightning, crack, hearts, and legacy fire do not
collapse into one generic template. `visual-technique-plan` defaults to
review-only candidate parameters; use `--confirmed` only after user/reviewer
acceptance. These commands are no-render checks; `final.mp4` must remain absent.

After writing `visual_technique_plan.json`, inspect the route surface:

```powershell
python tools\pipeline_home.py --run RUN_DIR --json
```

Candidate plans stop at `effect_factory_parameter_review`; confirmed plans move
to `effect_factory_contract`. If the user/reviewer selects an option, write
`visual_technique_review.json`, then apply it:

```powershell
python video_tools.py visual-technique-review-apply `
  --plan RUN_DIR\visual_technique_plan.json `
  --review RUN_DIR\visual_technique_review.json `
  --out RUN_DIR\visual_technique_plan.confirmed.json
```

Common Remotion adapter commands:

```powershell
python video_tools.py remotion-prompt-pack ...
python video_tools.py remotion-worker-smoke --dry-run ...
python video_tools.py remotion-worker-outputs ...
python video_tools.py remotion-composite-draft ...
```

Material-first Remotion memory acceptance:

```powershell
python tools\remotion_material_first_memory_acceptance.py `
  --run-dir RUN_DIR `
  --project-map RUN_DIR\project_material_map.json `
  --wall-verdict RUN_DIR\material_wall_review_verdict.json `
  --wall-request RUN_DIR\verify\material_wall\material_wall_request.json `
  --json
```

## Soundtrack Arranger Branch

Use when the route needs music, songs, BGM, voiceover mood, speech preservation,
or license/source decisions before Audio Director.

Read:

```text
skills/soundtrack-arranger.md
docs/soundtrack-arranger-route.md
skills/audio-director.md
```

Soundtrack Arranger owns:

```text
soundtrack_plan.json
music_source_candidates.json
sound_license_manifest.json
audio_director_handoff.json
```

No provider token is required for this planning step. Jamendo/Pixabay
credentials are optional API layer inputs for later provider search; famous
songs and YouTube references stay `reference_only` until license evidence
exists.

Minimal command:

```powershell
python video_tools.py soundtrack-arrange RUN_DIR\video_intent.json --out-dir RUN_DIR
```

Stop before Audio Director when `audio_director_handoff.json` reports blocks
such as `license_missing`, `reference_only`, or `speech_policy_missing`.

Optional provider search and download:

```powershell
python video_tools.py soundtrack-provider-search `
  --plan RUN_DIR\soundtrack_plan.json `
  --out RUN_DIR\music_source_candidates.json `
  --providers jamendo,pixabay `
  --limit 3

python video_tools.py soundtrack-provider-download `
  --candidates RUN_DIR\music_source_candidates.json `
  --candidate-id CANDIDATE_ID `
  --out-dir RUN_DIR

python video_tools.py soundtrack-import-url `
  --url "https://www.youtube.com/watch?v=..." `
  --section-id mv_climax `
  --source-type youtube_audio_library `
  --usage-scope internal_only `
  --license-note "user confirmed internal classroom use" `
  --out-dir RUN_DIR

python video_tools.py soundtrack-audio-handoff-accept `
  --handoff RUN_DIR\audio_director_handoff.json `
  --soundtrack-plan RUN_DIR\soundtrack_plan.json `
  --license-manifest RUN_DIR\sound_license_manifest.json `
  --out-dir RUN_DIR
```

Jamendo uses `JAMENDO_CLIENT_ID` and can return deliverable song candidates with
`audiodownload` plus license metadata. Pixabay uses `PIXABAY_API_KEY`, but
Pixabay music is not available through the documented official API surface; the
provider search reports `provider_unavailable` for audio. If a reviewed Pixabay
or other licensed track is manually imported with `direct_download_url`, the
download command can still fetch it and write `sound_license_manifest.json` plus
`audio_director_handoff.json`.

Priority rule: for songs/vocals, use Jamendo first. Use `soundtrack-import-url`
as a fallback for internal/non-public videos or manually licensed sources. URL
import requires `--license-note` or `--license-url`; `reference_only` sources
must not be imported into deliverable audio.

`soundtrack-audio-handoff-accept` is the no-render gate before mixing. It writes
`audio_handoff_acceptance.json` and `audio_mix_plan.json`; only a passing
acceptance should move to Audio Director mixing.

This is not final delivery.

No-render boundary acceptance for the whole Soundtrack -> Audio Director handoff:

```powershell
python tools\soundtrack_flow_acceptance.py `
  --input RUN_DIR\video_intent.json `
  --out-dir RUN_DIR `
  --selected-section-id mv_climax `
  --source-type youtube_audio_library `
  --license-note "user confirmed internal classroom use" `
  --fake-reviewed-audio `
  --json
```

This verifies `soundtrack_plan.json`, selected audio/license handoff,
`audio_handoff_acceptance.json`, `audio_mix_plan.json`, and `pipeline_home.py`
state without downloading real music, mixing, or rendering.

Once `audio_mix_plan.json` is accepted, execute audio-only mix output:

```powershell
python tools\audio_mix_plan_execute.py `
  --plan RUN_DIR\audio_mix_plan.json `
  --acceptance RUN_DIR\audio_handoff_acceptance.json `
  --out-dir RUN_DIR `
  --json
```

This writes `final_audio.wav` and `audio_mix_report.json` only. It does not
render `final.mp4`; after it passes, `pipeline_home.py` should return
`cursor=audio_ready` and `next=return_to_build_with_final_audio`.

For section-aware music placement, include `sections[]` in `audio_mix_plan.json`.
Audio Director will place each track by `section_id`, trim it to
`duration_sec`, apply optional `fade_in_sec` / `fade_out_sec`, and write the
actual `placements[]` into `audio_mix_report.json`. Without `sections[]`, the
tool keeps simple single-track or concat behavior.

For speech or preserved original audio, put a voice/original-audio track in the
same section and set the music track `ducking_policy=duck_under_voice`. The
report must show `ducking_applied=true` and a lowered `applied_volume` for that
music placement. If a speech-critical section cannot prove this, repair the
audio plan before BUILD.

`audio_mix_report.json` must also carry level evidence. Audio Director writes
`mean_dbfs` and `peak_dbfs`; delivery blocks mixes with `peak_dbfs > -0.5` and
blocks required ducking that did not apply.

To hand accepted audio back into BUILD without rendering video, run the normal
dry-build after `final_audio.wav` exists:

```powershell
python video_tools.py contract-dry-build RUN_DIR\segment_contract.json `
  --categories examples\material_categories.json `
  --out-dir RUN_DIR

python tools\pipeline_home.py --run RUN_DIR --json
```

Expected BUILD audio handoff:

```text
audio_build_handoff.json
artifact_manifest.audio_build_handoff = RUN_DIR\audio_build_handoff.json
artifact_manifest.final_audio = RUN_DIR\final_audio.wav
pipeline_home cursor=audio_build_handoff
pipeline_home next=continue_build_or_material_gate
final.mp4 absent in dry-build
```

This is the correct stop point for no-render audio-to-BUILD validation. Do not
run `contract-run` or render `final.mp4` unless the user explicitly asks for a
full render after the material and delivery gates are clean.

## BUILD And Official Render

Only render after current gates pass.

Minimal canonical contract run:

```powershell
python video_tools.py contract-run RUN_DIR\segment_contract.json `
  --material-db RUN_DIR\materials_db.json `
  --music RUN_DIR\bgm.mp3 `
  --out RUN_DIR\final.mp4 `
  --mat-dir RUN_DIR
```

Do not use stale `material_delta.json`. Do not bypass pre-BUILD gates.

## Verify And Delivery

Run verify/audits appropriate to the route:

```powershell
python video_tools.py verify ...
python video_tools.py black-frame-audit ...
python video_tools.py caption-audit ...
python video_tools.py keyframe-grid ...
python video_tools.py visual-audit ...
python tools\write_delivery_gate_report.py --run RUN_DIR --json
python tools\validate_pipeline_run_folder.py RUN_DIR --complete-video
```

`verify_result.json` is technical verify evidence only. A run can have
`verify_result.pass=true` and still be blocked by material truth, subtitle,
audio, effect, or delivery semantics. Always read or write `delivery_gate.json`
before claiming the run is deliverable. `delivery_gate.json` is the persisted
delivery report for agents and the dashboard; it should carry
`generated_by=tools/write_delivery_gate_report.py` and
`report_source=dashboard_state.artifacts.delivery_gate` when written by the
canonical tool.

Before claiming delivery:

- `final.mp4` exists from the current run;
- duration matches target length or has an explicit waiver;
- required narration/music/subtitle/audio manifests exist when required;
- subtitles are readable on screen, not merely text-matching;
- real-material routes have frame evidence;
- generated-material routes have prompt lineage and explicit generated review;
- planned effects have `effect_render_verification.json` or accepted handoff
  evidence;
- no reviewer has unresolved `revise`, `soft_block`, or `hard_block`;
- `--complete-video` has no warning channel: warnings are errors.

## Workbench / Dashboard

Dashboard is a review surface. Workbench is a draft editing surface.

```powershell
python tools\dashboard_server.py --root RUN_DIR --port 8765
python tools\workbench_server.py --artifact-root RUN_DIR --port 8770
```

Workbench may write:

- `preview_timeline.json`
- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- subtitle/audio/effect draft patches

Workbench must not overwrite:

- `segment_contract.json`
- `project_material_map.json`
- `material_needs.json`
- `timeline_build.json`
- `final.mp4`

Workbench handoff is a route-back artifact, not canonical truth. When
`workbench_handoff.json` contains `route_back`, stop at
`review_workbench_route_back` and send each draft patch back to its owner:

| Draft patch | Owner route | Why |
| --- | --- | --- |
| `timeline_patch.json` with `replace_clip` / `insert_clip` | Material Map | clip replacement changes material truth |
| `timeline_patch.json` with `set_duration` / `set_source_window` / `move_clip` | BUILD planning | timing/order changes the build plan |
| `subtitle_patch.json` | Subtitle Director | readability and language policy must be preserved |
| `audio_cue_patch.json` | Audio Director | mix, ducking, and license policy must be preserved |
| `effect_patch.json` | Effect Factory | effects must return through effect contract/review |

Validate handoff:

```powershell
python video_tools.py workbench-handoff-validate RUN_DIR --out RUN_DIR\workbench_handoff_report.json
python video_tools.py workbench-draft-rerender RUN_DIR --out RUN_DIR\workbench_rerender.mp4
```

Draft rerenders are not canonical delivery.

## Multi-Agent Execution

Use bounded route task packets. Parent agent remains orchestrator.

```powershell
python video_tools.py route-task-next RUN_DIR --out RUN_DIR\route_subagent_task.json
python video_tools.py route-task-accept `
  --task RUN_DIR\route_subagent_task.json `
  --result RUN_DIR\route_subagent_result.json `
  --state-out RUN_DIR\route_orchestrator_state.json
python video_tools.py route-orchestrator-acceptance RUN_DIR `
  --route existing-material-first `
  --stage-count 4 `
  --out RUN_DIR\route_orchestrator_acceptance.json
```

Operator rule:

- short decision/review tasks can be delegated to subagents;
- long renders should be launched/monitored by the parent or a durable runner;
- subagents should read/write artifacts, not depend on conversation memory;
- if a gate blocks, stop and return the artifact reason.

## Test Tiers

Use focused tests first:

```powershell
python -m unittest tests.test_canonical_route_acceptance -v
python -m unittest tests.test_effects_roadmap_alignment_docs -v
python -m unittest tests.test_remotion_worker_bridge tests.test_remotion_effects -v
```

Broader tests:

```powershell
python -m unittest discover -s tests -v
```

For frontend changes, also run browser checks against the dev server or local
server; do not claim frontend work from unit tests only.

## Troubleshooting

- If a run unexpectedly starts local Ollama/qwen, treat it as legacy opt-in
  leakage unless the command explicitly requested local VLM.
- If Material Map says ready but BUILD says zero supply, inspect whether review
  verdicts were applied to scene/need satisfies edges.
- If effects look generic, check `effect_contract.json` before blaming the
  worker. Vague intent should not be sent directly to a backend.
- If Chinese text becomes `????`, inspect source artifact encoding first, then
  renderer/font handling.
- If `final.mp4` exists after a blocked build, treat it as stale until the
  current route writes and verifies it.
