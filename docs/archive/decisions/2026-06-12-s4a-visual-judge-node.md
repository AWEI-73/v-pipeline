# Decision: S4a Visual Judge Node

Date: 2026-06-12
Status: verified
Scope: Sensory Phase S4a / dashboard node lifecycle

## SPEC

Promote the existing E6 agent visual-review gate to explicit Node `10.5`,
between Timeline and Editor Review. Do not change request/verdict machinery.

## DO

- Add `10.5 Visual Judge` to `NODE_ORDER` and `NODE_REGISTRY`.
- Verify request/verdict lifecycle:
  - neither: optional;
  - request only: warn, awaiting verdict;
  - request plus verdict: done;
  - verdict only: warn, malformed lifecycle.
- Surface request and verdict artifact links on the node.
- Preserve decimal node IDs as strings in dashboard state.
- Attribute the existing await-review finding to Node `10.5`.

## VERIFY

- Focused node/dashboard/runtime regression: 40 tests PASS.
- Full regression: 639 tests PASS.
- Python compile and `git diff --check`: PASS.

Real-run dashboard review:

- City-lite S3b: Node `10.5` is optional, with no review artifacts.
- Gen-smoke `20260612-111722-run-auto`: Node `10.5` is done, links both
  request and verdict, and leaves `next_action=complete_review_final`.

Agent sensory review:

- Gen-smoke seg1 montage supports the existing qualified acceptance: notebook,
  coffee, and warm domestic light are present, while the bed tray and visible
  hand differ from the brief.
- Seg2 montage supports the existing rejection: static dark top-down notebook
  and icon do not match a warm floating origami lightbulb.

## Decision Notes

This is lifecycle visibility only. E6 request generation, montage evidence,
verdict validation, and resume behavior remain unchanged.

Search tags: `s4a`, `visual-judge`, `node-10.5`, `visual-review`
