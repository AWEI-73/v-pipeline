# Editing Quality and Capability Dispatch Convergence Implementation Plan

> **For agentic workers:** REQUIRED: Use `superpowers:executing-plans` to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Use one sequential writer; do not dispatch subagents because the 39-second candidate, `video_tools.py`, contract parser, and Skill contracts are shared hot state.

**Goal:** Wire Material Map diversity and speech-aware ducking into one fresh Canon 67 39-second candidate, then converge Hermes tools behind one live capability catalog with orphan prevention while leaving Workbench artifacts and promotion boundaries unchanged.

**Architecture:** Existing Tools remain the deterministic data plane. Owning Domain Skills remain the only `TOOL_CONTRACT` write source. A shared parser builds live Capability Cards in memory, and one read-only `dispatch-capabilities` command lets Director Skills and agents find them. The Editing Loop remains a thin control doctrine over existing factory capabilities; this campaign adds no route runner, daemon, registry database, or second orchestrator.

**Tech Stack:** Python 3.11, `unittest`, ffmpeg/ffprobe, JSON/Markdown artifacts, existing Hermes V Pipeline CLIs, Git.

---

## Authority, State, and Workspace Rules

- Product design: `docs/superpowers/specs/2026-07-12-editing-quality-and-capability-dispatch-convergence-design.md`.
- Formal execution boundary: `docs/construction-guides/work-orders/2026-07-12-editing-quality-and-capability-dispatch-convergence.md`.
- Current design base must include commit `bc9b3750` or a descendant.
- Frozen old candidate: `.tmp/editing_loop_39s_integrated_campaign/wave_r/r5/final.mp4`, SHA-256 `FE4366FC7D6C308442FD7A21CFFC40D6E33404D50FD0CAFEE3CAFBAD5834F5E2`.
- New evidence root: `.tmp/editing_quality_capability_convergence/**`; never overwrite Wave R evidence.
- Use the current workspace, not a new worktree. The current canonical `skills/editing-loop-director.md` contains approved uncommitted work that is absent from HEAD; a worktree would create a conflicting second truth. Record pre-hashes and patch in place.
- Never stage or commit pre-existing dirty content. If an authorized file is dirty before this campaign, record its pre-hash, patch only the intended section, and leave it unstaged for integrator reconciliation.
- `human_creative_approval=false` and `final_delivery_claimed=false` throughout.
- Workbench compatibility is a hard regression boundary: no new required field in existing rough-cut, preview, patch, audio, effect, or handoff artifacts.

## Planned File Map

### Wave A1 — Material Map and picture selection

- Modify: `video_pipeline_core/material_retrieval.py`
- Modify: `video_pipeline_core/material_rough_cut.py`
- Modify only for thin CLI pass-through/read-back if RED requires: `tools/material_rough_cut.py`
- Modify if the RED test proves the call-chain needs it: `video_pipeline_core/mv_cut.py`
- Modify: `video_pipeline_core/semantic_novelty_audit.py`
- Modify: `tests/test_material_retrieval.py`
- Modify: `tests/test_material_rough_cut.py`
- Modify: `tests/test_map_retrieval_wiring.py`
- Modify: `tests/test_mv_cut.py`
- Modify: `tests/test_semantic_novelty_audit.py`
- Use without schema changes: `video_pipeline_core/project_material_map.py`, `video_pipeline_core/visual_diversity_review.py`

### Wave A2/A3 — Audio and forward candidate

- Modify: `video_pipeline_core/audio_mix_plan_executor.py`
- Modify only if required by the opt-in public contract: `video_pipeline_core/audio_handoff_acceptance.py`
- Modify: `tests/test_audio_mix_plan_executor.py`
- Modify if contract validation changes: `tests/test_audio_handoff_acceptance.py`
- Re-run adjacent existing tests: `tests/test_soundtrack_arranger.py`, `tests/test_soundtrack_probe.py`, `tests/test_delivery_gate.py`, `tests/test_preview_timeline.py`

### Wave B — Shared parser, live catalog, and contracts

- Create: `video_pipeline_core/skill_tool_contract.py`
- Create: `video_pipeline_core/capability_catalog.py`
- Create: `tests/test_skill_tool_contract_parser.py`
- Create: `tests/test_dispatch_capabilities.py`
- Modify: `tools/skill_tool_contract_audit.py`
- Modify: `tools/pipeline_interface_discovery.py`
- Modify: `video_pipeline_core/tool_command_catalog.py`
- Modify: `video_tools.py`
- Modify: `tests/test_skill_tool_contracts.py`
- Modify: `tests/test_pipeline_interface_discovery.py`
- Modify: `tests/test_pipeline_interface_audit.py`
- Modify: `tests/test_video_tools_command_catalog.py`
- Modify the `TOOL_CONTRACT` blocks in the 11 existing operational Domain Skills listed in Chunk 4.
- Patch only the capability lookup section in `skills/editing-loop-director.md`; preserve its pre-existing dirty content.
- Re-run, but do not change unless a real regression is found: `tests/test_workbench_handoff.py`, `tests/test_preview_timeline.py`, `tests/test_workbench_contract_sync.py`, `tests/test_workbench_draft_rerender.py`.

## Shared Data Shapes

The opt-in speech-aware plan shape is backward compatible with the current string policy:

```json
{
  "ducking_policy": "speech_aware",
  "ducking": {
    "duck_db": -12.0,
    "attack_ms": 80,
    "release_ms": 300,
    "activity_source": "protected_audio_silencedetect"
  }
}
```

`activity_source` is not user-supplied timing. The executor derives speech/silence
runs from the actual protected audio using the existing
`video_pipeline_core.material_map.detect_speech_runs()` behavior:

```text
ffmpeg -hide_banner -i $PROTECTED_AUDIO_FILE \
  -af silencedetect=noise=-35dB:d=0.4 -f null -
```

`$PROTECTED_AUDIO_FILE` means the resolved `audio_file` of the protected
`preserve_original_audio` placement; the executor writes the resolved absolute
path into its command evidence.

The fixed detector threshold (`-35 dBFS`) and minimum silence (`0.4s`) are
reported evidence, not configurable public fields in this first version. An
empty/failed detection makes speech-aware execution fail closed; transcript cue
windows remain text truth but are not used as VAD windows.

The live Capability Card is derived, never hand-maintained as a second catalog:

```json
{
  "capability_id": "cap.audio-director.audio-mix-plan-execute.v1",
  "owner": "audio-director",
  "stage_owner": "audio_director_mix_execution",
  "kind": "canonical",
  "tool": "tools/audio_mix_plan_execute.py",
  "loops": ["L3"],
  "maturity": "bounded",
  "certified_scope": "Canon 67 39s speech-aware preview mix",
  "when": "execute an accepted audio mix plan without rendering video",
  "inputs": ["audio_mix_plan.json", "audio_handoff_acceptance.json"],
  "outputs": ["final_audio.wav", "audio_mix_report.json"],
  "stop_if": ["acceptance is not ok", "required audio file is missing"],
  "source_skill": "skills/audio-director.md"
}
```

Canonical entries outside Editing Loop may use `"loops": []`; their parent contract's non-empty `stage_owner` supplies the stage classification. `certified_scope` is required only for `bounded` or `certified` maturity and must not overclaim evidence.

---

## Chunk 1 — Freeze State and Wire L0/L1 Diversity

### Task 1: Freeze the baseline and create a command ledger

**Files:**
- Create: `.tmp/editing_quality_capability_convergence/baseline/**`
- Create: `.tmp/editing_quality_capability_convergence/campaign_status.md`

- [ ] **Step 1: Read authority in order**

Read `AGENTS.md`, the design spec, this plan, the formal work order, `skills/material-map.md`, `skills/audio-director.md`, `skills/verify.md`, and `skills/editing-loop-director.md` with explicit UTF-8.

- [ ] **Step 2: Record immutable inputs**

