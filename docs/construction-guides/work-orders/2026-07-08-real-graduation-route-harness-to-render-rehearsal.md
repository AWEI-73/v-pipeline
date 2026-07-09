# Real Graduation Route Harness To Render Rehearsal

Date: 2026-07-08
Status: ready for worker

## Goal

Run the graduation product route harness against real graduation route evidence,
not a tiny fixture, and push as far as a truthful render rehearsal allows.

This round should consolidate the product route, shot proof, visual review,
effect handoff, music/subtitle profile, harness trace, rendered product QA, and
no-skip evidence into one fresh real-route rehearsal run. If the route is truly
ready, render a rehearsal candidate and verify it. If it is not ready, stop at
the first real blocker with enough evidence to guide the next high-leverage
work.

## Background Source

Recent proof established:

- `tools/run_graduation_product_route.py` records `pipeline_execution_trace.json`.
- `tools/rendered_product_qa.py` runs before `tools/no_skip_execution_trace.py`
  when a rendered candidate exists.
- controlled fixtures can pass the harness path, but they are not real route
  evidence.

The product-level objective is to prevent graduation render rehearsals from
skipping product-route, visual, effect, music/subtitle, rendered QA, and
no-skip evidence.

## Owner Zone

The worker may edit only:

- `docs/construction-guides/work-orders/2026-07-08-real-graduation-route-harness-to-render-rehearsal-report.md`
- `.tmp/real_graduation_route_harness_to_render_rehearsal_*`

If and only if the real-route rehearsal exposes a harness or rendered-QA bug,
the worker may also edit:

- `tools/run_graduation_product_route.py`
- `tools/rendered_product_qa.py`
- `video_pipeline_core/graduation_product_route_runner.py`
- `video_pipeline_core/rendered_product_qa.py`
- `tests/test_graduation_product_route_runner.py`
- `tests/test_rendered_product_qa.py`

## Forbidden Zone

Read-only:

- `tools/pipeline_home.py`
- `tools/film_canon_route.py`
- `tools/film_canon_readiness.py`
- `tools/write_product_route_review_decision.py`
- `tools/visual_selection_gate.py`
- `tools/write_visual_selection_review.py`
- `tools/no_skip_execution_trace.py`
- `tools/write_delivery_gate_report.py`
- `video_pipeline_core/delivery_gate.py`
- `video_pipeline_core/no_skip_execution_trace.py`
- `docs/branch-contract-registry.json` unless a verified wrapper bug requires
  registry wording only
- `Downloads/`
- `deliveries/`
- existing `.tmp/` runs
- `.env`, `.venv*`, reference repos, provider runtimes

## Required Pieces

1. Real evidence inventory
   - Read-only inspect the relevant prior outputs:
     - `.tmp/product_route_review_writer_20260707-061959/graduation_approved`
     - `.tmp/shot_level_material_proof_completion_20260708-080727`
     - `.tmp/effect_factory_integration_completion_20260708-154117`
     - `.tmp/reference_aligned_script_copyedit_20260708-171900`
     - `.tmp/graduation_v5_content_verify_effect_montage_20260707-200659/run`
     - `.tmp/real_graduation_production_candidate_v1_20260707-062900/run`
   - Build `real_route_evidence_inventory.json` in this round's output root.
   - Classify every source artifact as real-route evidence, fixture-only,
     copied prior evidence, missing, or not applicable.

2. Fresh route run assembly
   - Create a fresh run under
     `.tmp/real_graduation_route_harness_to_render_rehearsal_*`.
   - Copy only evidence artifacts needed to run the harness; preserve source
     paths/provenance in `real_route_evidence_manifest.json`.
   - Do not mutate prior runs.
   - Do not write `story_human_review_decision.json`,
     `human_transcript_review_decision.json`, or legal/music approval.

3. Fill only mechanical missing artifacts
   - If a required harness artifact is missing but can be produced by an
     existing repo tool without product judgment, run that tool.
   - If the missing artifact requires human/product/legal/story judgment, stop
     and classify it; do not self-approve.
   - If an artifact is only a fixture or tiny proof, do not use it as real-route
     evidence.

4. Harness no-render pass
   - Run `tools/run_graduation_product_route.py --mode no-render` against the
     fresh real-route run.
   - Required result: trace must get past `pipeline_home` and must either
     reach `ready_for_render_rehearsal` or stop at a real, named blocker.

