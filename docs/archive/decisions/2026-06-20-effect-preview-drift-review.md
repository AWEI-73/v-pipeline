# Review Report: Effect Preview Drift (FX preset visual source-of-truth)

Date: 2026-06-20
Status: open ??awaiting Codex review verdict
Scope: effects-director / Workbench native preview / FX4 Remotion adapter / Node14
Reviewer ask: Codex (verify finding ??pick fix ??Claude implements ??TDD green)

> Encoding note (per `CODEX.md`): read the Markdown / `.js` / `.py` artifacts below with
> explicit UTF-8 and a `嚙窯 replacement-char check before reporting any corruption.

## Summary

The pipeline has **two independent implementations of "what an effect preset looks
like" with no shared source of truth.** The effect *intent* layer is correctly
shared, but the *visual appearance* math is hand-coded separately on each side.
This is a **preview-vs-render drift risk**, not a crash bug. This report asks Codex
to confirm the finding and choose between two fixes.

## How this was found (graphify knowledge-graph trail)

A densified knowledge graph of the repo (`graphify-out/graph.html`, 6,008 nodes)
surfaced the gap in three steps:

1. **Deep-mode densify** added a cross-document edge:
   `FX4 Remotion Prompt-Driven Adapter --semantically_similar_to[INFERRED]-->
   Borrowed Remotion Preview Model` (which lives in the Native Preview Engine
   decision). The graph flagged "these describe the same thing but are not linked."
2. **Structural-edge check**: between the 154 effects-code nodes
   (`remotion_effects.py`, `effect_contract.py`, FX1?X4) and the 22 workbench
   preview-code nodes, there are **0** `calls` / `imports_from` / `shares_data_with`
   edges. They are connected only through doc co-references via the Docs Index hub.
3. **Source confirmation** (below) showed the appearance math is independently
   hand-coded on each side.

## The finding (precise)

**Shared (good):** Both sides consume the same effect *intent* ??preset names +
intensity + timing ??originating from `effect_contract` / `effect_intent_plan`
(FX1). There is no fork at the intent level.

**Forked (the risk):** The visual rendering of each preset is defined twice.

- JS preview ??`dashboard/workbench_native/workbench_core.js`,
  `buildEffectPreviewStyle` (~line 536). Hand-coded magic numbers:
  - `flash` / `title_reveal` / `caption_emphasis`
    ??`overlay_opacity = 0.12 * intensity * (1 - progress)`, capped at `0.8`
  - `zoom_punch` ??`scale = 1 + 0.012 * intensity * pulse`
  - `shake_light` ??`tx/ty` via `sin/cos * intensity`
  - `speed_ramp_hint` / `freeze_frame_hint` ??label only
  Function comment self-describes as "lightweight monitor CSS preview state."

- Python real render ??`video_pipeline_core/remotion_effects.py`,
  `video_pipeline_core/effect_contract.py`, and the FX4 path in `video_tools.py`
  (`cmd_remotion_prompt_pack` ??worker ??`cmd_remotion_composite_draft` ??ffmpeg
  overlay). This produces the actual delivered render.

**Consequence:** the workbench monitor shows e.g. `zoom_punch` intensity=4 as
`scale 1.048`, but the Remotion/ffmpeg final render is whatever the prompt pack +
worker produce. There is no shared constant keeping them aligned, so tuning the
render side does not update the preview, and vice versa.

## What Codex should decide

Confirm or reject the drift, then choose one fix:

- **(a) Single source of truth** ??extract one canonical `preset ??visual-parameter`
  table (intensity curves, overlay opacity, scale/translate factors) that BOTH the
  Python render path and the JS preview consume, so they cannot drift.
- **(b) Approximate-by-design, made explicit** ??if the lightweight preview is
  intentionally an approximation, document that in the Native Preview Engine
  decision (`docs/archive/decisions/2026-06-16-native-preview-engine.md`) and in a code
  comment, AND add a test asserting the preview preset set is a subset of the
  contract preset set (so a new contract preset can't silently render blank in the
  monitor).

## Evidence bar

Per the project's review loop, the only accepted evidence of correctness is
`python -m unittest discover -s tests` green (currently ~516 tests). Whichever
option is chosen must land with added/extended tests for that path.

## Notes / boundaries

- This does not change the canonical renderer: ffmpeg / `contract-run` stays
  authoritative; Workbench stays a draft/preview surface (per
  `docs/archive/decisions/2026-06-19-effects-node14-roadmap-alignment.md`).
- Do not modify `graphify-out/` ??it is generated analysis output.
- Start by reading `workbench_core.js` (`buildEffectPreviewStyle`, `getActiveEffects`)
  and `remotion_effects.py` + `effect_contract.py` to confirm the gap before
  proposing changes.
