# Material-map relation review

Date: 2026-06-19

## Finding

No new runtime layer is needed after ISF1.

The flow is already structurally coherent:

```text
interactive brief
  -> story soul artifacts
  -> material_needs
  -> material-map lifecycle
  -> generated fallback when allowed
  -> material-map review
  -> BUILD handoff
  -> Workbench draft review
  -> verify / delivery
```

The gap was documentation clarity, not backend behavior. The material-map docs
did not explicitly say how generated assets, storyboard panel locking, and
Workbench draft patches relate back to material truth.

## Decision

Keep material-map as the single supply/demand truth layer.

- Generated assets return as candidates and require review before they can
  satisfy `material_delta`.
- Workbench drafts are not material truth and must not overwrite canonical
  `material_needs`, maps, delta, or BUILD handoff.
- `storyboard_panel_locked=true` is a BUILD/story semantics boundary: one panel
  owns one narration beat. Stretch the panel, generate more panels, or shorten
  narration instead of auto-filling unrelated generated panels.
- Official BUILD handoff remains backend-owned and must pass M6/`contract-run`
  gates.

## No new runtime layer

Do not add another orchestrator between ISF1 and M6. Use the existing owners:

- `video-workflow` for interactive ambiguity reduction.
- `story-soul-blueprint` for story intent.
- `material-map` for supply/demand truth.
- `generated-material-producer` for provider execution and candidate evidence.
- Workbench for draft-only manual patching.
- `video-pipeline` / `contract-run` for official BUILD.

## Verification

Locked by `tests/test_material_map_relation_docs.py`.
