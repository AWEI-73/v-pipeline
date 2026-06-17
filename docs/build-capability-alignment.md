# BA1 — BUILD Alignment Audit

Date: 2026-06-14
Type: bounded documentation audit (no new feature, no new quality audit, no
renderer rewrite). Grounded in call-site grep, not memory.

**Question:** which declared dictionaries / Skills / tools actually change BUILD
output today, vs. which are stored-but-unconsumed? This tells us where new BUILD
work has leverage and prevents claiming "active" without a real consumer.

Status values: `active` (real BUILD/render consumer + evidence) · `partial`
(consumed only on some paths or planning-only) · `declared_only` (stored, no
BUILD consumer yet) · `missing` · `deprecated`.

## How to read this

Three layers, kept separate on purpose — a planning gate is NOT a BUILD
capability, and a VERIFY check creates nothing:

- **A. Pre-BUILD gates** — run before BUILD; they accept/shorten/block the SPEC.
  They change the *input* to BUILD, never emit timeline/render themselves.

> Node-registry node "14" is a **flow-grouping / scaffold label**, not a BUILD
> consumer. The actual motion-graphics BUILD consumer is the `contract_adapter`
> build path calling `motion_graphics`. Do not cite Node 14 as the consumer.

- **B. BUILD capabilities** — consumed during BUILD; they change the actual
  timeline and/or rendered output.
- **C. VERIFY audits** — inspect the result; they create no edit and choose no
  replacement.

### A. Pre-BUILD gates (planning layer — not BUILD capabilities)

| Gate | Declared source | Tool | Where it runs | Effect on BUILD | Status |
|---|---|---|---|---|---|
| `B5 out_of_capability` | `capability_manifest` (M0) | `capability_manifest.build_capability_manifest` via `spec_review` | `spec_review` pre-BUILD | blocks SPEC requesting unsupported capability | active (gate) |
| `B6 script_overreach` | `supply_review` (M1) | `review_supply` via `spec_review` | `spec_review` pre-BUILD | forces shorten/merge before BUILD | active (gate) |
| Supply review | M1 `supply_review` | `review_supply` | pre-BUILD | shortened contract is BUILD input | active (gate) |

> [!NOTE]
> **VD1.1 Vocabulary Contract Principles:**
> 1. **Project-local contract**: The vocabulary is a project-local contract that different Agents use to align their visual-family definitions before reviewing.
> 2. **Not Core Engine Words**: The vocabulary does NOT represent generic built-in genre vocabulary in the core video pipeline engine.
> 3. **Deterministic Mapping**: Normalization is a deterministic mapping (canonical family and aliases) and is NOT semantic or fuzzy understanding.
> 4. **Evidence Prep / VD2 Prerequisite (Not a BUILD/Delivery Blocker)**: This contract is for evidence preparation and consistency validation. It does **not** block general build or delivery. VD2 soft-ranking remains blocked by default until the frozen-vocabulary independent consistency re-review is performed and passes.


### B. BUILD capabilities (change timeline / render)

