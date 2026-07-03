# Mainline Branch Convergence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use `superpowers:subagent-driven-development` or `superpowers:executing-plans` to implement this plan task-by-task. This document is a construction plan, not permission to start rendering or rewriting UI.

**Goal:** Converge the Hermes Video Pipeline main route with its major side branches: Material Map, Soundtrack Arranger, Effect Factory, Subtitle/Voiceover, Workbench/Brownfield, and Verify/Delivery.

**Architecture:** Keep one main route. Stage 0 writes child contracts. Side branches own their own artifacts and return through explicit handoff artifacts. BUILD and Delivery consume only accepted handoffs and must fail closed when evidence is missing.

**Tech Stack:** Python CLI tools, `video_tools.py`, `tools/*.py`, `video_pipeline_core/*`, JSON artifacts, Windows PowerShell, `unittest`, optional ffmpeg/ffprobe/yt-dlp/provider APIs.

---

## 0. Scope

### 0.0 Planning Status

This document is the construction plan. Reading or updating this document does
not authorize implementation, provider downloads, Remotion previews, ffmpeg
renders, or happy-path E2E runs.

Before construction begins, the worker must:

1. read this plan end-to-end;
2. run the Phase 0 baseline audit commands;
3. confirm the dirty worktree contains no unrelated tracked edits;
4. choose the next unchecked implementation slice from Section 14;
5. write or update the focused failing test for that slice before changing
   production code.

If the user says "施工圖先補全" or "先不要施工", stop after updating this
document and report the plan delta only.

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

Stage 0 decision order must be deterministic:

1. **Resume check:** if a run folder exists or the user points to an existing
   run, inspect `pipeline_home.py` first. Do not write new Stage 0 artifacts
   until the cursor is known.
2. **Whole-video vs bounded branch:** decide whether the request is a whole
   film/video route or a bounded branch request such as "make this opening
   effect" or "find one BGM track". Whole-video requests always start at
   Stage 0, even when they mention music, effects, subtitles, or style.
3. **Input state:** classify available inputs as material available, one long
   source, text/story/article available, idea only, or unknown.
4. **Entry path:** choose `material-first`, `structure-first`, or
   `needs-context`.
5. **Child contracts:** write material, soundtrack, subtitle/voiceover, effect,
   and communication contracts. A child contract may be `required`,
   `optional`, `deferred`, or `not_applicable`, but it must be explicit.
6. **First owner:** choose one executable owner for the next action. Other
   branches remain recorded as child contracts until their insertion point.

Child branch insertion points:

| Branch | When it may run | Required input | Returns to |
|---|---|---|---|
| Material Map | Immediately after Stage 0 for `material-first`, after story needs for `structure-first`, or during Brownfield material replacement | `material_contract`, source folder or generated candidates, material needs when available | Stage 1/contract if story shape changes; otherwise BUILD eligibility |
| Soundtrack Arranger | After Stage 0 when music/song/BGM/source-audio is required, or after rough structure exposes sections | `soundtrack_contract`, target sections/durations, vocal/speech policy | Audio Director / BUILD handoff |
| Subtitle/Voiceover | After Stage 0 when narration/subtitle is required, or after script/segment text exists | `subtitle_voiceover_contract`, language/script/provider policy | BUILD handoff / Delivery evidence |
| Effect Factory | After Stage 0 when effect policy is required, after structure when effect role/duration is known, or from Brownfield finishing request | `effect_policy`, section/role/duration/source refs when bounded | BUILD/Workbench bounded asset handoff |
| Workbench/Brownfield | After a draft, rough cut, preview, final candidate, or local patch exists | draft timeline/preview and intended patch | owning branch route-back, never direct canonical overwrite |
| Verify/Delivery | After any candidate final/preview package or when asked to review current output | current artifacts plus manifest evidence | repair route, review stop, or delivery/promotion |

BUILD is not a branch. It is the convergence point that may consume accepted
branch handoffs only after prerequisites in Section 5 are satisfied.

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

### 4.0 Integration Contract Summary

The convergence pass is considered structurally valid only when these three
surfaces agree:

