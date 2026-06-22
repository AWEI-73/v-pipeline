---
title: Hermes Video Pipeline ??Canonical Roadmap
type: project
status: active
updated: 2026-06-14
tags: [project, video, pipeline, roadmap, agent-workflow]
---

# Hermes Video Pipeline ??Canonical Roadmap

> ?祆?隞嗆撠??臭??瑟? roadmap???餌? `REVIEW_REPORT*`?video_pipeline_architect_review.md`
> ??`HANDOFF_NEXT_SESSION.md` ????隢歇?游??圈ㄐ嚗?蝥?agent ?芸?霈?祆???
> `HANDOFF_CURRENT.md`?RUNBOOK.md`?README.md`??

---

## Current Frontend Integration State (2026-06-17)

- Dashboard = node/status/review surface.
- Workbench = interactive preview/patch/handoff surface.
- Workbench writes draft artifacts only.
- Official render remains ffmpeg/backend.
- Current cleanup focus: integration contract, layout stability, artifact
  handoff, and technical-debt reduction.

---

## 2026-06-14 Executive Status

**Current accepted baseline:** M0-M4 material-aware planning and the M5 true
render are stable enough to pause. The 67th result is accepted as a
material-limited baseline, not as proof of human-edit-quality parity.

**M6a contract layer COMPLETE** (2026-06-14, evidence: 791 tests OK at round 3).
VD0 shallow-label storage also complete.

**MM1 COMPLETE** + **BA1 COMPLETE** (2026-06-14, Codex re-review passed). BA1
motion_graphics consumer corrected to the `contract_adapter` build path (Node 14
is scaffold/flow-grouping only).

**BR1 Opening / Hook Sequence Builder implemented** (2026-06-14):
`opening_sequence.py` compiles an approved recipe (hook ??context montage ??
sound-punctuation cue ??title reveal ??story entry) into render-plan clips that
are **prepended to the plan and reindexed**, so it changes both timeline and
true render. Graceful fallback drops beats with no material. Consumed via `script["opening_recipe"]` in `run_mv`.

**SRP1 Segment Sequence Recipe Planner COMPLETE** (2026-06-15):
Automatically plans a deterministic sequence recipe (`plan_segment_sequence`) from approved local map-ranked slots when no manual beat recipe is provided. Restructures timeline slots using the existing BR2 compiler while preserving correctness ranking, visual family diversity, and window integrity. Fully validated with dynamic video/photo renders.

**SRP2 Opening / Hook Auto Planner COMPLETE** (2026-06-16):
A deterministic SHALLOW opening planner ??NOT full story understanding or aesthetic
direction, only a re-organization of approved story slots.
`opening_recipe_planner.plan_opening_recipe(script, approved_story_plan)` derives a
runtime-ephemeral opening recipe (hook ??context_montage ??title_reveal ??story_entry,
scaled to the qualified-candidate count) from the already-approved story-plan slots and
hands it to the existing BR1 `compile_opening_sequence`, which PREPENDS it to the plan
and reindexes `slot_index` (so it changes both timeline and true render). The original
story timeline stays fully intact and the original script is never mutated.

Safety (inherited from SRP1): a manual `script["opening_recipe"]` ALWAYS wins (auto
stands down); only approved, scene_id-bearing, renderable slots are eligible (GAP /
missing source / source_speech / keep_audio / hold / fallback-only / illegal-window
excluded); correctness (retrieval_score) is never overridden by diversity preferences
(diversity is a same-tier soft tie-break only); no material is re-retrieved and no
source / scene_id / window / evidence is invented; title text comes only from explicit
`script.opening_title` / `script.title` (never fabricated); evidence / window / photo
lineage is preserved on the prepended opening clips (BR1 `_shot_clip` now carries the
same lineage fields as BR2 `_beat_clip`); and because the planner runs AFTER the
per-segment loop it never pollutes VD2 / SRP1 shared history. Compiler-empty /
`ValueError` / `TypeError` ??graceful fallback that keeps the story plan with a
diagnostic trace; `RuntimeError` and other unexpected exceptions propagate. No new
schema, no second opening compiler, no hard gate. Out of scope and NOT
started: SRP3 story-arc / emotional planner, VERIFY?UILD revision loop, VD3,
dashboard/UI, Node 14 / effects.

**SRP2 selection + duration-budget hardening** (2026-06-16): (1) **scene_id
uniqueness** ??qualified candidates are deduplicated by `scene_id` (keeping the
best correctness-ranked occurrence) BEFORE the opening shape is decided, so a
repeated scene_id can neither inflate `qualified_candidate_count` nor pad a beat;
the same source with a different scene_id/window is still a distinct approved
shot. (2) **Same-tier role selection** ??roles are now filled correctness-first
and greedily (each role takes the highest remaining retrieval_score tier; a lower
score never jumps a higher one for an angle/family preference), with soft
preferences applied ONLY within a tier: hook prefers close?edium?ide??
video?cene_id; context prefers an unused visual_family?ide?edium?lose??
video?cene_id; the title base prefers an unused scene_id and a different family.
Missing family/scale degrades deterministically. (3) **target_sec whole-film
budget** ??before prepending, `run_mv` computes `story_duration` and the compiled
opening duration; with no `target_sec` behavior is unchanged; when the story +
opening would exceed `target_sec`, `trim_opening_for_budget` drops extra context
??then title_reveal ??then shortens the hook (never below a legal positive
duration, never expanding a video window, never touching approved story slots),
and falls back to no opening if no legal hook fits ??so the auto opening can never
push the plan past the whole-film target. Manual openings keep their existing
behavior (no auto budget policy). The `opening_plan.execution` trace records
`target_sec`, `story_duration`, `requested_opening_duration`,
`applied_opening_duration`, and `dropped_for_budget`. Validated with the A?
falsification suite incl. a budget-bounded dynamic-photo true render (plan and
rendered file both stay within `target_sec`): focused **44 tests**; full
regression **1177 tests OK**.

**AR1 Runtime Planning Extraction COMPLETE** (2026-06-16): a ZERO-behavior-change
refactor (not a new feature, not a new Pipeline framework). `run_mv` in
`mv_cut.py` was a ~400-line god-function; its planning logic is now extracted into
clear private helpers with explicit inputs/returns and no module-global state:
`_plan_story_timeline` (per-segment dispatch, SRP1/BR2 auto+manual beat sequence,
anti-presentation, slot trace + slot_index, and the VD2 shared-history update ??
a fresh local list each call), `_apply_opening_bookend` (manual BR1 + SRP2 auto
opening + target_sec budget), `_apply_ending_bookend` (BR4 ending), and
`_finalize_timeline` (edit-point planning + motion snap). `run_mv` is now a
~110-line orchestrator: normalize ??analyze music / allocate ??plan story ??apply
opening ??apply ending ??finalize ??render / state / result. The `run_mv` public
signature and the result schema are unchanged, and SRP1 / SRP2 / VD2 / BR1 /
ending / target_sec behavior is byte-for-byte identical (locked by a new
`tests/test_ar1_run_mv_characterization.py` A? suite incl. a real ffmpeg render;
full regression **1193 tests OK**). This only establishes the runtime planning
boundaries needed before SRP3 ??it does NOT start SRP3. Audio Graph V2, test
tier-ing, and the VERIFY?UILD revision loop remain deferred.

**SRP3 Story Arc / Emotional Progression Planner COMPLETE** (2026-06-16): a
whole-film-level, SHALLOW, DETERMINISTIC arc planner ??NOT semantic story
understanding and NOT an auto-director. `story_arc_planner.plan_story_arc(script)`
derives arc roles (setup ??challenge ??progression ??climax ??resolution, scaled
to the segment count) from segment ORDER and explicit manual metadata only, and
emits per-segment BUILD planning hints (arc_role, intensity, pace_hint,
weight_multiplier). `apply_story_arc_hints` applies them to a runtime script copy
BEFORE `allocate_segments`, so the hints feed the existing duration allocation and
story planning. SRP3 never re-picks material, never touches the material map or
correctness ranking, never reorders/drops/?ewrites segments, and builds no hard
gate; it is a runtime-ephemeral plan (no new canonical schema).

Manual intent always wins, with the final hardened contracts (2026-06-16):
- **Manual `arc_role` is conservative**: a segment that declares `arc_role` has
  SRP3 derive NOTHING for it ??no auto weight / pace / intensity / source. The
  manual role is preserved and never relabeled auto (no ambiguous "manual role,
  auto rhythm" state).
- **Duration-protected segments never get a BUILD-rhythm hint**: a `hold` /
  `hold_reason` / `source_speech` / `keep_audio` / `diegetic` / `duck` segment
  receives neither auto `weight` nor auto `pace`, even at a progression/climax
  position; only trace-only `arc_role` / `arc_intensity` may be stamped.
- **Auto weight/pace** apply only to an auto-role, non-protected segment: weight
  when no manual `weight` and no positive `requested_duration_sec`; `pace="fast"`
  for a fast role with no manual `pace` (engine pace vocabulary is {fast, hold}).
- **Manual intensity precedence**: a manual `intensity` / `arc_intensity` is
  preserved and SRP3 writes no conflicting auto `arc_intensity`.
- **Every auto-applied field is traceable**: the segment and the
  `story_arc_plan.execution.applied` trace record `story_arc_applied_fields`
  (e.g. `["arc_role","arc_intensity","weight","pace"]`). This SAME key,
  `story_arc_applied_fields`, is the consistent projection across the runtime
  segment, the `story_arc_plan.execution.applied` trace, and the stamped final
  story slots / per_seg entries, so downstream can see exactly which BUILD fields
  SRP3 derived. (The concrete auto `weight`/`pace` VALUES live on the segment and
  in `execution.applied` ??they are allocation inputs, not slot fields.)

`story_arc=false` / `disable_auto_story_arc=true`, fewer than 3 segments,
non-object segments, **missing / blank / None / NaN / 簣Infinity / non-unique
segment identity** (identity is fail-closed and accepts only a non-bool int, a
finite float, or a trimmed non-blank string ??there is no segment_index fallback
for the runtime trace join), pure-source_speech, and pure-stock scripts are
`not_applicable` and the existing flow is unchanged. The auto hints are applied
atomically to a trial copy (committed only on success); expected
ValueError/TypeError leave the un-applied runtime script + a fallback trace,
RuntimeError propagates, and the original input script is never mutated. `run_mv`
gains one backward-compatible result key, `story_arc_plan`; produced story slots /
per-segment entries carry `arc_role` / `arc_intensity` / `story_arc_source="auto"`
/ `story_arc_reason` / `story_arc_applied_fields` trace (opening/ending evidence is
never arc-tagged). The final duration decision still belongs to
`allocate_segments` ??SRP3 only nudges relative weights, so total story duration
and `target_sec` are preserved (climax outweighs setup). Validated by an A?
falsification suite plus the final hardening reverse proofs (protected-at-climax,
identity fail-closed incl. NaN/簣Inf, manual-role derives nothing, manual-intensity
precedence, execution?lot trace consistency) incl. a 5-segment dynamic-photo true
render proving climax story duration > setup; focused **47 tests** (35 planner +
12 runtime); full regression **1240 tests OK**. NOT started: Agent/VLM story
understanding, script rewrite, segment reorder/drop, VERIFY?UILD revision loop,
VD3, Audio Graph V2, Dashboard/UI/Node 14/effects.

**SRP Acceptance Replay COMPLETE** (2026-06-16): a reproducible, controlled
validation that the accumulated BUILD thickness (M6 + VD2 + Photo renderability +
SRP1/SRP2/SRP3 over AR1's `run_mv`) produces a traceable, watchable timeline/render
difference on controlled material ??NOT a proof the cut is "good", and NO new
editing capability. `tools/srp_acceptance_replay.py --gemini-root <dir>` builds a
canonical `project_material_map` from the controlled Gemini photo set (7 needs +
3 distractors, all real PNGs at absolute paths) + a 7-segment montage script +
lavfi music, then runs `run_mv` twice with identical inputs: **baseline** (VD2 /
SRP1 / SRP2 / SRP3 off via the minimal disable flags `disable_visual_diversity` /
`disable_auto_sequence` / `disable_auto_opening` / `story_arc:false`, keeping
map-ranked retrieval + photo renderability so both cuts use the same photos) and
**enhanced** (all on). Both are??ffmpeg rendered. Four planning-only
single-capability isolation runs give honest per-capability attribution. Artifacts
go to the gitignored `.tmp/srp_acceptance/`: `baseline|enhanced/final.mp4` +
`timeline.json`, `comparison_report.{json,md}`. Every DECLARED manifest image is
fail-closed: a single missing / empty / unreadable declared image BLOCKS the whole
replay (non-zero) ??the controlled set is never silently down-sampled into a
"successful" report. **Render content is verified at the SLOT level, not just
exists/non-empty.** Root cause of a prior fake render (a red opening card, blue
mid card): `run_mv` writes its `mvseg_<slot_index>.mp4` intermediates into the
SHARED `tempfile.gettempdir()` keyed only by slot_index, so a concurrent/prior
`run_mv` (incl. the test suite's solid-color renders) collided on those names and
the concat spliced in foreign red/blue color clips. Fixed by giving each
acceptance `run_mv` an ISOLATED `mat_dir` (`.tmp/srp_acceptance/<variant>/_work/`)
??no core render change. The gate now BLOCKS unless, for EVERY plan slot, the
frame sampled at that slot's mid time is non-monochrome (max per-channel spatial
stdev ??10 ??a solid red/black/white card scores ~0) AND basically correlates
(grayscale Pearson ??0.08) with that slot's OWN source photo; a coarse whole-video
check is also kept. `slot_render_checks` records every slot (slot_index, segment,
opening_role/beat_role, scene_id, source, sample_time, stdev, best_correlation,
ok, reason) + summary (checked_slots, failed_slots, ok). This catches the
"timeline correct but render faked (flat color card)" mode the previous
4-frame-whole-video sample skipped over. The controlled set's images are JPEG data
with a `.png` extension (`mjpeg`/`yuvj420p`); after the mat_dir fix they render as
real photo content from frame 0 (0.5s/1.5s/3.0s no longer color cards;
all 14 baseline / 15 enhanced slots pass). First run: enhanced timeline ??
baseline; VD2 active
(consecutive same-family runs 7??), SRP1 active (beat sequences in all 7 chapters),
SRP2 active (opening prepended), SRP3 active (climax 3.606s > setup 2.496s) with
total duration / `target_sec` preserved and GAP=0. The report does NOT claim
distractors are excluded ??an off-topic distractor's subject terms can still
overlap a segment query, so the report instead DISCLOSES whether any distractor
was actually used (`distractor_usage`): on this set both cuts selected the
duplicate-assembly and bad-group distractors, because BUILD-time VD2 does not
dedup / reject distractors (that is the VERIFY-side `semantic_novelty_audit`'s job,
out of scope this round). The minimal disable flags default to existing behavior
(zero change when unset) and add no new editing capability. No new canonical
schema, no M6 gate / delivery / material-map-contract change, no Node 14 / effects
/ Dashboard / Audio Graph, no 67th footage. Focused harness tests **27**; full
regression **1267 tests OK**.

**67th real-footage SRP sanity replay COMPLETE** (2026-06-16): `tools/srp_real67_sanity.py`
formalizes the ad hoc 67th probe. It first rebuilds the M6e fixture from
`M6E_FOOTAGE` / `--footage-root`, then uses the M6e **covered subset** artifacts
(`.tmp/m6e/out_C/generated_mv_script.json` + `project_material_map.json`) to run
the same real `.MOV` sources twice: **baseline** (VD2/SRP1/SRP2/SRP3 disabled,
map-ranked retrieval still enabled) and **enhanced** (all enabled). Outputs are
gitignored under `.tmp/srp_real67/`: `baseline/final.mp4`,
`enhanced/final.mp4`, both `timeline.json`, and
`comparison_report.{json,md}`. Real run evidence on the 67th covered subset:
baseline render **6.967s**, enhanced render **10.5s**, timelines differ,
enhanced auto opening **planned** with 2 opening clips, enhanced story arc
**planned/applied**, slot render checks pass for **3/3 baseline** and **5/5
enhanced** slots. Honest boundary: this is only the M6e 3 accepted-scene covered
subset, not the full 304-file ingest and not an aesthetic score. Because each
covered segment has only one approved scene, SRP1 auto sequence has **0**
eligible segments and SRP3 cannot prove climax > setup on this subset
(setup/climax/resolution all 2.295s); those are reported as material-shape
limits, not failures. The slot gate is adapted for real video: a low-variance
near-white frame is allowed only when it strongly matches its own source frame,
so legitimate bright source cards do not false-block while foreign color-card
renders still fail. Focused tests **8** (35 with the existing SRP acceptance
harness); full regression **1275 tests OK**. Formal replay passed with
`python tools/srp_real67_sanity.py --footage-root <67th-material-dir>` (fresh M6e
rebuild, no stale fixture).

**67th review-demo canonical need-aware hardening COMPLETE** (2026-06-16):
Claude review found the earlier review harness had been masking production
schema drift by stamping `scene.need_id` from `satisfies[]`. Core retrieval now
reads canonical `material_fit.need_refs[]` and `scene.satisfies[].need_id`
directly, and the review demo no longer stamps scene-level need ids. Replayed
with `tools/srp_real67_review_demo.py --skip-m6e`: final **11.3s**,
`all_matched=True`, `drift=[]`, report states
`canonical satisfies evidence; no scene need_ids stamped`. The short duration
and odd representative shots remain a covered-subset/window-quality limitation:
3 accepted scenes, one scene per need, 0 SRP1-eligible segments, not a full
ingest or aesthetic verdict. Focused tests **51**; full regression **1307 tests
OK**.

**Gemini enhanced-only demo film COMPLETE** (2026-06-16): `tools/gemini_demo_film.py`
runs the node-shaped flow from controlled Gemini material into one rendered demo:
script/needs -> project material map -> BUILD/SRP -> render -> review report. It
does **not** run a baseline comparison and adds no editing capability; it is a
single enhanced demo proving an agent can fill parameters and drive the existing
pipeline from manifest to final video. Command:
`python tools/gemini_demo_film.py --gemini-root <gemini-material-dir> --target-sec 75`.
Artifacts are gitignored under `.tmp/gemini_demo_film/`: `final.mp4`,
`generated_mv_script.json`, `project_material_map.json`, `timeline.json`, and
`review_report.{json,md}`. Real run evidence on the 36-image controlled Gemini
set: requested **75.0s**, rendered **75.6s**, plan **75.0s**; 36 assets across 7
needs; SRP2 opening **planned**; SRP1 auto sequences in **7/7** segments; SRP3
**planned/applied**; slot render check **25/25 pass**. The demo script declares
`pacing.preferred_shot_sec=[2.8,3.4]` so allocation stays in the 60-90s range
without changing SRP1's approved-window integrity. Honest boundary: this is
synthetic Gemini material, not 67th real footage and not an aesthetic verdict.
The report explicitly discloses distractor usage; this run used
`distractor_duplicate_assembly` in segment 1 and `distractor_bad_group_photo` in
segment 7, which is review evidence rather than a silent success. Focused tests
**6** (41 with SRP acceptance/sanity harnesses); full regression **1281 tests OK**.

**Gemini demo semantic-alignment review COMPLETE** (2026-06-16): the demo report
now maps every selected non-opening slot back to the manifest `need_id` and the
script segment's `need_ref`. It reports per-segment `matched_slots`,
`wrong_need_slots`, `distractor_slots`, `matched_ratio`, and `semantic_drift`
(drift when matched ratio < 0.5 or any distractor is used). Follow-up
need-aware retrieval now consumes explicit `segment.need_ref`,
`material_fit.need_ref`, or canonical `material_fit.need_refs[]` against
canonical `scene.satisfies[].need_id` (accepted/candidate only) as correctness
evidence before text/function/pace fallback. Legacy `scene.need_id` /
material-map `need_id` are fallback only. This is not prompt-time semantic
guessing: the agent may write/review the labels, but BUILD uses the
deterministic join key. Wrong-need text matches remain available only as
fallback when no matching need evidence exists. Replayed result on the current
Gemini demo improved from historical drift **[1, 2, 3, 7]** to **[]**:
all 24 story slots match their expected need and no distractors are selected.
The final timeline also preserves `need_id` through map-ranked slots, SRP1 beat
clips, and SRP2 opening clips. Focused tests cover need-priority, fallback,
canonical satisfies-edge lookup, and lineage preservation. Focused tests **134**;
full regression **1286 tests OK**.

**Gemini demo review subtitles COMPLETE** (2026-06-16): the enhanced demo script
now writes per-segment review subtitles (`Seg N | need_id theme`) into the story
text layer, `run_mv` burns non-auto subtitles at the bottom of rendered clips, and
the demo emits `review_subtitles.srt` beside `final.mp4` for easier manual review.
This is review affordance only; it does not alter material selection, gates, or
semantic scoring. Focused tests **134**; full regression **1288 tests OK**.

**Do not start:** M6a lineage integration, `material_delta`, the complete Visual
Diversity Guard. Do not expand the MM1 contract further.

**Do not start yet:** M5c designed sequences, M5d human-vs-agent automation,
M5e rerender, effects expansion, CLIP hard dependency, or further 67th-specific
sensory tuning.

**Gate policy:**

- Tier 1 blocks objective invalid delivery: unsupported capability, unresolved
  required-material gap, script overreach, wrong proof material, technical
  VERIFY failure, and unreadable/defective render.
- Tier 2 provides quality evidence: perceptual composition repetition, action
  progression, pacing, designed-sequence quality, and human sensory judgment.
- A tier-2 proxy is not promoted to tier 1 from unit tests or one case.

External review handoff:
`docs/archive/decisions/2026-06-14-roadmap-course-correction.md`.

## 2026-06-13 Active Direction: Material Phase(???移?芣??M0-M4)

**?暹????*:Sensory S1-S4 + bakery ?游?撽撌脫??026-06-13 ?祕摮詨蝝?
獢?(???犖?芸???閬?`docs/archive/reviews/2026-06-13-student-vs-agent-montage-review.md`
??`??spec-weight-assessment.md`)?文?:蝯???蝔??脫郊,**?芾摩?釭 VERIFY 銝?**??
??潛:撟曆?瘥仃??蝟餌絞鋆⊿撌脫?閮??券(broll_audit ?? fail?????GAP??
?嗅??寥?),**雿??遙雿???瘙箇?甈?*;銝??砍靘策閰摯?停?輯姥?,?澆
??銴??′鋆???

**?迨?祇?畾萇??芸?摨:?策閮?瘙箇?甈?M0)??蝯虫?蝯衣?銵?M1)?敺???
?啣頛舀???M2/M3)??* ?挾??璅?(?閰摯?勗?,??):

```text
?喃蝙敶梁?霈,銋?雿輻?航炊蝝???
?喃蝙蝡?皜?,銋???蝝?蝖祈?????
?喃蝙??頛陛??銋Ⅱ靽??挾?賡?迤蝣箔?頞喳???閬箄???
```

??OpenMontage(reference repo)**??敹?*(corpus ??甈⊿蝺?LIP ????
silence jump-cut)??*AGPL v3,銝銵Ⅳ?賭??舀?????import**,?券 clean-room ?芸神??

### M0 閬瘙箇?甈???芸?;?券?臬瘜?銝神?啣頛航??

```text
M0a capability_manifest.json(????蝯??神):
    `python video_tools.py capability-manifest` 敺?撘Ⅳ撣豢敶楊:
      transitions      = video_pipeline.ALLOWED_TRANSITIONS
      still_treatments = edit_artifacts._STILL_TREATMENT_MODES
      sfx_cues         = sfx.ASSET_COUNTS keys(whoosh/hit/riser)
      patch_types      = visual_review ??window/crop/treatment
      audio_policies   = duck/music(+M2d 敺? source_speech)
      render_profiles / providers(stock|local|generated + 隤祕閬???)
      judge_modes      = agent|ollama|none
      unsupported      = multi_track_music, arbitrary_effects, full_nle_ui,
                         cloud_vlm_default, remotion_backend(璈?航???)
    skills/spec-contract.md 憓???詻??? manifest(銝?銴雁霅瑟???;
    director/writer skill ??銝銵神 SPEC ??霈 manifest??
M0b spec_review ?啗???B5(out_of_capability):??閬? manifest 瘝????
    ??blocking,??manifest 頝臬???餈?瘜潦??訾??犖撠勗?舀?????隞嗚?
M0c 閬銝惜??閰摯?勗???撅?蝺券脰???metadata,銝???):
      tier1 銝??:隤?甇?Ⅱ/靘?隤祕/proof 銝???嗅?銝???GAP 銝?蝜?
                      銝???蝖祈??/VERIFY ?餅?銝?鈭支?
      tier2 ?釭?格?:??蝯?/?⊿?/蝭憟???瘥??啗?閮?
      tier3 憸冽?末:?格??/?寞?/摮?憸冽/頧/?單?/?脩?
    ?萄?:tier3 銝?憯?tier2,tier2 銝?憯?tier1??*target_length ?芣迨?
    tier3**??霈郊蝯?max_honest_duration(M1),銝??舐′閬???
