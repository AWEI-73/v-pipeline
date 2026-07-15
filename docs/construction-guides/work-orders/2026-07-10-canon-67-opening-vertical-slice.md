# Work Order: Canon 67 Opening Vertical Slice

Date: 2026-07-10  
Status: approved for construction; Wave A only

## Goal And Source

Turn the existing graduation-film control plane and disconnected editing parts
into one reproducible, repo-owned vertical path that renders a technically
reviewable 0:00-0:44 opening candidate from real approved source material.

The visible candidate has three timed movements:

1. 0:00-0:11: real footage or photo treatment with a progressive/typewriter
   title overlay.
2. 0:11-0:18: black poetry card with three progressively revealed lines.
3. 0:18-0:44: at least 15 distinct accepted assets cut on the supplied music
   beat grid.

Primary context sources:

- `docs/construction-guides/2026-07-10-canon-67th-film-gap-table.md`
- `docs/construction-guides/work-orders/2026-07-09-real-graduation-render-owner-rehearsal-report.md`
- `.tmp/real_graduation_render_handoff_construction_20260709-005405/run/`

Current real behavior: the prior rehearsal produced a 41-second candidate only
through a run-local `render_owner_execute.py`; rendered QA then stopped on
`title_effect_evidence_missing`. The product route checks a pre-existing
`render_handoff.json` but does not own construction of the composition.

This wave is successful only when the same class of output is produced by
repo-owned code through canonical artifacts, without a generated run-local
Python renderer. It is a technical/creative-review candidate, not delivery.

## Pinned Architecture And Ownership

- Soundtrack Arranger owns music evidence, beat/energy analysis, and audio
  handoff. It does **not** own `render_handoff.json`.
- Main Pipeline owns composition: accepted material and side-branch handoffs
  become `edit_decision_plan.json`, `timeline_build.json`,
  `render_handoff.json`, and the run-local render candidate.
- Verify owns the numeric beat-vs-cut result and existing rendered-product
  gates. Verification code must not silently repair the plan it checks.
- `edit_decision_plan.json` is the canonical composition truth. A renderer may
  support a bounded subset and must fail closed on an unsupported instruction.
- The opening-specific runner may assemble inputs, but graduation-specific
  content or timing must not be embedded in the generic renderer.
- The reference film `67期結訓影片-終.mp4` is observation-only and must never
  be selected as footage for the candidate.

## Owner Zone

The worker may edit only these paths:

- `video_pipeline_core/edit_decision_plan.py`
- `video_pipeline_core/edit_artifacts.py`
- `video_pipeline_core/opening_sequence.py`
- `video_pipeline_core/beat_cut_composer.py` (new)
- `video_pipeline_core/edit_decision_renderer.py` (new)
- `video_pipeline_core/graduation_opening_slice.py` (new)
- `video_pipeline_core/motion_graphics.py`
- `tools/run_graduation_opening_slice.py` (new)
- `tools/verify_beat_cut_alignment.py` (new)
- `examples/graduation_opening_slice_request.json` (new)
- `docs/branch-contract-registry.json`
- `docs/branch-contract-registry.md`
- `video_pipeline_core/graduation_product_route_runner.py`
- `tests/test_compile_edit_decision_plan.py`
- `tests/test_edit_artifacts.py`
- `tests/test_opening_sequence.py`
- `tests/test_motion_graphics.py`
- `tests/test_graduation_product_route_runner.py`
- `tests/test_graduation_route_registry_consistency.py`
- `tests/test_beat_cut_composer.py` (new)
- `tests/test_edit_decision_renderer.py` (new)
- `tests/test_graduation_opening_slice.py` (new)
- `docs/construction-guides/work-orders/2026-07-10-canon-67-opening-vertical-slice-report.md` (new)
- `.tmp/canon_67_opening_slice_*` (fresh outputs only)

## Forbidden Zone

Read-only even if it appears relevant:

- `AGENTS.md`, `RUNBOOK.md`, `video_tools.py`
- `video_pipeline_core/rendered_product_qa.py`
- `video_pipeline_core/title_effect_lifecycle_qa.py`
- `video_pipeline_core/no_skip_execution_trace.py`
- `video_pipeline_core/delivery_gate.py`
- `tools/rendered_product_qa.py`, `tools/no_skip_execution_trace.py`
- `skills/**`, `deliveries/**`, `reference repo/**`, `.env`
- `docs/construction-guides/2026-07-10-canon-67th-film-gap-table.md`
- every existing `.tmp/**` run
- `C:\Users\user\Downloads\微電影素材\_整理後\**`

Existing `.tmp` runs and Downloads are read-only evidence/input. Do not amend
prior artifacts, write into the source tree, run delivery promotion, push,
open a PR, or weaken an existing QA rule. If an owner-zone conflict is found,
stop the affected piece and report it; do not expand scope locally.

