# Decision: Attention Budget Drives Build Allocation

Date: 2026-06-12
Status: verified
Scope: Node 9 / BUILD allocator / Node 10
Superpowers phase: verify

## SPEC

Requirement:

Make BUILD consume the existing segment-level attention budget.

Why:

Node 9 calculated attention ownership and Node 11 audited it, but the renderer
still allocated shots from legacy pace fields. Music-only segments could remain
slow even when the attention budget required visual progression.

Direction:

Use Node 9 as the semantic source. Attach its budget to the flat runtime payload
before render, let `allocate_segments` consume music/visual shot bands, and
preserve the consumed budget in render-plan and timeline traces.

Non-goals:

Do not infer speech from text cards. Do not change protected opening, closing,
or title holds.

## DO

Files / modules:

- `video_pipeline_core/attention_budget.py`: music-only pacing band.
- `video_pipeline_core/edit_artifacts.py`: correct narration-mode mapping and
  preserve timeline budget trace.
- `video_pipeline_core/contract_adapter.py`: attach Node 9 budgets before render.
- `video_pipeline_core/mv_cut.py`: consume budget during shot allocation.

Function-level plan:

`_attach_attention_budgets` builds Node 9 intent before `mv_chain`.
`allocate_segments` gives music/visual owners precedence over generic hold and
legacy pacing. Explicit speech ownership continues to allow longer holds.

Data / interface changes:

Generated runtime segments, render-plan slots, and timeline clips may contain
`attention_budget: {owner, shot_sec, reason}`.

Migration / compatibility:

Legacy payloads without `attention_budget` retain their prior allocation.

## VERIFY

Pre-checks:

E3 v1 proved the budget attachment path existed but exposed that
`audio.role: music` was incorrectly mapped to narration.

Tests:

Focused allocator, attention-budget, contract-adapter, edit-artifact, and
visual-fatigue suites pass. Full-suite verification is required before closure.

Manual checks:

Real run:
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-e3-attention-budget-v2`

Result: segment 2 increased from 6 to 8 shots and segment 3 from 8 to 12 shots;
total cuts increased from 16 to 22. Opening and closing remained one shot each.
VERIFY 92.5, P1 audits, visual review, xfade, and light-effects baseline passed.

Regression risks:

Incorrect narration detection can over-permit long holds. Bookend protection
must not become a general exemption for music-only segments.

## Decision Notes

Accepted because:

The channel carrying the story must control time allocation. Keeping this rule
in Node 9 avoids duplicating semantic inference inside the renderer.

Tradeoffs:

Music-only segments may reuse more source windows when source variety is low.
Existing source-reuse and visual-fatigue audits remain responsible for flagging
that separate quality issue.

Open questions:

E4 should expose deterministic HTML overlay recipes without weakening the
attention-budget allocation now established.

## Git / Retrieval

Related files:

`video_pipeline_core/attention_budget.py`,
`video_pipeline_core/edit_artifacts.py`,
`video_pipeline_core/contract_adapter.py`,
`video_pipeline_core/mv_cut.py`

Related commits:

Pending.

Graphify anchors:

`resolve_attention_budget`, `_attach_attention_budgets`,
`build_assembly_plan`, `allocate_segments`, `build_timeline_build`

Search tags:

`decision-log`, `E3`, `attention-budget`, `build-allocation`, `pacing`