| Capability | Declared source | Existing tool | BUILD consumer | Timeline evidence | Render evidence | Status |
|---|---|---|---|---|---|---|
| Transitions | `ALLOWED_TRANSITIONS` (video_pipeline) | `build_filter_chain` | narrative `compose_and_qa`, `mv_cut` | xfade offsets in filter chain | rendered xfades | active |
| Still treatments (push/pan/ken-burns) | `_STILL_TREATMENT_MODES` (edit_artifacts) | `mv_cut` zoompan | `mv_cut` render (`_video_vf`/still path) | `still_treatment` on clips | rendered motion on stills | active |
| Attention budget | `attention_budget` facet | `resolve_attention_budget` | `edit_artifacts` plan + `mv_cut.allocate_segments` | per-seg budget + shot count | shot durations follow budget | active |
| SFX punctuation | `sfx.ASSET_COUNTS` + `sfx_plan` | `sfx-mix` | `video_pipeline` audio mix | `sfx_plan.json` cues | cues in final_audio | active |
| Music structure / climax align | `music_structure` sections | `music_alignment` | `video_pipeline` bgm offset | `music_alignment_plan.json` | bgm offset in render | active |
| J/L cut + speech-tail + motion snap | edit_artifacts / vt_audio | `snap_render_plan_to_motion`, jl/tail | `video_pipeline`, `mv_cut` | adjusted extract starts | rendered seams | active |
| Window retrieval (map-based) | M2 `material_retrieval` | `plan_ranked_windows`, `plan_sound_bite` | `mv_cut._plan_local_segment` — **default** local path whenever a valid material map exists (MR1; no longer gated on clip_list picks), honest matched/live fallback | ranked slots w/ scene_id+window evidence + `retrieval_path` trace | rendered map-ranked windows (`test_map_retrieval_wiring` G) | active |
| motion_graphics: ffmpeg_libass | `build_profile.motion_graphics_backend` | `motion_graphics.py` | **contract_adapter build path → motion_graphics render/composite** (when render_profile ∈ light_effects/motion_graphics) | `motion_graphics_render_plan.json` | rendered overlays | active |
| motion_graphics: html_playwright | build_profile | `motion_graphics.py` | contract_adapter build path (one recipe) | render plan | rendered frames | partial |
| motion_graphics: remotion | build_profile enum | — | none | — | — | declared_only |
| CapCut finishing | capcut_backend | draft manifest | Node 13 sub-state | draft JSON | GUI export (human gate) | partial |
| Material needs + satisfies edge | M6a `material_needs` | `validate-needs` | none (contract/lineage only) | — | — | declared_only |
| Project material map | MM1 `project_material_map` | `project-material-map` | none yet (read model for agents/UI) | — | — | declared_only |
| VD0 shallow labels (`visual_family`/`angle_scale`/`action_family`/`subject`) | VD0 contract | `visual-diversity-review` Agent verdict application | `material_retrieval` select_diverse_ranked_scenes | stored on scenes with review lineage | — | active (only visual_family, angle_scale, asset_type consumed) |
| VD1 label coverage evidence | project material map | `visual-diversity-coverage` | none (evidence gate before VD2) | `visual_diversity_coverage.json` | — | active (evidence only) |
| VD1.1 family vocabulary | `visual_family_vocabulary` | `visual-family-normalize` | none (does not block build/delivery) | normalized review with lineage | — | active (evidence prep / VD2 prerequisite) |
| VD2 visual diversity soft selection | VD0 contract + project map | `plan_ranked_windows` select_diverse_ranked_scenes | `mv_cut._plan_local_segment` | prioritized diversity selection | rendered diversified slots | active |
| SRP1 Segment Sequence Recipe Planner | approved slots | `plan_segment_sequence` | `mv_cut` run_mv loop | auto-planned beats and trace keys on slots | rendered auto-sequence | active |
| SRP2 Opening / Hook Auto Planner | approved story-plan slots | `plan_opening_recipe` | `mv_cut` run_mv (post story-plan; reuses BR1 `compile_opening_sequence`) | auto opening clips prepended + `opening_recipe_source=auto` trace/lineage | rendered auto opening before story | active |
| SRP3 Story Arc / Emotional Progression Planner | script segment order + manual metadata | `plan_story_arc` / `apply_story_arc_hints` | `mv_cut` run_mv (BEFORE `allocate_segments`) | arc_role/intensity/pace/weight hints shift relative allocation; `arc_role`/`story_arc_source=auto` trace on story slots & per_seg | climax story duration > setup (true render) | active |

### C. VERIFY audits (inspect only — not BUILD capabilities)