## Required Pieces

### Piece 1 - Normalize The Render-Handoff Boundary

First add red coverage for the observed ownership drift, then make these facts
executable:

- remove `render_handoff.json` from Soundtrack Arranger canonical outputs;
- add it to Main Pipeline BUILD/composition outputs;
- the graduation runner's music/subtitle stage must not treat
  `render_handoff.json` as music evidence;
- `compose_render_handoff` remains a distinct later stage and validates an
  `ok=true`, Main-Pipeline-owned handoff rather than mere file existence.

Commit: `Assign render handoff to main composition`

### Piece 2 - Build A Beat-Cut Composer And Numeric Instrument

Add a deterministic composer that accepts an approved material list, a beat
grid, an output window, fps, and minimum distinct-asset count. It emits cuts
with source lineage and exact timeline positions; it does not select by raw
filename outside the accepted catalog.

For the 18-44 second montage:

- at least 15 distinct accepted source assets;
- every internal intended cut boundary is assigned to an actual beat anchor;
- target end is 44 seconds within one frame at the declared fps;
- missing beat coverage, insufficient accepted material, duplicate-only input,
  invalid media duration, or target overflow blocks instead of guessing.

Add a separate verifier that reads the produced timeline and declared beat
grid, writes `beat_cut_alignment_report.json`, and exits non-zero unless 100%
of intended montage boundaries are within one frame.

Commit: `Compose and verify beat aligned cuts`

### Piece 3 - Carry Visible Composition Through Canonical Artifacts

Extend the existing opening/edit-decision/timeline path without inventing a
second composition schema:

- preserve text, treatment, overlay, transition, timing, and lineage fields
  needed by the renderer;
- populate `overlays` and `transitions` when accepted opening instructions are
  present instead of always emitting empty lists;
- represent the black poetry card as an explicit generated/background
  instruction, not as fake source footage;
- support a bounded progressive/typewriter text treatment in the existing
  motion-graphics layer;
- keep unsupported instructions visible and blocking.

The example request contains, as data rather than code constants:

- title: `台電67TH養成班`
- subtitle: `ON THE LAST PAGE`
- poem lines:
  `當風雨掩襲城市的每一道亮光`,
  `總有人逆著風雨疾行`,
  `而今天 我們正在成為他們的路上`
- fps 30, resolution 1920x1080, target duration 44 seconds.

Commit: `Carry opening graphics through edit decisions`

### Piece 4 - Add A Bounded Canonical Renderer

Add a repo-owned renderer that consumes the canonical edit decision/timeline
and accepted audio/effect inputs. For this wave it must support only what the
opening requests: images/video cuts, black generated background, progressive
text overlays, hard cuts, one BGM track, and normalized 1920x1080 output.

It must:

- copy accepted external inputs into a fresh run-local asset store before
  rendering and preserve source provenance;
- write `timeline_build.json`, `render_handoff.json`, and a command/input
  manifest before `final.mp4`;
- render `final.mp4` with video and audio streams;
- never generate a run-local Python execution script;
- keep `final_delivery_claimed=false` and reject unsupported composition data.

Commit: `Render bounded edit decisions to final mp4`

### Piece 5 - Prove The Real 0-44 Second Vertical Slice

Add one repo-owned command:

```text
tools/run_graduation_opening_slice.py
```

It uses the prior accepted catalog and soundtrack evidence as read-only seed,
copies the needed inputs into a fresh owner root, constructs the canonical
artifacts, renders, runs beat verification, extracts rendered title/poem
enter-hold-exit frames, writes the existing lifecycle evidence shape, and runs
rendered-product QA.

The command exits 0 only when all technical gates pass. Its output must include:

- `run/edit_decision_plan.json`
- `run/timeline_build.json`
- `run/render_handoff.json`
- `run/final.mp4`
- `beat_cut_alignment_report.json`
- `rendered_qa/rendered_product_qa.json` with `pass=true`
- title/poem enter-hold-exit frame evidence and a contact sheet
- `opening_slice_acceptance.json`
- `creative_review_packet.md` with `human_creative_approval=false`

The acceptance JSON blocks if duration differs from 44 seconds by more than one
frame, streams are missing, fewer than 15 montage assets are used, a source is
unaccepted, the reference film is used as footage, beat alignment fails,
rendered QA fails, or any required artifact is missing.

Commit: `Prove the real graduation opening slice`

### Piece 6 - Report Without Promoting

Write the report named in the Owner Zone. Do not append it to this work order.
The candidate remains a technical rehearsal pending owner visual judgment.

Commit: `Report canon 67 opening slice evidence`

## Red-First Verification

Before changing behavior, add and run focused tests that fail for these current
facts:

1. Soundtrack claims `render_handoff.json`, and the music stage consumes it.
2. `edit_decision_plan.overlays`/`transitions` cannot carry this opening.
3. No canonical consumer renders the edit decision to a candidate.
4. A timing-only title QA artifact lacks rendered-frame evidence.
5. Misaligned cuts and fewer than 15 distinct montage assets are rejected.

Record the failing command and the relevant assertion/error in the report.

## Acceptance Commands

Run from `C:\Users\user\Desktop\video_pipeline`. Use
`C:\Users\user\miniconda3\python.exe`; do not use bare `python` or `pytest`.

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_beat_cut_composer tests.test_edit_decision_renderer tests.test_graduation_opening_slice tests.test_compile_edit_decision_plan tests.test_edit_artifacts tests.test_opening_sequence tests.test_motion_graphics tests.test_graduation_product_route_runner tests.test_graduation_route_registry_consistency -v
```

Expected exit code: `0`.

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py registry-audit --json
C:\Users\user\miniconda3\python.exe video_tools.py interface-audit
```

Expected exit code: `0` for each command.

```powershell
C:\Users\user\miniconda3\python.exe tools\run_graduation_opening_slice.py --seed-run .tmp\real_graduation_render_handoff_construction_20260709-005405\run --source-root "C:\Users\user\Downloads\微電影素材\_整理後" --request examples\graduation_opening_slice_request.json --out .tmp\canon_67_opening_slice_acceptance --json
```

Expected exit code: `0` and
`.tmp/canon_67_opening_slice_acceptance/opening_slice_acceptance.json` has
`pass=true`, `human_creative_approval=false`, `duration_sec` within one frame
of 44, `montage_distinct_asset_count>=15`, and `final_delivery_claimed=false`.

```powershell
C:\Users\user\miniconda3\python.exe tools\verify_beat_cut_alignment.py --timeline .tmp\canon_67_opening_slice_acceptance\run\timeline_build.json --beats .tmp\canon_67_opening_slice_acceptance\run\soundtrack_probe_report.json --window-start 18 --window-end 44 --fps 30 --out .tmp\canon_67_opening_slice_acceptance\beat_cut_alignment_report.json --json
```

Expected exit code: `0`; report has `pass=true` and
`within_one_frame_ratio=1.0`.

```powershell
ffprobe -v error -show_entries format=duration -show_entries stream=codec_type,codec_name,width,height -of json .tmp\canon_67_opening_slice_acceptance\run\final.mp4
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run .tmp\canon_67_opening_slice_acceptance\run --out-dir .tmp\canon_67_opening_slice_acceptance\rendered_qa --json
```

Expected exit code: `0` for each command; ffprobe shows video and audio.

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py asset-path-audit .tmp\canon_67_opening_slice_acceptance\run --strict --json
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests
git diff --check
```

Expected exit code: `0` for each command.

## Stop-Loss Limits

- At most five implementation commits plus one report commit.
- At most sixteen edited code/test files, excluding the new example, registry docs,
  and report. Stop before exceeding this limit.
- One repair attempt per failure class. If the same class recurs after repair,
  classify LOCAL or STRUCTURAL and stop at the last green commit.
- Stop if a new dependency, registry/schema migration, existing QA relaxation,
  edit outside Owner Zone, source write, license/publication decision, or
  product-taste decision is required.
- If real inputs cannot supply 15 accepted non-reference assets, report the
  exact accepted count and stop; do not lower the threshold or accept new
  material in this wave.
- If the focused suite passes but the real render or rendered QA fails, preserve
  the failed artifact and stop after one bounded repair of that failure class.
- A full-suite failure outside the touched scope is reported, not repaired.

## Delegated Decisions

- Internal function/class names in the three new core modules.
- Whether progressive text is encoded as ASS events or an equivalent existing
  ffmpeg/libass-safe mechanism; no new dependency is allowed.
- Beat subsampling strategy, provided every emitted cut uses a real supplied
  anchor and all pinned timing/count gates pass.
- Exact run-local manifest names beyond the required artifacts.
- Test fixture construction and helper placement inside the named test files.

The worker may not decide ownership, lower thresholds, replace real input with
synthetic acceptance, reinterpret the three segment timings, or claim visual
approval.

## Report Evidence Required

Start the report with `[WORKER REPORT - REVIEW MODE]` and include:

- commits and files changed;
- red-first commands with failure excerpts;
- every acceptance command, exit code, and final tail line;
- output root and all required artifact paths;
- ffprobe duration/stream evidence;
- montage distinct count and beat-alignment metrics;
- rendered QA status and frame/contact-sheet paths;
- source provenance and confirmation that the reference film was not used;
- exact `git status --short`;
- deviations, skips, blockers, and `No deviations` when truly none;
- a concise final-output prompt that treats the report as unverified evidence.
