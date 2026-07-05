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
  acceptance-contract, interface-audit, asset-path-audit --strict all exit 0.
- R2 and R3 mini re-probes pass as specified.
- Report appended below: per-piece red evidence quotes, commits, re-probe
  traces, and anything skipped with reasons.
  Report commit: `Record probe repair round report`

## Probe Repair Round Report - 2026-07-04

Supervisor: Codex. Miniconda Python was used for implementation and
acceptance commands. Mini agents were used only for post-fix re-probe
acceptance; commits were made only by the supervisor.

### Commits

- R0: `11448d50 Clarify probe report enforcement flags and provider labels`
- R1: `58352603 Parse hour and Chinese duration forms and block unparseable targets`
- R2a: `8a9c14a7 Build timeline clips from covered stock contract`
- R2b: `9297230f Fail closed on empty music structure`
- R2c: `0a9cc499 Guard concat assembly against streamless segments`
- R2 acceptance follow-up: `cc26ceb9 Use audio duration for sparse music timing`
- R3a: `8a2e5dec Validate media integrity at material intake`
- R3b: `72fdd83c Validate aspect ratio at stage0 intake`
- R3c: `65fb761d Refuse missing material folders with needs-context`
- R4a: `8dabf04a Verify final video streams at delivery gate`
- R4b: `c456c9bf Keep artifact manifest handoff refs resolvable`
- R4c: `d23ff1bb Unify dotenv loading across provider paths`
- R4d: `ff3f3b6a Document rerun authority order`

### Red Evidence And Fix Summary

- R0 red evidence: the supervisor report had an apparent duration
  contradiction because one run enforced target length and the other did
  not, and `runs/stress_provider_stock_20260704_master_report.json` mixed
  `live_provider_result=false` with real download artifacts. The reports now
  state the enforcement/provider-label correction explicitly.
- R1 red evidence:
  `runs/stress_duration_20260704_target_length_stress_v2/case3_5h/`
  parsed `5 hours` as `target_sec=5.0`, while
  `case4_zh_5h` and `case5_banana` silently warned with
  `ready_for_build=true`. Parser tests now cover hour forms, minute forms,
  Chinese duration forms, and unparseable values. Unparseable spec-review
  targets now block as `target_length_unparseable`; Stage 0 produces a
  required follow-up question.
- R2a red evidence:
  `runs/storybook-stock-story/runs/20260704-storybook-stock-story-probe/timeline_build.json`
  originally had `clips=[]` despite covered stock inputs. The repaired run
  now writes non-empty clips; supervisor spot-check showed `clips[0]` in the
  same artifact with `source_path: mvstock_1.mp4` and timeline coverage.
- R2b red evidence:
  `runs/storybook-stock-story/runs/20260704-storybook-stock-story-probe/music_structure.json`
  originally had `sections=[]`. Empty analysis no longer passes silently.
  Sparse real music now produces a duration-derived fallback section when
  duration evidence exists; otherwise it routes to repair instead of emitting
  an empty scaffold.
- R2c red evidence:
  `runs/storybook-stock-story/runs/20260704-storybook-stock-story-probe/mv_audio_wgm0gltx/mvseg_000.mp4`
  was audio-only, leading to final mux failure:
  `Stream map '0:v:0' matches no streams`. Assembly now validates segment
  streams before concat and names the offending segment in an actionable
  failure.
- R3a red evidence: Darwin's corrupt material case under
  `runs/stress_material_20260704_boundary_probe/` allowed bad media to flow
  toward material mapping/rough-cut planning. Media intake now ffprobe-checks
  candidates, passes valid assets, and records invalid ones as rejects.
- R3b red evidence: Mini-F aspect-ratio probes accepted unsupported or
  malformed ratios such as `32:9`. Stage 0 now allowlists `16:9`, `9:16`,
  and `1:1`, and asks for clarification on unsupported/malformed ratios.
- R3c red evidence: direct source-folder routes could raise a traceback for
  missing folders or too few usable files. They now return structured
  needs-context refusals.
- R4a red evidence: the render-free smoke wrote a placeholder `final.mp4`,
  and delivery evidence needed to reject byte placeholders. Delivery gate now
  probes final media streams and reports `final.mp4 is not a valid playable
  media file` when ffprobe fails. The simulated e2e-smoke remains green when
  run in a fresh out-dir.
- R4b red evidence: the storybook manifest could point at a missing
  `audio_build_handoff.json` and stall at
  `repair_artifact_manifest_or_regenerate_handoff`. Manifest writing now
  removes dangling handoff refs and records an explicit
  `artifact_waivers.audio_build_handoff` entry with next action
  `repair_audio_build_handoff`.
- R4c red evidence: Mini-B observed provider keys missing at runtime while
  preflight could see them. `.env` loading is now centralized through
  `video_pipeline_core.env_loader` and shared by preflight, provider search,
  soundtrack providers, and `video_tools.py`.
- R4d red evidence: Euler's stale-state finding showed that a stale
  `state.json` cursor could be misread as completion authority. The operating
  map now documents that `pipeline_home.py` re-derives route state from
  current intent and artifacts, and lists the authority order before trusting
  `state.json.next_action`.

### Mini Re-Probe Acceptance

- R2 fresh mini: Popper checked
  `runs/storybook-stock-story/runs/20260704-storybook-stock-story-probe/`.
  Reported `final.mp4` size `21437241` bytes, ffprobe streams `video` and
  `audio`, `verify_result.json` with `pass: true`, `score: 100`,
  `issues: []`, and `state.json.next_action: complete_review_final`.
  Supervisor spot-check reran ffprobe on the same `final.mp4` and confirmed
  both video and audio streams.
- R3 fresh mini: Carson reran four cases into
  `.tmp/r3_acceptance_probe/`: Mini-F missing material folder, target length
  `5h`, aspect ratio `32:9`, and Darwin corrupt mp4. The missing-folder case
  exited cleanly with `material_first_source_refusal.json`; the `5h` case
  produced `target_sec=18000.0`; the aspect-ratio case returned
  `entry_path=needs-context` with supported ratios; the corrupt mp4 case
  marked the bad asset `invalid_media` and did not produce
  `project_material_map.json` or `rough_cut_plan.json`. Carson reported zero
  tracebacks across all four cases.

### Final Acceptance Evidence

- `C:\Users\user\miniconda3\python.exe -m unittest discover`:
  `Ran 2393 tests in 654.009s`, `OK`.
- `C:\Users\user\miniconda3\python.exe video_tools.py e2e-smoke --case stock_story --out-dir .tmp\final_stock_story`:
  `ok: true`, final next action `complete_review_final`, no stalled action.
- `C:\Users\user\miniconda3\python.exe video_tools.py e2e-smoke --case single_long_highlight --out-dir .tmp\final_single_long_highlight`:
  `ok: true`, final next action `material-quick-inventory`, no stalled action.
- `C:\Users\user\miniconda3\python.exe video_tools.py registry-audit`:
  `Registry Audit: OK (7 branches, 14 stages)`.
- `C:\Users\user\miniconda3\python.exe video_tools.py asset-path-audit --strict .tmp\final_stock_story`:
  `0 absolute path finding(s); 0 strict finding(s)`.
- `C:\Users\user\miniconda3\python.exe video_tools.py interface-audit --out .tmp\review_interface_audit.json`:
  `ok: true`, `missing_commands: []`.

### Skipped / Deferred

- Stock semantic-fit honesty layer remains deferred exactly as ordered. It
  needs product-design decisions around hard-query relevance judgment and was
  not implemented in this round.
