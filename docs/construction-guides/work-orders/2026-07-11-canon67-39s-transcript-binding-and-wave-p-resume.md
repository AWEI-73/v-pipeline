# Work Order — Canon 67 39s Transcript Binding and Wave P Resume

Date: 2026-07-11
Status: ready for execution
Execution shape: one bounded long-running worker; sequential shared-state tasks

## Goal and construction basis

Repair the verified production seams that stopped Wave P, prove them with RED→GREEN tests, and regenerate the real 0.00–39.34s transcript-review packet. The only design basis is:

1. `docs/superpowers/specs/2026-07-11-canon67-39s-l0-l5-integrated-loop-design.md`
2. `docs/superpowers/plans/2026-07-11-canon67-39s-transcript-binding-implementation-plan.md`
3. This work order

Verified baseline defects:

- real probe nested cues: 20; current adapter output: 0;
- current approved review artifact has no approved text/source binding;
- current subtitle QA returns `pass: true` when actual subtitle text is `WRONG`.

## Owner zone

- `video_pipeline_core/agent_transcript_repair.py`
- `video_pipeline_core/human_transcript_review_decision.py`
- `video_pipeline_core/source_speech_subtitle_qa.py`
- `tools/agent_transcript_repair.py`
- `tools/write_human_transcript_review_decision.py`
- `tools/source_speech_subtitle_qa.py`
- `tests/test_source_speech_transcript_repair.py`
- `tests/test_write_human_transcript_review_decision.py`
- `tests/test_source_speech_subtitle_qa.py`
- `.tmp/editing_loop_39s_integrated_campaign/**`
- one new child folder under the already-authorized Drive workspace, containing only the Wave P review packet
- worker report at `docs/construction-guides/work-orders/2026-07-11-canon67-39s-transcript-binding-and-wave-p-resume-report.md`

## Read-only / forbidden zone

- `.tmp/editing_loop_certification_campaign/**` except read-only input/evidence
- `AGENTS.md`, `HANDOFF_CURRENT.md`, `RUNBOOK.md`, `docs/INDEX.md`
- `skills/**`, Product Spec, registries, dictionaries, route runners, renderer code, effect/audio code, Material Map code
- raw source media and reference-film/music folders
- existing candidates, closures, durable evidence, approval flags
- no push, reset, cleanup, mass formatting, dependency install, or full suite

## Ordered execution

### Phase H1 — nested cue adapter

Execute Plan Task 1. Capture a real failing assertion before production code. Preserve legacy top-level cue behavior and add opt-in zero-cue failure.

Acceptance: targeted tests exit 0 after the recorded RED; true-shape copied probe produces more than zero suggestions.

### Phase H2 — bound review decision v2

Execute Plan Task 2. The existing writer remains the sole production path. Partial v2 input, non-human approval, bad source hash, bad reviewed-draft hash, duplicate/missing cue data, or out-of-window timing must fail closed.

Acceptance: targeted tests exit 0 after the recorded RED; v1 compatibility test remains green.

### Phase H3 — actual-subtitle equality

Execute Plan Task 3. Reuse `caption_audit.parse_srt`. A copied evidence cue list cannot substitute for the actual run-local SRT. Only whitespace/line wrapping may normalize. Add an opt-in required-binding mode so legacy callers remain compatible while the 39-second route cannot silently fall back to v1.

Acceptance: targeted tests exit 0 after the recorded RED; missing/legacy decision and wrong text/hash/time each produce a blocking rule and non-zero exit under `--require-approved-text-binding --strict-exit`.

### Phase H4 — combined capability closure

Run the combined affected suite and `git diff --check`. Make scoped commits only after green, staging only owner-zone production/test files. Do not include existing dirty files or campaign artifacts.

If a focused test reveals an adjacent production owner outside this work order, record it and stop that piece; do not expand the owner zone.

### Phase P — true 39-second owner packet

Use the exact source:

- path: `C:/Users/user/Downloads/微電影素材/_整理後/主任勉勵/IMG_2145.MOV`
- SHA-256: `85BAEAFCE7D3D7FBEB56C1A354B9EDAF2EE500AB4285BF56893B906C49F9CFCB`
- window: `0.00–39.34s`

Use only public tools: ffmpeg extraction, `tools/soundtrack_probe.py --enable-asr --asr-model small --language zh`, then `tools/agent_transcript_repair.py --require-cues`. Generate and upload the review packet specified in Plan Task 5.

Stop at `WAITING_OWNER_39S_TRANSCRIPT_VERDICT`. Owner silence is not approval. Wave R and candidate rendering remain forbidden.

## Stop-loss

- One LOCAL correction is allowed per failure class and must be recorded.
- The same failure class recurring, an interface bypass, a needed edit outside owner zone, or inability to state a component's role is STRUCTURAL: stop at the last green state.
- Do not weaken tests, hand-write a private conversion script, manually author an approval artifact, or use a run-local SRT/table to impersonate the production chain.
- Drive upload failure does not invalidate local packet PASS; report it separately and do not retry blindly.

## Acceptance commands

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_write_human_transcript_review_decision tests.test_source_speech_subtitle_qa tests.test_caption_audit -v
git diff --check
```

Both commands must exit 0. Full suite is explicitly deferred until the final 39-second L0–L5 closure after the owner transcript gate.

## Required report

Report commits, exact RED/GREEN commands and exits, combined test tail, diff scope, pre/post git status, true-shape cue count, negative equality evidence, all campaign/Drive artifact paths and hashes, LOCAL/STRUCTURAL deviations, skipped work, blind spots, and final wait state. Keep:

- `human_creative_approval=false`
- `final_delivery_claimed=false`
