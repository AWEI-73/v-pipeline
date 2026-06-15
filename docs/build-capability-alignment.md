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
- **The material-evidence layer has been upgraded with VD2 active/complete.** Only `visual_family`, `angle_scale`, and `asset_type` are currently consumed by `plan_ranked_windows`
  to order and select diversified candidates during build, without acting as a delivery blocker. Other VD0 labels like `action_family` and `subject` are stored but not yet used.
  Correctness/evidence score tiering remains prioritized.
- **Photo map-ranked renderability is active/complete.** Photo assets (where `asset_type == "photo"`) are renderable in map-ranked window planning, using the segment's allocated `clip_dur` as their design duration (independent of the source video window bounds).
- **SRP1 Segment Sequence Recipe Planner is active/complete.** Local segments with at least 2 approved map-ranked slots and no manual beat recipe are automatically planned into a sequence (e.g. context -> payoff) preserving window integrity, and rendering a true sequential movie.
- **SRP2 Opening / Hook Auto Planner is active/complete.** When a build has no manual `script["opening_recipe"]`, a shallow deterministic opening (hook -> context_montage -> title_reveal -> story_entry, scaled to the qualified-candidate count) is planned from the already-approved story-plan slots and prepended via the existing BR1 compiler. It is a re-use of approved shots only. Candidates are deduplicated by `scene_id` (same source + different window stays distinct). Selection is correctness-first and greedy by retrieval_score tier — a lower-score shot never outranks a higher one — with same-tier soft role preferences actually applied: hook prefers close>medium>wide, context prefers an unused `visual_family` then wide>medium>close, title base prefers an unused scene_id / different family (video-over-photo and deterministic scene_id as final tie-breaks; missing family/scale degrades deterministically). Only approved scene_id-bearing slots are eligible (GAP / source_speech / keep_audio / hold / fallback-only / illegal-window excluded); title text comes only from explicit script fields; evidence/window/photo lineage is preserved; the original story plan is left intact (opening prepended, slot_index reindexed); and VD2/SRP1 shared history is not polluted. When the build declares `target_sec`, the auto opening is duration-budgeted against the whole-film target (drop extra context -> title -> shorten hook -> fallback) so it never pushes the plan past `target_sec`; approved story slots are never trimmed and manual openings are exempt. A manual opening recipe always wins. It is NOT story understanding or aesthetic direction.
- **Quality proxies (M5a/M5b) are VERIFY-only by design** (tier-2 warn). Correct
  per the gate policy; they must not be counted as BUILD capabilities.
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
