# Editing Intent / Sequence Grammar Spec

Updated: 2026-06-08

Status: draft for implementation

Purpose: prevent low-effort assembly such as one segment using one long stock
clip, static photos held too long, or unmotivated visual effects. This is not a
new render backend. It is a three-layer contract that lets SPEC, BUILD, and
VERIFY agree on why a shot exists, when to cut, and when not to cut.

## Core Principle

Do not optimize for maximum cuts. Optimize for meaningful visual change.

```text
Every cut should have a reason.
Every long hold should also have a reason.
```

A warm documentary can hold longer shots. A rhythmic MV needs more source
variety. A story sequence should not jump just to satisfy a cut count. The
pipeline must encode these differences so agents do not default to the cheapest
possible render.

## Layer Ownership

```text
Pre-SPEC layer:
  whole-video editorial design decisions before writing segment contracts:
  narration, subtitles, text layers, music structure, effects intensity, still
  image language, and audience attention strategy.

SPEC layer:
  editing intent, sequence grammar, pacing range, still-image policy,
  transition philosophy, and minimum visual requirements.

BUILD layer:
  shot slots, selected sources, usable windows, durations, transitions,
  still treatments, and optional effects.

VERIFY layer:
  visual fatigue, pacing fit, continuity fit, source repetition, still-photo
  misuse, transition/effect overuse, and sequence completeness.
```

## Node Changes

### Pre-SPEC: Editorial Design Intake

Review:
Before `brief.json` and `segment_contract.json`, the flow needs one whole-video
editorial design artifact. These decisions are not VERIFY findings. They are the
creative language of the film and must be settled before the segment contract is
written.

This is especially important for:

```text
narration vs subtitles
full subtitles vs key phrases
chapter music vs single BGM
restrained effects vs expressive effects
photo memory treatment vs photo fallback treatment
text placement / logo-safe layout
```

Build:
Add `editorial_design.json` as a Pre-SPEC artifact that feeds Node 0 and Node 3:

```json
{
  "artifact_role": "editorial_design",
  "version": 1,
  "video_mode": "training_recap",
  "editorial_intent": {
    "tone": "warm_reflective",
    "energy_curve": ["opening_calm", "training_active", "achievement_proud", "closing_emotional"],
    "attention_strategy": "story_progression_with_visual_variety",
    "continuity_priority": "high",
    "visual_variety_priority": "medium"
  },
  "narration_strategy": {
    "mode": "voiceover | interview_led | subtitles_only | text_cards | no_speech | mixed",
    "density": "light | medium | heavy",
    "purpose": ["context", "emotion", "explanation", "ceremony"],
    "speaker": "neutral_narrator | director | trainee | mixed"
  },
  "subtitle_strategy": {
    "mode": "full_subtitle | key_phrase_only | no_subtitle | mixed",
    "placement": "bottom_safe | lower_third | dynamic_by_scene",
    "density": "light | medium | full",
    "avoid": ["logo", "face", "hands_action", "training_equipment"],
    "style": "clean | documentary | energetic"
  },
  "text_layer_strategy": {
    "subtitle": "full | key_only | none",
    "chapter_titles": true,
    "name_supers": "director_only | speakers | teachers | none",
    "callouts": "training_terms_only | proof_points | none",
    "max_simultaneous_text_layers": 2
  },
  "music_strategy": {
    "mode": "single_theme | chapter_based | single_theme_with_reprise | mixed",
    "duck_under_speech": true,
    "chapter_music": [
      {
        "chapter": "morning_training",
        "mood": "energetic_light",
        "intensity": "medium"
      },
      {
        "chapter": "director_message",
        "mood": "warm_ambient",
        "intensity": "low",
        "duck_under_speech": true
      }
    ]
  },
  "effects_strategy": {
    "intensity": "none | restrained | moderate | expressive",
    "allowed_roles": ["chapter_transition", "title_card", "photo_motion", "emphasis"],
    "avoid": ["over_animation", "random_transition", "effect_every_cut"],
    "reason_required": true
  },
  "still_image_strategy": {
    "use_case": "memory | proof | fallback | montage",
    "treatment": ["slow_push", "pan", "crop_detail", "sequence", "collage"],
    "max_static_hold_sec": 5,
    "allow_long_hold_when": ["group_photo", "emotional_memory", "certificate_proof"]
  }
}
```

