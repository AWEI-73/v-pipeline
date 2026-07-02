# Mainline Branch Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. This document is a construction plan, not permission to start rendering or rewriting UI.

**Goal:** Converge the Hermes Video Pipeline main route with its major side branches: Material Map, Soundtrack Arranger, Effect Factory, Subtitle/Voiceover, Workbench/Brownfield, and Verify/Delivery.

**Architecture:** Keep one main route. Stage 0 writes child contracts. Side branches own their own artifacts and return through explicit handoff artifacts. BUILD and Delivery consume only accepted handoffs and must fail closed when evidence is missing.

**Tech Stack:** Python CLI tools, `video_tools.py`, `tools/*.py`, `video_pipeline_core/*`, JSON artifacts, Windows PowerShell, `unittest`, optional ffmpeg/ffprobe/yt-dlp/provider APIs.

---

## 0. Scope

This plan is for non-UI convergence. It does not redesign Dashboard or Workbench screens.

The work should make the repository easier for an agent to operate by answering:

- Which route owns this request?
- Which artifacts prove the route is ready?
- Which tools are allowed for the current branch?
- Which next action is executable, and which is a human/agent review stop?
- What must fail closed before BUILD, Verify, or Delivery?

Primary outcome:

```text
Stage 0
  -> child contracts
  -> Material / Audio / Effect / Subtitle / Workbench branch as needed
  -> branch handoff manifests
  -> BUILD eligibility
  -> Verify / Delivery gate
  -> Happy path acceptance runs
```

## 1. Current Repo Map

Current single-entry documents:

| Purpose | File |
|---|---|
| Operator start point | `RUNBOOK.md` |
| Route decision tree | `docs/pipeline-decision-tree.md` |
| Branch ownership contract | `docs/branch-contract-registry.json` |
| Human branch summary | `docs/branch-contract-registry.md` |
| Stage/tool map | `docs/video-pipeline-operating-map.md` |
| Tool ownership simplification | `docs/stage-tool-simplification.md` |
| Stage boundary matrix | `docs/stage-boundary-matrix.md` |
| Soundtrack branch route | `docs/soundtrack-arranger-route.md` |
| Effect branch route | `docs/effect-factory-route.md` |
| Workbench integration | `docs/workbench-dashboard-integration.md` |

Current branch map:

| Branch | Owns | Must Not Own |
|---|---|---|
| Main Pipeline | Stage 0, route orchestration, BUILD eligibility, delivery promotion | Branch-internal decisions without handoff |
| Material Map | material truth, matrix, scene-to-need edges, deltas, rough-cut facts | `final.mp4` |
| Soundtrack Arranger | music requirements, candidate/source/license, probe, Audio Director handoff | final video render or subtitle repair |
| Subtitle/Voiceover | caption/voiceover readiness, provider plan, VoxCPM handoff, caption evidence | mixing music or final video render |
| Effect Factory | semantic effect translation, capability review, worker handoff, effect evidence | direct timeline mutation or final render |
| Workbench/Brownfield | draft patching and route-back handoffs | canonical truth |
| Verify/Delivery | final evidence, fail-closed semantic gate, repair routing | direct repair of canonical artifacts |

## 2. Main Flow To Converge

Canonical intent:

```text
Stage 0 Video Intent Planner
  -> project_brief.json
  -> interaction_log.md
  -> video_intent.json
     - material_contract
     - soundtrack_contract
     - subtitle_voiceover_contract
     - effect_policy
     - communication_intent
     - handoff_packet
  -> selected owner branch
  -> branch handoff artifact(s)
  -> segment_contract.json / BUILD planning
  -> Verify / Delivery Gate
```

Stage 0 should not make the finished video. It decides:

- input state: material available, text/story available, idea only, unknown;
- entry path: material-first, structure-first, needs-context;
- material scan decision;
- music/song/BGM/source-audio policy;
- subtitle/voiceover policy;
- effect policy;
- which branch owns the next concrete action.

## 3. Convergence Principles

