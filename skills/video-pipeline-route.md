---
name: video-pipeline-route
description: Use when the user asks to make, edit, cut, review, plan, add effects to, or export a video in Hermes; includes fuzzy video requests, existing footage, story-only ideas, draft edits, rendering, and delivery
---

# Video Pipeline Route Skill

This is the operator entry skill for the full Hermes Video Pipeline.

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "video-pipeline-route",
  "stage_owner": "route_stage0_orchestrator",
  "triggers": [
    "User requests video editing, creation, pipeline reruns, or next action determination",
    "Needs to read run folder state, create entry brief, or dispatch side branches"
  ],
  "canonical_tools": [
    {
      "tool": "tools/pipeline_home.py",
      "when": "Read the current cursor, mode, and next action of the run folder to prevent agents from guessing the route",
      "inputs": [
        "run folder"
      ],
      "outputs": [
        "pipeline_home state JSON"
      ],
      "stop_if": [
        "mode=waiting",
        "next action asks for repair or review"
      ],
      "capability_id": "cap.video-pipeline-route.pipeline-home.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L0",
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/video_intent_acceptance.py",
      "when": "驗證 Stage 0 Video Intent Planner 與模糊需求分流",
      "inputs": [
        "brief text or fixture"
      ],
      "outputs": [
        "video_intent_acceptance_report.json"
      ],
      "stop_if": [
        "required_followup_questions remains unresolved"
      ],
      "capability_id": "cap.video-pipeline-route.video-intent-acceptance.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L0",
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/operator_flow_acceptance.py",
      "when": "驗證 bounded operator package 是否完整，不做正式 render",
      "inputs": [
        "operator run folder"
      ],
      "outputs": [
        "operator_flow_acceptance_report.json"
      ],
      "stop_if": [
        "report ok=false",
        "protected artifacts changed unexpectedly"
      ],
      "capability_id": "cap.video-pipeline-route.operator-flow-acceptance.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L0",
        "L5"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/preflight.py",
      "when": "開工前檢查環境:python/ffmpeg/node/依賴模組/API key 是否就緒",
      "inputs": [
        "repo root",
        ".env.example key names"
      ],
      "outputs": [
        "capability summary JSON + human report"
      ],
      "stop_if": [
        "--strict 模式下缺硬性依賴"
      ]
    },
    {
      "tool": "tools/canonical_route_acceptance.py",
      "when": "回歸 canonical route artifacts 與 route surface",
      "inputs": [
        "route fixture or run folder"
      ],
      "outputs": [
        "canonical route acceptance report"
      ],
      "stop_if": [
        "route artifact is missing or stale"
      ]
    },
    {
      "tool": "tools/pipeline_map.py",
      "when": "產生人類可讀的 pipeline/tool/artifact map",
      "inputs": [
        "repo root"
      ],
      "outputs": [
        "pipeline map report"
      ],
      "stop_if": [
        "map generation fails"
      ]
    },
    {
      "tool": "tools/run_artifact_index.py",
      "when": "operator, dashboard, or agent needs a compact review index for a run folder instead of reading every generated file",
      "inputs": [
        "run folder"
      ],
      "outputs": [
        "run_artifact_index.json"
      ],
      "stop_if": [
        "run folder is missing",
        "decision/contract/evidence files are hidden as debug noise"
      ]
    },
    {
      "tool": "tools/skill_tool_contract_audit.py",
      "when": "檢查 skills/*.md 的 Tool Contract 與 tools/*.py 歸屬是否完整",
      "inputs": [
        "skills directory",
        "tools directory"
      ],
      "outputs": [
        "skill_tool_contract_audit_report"
      ],
      "stop_if": [
        "unowned tool exists",
        "contract block is malformed"
      ]
    },
    {
      "tool": "tools/pipeline_interface_audit.py",
      "when": "審計主線與支線的 pipeline API/interface 字典，確認各支線 request、handoff、repair 接口都有對齊",
      "inputs": [
        "optional dictionary path",
        "optional branch registry path"
      ],
      "outputs": [
        "pipeline_interface_audit_report"
      ],
      "stop_if": [
        "major side branch lacks request/handoff/repair coverage",
        "referenced tool is missing",
        "protected canonical output can be written by a side branch interface"
      ]
    },
    {
      "tool": "tools/pipeline_interface_discovery.py",
      "when": "自動探查主線與支線可能漏登的 pipeline API/interface 候選者並與字典對照",
      "inputs": [
        "optional dictionary path",
        "optional branch registry path",
        "optional skills-dir",
        "optional tools-dir"
      ],
      "outputs": [
        "pipeline_interface_discovery_report"
      ],
      "stop_if": [
        "missing candidates detection error"
      ]
    },
    {
      "tool": "tools/product_artifact_dictionary_audit.py",
      "when": "審計產品產物字典，確認上游語意能對應到剪輯、音訊、特效、字幕口白與驗證的功能性參數",
      "inputs": [
        "optional product artifact dictionary path"
      ],
      "outputs": [
        "pipeline_product_artifact_dictionary_audit_report"
      ],
      "stop_if": [
        "required product artifacts are missing",
        "functional parameters are missing"
      ]
    },
    {
      "tool": "tools/compile_edit_decision_plan.py",
      "when": "從 rough cut 與 audio/effect/subtitle handoff 編譯 edit_decision_plan 與 build_handoff，不 render",
      "inputs": [
        "run folder with rough_cut_plan and optional branch handoffs"
      ],
      "outputs": [
        "edit_decision_plan.json",
        "audio_decision_plan.json",
        "effect_decision_plan.json",
        "subtitle_voiceover_decision_plan.json",
        "build_handoff.json"
      ],
      "stop_if": [
        "required material rough cut is missing",
        "deferred branch handoffs must be resolved before BUILD"
      ]
    },
    {
      "tool": "tools/route_orchestrator_acceptance.py",
      "when": "驗證 route task packet / runner protocol 不被 worker 越界",
      "inputs": [
        "route task fixture"
      ],
      "outputs": [
        "route orchestrator acceptance report"
      ],
      "stop_if": [
        "task packet violates must_not_touch or freshness rules"
      ]
    },
    {
      "tool": "tools/srp_acceptance_replay.py",
      "when": "重播 subagent runner protocol acceptance case",
      "inputs": [
        "SRP fixture"
      ],
      "outputs": [
        "SRP replay report"
      ],
      "stop_if": [
        "replay diverges from expected route state"
      ]
    },
    {
      "tool": "tools/srp_real67_fuller_replay.py",
      "when": "針對第67期案例重播較完整 route 行為",
      "inputs": [
        "real67 fixture/run folder"
      ],
      "outputs": [
        "real67 replay report"
      ],
      "stop_if": [
        "route state blocks or fixture is stale"
      ]
    },
    {
      "tool": "tools/srp_real67_review_demo.py",
      "when": "示範 real67 reviewer handoff，不作正式 build",
      "inputs": [
        "real67 review fixture"
      ],
      "outputs": [
        "review demo report"
      ],
      "stop_if": [
        "review artifact missing"
      ]
    },
    {
      "tool": "tools/srp_real67_sanity.py",
      "when": "快速檢查 real67 route artifacts 是否仍可讀",
      "inputs": [
        "real67 run folder"
      ],
      "outputs": [
        "sanity report"
      ],
      "stop_if": [
        "required artifact missing"
      ]
    },
    {
      "tool": "tools/validate_pipeline_run_folder.py",
      "when": "驗證 run folder 結構和必備 artifacts",
      "inputs": [
        "run folder"
      ],
      "outputs": [
        "run folder validation report"
      ],
      "stop_if": [
        "layout invalid"
      ]
    },
    {
      "tool": "tools/doc_reference_hygiene.py",
      "when": "Check documentation references that route reports and registries depend on",
      "inputs": [
        "docs tree",
        "reference manifest"
      ],
      "outputs": [
        "doc reference hygiene report"
      ],
      "stop_if": [
        "missing or stale reference is found"
      ]
    },
    {
      "tool": "tools/factory_improvement_loop.py",
      "when": "Run route-level improvement-loop evidence for factory/product-route closure",
      "inputs": [
        "run folder",
        "route artifacts"
      ],
      "outputs": [
        "factory improvement loop report"
      ],
      "stop_if": [
        "loop evidence is missing or blocks"
      ]
    },
    {
      "tool": "tools/film_canon_readiness.py",
      "when": "Evaluate film-canon product-route readiness before production handoff",
      "inputs": [
        "film canon artifacts",
        "review decision"
      ],
      "outputs": [
        "film canon readiness report"
      ],
      "stop_if": [
        "readiness is waiting, repair, or unknown"
      ]
    },
    {
      "tool": "tools/film_canon_route.py",
      "when": "Create or inspect registered film-canon route artifacts without rendering delivery output",
      "inputs": [
        "film type",
        "source metadata",
        "brief"
      ],
      "outputs": [
        "film canon route artifacts"
      ],
      "stop_if": [
        "unknown film type or required source metadata is missing"
      ]
    },
    {
      "tool": "tools/graduation_film_blueprint_catalog.py",
      "when": "Build graduation film blueprint/catalog planning artifacts for the product route",
      "inputs": [
        "graduation brief",
        "source metadata"
      ],
      "outputs": [
        "graduation blueprint and catalog artifacts"
      ],
      "stop_if": [
        "catalog assignments need human confirmation"
      ]
    },
    {
      "tool": "tools/route_closure_integrity.py",
      "when": "Check that route-closure artifacts are pipeline-owned and not self-authored substitutes",
      "inputs": [
        "run folder",
        "closure artifacts"
      ],
      "outputs": [
        "route closure integrity report"
      ],
      "stop_if": [
        "closure artifact provenance is missing or invalid"
      ]
    },
    {
      "tool": "tools/run_graduation_product_route.py",
      "when": "Run the graduation product-route harness through canon, catalog, readiness, and review packet stages",
      "inputs": [
        "fixture or source metadata",
        "route options"
      ],
      "outputs": [
        "graduation product route harness result"
      ],
      "stop_if": [
        "harness stops at waiting, repair, unknown, or missing evidence"
      ]
    },
    {
      "tool": "tools/visual_selection_gate.py",
      "when": "Gate render-facing visual selections before production handoff",
      "inputs": [
        "visual selection candidates",
        "review decision"
      ],
      "outputs": [
        "visual selection gate report"
      ],
      "stop_if": [
        "accepted selection lacks visual confirmation evidence"
      ]
    },
    {
      "tool": "tools/write_product_route_review_decision.py",
      "when": "Write the human product-route review decision consumed by readiness checks",
      "inputs": [
        "reviewer decision",
        "review packet"
      ],
      "outputs": [
        "product_route_review_decision.json"
      ],
      "stop_if": [
        "reviewer is non-human or decision is incomplete"
      ]
    },
    {
      "tool": "tools/write_visual_selection_review.py",
      "when": "Write the human visual-selection review decision for sensitive render-facing choices",
      "inputs": [
        "reviewer decision",
        "candidate evidence"
      ],
      "outputs": [
        "visual_selection_review.json"
      ],
      "stop_if": [
        "review lacks reviewer, evidence, forbidden-role checks, or reason"
      ]
    },
    {
      "tool": "tools/run_graduation_opening_slice.py",
      "when": "Replay the legacy Canon 67 0-44 opening as a bounded technical acceptance/control; it is not the editing-loop front door",
      "inputs": [
        "accepted seed run",
        "read-only source root",
        "opening slice request"
      ],
      "outputs": [
        "Canon 67 opening technical control artifacts",
        "technical acceptance report"
      ],
      "stop_if": [
        "technical acceptance blocks",
        "source provenance or reference-footage exclusion fails"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not call contract-run from a fuzzy request",
    "Do not render final.mp4 before pipeline_home and gates are green",
    "Do not use route_judgment as a replacement for video_intent.json"
  ],
  "capability_namespace": "cap.video-pipeline-route.*",
  "capability_lookup_owner": "video-pipeline-route"
}
<!-- TOOL_CONTRACT_END -->

Shared hard boundary: read `skills/pipeline-boundary.md`. Stage 0 entry lock
applies to this route. Do not direct-cut from a fuzzy request.

Read `RUNBOOK.md` first for the semantic operation table. Then read
`docs/START_HERE_VIDEO_PIPELINE.md` and `docs/pipeline-decision-tree.md`. Use
`docs/video-pipeline-operating-map.md` as the stage/tool/artifact checklist and
`docs/canonical-video-pipeline-route.md` as the route definition. Use
`docs/stage-boundary-matrix.md` when dispatching workers or deciding what a
stage may write. When the project needs story quality before material work, read
`docs/upstream-story-route.md`. When the project needs designed effect assets,
read `docs/effect-factory-route.md` and `skills/video-effect-factory.md`.

## Semantic Trigger Router

Use this table before searching for tools. If a run folder already exists, run
`python tools/pipeline_home.py --run RUN_DIR --json` first and follow its
cursor/next action.

Precedence: resume existing runs before new intake; whole-video requests go
through Stage 0 before side branches; side-branch words such as music,
transition, warm, hot-blooded, subtitle, effect, or cinematic are child intents
unless the request is clearly bounded to that branch. Bounded music/song/BGM
intent may enter Soundtrack Arranger; volume repair belongs to Audio Director or
Brownfield/Workbench. Whole-video subtitle intent stays a child intent after
Stage 0; subtitle repair on an existing draft belongs to Subtitle Director or
Brownfield/Workbench. Generated candidate fallback happens after story/needs
and material delta, not directly from a fuzzy idea.

Stage 0 package is `project_brief.json`, `interaction_log.md`, and
`video_intent.json`. `video_intent.json` must include `target_length` when the
user provides one; if target length or another route-changing fact is unknown,
write it in `required_followup_questions` and stop before branch work.

| User says | Entry | First safe action | Stop condition |
|---|---|---|---|
| "this run is stuck", "continue this run", "resume" | Resume existing run | read `pipeline_home.py --run RUN_DIR --json` | unknown run, repair cursor, unresolved gate/review |
| "help me cut a video", "make a recap", "edit a graduation film" | Stage 0 Video Intent Planner | write/read the Stage 0 package: `project_brief.json`, `interaction_log.md`, `video_intent.json` | `required_followup_questions` is non-empty |
| "I have footage", "use this folder", "existing materials" | Material-first | Material Map branch and material wall/review acceptance | material-first report is `repair:*` or missing needs |
| "no footage", "I have a story/article/idea" | Structure-first | upstream story route, material needs, generated candidate fallback | generated assets are not reviewed |
| "opening / transition / effect", "make it cinematic", "lightning/fire/hearts" | Effect Factory | `visual_technique_plan.json` and parameter review | unconfirmed candidate parameters |
| "edit this draft", "change this rough cut", "swap a clip" | Workbench / Brownfield | validate draft patch, keep it non-canonical | patch would overwrite canonical truth |
| "export final video", "render final.mp4" | Delivery gate | inspect `pipeline_home.py`, then only render if gates are green | any repair cursor, missing verification, or stale material |

Do not turn a semantic trigger into a direct command. Translate the request into
the entry, artifacts, allowed tools, and stop condition first. `RUNBOOK.md` is
the operator manual, `docs/pipeline-decision-tree.md` is the branch decision
tree, `pipeline_home.py` is the state reader, and `docs/stage-boundary-matrix.md`
is the write-boundary table.

A route note is not a route artifact. `route_judgment is not a Stage 0 artifact`;
`route_judgment.md/json` may be useful commentary, but it does not
advance the pipeline. For any "help me cut" or "I have footage" request, write
or refresh the Stage 0 package: `project_brief.json`, `interaction_log.md`, and
`video_intent.json`, or return
`needs-context` with follow-up questions. After Stage 0, `pipeline_home.py must not remain unknown`;
if it does, the worker has not produced a recognized
handoff artifact yet.

When the user has footage but asks for a story-shaped video, `material-first owns the route before story structure`.
Do not switch to upstream story just because the intended edit has a story arc.
Run material map first; `story structure must be derived from material-map facts`
such as actual scenes, speeches, actions,
usable ranges, repeated material, and gaps. The story skeleton may be drafted
after those facts are visible.

For material-map-only requests, `Material Delta is the next gate, not a forbidden action`.
It is forbidden to jump to BUILD/render from material inventory, but it
is valid to produce `material_delta.json` after material maps/review edges exist
so the route can decide build, generated fallback, reshoot, rewrite, drop, or
waiver.

## Core Rule

Do not jump straight to render.

Stage 0 is **Video Intent Planner**. Always decide **input state** first, then
the entry path:

```text
Video Intent Planner
-> input_state: material_available | text_available | idea_only | unknown
-> entry_path: material-first | structure-first | needs-context
draft review / brownfield edit
```

Then produce or verify the artifacts for the current stage.

Stage 0 owns the canonical `video_intent.json` artifact and keeps the full
Stage 0 package visible: `project_brief.json`, `interaction_log.md`, and
`video_intent.json`. Produce the intent artifact with:

```powershell
python video_tools.py video-intent-plan project_brief.json --out video_intent.json
```

It must include `input_state`, `entry_path`, `video_type`, `audience`, `goal`,
`material_availability`, `text_availability`, `route`,
`material_contract`, `material_scan_decision`, `soundtrack_contract`, `effect_policy`,
`subtitle_voiceover_contract`,
`stage0_child_contracts`,
`required_followup_questions`, `assumptions`, and `handoff_to`.
If route-changing information is missing, ask the follow-up questions instead
of guessing or entering Story Soul/BUILD.

Stage 0 artifact ownership:

- `project_brief.json` / `brief.json` is raw input.
- `video_intent.json` is the canonical Stage 0 route decision.
- `route_decision.json` is legacy/compat unless a current harness explicitly
  requires it.
- `input_state` records `material_available`, `text_available`, `idea_only`, or
  `unknown`.
- `entry_path` records `material-first`, `structure-first`, or `needs-context`;
  hybrid is not a primary Stage 0 entry path.
- `material_contract` records the first material owner and gap policy.
- `material_scan_decision` records whether the single Stage 0 entry should ask
  for a scan scope and then run quick inventory. For material-first editing,
  default to scanning all materials first unless the user names a folder/file
  scope. This is not a second route; it is the first observation step before
  deeper Material Map review and interaction.
- `soundtrack_contract` records whether the route wants `song`, `bgm`, `mixed`,
  `none`, or `unsure`; bounded music work may then enter Soundtrack Arranger.
- `effect_policy` records effect intent without launching Remotion. Only a
  bounded effect request routes directly to Effect Factory; whole-video style
  effects wait for Brownfield/segment review.
- `subtitle_voiceover_contract` is the reserved child contract for whole-video
  subtitle language, narration, and voiceover intent. It usually threads into
  Director Shot Plan, Subtitle Director, Audio Director, Verify, and Delivery
  instead of becoming a separate first route.
- Every child contract must expose `contract_status` using
  `required`, `optional`, `deferred`, or `not_applicable`. Keep the legacy
  `status=requested|unspecified` field for compatibility, but downstream gates
  should use `contract_status` for stop/go decisions.
- `stage0_child_contracts` mirrors the material, soundtrack, effect,
  subtitle/voiceover, and communication contracts so adapters can pass Stage 0
  intent forward without re-detecting it.

The first upstream role is a Video Intent Planner. It may behave like a
teacher, personal video editor, event director, brand editor, or storybook
writer depending on the user's goal and material availability. Do not force a
teaching or personal video into a generated story route.

## Route Boundary

The route owns orchestration, handoff, and stop/go decisions. It does not own
every implementation detail.

Route owns:

- Stage 0 input-state and entry-path decision.
- Greenfield / brownfield / hybrid badge selection.
- `next_action`, `handoff_to`, and bounded task packet shape.
- Review stop points and whether a stage may continue.
- Expected artifacts for each stage and freshness checks.
- Return routes when material, generated outputs, Workbench drafts, or reviews
  change the truth.
- Calling side branches when needed: Material Map for material truth and Effect
  Factory for designed effect assets.

Route does not own:

- Renderer internals, ffmpeg implementation details, Remotion implementation
  details, or provider account/auth.
- Treating generated files as accepted material without explicit review.
- Turning Workbench draft patches into canonical truth.
- Manual timeline editing inside Dashboard or Material Map.
- Final visual/story quality judgment by artifact existence alone.
- Remotion implementation details. The route may call Effect Factory, which may
  call `remotion-effect-worker.md`, but official delivery still returns through
  BUILD/Verify.

Route must stop instead of continuing when:

- Stage 0 lacks route-changing intent or material information.
- Material Map has candidate/thin/missing must-have needs.
- Generated provider outputs exist but have not re-entered import + explicit
  generated-material review.
- `material_delta.json` blocks ready-for-build.
- reviewer aggregation or a hard-gate reviewer blocks.
- Workbench draft artifacts exist and need agent/backend review.

Dashboard and Material Map are review surfaces. They may save review decisions
or draft artifacts, but must not silently rewrite canonical pipeline truth.
Workbench may draft timeline/material edits, but backend/agent review decides
whether they become official.

Compatibility keyword: generation is fallback for material-first teaching and
personal video routes with real material.

- **material-first**: real or partial media exists. Run material-map early.
  Existing media and existing material reveal people, scenes, actions, emotions, timeline, and gaps;
  then interaction reduces ambiguity and builds the structure. generation is
  fallback only for missing/non-proof support.
- **structure-first**: no usable media exists, but an article, outline, script,
  story, or developed idea exists. Clarify the structure first, then create
  material needs and route missing visuals through generated material fallback.
- **needs-context**: the request is too vague to choose a handoff. Ask focused
  questions first.

Legacy wording remains accepted as compatibility language:
`existing-material-first` maps to `material-first`; `story-first` maps to
`structure-first`; `hybrid` is not a primary Stage 0 entry path. Partial
material enters `material-first`, then material-delta decides generation,
reshoot, rewrite, drop, or waiver.

Review policy is route-driven, not universal. Use
`docs/artifact-reviewer-map.md` to decide whether the route needs `light`,
`normal`, or `deep` review. Materialize the policy when needed:

```powershell
python video_tools.py reviewer-policy --level normal --out reviewer_policy_packet.json
python video_tools.py reviewer-flow-acceptance --level deep --scenario all --out reviewer_flow_acceptance.json
```

For multi-agent execution, do not let subagents decide the whole route ad hoc.
Issue bounded task packets and accept them with the route orchestrator harness:

```powershell
python video_tools.py route-task-next RUN_DIR --out route_subagent_task.json
# external agent writes allowed outputs and route_subagent_result.json
python video_tools.py route-task-accept --task route_subagent_task.json --result route_subagent_result.json --state-out route_orchestrator_state.json
python video_tools.py route-orchestrator-acceptance RUN_DIR --route existing-material-first --stage-count 4 --out route_orchestrator_acceptance.json
```

The harness enforces `must_not_touch`, output freshness, allowed output
whitelists, and explicit `blocked / needs_context / failed` transitions. It
trusts artifacts, not agent claims.

Worker-facing packet rules and a copyable prompt template live in
`docs/route-agent-runner-protocol.md`.

## Stage Order

Use this order unless the user explicitly asks for a bounded review/edit task:

1. Intake
2. Story Soul
3. Director Shot Plan
4. Material Truth
5. Coverage / Decision Gate
6. BUILD Planning
7. Official Render
8. Verify
9. Workbench Draft Review
10. Brownfield Edit / Finishing
11. Delivery

Legacy names are aliases, not the public route:

- `M6` = Material Truth + Coverage / Decision Gate
- `SRP` = BUILD planning internals
- `FX` = Effects route internals
- `Node14` = Brownfield Edit / Finishing route

## Upstream Story Line

Use this before Material Truth when the brief is story-heavy, generated,
children-oriented, essay-like, or emotionally framed:

```text
Role / Literary Lens
-> Blueprint Interview
-> Story Soul Package
-> Director Shot Plan
-> Contract Compile
-> Material-Ready Handoff
```

This route is documented in `docs/upstream-story-route.md`.

Do not collapse these into one prompt if quality matters. The important split:

- `Role / Literary Lens`: what kind of mind is writing the piece;
- `Blueprint Interview`: prose soul in `blueprint.md` plus beat index in
  `blueprint.json`;
- `Story Soul Package`: executable story-world, concept, beats, shot plan,
  material needs, and generation manifest;
- `Director Shot Plan`: concrete visual/audio/subtitle/effect needs;
- `Contract Compile`: validated `segment_contract.json` and traceable
  `material_needs.json`;
- `Material-Ready Handoff`: enter material map / delta, not BUILD directly.

## Intake Questions

Ask only what materially changes the route:

- audience and purpose;
- target length;
- output type: story / event / training / explainer / recap;
- material availability and material mode:
  existing-material-first / story-first / hybrid;
- can reshoot or generate missing material;
- must-have beats or people;
- subtitle / voiceover / music expectations;
- review level: quick smoke, normal, high.

If enough information already exists in artifacts, do not re-ask. Read the
artifacts and continue.

## Route Selection

### Existing-material route

Use when the user already has footage or images.

Expected path:

```text
material-map -> material_delta -> contract-run -> verify -> Workbench/Brownfield if needed
```

### Generated-material route

Use when material is missing or the requested style is synthetic/comic/storybook.

Expected path:

```text
story-soul-blueprint
-> material_needs
-> initial project_material_map.json (empty or initial material truth)
-> initial material_delta.json with ready_for_build=false
-> material-generation-fallback
-> generated-image-provider-packet
-> image-agent-prompt-handoff
-> call_image_generation_agent if real provider outputs do not exist yet
-> provider output mapping is required
-> generated-material-import
-> generated-material-review
-> material_delta
-> contract-run
```

Generated files must be reviewed before they satisfy material needs.
For zero-material projects, do not skip the initial delta: fallback should be
driven by missing/thin evidence, not by agent confidence alone.
For the bounded happy path, prefer `tools/story_first_provider_happy_path.py`;
it writes the story-first artifacts and stops at image-agent handoff instead of
creating placeholder cards.

### Hybrid route

Use when some real material exists and some needs must be generated or reshot.

Expected path:

```text
project_material_map + generated candidates
-> explicit review
-> fresh material_delta
-> revision or BUILD
```

### Draft / Brownfield route

Use after a render or review when the user wants local changes.

Expected path:

```text
Workbench draft patch
-> workbench handoff
-> Brownfield edit if needed
-> rerender / verify
```

If the edit changes material truth, return to Material Truth and rerun delta.

### Effect Factory side branch

Use when a segment or review needs designed effects:

```text
effect need / segment context
-> video-effect-factory
-> effect_design_map.json
-> effect_contract.json
-> backend handoff, often remotion-effect-worker
-> effect_review.json
-> effect_handoff.json
-> Workbench / BUILD / Verify return point
```

Effect Factory is not the renderer and does not own `final.mp4`. It may call
`remotion-effect-worker.md` for bounded Remotion assets, or choose a lighter
ffmpeg effect when enough. If the effect changes story or material truth, return
to Story/Material stages instead of treating the effect as proof.

## Resume Existing Run

When the user points to an existing run folder, recover state before planning
new work:

1. Locate the newest or user-specified run directory.
2. Read available artifacts in this order:
   `video_intent.json`, `state.json`, `segment_contract.json`, `material_needs.json`,
   `project_material_map.json`, `material_delta.json`, `timeline_build.json`,
   `verify_result.json`, `preview_timeline.json`, `timeline_patch.json`,
   `workbench_contract_patch.json`.
3. If `final.mp4` exists, treat it as a delivery candidate only after checking
   `verify_result.json` or rerunning `verify`.
4. If draft artifacts exist, do not assume they are canonical. Route them
   through `workbench-handoff-validate` or Brownfield Edit.
5. If material or needs changed, rerun `material-delta` fresh before BUILD.

## Tool Checklist

Use deterministic tools for facts:

- `reviewer-policy`: reviewer role expansion and eval principle packet.
- `video-intent-plan`: Stage 0 `video_intent.json` route decision artifact.
- `video-intent-acceptance`: deterministic VIP0 route/follow-up acceptance.
- `reviewer-flow-acceptance`: reviewer policy smoke/e2e harness for route,
  upstream, and effects/brownfield reviewer sets.
- `validate-needs`: material need schema.
- `project-material-map`: aggregate material maps.
- `material-map-lifecycle`: route material stage.
- `material-delta`: coverage decision.
- `material-revision`: accepted revision decisions.
- `contract-run`: official BUILD and pre-BUILD gate.
- `verify`: delivery quality.
- `workbench-handoff-validate`: draft handoff safety.
- `effect-revision-*` / `remotion-*`: Brownfield effect route.
- `video-effect-factory.md`: side-branch design/contract/review layer for
  effects; calls `remotion-effect-worker.md` when Remotion is the backend.
- `route-task-next` / `route-task-accept` / `route-orchestrator-acceptance`:
  runner-neutral multi-agent packet issuance and fail-closed acceptance.
- `tools/material_first_boundary_acceptance.py`: local material-first boundary
  acceptance from Stage 2/3 through Stage 5. It writes
  `material_first_boundary_acceptance_report.json`, which `pipeline_home.py`
  and Dashboard state use as the compact handoff result.

## Minimal CLI Skeletons

Existing material:

```powershell
python video_tools.py project-material-map --maps-dir MATERIAL_MAPS --needs material_needs.json --out project_material_map.json
python video_tools.py material-map-lifecycle --out-dir RUN --needs material_needs.json --project-map project_material_map.json --contract segment_contract.json
python tools/material_first_boundary_acceptance.py --out RUN --source-dir MATERIAL_SOURCE_DIR --wall-verdict material_wall_review_verdict.json --max-assets 12 --json
python video_tools.py contract-run segment_contract.json --material-db materials_db.json --music bgm.mp3 --out final.mp4 --mat-dir RUN
python video_tools.py verify --script segment_contract.json --timing audio/tts_timing.json --edit-log edit_log.json --srt subtitles.srt --video final.mp4 --out verify_result.json
```

For material-first route testing, prefer
`tools/material_first_boundary_acceptance.py` before render. If
`material_first_boundary_acceptance_report.json` returns `ok=false`, stop and
repair the reported `failed_stage`; do not continue to `contract-run`. Workers
must use the operator-provided material folder exactly: do not substitute `--source-dir`; if the specified folder is missing, stop and report blocked
instead of selecting a neighboring folder.

Generated material:

```powershell
python video_tools.py material-generation-fallback material_delta.json --needs material_needs.json --out material_generation_fallback.json
python video_tools.py generated-image-provider-packet material_generation_fallback.json --out-dir provider_packet
python video_tools.py image-agent-prompt-handoff provider_packet/generated_provider_packet.json --out-dir provider_packet/image_agent_handoff
# image-capable agent writes each target_file from generated_provider_packet.json
python video_tools.py codex-imagegen-provider-fill provider_packet/generated_provider_packet.json --image-files <generated images in packet order>
python video_tools.py generated-material-import material_generation_fallback.json --needs material_needs.json --provider-outputs provider_outputs.json --out-dir generated_material
python video_tools.py generated-material-review generated_material/project_material_map.json --needs material_needs.json --verdict generated_material_review.json --out reviewed_project_material_map.json
```

Workbench / Brownfield:

```powershell
python tools/preview_timeline.py build --artifact-root RUN --out preview_timeline.json
python tools/timeline_patch.py apply --artifact-root RUN --patch timeline_patch.json --out patched_draft_timeline.json
python video_tools.py workbench-handoff-validate RUN --out workbench_handoff_report.json
python video_tools.py effect-revision-request --baseline-review light_effects_baseline_review.json --light-effects-plan light_effects_plan.json --out effect_revision_request.json
```

## Stop Conditions

Stop and report instead of guessing when:

- must-have material is missing and no fallback/waiver exists;
- generated provider outputs are missing or cannot be mapped to jobs;
- generated material has not been explicitly reviewed;
- material delta is broken or stale;
- Workbench patch would overwrite canonical truth;
- effect output changes story evidence instead of finishing;
- verify fails on black frames, subtitle corruption, or content mismatch.

## Storybook / Comic Route

For picture-book, comic, fairy-tale, or children story cases:

- set `storyboard_panel_locked=true`;
- usually use `review_policy.level=deep`;
- use generated material fallback if no source art exists;
- include `generation_manifest.json`, style/character consistency rules, panel
  count, and generated material review rubric before provider handoff;
- state Chinese subtitle requirements if the output is for Chinese-speaking
  children;
- prefer more panels over unrelated filler;
- if holding one panel for a long time, make that intentional in pacing;
- verify Chinese subtitles are real UTF-8 text, not `????`;
- never map generated images by "latest N files"; use provider output mapping.

## Delivery Summary

A completed route report must state:

- final video path;
- duration;
- material coverage summary;
- generated or real material source count;
- verify result;
- known limitations;
- next action, if any.
