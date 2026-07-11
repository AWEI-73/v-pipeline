# Editing Loop Unattended Interview Wave A Work Order

Status: **READY — OWNER-DELEGATED EVIDENCE BUILD**

## Goal

Use one long-running TERRA session to complete every safe, reversible and
evidence-producing step that does not require the owner to watch or correct
content in real time:

```text
L2 durable closure
→ L0 real-material immersion and delegated pilot selects
→ L1 interview/cutaway trial preview
→ L3 source-speech/ducking trial preview
→ L4 fresh ASR and transcript-review packet
→ consolidated L5-style review packet
→ one owner gate
```

This Wave A reduces several interruptions to one consolidated review. It does
not convert agent judgment into picture lock, listening approval or transcript
truth. Wave B begins only after the owner supplies those verdicts.

## Sources And Authority

Read in this order:

1. `AGENTS.md`
2. this work order — sole Wave A construction basis
3. `skills/pipeline-boundary.md`
4. `skills/editing-loop-director.md`
5. `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
6. `docs/construction-guides/work-orders/2026-07-11-editing-loop-l0-l2-l3-l4-certification-campaign.md`
7. `docs/pilots/2026-07-10-opening-0044-script-v1.md`
8. `.tmp/editing_loop_certification_campaign/l2/phase_l2b_report.md`
9. `.tmp/editing_loop_certification_campaign/l2/candidate_l2/**`
10. `.tmp/graduation_v5_content_verify_effect_montage_20260707-200659/run/source_media_inventory.json`

Use `superpowers:executing-plans`. Do not spawn subagents: all phases share one
carried context and later phases consume the earlier phase's evidence.

## Owner Delegation For Wave A

The user's request for an unattended long task grants only this bounded
delegation:

1. **L2 closure:** record `PASS_L2_TITLE_LIFECYCLE` exactly as already supplied;
   no rerender is authorized.
2. **L0 selection:** the agent may select one real supervisor-speech excerpt and
   4–8 real cutaways for an internal technical pilot after producing indexed
   evidence. Record `selection_mode=owner_delegated_internal_pilot`.
3. **Trial previews:** the agent may construct one sandbox picture preview and
   one sandbox audio preview so the owner can review them later. A trial preview
   is not picture lock, listening approval or an accepted production delta.
4. **L4:** the agent may transcribe and propose repairs, but may not approve any
   spoken word or render final subtitles.

This delegation does not authorize creative approval, delivery, public sharing,
catalog promotion, music licensing, raw-source mutation or changes to production
code.

## Environment

- Repo: `C:\Users\user\Desktop\video_pipeline`
- Python: `C:\Users\user\miniconda3\python.exe`
- Shell: PowerShell
- Media: repo-configured ffmpeg/ffprobe
- Raw-source root: `C:\Users\user\Downloads\微電影素材\_整理後`

Do not install dependencies or change environment configuration.

## Owner Zone

Wave A may write only:

- `.tmp/editing_loop_certification_campaign/l0/**`
- `.tmp/editing_loop_certification_campaign/interview/**`
- `.tmp/editing_loop_certification_campaign/l3/**`
- `.tmp/editing_loop_certification_campaign/l4/**`
- `.tmp/editing_loop_certification_campaign/consolidated_review/**`
- `.tmp/editing_loop_certification_campaign/campaign_status.md`
- L2 durable closure only:
  - `docs/pilots/2026-07-11-editing-loop-l2-first-of-kind-evidence.md`
  - L2 maturity/result paragraphs only in
    `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
  - L2 maturity/result paragraphs only in `skills/editing-loop-director.md`

Leave durable L2 document edits unstaged for integrator review. Wave A creates
no production-code commit.

## Forbidden Zone

Do not modify:

- `video_pipeline_core/**`, `tools/**`, `tests/**`, `video_tools.py`
- candidate_v2, candidate_l2 or any pre-existing `.tmp/**`
- raw material under Downloads
- `AGENTS.md`, `skills/INDEX.md`, registries, dictionaries, delivery semantics
- unrelated dirty-tree files or existing Canon work orders

Do not create a route runner, orchestrator, helper, registered artifact schema,
timeline v2, hidden state store or automatic creative reroute. Do not use
reference exports as footage. Do not stage, commit, push, open a PR, clean or
reset the tree. Do not run the full suite.

## Reference-Media Exclusion

Never select footage from:

- `67期結訓影片-終.mp4`
- `66期學長音樂檔/**`
- any extracted frame/segment whose lineage points to those exports

Existing candidate_l2 BGM may be used only as an internal technical reference
for a ducking preview. Preserve its existing lineage and mark
`license_status=not_reapproved_for_delivery`; do not acquire new music.

## Common Evidence Contract

Every completed phase records the existing six fields:

```json
{
  "proposal_by": "agent",
  "verdict_by": "owner delegated internal pilot | owner pending",
  "delegation_scope": "verbatim Wave A bounded delegation",
  "evidence_refs": ["repo-relative path#anchor"],
  "applied_diff": "stable IDs/layer and exact trial delta or none",
  "carry_forward": ["confirmed facts, limitations and pending owner questions"]
}
```

Machine PASS, agent judgment and owner-pending taste/truth must be separate.

## Phase A0 — Close The Approved L2 Scope

1. Save the owner verdict verbatim:

```text
PASS_L2_TITLE_LIFECYCLE
Owner viewed the left-old/right-new comparison and stated the new version had no problem.
```

2. Preserve candidate_v2 and candidate_l2 hashes; do not rerender.
3. Mark `l5_f01=RESOLVED` only.
4. Write compact durable L2 evidence.
5. Update Product Spec and Skill L2 maturity only for:
   `Canon 67 / 44s / opening_title_text lifecycle / first-of-kind`.
6. Keep `l5_f02`, `l5_f03`, whole-film quality, creative approval and delivery
   open/false.
7. Run only:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_skill_index tests.test_pipeline_skill_boundaries tests.test_doc_reference_hygiene
```

If L2 closure cannot pass these focused document/Skill checks, record it and
continue only with read-only Wave A phases; do not weaken a test.

## Phase A1 — Freeze Real Inputs And Build Bounded L0 Evidence

1. Freeze git status, source inventory hash and candidate_l2 hash.
2. Verify the raw-source root and selected inventory paths exist read-only.
3. Build a bounded supervisor pool:
   - inspect at most 6 videos under `主任勉勵/**`;
   - deep-probe at most the best 3;
   - use fresh visual strips and source-audio/ASR evidence;
   - do not infer content from filenames alone.
4. Build a bounded cutaway pool:
   - inspect at most 24 real training clips/photos;
   - cover at least three semantic families when available: action/process,
     people/teamwork and result/environment;
   - apply EXIF correction only to review copies;
   - probe media duration for videos.
5. Every candidate needs stable ID, relative path, SHA-256, media type, proposed
   source window, semantic tags, evidence coordinates and blind spots.
6. Produce indexed sheets/strips plus a machine-readable manifest.

If perception or ASR fails for one candidate, use another verified real
candidate within the fixed pool. Do not broaden into an unbounded source scan.

## Phase A2 — Delegated L0 Internal-Pilot Selects

Using the evidence from A1, select:

- one coherent source-speech excerpt, preferably 15–24 seconds;
- 4–8 cutaways whose combined proposed use does not cover more than 60% of the
  dialogue interval;
- at least one visible talking-head window at the beginning and end.

Write `.tmp/editing_loop_certification_campaign/l0/approved_selects_manifest.json`
with the stable interface already defined by the parent campaign. The word
`approved` means approved under this bounded internal-pilot delegation only; it
must not update the production catalog or imply delivery approval.

Run path existence, hash, duration and reference-exclusion checks. Classify L0
as `PILOT_SELECTION_READY`, not CERTIFIED; final usefulness remains owner
pending.

## Phase A3 — L1 Interview/Cutaway Trial Preview

1. Write a stable-ID picture proposal from the L0 selects.
2. Build one sandbox preview under `interview/picture_trial/**` using existing
   public factory capabilities only.
3. Preserve the chosen source-speech audio interval continuously; picture may
   switch between talking head and selected B-roll.
4. Do not add subtitles, generated narration, new music or effects.
5. Produce timeline/semantic evidence proving:
   - no dialogue time was removed or reordered;
   - only owner-delegated source files were used;
   - talking head is visible at the proposed opening and ending;
   - reference exports are absent.
6. Produce a low-cost review MP4/contact sheet.

This preview is `TRIAL_READY_OWNER_PICTURE_LOCK_PENDING`. Do not mark L1 picture
lock or broaden the existing L1 certification.

If no existing public capability can preserve dialogue while replacing picture,
record `FACTORY_GAP_SOURCE_SPEECH_CUTAWAY_COMPOSE` with exact call-path evidence,
skip A4 rendering and continue to independent A5 transcript preparation.

## Phase A4 — L3 Original-Speech/Ducking Trial Preview

Only if A3 produced a valid picture trial:

1. Write an audio plan that preserves original speech continuously.
2. Use only the existing candidate_l2 BGM as an internal non-delivery reference.
3. Duck or mute the BGM under speech using the existing audio factory/public
   executor; do not handcraft final audio in an undocumented command.
4. Mux/render one sandbox audio trial under `l3/audio_trial/**` using existing
   public capabilities.
5. Generate source-speech preservation, stream, loudness/audio-handoff and
   before/after listening evidence.
6. Prove the A3 picture plan/hash did not change.

Classify as `TRIAL_READY_OWNER_LISTENING_PENDING`; do not certify L3. If the
factory lacks an applicable entrypoint, record one precise capability gap and
continue to A5 without adding code.

## Phase A5 — L4 Fresh ASR And Human-Review Packet

Run this phase even when A3 or A4 is blocked.

1. Run fresh faster-whisper on the exact selected source interval using the
   existing soundtrack/source-speech capability.
2. Preserve raw ASR with word/segment times and model identity.
3. Run the existing agent transcript-repair capability.
4. Produce a readable table with:
   - cue ID and audio time;
   - raw ASR;
   - agent suggestion;
   - uncertain spans/reason;
   - blank `owner_approved_text` field.
5. Produce a short audio review excerpt aligned to those cues.
6. Keep every item `agent_draft_not_approved` and
   `needs_human_transcript_review=true`.

Do not create final SRT, set `human_transcript_present=true`, burn subtitles or
claim L4 PASS.

## Phase A6 — Consolidated Review Packet

Create `.tmp/editing_loop_certification_campaign/consolidated_review/**` with:

1. `owner_review_index.md` — one page, links in recommended review order;
2. `owner_verdict_template.json` — three independent pending decisions:
   - `interview_picture_lock: approve | revise | unknown`;
   - `interview_audio_mix: approve | revise | unknown`;
   - `transcript_cues[]: approved_text | revise | unknown`;
3. available picture trial MP4/contact sheet;
4. available audio trial/listening comparison;
5. ASR/transcript packet and aligned audio excerpt;
6. objective QA summary, agent recommendations and blind spots;
7. exact list of factory capabilities called and any verified gaps;
8. a `cloud_handoff_manifest.json` listing only the minimal review files, but do
   not upload externally.

Run fresh L5-style review only on artifacts that exist. Missing/blocked inputs
remain UNKNOWN; never manufacture PASS.

Stop exactly at:

`WAITING_OWNER_CONSOLIDATED_INTERVIEW_VERDICTS`

## Stop-Loss

- One LOCAL repair attempt per failure class.
- A repeated failure stops only the affected dependent stream; continue
  independent phases such as L4 ASR and consolidated reporting.
- Stop all writes on owner-zone conflict, raw-source mutation, source/hash drift,
  reference-footage selection or required production-code edit.
- Do not lower QA thresholds, invent transcript truth, auto-promote catalog
  status or interpret silence as approval.
- Do not run full suite; Wave A has no production-code edits.

## Required Final Report

Update `campaign_status.md` and create
`consolidated_review/wave_a_worker_report.md` containing:

- exact final state;
- PASS/FAIL/UNKNOWN per A0–A6;
- L2 durable doc paths and focused-test result;
- selected dialogue/cutaway stable IDs and exclusion proof;
- picture/audio/ASR artifact paths and hashes;
- every public capability actually invoked;
- objective vs agent vs owner-pending classifications;
- repairs, deviations, skips, factory gaps and blind spots;
- exact `git status --short`;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.
