# Work Order — Canon 67 39s Wave R L0–L5 Integrated Render

Date: 2026-07-12
Status: ready for execution
Execution shape: one sequential long-running worker; final owner gate only

## 1. Goal And Authority

Produce one 39.34-second internal-review candidate that carries the same continuous supervisor speech through:

```text
L0 evidence-backed selects
→ L1 picture composition
→ L2 documentary lower third
→ L3 preview-only ducked music
→ L4 owner-approved subtitles
→ L5 fresh rendered review
```

Construction basis, in order:

1. `AGENTS.md`
2. `skills/pipeline-boundary.md`
3. `skills/editing-loop-director.md`
4. `docs/superpowers/specs/2026-07-11-canon67-39s-l0-l5-integrated-loop-design.md`
5. this work order
6. `.tmp/editing_loop_39s_integrated_campaign/wave_p/human_transcript_review_decision.json`

Owner transcript verdict is valid and narrow:

- artifact SHA-256: `5D40C6ED1555FE9E08E51FA398295FEF16F28496EFA76E671287FF1EFC5DC046`
- `cue04`: `大家終於活了下來`
- `cue11`: `不斷呵護、不斷地生根、深耕`
- all other cues use the integrator proposal;
- `cue12` ends at `39.34s`;
- transcript approval is not creative approval or delivery approval.

The user has already approved the 39-second design, the restrained lower-third direction, internal-preview music use, and default agent authorization for reversible selection/composition decisions so the run does not deadlock at every intermediate gate. Record that delegation verbatim in L0/L1 provenance. It does not authorize final taste, rights, delivery, threshold changes, or source invention.

## 2. Fixed Inputs

| Input | Required value |
| --- | --- |
| capability baseline | HEAD is `9843d256` or a descendant containing it |
| source media | `C:/Users/user/Downloads/微電影素材/_整理後/主任勉勵/IMG_2145.MOV` |
| source SHA-256 | `85BAEAFCE7D3D7FBEB56C1A354B9EDAF2EE500AB4285BF56893B906C49F9CFCB` |
| speech window | `0.00–39.34s` continuous |
| owner decision | `.tmp/editing_loop_39s_integrated_campaign/wave_p/human_transcript_review_decision.json` |
| owner decision SHA-256 | `5D40C6ED1555FE9E08E51FA398295FEF16F28496EFA76E671287FF1EFC5DC046` |
| reviewed draft SHA-256 | `3DBFCB115540C49BFAD3A6DECE0ECD5E346C74F6B0E7580B7047BA3A2632F266` |
| prior repaired 22s picture | `.tmp/editing_loop_certification_campaign/interview/picture_trial/picture_trial_repaired.mp4` |
| prior repaired 22s picture SHA-256 | `F2BC84A1A397133F6532989E7927A686DD0DAB4619DA14815C9E339FCB80DD4D` |
| internal-preview BGM SHA-256 | `3B4BAA4B50E6949AF2D596E40FB9E16886C648D82E5FF524FFF32265DFFC503A` |
| Drive review parent | `1dCNkMOYtxUlJraumLPY8-ZIB7aoJX-fb` |
| Wave P Drive folder | `1tstjWGr9_KUWFFSIpKfjUvezwitOwklq` |

Re-hash every fixed input before work. Stop on drift.

## 3. Owner Zone

The worker may modify only:

- compiler closure:
  - `video_pipeline_core/human_transcript_review_decision.py`
  - `tools/write_human_transcript_review_decision.py`
  - `tests/test_write_human_transcript_review_decision.py`
- Wave R outputs:
  - `.tmp/editing_loop_39s_integrated_campaign/wave_r/**`
  - `.tmp/editing_loop_39s_integrated_campaign/campaign_status.md`
- report:
  - `.tmp/editing_loop_39s_integrated_campaign/wave_r/wave_r_worker_report.md`
- one new Google Drive review subfolder under the configured parent, only after a reviewable candidate and packet exist.

The compiler closure may be one scoped commit after RED→GREEN and focused regression. Stage only those three code/test paths.

## 4. Forbidden And Read-Only Zone

- `.tmp/editing_loop_39s_integrated_campaign/wave_p/**` is frozen read-only input.
- `.tmp/editing_loop_certification_campaign/**` and all prior candidates/closures are read-only.
- raw Downloads media is read-only.
- all other production code, tools, tests, Skills, Product Spec, registries, dictionaries, INDEX/HANDOFF/RUNBOOK, route runners and orchestrators are forbidden.
- reference exports and `66期學長音樂檔/**` may not enter picture/audio assets.
- no private renderer, private mixer, run-local subtitle generator, CapCut automation, dependency install, push, reset, cleanup or unrelated staging.
- never set `human_creative_approval=true` or `final_delivery_claimed=true`.

## 5. Common Evidence Contract

Every L0–L5 record carries:

```json
{
  "proposal_by": "agent",
  "verdict_by": "owner | owner_delegated_agent_decide | pending_owner_final",
  "delegation_scope": "verbatim bounded authority",
  "evidence_refs": ["path#time_range|stable_id|check_id"],
  "applied_diff": "exact stable IDs/layer change",
  "carry_forward": ["facts and constraints for the next loop"]
}
```

Record owner-verdict count, phase minutes and missing-control findings. Objective PASS, agent judgment and owner taste remain separate.

## 6. Phase C — Approved Decision To SRT Compiler Closure

The verified gap is narrow: the v2 writer can bind/validate approved cues but no public capability writes those cues to SRT. Do not enter Wave R by hand-writing SRT.

Use TDD:

1. Add a failing test for an opt-in public writer path that writes `subtitles.srt` solely from a valid v2 human-approved decision.
2. Add RED coverage for legacy/v1 rejection, exact cue order/text/timing, UTF-8 Chinese, and timestamp carry at a minute boundary (`59.9996s → 00:01:00,000`, never `00:00:60,000`).
3. Implement the smallest helper in the existing human transcript decision module and expose it through the existing CLI, for example `--write-approved-srt`. Do not create a new module, schema, route or generic subtitle engine.
4. Legacy CLI behavior without the flag remains unchanged.
5. Run RED, implement minimum GREEN, then run:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_write_human_transcript_review_decision tests.test_source_speech_transcript_repair tests.test_source_speech_subtitle_qa tests.test_caption_audit -v
git diff --check
```

Expected exits after GREEN: `0`. Commit only the three owner-zone code/test files. Full suite remains deferred until Phase R6.

## 7. Phase R0 — Freeze And Copy Inputs

Create `.tmp/editing_loop_39s_integrated_campaign/wave_r/` and copy—not move—the owner decision and required historical inputs into an input freeze. Record original and copied hashes, current HEAD, dirty tree and reference exclusions. Preserve Wave P and every historical hash.

## 8. Phase R1 — L0 Selects And L1 Picture

The agent is delegated to decide reversible internal-preview selections inside these fixed story beats:

| Time | Required semantic function |
| ---: | --- |
| 19.34–22.34 | 回首剛進中心 |
| 22.34–26.34 | 忐忑不安／初學 |
| 26.34–29.34 | 小樹苗／被帶領 |
| 29.34–32.34 | 師長手把手照顧 |
| 32.34–36.34 | 呵護、生根、深耕／重複訓練 |
| 36.34–39.34 | 集體成果／大樹收束 |

Rules:

- inspect actual pixels/time strips; never select by filename or catalog order;
- carry relative path, SHA-256, source window, observed content, assigned story function, direct-story evidence, reason and blind spots;
- preserve the accepted direction of `0.00–19.34s`; explain every overlap delta from the prior 22s picture plan;
- supervisor source audio remains continuous `0.00–39.34s` and is never replaced by cutaway audio;
- keep talking-head anchors at opening, the 19.34s semantic turn and closing; total cutaway coverage must remain `≤0.60` unless a measured continuity reason proves a smaller value is impossible;
- use existing public rough-cut/edit-decision compile and render surfaces only.

Produce a 39.34s picture-only candidate, semantic diff, source-speech continuity evidence, contact sheet and dense strips. The delegated internal picture decision is provisional; final taste remains owner-gated at R6.

## 9. Phase R2 — L2 Effect Factory

Use `video-effect-factory` with the already-approved fixed contract:

- effect role: `speaker_segment_opening / lower_third`;
- story function: identify the segment as `主任勉勵` without interrupting footage;
- backend: existing ffmpeg/light-effect or motion-graphics capability; no Remotion;
- lifecycle: approximately `0.60–3.20s`;
- style: lower-left safe area, white text, warm-yellow fine line, restrained 8–12-frame slide/fade;
- negative rules: no fullscreen card, particles, glare, bounce, face obstruction, subtitle collision or unverified name/title.

Write `effect_design_map.json`, `effect_contract.json`, actual render evidence, `effect_review.json` and `effect_handoff.json`. The factory must not own final.mp4; V Pipeline performs final assembly. Verify lifecycle, exact text, safe area and non-collision with cue01.

## 10. Phase R3 — L3 Original Speech And Preview-Only Mix

Reuse the accepted public audio-plan/mix/assembly path and the frozen internal-preview BGM. Preserve:

```text
preview_only=true
delivery_allowed=false
music_use_basis.status=pipeline_default_internal_preview
```

Requirements:

- original speech is continuous and dominant for all 39.34s;
- BGM ducks under speech using measurable gain/loudness evidence;
- cutaway source audio never leaks into the mix;
- picture/effect hashes are unchanged;
- audio handoff accepts internal preview while delivery gate rejects public delivery for the expected preview-only reason.

Produce a listening candidate and objective audio evidence, but continue without a separate owner stop under the approved internal-preview delegation. Final listening remains part of R6.

## 11. Phase R4 — L4 Owner-Approved Subtitles

1. Use only the frozen v2 owner decision; do not read ASR suggestions as text truth.
2. Generate `subtitles.srt` with the public compiler from Phase C.
3. Write `source_speech_subtitle_evidence.json` with the exact source binding, all 12 approved cues, `subtitle_source=human_approved`, `human_transcript_present=true`, and the owner decision path/hash.
4. Run:

```powershell
C:/Users/user/miniconda3/python.exe video_tools.py caption-audit --srt <run>/subtitles.srt --out <run>/caption_audit.json
C:/Users/user/miniconda3/python.exe tools/source_speech_subtitle_qa.py --run <run> --require-approved-text-binding --strict-exit --json
C:/Users/user/miniconda3/python.exe tools/subtitle_voiceover_handoff_accept.py --contract <run>/subtitle_voiceover_contract.json --caption-audit <run>/caption_audit.json --subtitles <run>/subtitles.srt --out-dir <run> --json
```

5. Burn/assemble subtitles through the existing public V Pipeline surface.
6. Prove exact approved-text equality, timing equality, 12/12 coverage, Traditional Chinese readability, no U+FFFD or repeated literal question marks, no lower-third collision, unchanged decoded-audio MD5 and protected picture/effect semantics.

## 12. Phase R5 — Same-Candidate Integration

The review candidate must contain all four layers together:

- picture from R1;
- lower third from R2;
- original speech plus preview-only ducked BGM from R3;
- owner-approved subtitles from R4.

Use a public edit-decision/contract-run render path. Do not concatenate separately rendered loop outputs and do not handcraft final assembly. Produce layer-by-layer semantic diff and prove the candidate is exactly `39.34s` within one frame, with one video and one audio stream.

## 13. Phase R6 — Fresh L5, Full Regression, Drive Handoff

Run fresh—not copied—evidence on the same integrated candidate:

```powershell
C:/Users/user/miniconda3/python.exe tools/rendered_product_qa.py --run <run> --out-dir <l5>/rendered_qa --json
C:/Users/user/miniconda3/python.exe video_tools.py final-product-verify <candidate> --out-dir <l5>/final_verify --samples 20
C:/Users/user/miniconda3/python.exe video_tools.py perception-field-check <candidate> --out <l5>/perception
```

Also run applicable stream/duration, black-frame, source-speech continuity, audio scope/loudness, caption readability/equality, effect lifecycle and protected-hash checks. Beat alignment is `not_applicable` for this dialogue-led slice.

Read the complete low-density wall and dense strips around lower-third, each subtitle uncertainty window, every picture cut, and the final 36.90–39.34s landing. Create an L5 findings packet with objective/taste separation and proposed target LOOP; do not auto-edit findings.

After all focused candidate checks are green, run the full suite once, last:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest discover -s tests
git diff --check
```