| Surface | Source of truth | Why it matters |
|---|---|---|
| Route/state | `pipeline_home.py`, `runtime_orchestrator.py`, `node_registry.py` | Prevents a branch from emitting a `next_action` that no runner understands |
| Contract passthrough | `video_intent.json` -> story/contract/timeline/build/delivery artifacts | Prevents Stage 0 child requirements from disappearing before BUILD/Verify |
| Artifact evidence | `artifact_manifest.json` plus branch handoff reports | Prevents BUILD/Delivery from guessing by filename or trusting stale evidence |

Any phase that changes a branch artifact must update or verify all three
surfaces. A branch is not "integrated" when its own CLI passes but
`pipeline_home.py`, the manifest reader, or Delivery Gate cannot see the result.

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
- `runtime_orchestrator.py` and any node runner must not try to execute review/repair states.
- `node_registry.py` must not report a node as build/delivery ready when its
  branch contract is required and the owning handoff is absent.
- Unknown next actions should fail closed with `unknown_next_action`, not continue.
- New `next_action` strings must be registered in one place and covered by a
  focused route test before a branch emits them.

Required implementation shape:

```json
{
  "next_action": "soundtrack-arrange",
  "next_action_class": "executable",
  "owner": "soundtrack_arranger",
  "source": "video_intent.json",
  "safe_command": "python video_tools.py soundtrack-arrange RUN_DIR\\video_intent.json --out-dir RUN_DIR",
  "stop_reason": null
}
```

`safe_command` is optional for review/repair stops and must not be emitted when
the action requires user judgment. If a branch cannot classify its next action,
it should return:

```json
{
  "next_action": "unknown_next_action",
  "next_action_class": "repair_stop",
  "owner": "main_pipeline",
  "stop_reason": "unclassified_next_action"
}
```

The taxonomy source should be central and testable. Prefer a small registry in
the pipeline state/home layer over duplicated string checks spread across
branch tools.

State-machine alignment tests must cover:

- a known executable action returns a safe command;
- a review stop returns no safe command;
- a repair stop returns owner and stop reason;
- an unknown action returns `unknown_next_action`;
- a `state.json` action and a branch report action disagreeing routes to repair
  instead of continuing silently.

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

Minimum passthrough checkpoints:

| From | To | Required behavior |
|---|---|---|
| `video_intent.json` | story / structure artifacts | copy `stage0_child_contracts` or write `deferred_child_contracts[]` |
| story / structure artifacts | `segment_contract.json` | preserve child contracts and material/audio/effect/subtitle requirements |
| `segment_contract.json` | `timeline_build.json` | preserve branch requirements and link timeline clips to accepted material/audio/effect/subtitle evidence |
| `timeline_build.json` | render/build payload | preserve final audio, subtitle, effect, material trace refs |
| render/build payload | Verify / Delivery | report consumed branch evidence and any deferred or missing contract |

Every passthrough test should include at least one required child contract and
one deferred child contract, so a tool cannot pass by copying only happy-path
fields.

Required passthrough policy:

- Prefer a whitelist-style copier for known child contracts.
- The copier must preserve unknown nested fields under each child contract
  unless the target artifact explicitly documents why the field is not allowed.
- A transformation may summarize a contract, but the original contract must
  remain available through `stage0_child_contracts` or
  `deferred_child_contracts[]`.
- A missing required child contract is a test failure even when the branch is
  not used by the current happy path.

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
- Flat keys and nested `artifacts.<key>.path` entries are both valid during the migration period.
- If manifest points to a missing file, Delivery Gate must emit `artifact_manifest_stale` and fail closed before claiming delivery.

Manifest ownership rule:

| Branch | Writes manifest keys | Does not write |
|---|---|---|
| Material Map | material matrix/map/delta/review/handoff keys | audio/effect/subtitle handoff keys |
| Soundtrack / Audio Director | soundtrack/source/license/probe/audio handoff/mix keys | material map, effect output, final video |
| Subtitle/Voiceover | subtitle/voiceover provider/readiness/caption/narration keys | music mix or material truth |
| Effect Factory | effect plan/review/worker/handoff/evidence keys | canonical timeline or final video |
| Workbench/Brownfield | draft preview/patch/route-back keys | canonical truth and `final.mp4` |
| Verify/Delivery | delivery report, final evidence index, repair route keys | branch-internal repair artifacts |

Manifest entries should include enough metadata for stale detection:

```json
{
  "artifact_manifest_version": 1,
  "artifacts": {
    "audio_build_handoff": {
      "path": "audio_build_handoff.json",
      "owner": "soundtrack_arranger",
      "status": "accepted",
      "updated_by": "tools/audio_mix_plan_execute.py"
    }
  }
}
```

If the existing manifest format is flat, the first implementation may keep flat
keys for compatibility and add metadata in a sidecar or nested `artifacts`
field. Do not break existing readers without a migration test.

Manifest integration tests must cover:

- valid flat manifest key;
- valid nested `artifacts.<key>.path`;
- relative and absolute paths;
- stale path;
- manifest key exists but status is not `accepted`;
- fallback filename search still works only when no manifest key exists.

### 4.4 Network / Provider Boundary

Provider integrations are allowed, but tests must not depend on live network.

Rules:

- Jamendo, yt-dlp, Pexels, Pixabay, and other remote providers must be mocked in
  unit and branch acceptance tests.
- Real downloads are manual smoke or Phase 8 happy-path actions only.
- Provider output must always include source, license note or URL, provider
  name, query, selected track/file id when available, and fallback reason when
  fallback is used.
- A provider failure must become a branch repair/needs-context state, not a
  silent empty result.

### 4.5 Run Artifact Hygiene

Happy-path or smoke runs may create large files. They must write only under:

- `runs/<campaign_or_phase>/...`
- `.tmp/...`
- a user-provided output directory explicitly named in the command

Never commit generated media, downloaded provider assets, temporary wav/mp4
files, contact sheets, or generated run folders unless the user explicitly asks
for a golden fixture.

Every Phase 8 report must include:

- run folder;
- generated media size summary;
- whether `final.mp4` exists;
- whether any preview was promoted;
- cleanup recommendation.

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

### Phase 0.5: State / Manifest / Passthrough Contract Skeleton

**Goal:** Before improving any branch, make the shared convergence surface
explicit. This prevents Audio, Effect, Subtitle, Material, and Workbench from
each inventing their own state and handoff conventions.

**Likely files:**

- `tools/pipeline_home.py`
- `tools/pipeline_map.py`
- `video_pipeline_core/dashboard_state.py`
- `video_pipeline_core/delivery_gate.py`
- any existing artifact manifest helper module, or a new focused helper if no
  central helper exists
- `tests/test_pipeline_home.py`
- `tests/test_pipeline_map.py`
- `tests/test_dashboard_state.py`
- delivery gate tests

**Required behaviors:**

- `pipeline_home.py` returns `next_action_class`, `owner`, `source`, and either
  `safe_command` or `stop_reason`.
- Unknown/unclassified actions fail closed.
- Manifest lookup is preferred over filename guessing, while fallback search
  remains for backward compatibility.
- Stale manifest path means repair/blocked state, not success.
- Child contracts can be read from `video_intent.json`,
  `stage0_child_contracts`, or a documented deferred contract list.
- Existing dashboard state can show manifest-backed handoff artifacts without
  requiring UI redesign.

**Acceptance:**

- A fixture with a valid manifest handoff routes to the branch return state.
- A fixture with a stale manifest path fails closed.
- A fixture with an unknown `next_action` returns `unknown_next_action`.
- A fixture where an adapter drops `soundtrack_contract` or `effect_policy`
  fails the passthrough test.

**Focused tests:**

```powershell
python -m unittest `
  tests.test_pipeline_home `
  tests.test_pipeline_map `
  tests.test_dashboard_state -q
