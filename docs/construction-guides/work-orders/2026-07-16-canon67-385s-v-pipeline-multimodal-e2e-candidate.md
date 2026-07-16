# Canon 67 — 385 秒 V Pipeline 眼耳心端到端候選片

Date: 2026-07-16
Owner: integrator
Execution shape: single-route formal work order
Final success state: `WAITING_OWNER_CANON67_385S_MULTIMODAL_CANDIDATE_VERDICT`

## 1. Goal

沿用已核准的 Canon 67 `revision_0012` 與 385 秒 paper edit，從 Stage 6
正式總裝出一支包含畫面、預覽音樂、主任原始語音與 12 條核准字幕的
review candidate；再經 Stage 7 客觀驗證與 Stage 8 眼／耳／心 Reviewer。

這是路徑驗證與創意審查候選片，不是 final delivery。

## 2. Frozen truth

- Editorial state:
  `.tmp/canon67_540s_route_acceptance/accepted_chain/revision_0012.json`
- Picture base:
  `.tmp/canon67_540s_route_acceptance/stage6/paper_edit_preview_v1/canon67_385s_picture_base.mp4`
- Picture SHA-256:
  `d31e6395a0e81a6141efafe38a4ac1b9dcd84298d5294b83cd8a6ff1d597d582`
- Protected speech timeline WAV:
  `.tmp/canon67_540s_route_acceptance/stage6/paper_edit_preview_v1/canon67_385s_preview_audio.wav`
- Protected speech WAV SHA-256:
  `7d6721a731e4105fefc4116a78b8435663f329111b168dfea29a953cb2df2d73`
- Owner-approved shifted subtitles:
  `.tmp/canon67_540s_route_acceptance/stage6/paper_edit_preview_v1/canon67_385s_shifted_speech_subtitles.srt`
- Preview BGM:
  `.tmp/capcut_finishing_pilot/music/peaceful_calm_documentary_preview.mp3`
- Preview BGM SHA-256:
  `cb7e3947ae8e6814e5128bcc5a64c56f75af8206c52059a41dd1ef72e3a4c859`
- BGM usage scope:
  `internal_preview_only_pending_owner_legal_review`

The following remain fixed:

- total semantic duration 385.00 sec;
- seg03 36 sec;
- seg08 complete 39.34 sec supervisor speech;
- seg09 0 sec and 13/13 teacher roster deferred;
- seg10 accepted memory-to-group-photo ending;
- the known `picture_tail_one_frame_short` finding remains visible and must not
  be relabelled PASS.

## 3. Owner zone

New run artifacts may be written only below:

`.tmp/canon67_540s_route_acceptance/stage6/multimodal_candidate_v1/**`

This work order may be written in its current documentation path. Production
code, tests, Skills, registry, accepted chain, campaign state and HANDOFF are
read-only unless a real structural failure requires a separate TDD work order.

## 4. Ordered execution

### Task 0 — Freeze and preflight

1. Hash every frozen input and fail closed on drift.
2. Record current HEAD/status and tool versions.
3. Validate `revision_0012` with the public global editorial state validator.

### Task 1 — Soundtrack evidence

1. Run public `tools/soundtrack_probe.py` on the preview BGM.
2. Preserve the preview-only legal boundary in the mix plan and every handoff.
3. Do not infer a delivery licence from local availability or prior CapCut use.

### Task 2 — Audio composition

1. Build a public `audio_mix_plan` covering 385.00 sec.
2. Reuse the preview BGM in bounded consecutive placements; do not time-stretch.
3. Preserve the full 385 sec speech timeline WAV at unity gain.
4. Use `speech_aware` ducking with an initial `duck_db=-18`, 80 ms attack and
   350 ms release. BGM baseline volume must be restrained (`0.16–0.22`).
5. Execute with `tools/audio_mix_plan_execute.py`.
6. Require protected-speech waveform evidence PASS and audible recovery outside
   speech windows.

### Task 3 — Candidate composition

1. Start from the frozen picture base, not the review-captioned preview.
2. Mux the mixed audio and burn only the exact owner-approved 12-cue SRT through
   the existing public `video_tools.py merge-final` path using
   `--subtitle-text-policy exact`.
3. Do not burn segment review captions.
4. Do not add invented copy, teacher roster or new factual claims.
5. Output `canon67_385s_multimodal_candidate_v1.mp4` and a composition manifest.

### Task 4 — Objective Stage 7 Verify

Run the existing public objective checks applicable to a review candidate:

- ffprobe media health/read-back;
- exact subtitle text/timing audit;
- protected speech continuity/binding check;
- rendered-product QA under the preview-only audio contract;
- final-product verification in review-candidate scope;
- black/decode checks;
- candidate/input hash read-back.

The known picture-tail one-frame deviation must remain a separate FAIL finding.
It is non-blocking only for this internal owner review candidate.

### Task 5 — Stage 8 eye/ear/heart review packet

1. Probe the candidate soundtrack with the public soundtrack probe.
2. Run `tools/timeline_review_packet.py` with:
   - `--review-subject-type current_candidate`
   - `--interval-sec 0.5`
   - `--wall-duration-sec 30`
   - the candidate soundtrack probe
   - the owner-approved SRT
   - `--text-authority owner_approved`
3. Inspect every generated wall, not a sample.
4. Produce findings only in:
   `objective | structural_candidate | taste`.
5. Reviewer checks must cover:
   - chapter/story progression against revision 0012;
   - non-adjacent semantic repetition and misplaced event families;
   - subtitle presence/readability and speech timing;
   - music level/recovery/ducking around seg08;
   - effect/title lifecycle visible in rendered pixels;
   - final landing.

### Task 6 — One bounded revision or stop

- If objective evidence fails, stop at the last green state.
- If Reviewer finds one locally reversible mix/text defect, one bounded revision
  is allowed without changing picture/story truth, followed by affected checks.
- Structural story/picture findings stop for Owner; do not silently recut.
- No second music search, no new engine and no route bypass.

## 5. Acceptance

Technical PASS requires all of the following:

- frozen hashes match;
- public audio mix execution succeeds;
- BGM covers the full 385 sec and speech-aware ducking is evidenced;
- protected speech is complete and preserved;
- 12/12 owner-approved subtitle texts and bindings match;
- candidate is decodable H.264/AAC and review-candidate QA passes;
- every 0.5 sec wall is generated and reviewed;
- Reviewer outputs traceable findings with time/evidence references;
- no segment-review caption is present in candidate;
- BGM provenance is explicitly preview-only;
- `human_creative_approval=false`;
- `final_delivery_claimed=false`.

Final state may be set to
`WAITING_OWNER_CANON67_385S_MULTIMODAL_CANDIDATE_VERDICT` only after the above
evidence exists. Creative quality and public-delivery legality remain UNKNOWN.

## 6. Validation policy

- No production-code change is planned; do not run the full suite merely for
  run artifacts.
- Run focused checks for the public tools actually used plus `git diff --check`.
- If production code must change, stop and open a separate red-first TDD plan.
- Never weaken a gate, handwrite a private renderer, or claim a waiver as PASS.
