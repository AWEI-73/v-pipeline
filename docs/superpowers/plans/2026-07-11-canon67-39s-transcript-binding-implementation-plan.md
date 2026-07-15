# Canon 67 39s Transcript Binding — Implementation Plan

> **For the executing agent:** use test-driven development and execute the tasks in order. Stop at the last green state when a repeated failure class or an owner gate is reached.

**Goal:** Repair the existing ASR → agent repair → human-approved transcript → actual L4 subtitle chain, then regenerate the 0.00–39.34s owner transcript review packet without rendering a candidate.

**Architecture:** Keep the existing three production capabilities and add backward-compatible v2 binding at their seams. The probe adapter explicitly recognizes the current nested soundtrack-probe shape; the human decision artifact binds source hash/window and approved cues; source-speech QA parses the actual run-local SRT and compares it to that decision. No route, orchestrator, registry, renderer, or Skill is added.

**Runtime:** `C:/Users/user/miniconda3/python.exe`, Python `unittest`, existing ffmpeg and `tools/soundtrack_probe.py`.

**Campaign root:** `.tmp/editing_loop_39s_integrated_campaign/`. The existing `.tmp/editing_loop_certification_campaign/` tree is read-only historical evidence.

---

## Task 1: Make nested soundtrack-probe cues a supported input

**Files**

- Modify: `tests/test_source_speech_transcript_repair.py`
- Modify: `video_pipeline_core/agent_transcript_repair.py`
- Modify: `tools/agent_transcript_repair.py`

1. Add a test whose fixture matches `features.vocal_analysis.segments` and assert `write_agent_transcript_repair_for_run()` writes the same non-zero cue count and a non-empty draft SRT.
2. Add a CLI test or directly test `main(argv)` for a new opt-in `--require-cues` mode; zero cues must return a non-zero exit while legacy invocation remains compatible.
3. Run the targeted tests and capture the expected RED caused by zero adapted cues.
4. Add one explicit nested-shape fallback inside the probe adapter. Preserve top-level `segments/items/cues` precedence; do not add recursive schema guessing.
5. Implement `--require-cues` as an opt-in fail-closed mode.
6. Re-run the targeted tests to GREEN.

Targeted command:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_source_speech_transcript_repair -v
```

## Task 2: Add a backward-compatible bound human-review decision

**Files**

- Modify: `tests/test_source_speech_transcript_repair.py`
- Create: `tests/test_write_human_transcript_review_decision.py`
- Modify: `video_pipeline_core/human_transcript_review_decision.py`
- Modify: `tools/write_human_transcript_review_decision.py`

1. Add RED tests for an approved v2 payload with this minimum shape:

```json
{
  "decision": "approved",
  "reviewer": "human",
  "reviewed_draft": "subtitles.draft.srt",
  "source_binding": {
    "source_path": "<IMG_2145.MOV>",
    "source_relative_path": "主任勉勵/IMG_2145.MOV",
    "source_sha256": "85BAEAFCE7D3D7FBEB56C1A354B9EDAF2EE500AB4285BF56893B906C49F9CFCB",
    "window_start_sec": 0.0,
    "window_end_sec": 39.34
  },
  "approved_cues": [
    {"cue_id": "cue01", "start_sec": 0.0, "end_sec": 2.0, "approved_text": "核准文字"}
  ]
}
```

2. Tests must reject missing/invalid SHA-256, invalid or out-of-window cue timing, duplicate cue ids, blank approved text, and a source or reviewed-draft hash mismatch at write time.
3. Preserve legacy v1 callers when no v2 fields are supplied. If any v2 binding field is supplied, require the complete v2 contract; partial v2 must fail closed.
4. The normalized v2 artifact stores `version: 2`, the complete source binding, ordered approved cues, `reviewed_cue_ids`, and the computed `reviewed_draft_sha256`.
5. Add `--payload-file <utf8-json>` to the existing writer. It must use the same production builder/writer, not a second schema path. Keep legacy CLI flags working.
6. Run RED, implement the minimum code, then run GREEN.

Targeted command:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_write_human_transcript_review_decision -v
```

## Task 3: Verify approved cues against the actual L4 SRT

**Files**

