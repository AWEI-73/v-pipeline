# Decision: Bounded controls for the existing motion-graphics info card

Date: 2026-07-12
Status: accepted
Scope: `video_pipeline_core.motion_graphics` / Canon 67 Wave R R2
Superpowers phase: review

## SPEC

Requirement: The existing public `motion_graphics.html_playwright` info-card capability must be able to render a compact lower third with bounded geometry and independently bounded enter/exit timing, while preserving its current output when those controls are omitted.

Why: The Canon 67 R2 forward test proved that the current public template hard-codes a large card and derives animation duration from 20% of the whole asset. It therefore cannot simultaneously satisfy the approved `0.60–3.20s` lifecycle, an 8–12-frame entrance/exit, and non-collision with frozen cue01. The approved subtitle presentation and the fixed R2 design are not mutually contradictory; the card can fit above cue01 if it is compact and slightly higher.

Direction: Extend the existing v1 motion-graphics contract with one optional, validated `style.info_card` object. Pass only recognized bounded numeric fields into the render plan and HTML writer. Use opt-in values for the Canon 67 repair; retain all legacy defaults and behavior when the object is absent.

Non-goals: Do not create a renderer, route, schema version, generic layout engine, subtitle-placement option, Remotion worker, or project-wide style system. Do not weaken the fixed lower-third contract or move cue01 to hide the defect.

## DO

Files / modules:

- `video_pipeline_core/motion_graphics.py`
- `tests/test_motion_graphics.py`

Function-level plan:

- Validate a closed set of optional `style.info_card` numeric fields with explicit bounds.
- Preserve the validated object in `build_motion_graphics_render_plan()`.
- Make `_write_html_overlay()` consume those values for card geometry, typography, accent line, alpha, translation distance, and independent enter/exit frame counts.
- Preserve current hard-coded HTML and `q*5` animation semantics when no opt-in object is supplied.

Data / interface changes: Optional fields only; existing v1 contracts remain valid. Unknown keys and non-finite, non-numeric, or out-of-range values fail closed.

Migration / compatibility: No migration. Existing artifacts and call sites that omit `style.info_card` must render as before.

## VERIFY

Pre-checks: Re-hash the frozen L1 candidate and retain the rejected R2 artifacts as before evidence.

Tests:

- RED then GREEN for render-plan pass-through of every allowed field.
- Reject unknown, wrong-type, non-finite, and out-of-range controls.
- Assert generated HTML contains the requested numeric CSS values.
- Assert `enter_frames` and `exit_frames` are independent of total asset duration.
- Assert legacy no-control output keeps the existing defaults and transition formula.

Manual / product checks: Render the repaired card on the frozen 39.34-second L1 candidate at exactly `0.60–3.20s`. Verify exact text, lifecycle, 8–12-frame transitions, face safety, compact bounds, at least 24px separation from cue01, unchanged decoded-audio MD5, unchanged stream count, and unchanged duration within one frame.

Regression risks: Silent change to existing info-card appearance; accepting arbitrary CSS; animation divide-by-zero at short durations; treating a process exit as visual acceptance.

## Decision Notes

Accepted because: Fresh rendered evidence shows a one-pixel intersection at the current hard-coded card edge, while the card itself is substantially larger than the requested restrained documentary lower third. A bounded extension to the existing capability fixes the owning component without moving subtitles or weakening the design.

Tradeoffs: A few numeric controls expand the public surface, but a closed optional object is smaller and safer than a new renderer or a one-off composition path.

Open questions: None for this repair. Broader responsive layout remains evidence-triggered future work.

## Git / Retrieval

Related files:

- `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2/factory_gap_l2_lower_third_public_surface.json`
- `.tmp/editing_loop_39s_integrated_campaign/wave_r/l2/effect_render_evidence.json`
- `.tmp/editing_loop_39s_integrated_campaign/wave_r/wave_r_worker_report.md`
- `docs/construction-guides/work-orders/2026-07-12-canon67-39s-wave-r-l0-l5-integrated-render.md`

Related commits: `52650b84ae734361b6c0d0a95e20e6f08da9385b`

Graphify anchors: motion graphics info card; lower-third collision; bounded renderer controls; Canon 67 Wave R R2.

Search tags: `decision-log`, `motion-graphics`, `lower-third`, `subtitle-collision`, `wave-r`, `canon67`