1. **Contract first:** Every branch must expose a small, stable JSON handoff contract before downstream tools consume it.
2. **Fail closed:** Missing license, probe, provider, effect evidence, subtitle evidence, or material truth blocks delivery.
3. **No hidden branch writes:** Side branches do not overwrite `final.mp4`, `segment_contract.json`, `project_material_map.json`, or `timeline_build.json`.
4. **Manifest over guessing:** Downstream tools should read branch handoffs from `artifact_manifest.json` or the dashboard/run state API, not by blindly searching filenames.
5. **Review states are not executable states:** `needs-context`, `await_review`, `repair_*`, and `review_*` stop execution.
6. **Heavy external calls are opt-in:** Provider APIs, real downloads, Remotion renders, and final video renders are smoke/manual/happy-path actions, not unit-test dependencies.
7. **Warnings are not delivery pass:** For complete-video validation, warnings should route to repair or explicit waiver.

## 4. Critical Integration Seams

These are the seams that must be closed for real convergence.

### 4.1 `next_action` Taxonomy

Problem: branch tools currently emit many `next_action` values. Some mean "run a tool"; others mean "stop and ask/review". If they are not classified, an agent can loop, skip a gate, or run BUILD too early.

Required taxonomy:

| Class | Examples | Behavior |
|---|---|---|
| `executable` | `soundtrack-arrange`, `execute_audio_mix_plan`, `accept_subtitle_voiceover_handoff` | Parent/orchestrator may call a deterministic tool |
| `review_stop` | `needs-context`, `await_map_review`, `review_candidate_parameters` | Stop and ask user/reviewer/agent |
| `repair_stop` | `repair_audio_handoff`, `repair_caption_or_voiceover`, `revise_effect_intent` | Stop; route to owning branch |
| `return_route` | `return_to_build`, `return_to_build_with_final_audio`, `return_to_verify` | Only allowed after owning gate passed |
| `complete` | `complete`, `ready_for_delivery_gate` | Still requires delivery gate before final claim |

Implementation requirements:

- `pipeline_home.py` and Dashboard state must display class, owner, source artifact, and next safe command/review action.
- `runtime_orchestrator.py` must not try to execute review/repair states.
- Unknown next actions should fail closed with `unknown_next_action`, not continue.

### 4.2 Contract Passthrough

Problem: Stage 0 child contracts can be lost when artifacts are transformed from intent to story, segment contract, timeline, and delivery reports.

Contracts that must survive or be explicitly deferred:

```text
material_contract
soundtrack_contract
subtitle_voiceover_contract
effect_policy
communication_intent
handoff_packet
```

Required rule:

- Any adapter from `video_intent.json` to story/segment/build artifacts must either:
  - copy the child contract into a stable field such as `stage0_child_contracts`, or
  - write an explicit `deferred_child_contracts[]` entry with owner, reason, return point, and non-blocking gate evidence.

Tests must prove child contracts are not silently dropped.

### 4.3 Handoff Artifact Manifest

Problem: downstream tools should not guess whether a branch completed by scanning random filenames.

Every branch acceptance tool should update `artifact_manifest.json` with canonical keys.

Minimum manifest keys:

```json
{
  "soundtrack_plan": "...",
  "music_source_candidates": "...",
  "sound_license_manifest": "...",
  "soundtrack_probe_report": "...",
  "audio_handoff_acceptance": "...",
  "audio_mix_plan": "...",
  "audio_mix_report": "...",
  "audio_build_handoff": "...",
  "subtitle_voiceover_handoff_acceptance": "...",
  "subtitle_voiceover_build_handoff": "...",
  "voiceover_provider_plan": "...",
  "voxcpm_runtime_check": "...",
  "caption_audit": "...",
  "narration_manifest": "...",
  "effect_handoff": "...",
  "remotion_effect_handoff": "...",
  "effect_render_verification": "...",
  "workbench_handoff": "...",
  "delivery_gate": "..."
}
```

Required rule:

- `pipeline_home.py`, Dashboard state, BUILD handoff checks, and Delivery Gate must prefer manifest paths before fallback search.
- Manifest paths may be relative to the run folder or absolute.
- If manifest points to a missing file, report stale/missing evidence and fail closed.