M0d 鈭支?蝖祇?(?祆活獢???乩耨敺??券?胯策?Ｘ?閮?瘙箇?甈?:
      broll_audit fail(max_source_repeats/unique_source_ratio)??銝?
        complete_review_final,next_action 蝬剜? fix 頝舐(dashboard waterfall 瘨祥)
      ?嗅?/??caption/?∪???梁? local 蝒???planner ?(stock ??
        _STOCK_OFF_TOPIC_FLOOR ??local 蝑??
      蝝??啣?璅?GAP ?挾 ???芾 await_material / 蝮桃 / ?神,銝?隞?
        ???嗡?靘??∟憛怨?
      editorial_qa / ?芾摩?釭 VERIFY fail ????,銝?璅?complete
      暺?/餈征?賢?瑼Ｘ葫(?銵撩?瑞?,tier1):??撌脣祕雿?black_frame_audit.py
        (ffmpeg signalstats ?賣見 YMIN/YMAX/YAVG ??black: avg??6;
        blank: avg??35 銝?range??2;run??.4s ??fail)? delivery_gate
        HARD_AUDITS + dashboard node 12;CLI `video_tools.py black-frame-audit`??
        ?葡撽?:暺??賣葫閰衣??◤?,敶拇?銋暹楊?瘜圾蝣潭??⊥??見??
        fail-closed?????桀?撠?舀??????質閮剛??～?閮勗???
        ?隞乩???tier1 ??? SPEC ??timeline ??憿臬?靘?嚗??賡??葫??
      proof/identity/testimony 畾?core.proof_critical / identity_sensitive)
        ??撘瑕韏?node 10.5 judge,瘝? accept verdict ????敺?timeline
        (wrong-proof-material ?瘜???瘣餌??舫?撠望????靘?
M0e ?Ｘ? SPEC 甈??格(閰摯?勗??????蔥/??/蝘駁???銝甈⊥?:
    撠?spec_contract schema + 撖行?????雿?銝?(隤唳?鞎餅捱蝑?隤圈?霅?
    ????蝔?隞暻?,銝??征 ??蝘駁?蔥甈??Ｗ甈?皜?
    docs/archive/decisions/spec-field-census.md,銋??唳?雿????SPEC??
摰??斗?:??2026-06-13 獢???run artifacts ???漱隞???????M0d
銋?敹?韏唬???complete(鋡怠????閬神?脫葫閰?;甈?皜?閬? 100% ?暹?甈???
```

M0 status (2026-06-13): COMPLETE. `capability_manifest.json` is generated
from runtime constants; `spec_review` B5 blocks unsupported required
capabilities and emits tier metadata; target length is documented as tier 3;
failed existing audits and unresolved material GAPs now block delivery through
`delivery_gate`; zero-score local matches remain honest GAPs; SPEC field census
is recorded in `docs/archive/decisions/2026-06-13-spec-field-census.md`.

Verification: focused M0 suite passed; full suite `672 tests OK`; replay of
`20260612-232948-story-mv` resolves to `pass=false`, `next_action=curator`,
blocked by failed `broll_audit` and unresolved live-line segment 7 GAP.
M1 status (2026-06-13): COMPLETE. Deterministic material maps now record
per-asset scenes, speech/silence runs, motion peaks, optional scene captions /
bridge labels, and opt-in transcript text. `supply_review.json` estimates
effective shots, unique sources, function coverage, and
`max_honest_duration_sec`; its conservative fallback counts each positive
unscanned coverage pick as one useful window and rejects zero-score picks.
`spec_review` B6 blocks script duration above evidenced supply.

Verification: focused M1 suite passed; full suite `685 tests OK`; replay of the
11-minute `20260612-232948-story-mv` run marked segment 7 and the old zero-score
segment 8 as GAP, all remaining segments as thin, and B6 emitted 20 tier-1
`script_overreach` blockers with `ready_for_build=false`.

Next: M2.

### M1 蝝?靘?撣?supply-before-script:靘策瘙箏??輯姥)

```text
?箏?(銝???:caption-meta + E7 agent ?云憟??詻etect_shots(PySceneDetect)??
keyframe_grid?ilter_static_windows 撟撌格??瑯apcut_backend._parse_silencedetect
(?砍???亙神蝚砌?隞??roll_audit(靘???蝯梯?撌脣?????
M1a `video_tools.py material-map <src>`(蝣箏????唳芋蝯?material_map.py):
      scenes[]  start/end/midpoint thumb(detect_shots)
      speech[]  silencedetect ? talk/silence runs
      motion[]  瘥?scene 撟撌株??閬?S1a/S2a 璈)
    頛詨 materials/maps/<asset_id>.map.json;materials_db 閮?map 頝臬?;?芰???
M1b ??scene caption:瘝輻 E7 ?拇芋撘??砍 VLM ?身 / agent 閬芰?),撖怠?
    map.scenes[].caption;agent 銴???bridge 璅?(閬?M3c)??
M1c 靘?撣?supply_review.json,?摰阮?? blocking 蝭暺?:
    瘥?蝭/畾菔閮?(閰摯?勗???schema ?扳):
      required_effective_shots = requested_duration / target_shot_sec
      estimated_effective_shots(map.scenes ??⊿;?抒?蝬?P5 憭?撅?
        ?憭? 2;??靘???蝒?*銝?憭見??*,unique source ?西?)
      required_functions 閬?(establish/action/detail/result/reaction
        ?誑 caption ?閰??蝎?憿?銝?蝎暹?,瘙撩??閬?
      max_honest_duration_sec?easibility(ok|thin|gap)??
      recommended_action(ok|shorten_or_merge|reshoot|await_material)
M1d spec_review ?啗???B6(script_overreach):蝡??輯姥蝘 > max_honest_duration
    ??blocking;撠??芾蝮桃/?蔥/?????柴??祆隢曇甇斤靘策瘙箏???
M1e (opt-in)transcript:faster-whisper(撌脣摮?頝臬?)撠?speech runs 撣嗆??
    頧神,撖?map.speech[].text?ound-bite 瑼Ｙ揣?啣;?芸?鋆?map 隞??氬?
摰??斗?:撠?2026-06-13 獢?蝝???靘?撣?摰???箝暑蝺?gap??瘣餅挾=thin??
撱箄降蝮桃????擗?30s 蝡?+2 ?臬蔣??3 撘萇,B6 ??銝衣策??max_honest_duration??
```

### M2 蝒蝝炎蝝?+ ?啗?閮祟閮?鋆?詨?蝚砌???

```text
?箏?(銝???:_plan_matched_segment/_windows_from_clip?ontent_qa.score_segment
(?賊冗?)?isual judge node 10.5 + needs_patch?roll_audit??
M2a ?蝒? map.scenes ???誨??脣?):瘥?scene 靘?pace ??0-2 蝒?
M2b 蝣箏??扳?摨(material_retrieval.py):?閰?(caption/transcript ?
    visual_desc)+ ? fit + ? fit;????勗神?脣(蝯?judge ??
    montage ?葆,?航圾??? caption/?嗅? ??銝?(M0d ??銝虜????
M2c (opt-in)CLIP ??:?砍 clip-vit-base-patch32 撠?top-K cosine ??,
    ??model_routes "ranker";?芸?鋆 M2b??*ranker ?芣?摨?judge ??瘙?*??
M2d sound-bite:segment 摰?? audio.role=source_speech(keep_audio)???蝒?
    ?芾?箄 speech runs,蝡舫??賊??亦?(??transcript ?典???∪? silence ??)??
M2e new_visual_information 撖抵?(閰摯?勗????賢,?游? visual_fatigue/
    broll_audit,銝韏瑞???:
      ??皞?啁?敹?頝?scene ??撌?> ?曉???scene ?? ???圈??
      new_visual_information_ratio / repeated_visual_hold_sec ??audit 頛詨
      fail ??M0d ??鞎?銝? complete)
摰??斗?:?? visual_desc???餌??vs map 瑼Ｙ揣?/B montage 蝯?judge 鋆捱;
2026-06-13 獢???皞?23 甈～ M2e 銝???fail 銝西◤????
```

M2 status (2026-06-13): COMPLETE. Scene-level retrieval now ranks material-map
scenes by caption relevance, sequence function, pace/motion fit, and an optional
external ranker that may rerank but cannot admit zero-evidence scenes. The
matched planner automatically loads maps recorded in `materials_db`, selects
ranked scene windows, and emits `scene_id` plus retrieval score. `source_speech`
segments preserve audio and select mapped speech runs, preferring transcript
evidence. `new_visual_information_audit.json` measures new-visual ratio and
repeated visual hold, appears in dashboard/editor review, and blocks delivery.

Verification: focused M2 suites passed; full suite `699 tests OK`; replay of
`20260612-232948-story-mv` failed M2e with
`new_visual_information_ratio=0.4781` and
`repeated_visual_hold_sec=331.531`, exposing the repeated photos and repeated
source-time windows behind the unnatural edit.

Next: M3.

### M3 ??鋆?(鋆?詨?蝚砌???隤 + ?? + ?Ｘ?璈挾)

```text
M3a snap ?芸?摨??edit_artifacts.snap_to_edit_point ?Ｘ?璈):
    keep_audio 蝒???speech ?? > scene cut > motion peak;??keep_audio 銝???
M3b jump-cut(雓店?瑟挾?西澈):`jumpcut-plan <src>` 霈 map.speech ??
    jumpcut_plan.json(mark 璅∪??芣?銝)??agent ?詨(瘝輻 verdict ??
    accept/needs_patch 隤?)??`jumpcut-apply` ??materials/processed/<id>.mp4
    閮?lineage?peed_up 璅∪???backlog??
M3c ???????畾?閰摯?勗??犖憿?撅?典?瑯?撠銵?):
      ???訾?:map.motion ?賡??脩???rise/peak/settle;M2a ?箇???
        cut-in 撠?rise?ut-out 撠?settle 銋?(S2a 撜啣澆?????游?)
      ?Ｘ?璈挾:M1b agent 銴?? scene ??bridge(蝝??批歇?末??
        ?寞?/摮/璈挾)??閰?scene ?芾?湔挾?冽?銝,銝????
    銝?:頝函??????摮貊??犖?拙???閫?隤祕璅酉?箔??挾)??
摰??斗?:?祕雓店蝝??游 vs jump-cut A/B ?賣?銴;隤脩?畾菔 A/B
(?箏?蝘 vs ??撠?)??judge ?券?撖漲 montage 鋆捱??
```

M3 status (2026-06-13): COMPLETE. Render planning now treats mapped speech,
scene boundaries, and motion peaks as ordered edit-point evidence. Clips with
`keep_audio` expand to complete intersecting speech runs and are protected from
later generic motion snapping. Action-aligned scenes use mapped
rise/peak/settle phases, while scenes reviewed as `bridge` are excluded from
primary action phase selection.

`jumpcut-plan`, `jumpcut-review`, and `jumpcut-apply` provide a review-gated
workflow with processed-material lineage. A jump-cut is never applied without
an accepted verdict, and material with no qualifying silence remains uncut.

Verification: actual action material `?▼/IMG_8346.MOV` (15.865s) produced
6 motion peaks and 6 rise/peak/settle phases. Actual speech material
`銝颱遙?/IMG_2118.MOV` (70.817s) produced one continuous speech run and zero
qualifying long-silence candidates, correctly marking jump-cut as not
applicable. An 8-frame fixed-window vs motion-phase A/B showed the phase window
preserving a complete foreground walk-in action instead of an arbitrary crane
exit. This improves action continuity but does not yet identify which action is
semantically most important. Focused M3 suites and full regression passed:
`715 tests OK`.

Next: M4.

### M4 VERIFY 霅??? + ?游?撽(?典?銝?舀?靘???

```text
M4a 擃?摨西?憭芸? VERIFY(閰摯?勗??惜霅??嗅漲???券??keyframe_grid
    ?Ｘ?璈?寞璅??摨?+ 銝??憟?皜脫???:
      ?函?曈亦 36-48 ??/ ?? 12-16 ??/ ?畾?24-40 ??/ 蝭憟?(?券??
      ?瑕漲??)?撓?粹?verify artifacts,judge 銴隞交迨?箄??皞?
M4b ??**????2026-06-13 摮詨蝝????券?**???潛?:
      銝???璅??其葉(?航??准皜?????蝖祈?)
      M0d/M1d/M2e ??? 0 蝜?;judge verdict ?函???
      ??撠銝活:2 蝘?⊿瘥??nique_source_ratio??
      max_source_repeats?鞈?瘥ction_phase_coverage(M1c ?
      ???冽???timeline 銝?閬?)??閮?decision log
      sound-bite >=1 畾萸ump-cut >=1 畾??亥府蝝??拍)
摰??斗? = 銝膩?其葉 + ?刻艘甇貊? + decision log(??2026-06-13 review ?撘?
憟賢??賢神)??
```

M4 status (2026-06-13): COMPLETE. M4a provides the four-layer evidence bundle.
M4b first failed and correctly routed to `revise:director(spec_review)`, then
passed after a material-aware director revision reduced the contract from 20
chapters / 660s to 15 chapters / 180.5s while preserving all must-include beats.

The replay exposed and fixed three BUILD gaps: matched candidates were consumed
from the first source instead of interleaved, `requested_duration_sec` was lost
before allocation, and an explicit director `file` choice did not override
automatic matching. The final planning replay uses distinct opening/closing
aerials and passes formal supply, timeline, b-roll, new-visual-information, and
judge-lineage gates.

Final replay metrics:
`shot_le_2s_ratio=0.0192`, `unique_source_ratio=1.0`,
`max_source_repeats=1`, `new_visual_information_ratio=1.0`,
`repeated_visual_hold_sec=0.0`, `action_phase_coverage=0.0`,
sound bites `=2`, jump-cut not applicable. Duration adaptation and chapter
adaptation both pass. See
`docs/archive/decisions/2026-06-13-m4-material-aware-replay.md`.

Verification: M4 replay acceptance passed; full regression `731 tests OK`;
`py_compile` and `git diff --check` passed. The run is planning-only
(`--skip-render`), so final video delivery remains outside M4b acceptance.

Next: begin the post-M4 roadmap. Preserve the new rule that material supply and
explicit director duration/source choices constrain BUILD rather than merely
informing SPEC review.

### M5 True Render And Sensory Acceptance

M5 status (2026-06-13): TRUE RENDER COMPLETE; SENSORY ACCEPTANCE FAILED.

The M0-M4 material-aware plan was rendered as a real 180.5-second candidate:
`C:\Users\user\Desktop\video_project\67th-graduation-film\runs\20260613-m5-real-render\final.mp4`.
Technical VERIFY passed at 98.7, and the four-layer montage evidence completed.
However, dense visual review against the student edit proves that the current
acceptance model still confuses file-level novelty with viewer-perceived
editing quality.

Observed gaps:

- Different source files still produce long runs of perceptually similar
  classroom, group, and ceremony compositions.
- Motion-peak snapping can show no visible setup/execution/result progression.
- Opening, course transitions, and ending lack designed sequence grammar.
- Technical VERIFY passes while story tension and human-edit feel do not.

M5 scope decision (2026-06-14):

- The 180.5-second result is accepted as the current material-limited baseline,
  not as a human-edit-quality reference.
- Freeze M0-M4 behavior. Do not keep tuning the 67th case to manufacture a
  sensory pass from limited material.
- M5a and M5b remain tier-2 review evidence. They are not delivery-authorizing
  truth and must not be promoted into `HARD_AUDITS` without broader validation.
- M5c/M5d/M5e are deferred until a case with richer, intentionally collected
  material is available. They are not the immediate active roadmap.

VD0  瘛箸?蝐文?蝝?+ lineage              ??撌脣???閬?)
VD1  璅惜閬???霅??極????:    ??憟?摰?;?祕蝝?霅?撌脩??
       ?函?撖衣?????璅酉閬????璅?靘?
       ???楊 Agent ??銝?湔?蝎?摨?銝?瘙??其???;
       閬???銝?湔折?璅??澆?撖?ranker,?血? ranker 憭??瘝???
VD2  BUILD soft-ranking(editor 蝡?   ??撌脣???(VD2a, 2026-06-15)
VD3  VERIFY tier-2 warning backstop    漎??游? visual_fatigue ?振???芾郎蝷?

M5 component status:

1. M5a perceptual composition novelty audit. ??璈撌脣祕雿?蝬剜? tier-2 霅?
   `semantic_novelty_audit.py`:dHash ???(蝝?PIL,?⊥芋??+ 鞎芸帚??;
   fail 璇辣 distinct_composition_ratio<0.5 ??瑽??畾?6s? dashboard
   node 11 + CLI `semantic-novelty-audit`嚗?? delivery_gate HARD_AUDITS??
   dHash ?舀???隡潔誨??璅?銝恐蝔梁?甇??蝢拍?閫??7th ?葡? 10s
   餈撮瑽????畾蛛?CLIP 隞 opt-in??
2. M5b action setup-execution-result progression audit. ? 璈撌脣祕雿??游??芸???
   `action_progression.py`:蝣箏??折?隤?caption+? `classify_function`(憛怨?
   action_phase_coverage=0.0 ????賣?閮駁??餃??agent 銴);??
   material_retrieval 霈蝒撣?function,瘚?timeline?udit 撠恐??
   required_functions ?挾瑼Ｘ establish?ction?esult spine 閬???摨?
   ??dashboard node 11 + CLI `action-progression-audit`嚗?? HARD_AUDITS??
   67th ?暹? contract/timeline ?芸恐??required_functions嚗祕皜祉??
   `no_required_functions`嚗?甇支??賢恐蝔望迨獢? action coverage 撌脤?嚗?
   敺?隞???contract grammar ??timeline clips 蝯??臬祟 segment??
3. M5c designed sequence grammar for opener, course transitions, and ending.
   漎??芸?(tier-2;?/隤脩?頧/蝯偏??瑁?蝯?)??
4. M5d high-density human-vs-agent critical-section comparison. 漎??芸?
   (M4a ?惜?云憟??瑕歇??蝻箇??航?摮詨???菜挾?蒂??撠?蝔???
5. M5e rerender; require both technical and sensory acceptance. 漎??芸?
   (deferred; do not rerender the limited 67th case merely to raise proxy
   metrics. Resume only with a richer comparison case and explicit acceptance
   rubric.)

### M5a/M5b ?摰?:Visual Diversity Guard(2026-06-14,?祕??

雿輻????誨 M5a/M5b ??皜祇?敹?:**?格?銝?圾?恍隤儔??雿?鈭?
?????暸????訾撮蝝???閬死?脖???*?????訾??曹犖撌?Agent ???
摰?,蝟餌絞?芷甇Ｘ?憿舫?銴??桀? M5a/M5b ?游?撖艾?舫? Agent ??

銝餌?:
```
鈭箏極嚗gent ??蝝?
??ingest ????閬死摰嗆?(coarse,銝???菜葫)
??BUILD soft-ranking:甇?Ⅱ?批??憭見?批???銝蝖祈歲??
??蝻箇???璅撩???迂鈭箏極?????
??VERIFY:?芾圾瘙箇?閬死?脖?憿舐內??tier-2 warning(銝?鈭支?)
```

**?詨?靽格迤(2026-06-14,?∠? Codex ??,?函蕃??蝖祈??神瘜?:憭見?扳
soft-ranking ????,瘞賊?銝???蝝?甇?Ⅱ?扼?* ????甇Ｗ? family ???/
?瑕?批停頝喲??蝖祈???蝝?銝雲???澆?游???航炊(?箸??恍?函????
頝喲??臭??質???隞嗥???⊿?蔣??拿??抒?瘞訾?鋡恍)??箔???摨?

```
?貊??芸?摨?BUILD,??瘞賊?憯???:
1. must_have / proof / identity / need 皛輯雲   ??tier-1 甇?Ⅱ??銝鋡怠?璅?抒??
2. ???挾?賜??
3. 撌脫??judge accepted)蝝?
4. media_type 撘勗?憟?敶梁??亙?潛?摹 prior,?′閬?;
   ?抒??交?雿??臭?霅?隞???
5. visual_family / angle_scale / action_family 憭見?批???tiebreaker)
6. ?抒???閮梁? fallback
```

閬?(蝎?摨??券?舀?璇啣,tier-2 ?釭;**?函??/霅衣內,???*):
- ?????`visual_family` ??**??,銝蝳迫**(??撱?????誨閫雿蹂???獢?
  銋??振? 67th ?株矽?孵?,雿圾瘜????,銝 veto)??
- `angle_scale`(??銝?餈??犖???湔/閬?鈭斗 ??????
- ?詨?靘??瑕(撌脫?,閬????具???
- ?桐????脖? = `action_family` ??? ????,雿萄?砍??,銝蝡?M5b 憭抒頂蝯晞?

?賢??(蝯?Codex):
- **? `visual_fatigue_audit`,銝??血遣撟唾?蝟餌絞**??撌脫? source ?瑕??撠?准?
  reuse 銝?;VERIFY 蝡舐?摰? = 霈???鞎?`visual_family` / `angle_scale` /
  `action_family`,**隞?warning ?**(????振?隤??? fail???漱隞?
- **dHash ?頛**:?芸????銋??Ｕ?摮餈?銴?,雿 backstop,
  **銝蜓撠??*;`semantic_novelty_audit` ???園??券??亥?摰???
- M5b ??establish?ction?esult spine ??**?嗆?**;?芯???`action_family`
  ????脖???璇蔥?亙??(action_phase_coverage 銝??舫??園?瑼???
- **閬死摰嗆???per-project 閰?,銝撖急香**:蝭?(?嗅???撱??/隤脣??飛/雓葦甇?/
  摮詨????擃征雿平/撌亙???孵神/鈭箇??/?∪?蝛箸?)?舐?閮?撠惇;????
  **頠?*(`media_type` 瘝輻 asset_type?angle_scale` wide|medium|close?ubject),
  摰嗆?皜??Agent ??ingest/caption 銴??撠?憛?蝟餌絞?芾?頠?+ 撠?摰嗆?銵具?
- **?芣?閮餌??????蝝?*:soft-ranker ?瘝? `visual_family` ????
  ??銵????芰?賊????詨?/慦??),銝??撩璅惜???斤???銝剜迫 BUILD??

#### VD 撖虫???(soft-ranking ?冽?蝐方???????敺?撖?

```
VD0  瘛箸?蝐文?蝝?+ lineage              ??撌脣???閬?)
VD1  璅惜閬???霅??極????:    ??憟?摰?;?祕蝝?霅?撌脩??
       ?函?撖衣?????璅酉閬????璅?靘?
       ???楊 Agent ??銝?湔?蝎?摨?銝?瘙??其???;
       閬???銝?湔折?璅??澆?撖?ranker,?血? ranker 憭??瘝???
VD2  BUILD soft-ranking(editor 蝡?   ??撌脣???(VD2a, 2026-06-15)
VD3  VERIFY tier-2 warning backstop    漎??游? visual_fatigue ?振???芾郎蝷?
```

?輯?頛詨??ingest ??瘛箸?蝐手?*瘝? soft-ranker 撠勗?賡?銵???*,?隞?
VD1 ????霅???VD2 ??蝵桅??1b/E7 ??agent 銴暺停?臬神??甈???嫘?
?砍???函???M6 delta??

**? skill ??摨????? SKILL?? Codex 撖拇?):?曉?神??隞?
???Visual Diversity contract/policy**(?頠?`media_type`/`angle_scale`/
`subject` + 蝎?憿瘜?+ soft-ranking ??),??curator(璅?/ editor(??/
verify(霅衣內)銝??脫??賢????**銝韏瑞洵 4 憟銵?蝔?*?? VD2 ??editor
蝡舐???鞎餅?蝐扎?????蝯?獢?敺??捱摰?血?鋆??舐蝡??? Skill??
?血??曉???臭????豢???鞈??痊隞餅芋蝟?蝛箸挺?振??敶偶??per-project??

#### VD0 Shallow-label contract ??complete (bounded)

- `apply_scene_review_verdict` 靽??滓璅惜嚗curator.md` ??銴鞎砌遙??
- 璅惜蝻箏仃隞?” `unreviewed`嚗???pass嚗?銝 tier-1 fail??
- 撽?芾???蝐方敺?review verdict 撖怠 material-map scene 銝虫???lineage??
- ?璅?甇日?畾萎?撖?family cooldown???寥??摰?迂?釭????
- Evidence: scene-review lineage test plus dashboard/runtime tier-2
  nonblocking tests; full regression `760 tests OK` on 2026-06-14.

Decision log:
`docs/archive/decisions/2026-06-13-m5-real-render-sensory-acceptance.md`??
`docs/archive/decisions/2026-06-14-m6a-review-response.md`??
M5a/M5b 撖虫?閬?commit(semantic_novelty_audit / action_progression)??

### Next After VD0: M6 Material-Map Lifecycle

**Product decision:** default editing remains actual-material-first. A
script-first workflow is supported as a pre-production planning mode, but every
final edit must be revised against actual material evidence before BUILD.

Do not invent duplicate schemas. Canonicalize the existing artifacts:

| Lifecycle concept | Canonical artifact | Current state |
|---|---|---|
| Required material map | `material_needs.json` + `shooting_brief.md` | Existing Skill flow; weak runtime integration |
| Actual material map | per-asset `*.map.json` + `supply_review.json` | Implemented and enforced before BUILD |
| Requirement-vs-actual delta | `material_delta.json` | Missing |
| Revised executable story | revised `segment_contract.json` | Exists, but not yet driven by a canonical delta |

#### M6a Canonical contracts ??contract layer complete (2026-06-14)

> Codex re-review passed after hardening rounds 1-3.
> round 2(`c810ab3`):`fallback_tier` ?湔?(??boolean `True`/摮葡/float
> ?True in (1,2,3,4)` ??Python ??True ???+ CLI 撽?憭望?????exit code??
> round 3(?祈憚):`apply_satisfaction_verdict` 撘瑕 `valid_need_ids`(?芣?靘
> ValueError,?萎? unchecked 撖怠頝臬?);`need_id` ???蝛箏?銝?canonical ??
> verdict ?拍垢);`fallback_options` ???list[str](蝘駁?? `list()` 頧?);
> 蝘駁 permissive satisfaction 皜祈岫??*?典?隞?791 tests OK**??


撖虫? `material_needs.py` + `validate-needs` CLI + `tests/test_material_needs.py`??
M6a-hardening 撌脖耨甇??蝝?review ???4 ??憿?F1-F4):
- **F1 頨怠?蝛拙?(?)**:銝辣鈭??Ｔmigrate_material_needs`(?蔭/?瑞宏,
  ?芰策蝻?id ??need ??id,content-hash ?**擐活?蔭??*)?validate_material_needs`
  (?湔撽?,**銝?蝵柴???join key????頧?**)?楊頛???purpose/type/
  category 瘞訾???id)?anonical need 銝?行? id ?單偶銋????寧???? id??