- Modify: `tests/test_source_speech_subtitle_qa.py`
- Modify: `video_pipeline_core/source_speech_subtitle_qa.py`
- Modify: `tools/source_speech_subtitle_qa.py`
- Reuse without modification unless a failing test proves otherwise: `video_pipeline_core/caption_audit.py`

1. Add a RED test showing that approved text `APPROVED` and actual subtitle text `WRONG` currently pass.
2. Add RED tests for strict mode with a missing/legacy decision, missing actual SRT, cue count/order mismatch, text mismatch, timing mismatch, and source hash/window mismatch. Add one GREEN case where only SRT line wrapping differs.
3. Extend `write_source_speech_subtitle_qa_for_run(..., require_approved_text_binding=False)`. When strict binding is requested, or when a v2 decision exists, load `human_transcript_review_decision.json`, parse the actual run-local `subtitles.srt` with `caption_audit.parse_srt`, and use those parsed cues for equality. Do not trust copied `subtitle_cues` as actual-output evidence. In strict mode, missing/legacy decision or missing SRT blocks.
4. Normalize whitespace only (`" ".join(text.split())`); do not normalize characters, punctuation, homophones, or wording. Compare cue timing within an explicit maximum tolerance of 0.002s.
5. Emit blocking rules for missing decision/SRT, source-binding mismatch, cue-set mismatch, text mismatch, and timing mismatch. Report whether approved-text equality was actually checked.
6. Add opt-in `--require-approved-text-binding` and `--strict-exit` CLI flags. The former selects the v2 requirement; the latter makes a blocking report return non-zero. Legacy invocation remains compatible.
7. Run RED, implement the minimum code, then run GREEN.

Targeted command:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_source_speech_subtitle_qa tests.test_caption_audit -v
```

## Task 4: Focused regression and true-shape forward test

1. Run the combined affected suite, then `git diff --check`. Do not run the full suite in this phase.
2. Under `.tmp/editing_loop_39s_integrated_campaign/capability_forward_test/`, copy the existing true-shape probe and prove `--require-cues` yields non-zero cues.
3. Prove three negative cases through production APIs in required-binding mode: one changed approved character, one changed source hash, and one shifted cue time all block. Preserve their JSON reports as evidence.
4. Commit only the scoped production/test files after all affected checks are green. Do not stage pre-existing dirty files.

Combined command:

```powershell
C:/Users/user/miniconda3/python.exe -m unittest tests.test_source_speech_transcript_repair tests.test_write_human_transcript_review_decision tests.test_source_speech_subtitle_qa tests.test_caption_audit -v
```

## Task 5: Resume Wave P and stop at the real owner gate

1. Revalidate `IMG_2145.MOV` SHA-256 as `85BAEAFCE7D3D7FBEB56C1A354B9EDAF2EE500AB4285BF56893B906C49F9CFCB` and duration coverage through 39.34s.
2. Extract exactly `0.00–39.34s` to `wave_p/source_speech_0_39_34.wav`; run one fresh ASR with the existing public soundtrack probe, then run transcript repair with `--require-cues`.
3. Create an owner review template carrying every cue id, start/end, raw ASR, agent suggestion, uncertainty, and blank `approved_text`. This is a review input, not an approval artifact.
4. Validate UTF-8, non-zero cues, cue timing within 0.00–39.34s, source binding, hashes, and evidence paths.
5. Upload only the WAV, owner review template, repair suggestions, and a manifest to a new review subfolder under Drive folder `1dCNkMOYtxUlJraumLPY8-ZIB7aoJX-fb`. Read back the uploaded names/ids/hashes where supported.
6. Stop at `WAITING_OWNER_39S_TRANSCRIPT_VERDICT`. Do not write `human_transcript_review_decision.json`, render subtitles, build candidate_39s, run Wave R, or claim creative/delivery approval.

## Final evidence to report

- Red and green command/exit evidence for Tasks 1–3.
- Scoped diff/commit and pre/post dirty-tree status.
- True-shape non-zero cue count and the three negative QA reports.
- 39-second source/audio/probe/repair/template/manifest paths and hashes.
- Drive folder URL and uploaded file ids, or an honest upload blocker.
- Explicit `human_creative_approval=false` and `final_delivery_claimed=false`.