5. Render rehearsal only if gated
   - If no-render result is `ready_for_render_rehearsal` and a real render
     handoff exists, render a rehearsal candidate using existing route-approved
     inputs.
   - If render cannot be done without inventing creative/story/legal approval,
     stop before render.
   - Any rendered candidate must be rehearsal-only, not final delivery.

6. Rendered QA and no-skip
   - If a rendered candidate exists, run `tools/rendered_product_qa.py`.
   - Then run `tools/no_skip_execution_trace.py`.
   - Verify `pipeline_execution_trace.json` records
     `rendered_product_qa` before `no_skip_execution_trace`.
   - Do not run delivery gate unless the work order reaches a real rendered
     candidate with no-skip pass; even then, report it as technical only.

7. Product-level review packet
   - Write `real_route_rehearsal_review_packet.md` summarizing:
     - route evidence used;
     - stop gate or rendered candidate path;
     - trace depth and stage order;
     - rendered QA/no-skip status;
     - remaining human/product/legal/story review needs.

## Acceptance Commands

Use only:

```powershell
C:\Users\user\miniconda3\python.exe
```

No bare `python` and no `pytest`.

Always run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace
```

Expected exit code: `0`.

If harness/QA code changes, also run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace tests.test_graduation_film_blueprint_catalog tests.test_pipeline_home
```

Expected exit code: `0`.

Run the no-render harness:

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run REAL_ROUTE_RUN --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --mode no-render --out-dir NO_RENDER_OUT --json
```

Expected process exit code: `0`. Truth is in the JSON result and trace.

If a rendered rehearsal candidate is created, run:

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run REAL_ROUTE_RUN --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --mode render-rehearsal --out-dir RENDER_OUT --json
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run REAL_ROUTE_RUN --out-dir RENDER_OUT --json
C:\Users\user\miniconda3\python.exe tools\no_skip_execution_trace.py --run RENDER_OUT --out-dir RENDER_OUT --json
```

Expected process exit code: `0` for artifact generation; truth is in generated
JSON.

Run:

```powershell
git diff --check
```

Expected exit code: `0`; existing CRLF warnings may appear, but no new
whitespace errors.

Final artifact check with `C:\Users\user\miniconda3\python.exe` must verify:

- fresh output root exists.
- `real_route_evidence_inventory.json` exists.
- `real_route_evidence_manifest.json` exists.
- no-render harness trace exists and gets past `pipeline_home`.
- every trace stage has owner/status/evidence.
- if rendered candidate exists, rendered QA exists before no-skip.
- copied/fixture-only artifacts are not classified as real-route proof.
- no `story_human_review_decision.json` or legal approval artifact was written.
- prior `.tmp` runs and Downloads were not modified.
- generated JSON/Markdown decode as UTF-8 and contain no `\ufffd` or suspicious
  repeated `????`.

## Stop-Loss Limits

Stop and report rather than bypass when:

- real route evidence is missing for product-route approval, shot proof, visual
  review, effect handoff, music/subtitle profile, or render handoff;
- evidence is only fixture/tiny proof and not a real route artifact;
- a required decision belongs to the human/product/legal/story owner;
- no-render harness stops at a real blocker;
- render rehearsal would require inventing creative or legal approval;
- rendered QA or no-skip fails for a valid reason;
- fixing would require modifying forbidden tools/gates/prior runs.

Stop-loss is useful output. Do not turn it into another narrow branch task
unless the blocker is local and blocks product-level done-evidence.

## Delegated Decisions

- The worker may choose which prior real artifacts to copy into the fresh run if
  provenance is recorded and prior runs remain unmodified.
- The worker may decide whether a mechanical missing artifact can be regenerated
  by existing tools; any human/product/legal/story decision must remain blocked.
- The worker may render a rehearsal only if the harness and evidence manifest
  justify it.

## Final Report Requirements

Write:

`docs/construction-guides/work-orders/2026-07-08-real-graduation-route-harness-to-render-rehearsal-report.md`

The report and chat final output must start with:

`[WORKER REPORT - REVIEW MODE]`

Include:

- Summary.
- Files changed.
- Artifacts created or updated.
- Commands / exit codes.
- Acceptance results.
- Evidence inventory summary.
- No-render harness trace depth and stop/pass result.
- Render rehearsal path if reached.
- Rendered QA/no-skip status if reached.
- Blockers / stop-loss.
- Deviations.
- Next recommended work, advisory only.
- A section titled `Final output prompt` for the next manager/worker. It must
  frame the report as unverified evidence, require verification of
  claims/artifacts, keep the product-level objective visible, classify blockers,
  respect scope/stop-loss, and align next steps with product-level
  done-evidence.
