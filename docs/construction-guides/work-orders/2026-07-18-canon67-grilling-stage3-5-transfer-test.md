# Work Order: Canon 67 grilling-to-Stage-5 transfer test

Date: 2026-07-18
Owner: `main-pipeline` integrator
Worker profile: LUNA high or equivalent bounded paper-edit worker
Target state: `WAITING_INTEGRATOR_CANON67_GRILLING_STAGE3_5_TRANSFER_REVIEW`

## 0. Goal

Test whether the newly hardened Stage 0–2 interactive ambiguity method can
carry an owner-approved conversation into Stage 3 material binding and a Stage
5 reviewable paper edit without losing its intent.

This is a **transfer test**, not a new Canon 67 canonical revision. Produce a
fresh sandbox proposal and a short storyboard preview. Do not create a full
candidate, perform a canonical Stage 6 render, choose licensed music, operate
CapCut, approve creative quality, or claim delivery.

## 1. Read first and freeze

Read completely:

1. `AGENTS.md`
2. `RUNBOOK.md`
3. this work order
4. `skills/editorial-ambiguity-loop.md`
5. `skills/material-map.md`
6. `skills/editing-loop-director.md` sections L0/L1 only

Freeze and read back these source artifacts:

| Artifact | SHA-256 |
|---|---|
| `skills/editorial-ambiguity-loop.md` | `e11988ebc4aaf460726d1432440a24cd413c7a301e92fa3555f3910c3704d86d` |
| `.tmp/canon67_editorial_reconstruction_v2/accepted/project_material_map_v3.json` | `704a1fed801218530d206665bf906f67a60ad28f216e3c954ee195b23775962c` |
| `.tmp/canon67_540s_route_acceptance/stage5/paper_edit_v1/owner_verdict.json` | `80505a3c70d1a351316081528b83b8bd17b2782312fe933ca064ed697947749c` |
| `.tmp/canon67_540s_route_acceptance/stage6/paper_edit_preview_v1/canon67_385s_shifted_speech_subtitles.srt` | `31af574bbd9273e87a2d90672dfbbd0937a0a58a0f3389f479357b9c796ea244` |
| `C:/Users/user/Downloads/微電影素材/_整理後/主任勉勵/IMG_2145.MOV` | `85baeafce7d3d7fbeb56c1a354b9edaf2ee500ab4285bf56893b906c49f9cfcb` |

Record pre-work HEAD and `git status --short --branch`. Stop on a frozen hash
mismatch. Do not reuse the old 385-second clip order, source-window order, or
BGM placement as the new proposal.

## 2. Owner and forbidden zones

Owner zone:

`.tmp/canon67_grilling_stage3_5_transfer_v1/**`

Everything else is read-only, including source media, accepted artifacts,
production code, tests, Skills, registry, docs, Git index/history,
`HANDOFF_CURRENT.md`, and campaign state.

This evidence-only sandbox does not need an execution companion or strict
receipt DAG. Do not add either. Do not commit, stage, push, upload, or mutate
source media.

## 3. Frozen interaction answer sheet

Treat the following as owner-approved for this transfer test only:

1. Product: external-audience graduation results report.
2. Story spine: progressive capability formation, not chronology or an
   activity catalogue.
3. Text hierarchy: narrative chapter cards plus replaceable factual training
   labels. Unknown official names remain proposed/UNKNOWN.
4. Coverage: mention every evidence-supported category; develop only 4–6 core
   units. Material shortage shortens the film and never authorizes repetition.
5. Target length: 380–410 seconds; never pad to 540 seconds.
6. Six chapters, in order: discipline-and-safety, basic-skills,
   advanced-practice, integrated-training, group-life,
   graduation-and-responsibility.
7. Opening: pole lift → live-line work → cable teamwork → disciplined
   formation; full-frame words `規模 / 專業 / 協作 / 紀律`; then
   `第67期養成班 / 結訓成果影片`.
8. Supervisor speech: exact 39.34-second talking-head picture and source audio,
   with all 12 approved captions. It is not narration and must have no cutaway.
9. No additional AI narration. Use cards, music, short original-sound accents,
   and the supervisor speech.
10. Audio design: chapter-level cues from 4–5 music sources; speech always wins;
    actual tracks and licences remain UNKNOWN.
11. Visual language: industrial documentary through the training chapters,
    then warm retro photographic recollection.
12. Placement-preference footage: only a 6–8 second `活動紀實` inside group
    life, video followed by two or three photos; it carries no story turn.
13. Ending: retro photos plus three short reflection passages, then one clean
    full-group photo and the approved copy `第67期養成班｜結訓` /
    `每一次準備，都是穩定的開始。` No MemoryPhotoWall is required.
14. Only class 8 has class/adviser media. Do not create a partial class or
    adviser roll. A true whole-cohort final photo is allowed.

Do not reopen these decisions. Preserve the owner's correction that the
supervisor must remain visibly speaking for the complete approved window.

## 4. Task A — Compact Stage 0–2 proposal

Under the owner zone create:

- `stage2/story_decision_packet.proposed.json`
- `stage2/segment_story_contract.proposed.json`
- `stage2/evidence_need_map.proposed.json`
- `stage2/interaction_compaction_audit.json`

The three proposal artifacts must follow the existing schemas and bind one
another by relative path and SHA-256. The audit maps every numbered decision
above to its exact downstream field(s) and reports any omitted or altered
meaning as FAIL.

Run the public Stage 2 validator and write:

`stage2/stage2_ambiguity_gate_report.json`

Required: exit 0, `stage2_completion=PASS`, `ready_for_stage3=true`. This is
schema/lineage readiness only, not creative approval.

## 5. Task B — Evidence-bound Stage 3 retrieval

Use the accepted Material Map v3 and registered public retrieval/ranking
surfaces. Do not re-review the full 283-asset pool and do not hand-pick around
the ranker.

Create:

- `stage3/retrieval_ranking_report.json`
- `stage3/core_unit_coverage.json`
- `stage3/rejected_candidate_log.json`

The coverage report must distinguish complete micro-stories, montage-only
families, and unsupported/provisional labels. At minimum, independently check
the known cable sequence (`IMG_8190`, `IMG_8194`, `IMG_8195`, `IMG_8218`), the
pole/live-line/height families, discipline/safety, group-life, the full speech
anchor, and the final whole-group photo.

Filename/folder text is prior, never visual truth. No selected source window may
repeat merely to meet target length.

## 6. Task C — Stage 5 paper edit and method handoffs

Create one 380–410 second proposed paper edit:

- `stage5/l1_picture_plan.proposed.json`
- `stage5/opening_effect_intent.proposed.json`
- `stage5/chapter_caption_plan.proposed.json`
- `stage5/music_cue_plan.proposed.json`
- `stage5/ending_effect_intent.proposed.json`
- `stage5/repetition_and_family_report.json`
- `stage5/stage2_to_stage5_lineage_audit.json`

Every selected clip needs stable ID, chapter, evidence role, asset/scene ID,
source hash, source window or still hold, timeline window, observed content,
selection reason, and evidence refs. Related activity families stay contiguous.
Non-adjacent semantic repetition must be reported, not only adjacent duplicate
assets.

Effect and music artifacts are **intent handoffs**, not renderer commands. They
must preserve the opening words, the industrial-to-retro visual change, the
no-narration rule, original-sound accents, speech priority, and simplified
retro-photo ending.

## 7. Task D — Review-only storyboard

Build a review-only matrix adapter inside the owner zone from existing reviewed
keyframes and their evidence refs. Do not generate a new private tool.

Run the registered `tools/rough_cut_storyboard_preview.py` to create:

- `review/storyboard_preview.mp4`
- `review/storyboard_preview_report.json`
- `review/owner_review_index.md`
- `review/owner_verdict_template.json`

Use 1.0–1.5 seconds per selected clip, 1280×720, no audio. Overlay review-only
chapter/unit captions when the public tool can express them; otherwise put an
exact timeline caption table in the owner index and report the limitation.

The preview is for order, grouping, repetition, and information-flow review. It
is not the 380–410 second final render and cannot prove timing taste.

## 8. Acceptance

Run focused checks only:

```powershell
C:\Users\user\miniconda3\python.exe -m unittest `
  tests.test_editorial_ambiguity `
  tests.test_material_retrieval `
  tests.test_material_rough_cut `
  tests.test_picture_plan_retrieval_gate `
  tests.test_rough_cut_storyboard_preview -v
C:\Users\user\miniconda3\python.exe tools\skill_tool_contract_audit.py --json
git diff --check
```

Also verify by read-back:

- all JSON/Markdown/SRT is UTF-8 with no replacement characters or suspicious
  Chinese question-mark runs;
- all frozen hashes match;
- Stage 2 gate passes and cross-artifact hashes match;
- proposed timeline is contiguous and totals 380–410 seconds;
- every selected source exists and source hash matches Material Map v3;
- every picture clip is in its role-specific public Top-K with zero overrides;
- no exact or overlapping source window is reused without an explicit callback;
- supervisor picture/audio is one continuous 39.34-second talking-head window
  with 12/12 caption bindings and no cutaway;
- no partial class/adviser roll exists;
- no full candidate/final render, music download, or CapCut project exists;
- pre/post Git status is identical.

Do not run the full suite because production code/tests are read-only.

## 9. Report and stop-loss

Write:

- `final/command_log.json`
- `final/artifact_sha256.json`
- `final/worker_report.md`

Report PASS/FAIL/UNKNOWN separately, exact commands/exit codes, artifacts,
deviations, skips, blind spots, and pre/post Git status.

One LOCAL correction is allowed per actual failure class. On recurrence, stop
that stream as STRUCTURAL at the last green state. If a public surface cannot
express the accepted decision, write `final/factory_gap.json`; do not modify
production code or create a private bypass.

Keep:

- `human_creative_approval=false`
- `final_delivery_claimed=false`

Legal success state:

`WAITING_INTEGRATOR_CANON67_GRILLING_STAGE3_5_TRANSFER_REVIEW`

