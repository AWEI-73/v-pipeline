# Work Order: Probe Repair Round (post clean-clone / stress probes)

Date: 2026-07-04
Basis: audit-accepted findings from
`2026-07-04-clean-clone-verification.md` (Boundary Probes / Mini-G),
`2026-07-04-mini-stress-probes.md`, and
`2026-07-04-storybook-stock-story.md`. Every piece below has probe
artifacts as red-test source material — derive fixtures from them, do not
invent scenarios.

Implementer: supervisor (Codex) directly. Minis are used ONLY for
re-probe acceptance (fresh sessions, no repo edits, no commits).
Discipline: per `docs/agent-ops/work-order-sop.md`. Full suite green
(miniconda) before every commit. Red-first for every behavior change.

## R0 — Report hygiene (30 min, do first)

1. Append one line to the Mini-F duration entry (clean-clone report) and
   the Dirac section (stress report) stating whether that run's brief set
   `enforce_target_length` — resolves the apparent ready_for_build
   contradiction between the two probes.
2. Add a supervisor-correction note file next to
   `runs/stress_provider_stock_20260704_master_report.json` stating the
   labeling inconsistency (live_provider_result=false while downloads
   exist), so nobody reads the raw artifact as truth.
Commit: `Clarify probe report enforcement flags and provider labels`

## R1 — Duration intake integrity (P0-2)

Evidence: `runs/stress_duration_20260704_target_length_stress_v2/`
(case3_5h parsed "5 hours" as target_sec=5.0; case4_zh_5h and "banana"
silently warned with ready_for_build=true).

1. Fix the target-length parser (spec_review's `_parse_target_sec` and/or
   the Stage 0 intent layer — locate the single authority and fix there):
   - hour units: `5 hours`, `2h`, `1.5 hr` → seconds;
   - minute forms already working stay working (`10 minutes`, `30 minutes`);
   - Chinese forms: `5小時`, `五小時`, `3分鐘`, `90秒`;
   - unparseable strings (`banana`) → NOT a silent warning: at Stage 0 this
     becomes a required_followup_question; at spec review (no Stage 0
     context) it becomes a blocking finding `target_length_unparseable`.
2. Add `enforcement` field to the target_length finding payload so future
   probes can read whether enforce_target_length was active.
3. Red tests first, derived from the three probe cases + existing passing
   forms. Full matrix in `tests/test_spec_review.py` (or the parser's own
   test module).
Commit: `Parse hour and Chinese duration forms and block unparseable targets`

## R2 — Real stock chain repair (P0-1, the heavy piece)

Evidence: `runs/storybook-stock-story/runs/20260704-storybook-stock-story-probe/`
— `timeline_build.json` clips=[], `music_structure.json` sections=[],
`mv_audio_wgm0gltx/mvseg_000.mp4` audio-only first segment,
final mux `Stream map '0:v:0' matches no streams`.

Sub-pieces, in order (each red-first, each its own commit):

1. **R2a timeline schedule**: diagnose why the probe run's contract +
   coverage produced an empty clips schedule. Fixture-ize the minimal
   inputs from the probe run into `examples/` or `tests/fixtures/`;
   red test = those inputs must yield a non-empty, duration-covering
   clip schedule. Fix the builder.
   Commit: `Build timeline clips from covered stock contract`
2. **R2b music sections**: a 60s piece with music intent must not pass
   through with sections=[] silently — either produce sections from the
   music analysis or emit a blocking/repair finding that routes back to
   soundtrack. No silent empty scaffold.
   Commit: `Fail closed on empty music structure`
3. **R2c mux stream guard**: assembly must guarantee the concat list's
   stream layout (video-first or normalized) OR validate per-segment
   streams before concat and fail with an actionable message naming the
   offending segment. The probe's audio-only mvseg_000 case becomes the
   red test.
   Commit: `Guard concat assembly against streamless segments`
4. **R2 acceptance (mini re-probe)**: dispatch a FRESH mini with the
   original storybook Prompt 2 (same brief, cached local stock allowed —
   live provider not required for chain validation). Acceptance = the run
   reaches a real `final.mp4` whose ffprobe shows both video and audio
   streams, verify gate runs, and the mini's trace shows no manual
   state-machine surgery beyond the allowed review verdicts.

## R3 — Intake fail-closed bundle (P1)

Evidence: Mini-F boundary runs + Darwin's
`runs/stress_material_20260704_boundary_probe/`.

1. **R3a media integrity gate**: ffprobe validation before an asset can
   enter `project_material_map.json` / rough-cut planning. Corrupt file →
   rejected with reason recorded; mixed folder → good assets pass, bad
   ones listed in a rejects section. Red test: Darwin's corrupt-mp4 case.
   Commit: `Validate media integrity at material intake`
2. **R3b aspect ratio validation**: allowlist (16:9, 9:16, 1:1) at the
   creator-profile / video-intent layer. Unsupported or malformed values
   (`32:9`, `abc:def`, `cinemascope but vertical`) → required followup
   question, never silent acceptance. Extending the allowlist stays a
   one-line config change.
   Commit: `Validate aspect ratio at stage0 intake`
3. **R3c missing-folder clean refusal**: the direct source-folder route
   must turn "folder missing / <3 usable files" into a structured
   needs-context response, not a ValueError traceback.
   Commit: `Refuse missing material folders with needs-context`
4. **R3 acceptance (mini re-probe)**: fresh mini reruns the Mini-F
   three-case battery + Darwin's corrupt case; all four must now stop
   cleanly with explicit refusal/clarify, zero tracebacks.

## R4 — Honesty and observability (P2)

1. **R4a placeholder guard**: delivery-gate/verify layer checks
   `final.mp4` media streams via ffprobe; a placeholder byte file must
   fail delivery evidence with a clear finding. The e2e-smoke's simulated
   chain must remain green (it does not run the delivery gate; if it
   does anywhere, scope the check to delivery evidence only).
   Commit: `Verify final video streams at delivery gate`
2. **R4b audio handoff evidence**: the storybook stall at
   `repair_artifact_manifest_or_regenerate_handoff` (manifest pointing to
   missing `audio_build_handoff.json`) — make the manifest writer either
   produce the evidence or record an explicit waiver; no dangling refs.
   Commit: `Keep artifact manifest handoff refs resolvable`
3. **R4c dotenv loading consistency**: investigate why Mini-B's runtime
   reported missing provider keys while preflight saw them — find code
   paths reading env without loading `.env`, unify through one loader.
   Investigate first; fix if the fix is bounded, else report.
   Commit: `Unify dotenv loading across provider paths`
4. **R4d authority-order doc**: document in
   `docs/video-pipeline-operating-map.md` that pipeline_home re-derives
   from current intent/artifacts and stale `state.json` cursors do not
   force completion (Euler's finding). Doc-only.
   Commit: `Document rerun authority order`

Deferred (recorded, NOT this round): stock semantic-fit honesty layer
(hard-query relevance judgment) — needs product design, park it.

## Acceptance for the whole round

- Full suite green; both e2e-smoke cases green; registry-audit,
  interface-audit, asset-path-audit --strict all exit 0.
- R2 and R3 mini re-probes pass as specified.
- Report appended below: per-piece red evidence quotes, commits, re-probe
  traces, and anything skipped with reasons.
  Report commit: `Record probe repair round report`
