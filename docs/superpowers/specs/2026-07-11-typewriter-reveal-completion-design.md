# Progressive Typewriter Reveal Completion Design

Status: **OWNER APPROVED IN CONVERSATION — READY FOR FOCUSED TDD**

## Problem

The approved Canon 67 opening script requires one logical title to:

- first appear at `3.5s` (inside the approved `3–4s` window);
- become fully visible at `9.0s`;
- remain fully visible until `11.0s`.

The current `progressive_typewriter` contract exposes only `start_sec` and
`end_sec`. Its ASS writer distributes every progressive state across that whole
range, so it cannot independently control reveal completion and full-text hold.

## Decision

Add one optional overlay field:

```json
{
  "treatment": "progressive_typewriter",
  "start_sec": 3.5,
  "reveal_complete_sec": 9.0,
  "end_sec": 11.0
}
```

Semantics:

- `start_sec`: first progressive state becomes visible;
- `reveal_complete_sec`: full main text becomes visible;
- `end_sec`: full text stops being visible.

When `reveal_complete_sec` is absent, the generated ASS must remain byte-shape
compatible with the current timing algorithm. When present, it must satisfy
`start_sec < reveal_complete_sec <= end_sec`. Invalid values fail closed before
render.

## Data Flow

```text
edit_decision_plan.overlays[].reveal_complete_sec
→ edit_decision_renderer validation
→ motion_graphics_contract.items[].timing.reveal_complete_sec
→ motion_graphics_render_plan.items[].reveal_complete_sec
→ ffmpeg/libass ASS dialogue timing
```

No second overlay, `static_hold` treatment, new effect family, helper, schema
version, route or renderer is introduced.

For a multi-character main title with the optional field, progressive states
are distributed so the first state starts at `start_sec`, the final/full state
starts exactly at `reveal_complete_sec`, and the final state ends at `end_sec`.
For a one-character title, first and full visibility are necessarily the same;
the existing first-visible behavior is retained.

## Alternatives Rejected

1. Two overlays (`progressive_typewriter` + `static_hold`): expands the supported
   treatment set, duplicates text and creates overlap/stable-ID questions.
2. Accept an existing-surface approximation: leaves objective finding `l5_f01`
   unresolved against the approved script.
3. Run-local ASS or ffmpeg workaround: bypasses the formal public renderer and
   creates pilot-only technical debt.

## Scope

Production:

- `video_pipeline_core/edit_decision_renderer.py`
- `video_pipeline_core/motion_graphics.py`

Tests:

- `tests/test_edit_decision_renderer.py`
- `tests/test_motion_graphics.py`

The edit-decision compiler already copies opening overlay objects without
dropping unknown fields; it requires regression verification but no planned
production edit.

## Acceptance

- Red-first tests prove the field is currently not propagated/honored.
- Focused suites for renderer, motion graphics and compiler pass.
- Legacy no-field typewriter timing remains unchanged.
- Invalid completion timing fails before render.
- A fresh Canon 67 `candidate_l2` shows first title at `3.5s`, full title at
  `9.0s`, and full-title hold through `11.0s`.
- Semantic diff proves picture, audio, poem, montage, ending and duration did not
  change; candidate_v2 remains hash-frozen.
- No full suite is run during this phase. Full suite is deferred until the
  campaign's production-code changes are complete and before final integration.