| Audit | Declared source | Tool | Tier | Effect | Status |
|---|---|---|---|---|---|
| Black/blank frame | M0d | `black-frame-audit` | tier-1 | fail-closed blocks delivery on defect | active |
| Semantic novelty (dHash) | M5a | `semantic-novelty-audit` | tier-2 | warns; never blocks | active (warn) |
| Action progression | M5b | `action-progression-audit` | tier-2 | warns; never blocks | active (warn) |

## Findings

- **The render-time grammar is genuinely active** (transitions, treatments,
  attention budget, SFX, music align, micro-rhythm). The Sensory phase landed in
  BUILD, not just VERIFY.
- **The material-evidence layer has been upgraded with VD2 active/complete plus
  need-aware correctness.** `plan_ranked_windows` now consumes explicit
  `segment.need_ref` / `material_fit.need_ref` / `material_fit.need_refs[]`
  versus canonical `scene.satisfies[].need_id` (accepted/candidate only) as
  deterministic correctness evidence before text/function/pace fallback. Legacy
  `scene.need_id` / material-map `need_id` remain fallback only. This is the
  practical boundary:
  agents may author/review labels, but BUILD should not rely on prompt-time
  semantic guessing when a join key is available. `visual_family`, `angle_scale`,
  and `asset_type` are still used for same-tier visual diversity and photo/video
  handling, without acting as a delivery blocker. Other VD0 labels like
  `action_family` and `subject` are stored but not yet used.
- **Photo map-ranked renderability is active/complete.** Photo assets (where `asset_type == "photo"`) are renderable in map-ranked window planning, using the segment's allocated `clip_dur` as their design duration (independent of the source video window bounds).
- **SRP1 Segment Sequence Recipe Planner is active/complete.** Local segments with at least 2 approved map-ranked slots and no manual beat recipe are automatically planned into a sequence (e.g. context -> payoff) preserving window integrity, and rendering a true sequential movie.
- **SRP2 Opening / Hook Auto Planner is active/complete.** When a build has no manual `script["opening_recipe"]`, a shallow deterministic opening (hook -> context_montage -> title_reveal -> story_entry, scaled to the qualified-candidate count) is planned from the already-approved story-plan slots and prepended via the existing BR1 compiler. It is a re-use of approved shots only. Candidates are deduplicated by `scene_id` (same source + different window stays distinct). Selection is correctness-first and greedy by retrieval_score tier — a lower-score shot never outranks a higher one — with same-tier soft role preferences actually applied: hook prefers close>medium>wide, context prefers an unused `visual_family` then wide>medium>close, title base prefers an unused scene_id / different family (video-over-photo and deterministic scene_id as final tie-breaks; missing family/scale degrades deterministically). Only approved scene_id-bearing slots are eligible (GAP / source_speech / keep_audio / hold / fallback-only / illegal-window excluded); title text comes only from explicit script fields; evidence/window/photo lineage is preserved; the original story plan is left intact (opening prepended, slot_index reindexed); and VD2/SRP1 shared history is not polluted. When the build declares `target_sec`, the auto opening is duration-budgeted against the whole-film target (drop extra context -> title -> shorten hook -> fallback) so it never pushes the plan past `target_sec`; approved story slots are never trimmed and manual openings are exempt. A manual opening recipe always wins. It is NOT story understanding or aesthetic direction.
- **Quality proxies (M5a/M5b) are VERIFY-only by design** (tier-2 warn). Correct
  per the gate policy; they must not be counted as BUILD capabilities.