- **F2 ?? id**:?Ⅱ?? `need_id` ??validation **error**(銝?????_2 敺韌);
  ?芸??蔭?芸?瑞宏蝻?id ???銝?content-identical 銵???閮?migration_notes??
- **F3 reference integrity**:`apply_satisfaction_verdict(..., valid_need_ids=...)`
  **撘瑕**?賢???round 3:?芣?靘 ValueError),撠?摮/??銝?need_id **raise**
  (typo 銝?敶Ｘ?撟賡? edge);`need_ids()` ???賢??柴?
- **F4 ?湔?**:`must_have` ?芣??boolean(`"false"` ??error)?count` ?芣??
  甇???0/鞎?摮葡/float/bool ??error,銝??reated as 1?瘝????
- **蝛拙? project-local `need_id`**,??segment 蝺刻??⊿?;蝡? renumber 銝 id;
  legacy `id` ??? `display_id`,segment ? advisory `segment_hint`??
- **scene-level `satisfies` edge**:status = candidate|accepted|rejected + lineage
  (頧?閮?`previous_status`,timestamp ??verdict ??,?⊿??????
- `summarize_satisfaction` ??scene?eed ?航??(**??delta**)??
- ???詨捆:??needs / ??satisfies ???Ｘ?蝝?瘚?銝?敶梢;legacy 撌Ｙ???flat
  ?頛詨;?芰１ supply_review / rank-local??*?典?隞?791 tests OK(round 3)**??

#### M6a Lineage Integration ??reference chain complete (2026-06-14)

The end-to-end `need_id` reference chain now joins every artifact, with NO
`material_delta` decision (that boundary is M6b):

```
need_id (material_needs)
  ??shooting-brief requirement (shooting_brief.requirements[].need_id)
  ??scene satisfies edge        (material_map.scenes[].satisfies[].need_id)
  ??revised segment_contract    (segment.material_fit.need_refs[])
```

- `material_lineage.build_shooting_brief(needs)` projects each **strict-validated**
  canonical need into a brief requirement carrying its `need_id` (the join key
  the human-authored prose brief must preserve). It is a projection, not a second
  required-map format; invalid/un-migrated needs raise.
- `segment_contract` gains optional `material_fit.need_refs` (list of need_id).
  `spec_contract.validate_segment_contract` validates **shape only** (non-empty
  string array); the cross-file join is enforced by the linker ??same split as
  `blueprint_ref`.
- `material_lineage.link_lineage(needs, shooting_brief, material_maps, contract)`
  produces a neutral join view (`chain[need_id] = {in_brief, satisfied_by,
  contract_segments}`) and fails (`ok=False`) only on a **dangling reference** ??
  any brief/satisfies/contract hop pointing at a need_id absent from canonical
  needs. It makes NO covered/thin/missing verdict: a need with zero satisfying
  scenes is reported as-is, never flagged missing.
- CLI `lineage-link [--build-brief] [--brief] [--project-map] [--contract]`.
  Reuses `summarize_satisfaction` (scene?eed inversion) and
  `expand_project_material_map` (MR1 loader). Backward compatible: needs-only or
  no-need_refs flows stay `ok`.

Falsification tests `tests/test_material_lineage.py` (brief carries need_id;
invalid needs cannot build a brief; need_refs shape; need_id survives all four
artifacts; dangling at each hop fails; no-delta boundary asserts no
coverage/route/status keys leak): 11 tests. Full regression: **900 tests OK**.
M6b `material_delta` stays deferred ??it now has a join to diff over.

M6a lineage hardening (2026-06-14): (1) `contract_need_refs` returns ordered
records `[{segment_ref, segment_index, need_refs}]` instead of a dict keyed by
`section_role` ??a repeated role no longer overwrites a sibling's references, so
a dangling ref on the first of two same-role segments is caught. (2) `link_lineage`
now shape-validates every supplied artifact reference (brief requirement = object
with non-empty-string need_id; contract need_refs = non-empty list of need_id
strings, no silent filtering; satisfies edge = object with non-empty-string
need_id and candidate/accepted/rejected status, reusing material_needs'
`VALID_STATUSES`). Malformed input returns `ok=False` + errors without crashing
(satisfaction inversion is now built crash-safe inline rather than via
`summarize_satisfaction` on unvalidated data). Reverse tests: repeated-role
dangling, brief missing/non-string need_id, contract `[123]`/`[]`/non-list,
satisfies non-object/non-string/illegal-status, legal four-link still ok. Focused:
16 tests OK; full regression: **905 tests OK**.

M6a lineage final hardening (2026-06-14): `chain.contract_segments` now
preserves both display `segment_ref` and artifact-local `segment_index`, so
same-role segments remain individually addressable by downstream M6b/M6c.
`segment_index` is intentionally only an identity inside the current contract
artifact; it is not claimed stable after contract reordering. Supplied
shooting-brief and contract top-level shapes now fail safely (`ok=False` +
errors) instead of crashing or silently passing. Reverse tests cover duplicate
display roles and malformed top-level brief/contract inputs. Focused:
18 tests OK; full regression: **907 tests OK**.

Original design goals (all met by the above):

- Model one lifecycle with existing-material and planned-capture entry points;
  partial material availability is first-class, not a third branch.
- Validate and canonicalize existing `material_needs.json` before downstream use.
- Add the load-bearing `satisfies: [need_id]` edge on reviewed assets/scenes.
- Reconcile requirement-purpose vocabulary before any delta implementation.
- Specify stable IDs linking requirement ??shooting brief ??actual asset/scene
  ??revised contract segment.
- Reuse `material_needs.json`; do not create a second required-map format.
- Acceptance: the same requirement ID survives through every artifact, and
  every entry point converges on actual-material review before BUILD.

#### M6b Material delta

- Produce `material_delta.json` by comparing requirements with actual supply.
- Required outcomes: `covered`, `thin`, `missing`, `wrong_semantics`,
  `insufficient_action_phases`, and `excess/unplanned`.
- Each delta must carry evidence and one explicit route:
  `collect_material`, `reshoot`, `shorten_or_merge`, `script_rewrite`,
  `drop_segment`, or `dashboard_review`.
- Acceptance: no requested beat silently becomes an unrelated clip.

##### M6b increment 1 ??coverage-based outcomes (2026-06-15)

Bounded first increment, built ONLY on the validated M6a join
(`material_needs ??satisfies edges ??link_lineage`). `material_delta.py`
`compute_material_delta(needs, material_maps)` emits a deterministic per-need
outcome ??`covered | thin | missing | excess` ??each with `tier`, `route`,
`reason`, and `evidence` (the counts it decided from), plus a machine-readable
`blocks_ready_for_build` and a top-level `ready_for_build`.

- Deterministic thresholds: `usable = accepted + candidate`. `usable==0` ??
  `missing`; `accepted > count` ??`excess`; `accepted >= count` ??`covered`;
  else ??`thin` (candidate-only material is thin, never missing).
- **Only tier-1 case this increment**: a `must_have` need with no usable
  material AND no permitted `fallback_options` ??`tier=1`, route `reshoot`,
  `blocks_ready_for_build=true`. `must_have` WITH a permitted fallback, and all
  optional misses, are `tier=2` and do not block.
- **Broken join ??missing**: an invalid `material_needs` or a dangling/malformed
  satisfies edge makes the whole delta `ok=False` with `errors` and zero deltas
  ??it is never silently classified as `missing`.
- CLI `material-delta <needs> [--project-map] [--out]`. Reuses
  `expand_project_material_map` + `link_lineage`; exits non-zero only on `ok=False`.

Deferred to a later batch (confirmed): `wrong_semantics` /
`insufficient_action_phases` (need the F2 canonical shot-function vocabulary; no
`action_progression` dependency taken here), and wiring `blocks_ready_for_build`
into the pre-BUILD gate (`delivery_gate` stays a backstop only, not the primary
block site). No BUILD ranking / script / timeline change.

Falsification tests `tests/test_material_delta.py` (covered/thin/excess/missing
thresholds incl. candidate-only=thin and rejected-only=missing; must_have+no-
fallback+missing ??tier-1 blocks; legal fallback ??not tier-1; optional miss
does not block; the minimal one-must_have-zero-material disproof; dangling/
malformed/invalid ??fail-not-missing; no-semantic-field boundary; multi-need
summary): 14 tests. Full regression: **921 tests OK**. F2 stays deferred until a
real case proves semantic function classification is needed.

M6b increment-1 hardening (2026-06-15): coverage now counts only BUILD-usable
evidence. (1) A satisfying scene is counted only if its source is a non-empty
string and its start/end are valid numbers with `end > start`; unrenderable
evidence is recorded in `evidence.dropped_evidence` (reason
`missing_source`/`invalid_bounds`/`non_positive_length`) and never makes a need
`covered` ??so a zero-length or sourceless accepted scene cannot flip a must_have
need to `ready_for_build`. (2) `fallback_options` items must be trimmed non-empty
strings; `[""]`/`["   "]` now fail validation (??`ok=False`) and therefore cannot
relieve a tier-1 block. (3) Evidence is deduped by `(need_id, asset_id,
scene_index)` at its strongest status, so a duplicated accepted scene cannot
inflate `covered`/`excess`. Future pre-BUILD gate MUST require
`delta.ok is True AND delta.ready_for_build is True` (not `blocks_ready_for_build`
alone) ??documented in `material_delta` module. Reverse tests: zero-length /
missing-source / invalid-bounds accepted dropped; duplicate accepted counted
once; `[""]`/`["   "]` fallback fails. Focused: 19 tests OK; full regression:
**926 tests OK**.

M6b increment-1 identity hardening (2026-06-15): `compute_material_delta` now
requires every input material map to carry a non-empty-string `asset_id` that is
unique across the input ??`asset_id` is the identity half of the
`(asset_id, scene_index)` evidence key, so a missing/blank/non-string or
duplicate id makes evidence resolution ambiguous and order-dependent. Such input
is a hard failure (`ok=False`, `ready_for_build=False`, `deltas=[]`), never
silently resolved into covered/missing. Reverse tests: duplicate asset_id fails
in both map orders (no order-dependent verdict); missing/blank/non-string id
fails; unique ids still pass. Focused: 22 tests OK; full regression:
**929 tests OK**.

##### M6b pre-BUILD gate ??integrated (2026-06-15)

`material_delta` is now a real BUILD-blocking dependency. `material_delta.material_delta_gate`
is a fail-closed verdict built ONLY on `compute_material_delta` (no second delta
logic): a build may proceed iff `delta.ok is True AND delta.ready_for_build is
True` ??`blocks_ready_for_build` alone is insufficient.

- **Lifecycle position**: `contract_adapter.run_contract`, AFTER the `spec_review`
  `ready_for_build` gate and BEFORE music/timeline/`mv_chain` render. A blocked
  build returns `{ok:False, stage:"material_delta", ...}` and never renders a new
  final. If a previous build's `final.mp4` already exists, it is **moved aside**
  to `stale_previous_final.mp4` (never silently deleted) so it cannot masquerade
  as this run's output; `state.json`/result record `final: null` and
  `stale_final_path`. `delivery_gate.HARD_AUDITS` is untouched (backstop only).
- **Existing-material-first skip**: the gate runs only when the contract declares
  `material_needs_ref`. No declaration ??skipped ??existing flow unchanged
  (backward compatible). Declared-but-missing / unparseable needs, or a
  declared-but-missing/corrupt per-asset map, are hard blocks (fail-closed),
  never a silent skip or "treated as zero material".
- **Freshness**: the verdict is computed fresh from the current `material_needs`
  + current per-asset maps every run; a stale `material_delta.json` is never
  trusted (it is overwritten with the truth). No second delta judgment path.
- **Diagnostics on block**: `state.json` + return carry `stage`, `next_action`
  (`await_material` for tier-1 missing, `revise:material(material_delta)` for
  broken/invalid), `route` (`await_material` | `fix_material_map_or_needs`),
  `blocking_need_ids`, `reason`, and the `material_delta.json` evidence path.
  Non-blocking thin / optional-missing pass with the delta artifact as warning.

Falsification tests `tests/test_material_delta_gate.py` (A no-needs runs existing
flow; B covered passes; C must_have+no-fallback blocks; D must_have+fallback does
not tier-1 block; E broken satisfies ??fix-route block not missing; F declared
needs file missing ??fail-closed; G corrupt map / invalid asset identity blocks;
H stale artifact ignored, recomputed and overwritten; I tier-1 block stops before
render ??`mv_chain` not called, no final video; J gate-pass lets render run):
13 tests. Full regression: **942 tests OK**.

M6b gate final hardening (2026-06-15): (1) on block, a pre-existing `final.mp4`
is quarantined to `stale_previous_final.mp4` (atomic move, preserved not
deleted); `state.json`/result carry `final: null` + `stale_final_path`, so a
stale render can never be reported as this run's success. (2) `material_needs_ref`
is strictly validated ??only an ABSENT key skips (existing-material-first); a
present-but-malformed value (`""`/`"   "`/non-string/`[]`/`{}`) is a fail-closed
verdict, never a crash. (3) Relative `material_map` paths resolve against the
`material_db.json` directory (not the process cwd); declared-but-unresolvable
maps block. Reverse tests: stale-final quarantine + lineage; malformed ref
fail-closed; cwd-independent relative-map resolution; unresolvable relative map
blocks; absent key still skips. Focused: 18 tests OK; full regression:
**947 tests OK**.

M6b gate quarantine identity hardening (2026-06-15) ??**M6b COMPLETE**: the
stale-final quarantine never deletes or overwrites an already-quarantined file;
it picks the first unused deterministic name (`stale_previous_final.mp4`, then
`_2`, `_3`, ...). `state.json`/result record the actual `stale_final_path`. On a
move/rename failure it returns a `quarantine_error`, keeps the block, and reports
`canonical_final_cleared: false` ??never claiming the canonical final was cleared.
Reverse tests: pre-existing stale not clobbered (??`_2`); three consecutive
quarantines keep all three; simulated `replace` failure is diagnosable and
preserves the final, and the blocked run never claims it cleared. Focused: 22
tests OK; full regression: **951 tests OK**.

**M6b is complete.** Next step: **M6c delta-driven script revision** (separate
batch). F2 / `wrong_semantics` / `insufficient_action_phases` remain deferred.

**Next step: M6c delta-driven script revision** (convert accepted delta decisions
into a revised `segment_contract.json`; preserve director decisions; record
revision lineage). The M6b gate stays the objective tier-1 block; M6c is a
separate batch. F2 / `wrong_semantics` / `insufficient_action_phases` remain
deferred.

#### M6c Delta-driven script revision

- Convert accepted delta decisions into a revised `segment_contract.json`.
- Preserve human/director decisions and record revision lineage.
- BUILD remains blocked only by objective tier-1 gaps; aesthetic tier-2
  findings remain review evidence.
- Acceptance: a missing requirement either changes the script, requests
  material, or is explicitly waived. It is never hidden by repetition.

##### M6c revision engine ??(2026-06-15)

`material_revision.apply_revisions(contract, material_delta, decisions)`
deterministically converts ACCEPTED human/director decisions into a revised
`segment_contract` ??the agent never invents content or silently edits. Reuses
the existing `need_id` + route enum (no second needs/delta schema).

- **Decision contract** (`revision_decisions[]`): `decision_id` (unique,
  non-empty), `need_id` (must exist in the current delta), `route` (must be
  compatible with that need's delta outcome), `status` accepted|rejected,
  `target_segment` (required for segment-modifying routes; resolved to exactly
  one segment by its `segment` identity), `patch` (shorten/rewrite), `waiver`
  (reviewer+reason; the ONLY thing that releases a tier-1 block), `lineage`
  (reviewer/reason/at, caller-supplied ??no hidden clock).
- **Route behavior**: `collect_material`/`reshoot`/`dashboard_review` ??no script
  change, status `blocked`, next_action `await_material`/`await_review`;
  `shorten_or_merge` ??edits only the target segment's duration (allow-listed
  keys), need_refs preserved; `script_rewrite` ??merges only the explicit patch
  (identity/need_refs/need_id changes rejected); `drop_segment` ??removes the
  named segment, and a must_have need cannot be dropped without an explicit
  waiver.
- **Safety (all fail-closed, order-independent)**: `material_delta.ok=false`
  forbids revision; unknown/stale `need_id`, duplicate `decision_id`,
  incompatible route, missing/ambiguous target, conflicting accepted patches on
  one segment, and identity-touching patches all fail with no revised contract.
  The original contract is never mutated (deep copy); the revised contract must
  re-pass `spec_contract.validate_segment_contract`; tier-1 gaps not covered by
  an explicit waiver remain in `unresolved_blocking_needs` (still blocked).
- **Artifacts**: `revised_segment_contract.json` (new copy) +
  `material_revision.json` (per-decision applied/rejected/blocked status,
  before/after contract hash, need_id/route/target, lineage,
  unresolved_blocking_needs, next_action). CLI `material-revision` writes both on
  success; invalid input exits non-zero and writes no half-baked artifact.

Falsification tests `tests/test_material_revision.py` A? (no-op/identical;
rejected no change; non-modifying routes; shorten only-target + need_refs kept;
script_rewrite only explicit patch; drop optional ok / must_have-no-waiver fail;
explicit waiver releases block with lineage; unknown/dup/incompatible fail;
ambiguous/missing target fail; conflicting patches fail both orders; identity
patch fail; original untouched; revised validates; unresolved tier-1 still
blocks; CLI two-artifact + fail-closed): 17 tests. Full regression:
**968 tests OK**.

M6c hardening (2026-06-15): (1) Unified waiver/gate contract ??the M6b gate is
now waiver-aware via a single `material_delta.gate_from_delta(delta, waivers)`
verdict that both `run_contract`'s gate and M6c consume, with a canonical waiver
artifact `{need_id, reviewer, reason, at}`. M6c's `ready_for_build` IS that gate
verdict, so `material_revision.ready=true` can never contradict a gate block; a
tier-1 block is released only by a canonical waiver (explicit reviewer+reason).
(2) `drop_segment` now protects EVERY `material_fit.need_refs` of the target ??
each referenced must_have / tier-1 need requires its own explicit waiver, an
unknown need_ref is fail-closed, and `affected_need_ids` is recorded.
(3) `write_revision_artifacts` is all-or-nothing: the two outputs must differ,
both parent dirs are created, both files are written to temporaries and only
`os.replace`d after both succeed; on failure temporaries are cleaned and existing
official artifacts are left intact. Reverse tests: gate reproduces M6c ready
(and the no-waiver no-release case); multi-ref drop protection incl.
per-need waiver and unknown-ref fail; affected_need_ids recorded; CLI atomicity
(same-path fail, missing-parent create, second-write failure leaves no new first
artifact). Focused: 26 tests OK; full regression: **977 tests OK**.

M6c final contract hardening (2026-06-15): (1) ONE shared canonical-waiver
validator `material_delta.is_canonical_waiver` ??a waiver releases a tier-1 block
only when need_id/reviewer/reason/**at** are all trimmed non-empty strings; both
`gate_from_delta` and M6c route through it (no second rule), so a malformed
waiver silently releases nothing. (2) `write_revision_artifacts` now survives a
commit-stage (`os.replace`) failure: existing officials are backed up before any
replace, a failed second replace rolls the first back to its prior content (or
removes the newly-created file when none existed), and temps/backups are cleaned
??the disk is never a new/old mix. If rollback itself fails, backups are kept and
a `RuntimeError` is raised (atomic success is never claimed). Reverse tests:
malformed at/reviewer/reason/need_id release nothing (and the gate still blocks);
a legal M6c waiver is reproduced by the gate; second-replace failure leaves an
existing pair unchanged / leaves neither output when none existed; no temp/backup
residue; rollback-failure is diagnosable; success updates both. Focused: 34 tests
OK; full regression: **985 tests OK**.

M6c artifact-transaction final hardening (2026-06-15): (1) the BACKUP phase is
now itself transactional ??if the first official is moved to backup but the
second backup fails, the first backup is restored to its official path (a backup
holding the only good copy is never unlinked); a failed backup-rollback preserves
the backup and raises a not-atomic `RuntimeError`. (2) Before a transaction
starts, a pre-existing `.m6c.bak` is fail-closed (it may hold the only good copy
from a prior failed run ??refuse rather than overwrite/delete), while stale
`.m6c.tmp` scratch is cleared explicitly. (3) Output-path identity is compared
with `os.path.normcase(abspath(...))`, so on Windows `A.json` and `a.json` are
correctly rejected as the same output. Reverse tests: second-backup failure
leaves both officials unchanged; backup-rollback failure preserves backup + flags
not-atomic; pre-existing backup fail-closed untouched; stale temp cleared and run
succeeds; Windows case-alias outputs fail. Focused: 39 tests OK; full regression:
**990 tests OK**.

##### M6c runtime plumbing ??(2026-06-15) ??**M6c COMPLETE**

`contract_adapter.run_contract` now wires revision into the SPEC?UILD flow. When
the contract declares `revision_decisions_ref`, BEFORE script generation it:
computes a FRESH `material_delta` from current needs+maps ??`apply_revisions`
(only accepted decisions) ??writes `revised_segment_contract.json` +
`material_revision.json` atomically ??re-runs `gate_from_delta` with the canonical
waivers. The whole downstream pipeline (script, supply, spec_review, M6b gate,
render) then runs on the **revised** contract, and the M6b gate is re-checked with
the same waivers. No declaration ??existing flow unchanged (backward compatible).

Invariants: the original input contract file is never written; BUILD runs on the
revised contract only when the post-revision gate passes; every verdict is fresh
(no stale `material_delta`/`material_revision`/revised contract trusted);
`material_revision.ready_for_build` and the re-run gate must agree or it blocks;
only accepted decisions apply. Blocked runs stop before render and reuse the M6b
stale-final quarantine. Fail-closed on: malformed/missing/unparseable
decisions_ref, no resolvable needs/maps, broken fresh delta, engine failure,
ready_for_build=false / pending await (collect/reshoot/review), gate/revision
disagreement, invalid revised contract.

Falsification `tests/test_material_revision_runtime.py` A? + 5 adversarial
(decisions_ref without needs_ref; decisions not a list; revision does NOT mask an
unrelated tier-1 gap; conflicting accepted decisions; stale revised artifact
overwritten with fresh): 16 tests. Full regression: **1006 tests OK**.

M6c runtime plumbing hardening (2026-06-15): (1) `material_needs_ref` and
`revision_decisions_ref` now share ONE strict resolver `_resolve_declared_ref` ??
an absolute ref resolves to itself, a relative ref resolves ONLY against the
contract file's directory (never the process cwd or `examples/`), and a relative
ref with an inline (dict) contract is an explicit error rather than a cwd guess;
missing ??fail-closed. (2) The revision lifecycle strict-loads the current
material_db before doing anything: a missing/corrupt DB, non-object top level,
non-list `files`, or non-object entry is a structured block
(`next_action=revise:material(material_delta)`) ??never degraded to `{"files":
[]}`, so `apply_revisions` is not called and no artifacts/BUILD happen. Reverse
tests: missing decisions/needs beside the contract block despite a cwd/examples
copy; valid relative refs resolve from a different cwd; corrupt/missing/non-object
DB all block without exception; optional-only needs + corrupt DB still blocks;
invalid DB writes no revision artifacts and no final. Focused: 22 tests OK; full
regression: **1012 tests OK**.

M6c runtime final input-shape hardening (2026-06-15) ??**M6c COMPLETE**:
`_load_material_db_strict` rejects a `None`/non-path-like/empty `material_db` as a
structured block (no `TypeError`). `_load_current_material_maps` distinguishes an
ABSENT `material_map` key (skip ??not declared) from a PRESENT-but-malformed value:
`None`/blank/number/bool/list/dict all return a structured `map_error`, and a
`material_map` pointing at a directory (or an unreadable file) is fail-closed too.
Reverse tests: `material_db=None`/non-path block without crash; bad `material_map`
shapes block; absent key skipped; directory map blocks; a bad map in the revision
lifecycle writes no artifacts and skips BUILD. Focused: 27 tests OK; full
regression: **1017 tests OK**. The M6 lifecycle is complete; next step is **M6d
Independent Material Map Skill**.

**Next: M6d Independent Material Map Skill** (deferred). F2 / `wrong_semantics` /
`insufficient_action_phases` remain deferred. The M6 lifecycle
(needs ??lineage ??delta ??pre-BUILD gate ??revision ??runtime) is now end-to-end.

#### M6d Independent Material Map Skill

- Expose the lifecycle as an independently runnable Skill/template:
  discussion ??required map ??shooting brief ??ingest actual material ??
  actual map ??delta ??revised script.
- It must also support starting from existing material, skipping required-map
  generation until the user chooses to discuss or request missing shots.
- Acceptance: the Skill can stop after planning/collection guidance without
  forcing a video render.

##### M6d implementation ??COMPLETE (2026-06-15, after final map-input hardening)

`material_map_lifecycle.run_lifecycle` + CLI `material-map-lifecycle` +
`skills/material-map.md`. Orchestration only ??composes the M6a?6c canonical
tools, adds no editing capability and no second source of truth. The stage is
derived FRESH from the artifacts present (never a prior lifecycle/delta/revised
contract): `await_requirements_discussion` (material-only, no invented needs/no
delta) 繚 `await_material` (must_have missing) 繚 `await_map_review` (maps unlinked
to needs, or material sufficient but no contract) 繚 `await_revision_decision`
(pending/none-accepted decisions) 繚 `revision_blocked` 繚 `build_ready` 繚 `invalid`
(dangling need / duplicate asset / corrupt input ??fail-closed). It can stop at
any planning/await stage WITHOUT rendering. A `build_ready` handoff
(`{contract_ref, material_db_ref, material_needs_ref, revision_waivers,
ready_for_build}`) points only at existing files; no-revision ??original contract,
revision ??revised contract. The handoff is re-verified by `run_contract`'s own
fresh M6b/M6c gate (M6d never bypasses it ??proven by a real run_contract handoff
smoke). The lifecycle report is a projection (refs + summaries), not a canonical
schema. Tests `tests/test_material_map_lifecycle.py`: entry (?6), freshness (?2),
failure (?3), stop-without-render, handoff missing-ref + run_contract gate smoke
(14 tests). Skill doc defines the method and decision responsibility;
deterministic validate/join/gate/revision stay in Python.

M6d hardening (2026-06-15): `build_ready` is now genuinely runnable + gate-bound.
(1) Exactly ONE actual-side source is allowed (no silent priority); `--material-db`
is the ONLY source that can reach `build_ready` ??`--maps-dir`/`--project-map` are
inventory-only. (2) `build_ready` requires the contract to pass
`spec_contract.validate_segment_contract` AND declare a `material_needs_ref` that
strict-resolves (relative to the contract dir) to the SAME needs file the lifecycle
used; a revision build also requires a bound `revision_decisions_ref`. The handoff
`contract_ref` is the original contract (run_contract re-runs the fresh M6b/M6c gate
and, for revisions, re-applies the decisions + re-derives waivers); the revised
contract is recorded as evidence in `refs.revised_contract`. (3) Supplied decisions
are ALWAYS canonically validated via `apply_revisions` (non-list/malformed/unknown
need_id/dup id/illegal status/route ??`invalid`, even when none are accepted);
valid rejected-only ??`await_revision_decision`, nothing applied. (4) A declared
but missing/corrupt categories file ??`invalid` (never silently `None`). Reverse
tests A? + categories + source-ambiguity + decisions-validation: 26 tests total.
Full regression: **1043 tests OK**.

M6d final map-input hardening (2026-06-15): (1) a declared `project_map_ref` /
`maps_dir` must be a non-empty str/PathLike ??blank/int/bool/list/dict ??
structured `invalid` (no `TypeError`); `None` = not provided. (2) ALL three
sources are canonically normalized through `expand_project_material_map` after
load (no M6d map schema), so a malformed asset / asset_id / source / non-object
scene / non-list `scenes` container fails closed BEFORE
`build_project_material_map`/`_total_satisfies` can crash; the `build_project_material_map`
calls also catch `TypeError` (malformed `satisfies`). (3) Orchestration catches
only `TypeError`/`OSError`/`ValueError` (no broad `except Exception`). Reverse
tests: bad ref shapes; non-object scene; non-list scenes; malformed
asset/asset_id/source; material_db map with malformed scene; legal project-map
source still inventories (32 tests total). Full regression: **1049 tests OK**.
**M6d COMPLETE.** Next: M6e real-case acceptance (real ffmpeg render +
student-footage replay across the three entry points).

**Still open: M6e real-case acceptance** (real ffmpeg render + 67th-style student
footage replay across the three entry points) is NOT yet done. F2 /
`wrong_semantics` / `insufficient_action_phases` remain deferred.

#### M6e Validation

- Validate with two cases, not only 67th:
  1. existing-material-only case with honest shortening;
  2. script-first case where requested shots are collected, missed, and revised.
- Do not promote new proxy metrics to tier-1 based only on unit tests.
- Completion requires artifact lineage, route correctness, and human review of
  whether the revised script matches actual supply.

##### M6e automated acceptance ??on real 67th footage (2026-06-15)

Ran the M6d lifecycle CLI + `run_contract` on the REAL 67th material
(`敺桅敶梁???_?渡?敺; cross-reference table = 22% covered / 55% missing). Harness
`tools/m6e_acceptance.py`; full write-up `docs/archive/decisions/2026-06-15-m6e-real-case-acceptance.md`.
- **A existing-material** ??`await_requirements_discussion`, no render, no invented needs.
- **B script-first insufficient** ??`shooting_brief.json` + `await_material`;
  `run_contract` returned `stage=material_delta` and produced **no final.mp4**
  (blocked before render; blockers = the two un-shot must_haves ?冽?/蝜拍?).