Verify:
- If the user request is ambiguous, the flow should ask targeted questions
  before writing the contract.
- If the artifact is absent, Node 0 may write a documented default, but the
  default must be explicit and visible.
- The artifact must not contain provider-specific choices such as Pexels result
  IDs, CapCut template IDs, Remotion components, or exact local file paths.

Implementation note:
This can be implemented as a Node 0 sub-step rather than a new permanent node:

```text
Node 0A editorial_design.json
Node 0B brief.json
Node 3  segment_contract.json
```

The artifact should still be indexed in `artifact_manifest.json` when present so
dashboard and `editorial_qa.json` can trace the decision lineage.

## SPEC To BUILD Compilation Contract

Every accepted SPEC field must have a BUILD consumer. A field without a consumer
is documentation only and must not be marked implemented.

The main execution-plan node is **Node 9 Assembly**:

```text
Node 8 converts intent into executable policy/defaults.
Node 9 decomposes policy + segment contract into an execution plan.
Node 10 binds the plan to concrete media windows and timeline operations.
Node 13 executes the concrete render backend.
```

Required mapping:

| Pre-SPEC / SPEC decision | BUILD consumer | Executable output | Typical runner/tool | VERIFY owner |
|---|---|---|---|---|
| `editorial_intent.mode` | Node 8 | `editing_policy` preset | policy resolver | Node 11/12 |
| `narration_strategy` | Node 9 | narration tasks / speech sections | TTS, supplied speech, audio runner | Node 12 |
| `subtitle_strategy` | Node 9/10 | subtitle tasks, placement/safe-area plan | SRT/text layer/CapCut text | Node 11/12 |
| `text_layer_strategy` | Node 9/10 | title/name-super/callout tasks | title-card, lower-third, CapCut text | Node 11/12 |
| `music_strategy` | Node 5/9/10 | music sections, ducking, transition points | music fetch/structure/audio mix | Node 12 |
| `effects_strategy` | Node 8/9/10 | allowed effects and reasoned effect tasks | ffmpeg-safe effects/CapCut | Node 11/12 |
| `still_image_strategy` | Node 9/10 | still treatment per photo shot | Ken Burns, collage, crop detail | Node 11 |
| `sequence_grammar` | Node 9 | required `shot_slots` | assembly planner | Node 11 |
| `pacing` | Node 9/10 | target shot durations/cut reasons | timeline compiler | Node 11/12 |
| `transition_philosophy` | Node 9/10 | transition plan with reasons | timeline/render runner | Node 11 |

Execution-readiness gate:

```text
For every active SPEC strategy:
  consumer node exists
  executable output field exists
  allowed runner/tool exists or a human/CU gate is explicit
  verify rule exists

Otherwise:
  ready_for_build = false
  next_action = revise:director | configure_build | human_gate
```

This gate prevents unsupported creative requirements from silently degrading
into the default renderer behavior.

Tool constraints belong in BUILD, not SPEC:

```text
SPEC:
  "photo needs restrained motion"

BUILD:
  choose slow_push via ffmpeg, CapCut, or another allowed backend

SPEC:
  "chapter change needs a clear visual bridge"

BUILD:
  choose title card, dissolve, direct cut, or human finishing based on profile
```

If no allowed tool can execute an intent, Node 9 must report the gap rather than
dropping the requirement.

### Node 0: Brief

Review:
The brief must identify the whole-video editorial style before segment writing.
Without this, agents apply generic MV rules to calm story content or generic
documentary pacing to energetic montage content.

Build:
Read `editorial_design.json` and summarize its whole-video choices into
`brief.json`. Add `editorial_intent` to `brief.json`:

```json
{
  "editorial_intent": {
    "mode": "warm_documentary | story_documentary | rhythmic_mv | training_recap | promo",
    "emotional_tone": "warm_reflective",
    "energy_curve": ["calm", "active", "proud", "emotional"],
    "attention_strategy": "story_progression | visual_variety | music_rhythm",
    "continuity_priority": "low | medium | high",
    "visual_variety_priority": "low | medium | high",
    "effects_intensity": "none | restrained | moderate | expressive"
  }
}
```

Verify:
- A brief without `editorial_intent.mode` should ask a clarification question or
  fall back to a documented default, not silently assume MV.
- Brief generation should preserve narration/subtitle/music/effects strategy at
  summary level so Node 3 can expand it into segment contracts.

### Node 3: Contract

Review:
`segment_contract.json` should describe visual obligations without binding the
segment to one provider, file, or render backend.

Build:
Add segment-level `editing_intent`, `sequence_grammar`, and `pacing`:

```json
{
  "segment": 1,
  "core": {
    "story_purpose": "establish the training journey and 0.66% theme"
  },
  "editing_intent": {
    "segment_role": "opening | development | skill_demo | certificate_demo | emotional_payoff | closing",
    "continuity_priority": "high",
    "visual_variety_priority": "medium",
    "effects_intensity": "restrained",
    "attention_strategy": "story_progression"
  },
  "sequence_grammar": {
    "required_functions": ["establish", "action", "detail", "result"],
    "optional_functions": ["reaction", "bridge"],
    "exit_function": "bridge_to_next_chapter"
  },
  "pacing": {
    "preferred_shot_sec": [4, 7],
    "max_meaningful_shot_sec": 12,
    "max_single_source_sec": 10,
    "max_still_hold_sec": 6,
    "allow_long_hold_when": ["emotion_developing", "action_incomplete", "story_payoff"],
    "require_visual_change_when": ["information_exhausted", "source_repeating", "energy_change", "new_story_beat"]
  },
  "still_image_policy": {
    "allowed": true,
    "preferred_treatments": ["slow_push", "pan", "crop_detail", "sequence", "collage"],
    "static_hold_allowed_when": ["emotional_photo", "proof_photo"],
    "max_static_hold_sec": 5
  },
  "transition_philosophy": {
    "style": "motivated | restrained | rhythmic",
    "allowed": ["direct_cut", "dissolve", "beat_cut", "graphic_bridge"],
    "reason_required": true
  }
}
```

Verify:
- Contract validation should check shape and allowed values.
- Contract validation should not require a specific tool such as CapCut,
  Remotion, or Pexels.

### Node 2: Material Coverage

Review:
Coverage must answer more than "is there any material?" It must answer whether
the segment has enough visual variety to satisfy the sequence grammar.

Build:
Extend `material_coverage_map.json` with beat/function coverage:

```json
{
  "segment": 1,
  "coverage": "ready | weak | missing",
  "function_coverage": {
    "establish": {"status": "ready", "candidate_count": 3, "video_count": 2, "photo_count": 1},
    "action": {"status": "ready", "candidate_count": 5, "video_count": 4, "photo_count": 1},
    "detail": {"status": "weak", "candidate_count": 1, "video_count": 0, "photo_count": 1},
    "result": {"status": "missing", "candidate_count": 0}
  },
  "variety": {
    "unique_sources": 6,
    "unique_visual_categories": 3,
    "stock_similarity_risk": "low | medium | high"
  },
  "next_action": "ready | await_material | request_generated_asset | revise:director"
}
```

Verify:
- A segment can be blocked even when it has one usable clip if the required
  functions cannot be covered.
- Stock/Pexels coverage should mark high similarity risk when all candidates are
  visually near-identical.

### Node 8: Build Profile

Review:
The build profile owns concrete policy thresholds. SPEC describes intent;
`build_profile.json` sets operational defaults.

Build:
Add `editing_policy`:

```json
{
  "editing_policy": {
    "default_mode": "warm_documentary",
    "min_shots_per_segment": 2,
    "min_shots_per_visual_function": 1,
    "target_shot_sec_by_mode": {
      "warm_documentary": [4, 8],
      "story_documentary": [3, 8],
      "rhythmic_mv": [1.5, 4],
      "training_recap": [2.5, 6]
    },
    "max_single_source_sec_by_mode": {
      "warm_documentary": 12,
      "story_documentary": 10,
      "rhythmic_mv": 6,
      "training_recap": 8
    },
    "max_still_hold_sec_by_mode": {
      "warm_documentary": 7,
      "story_documentary": 6,
      "rhythmic_mv": 3,
      "training_recap": 4
    },
    "source_reuse": {
      "max_reuse_per_run": 2,
      "reuse_cooldown_sec": 25
    },
    "transition_policy": "motivated_only",
    "still_image_motion_required": true
  }
}
```

Verify:
- Missing `editing_policy` should load defaults.
- Heavy effects must not be implied by this policy. This policy may request
  `slow_push` or `collage`, but not Remotion/Blender unless the build profile
  separately allows those backends.
- `build_profile.json` should convert editorial design into executable defaults
  such as subtitle placement, BGM ducking, chapter music behavior, still-image
  treatment defaults, and transition limits.

### Node 9: Assembly

Review:
Node 9 is where low-effort edits should be prevented. It must expand segments
into shot slots using the contract grammar and material coverage.

Node 9 is also the execution-plan bridge. If SPEC is rich but Node 9 does not
turn it into concrete work, BUILD will still fall back to one clip per segment.

Build:
Extend `assembly_plan.json`:

```json
{
  "segment": 1,
  "execution_plan": {
    "narration": {
      "mode": "voiceover",
      "source": "script_or_director_clip",
      "duck_music": true
    },
    "subtitles": {
      "mode": "full_subtitle",
      "placement": "bottom_safe",
      "avoid": ["logo", "hands_action"]
    },
    "music": {
      "section": "morning_training",
      "mood": "energetic_light",
      "intensity": "medium"
    },
    "effects": {
      "intensity": "restrained",
      "allowed_roles": ["photo_motion", "chapter_transition"]
    }
  },
  "shot_slots": [
    {
      "slot": "1.1",
      "function": "establish",
      "reason": "introduce location and journey theme",
      "preferred_media": ["video"],
      "fallback_media": ["photo_sequence"],
      "target_duration_sec": 5,
      "candidate_requirements": {
        "min_candidates": 2,
        "avoid_same_source_as_previous": true
      }
    },
    {
      "slot": "1.2",
      "function": "action",
      "reason": "show training in progress",
      "preferred_media": ["video"],
      "target_duration_sec": 4
    }
  ],
  "transition_plan": [
    {
      "from_slot": "1.1",
      "to_slot": "1.2",
      "type": "direct_cut",
      "reason": "same location, action begins"
    }
  ]
}
```

Verify:
- A segment with `required_functions` should produce matching shot slots.
- If coverage is weak, assembly should either plan fallback shots or route to
  `await_material` / `request_generated_asset` / `revise:director`.
- Every SPEC-level editorial strategy used by the segment should be converted
  into executable `execution_plan` fields. Missing execution fields should warn
  before render.

### Node 10: Timeline

Review:
Node 10 should turn shot slots into concrete clip windows. It should not merely
map one segment to one long source.

Build:
Extend `timeline_build.json` clips:

```json
{
  "segment": 1,
  "slot": "1.2",
  "function": "action",
  "source_path": "training_001.mp4",
  "source_in_sec": 4.2,
  "source_out_sec": 8.8,
  "duration_sec": 4.6,
  "timeline_in_sec": 5.0,
  "shot_reason": "complete training motion",
  "cut_reason": "action_completed",
  "still_treatment": null,
  "transition_in": {
    "type": "direct_cut",
    "reason": "same scene action continuity"
  }
}
```

