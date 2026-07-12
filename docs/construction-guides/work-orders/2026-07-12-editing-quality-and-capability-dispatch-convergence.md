# Work Order — Editing Quality And Capability Dispatch Convergence

Date: 2026-07-12  
Status: ready for execution  
Execution shape: one sequential long-running worker; four ordered chunks, scoped commits, no parallel writers

## 1. Goal And Construction Sources

Complete two verified editing-quality gaps on a fresh Canon 67 39-second candidate, then converge the existing factory into one discoverable Tool → Capability Card → Domain Skill → Director Skill chain with orphan prevention.

Read in this order:

1. `AGENTS.md`
2. `docs/superpowers/specs/2026-07-12-editing-quality-and-capability-dispatch-convergence-design.md`
3. `docs/superpowers/plans/2026-07-12-editing-quality-and-capability-dispatch-convergence.md`
4. this work order
5. `skills/material-map.md`
6. `skills/audio-director.md`
7. `skills/verify.md`
8. `skills/editing-loop-director.md`
9. `.tmp/editing_loop_39s_integrated_campaign/wave_r/r6/review_report.md`
10. `.tmp/editing_loop_39s_integrated_campaign/wave_r/r6/l5_packet.json`

The design fixes architecture and acceptance. The implementation plan supplies exact task steps. This work order supplies authority, ownership, stop-loss, and reporting. A worker may not replace them with a new spec or inferred route.

## 2. Verified Starting Boundary

| Item | Required value |
| --- | --- |
| design base | commit `bc9b3750` or descendant |
| frozen old candidate | `.tmp/editing_loop_39s_integrated_campaign/wave_r/r5/final.mp4` |
| frozen old candidate SHA-256 | `FE4366FC7D6C308442FD7A21CFFC40D6E33404D50FD0CAFEE3CAFBAD5834F5E2` |
| prior technical baseline | full suite previously `2655 tests`, exit `0` |
| new run root | `.tmp/editing_quality_capability_convergence/**` |
| legal success stop | `WAITING_OWNER_CONSOLIDATED_FINAL_VERDICT` |

Before mutation, record HEAD, exact dirty tree, tracked-dirty hashes, old candidate hash, and dynamic tool/command counts. Use the current workspace: `skills/editing-loop-director.md` contains approved uncommitted authority text that is not present in HEAD. Do not create a clean worktree that silently omits it.

## 3. Owner Zone

The worker may edit only the following production/contract paths when the matching implementation-plan RED evidence requires them:

### Wave A1

- `video_pipeline_core/material_retrieval.py`
- `video_pipeline_core/material_rough_cut.py`
- `tools/material_rough_cut.py`, only for thin contract pass-through/read-back if RED requires it
- `video_pipeline_core/mv_cut.py`
- `video_pipeline_core/semantic_novelty_audit.py`
- `tests/test_material_retrieval.py`
- `tests/test_material_rough_cut.py`
- `tests/test_map_retrieval_wiring.py`
- `tests/test_mv_cut.py`
- `tests/test_semantic_novelty_audit.py`

`video_pipeline_core/project_material_map.py` and
`video_pipeline_core/visual_diversity_review.py` are read-only unless the Task 2
existing-path fixture objectively proves an approved field is dropped. If that
happens, stop and report the exact required edit rather than expanding scope.

### Wave A2

- `video_pipeline_core/audio_mix_plan_executor.py`
- `video_pipeline_core/audio_handoff_acceptance.py`, only if opt-in contract validation RED requires it
- `tests/test_audio_mix_plan_executor.py`
- `tests/test_audio_handoff_acceptance.py`

### Wave B

- new `video_pipeline_core/skill_tool_contract.py`
- new `video_pipeline_core/capability_catalog.py`
- `tools/skill_tool_contract_audit.py`
- `tools/pipeline_interface_discovery.py`
- `video_pipeline_core/tool_command_catalog.py`
- `video_tools.py`
- new `tests/test_skill_tool_contract_parser.py`
- new `tests/test_dispatch_capabilities.py`
- new `tests/fixtures/capability_contract_audit/**`
- `tests/test_skill_tool_contracts.py`
- `tests/test_pipeline_interface_discovery.py`
- `tests/test_pipeline_interface_audit.py`
- `tests/test_video_tools_command_catalog.py`
- `tests/test_pipeline_skill_boundaries.py`
- `tests/test_interactive_skill_flow_docs.py`, only for Director capability-reference assertions
- the `TOOL_CONTRACT` blocks and short lookup hints in the 11 Domain Skills listed in plan Task 13
- only the new capability lookup/reference section in `skills/editing-loop-director.md`

### Evidence

- `.tmp/editing_quality_capability_convergence/**`

