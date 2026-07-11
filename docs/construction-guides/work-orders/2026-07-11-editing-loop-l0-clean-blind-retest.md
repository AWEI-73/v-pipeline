# Editing Loop L0 Clean-Blind Reproducibility Retest

Status: **READY — FRESH SESSION ONLY**

## 1. Goal

Produce one uncontaminated first-of-kind reproducibility test for the L0
material-immersion and selection procedure.

This work order exists only because the prior L0 shadow run truthfully declared
that its active conversation already contained earlier selection information.
That result remains `UNKNOWN`; it must not be edited, overwritten, or relabeled.

The retest must answer one narrow question:

> Can a fresh agent, without access to prior answers, inspect the raw Canon 67
> material and independently produce an evidence-backed supervisor-interview
> dialogue select plus training cutaway proposal with the same procedural
> quality?

This is not a picture edit, render, owner taste decision, catalog promotion,
or L1–L5 rerun.

## 2. Fresh-Session Requirement

Run this work order only in a completely new TERRA session:

- do not continue, fork, summarize, or import any previous TERRA/Fable/SOL
  conversation;
- paste only the dispatch prompt that names this work order;
- do not paste prior reports, selected IDs, source filenames, hashes, verdicts,
  or candidate descriptions;
- if the worker can recall any specific prior dialogue/cutaway answer before
  inspecting raw evidence, it must declare contamination and stop.

The worker must write `session_context_declaration.json` before inspecting
source media. It must state whether prior conversation or answer details are
available. A value other than a truthful clean declaration makes the final
result `UNKNOWN`.

## 3. Authority And Pre-Seal Read Order

Before the blind seal, read only:

1. `AGENTS.md`
2. this work order — sole construction basis
3. `skills/pipeline-boundary.md`
4. the Entry, Context, L0, authorization, and boundary sections of
   `skills/editing-loop-director.md`
