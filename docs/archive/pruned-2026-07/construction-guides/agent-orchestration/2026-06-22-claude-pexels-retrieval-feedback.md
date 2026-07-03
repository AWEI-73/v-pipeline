# 2026-06-22 Claude Pexels-Retrieval Run Feedback

## Classification

- Source: Claude (Opus) orchestrated subagent run, retrieval-based.
- Scope: external agent orchestration, run lifecycle, verify-gate sufficiency, stock_first route truth.
- Status: construction feedback; intended as the **comparison counterpart** to
  `2026-06-22-gemini-antigravity-runner-feedback.md` (which covered a *generation*-based run).
- Related run folder: `C:\Users\user\Desktop\video_project\city-dawn-doc\runs\20260622-094200-run-auto`
- Brief: `narration_video` / `stock_first` / `warm_documentary` / target 180s / zh-TW, realistic Pexels footage, copy-driven.

This note records a real end-to-end run driven by short-lived subagents (operator role)
plus a parent orchestrator (decision + gate role), producing a delivered `final.mp4`.
It is written to answer the **Pending Comparison** questions raised in the Gemini note.

## Observed Run Result

The pipeline reached delivered output and a clean terminal state:

- `final.mp4` exists — 1920×1080 @ 30fps, H.264+AAC, 135.87s.
- `qa_report.json` reports `pass: true`, score `100.0`; all five technical dims = 100
  (script_coverage / duration_fit / subtitle_accuracy / audio_levels / technical_quality).
- `editor_review.json` reports `status: pass` — 17/17 clip checks pass, **zero findings**,
  including `duplicate_footage` passing on every segment.
- `artifact_manifest.json` present (41 entries).
- After canonical-chain backfill, `state.json` `next_action = complete_review_final`.

Unlike the Gemini run, there was **no split material-truth** and **no `await_material` loop**:
`runtime status` reported `material_coverage_map.json` as *optional (stock_first mode)*. The
stock_first route does not go through the material-map lifecycle that produced Gemini's
`material_delta` vs `material_coverage_map` contradiction. **That class of bug is route-specific
to the generated/material-map path, not universal.**

## Answers to the Gemini "Pending Comparison" Questions

1. **Does Pexels retrieval avoid duplicate assets better than generated material?**
   **Yes, decisively.** 17 segments → 17 distinct downloaded clips, all distinct files;
   `editor_review.duplicate_footage` passed on all 17. The generation run's failure mode
   (60 items, large exact-hash duplicate groups, one shared prompt prefix) **did not appear**.
   Retrieval returns provider-distinct results by construction; the duplication problem is
   largely a *generation-prompt-diversity* problem, not a pipeline-wide one.
   Caveat: the duplicate check is footage/hash-based; near-duplicate / semantic-overlap across
   segments was not deeply tested here.

