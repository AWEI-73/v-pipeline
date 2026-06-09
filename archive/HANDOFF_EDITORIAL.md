# HANDOFF — Editorial Soul Layer (full-takeover ready)

> **STATUS 2026-06-08:** the editorial layer is now **fully wired** — Tasks 4/5
> (editorial_qa, shot_slots) and the shared-file wiring (A: editing_policy in
> build_profile; B: blueprint-compile CLI; C: editorial_qa/shot_slots into Node 12/9)
> all landed. Full suite **453 OK**. For the consolidated conceptual map read
> **`docs/editorial-layer.md`**. The task descriptions below are kept as historical
> reference (and for Task D beat-grid polish, if pursued).

Updated: 2026-06-08. This document is self-contained: any agent (Gemini/Codex/Claude)
can continue the editorial-layer work from here, including the shared-file wiring.

Read first: `roadmap.md`, then the three specs:
`docs/narrative-blueprint-spec.md` (WHY), `docs/editing-intent-sequence-grammar-spec.md`
(HOW-structure, Codex), `docs/material-treatment-grammar-spec.md` (HOW-material).
Decision log: `docs/decisions/2026-06-08-editorial-soul-layer-and-treatment-grammar.md`.

## 1. Goal

The converged SPEC→render→verify pipeline made correct-but-lifeless videos. The
editorial layer adds, at the front: a narrative spine (every shot serves one thesis)
and content-driven material treatment (e.g. an enumeration renders as a labeled
beat photo-stack, not one long clip). Turn "clip selection + subtitle" into "a told
story segment".

## 2. Current state (commits on `master`)

```
f571e44  three-tier soul layer + material treatment grammar + stack renderer
9024877  editing-intent modules (visual_fatigue/editorial_design/blueprint_compile)
         + visual_fatigue wired into Node 11
```

- Full suite: **442 tests OK** (`python -m unittest discover -s tests`).
- Green fixtures: `examples/genre_tests/stock_story_e2e` (ffmpeg E2E, verify 92.5 PASS,
  blueprint gate live) and `examples/genre_tests/treatment_demo` (enumeration → 3
  beat-fast ~0.93s labeled stills, treatment_audit PASS).

### Wired vs not

```
WIRED (live in runtime):
  blueprint gate              blueprint.py -> runtime_orchestrator.check_run (pre-render, blocking)
  material treatment          contract_adapter passthrough -> edit_artifacts.build_assembly_plan
                              -> treatment_audit.json -> dashboard_state/_AUDIT_NODE (node 11)
  photo-stack renderer        mv_cut (_stack_items/allocate_segments/_plan_stock_stack_segment)
  visual_fatigue audit        edit_artifacts emits visual_fatigue_audit.json (opt-in on editing_policy)

NOT WIRED (modules exist + tested, integration pending):
  editorial_design.py         default/validate exist; NOT fed into build_profile yet
  blueprint_compile.py        compile_blueprint_md exists; no CLI / Node 0A producer
  editorial_qa (Node 12)      module not written yet (Task 4)
  shot_slots expansion (Node 9) module not written yet (Task 5)
```

## 3. The reusable AUDIT-WIRING recipe (follow exactly)

Every new deterministic audit plugs into Node 11/12 the same way. Use this for
editorial_qa or any future audit. Concrete names from the existing wiring:

1. **Produce** the JSON in `edit_artifacts.write_edit_artifacts` (after timeline is
   built). Gate it so it's inert for runs that don't opt in (e.g. `if editing_policy:`
   or `if any(s.get("treatment") ...)`). Add the path to the returned `result` dict.
2. **Load + surface** in `dashboard_state.load_dashboard_state`:
   - `X = safe_load_json(manifest.get("X")) or safe_load_json("X.json")`
   - add `X` to the `audit_data` dict and to the `audit_evidence` role tuple
   - add `"X"` to `NODE_AUDIT_MAP[11]` (or `[12]`) and `AUDIT_PRIMARY_NODE["X"]=11`
   - the existing loop turns `pass is False` into a routed `type:"error"` finding.
3. **Route** in `runtime_orchestrator._AUDIT_NODE`: add `"X": "11"`. `resolve_audit_route`
   then blocks completion on a failing finding.
4. **Clear on rerun**: add `"X.json"` to the Node 11 `outputs` list in `node_registry.py`.

Key principle everywhere: **opt-in / inert-when-absent** — a new feature must not
change a run that didn't ask for it. This is why the green fixtures stay green.

## 4. Remaining tasks (full takeover)

### Pure-module tasks (no shared-file edits; template = treatment_audit.py)

