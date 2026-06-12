# Decision: S4b Needs-Patch Visual Verdict

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S4b / agent visual-review verdict

## SPEC

Extend visual verdicts beyond binary accept/reject with:

```json
{"action":"needs_patch","patch":{"type":"window|crop|treatment","hint":{}}}
```

Keep legacy `accept: true|false` verdicts valid.

## DO

- Normalize `action` and legacy `accept` in `visual_review.py`.
- Validate patch type/hint and derive picked windows for window patches.
- Consume window patches as new extract windows.
- Consume crop patches as concrete `crop_center`; the MV renderer applies a
  crop-aware ffmpeg filter.
- Consume treatment patches as concrete `still_treatment`, using the existing
  photo treatment renderer.
- Mark patched selections as `agent_patch` in the plan trace.

## VERIFY

- Focused verdict/planner/render-filter tests: 33 PASS.
- Full regression: 645 tests PASS.
- Gen-smoke real candidate smoke: window, crop, and treatment patches each
  produced the expected concrete slot and `agent_patch` trace.
- Existing accept/reject verdict and runtime resume tests remain passing.

## Decision Notes

`needs_patch` means the candidate is usable after a bounded deterministic
correction. It is not an invitation for arbitrary generation or opaque edits.

Search tags: `s4b`, `needs_patch`, `visual-review`, `crop_center`
