# Frontend Stability And Modularization Decision

Date: 2026-06-17

## Decision

Stabilize the Workbench frontend before broader backend cleanup. The immediate direction is a small, contract-oriented cleanup:

- Add automated Workbench smoke coverage so basic browser/API workflows can be checked without manual clicking.
- Split HTTP API calls out of the large DOM controller.
- Keep the Workbench as a draft review/editing surface, not as the canonical ffmpeg renderer or source of truth.

## Rationale

The backend material-map and BUILD layers are now large enough that frontend instability would slow review and integration. The Workbench is already useful as a lightweight material-composition preview, but the current controller is too dense and manual browser checks are too expensive to repeat. A smoke harness plus a narrow API module gives us a stable base for later UI improvements.

## Boundaries

In scope:

- Draft timeline/material preview stability.
- Patch and handoff contract verification.
- Small JavaScript module extraction.
- Documentation of frontend responsibility.

Out of scope:

- Visual redesign.
- Full real-time editing engine.
- Remotion integration.
- Node 14/effects implementation.
- Canonical contract overwrite.
- Physical material folder moves.

## Expected Follow-Up

After this pass, future work can proceed in smaller lanes:

- Material browser improvements and replacement workflow.
- Dashboard shell integration.
- Node 14/effect intent UI.
- Backend technical-debt cleanup after the frontend base is stable.
