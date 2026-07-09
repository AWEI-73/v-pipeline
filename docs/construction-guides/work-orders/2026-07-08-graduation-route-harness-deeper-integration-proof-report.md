[WORKER REPORT - REVIEW MODE]

## Summary

Executed the deeper integration proof for the existing Graduation Product Route
Execution Harness. No harness or rendered-product QA code changes were needed.

The prior harness smoke was verified as shallow: it only reached
`pipeline_home` and stopped at `UNKNOWN`. This round built fresh, minimal
fixtures under the proof output root and showed:

- no-render proof got past `pipeline_home` and stopped truthfully at missing
  `shot_level_material_proof_plan.json`;
- render-rehearsal proof reached `rendered_product_qa` and then
  `no_skip_execution_trace`;
- `rendered_product_qa` appears before `no_skip_execution_trace` in
  `pipeline_execution_trace.json`;
- no-skip still blocks unknown gate evidence.

This is an integration proof only. It is not delivery approval, not render
quality approval, and not human story approval.

## Files Changed

- `docs/construction-guides/work-orders/2026-07-08-graduation-route-harness-deeper-integration-proof-report.md`
- `.tmp/graduation_route_harness_deeper_integration_proof_20260708-233705/*`

No harness/QA source code or tests were changed in this round.

## Artifacts Created Or Updated

Output root:

`C:\Users\user\Desktop\video_pipeline\.tmp\graduation_route_harness_deeper_integration_proof_20260708-233705`

Key artifacts:

- `prior_route_artifact_inspection.json`
- `tiny_mp4_generation.json`
- `no_render_run/`
- `no_render_out/pipeline_execution_trace.json`
- `no_render_out/graduation_product_route_harness_result.json`
- `render_run/final.mp4`
- `render_out/rendered_product_qa.json`
- `render_out/no_skip_contract_decision.json`
- `render_out/pipeline_execution_trace.json`
- `render_out/graduation_product_route_harness_result.json`
- `no_skip_unknown_gate_run/`
- `no_skip_unknown_gate_out/no_skip_contract_decision.json`
- `final_artifact_check.json`

Preferred prior folder inspected read-only:

`.tmp/product_route_review_writer_20260707-061959/graduation_approved`

It existed and was not modified by this proof.

## Commands / Exit Codes

Created fresh proof fixtures and tiny local MP4:

```powershell
C:\Users\user\miniconda3\python.exe -c "<fixture generation script>"
```

Exit code: `0`.

No-render harness proof:

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run .tmp\graduation_route_harness_deeper_integration_proof_20260708-233705\no_render_run --source-root C:\Users\user\Downloads\微電影素材\_整理後 --mode no-render --out-dir .tmp\graduation_route_harness_deeper_integration_proof_20260708-233705\no_render_out --json
```

Exit code: `0`.

Result:

- `pass=false`
- `stop_gate=shot_level_material_proof`
- `stop_reason=missing shot_level_material_proof_plan.json`

Render-rehearsal harness proof:

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_product_route.py --run .tmp\graduation_route_harness_deeper_integration_proof_20260708-233705\render_run --source-root C:\Users\user\Downloads\微電影素材\_整理後 --mode render-rehearsal --out-dir .tmp\graduation_route_harness_deeper_integration_proof_20260708-233705\render_out --json
```

Exit code: `0`.

Result:

- `pass=true`
- `stop_gate=null`
- `next_action=route_trace_complete`

No-skip unknown gate proof:

```powershell
C:\Users\user\miniconda3\python.exe tools\no_skip_execution_trace.py --run .tmp\graduation_route_harness_deeper_integration_proof_20260708-233705\no_skip_unknown_gate_run --out-dir .tmp\graduation_route_harness_deeper_integration_proof_20260708-233705\no_skip_unknown_gate_out --json
```

Exit code: `0` for artifact generation.

Decision artifact:

- `no_skip_contract_decision.pass=false`
- blocking rule: `unknown_gate_authenticity`
- blocked artifact: `visual_selection_gate.json`