**Task 4 — Node 12 editorial_qa.** New `video_pipeline_core/editorial_qa.py` +
`tests/test_editorial_qa.py`.
```python
def review_editorial(artifacts: dict) -> dict:
    # artifacts: brief, blueprint, contract, assembly_plan, timeline_build,
    #   treatment_audit, visual_fatigue_audit, blueprint_coverage, verify_result
    # -> {"artifact_role":"editorial_qa","version":1,"pass":bool,"score":int,
    #     "dimensions":{intent_alignment,narrative_coherence,artifact_consistency,
    #                   visual_variety_fit,pacing_fit,...},
    #     "findings":[{"level","dimension","message","route"}]}
```
Mechanical-first (optional VLM later). Reviewer rules from spec §Node 12: report
mismatches only, never mutate artifacts or invent requirements, every finding has a
`route`. Pure function.

**Task 5 — Node 9 shot_slots.** New `video_pipeline_core/shot_slots.py` +
`tests/test_shot_slots.py`.
```python
def expand_shot_slots(segment: dict, n_required: int | None = None) -> list[dict]:
    # expand segment.sequence_grammar.required_functions into shot_slots
    # -> [{"slot","function","reason","preferred_media","target_duration_sec",
    #      "candidate_requirements"}]   (spec §Node 9 shape)
```
Pure; no rendering.

### Shared-file wiring tasks (touch the integration spine — do carefully, opt-in)

**Task A — editorial_design → build_profile.editing_policy** (activates visual_fatigue).
- `build_profile.py`: add an optional `editing_policy` field to the profile (default
  `None`/absent; populate from an `editorial_design.json` when present).
- `contract_adapter.py` (`run_contract`/around the build_profile build, ~line 460-520):
  load `editorial_design.json` from the run dir if present, derive `editing_policy`
  (via `editorial_design`/spec §Node 8 defaults), put it into `build_profile_payload`.
  `write_edit_artifacts` already forwards `build_profile_payload.get("editing_policy")`,
  so once it's non-None, `visual_fatigue_audit.json` starts being produced.
- Verify: a run with an editorial_design produces `visual_fatigue_audit.json`; a run
  without one does not (green fixtures unchanged).

**Task B — blueprint_compile CLI + Node 0A.**
- `video_tools.py`: add a `blueprint-compile <blueprint.md> [--out blueprint.json]`
  command (thin shim over `blueprint_compile.compile_blueprint_md`; pattern = the
  `blueprint-coverage` cmd already there). Register in parser + dispatch.
- Optional: in `runtime_orchestrator._copy_initial_artifacts`, if `blueprint.md`
  exists but `blueprint.json` doesn't, compile it.

**Task C — wire editorial_qa (Task 4) into Node 12** using the §3 recipe (it's an
audit; node 12). And **wire shot_slots (Task 5)** into `edit_artifacts.build_assembly_plan`
(add `shot_slots` to each segment entry when sequence_grammar is present, opt-in).

**Task D — beat-grid binding for stacks.** `mv_cut`: bind stack still cut times to the
actual beat grid timestamps (today each still is a fixed ~one-beat length via
`stack_shot_sec`, not snapped to grid times). Then `treatment_audit` beat_lock can be
exercised. Optional polish.

## 5. Conventions & gotchas (Windows)

- Run tests: `python -m unittest discover -s tests` (set `$env:PYTHONUTF8=1` or
  `export PYTHONUTF8=1` first; cp950 console otherwise breaks on CJK/emoji).
- Inline `python -c` reading a path: MSYS translates CLI args but NOT in-string
  literals — run multi-step checks in ONE in-process `python - <<PY` script, or use
  repo-relative paths. (This bit us once.)
- Real E2E: `python video_tools.py project-init "<name>"`, `project-new-run --label x`,
  copy `segment_contract.json`+`brief.json`(+`material_categories.json`,`blueprint.json`)
  into `<project_root>/<slug>/input/`, then `python runtime.py run --project <slug>`.
  Needs ffmpeg on PATH, `PEXELS_API_KEY` in `.env` (auto-loaded), yt-dlp, Ollama. A
  contract MUST have a brief (else the runtime now stops asking for one).
- Honesty guard is sacred: content_pattern testimony/proof/identity and any
  `must_include` segment must never be filled by stock/generated (see
  `stock_first._can_use_stock`, `material_treatment` honesty guard).
- Do NOT commit `roadmap.md` (it had a pre-existing uncommitted edit not made by this
  work). External run outputs live in `../video_project/` (gitignored) — never commit.
- ffmpeg stays canonical. No new render backend. No forced cuts.

## 6. Suggested order

Task 4 + Task 5 (Gemini, parallel, isolated) → Task A (activates visual_fatigue) →
Task C (wire 4/5) → Task B → Task D. After each, run the full suite and confirm the
two green fixtures still pass.