```

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

**Stage 0 output semantics:**

| Contract status | Meaning | Downstream behavior |
|---|---|---|
| `required` | The branch must resolve before delivery and usually before BUILD | missing handoff blocks |
| `optional` | Branch may run if evidence exists or user requests it later | missing handoff does not block |
| `deferred` | Branch is known but cannot run yet | must include reason, owner, return point, and review/gate condition |
| `not_applicable` | Branch is not part of this run | no branch gate required |

`deferred` is valid only when all fields below exist:

```json
{
  "status": "deferred",
  "owner": "effect_factory",
  "reason": "effect duration depends on final segment structure",
  "return_point": "after_segment_contract",
  "gate": "effect_policy_recheck"
}
```

If a contract is ambiguous and affects route choice, keep the run in
`needs-context` for at most two focused question rounds. After two rounds,
write the remaining questions to `required_followup_questions` and stop; do not
guess and continue.

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
- If timeline duration is shorter than planned audio, default behavior is
  clamp-to-video-duration with fade-out.
- If timeline duration is longer than planned audio, report the gap and route
  to audio repair or explicit waiver; do not silently leave dead air.
- If source material has important original speech, music placement must show
  ducking/preservation evidence before returning to BUILD.

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
- Delivery report must include both the thin technical verify result and the
  semantic/branch gate verdict so reviewers cannot mistake `verify_result`
  alone for final delivery approval.

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
- Provider tools and handoff acceptance should register flat and nested manifest
  entries for `voiceover_provider_plan`, `narration_manifest`, and
  `subtitle_voiceover_build_handoff`.

**Acceptance:**

- Missing required narration blocks BUILD/delivery.
- Missing caption audit blocks required subtitle delivery.
- Provider unavailable reason includes missing module/model/python/repo details where available.
- Manifest records subtitle/voiceover handoff artifacts.
- Allowed provider fallback records `fallback_used`, `fallback_reason`, and
  `selected_provider`; silent fallback is not accepted.
- If `preferred_provider=voxcpm` and runtime is unavailable:
  - `fallback_allowed=false` routes to repair/needs-context;
  - `fallback_allowed=true` records selected fallback provider and reason;
  - no branch may claim narration-ready without actual audio or an explicit
    deferred contract.

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
- Route acceptance writes flat and nested manifest entries for effect evidence.
- Unsupported required effects write a blocked route acceptance report and no
  `effect_handoff.json`.
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

### Phase 7.5: BUILD Convergence Surface

**Goal:** Make BUILD eligibility explicit after branch handoffs. BUILD should
not infer readiness from the existence of random files.

**Likely files:**

- BUILD/dry-build CLI adapters such as `video_tools.py contract-dry-build`
- `tools/pipeline_home.py`
- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/dashboard_state.py`
- tests that cover BUILD eligibility and branch handoff consumption

**BUILD prerequisites are AND conditions:**

1. `segment_contract.json` exists and passes contract/spec review.
2. Material requirements are either accepted, waived with reason, or explicitly
   marked not applicable.
3. Required audio has an accepted audio handoff and, if mixed, a valid
   `audio_build_handoff.json`.
4. Required subtitles/voiceover have accepted handoff and readability/narration
   evidence, or a valid deferred contract with return point.
5. Required effects have accepted capability/review/handoff evidence, or a
   valid deferred contract with return point.
6. Workbench patches are either absent, draft-only, or routed back and accepted
   by the owning branch.

Deferred contracts count as satisfying a BUILD prerequisite only when they
include owner, reason, return point, gate, and a statement that BUILD is allowed
to proceed without that branch. Deferred contracts do not satisfy Delivery
unless the Delivery Gate has an explicit waiver rule for that contract.

**Required BUILD handoff summary:**

```json
{
  "build_eligibility": {
    "ready": false,
    "blocking": ["missing_audio_build_handoff"],
    "deferred": [
      {
        "contract": "effect_policy",
        "owner": "effect_factory",
        "return_point": "after_preview_review"
      }
    ],
    "consumed_handoffs": {
      "material": "project_material_map.json",
      "audio": null,
      "subtitle_voiceover": "subtitle_voiceover_build_handoff.json",
      "effect": null
    }
  }
}
```

**Acceptance:**

- Missing required branch handoff blocks BUILD.
- Valid deferred branch contract allows BUILD only when explicitly marked
  build-deferable.
- BUILD consumes manifest-backed handoffs and reports stale/missing manifest
  entries.
- BUILD does not write `final.mp4` during dry-build or handoff validation.

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

When implementation begins, start with the smallest convergent slice:

1. Stage 0 child contract passthrough test.
2. Audio section requirement contract.
3. Audio handoff `required_track_count` and probe/license gate.
4. Audio mix duration clamp/fade handoff.
5. Manifest-backed `pipeline_home.py` lookup.
6. Subtitle/Voiceover provider readiness visibility.
7. Delivery Gate branch-evidence fail-closed tests.