Each clean production/test group may have one scoped commit after GREEN. Never stage a file that was dirty at baseline. For a baseline-dirty authorized file, record pre/post hashes, patch narrowly, leave unstaged, and include the campaign-only diff in the report.

## 4. Read-Only And Forbidden Zone

- All existing `.tmp/editing_loop_39s_integrated_campaign/wave_r/**` artifacts.
- Raw source media and reference films.
- `AGENTS.md`, `HANDOFF_CURRENT.md`, `RUNBOOK.md`, `docs/INDEX.md`.
- `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`.
- This design, plan, and work order during execution.
- `skills/INDEX.md`, branch registry, artifact dictionary, next-action vocabulary, route runners, and orchestrators.
- Workbench production code, Workbench artifact schemas, `workbench-brownfield` ownership, draft-only promotion boundary, and existing Workbench fixtures.
- Subtitle text/timing, transcript decisions, lower-third content/lifecycle, source-speech truth, and preview-only delivery policy.
- Do not add a `tools/*.py` helper, generated catalog committed to the repo, database, daemon, cache service, router, new workflow, or third `TOOL_CONTRACT` parser.
- Do not build a private renderer/mixer, use a run-local JSON compiler as a production surface, weaken an audit, hand-edit a PASS artifact, or treat process exit alone as product evidence.
- No stage/reset/cleanup of unrelated dirty files; no push, merge, upload, deletion, or final delivery.
- Never set `human_creative_approval=true` or `final_delivery_claimed=true`.

## 5. Ordered Outcomes

Execute all implementation-plan checkboxes in order without an intermediate owner stop:

1. **Chunk 1:** freeze baseline; prove L0 evidence enters the existing Project Material Map; add opt-in cutaway source/family diversity with explicit fallback; make inapplicable semantic novelty UNKNOWN.
2. **Chunk 2:** add opt-in speech-aware BGM envelope with objective 6-second fixture; build one fresh 39.34-second Material-Map-driven candidate; preserve subtitles, lower third, source speech, duration/profile, rights flags, and delivery rejection; produce fresh L5 evidence.
3. **Chunk 3:** extract the duplicated `TOOL_CONTRACT` parsing into one shared module; build a live in-memory Capability Card catalog; expose the read-only `video_tools.py dispatch-capabilities` query and classify it in the existing command catalog.
4. **Chunk 4:** migrate every existing canonical entry to one deterministic capability ID with honest maturity; make Director a consumer; extend the existing orphan audit; prove Workbench legacy artifacts still load; run combined tests, real audits, one final full suite, integrity read-back, and closure report.

Wave B may start after Wave A objective/technical checks are all PASS. Picture/audio taste stays UNKNOWN until the final consolidated owner gate; it does not block mechanical registry work.

## 6. Fixed Decisions

- Existing Tools remain the execution layer. Capability catalog is read-only control-plane metadata.
- Owning Domain Skill `TOOL_CONTRACT` is the only write source.
- `dispatch-capabilities` builds from live contracts on every invocation; `--out` is run-local evidence only.
- Capability ID is `cap.<owner-skill>.<tool-or-public-action>.v<major>`; collisions fail instead of receiving guessed suffixes.
- Canonical entries require ID, loops list, maturity, and a non-empty parent `stage_owner`; `bounded`/`certified` also require evidence-bounded scope. Non-editing tools may use an empty loops list.
- Supporting/internal/diagnostic tools require an owner but are not Director public entries.
- New ducking is opt-in `speech_aware`; legacy `duck_under_voice` behavior is unchanged.
- Speech activity comes from the actual protected waveform through the existing `silencedetect=noise=-35dB:d=0.4` detector; subtitle cue windows remain text truth and are never substituted for VAD.
- Ducking fixture defaults/thresholds are fixed by the design: `-12 dB`, `80 ms`, `300 ms`, active reduction `>=8 dB`, recovery `>=4 dB`, duration delta `<=20 ms`.
- Talking head is a protected speech anchor, not a cutaway subject to repeat ceiling.
- Workbench artifacts do not gain mandatory capability metadata and Workbench does not depend on the new query command.
- Full suite runs once, only after every focused/adjacent test and real audit is green.

## 7. Delegated Decisions

The worker may decide reversible internal details that the fixed tests catch:

- private helper/function names and exact module-internal decomposition;
- the deterministic ffmpeg volume-expression/filter implementation;
- compact human formatting of query results;
- which additional existing adjacent test modules are discovered by imports/diff impact;
- evidence filenames below the authorized run root.

The worker may not decide product taste, licensing, capability ownership changes, new public schemas outside the specified opt-in fields, Workbench behavior changes, threshold relaxation, or owner-zone expansion.

## 8. Red-First And Acceptance

