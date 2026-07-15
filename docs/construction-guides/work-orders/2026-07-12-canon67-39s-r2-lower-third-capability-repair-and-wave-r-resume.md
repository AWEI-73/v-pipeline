# Work Order — Canon 67 39s R2 Lower-Third Capability Repair And Wave R Resume

Date: 2026-07-12
Status: ready for execution
Execution shape: one sequential long-running worker; TDD capability repair, real forward test, then resume the frozen Wave R plan

## 1. Goal And Authority

Repair the existing public `motion_graphics.html_playwright` info-card surface so the already-approved Canon 67 lower third can pass its fixed R2 contract, then resume R3–R6 from the frozen L1 last-green state.

Read in this order:

1. `AGENTS.md`
2. `skills/pipeline-boundary.md`
3. `skills/editing-loop-director.md`
4. `skills/video-effect-factory.md` if present in this repository; otherwise use the installed `video-effect-factory` skill
5. `docs/decisions/2026-07-12-motion-graphics-bounded-info-card-controls.md`
6. `docs/construction-guides/work-orders/2026-07-12-canon67-39s-wave-r-l0-l5-integrated-render.md`
7. this work order
8. `.tmp/editing_loop_39s_integrated_campaign/wave_r/wave_r_worker_report.md`
9. `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2/factory_gap_l2_lower_third_public_surface.json`

This work order supersedes only the original Wave R production-code boundary for the bounded R2 capability repair below. All fixed inputs, delegations, transcript truth, R3–R6 requirements, final owner gate, and approval flags from the original work order remain unchanged.

## 2. Verified Starting State

| Item | Required value |
| --- | --- |
| Phase C commit | `52650b84ae734361b6c0d0a95e20e6f08da9385b` or descendant |
| frozen L1 candidate | `.tmp/editing_loop_39s_integrated_campaign/wave_r/l1/picture_candidate.mp4` |
| frozen L1 SHA-256 | `145C0D845C5B7D1C099D5CA63F982DB0410BC22664956454470AA86E937827BC` |
| frozen L1 decoded-audio MD5 | `25b4f998e873dd6a27c7a0af3e43daba` |
| owner transcript decision SHA-256 | `5D40C6ED1555FE9E08E51FA398295FEF16F28496EFA76E671287FF1EFC5DC046` |
| rejected R2 candidate SHA-256 | `D0E5D380D611F6658459D415096588D3F57E242AB424830EC403377079F5DCC5` |
| final legal endpoint | `WAITING_OWNER_39S_L0_L5_FINAL_VERDICT` |

Before mutation, verify every frozen hash and preserve the rejected `wave_r/l2/**` evidence unchanged. Stop on drift.

## 3. Root Cause And Fixed Decision

This is not a conflicting-contract case. The existing HTML info card hard-codes approximately:

- `left=140px`, `bottom=150px`, `min-width=620px`;
- `padding=45px 55px`, `font-size=150px`, `border-left=8px`;
- transition envelope `min(1, q*5, (1-q)*5)`.

The fixed geometry produces lower-third bbox `[140,674,877,929]`; frozen cue01 produces `[543,928,1377,993]`. Their intersection is `[543,928,877,929]`. The card is also materially larger than the approved restrained lower-third direction.

Decision: add a backward-compatible, closed, bounded `style.info_card` object to the existing public capability. Do not alter subtitle placement or the approved R2 timing.

## 4. Owner Zone

Capability commit may modify only:

- `video_pipeline_core/motion_graphics.py`
- `tests/test_motion_graphics.py`

Execution artifacts may be written only to:

- `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2_repair/**`
- the existing Wave R report and campaign status, append/update without deleting prior stop evidence;
- original R3–R6 output locations already authorized by the parent work order after repaired R2 is objectively green;
- one new Drive review subfolder authorized by the parent work order, only after R6 is green.

Stage and commit only the two capability/test paths after focused GREEN. Preserve the pre-existing dirty tree.

## 5. Forbidden Zone

- Do not modify `video_pipeline_core/subtitle_presentation.py`, subtitle burn code in `video_tools.py`, approved transcript artifacts, raw media, Skills, Product Spec, registries, route runners, or orchestrators.
- Do not create a renderer, route, schema version, generic layout engine, private ffmpeg path, run-local JSON compiler, or Remotion implementation.
- Do not overwrite or promote the rejected `wave_r/l2/**` artifacts.
- Do not change the fixed text, lifecycle, subtitle placement, acceptance thresholds, or owner transcript decision.
- Do not run the full suite before R6 candidate checks are all green.
- Never set `human_creative_approval=true` or `final_delivery_claimed=true`.

If a RED test proves that another production path is strictly required, stop and report the exact dependency; do not expand the owner zone yourself.

## 6. H1 — RED/GREEN Bounded Public Controls

Use TDD. First add failing tests, capture their command/exit, then make the smallest implementation.

Add one optional `style.info_card` object. It may contain only these numeric fields, with explicit sane bounds:

```json
{
  "left_px": 140,
  "bottom_px": 190,
  "min_width_px": 360,
  "padding_x_px": 32,
  "padding_y_px": 22,
  "main_font_px": 76,
  "accent_width_px": 4,
  "background_alpha": 0.78,
  "translate_y_px": 18,
  "enter_frames": 10,
  "exit_frames": 10
}
```

Requirements:

1. The validator rejects unknown keys, booleans masquerading as numbers, non-finite numbers, wrong types and out-of-range values.
2. `build_motion_graphics_render_plan()` preserves only validated values.
3. `_write_html_overlay()` uses the opt-in values for CSS and independently frame-bounded enter/exit progress.
4. `enter_frames` and `exit_frames` do not scale with total asset duration. Handle zero/short duration safely.
5. With no `style.info_card`, legacy output remains byte/semantic compatible with its existing defaults and `q*5` transition behavior.
6. Do not accept arbitrary CSS strings or expressions.

Minimum RED coverage:

- full allowed-field pass-through;
- unknown/wrong-type/non-finite/out-of-range rejection;
- exact requested CSS values in generated HTML;
- a 2.60s, 30fps asset uses 10-frame enter and 10-frame exit envelopes;
- legacy no-control output retains prior defaults.

Run:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_motion_graphics -v
git diff --check -- video_pipeline_core/motion_graphics.py tests/test_motion_graphics.py
```

Expected after GREEN: exit `0`. Then run the directly adjacent existing tests that import or exercise motion graphics; list the exact discovered modules and results in the report. Do not guess a nonexistent test name.

Commit only the two authorized files with a narrow message such as `feat: add bounded info-card controls`.

## 7. H2 — Real Repaired R2 Forward Test

Create fresh artifacts under `wave_r/l2_repair/**`; never copy a PASS from old evidence.

Use Effect Factory to produce a public v1 motion-graphics contract with:

- exact text: `主任勉勵`;
- exact schedule: start `0.60s`, duration `2.60s`, end `3.20s`;
- lower-left compact info card;
- white text and warm-yellow fine accent;
- the exact `style.info_card` values from H1;
- 10-frame entrance and 10-frame exit;
- no name/title invention.

Render the effect asset with the existing public HTML Playwright backend, then assemble it onto the frozen L1 candidate through the existing public V Pipeline path. The Effect Factory owns the effect contract, review and handoff; it does not own the integrated `final.mp4`.

Produce at minimum:

- `effect_design_map.json`
- `effect_contract.json`
- `motion_graphics_render_plan.json`
- actual effect asset and lifecycle evidence
- same-candidate cue01 collision diagnostic
- dense frames/strip at entrance, full display, exit, and cue01 overlap window
- `effect_review.json`
- `effect_handoff.json`
- semantic diff and hashes

Objective R2 acceptance:

| Check | Required result |
| --- | --- |
| text | exact `主任勉勵` |
| schedule | `0.60–3.20s` within one frame |
| entrance / exit | each 8–12 frames; target 10 |
| card bounds | width `≤620px`, height `≤170px` |
| cue01 separation | no pixel intersection and minimum vertical gap `≥24px` |
| face safety | no face obstruction on sampled frames |
| style | white text, warm-yellow fine line, restrained documentary appearance |
| L1 decoded audio MD5 | exactly `25b4f998e873dd6a27c7a0af3e43daba` |
| streams / duration | one video + one audio; 39.34s within one frame |
| protected layers | picture timing and approved transcript inputs unchanged |

Process exit alone is not PASS. Inspect the actual full-resolution frames. If any objective item fails, use at most one LOCAL correction for that failure class; recurrence is STRUCTURAL and stops at the last green state.

## 8. H3 — Resume Parent Wave R R3–R6

Only after every H2 objective check passes:

1. Promote the repaired R2 handoff as the active L2 input while retaining rejected evidence as history.
2. Resume Sections 10–13 of `2026-07-12-canon67-39s-wave-r-l0-l5-integrated-render.md` without redoing L0/L1 or changing their decisions.
3. Complete L3 preview-only ducked music, L4 owner-approved subtitles, R5 same-candidate four-layer integration, and fresh R6/L5 review.
4. Run focused/adjacent checks first. Run the full suite exactly once, last, only after the integrated candidate is objectively green:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest discover -s tests
git diff --check
```

5. Upload the parent work order's bounded review package to a new subfolder under Drive parent `1dCNkMOYtxUlJraumLPY8-ZIB7aoJX-fb`; read the folder back and record IDs, URLs, names and sizes.
6. Stop at `WAITING_OWNER_39S_L0_L5_FINAL_VERDICT`. Final creative quality remains `UNKNOWN` until the owner watches/listens.

## 9. Stop-Loss And Reporting

- One LOCAL correction per failure class. Recurrence or interface bypass is STRUCTURAL.
- Stop on fixed-hash drift, inability to preserve legacy behavior, subtitle code becoming necessary, public assembly failure, objective QA failure, or required out-of-zone edits.
- Never hide failure by shrinking evidence windows, moving cue01, changing thresholds, or calling an output approved.
- Record every command, exit, hash, visual measurement, deviation, skipped phase, dirty-tree snapshot and blind spot.

Update `.tmp/editing_loop_39s_integrated_campaign/wave_r/wave_r_worker_report.md` and campaign status. The report must distinguish:

- capability test PASS;
- real R2 product PASS/FAIL;
- R3–R6 PASS/FAIL/UNKNOWN;
- owner taste `UNKNOWN`;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

The worker may report `WAITING_OWNER_39S_L0_L5_FINAL_VERDICT` only if repaired R2, the four-layer candidate, fresh L5, final full suite and Drive read-back all exist and pass. Otherwise report the exact last-green state and blocker.
