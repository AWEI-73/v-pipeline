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

### B. BUILD capabilities (change timeline / render)

| Capability | Declared source | Existing tool | BUILD consumer | Timeline evidence | Render evidence | Status |
|---|---|---|---|---|---|---|
| Transitions | `ALLOWED_TRANSITIONS` (video_pipeline) | `build_filter_chain` | narrative `compose_and_qa`, `mv_cut` | xfade offsets in filter chain | rendered xfades | active |
| Still treatments (push/pan/ken-burns) | `_STILL_TREATMENT_MODES` (edit_artifacts) | `mv_cut` zoompan | `mv_cut` render (`_video_vf`/still path) | `still_treatment` on clips | rendered motion on stills | active |
| Attention budget | `attention_budget` facet | `resolve_attention_budget` | `edit_artifacts` plan + `mv_cut.allocate_segments` | per-seg budget + shot count | shot durations follow budget | active |
| SFX punctuation | `sfx.ASSET_COUNTS` + `sfx_plan` | `sfx-mix` | `video_pipeline` audio mix | `sfx_plan.json` cues | cues in final_audio | active |
| Music structure / climax align | `music_structure` sections | `music_alignment` | `video_pipeline` bgm offset | `music_alignment_plan.json` | bgm offset in render | active |
| J/L cut + speech-tail + motion snap | edit_artifacts / vt_audio | `snap_render_plan_to_motion`, jl/tail | `video_pipeline`, `mv_cut` | adjusted extract starts | rendered seams | active |
| Window retrieval (map-based) | M2 `material_retrieval` | `plan_ranked_windows`, `plan_sound_bite` | `mv_cut` (called when material_maps present) | ranked slots / sound-bite | rendered windows | partial |
| motion_graphics: ffmpeg_libass | `build_profile.motion_graphics_backend` | `motion_graphics.py` | **contract_adapter build path → motion_graphics render/composite** (when render_profile ∈ light_effects/motion_graphics) | `motion_graphics_render_plan.json` | rendered overlays | active |
| motion_graphics: html_playwright | build_profile | `motion_graphics.py` | contract_adapter build path (one recipe) | render plan | rendered frames | partial |
| motion_graphics: remotion | build_profile enum | — | none | — | — | declared_only |
| CapCut finishing | capcut_backend | draft manifest | Node 13 sub-state | draft JSON | GUI export (human gate) | partial |
| Material needs + satisfies edge | M6a `material_needs` | `validate-needs` | none (contract/lineage only) | — | — | declared_only |
| Project material map | MM1 `project_material_map` | `project-material-map` | none yet (read model for agents/UI) | — | — | declared_only |
| VD0 shallow labels (`visual_family`/`angle_scale`/`action_family`/`subject`) | VD0 contract | scene review verdict | none (no BUILD ranking yet) | stored on scenes | — | declared_only |

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