Every behavior change must capture a failing focused test/evidence before production edits. Each plan task lists its exact focused command and expected transition. At the final boundary, all of the following must exit `0`:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_material_retrieval tests.test_material_rough_cut tests.test_map_retrieval_wiring tests.test_mv_cut tests.test_semantic_novelty_audit tests.test_visual_diversity_coverage tests.test_visual_diversity_review tests.test_audio_mix_plan_executor tests.test_audio_handoff_acceptance tests.test_soundtrack_arranger tests.test_soundtrack_probe tests.test_delivery_gate tests.test_preview_timeline tests.test_skill_tool_contract_parser tests.test_skill_tool_contracts tests.test_pipeline_interface_discovery tests.test_pipeline_interface_audit tests.test_dispatch_capabilities tests.test_video_tools_command_catalog tests.test_pipeline_skill_boundaries tests.test_interactive_skill_flow_docs tests.test_skill_index tests.test_workbench_handoff tests.test_workbench_contract_sync tests.test_workbench_draft_rerender -v
C:/Users/user/miniconda3/python.exe tools/skill_tool_contract_audit.py --skills-dir skills --tools-dir tools --out .tmp/editing_quality_capability_convergence/final/skill_tool_contract_audit.json
C:/Users/user/miniconda3/python.exe video_tools.py commands-manifest --out .tmp/editing_quality_capability_convergence/final/commands_manifest.json
C:/Users/user/miniconda3/python.exe video_tools.py interface-audit --out .tmp/editing_quality_capability_convergence/final/interface_audit.json
C:/Users/user/miniconda3/python.exe -m unittest discover -s tests
git diff --check
```

Also require executable/read-back evidence for:

- old candidate hash unchanged;
- new candidate has one H.264 video and one AAC audio stream, 39.34 seconds within one frame;
- source speech continuous and exact 12/12 subtitle text/timing preserved;
- lower-third content/lifecycle unchanged;
- cutaway decisions came from reviewed Project Material Map and record fallback honestly;
- semantic novelty used the actual render and is applicable;
- dynamic ducking changes measured BGM level while protected speech placement stays unchanged;
- preview-only music remains rejected by delivery gate;
- `owned_python_tool_count == python_tool_count` and `unclassified_commands == []` using final dynamic counts;
- no duplicate/broken capability or Director reference;
- all 22 named invalid-contract/orphan fixtures make the existing audit exit `1` with their exact expected error codes;
- final command count is at least baseline + 1 and `dispatch-capabilities` is present in the existing `workspace` group;
- all four real query modes work and nonexistent queries exit `1`;
- legacy Workbench fixtures without capability metadata remain readable;
- Workbench production/data-plane file hashes and the selected legacy handoff hash remain unchanged;
- explicit UTF-8/JSON/path/hash validation passes.

## 9. Stop-Loss

- One LOCAL correction per failure class. The same class recurring is STRUCTURAL; stop at the last green commit.
- Stop immediately on frozen-hash drift, unexpected baseline-dirty hash drift, owner-zone conflict, required forbidden-path edit, transcript/lower-third/source-speech mutation, reference-footage use, delivery-policy bypass, invalid UTF-8, or missing owner truth.
- If Wave A objective evidence cannot pass through public surfaces, do not enter Wave B or register the unproven capability.
- If a real audit finds ambiguous ownership, preserve current owner and stop/report; do not guess.
- Any orphan-audit failure blocks closure; a waiver cannot turn it into PASS.
- The final full suite is one-shot acceptance. A timeout is UNKNOWN and a non-zero completion is FAIL; either result ends this campaign immediately at the last green commit. Do not repair after that run and do not run the suite a second time in this campaign. Record the evidence and request a separately authorized continuation, which may repair the authorized cause and perform its own fresh full-suite run.
- A blocked later chunk does not erase earlier scoped commits or evidence. Preserve them and report PASS/FAIL/UNKNOWN separately.

## 10. Required Worker Report

Write `.tmp/editing_quality_capability_convergence/final/worker_report.md` and update `campaign_status.md` with:

- exact final state and last-green commit;
- pre/post HEAD, dirty tree, and tracked-dirty pre/post hashes;
- each scoped commit with `git show --stat` scope;
- every RED/GREEN/adjacent/full-suite command, exit code, duration, and log path;
- old/new candidate, protected input, catalog/audit, query, and packet paths/SHA-256 values;
- baseline/final dynamic tool, owner, capability, command, and unclassified counts;
- Wave A picture/audio objective evidence and remaining taste/rights limitations;
- Workbench backward-compatibility evidence;
- every LOCAL repair, deviation, skip, blind spot, and structural blocker;
- explicit `human_creative_approval=false`;
- explicit `final_delivery_claimed=false`.

Only when all objective acceptance is green may the worker stop at:

`WAITING_OWNER_CONSOLIDATED_FINAL_VERDICT`

Otherwise use an exact `STOPPED_<CHUNK>_<STRUCTURAL_REASON>` state and do not claim completion.