- **C covered** ??`build_ready` ??`run_contract` **real ffmpeg render ??final.mp4
  (8.47s, verify 98.5 PASS)** from the real `.MOV` sources via MR1 map-ranked.
- **D revision** (drop+waive the 2 missing must_haves) ??`build_ready`(revised
  3-seg); `run_contract` re-ran M6c, re-derived the waivers, and rendered the
  revised cut. The handoff never bypassed the runtime gate.

**M6e.1 ??unified material_map loader (2026-06-15) ??M6e automated acceptance
COMPLETE.** One canonical loader `project_material_map.material_maps_from_db`
/ `material_maps_from_db_payload` (+ `load_material_db`): a relative
`material_map` resolves against the materials_db dir (never cwd), absolute stays
as-is, declared-but-missing/directory/unreadable/malformed maps are fail-closed,
absent keys skipped, loaded maps canonically normalized. All three consumers
route through it ??run_contract supply-review,
`contract_adapter._load_current_material_maps` (M6b/M6c gate), and
`mv_cut._load_material_maps`/`mv_chain` (BUILD) ??so supply judgement and the
render see identical maps. The absolute-path workaround is removed; the harness
`tools/m6e_acceptance.py` now uses RELATIVE `material_map` paths, runs each entry
from an unrelated cwd, and asserts all four (exits non-zero on any failure):
A `await_requirements_discussion` (no render) 繚 B `await_material` + brief + BUILD
blocked (no final) 繚 C `build_ready` ??real final.mp4 (render_ok+verify_ok) 繚
D revision drop+waive ??build_ready ??real final.mp4. Focused
`tests/test_material_map_loader.py` (A cross-cwd one-map across all consumers;
B relative?ap-ranked window; C missing/corrupt/dir fail-closed; D absolute compat;
E absent key skipped; F malformed not covered; + run_contract relative-missing
blocks before render): 7 tests. Full regression: **1056 tests OK**.

**Still open (do NOT block automated acceptance):** human viewing sign-off (watch
`out_C`/`out_D` finals vs `67??閮蔣??蝯?mp4`) and full-scale curator ingest over
all 304 files (HEIC not exercised). Automated three-entry acceptance: **COMPLETE**.

**Explicit non-goals for M6:** effects expansion, CLIP as a hard dependency,
automatic claim of semantic understanding, forced ten-minute duration, and
further 67th-specific sensory tuning.

M6a must not revive the deprecated M5b `establish ??action ??result` acceptance
spine. Requirement-purpose vocabulary and Visual Diversity labels solve
different problems and must remain separate.

Review handoff:
`docs/archive/decisions/2026-06-14-roadmap-course-correction.md`.

### MM1 Project Material Map V1 ??COMPLETE (2026-06-14, Codex review passed)

`project_material_map.py` + `project-material-map` CLI + `tests/test_project_material_map.py`
(14 tests). 6 acceptance criteria + hardening:
- deterministic aggregate (sorted by asset_id); CLI writes `project_material_map.json`.
- **reference integrity**: every satisfies edge validated (object / non-empty
  string need_id / status in candidate|accepted|rejected / known need_id);
  unknown need_id fails when needs present; **a satisfies edge with no canonical
  needs fails** (phantom-edge bypass closed).
- **asset_id** must be a unique non-empty string (duplicate / empty / non-string fail).
- **needs_path** explicitly provided but missing ??fail (not silently treated as needs-less).
- **metrics renamed for honesty**: `captioned_scene_ratio` (scenes with a caption)
  and `vd0_labeled_scene_ratio` (scenes with ?? VD0 label) ??no longer overclaim
  "reviewed" / full "label coverage".
- projects without needs stay valid; non-goals held (no delta/decision, BUILD, UI).

**Goal:** aggregate the existing per-asset `*.map.json` evidence into one
project-level material map that can be consumed by agents, BUILD, and a future
UI without creating another source of truth.

Canonical output: `project_material_map.json`.

Minimum contract:

```json
{
  "artifact_role": "project_material_map",
  "version": 1,
  "assets": [],
  "needs": [],
  "satisfaction_summary": {},
  "metrics": {
    "asset_count": 0,
    "scene_count": 0,
    "captioned_scene_ratio": 0,
    "vd0_labeled_scene_ratio": 0
  }
}
```

Required behavior:

- Aggregate asset and scene identity, caption, speech, motion evidence, VD0
  shallow labels, and validated scene-level `satisfies` edges.
- When canonical material needs exist, include the validated needs and a
  read-only satisfaction summary.
- When no material needs exist, remain useful as an existing-material-first
  library.
- Preserve source evidence and lineage; do not silently invent labels or edges.
- Produce deterministic output for identical inputs.

Explicit non-goals:

- No `covered` / `thin` / `missing` decision and no `material_delta`.
- No script revision, BUILD ranking, Dashboard/UI, Node 14, or effects work.
- Do not replace per-asset maps; the project map is their validated aggregate.

Acceptance:

1. Multiple per-asset maps aggregate into one deterministic project map.
2. Unknown or invalid `satisfies.need_id` references fail.
3. Projects without material needs remain valid.
4. Metrics truthfully report asset/scene count and review/label coverage.
5. A CLI produces `project_material_map.json`.
6. Focused tests and the full regression pass.

### SRP1 Segment Sequence Recipe Planner ??COMPLETE (2026-06-15)

The planner (`sequence_recipe_planner.py`) runs during the segment planning loop in `run_mv` to automatically restructure eligible segments:
- **Eligibility**: Only plans for local map-ranked segments with at least 2 approved slots, no manual `beat_recipe`, no speech/keep_audio requirements, no stock-only assets, and no GAP/fallback segments.
- **Beat Assignment**: Dynamically chooses a 2-beat (`context` -> `payoff`), 3-beat (`context` -> `primary_action` -> `payoff`), or 4-beat (`context` -> `primary_action` -> `detail_reaction` -> `payoff`) recipe.
- **Integrity**: Preserves exact source, scene_id, extract_start, and extract_dur by setting recipe durations to the slots' original `extract_dur`.
- **Traceability**: Injects `sequence_recipe_source = "auto"`, `sequence_recipe_reason`, and `sequence_recipe_evidence` on both the segment script entry and each slot in the final plan.
- **Testing**: 12 dedicated tests cover all A-K fallback rules, window/photo integrity, and a real FFmpeg integration test (L) proving auto-sequence output.

### SRP2 Opening / Hook Auto Planner ??COMPLETE (2026-06-16)

A deterministic, shallow opening planner that structures a runtime-ephemeral opening recipe from approved story-plan slots and prepends it via the BR1 compiler:
- **Deduplication**: Qualified candidates are deduplicated by `scene_id` (keeping the best correctness-ranked occurrence) before the opening shape is decided to prevent duplicate beats.
- **Same-Tier Selection**: Roles are filled correctness-first and greedily by retrieval score tier. Soft preferences (e.g., angle scale, unused visual family) apply only within a tier:
  - Hook prefers: `close` -> `medium` -> `wide` -> `video` -> `scene_id`.
  - Context prefers: unused `visual_family` -> `wide` -> `medium` -> `close` -> `video` -> `scene_id`.
  - Title prefers: unused `scene_id` and different family.
- **Budgeting**: When the combined duration exceeds `target_sec`, `trim_opening_for_budget` dynamically drops context beats, then title_reveal, then hook duration (never below a legal positive duration, never touching story slots). Manual openings bypass budget checks.
- **Safety**: Manual `script["opening_recipe"]` always overrides the auto planner. Only approved, scene_id-bearing, renderable slots are eligible (GAP/missing/source_speech/keep_audio/hold/fallback-only/illegal-window excluded).
- **Testing**: Dynamic-photo true render, 44 focused tests, and full regression pass (1177 tests OK).

### AR1 Runtime Planning Extraction ??COMPLETE (2026-06-16)

A zero-behavior-change refactoring of the `run_mv` god-function in `mv_cut.py` to extract planning logic into clean, stateless helper functions:
- **Structure**: `run_mv` signature is preserved as an orchestrator (~110 lines) delegating to four helpers:
  - `_plan_story_timeline`: segments planning dispatch, sequence compilation, anti-presentation planning, slot trace, and VD2 shared history updates.
  - `_apply_opening_bookend`: manual BR1 / auto SRP2 opening compilation and target_sec budgeting.
  - `_apply_ending_bookend`: BR4 ending sequence compilation.
  - `_finalize_timeline`: edit-point layout and motion-peak snapping.
- **Compatibility**: Behavior is verified byte-for-byte identical to the pre-refactor state.
- **Testing**: Covered by `tests/test_ar1_run_mv_characterization.py` characterization tests (A-L), real ffmpeg render, and full regression pass (1193 tests OK).

### SRP3 Story Arc / Emotional Progression Planner ??COMPLETE (2026-06-16)

A whole-film level, shallow, deterministic story arc planner:
- **Role Assignment**: `story_arc_planner.plan_story_arc(script)` assigns emotional intensity roles (setup -> challenge -> progression -> climax -> resolution, scaled to segment count) and nudges duration weights.
- **Budget Allocation**: Climax segments receive higher weight multipliers, directing `allocate_segments` to allocate more duration to climax shots while preserving total story duration and `target_sec`.
- **Safety**: Manual intent always overrides the auto planner (declaring arc_role, pace, weight, or requested duration prevents auto modifications). Protected segments (hold, source_speech, keep_audio) are never shrunk. `disable_auto_story_arc=true` or non-applicable segments (e.g., <3 segments, pure-stock, duplicate identities) disable the planner.
- **Testing**: Validated with A-R falsification suite, 5-segment dynamic-photo true render, 32 focused tests, and full regression pass (1225 tests OK).

### BA1 BUILD Alignment Audit ??COMPLETE (2026-06-14, Codex review passed)

`docs/build-capability-alignment.md`: split into A) pre-BUILD gates B) BUILD
capabilities C) VERIFY audits. motion_graphics BUILD consumer corrected to the
`contract_adapter` build path (Node 14 = scaffold only, not a consumer). Key
finding ??render-time grammar is `active` in BUILD; the material-evidence layer
(needs/satisfies/MM1/VD0) is `declared_only`; M2 retrieval is `partial`.
Smallest high-value gap = BR1 opening/hook. Documentation only, no feature.

### BR1 Opening / Hook Sequence Builder ??implemented + hardened (2026-06-14), pending Codex review

BR1-hardening: `sound_punctuation` cues resolved AFTER clips, only emit when the
`title_reveal` anchor exists (else `anchor_missing:title_reveal`).