5. the positioning, loop shape, maturity definition, and L0 rows of
   `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
6. `.tmp/graduation_v5_content_verify_effect_montage_20260707-200659/run/source_media_inventory.json`
7. raw source media under
   `C:\Users\user\Downloads\微電影素材\_整理後`

Do not use codebase-memory, Graphify, repo-wide search, prior pilot documents,
decision reports, campaign status, git history prose, or another work order to
learn selection answers before the seal.

Use `superpowers:executing-plans`. Do not spawn subagents; one clean context
must own the entire pre-seal procedure.

## 4. Pre-Seal Forbidden Answer Sources

Before `blind_seal.json` is written, never read semantic contents from:

- `.tmp/editing_loop_certification_campaign/l0/**`
- `.tmp/editing_loop_certification_campaign/interview/**`
- `.tmp/editing_loop_certification_campaign/l3/**`
- `.tmp/editing_loop_certification_campaign/l4/**`
- `.tmp/editing_loop_certification_campaign/consolidated_review/**`
- `.tmp/editing_loop_certification_campaign/integrated_closure/**`, except the
  new Owner Zone in §6
- `.tmp/loop_f1_blind_reproducibility/**`
- `docs/pilots/**`
- prior Canon 67 work orders and worker reports

Existence checks against these roots are also unnecessary and forbidden before
the seal. The worker must not parse them under a "non-semantic" exception.

## 5. Environment

- Repo: `C:\Users\user\Desktop\video_pipeline`
- Python: `C:\Users\user\miniconda3\python.exe`
- Shell: PowerShell
- Raw-source root: `C:\Users\user\Downloads\微電影素材\_整理後`
- Retest root:
  `.tmp/editing_loop_certification_campaign/integrated_closure/l0_clean_blind_retest_v2/`

Do not install dependencies or alter environment configuration.

## 6. Owner Zone

The worker may write only:

`.tmp/editing_loop_certification_campaign/integrated_closure/l0_clean_blind_retest_v2/**`

Everything else is read-only. Do not update global campaign status, Product
Spec, Skill maturity, existing closure artifacts, production code, tools,
tests, registries, raw sources, candidates, plans, or prior reports.

Do not stage, commit, push, upload, clean, reset, or open a PR.

## 7. Selection Need And Rubric

The bounded product need is:

- one continuous supervisor-speech excerpt, preferably 12–25 seconds;
- 4–8 real training/life cutaways that can support that speech visually;
- talking-head continuity must remain possible at the beginning and ending;
- reference exports and prior-period music are never candidate media.

Dialogue proposal criteria:

- clear, continuous source speech and usable audio;
- stable formal speaker composition;
- enough duration for a coherent sentence group;
- exact source interval, hash, evidence coordinates, reason, and blind spots.

Cutaway proposal criteria:

- observed action or cohort content, not filename inference;
- varied semantic roles, framing scale, task, or setting where evidence permits;
- exact source interval, hash, evidence coordinates, reason, and blind spots;
- no selection by catalog order, directory order, or first-N slicing.

The worker chooses the actual sources. This work order intentionally contains no
prior selected source IDs, filenames, time windows, or hashes.

## 8. Phase A — Declare And Log Clean Context

Before reading the inventory or raw-source directory, write:

`session_context_declaration.json`

Minimum fields:

```json
{
  "artifact_role": "editing_loop_l0_clean_session_declaration",
  "fresh_session": true,
  "prior_conversation_available": false,
  "specific_prior_selection_answers_known": false,
  "prompt_included_prior_answers": false,
  "answer_leakage_detected": false
}
```

Also start `preseal_access_log.json`, listing every document, inventory, source
directory, and generated evidence artifact read before the seal. The log is
evidence only, not a new durable journal or schema.

If any declaration is false or uncertain, write the reason and stop at:

`STOPPED_L0_CLEAN_BLIND_CONTEXT_CONTAMINATED`

## 9. Phase B — Independent Material Immersion

1. Read the full source inventory and choose a bounded inspection pool without
   reading prior answer artifacts.
2. Inspect at least three plausible supervisor-speech sources with fresh public
   material matrices/contact sheets and fresh audio probes. ASR remains draft
   evidence and never becomes transcript truth.
3. Inspect 5–8 plausible training/life B-roll sources with fresh public
   `perception-field-check` evidence and indexed walls/strips.
4. Invoke perception one source at a time so a batch timeout cannot hide which
   item completed. One LOCAL retry is allowed only for a tool/command failure;
   do not lower coverage thresholds.
5. Apply EXIF correction to review copies when photos are inspected. Probe
   duration and streams for video.
6. Record rejected alternatives and why evidence did not support selection.
7. Exclude reference films/exports and prior-period music from candidate media.

Coverage proves only that the source was inspected. Semantic role, narrative
fit, and visual diversity remain agent judgment with evidence coordinates.

## 10. Phase C — Proposal And Immutable Blind Seal

Write `proposal.json` containing:

- one dialogue proposal and 4–8 cutaway proposals;
- stable IDs;
- raw-source-relative paths and SHA-256;
- exact source in/out/duration;
- semantic role and selection reason;
- evidence refs with cell/shot/time coordinates;
- rejected alternatives;
- blind spots and explicit reference exclusion;
- the six carried decision fields and telemetry.

Then validate UTF-8/JSON and write `blind_seal.json` containing:

- proposal path and SHA-256;
- session-context declaration path and SHA-256;
- pre-seal access-log path and SHA-256;
- creation time;
- complete declared-unread answer roots;
- `answer_leakage_detected=false` only if truthful;
- `proposal_modified_after_seal=false`.

After the seal, do not modify `proposal.json`, the context declaration, access
log, or seal. Re-hash them at final read-back.

If answer leakage is detected at any time before the seal, preserve evidence
and stop without comparison.

## 11. Phase D — Post-Seal Comparison

Only after a valid seal exists may the worker read exactly this prior-answer
artifact:

`.tmp/editing_loop_certification_campaign/l0/approved_selects_manifest.json`

Do not read the previous contaminated shadow proposal or comparison.

Write `reproducibility_comparison.json` comparing:

- dialogue function and interval shape;
- cutaway semantic roles and diversity;
- source/exclusion truth;
- evidence completeness and blind spots;
- exact source/path/window overlap as descriptive evidence only.

Exact answer identity is not required and must not be used as the sole PASS
criterion. A clean procedure may select a different valid speaker or time
window. Classification remains an integrator decision.

## 12. Acceptance

The worker may report `CLEAN_BLIND_EVIDENCE_READY`, not `CERTIFIED`.

Required evidence:

- clean session declaration;
- complete, permitted pre-seal access log;
- fresh inspection evidence for the bounded pools;
- proposal hash sealed before any prior-answer read;
- no prior-answer path in the pre-seal access log;
- valid post-seal comparison;
- all selected raw paths exist and hashes match;
- no forbidden reference candidate;
- proposal/context/log/seal hashes unchanged at final read-back;
- exact pre/post `git status --short` preserved;
- UTF-8/JSON checks pass;
- `git diff --check` exit 0.

No focused or full unit suite is required because this retest cannot modify
code or tracked docs. Do not run the full suite.

Successful stop state:

`WAITING_INTEGRATOR_L0_CLEAN_BLIND_REVIEW`

Only the integrator may convert the evidence to bounded L0 `CERTIFIED` and
carry it into the L0–L5 closure.

## 13. Stop-Loss

- One LOCAL retry per evidence-generation failure class.
- A repeated class is STRUCTURAL; stop that stream and report it.
- Stop on context contamination, prior-answer read before seal, raw-source
  mutation, missing source truth, reference selection, hash drift, owner-zone
  conflict, or any required production-code/test change.
- Do not fabricate a clean declaration, erase access history, modify the sealed
  proposal, copy prior PASS evidence, or relax a threshold.

## 14. Worker Report

Write `clean_blind_retest_report.md` with:

- exact stop state and PASS/FAIL/UNKNOWN classifications;
- fresh-session and answer-leakage declarations;
- complete pre-seal access list;
- commands, exits, repairs, timeouts, skips, and material read-backs;
- proposal/seal/context/log/comparison paths and hashes;
- source/exclusion and evidence-completeness results;
- objective facts versus agent judgments;
- exact pre/post git status;
- deviations and blind spots;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

Do not claim L0 certification, picture lock, creative approval, delivery, or
general autonomous editing.
