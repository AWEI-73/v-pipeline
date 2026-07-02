---
name: video-intent-planner
description: Use at Stage 0 before story, material, or BUILD work to decide input state, entry path, follow-up questions, and handoff.
---

# Video Intent Planner

Stage 0 is **Video Intent Planner**. It is infrastructure, not a template for a
specific video type.

Shared hard boundary: read `skills/pipeline-boundary.md`. This skill owns the
Stage 0 entry lock. Do not direct-cut from a fuzzy request; if route-changing
facts are missing, write `required_followup_questions` and hand off to
`ask_followup`.

Use it before Story Soul, Material Truth, generated material fallback, BUILD,
Workbench, Brownfield, Node14, or Remotion.

## Responsibility

Decide only what changes the route:

- video purpose and goal;
- audience;
- target length;
- video type;
- existing material availability, quality, and quantity;
- material scan scope decision when material exists;
- text/article/outline/story availability;
- input state: `material_available`, `text_available`, `idea_only`, or
  `unknown`;
- entry path: `material-first`, `structure-first`, or `needs-context`;
- whether generated material fallback may be needed;
- the next handoff target.

Do not write a teaching template, event template, renderer plan, BUILD ranking
rule, or effect/Remotion route here.

## Canonical Artifact

Stage 0 package is `project_brief.json`, `interaction_log.md`, and
`video_intent.json`. `target_length` is required when the user provides it; if
it is unknown and route/build decisions depend on it, add a focused item to
`required_followup_questions` and stop at `needs-context`.

Write `video_intent.json` through:

```powershell
python video_tools.py video-intent-plan project_brief.json --out video_intent.json
```

Required shape:

```json
{
  "artifact_role": "video_intent",
  "stage": "Video Intent Planner",
  "input_state": "material_available | text_available | idea_only | unknown",
  "entry_path": "material-first | structure-first | needs-context",
  "video_type": "teaching | storybook | graduation-event | personal-memory | brand-product | ...",
  "audience": "...",
  "goal": "...",
  "target_length": "about 5 minutes | 90 seconds | unknown",
  "material_availability": "existing | none | partial",
  "text_availability": "article | outline | brief | script | story | none | unknown",
  "route": "material-first | structure-first | needs-context",
  "legacy_route": "existing-material-first | story-first | hybrid | null",
  "material_contract": {
    "artifact_role": "stage0_material_intent",
    "contract_status": "required | optional | deferred | not_applicable",
    "availability": "existing | none | partial | unknown",
    "owner": "material_map_lifecycle | upstream_structure_route | Video Intent Planner",
    "first_action": "material_map_quick_inventory | derive_material_needs_after_structure | ask_material_availability",
    "gap_policy": "material_delta_decides_generate_reshoot_rewrite_drop_or_waiver",
    "scan_decision": {}
  },
  "material_scan_decision": {
    "artifact_role": "stage0_material_scan_decision",
    "needed": true,
    "default_scope": "all_materials | user_specified | not_applicable",
    "user_scope": "optional user-provided folder/file scope",
    "scan_depth": "quick_inventory_first | none",
    "first_action": "material_map_quick_inventory | none",
    "followup_question": "要先掃全部素材，還是只掃指定資料夾 / 檔案？"
  },
  "soundtrack_contract": {
    "artifact_role": "stage0_soundtrack_intent",
    "status": "requested | unspecified",
    "contract_status": "required | optional | deferred | not_applicable",
    "music_role": "song | bgm | mixed | none | unsure",
    "vocal_policy": "vocal_ok | instrumental_preferred | section_dependent | none | unknown",
    "energy_intent": "warm_to_high | high | warm | unspecified",
    "speech_preservation": "required | preserve_if_detected",
    "ducking_policy": "duck_under_voice | none",
    "fallback_policy": {
      "provider_fallback": ["jamendo_song", "pixabay_music", "manual_import", "reference_only"],
      "role_fallback": "song_to_bgm_requires_review | bgm_to_silence_requires_review",
      "brownfield_fallback": "workbench_replace_or_retime_after_review"
    },
    "section_strategy": "section_based | unknown",
    "handoff_to": "soundtrack-arranger | none"
  },
  "communication_intent": {
    "artifact_role": "stage0_communication_intent",
    "voiceover_policy": "required | optional | none | undecided",
    "subtitle_policy": "required | optional | none | undecided",
    "original_audio_policy": "preserve_speech | replace_with_music | mixed | preserve_if_detected | undecided",
    "music_policy": "bgm | song | mixed | none | undecided",
    "speech_priority": "high | medium | low | unknown",
    "ducking_policy": "duck_under_voice | none",
    "time_authority": "video_sections | music_sections",
    "handoff_to": ["soundtrack_arranger", "audio_director", "subtitle_director"]
  },
  "effect_policy": {
    "artifact_role": "stage0_effect_policy",
    "status": "requested | unspecified",
    "contract_status": "required | optional | deferred | not_applicable",
    "activation": "route_to_effect_factory | defer_to_brownfield_or_segment_review | none",
    "required_now": false,
    "handoff_to": "video-effect-factory | video-effect-factory_when_segment_requires_effect | none"
  },
  "subtitle_voiceover_contract": {
    "artifact_role": "stage0_subtitle_voiceover_intent",
    "status": "requested | unspecified",
    "contract_status": "required | optional | deferred | not_applicable",
    "language": "zh-TW | en | mixed | unknown",
    "subtitle_required": true,
    "voiceover_required": false,
    "narration_policy": "required | optional | none | unknown",
    "preferred_provider": "voxcpm | legacy_tts | none",
    "fallback_provider": "legacy_tts | none",
    "fallback_allowed": false,
    "provider_runtime": "local | generic | none",
    "handoff_to": "subtitle-director | audio-director | none"
  },
  "stage0_child_contracts": {
    "material": {},
    "soundtrack": {},
    "effect": {},
    "subtitle_voiceover": {},
    "communication": {}
  },
  "required_followup_questions": [],
  "assumptions": [],
  "handoff_to": "material_map_lifecycle | upstream_structure_route | ask_followup",
  "handoff_packet": {
    "owner": "material_map_lifecycle | upstream_structure_route | Video Intent Planner",
    "first_action": "material_map_quick_inventory | story_soul_blueprint | ask_followup_questions",
    "required_inputs": [],
    "expected_outputs": [],
    "return_to": "..."
  }
}
```