## 5. Phase Plan

### Phase 0: Baseline Audit

**Goal:** Confirm current route/tool/skill ownership before changing behavior.

**Read:**

- `RUNBOOK.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.json`
- `docs/stage-tool-simplification.md`
- `docs/video-pipeline-operating-map.md`

**Commands:**

```powershell
python tools\skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --json
python tools\pipeline_map.py
python -m unittest tests.test_branch_contract_registry tests.test_skill_tool_contracts -q
```

**Acceptance:**

- Tool ownership audit has no unexplained orphan tool.
- Branch registry tests pass.
- Generated map reflects all active branches.
- Any known orphan/noise file is listed, not silently deleted.

### Phase 1: Stage 0 Child Contract Alignment

**Goal:** Stage 0 must write enough child contracts for downstream branches to know whether they are required, optional, deferred, or blocked.

**Likely files:**

- `video_pipeline_core/video_intent_planner.py`
- `tests/test_video_intent_planner.py`
- `docs/pipeline-decision-tree.md`
- `skills/video-pipeline-route.md`

**Required fields in `video_intent.json`:**

```json
{
  "entry_path": "material-first",
  "material_contract": {},
  "soundtrack_contract": {},
  "subtitle_voiceover_contract": {},
  "effect_policy": {},
  "communication_intent": {},
  "required_followup_questions": [],
  "handoff_packet": {}
}
```

**Acceptance:**

- Fuzzy whole-video request writes Stage 0 package, not branch output only.
- Existing material route records material scan decision.
- Music/song/BGM intent records soundtrack contract.
- Subtitle/voiceover intent records provider/fallback policy.
- Effect style intent records bounded/deferred effect policy.
- `needs-context` asks at most two rounds, then stops with required questions.

**Focused tests:**

```powershell
python -m unittest tests.test_video_intent_planner tests.test_pipeline_home -q
```

### Phase 2: Soundtrack Source / Download / Probe Convergence

**Goal:** Audio source selection should be section-aware and license-aware, and should produce enough evidence for Audio Director and Delivery Gate.

**Likely files:**

- `video_pipeline_core/soundtrack_arranger.py`
- `video_pipeline_core/soundtrack_providers.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `tools/soundtrack_flow_acceptance.py`
- `docs/soundtrack-arranger-route.md`
- `tests/test_soundtrack_arranger.py`
- `tests/test_soundtrack_providers.py`
- `tests/test_soundtrack_flow_acceptance.py`

**Required artifacts:**

- `soundtrack_plan.json`
- `music_source_candidates.json`
- `sound_license_manifest.json`
- `soundtrack_probe_report.json` or `soundtrack_probe_bundle`
- `audio_director_handoff.json`
- `audio_handoff_acceptance.json`
- `audio_mix_plan.json`

**Required behaviors:**

- `soundtrack_plan.json` exposes `required_track_count`.
- Each section exposes role, duration, vocal policy, energy curve, source priority, probe requirement, and license requirement.
- Songs/vocals prefer Jamendo or reviewed manual import.
- BGM can use reviewed manual import or yt-dlp import with license note.
- Pixabay official API audio search remains fail-closed unless a supported source exists.
- Unit tests mock Jamendo/provider network. Real network is only manual smoke/happy path.

**Acceptance:**

- Missing license/source note blocks handoff.
- `reference_only` cannot become deliverable audio.
- Missing probe blocks required deliverable audio.
- Selected valid tracks must satisfy `required_track_count`.
- Fake/no-render acceptance can satisfy the contract without real downloads.

**Focused tests:**

```powershell
python -m unittest `
  tests.test_soundtrack_arranger `
  tests.test_soundtrack_providers `
  tests.test_audio_handoff_acceptance `
  tests.test_soundtrack_flow_acceptance -q