2. **Does it still suffer stale `material_coverage_map.json` vs `material_delta.json` conflict?**
   **No — sidestepped.** stock_first treats the coverage map as optional, so the lifecycle
   that caused the conflict was never exercised. The precedence fix (Gemini rec #3) remains
   correct for the material-map route, but stock_first runs won't surface it.

3. **Does a monolithic subagent also exhaust context on retrieval-based runs?**
   **Yes — and with a new, worse wrinkle.** The Round-3 subagent ran revise+build in one
   context, **backgrounded `runtime.py run`**, hit its turn/token budget, and ended — which
   **orphaned the background render**; it then stalled at seg9 with no progress for 5+ minutes.
   Gemini saw "background rerun unexpectedly completed while the main subagent was stuck"; here
   the background process *died/stalled* with the subagent. Same root cause, confirmed on the
   retrieval path: **execution lifetime must not be bound to a subagent's context budget.**
   Recovery worked only because the run was resumable (see below).

4. **Are retrieved clips accepted with enough semantic evidence, or does "quantity counted as
   coverage" reappear?**
   **Milder, but still present.** Retrieval *does* add a per-segment VLM judge (qwen3-vl:4b) at
   selection time — better than the generation run, which accepted all 60. But the VLM verdict
   is **discarded before final verify**: the closing hero (seg9 in the first 9-seg cut) had all
   candidates judged `VLM=no`, yet the engine picked the "best" and continued, and final QA
   (5 technical dims, no `content_alignment`) scored 100. So "technically clean but off-topic"
   can still pass. The semantic gate exists earlier but is **not load-bearing at verify**.

## New Findings From This Run (not in the Gemini note)

### F1. The brief's `target_length` is never enforced (correctness gap)
`target_length="3 minutes"` passed spec-review green against a 9-segment contract that TTS'd to
**47.93s**. `duration_fit` scored 100 because it measures *relative* alignment to the TTS track,
not fit to the brief target. The user's most explicit number had **zero enforcement** anywhere in
SPEC→VERIFY. A 180s target produced a 48s deliverable that scored perfect.
→ spec-review should warn when estimated narration duration deviates from `target_length`
  beyond a threshold (here ~3.7x), **before** BUILD.

### F2. `subtitle_accuracy=100` while the on-screen subtitle is truncated (correctness gap)
The final line rendered as `替你先把這座…` (visually clipped). `subtitle_accuracy` compares text to
script, not legibility on screen. Text-match ≠ readable-on-screen.
→ add a render-side subtitle overflow/safe-area/line-count check (warn is enough).

### F3. Render path and canonical BUILD-chain are two disjoint paths (state-machine gap)
`runtime.py run` produced `final.mp4` + passing verify via the legacy assemble/merge path, but
**never emitted Node 8–11** (`build_profile`/`assembly_plan`/`timeline_build`/`editor_review`).
So a PASS render sat at `next_action = missing_artifact:build_profile.json` and could not reach a
terminal state. Reaching `complete_review_final` required manually running
`video_tools.py contract-dry-build --out-dir <run>` to backfill the canonical chain + manifest.
→ either `run` emits the canonical chain itself, or the done-definition must not require artifacts
  the render path never produces. As-is, an autonomous loop can never self-terminate on this route.

### F4. Progress is invisible to stdout (observability gap)
`runtime.py run/resume` writes progress to stderr/state, not stdout, so the captured run log was
**empty** throughout. Both the subagent and the orchestrator had to infer progress from run-dir
file mtimes and ken-burns temp files, and stall-detection had to be mtime-based.
→ emit one stdout heartbeat per node/segment (e.g. `[seg 9/17] material fetched`). This alone makes
  monitoring and stall-vs-progress detection reliable.

### F5. `subtitle:"auto"` is a structural landmine for narration/stock_first (DX gap)
First spec-review blocked all 9 segments via rule B3 (`subtitle_auto_no_speech`): TTS narration
+ silent stock footage → ASR on a silent track scores 0. The operator had to rewrite every subtitle
to explicit narration text. This is *structurally inevitable* whenever the visual track is silent
stock.
→ the contract generator should default subtitle to the narration text (not `auto`) when
  `mode=narration` / `stock_first`. Saves a guaranteed gate round-trip.

## What Worked Well (corroborating the architecture)

- **File-state resumability is the hero.** After the orphaned-render stall, `runtime.py resume`
  reused the active run (`runtime_orchestrator.py:479` — reuse-if-active), preserving seg1–9
  downloads and the **VLM pick selection (~9 min, the most expensive stage)**. Recovery cost was
  near-zero. This is the single strongest property of the design.
- **Stateless operators + state.json as the contract.** Each operator subagent cold-started and
  picked up purely from on-disk state (no `SendMessage` continuity was available, and none was
  needed). This validates the Gemini-recommended dispatch shape from the retrieval side.
- **Gate discipline held.** Operators stopped and reported at gates, never modified pipeline code,
  and only edited contract/artifacts (B3 fix, seg9 weak report). The "tools immutable, artifacts
  mutable" boundary was clean.

## Recommended Adjustments (retrieval-path additions to the Gemini list)

These supplement, not replace, the Gemini recommendations.

### R1. Separate "decision/gate" agents from "long execution" (extends Gemini rec #1)
Confirmed: the failure was not only token pressure (Gemini's 429) but **process orphaning** when a
long render is backgrounded inside a subagent. Make render/execution run under a lifetime that
outlives any single agent turn (parent-managed background, or a dedicated runner), while operator
agents stay short and only: read status → dispatch one node/phase → report → terminate.
Acceptance: no render process is a child of an agent that can hit a budget mid-render.

### R2. Make the brief target a real gate (new)
`target_length` (and `must_include`) should produce spec-review warnings/blocks on large deviation,
not be silently absorbed by relative-fit metrics. Acceptance: a 180s brief cannot ship a 48s cut at
score 100 without an explicit waiver.

### R3. Carry the VLM verdict into verify as `content_alignment` (extends Gemini rec #4)
The retrieval path already has per-segment semantic judgment; wire that verdict into `qa_report`
as a dimension (warn-level is fine). Acceptance: a segment whose chosen clip is `VLM=no` cannot
contribute to a 100 score without surfacing.

### R4. Unify the render and canonical-artifact paths (new; see F3)
Acceptance: a successful `runtime.py run` reaches `complete_review_final` on its own, with no
manual `contract-dry-build` backfill.

### R5. Subtitle render-quality check + mode-aware subtitle default (new; F2 + F5)

## Proposed Priority (retrieval-run view)

1. Separate long-execution from subagent lifetime (R1) — this was the only hard failure.
2. Unify render vs canonical-artifact path so the state machine can self-terminate (R4 / F3).
3. Enforce brief target_length at spec-review (R2 / F1).
4. Wire VLM verdict into verify as content_alignment (R3).
5. stdout progress heartbeat (F4) + subtitle render check & mode-aware default (R5 / F2 / F5).

## Cross-reference

- Generation-path counterpart + Codex assessment: `2026-06-22-gemini-antigravity-runner-feedback.md`.
- Net of the two runs: **duplication and material-truth split are generation/material-map-specific;
  monolithic-subagent fragility and "semantics not gated at verify" are common to both paths.**
- Full interaction transcript for this run: `city-dawn-doc/interaction_log.md`;
  delivery review: `city-dawn-doc/REVIEW_REPORT.md`.
