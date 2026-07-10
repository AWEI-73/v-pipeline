# Editing Loop L0/L2/L3/L4 Certification Campaign Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. Do not use subagents: the campaign has shared candidate state and sequential owner gates.

**Goal:** Repair the two verified L5 audit-contract mismatches, then certify evidence-carrying L2, L0, L3 and L4 first-of-kind loops on real Canon 67 material before one bounded L0→L5 integration flight.

**Architecture:** This is one sequential campaign, not a new orchestrator. `skills/editing-loop-director.md` supplies the control doctrine; existing V Pipeline public capabilities do the work; `.tmp/editing_loop_certification_campaign/**` carries versioned candidates, evidence and six-field decisions between loops. Every creative or transcript decision stops at an owner gate.

**Tech Stack:** Python 3.11, `unittest`, existing Hermes V Pipeline modules and CLIs, ffmpeg/ffprobe, faster-whisper, JSON/Markdown evidence, Git.

## Global Constraints

- Product authority: `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`.
- Execution doctrine: `skills/editing-loop-director.md`.
- No route runner, driver service, timeline v2, journal, finding registry, automatic reroute or CapCut GUI automation.
- Raw material under `C:\Users\user\Downloads\微電影素材\_整理後` is read-only; `67期結訓影片-終.mp4` and `66期學長音樂檔/**` are reference-only and must never become candidate footage.
- `human_creative_approval=false` and `final_delivery_claimed=false` throughout this campaign.
- A worker report is not acceptance. The integrator independently checks code diff, commands, hashes and rendered evidence.
- Existing dirty-tree files are unrelated and byte-preserved.

## File Map

- Modify `video_pipeline_core/timeline_invariants.py`: recognize explicitly generated visual sources as valid trace evidence.
- Modify `tests/test_timeline_invariants.py`: red/green coverage for generated-source trace and genuinely missing trace.
- Modify `video_pipeline_core/new_visual_information_audit.py`: read the formal timeline duration contract while retaining legacy duration inputs.
- Modify `tests/test_new_visual_information_audit.py`: red/green coverage for `target_duration_sec` and timeline in/out fallback.
- Write `.tmp/editing_loop_certification_campaign/**`: all experimental proposals, owner verdicts, candidates, fresh audits and campaign reports.
- Modify maturity/result paragraphs in `docs/construction-guides/2026-07-10-editing-loop-product-spec.md` and `skills/editing-loop-director.md` only after an owner/integrator certifies a first-of-kind scope.
- Create `docs/pilots/2026-07-11-editing-loop-<loop>-first-of-kind-evidence.md` only after the matching owner/integrator verdict.

---

### Task 1: h01 Generated-Source Timeline Trace Compatibility

**Files:**
- Modify: `tests/test_timeline_invariants.py`
- Modify: `video_pipeline_core/timeline_invariants.py`

**Interfaces:**
- Consumes: formal timeline clips with `source_lineage.generated=true` and a non-empty `generated_background` or equivalent explicit generated source descriptor.
- Produces: unchanged `audit_timeline(...)` return contract; generated clips pass `clip_trace_present`, while untraced clips still fail.

- [ ] **Step 1: Add the red test**

Add a test using the actual poetry-card shape from Canon 67: stable `id`, `source_type="generated_background"`, `source_lineage={"generated": True, ...}`, `generated_background={"color": "black"}`, timeline in/out, and no file path. Assert `clip_trace_present=pass`. Keep `test_missing_trace_fails` unchanged.

- [ ] **Step 2: Prove red**

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_timeline_invariants -v
```

Expected before implementation: nonzero exit; the new generated-source test fails because `_has_trace` only accepts `trace`, `source_path` or `file`.

- [ ] **Step 3: Implement the narrow predicate**

Change `_has_trace(clip)` only enough to accept either existing path/trace evidence or explicit generated lineage backed by a non-empty generated visual descriptor. A bare `source_type="generated_background"` or `generated=True` without a descriptor must not pass.

- [ ] **Step 4: Prove green and retain the negative case**

Run the Task 1 command again. Expected: exit `0`; both the new generated-source test and `test_missing_trace_fails` pass.

- [ ] **Step 5: Commit Task 1 only**

Stage exactly the two Task 1 files and commit with a focused message. Do not stage pre-existing dirty files.

### Task 2: h02 Formal Timeline Duration Compatibility

**Files:**
- Modify: `tests/test_new_visual_information_audit.py`
- Modify: `video_pipeline_core/new_visual_information_audit.py`

**Interfaces:**
- Consumes duration in priority order: positive `duration_sec`, positive `extract_dur`, positive `target_duration_sec`, then non-negative `timeline_out_sec - timeline_in_sec`.
- Produces unchanged `audit_new_visual_information(...)` result shape and legacy compatibility.

- [ ] **Step 1: Add two red tests**

Add one test with distinct formal clips using `target_duration_sec` and one test using only timeline in/out. Assert ratio `1.0` and PASS. Do not weaken the repeated-scene failure test.

- [ ] **Step 2: Prove red**

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_new_visual_information_audit -v
```