Commit after each coherent slice. Do not mix UI redesign with this convergence pass.

## 10. Corrected Implementation Slice

The older Section 9 list is superseded by this corrected order. Use this order
when implementation begins:

1. Baseline audit and focused test snapshot.
2. Shared state/manifest/passthrough skeleton.
3. Stage 0 child contract alignment.
4. Audio section requirement contract.
5. Audio handoff `required_track_count` and probe/license gate.
6. Audio mix duration clamp/fade handoff.
7. Subtitle/Voiceover provider readiness visibility.
8. Effect Factory manifest and required-evidence alignment.
9. BUILD convergence surface.
10. Delivery Gate branch-evidence fail-closed tests.
11. Three happy path acceptance runs.

Commit after each coherent slice. Do not mix UI redesign with this convergence
pass.

## 11. Execution Guardrails

This plan should be executed as a sequence of bounded changes, not as one large
rewrite.

Recommended loop per slice:

```text
read owning docs
write or update failing focused tests
implement the smallest behavior
run focused tests
update route docs/skill contract if behavior changed
commit
continue
```

Do not start provider downloads, Remotion previews, ffmpeg final renders, or
long E2E runs while implementing contract/gate slices. Those belong to Phase 8
or explicit manual smoke tests.

If a slice requires changing current behavior and current tests disagree with
the construction plan, prefer adding an explicit migration note in the test or
plan over silently changing the route semantics.

## 12. Documentation Updates Required During Execution

Whenever implementation changes behavior, update the matching operator-facing
document in the same commit:

| Code behavior changed | Update |
|---|---|
| Stage 0 entry/path/child contract | `RUNBOOK.md`, `docs/pipeline-decision-tree.md`, `skills/video-pipeline-route.md` |
| Branch ownership or tool ownership | `docs/branch-contract-registry.json`, `docs/branch-contract-registry.md`, `docs/stage-tool-simplification.md` |
| Pipeline stage map or generated route map | `docs/video-pipeline-operating-map.md`, generated map if applicable |
| Soundtrack/audio branch | `docs/soundtrack-arranger-route.md`, soundtrack/audio skill docs |
| Subtitle/voiceover branch | `RUNBOOK.md`, subtitle/voiceover skill docs if present |
| Effect Factory branch | `docs/effect-factory-route.md`, `skills/video-effect-factory.md`, `skills/remotion-effect-worker.md` |
| Workbench route-back | `docs/workbench-dashboard-integration.md` |
| Verify/Delivery gate | `RUNBOOK.md`, `docs/pipeline-decision-tree.md` |

Docs should remain concise and operational. Do not move construction-only
details into `RUNBOOK.md`; link to this construction plan instead.

## 13. Open Risks To Track During Execution

| Risk | Mitigation in this plan |
|---|---|
| Stage 0 child contracts are silently dropped by adapters | Phase 0.5 and Phase 1 passthrough tests |
| Branch tools emit unclassified next actions | Section 4.1 taxonomy and Phase 0.5 tests |
| Manifest and fallback search disagree | Section 4.3 manifest stale/missing fail-closed behavior |
| Network/API tests become flaky | Phase 2 mock-first provider tests; real downloads only in smoke/happy path |
| Audio length and video length drift | Phase 3 clamp/fade and gap reporting |
| VoxCPM unavailable but narration is marked ready | Phase 5 provider readiness fail-closed rule |
| Effect Factory returns generic assets for required effects | Phase 6 capability/review/evidence gate |
| Workbench overwrites canonical truth | Phase 7 route-back guard |
| `verify_result.pass=true` is mistaken for delivery pass | Phase 4 Delivery Gate evidence report |
| Full regression is too long for every slice | Focused tests per phase; full regression at end or checkpoint |

## 14. Execution Checklist For The Next Worker

This checklist turns the phase plan into small implementation slices. Each
slice should be implemented, tested, documented, and committed before moving to
the next slice.

### Slice 0: Baseline Snapshot

**Purpose:** Prove the worker understands the current repo before touching code.

**Read:**

- `RUNBOOK.md`
- `docs/pipeline-decision-tree.md`
- `docs/branch-contract-registry.json`
- `docs/stage-tool-simplification.md`
- `docs/video-pipeline-operating-map.md`
- this construction plan