Focused acceptance:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_graduation_product_route_runner tests.test_rendered_product_qa tests.test_no_skip_execution_trace
```

Exit code: `0`; `Ran 13 tests ... OK`.

Final artifact check:

```powershell
C:\Users\user\miniconda3\python.exe -c "<final artifact check script>"
```

Exit code: `0`; status: `ok`.

```powershell
git diff --check
```

Exit code: `0`; existing CRLF warnings only, no whitespace errors.

## Acceptance Results

PASS.

The required harness proofs ran with the pinned interpreter. The final artifact
check verified:

- no-render proof trace exists;
- no-render proof trace depth is greater than one;
- no-render proof got past `pipeline_home`;
- render-rehearsal proof trace exists;
- when both stages appear, `rendered_product_qa` appears before
  `no_skip_execution_trace`;
- no `story_human_review_decision.json` was written;
- the inspected prior `.tmp` route folder was not modified after this proof
  root was created;
- generated JSON/Markdown decoded as UTF-8 with no replacement characters or
  repeated question-mark mojibake pattern.

## No-Render Proof Root And Trace Depth

Root:

`.tmp/graduation_route_harness_deeper_integration_proof_20260708-233705/no_render_out`

Trace depth: `5`

Stages:

1. `pipeline_home`
2. `film_canon_route_artifact_check`
3. `film_canon_readiness`
4. `product_route_review_decision`
5. `shot_level_material_proof`

Stop gate:

- `shot_level_material_proof`
- reason: `missing shot_level_material_proof_plan.json`

This proves the harness got beyond the prior shallow `pipeline_home UNKNOWN`
case and stopped at the next missing render-facing proof artifact.

## Render-Rehearsal Proof Root And Stage Ordering

Root:

`.tmp/graduation_route_harness_deeper_integration_proof_20260708-233705/render_out`

Trace depth: `11`

Stages:

1. `pipeline_home`
2. `film_canon_route_artifact_check`
3. `film_canon_readiness`
4. `product_route_review_decision`
5. `shot_level_material_proof`
6. `visual_selection_gate`
7. `effect_handoff`
8. `music_subtitle_profile`
9. `compose_render_handoff`
10. `rendered_product_qa`
11. `no_skip_execution_trace`

Ordering proof:

- `rendered_product_qa` index: `10`
- `no_skip_execution_trace` index: `11`
- rendered QA ran first.

Rendered product QA:

- tiny local MP4 fixture generated inside the output root;
- ffprobe/frame evidence generated by `tools/rendered_product_qa.py`;
- no prior final video was copied for the render proof.

No-skip visibility:

- `render_out/no_skip_contract_decision.json` had `pass=true`;
- gate authenticity classified `rendered_product_qa.json` as
  `pipeline_tool_generated` with source tool `tools/rendered_product_qa.py`.

## No-Skip Blocking Proof

Fixture:

`.tmp/graduation_route_harness_deeper_integration_proof_20260708-233705/no_skip_unknown_gate_run`

Output:

`.tmp/graduation_route_harness_deeper_integration_proof_20260708-233705/no_skip_unknown_gate_out`

Result:

- `no_skip_contract_decision.pass=false`
- blocking rule: `unknown_gate_authenticity`
- artifact: `visual_selection_gate.json`
- message: `canonical gate artifact lacks generated_by/source_tool/trace evidence`

This demonstrates copied/stale/unknown gate evidence remains blocking; the
proof did not relax no-skip semantics.

## Blockers / Stop-Loss

- No-render proof correctly stopped at missing shot-level material proof.
- Render-rehearsal proof did not hit a stop-loss; it completed the harness
  trace path using a local fixture.
- No-skip blocking proof correctly blocked unknown visual-selection gate
  evidence.

No delivery, story, transcript, legal/music, or render quality approval was
claimed.

## Deviations

- A minimal fixture was synthesized under the proof output root instead of
  copying a prior route folder. The preferred prior folder was inspected
  read-only, but the fixture gave tighter control over stage ordering and avoided
  mutating prior runs.
- `state.json` with `next_action=build` was used only in the fresh fixtures to
  let `pipeline_home` return a non-UNKNOWN executable state. This was not used
  to claim route completion.
- The no-skip unknown-gate command exits `0` because it successfully writes its
  audit artifacts; the blocking truth is in `no_skip_contract_decision.pass=false`.

## Next Recommended Work

Use the harness against a real, non-fixture graduation route run that has
human product-route approval, production readiness, shot-level proof,
visual-selection review, effect handoff, and music/subtitle profile artifacts.
That next proof should replace synthetic fixture confidence with real route
evidence before any longer render rehearsal is dispatched.

## Final output prompt

Treat this worker report as unverified evidence. Verify the proof artifacts,
trace depth, stage ordering, command outputs, and no-skip blocking decision
before using it as planning input. Keep the product-level objective visible:
prevent graduation render rehearsals from skipping product-route, visual,
effect, music/subtitle, rendered QA, and no-skip evidence. Classify blockers
separately: the no-render fixture stopped at missing shot-level proof by design,
while the render fixture completed only as a controlled integration proof, not a
real delivery route. Align the next step with product-level done-evidence by
running the harness on a real route run with actual approved route artifacts and
reviewed render-facing evidence before dispatching another production render.