Upload the integrated MP4, dynamic/full-length review media, contact sheet, owner-approved transcript, L5 packet, worker report and a manifest to one new Drive review folder. The manifest must record local hashes plus observed Drive IDs, URLs, names and sizes. Verify the folder by connector read-back.

Stop at:

`WAITING_OWNER_39S_L0_L5_FINAL_VERDICT`

Do not claim creative approval or delivery.

## 14. Stop-Loss

- One LOCAL correction per failure class; recurrence is STRUCTURAL and stops the affected phase at the last green state.
- Stop on fixed-input drift, invalid owner decision, missing direct story evidence, reference contamination, speech discontinuity, rights ambiguity, objective QA failure, required out-of-zone code, or inability to use a public assembly surface.
- Do not relax thresholds, fabricate text/material truth, copy old PASS reports, silently drop a layer, or treat process exit as product acceptance.
- A production gap outside Phase C writes one exact `factory_gap_*.json`; no workaround is authorized.

## 15. Required Report And Machine-Checkable Closure

Write `.tmp/editing_loop_39s_integrated_campaign/wave_r/wave_r_worker_report.md` and update campaign status with:

- exact final state and PASS/FAIL/UNKNOWN for C and L0–L5;
- commits, every command/exit, fixed/final hashes and dirty tree;
- all six-field loop records and telemetry;
- verbatim owner transcript verdict and decision hash;
- delegated L0/L1 decisions with evidence coordinates;
- deviations, LOCAL repairs, skipped work, blind spots and blockers;
- full-suite result and Drive read-back IDs/URLs/sizes;
- `human_creative_approval=false` and `final_delivery_claimed=false`.

The worker may not report the final wait state unless all checks below pass:

```powershell
if (!(Test-Path '.tmp/editing_loop_39s_integrated_campaign/wave_r/wave_r_worker_report.md')) { throw 'missing worker report' }
if (!(Test-Path '.tmp/editing_loop_39s_integrated_campaign/wave_r/l5')) { throw 'missing fresh L5 evidence' }
if (!(Test-Path '.tmp/editing_loop_39s_integrated_campaign/wave_r/review_packet_manifest.json')) { throw 'missing review packet manifest' }
```
