# 2026-07-04 Mini Stress Probe Supervisor Report

## Scope

The user approved additional pressure tests after the clone/storybook guide verification. I supervised six `gpt-5.4-mini` subagents. Each subagent was instructed not to edit repository files and not to commit. Run products were left under `runs/`.

Dispatch used the existing mini-agent supervision rule: the supervisor spot-checks reported commands and upgrades any judgment-sensitive or inconsistent result instead of accepting the mini report at face value.

## Subagents

| Probe | Subagent | Focus | Primary evidence |
| --- | --- | --- | --- |
| Stress-P | Mendel | Stock/provider truth path | `runs/stress_provider_stock_20260704_master_report.json` |
| Stress-T | Dirac | Target length parser boundaries | `runs/stress_duration_20260704_target_length_stress_v2/summary.json` |
| Stress-Fmt | Dalton | Aspect ratio / format boundaries | `runs/stress_format_20260704_summary.json` |
| Stress-M | Darwin | Material intake boundary cases | `runs/stress_material_20260704_boundary_probe/stress_material_boundary_probe_report.json` |
| Stress-R | Euler | Resume/rerun behavior with stale artifacts | `runs/stress_resume_rerun_20260704_001/case_a` |
| Stress-SB | Aristotle | Storybook stock/provider rerun | `runs/stress_storybook_provider_20260704_001/provider_probe_report.json` |

## Supervisor Spot Checks

- Re-ran `tools/pipeline_home.py --run runs/stress_resume_rerun_20260704_001/case_a --json`; it returned `WAITING` at `stage0_video_intent`, reading `video_intent.json`, so stale downstream artifacts did not silently complete the run.
- Parsed the material boundary report and confirmed missing, empty, and too-small material folders fail closed, while corrupt `.mp4` files are silently accepted into later material planning.
- Checked the storybook provider report and confirmed the Pexels key was present, live Pexels search/download calls occurred, and the stock-story smoke still stalled at `repair_artifact_manifest_or_regenerate_handoff`.
- Checked provider stress artifacts and corrected the mini summary: the master report labels cases as `true_provider` but `live_provider_result=false` / `fail_closed=true`; however `stock_download.mp4` exists for the normal and multi-query cases at 8,381,180 and 9,252,536 bytes. This is an internal probe/reporting inconsistency, not a clean pass.

## Findings

### Provider / Stock

- Live provider access is real. The probes used Pexels search results, and Storybook provider rerun downloaded two Pexels files.
- The provider stress master report is internally inconsistent: normal and multi-query cases created downloaded `stock_download.mp4` files, but the summary still marked `live_provider_result=false`, `fail_closed=true`, and `stop_point=provider/search error or partial outcome`.
- Hard/odd query cases still returned Pexels candidates, which means "hard query" is not enough by itself to prove honest no-result behavior. The stock honesty layer must evaluate semantic fit, not only provider result count.

### Storybook Stock Rerun

- Result: stalled, not a deliverable storybook video.
- `provider_probe_report.json` shows live provider truth and cached/local smoke truth are separate. The smoke path uses a fixture/cached route and placeholder `final.mp4`; it does not prove full live provider ingestion.
- `pipeline_home` stopped at `repair_artifact_manifest_or_regenerate_handoff` because `artifact_manifest.json` pointed to missing `audio_build_handoff.json` evidence.
- `spec_review` and `contract_dry_build` both reported missing `material_coverage_map.json`.

### Target Length

- `10 minutes` and `30 minutes` were accepted with `target_sec=600.0` and `target_sec=1800.0`.
- `5 hours` failed closed, but for the wrong reason: it was parsed as `target_sec=5.0`, then blocked by a target length mismatch against 18,000 seconds.
- Enforcement note: Stress-T/Dirac v2 had `stats.enforce_target_length=true`, so the mismatch became blocking; this resolves the apparent contradiction with Mini-F, whose earlier boundary artifact had `enforce_target_length=false` and therefore reported `ready_for_build=true`.
- The Chinese duration case (`case4_zh_5h`, intended as a five-hour phrase) and invalid `banana` were treated as missing/unparsable target length warnings while `ready_for_build=true`. That is a silent-accept gap.
- The duration summary artifact itself has encoding damage around Chinese text, which made `ConvertFrom-Json` fail during supervisor spot check.

### Format / Aspect Ratio

- `16:9`, `9:16`, and `1:1` are accepted and routed to structure-first.
- `32:9` was marked PASS by the mini because the current system accepts the string. Supervisor classification: this is a policy gap unless ultrawide is explicitly supported.
- `cinemascope but vertical` and `abc:def` are silently accepted by creator-profile / video-intent routing and only fail the probe expectation. Aspect ratio validation is missing.

### Material Intake

- Missing folder, empty folder, and one-asset folder fail closed at `stage2_3_material_wall_to_review_apply`.
- Chinese folder and filenames pass through without crash.
- Corrupt `.mp4` assets are silently accepted into `project_material_map.json` and `rough_cut_plan.json`. Mixed good assets plus one corrupt video also silently accepts the bad file.
- The material gate needs actual media validation before map/rough-cut planning, not just extension/path acceptance.

### Resume / Rerun

- `pipeline_home.py` safely re-evaluates current artifacts and does not let stale `final.mp4`, `timeline_build.json`, or `material_delta.json` force a complete state.
- Caveat: the serialized `state.json` remained at the prior cursor in the probe; the safe behavior came from `pipeline_home.py` reading newer `video_intent.json`, not from state mutation. This is acceptable for routing but should be documented as the intended authority order.

## Mini-Agent Assessment

- Mendel found useful provider evidence but over-stated the pass condition. Supervisor had to correct the report/artifact inconsistency.
- Dirac exposed the highest-value parser gaps and correctly classified the invalid target length silent accepts.
- Dalton executed the format sweep, but treated `32:9` as clean PASS without product-policy judgment.
- Darwin produced strong material boundary coverage and correctly identified corrupt media silent accepts.
- Euler produced a clean resume/rerun trace; supervisor spot check confirmed it.
- Aristotle separated live provider calls from cached smoke behavior and captured the artifact-manifest stall correctly.

## Product Data

`gpt-5.4-mini` is useful for broad probe execution, but it is not independently sufficient for this pipeline's judgment-sensitive gates. It needs supervisor review for:

- distinguishing real provider ingestion from cached/fixture smoke success;
- interpreting fail-closed versus wrong-reason failures;
- recognizing policy gaps such as unsupported aspect ratios;
- reconciling contradictory run artifacts and summary labels.

Recommended follow-up repairs:

1. Add strict target length parsing and reject/ask-followup behavior for hours, Chinese duration forms, and invalid strings.
2. Add aspect ratio validation before creator-profile or video-intent can route the run.
3. Add media integrity validation before corrupt video files can enter material maps or rough cuts.
4. Fix stock-story smoke artifacts so placeholder `final.mp4` cannot masquerade as delivery, and ensure required audio handoff evidence is either produced or explicitly waived.
5. Document `pipeline_home.py` authority order for reruns: current intent/artifacts override stale serialized cursor state.