- **SRP3 Story Arc Planner is active/complete (shallow, deterministic).** When a
  build has ≥3 eligible segments and is not disabled, `plan_story_arc` assigns
  arc roles from segment ORDER + manual metadata (NOT semantic understanding) and
  `apply_story_arc_hints` nudges per-segment intensity/pace/weight hints into the
  existing `allocate_segments` BEFORE allocation. It only re-weights — it does not
  re-pick material, touch the material map, change correctness ranking, or
  reorder/drop/​rewrite segments. Manual `arc_role`/`pace`/`weight`/`intensity`/
  `requested_duration_sec` always win. Hardened contract (2026-06-16): a manual
  `arc_role` segment derives NOTHING (no auto weight/pace/intensity/source, never
  relabeled auto); duration-protected segments (hold/hold_reason/source_speech/
  keep_audio/diegetic/duck) never get auto weight or pace even at progression/
  climax; manual intensity is never given a conflicting auto value; segment
  identity is fail-closed (missing/blank/None/non-unique → not_applicable, no
  segment_index fallback); and every auto-applied field is recorded in
  `story_arc_applied_fields`. Total story duration and `target_sec` are preserved
  (climax outweighs setup). It adds one backward-compatible result key
  (`story_arc_plan`) and arc trace on story slots/entries; opening/ending evidence
  is never arc-tagged.
