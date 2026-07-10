# Editing Loop L0/L2/L3/L4 Certification Campaign Work Order

Status: **READY FOR CAMPAIGN PHASE H + L2A**

## Goal And Sources

Run one resumable, sequential campaign that:

1. repairs the verified `h01`/`h02` audit-contract mismatches with focused TDD;
2. certifies L2 title lifecycle from real finding `l5_f01`;
3. certifies L0 real-material immersion/selects for a bounded supervisor interview;
4. uses the certified L1 shape to build a dialogue-continuous cutaway picture bridge;
5. certifies L3 original-speech preservation and music ducking;
6. certifies L4 ASR-draft → owner-approved transcript → subtitles;
7. runs one fresh L0→L5 integration review.

Authority, in order:

1. `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
2. `skills/editing-loop-director.md`
3. `docs/superpowers/plans/2026-07-11-editing-loop-l0-l2-l3-l4-certification-campaign.md`
4. this work order, which is the sole construction basis

This is a long-running campaign, not a daemon or orchestrator. One worker may
resume the same session across gates, but must stop whenever this document says
`WAITING_*`. Owner silence is never approval.

## Known Input Facts

- Frozen Canon 67 candidate:
  `.tmp/loop_f1_blind_reproducibility/candidate_v2/run/final.mp4`
- Frozen SHA-256:
  `EE6EFC6FE624A3CF20A0C8A616480FF63C7C04E250168D806E7DF3777C7DC3B6`
- Approved opening script:
  `docs/pilots/2026-07-10-opening-0044-script-v1.md`
- L5 durable evidence:
  `docs/pilots/2026-07-10-editing-loop-l5-first-of-kind-evidence.md`
- Real-source root:
  `C:\Users\user\Downloads\微電影素材\_整理後`
- Verified real supervisor source exists:
  `主任勉勵/IMG_2141.MOV`; this is evidence of availability, not a pinned select.
- Inventory evidence:
  `.tmp/graduation_v5_content_verify_effect_montage_20260707-200659/run/source_media_inventory.json`
- Candidate catalog evidence:
  `.tmp/film_canon_production_readiness_20260707-011141/graduation/reviewed_catalog_map.json`
  currently marks supervisor candidates `human_review_status=missing`; never
  promote them to accepted without the L0 owner verdict.
- `67期結訓影片-終.mp4` and everything under `66期學長音樂檔/**` are reference
  films/exports only. They may inform structure but must not be candidate media.

## Required Read Order

1. `AGENTS.md`
2. this work order
3. `skills/pipeline-boundary.md`
4. `skills/editing-loop-director.md`
5. Product Spec
6. campaign implementation plan
7. L5 durable evidence and approved opening script
8. only the phase-specific artifacts named below

Use `superpowers:executing-plans`. Do not delegate or spawn subagents: phases
share candidate state and every creative boundary is sequential.

## Environment

- Repo: `C:\Users\user\Desktop\video_pipeline`
- Python: `C:\Users\user\miniconda3\python.exe`
- Shell: PowerShell
- Media: repo-configured ffmpeg/ffprobe

Do not install dependencies or change environment configuration.

## Owner Zone

The worker may modify only:

- Phase H code/tests:
  - `video_pipeline_core/timeline_invariants.py`
  - `tests/test_timeline_invariants.py`
  - `video_pipeline_core/new_visual_information_audit.py`
  - `tests/test_new_visual_information_audit.py`
- Experimental campaign outputs:
  - `.tmp/editing_loop_certification_campaign/**`
- After the matching owner/integrator certification only:
  - `docs/pilots/2026-07-11-editing-loop-*-first-of-kind-evidence.md`
  - `docs/pilots/2026-07-11-editing-loop-integration-flight-evidence.md`
  - maturity/result paragraphs only in the Product Spec and Editing Loop Skill

Phase H must use two exact, focused commits. Experimental phases must not be
committed. Durable evidence/maturity edits remain unstaged for integrator review.

## Forbidden And Read-Only Zone

Never modify:

- `.tmp/loop_f1_blind_reproducibility/**`
- `.tmp/loop_pilot_0044/**`
- every pre-existing `.tmp/**` outside the campaign Owner Zone
- raw source material under Downloads
- `video_tools.py`, other `video_pipeline_core/**`, other `tools/**`, other `tests/**`
- `AGENTS.md`, `skills/INDEX.md`, `skills/pipeline-boundary.md`
- registries, artifact dictionaries, delivery/reviewer semantics
- unrelated dirty-tree files: existing Canon work orders, `r`, `supply_review.json`

Do not push, open a PR, clean/reset the tree, change approval flags, create a
route runner/driver/state machine, or add a registered schema/helper. A public
capability gap discovered during an experimental loop is a finding and stop,
not permission to expand code scope.

## Decisions Delegated To The Worker

The worker may decide:

- minimal implementation details for h01/h02 within the pinned contracts;
- which real supervisor and cutaway candidates to propose after inspecting fresh
  evidence, without treating filenames as acceptance;
- evidence framing, stable IDs, candidate timing proposals and applicability;
- one LOCAL repair attempt per evidence-generation failure class inside the
  campaign Owner Zone.

The worker may not decide:

- title/picture/audio/text taste, picture lock, final creative quality or delivery;
- exact transcript truth;
- source acceptance unless owner explicitly delegates the bounded L0 selection;
- music license/authorization;
- a new public API, helper, artifact contract or architecture.

## Common LOOP Contract

Every phase writes or appends the existing six decision fields:

```json
{
  "proposal_by": "agent",
  "verdict_by": "owner or pending",
  "delegation_scope": "verbatim bounded authority or none",
  "evidence_refs": ["repo-relative path#anchor"],
  "applied_diff": "stable IDs/layer and exact delta or none",
  "carry_forward": ["confirmed constraints/findings for the next phase"]
}
```

Also record owner-verdict count, phase minutes and missing-control findings.
Machine PASS, agent judgment and owner taste must remain distinct.

## Campaign Phase H — h01/h02 TDD And Real Audit Closure

Follow Tasks 1–3 of the campaign plan exactly.

Required commands:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_timeline_invariants -v
C:\Users\user\miniconda3\python.exe -m unittest tests.test_new_visual_information_audit tests.test_video_tools_audits -v
C:\Users\user\miniconda3\python.exe video_tools.py timeline-audit .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --expected-duration 44 --out .tmp\editing_loop_certification_campaign\hardening\timeline_invariants.json
C:\Users\user\miniconda3\python.exe video_tools.py new-visual-audit .tmp\loop_f1_blind_reproducibility\candidate_v2\run\timeline_build.json --out .tmp\editing_loop_certification_campaign\hardening\new_visual_information_audit.json
```

Expected exits: `0`. Red-first evidence must be recorded before each fix. Real
audit acceptance additionally requires:

- `opening_poetry_card` is accepted only because explicit generated lineage and
  generated visual description are both present;
- a truly untraced clip test still fails as designed;
- new-visual total duration is nonzero and uses formal `target_duration_sec` or
  timeline in/out rather than invented values;
- legacy duration tests remain green.

Write `hardening/phase_h_report.md`. If green, make two focused commits and
continue to L2A. If any material check is nonzero, stop at
`WAITING_INTEGRATOR_HARDENING_REVIEW` at the last green commit.

## Campaign Phase L2A — Proposal Only

Consume `l5_f01`: approved script requires title appearance around 3–4 seconds,
completion around 9 seconds and hold to 11 seconds. Do not combine `l5_f02` or
`l5_f03`.

1. Re-hash and freeze candidate_v2 plus relevant plan/timeline/motion artifacts.
2. Reconstruct the existing repo-owned render call from
   `phase_b_render_invocation.json` and public renderer code; do not create a
   run-local renderer.
3. Propose an exact effects/text-layer lifecycle delta with stable overlay IDs.
4. Create readable current/proposed timing evidence and state blind spots.
5. Write `l2/proposal/**`, `l2/phase_l2a_report.md` and stop exactly at:

`WAITING_OWNER_L2_APPLY_VERDICT`

No render or candidate_l2 is authorized before that verdict.

## Campaign Phase L2B — Apply And Final Taste Gate

Authorized only by an explicit owner verdict naming the approved title timing.

1. Store the verdict verbatim.
2. Clone required inputs into `l2/candidate_l2/run/**`; never edit candidate_v2.
3. Apply exactly one title-lifecycle delta using existing public compile/render
   surfaces.
4. Produce semantic diff proving picture sources/timing, audio, poem, montage,
   ending, duration and approval flags are unchanged.
5. Run fresh lifecycle QA, rendered QA, final verify and before/after dynamic.
6. Stop at `WAITING_OWNER_FINAL_L2_TASTE_VERDICT`.

Only an owner/integrator PASS may create durable L2 evidence or mark L2
CERTIFIED for the narrow title-lifecycle scope.

## Campaign Phase L0A/L0B — Real Interview Selects

L0A may begin after L2B technical evidence, but L2 certification remains
pending until its final taste verdict.

1. Freeze raw-source inventory and verify source existence read-only.
2. Exclude reference exports by path and hash them only to prove exclusion.
3. Inspect a bounded supervisor pool under `主任勉勵/**` and a bounded training
   B-roll pool using fresh indexed sheets/walls/strips. Apply EXIF correction to
   review copies; probe video duration/audio.
4. Propose one coherent dialogue excerpt (prefer 12–25 seconds) and 3–8 cutaway
   candidates with relative paths, hashes, time windows, semantic tags, evidence
   coordinates, selection reasons and blind spots.
5. Stop at `WAITING_OWNER_L0_SELECTS_VERDICT`.

After explicit approve/revise/delegate, write `l0/approved_selects_manifest.json`
and provenance. Its stable consumption interface is:

```json
{
  "dialogue_select": {
    "select_id": "stable worker-assigned ID",
    "source_relative_path": "path relative to the frozen source root",
    "source_in_sec": 0.0,
    "source_out_sec": 18.0,
    "sha256": "64 lowercase hex characters"
  },
  "cutaway_selects": [
    {
      "select_id": "stable worker-assigned ID",
      "source_relative_path": "path relative to the frozen source root",
      "source_in_sec": 0.0,
      "source_out_sec": 2.0,
      "sha256": "64 lowercase hex characters"
    }
  ]
}
```

Times above describe field types, not pre-approved values; the owner verdict
fixes the real values. Every path must exist; no reference footage may appear.
Stop on missing truth instead of substituting a filename guess.

## Campaign Phase L1 Bridge — Interview Picture Only

Use the already-certified L1 loop shape; do not claim new L1 maturity.

1. Keep the approved dialogue source/time range continuous.
2. Propose stable-ID talking-head and B-roll picture windows while leaving all
   audio untouched.
3. Stop at `WAITING_OWNER_INTERVIEW_PICTURE_VERDICT`.
4. After approval, use existing compose/render capabilities to build
   `interview/picture/candidate_picture/**`.
5. Verify picture diff, source hashes and unchanged dialogue timing.

Do not resolve or touch `l5_f03`.

## Campaign Phase L3A/L3B — Original Speech And Ducking

L3A proposal must define:

- the original-dialogue source and exact continuous interval;
- music source/license evidence, or an explicit no-music fallback;
- ducking/mute policy and measurable voice-priority acceptance;
- protected picture hash.

Stop at `WAITING_OWNER_L3_MIX_VERDICT` before mixing.

After approval:

1. execute a formal plan using `tools/audio_mix_plan_execute.py`;
2. mux/render through existing public surfaces;
3. generate fresh audio mix, source-speech preservation, stream and relevant
   loudness/audio-handoff evidence;
4. verify picture hash/semantic plan unchanged and dialogue has no timeline gap;
5. produce a listening excerpt and stop at
   `WAITING_OWNER_FINAL_L3_LISTENING_VERDICT`.

No music without authorization evidence. A no-music L3 can certify original
speech preservation, but cannot certify ducking; report the narrower scope.

## Campaign Phase L4A/L4B — Human-Approved Source-Speech Subtitles

L4A runs fresh ASR only after the dialogue excerpt is locked:

```powershell
$m = Get-Content -Raw -Encoding UTF8 .tmp\editing_loop_certification_campaign\l0\approved_selects_manifest.json | ConvertFrom-Json
$approvedSource = Join-Path 'C:\Users\user\Downloads\微電影素材\_整理後' $m.dialogue_select.source_relative_path
C:\Users\user\miniconda3\python.exe tools\soundtrack_probe.py --audio $approvedSource --out .tmp\editing_loop_certification_campaign\l4\draft\source_speech_asr_probe.json --enable-asr --asr-model small --language zh --json
C:\Users\user\miniconda3\python.exe tools\agent_transcript_repair.py --run .tmp\editing_loop_certification_campaign\l4\draft --json
```

The worker substitutes only the owner-approved real source path from L0. ASR,
agent repairs and draft SRT remain unapproved. Produce a packet showing audio
time, raw ASR, suggestion, uncertainty and editable owner text, then stop at:

`WAITING_OWNER_L4_TRANSCRIPT_APPROVAL`

L4B requires the owner's verbatim approved cues/timing. Then:

1. store the exact verdict and build final SRT only from approved text;
2. create `source_speech_subtitle_evidence.json` with
   `human_transcript_present=true` and an owner-verdict ref;
3. run:

```powershell
C:\Users\user\miniconda3\python.exe video_tools.py caption-audit --srt .tmp\editing_loop_certification_campaign\l4\approved\subtitles.srt --out .tmp\editing_loop_certification_campaign\l4\approved\caption_audit.json
C:\Users\user\miniconda3\python.exe tools\source_speech_subtitle_qa.py --run .tmp\editing_loop_certification_campaign\l4\approved --json
```

4. burn/render through the existing public subtitle capability;
5. verify exact UTF-8 text, timing, picture/audio preservation and rendered
   readability; stop at `WAITING_OWNER_FINAL_L4_TEXT_VERDICT`.

## Campaign Phase I — L0→L5 Integration Flight

Authorized only after bounded L0, L2, L3 and L4 final owner verdicts are PASS.
L1 bridge must be picture-locked.

1. Write `integration/input_manifest.json` referencing the confirmed opening/L2
   slice and interview/L0-L4 slice. It is an experimental two-slice evidence
   bundle, not a new registered contract or a new story edit.
2. For every loop, read back proposal, verbatim verdict, applied diff, focused
   verification and carry-forward; all paths and hashes must resolve.
3. Do not concatenate the two slices. A combined film requires a separately
   approved story/script decision and is outside this campaign.
4. Run applicable fresh L5 objective checks, perception field, detailed strips
   and review packet on each bounded candidate. Do not copy prior PASS reports.
5. Prove no route runner was called and the next-loop recommendation is only a
   finding, not an automatic action.
6. Stop at `WAITING_OWNER_FINAL_INTEGRATION_VERDICT`.

After an owner PASS, write durable summaries and scoped maturity paragraphs,
then stop at `WAITING_INTEGRATOR_CAMPAIGN_ACCEPTANCE`. Whole-film quality,
creative approval and delivery remain UNKNOWN/false.

## Phase Acceptance Matrix

| Phase | Required fresh evidence | Owner gate |
|---|---|---|
| H | red-first tests, focused green, real audits, two commits | integrator if any mismatch |
| L2 | one title-only semantic diff, lifecycle/render QA, dynamic | apply + final taste |
| L0 | indexed real-source evidence, approved manifest, exclusion proof | selects/delegation |
| L1 bridge | stable picture plan, continuous dialogue timing | picture lock |
| L3 | formal audio plan, preservation/ducking/audio QA, listening excerpt | mix + final listening |
| L4 | fresh ASR draft, verbatim approval, caption/source-speech QA, render | transcript + final text |
| I/L5 | resolved evidence graph, fresh QA/perception/findings | final integration |

## Stop-Loss

- One repair attempt per LOCAL failure class. A repeat is STRUCTURAL: stop the
  affected phase and preserve the last green state.
- Stop on owner-zone conflict, missing required authority, candidate/source hash
  drift, a nonzero material acceptance command, or any needed out-of-zone edit.
- Never relax a threshold, fabricate a transcript, synthesize missing approval,
  copy old PASS evidence, or use reference footage to continue.
- A phase may be `PASS`, `FAIL` or `UNKNOWN`; a waiver never creates PASS.
- Do not proceed past a `WAITING_*` state until the same session receives an
  explicit continuation containing the owner/integrator verdict.

## Required Worker Report At Every Stop

Write `.tmp/editing_loop_certification_campaign/campaign_status.md` containing:

- exact phase/state and PASS/FAIL/UNKNOWN classifications;
- commits created in Phase H;
- every command and exit code with material result;
- input/output hashes and artifact paths;
- six decision fields and three telemetry values for completed loops;
- objective vs agent judgment vs owner taste separation;
- exact `git status --short`;
- deviations, repairs, skips, blind spots and blockers;
- literal `No deviations` when true;
- confirmation that approval flags remain false and reference footage was excluded.

The worker must not claim campaign completion before
`WAITING_INTEGRATOR_CAMPAIGN_ACCEPTANCE`.