## Interaction Rule

If route-changing information is missing, ask a small number of key questions
instead of guessing:

- What kind of video is this: teaching, event recap, story, brand short,
  personal memory, or other?
- Do you already have material? Is it complete, partial, or uncertain quality?
- If this is an editing request with material, should we scan all materials
  first or only a specified folder/file scope?
- Do you have an article, outline, script, story, or only a loose idea?
- Roughly how long should the final video be?
- Who is the audience?
- Should the style feel documentary, energetic, warm, story-driven, MV-like, or
  clearly instructional?
- If music matters, should it be songs with vocals, instrumental BGM, mixed by
  section, or no music?
- If effects matter, which section needs the effect and what story function
  should it serve?

## Second-Turn Canonical Output Rule

After the user answers the first clarification question, write or update the
Stage 0 summary as canonical objects. Do not collapse child contracts into
free-form strings just because the branch will run later.

For material-first editing requests, the second-turn summary must include:

```json
{
  "input_state": "material_available",
  "entry_path": "material-first",
  "route": "material-first",
  "material_scan_decision": {
    "artifact_role": "stage0_material_scan_decision",
    "needed": true,
    "default_scope": "all_materials",
    "user_scope": null,
    "scan_depth": "quick_inventory_first",
    "first_action": "material_map_quick_inventory",
    "followup_question": "要先掃全部素材，還是只掃指定資料夾 / 檔案？"
  },
  "soundtrack_contract": {
    "artifact_role": "stage0_soundtrack_intent",
    "status": "requested | unspecified",
    "music_role": "song | bgm | mixed | none | unsure",
    "vocal_policy": "vocal_ok | instrumental_preferred | section_dependent | none | unknown",
    "speech_preservation": "required | preserve_if_detected",
    "ducking_policy": "duck_under_voice | none",
    "handoff_to": "soundtrack-arranger | none"
  },
  "subtitle_voiceover_contract": {
    "artifact_role": "stage0_subtitle_voiceover_intent",
    "status": "requested | unspecified",
    "language": "zh-TW | en | mixed | unknown",
    "subtitle_required": true,
    "voiceover_required": false,
    "preferred_provider": "voxcpm | legacy_tts | none",
    "fallback_provider": "legacy_tts | none",
    "fallback_allowed": false,
    "provider_runtime": "local | generic | none",
    "handoff_to": "subtitle-director | audio-director | none"
  },
  "handoff_packet": {
    "owner": "material_map_lifecycle",
    "first_action": "material_map_quick_inventory"
  }
}
```