```

### Phase 3: Audio Mix / BUILD Handoff Alignment

**Goal:** Accepted soundtrack/audio plans should produce a BUILD-facing audio handoff without rendering final video.

**Likely files:**

- `video_pipeline_core/audio_mix_plan_executor.py`
- `tools/audio_mix_plan_execute.py`
- `tools/pipeline_home.py`
- `video_pipeline_core/dashboard_state.py`
- `tests/test_audio_mix_plan_executor.py`
- `tests/test_pipeline_home.py`
- `tests/test_dashboard_state.py`

**Required artifacts:**

- `final_audio.wav`
- `audio_mix_report.json`
- `audio_build_handoff.json`
- `artifact_manifest.json`

**Required behaviors:**

- Audio duration clamps to video/timeline duration by default.
- Clamped audio receives tail fade-out rather than hard cut.
- Speech-critical sections require ducking/preservation evidence.
- `audio_mix_report.json` includes duration alignment and level evidence.
- `pipeline_home.py` reads manifest-based audio handoff and returns a build-ready/return-to-build state.

**Acceptance:**

- Missing or failed audio handoff routes to `repair_audio_handoff`.
- Ready audio mix routes to `return_to_build_with_final_audio`.
- No `final.mp4` is written during audio mix.

**Focused tests:**

```powershell
python -m unittest `
  tests.test_audio_mix_plan_executor `
  tests.test_pipeline_home `
  tests.test_dashboard_state -q
```

### Phase 4: Verify / Delivery Gate Integration

**Goal:** Delivery Gate should consume branch evidence from Material, Audio, Effect, Subtitle/Voiceover, and Workbench. `verify_result.pass=true` alone is never enough.

**Likely files:**

- `tools/write_delivery_gate_report.py`
- `video_pipeline_core/dashboard_state.py`
- `tools/pipeline_home.py`
- delivery gate tests
- `tests/test_dashboard_state.py`
- `tests/test_pipeline_home.py`

**Required checks:**

- Material timeline clips match material map ids and need refs.
- Required audio has `audio_build_handoff.json`, `audio_mix_report.json`, and probe/license evidence.
- Required subtitle/voiceover has build handoff, caption audit, and narration manifest when applicable.
- Required effects have effect handoff and render/review evidence.
- Workbench draft or rerender preview is not final unless promoted.
- Manifest entries are checked for stale/missing paths.

**Acceptance:**

- `verify_result.json = {"pass": true}` but missing branch evidence still fails delivery.
- Missing audio evidence returns audio repair route.
- Missing subtitle/voiceover evidence returns subtitle/voiceover repair route.
- Missing effect evidence returns effect repair route.
- Workbench preview returns review/promotion route, not complete.

**Focused tests:**

```powershell
python -m unittest `
  tests.test_pipeline_home `
  tests.test_dashboard_state -q
```

Add dedicated delivery gate tests if an existing delivery gate test module exists; otherwise create a focused test module for branch evidence fail-closed behavior.

### Phase 5: Subtitle / Voiceover Alignment

**Goal:** Subtitle and voiceover requirements should become explicit build handoffs. VoxCPM can be a preferred provider, but missing runtime must be visible and fail closed unless fallback is allowed.

**Likely files:**

- `video_pipeline_core/subtitle_voiceover_handoff.py`
- `tools/subtitle_voiceover_handoff_accept.py`
- `tools/voxcpm_runtime_check.py`
- `tools/voxcpm_voiceover_provider.py`
- `tests/test_subtitle_voiceover_handoff.py`
- `tests/test_voiceover_provider.py`
- `tests/test_voxcpm_voiceover_provider_cli.py`

**Required artifacts:**

- `subtitle_voiceover_handoff_acceptance.json`
- `subtitle_voiceover_build_handoff.json`
- `voiceover_provider_plan.json`
- `voxcpm_runtime_check.json`
- `caption_audit.json`
- `narration_manifest.json`

**Required behaviors:**

- `preferred_provider=voxcpm` checks runtime before claiming ready.
- If VoxCPM unavailable and `fallback_allowed=false`, route to `needs-context` or `repair_subtitle_voiceover_handoff`.
- If fallback is allowed, record selected provider and fallback reason.
- Caption/readability evidence is visible to Delivery Gate.

