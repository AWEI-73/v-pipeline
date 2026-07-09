# 2026-07-08 Shot-Level Material Proof Completion Report

## Result

Status: completed as no-render shot-level proof package with limitations.

Output root:

```text
.tmp\shot_level_material_proof_completion_20260708-080727
```

The run did not render final media and did not write `story_human_review_decision.json`.

## Source Preflight

Real source folder:

```text
C:\Users\user\Downloads\微電影素材\_整理後
```

Preflight result from `source_preflight.json`:

- exists: true
- is_dir: true
- file_count: 306

## Red-First Evidence

Command:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json,sys; from pathlib import Path; p=Path('.tmp/soul_first_real_material_planning_20260708-060509/render_facing_shot_plan.json'); data=json.load(open(p,encoding='utf-8')); views=data.get('views',[]); missing=[]; req=['shot_id','source_relative_path','asset_kind','planned_duration_sec','raw_or_compiled_risk']; for i,v in enumerate(views): ..."
```

Exit code: 1

Evidence:

```text
render_facing_views 18
missing_required_shot_level_fields 90
```

The prior soul-first render-facing plan was beat-level only and lacked per-shot IDs, source-relative paths, asset kind, planned shot durations, and raw/compiled risk classification.

## Artifacts

Generated under the fresh output root:

- `shot_level_material_proof_plan.json`
- `shot_pool_inventory.json`
- `compiled_source_risk_audit.json`
- `certification_gap_completion_plan.json`
- `supervisor_transcript_review_packet.md`
- `supervisor_transcript_review_packet.json`
- `render_rehearsal_entry_packet.json`
- `shot_level_review_packet.md`
- `production_line_completion_map.json`
- `final_artifact_check.json`
- `source_preflight.json`
- `generation_command_log.json`
- `frame_evidence\*.jpg`

Frame evidence count: 35.

## Shot Pool Summary

Total shot-level candidates: 35.

Risk summary:

- raw_usable: 27
- compiled_reference_only: 6
- needs_human_review: 2
- reject_for_primary_proof: 0

Section counts:

- opening_story: 3 candidates, 2 raw usable, 1 compiled/reference
- training_mv: 21 candidates, 18 raw usable, 3 compiled/reference
- supervisor_source_speech: 3 candidates, 1 compiled/reference, 2 needs human review
- teacher_class_intro: 4 candidates, 4 raw usable
- closing_story: 4 candidates, 3 raw usable, 1 compiled/reference

## Compiled-Source Risk Audit

`compiled_source_risk_audit.json` marks compiled/final/music-folder sources as not allowed for primary proof. These items remain visible as reference/support evidence only and are not silently promoted.

Classification counts:

- raw_usable: 27
- compiled_reference_only: 6
- needs_human_review: 2
- reject_for_primary_proof: 0

## Certification / Check Gap

`certification_gap_completion_plan.json` status:

```text
thin_blocked_for_primary_proof
```

Decision:

```text
do_not_promote_old_compiled_certification_video_as_primary_proof
```

Allowed next handling:

- shorten the certification/check beat
- use standards/check bridge language
- search for or collect raw certification/check material

Blocked handling:

- do not use the compiled music-folder certification video as primary proof
- do not claim certification visual proof without raw source evidence

## Supervisor Transcript Review

`supervisor_transcript_review_packet.json` status:

```text
blocked_pending_human_transcript_review
```

The supervisor source-speech route remains blocked because the transcript is not human-approved. The candidate takes may be used only as silent/support visual, or omitted from a formal source-speech segment until human transcript review is completed.

## Render Rehearsal Entry Recommendation

`render_rehearsal_entry_packet.json` recommends:

```text
music_subtitle_only
```

Profile status:

- `music_subtitle_only`: ready_with_limitations, requires_voxcpm=false
- `source_speech_plus_music`: blocked, requires_voxcpm=false, blocker: supervisor transcript review required
- `narrated_optional`: blocked, requires_voxcpm=true, blocker: VoxCPM lead-in provider issue not resolved for delivery narration

The next render rehearsal can proceed only as `music_subtitle_only`, with visible limitations for certification/check proof, source speech, and music/legal review.

## Production-Line Completion Update

`production_line_completion_map.json` in the fresh output root records:

- shot_level_material_proof_layer: partial
- ready_route: music_subtitle_only
- next_render_rehearsal_entry_point: music_subtitle_only five-minute rehearsal after human review of `shot_level_review_packet.md` and acceptance of certification shortening
- new blockers:
  - supervisor_transcript_review_required_for_source_speech_plus_music
  - certification_raw_proof_thin

## Acceptance Commands

Red-first precheck:

```powershell
C:\Users\user\miniconda3\python.exe -c "<prior render_facing_shot_plan missing-field precheck>"
```

Exit code: 1, expected red-first failure.

Artifact generator:

```powershell
C:\Users\user\miniconda3\python.exe -
```

Exit code: 0.

Final artifact check:

```powershell
C:\Users\user\miniconda3\python.exe -c "import json; from pathlib import Path; root=Path('.tmp/shot_level_material_proof_completion_20260708-080727'); check=json.load(open(root/'final_artifact_check.json',encoding='utf-8')); print(json.dumps(check,ensure_ascii=False,indent=2)); raise SystemExit(0 if check.get('status')=='ok' else 1)"
```

Exit code: 0.

UTF-8/no-corruption check:

```powershell
C:\Users\user\miniconda3\python.exe -c "from pathlib import Path; root=Path('.tmp/shot_level_material_proof_completion_20260708-080727'); bad=[]; count=0; ..."
```

Exit code: 0.

Output:

```text
checked 12
bad []
```

Git diff check:

```powershell
git diff --check
```

Exit code: 0.

Output contained existing CRLF warnings only for unrelated tracked files:

```text
warning: in the working copy of 'docs/branch-contract-registry.json', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/branch-contract-registry.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/pipeline-decision-tree.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'docs/video-pipeline-operating-map.md', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'tests/test_graduation_film_blueprint_catalog.py', LF will be replaced by CRLF the next time Git touches it
warning: in the working copy of 'video_pipeline_core/graduation_film_blueprint_catalog.py', LF will be replaced by CRLF the next time Git touches it
```

## Final Artifact Check

`final_artifact_check.json` status:

```text
ok
```

Verified:

- fresh output root exists
- no final/rendered media was created
- all required artifacts exist
- every beat has candidate shots or an explicit decision
- compiled/final/music-folder sources are not primary proof
- certification/check has an explicit gap decision
- supervisor transcript review packet exists
- no-narration profile does not require VoxCPM
- generated JSON/Markdown text decodes as UTF-8 with no replacement characters or suspicious repeated question marks

## Deviations

- No reusable code or tests were added. The work order delegated whether to add tools; this execution used a pinned-Python run-local generator because the requested outcome was a no-render artifact package and no code defect was required to complete it.
- The generated proof package classifies 6 items as `compiled_reference_only`, rather than treating them as raw proof. This is intentional and follows the stop-loss rule.
- The shot-level proof layer is `partial`, not `ready`, because certification/check and supervisor source speech remain blocked/thin.

## Blockers

- Certification/check has only old compiled/reference evidence and remains `thin_blocked_for_primary_proof`.
- Supervisor source speech remains `blocked_pending_human_transcript_review`.
- `source_speech_plus_music` route remains blocked.
- `narrated_optional` route remains blocked by unresolved VoxCPM lead-in/provider issues.
- Music/legal approval is not claimed.

## Next Recommended Work

Review `.tmp\shot_level_material_proof_completion_20260708-080727\shot_level_review_packet.md`.

If the certification/check shortening is accepted, start a `music_subtitle_only` five-minute render rehearsal from `.tmp\shot_level_material_proof_completion_20260708-080727\render_rehearsal_entry_packet.json`.

If a stronger source-speech route is desired, resolve supervisor transcript review first and collect or identify raw certification/check proof before rendering.