BR1 duration contract (2026-06-14): **`shot.dur` = approved window length, so
available = dur (start is the window's position, NOT a deduction)**; video clip =
`min(design_dur, dur)`. Video shots with missing / non-numeric / ?? dur are
**dropped** (`invalid_video_dur`), never rendered at a guessed design length.
Photos keep their design length (loop). 18 tests incl. two real renders +
opening_pool_from_plan?lip extract integration. 823 full regression OK.


`opening_sequence.py` + `run_mv` integration + `tests/test_opening_sequence.py`
(10 tests incl. real render). Compiles an approved recipe into render-plan clips
(hook slow-push / context montage / title-reveal card / sound-punctuation cue /
story-entry marker), `prepend_opening_to_plan` reindexes slot_index across the
whole plan. **Changes timeline AND true render** (real-render test renders the
compiled opening, incl. title overlay, to a video of expected duration).
Graceful fallback: beats with no material are dropped and recorded; no recipe ??
plan unchanged. Consumed via `script["opening_recipe"]`. sound_punctuation is a
cue only (audio wiring is BR3). No VERIFY-only behavior ??it is a BUILD change.

**Goal:** identify which existing dictionaries, Skills, and tools actually
change BUILD output before adding more BUILD features.

Required output: `docs/build-capability-alignment.md`.

Required table:

| Capability | Declared source | Existing tool | BUILD consumer | Timeline evidence | Render evidence | Status |
|---|---|---|---|---|---|---|

Allowed status values:

```text
active | partial | declared_only | missing | deprecated
```

Acceptance:

- Every capability claimed as `active` names a real BUILD consumer and
  timeline/render evidence.
- Declared-only policies and unused tools are listed rather than treated as
  implemented.
- The audit identifies the smallest high-value BUILD gaps.
- This is a bounded documentation audit: no new feature, no new quality audit,
  and no renderer rewrite.

### Tool And Responsibility Boundary

Use this boundary for MM1, BA1, and later BUILD work:

```text
Agent / Skill
  chooses creative intent, project vocabulary, and a supported recipe

Deterministic tool
  validates inputs and compiles the chosen recipe into artifacts/timeline

BUILD
  consumes approved material evidence and recipes to produce the edit

VERIFY
  checks the result; it does not create excitement or choose a replacement

Future UI
  submits review/change-request artifacts; it does not directly mutate
  canonical material maps, contracts, timeline, or route state
```

### BUILD Thickening Backlog

After MM1 and BA1 review, implement one bounded capability at a time in this
priority order:

#### BR1 Opening / Hook Sequence Builder ??P0

Compile an approved opening recipe into a designed opening sequence:

```text
hook visual -> quick context montage -> sound punctuation
-> title reveal -> story entry
```

Acceptance must prove the recipe changes the timeline and true render. It must
gracefully fall back when the required material is unavailable.

#### BR2 Beat-to-Sequence Recipes ??P0 ??COMPLETE (2026-06-14)

`beat_sequence.py` + `run_mv` per-segment hook + `tests/test_beat_sequence.py`
(11 tests incl. real render). A segment opting into `beat_recipe` is compiled
into context ??primary_action ??detail_reaction ??payoff and **replaces that
segment's render-plan slots** (real timeline change). Reuses BR1's approved-window
contract (`_usable_shot`/`_effective_dur`) so all video windows obey {start,dur}.
Graceful fallback drops beats with no material; no recipe ??segment unchanged.
Optional payoff punctuation cue emitted only when the payoff clip exists.
Selectable recipe, NOT a universal action-spine gate.
BR2-hardening (2026-06-14): replaced slots inherit segment semantics ??
keep_audio/audio_role, text/subtitle/narrative layer (every slot, mirroring
`_windows_from_clip`), and `anti_presentation_plan` (BR2 now runs before the
anti-presentation pass); trace metadata (attention_budget/creative_exception/
beat_alignment/reason) still applied by the slot loop. Reverse tests cover
keep_audio/audio_role + text placement.

```text
context -> primary action -> detail/reaction -> payoff
```

#### VD1 / VD2 Visual Diversity Evidence And Soft Ranking ??P1

**VD1 evidence contract completed (2026-06-14); [Historical Blocked: VD2 remained blocked until consistency re-review passed on 2026-06-15. Current State: VD2a BUILD soft-ranking is complete].**
`visual_diversity_coverage.py` + `visual-diversity-coverage` CLI reads the
validated `project_material_map.json` and emits
`visual_diversity_coverage.json`: per-axis labeled/missing counts and scene
references, any/full-label ratios, and an explicit `ready_for_vd2` decision.
The default preconditions are `visual_family` coverage >= 0.70,
`angle_scale` coverage >= 0.60, and an independent coarse-label review with at
least 10 comparable scenes and >= 0.70 agreement **on each required axis**.
`action_family` and `subject` remain measured but do not universally block
because they may be inapplicable. The CLI accepts repeatable
`--consistency-review` project maps. It performs no ranking, selection, or map
mutation.

A reproducible evidence run used 12 real photo assets selected from distinct
folders under `_?渡?敺. The resulting project map had 12 scenes, but actual
VD0 coverage was 0% and no independent consistency review existed. Therefore,
historically, VD2 was truthfully blocked; writing the ranker then would produce a feature that
usually has no labels to consume. Generated evidence is kept under
`.tmp/vd1-real-evidence/` and is not a claimed review artifact.

VD1 Agent-review application entry (2026-06-15): `visual_diversity_review.py` +
`visual-diversity-review` CLI now apply a separate Agent-authored shallow-label
verdict to a project material map. The tool validates reviewer/timestamp,
project-map scene references, duplicate verdicts, `wide|medium|close` scale,
non-empty project-local labels, and existing lineage; invalid input is
fail-closed and never replaces the output. Applied scenes preserve
`visual_diversity_lineage`. This closes the Agent-operation gap without
inventing labels or bypassing VD1: one baseline review may raise coverage, but
[Historical State: VD2 remained blocked until an independent review supplied the
required consistency evidence.]

Gemini-generated 36-image consistency replay (2026-06-15): independent Gemini
and Codex reviews both reached 100% required-axis coverage and agreed on
`angle_scale` for `36/36` scenes, but exact `visual_family` agreement was only
`44.44%` (`ready_for_vd2=false`). This was the trigger for a project-local
visual-family vocabulary contract: family granularity must be agreed without
hard-coding project terms into the generic engine, then independently
re-reviewed before VD2 soft-ranking begins.

VD1.1 Project-local Visual Family Vocabulary Contract (2026-06-15): implemented
`visual_family_vocabulary.py` and the `visual-family-normalize` CLI. The
vocabulary is a project-local contract that different Agents use to align their
visual-family definitions before reviewing. It does NOT represent generic built-in
genre vocabulary in the core engine. Normalization is a deterministic mapping
(canonical/aliases) and is NOT semantic or fuzzy understanding. [Historical State:
VD2 remained blocked by default until coverage consistency was re-measured and passed.]
Re-measuring
Gemini vs Codex reviews on the normalized project-local mountain rescue vocabulary
yielded 94.44% visual_family agreement and 100.00% angle_scale agreement. However,
this is an offline "normalization replay" on pre-existing reviews and does NOT
constitute or prove real independent consistency. [Historical State: The actual VD2
soft-ranking remained BLOCKED until the vocabulary contract was officially frozen,
and both review Agents read this frozen contract to perform an independent re-review of
the images from scratch, passing the consistency check under those conditions.]

Frozen-vocabulary independent re-review completed (2026-06-15): two isolated
workers received only the 36 original images, original project map, and frozen
vocabulary SHA256
`754FA19ED100EAE692BB498012A36E9B8DE09A925F2E7DD47EC08936E996A1D2`.
Both produced complete canonical reviews without prior-answer access.
Fresh consistency measured `97.22%` for `visual_family` and `97.22%` for
`angle_scale`; `ready_for_vd2=true`. The remaining two disagreements are
legitimate boundary cases rather than vocabulary failures. VD1 evidence
prerequisite is now satisfied; VD2 BUILD soft-ranking is complete
(VD2a, 2026-06-15): it runs in `material_retrieval.py` during map-ranked window planning.
Only `visual_family`, `angle_scale`, and `asset_type` are consumed by the BUILD soft selection.
It acts as a soft preference after correctness/relevance/renderability, prioritizing
unused visual family, changing angle scale, and video over photo. It does not become
a BUILD or delivery hard gate.



Real baseline application evidence (2026-06-15): one Agent review was applied
to 12 visually inspected photos from the 67th-graduation material set. All four
shallow axes reached `12/12 = 100%` coverage, while
`ready_for_vd2=false` remained correctly blocked only by
`consistency_evidence_missing`. The application entry also rejects malformed
project-map asset/scene shapes without crashing. Generated review/map/coverage
artifacts remain under `.tmp/vd1-real-evidence/`; this is baseline operational
evidence, not an independent consistency review. Verification: focused VD0/VD1
and material-map suite `41 tests OK`; full regression `1067 tests OK`.

After that evidence exists, labels may be used only as a soft tiebreaker after
correctness, relevance, and approved material.

Photo map-ranked renderability completed (2026-06-15): Photo assets (where `asset_type == "photo"`) are now fully renderable in map-ranked window planning, using the segment's allocated `clip_dur` as their design duration (with `extract_start=0.0`). Photos with zero or missing duration are no longer dropped, while zero-duration video assets or assets with missing/unknown `asset_type` remain correctly unrenderable. This supports rendering of photo assets in map-ranked window planning by mapping them to design duration instead of physical video time window bounds.

#### BR3 Music / Sound Punctuation ??COMPLETE (2026-06-14)

`punctuation.py` + `run_mv` post-render hook + `tests/test_punctuation.py`
(8 tests incl. real audio mix). Consumes BR1/BR2 valid cues: resolves each
anchor to a timeline timestamp (cumulative extract_dur of the matching produced
role, segment-scoped), maps cue type ??CC0 sfx asset, and **remuxes the hits
into the rendered video's audio** via the loudness-preserving sfx filter (real
output change). Cues whose anchor is absent/dropped are dropped
(`anchor_missing:`). No cues ??audio unchanged. Real-mix test proves a hit
raises audio energy at its anchor time vs the silent baseline.
BR3-hardening (2026-06-14): cue resolver computes anchor time with **xfade/
transition overlap** (a crossfading clip starts `transition_duration` earlier),
matching the render's `_build_transition_filter`. `apply_punctuation_to_video`
returns `{status, cues_mixed, error}`; a non-zero ffmpeg exit or missing output
raises `PunctuationMixError` (never reported as mixed). run_mv stays non-fatal
but records `status=failed`, `error`, `cues_mixed=0`. Reverse tests cover xfade
timing and remux failure.

BR3 final alignment (2026-06-14): cue timing now mirrors renderer
**contiguous-segment groups** and clamps overlap with
`min(transition_duration, accumulated_duration, incoming_group_duration)`.
Transitions declared inside one group do not shift time; oversized transitions
cannot produce negative cue timestamps. Focused BR1/BR2/BR3/VD1/MM1 suite:
61 tests OK; full regression: 852 tests OK.

#### BR4 Ending / Payoff Sequence ??COMPLETE (2026-06-14)

`ending_sequence.py` compiles an approved script-level `ending_recipe` into
`callback -> payoff -> closing_title` clips and appends them to the real render
plan. Its default pool walks the story tail backward, all video windows reuse
BR1's approved `{start,dur}` contract, and an optional payoff cue flows into
BR3. Missing recipe/material leaves the existing plan unchanged; title and cue
anchors are emitted only when their visual beat exists. Focused tests include
plan integration, negative fallbacks, bookend composition, and a true ffmpeg
render. Focused BR1/BR2/BR3/BR4/VD1 suite: 64 tests OK; full regression:
869 tests OK.

#### MR1 Map-Based Window Retrieval ??PARTIAL ??ACTIVE (2026-06-14)

Promotes M2 map retrieval from a clip_list-gated path to the **default** local
selection path. Previously `plan_ranked_windows` only fired inside the matched
branch (i.e. after a `match-mv` clip_list existed); a direct `run_mv` with maps
but no clip_list fell through to live VLM scoring. Now:

- **Single loading entry** `project_material_map.expand_project_material_map`
  normalizes a `project_material_map` dict / per-asset list / single map into the
  per-asset maps retrieval consumes (verbatim ??no second scene schema). Unknown
  `artifact_role`, sourceless project asset, and non-numeric scene bounds fail
  loudly; `run_mv` normalizes once at entry.
- **Default + fallback** `mv_cut._plan_local_segment`: map-ranked first whenever
  a valid map exists ??**matched_fallback** (clip_list/explicit file picks) ??
  **live_fallback** (VLM on material_root) ??honest GAP only when nothing exists.
  A map with no evidence-fit scene for a segment never emits an empty/GAP segment
  on its own. Every per-seg entry records `retrieval_path ??{map_ranked,
  matched_fallback, matched, live_fallback, live}`.
- **Window/source honesty** `plan_ranked_windows`: sourceless and zero/negative
  length scenes never enter the timeline; the window is clamped strictly within
  the scene `[start,end]`; slots preserve `source/scene_id/extract_start/
  extract_dur/retrieval_score`. Existing caption/function/pace evidence scoring
  unchanged ??no `visual_family`/diversity ranking, no VD2, no dHash/CLIP/VLM
  dependency added.
- Stock, photo_stack, and `source_speech` (`plan_sound_bite`) paths unchanged.

Falsification tests `tests/test_map_retrieval_wiring.py` (A map-ranked w/o
clip_list; B matched & live fallback; C no-map compat; D project-map expansion;
E malformed/sourceless/zero-length; F window-in-bounds; G **real ffmpeg
map-ranked render**; H stock/source_speech no-regression): 17 tests. Full
regression: **886 tests OK**.

MR1 hardening (2026-06-14): two correctness fixes after self/Codex review.
(1) `_plan_local_segment` fallback now keys on *actual usable slots*, not on
`clip_list is not None`: a segment with no picks (or whose matched picks yield
no window) continues to the live fallback instead of returning an empty
`matched_fallback`; honest GAP only when no `material_root` exists. (2)
`plan_ranked_windows` filters unrenderable candidates (no source / zero-or-
negative length) **before** applying `limit`, so an illegal top-ranked scene no
longer starves a valid lower-ranked window (ranking order preserved; rank_scenes
scoring untouched). Reverse tests added: empty-assignments?ive, empty-matched??
live, illegal-rank-1+valid-rank-2 picks #2. Focused: 20 tests OK; full
regression: **889 tests OK**.

### Deferred Until After BUILD Alignment

- ~~M6a lineage integration: `need_id` through shooting brief and revised
  contract references.~~ DONE (2026-06-14) ??see "M6a Lineage Integration" above.
- M6b `material_delta` and delta-driven script revision.
- Dashboard/UI, Node 14, effects expansion, and front/back-end separation.
- New aesthetic hard gates or further 67th-specific tuning.

### ?瑁?蝝敺??脣?頝?蝯?Codex)

```text
1. ???箏? M0?1?2?3?4?0/M1 ?臬瘜?蝞?,?餅???唳??瑕???
   ?祇?畾萇?頨靘?策?Ｘ?閮?瘙箇?甈?銝?游??芾摩?賢???
2. 瘥??????摨?銝??????桐蒂 grep 撽???憭折◢?芣?極:
   ??蝯梯?(broll_audit)/??/閰?/judge/caption ?券撌脣????啁Ⅳ?芸‵
   ?????撣喋?炎蝝Ｕ?暺?
3. 瘥?摰? = ??????+ agent ??銴 + 蝣箏??扳葫閰?Sensory 蝝敺?霈???
   M0/M1/M2e ?血???靘??整?2026-06-13 ?????◤甇?Ⅱ????
4. 銝??啣???????閰摯?勗?蝯?):?啗???敺? tier,tier1 敹???
   ??鞎餉?蝑??箝狐瘨祥/隤圈?霅?????隞暻潦?甈?銝???SPEC??