- **Controlled SRP acceptance replay confirms the BUILD thickness is real and
  attributable.** `tools/srp_acceptance_replay.py` drives `run_mv` over one
  controlled Gemini photo set (7 needs + 3 distractors) twice — baseline (VD2/
  SRP1/SRP2/SRP3 off via minimal disable flags, map-ranked + photo renderability
  kept) and enhanced (all on) — plus four planning-only single-capability
  isolation runs for honest attribution. Real ffmpeg renders both `final.mp4`.
  On this material the enhanced timeline differs from baseline and each capability
  is independently attributable: VD2 changes per-chapter selection (consecutive
  same-family runs 7→0), SRP1 adds beat sequences in every chapter, SRP2 prepends
  an opening, and SRP3 makes the climax chapter longer than setup (3.6s vs 2.5s)
  while preserving total duration / `target_sec`. Every declared manifest image is
  fail-closed (a missing/empty/unreadable declared image blocks the run). The
  harness does NOT claim distractors are excluded — a distractor's subject terms
  can still overlap a segment query — so the report instead DISCLOSES distractor
  usage; on this set both cuts selected the duplicate-assembly and bad-group
  distractors (BUILD-time VD2 does not dedup/reject distractors; that is the
  VERIFY-side `semantic_novelty_audit`'s job). Render content is verified at the
  SLOT level: each acceptance `run_mv` uses an isolated `mat_dir` (fixing a shared-
  temp `mvseg_<slot_index>` collision that previously spliced foreign red/blue
  color clips into the concat), and the replay BLOCKS unless every plan slot's
  mid-frame is non-monochrome (solid card → per-channel spatial stdev ~0) AND
  correlates with that slot's own source photo (`slot_render_checks`) — preventing
  a "timeline ok but render faked (color card)" pass. The disable flags
  (`disable_visual_diversity` / `disable_auto_sequence` / `disable_auto_opening` /
  `story_arc:false`) are minimal, backward-compatible controls (default = existing
  behavior); they add no new editing capability.
- **67th real-footage SRP sanity replay confirms the SRP stack runs on true
  footage, but only on the M6e covered subset.** `tools/srp_real67_sanity.py`
  rebuilds the M6e real-footage fixture, then reuses
  `.tmp/m6e/out_C/generated_mv_script.json` and `project_material_map.json` to
  render baseline/enhanced cuts from real `.MOV` sources. Outputs land in
  `.tmp/srp_real67/`. Current evidence: baseline `final.mp4` 6.967s, enhanced
  `final.mp4` 10.5s, timelines differ, SRP2 auto opening planned (2 opening
  clips), SRP3 planned/applied, and slot render checks pass for all slots
  (3/3 baseline, 5/5 enhanced). Honest boundary: the covered subset has only
  three accepted scenes, so SRP1 has 0 eligible multi-slot segments and SRP3 does
  not demonstrate climax > setup on this material shape. This replay is a sanity
  check for runtime integration and render correctness, not a full 304-file
  ingest and not a quality/aesthetic verdict.
- **Gemini enhanced-only demo film confirms the node-shaped flow can be driven
  without hand-writing a timeline.** `tools/gemini_demo_film.py` starts from the
  controlled Gemini manifest, builds a shallow 7-need script and project material
  map, then runs the enhanced BUILD path (VD2 + SRP1 + SRP2 + SRP3) into a real
  render and review report. It is not a new planner and not a baseline comparison.
  Current evidence: requested 75.0s, rendered 75.6s, plan 75.0s; 36 synthetic
  assets across 7 needs; SRP2 opening planned; SRP1 auto sequences in all 7
  segments; SRP3 planned/applied; slot render checks pass for 25/25 slots.
  The script uses `pacing.preferred_shot_sec=[2.8,3.4]` as a script-level pacing
  parameter so the demo reaches 60-90s without changing SRP1's approved-window
  contract. The report explicitly discloses distractor usage, so curator/review
  can see material issues instead of accepting a silent success. After
  need-aware retrieval, the current replay uses **0** distractor slots and the
  review-only `semantic_alignment` section reports drift segments **[]**: every
  story slot selected for N01-N07 maps back to the segment's expected `need_ref`.
  This remains a BUILD selection improvement and review signal, not a hard
  delivery gate.
- **AR1 runtime planning extraction is internal structure, not a capability.**
  `run_mv` now delegates to private helpers (`_plan_story_timeline`,
  `_apply_opening_bookend`, `_apply_ending_bookend`, `_finalize_timeline`) with
  explicit inputs/returns and no module-global state. This is a zero-behavior /
  zero-schema / zero-API change refactor establishing the runtime planning
  boundaries needed before SRP3 — it adds no BUILD capability and is NOT a new
  Pipeline framework. Audio Graph V2, test tier-ing, and VERIFY→BUILD remain
  deferred.

## Smallest high-value BUILD gaps (ranked)

1. **BR1 Opening / Hook sequence builder** — highest viewer-perceived leverage;
   the student-case review's biggest miss was a flat opener. Consumes existing
   active grammar (transitions/treatments/attention budget) — no new evidence
   layer required, so it can ship before VD2.
2. **VD2 BUILD soft-ranking on `visual_family`** — complete (VD2a, 2026-06-15):
   turns the `visual_family`, `angle_scale`, and `asset_type` labels into actual shot ordering (correctness-first, diversity as bonus).
3. ~~**Promote M2 window retrieval from `partial` to `active`**~~ — DONE (MR1,
   2026-06-14): the map-based path is now the default local selection when a
   valid material map exists, with honest matched/live fallback.
4. **Photo map-ranked renderability** — complete (2026-06-15): supports rendering of photo assets in map-ranked window planning by mapping them to design duration instead of physical video time window bounds.
5. **SRP1 Segment Sequence Recipe Planner** — complete (2026-06-15): automatically plans sequence recipes for eligible segments using only the approved slots, changing both the timeline and true render.

These are scope notes for later rounds. BA1 itself adds no feature.

## NPE1 — Native Preview Engine (2026-06-16)

New **interactive preview middle-layer**, deliberately outside the BUILD A/B/C
layering above: it neither gates the SPEC, nor renders, nor audits the result.
It is a fourth, side-car layer — *editorial proposal* — that reads canonical
artifacts read-only and emits only a `timeline_patch.json` proposal.

- `preview_timeline.json` (`tools/preview_timeline.py`) — `declared_only` w.r.t.
  BUILD: it changes no timeline and no render; it is a browser-facing projection
  of existing artifacts for interactive preview.
- `timeline_patch.json` (`tools/timeline_patch.py`) — `declared_only` w.r.t.
  BUILD today. It is *not* yet a BUILD consumer: applying a patch produces
  `patched_draft_timeline.json` only. Re-entry into the canonical BUILD chain is
  intentionally deferred, so do **not** cite the workbench as a BUILD capability.
- `tools/workbench_server.py` — write-limited server, separate from the read-only
  Review Dashboard; canonical artifacts are write-blocked.

Canonical render remains ffmpeg. See
`docs/decisions/2026-06-16-native-preview-engine.md`.

## NPE3 — Workbench patch → pipeline contract draft sync (2026-06-17)

Side-car layer, same as NPE1/NPE2: it neither gates the SPEC, nor renders, nor
audits. It converts a workbench `timeline_patch` into a **draft** proposal.

- `workbench_contract_patch.json` (`tools/workbench_patch_to_contract.py`) —
  `declared_only` w.r.t. BUILD. It is a *proposal* describing desired contract
  changes (segment duration suggestion, material window override); it is **not**
  applied to `segment_contract.json` and changes no BUILD output by itself. The
  Agent / ffmpeg pipeline may later consume the draft and rebuild — that
  re-entry is intentionally out of scope here.
- `move_clip` never rewrites segment order; cross-segment moves are diagnosed
  `unsupported_for_contract_sync`. `slot_index` is a stable identity.
- Fail-closed on unknown slot / non-finite duration / source window beyond scene
  bounds. Canonical artifacts (incl. `segment_contract.json`) are write-blocked.
- `POST /api/workbench/sync-contract` writes only the two draft artifacts.

Do **not** cite the workbench as a BUILD capability: it produces drafts/patches
only. Canonical render remains ffmpeg. See
`docs/decisions/2026-06-16-native-preview-engine.md`.

## NPE4 — Lightweight editorial runtime tracks (2026-06-17)

Same side-car layer as NPE1–3: previews + edits, never renders, never writes
canonical. Adds three more **intent/marker** draft contracts, all `declared_only`
w.r.t. BUILD (they change no rendered output by themselves):

- `subtitle_patch.json` (`subtitle_patch.py`) — subtitle text/timing draft; the
  source SRT is never rewritten.
- `audio_cue_patch.json` (`audio_cue_patch.py`) — sound-effect cue markers; a
  marker layer, **not** a mixer / audio renderer.
- `effect_patch.json` (`effect_patch.py`) — effect-intent presets. **Intent only**;
  Node14 consumption is deferred and no effect is rendered. Do not cite it as a
  BUILD effect capability.
- `workbench_handoff.json` (`workbench_handoff.py`) — index + per-layer edit
  counts for the Agent; `save-all` writes track patches atomically.

Boundary unchanged: official delivery runs the Agent / FFmpeg / Node14 pipeline
on the drafts; the Workbench never produces canonical output and does not
guarantee pixel-perfect preview. See
`docs/decisions/2026-06-16-native-preview-engine.md`.

## NPE6 — Workbench preview proxy cache (2026-06-17)

Side-car preview performance only. `tools/workbench_proxy.py` creates derived,
trimmed MP4 proxies under `<root>/workbench_proxy/`; `/api/workbench/proxies`
returns a manifest and the frontend uses those proxies for monitor playback when
available. This reduces `.MOV` seek/load stalls for short clips. It does not
change selection, timeline contracts, material maps, delivery gates, or final
rendering. Failed/missing proxies fall back to original media.
## EF1 — Effect assets in the material map (2026-06-17)

Contract groundwork only. Project material maps may carry non-main-timeline
assets such as `asset_type: effect_overlay`, `motion_asset`, and `sfx` so the
same material inventory can describe visual footage, audio cues, and future
effect overlays. These assets are **library assets**, not ordinary story shots:

- `material_retrieval.rank_scenes` excludes `effect_overlay`, `motion_asset`,
  and `sfx` from map-ranked video/photo selection, so they cannot be accidentally
  chosen as main picture.
- `effect_patch.json` may reference an `asset_id`, but that id must point to an
  effect asset (`effect_overlay` or `motion_asset`) in `project_material_map`.
  Referencing a regular `video`/`photo` asset as an effect fails closed.
- This still does **not** render effects. Workbench shows intent/preview only;
  official effect consumption remains deferred to a future renderer/Node14
  integration.