**Run:**

```powershell
git status --short
python tools\skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --json
python -m unittest tests.test_branch_contract_registry tests.test_skill_tool_contracts -q
```

**Pass condition:**

- no unrelated tracked edits are mixed into the construction work;
- tool/skill ownership audit passes or known exceptions are documented;
- no source code changes in this slice.

### Slice 1: Shared Route State Taxonomy

**Purpose:** Make every route output classifiable before branch work expands.

**Files likely touched:**

- `tools/pipeline_home.py`
- `video_pipeline_core/dashboard_state.py`
- `video_pipeline_core/runtime_orchestrator.py`
- `video_pipeline_core/node_registry.py`
- `tests/test_pipeline_home.py`
- `tests/test_dashboard_state.py`

**TDD first:**

- add a fixture with executable action such as `soundtrack-arrange`;
- add a fixture with review stop such as `await_map_review`;
- add a fixture with repair stop such as `repair_audio_handoff`;
- add a fixture with unknown action;
- add a fixture where `state.json.next_action` conflicts with branch report.

**Pass condition:**

- executable actions include owner and safe command;
- review/repair actions include owner and stop reason but no unsafe command;
- unknown or conflicting actions fail closed.

**Run:**

```powershell
python -m unittest tests.test_pipeline_home tests.test_dashboard_state -q
```

### Slice 2: Manifest Reader And Stale Evidence Gate

**Purpose:** Make branch handoffs discoverable by manifest, not filename guess.

**Files likely touched:**

- a small manifest helper if one exists or is needed;
- `tools/pipeline_home.py`
- `video_pipeline_core/dashboard_state.py`
- `video_pipeline_core/delivery_gate.py`
- `tests/test_pipeline_home.py`
- `tests/test_dashboard_state.py`
- `tests/test_delivery_gate.py`

**TDD first:**

- flat manifest key resolves;
- nested `artifacts.<key>.path` resolves;
- relative and absolute paths resolve;
- stale manifest path fails closed;
- manifest status not `accepted` does not satisfy required handoff;
- fallback filename search still works only when no manifest key exists.

**Pass condition:**

- manifest-backed handoffs are the preferred source;
- stale/missing manifest entries appear as repair blockers in home/dashboard
  and Delivery Gate.

**Run:**

```powershell
python -m unittest tests.test_pipeline_home tests.test_dashboard_state tests.test_delivery_gate -q
```

### Slice 3: Stage 0 Child Contract Passthrough

**Purpose:** Prevent Stage 0 decisions from disappearing during route
conversion.

**Files likely touched:**

- `video_pipeline_core/video_intent_planner.py`
- contract/story/timeline adapter modules that already transform intent
- `tests/test_video_intent_planner.py`
- relevant adapter tests such as `tests/test_blueprint_to_contract.py` or
  `tests/test_contract_adapter.py`
- `RUNBOOK.md`
- `docs/pipeline-decision-tree.md`
- `skills/video-pipeline-route.md`

**TDD first:**

- fuzzy whole-video request creates all child contracts;
- required and deferred child contracts survive intent -> contract conversion;
- adapter dropping `soundtrack_contract`, `subtitle_voiceover_contract`, or
  `effect_policy` fails.

**Pass condition:**

- every downstream build-facing artifact can expose `stage0_child_contracts`
  or explicit `deferred_child_contracts[]`;
- deferred contract includes owner, reason, return point, gate, and whether it
  is build-deferable.

**Run:**

```powershell
python -m unittest tests.test_video_intent_planner tests.test_contract_adapter tests.test_pipeline_home -q
```

If a named adapter test does not exist, add the smallest focused test next to
the adapter being changed.

### Slice 4: Soundtrack Requirement / Source / Probe Contract

**Purpose:** Make music selection section-aware and license/probe-gated.

**Files likely touched:**

- `video_pipeline_core/soundtrack_arranger.py`
- `video_pipeline_core/soundtrack_providers.py`
- `video_pipeline_core/soundtrack_probe.py`
- `video_pipeline_core/audio_handoff_acceptance.py`
- `tools/soundtrack_flow_acceptance.py`
- `docs/soundtrack-arranger-route.md`
- `skills/soundtrack-arranger.md`
- soundtrack tests

