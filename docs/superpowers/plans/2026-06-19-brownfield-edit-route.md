# Brownfield Edit Route Implementation Plan

> **For agentic workers:** REQUIRED: Use superpowers:subagent-driven-development (if subagents available) or superpowers:executing-plans to implement this plan. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reposition Node14 as a Brownfield Edit route for local patch/revision work while preserving existing effect revision artifacts and commands.

**Architecture:** Brownfield Edit is a route layer after REVIEW/VERIFY/Workbench, not a replacement for the canonical pipeline. Existing Node14/effect commands remain compatible implementation tools under the Brownfield route. The route produces draft/reviewed artifacts and sends them through a second `contract-run`; it does not overwrite canonical inputs or bypass material-map gates.

**Tech Stack:** Python stdlib, `video_tools.py`, `video_pipeline_core/tool_command_catalog.py`, `video_pipeline_core/node_registry.py`, Markdown skills/docs, `unittest`.

---

## Scope

In scope:
- Add `skills/brownfield-edit.md` as the route skill.
- Add `brownfield_edit_route` to the workflow manifest using existing commands.
- Relabel node 14 as `Brownfield Edit` while keeping artifact compatibility.
- Update roadmap / decision / docs index.
- Add focused tests and run full regression.

Out of scope:
- Renaming existing `effect_revision_request.json`, `effect_recipe_patch.json`, or `effect-revision-*` CLI commands.
- Remotion adapter execution.
- Story-material auto coverage from Node14/Brownfield.
- Canonical artifact overwrite.

## Task 1: Define Brownfield Route Tests

**Files:**
- Modify: `tests/test_video_tools_command_catalog.py`
- Modify: `tests/test_node_registry.py`
- Modify: `tests/test_effects_roadmap_alignment_docs.py`

- [x] Write failing tests for `brownfield_edit_route`, node 14 label/skill, and docs/skill boundaries.
- [x] Run focused tests and verify they fail for missing workflow/doc/label.

## Task 2: Implement Minimal Route Surface

**Files:**
- Modify: `video_pipeline_core/tool_command_catalog.py`
- Modify: `video_pipeline_core/node_registry.py`
- Create: `skills/brownfield-edit.md`

- [ ] Add a `brownfield_edit_route` workflow that validates Workbench handoff, optionally renders non-canonical preview, converts effect gaps to draft patches, explicitly applies reviewed drafts, then returns to second `contract-run`.
- [ ] Change node 14 label/skill/description to Brownfield Edit while preserving outputs.
- [ ] Write the route skill with strict boundaries:
  - do not rewrite the blueprint;
  - do not satisfy story evidence material;
  - allow effect asset / sfx / overlay incremental patches;
  - require reviewed artifact before second render.

## Task 3: Align Roadmap And Decision Docs

**Files:**
- Modify: `roadmap.md`
- Modify: `docs/decisions/2026-06-19-effects-node14-roadmap-alignment.md`
- Modify: `docs/INDEX.md`

- [ ] Update FX3 wording to Brownfield Edit route with Node14 as legacy implementation node.
- [ ] Keep deferred items honest: actual Remotion adapter and automatic canonical overwrite remain deferred.
- [ ] Add docs index pointer to `skills/brownfield-edit.md`.

## Task 4: Verify And Commit

**Commands:**
- `python -m unittest tests.test_video_tools_command_catalog tests.test_node_registry tests.test_effects_roadmap_alignment_docs -v`
- `python -m py_compile video_pipeline_core/tool_command_catalog.py video_pipeline_core/node_registry.py`
- `python -m unittest discover -s tests -q`
- `git diff --check`

- [ ] Commit bounded change.