Record `git rev-parse HEAD`, `git status --short --branch`, SHA-256 for every tracked-dirty file, and a baseline manifest enumerating the old candidate plus the exact protected Wave R inputs: source-speech WAV, owner transcript decision, 12-cue SRT, repaired lower-third contract/asset/handoff, L1 rough-cut plan, L3 mix plan/report, delivery gate, and L5 packet. Expected old candidate hash is the fixed value above. Any missing path or hash mismatch is a structural stop.

- [ ] **Step 3: Capture dynamic registry baselines**

Run:

```powershell
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/editing_quality_capability_convergence/baseline/skill_tool_contract_audit.json
C:/Users/user/miniconda3/python.exe tools/pipeline_interface_discovery.py --skills-dir skills --tools-dir tools --out .tmp/editing_quality_capability_convergence/baseline/pipeline_interface_discovery.json
C:/Users/user/miniconda3/python.exe video_tools.py commands-manifest --out .tmp/editing_quality_capability_convergence/baseline/commands_manifest.json
C:/Users/user/miniconda3/python.exe video_tools.py interface-audit --out .tmp/editing_quality_capability_convergence/baseline/interface_audit.json
```

Expected: each exits `0`. Record actual tool/ownership/command counts; do not freeze historical `107` or `149` as final acceptance values.

- [ ] **Step 4: Start the campaign ledger**

Write command, exit code, output path/hash, PASS/FAIL/UNKNOWN, deviations, and last-green commit after every task. This ledger is evidence, not a second state machine.

### Task 2: Prove actual L0 evidence enters the existing Material Map path

**Files:**
- Modify: `tests/test_map_retrieval_wiring.py`
- Use: `video_pipeline_core/project_material_map.py`
- Use: `video_pipeline_core/visual_diversity_review.py`

- [ ] **Step 1: Add an integration fixture from real L0-shaped fields**

Create a test fixture with the same field names as `.tmp/editing_loop_39s_integrated_campaign/wave_r/l0/l0_selects_provenance.json`: stable asset/scene IDs, source windows, observed caption, `visual_family`, `angle_scale`, `action_family`, subject, story function, evidence refs, and blind spots. Use the existing Project Material Map plus visual-diversity review functions; do not invent a new L0 envelope.

- [ ] **Step 2: Assert honest normalization**

The test must prove reviewed fields survive into a `project_material_map`, missing labels remain absent, source windows and evidence refs remain unchanged, and filenames are never promoted into semantic labels.

- [ ] **Step 3: Run the existing path before adding production code**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_project_material_map tests.test_visual_diversity_review tests.test_map_retrieval_wiring -v
```

Expected: exit `0`. If this passes, no new L0 normalizer is allowed; the missing work is wiring and Skill doctrine. If it fails because an existing approved field is dropped, classify the exact owner-path requirement before changing code; do not create a helper tool to bypass the map.

- [ ] **Step 4: Project the actual Canon 67 L0 records without omitting any record**

Read `.tmp/editing_loop_39s_integrated_campaign/wave_r/l0/l0_selects_provenance.json` as the source evidence. Create these run artifacts:

```text
.tmp/editing_quality_capability_convergence/wave_a/material/materials_db.json
.tmp/editing_quality_capability_convergence/wave_a/material/l0_to_scene_projection.json
.tmp/editing_quality_capability_convergence/wave_a/material/l0_visual_diversity_review.json
```

`l0_to_scene_projection.json` must map every provenance `stable_id` to one asset ID, scene index, source path/window, evidence refs, and blind spots. Talking-head records may be tagged as protected speech anchors; all other records are cutaway candidates. Semantic labels are agent judgment and must name their evidence source. No record may disappear silently.

- [ ] **Step 5: Run the public Material Map surfaces**

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py material-map .tmp/editing_quality_capability_convergence/wave_a/material/materials_db.json --maps-dir .tmp/editing_quality_capability_convergence/wave_a/material/maps --update-db .tmp/editing_quality_capability_convergence/wave_a/material/materials_db.mapped.json --out .tmp/editing_quality_capability_convergence/wave_a/material/material_map.md --selected-only
C:/Users/user/miniconda3/python.exe video_tools.py project-material-map --maps-dir .tmp/editing_quality_capability_convergence/wave_a/material/maps --out .tmp/editing_quality_capability_convergence/wave_a/material/project_material_map.json
C:/Users/user/miniconda3/python.exe video_tools.py visual-diversity-review .tmp/editing_quality_capability_convergence/wave_a/material/project_material_map.json --review .tmp/editing_quality_capability_convergence/wave_a/material/l0_visual_diversity_review.json --out .tmp/editing_quality_capability_convergence/wave_a/material/reviewed_project_material_map.json
```

Expected: each exit `0`. Read back the projection, mapped materials DB, and reviewed map, then write `l0_material_map_readback.json` proving record count equality; every `stable_id` resolves through the projection; the joined source path/hash/window and evidence refs match the actual L0 provenance; missing semantic labels remain missing; no reference film entered the map.

### Task 3: Add opt-in strict diversity with explicit fallback evidence

**Files:**
- Modify: `tests/test_material_retrieval.py`
- Modify: `tests/test_material_rough_cut.py`
- Modify: `tests/test_map_retrieval_wiring.py`
- Modify: `tests/test_mv_cut.py`
- Modify: `video_pipeline_core/material_retrieval.py`
- Modify: `video_pipeline_core/material_rough_cut.py`
- Modify only if CLI pass-through/read-back requires: `tools/material_rough_cut.py`
- Modify: `video_pipeline_core/mv_cut.py`

- [ ] **Step 1: Add RED tests for the observed gap**

Add tests proving all of the following:

```python
# enough alternatives: no cutaway repeats a source or visual family
policy = {
    "max_source_repeats": 1,
    "require_unique_visual_family": True,
}

# insufficient alternatives: selection continues but says why
assert slot["diversity_fallback_reason"] == "eligible_supply_exhausted"

# legacy/no-policy path remains unchanged
assert legacy_result == previous_expected_result
```

Also prove the fixed `talking_head` speech anchor is outside the cutaway repeat ceiling rather than weakening the ceiling globally.

- [ ] **Step 2: Add a RED public-planner integration assertion**

Test both public planning consumers. Invoke `run_mv(fixture_script, None, str(tmp_path / "unused.mp4"), music_path=str(fixture_music), mat_dir=str(tmp_path / "mat"), verbose=False, skip_render=True, target_sec=39.34, burn_text=False, visual_judge="none", material_maps=reviewed_project_material_map, max_source_repeats=1, require_unique_visual_family=True)` and invoke `build_rough_cut_plan(contract_with_opt_in_policy, reviewed_project_material_map)`. Assert both report the ranked Material Map path; produced slots/clips carry `scene_id`, `visual_family`, `diversity_selection_reason`, and any fallback reason; changing that reviewed map changes L1 picks. The material-rough-cut output must already match `tools/rough_cut_plan_execute.py` input shape. A selector-only call or a worker-authored translation is insufficient. The protected source-speech segment must keep its own source/timing and must not consume the cutaway repeat budget.

- [ ] **Step 3: Prove RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_material_retrieval tests.test_material_rough_cut tests.test_map_retrieval_wiring tests.test_mv_cut -v
```

Expected before implementation: nonzero exit because current source-cap fallback and visual-family preference do not emit the required explicit fallback contract and the public planner does not expose the opt-in unique-family control.

- [ ] **Step 4: Implement the smallest opt-in behavior**

Extend `select_diverse_ranked_scenes()` and `plan_ranked_windows()` with an opt-in unique-family policy. Preserve current defaults. When the eligible pool is exhausted, choose the best deterministic fallback and attach a stable reason; do not silently use the full tier. Propagate the optional control through `run_mv()` → `_plan_story_timeline()` → local map-ranked selection and through the opt-in branch of `build_rough_cut_plan()`. The tool wrapper only passes existing contract/project-map inputs and writes returned artifacts; it must not implement a second selector.

- [ ] **Step 5: Prove GREEN and legacy compatibility**

Run the Task 3 test command. Expected: exit `0`, including existing diversity-off, history, source-repeat, window-quality, and no-map fallback cases.

- [ ] **Step 6: Commit only clean authorized production/test files**

Commit the Task 3 files with a narrow message such as `feat: make cutaway diversity fallback explicit`. Do not stage a file that was dirty before Task 1.

### Task 4: Make semantic novelty applicability fail honestly

**Files:**
- Modify: `tests/test_semantic_novelty_audit.py`
- Modify: `video_pipeline_core/semantic_novelty_audit.py`

- [ ] **Step 1: Add RED negative cases**

Assert that a missing render, missing representative hash, or hashing failure returns an explicit `applicability=unknown` (or equivalent existing-schema field) and never a passing result. For a real perceptual FAIL, assert each finding contains the affected timeline clip's stable segment/clip IDs rather than only cluster numbers. Keep valid rendered fixtures and cluster findings unchanged.

- [ ] **Step 2: Prove RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_semantic_novelty_audit -v
```

