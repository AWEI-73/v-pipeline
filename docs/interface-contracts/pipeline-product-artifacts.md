# Pipeline Product Artifacts

This document defines the product-facing artifact layer between fuzzy user
intent and low-level BUILD parameters.

The goal is not to create more templates. The goal is to make every branch
produce reviewable functional parameters that can be consumed by BUILD,
Workbench, Dashboard, and Verify.

Canonical dictionary:

```text
docs/interface-contracts/pipeline-product-artifact-dictionary.json
```

Audit command:

```powershell
python tools/product_artifact_dictionary_audit.py --json
```

Compile command:

```powershell
python tools/compile_edit_decision_plan.py --run RUN_DIR --json
```

## Why This Layer Exists

Stage 0 and branch routes decide where work should go. The API dictionary
defines how branches request, hand off, and repair work. Product artifacts
define what the user's requested video becomes before it reaches renderer
or ffmpeg-specific implementation.

```text
User semantics
  -> product artifact decisions
  -> branch handoffs
  -> BUILD/timeline/audio/effect/subtitle workers
  -> Verify evidence
```

## Core Product Artifacts

| Artifact | Owner | Purpose |
| --- | --- | --- |
| `source_media_review.json` | material-map | Summarize source footage, sections, visual quality, and original audio facts. |
| `material_matrix.json` | material-map | Map material needs to selected/rejected/candidate assets and coverage gaps. |
| `edit_decision_plan.json` | main-pipeline | Translate story and material facts into cuts, overlays, audio, effects, subtitles, and transitions. |
| `audio_decision_plan.json` | soundtrack-arranger | Define section-aware music, original audio policy, ducking, fades, and license/source choices. |
| `effect_decision_plan.json` | effect-factory | Convert effect intent into story function, visual family, motion grammar, asset usage, and negative rules. |
| `subtitle_voiceover_decision_plan.json` | subtitle-voiceover | Define subtitle, narration, provider, speech preservation, and readability policy. |
| `build_handoff.json` | main-pipeline | Collect accepted branch handoffs and deferred items before BUILD. |
| `final_review_bundle.json` | verify-delivery | Review final/preview output against the product artifact chain and route repairs. |

## Edit Decision Plan Shape

`edit_decision_plan.json` is the central product contract. It should carry
functional parameter groups inspired by proven editing APIs:

- `cuts`: source ref, in/out seconds, target duration, speed, layer, reason.
- `overlays`: text/image/graphic overlays, placement, timing, opacity, animation.
- `audio`: original audio policy, narration refs, music refs, ducking, fades.
- `effects`: effect refs, story function, visual family, intensity, source refs.
- `subtitles`: subtitle source, style, language, readability constraints.
- `transitions`: transition type, timing, duration, and emotional function.
- `review_focus`: checks for Workbench and Verify.

This is still a candidate product contract. It must not directly overwrite
`final.mp4` or bypass branch handoff gates.

## Compile Behavior

`tools/compile_edit_decision_plan.py` reads existing branch artifacts from a run
folder:

- `rough_cut_plan.json` or `preview_rough_cut_plan.json`
- `audio_director_handoff.json`
- `effect_handoff.json` or `remotion_effect_handoff.json`
- `subtitle_voiceover_build_handoff.json`

It writes:

- `edit_decision_plan.json`
- `audio_decision_plan.json`
- `effect_decision_plan.json`
- `subtitle_voiceover_decision_plan.json`
- `build_handoff.json`

Missing side branches are recorded as `build_handoff.deferred_items`; the tool
does not invent music, effects, subtitles, or voiceover, and it never renders
`final.mp4`.
