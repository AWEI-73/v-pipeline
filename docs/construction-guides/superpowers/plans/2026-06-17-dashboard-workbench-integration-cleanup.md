# Dashboard / Workbench Integration Cleanup Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Consolidate the current dashboard + native workbench into a stable two-surface frontend, align its patch/handoff artifacts with the backend pipeline, and reduce technical debt without adding new editing features.

**Architecture:** Keep the system as two explicit surfaces: Dashboard for project/node/status review, Workbench for interactive timeline/material/subtitle/audio/effect patching. Do not build a full browser NLE and do not make the frontend the canonical renderer. All edits remain draft patches that the backend/agent can inspect, validate, and convert into pipeline decisions.

**Tech Stack:** Python stdlib HTTP servers and CLI tools, vanilla HTML/CSS/JS frontend, ffmpeg-backed preview/export helpers, existing `video_pipeline_core` and `tools/*` contracts, `unittest` + Node smoke tests.

---

## Current Baseline

### Known Frontend Surfaces

- `dashboard/dashboard_v1.html`
- `dashboard/dashboard_v1.css`
- `dashboard/dashboard_v1.js`
- `dashboard/workbench_native/index.html`
- `dashboard/workbench_native/workbench.css`
- `dashboard/workbench_native/workbench.js`
- `dashboard/workbench_native/workbench_core.js`

### Known Workbench Backend Tools

- `tools/workbench_server.py`
- `tools/preview_timeline.py`
- `tools/timeline_patch.py`
- `tools/workbench_patch_to_contract.py`
- `tools/workbench_export.py`
- `tools/workbench_handoff.py`
- `tools/workbench_proxy.py`
- `tools/workbench_thumbs.py`
- subtitle/audio/effect patch helpers already referenced by `workbench_server.py`

### Known Contracts

- `preview_timeline.json`: built snapshot for frontend preview. It is not authored by humans.
- `timeline_patch.json`: ordered draft edits from Workbench.
- `patched_draft_timeline.json`: preview timeline with patch applied.
- `workbench_contract_patch.json`: draft contract-level interpretation of timeline edits.
- `workbench_handoff.json`: package for agent/backend review.
- Canonical output artifacts (`final.mp4`, canonical `timeline.json`, material maps, contract files) must not be overwritten by Workbench.

### Current Untracked / Hygiene Risk

Do not stage or depend on these unless a separate cleanup task explicitly classifies them:

- `.claude/`
- `alternative_tech_demos.html`
- `dashboard/workbench_native/canvas_demo.html`
- `taipower_3d_intro_demo.html`
- `taipower_logo.svg`

---

## Non-Goals

- Do not build Remotion into this project.
- Do not turn Workbench into the canonical renderer.
- Do not add heavy realtime effects.
- Do not implement full drag-to-reorder or multi-track nonlinear editing unless explicitly scoped later.
- Do not change M6 material-map gates, delivery gates, or canonical BUILD semantics.
- Do not make UI edits silently rewrite source specs/contracts.
- Do not reorganize the entire repository in one pass.

---

## File Structure Target

### Documentation

- Create or update: `docs/archive/decisions/2026-06-17-dashboard-workbench-integration-cleanup.md`
  - Durable rationale: why Dashboard and Workbench are separate but connected.
- Create or update: `dashboard/README.md`
  - Operator entrypoints and artifact contract.
- Create or update: `docs/workbench-dashboard-integration.md`
  - End-to-end flow: SPEC -> material map -> BUILD -> Workbench patch -> agent review -> backend render.
- Update: `roadmap.md`
  - Add a short current-state pointer near the top, not another long historical section.

### Frontend

- Modify: `dashboard/workbench_native/index.html`
  - Ensure page structure is stable and has clear regions: nav, materials, monitor, inspector, timeline.
- Modify: `dashboard/workbench_native/workbench.css`
  - Layout cleanup only. Keep class names stable where possible.
- Modify: `dashboard/workbench_native/workbench.js`
  - Split only if necessary. Prefer extracting focused helper functions before creating many files.
- Modify: `dashboard/workbench_native/workbench_core.js`
  - Pure data transforms only. No DOM. No fetch. No side effects.
- Modify: `dashboard/dashboard_v1.*`
  - Only add navigation / handoff links if required. Avoid redesigning the node dashboard in this cleanup.

### Backend / Tools

- Modify: `tools/workbench_server.py`
  - Confirm endpoint naming and write boundaries.