5. OpenMontage ??AGPL v3:?芰?璁艙????瑽?銝?蝣潦? import?? vendoring??
6. 銝１:憭???LIP 銋??璅∪?靘陷?蝡?API ?身?I;CLIP ?祈澈 opt-in??
7. ffmpeg ?唾??????4.3.1 撖行葫?踹漲(volumedetect ?????commit
   (amix normalize / ?脤?憛??)??
```

---

## ??2026-06-12(撌脣???: Sensory Phase(??撅斗??S1-S4)

**?暹?閮箸(SYSTEM-DESIGN.md + 憭閰?鋆捱敺?**:蝯?撅?soul/?豢?/摰?蝭憟?
~70-80%)撌脫餈偌皞?**??撅??恍?扯”?曉? ~40%?凝蝭憟?~45%?閮釭??~50%)**
?航??曄?交???蝻箏?璅?S1-S3 摰?銝衣????嗅?頝券???銝?芸???????
?祉?**?誨??E2???孵澈??蝢?*???嗅??亙???瘝??寞???陛?望??菜葫??
?銝????:?孵鋆～隞暻潛?隞嗚??皞?

### S1 ?陛?望?撘?(??芸?;??:閮????+ 皜脫?敺祟閮?

```text
S1a presentation_feel_audit.py(?唳芋蝯?蝣箏???Node 12 audit 摰嗆?)
    ?剖皜砍(?典璈１??:
      static_photo_too_long      ??桃? > max_still_hold(editing_policy 撌脫?甇文?
      no_foreground_motion       ?恍?雿?撟撌?RMS?鋆?filter_static_windows
                                 (mv_cut)???撌格???撠?timeline ??clip ?賣葫
      centered_caption_card      摮蝵桐葉銝?摮?雿? > 25%:敺?ASS 璅??/摮
                                 ??函?(subtitle_presentation/motion_graphics)
      repeated_push_in           ??? >=3 ??????霈 timeline ??still_treatment
                                 / zoompan mode 摨?(P5 撌脰???mode)
      text_blocks_dominate       ????銵/雿?頞?
      single_layer_composition   ??? >=N clip ?∩遙雿?overlay/text/??撅?
    頛詨 presentation_feel_audit.json{findings, score},??dashboard Node 12,
    頝?visual_fatigue ?狡?亦?(edit_artifacts/dashboard_state ?扳?摰? wiring)??
S1b 閮????Node 9,edit_artifacts/_resolve_seg_treatment 銝撣?:
    ?菜葫璇辣?冽?蝔?撠望?鋆?,?芸??函?隞?
      ??        ??P5 ?抒?憭???2-3 ??crop ??(_windows_from_clip ?抒???
      蝵桐葉摮        ??lower-third ?(E2 ???撌脫?)
      ??????    ???頛芣??slow_push/pan_left/pan_right/hold 頛芣?
                        (P5 ??modes 銵典歇摮,?寞?????銝?畾萸??
    摰??斗?:city-lite ??,S1a ?菜葫??0 fail;撠???喳? 3 ?皜砍????
```

S1a status (2026-06-12): COMPLETE. Deterministic audit, Node 12 wiring,
dual-baseline real renders, sensory review, and full regression are verified.
See `docs/archive/decisions/2026-06-12-s1a-presentation-feel-audit.md`. Next: S1b.

S1b status (2026-06-12): COMPLETE. Node 9 now emits deterministic
anti-presentation plans for long still rotation and centered narrative
lower-thirds; the directives reach both the base renderer and light-effects
motion-graphics path. Dual-baseline real renders, sensory review, 0-fail S1a
audits, and full regression are verified. See
`docs/archive/decisions/2026-06-12-s1b-anti-presentation-planning.md`. Next: S2.

### S2 敺桃?憟?cut-on-motion / J-L cut / ???澆)

```text
S2a cut-on-motion:???賊???雿陸?潦??_snap_to_scene_cut(edit_artifacts)
    ?芸?湔??;?啣? motion-peak ?菜葫(撟撌株????撅?冽扔憭???S1a 璈),
    撱?timeline ??scene-cut ??motion-peak ???scene ?芸?,撜啣潭活銋???
S2b J/L cut(narrative ??:頧?閮?銵?撱嗅? 0.3-0.7s?暺 narrative 皜脫?
    ?挾?蝮?video_pipeline xfade/concat 畾?,蝝?timeline 雿宏,銝１蝝???
S2c ???澆:?亙偏敺? 0.3-0.5s ???TS timing(audio/tts_timing.json)撌脫?
    ?亦?;?冽挾?瑁?蝞???tail padding??
    摰??斗?:city-lite 蝝?賜???,??3 ???港犖???喲???agent 霈瘜Ｗ耦+撟)??
```

S2a status (2026-06-12): COMPLETE. Deterministic frame-difference motion peaks,
scene-first/motion-second snap precedence, pre-render concrete-plan snapping,
source-duration safety, Node 10 trace, dual-baseline real renders, and sensory
review are verified. See
`docs/archive/decisions/2026-06-12-s2a-cut-on-motion.md`. Next: S2b.

S2b status (2026-06-12): COMPLETE. Narrative renders now alternate deterministic
0.5s J/L visual seams around unchanged TTS boundaries, persist the plan in
timing/edit artifacts, budget chained-xfade tail correctly, and trim to the
voice duration. City-lite narrative true render, three seam waveform/frame A/B
checks, and full regression are verified. See
`docs/archive/decisions/2026-06-12-s2b-narrative-jl-cuts.md`. Next: S2c.

S2c status (2026-06-12): COMPLETE. Non-final narrative segments now carry a
real 0.3-0.5s speech-tail silence, explicit `speech_end_sec` /
`tail_padding_sec` timing, unchanged phrase subtitles, and audio-probed duration
truth. City-lite narrative true render and three sentence-tail waveform/frame
checks are verified. See
`docs/archive/decisions/2026-06-12-s2c-speech-tail-breathing.md`. Next: S3a.

### S3 ?唾???撅?SFX 璅? + ?單?蝯?撠?)

```text
S3a SFX 璅?:撠??砍?單?摨?assets/sfx/,whoosh/hit/riser ??2-3 ??CC0)??
    蝣箏??扯暺?蝡?頧=whoosh???⊿脣=hit;瘛琿?final_audio(vt_audio,
    ??BGM ?? amix ???喲? ~0.15)??
S3b ?單?蝯?撠?:瘨祥 music_structure.sections(甈??拙停?ender 銝?):
    ?雿?=BGM 敺?餈?蝯?暺絲??offset),擃蔭畾?climax role)撠?賡?畾萸?
    憭??銝?祇?畾?backlog 銝?)??
    摰??斗?:???舐? A/B(? S3)?葡銝甈?agent ?賣?銴閮?撌桃??
```

S3a status (2026-06-12): COMPLETE. Narrative runs now emit sparse deterministic
`sfx_plan.json` cues, rotate a six-file local synthetic CC0 library, and mix
chapter whooshes / explicit title-card hits into final audio without lowering
the base track. City-lite SFX A/B, true final render, audio-level VERIFY, and
full regression are verified. See
`docs/archive/decisions/2026-06-12-s3a-sfx-punctuation.md`. Next: S3b.

S3b status (2026-06-12): COMPLETE. Narrative single-track BGM now consumes
energy-scored `music_structure.sections`, snaps source playback to the nearest
structural offset, and aligns a declared climax with the highest-energy music
section. City-lite offset-0/aligned A/B, true render, sensory waveform review,
technical VERIFY, and full regression are verified. See
`docs/archive/decisions/2026-06-12-s3b-music-structure-alignment.md`. Next: S4a.

### S4 鋆捱擃頂?嗅偏(?∠?憭閰? A + creative_exception)

```text
S4a VISUAL_JUDGE ??蝝?暺???node_registry(撱箄降 node id "10.5" 摮葡,
    NODE_ORDER ? 10 ??11 銋?),verify_fn 霈 visual_review_request/verdict
    摮?扯????dashboard ?芰憿舐內?6 璈銝?,?芣????
S4b verdict 憓? needs_patch 鋆捱(?曉??accept/reject):
    {action:"needs_patch", patch:{type:"window|crop|treatment", hint:{...}}}
    撘?瘨祥:window? extract 蝒?撱?crop? crop_center;treatment?
    still_treatment?isual_review.py ??validate/consume ?拍垢?郊?氬?
S4c creative_exception 蝯曹?甈?(segment 蝝?:
    {"creative_exception":{"rule_bent":"...","reason":"...","risk":"...",
     "requires_review":true}}
    瘨祥蝡?spec_review/pacing_review/visual_fatigue/presentation_feel ?
    ??雿府畾菜?撠? exception ??? warn-with-ack(??review 皜,銝?block)??
    ??????allow_long_hold_when/hold_reason)甇訾??圈?瘜?銝?
    (???詨捆靽???雿???
```

S4a status (2026-06-12): COMPLETE. The existing E6 visual-review gate is now
explicit Node `10.5 Visual Judge` between Timeline and Editor Review, with
optional/warn/done lifecycle verification, request/verdict artifact links, and
dashboard routing. City-lite and gen-smoke real-run dashboard states, montage
sensory review, and full regression are verified. See
`docs/archive/decisions/2026-06-12-s4a-visual-judge-node.md`. Next: S4b.

S4b status (2026-06-12): COMPLETE. Visual verdicts now support bounded
`needs_patch` actions for window, crop, and treatment corrections while
preserving legacy accept/reject verdicts. Patches flow into concrete slots,
crop patches reach the MV ffmpeg renderer, and patched choices are traced as
`agent_patch`. Gen-smoke real-candidate patch smoke and full regression are
verified. See `docs/archive/decisions/2026-06-12-s4b-needs-patch-verdict.md`. Next: S4c.

S4c status (2026-06-12): COMPLETE. Segment-level `creative_exception` now has
a validated reviewable schema, survives canonical/runtime/assembly/timeline
artifacts, and downgrades only the matching rule in spec, pacing, visual-fatigue,
and presentation-feel review to warn-with-ack. Legacy hold reasons remain
accepted but are normalized into visible acknowledged warnings. City-lite
real-video baseline review and full regression are verified. See
`docs/archive/decisions/2026-06-12-s4c-creative-exception.md`. Next: E7 or next roadmap
priority.

Sensory integrated acceptance status (2026-06-12): COMPLETE for the
MV/local-material/light-effects branch. The fresh bakery v5 run passed true
render, technical VERIFY 100, editor review, treatment audit, editorial QA 85,
light-effects 5/5, agent keyframe sensory review, and 663-test regression.
Integration fixes covered missing source audio, photo-stack pacing, safe
motion-peak snapping, hold-reason trace, and rendered-timeline beat grids. See
`docs/archive/decisions/2026-06-12-sensory-integrated-bakery-acceptance.md`.

### ?瑁?蝝敺??脣?頝?蝯?Codex)

```text
1. ???箏? S1a?1b?2?3?4,瘥??蝡?commit + 皜祈岫;銝?銝西????
2. 瘥????? ???葡 + agent 霈???賣?銴 + 蝣箏??扳葫閰?銝撩銝銝
   (PlayRes ??:?桀?皜祈岫???唳?摰撩????
3. ?啣皜砍/鋆?銝敺粥?Ｘ? wiring 璅∪?(visual_fatigue ?舐???,銝??亦???
4. 銝１:憭???蝡?API?LE UI?emotion/blender(non-goals 銝?)??
5. ?箸???city-lite(??)+ skill-smoke(MV)?皞??孵??孵??質????扼?
```

---

## ?? 2026-06-12(鋡?Sensory Phase ?誨/?豢): Effects Phase(?寞??)

???挾(P1-P6 + city-lite ?蔥撽?)撌脫;?祇?畾萄 Codex ?芸末??motion_graphics
曋寞銝?*憛怨”?曉??批捆**,銝??剖?箝?

### Backend ?０(build_profile.motion_graphics_backend)

```text
ffmpeg_libass   ??撌脣祕雿?ASS ??+render plan+撖行葡 smoke)???祇?畾萎蜓??
                摮? / lower-thirds / ?脣漲璅惜 / 撘瑁矽摮?
html_playwright ??MVP 撌脰粥??HTML/CSS/JS ?(web ?舀?鞊???2D motion
                隤?:摮?/easing/SVG/canvas)??Playwright ?⊿?芸?/?ˊ
                ??ffmpeg overlay???閮?敶????”/infobox/閮?具?
remotion / mlt / blender  ?? enum 撌脩?雿???挾?格?(?郎??蝑?瘙?????
```

### 撌乩???

```text
E1 ?箸?????city-lite / skill-smoke 隞?render_profile=light_effects ??,
   ?澆?暹? effects ???銝?閬死??(??city-lite 摮? PlayRes ??:
   ?桀?皜祈岫???啗?閬箇撩??瘥??寥閬?皜???)??
E2 ffmpeg_libass ?摨?title card ?脣?游??怒ower-third?挾?賣?蝐扎?
   撘瑁矽摮??刻粥 editorial_design.effects_strategy 摰??,??畾菔?
   (?萄?:?寞????,??憌?effects-director ???)??
E3 P2 ??蝡航?摰?BUILD ??瘨祥 attention_budget?? 2026-06-12 摰?,
   ?寞?蝭憟?瘜冽???蝞?皞?
E4 html_playwright MVP:銝???????詨?/infobox)韏圈? 2026-06-12 摰?
   HTML?laywright?????verlay ?券?,撱箇?蝚砌? backend ??verify 璅∪???
E5 P4 ?嗅偏:CapCut GUI 頛撽?(鈭箏極???? 2026-06-12 摰?
E6 agent-as-visual-judge V1:stock ?貊??寞? evidence ??await_visual_review
   ??agent verdict ??resume嚗???ollama/none ??璅∪?????賢極銝?
E7 蝝??云憟?閫?瘥?瑞????Ｙ??湔銝剝?+????montage嚗 agent
   撖怠??舫??刻?????誨??撘望芋?炊畾箝?
E8 agent-judge ?游?:撠?E6 璅∪?撱嗡撓??narrative prepick ??Node 12
   content/editorial QA嚗??run ?蔥?甈∩犖撌?agent gate??

瘥?E 摰??斗?:?葡頛詨 + keyframe 鈭箇銴 + P1 audits ?? + 皜祈岫??
```

### 2026-06-11 E1 ?瑁????

E1 撌脣???`skill-smoke` ?祕 light-effects baseline嚗?

- real render ??VERIFY ??嚗?1.5嚗?
- timeline/caption/broll/visual P1 audits ??嚗eyframe grid 撌脖犖?潸??賂?
- ?啣? `light_effects_baseline_review.json` ??dashboard Node 14 gap 憿舐內嚗?
- 撖行葫蝯?嚗? planned effects?? rendered effects??% effect coverage??

E2 ?芸????迨蝣箏??綽????title card / section label /
lower-third 蝑?摮? ffmpeg/libass ?嚗??? xfade ??Ken Burns??
霅??捱蝑?
`docs/archive/decisions/2026-06-11-effects-baseline-and-recipe-order.md`??

### 2026-06-11 E2 ????瑁????

E2 蝚砌?畾萄歇摰?銝阡??祕敶梁?撽?嚗?

- title sequence?ection label?ower-third ??3 ??ffmpeg/libass ?撌脩?甇????
- renderer ownership 撌脫?蝣箏?嚗ight-effects / motion-graphics profile 靽??? trace嚗?
  雿 motion-graphics compositor ?桃鞎痊?航???嚗??base drawtext ???嚗?
- real render?ERIFY 91.5?1 audits ??keyframe 鈭箇銴??嚗?
- effects contract 隤?撌脖耨甇??hold video 銝???Ken Burns嚗eat/direct cut 銝???
  xfade嚗hoto Ken Burns ??敺?MV renderer ?神?祕 evidence嚗?
- 靽格迤敺?real baseline ??3 planned / 3 composited / 0 gaps / PASS??

E2 explicit xfade 撌脣???撠 fixture ?芸?Ⅱ摰?? `transition: xfade`
???ffmpeg `xfade` / `acrossfade`嚗imeline 撠恐???瑕遣璅∠ intentional
overlap嚗??舐 montage/fast ?勗??冽??

?祕撽?嚗?
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260611-effects-e2-explicit-xfade-v6`

- VERIFY 92.5 PASS嚗uration/subtitle/technical quality ??100嚗?
- light-effects baseline 4 planned / 4 rendered / 0 gaps / PASS嚗?
- timeline/caption/broll/visual audits ?券 PASS嚗?
- xfade boundary grid 蝣箄? 0.5 蝘?crossfade 撖阡??航?嚗?
- caption SRT ?芸???narrative/subtitle嚗??? label/name super ?嗅?撟?

E2 ffmpeg/libass light-effects baseline 撌脤???銝?甇乩? roadmap ?脣 E3
attention budget / pacing enforcement??

### 2026-06-12 E3 attention-budget BUILD allocation

E3 撌脣???Node 9 ??BUILD ??Node 10 ?亦?嚗?

- `contract_adapter` ??render ? Node 9 assembly plan ?‵瘥挾
  `attention_budget`嚗?
- 靽格迤 `audio.role: music` 鋡怨炊?斤 narration mode ???隤歹?
- 蝝璅??祆挾雿輻 `[1.5, 4.0]`嚗??賡璅蝙??`[0.8, 2.0]`嚗?
- music/visual owner ??撖?generic hold / ? pacing嚗pening/closing/title
  ??narration-owned hold 靽?嚗?
- render plan ??`timeline_build` 靽?撖阡?瘨祥??attention-budget trace??

?祕撽?嚗?
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-e3-attention-budget-v2`

- seg2嚗? ??8 shots嚗edian 3.532s ??2.649s嚗?
- seg3嚗? ??12 shots嚗edian 4.238s ??2.825s嚗?
- total cuts嚗?6 ??22嚗pening/closing 隞? 1 shot嚗?
- VERIFY 92.5 PASS嚗???P1 audits ??light-effects baseline PASS??

E3 ????

### 2026-06-12 E4 html_playwright MVP

E4 撌脣??洵鈭撖行葡 motion-graphics backend嚗?

- `info_card` ???deterministic HTML嚗? Python Playwright ?頂蝯?
  Chrome ???芸??? PNG嚗?
- 摨?撟??ffmpeg 蝺冽? alpha qtrle MOV嚗?靘恐?? `start_sec`
  ???蜓敶梁?嚗?
- manifest 靽? HTML?rames?verlay?rame count ??composited ???
- safe backend dispatcher ?箏?????`ffmpeg_libass`嚗???
  `html_playwright`嚗?
- 1080p info card ?雿祝摨?620px嚗蜓?詨? 150px?璅?40px嚗?????航???

?祕撽?嚗?
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-e4-html-playwright-v2`

- Playwright 撖阡??芸? 30 撟嚗lpha overlay ??蝯蔣?????Ｙ?嚗?
- manifest output ??`composited`嚗?
- contact sheet ??1080p midpoint 撌脖犖?潸??賂?瘛∪/??/瘛∪甇?虜嚗?
  lower-third 摮皜?銝鋆???

E4 ??嚗?銝甇乩? roadmap ?脣 E5 CapCut GUI 頛鈭箏極??

### 2026-06-12 E5 CapCut GUI gate ?瑁????

撌脣遣蝡?撽?獢?
`C:\Users\user\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\20260612-e5-text-audio-gate`

- draft JSON ??2 ??video segments?? ??editable text segments?? ??audio
  segment嚗?
- video/audio 蝝?頝臬???嚗?
- smoke 霅?雿
  `C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-e5-capcut-gui-gate-v1`??

CapCut 8.7.0.3685 GUI 頛撽?撌脤?嚗?

- 撖阡??? `20260612-e5-text-audio-gate`嚗頛?航炊嚗?
- ??頠賊＊蝷箏畾?editable text嚗E5 TEXT TRACK`?AUDIO + TEXT LOADED`嚗?
- ??頠賊＊蝷箔?璇?audio 頠??拇挾 video 頠?
- ?汗?恍??憿舐內??閬???

E5 ??嚗4 CapCut text/audio draft bridge 撌脣???JSON ??GUI ?惜撽???

### 2026-06-12 H2 music resolver hygiene

- `_resolve_music_path` 銝??? repo root ??project root ?遙?閮?
- ?芸?閫???芣??蝣?`args.music`?run_dir/bgm.*`?project/input/*`嚗?
  ?血?靘?contract `music.query` ??嚗?
- repo-root 瘚答 mp3 撌脫??
  `C:\Users\user\Desktop\video_project\recovered_media\stray_repo_audio`??

H2 ??嚗?銝甇乩? E6 撖虫? agent-as-visual-judge V1??

---

## ??2026-06-11: Expressiveness & Chain Merge ??撌脣銵?P1-P6)

> ???P1 ????city-lite 閬死撽?敺? PlayRes/?瑁?靽格迤 `4d08a88`)??
> P2 ?(撖抵?蝡臬???BUILD ??蝡????寞?? E3)?3 ??city-lite canonical
> contract?arrative E2E,qa 97)?4 ?(draft JSON 摰?;GUI 頛????E5)??
> P5 ?6 ??曋寞+smoke)??雿菟?霅???撖急???閬?
> `docs/archive/decisions/2026-06-11-e2e-smokes-and-next-phase.md` ??skills/spec-contract.md??

### ??????餈賣滲)


**?嗆?(銝? C0-C6)撌脤???DoD**:蝯曹? driver(route.py ?敶??pec_review
pre-BUILD gate?ender-free dry-build??舐?撖?E2E ??
(skill-smoke MV 35s ??verify 91.5 PASS / editorial_qa 94;
city-day narrative 5min 21 畾????券???TTS ??+BGM+VLM gate 頝???16 tests OK??
霅?:git log 2026-06-10/11 + `docs/archive/decisions/2026-06-11-e2e-smokes-and-next-phase.md`??

銝??挾?敹??舀憭?gate,??*????*:蝯?撅???暻???敹?撌脰◤瘨?,
銵函撅??恍?批?????/摮?蝢?)?舀?予?望???:

```text
P1 摮? polish(蝣箏???~1 憭?
   銝凋?蝵桐葉??暺?瘣??敶Ｙ征????蝝閫??摨艾銵?14-16 ?典耦摮?憭銵?
   ??editorial_design.subtitle_strategy ?身 + subtitle-director ??撌亙??
P2 瘜冽???蝞?pacing(?蝙?刻皞潛楊蝣潮脰???
   ????刻牧??,?芸?撠望????segment 蝝?hold ?? =
   f(???, 蝝???蝔漲, ?單??賡?)???抒?寞? 1-2s????1s/2 撘?敹怒?
   ??畾萄 hold ?瑯??單?畾萄??翰?芥?蝝?pacing_review / visual_fatigue??
P3 canonical contract ??narrative ??瘚??寞祥?亙銝?蝔?
   contract ??narration facet ??銝隞?SPEC 擗萄璇?;video_pipeline.py 霈?
   runtime 摨???narrative runner(銝撱Ｘ????臬???蝻箇???adapter)??
   ?葆??spec_review/soul 撅文葆蝯血?賜???
P4 CapCut draft 鋆?text/audio 頠?Half-baked Bridge 鋆?)
   BGM/摮?/outro ?湔??draft,霈犖?典?ㄐ?質矽,???臬敺?ffmpeg 撘瑁? finalize??
   ??NarratoAI jianying_draft_builder(??瘜????冽?甈?銴ˊ,
   閬?docs/reference-repos-map.md)??
P5 ?抒?憭?撅???銝撘萇????憭?crop/push ?⊿)
   ??multi-window ???摨怒???券???crop 摨扳?+zoom 頝臬?蝝Ⅱ摰?
   VLM ?暺?蝝??末 review??
P6 銵函撅?motion_graphics backend(?PT ?予?望)
   light_effects ??motion_graphics ?祕雿?;effects-director ??Node 14??

Opt-in(??閮?:?脩垢 VLM 隞脰?韏?model_routes(local-first ?輻?銝?;
4b ?賊冗?敺??日憿?畾菜???隞脰?)??

Non-goals 撱嗥?:銝?摰 NLE UI(??dashboard + 撖怠????祟??鋆??Ｘ??
??nly-seg ?葡?? in/out?蝒?皜脯?瑽矽?氯?Node 14 revision);
銝?閮剝蝡?API??
```

---

### 2026-06-11 ?瑁?霅?(Codex ?寞活)

The current P1-P6 implementation direction is complete:

- P1 subtitle polish: shared presentation policy, punctuation/line wrapping, bottom-center styling.
- P2 attention-budget pacing: narration/music/visual ownership and visual-fatigue integration (audit-side; BUILD allocation does not consume it yet).
- P3 canonical contract to narrative chain: traceable narrative adapter and runtime routing.
- P4 CapCut text/audio tracks: editable text tracks and explicit BGM/audio tracks in real drafts (JSON-level done; CapCut GUI load verification is a pending human/CU gate).
- P5 photo multi-shot expander: one photo expands into distinct push/pan/detail shots with timeline trace.
- P6 motion graphics backend: canonical timeline to Node 14 contract/plan and rendered ffmpeg/libass overlays.

Verification evidence:

- Full suite: `python -m unittest discover -s tests` -> 541 tests OK.
- P5 real ffmpeg smoke: one photo rendered as slow-push, pan-right, and detail-push shots.
- P6 real ffmpeg/libass smoke: generated ASS overlay rendered into a playable 2-second MP4.

Dashboard Build Control Surface is complete:

- dashboard state exposes a read-only `controls` contract for profile, generated
  asset status, and route/next-action;
- every node exposes absolute links for artifacts that actually exist;
- self-contained dashboard/story-map output embeds the control contract.

C6 hygiene is complete:

- `.understand-anything/` remains ignored local exploration output;
- `graphify-out/` remains the accepted project map;
- `.graphifyignore` keeps external reference repositories, generated media, and
  run outputs outside the formal project map;
- `HANDOFF_CURRENT.md` and `RUNBOOK.md` point to the current Windows state.

Graphify was refreshed once after P1-P6 stabilized: 104 code files produced
1,734 nodes and 2,575 edges. The clean source-only rebuild contains the new
attention-budget, subtitle-presentation, motion-graphics, photo multi-shot, and
dashboard-state modules; retired `route.py` and `reference repo/` have zero
source nodes.

---

## ??2026-06-08(撌脣???2026-06-11): Converge One Complete Pipeline

The next work is **pipeline convergence**, not more tool expansion. Treat this
section as the current source of truth for Claude/Hermes/Codex implementation.
Older roadmap sections are historical context unless they directly support this
convergence work.

Both render paths have passed E2E:

```text
ffmpeg canonical path:
  SPEC -> contract-run/runtime -> final.mp4 -> VERIFY/P1 audits -> PASS

CapCut optional finishing path:
  SPEC -> contract-run/runtime -> real CapCut draft -> human/CU GUI export
  -> capcut-finalize -> final video -> VERIFY/P1 audits -> PASS
```

The remaining problem is not whether the tools can work. The problem is that the
workflow is still spread across too many partially connected entrypoints. The
goal is one coherent, repeatable run chain from SPEC to final verified output.

### Target MVP Flow

```text
Node 0  Brief / interactive SPEC
-> Node 3  segment_contract.json
-> Node 2  material coverage / material requirements
-> Node 4-7 contract facets: story, sound, effects, subtitles
-> Node 8  build_profile.json
-> Node 9  assembly_plan.json
-> Node 10 timeline_build.json
-> Node 11 editor_review + deterministic audits
-> Node 13 render candidate
   -> ffmpeg path: final.mp4
   -> CapCut path: draft folder -> capcut_exported.mp4 -> capcut-finalize
-> Node 12 verify_result + P1 audit pack
-> Node 14 revision only when verify/audit fails
```

### Priority Order For Claude / Agents

Do these in order. Do not start Remotion, HTML/Playwright, Blender, or new
provider work before this list is complete.

#### C0. SPEC Entry And Execution-Readiness Gate

Review:
The canonical public SPEC is `segment_contract.json`, but the complete route must
start from an interactive brief and remove ambiguity before BUILD. Runtime must
not silently invent missing story/material/audio/effects/subtitle decisions.
The editing-quality contract for this step is
`docs/editing-intent-sequence-grammar-spec.md`.
That spec also defines Node 12 `editorial_qa.json`, reviewed by the main flow
agent/strong model rather than a subagent.

Build:
- Define one supported greenfield entry:

```text
interactive brief
-> editorial_design.json
-> brief.json
-> segment_contract.json
-> contract validation
-> material requirements / coverage
-> build_profile.json
-> ready_for_build
```

- Keep `segment_contract.json` provider/backend neutral.
- Record unresolved questions and required human decisions explicitly.
- Convert Pre-SPEC editorial choices into BUILD-consumable plans, not just
  descriptive prose.
- Produce an execution-readiness result before runtime enters BUILD:

```text
ready_for_build = true | false
blocking = [...]
next_action = revise:director | await_material | ready
```

- Ensure each segment has enough executable intent:
  - story purpose / content;
  - required or acceptable material;
  - text/subtitle/narration intent;
  - audio intent;
  - effects intent or explicit `none`;
  - fallback policy;
  - verification-sensitive requirements.

Verify:
- One general SPEC example reaches `ready_for_build=true`.
- One intentionally ambiguous example is blocked with actionable questions.
- Contract validation remains independent of ffmpeg/CapCut/provider selection.

#### C1. Runtime Route Unification

Review:
Runtime can resume, rerun, compile, verify, and handle some material/generated
provider waits. CapCut export/finalize must become a first-class route instead
of a hidden manual step.

Build:
- Add a route for `render_backend=capcut_draft`.
- After `contract-run` writes the CapCut draft, runtime should pause clearly:

```text
next_action = await_capcut_export
expected artifact = capcut_exported.mp4
instruction = open CapCut, export to this run folder, then resume
```

- On resume, if `capcut_exported.mp4` exists:
  - write/update `capcut_export_manifest.json`;
  - run `video_tools.py capcut-finalize`;
  - produce the canonical post-CapCut final artifact;
  - continue to Node 12 verify.

Verify:
- Unit test `await_capcut_export` with and without `capcut_exported.mp4`.
- Regression test that the default ffmpeg path is unchanged.
- Focused smoke on the `coffee` run.

#### C2. Artifact Contract Cleanup

Review:
Artifacts exist, but final naming must be strict across ffmpeg and CapCut so
agents do not guess which file is final.

Build:
Define one run artifact contract:

```text
final.mp4                  canonical accepted final candidate
capcut_exported.mp4        raw GUI export, never accepted directly
capcut_finalized.mp4       optional post-CapCut intermediate if needed
capcut_export_manifest.json
artifact_manifest.json     indexes all of the above
state.json                 carries pass/next_action
```

If `capcut-finalize` writes a different name today, either standardize it or
record it explicitly in `artifact_manifest.json` and dashboard state.

Verify:
- Manifest tests assert both render paths expose the same final artifact surface.
- Dashboard state shows which backend produced the final.

#### C3. Node / Skill / Runtime Alignment

Review:
Node registry is good enough, but CapCut introduced a human/CU gate that should
be visible as a controlled Node 13 route.

Build:
- Keep Node 13 as `Render Candidate`.
- Treat CapCut GUI export as a Node 13 sub-state, not a new core node unless
  absolutely necessary.
- Make dashboard/runtime show:

```text
Node 13: Render Candidate
  backend: ffmpeg | capcut_draft
  status: running | awaiting_export | exported | finalized
  artifacts: capcut_draft_manifest, capcut_export_manifest, final.mp4
```

Verify:
- `runtime.py status --project coffee` makes the next action obvious.
- No hidden manual step should be required outside the status text/runbook.

#### C4. One Runbook

Review:
The project has many historical documents. Claude and Hermes need one current
runbook for the MVP, not a search exercise.

Build:
Update `RUNBOOK.md` with exactly these flows:

```text
Flow A: ffmpeg default
  project-init -> project-new-run -> runtime resume -> verify

Flow B: CapCut finishing
  build_profile.render_backend=capcut_draft
  runtime resume -> open CapCut -> export capcut_exported.mp4
  runtime resume -> capcut-finalize -> verify

Flow C: rerun / revision
  rerun node -> verify failed -> fix smallest affected node -> resume
```

Verify:
- Commands are copy/pasteable on Windows PowerShell.
- Do not use WSL paths except as reference notes.

#### C5. Dashboard Minimum Control Surface

Review:
Dashboard should remain read-first. This is not a cinematic director UI.

Build:
Add only controls/status needed for the converged MVP:

```text
current project/run
active backend
node status
next_action
open key artifacts
CapCut export instruction when awaiting_export
verify score and audit findings
editorial_qa summary and routed findings
```

Do not add cinematic shot controls, Remotion controls, Blender controls, or
large parameter panels.

Verify:
- Dashboard generated from ffmpeg run and CapCut run.
- Text makes the next action clear without reading JSON.

#### C6. Graphify / Understand Anything Hygiene

Review:
Graphify is the project map; Understand Anything is useful exploration output.
Neither should pollute the canonical source tree unless intentionally curated.

Build:
- Keep `graphify-out/` only as the accepted project map.
- Decide whether `.understand-anything/` is ignored local exploration output or
  curated into stable docs.
- Do not commit UA cache/intermediate files by default.

Verify:
- `git status --short` should not show accidental knowledge-cache output.
- If graphify is stale after convergence changes, update it once after code is
  stable.

### Explicit Non-Goals During Convergence

```text
Remotion backend
HTML/Playwright render backend
Blender / AE / heavy 3D effects
new cinematic director UI
new provider-specific SPEC fields
new generated-image provider architecture
large dashboard redesign
```

### Definition Of Done

Convergence is complete when:

```text
1. A new project can start from SPEC and reach PASS via ffmpeg.
2. The same or representative project can reach PASS via CapCut finishing.
3. runtime.py status/resume/rerun explains every next_action.
4. artifact_manifest.json is complete for both paths.
5. dashboard shows backend, artifacts, verify, and next action.
6. RUNBOOK.md has copy/paste Windows commands.
7. Full unit suite passes.
8. HANDOFF_CURRENT.md points to this convergence state.
```

## ??2026-06-06(撌脣???: Windows Native Migration

The active development project has moved to Windows:

```text
Primary development project:
  C:\Users\user\Desktop\video_pipeline

Windows project/output root:
  C:\Users\user\Desktop\video_project

Example project:
  C:\Users\user\Desktop\video_project\coffee

WSL reference implementation:
  \\wsl$\Ubuntu-24.04\home\lio730309\video_pipeline
```

Windows is now the primary development target. The WSL project remains a
reference implementation and regression comparison source during migration. Do
not continue feature development independently in both copies.

Migration must be seamless and incremental:

```text
preserve canonical SPEC/artifact contracts
-> replace one Linux assumption at a time
-> run focused Windows verification
-> compare behavior with WSL when relevant
-> run broader Windows regression tests
-> continue to the next migration step
```

The implementation source for this migration is:

```text
docs/windows-native-migration-spec.md
```

Current Windows baseline:

```text
Python 3.10.16
video_tools.py --help: pass
All Windows unit tests: 255 tests pass (100% success)
Windows project_workspace focused verification: pass (paths normalized to POSIX style)
Full native video runtime: verified (W5 canonical no-effects E2E completed successfully)
Dashboard, state, and story-map monitoring: verified (W6 completed successfully)
Graphify: rebuilt successfully on Windows (W7 completed successfully)
```

Migration priority:

```text
W0 establish Windows source/output boundaries -> [Completed]
W1 add cross-platform tool/path resolver -> [Completed]
W2 remove hardcoded WSL/Linux paths -> [Completed]
W3 replace bash-only orchestration with Python runtime -> [Completed]
W4 verify ffmpeg/ffprobe/yt-dlp/Ollama on Windows -> [Completed]
W5 run canonical no-effects E2E on Windows -> [Completed]
W6 verify route/dashboard/project monitoring -> [Completed]
W7 rebuild Graphify from the stable Windows source tree -> [Completed]
```

Do not rebuild Graphify before the Windows runtime boundaries stabilize. The
existing WSL graph remains a historical architecture reference, not the current
Windows source-of-truth graph.

## ??2026-06-07(撌脣???: Editing and VERIFY Tool Pack

Approved integration reference:

```text
https://github.com/Hao0321/video-autopilot-kit
```

The external MIT-licensed repository is a technique/tool reference, not a new
workflow owner. The canonical implementation spec and execution plan are:

```text
docs/video-autopilot-tool-integration-spec.md
docs/construction-guides/superpowers/plans/2026-06-07-video-autopilot-tool-integration.md
```

Implementation order:

```text
P1-A deterministic audits                                         [Completed 2026-06-07]
  timeline invariants      -> timeline_invariants.json (Node 11)
  B-roll ratio/repetition  -> broll_audit.json (Node 11)
  caption gap/overlap      -> caption_audit.json (Node 11/12)

P1-B visual evidence                                              [Completed 2026-06-07]
  keyframe grid/contact sheet     -> keyframe_grid.jpg (Node 12, ffmpeg)
  optional configured VLM audit   -> visual_audit.json (Node 12, mechanical + optional VLM)

P2 creator_profile.json                                          [Completed 2026-06-08]
  creator_profile.py + creator-profile CLI; brief always overrides creator
  defaults; contract-run --creator-profile fills build_profile broll policy and
  writes creator_profile_applied.json lineage (indexed in manifest)

P3 optional CapCut draft backend                                 [Scaffolding 2026-06-08]
  version-independent framework built (build_profile.render_backend,
  capcut_backend.py: provider-neutral draft manifest + export-as-render-candidate,
  human/CU gate, Node 12 verify required). Real proprietary .draft serialization
  deferred ??CapCut not installed; see docs/archive/decisions/2026-06-08-p3-capcut-optional-backend.md.
  ffmpeg remains canonical; never a core dependency.
```

P1 status: implemented as focused `video_pipeline_core` modules with thin
`video_tools.py` CLI shims (`timeline-audit`, `broll-audit`, `caption-audit`,
`keyframe-grid`, `visual-audit`), optional `artifact_manifest.json` keys,
Node 11/12 dashboard evidence, and a pure `runtime_orchestrator.resolve_audit_route`
consumer. Mechanical-only verify works without Ollama; policy is parameterized
(no creator keyword map baked in). Graphify rebuild intentionally deferred until
P1 boundaries settle. See `docs/build-tool-runner-spec.md` P1 section.

P1.5 (auto-wire, 2026-06-07): `contract-run` now auto-produces the enabled audit
artifacts in a single build pass, gated by `build_profile.verification_tools`
(default OFF, so existing runs are unchanged). `caption-audit` reads a real
`subtitles.srt`; `keyframe-grid` fails loudly on empty output. This closes the
Codex review's main gap ("the canonical build chain should self-produce audit
evidence"). Full Windows suite: 320 tests OK. Remaining P2-level follow-up:
future-proof `timeline_invariants` for non-`clips` timeline shapes.

Graphify rebuilt 2026-06-08 (source-only) after P1/P1.5 settled: 1346 nodes,
1992 edges, 115 communities from 121 source files; the P1 verification tool pack
and its Node 11/12 integration are captured (dedicated hyperedge present).
Outputs in `graphify-out/`. Next milestone: P2 creator_profile.json.

Constraints:

```text
Node 11/12 own P1 evidence and findings
all outputs are explicit artifacts indexed by artifact_manifest.json
segment_contract.json remains provider/backend neutral
CapCut and Computer Use remain optional
mechanical-only Verify must work without Ollama
do not copy author-specific keyword maps or creator preferences
```

## ?? 2026-06-05 Canonical State(甇瑕敹怎,?暹?隞?HANDOFF_CURRENT.md ?箸?)

### 銝?亥店?

??蝟餌絞撌脣??? `script.json` flat workflow嚗?? **canonical contract-led video workflow**嚗?

```text
brief / interactive spec
-> segment_contract.json
-> contract_adapter.py
-> generated_mv_script.json
-> mv_chain / render
-> artifact_manifest.json + state.json + verify artifacts
```

?曉?敹??臬???SPEC嚗霈?銝隞?SPEC ?臭誑??銝? BUILD profile 頝銝??釭/?/?漲?蔣??

### Source Of Truth

```text
segment_contract.json
  public canonical SPEC??餈唳挾?賜????瘙?喋?摮?閬粹◢?潸? fallback 隤祕????

generated_mv_script.json
  legacy runtime payload? contract_adapter ?Ｙ?嚗靘??mv_cut/video runtime 瘨祥??

artifact_manifest.json / state.json
  BUILD + VERIFY ?瑁???策 agent/dashboard/operator ?方???

build_profile.json
  BUILD provider/profile artifact?捱摰甈?run 雿輻 no_effects/light_effects/
  motion_graphics?allback provider?otion graphics backend?odel routes??

generated_asset_requests.json
  generated fallback ??provider-neutral 隢?皜???contract ?迂?挾?賜??
  identity/proof/must_include 銝???蹂誨??
```

?? `script.json` 隞閬 runtime/legacy layer嚗????箏??SPEC ?孵???

### Current Graphify Architecture

???Graphify 頛詨雿 `graphify-out/`??026-06-05 撌脩 source-only graphify skill
蝔???嚗???run output????media?rchive 憿????芣? engine?kills?ocs??
examples ??tests嚗?

```text
120 files 繚 ~82,119 words
1188 nodes
1561 edges
122 communities
95% EXTRACTED / 5% INFERRED / 0% AMBIGUOUS
Import cycles: none
Edge diagnostic: no dangling / duplicate / endpoint-collapsed edges
```

銝餉?蝷曄黎?瑽?蝢抬?

```text
contract_adapter.py cluster
  canonical SPEC -> legacy runtime payload -> manifest/run artifacts??

spec_contract.py / FallbackRouteTest cluster
  brief?egment contract?allback route?ode 9-14 閰?摰???

mv_cut.py / run_mv cluster
  beat-driven MV runtime嚗 stock/local/live 銝??胯ender plan?udio/text layer??

edit_artifacts.py cluster
  Node 9 assembly_plan ??Node 10 timeline_build嚗??????????

editor_review.py cluster
  Node 11/12 deterministic clip review??

music_structure.py cluster
  music_structure.json嚗? beat/grid/section 霈??臬???artifact??

model_routing.py cluster
  model_routes.json嚗? verify/content_qa/asr/agent model 霈? BUILD artifact??

stock_first.py / vt_stock.py cluster
  stock-first conceptual MVP route嚗exels first + Pixabay fallback??

motion_graphics.py cluster
  optional motion graphics contract/render_plan/manifest scaffold嚗ashboard 隞?Node 14
  Revision ?嚗ffects 銝 Node 14 ?祇???

Generated provider cluster
  build_profile / generated_asset_requests 撠?generated fallback 靽? provider-neutral??
  ComfyUI 撌脫 deprecated provider嚗?雿 active default嚗??fallback image ?釭隞?
  Antigravity / assistant_imagegen / codex_imagegen ?芸???
```

Graphify 憿舐內??god nodes 隞? `ToolError`?run()`?pipeline()`?_audio_duration()`??
`run_tool()`?compose_and_qa()`??026-06-05 撌脣?靽格迤?拙祕??朣?嚗?

```text
video_pipeline.py fix_class -> fix_target now aliases video_pipeline_core.vt_core.FIX_TARGET.
run_content_qa() now invokes python3 -m video_pipeline_core.content_qa instead of a removed root content_qa.py.
```

?瑞?隞?????`video_pipeline.py` ??CLI facade ?葉敹改?雿??MVP 撌脣??
canonical adapter + package module 頝舐?????

### Completed Runtime Readiness

?桀? V3/P7 撖虫????

```text
P0 canonical run CLI + manifest: done
P1 music_structure.json: done
P2 assembly_plan/timeline_build split: done
P3 editor_review.json deterministic checks: done
P4 scene-cut snapping/crop metadata: done
P5 model_routes.json: done
P6 motion_graphics contract scaffold: done
P7 stock-first connectivity + Pexels/Pixabay fallback: done
P8 build_profile.json + generated_asset_requests.json: done
P9 package/module entrypoint alignment: done
```

撌脤?霅?

```text
python3 -m unittest discover -s tests -v
Ran 222 tests
OK
```

撖西? stock-first conceptual MV嚗?

```text
examples/stock_first_concept_mv.json
-> stock_first_route.json
-> generated_mv_script.json(source=stock)
-> Pexels/Pixabay stock fetch
-> timeline_build/editor_review
-> stock_first_run/final.mp4
```

蝯?嚗?

```text
final.mp4 duration: ~60s
stock segments: 3/3 fetched
editor_review: pass
state pass: true
blocking: []
```

### SPEC Layer Decision

SPEC 撅斤???剁?銝??芸???schema??蝥????撘瑁?撽?摰?嚗?

```text
靽?鈭?撘?甇?
靽?畾菔?桃???鈭???
靽? fallback 隤祕??
蝳迫 must_include / identity_sensitive / proof_critical 鋡?stock/generated ?瑟?
```

?迤??皜賊◢?芣????鈭?璊蔣???澆耦撘?甇?V4 ????隢??舀? SPEC 霈?嚗?
??/撘瑕? narrative spine 雿?惜?嗆?嚗?

```text
narrative.thesis
narrative.arc / 韏瑟頧?
narrative.big_story
narrative.breakdown
narrative.mode_plan
segments[].core.story_purpose ladder ??arc
```

?銝???SPEC/VERIFY 撠嚗???engine ????

### BUILD Layer Decision

BUILD 撅方?鋆??臬極?瑁身摰?銝 SPEC?遣霅啣???run/tool profile嚗?

```json
{
  "render_profile": "no_effects | light_effects | motion_graphics | debug",
  "fallback_visual_provider": "pexels | pixabay | antigravity | assistant_imagegen | gemini_veo",
  "fallback_visual_mode": "stock_video | generated_image | generated_video | text_bridge",
  "effects_enabled": false,
  "motion_graphics_backend": "ffmpeg_libass | html_playwright | remotion | blender",
  "model_routes": "model_routes.json",
  "quality_baseline": "connectivity | no_effects_quality | final_review"
}
```

??嚗?

```text
SPEC 瘙箏??臭??臭誑 fallback?鈭挾銝?蹂誨?挾?賡?閬?暻澆??賬?
BUILD profile 瘙箏?撖阡??典??provider / renderer / model / effects backend??
```

撌脰?堆?

```text
build_profile.py
  default/load/validate/write build_profile.json嚗omfyUI 銝? active provider??

generated_assets.py
  敺?segment_contract ??generated_asset_requests.json嚗?賢? generated-capable provider嚗?
  stock provider(Pexels/Pixabay)?策 stock-first嚗?瘛瑞??

contract_adapter.py run
  瘥活 canonical run 撖?build_profile.json?enerated_asset_requests.json嚗?
  銝行??artifact_manifest.json??
```

### BUILD Runner Strengthening

BUILD 鋆撥銝???暺?冽撘?SPEC嚗??tool selection ??runner
execution ??璆?蝥撌亙??嚗?

```text
docs/build-tool-runner-spec.md
```

?賢極璅∪?嚗?

```text
Policy artifacts
  build_profile.json
  model_routes.json

Request artifacts
  generated_asset_requests.json
  motion_graphics_render_plan.json
  assembly_plan.json
  timeline_build.json

Runners
  stock runner
  generated asset runner
  motion graphics runner
  mv_chain render runner
  verify/editor-review runner
```

?桀????

```text
wired:
  contract_adapter.run_contract
  stock runner via Pexels/Pixabay
  local material ingest/match
  mv_chain render runner
  editor_review runner
  dashboard/story-map reader

request/plan only:
  generated asset runner
  motion graphics runner

next priority:
  P1 artifact_manifest completeness: implemented
  P2 generated_asset_manifest/manual provider adapter: implemented
  P3 light effects runner: implemented as ffmpeg-safe operation planner
  P4 motion graphics backend runner
  P5 dashboard build control surface
```

撽??嚗?

```text
瘥?BUILD runner ?賢??? input artifact?utput artifact?anifest entry??
dashboard node status?ocused unit test???賢??prompt ??剔?摰?
```

### Antigravity Feedback

鈭箏極??嚗?

```text
蝝?寞??(no_effects)
fallback ????Antigravity ?Ｙ?
頛詨 final / final_etf
?釭?＊?芣蝝?stock-first
```

蝯?嚗??鞈芰?訾?銝摰?芾摩蝯???SPEC 銝雲嚗 fallback 蝝??釭?ntigravity
????BUILD provider嚗?銝?撖恍?segment_contract ?蝖砌?鞈氬?

?拍嚗?

```text
symbolic cutaway
chapter/card background
conceptual process illustration
stock 銝末?賭葉?鞊??典/撠平?湔
no_effects baseline ???釭 fallback image
```

蝳迫嚗?

```text
??鈭箇
?祕?游霅?
銝颱遙?渲?
摮詨?砌犖
憭批???
must_include / proof_critical / identity_sensitive 畾菔
```

### Testing Baselines

皜祈岫??撅歹?銝?瘥活?質???敶梁?嚗?

```text
1. Contract/artifact unit tests
   敹恍蝬脰楝?憭批?敶梁??? canonical -> payload -> manifest -> artifacts??

2. Stock-first connectivity E2E
   ??Pexels/Pixabay??蝭暺???rovider?anifest?inal.mp4 ?臬?Ｗ??
   銝靘??恍?釭??

3. No-effects quality baseline
   ??Antigravity fallback image + no_effects render??
   final / final_etf 雿鈭箏極 review baseline??

4. True-material regression E2E
   ??66 ???????芸??蝣??? must_include???喋?撟?憟eview route??
```

敶梁?頛詨銝?? repo root?epo ??engine/source嚗?撖?project ??run output
?身?曉 repo 憭?

```text
<project-root>/<project>/
  input/materials/
  runs/<timestamp>-<case>/
    spec/
    build/
    verify/
    materials/
      raw/
      selected/
      generated/
      stock/
    nodes/
    thumbs/
    logs/
    brownfield/
```

?菜葫??:

```text
run root = ?臭? output truth source
spec = 甇?? SPEC layer ?Ｙ雿蔭;??雿蔭,銝??神甇?node schema
build = BUILD layer ?Ｙ雿蔭;蝑?build contract 蝣箄?敺?蝝啣?
verify = VERIFY layer ?Ｙ雿蔭
materials/raw = ?蝝?
materials/selected = 撌脫????芾摩?舐?交?鞎餌???
materials/generated = generated fallback 頛詨
nodes = node 撠惇銝剝? artifact;node 蝺刻?/?迂蝑?contract 蝣箄?敺?撱?
brownfield = 撠郊敹怨? SPEC/DO/VERIFY 靽格迤蝝??
```

repo ?批靽? `.project/active.json` 雿 repo-relative local pointer嚗?

```bash
python3 video_tools.py project-init "ETF Demo"
python3 video_tools.py project-new-run --label baseline
```

Git ?芯?????artifacts嚗?

```text
artifact_manifest.json
state.json
editor_review.json
contact_sheet.jpg
```

### Active Roadmap

```text
P0: 靽? canonical SPEC 蝛拙?嚗??之撟? schema??
P1: BUILD layer run/tool profile ??? build_profile.json 撌脰?啜?
P2: Antigravity / assistant_imagegen fallback image 蝝 generated_asset provider?? generated_asset_requests.json 撌脰?堆?撖阡?憭 provider runner 敺??
P3: no_effects quality baseline ?箏???final/final_etf)??
P4: narrative architect / narrative spine嚗hesis?絲?輯??ig_story?ode_plan?erify check??
P5: dashboard 憿舐內 manifest + baseline outputs + provider decisions??
P6: light effects only嚗ade / xfade / Ken Burns / lower third / subtitle style??
P7: motion graphics backend嚗tml_playwright ??Remotion??
P8: narration+MV mixed engine嚗ts story segments + beat MV segments in one contract run??
```

### Agent Rules

```text
銝??神 SPEC 銝駁???
銝???Antigravity / assistant_imagegen / ComfyUI 撖急? segment_contract 蝖砌?鞈氬?
銝?霈?generated image ??????
銝???heavy effects ??MVP ?蔭璇辣??
瘥活?箇??賢神 artifact_manifest ??provider decisions??
ComfyUI ?身 disabled/deprecated嚗?蝙?刻?蝣箄?瘙祕撽?銝??詨???provider??
?芸?靽?BUILD profile / dashboard / verify嚗??臬?? workflow??
```

---

## Historical Notes Below

隞乩?靽???roadmap ?風?脰?蝯∟?撌脣??敦蝭?????Current Canonical State 銵?嚗?
隞乩??寧皞?

## 銝?亥店?
> 銝憟銴ˊ?蝘餅???**Video Route Skill Project**:??`script.json` ?膩敶梁??eterministic pipeline ?Ｙ + `state.json` ?嗅銝??route.py` 瘣曉極銝?甇乓ashboard ?犖璈?review?omfyUI ?芯??芯?憭 `generated` 蝝? provider,銝脫敹?
> 2026-06-05 ?湔:ComfyUI 撌脤???deprecated/disabled嚗enerated 撖血??芸? Antigravity / assistant_imagegen / Codex ??

---

## ?扔??蝯曹?畾菔璅∪?(Unified Segment Model)

> **銝?挾?賜??閮?????蝢?銝?敶梁?憿?(蝯? MV / ?嗥???/ ???/ ?亥????芣??畾菔璅∪??撓?粹??+ ??頠訾?皞?銝?蝯???* 銝憟頂蝯勗?憭車????蝬剛風憭? pipeline??

?頂蝯梢?批?閮准??賡?????頠詨? TTS)??**銝餌??閮???MV??**;??舀靘雿???貉?迤閫?銝車????銝畾菔璅∪? + ?舀??撓????頠詻?

**畾菔 = 蝯?????+ ?舫頛詨?駁? + ??頠訾?皞?*

????靽?(??????鞎餉?銝??芾冪??閮?D5:?????VLM ? 56.4,`visual_desc` ??撖?68.2):

| 甈? | 瘨祥??| MV ?冽? |
|---|---|---|
| `visual_desc` | VLM ?貊???+ 撠??? | **銝?SPEC**(?貊?????) |
| `search_query`/`material_hint` | ?曄???| ?砍蝝?憭?靘??內 |
| `text`(?) | ?單(TTS) | 蝛?蝝?MV;??璈挾??TTS |
| `caption`/`title`(摮?) | ?Ｗ? | 璅???鈭箏?/甇? |
| `must_include`(敹) | VERIFY 摰? | **?**:????孵?鈭箏???|

?拙撓??toggle(敺?銝?):摮?/璅?=蝝”?曉惜**銝蔣?踵??遘**(??);??脤(TTS)=**敶梢??頠?*+憭?璇頠??爸????

??頠訾?皞??舀?????MV ????:`tts`(??瑕漲?ctual_dur)/ `beat`(librosa?ut_grid,蝯? MV)/ `fixed`(?∠?/?撠????頛詨?勗?隞??畾菜???????銝虜 render/concat/QA/state/dashboard ~70% ?梁,?芸???遘靘? + ?豢挾璅∪?????

**?賢敺齒**(霈芋????):????頠訾?皞???(?桀? `actual_dur` 鞎怎忽?券,??refactor)??`text` 霈??蝛箏?頝?TTS)??摮?靘?閫?????質楝敺?璅?/鈭箏?/甇?)??MV script schema(??撌脰??閬?)??MV 隤?撠? >> 蝺典???
> ?? ???質情 ?????撠?撖血???**?亦?質情?芷?撱嗅??臭?蝖祈???詨末?挾+撠?)**??

---

## ?拙惜璅∪??極(??嗆???)
> **憭扳芋?恣?斗/SPEC/route;ollama 蝞∪之????璈１撅斤恣蝝???*

| 撅?| 隤?| ??暻?|
|---|---|---|
| **Agent(憭扳芋??** | Hermes/Codex/Claude | **璅∠?瘨**(vague??撠?prompt??瑽? SPEC)???瞍?YML/憸冽??*ROUTE 瘣曉極**?? caption 瘙箏?蝝?甇賊?/?黎/敹???/?斗?暑 |
| **Tool(?砍 VLM)** | ollama qwen3-vl | ?? caption??閰??噶摰????撌?**銝?甇賊?瘙箇?** |
| **璈１** | ffmpeg/librosa/scenedetect | ?賢?/??/?/皜脫?,?嗅??|

- **璅∠?瘨(???)** = Agent 撅?`?瘙???)??video-workflow 撘?撱箸瑽???撠??箏? YML/憸冽`?????暻潦???瑁? SPEC??
- **蝝?隤?甇賊? = ?拙惜??**:ollama ??蝑隞暻潦? 憭扳芋?? caption ?扎獐?黎/?芯?敹/???獐?乓llama ?芯?鈭祕,?斗?典之璅∪???

**SPEC 銝???*:`video-workflow`(??/?行,??銝虜,頛詨 brief ??)??`director`(鋆賭? SPEC:?挾/敹/?單?/?貊???MV 銝餃?)??`writer`(MV=?Ｗ???撅?璅惜/??摮/瞍?摮?;???具?摰?)??
> ?? 璅∠?瘨撅?video-workflow(??30 銵?敺?蝝???皜?,**銝蝺典???**??

**撱箇蔭??:璈１ vs ?斗**(瘙箏??芾ㄐ?憚摮?銝?典?畾?敺挾??:
- **璈１=?啗???lib**(銝???repo):beat=librosa(ISC)?hot=PySceneDetect(BSD)?ender=ffmpeg??
- **?斗=?芸楛??*(霅瑕?瘝?:隤???/?舐?扼?芸嗾畾萸?*敹摰?**??憿?撖衣撩????SPEC??
- **??霈?銝?蝣?**:CutClaw??閫??caption?????豢挾?祟?乓?摨??踹??utClaw ?⊥?甈??芸飛???撌梢?撖怒ontage-ai(noncommercial)/OpenMontage(AGPL)???芾?銝??

---

## MV-cut ?暹?(??蝡臬蝡臬頝??

`mv_cut.py` ??MV 撘????蝬?93 皜?:
- **??beat?ut_grid** ??`beats_to_cut_grid`/`grid_durations`/`detect_beats`(librosa lazy)??
- **???瑞???** ??`detect_shots`(PySceneDetect,????⊿ fallback)+ **`fixed_windows`(raw 蝝????蝒?隤?**??*撖行葫:?祕摮詨蝝??舫???琿??ContentDetector 撠?raw ?⊥? ????fixed_windows??*
- **???蝒??畾?* ??`select_windows`(**敹摰?:敹?? min_score**?撩??unfilled?ERIFY 蝻箏)+ `score_windows`(??midpoint 撟?content_qa.score_segment` VLM)??
- **??renderer** ??`plan_mv`(?貊??eat ?局)+ `render_mv`/`render_mv_audio`(?賣挾??920x1080?′???芷璅???
- **run_mv**(?撽??券?) ??stock(Pexels resilient?AP)/ clip_list(??match-mv)/ live 銝??胯?*????*:per-畾?visual_desc 蝯衣??(?剔??亙虜 vs??瘜其?隤脯???10 鋡思????蝥?100/60),閫??????100?min_score=60`(敹 override)??
- **?亦?** ??`run_mv(clip_list=)` ??match-mv 撌脤? clip 銝?live ??;`mv_chain(script,material_db,out,music)` ?桐??亙銝?match?ender??
- **??撅?* ??`label`(摨?蝐?+ `name_super`(撌虫?鈭箏?)+ **ASR 瞍?摮?**(faster-whisper,`subtitle:"auto"`?????喇???CJK)?祕撟/SRT 撽?(??摮?蝺?璆准??撜餅 ?葦?? ASR?摰? ?梯??平?具???
- **?唾?** ??v0:?挾 `audio_role`(music/duck/diegetic),v0 ?箏?雿????sidechain)??
- **schema** ??`validate_mv_script` + `python3 mv_cut.py validate <script>`??雿?visual_desc/material_hint/kind/layout/pace/must_include/high_weight/needs_review/hold/keep_audio/audio_role/name_super/text + ?惜 style/music??靘?`examples/graduation_mv_*.json`??
- **dashboard 璈** ??`build_mv_state` 撖?dashboard ?詨捆 state.json(segments+SPEC+status+blocking+next_action,mode="mv")??

**curator/蝝??啣** ??`cmd_ingest_meta`(+`classify_asset` 璈１:璈怎/閫??摨??/usable)+ `caption-meta`(?砍 VLM 憛怠祕?摰?+ `material-map`(鈭箏霈?啣?)+ `match-mv`(?瘙?蝯?CJK bigram 瘥??lip_list+蝻箏,銝? VLM)??*??霅?VLM ???瑞?憛怠?憿aption ??霅啣恕?/?寡???瘥????閰?)??garbage-in 閫????*

### 潃?撠蝯?gold standard(?舫?皜祉璅?
鈭箏極?芸末??`~/.hermes/profiles/video_director/vault/66???-擃?蝯?敶梁??汰K.mp4`:**13.4 ????68 shot?葉雿?1.47s??7.5 cuts/??*;<1s?113/1-3s?197/3-6s?41/>6s?17?? 敹怠 montage(憭)+ 敹??hold(17 畾?>6s)銝血??皞?`every_n_beats` ?身憭芣,隤?`?? + min_seg??.6` 撠? 1.5s??*閰摯瘜?*:mv-cut ?箇? ??瘥?66 ???瑕漲/蝭憟?敹?曉?瘝???

---

## ? 敺?撘瑟???靘?Codex review 蝣箄????)

> Codex ?⊥????**??蝛拍?????啣,銝蕭?芾摩?望?)?﹐V 韏啜犖?舀?阮??0-80 ??鈭箄??/?嗅偏/敹/鈭箏???90,??芸?摰? ?┴oute 敺??賜?????MV chain(state ?膩 gap/missing photo/must_include unfilled/opening-ending review)?τode-timeline dashboard ?舫??萇??撌乩?????憌??七utClaw ?芰 recipe??* 霅瑕?瘝?銝剜?瘣餃?敶梁????曉??????犖鋆?oute state??

1. **蝝??啣?蝛拙(?啣,?擃??** ????026-06-04?????冽? `C:\Users\user\Downloads\敺桅敶梁???ingest-meta`(302 瑼?88 敶梁?+214 ?抒?,264 keyframe,104 HEIC 頧?)??`caption-meta`(qwen3-vl:4b,**302/302 caption?? error**)??`material-map`(301 銵犖?航??啣?)??*garbage-in 閫???祕霅?*:VLM 甇?Ⅱ霈???蝺??萄?擃征蝬凋耨/???餌?/??瘣餃?/銝颱遙瞍?),?霈?箸帖撟?????蝺????圈??銵?犖??*??agent ?斗甇?**:憭扳芋?? caption 瘙箏??黎 ??stage ?葉??*????鈭箇? material_map.md 撖怠?撖血???????match??* ?b/map ??`_fullpool/`(gitignored)??
2. **node-timeline dashboard(??Ｗ?=撌乩???** ????026-06-03??`build_mv_state` 瘥挾??(visual_desc/layout/audio_role/must_include/name_super/label/subtitle + BUILD:picked_clips/n_slots + ??頠?start/dur + ?惜 total_dur,plan slots ?函?)+ `dashboard.html` `renderTimeline()`:瘥?暺??? + 瘥??璇?+ SPEC?UILD?ERIFY 銝惜(SPEC layout/audio_role/????鈭箏?/璅惜/摮??UILD ?訾??芣 clip?slot ??GAP+fix?ERIFY status/score/敹??,銵冽???箇?蝝啁??eadless render 撽? + self-contained ?Ｙ??函摰嫘?4 皜祉???*??鈭箄?鈭?)**:dashboard 銝??貊?暺?撖恍畾?鋆??湔撠?鋆????桀??航??,鈭箄?隞粥 `--only-seg`/route)??*蝝??蝮桀?**:state 撠撣?thumb 頝臬???
3. **video-workflow 鈭?撘芋蝟???*:?瘙???)??撘? prompt ???Ｗ撠? MV YML ??璇??SPEC ?銝虜)??
4. **bookend ?抒??? + pacing** ???抒? ??026-06-03??`find_photos`+`_is_image`+`_photo_vf`(kenburns 蝺拇/hold);run_mv ??photo(media=photo / opening|closing|title / ?∪蔣??????still slots);match-mv ??抒? ??1 撘?1 still;render `-loop 1`+kenburns+?(??`-t` ??filter 敺??祕 ffmpeg smoke ?蝎暹???*??*:pacing 隤踹(montage 敹?1.5s vs hold ????
5. **audio-director sidechain** ????026-06-03??`_mv_music_mix` ?誨?箏?雿???畾?duck/diegetic)??`sidechaincompress` 霈璅?渲?/????雿???montage ?單??嗡蜓?唾??usic_vol 0.35??.7?祕 smoke ?拙??臬??*??*:?撣?skill ???? audio_role+?+?? ?毽?唾??怒??暹撘?撅方????
6. **verify ?唾??剝?蝬剖漲** ????026-06-03??`audio_qa` ??subtitle:auto ?餅?靽??(摮?瘝皞??單???)?iegetic 瘝???撖恍?state.qa.audio_pairing + dashboard 蝬剖漲憿舐內??
7. **route?V ?游?** ????026-06-03??`route.py --mv`(--material-db+--music)撽? mv_chain;state ?膩 MV 蝻箏(must_include unfilled 暺?敹?ookend 蝻箏璅????review_points` opening/closing/title 擃???needs_review);`_route_mv` surface 鈭箏極銴暺?鈭箏餈游??仿?)??*??*:?蝺?route 瘨祥 `revise:director`?egacy top-text fallback ?寡?撖?route??
8. **瘥?66 ??gold standard ?嗅?鞈?*(??蝣?????026-06-04??`mv_chain` ???冽? captioned db + ?璅???`graduation_66_auto.mp4`(99.9s/1920x1080/26 cut,state pass=True/audio_pairing=100)??*match 皞?*(???餌? 0.929??獢?0.7?蜓隞餃???0.625?蝝撣?0.5?征??0.583?之? 0.5)?shot_stats` vs 66 ??**銝凋? cut 1.5s vs 1.47s(ratio 1.02,??cut 蝭憟?銝?**,雿?**cuts/min 10.8 vs 27.5(ratio 0.39=憭芣)**?? ? hold(蝛箸?/銝颱遙?/摮/憭批??????湧?;蝯?:montage 畾菟??游? or holds 蝮桃(`weight`/??航矽????撌脣???耨鈭?concat ?詨?頝臬????韌 bug??*??餈凋誨)**:montage-heavy ????潸? 27 cuts/min??
9. **graphify ?遣**(?嗅偏)????026-06-04??scoped ?遣(59 瑼?source-only,? _fullpool/蝝?/artifact)??**484 蝭暺?732 ??52 蝷曄黎,99% EXTRACTED**(?? 270 蝭暺??od nodes:ToolError(40)/run()/pipeline()/run_tool()/**run_mv()(15)**/compose_and_qa()?冗蝢斗項? MV-cut(MV-cut Engine?un_mv?uild_mv_state?core_windows?ender_mv_audio?ilter_static_windows + PhotoHandling/AudioQa/StaticPrefilter/ShotStats/MusicMix 皜祈岫蝢???霅?蝷箏???`pipeline()`/`run()`/`ToolError` 隞頝函冗蝢?god nodes?ipeline Core cohesion 雿?0.05)???嗆? Project Kit 隞?瑞??孵??utputs ?湔??`graphify-out/`?ST(code)撅?doc 隤?撅斗迨頛芰??之??subagent fan-out??

**撠**:??`narrative` ?典?摮?? window ?迫蝒?蝭?freezedetect)?? music-fetch `ytsearchN`?? ASR ?之璅∪?(`MV_ASR_MODEL` ?航矽)?? pacing weights(hold ?臬?甈???詨???

---

## Pipeline 撖阡?瘚?(?蝺?`video_pipeline.py`?pipeline()`)