**TDD first:**

- `required_track_count` is derived from sections;
- selected tracks must satisfy section role/duration/vocal policy;
- missing license note or URL blocks handoff;
- missing probe blocks deliverable required audio;
- Jamendo/provider calls are mocked in tests;
- provider failure returns repair/needs-context with reason.

**Pass condition:**

- fake/no-render acceptance can complete without network;
- real download path is isolated to smoke/happy path and writes under `runs/`
  or `.tmp/`;
- provider metadata includes provider, query, source id/path, license, fallback.

**Run:**

```powershell
python -m unittest tests.test_soundtrack_arranger tests.test_soundtrack_providers tests.test_soundtrack_probe tests.test_audio_handoff_acceptance tests.test_soundtrack_flow_acceptance -q
```

### Slice 5: Audio Mix BUILD Handoff

**Purpose:** Convert accepted audio into BUILD-facing evidence without writing
final video.

**Files likely touched:**

- `video_pipeline_core/audio_mix_plan_executor.py`
- `tools/audio_mix_plan_execute.py`
- `tools/pipeline_home.py`
- `video_pipeline_core/dashboard_state.py`
- `tests/test_audio_mix_plan_executor.py`
- `tests/test_pipeline_home.py`

**TDD first:**

- audio longer than video clamps to video duration and fades out;
- audio shorter than video reports gap and routes to repair/waiver;
- speech-critical sections require ducking/preservation evidence;
- `audio_build_handoff.json` is written to manifest only when mix evidence is
  accepted.

**Pass condition:**

- `final_audio.wav`, `audio_mix_report.json`, and
  `audio_build_handoff.json` can satisfy BUILD eligibility;
- no `final.mp4` is written;
- missing or failed audio mix routes to `repair_audio_handoff`.

**Run:**

```powershell
python -m unittest tests.test_audio_mix_plan_executor tests.test_pipeline_home tests.test_dashboard_state -q
```

### Slice 6: Subtitle / Voiceover Provider Visibility

**Purpose:** Make narration/subtitle readiness explicit, especially VoxCPM
runtime and fallback behavior.

**Files likely touched:**

- `video_pipeline_core/subtitle_voiceover_handoff.py`
- `video_pipeline_core/voiceover_provider.py`
- `tools/subtitle_voiceover_handoff_accept.py`
- `tools/voxcpm_runtime_check.py`
- `tools/voxcpm_voiceover_provider.py`
- subtitle/voiceover tests
- `RUNBOOK.md`

**TDD first:**

- `preferred_provider=voxcpm` unavailable with `fallback_allowed=false` blocks;
- same unavailable provider with `fallback_allowed=true` records selected
  fallback and reason;
- no branch claims narration-ready without actual audio or deferred contract;
- caption audit missing blocks required subtitle delivery.

**Pass condition:**

- handoff report includes provider, selected provider, fallback_used,
  fallback_reason, runtime check path, caption/narration evidence;
- manifest includes subtitle/voiceover handoff keys.

**Run:**

```powershell
python -m unittest tests.test_subtitle_voiceover_handoff tests.test_voiceover_provider tests.test_voxcpm_voiceover_provider_cli tests.test_pipeline_home -q
```

### Slice 7: Effect Factory Evidence And Boundary

**Purpose:** Keep Effect Factory as a semantic-to-capability branch, not a
template shortcut or final renderer.

**Files likely touched:**

- `tools/visual_technique_plan.py`
- `tools/effect_factory_route_acceptance.py`
- `tools/effect_factory_boundary_acceptance.py`
- `video_pipeline_core/effect_*`
- `skills/video-effect-factory.md`
- `skills/remotion-effect-worker.md`
- `docs/effect-factory-route.md`
- effect tests

**TDD first:**

- bounded effect request creates reviewable parameter contract;
- fuzzy whole-video style records `effect_policy` and does not render;
- unsupported required effect writes blocked report and no handoff;
- different effect intents do not collapse into one generic output;
- manifest indexes effect evidence.

**Pass condition:**

- no branch writes `final.mp4`;
- required effect evidence is visible to Delivery Gate;
- Workbench/BUILD can consume effect handoff only after review/promotion.

**Run:**

