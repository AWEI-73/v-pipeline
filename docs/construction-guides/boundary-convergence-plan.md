# Boundary Convergence Plan

Status: active construction plan
Updated: 2026-06-25

This plan keeps the next work focused on boundary convergence instead of broad
feature expansion or full E2E reruns.

## Order

1. Route map and orphan audit
   - Keep `tools/pipeline_map.py`, `tools/orphan_audit.py`, and
     `docs/generated/pipeline_map.*` current.
   - Regenerate after route/skill/tool changes.
   - Treat Graphify as advisory; `graph.html` is optional.

2. Material gap brief boundary
   - Input: `material_needs.json`, `material_delta.json`, optional
     `material_map_lifecycle.json`.
   - Output: `material_gap_brief.json`, `shooting_brief.md`,
     `generated_material_jobs.json`, `stock_retrieval_jobs.json`.
   - Rule: gap tasks do not satisfy coverage and do not release BUILD.
     Resulting material must return through material-map review and fresh delta.

3. Curator / rough-cut boundary
   - Input: reviewed project material map with curator verdicts and
     `usable_range`.
   - Output: `rough_cut_plan.json` and optional `timeline_build.json`.
   - Rule: `reject` and `duplicate` cannot enter rough cut unless explicitly
     overridden later by a separate reviewed decision.

4. Effect Factory contract boundary
   - Input: effect intent/design language.
   - Output: `effect_design_map.json`, `effect_contract.json`,
     `remotion_prompt_pack.json`, `remotion_worker_outputs.json`,
     `effect_review.json`, `effect_handoff.json`,
     `effect_factory_boundary_acceptance_report.json`.
   - Rule: Remotion/HTML outputs are reviewed candidates, not final delivery.
   - Dictionary rule: style families are reviewable parameter surfaces. They
     propose options and controls for interaction; they are not fixed creative
     templates and must not be handed to a worker before confirmation unless the
     task explicitly requests a bounded probe.
   - Command:
     `python video_tools.py visual-technique-plan --request <TEXT> --effect-role <ROLE> --out <RUN_DIR>/visual_technique_plan.json`.
   - Route surface:
     `pipeline_home.py` must route unconfirmed plans to
     `effect_factory_parameter_review`, plans with
     `visual_technique_review.json` to `effect_factory_parameter_review_apply`,
     and confirmed plans to `effect_factory_contract`.
   - Review apply command:
     `python video_tools.py visual-technique-review-apply --plan <PLAN> --review <REVIEW> --out <CONFIRMED_PLAN>`.
   - Boundary acceptance command:
     `python tools/effect_factory_boundary_acceptance.py --out <RUN_DIR> --json`.

5. Real material-first E2E
   - Run only after the material gap and curator/rough-cut boundaries are green.
   - Goal is route correctness, not final aesthetic polish.

6. Story-first/generated E2E
   - Generated files must return through material-map candidate review and fresh
     delta before they count as coverage.

7. Dashboard / Workbench UI
   - Defer until backend artifacts are stable.
   - UI may display and patch artifacts, but must not create a second pipeline
     state machine.

8. Verification discipline
   - Use focused boundary tests while iterating.
   - `python -m unittest discover -s tests -q` is a heavy full regression and
     includes render/replay characterization. On the current Windows machine it
     can take about 8 minutes, so short client timeouts are not evidence of a
     failing suite.
   - Treat full regression as passed only when it exits 0; otherwise identify
     the first failing or hanging test module before changing code.

## Current Increment

Implement and test:

- deterministic material gap brief builder;
- rough-cut exclusion of curator `reject` / `duplicate` verdicts;
- Effect Factory no-render boundary acceptance across multiple semantic
  families;
- pipeline map / orphan audit updates proving these are connected.