```
[1]TTS?2]SRT?3]mix-audio
        ???????餈游?憭頝?甈?
?? ?岫餈游?(P2-3,?身??max_retries=2)????????????????
??[4]gather+pick ??P1-1 prepick VLM gate + fallback ??   ??
??[5]render segments ??render_one(?岫?芷?皜脰??挾)        ??
??[5b]precompose gate ??P1-2 閬/?撽?                  ??
??[6]xfade concat?8]merge-final?9]thumbnails             ??
??[10]verify(?銵?5 蝬??11]content_qa(0.30)            ??
?? ??銝?: collect_fix_actions 靘?fix_target 頝舐          ??
?????????????????????????????????????????????????????????????
        ??decision_log.json(P1-3 ?憚頠楚)
```
?Ｙ:`final.mp4`繚`qa_report.json`繚`content_qa.json`繚`decision_log.json`繚`precompose_gate.json`繚`edit_log.json`繚`picks.json`

## 閫 Skill 憟?(`skills/`)
| Skill | 閫 | I/O |
|---|---|---|
| video-workflow | ??/?行(SPEC ?銝虜) | ?瘙???brief(敺?蝝???皜? |
| director | 撠?(MV 銝餃? SPEC) | ?批捆 ??鋆賭?閮剛?(style/media_pref/layout/bgm/敹/MV schema) |
| writer | 蝺典?(MV=?Ｗ???撅? | 銝駁? ??script ?批捆甈? + MV ??撅?label/narrative/subtitle) |
| curator | 撠楊 | script ??ingest/caption/material-map/match-mv ??clip_list |
| editor | ?芾摩撣?| assemble + merge-final(瑼?撅斤?) |
| audio-director | ?單撣?| edge-tts + BGM mix(敺?蝝毽?唾??? |
| subtitle-director | 摮?撣?| tts_timing ??subtitles.srt |
| verify | VERIFY | 5 蝬?QA ??qa_report + fix_target |
| route | 瘣曉極 | 霈 state.next_action ??摰?/await_material/retry/review |
| effects-director | ?寞?撣?| grade/title/transition/montage policy |
| generative-director | ??蝝?憟? | 憭 provider:`source=generated` |
| gap-analyzer | 蝻箏?? | script ??material_needs.json |
| dashboard | ?? | ??workdir ??HTML ???|

?梁敺垢:`video_tools.py`(tts/srt/mix-audio/merge-final/verify/kenburns/pexels-*/music-fetch/caption-meta/material-map/match-mv/dashboard)??

---

## 撌脣???獢澈(?蝺?憯葬)
- **P1-1/P1-2/P1-3** ??5-29??prepick VLM gate(?典瘙?fallback ??)?recompose gate(閬/? 簣0.3s)?ecision_log 蝯曹??憚頠楚??
- **P2-1/P2-3** ??5-29??Pexels+Pixabay ??;self-reflection retry(靘?fix_target 頝舐?? survivor+8b 銴?璅?unfixable?ax_retries=2)??
- **content_qa ?游? + D1~D5** ??5-29??content_alignment 瘜典 qa;?格挾 content gate(隞颱?畾?60 fail);銝剜?蝝?蝑(search_query 銝剜??摮?+ `visual_desc` 雿?VLM 璅? + `cultural_specificity`);rubric(somewhat??5);摮?蝢飛?un5:8 畾萄?憿? 畾菔?撖?unfixable+鋆???? HTTPError??
- **effects-director** ??5-30??grade/title-card/12 頧(?賢??桅暺?);content_qa ?賢摨???閫?grade?esc ?);15 畾萄?芸? score 93??
- **title-sequence + style ?輻? + ?挾瘛琿◢??* ??5-30??????撠?+ `kind:title`;style(narrative/mv/promo)?挾閬神?ravel 銝駁? score 95.5/align 85(?擃???
- **BGM ??摨?+ collage** ??5-31??`gen-bgm`(7 ??憓?)+ script `bgm` 甈?`collage`(蝢文?畾???
- **5 ?? story+MV ?瑞?** ??6-01??25 畾?final 333.6s/QA 100/align 70/5 畾菔?撖?unfixable???video stock ?瑞?蝻箏(撌脖耨,閬?)??
- **BUILD ?舀敺拙? + fix_class 銝?憿?* ??6-02??`RecoverableBuildError`(material/spec/human),4 ?′ raise ?孵?Ｗ儔(蝻箸??lock?銝雲??蝝?recompose ?渡??ate_review),render loop ??per-seg 憭望??laceholder ?批虜?箇?;`build_state` 瘥挾璅?fix_class + `revise:director` next_action??
- **music-fetch** ??6-02??`music-fetch <q> --source yt`(yt-dlp ?賡閮?mp3,撖西? lofi 68.2s);Pixabay ??music API ????script `bgm` dict?????ix-audio --duck??
- **Longform Duration Policy** ??6-02??`_seg_target_len`(?桐??)+ `_filter_video_candidates`+ `_video_fill_plan`;???寧 TTS `actual_dur+xfade`,憭芰??`-stream_loop` 鋆遛銝? hard fail??
- **蝺冽?撅?route?tate.json?kill** ??5-31????`build_state()` ?凋遢 artifact ?嗆??桐??(stages+segments+blocking+next_action)??`--only-seg N` ?挾?葡(?園?皜脫窒????`route.py`+`skills/route.md` 瘣曉極撅???state?uild/null???await_material?皜?`seg{n}_user.*` 頧?local ?葡/retry/review)?飛?∠???祕霅?qa 92??7?lign 74??0??
- **Dashboard ?亙** ??6-02??`dashboard.html` 霈 route state schema(banner/stages/QA/segments/blocking/final,auto-refresh 5s);`dashboard <outdir>` ??self-contained `dashboard_view.html`(閫?file:// 銝 fetch)??

### ??Deferred(撌脩蝻粹?)
- **D2-C ?游末銝剜?蝝?皞?*:Pexels 撠??????拇?摮??⊥?擗??⊥?蝎???銝剜?蝝?摨急???撘????
- **?單??脤?**:蝝璅挾璅∪?(`kind:music` 頝?TTS)?amendo client_id(?祇??潔?)?挾/靘?style ?芸??豢??
- **?寞??脤?**:?豢?+蝎???ffects ?湔??????拚(? Remotion/AE 蝝?蝑?project kit 蝛???
- **?拍?銝?**:stock 摨急????啁撠?撖阡? ??unfixable+鋆?(D2-C/??撘?;stock ???啜摰蝢支犖??祈釭憭抵?????飛?∠????

---

## ?Ｗ?摰?(2026-05-31)
**銝璇揹撖艾??撖艾?游??頂蝯?*,甇????葉???賢蔣????1 ?=1 clip 撟餌??芋??頧???*蝯? MV ?芸??芾摩??*??beat-driven ?豢挾+撠?+敹+??撅?鈭箄??亙?)??皞?????摮詨?芣?(蝝撖虫蜓擃?~80%,?閰脰??)??stock(Pexels 瘜?敹?????撘?Antigravity / assistant_imagegen / Codex ?? ceiling,???箇摰犖,?芰 B-roll)????Route Skill Project ?????dashboard review ???????撟喳?⊿?蝘餉?(Project Kit 敺?????provider ?勗銝 agent ?函??瑁?,?砍?獢摰儔 `source=generated` 隞嚗omfyUI 撌脤???deprecated/disabled??
## 2026-06-12 E6 Agent-As-Visual-Judge V1 Complete

E6 is verified:

- V1 stock candidates produce timestamped montage evidence in agent mode.
- One `visual_review_request.json` pauses the run at `await_visual_review`.
- A validated `visual_review_verdict.json` resumes deterministic window cutting/rendering.
- Dashboard/runtime route the single review gate.
- `ollama` and `none` remain supported build-profile modes.
- Focused E6 regression: 164 tests passed; full suite: 596 tests passed.

Next roadmap item: E7 material montage understanding. E8 narrative prepick and Node 12
agent-judge expansion remain deferred until E7 is stable.

### 2026-06-12 E7 Material Montage Understanding In Progress

First contract slice complete:

- `build_material_review_request` creates per-asset visual evidence without invoking a model.
- Videos use timestamped montage evidence; photos use their display image.
- `apply_material_review_verdict` writes agent-authored `vlm_caption` plus explicit lineage.

Next E7 step: connect this request/verdict contract to `caption-meta` await/resume CLI behavior.

E7 status (2026-06-12): COMPLETE. `caption-meta --visual-review-dir` now writes
a timestamped material montage request and returns
`await_material_visual_review`; rerunning after an agent-authored verdict
applies complete captions with explicit lineage. Partial verdicts are rejected,
UTF-8 BOM verdicts are accepted, root-level ingest files are no longer skipped,
and an empty pending set completes without a false wait. Real city-lite long
material await/resume and montage sensory review are verified. See
`docs/archive/decisions/2026-06-12-e7-material-montage-review.md`. Next: integrated
fresh-film sensory acceptance, then E8.

### 2026-06-16 NPE1 Native Preview Engine (Remotion-like, no Remotion) ??COMPLETE

A Hermes-native interactive preview middle-layer. Borrows the Remotion preview
model (fps / currentTime / durationFrames / composition props / per-clip media
timing) but adds **zero** Remotion dependency ??no install, no runtime, no
reference-repo edits, and `final.mp4` is never the primary preview.

- New contract `preview_timeline.json` ??single input to the native frontend,
  built (never authored) by `tools/preview_timeline.py` from `timeline.json` /
  `draft_timeline.json` + `project_material_map.json` + `review_subtitles.srt`.
  Deterministic `timeline_start_sec`; video `source_start_sec`/`source_duration_sec`;
  browser-safe `/media?src=` URLs; missing sources ??diagnostics.
- New contract `timeline_patch.json` ??only write path for interactive edits
  (`set_duration` / `set_source_window` / `move_clip`), validated and applied by
  `tools/timeline_patch.py` into `patched_draft_timeline.json`. `timeline.json`
  is never overwritten.
- New frontend `dashboard/workbench_native/` with a pure, node-testable core
  (`workbench_core.js`): play/pause via rAF, image?ideo?mage switching by
  `currentTime`, source-start seek, subtitle overlay, inspector edits, patch out.
- New write-limited `tools/workbench_server.py` (separate from the read-only
  Review Dashboard) ??may write only the three workbench artifacts; canonical
  artifacts are hard-blocked.
- Tests: `tests/test_preview_timeline.py` + `tests/test_timeline_patch.py`
  (21 focused) and `tests/workbench_core_smoke.js` (9 node checks).
- ffmpeg BUILD stays canonical; a patch is an editorial proposal, not a render.
  See `docs/archive/decisions/2026-06-16-native-preview-engine.md`.

Deferred: Remotion Player adoption, full NLE, precise audio mix, transitions,
canvas compositing, real export, Node-registry 14 effects, and promoting
`patched_draft_timeline.json` back into the canonical BUILD chain.

### 2026-06-16 NPE2 Workbench export + save-time spec alignment ??COMPLETE

Two follow-ups on NPE1, both keeping ffmpeg canonical:

- **Save-time FALLBACK spec alignment** ??`apply_patch` now runs
  `align_plan_to_contract` over the whole plan, reconciling edited values back
  onto the canonical timeline field spec and clamping anything that drifted off
  the material window (source window > material duration, image start ??0,
  non-positive durations). Corrections are reported in
  `patched_draft_timeline._spec_alignment` and surfaced in the UI. The saved
  artifact is contract-conformant even when the base carried drift.
- **Opt-in export** (`tools/workbench_export.py` + `POST /api/workbench/export`
  + "Export (ffmpeg)" button) ??hands the patched, aligned plan to the canonical
  `mv_cut.render_mv` (the same ffmpeg path BUILD uses), writing
  `workbench_export.mp4`. Canonical outputs (`final.mp4`, ?? are hard-blocked.
  This is the "second set you can use to actually output" ??not a browser
  renderer.

Tests: `tests/test_workbench_export.py` (5) + alignment cases in
`tests/test_timeline_patch.py`. Clipchamp-style timeline drag/split and
canvas/WebGL compositing remain deferred (see decision doc).

### 2026-06-17 NPE3 Workbench Patch ??Pipeline Contract draft sync ??COMPLETE

(The increment requested as "NPE2 Patch ??Pipeline Contract Sync"; labelled NPE3
here because the NPE2 slot was already used by the export + spec-alignment work.)

Translates a workbench `timeline_patch` into a **draft** that the pipeline can
read, without ever touching canonical artifacts. This is **not** an editor, not
Remotion, not Node14/effects, not an Audio Graph, not a final render.

- New `tools/workbench_patch_to_contract.py` ??`sync` produces
  `workbench_contract_patch.json` (a draft describing desired contract changes,
  never applied) + `patched_draft_timeline.json`. Sync rules:
  - `set_duration` ??per-segment `segment_duration_suggestion` (draft only).
  - `set_source_window` ??`material_window_override` (draft), validated to stay
    inside `project_material_map` scene bounds.
  - `move_clip` ??stays in the timeline draft; intra-segment reorder is info,
    cross-segment is diagnosed `unsupported_for_contract_sync` (segment order is
    never silently rewritten). `slot_index` identity is preserved across moves.
- Fail-closed: unknown slot, non-finite/non-positive duration, or a source
  window beyond scene bounds aborts with no artifact written. Canonical files
  (`timeline.json`, `segment_contract.json`, `revised_segment_contract.json`,
  `project_material_map.json`, `material_needs.json`, `final.mp4`, ?? are
  hard-blocked from writes.
- Server: `POST /api/workbench/sync-contract` writes only the two draft
  artifacts; a fail-closed sync writes nothing.
- Lightweight preview render reuses the existing `workbench_export.py` (canonical
  ffmpeg) to emit `preview_render.mp4` from a patched draft ??never `final.mp4`.

Tests: `tests/test_workbench_contract_sync.py` (A?) + sync cases in
`tests/test_workbench_server.py`. Official delivery still runs through the
Agent / ffmpeg pipeline consuming the draft/patch, then build.

### 2026-06-17 NPE4 Lightweight Editorial Runtime Tracks ??COMPLETE

The Workbench grows from single-video-timeline tuning into a **lightweight
editorial runtime**: it previews and edits four track layers and writes each as
an Agent-readable draft patch. It is **not** a final renderer, **not** Remotion,
does **not** guarantee pixel-perfect preview, and never writes canonical
artifacts. Official output remains the Agent / FFmpeg / Node14 pipeline.

- **Layer 1 Subtitle** (`subtitle_patch.py`): edit text / start / duration over the
  parsed SRT; `subtitle_patch.json`; SRT never rewritten; overlap = warning.
- **Layer 2 Audio cue** (`audio_cue_patch.py`): add/move/delete cue markers
  (enum cue_type, time ??duration+1s, strength 1??, anchor slot checked);
  `audio_cue_patch.json`. Marker layer, not a mixer.
- **Layer 3 Effect intent** (`effect_patch.py`): add effect presets (enum) on a
  clip with intensity 1??; window must fit the target clip (fail-closed);
  `effect_patch.json`. **Intent only ??Node14 consumption deferred, no effect
  rendered.**
- **Layer 4 Unified save / handoff** (`workbench_handoff.py`): `save-all` writes
  all provided track patches atomically (any invalid ??nothing written) and emits
  `workbench_handoff.json` indexing artifacts + per-layer edit counts +
  `next_action: agent_review_and_render_preview`.
- Server: `POST /api/workbench/{subtitle-patch,audio-cue-patch,effect-patch,save-all}`,
  all write-limited; canonical (incl. `review_subtitles.srt`) hard-blocked.
- Frontend: clickable subtitle track, cue/effect marker tracks, track inspector,
  "Save all + handoff". Effect preview is a CSS/marker hint, not real ffmpeg.

Tests: `tests/test_workbench_tracks.py` (A?, O), `test_workbench_server` (M/N/P/Q
+ subtitle endpoint), JS smoke +4. Full regression green. Verified live on
`.tmp/srp_real67_fuller_replay`. Deferred: Node14 effect consumption, real audio
mixing, replace_clip / material swap, drag-drop NLE.

### 2026-06-17 NPE5 Workbench preview perf pass + filmstrip thumbnails ??COMPLETE

A smoothness/usability pass (Tier A + Tier B from the perf consult). Not a real
NLE: no frame cache / GPU compositing / WebCodecs, no Remotion, no new npm dep.

- **Tier A perf**: the `/media` allow-list is now cached per root (it was
  rebuilding the whole `preview_timeline` on every byte-range request ??the main
  server stall during playback/scrub); `/media` streams in 256 KiB chunks
  instead of reading the whole file into memory; the frontend only seeks the
  `<video>` on a clip change (and corrects only on >0.5s drift) instead of every
  animation frame.
- **Tier B filmstrip**: `workbench_thumbs.py` extracts one 320px JPEG per video
  clip with the existing ffmpeg (cached under `<root>/workbench_thumbs/`, a
  derived cache, never canonical); `GET /api/workbench/thumbnails` returns the
  manifest; clip blocks render the thumbnail as a background so the timeline is
  readable without playing. Image clips reuse their own src.

Residual boundary stutter when switching `.MOV` clips is inherent to a single
`<video>` + browser decode and only Tier C (frame cache / WebCodecs) removes it ??intentionally deferred (and .MOV/HEVC may not decode in WebCodecs anyway).

Tests: `tests/test_workbench_thumbs.py` (4) + server thumbnails/allow-list-cache
cases; JS smoke unchanged. Full regression green. Verified live on
`.tmp/srp_real67_fuller_replay`: filmstrip on all 43 clips, thumbnails served via
/media, canonical untouched.

### 2026-06-17 NPE6 Workbench preview proxy cache ??COMPLETE

Adds a derived preview-proxy cache for smoother monitor playback without turning
the workbench into a full render engine. `workbench_proxy.py` trims each video
clip window into a browser-friendly low-bitrate MP4 under
`<root>/workbench_proxy/` (cached by source + mtime + clip window). The workbench
loads `GET /api/workbench/proxies` asynchronously; once a proxy exists, monitor
playback uses that proxy URL with `source_start_sec=0`, while the original
`source_path` / material-map timing stays intact for patch and contract sync.

This is **not** Tier C: no WebCodecs, no frame cache, no Remotion, no new npm
dependency, and no canonical artifact writes. Missing/failed proxies gracefully
fall back to the original media. `/media` allows only canonical preview sources,
`workbench_thumbs/`, and `workbench_proxy/`.

Tests: `tests/test_workbench_proxy.py` (4), server proxy endpoint/cache access
cases, and JS smoke for proxy playback timing. Full regression green.
### 2026-06-17 EF1 Effect asset material-map compatibility ??COMPLETE

Effect-related assets can now be represented in the project material map without
being mistaken for ordinary story footage. `effect_overlay`, `motion_asset`, and
`sfx` are accepted as library asset types, but map-ranked video/photo retrieval
excludes them from the main picture timeline. `effect_patch.json` may reference
an `asset_id`, and validation requires that referenced id to be an effect asset
(`effect_overlay` or `motion_asset`) from `project_material_map`; regular
video/photo ids fail closed.

Boundary: this is contract groundwork only. Workbench may preview effect intent,
but official final rendering of those effect assets remains deferred to a future
renderer/Node14 increment.

### 2026-06-17 EF2 Workbench effect asset selection ??COMPLETE

`preview_timeline` now projects material-map effect assets into
`effect_assets[]`, and the Workbench exposes them as an optional selector when
adding an effect intent. `effect_patch` save payloads preserve `asset_id`, so an
Agent or future renderer can distinguish pure preset intent from an effect
overlay/motion asset reference.

Boundary: still draft-only. No canonical artifact is rewritten and no final
render path consumes these assets yet.
# 2026-06-17 Update ??EF3 Workbench Effect Export Renderer

EF3 is implemented as a bounded, opt-in workbench export path. `tools/workbench_export.py --effects`
and `/api/workbench/export` with `effects:true` now consume validated `effect_patch.json` and render
simple ffmpeg-safe overlays (`flash`, `title_reveal`, `caption_emphasis`) onto `workbench_export.mp4`.
Unsupported effect intents stay in the patch and are reported as skipped; they are not silently claimed.
Canonical `final.mp4`, delivery gates, material maps, Node 14, and Dashboard remain untouched.

Validation: focused `tests.test_workbench_export` + server export flag test + JS smoke passed. Full
regression is required before marking this bounded increment committed.
# 2026-06-17 Update ??EF4 Workbench Material Browser

EF4 initial support is implemented as a read-only material browser in the native
Workbench. `preview_timeline.json` now projects main visual assets from
`project_material_map.json` into `material_assets` (video/photo/image only;
effect/sfx assets excluded). The Workbench displays a left-side material panel
with asset cards, family/search filtering, and selection diagnostics. This does
not yet implement drag-to-replace, material-map editing, or canonical contract
write-back; it is the stable visual inventory surface for those later steps.
# 2026-06-17 Update ??EF5 Dashboard Workbench Entrypoint

Dashboard integration is implemented as an explicit entrypoint, not a merge of
the two apps. `/api/artifacts` now exposes `workbench` metadata with the
recommended `tools/workbench_server.py` command and default
`http://localhost:8770/workbench` URL. `dashboard_v1.html/js` adds a Workbench
button that opens that external write-limited workbench. The Review Dashboard
remains read-only; Workbench retains its own write-limited patch/export server.

### 2026-06-18 OPF1 Operator Flow Acceptance Package ??COMPLETE

`operator-flow-acceptance` now supports a deterministic complete demo package
for backend Node0??3 smoke acceptance:

```powershell
python video_tools.py operator-flow-acceptance .tmp/operator_flow_full_acceptance `
  --init-demo-package `
  --require-build-ready `
  --out .tmp/operator_flow_full_acceptance/operator_flow_acceptance.json `
  --rerender-out operator_flow_rerender.mp4 `
  --rerender-report-out operator_flow_rerender_report.json
```

The generated package includes a Node0 brief, `material_needs.json`,
per-asset material map, `materials_db.json`, `project_material_map.json`,
`segment_contract.json`, `music.wav`, Workbench timeline/draft artifacts, and
handoff. Acceptance requires `material_lifecycle.stage == build_ready`, validates
the Workbench handoff, and renders a non-canonical ffmpeg draft candidate. It
never writes canonical `final.mp4`.

Verified result: `stage=passed`, `can_build=true`, handoff `ok=true`,
non-canonical rerender `ok=true`, rendered clips `2`, ffprobe output
`2.0s` H.264 video + AAC audio, and canonical `final.mp4` absent.