```powershell
python -m unittest tests.test_effect_factory_route_acceptance tests.test_effect_factory_boundary_acceptance tests.test_effect_capability_review tests.test_effect_render_verification tests.test_pipeline_home -q
```

### Slice 8: BUILD Eligibility Convergence

**Purpose:** BUILD should consume accepted handoffs and report blockers before
render.

**Files likely touched:**

- `tools/pipeline_home.py`
- BUILD/dry-build adapter modules
- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/dashboard_state.py`
- build/home/delivery tests

**TDD first:**

- missing required material/audio/subtitle/effect handoff blocks BUILD;
- valid deferred build-deferable branch contract allows BUILD but not Delivery;
- stale manifest entry blocks BUILD;
- all accepted handoffs produce `build_eligibility.ready=true`.

**Pass condition:**

- `build_eligibility` reports `ready`, `blocking`, `deferred`, and
  `consumed_handoffs`;
- dry-build/handoff validation does not write `final.mp4`.

**Run:**

```powershell
python -m unittest tests.test_pipeline_home tests.test_delivery_gate tests.test_dashboard_state -q
```

### Slice 9: Delivery Gate Branch Evidence

**Purpose:** A thin `verify_result.pass=true` can never be mistaken for final
approval.

**Files likely touched:**

- `video_pipeline_core/delivery_gate.py`
- `tools/write_delivery_gate_report.py`
- `video_pipeline_core/dashboard_state.py`
- `tools/pipeline_home.py`
- delivery tests

**TDD first:**

- `verify_result.json = {"pass": true}` plus missing audio evidence fails;
- missing material map id / need ref evidence fails;
- missing subtitle/voiceover evidence fails when required;
- missing effect evidence fails when required;
- Workbench preview not promoted fails delivery/promotes to review route.

**Pass condition:**

- delivery report includes technical verify verdict and semantic branch gate
  verdict;
- repair route points to the owning branch, not generic failure.

**Run:**

```powershell
python -m unittest tests.test_delivery_gate tests.test_delivery_gate_report tests.test_pipeline_home tests.test_dashboard_state -q
```

### Slice 10: Three Happy Path Acceptance Runs

**Purpose:** Prove the converged route is operable end-to-end at bounded scope.

**Run folders:**

- `runs/convergence_happy_path/<timestamp>/single_long_source_highlight`
- `runs/convergence_happy_path/<timestamp>/multi_material_recap`
- `runs/convergence_happy_path/<timestamp>/story_first_generated`

**Requirements:**

- run commands and interaction assumptions are written into each run folder;
- no real provider/network call unless this is explicitly a happy-path smoke;
- previews are not promoted unless a review decision artifact says so;
- every run ends with `pipeline_home.py --json` output saved in the folder;
- every run includes cleanup notes and generated file size summary.

**Pass condition:**

- Single long source: transcript/script logic exists before cut plan, original
  audio/music policy explicit, no half-sentence cut in accepted preview plan.
- Multi-material recap: material matrix/contact evidence exists, music/effect/
  subtitle contracts are resolved or explicitly deferred, Delivery Gate reports
  evidence truthfully.
- No-material story: provider handoff exists, placeholder text-card images are
  not promoted, generated material candidates require review.

**Run:**

```powershell
python tools\pipeline_home.py --run RUN_DIR --json
python -m unittest tests.test_material_first_happy_path tests.test_story_first_provider_happy_path tests.test_final_product_verify -q
```

Use additional focused tests for source-highlight paths when the run exercises
single-long-source clipping.

## 15. Final Handoff Report Template

At the end of construction, write a concise handoff report under the final run
or construction folder with this structure:

```markdown
# Mainline Branch Convergence Handoff

## Scope Completed
- ...

## Commits
- ...

## Tests Run
- command: result

## Branch Status
| Branch | Status | Evidence |
|---|---|---|
| Main pipeline | ... | ... |
| Material Map | ... | ... |
| Soundtrack / Audio | ... | ... |
| Subtitle / Voiceover | ... | ... |
| Effect Factory | ... | ... |
| Workbench / Brownfield | ... | ... |
| Verify / Delivery | ... | ... |

## Happy Path Runs
| Path | Run folder | Result | Promotion status |
|---|---|---|---|

## Remaining Risks
- ...
```
