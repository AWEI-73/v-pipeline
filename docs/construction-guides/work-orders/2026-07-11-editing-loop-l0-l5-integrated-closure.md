# Editing Loop L0–L5 Same-Candidate Integrated Closure Work Order

Status: **READY — PHASE 0/1, THEN OWNER GATE**

## 1. Goal

Close the remaining first-of-kind Editing Loop proof on one real, bounded
candidate:

```text
real-material L0 selects
→ L1 22-second interview/cutaway picture
→ L2 evidence-backed no-op
→ L3 original speech + internal-preview BGM ducking
→ L4 owner-approved source-speech subtitles
→ L5 fresh rendered review
→ integrator acceptance
```

This is a **closure and integration work order**, not a capability-building
campaign. Use the existing V Pipeline factories and the
`editing-loop-director` Skill. Do not create another orchestrator, route,
driver, context engine, schema registry entry, or reusable helper.

The final successful claim is deliberately bounded:

> Canon 67 / 22-second supervisor interview-and-cutaway / internal review /
> L0–L5 first-of-kind integrated closure.

It is not a claim about the 9.4-minute film, all video types, creative delivery,
music rights, production-catalog promotion, or general autonomous editing.

## 2. Product Decisions Already Fixed

1. All LOOPs must carry evidence forward; none is an isolated island.
2. The Skill directs the work and existing factories execute it.
3. The same rendered candidate must be carried from picture through audio,
   subtitles, and review. Separate historical demonstrations do not by
   themselves prove integration.
4. L2 may close as an explicit **no-op** when the approved interview script and
   picture require no title, transition, chapter card, or effect delta. Do not
   add an effect merely to make L2 non-empty.
5. Owner silence is not approval. Picture taste, audio taste, and transcript
   truth remain owner-only.
6. A required production-code or test change is a separate TDD work order. It
   must not be implemented inside this closure run.
7. Run the full suite once, only after all media/evidence work is finished.

This work order supersedes only the **remaining execution** of Phase I in
`2026-07-11-editing-loop-l0-l2-l3-l4-certification-campaign.md` for this
bounded 22-second candidate. Historical artifacts and prior reports remain
immutable evidence.

## 3. Authority And Required Read Order

### Before the L0 blind seal

Read only:

1. `AGENTS.md`
2. this work order — sole construction basis
3. `skills/pipeline-boundary.md`
4. `skills/editing-loop-director.md`
5. `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
6. `docs/decisions/2026-07-10-evidence-carrying-editing-loop.md`
7. the source inventory and raw-source evidence named in Phase 1

Before writing the L0 blind seal, do **not** read:

- `.tmp/editing_loop_certification_campaign/l0/approved_selects_manifest.json`
- the existing interview picture plan or preview
- L3 mix artifacts
- L4 transcript artifacts
- consolidated owner packets or worker reports that reveal prior selections

### After the L0 blind seal

Read, in order:

1. `.tmp/editing_loop_certification_campaign/l0/approved_selects_manifest.json`
2. `.tmp/editing_loop_certification_campaign/interview/picture_trial/b4_repaired_picture_trial_evidence.json`
3. `.tmp/editing_loop_certification_campaign/l3/audio_trial/preview_mix_contract_v1/phase_l3_preview_mix_contract_report.md`
4. `.tmp/editing_loop_certification_campaign/consolidated_review/owner_review_index.md`
5. `.tmp/editing_loop_certification_campaign/consolidated_review/owner_verdict_template.json`
6. `.tmp/editing_loop_certification_campaign/l4/review/transcript_review_table.json`
7. `skills/subtitle-director.md`
8. the L5 sections of the Product Spec and Editing Loop Skill

Use `superpowers:executing-plans`. Do not spawn subagents: every phase consumes
the same carried candidate and the gates are sequential.

## 4. Environment

- Repo: `C:\Users\user\Desktop\video_pipeline`
- Python: `C:\Users\user\miniconda3\python.exe`
- Shell: PowerShell
- ffmpeg/ffprobe: repo-configured executables
- Closure root:
  `.tmp/editing_loop_certification_campaign/integrated_closure/`

Do not install dependencies or modify environment configuration.

## 5. Frozen Baseline

Re-read and record every hash before Phase 1. Stop on drift.

| Artifact | Required SHA-256 |
|---|---|
| frozen 44s candidate_v2 | `EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6` |
| frozen 44s candidate_l2 | `F1EF6951FA29E17C105518119B5B18DC2F847BEA4B005FD41E6E3857FFBC53A9` |
| repaired 22s picture | `F2BC84A1A397133F6532989E7927A686DD0DAB4619DA14815C9E339FCB80DD4D` |
| 22s picture plan | `4D6F7D512CAD0A0ADFB3C4B9A12F5FD987CF7DAA4F462B42ACF95B83413C19DA` |
| internal-preview BGM | `3B4BAA4B50E6949AF2D596E40FB9E16886C648D82E5FF524FFF32265DFFC503A` |
| soundtrack plan | `C6D21165FA873AAEFDC95F5CF728843B6CE8827B15A70B97E48549ABC77B3823` |
| valid L3 preview MP4 | `33D63F887EC2BF2D81D7A622BCF9741859175A8890AE1B81DB5D5E411F31B692` |

Required code baseline is commit `a8273610` or a descendant that contains it.
Do not reset if HEAD is newer; record the real HEAD and verify that commit is an
ancestor. Preserve all pre-existing dirty-tree paths exactly.

The L3 BGM remains:

```text
preview_only=true
delivery_allowed=false
music_use_basis.status=pipeline_default_internal_preview
```

No later phase may convert that into rights, license, creative, or delivery
approval.

## 6. Owner Zone

The worker may create or update only:

- `.tmp/editing_loop_certification_campaign/integrated_closure/**`
- `.tmp/editing_loop_certification_campaign/campaign_status.md`
- after every phase is technically complete and the owner verdict is valid:
  `docs/pilots/2026-07-11-editing-loop-l0-l5-integrated-closure-evidence.md`

Experimental media and JSON remain uncommitted. The durable evidence Markdown
also remains unstaged for integrator review.

## 7. Forbidden And Read-Only Zone

Never modify:

- production code, `tools/**`, `video_tools.py`, or `tests/**`
- `skills/**`, Product Spec, decisions, registries, dictionaries, INDEX files,
  route runners, orchestrators, or artifact ownership contracts
- all historical campaign artifacts outside the Owner Zone
- `.tmp/loop_f1_blind_reproducibility/**` and `.tmp/loop_pilot_0044/**`
- raw source material under Downloads
- prior candidates, plans, reports, verdicts, before evidence, or hash-frozen
  inputs
- `AGENTS.md`, existing unrelated dirty-tree paths, `r`, or
  `supply_review.json`

Do not stage, commit, push, upload, open a PR, clean/reset the tree, mutate raw
media, promote materials to a catalog, or set either approval flag true.

If an existing public factory cannot complete a required step, write one exact
factory-gap artifact and stop the affected stream. Do not add a workaround that
duplicates the factory.

## 8. Carried Decision Record

Every LOOP must write these six fields into its evidence record:

```json
{
  "proposal_by": "agent",
  "verdict_by": "owner, integrator, delegated scope, or pending",
  "delegation_scope": "verbatim bounded authority or none",
  "evidence_refs": ["repo-relative path#time_range|cell_id|check_id"],
  "applied_diff": "stable IDs/layer and exact delta, no-op, or none",
  "carry_forward": ["confirmed decisions, constraints, hashes, findings"]
}
```

Also record owner-verdict count, elapsed minutes, and missing-control findings.
Machine PASS, agent judgment, and owner taste must remain separate.

## 9. Phase 0 — Freeze And Baseline Audit

1. Record HEAD, ancestor check for `a8273610`, `git status --short`, Python,
   ffmpeg, and ffprobe identity.
2. Hash all frozen inputs and write `input_freeze.json`.
3. Validate that all historical evidence paths needed later exist and decode.
4. Confirm the valid L3 preview is 22.000 seconds, 660 frames at 30 fps, with
   one video and one audio stream.
5. Do not run the full suite or rerender anything.

Write `phase_0_baseline_report.md`. Any hash drift or missing evidence stops at
`WAITING_INTEGRATOR_BASELINE_RECONCILIATION`.

## 10. Phase 1 — L0 Blind Reproducibility Shadow

This phase certifies the **procedure**, not exact taste identity.

1. Use the read-only source root
   `C:\Users\user\Downloads\微電影素材\_整理後` and the source inventory
   `.tmp/graduation_v5_content_verify_effect_montage_20260707-200659/run/source_media_inventory.json`.
2. Independently inspect a bounded supervisor-speech pool plus training B-roll
   pool. Produce fresh indexed walls/sheets/strips under
   `integrated_closure/l0_shadow/evidence/`; apply EXIF correction to review
   copies and probe video/audio where applicable.
3. Exclude `67期結訓影片-終.mp4` and everything under
   `66期學長音樂檔/**` as reference exports.
4. Propose one 12–25 second dialogue excerpt and 4–8 cutaways with stable IDs,
   relative paths, hashes, source windows, semantic roles, evidence
   coordinates, reasons, and blind spots. Do not select by catalog order or
   filename alone.
5. Write `l0_shadow/proposal.json`, then write
   `l0_shadow/blind_seal.json` containing its SHA-256, creation time, declared
   unread prior-answer paths, and `answer_leakage_detected=false|true`.

Only after the seal exists may the worker read historical L0/L1 artifacts.
Compare the shadow proposal to the carried approved-selects manifest by:

- dialogue function and interval;
- cutaway semantic roles and diversity;
- source/exclusion truth;
- evidence completeness;
- exact overlap, while explicitly stating that exact overlap is not required.

Write `l0_shadow/reproducibility_comparison.json` and
`phase_1_l0_shadow_report.md`. Any detected answer leakage makes L0
reproducibility `UNKNOWN`, not PASS; continue only to prepare the owner packet.

## 11. Phase 2 — Consolidated Owner Gate

Build one review packet under `integrated_closure/owner_gate/` containing:

1. L0 carried selects plus the blind shadow comparison;
2. the valid repaired 22-second picture preview and contact sheet;
3. the valid internal-only L3 audio preview, WAV, listening packet, and
   source-speech comparison;
4. the seven L4 ASR cues, uncertainty notes, and aligned review audio;
5. an L2 applicability statement proposing `no_change_approved` because this
   bounded interview candidate has no approved effect requirement;
6. objective facts, agent recommendations, and blind spots in separate blocks.

Create `integrated_owner_verdict_template.json` with this minimum shape:

```json
{
  "artifact_role": "editing_loop_l0_l5_integrated_owner_verdict",
  "scope": "Canon 67 22-second interview internal review only",
  "l0_selects": "approve | revise | unknown",
  "l1_picture": "approve | revise | unknown",
  "l2_effects": "no_change_approved | revise | unknown",
  "l3_audio": "approve_internal_preview | revise | unknown",
  "l4_transcript_cues": [
    {"cue_id": "cue_001", "approved_text": "", "verdict": "approved_text | revise | unknown"}
  ],
  "non_delegated": [
    "delivery",
    "human_creative_approval",
    "final_delivery_claimed",
    "music rights",
    "production catalog promotion"
  ],
  "human_creative_approval": false,
  "final_delivery_claimed": false
}
```

Include all seven cue IDs. Validate every link and then stop exactly at:

`WAITING_OWNER_L0_L5_INTEGRATED_VERDICTS`

No owner response means no Phase 3.

## 12. Phase 3 — Validate And Apply Owner Verdict

Resume only after the owner supplies an explicit verdict artifact or verbatim
message covering all five fields.

### Verdict validation

- Any `unknown`, blank approved text, missing cue, or ambiguous decision keeps
  the corresponding LOOP `UNKNOWN`.
- Any `revise` writes one structured finding with target LOOP, stable IDs/time
  range, evidence, requested change, and owner wording, then stops at
  `WAITING_OWNER_TARGETED_LOOP_REVISION`.
- Do not infer text from ASR, agent suggestions, context, or the reference film.
- Do not continue only the convenient fields while silently waiving another.

When all fields are valid:

- **L0:** carry the current approved selects and the blind-comparison result;
  no catalog promotion.
- **L1:** picture-lock the exact repaired picture plan and hash; no picture
  rerender.
- **L2:** write an applicability/no-op record with
  `applied_diff=no-op`, owner verdict ref, and unchanged picture hash.
- **L3:** accept only the existing internal-preview mix for this candidate;
  preserve `preview_only=true` and `delivery_allowed=false`.
- **L4:** use only the seven owner-approved cue texts and approved cue timings.

Write one loop decision record per L0–L4 before rendering subtitles.

## 13. Phase 4 — L4 Approved Subtitle Factory Path

Create `integrated_closure/candidate_l4/run/` as a fresh run. Copy the valid L3
preview into it as `pre_caption_preview.mp4`; do not edit the historical file.

### 13.1 Approved SRT and human decision

1. Reuse cue IDs/timings from the review table unless the owner explicitly
   approved a timing revision.
2. Build `subtitles.srt` solely from owner-approved text.
3. First audit existing public subtitle tools. If no public tool accepts the
   owner-verdict cue shape directly, a persisted run-local evidence generator
   may be written only at
   `candidate_l4/execution/build_approved_srt.py`. It must read UTF-8 JSON,
   contain no Chinese text literals, write only inside `candidate_l4/run/`, and
   never be imported, registered, or described as a reusable helper.
4. Run the existing human decision writer with `reviewer=human`, the approved
   SRT as `reviewed_draft`, and all seven reviewed cue IDs.
5. Write `source_speech_subtitle_evidence.json` with the exact 0–22 second
   source-speech segment, all approved cues, `subtitle_source=human_approved`,
   `human_transcript_present=true`, and the owner-verdict/decision refs.

Generated JSON/SRT/Markdown must decode as UTF-8, contain no `\ufffd`, and
contain no suspicious run of four or more literal question marks.

Use the existing writer, repeating `--reviewed-cue-id` once per cue:

```powershell
C:\Users\user\miniconda3\python.exe tools\write_human_transcript_review_decision.py --run <run> --decision approved --reviewer human --reviewed-draft <run>\subtitles.srt --reviewed-cue-id cue_001 --reviewed-cue-id cue_002 --reviewed-cue-id cue_003 --reviewed-cue-id cue_004 --reviewed-cue-id cue_005 --reviewed-cue-id cue_006 --reviewed-cue-id cue_007 --json
```

### 13.2 Public subtitle acceptance and render

Use the existing public capabilities, not private ffmpeg assembly:

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py caption-audit --srt <run>\subtitles.srt --out <run>\caption_audit.json
C:\Users\user\miniconda3\python.exe tools\source_speech_subtitle_qa.py --run <run> --json
C:\Users\user\miniconda3\python.exe tools\subtitle_voiceover_handoff_accept.py --contract <run>\subtitle_voiceover_contract.json --caption-audit <run>\caption_audit.json --subtitles <run>\subtitles.srt --out-dir <run> --json
C:\Users\user\miniconda3\python.exe video_tools.py burnsub <run>\pre_caption_preview.mp4 <run>\subtitles.srt --out <run>\verified_preview.mp4
```

The run-local contract must be the minimal truthful Stage-0 subtitle intent:
`language=zh-TW`, `subtitle_required=true`, `voiceover_required=false`. Source
speech is already present; do not mislabel it as synthesized voiceover.

Required acceptance:

- caption audit PASS with seven nonblank cues;
- source-speech subtitle QA PASS with human review cleared;
- subtitle handoff acceptance `ok=true` and `subtitle_ready=true`;
- 22.000-second rendered preview within 0.05 seconds, 660 frames at 30 fps;
- one video and one audio stream;
- decoded-audio MD5 before/after subtitle burn is identical; `burnsub` must not
  alter the accepted L3 mix;
- rendered frames prove readable Traditional Chinese subtitles at early,
  middle, and late cue windows;
- no frozen historical hash changes.

If the public path fails because of a true factory gap, write
`factory_gap_l4_approved_subtitle_path.json` and stop. Do not patch code.

## 14. Phase 5 — Fresh L5 On The Same Candidate

Run L5 only on `candidate_l4/run/verified_preview.mp4`. Do not copy a prior L5
PASS report.

At minimum run:

```powershell
C:\Users\user\miniconda3\python.exe tools\rendered_product_qa.py --run <run> --out-dir <l5>\rendered_qa --json
C:\Users\user\miniconda3\python.exe video_tools.py final-product-verify <run>\verified_preview.mp4 --out-dir <l5>\final_verify --samples 16
C:\Users\user\miniconda3\python.exe video_tools.py perception-field-check <run>\verified_preview.mp4 --out <l5>\perception
```

Also perform the applicable black-frame, stream/duration, caption readability,
source-speech, audio-scope, and protected-hash checks available in the current
repo. Beat alignment is `not_applicable` for this dialogue-led slice unless
there is an approved beat requirement; never manufacture a beat PASS.

Read the full low-density wall and dense strips around every subtitle window.
Create a fresh L5 packet with:

- objective checks and exact command exits;
- agent visual/audio/text observations with time coordinates;
- objective versus taste findings;
- proposed target LOOP for each finding;
- no automatic edit or reroute.

If any objective finding blocks the bounded integrated claim, stop at
`WAITING_OWNER_OR_INTEGRATOR_L5_FINDING_VERDICT`. A taste finding stays open
unless the owner explicitly resolves or waives it; a waiver is not a machine
PASS.

## 15. Phase 6 — Durable Evidence And Final Regression

Only when Phases 0–5 have technically completed and every required owner
verdict is valid:

1. Write
   `docs/pilots/2026-07-11-editing-loop-l0-l5-integrated-closure-evidence.md`.
2. Record PASS/FAIL/UNKNOWN separately for every LOOP. L0 may be proposed for
   bounded CERTIFIED only when the blind seal is clean and the integrator
   accepts the reproducibility comparison. L3/L4 may be proposed for bounded
   CERTIFIED only for this 22-second case.
3. Record that L2 was an approved no-op, not a newly certified effect pattern.
4. Record all hashes, verdict refs, six-field records, telemetry, commands,
   evidence paths, open findings, limitations, and both false approval flags.
5. Do not edit Product Spec or Skill maturity wording; that is the integrator's
   post-acceptance responsibility because those files are already dirty.
6. Run the full suite once, last:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest discover -s tests
git diff --check
```

Expected exits: `0`. Existing line-ending warnings may be reported; no new
whitespace error is allowed. A full-suite failure is FAIL/UNKNOWN evidence, not
permission to edit the Forbidden Zone.

Successful worker stop state:

`WAITING_INTEGRATOR_L0_L5_INTEGRATED_CLOSURE_REVIEW`

The worker must not write `CLOSED`, `human_creative_approval=true`, or
`final_delivery_claimed=true`.

## 16. Stop-Loss

- One LOCAL artifact/command repair attempt per failure class.
- The second occurrence of the same class is STRUCTURAL; stop the affected
  stream at its last green state.
- Stop immediately on source/candidate hash drift, answer leakage, missing
  owner truth, invalid UTF-8, reference-footage selection, rights/delivery
  ambiguity, owner-zone conflict, or required production-code/test change.
- Do not lower a threshold, fabricate a transcript, relabel preview music,
  handcraft a private renderer/mixer, copy old PASS evidence, or interpret
  successful process exit as product acceptance.
- Preserve before evidence and every last-green artifact.

## 17. Required Worker Report

Update `campaign_status.md` and write
`integrated_closure/integrated_closure_worker_report.md` with:

- exact final state;
- PASS/FAIL/UNKNOWN per phase and per L0–L5;
- baseline and final HEAD, exact dirty tree, and frozen-hash preservation;
- blind-seal hash and answer-leakage declaration;
- verbatim owner verdict and its artifact hash;
- every command, exit code, and material read-back;
- SRT, human decision, handoff, rendered preview, L5 packet, and durable
  evidence paths/hashes;
- objective versus agent versus owner classifications;
- deviations, repairs, skips, factory gaps, blind spots, and open findings;
- full-suite and `git diff --check` results;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

No commit, upload, delivery, or general maturity claim is authorized.
