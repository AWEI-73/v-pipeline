# Working Loop & TDD-Evidence Rule (shared, repo-tracked)

Date: 2026-06-14
Status: active convention

This is the repo-visible copy of the working agreement so every agent (Claude,
Codex, future) shares it. (Claude also keeps a private memory note, but that is
not visible to other agents — this file is the source of truth.)

## The loop

```
Claude 實作 → Codex Review → Claude 修正
```

- **Incremental, not revert.** Fixes stack on top of prior commits; do not revert
  a reviewed commit to "redo it cleanly". Review history must stay legible
  (e.g. `e48b307` contract → `cbc171c` hardening F1-F4 → `c810ab3` round 2 →
  round 3, each a separate commit).
- **No front/back-end split.** Single codebase, single pipeline.
- **Out of scope unless explicitly asked:** Dashboard / UI, Node 14 / effects,
  `material_delta`, BUILD soft-ranking, `supply_review` rewrite, `rank-local`,
  the M5b action spine.

## TDD-evidence rule

**Green tests are the only accepted evidence that a piece works.**

- After every completed piece: write TDD tests, then run focused tests AND the
  full suite: `python -m unittest discover -s tests` (miniconda python).
- Do not claim "done" / "complete" without quoting a passing run.
- A reviewer may down-grade a self-declared "complete" to "implemented; hardening
  pending" until re-review passes. Only mark "contract/layer complete" after the
  reviewer's findings are all closed with passing tests.

## Validator discipline (hard-won)

Strict contracts must **error, not silently coerce or auto-fix**:
- Reject bad types explicitly; never "treat as default" while leaving the value
  unchanged.
- Python footguns to guard in validators: `isinstance(True, int)` is `True`, and
  `True in (1, 2, 3, 4)` is `True` — so booleans pass naive int/range checks.
  Reject `bool` explicitly where an int is required.
- Join keys (e.g. `need_id`): duplicates and unknown references are errors, never
  silent renames or silent skips. A write path that can create an unvalidated
  edge must require the validation set (no permissive default).