If the user says "scan everything", set `default_scope` to `all_materials` and
`user_scope` to `null`. If the user names a folder, file, time range, or
selection, set `default_scope` to `user_specified` and put the plain user scope
in `user_scope`.

Exact key names are part of the contract. Use the keys from the JSON block
above even when writing a short summary. Do not rename `scan_depth` to `mode`,
`scope`, or `quick_inventory_first`. Do not rename `first_action` value `material_map_quick_inventory` to `material_quick_inventory`. Do not move
`material_scan_decision` under a custom `video_intent` wrapper unless the same
canonical object is also present at top level.

Do not write `"material_scan_decision": "scan_all_materials"`.
Do not write `"soundtrack_contract": "defer"`.
Do not write `"subtitle_voiceover_contract": "defer"`.
Use `status: "unspecified"` and `handoff_to: "none"` when a branch is not
requested yet; use `status: "requested"` when the user asked for music,
subtitles, narration, voiceover, or source-audio preservation.

## Handoff

- `material-first` -> run material map lifecycle first, then use map findings
  to reduce ambiguity and build structure.
- `structure-first` -> run upstream structure route; if no material exists, run
  initial material delta before generated material fallback.
- `needs-context` -> ask follow-up questions before choosing a handoff.

Stage 0 may record child intent contracts, but must not run child branches from
fuzzy whole-video intake:

- `material_contract` is always written so the next operator knows whether
  Material Map or upstream structure owns the first real work.
- `material_scan_decision` is a Stage 0 child decision, not a separate entry.
  For material-first editing requests, default to `all_materials` with
  `quick_inventory_first` unless the user specifies a folder/file scope. This
  first scan is only to reveal enough material facts for better interaction; it
  is not full VLM review, BUILD, or render.
- `soundtrack_contract` records the initial song/BGM/mixed/none choice,
  energy direction, speech preservation, ducking, and fallback policy. It may
  hand off to Soundtrack Arranger after Stage 0. Provider fallback is allowed,
  but role fallback such as `song -> bgm` must be reviewed and cannot happen
  silently.
- `communication_intent` is the cross-lane policy for voiceover, subtitles,
  original source audio, and music. It decides the safe default before BUILD:
  preserve speech when speech is important, replace source audio with music for
  music-only highlight/MV sections, and use section-level mixed policy when the
  request combines speech-led and music-led parts.
- `effect_policy` records whether a bounded effect should go to Effect Factory
  now, or whether effects should wait for Brownfield/segment review. Do not
  launch Remotion from Stage 0 just because the whole video has a warm,
  energetic, cinematic, or MV-like style.
- `subtitle_voiceover_contract` records whole-video language, subtitle,
  narration, and voiceover intent. Keep it visible for Stage 2/5/7/10 even
  before the dedicated Subtitle / Voiceover branch is fully hardened.

`handoff_packet` is the run-folder / route-task handoff summary. It records the
next owner, first action, required inputs, expected outputs, and return point so
the next operator can continue without starting VIP1/VIP2 templates.

Compatibility:

- `existing-material-first` maps to `material-first`.
- `story-first` maps to `structure-first`.
- `hybrid` is not a primary Stage 0 entry path; partial material enters
  `material-first`, then material delta chooses generation, reshoot, rewrite,
  drop, or waiver.

Generated material remains fallback/candidate material until provider mapping,
import, explicit review, and fresh material delta pass.