For photos:

```json
{
  "media_type": "photo",
  "duration_sec": 4.5,
  "still_treatment": {
    "mode": "slow_push",
    "reason": "emotional_hold"
  }
}
```

Verify:
- Timeline should preserve `slot`, `function`, `shot_reason`, and treatment
  trace so Node 11 can review the edit.
- A long clip should be allowed only when `shot_reason` and content function
  justify it.
- Timeline should preserve `execution_plan` lineage for subtitles, music,
  narration, effects, and still treatment, so Verify can check that BUILD
  actually implemented the editorial design.

### Node 11: Editor Review

Review:
Node 11 should catch visual fatigue before final render or before accepting the
render. This is the main guard against one-source-per-segment videos.

Build:
Add or extend deterministic review with `visual_fatigue_audit.json` or include
equivalent findings in `editor_review.json`.

Checks:

```text
sequence completeness:
  required visual functions represented by shot slots/clips

single-source fatigue:
  source duration exceeds mode threshold without long-hold reason

still-image fatigue:
  photo exceeds hold threshold without treatment/reason

shot density fit:
  segment has too few shots for its mode and required functions

source repetition:
  same source reused too often or too soon

transition motivation:
  transition/effect lacks reason or conflicts with effects_intensity

pacing fit:
  shot durations fit the segment mode, unless exceptions are justified
```

Routing:

```text
material variety failure -> curator / await_material
shot structure failure   -> editor
still treatment failure  -> editor / effects-director
intent too vague         -> revise:director
effect overuse           -> effects-director
```

Verify:
- A one-source 20-second stock segment in `rhythmic_mv` mode should fail.
- A 10-second emotional hold in `warm_documentary` mode can pass when the hold
  reason is valid.
- A static photo held 12 seconds should fail unless explicitly justified and
  still within policy.

### Node 12: Verify

Review:
Technical verify alone cannot judge editing quality. Node 12 should incorporate
the visual fatigue/editorial-fit evidence as VERIFY artifacts, not as hidden
model opinion.

Node 12 also needs a final cross-artifact reviewer. This reviewer is the main
agent running the flow, preferably a stronger model. It should not dispatch a
subagent for this check, because the point is to review the whole chain with one
consistent editorial judgment.

Build:
Node 12 should surface:

```text
visual_fatigue_audit.json
pacing_fit score
continuity_fit score
source_repetition findings
still_fatigue findings
effect_overuse findings
editorial_qa.json
```

This can be mechanical first. Optional VLM review may be added later, but the
mechanical checks must work without Ollama.

Add `editorial_qa.json` as the final Node 12 reviewer artifact:

```json
{
  "artifact_role": "editorial_qa",
  "version": 1,
  "reviewer": {
    "type": "main_agent",
    "subagent_allowed": false,
    "model_role": "strong_editorial_reviewer"
  },
  "pass": true,
  "score": 86,
  "dimensions": {
    "intent_alignment": 88,
    "narrative_coherence": 84,
    "artifact_consistency": 92,
    "visual_variety_fit": 82,
    "pacing_fit": 86,
    "audio_visual_coherence": 90,
    "effects_fit": 85
  },
  "findings": [
    {
      "level": "warn",
      "dimension": "visual_variety_fit",
      "segment": 3,
      "message": "Segment 3 uses one visual source longer than intended for rhythmic_mv.",
      "evidence": ["segment_contract.json", "assembly_plan.json", "timeline_build.json"],
      "route": "editor"
    }
  ],
  "next_action": null
}
```

The main reviewer reads the full chain:

```text
brief.json
segment_contract.json
material_coverage_map.json
build_profile.json
music_structure.json
assembly_plan.json
timeline_build.json
editor_review.json
timeline_invariants.json
broll_audit.json
caption_audit.json
keyframe_grid.jpg / visual_audit.json
verify_result.json
final.mp4 or CapCut finalized output
```

The reviewer checks:

```text
artifact consistency:
  brief intent -> contract -> assembly -> timeline -> verify all line up

editorial consistency:
  whole-film tone, chapter order, energy curve, bridge logic, payoff

visual/pacing fit:
  edit density matches the selected mode; not too flat, not too frantic

audio/subtitle/effects coherence:
  music, captions, text overlays, effects, and CapCut manual changes do not fight
  the original intent

routeability:
  every blocking finding has a smallest target node/skill for Node 14
```

Rules:
- The main reviewer does not mutate artifacts.
- The main reviewer does not invent new SPEC requirements.
- The main reviewer may only report mismatches against existing intent,
  contracts, policies, and observed output.
- Findings must include `route` so Node 14 can create a small revision plan.
- Warn-only findings do not block completion unless the configured policy says
  they should.

Verify:
- `verify_result.json` or dashboard state must include blocking issues when
  visual fatigue audit fails.
- Warn-only findings should not block completion unless policy says so.
- `editorial_qa.json` should fail when artifacts are internally inconsistent
  even if technical verify passes.
- `editorial_qa.json` should pass a warm-documentary long hold when the hold is
  justified by the contract and pacing policy.

### Node 14: Revision

Review:
Revision must route to the smallest fix, not restart the whole workflow.

Build:
Generate `revision_plan.json` actions:

```json
{
  "actions": [
    {
      "target_node": 9,
      "target_skill": "editor",
      "reason": "segment 2 has one shot but requires establish/action/detail",
      "instruction": "expand segment 2 into at least 3 shot slots"
    },
    {
      "target_node": 2,
      "target_skill": "curator",
      "reason": "segment 3 lacks detail-function material",
      "instruction": "find or request detail material"
    }
  ]
}
```

Verify:
- Failing fatigue checks produce small targeted actions.
- Failing `editorial_qa.json` findings produce small targeted actions.
- Runtime rerun should clear only affected node/downstream artifacts.

## Example Mode Presets

### Warm Documentary

```json
{
  "mode": "warm_documentary",
  "preferred_shot_sec": [4, 8],
  "max_meaningful_shot_sec": 12,
  "max_still_hold_sec": 7,
  "effects_intensity": "restrained",
  "transition_style": "motivated",
  "attention_strategy": "story_progression"
}
```

Use when emotion, memory, or speech matters. Do not force rapid cuts.

### Rhythmic MV

```json
{
  "mode": "rhythmic_mv",
  "preferred_shot_sec": [1.5, 4],
  "max_single_source_sec": 6,
  "max_still_hold_sec": 3,
  "visual_variety_priority": "high",
  "transition_style": "rhythmic",
  "attention_strategy": "music_rhythm"
}
```

Use when music and visual variety carry attention. This mode should strongly
discourage one long stock clip per segment.

### Story Documentary

```json
{
  "mode": "story_documentary",
  "preferred_shot_sec": [3, 8],
  "max_meaningful_shot_sec": 10,
  "continuity_priority": "high",
  "visual_variety_priority": "medium",
  "transition_style": "motivated",
  "attention_strategy": "event_progression"
}
```

Use when causality and progression matter more than constant motion.

## Implementation Order

1. Add schema/defaults for `editorial_intent`, `editing_intent`, `pacing`,
   `still_image_policy`, and `transition_philosophy`.
2. Extend material coverage to report function-level coverage and variety.
3. Extend assembly plan to generate `shot_slots`.
4. Extend timeline build to preserve slot/function/reason/treatment trace.
5. Add mechanical visual fatigue/editorial-fit audit.
6. Surface audit findings in dashboard/runtime.
7. Add two E2E quality fixtures:
   - one MV-style fixture where one-source long holds fail;
   - one warm-documentary fixture where justified longer holds pass.

## Non-Goals

- Do not require cinematic director UI.
- Do not force rapid cuts for every video.
- Do not make CapCut, Remotion, Blender, or Playwright mandatory.
- Do not put provider-specific file choices in SPEC.
- Do not let optional VLM review become the only verifier.
