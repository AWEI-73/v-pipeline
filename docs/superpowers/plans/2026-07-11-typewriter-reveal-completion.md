# Progressive Typewriter Reveal Completion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add one backward-compatible `reveal_complete_sec` control to the existing progressive typewriter and use it to render the approved Canon 67 title lifecycle.

**Architecture:** The optional field travels through the existing edit-decision renderer into the existing motion-graphics contract/render plan and is consumed by the existing libass writer. No new effect type, renderer or orchestration surface is added.

**Tech Stack:** Python 3.11, unittest, ffmpeg/libass, existing edit-decision and motion-graphics modules.

## Global Constraints

- Follow `docs/superpowers/specs/2026-07-11-typewriter-reveal-completion-design.md` exactly.
- TDD is mandatory: observe the relevant test fail before production code changes.
- No full suite in this phase; run only the named focused/adjacent suites and real L2 verification.
- Preserve candidate_v2 and all unrelated dirty-tree files.
- `human_creative_approval=false`; `final_delivery_claimed=false`.

---

### Task 1: Define and Propagate the Optional Completion Time

**Files:**
- Modify: `tests/test_edit_decision_renderer.py`
- Modify: `tests/test_motion_graphics.py`
- Modify: `video_pipeline_core/edit_decision_renderer.py`
- Modify: `video_pipeline_core/motion_graphics.py`

**Interfaces:**
- Consumes: optional numeric `overlays[].reveal_complete_sec`.
- Produces: the same value in motion contract timing and render-plan item; invalid `start < complete <= end` fails closed.

- [ ] **Step 1: Write failing propagation and validation tests**

Add tests proving that `_motion_graphics_contract(...)` carries `9.0` from the
overlay into `timing.reveal_complete_sec`, that
`build_motion_graphics_render_plan(...)` carries it to the plan item, and that
completion before/equal to start or after end is rejected.

- [ ] **Step 2: Run red**

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_motion_graphics tests.test_edit_decision_renderer -v
```

Expected: nonzero because propagation/validation does not yet exist. Record the
failing test names and expected assertions.

- [ ] **Step 3: Implement minimal propagation and validation**

Add no new public function. Preserve absent-field behavior. Validate the optional
field in the existing renderer composition validation and motion-graphics
contract validation, then copy it through the two existing conversion points.

- [ ] **Step 4: Run focused green**

Run the Step 2 command. Expected: exit `0`.

### Task 2: Make the ASS Writer Honor Exact Full-Text Start

**Files:**
- Modify: `tests/test_motion_graphics.py`
- Modify: `video_pipeline_core/motion_graphics.py`

**Interfaces:**
- Consumes: a plan item with optional `reveal_complete_sec`.
- Produces: progressive ASS dialogue whose full-text state begins exactly at that time and ends at `end_sec`.

- [ ] **Step 1: Write a failing exact-timing test**

For main text `ABC`, start `3.5`, completion `9.0`, end `11.0`, parse/read the
ASS and assert the `ABC` dialogue is `0:00:09.00 → 0:00:11.00`. Also assert a
legacy `ABC`, `0 → 3` item without the field retains its prior final-state start
at `2.00s`.

- [ ] **Step 2: Run red and record the expected timing failure**

Run `tests.test_motion_graphics` only. Expected: nonzero for the new exact-timing test.

- [ ] **Step 3: Implement the explicit-field timing branch**

Only the explicit-field branch changes timing. Distribute multi-character states
from first state at `start_sec` to final state at `reveal_complete_sec`; keep the
final state through `end_sec`. Leave the absent-field branch untouched.

- [ ] **Step 4: Run focused and compiler-adjacent green**

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_motion_graphics tests.test_edit_decision_renderer tests.test_compile_edit_decision_plan -v
```

Expected: exit `0`.

- [ ] **Step 5: Commit the four-file capability patch only**

Do not stage experimental artifacts or unrelated files.

### Task 3: Apply the Approved L2 Lifecycle and Stop for Taste

**Files:**
- Create: `.tmp/editing_loop_certification_campaign/l2/candidate_l2/**`
- Update: `.tmp/editing_loop_certification_campaign/l2/**`
- Update: `.tmp/editing_loop_certification_campaign/campaign_status.md`

**Interfaces:**
- Consumes: candidate_v2 plus owner-approved `3.5/9.0/11.0` lifecycle.
- Produces: fresh candidate_l2, title lifecycle evidence, semantic diff, rendered QA and owner preview.

- [ ] **Step 1: Store the owner authorization verbatim and re-hash candidate_v2**
- [ ] **Step 2: Render a new candidate with only `opening_title_text.reveal_complete_sec=9.0` and approved start/end**
- [ ] **Step 3: Prove all protected picture/audio/poem/montage/ending/duration fields are unchanged**
- [ ] **Step 4: Read the generated ASS and render frames around 3.5, 9.0 and 11.0 seconds**
- [ ] **Step 5: Run fresh rendered QA, final verify and a current→candidate_l2 dynamic comparison**
- [ ] **Step 6: Stop exactly at `WAITING_OWNER_FINAL_L2_TASTE_VERDICT`**

Do not mark L2 certified, update maturity docs, start L0, or run the full suite.