- Modify: `tools/preview_timeline.py`
  - Only if frontend needs existing metadata surfaced.
- Modify: `tools/timeline_patch.py`
  - Only if patch validation is incomplete.
- Modify: `tools/workbench_handoff.py`
  - Ensure agent-facing handoff captures all draft artifacts.

### Tests

- Modify or add: `tests/workbench_core_smoke.js`
- Modify or add: `tests/test_workbench_server.py`
- Modify or add: `tests/test_preview_timeline.py`
- Modify or add: `tests/test_timeline_patch.py`
- Optional: add `tests/test_workbench_handoff.py` if current coverage is thin.

---

## Global Implementation Rules

- Every chunk must be TDD-first unless it is documentation-only.
- Every chunk must end with focused tests and one bounded commit.
- Every commit message must describe the bounded change, not the whole project.
- Keep existing behavior by default.
- Workbench writes only draft artifacts.
- Dashboard reads status and links to artifacts; it does not author timeline patches.
- If a browser check finds a visual issue, fix it in the same chunk before claiming done.
- If full regression fails on an unrelated pre-existing issue, capture evidence and stop for review.

---

## Chunk 0: Preflight And Baseline Lock

**Purpose:** Prove current repo state and avoid mixing unrelated untracked files into the cleanup.

**Files:**

- Read only initially:
  - `dashboard/workbench_native/workbench.js`
  - `dashboard/workbench_native/workbench_core.js`
  - `tools/workbench_server.py`
  - `docs/archive/decisions/2026-06-16-native-preview-engine.md`

### Task 0.1: Capture baseline git state

- [ ] Run:

```powershell
git status --short
git log --oneline -10
```

- [ ] Expected:
  - Worktree may contain known untracked demo files.
  - No unexpected modified tracked files.

- [ ] If unexpected modified tracked files exist:
  - Stop.
  - Report file list.
  - Do not overwrite user/agent changes.

### Task 0.2: Capture baseline tests

- [ ] Run focused checks:

```powershell
node --check dashboard\workbench_native\workbench.js
node --check dashboard\workbench_native\workbench_core.js
node tests\workbench_core_smoke.js
python -m unittest tests.test_preview_timeline tests.test_workbench_server tests.test_timeline_patch -q
```

- [ ] Expected:
  - Node smoke passes.
  - Focused Python tests pass.

### Task 0.3: Browser baseline

- [ ] Start or restart Workbench:

```powershell
$listeners = Get-NetTCPConnection -LocalPort 8770 -ErrorAction SilentlyContinue | Where-Object { $_.State -eq 'Listen' } | Select-Object -ExpandProperty OwningProcess -Unique
foreach ($ownerPid in $listeners) { Stop-Process -Id $ownerPid -Force }
Start-Process -FilePath 'C:\Users\user\miniconda3\python.exe' -ArgumentList @('C:\Users\user\Desktop\video_pipeline\tools\workbench_server.py','--artifact-root','C:\Users\user\Desktop\video_pipeline\.tmp\srp_real67_fuller_replay','--port','8770') -WorkingDirectory 'C:\Users\user\Desktop\video_pipeline' -WindowStyle Hidden
```

- [ ] Open:

```text
http://localhost:8770/workbench
```

- [ ] Manual baseline checklist:
  - Page loads.
  - Preview plays.
  - Timeline scrolls horizontally.
  - Timeline vertical area can be reached.
  - Material list shows assets.
  - Selecting a clip fills inspector.
  - Trim clamp still works.
  - Double-click material replacement still works.

### Task 0.4: Commit policy

- [ ] No commit for Chunk 0 unless a documentation-only preflight note is created.

---

## Chunk 1: Decision Log And Integration Contract

**Purpose:** Fix the project convention before changing code.

**Files:**

- Create: `docs/archive/decisions/2026-06-17-dashboard-workbench-integration-cleanup.md`
- Create or modify: `docs/workbench-dashboard-integration.md`
- Create or modify: `dashboard/README.md`
- Modify: `docs/INDEX.md`
- Modify: `roadmap.md`

### Task 1.1: Write decision log

- [ ] Create decision log with this shape:

```markdown
# Decision: Dashboard and Workbench Integration Cleanup

Date: 2026-06-17
Status: accepted
Scope: dashboard/workbench/frontend-backend handoff
Superpowers phase: plan

## SPEC

Requirement:
Dashboard and Workbench must be two connected surfaces, not one ambiguous UI.

Why:
The backend pipeline is now large enough that frontend edits must be traceable as draft patches, while dashboard review must remain reliable.

Direction:
Dashboard reads pipeline/node/run state. Workbench previews material composition and writes draft patches/handoff artifacts. Agent/backend consumes those artifacts and decides whether to rerender or revise contracts.

Non-goals:
No full browser NLE, no Remotion dependency, no direct canonical overwrite, no new material-map gate.

## DO
...

## VERIFY
...
```

- [ ] Keep it operational. Do not turn it into a giant spec.

### Task 1.2: Write integration doc

- [ ] Create `docs/workbench-dashboard-integration.md`.
- [ ] Include this exact flow:

```text
SPEC / contract
-> material map / needs / delta gates
-> BUILD timeline / final render
-> Dashboard review
-> Workbench draft edits
-> timeline_patch.json + patched_draft_timeline.json + workbench_contract_patch.json + workbench_handoff.json
-> Agent review
-> backend rerender / contract revision / reject patch
```

- [ ] Include hard rule:

```text
Workbench can preview and draft. Backend remains responsible for official render.
```

### Task 1.3: Write Dashboard README

- [ ] Create or update `dashboard/README.md`.
- [ ] Sections:
  - `Surfaces`
  - `Dashboard`
  - `Workbench`
  - `Artifact Ownership`
  - `Local Run Commands`
  - `Safety Rules`
  - `Known Deferred Work`

### Task 1.4: Add docs index entry

- [ ] Modify `docs/INDEX.md`.
- [ ] Add links:
  - `docs/workbench-dashboard-integration.md`
  - `docs/archive/decisions/2026-06-17-dashboard-workbench-integration-cleanup.md`

### Task 1.5: Roadmap current-state pointer

- [ ] Add a short section near the top of `roadmap.md`:

```markdown
## Current Frontend Integration State (2026-06-17)

- Dashboard = node/status/review surface.
- Workbench = interactive preview/patch/handoff surface.
- Workbench writes draft artifacts only.
- Official render remains ffmpeg/backend.
- Current cleanup focus: integration contract, layout stability, artifact handoff, and technical-debt reduction.
```

### Task 1.6: Verify documentation

- [ ] Run:

```powershell
git diff --check
```

- [ ] Expected: no whitespace errors.

### Task 1.7: Commit

- [ ] Run:

```powershell
git add docs/archive/decisions/2026-06-17-dashboard-workbench-integration-cleanup.md docs/workbench-dashboard-integration.md dashboard/README.md docs/INDEX.md roadmap.md
git commit -m "docs(workbench): define dashboard integration contract"
```

---

## Chunk 2: Workbench Layout Stabilization

**Purpose:** Make the current UI stable and usable without adding new editing features.

**Files:**

- Modify: `dashboard/workbench_native/index.html`
- Modify: `dashboard/workbench_native/workbench.css`
- Modify: `dashboard/workbench_native/workbench.js` only if DOM hooks need names.
- Test: `tests/workbench_core_smoke.js` if pure behavior changes.

### Task 2.1: Write visual/layout acceptance checklist before code

- [ ] Add checklist to `dashboard/README.md` or `docs/workbench-dashboard-integration.md`:

```markdown
Workbench layout acceptance:
- Left material panel scrolls independently.
- Center preview remains centered for portrait/landscape media.
- Inspector stays usable.
- Timeline area has both horizontal and vertical access when tracks overflow.
- No default browser selection border appears around the preview media.
- Play controls remain visible.
- Text/audio/effect lanes are visible as lanes even when empty.
```

### Task 2.2: CSS-only layout cleanup

- [ ] Inspect current region class names.
- [ ] Prefer CSS fixes over JS.
- [ ] Ensure:
  - App root uses viewport height.
  - Workbench body does not trap scroll incorrectly.
  - Timeline has explicit `overflow-x: auto`.
  - Track stack has explicit min width based on timeline duration, or an existing computed width.
  - Preview media uses centering rules for portrait clips.
  - The default focus/selection outline is removed only where replaced by a visible custom selected state.

### Task 2.3: Browser check

- [ ] Restart server.
- [ ] Open `http://localhost:8770/workbench`.
- [ ] Manual checks:
  - Scroll material list.
  - Scroll timeline horizontally past visible bars.
  - Select clip.
  - Play through a portrait clip.
  - Confirm portrait clip is centered.
  - Confirm no unwanted default border.

### Task 2.4: Focused verification

- [ ] Run:

```powershell
node --check dashboard\workbench_native\workbench.js
node --check dashboard\workbench_native\workbench_core.js
node tests\workbench_core_smoke.js
python -m unittest tests.test_workbench_server -q
```

### Task 2.5: Commit

- [ ] Run:

```powershell
git add dashboard/workbench_native/index.html dashboard/workbench_native/workbench.css dashboard/workbench_native/workbench.js dashboard/README.md docs/workbench-dashboard-integration.md
git commit -m "fix(workbench): stabilize preview and timeline layout"
```

---

## Chunk 3: Artifact Ownership And Handoff Hardening

**Purpose:** Make it unambiguous what the frontend writes and what the backend consumes.

**Files:**

- Modify: `tools/workbench_server.py`
- Modify: `tools/workbench_handoff.py`
- Modify: `tools/timeline_patch.py`
- Modify: `tools/workbench_patch_to_contract.py`
- Test: `tests/test_workbench_server.py`
- Test: `tests/test_timeline_patch.py`
- Optional new test: `tests/test_workbench_handoff.py`

### Task 3.1: Write failing server ownership tests

- [ ] Add tests for:
  - Server refuses to write canonical `timeline.json`.
  - Server refuses to write canonical `final.mp4`.
  - Server writes only whitelisted draft artifacts.
  - `save-all` writes a complete handoff or fails without partial canonical writes.
  - malformed patch returns structured error, not a traceback.

Expected first run:

```powershell
python -m unittest tests.test_workbench_server -q
```

Expected: fail only where the current contract is missing.

### Task 3.2: Implement minimal ownership fixes

- [ ] Keep whitelist centralized.
- [ ] Do not add broad write permissions.
- [ ] Return structured JSON:

```json
{
  "ok": false,
  "stage": "workbench_patch",
  "reason": "...",
  "next_action": "revise:workbench_patch"
}
```

### Task 3.3: Handoff completeness

- [ ] Ensure handoff includes:
  - source `preview_timeline.json` path/hash if available;
  - `timeline_patch.json` path/hash;
  - `patched_draft_timeline.json` path/hash;
  - `workbench_contract_patch.json` path/hash if produced;
  - subtitle/audio/effect patch paths/hashes if present;
  - known diagnostics.

- [ ] Do not embed large binary/video payloads.

### Task 3.4: Verify

- [ ] Run:

```powershell
python -m unittest tests.test_workbench_server tests.test_timeline_patch -q
git diff --check
```

### Task 3.5: Commit

- [ ] Run:

```powershell
git add tools/workbench_server.py tools/workbench_handoff.py tools/timeline_patch.py tools/workbench_patch_to_contract.py tests/test_workbench_server.py tests/test_timeline_patch.py
git commit -m "fix(workbench): harden draft artifact ownership"
```

---

## Chunk 4: Dashboard Entry Point Integration

**Purpose:** Let the operator move from Dashboard review to Workbench edit without confusing the two surfaces.

**Files:**

- Modify: `dashboard/dashboard_v1.html`
- Modify: `dashboard/dashboard_v1.css`
- Modify: `dashboard/dashboard_v1.js`
- Modify: `tools/dashboard_server.py` only if route/link generation exists there.
- Test: existing dashboard tests if present.

### Task 4.1: Find current dashboard server and tests

- [ ] Run:

```powershell
rg -n "dashboard_v1|dashboard_server|dashboard" tools video_pipeline_core tests -g "*.py"
```

- [ ] Identify the smallest test surface.

### Task 4.2: Add Dashboard-to-Workbench link

- [ ] Add a clear link/button:

```text
Open Workbench
```

- [ ] The link should point to the current workbench URL when served by the local server.
- [ ] If URL cannot be inferred, show a documented command instead of a broken link.

### Task 4.3: Show handoff artifact status

- [ ] Dashboard should display:
  - whether `workbench_handoff.json` exists;
  - whether `timeline_patch.json` exists;
  - whether `workbench_contract_patch.json` exists;
  - whether canonical final is still unchanged.

- [ ] This can be read-only.
- [ ] Do not add editing controls to Dashboard.

### Task 4.4: Verify

- [ ] Run focused dashboard tests, or if no tests exist:

```powershell
python -m unittest discover -s tests -q
```

- [ ] Manual browser check:
  - Dashboard loads.
  - Workbench link is visible.
  - Handoff status is readable.
  - No accidental editing UI appears in Dashboard.

### Task 4.5: Commit

- [ ] Run:

```powershell
git add dashboard/dashboard_v1.html dashboard/dashboard_v1.css dashboard/dashboard_v1.js tools/dashboard_server.py tests
git commit -m "feat(dashboard): link review surface to workbench handoff"
```

Only stage files actually changed.

---

## Chunk 5: Workbench Patch Review Report

**Purpose:** Give the agent a concise machine-readable + human-readable summary of what the human changed.

**Files:**

- Create or modify: `tools/workbench_review_report.py`
- Modify: `tools/workbench_server.py` if adding endpoint.
- Test: `tests/test_workbench_review_report.py`
- Docs: `docs/workbench-dashboard-integration.md`

### Task 5.1: Write failing tests

- [ ] Create tests for:
  - no patch -> report says `no_changes`;
  - duration edit -> report lists slot, before/after duration;
  - source window edit -> report lists source_start/source_duration change;
  - replace clip -> report lists old/new asset and scene;
  - subtitle/audio/effect cue changes are summarized if patch files exist;
  - report never claims canonical render changed.

### Task 5.2: Implement report generator

- [ ] Output:

```text
workbench_review_report.json
workbench_review_report.md
```

- [ ] JSON shape:

```json
{
  "ok": true,
  "canonical_changed": false,
  "summary": {
    "timeline_edits": 0,
    "replacement_edits": 0,
    "subtitle_edits": 0,
    "audio_cues": 0,
    "effect_cues": 0
  },
  "edits": []
}
```

- [ ] Markdown should be readable by a human reviewer.

### Task 5.3: Add server endpoint

- [ ] Optional endpoint:

```text
POST /api/workbench/review-report
```

- [ ] It writes only the two report files.

### Task 5.4: Verify

- [ ] Run:

```powershell
python -m unittest tests.test_workbench_review_report tests.test_workbench_server -q
```

### Task 5.5: Commit

- [ ] Run:

```powershell
git add tools/workbench_review_report.py tools/workbench_server.py tests/test_workbench_review_report.py tests/test_workbench_server.py docs/workbench-dashboard-integration.md
git commit -m "feat(workbench): add patch review report"
```

---

## Chunk 6: Technical Debt Cleanup Without Behavior Change

**Purpose:** Reduce future confusion without destabilizing the working system.

**Files:**

- Modify: `.gitignore`
- Modify: `README.md`
- Modify: `RUNBOOK.md`
- Modify: `docs/INDEX.md`
- Possibly move docs only. Avoid code moves unless tests are strong.

### Task 6.1: Classify untracked demo files

- [ ] Run:

```powershell
git status --short
```

- [ ] For each untracked file, classify:
  - keep and commit as docs/demo;
  - move to `scratch/`;
  - add to `.gitignore`;
  - delete only with explicit user permission.

Known current candidates:

```text
.claude/
alternative_tech_demos.html
dashboard/workbench_native/canvas_demo.html
taipower_3d_intro_demo.html
taipower_logo.svg
```

### Task 6.2: Update `.gitignore`

- [ ] If these are throwaway demos, add:

```gitignore
# Local UI experiments
alternative_tech_demos.html
taipower_3d_intro_demo.html
taipower_logo.svg
dashboard/workbench_native/canvas_demo.html
.claude/
```

- [ ] If any are valuable, move them to `scratch/` and document.

### Task 6.3: Runbook update

- [ ] Update `RUNBOOK.md` with:
  - start dashboard;
  - start workbench;
  - generate preview timeline;
  - save patch;
  - sync contract patch;
  - generate review report;
  - run backend render.

### Task 6.4: Verify docs and status

- [ ] Run:

```powershell
git diff --check
git status --short
```

### Task 6.5: Commit

- [ ] Run:

```powershell
git add .gitignore README.md RUNBOOK.md docs/INDEX.md scratch
git commit -m "chore(project): document frontend workflow and ignore local demos"
```

Only stage paths that actually changed.

---

## Chunk 7: End-to-End Review Gate

**Purpose:** Prove the integrated surfaces still support the real operator workflow.

**Files:**

- No code expected unless failures are found.
- May update: `docs/workbench-dashboard-integration.md` with verified commands.

### Task 7.1: Full focused verification

- [ ] Run:

```powershell
node --check dashboard\workbench_native\workbench.js
node --check dashboard\workbench_native\workbench_core.js
node tests\workbench_core_smoke.js
python -m unittest tests.test_preview_timeline tests.test_workbench_server tests.test_timeline_patch -q
```

### Task 7.2: Full regression

- [ ] Run:

```powershell
python -m unittest discover -s tests -q
```

- [ ] Expected: all tests OK.

### Task 7.3: Browser E2E

- [ ] Start Workbench server:

```powershell
python tools\workbench_server.py --artifact-root .tmp\srp_real67_fuller_replay --port 8770
```

- [ ] In browser:
  - Open `http://localhost:8770/workbench`.
  - Select a clip.
  - Trim right; confirm clamp at source window.
  - Double-click material to replace selected clip.
  - Add subtitle edit if available.
  - Add audio cue if available.
  - Add effect cue if available.
  - Save all.
  - Sync contract patch.
  - Generate review report if implemented.

- [ ] Verify files:

```powershell
Get-ChildItem .tmp\srp_real67_fuller_replay | Where-Object { $_.Name -match 'timeline_patch|patched_draft|workbench_contract|workbench_handoff|review_report' }
```

### Task 7.4: Canonical safety check

- [ ] Before manual edits, capture hashes:

```powershell
Get-FileHash .tmp\srp_real67_fuller_replay\timeline.json
Get-FileHash .tmp\srp_real67_fuller_replay\final.mp4
```

- [ ] After manual edits, re-run hashes.
- [ ] Expected:
  - canonical `timeline.json` unchanged;
  - canonical `final.mp4` unchanged;
  - only draft artifacts changed.

### Task 7.5: Final integration decision update

- [ ] Update `docs/archive/decisions/2026-06-17-dashboard-workbench-integration-cleanup.md`:
  - `Status: verified`
  - Add test commands and results.
  - Add final commit hashes.

### Task 7.6: Final commit

- [ ] Run:

```powershell
git add docs/archive/decisions/2026-06-17-dashboard-workbench-integration-cleanup.md docs/workbench-dashboard-integration.md
git commit -m "docs(workbench): record integration verification"
```

---

## Review Protocol

After each chunk:

1. Run focused tests.
2. Inspect `git diff --stat`.
3. Inspect the diff for accidental broad changes:

```powershell
git diff -- dashboard tools tests docs roadmap.md README.md RUNBOOK.md
```

4. If frontend changed, do a browser check.
5. Commit only the chunk.
6. Write a short report:

```markdown
Chunk N complete.
Files changed:
- ...
Tests:
- ...
Browser check:
- ...
Commit:
- ...
Deferred:
- ...
```

If any test fails:

- Do not continue to next chunk.
- Fix within the chunk if caused by current changes.
- If unrelated, record evidence and ask for direction.

---

## Commit Strategy

Expected commits:

1. `docs(workbench): define dashboard integration contract`
2. `fix(workbench): stabilize preview and timeline layout`
3. `fix(workbench): harden draft artifact ownership`
4. `feat(dashboard): link review surface to workbench handoff`
5. `feat(workbench): add patch review report`
6. `chore(project): document frontend workflow and ignore local demos`
7. `docs(workbench): record integration verification`

Do not squash during development. The commit sequence is part of the audit trail.

---

## Definition Of Done

The cleanup is complete only when:

- Dashboard and Workbench responsibilities are documented.
- Dashboard can point to Workbench / handoff status.
- Workbench still supports:
  - preview playback;
  - material replacement;
  - source-window trim clamp;
  - subtitle/audio/effect draft markers;
  - save/sync draft artifacts.
- Workbench cannot overwrite canonical outputs.
- Agent-facing handoff/report clearly states what changed.
- Browser check passes on `.tmp\srp_real67_fuller_replay`.
- Focused tests pass.
- Full regression passes.
- Decision log is updated to `verified`.
- Worktree has no unexpected tracked changes.

## Continuation Scope (2026-06-17)

After the first dashboard/workbench cleanup pass, continue with these bounded
alignment tasks:

1. Add a Workbench patch review report that an Agent can consume without opening
   the browser.
2. Keep the report draft-only; it must not imply canonical render changes.
3. Document material organization policy: material-map references are canonical;
   physical asset relocation is optional projection work, not required for the
   current pipeline.
4. Keep Dashboard read-only and Workbench write-limited.
5. Verify via focused tests, full regression, and HTTP API checks.

---

## Stop Conditions

Stop and report instead of pushing forward if:

- Workbench starts overwriting canonical artifacts.
- Dashboard gains editing behavior.
- Frontend changes require a new framework or package manager.
- A change requires modifying M6 gates or official render semantics.
- Full regression fails for reasons not caused by this cleanup.
- Browser preview becomes materially worse than the current state.