**Acceptance:**

- Missing required narration blocks BUILD/delivery.
- Missing caption audit blocks required subtitle delivery.
- Provider unavailable reason includes missing module/model/python/repo details where available.
- Manifest records subtitle/voiceover handoff artifacts.

**Focused tests:**

```powershell
python -m unittest `
  tests.test_subtitle_voiceover_handoff `
  tests.test_voiceover_provider `
  tests.test_voxcpm_voiceover_provider_cli `
  tests.test_pipeline_home -q
```

### Phase 6: Effect Factory Alignment

**Goal:** Effect Factory should operate as a semantic-to-capability translator and bounded worker handoff, not as a fixed-template shortcut or final renderer.

**Likely files:**

- `tools/visual_technique_plan.py`
- `tools/effect_factory_route_acceptance.py`
- `tools/effect_factory_boundary_acceptance.py`
- effect factory core modules
- `skills/video-effect-factory.md`
- `docs/effect-factory-route.md`
- effect factory tests

**Required artifacts:**

- `visual_technique_plan.json`
- `visual_technique_review.json`
- `visual_technique_plan.confirmed.json`
- `effect_capability_review.json`
- `effect_contract.json`
- `effect_intent_plan.json`
- `effect_revision_request.json`
- `remotion_prompt_pack.json`
- `remotion_worker_outputs.json`
- `remotion_effect_review.json`
- `effect_render_verification.json`
- `effect_handoff.json`

**Required behaviors:**

- Fuzzy whole-video style is recorded as `effect_policy`, not immediately rendered.
- Bounded effect request creates reviewable parameters first.
- Required effects need capability/review evidence.
- Backend limitations are visible; unsupported required effect blocks or asks for fallback.
- Effect output remains a bounded asset until BUILD/Workbench consumes it.

**Acceptance:**

- No-render effect route acceptance passes for multiple semantic families.
- Different effect intents do not collapse into one generic output contract.
- Missing required effect evidence fails delivery.
- Effect branch never writes `final.mp4`.

**Focused smoke:**

```powershell
python tools\effect_factory_route_acceptance.py `
  --out RUN_DIR `
  --request "formal cinematic opening with readable title and restrained light" `
  --effect-role opening_title `
  --duration-sec 6 `
  --json

python tools\pipeline_home.py --run RUN_DIR --json
```

Expected: `final.mp4` absent, route stops at human effect review or promotion handoff.

### Phase 7: Workbench / Brownfield Route-Back Alignment

**Goal:** Workbench remains a black-box editing surface for draft previews and local patches, but all canonical changes route back to the owning branch.

**Likely files:**

- `tools/workbench_*`
- `dashboard/workbench_native/API_CONTRACT.md`
- `video_pipeline_core/dashboard_state.py`
- `docs/workbench-dashboard-integration.md`
- Workbench tests

**Required behaviors:**

- Workbench can write draft patches.
- Material replacement routes back to Material Map.
- Subtitle patch routes back to Subtitle/Voiceover.
- Audio cue patch routes back to Soundtrack/Audio Director.
- Effect patch routes back to Effect Factory.
- Workbench rerender preview is never canonical final output.

**Acceptance:**

- `workbench_handoff.json` with route-back is visible in `pipeline_home.py`.
- Draft rerender does not mark run complete.
- Any patch that changes canonical truth fails until owner branch accepts it.

### Phase 8: Happy Path Acceptance Set

**Goal:** Prove the converged route can be followed without guessing.

Run three bounded happy paths. They may be no-render or preview-based unless the user explicitly asks for full render.

#### A. Single Long Source Highlight

Route:

```text
Stage 0 material-first
  -> source_section_map / source_material_matrix / source_transcript
  -> dialogue_edit_script or highlight_selection_plan
  -> rough_cut_plan
  -> safe_highlight_cut preview
  -> final-product-verify
  -> delivery candidate package
  -> review decision before promotion