Expected before implementation: nonzero exit because current no-render behavior can look pass-like.

- [ ] **Step 3: Implement the result-state distinction**

Use the existing report shape where possible. A valid render with enough hashes may PASS/FAIL; an inapplicable audit must be UNKNOWN with a concrete reason. A FAIL must expose `affected_stable_ids` derived from `stable_segment_id`, `stable_id`, or `id` in the audited timeline. Do not lower the distinct-ratio or similar-run thresholds.

- [ ] **Step 4: Prove L1 finding carry-forward**

On a negative rendered fixture, convert the semantic-audit FAIL into `.tmp/editing_quality_capability_convergence/wave_a/picture/l1_findings.json` with `loop=L1`, objective classification, affected stable IDs, evidence refs, `owner_domain=material-map`, and rerun gate. This is a carried finding artifact, not a route runner. If the real 39-second preview fails, the same shape blocks Task 8; if it passes, record an empty finding list plus the audit hash.

- [ ] **Step 5: Prove GREEN**

Run the Task 4 command plus:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_material_retrieval tests.test_material_rough_cut tests.test_map_retrieval_wiring tests.test_mv_cut tests.test_semantic_novelty_audit tests.test_visual_diversity_coverage tests.test_visual_diversity_review -v
```

Expected: exit `0`.

- [ ] **Step 6: Commit only the semantic novelty production/test files**

Commit only the semantic novelty production/test files after Step 5 is green.

---

## Chunk 2 — Add Speech-Aware Ducking and Render the Fresh 39 Seconds

### Task 5: Add the opt-in speech-aware contract and synthetic RED fixture

**Files:**
- Modify: `tests/test_audio_mix_plan_executor.py`
- Modify if validation requires: `tests/test_audio_handoff_acceptance.py`
- Modify later: `video_pipeline_core/audio_mix_plan_executor.py`
- Modify later only if required: `video_pipeline_core/audio_handoff_acceptance.py`

- [ ] **Step 1: Build deterministic 6-second audio fixtures**

Use existing test helpers/ffmpeg to generate continuous BGM and protected speech at `1.0–2.0s` and `4.0–5.0s`. Do not depend on ASR or a network service.

- [ ] **Step 2: Add RED contract tests**

Test defaults and validation for `duck_db=-12.0`, `attack_ms=80`, `release_ms=300`, and the only allowed first-version `activity_source=protected_audio_silencedetect`. Booleans, non-finite numbers, unknown keys, out-of-range depth/timing, a missing protected track, or an empty detector result must fail closed. Existing `duck_under_voice` string plans must retain their current behavior.

- [ ] **Step 3: Add RED rendered-audio acceptance**

Measure the output and assert:

- active BGM RMS is at least `8 dB` below neighboring silent/recovery BGM;
- inter-speech recovery is at least `4 dB` above active BGM;
- protected speech start/duration/gain remain exact;
- output duration differs by at most `20 ms`;
- measured 10–20 ms RMS slices across the `80 ms` attack and `300 ms` release are monotonic between full and ducked gain, and the transition reaches each endpoint within `20 ms` of the requested boundary;
- an actual-final-waveform check compares the rendered mixed audio against the protected source over derived speech windows. A window of at least `0.25s` passes only when absolute lag `<=10 ms`, estimated speech gain error `<=0.5 dB`, and normalized correlation `>=0.70`. With three or more eligible windows, `passing_window_ratio` must be `>=0.90`; with one or two, every eligible window must pass; zero eligible windows is UNKNOWN/blocked;
- existing final-peak limits still pass.

Add negative tests that shift the protected waveform by `50 ms`, change its gain by `2 dB`, or replace one active window; each must fail the final-waveform check.

- [ ] **Step 4: Prove RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_audio_mix_plan_executor tests.test_audio_handoff_acceptance -v
```

Expected before implementation: nonzero exit because the executor applies one scalar `0.28` to an entire overlapping music placement.

### Task 6: Implement and report the dynamic envelope

**Files:**
- Modify: `video_pipeline_core/audio_mix_plan_executor.py`
- Modify only if RED requires: `video_pipeline_core/audio_handoff_acceptance.py`

- [ ] **Step 1: Parse legacy and opt-in policies separately**

Leave `duck_under_voice` on its existing scalar branch. Validate and normalize `speech_aware` into an internal envelope specification without rewriting protected placements.

- [ ] **Step 2: Apply a time-varying envelope on duckable music only**

For the protected placement, call existing `material_map.detect_speech_runs()` with `placement["audio_file"]`, so the executor owns the resolved command shape `ffmpeg -hide_banner -i $PROTECTED_AUDIO_FILE -af silencedetect=noise=-35dB:d=0.4 -f null -`. Convert returned speech runs into a deterministic ffmpeg volume expression/filter using attack, release, and duck depth. Do not use subtitle cues as VAD, mix cutaway source audio, change source speech order, or run ASR inside the render path.

- [ ] **Step 3: Expand `audio_mix_report.json` evidence**

Record mode, parameters, detector command/threshold/minimum silence, derived speech and recovery windows, activity-source audio SHA-256, affected music windows, recovery applicability, protected speech source SHA-256/start/duration/gain, output duration, measured RMS/ramp results, and `protected_speech_waveform_check`. That check must decode the actual `final_audio.wav`, compare it to the protected source in derived active windows, and report lag/correlation/estimated-gain metrics against the fixed tolerances. `ducking_applied=true` alone is insufficient. Keep this evidence nested in `audio_mix_report.json`; do not add a second speech-activity truth artifact.

- [ ] **Step 4: Prove GREEN**

