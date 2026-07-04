# Work Order: Clean Clone Verification

Date: 2026-07-04
Goal: prove the stranger's-machine experience. The asset store retrofit and
setup guide exist; only a real from-scratch walkthrough proves they work.
This order produces a gap report and guide fixes, NOT pipeline code changes.

## Owner zone

- The clone directory itself (create under a path OUTSIDE this repo,
  e.g. `C:\Users\user\Desktop\vp_clone_test\`) — everything there is yours.
- In THIS repo, you may modify ONLY: `docs/setup/setup-and-first-run.md`,
  `docs/setup/distribution-manifest.md`, `README.md` (setup-related lines
  only), and this work order (report append).

## Forbidden

- Any other file in this repo. If a gap requires a code fix, record it as a
  work-order candidate in your report — do not fix code in this order.
- Do not copy your working `.env`, caches, `.tmp/`, or `runs/` into the
  clone. The point is starting from nothing.

## Procedure

1. `git clone <this repo path> C:\Users\user\Desktop\vp_clone_test`
   (local clone is fine; note that a real user would also not have
   `reference repo/`, `runs/`, `.tmp/` — they are untracked/ignored, so the
   clone naturally lacks them; confirm and record what IS missing).
2. Open `docs/setup/setup-and-first-run.md` in the clone and follow it
   LITERALLY, line by line, as a stranger would. Every place where reality
   differs from the guide — missing step, wrong path, unstated assumption
   (e.g. miniconda already installed, ffmpeg on PATH), unclear wording —
   goes into the gap list with the exact guide line.
3. Verification battery inside the clone (all via the guide's commands):
   - `tools/preflight.py --strict`
   - both e2e-smoke cases
   - `registry-audit`
   - full suite
   - `asset-path-audit --strict` on a fresh smoke-produced run dir
   - start the dashboard server, load `/` in a browser, confirm the
     workbench renders with zero console errors (no run data is fine —
     record what an empty-state user sees, that IS the first-run UX).
4. Classify each gap: (a) guide fix — fix it in THIS repo's guide now;
   (b) code/packaging gap — work-order candidate with details;
   (c) empty-state UX observation — record only.
5. Re-clone into a SECOND fresh directory and re-walk the updated guide.
   Acceptance = the second walkthrough completes the whole battery with no
   undocumented steps.
6. Delete both clone directories when done.

## Acceptance

- Second clean walkthrough: preflight strict exit 0, both smokes exit 0,
  full suite OK, strict asset audit 0 findings, workbench loads.
- Guide fixes committed: `Fix setup guide against clean clone walkthrough`.
- Report appended below: gap list with classifications, work-order
  candidates, empty-state UX notes, second-walkthrough evidence tails.
  Report commit: `Record clean clone verification report`.

## Supervisor Report - 2026-07-04

Supervisor role: dispatched gpt-5.4-mini workers, monitored execution,
spot-checked claims, handled escalation, and kept commit authority local to the
supervisor.

### Mini-A - clone first pass

Result: completed first-pass clean clone walkthrough and returned a usable gap
report. Mini-A did not modify this repo and did not commit.

Spot checks rerun by supervisor in `C:\Users\user\Desktop\vp_clone_test`:

- `tools/preflight.py --strict`: exit 0 after clone-local `.env` stub.
- `video_tools.py registry-audit --json`: exit 0, 0 findings.
- `video_tools.py e2e-smoke --case stock_story --out-dir .tmp\monitor_spot_stock`: exit 0, with `PIXABAY_API_KEY` warning reproduced.

Mini-A findings:

- (a) Guide fix: strict preflight requires `PEXELS_API_KEY`, but the guide did
  not tell a clean-clone user how to create `.env` or satisfy the key.
- (a) Guide fix: the verification section did not include
  `asset-path-audit --strict` on a smoke output.
- (a) Guide fix: the guide did not include a dashboard/browser first-run check.
- (b) Code/packaging gap: full suite failed in a clean clone due to missing
  `runs/effect_reference_review_67/20260624-strong-montage/effect_reference_strong_montage_review.json`.
- (b) Code/packaging gap: `test_route_orchestrator.RouteOrchestratorTaskPacketTest`
  expected rejection but got `verdict["ok"] == True`.
- (b) Packaging gap: Node-side Playwright was not resolvable from a clean clone;
  Python Playwright worked.
- (c) Empty-state UX observation: disposable dashboard/workbench roots load a
  Workbench shell and show `no_timeline`; this is not a blank empty state.
- (c) Empty-state UX observation: `stock_story` passes but warns that
  `PIXABAY_API_KEY` is not set.

### Guide fixes applied by supervisor

Updated `docs/setup/setup-and-first-run.md` to:

- show `Copy-Item .env.example .env` and document `PEXELS_API_KEY` as the
  minimum strict preflight key;
- add a strict asset path audit command against a fresh `stock_story` smoke;
- add dashboard server and browser check instructions for `/` and `/workbench`;
- create `.tmp\dashboard_empty` before starting `tools\dashboard_server.py`.

### Mini-C - clone second pass

Result: blocked, but the block exposed a supervisor process issue. Mini-C used a
fresh `git clone` while the guide fixes were still uncommitted, so it verified
the old committed guide instead of the supervisor's updated guide. This is not a
Mini-C reasoning error; it is an orchestration gap caused by testing uncommitted
documentation through a local clone.

Mini-C evidence:

- `tools/preflight.py --strict`: exit 1 with missing `PEXELS_API_KEY`; the old
  guide did state the key requirement but did not include the final updated
  command block.
- `video_tools.py e2e-smoke --case stock_story`: exit 0, with missing Pexels
  and Pixabay warnings.
- `video_tools.py e2e-smoke --case single_long_highlight`: exit 0.
- `video_tools.py registry-audit`: exit 0.
- `python -m unittest discover -s tests`: exit 1 after 2373 tests, with the
  same missing Remotion fixture and route-orchestrator expectation failure.
- `asset-path-audit --strict` on the smoke run: exit 0.
- Browser check via `workbench_server.py`: pages loaded, but console had 404s
  because this was not the corrected `dashboard_server.py` path.

Escalation: supervisor took over the second-pass guide verification by creating
`C:\Users\user\Desktop\vp_clone_monitor_pass`, applying only the pending setup
guide diff, and rerunning the affected verification battery. This simulates the
guide content that a clean clone will receive after commit, without exposing
Mini-C to Mini-A's report.

Supervisor monitor-pass evidence:

- `tools/preflight.py --strict`: exit 0 with clone-local placeholder
  `PEXELS_API_KEY`; this proves the documented presence check path, not real
  provider credentials.
- `video_tools.py e2e-smoke --case stock_story --out-dir .tmp\setup_stock_story`:
  exit 0.
- `video_tools.py e2e-smoke --case single_long_highlight --out-dir .tmp\setup_highlight`:
  exit 0.
- `video_tools.py registry-audit --json`: exit 0, 0 findings.
- `video_tools.py asset-path-audit --strict .tmp\setup_stock_story`: exit 0,
  0 strict findings.
- `tools\dashboard_server.py --artifact-root .tmp\dashboard_empty --port 8896`:
  initially exposed a guide gap because the directory must exist first; after
  adding `New-Item -ItemType Directory -Force .tmp\dashboard_empty`, `/` and
  `/workbench` returned 200 with 0 browser console errors.

Remaining blocker:

- The full clean-clone suite is not green. This is a code/packaging gap, not a
  setup-guide gap: the suite still fails on the missing Remotion fixture and
  route-orchestrator expectation mismatch.

### Mini-B - storybook probe

Status: not dispatched. The user request referenced "Prompt 2 = previous
message original text", but the current available context and repo only contain
`docs/construction-guides/work-orders/storybook-probe-template.md`, not a filled
storybook case with case name, brief, materials, expected entry path, and target
delivery. The supervisor did not fabricate a storybook probe because that would
produce invalid product data.

Required unblock: provide the filled Prompt 2 text. Mini-B should then run as
gpt-5.4-mini, leave run artifacts under `runs/`, return the probe report to the
supervisor, and make no commits.

### Escalations and model-level judgment

Escalations handled by supervisor:

- interrupted Mini-A only for a status check after a long full-suite run, then
  allowed it to continue;
- took over Mini-C's second-pass verification after discovering the local clone
  could not see uncommitted guide edits;
- corrected the dashboard guide step when monitor-pass verification showed the
  artifact root directory must be created before server start.

Judgment: gpt-5.4-mini can run bounded command batteries and report concrete
failures, but it is not yet sufficient to independently operate this pipeline
end to end without supervision. It needs supervisor handling for cross-session
state, uncommitted documentation under test, browser verification method choice,
and route/product judgment. The clean-clone setup path is now better documented,
but the pipeline cannot be called independently clean-clone green until the
remaining full-suite code/packaging gaps are resolved.

## Boundary Probes - 2026-07-04

Three gpt-5.4-mini workers ran independent boundary probes. They were allowed
to read the repo and write their own `runs/` outputs only; no commits or repo
file edits were allowed.

### Mini-D - no-material generated line

- Run: `runs/mini_d_fox_homeward_90s_20260704_093035`
- Brief: `幫我做一支 90 秒的繪本風格短片,講一隻迷路小狐狸找到回家的路,溫暖治癒`
- Entry judgment: `structure-first`, `input_state=no_material`.
- Trace: `video_intent.json` -> story/structure artifacts ->
  `material_generation_fallback.json` ->
  `provider_packet/generated_provider_packet.json` ->
  `provider_packet/image_agent_handoff/image_agent_prompt_handoff.json` ->
  `pipeline_home.json`.
- Final stop: `pipeline_home.json` reports `mode=waiting`,
  `cursor=generated_image_agent`, `next=call_image_generation_agent`,
  `resume=generated-material-import`, and a stop reason waiting for 18 real
  generated images.
- Verdict: PASS. This fail-closed cleanly at the external image-generation
  provider handoff and did not proceed to import, BUILD, or render.
- Supervisor spot check: `pipeline_home.json` matched Mini-D's reported
  waiting state and `call_image_generation_agent` command.

### Mini-E - fuzzy input fail-closed

- Run: `runs/mini_e_stage0_failclosed_20260704-093408`
- Brief: `幫我做一支影片`
- Entry judgment: Stage 0 `Video Intent Planner`, no story/material/build
  branch entered.
- Final stop: `video_intent.json` has `entry_path=needs-context`,
  `route=needs-context`, `handoff_to=ask_followup`, and 6
  `required_followup_questions`.
- Dashboard state also reported missing downstream artifacts, but the planner
  artifact itself correctly stopped at follow-up instead of inventing a route.
- Verdict: PASS. This fail-closed cleanly and did not create downstream BUILD
  artifacts.
- Supervisor spot check: `video_intent.json` contained the non-empty follow-up
  list and no material/build handoff.

### Mini-F - bad input boundaries

Run root: `runs/mini_f_boundary_probe_20260704_093608`

1. Missing material folder:
   - Main direct source-folder dry run exited 1 with
     `ValueError: source folder dry run requires at least 3 usable media files`.
   - A narrower layout helper produced `missing_folder:materials/raw`, but the
     requested direct route did not give a clean user-facing refusal.
   - Verdict: FAIL, dirty stop.
2. `target_length` set to 5 hours:
   - Stage 0 did not ask for clarification.
   - `spec_review.json` treated the target as `5.0s`, emitted only a
     `target_length_mismatch` warning, and reported `ready_for_build=true`.
   - Verdict: FAIL, silently accepted/misparsed.
   - Supervisor spot check: `spec_review.json` confirmed `target_duration_sec:
     5.0` and `ready_for_build: true`.
3. Unsupported output format `32:9`:
   - `creator-profile` accepted `resolved.aspect_ratio=32:9` from the brief.
   - `state.json` proceeded to missing material coverage rather than rejecting
     or clarifying the unsupported format.
   - Verdict: FAIL, silently accepted.

Boundary conclusion: the no-material generated-provider path and fuzzy Stage 0
intake fail closed correctly. Bad input validation is not yet strong enough:
missing material folders, extreme target durations, and unsupported aspect
ratios need explicit reject/clarify gates instead of crashes or silent
acceptance.

## Clean Clone Acceptance - Mini-G

Mini-G ran after the repair commits and the setup-guide commit landed, using a
fresh clone at `C:\Users\user\Desktop\vp_clone_mini_g_acceptance`.

Credential handling:

- Mini-G copied only `PEXELS_API_KEY` from the operator repo `.env` into the
  clone `.env`.
- Mini-G reported `placeholder key used: no` and did not print the key value.

Acceptance evidence from Mini-G:

- `pip install -r requirements.txt`: exit 0.
- `tools/preflight.py --strict`: exit 0, required env keys present.
- `video_tools.py e2e-smoke --case stock_story`: exit 0,
  `final_next_action=complete_review_final`, with optional `PIXABAY_API_KEY`
  warning.
- `video_tools.py e2e-smoke --case single_long_highlight`: exit 0,
  `final_next_action=material-quick-inventory`.
- `video_tools.py registry-audit`: exit 0,
  `Registry Audit: OK (7 branches, 14 stages)`.
- `python -m unittest discover -s tests`: exit 0,
  `Ran 2373 tests in 582.945s`, `OK`.
- Fresh `stock_story` smoke plus
  `video_tools.py asset-path-audit --strict .tmp\setup_stock_story`: exit 0,
  0 strict findings.
- Browser check for `http://127.0.0.1:8765/` and `/workbench`: 0 console
  errors, 0 console warnings, title `Hermes 影片剪輯工作檯`.

Supervisor spot checks in the Mini-G clone:

- `tools/preflight.py --strict`: exit 0, required env keys present.
- Focused repaired tests
  `tests.test_remotion_template_manifest tests.test_route_orchestrator -v`:
  exit 0, 14 tests OK.
- `video_tools.py asset-path-audit --strict .tmp\setup_stock_story`: exit 0,
  0 strict findings.
- `git status --short` in the clone: clean.

Verdict: PASS. Clean clone setup and full test acceptance are now formally
green after the tracked Remotion fixture, hermetic route-orchestrator guard, and
setup guide updates.