```

Acceptance:

- Uses transcript/script logic before cutting.
- Does not cut half sentences.
- Original audio/music policy is explicit.
- Preview candidate is not final until accepted/promoted.

#### B. Multi-Material Training/Event Recap

Route:

```text
Stage 0 material-first
  -> material inventory / understanding matrix
  -> material wall review
  -> material map / delta
  -> soundtrack section plan
  -> optional effect/subtitle/voiceover handoff
  -> BUILD dry path or preview
  -> Verify / Delivery Gate
```

Acceptance:

- Material matrix/contact sheet is reviewable.
- Material selection is not based only on filenames when visual evidence is required.
- Music/effect/subtitle contracts are either resolved or explicitly deferred.
- Delivery Gate reports missing evidence accurately.

#### C. No-Material Story

Route:

```text
Stage 0 structure-first
  -> story / structure / material_needs
  -> generated material fallback
  -> image-agent handoff
  -> generated output import/review
  -> soundtrack/effect/subtitle contracts
  -> BUILD dry path or bounded preview
  -> Verify / Delivery Gate
```

Acceptance:

- No placeholder text-card images are promoted as generated material.
- If image-capable provider is unavailable, route reports provider unavailable.
- Generated candidates require review before material map acceptance.

## 6. Test Strategy

Use layered tests. Do not wait until full E2E to find branch bugs.

### Focused Unit / Acceptance

```powershell
python -m unittest tests.test_video_intent_planner -q
python -m unittest tests.test_soundtrack_arranger tests.test_soundtrack_providers tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance -q
python -m unittest tests.test_audio_mix_plan_executor -q
python -m unittest tests.test_subtitle_voiceover_handoff tests.test_voiceover_provider tests.test_voxcpm_voiceover_provider_cli -q
python -m unittest tests.test_pipeline_home tests.test_dashboard_state -q
```

### Branch Smoke

```powershell
python tools\soundtrack_flow_acceptance.py --input RUN_DIR\video_intent.json --out-dir RUN_DIR --fake-reviewed-audio --json
python tools\effect_factory_route_acceptance.py --out RUN_DIR --request "bounded title intro" --effect-role opening_title --duration-sec 6 --json
python tools\pipeline_home.py --run RUN_DIR --json
```

### Full Regression

Run only after focused tests are green:

```powershell
python -m unittest discover -s tests -q
```

Network/provider tests should use mocks by default. Real downloads are manual/happy-path smoke tests and must write only under `runs/` or `.tmp/`.

## 7. Done Definition

This convergence is done when:

- Stage 0 writes stable child contracts.
- Branch contracts and skill/tool ownership are aligned.
- Audio can plan, source/import/download when allowed, probe, accept, mix, and hand off.
- Subtitle/Voiceover can expose provider readiness and fail closed.
- Effect Factory can translate bounded effect intent, review parameters, and hand off assets without writing final video.
- Workbench route-back keeps canonical truth protected.
- Delivery Gate reads manifest-backed branch evidence and fails closed on missing/stale evidence.
- Three happy paths produce run folders with clear `pipeline_home.py` state.
- Focused tests pass.
- Full regression is either green or explicitly documented if too long to run in-session.

## 8. Not In This Construction Pass

- Dashboard / Workbench visual redesign.
- New public OAuth/runtime web app.
- Replacing the canonical ffmpeg render path.
- Making Remotion the primary renderer.
- Training or hosting local music generation models.
- Treating YouTube/commercial music as deliverable without license/source note.
- Promoting generated placeholder/text-card images as real generated material.
- Deleting historical runs or reference repos.

## 9. First Implementation Slice

When施工 begins, start with the smallest convergent slice:

1. Stage 0 child contract passthrough test.
2. Audio section requirement contract.
3. Audio handoff `required_track_count` and probe/license gate.
4. Audio mix duration clamp/fade handoff.
5. Manifest-backed `pipeline_home.py` lookup.
6. Subtitle/Voiceover provider readiness visibility.
7. Delivery Gate branch-evidence fail-closed tests.

Commit after each coherent slice. Do not mix UI redesign with this convergence pass.