Expected before implementation: nonzero exit; formal clips total to zero under the old two-field reader.

- [ ] **Step 3: Add one private duration reader**

Use one private helper for both total and per-item duration. Reject negative or inverted fallback durations as `0.0`; preserve the public function signature and report schema.

- [ ] **Step 4: Prove focused and adjacent green**

Run:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest tests.test_new_visual_information_audit tests.test_video_tools_audits -v
```

Expected: exit `0`.

- [ ] **Step 5: Commit Task 2 only**

Stage exactly the two Task 2 files and commit separately from Task 1.

### Task 3: Re-run the Two L5 Objective Audits on the Frozen Candidate

**Files:**
- Create: `.tmp/editing_loop_certification_campaign/hardening/**`

**Interfaces:**
- Consumes: frozen `.tmp/loop_f1_blind_reproducibility/candidate_v2/run/timeline_build.json`.
- Produces: fresh timeline-invariants and new-visual reports plus input hash/read-back evidence.

- [ ] **Step 1: Freeze source hashes and git state**
- [ ] **Step 2: Run `video_tools.py timeline-audit` and `new-visual-audit` into the campaign Owner Zone**
- [ ] **Step 3: Verify `opening_poetry_card` no longer causes a null trace failure and total visual duration is nonzero**
- [ ] **Step 4: Run both focused test modules together and `git diff --check`**
- [ ] **Step 5: Write the hardening report and continue only if every objective item is PASS**

### Task 4: L2 Title-Lifecycle First-of-Kind

**Files:**
- Create: `.tmp/editing_loop_certification_campaign/l2/**`
- Later, after certification only: `docs/pilots/2026-07-11-editing-loop-l2-first-of-kind-evidence.md`
- Later, maturity paragraphs only: Product Spec and Editing Loop Skill

**Interfaces:**
- Consumes: frozen candidate_v2, approved `docs/pilots/2026-07-10-opening-0044-script-v1.md`, and open finding `l5_f01`.
- Produces: proposal → owner verdict → exactly one effects-layer title-lifecycle diff → candidate_l2 → fresh lifecycle/render/semantic evidence → final owner verdict.

- [ ] **Step 1: Freeze candidate_v2 and reconstruct its repo-owned render invocation from existing provenance**
- [ ] **Step 2: Produce a title-lifecycle proposal and visual timing evidence without changing the candidate**
- [ ] **Step 3: Stop at `WAITING_OWNER_L2_APPLY_VERDICT`**
- [ ] **Step 4: After explicit approval, render only the approved title lifecycle in a new candidate directory**
- [ ] **Step 5: Prove picture, audio, poem, montage and duration are semantically unchanged**
- [ ] **Step 6: Run fresh lifecycle QA, rendered QA and a before/after dynamic**
- [ ] **Step 7: Stop at `WAITING_OWNER_FINAL_L2_TASTE_VERDICT`; certify only after owner/integrator PASS**

### Task 5: L0 Real-Material Interview Selects First-of-Kind

**Files:**
- Create: `.tmp/editing_loop_certification_campaign/l0/**`
- Later, after certification only: `docs/pilots/2026-07-11-editing-loop-l0-first-of-kind-evidence.md`

**Interfaces:**
- Consumes: read-only real-source inventory and raw `主任勉勵/**` plus training B-roll; catalog `missing` is candidate evidence, never approval.
- Produces: indexed candidate sheets/walls, manifest with relative paths and hashes, semantic tags, blind spots, agent proposal and owner-approved selects.

- [ ] **Step 1: Verify real files and exclude all reference-film paths**
- [ ] **Step 2: Build fresh indexed evidence for supervisor-speech and cutaway pools with EXIF/media-duration handling**
- [ ] **Step 3: Propose one bounded dialogue excerpt and a small cutaway pool; record why and what was not heard/seen**
- [ ] **Step 4: Stop at `WAITING_OWNER_L0_SELECTS_VERDICT`**
- [ ] **Step 5: After owner approval/delegation, write approved selects and six-field provenance**
- [ ] **Step 6: Prove every selected path exists, hashes match, and no reference footage entered the manifest**

The approved manifest must expose
`dialogue_select.source_relative_path`, `dialogue_select.source_in_sec`,
`dialogue_select.source_out_sec` and `cutaway_selects[]`; later phases consume
these exact fields rather than guessing a filename.

### Task 6: L1 Bridge for the Interview Picture Cutaway

**Files:**
- Create: `.tmp/editing_loop_certification_campaign/interview/picture/**`

**Interfaces:**
- Consumes: owner-approved L0 dialogue excerpt and cutaway selects.
- Produces: one bounded picture candidate whose dialogue timeline is continuous while picture may cut to B-roll.

- [ ] **Step 1: Propose stable-ID picture windows without modifying audio**
- [ ] **Step 2: Stop at `WAITING_OWNER_INTERVIEW_PICTURE_VERDICT`**
- [ ] **Step 3: Apply only the approved picture plan using existing compile/render capabilities**
- [ ] **Step 4: Prove source-dialogue timing and selected source hashes are unchanged**

This task consumes the already-certified L1 shape; it does not broaden L1 certification or resolve `l5_f03`.

### Task 7: L3 Dialogue-Preserving Audio First-of-Kind

**Files:**
- Create: `.tmp/editing_loop_certification_campaign/l3/**`
- Later, after certification only: `docs/pilots/2026-07-11-editing-loop-l3-first-of-kind-evidence.md`

**Interfaces:**
- Consumes: owner-locked interview picture candidate, original dialogue audio and one already-authorized music source if available.
- Produces: audio mix plan, acceptance evidence, mixed candidate, preservation/ducking/loudness proof and owner preview.

- [ ] **Step 1: Write an audio proposal that keeps original speech continuous and ducks or mutes music under dialogue**
- [ ] **Step 2: Stop at `WAITING_OWNER_L3_MIX_VERDICT`**
- [ ] **Step 3: Execute the approved plan through `tools/audio_mix_plan_execute.py`; do not handcraft final audio with an undocumented ffmpeg command**
- [ ] **Step 4: Prove audible source-speech continuity, picture hash preservation, stream presence and audio acceptance**
- [ ] **Step 5: Stop at `WAITING_OWNER_FINAL_L3_LISTENING_VERDICT`; certify only after owner/integrator PASS**

### Task 8: L4 ASR-Draft to Approved-Subtitle First-of-Kind

**Files:**
- Create: `.tmp/editing_loop_certification_campaign/l4/**`
- Later, after certification only: `docs/pilots/2026-07-11-editing-loop-l4-first-of-kind-evidence.md`

**Interfaces:**
- Consumes: selected raw dialogue excerpt and L3 candidate.
- Produces: fresh ASR probe, agent repair suggestions, verbatim owner-approved transcript, final SRT, caption/source-speech QA, subtitled candidate and final owner verdict.

- [ ] **Step 1: Run fresh faster-whisper evidence with `tools/soundtrack_probe.py --enable-asr`; label it draft**
- [ ] **Step 2: Run `tools/agent_transcript_repair.py`; keep every suggestion `agent_draft_not_approved`**
- [ ] **Step 3: Stop at `WAITING_OWNER_L4_TRANSCRIPT_APPROVAL` with a readable transcript packet**
- [ ] **Step 4: After verbatim owner approval, build final SRT only from approved text**
- [ ] **Step 5: Run `video_tools.py caption-audit` and `tools/source_speech_subtitle_qa.py`, then burn/render subtitles through an existing public capability**
- [ ] **Step 6: Prove picture/audio continuity, exact text read-back and subtitle timing; stop at `WAITING_OWNER_FINAL_L4_TEXT_VERDICT`**

### Task 9: Bounded L0→L5 Integration Flight

**Files:**
- Create: `.tmp/editing_loop_certification_campaign/integration/**`
- Later, after owner/integrator acceptance only: `docs/pilots/2026-07-11-editing-loop-integration-flight-evidence.md`
- Later, result paragraphs only: Product Spec and Editing Loop Skill

**Interfaces:**
- Consumes: certified L0 selects, L1 picture bridge, L2 title candidate, L3 audio, L4 text and existing L5 doctrine.
- Produces: one two-slice evidence bundle proving each loop consumed confirmed deltas and carry-forward, plus fresh L5 review packets. The opening/L2 slice and interview/L0-L4 slice are not silently joined into a new story edit.

- [ ] **Step 1: Build an integration manifest from existing artifacts; do not invent a new registered envelope**
- [ ] **Step 2: Verify each carried evidence ref resolves and each protected hash matches**
- [ ] **Step 3: Review the two bounded candidates as a bundle; make no combined film unless a later owner-approved script explicitly requires one**
- [ ] **Step 4: Run applicable objective QA plus L5 perception/review fresh**
- [ ] **Step 5: Stop at `WAITING_OWNER_FINAL_INTEGRATION_VERDICT`**
- [ ] **Step 6: After owner verdict, write durable evidence and maturity updates without claiming full-film quality or delivery**

## Self-Review

- Spec coverage: h01/h02, L2 finding repair, real-material L0, dialogue L1 bridge, L3 preservation/ducking, L4 fail-closed transcript, L5 integration and all owner gates are represented.
- Placeholder scan: later candidate IDs are intentionally outputs of earlier owner-approved phases, not guessed placeholders; no code surface is authorized without a verified gap.
- Type consistency: all loops carry the existing four context sources plus six decision fields; no new registered state contract is introduced.
