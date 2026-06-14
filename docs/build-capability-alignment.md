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

## Capability table

| Capability | Declared source | Existing tool | BUILD consumer | Timeline evidence | Render evidence | Status |
|---|---|---|---|---|---|---|
| Transitions | `ALLOWED_TRANSITIONS` (video_pipeline) | `build_filter_chain` | narrative `compose_and_qa`, `mv_cut` | xfade offsets in filter chain | rendered xfades | active |
| Still treatments (push/pan/ken-burns) | `_STILL_TREATMENT_MODES` (edit_artifacts) | `mv_cut` zoompan | `mv_cut` render (`_video_vf`/still path) | `still_treatment` on clips | rendered motion on stills | active |
| Attention budget | `attention_budget` facet | `resolve_attention_budget` | `edit_artifacts` plan + `mv_cut.allocate_segments` | per-seg budget + shot count | shot durations follow budget | active |
| SFX punctuation | `sfx.ASSET_COUNTS` + `sfx_plan` | `sfx-mix` | `video_pipeline` audio mix | `sfx_plan.json` cues | cues in final_audio | active |
| Music structure / climax align | `music_structure` sections | `music_alignment` | `video_pipeline` bgm offset | `music_alignment_plan.json` | bgm offset in render | active |
| J/L cut + speech-tail + motion snap | edit_artifacts / vt_audio | `snap_render_plan_to_motion`, jl/tail | `video_pipeline`, `mv_cut` | adjusted extract starts | rendered seams | active |
| Supply review / `B6 script_overreach` | M1 `supply_review` | `review_supply` | `spec_review` pre-BUILD gate | shortened contract → BUILD | shorter film | active (planning gate) |
| Capability manifest / `B5` | M0 `capability_manifest` | `validate-needs`/spec_review | `spec_review` gate | blocks out-of-capability SPEC | — | active (gate) |
| Window retrieval (map-based) | M2 `material_retrieval` | `plan_ranked_windows`, `plan_sound_bite` | `mv_cut` (called when material_maps present) | ranked slots / sound-bite | rendered windows | partial |
| Material needs + satisfies edge | M6a `material_needs` | `validate-needs` | none (contract/lineage only) | — | — | declared_only |
| Project material map | MM1 `project_material_map` | `project-material-map` | none yet (read model for agents/UI) | — | — | declared_only |
| VD0 shallow labels (`visual_family`/`angle_scale`/`action_family`/`subject`) | VD0 contract | scene review verdict | none (no BUILD ranking yet) | stored on scenes | — | declared_only |
| Semantic novelty (dHash) | M5a | `semantic-novelty-audit` | VERIFY tier-2 only (warn) | — | — | declared_only (BUILD); active (VERIFY warn) |
| Action progression | M5b | `action-progression-audit` | VERIFY tier-2 only (warn) | — | — | declared_only (BUILD); active (VERIFY warn) |
| Black/blank frame | M0d | `black-frame-audit` | VERIFY tier-1 gate | — | fail-closed on defect | active (VERIFY) |
| motion_graphics: ffmpeg_libass | build_profile | libass overlay | Node 14 effects render | render plan | rendered overlays | active |
| motion_graphics: html_playwright | build_profile | playwright capture | Node 14 (one recipe) | render plan | rendered frames | partial |
| motion_graphics: remotion | build_profile enum | — | none | — | — | declared_only |
| CapCut finishing | capcut_backend | draft manifest | Node 13 sub-state | draft JSON | GUI export (human gate) | partial |

## Findings

- **The render-time grammar is genuinely active** (transitions, treatments,
  attention budget, SFX, music align, micro-rhythm). The Sensory phase landed in
  BUILD, not just VERIFY.
- **The material-evidence layer is mostly `declared_only` for BUILD.** M6a needs,
  the satisfies edge, MM1 project map, and VD0 labels are stored and validated
  but **nothing in BUILD selects or orders shots from them yet**. Window
  retrieval (M2) is the one map consumer and is only `partial` (map-present path).
- **Quality proxies (M5a/M5b) are VERIFY-only by design** (tier-2 warn). Correct
  per the gate policy; they must not be counted as BUILD capabilities.

## Smallest high-value BUILD gaps (ranked)

1. **BR1 Opening / Hook sequence builder** — highest viewer-perceived leverage;
   the student-case review's biggest miss was a flat opener. Consumes existing
   active grammar (transitions/treatments/attention budget) — no new evidence
   layer required, so it can ship before VD2.
2. **VD2 BUILD soft-ranking on `visual_family`** — turns the `declared_only` VD0
   labels into actual shot ordering (correctness-first, diversity as bonus).
   Gated on VD1 label-coverage evidence (per roadmap).
3. **Promote M2 window retrieval from `partial` to `active`** — make the
   map-based path the default selection when a project material map exists.

These are scope notes for later rounds. BA1 itself adds no feature.