Run the Task 5 command and:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_soundtrack_arranger tests.test_soundtrack_probe tests.test_delivery_gate tests.test_preview_timeline -v
```

Expected: both commands exit `0`; legacy mix plans and Workbench audio projection remain compatible.

- [ ] **Step 5: Commit the bounded audio capability**

Commit only clean authorized audio production/test files with a narrow message such as `feat: add speech-aware music ducking`.

### Task 7: Build the fresh picture plan from Material Map evidence

**Files:**
- Create: `.tmp/editing_quality_capability_convergence/wave_a/picture/**`

**Pinned read-only inputs:**

| Input | Exact path | SHA-256 |
| --- | --- | --- |
| source speech | `.tmp/editing_loop_39s_integrated_campaign/wave_p/source_speech_0_39_34.wav` | `C29A891E8AC670EFAED4D6D47D9A17EF1D10A574876DB628A46759F376AF396D` |
| owner transcript decision | `.tmp/editing_loop_39s_integrated_campaign/wave_r/input_freeze/wave_p/human_transcript_review_decision.json` | `5D40C6ED1555FE9E08E51FA398295FEF16F28496EFA76E671287FF1EFC5DC046` |
| exact SRT | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l4/subtitles.srt` | `D7BB03CECF49D42D242A307B6AA08FD97B157E3991EC6B93C7AFEF65C8B3042C` |
| lower-third contract | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2_repair/effect_contract.json` | `A5C290798FAA158DBFE26DE376CA94071945789B4C56B668904A3B3316F5D6DE` |
| lower-third handoff | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2_repair/effect_handoff.json` | `128DBE79C9E6C23D95C66F1586DA27FCDD8CCFCAE45A3A6D876A88838C918840` |
| lower-third render plan | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2_repair/motion_graphics_runtime/motion_graphics_render_plan.json` | `B27D6D3207AABB6DEB6EF208C12C4F7630CCA638A34462AE6C3AB81D3E51EC49` |
| lower-third manifest | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2_repair/motion_graphics_runtime/motion_graphics_manifest.json` | `0A6BCD3EBC501B32E9A1BB614F62CCF3277EBB26CD596ED78BCBB845A1A997B7` |
| lower-third lifecycle plan | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2_repair/title_effect_lifecycle_plan.json` | `5E59BD1799BF15D42DF2CEF138E7B4CAEDB4227B15E704CB98B9B6ADA119098B` |
| lower-third overlay | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2_repair/motion_graphics_runtime/motion_graphics/fx_supervisor_lower_third_repair_01.overlay.mov` | `3CD03E0A60DDA07876F2E5E437F2C61B9D30F307EECA5EDD04F26F3A1AB68A31` |
| source/subtitle binding evidence | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l4/source_speech_subtitle_evidence.json` | `DBD60D2CB62D7804EDC60AC694A7A75C2A724EC203D3F8D7264E4004163DC81F` |
| BGM | `.tmp/editing_loop_39s_integrated_campaign/wave_r/input_freeze/audio/bgm.mp3` | `3B4BAA4B50E6949AF2D596E40FB9E16886C648D82E5FF524FFF32265DFFC503A` |
| BGM probe | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l3/soundtrack_probe_report.json` | `4AE2E6C47D785FA969C7FC90C7217BBF62683771D1622517E623DF343F908A4D` |

- [ ] **Step 1: Freeze the old L0/L1 inputs but do not copy their decision JSON as truth**

Re-read every pinned hash plus `.tmp/editing_quality_capability_convergence/wave_a/material/reviewed_project_material_map.json` and its Task 2 read-back hash. Re-run selection from that reviewed Project Material Map; do not use old `wave_r/l1/rough_cut_plan.json` as the new decision source.

- [ ] **Step 2: Write the segment contract, not the clip plan**

Write `.tmp/editing_quality_capability_convergence/wave_a/picture/segment_contract.json` from the approved 39-second story and actual L0 projection. It declares the talking-head records as `protected_speech_anchor`, cutaway needs/roles, target duration `39.34`, and the opt-in diversity policy (`max_source_repeats=1`, `require_unique_visual_family=true`, explicit fallback required). It contains no selected clip path/order.

- [ ] **Step 3: Generate the plan through the formal Material Map CLI**

```powershell
C:/Users/user/miniconda3/python.exe tools/material_rough_cut.py --contract .tmp/editing_quality_capability_convergence/wave_a/picture/segment_contract.json --project-map .tmp/editing_quality_capability_convergence/wave_a/material/reviewed_project_material_map.json --out .tmp/editing_quality_capability_convergence/wave_a/picture/rough_cut_plan.json --timeline-out .tmp/editing_quality_capability_convergence/wave_a/picture/timeline_build.json --default-clip-sec 3.0
```

Expected: exit `0`; `rough_cut_plan.ok=true`; total duration `39.34` within one frame; every cutaway carries ranked/diversity evidence; protected speech anchors keep their source windows and do not consume cutaway repeat counts. The tool output, not the worker, is the executor input.

- [ ] **Step 4: Render the picture-only preview through existing public surfaces**

Run:

```powershell
C:/Users/user/miniconda3/python.exe tools/rough_cut_plan_execute.py --rough-cut-plan .tmp/editing_quality_capability_convergence/wave_a/picture/rough_cut_plan.json --audio .tmp/editing_loop_39s_integrated_campaign/wave_p/source_speech_0_39_34.wav --out .tmp/editing_quality_capability_convergence/wave_a/picture/picture_preview.mp4 --report .tmp/editing_quality_capability_convergence/wave_a/picture/rough_cut_preview_report.json --width 1920 --height 1080 --fps 30
```

Expected: exit `0`; one H.264 video stream, source-speech audio present, 39.34 seconds within one frame, and no reference-film source in plan/read-back.

- [ ] **Step 5: Run semantic novelty on the actual render**

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py semantic-novelty-audit .tmp/editing_quality_capability_convergence/wave_a/picture/timeline_build.json --video .tmp/editing_quality_capability_convergence/wave_a/picture/picture_preview.mp4 --out .tmp/editing_quality_capability_convergence/wave_a/picture/semantic_novelty_audit.json
```

Expected: exit `0`; report applicability is not UNKNOWN. A true novelty FAIL is a picture finding and blocks Task 8.

- [ ] **Step 6: Apply the frozen lower third through the existing Effect Factory backend**

Load the frozen motion-graphics manifest, pass its `render_outputs` plus the new `picture_preview.mp4` to `video_pipeline_core.motion_graphics.composite_motion_graphics_outputs()`, and write the returned public-backend command/result to `.tmp/editing_quality_capability_convergence/wave_a/picture/effect_composite_report.json`. Required output is `.tmp/editing_quality_capability_convergence/wave_a/picture/visual_with_lower_third.mp4`. The returned status must be `composited`, the overlay hash/start/duration must equal the pinned evidence, and input audio timing must remain unchanged. Do not substitute a worker-authored ffmpeg command.

### Task 8: Mix, assemble, and verify the new 39-second candidate

**Files:**
- Create: `.tmp/editing_quality_capability_convergence/wave_a/audio/**`
- Create: `.tmp/editing_quality_capability_convergence/wave_a/candidate/**`
- Create: `.tmp/editing_quality_capability_convergence/wave_a/l5/**`

- [ ] **Step 1: Derive activity from the actual protected waveform**

Use the pinned source-speech WAV as the only activity source. The executor must run the fixed `-35dB`/`0.4s` silencedetect path and carry its command/windows inside the new `audio_mix_report.json`; the 12 owner-approved cues remain text/timing truth only. Read the pinned BGM probe: if its vocal windows overlap derived speech, write `.tmp/editing_quality_capability_convergence/wave_a/audio/audio_taste_findings.json` with exact windows and owner-taste status. A finding satisfies the design; do not invent stronger attenuation without a separate policy.

- [ ] **Step 2: Execute the mix through `tools/audio_mix_plan_execute.py`**

Write the opt-in plan and acceptance artifact at the exact paths below, then run:

```powershell
C:/Users/user/miniconda3/python.exe tools/audio_mix_plan_execute.py --plan .tmp/editing_quality_capability_convergence/wave_a/audio/audio_mix_plan.json --acceptance .tmp/editing_quality_capability_convergence/wave_a/audio/audio_handoff_acceptance.json --out-dir .tmp/editing_quality_capability_convergence/wave_a/audio --output-name final_audio.wav --json
```

Expected: exit `0`; `audio_mix_report.json` proves derived activity/recovery windows, protected source hash/start/duration/gain, measured duck/ramp evidence, 39.34-second duration, and `preview_only=true`, `delivery_allowed=false`.

- [ ] **Step 3: Independently gate the actual mixed waveform**

Read `audio_mix_report.json.protected_speech_waveform_check`, which must have decoded `.tmp/editing_quality_capability_convergence/wave_a/audio/final_audio.wav` rather than the plan. For each eligible window, derive one boolean from the same `lag<=10ms`, `gain-error<=0.5dB`, and `correlation>=0.70` rule used by Task 5. Require ratio `>=0.90` when at least three windows exist, otherwise require all one/two windows to pass; zero eligible windows, missing metrics, or FAIL blocks assembly.

- [ ] **Step 4: Assemble the four protected layers**

Populate the new candidate run using these exact destinations without changing pinned bytes:

```text
candidate/human_transcript_review_decision.json  <- pinned owner decision
candidate/subtitles.srt                          <- pinned exact SRT
candidate/source_speech_subtitle_evidence.json   <- pinned binding evidence
candidate/effect_contract.json                   <- pinned effect contract
candidate/effect_handoff.json                    <- pinned effect handoff
candidate/motion_graphics_manifest.json          <- pinned motion-graphics manifest
candidate/title_effect_lifecycle_plan.json       <- pinned lifecycle plan
candidate/audio_mix_report.json                  <- new Wave A report
candidate/delivery_requirements.json             <- frozen preview-only policy
```

Then run the public exact-text merger:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py merge-final --visual .tmp/editing_quality_capability_convergence/wave_a/picture/visual_with_lower_third.mp4 --audio .tmp/editing_quality_capability_convergence/wave_a/audio/final_audio.wav --subs .tmp/editing_loop_39s_integrated_campaign/wave_r/l4/subtitles.srt --subtitle-text-policy exact --out .tmp/editing_quality_capability_convergence/wave_a/candidate/final.mp4
```

Expected: exit `0`; one 1920×1080 H.264 stream at 30fps, one AAC stream, and 39.34 seconds within one frame. The audio report must show the protected speech placement has source SHA `C29A891E8AC670EFAED4D6D47D9A17EF1D10A574876DB628A46759F376AF396D`, start `0.0`, duration `39.34`, gain `1.0`, and no time transform; the exact subtitle binding remains 12/12.

- [ ] **Step 5: Prove caption and source binding**

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py caption-audit --srt .tmp/editing_quality_capability_convergence/wave_a/candidate/subtitles.srt --out .tmp/editing_quality_capability_convergence/wave_a/l5/caption_audit.json
C:/Users/user/miniconda3/python.exe tools/source_speech_subtitle_qa.py --run .tmp/editing_quality_capability_convergence/wave_a/candidate --require-approved-text-binding --strict-exit --json
```

Expected: both exit `0`; cue count/text/timing/source hash equality is 12/12.

- [ ] **Step 6: Prove effect lifecycle and rendered media health**

```powershell
C:/Users/user/miniconda3/python.exe tools/title_effect_lifecycle_qa.py --run .tmp/editing_quality_capability_convergence/wave_a/candidate --json
C:/Users/user/miniconda3/python.exe tools/rendered_product_qa.py --run .tmp/editing_quality_capability_convergence/wave_a/candidate --out-dir .tmp/editing_quality_capability_convergence/wave_a/l5/rendered_product_qa --json
C:/Users/user/miniconda3/python.exe video_tools.py black-frame-audit .tmp/editing_quality_capability_convergence/wave_a/candidate/final.mp4 --out .tmp/editing_quality_capability_convergence/wave_a/l5/black_frame_audit.json
C:/Users/user/miniconda3/python.exe video_tools.py probe .tmp/editing_quality_capability_convergence/wave_a/candidate/final.mp4
```

Expected: each exit `0`; lower third remains `0.60–3.20s`, no blocking black/decode/media finding, and profile/duration match Step 3.

- [ ] **Step 7: Prove full-render novelty and perceptual coverage**

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py semantic-novelty-audit .tmp/editing_quality_capability_convergence/wave_a/picture/timeline_build.json --video .tmp/editing_quality_capability_convergence/wave_a/candidate/final.mp4 --out .tmp/editing_quality_capability_convergence/wave_a/l5/semantic_novelty_audit.json
C:/Users/user/miniconda3/python.exe video_tools.py final-product-verify .tmp/editing_quality_capability_convergence/wave_a/candidate/final.mp4 --out-dir .tmp/editing_quality_capability_convergence/wave_a/l5/final_verify --samples 20
C:/Users/user/miniconda3/python.exe video_tools.py perception-field-check .tmp/editing_quality_capability_convergence/wave_a/candidate/final.mp4 --out .tmp/editing_quality_capability_convergence/wave_a/l5/perception_field
```

Expected: each exit `0`; novelty applicability is known, sampling has no coverage gaps, and the report records the actual scene-aligned count rather than assuming 20.

- [ ] **Step 8: Prove preview-only delivery rejection**

```powershell
C:/Users/user/miniconda3/python.exe tools/write_delivery_gate_report.py --run .tmp/editing_quality_capability_convergence/wave_a/candidate --out-name delivery_gate.json --json
```

Expected: exit `1`, with `preview_only_audio_not_delivery_allowed` as the required blocking rule. Any delivery PASS is a structural failure.

- [ ] **Step 9: Write a semantic diff and fresh L5 packet**

Prove subtitles, lower third, source speech, target duration, rights flags, and delivery gate did not drift. Separate objective PASS, agent judgment, owner taste UNKNOWN, music-rights limitation, creative approval, and delivery claim.

- [ ] **Step 10: Allow Wave B after objective GREEN**

Do not stop for an intermediate taste verdict. Wave B is mechanical and may proceed after all Wave A objective checks pass. Save the final owner viewing/listening gate for campaign closure.

---

## Chunk 3 — Build the Single Parser and Read-Only Capability Query

### Task 9: Extract one shared `TOOL_CONTRACT` parser

**Files:**
- Create: `video_pipeline_core/skill_tool_contract.py`
- Create: `tests/test_skill_tool_contract_parser.py`
- Modify: `tools/skill_tool_contract_audit.py`
- Modify: `tools/pipeline_interface_discovery.py`
- Modify: `tests/test_skill_tool_contracts.py`
- Modify: `tests/test_pipeline_interface_discovery.py`

- [ ] **Step 1: Add RED tests for one exact parser API**

Pin these public pure functions in `video_pipeline_core.skill_tool_contract`:

- `parse_json_marker_blocks(path, text, *, start, end)` returns `(blocks, errors)` and stamps each block with its UTF-8 source path;
- `load_contracts(skills_dir)` returns all deterministic `*.md` contract blocks plus parse errors;
- `iter_tool_entries(contract)` returns copied canonical/supporting/internal/diagnostic entries with `_section` and owner metadata;
- `normalize_tool_ref(value)` canonicalizes slashes and the optional leading `python ` token without changing command identity;
- `validate_contract_schema(contracts)` returns sorted structured errors and performs no repository lookup.

Use this concrete RED assertion before extraction:

```python
with mock.patch("video_pipeline_core.skill_tool_contract.load_contracts") as shared:
    shared.return_value = ([{"skill": "fixture", "canonical_tools": []}], [])
    skill_tool_contract_audit.load_contracts(Path("fixture-skills"))
    pipeline_interface_discovery.extract_tool_contracts(Path("fixture-skills"))
    self.assertEqual(shared.call_count, 2)
```

Fixture coverage must include multiple Skill files, malformed JSON, duplicate blocks, UTF-8 Chinese text, canonical/supporting/internal/diagnostic sections, source path/skill/stage metadata, and deterministic ordering. `parse_json_marker_blocks` is also the only marker parser later used for Director consumer references.

- [ ] **Step 2: Prove RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts tests.test_pipeline_interface_discovery -v
```

Expected before implementation: nonzero exit because the two consumers have independent parsing logic.

- [ ] **Step 3: Implement the pure parser module**

Move block extraction, JSON loading, tool-entry flattening, tool-name normalization, source metadata, and shape-only validation into `video_pipeline_core/skill_tool_contract.py`. It must not inspect the filesystem beyond the passed Skill directory, import CLI code, execute tools, validate command dispatch, or write catalog files.

- [ ] **Step 4: Convert both consumers**

Delete their duplicate regex/loader logic and import the shared parser. Preserve existing public CLI shapes and baseline report fields unless the capability schema explicitly adds fields.

- [ ] **Step 5: Add the parser-uniqueness structure guard**

Assert `tools/skill_tool_contract_audit.py` and `tools/pipeline_interface_discovery.py` import the shared loader/normalizer; neither may contain a TOOL_CONTRACT marker regex or a second JSON block loader. The catalog and thin CLI assertions are added only after those files exist in Task 11/12.

- [ ] **Step 6: Prove GREEN**

Run the Task 9 command plus:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_pipeline_interface_audit -v
```

Expected: both exit `0`.

- [ ] **Step 7: Commit the parser extraction**

Commit the new parser, two converted consumers, and their tests only.

### Task 10: Add capability schema validation and orphan checks

**Files:**
- Modify: `video_pipeline_core/skill_tool_contract.py`
- Modify: `tools/skill_tool_contract_audit.py`
- Modify: `tests/test_skill_tool_contract_parser.py`
- Modify: `tests/test_skill_tool_contracts.py`
- Create: `tests/fixtures/capability_contract_audit/**`

- [ ] **Step 1: Separate pure and repository-dependent validation**

Keep field/type/format validation in `validate_contract_schema()`. Add repository-dependent checks only to the existing audit through `audit_repository_contracts(contracts, *, python_tools, dispatch_commands, catalog_commands, capability_consumers)`, returning one JSON-serializable audit report.

Every structured error has exactly these fields and is sorted by code/source/skill/tool/capability ID:

```json
{
  "code": "missing_capability_id",
  "source": "skills/material-map.md",
  "skill": "material-map",
  "capability_id": null,
  "tool": "tools/material_rough_cut.py",
  "message": "canonical tool is missing capability_id"
}
```

The report keeps existing count/ownership fields and adds `capability_errors`, `duplicate_capability_ids`, `broken_tool_references`, `broken_command_references`, `broken_domain_lookups`, `broken_director_references`, `active_legacy_references`, and `noncanonical_public_references`.

`analyze()` remains the CLI wrapper that loads live contracts, discovers Python tools, and supplies the real dispatch/catalog command sets. The later catalog consumes the same shape-validation errors and repository-audit errors; it must not reimplement them.

- [ ] **Step 2: Add `unowned_python_tool` RED fixture**

Expected audit exit `1`, code `unowned_python_tool`.

- [ ] **Step 3: Add `canonical_missing_capability_id` RED fixture**

Expected audit exit `1`, code `missing_capability_id`.

- [ ] **Step 4: Add `invalid_capability_id` RED fixture**

Expected audit exit `1`, code `invalid_capability_id`.

- [ ] **Step 5: Add `duplicate_capability_id` RED fixture**

Expected audit exit `1`, code `duplicate_capability_id`.

- [ ] **Step 6: Add `missing_loops` RED fixture**

Expected audit exit `1`, code `missing_loops`.

- [ ] **Step 7: Add `invalid_loops` RED fixture**

Expected audit exit `1`, code `invalid_loops` for an unknown loop or non-list value.

- [ ] **Step 8: Add `missing_maturity` RED fixture**

Expected audit exit `1`, code `missing_maturity`.

- [ ] **Step 9: Add `invalid_maturity` RED fixture**

Expected audit exit `1`, code `invalid_maturity`; allowed values are exactly `experimental|bounded|certified|legacy`.

- [ ] **Step 10: Add `empty_loops_without_stage_owner` RED fixture**

Expected audit exit `1`, code `missing_loop_or_stage`; an empty loops list is legal only when the parent contract has a non-empty `stage_owner`.

- [ ] **Step 11: Add `bounded_missing_certified_scope` RED fixture**

Expected audit exit `1`, code `missing_certified_scope`.

- [ ] **Step 12: Add `certified_missing_certified_scope` RED fixture**

Expected audit exit `1`, code `missing_certified_scope`.

- [ ] **Step 13: Add `capability_missing_tool` RED fixture**

Expected audit exit `1`, code `missing_tool_reference`.

- [ ] **Step 14: Add `duplicate_canonical_owner` RED fixture**

Expected audit exit `1`, code `duplicate_canonical_owner`.

- [ ] **Step 15: Add `command_missing_both` RED fixture**

Expected audit exit `1`, codes `command_not_dispatched` and `command_not_cataloged`.

- [ ] **Step 16: Add `command_dispatch_only` RED fixture**

Expected audit exit `1`, code `command_not_cataloged` only.

- [ ] **Step 17: Add `command_catalog_only` RED fixture**

Expected audit exit `1`, code `command_not_dispatched` only.

- [ ] **Step 18: Add explicitly shared-owner positive fixture**

Two contracts explicitly set `shared=true` for the same valid canonical reference. Audit must exit `0` and retain both owners in deterministic order.

- [ ] **Step 19: Define Domain and Director reference metadata**

Domain contracts carry `capability_namespace` and `capability_lookup_owner` as top-level fields inside the existing `TOOL_CONTRACT`; do not duplicate them in a second prose/YAML registry. The Director carries one bounded consumer block parsed by the same generic marker parser:

```json
{
  "version": 1,
  "consumer": "editing-loop-director",
  "active_capability_ids": ["cap.material-map.material-rough-cut.v1"],
  "active_namespaces": ["cap.material-map.*"]
}
```

The block markers are `CAPABILITY_CONSUMER_START/END`. It declares consumption only and cannot contain tool ownership.

- [ ] **Step 20: Add `broken_domain_lookup` RED fixture**

Expected audit exit `1`, code `broken_domain_lookup`.

- [ ] **Step 21: Add `broken_director_reference` RED fixture**

Expected audit exit `1`, code `broken_director_reference`.

- [ ] **Step 22: Add `active_legacy_reference` RED fixture**

Expected audit exit `1`, code `active_legacy_reference`. This first version has no replacement/supersedes field: migration resolves it by pointing the active consumer at a non-legacy ID, while the legacy card remains queryable but inactive.

- [ ] **Step 23: Add `supporting_promoted_as_public` RED fixture**

Expected audit exit `1`, code `noncanonical_public_reference`.

- [ ] **Step 24: Add `internal_promoted_as_public` RED fixture**

Expected audit exit `1`, code `noncanonical_public_reference`.

- [ ] **Step 25: Add `diagnostic_promoted_as_public` RED fixture**

Expected audit exit `1`, code `noncanonical_public_reference`.

- [ ] **Step 26: Pin stored-ID immutability**

Add pure `suggest_capability_id(owner, tool_ref)` for proposal generation only; it derives owner plus the normalized tool/command action. `validate_contract_schema()` never calls it. Add a positive test with the same stored ID and two different valid tool references; both versions pass. Never invent numeric suffixes for collisions. The audit report may expose `capability_id_proposals` for missing IDs, but proposals never make `ok=true`.

- [ ] **Step 27: Prove RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts -v
```

Expected before implementation: nonzero because capability schema, consumer references, and fixture error codes do not exist.

- [ ] **Step 28: Implement pure metadata validation**

Implement canonical ID/loops/maturity/scope and Domain lookup field validation in `skill_tool_contract.py` only.

- [ ] **Step 29: Implement repository reference validation**

Implement ownership, Python-tool existence, dispatch/catalog command existence, and shared-owner checks in `skill_tool_contract_audit.py`. Supported command references are the stored forms `video_tools.py command-name` and `python video_tools.py command-name`; tool references use `tools/tool_name.py`.

- [ ] **Step 30: Implement consumer validation**

Parse the Director consumer block through `parse_json_marker_blocks`; validate active IDs/namespaces against canonical non-legacy cards; reject canonical ownership fields in the consumer; reject supporting/internal/diagnostic public references.

- [ ] **Step 31: Prove fixture GREEN**

Run the Task 10 command again. Expected: test process exit `0` because each negative fixture is correctly rejected with audit return `1` and each positive fixture passes. The live repo audit itself is expected to exit `1` until Chunk 4 migration; record that as `EXPECTED_PRE_MIGRATION`, not a regression PASS.

- [ ] **Step 32: Commit capability schema and audit support**

Commit the shared schema additions, existing-audit extensions, fixtures, and tests separately from the catalog/CLI.

### Task 11: Build the live in-memory capability catalog

**Files:**
- Create: `video_pipeline_core/capability_catalog.py`
- Create/modify: `tests/test_dispatch_capabilities.py`
- Modify: `tests/test_skill_tool_contract_parser.py`

- [ ] **Step 1: Add RED tests for exact catalog APIs**

Pin these pure APIs:

- `build_catalog(contracts, *, validation_errors=())` returns a deterministic catalog or an `invalid_catalog` error result without writing files;
- `query_catalog(catalog, *, selector, value)` returns the exact query envelope below;
- `load_live_catalog(skills_dir, *, repository_errors=())` calls the shared loader/shape validator on every invocation, then calls `build_catalog`.

Test deterministic cards, exact ID/owner/loop, Unicode casefold AND-token query over ID/tool/when/inputs/outputs/owner, ambiguous result listing, no-result state, invalid-contract state, and deterministic JSON ordering.

- [ ] **Step 2: Specify return behavior**

Successful exact-ID fixture envelope:

```json
{
  "artifact_role": "capability_query_result",
  "version": 1,
  "ok": true,
  "selector": {"type": "id", "value": "cap.audio-director.audio-mix-plan-execute.v1"},
  "count": 1,
  "results": [
    {
      "capability_id": "cap.audio-director.audio-mix-plan-execute.v1",
      "owner": "audio-director",
      "stage_owner": "audio_director_mix_execution",
      "kind": "canonical",
      "loops": ["L3"],
      "maturity": "bounded",
      "certified_scope": "Canon 67 39s speech-aware preview mix",
      "tool": "tools/audio_mix_plan_execute.py",
      "when": "execute an accepted audio mix plan without rendering video",
      "inputs": ["audio_mix_plan.json", "audio_handoff_acceptance.json"],
      "outputs": ["final_audio.wav", "audio_mix_report.json"],
      "stop_if": ["acceptance is not ok", "required audio file is missing"],
      "source_skill": "skills/audio-director.md"
    }
  ],
  "error": null
}
```

No-match envelope:

```json
{
  "artifact_role": "capability_query_result",
  "version": 1,
  "ok": false,
  "selector": {"type": "query", "value": "definitely-absent"},
  "count": 0,
  "results": [],
  "error": {"code": "no_match", "message": "capability query: no matches"}
}
```

Invalid-catalog envelope has the same top-level fields, `count=0`, empty results,
and `error={"code":"invalid_catalog","message":"capability query: live catalog invalid"}`.
Always require `count == len(results)`. Match maps to exit `0`, no match to exit
`1`, and invalid live catalog to exit `2`. Query terms use deterministic AND
matching. Catalog construction performs no writes/tool execution and rejects
any supplied validation error.

- [ ] **Step 3: Prove RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_dispatch_capabilities -v
```

Expected before implementation: import failure/nonzero exit.

- [ ] **Step 4: Implement a read-only catalog**

Create normalized Capability Cards from the shared parser. Preserve `source_skill` for evidence but treat the owning `TOOL_CONTRACT` block as the only truth source. Do not cache across process runs or create a checked-in catalog.

- [ ] **Step 5: Add liveness and parser-delegation assertions**

Edit a temporary Skill between two `load_live_catalog()` calls and prove the second result changes without a generated catalog file. Extend the Task 9 structure guard so `capability_catalog.py` imports `skill_tool_contract` and contains neither marker parsing nor a second contract schema validator.

- [ ] **Step 6: Prove GREEN**

Run the Task 11 command; expected exit `0`.

### Task 12: Expose `video_tools.py dispatch-capabilities`

**Files:**
- Modify: `video_tools.py`
- Modify: `video_pipeline_core/tool_command_catalog.py`
- Modify: `tests/test_dispatch_capabilities.py`
- Modify: `tests/test_video_tools_command_catalog.py`

- [ ] **Step 1: Add RED CLI tests**

Require exactly one selector from `--id`, `--owner`, `--loop`, or `--query`; `--loop` accepts only `L0`–`L5`. Add the test seam `run_dispatch_capabilities_query(args, *, skills_dir, tools_dir, dispatch_commands, catalog_commands) -> int`, while `cmd_dispatch_capabilities(args)` supplies live defaults. Tests use a migrated temporary Skill directory because the real repo remains intentionally invalid until Chunk 4.

Success prints compact human output unless `--json`. Each card uses this fixed field order: first line is the capability ID followed by a space and maturity in square brackets, then `owner:`, `stage_owner:`, `kind:`, `loops:`, `certified_scope:`, `tool:`, `when:`, `inputs:`, `outputs:`, `stop_if:`, and `source_skill:`. Cards are ID-sorted and separated by `---`. `--json` prints the exact envelope. `--out` writes the exact same envelope to only the explicit path. With both flags, write and print byte-equivalent JSON.

No-match writes/prints the no-match envelope when `--out`/`--json` is present; human mode writes exactly `capability query: no matches` to stderr and no stdout. Runtime-invalid behaves identically with exact stderr `capability query: live catalog invalid`. Argparse selector/loop errors exit `2`, use argparse stderr, and do not create `--out`.

- [ ] **Step 2: Prove RED**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_dispatch_capabilities tests.test_video_tools_command_catalog -v
```

Expected before implementation: nonzero because the command is absent and the command manifest does not classify it.

- [ ] **Step 3: Add one thin CLI adapter**

The command parses live contracts, calls `capability_catalog`, and prints/writes results. It must not execute a capability, choose a route, mutate next-action vocabulary, or persist a repo catalog.

- [ ] **Step 4: Extend the parser-uniqueness guard to the CLI**

Assert `video_tools.py` delegates to `run_dispatch_capabilities_query()`/`capability_catalog` and contains no TOOL_CONTRACT marker parser or capability validation copy.

- [ ] **Step 5: Classify the command**

Add `dispatch-capabilities` to the existing `workspace` command group. Do not create a new group, workflow, or orchestrator.

- [ ] **Step 6: Prove fixture-backed GREEN**

Run the Task 12 command. Expected: exit `0` against the injected migrated fixtures. Do not claim the real repo command is green before Chunk 4.

- [ ] **Step 7: Commit catalog and CLI**

Commit the catalog, CLI/command-catalog changes, and tests only.

---

## Chunk 4 — Migrate Domain Skills, Protect Workbench, and Close

### Task 13: Migrate all existing canonical tool entries

**Files:**
- Modify `TOOL_CONTRACT` blocks only in:
  - `skills/audio-director.md`
  - `skills/brownfield-edit.md`
  - `skills/dashboard.md`
  - `skills/generated-material-producer.md`
  - `skills/material-map.md`
  - `skills/soundtrack-arranger.md`
  - `skills/spec-contract.md`
  - `skills/subtitle-director.md`
  - `skills/verify.md`
  - `skills/video-effect-factory.md`
  - `skills/video-pipeline-route.md`

- [ ] **Step 1: Generate a run-local migration proposal**

Run the pre-migration audit:

```powershell
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/editing_quality_capability_convergence/wave_b/capability_migration_proposal.json
```

Expected: exit `1` only because live canonical entries still lack the new metadata. Read `capability_id_proposals`, require one deterministic proposal per missing canonical entry and no collisions, and verify existing ownership before editing. This run-local audit report is evidence, not a registry; any additional error is a structural stop.

- [ ] **Step 2: Assign bounded metadata without overclaiming**

Add unique ID, loops, maturity, and evidence-bounded `certified_scope` where required. Apply this deterministic evidence rule: use `certified` only when an existing durable artifact explicitly certifies that exact capability and scope; use `bounded` only when focused tests plus a named real forward-test artifact exist; use `legacy` only when current repo text already marks the surface legacy/deprecated; otherwise use `experimental`. The new Material Map diversity and speech-aware audio entries may be `bounded` only to this 39-second evidence. Do not label a whole domain certified. Supporting/internal entries remain owned but do not need capability IDs or Director references.

- [ ] **Step 3: Add Domain lookup fields to the existing contract**

Add `capability_namespace` and `capability_lookup_owner` as top-level fields inside each existing `TOOL_CONTRACT`, matching Task 10's schema. Do not duplicate them into a second prose/YAML registry, copy Capability Cards into prose, or generate per-domain Markdown catalogs.

- [ ] **Step 4: Run the real audit**

```powershell
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/editing_quality_capability_convergence/wave_b/skill_tool_contract_audit.json
```

Expected: exit `0`; no unowned Python tool, duplicate capability, malformed canonical entry, broken tool reference, or invalid metadata.

- [ ] **Step 5: Commit only previously clean Domain Skills**

If a listed Skill was dirty at Task 1, do not stage it; record its pre/post hash and leave it for integrator reconciliation. Otherwise commit the migration as one mechanical contract commit.

### Task 14: Make Editing Loop Director a capability consumer

**Files:**
- Patch only: `skills/editing-loop-director.md`
- Modify: `tests/test_pipeline_skill_boundaries.py`
- Modify if existing doctrine assertions live there: `tests/test_interactive_skill_flow_docs.py`

- [ ] **Step 1: Preserve the dirty authority baseline**

Re-check the Director Skill pre-hash from Task 1. Stop if it changed unexpectedly during the campaign.

- [ ] **Step 2: Add RED boundary tests before patching the Director**

Without changing `skills/editing-loop-director.md`, add assertions that the Director contains exactly one `CAPABILITY_CONSUMER` block, every active reference resolves, Director owns no Domain tool, and deprecated/legacy references require a valid replacement before active use.

- [ ] **Step 3: Prove the pre-change Director fails the new contract**

Run the focused doctrine command below. Expected: exit `1` for the missing Director consumer contract; save the command, output, exit code, and Director pre-hash as RED evidence. Any unrelated failure is not valid RED evidence and must be classified before continuing.

- [ ] **Step 4: Add capability references, not ownership**

Add the single Task 10 `CAPABILITY_CONSUMER` JSON block for active L0–L5 capability IDs/namespaces and point prose to `dispatch-capabilities`. Keep owner gates and the evidence-carrying loop shape. Do not insert copied tool SOP, a second reference list, new route state, or canonical ownership.

- [ ] **Step 5: Re-run focused doctrine tests GREEN**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_pipeline_skill_boundaries tests.test_interactive_skill_flow_docs tests.test_skill_index -v
```

Expected: exit `0`. Leave the Director file unstaged because it was dirty before the campaign; record the exact campaign-only patch.

### Task 15: Prove query usefulness and Workbench non-regression

**Files:**
- Create: `.tmp/editing_quality_capability_convergence/wave_b/catalog_queries/**`
- Do not modify Workbench production code or artifact schemas.

- [ ] **Step 0: Freeze Workbench data-plane code hashes**

Record SHA-256 for `tools/workbench_handoff.py`, `tools/preview_timeline.py`, `tools/timeline_patch.py`, `tools/subtitle_patch.py`, `tools/audio_cue_patch.py`, and `tools/effect_patch.py`, plus the preserved real handoff path chosen in Step 4. These hashes must remain identical through Task 16.

- [ ] **Step 1: Run the four real query modes**

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --owner material-map --out .tmp/editing_quality_capability_convergence/wave_b/catalog_queries/material-map.json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --loop L3 --out .tmp/editing_quality_capability_convergence/wave_b/catalog_queries/l3.json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --query "speech ducking" --out .tmp/editing_quality_capability_convergence/wave_b/catalog_queries/speech-ducking.json
C:/Users/user/miniconda3/python.exe video_tools.py dispatch-capabilities --id cap.audio-director.audio-mix-plan-execute.v1 --out .tmp/editing_quality_capability_convergence/wave_b/catalog_queries/exact-audio.json
```

Expected: each exit `0`, results are small/evidence-backed, and no capability executes.

- [ ] **Step 2: Prove negative query behavior**

Run one nonexistent ID and one nonsense query. Expected: exit `1`, no output falsely marked PASS.

- [ ] **Step 3: Run Workbench backward-compatibility tests**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_workbench_handoff tests.test_preview_timeline tests.test_workbench_contract_sync tests.test_workbench_draft_rerender -v
```

Expected: exit `0` using existing fixtures that have no capability metadata. Do not add capability fields to make them pass.

- [ ] **Step 4: Validate a real old handoff/run if present**

Use the existing public Workbench handoff validation surface on a preserved legacy artifact. Record PASS/UNKNOWN and exact path; missing optional fixture is UNKNOWN, not a reason to change Workbench.

- [ ] **Step 5: Re-read Workbench hashes**

Assert all Step 0 production hashes and the chosen legacy artifact hash are unchanged. Also assert `git diff --name-only` contains no Workbench production path.

### Task 16: Run final audits, one full suite, and write the closure packet

**Files:**
- Create: `.tmp/editing_quality_capability_convergence/final/**`
- Update: `.tmp/editing_quality_capability_convergence/campaign_status.md`

- [ ] **Step 1: Run the combined focused/adjacent suite**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_material_retrieval tests.test_material_rough_cut tests.test_map_retrieval_wiring tests.test_mv_cut tests.test_semantic_novelty_audit tests.test_visual_diversity_coverage tests.test_visual_diversity_review tests.test_audio_mix_plan_executor tests.test_audio_handoff_acceptance tests.test_soundtrack_arranger tests.test_soundtrack_probe tests.test_delivery_gate tests.test_preview_timeline tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts tests.test_pipeline_interface_discovery tests.test_pipeline_interface_audit tests.test_dispatch_capabilities tests.test_video_tools_command_catalog tests.test_pipeline_skill_boundaries tests.test_interactive_skill_flow_docs tests.test_skill_index tests.test_workbench_handoff tests.test_workbench_contract_sync tests.test_workbench_draft_rerender -v
```

Expected: exit `0`.

- [ ] **Step 2: Re-run real repo audits and dynamic count checks**

Regenerate final artifacts with exact commands:

```powershell
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/editing_quality_capability_convergence/final/skill_tool_contract_audit.json
C:/Users/user/miniconda3/python.exe tools/pipeline_interface_discovery.py --skills-dir skills --tools-dir tools --out .tmp/editing_quality_capability_convergence/final/pipeline_interface_discovery.json
C:/Users/user/miniconda3/python.exe video_tools.py commands-manifest --out .tmp/editing_quality_capability_convergence/final/commands_manifest.json
C:/Users/user/miniconda3/python.exe video_tools.py interface-audit --out .tmp/editing_quality_capability_convergence/final/interface_audit.json
```

Expected: each exit `0`. Assert:

```text
owned_python_tool_count == python_tool_count
unclassified_commands == []
duplicate_capability_ids == []
broken_director_references == []
final_command_count >= baseline_command_count + 1
"dispatch-capabilities" is present and classified as "workspace"
```

Record baseline/final count deltas rather than hardcoding historical counts.

- [ ] **Step 3: Prove every orphan guard fails closed case by case**

For every named case directory under `tests/fixtures/capability_contract_audit/` from Task 10 (22 negative fixtures), invoke `tools/skill_tool_contract_audit.py` with that case's `skills/` and `tools/` paths and write its same-name JSON report under `.tmp/editing_quality_capability_convergence/final/negative_audits/`. Every invocation must exit `1` and contain its fixture's exact expected error code. Write `negative_fixture_matrix.json` with 22 rows containing case, command, exit, expected code, observed code, and report hash. A missing row, exit other than `1`, or wrong code blocks closure.

- [ ] **Step 4: Run the full suite exactly once, last**

```powershell
C:/Users/user/miniconda3/python.exe -m unittest discover -s tests
```

Expected: exit `0`. This is one-shot acceptance: a timeout is UNKNOWN and a non-zero completion is FAIL. Either result ends this campaign immediately at the last green commit; perform no repair and no second full-suite run in this campaign. Record the failing evidence and request a separately authorized continuation; only that continuation may repair the cause and run a fresh full suite. Do not edit unrelated owner zones merely to make the suite green.

- [ ] **Step 5: Run repository integrity checks**

```powershell
git diff --check
```

Expected: exit `0`. Explicitly decode every new/modified Chinese Markdown/JSON/SRT file as UTF-8; assert no `U+FFFD` and no suspicious run of four literal question-mark characters.

- [ ] **Step 6: Verify old and new media/evidence hashes**

Re-read the frozen old candidate hash, protected transcript/lower-third inputs, new candidate hash, every closure artifact path/hash, and all Task 15 Workbench production/data-plane hashes after the full suite. The old candidate and Workbench hashes must remain unchanged.

- [ ] **Step 7: Write the worker closure report**

Include commits and diff scope, all commands/exits, baseline/final counts, new candidate/evidence paths and hashes, Workbench compatibility evidence, deviations/LOCAL repairs/skips/blind spots, and separate status for objective quality, agent judgment, owner taste, licensing, creative approval, and delivery.

- [ ] **Step 8: Stop at the consolidated owner gate**

If every objective item is green, set state to `WAITING_OWNER_CONSOLIDATED_FINAL_VERDICT`. Do not upload or claim delivery. Owner reviews only the new final candidate and its short review packet; Wave B does not require a taste verdict.
