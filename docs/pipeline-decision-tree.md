# Hermes Pipeline Decision Tree

Status: canonical operator decision tree for main route and side branches

This file is the "what should I do next?" layer. It does not replace
`docs/video-pipeline-operating-map.md`, `docs/canonical-video-pipeline-route.md`,
`docs/stage-boundary-matrix.md`, or `docs/branch-contract-registry.json`. Use
this decision tree before choosing tools, dispatching a worker, or continuing a
run. After the current owner branch is known, use the branch contract registry
to check allowed writes, required handoff artifacts, stop gates, and return
routes.

The rule is simple: decide the owner, write or inspect the handoff artifacts,
then stop at the owning gate. Do not turn a user phrase into a direct command.
Each branch lists forbidden actions, handoff artifacts, and return route so a
worker can stop without guessing.

The branch registry is the machine-readable ownership contract for:

- `main-pipeline`
- `material-map`
- `soundtrack-arranger`
- `subtitle-voiceover`
- `effect-factory`
- `workbench-brownfield`
- `verify-delivery`

## Global Precedence

1. Existing run state wins. If a run folder exists, inspect it with
   `tools/pipeline_home.py --run RUN_DIR --json` before choosing a branch.
2. Whole-video requests enter Stage 0 first, even when they mention music,
   subtitle, transition, warm, cinematic, hot-blooded, or effects.
3. Side branches are first owners only for bounded branch work: a specific
   material-map review, effect asset, music/source decision, subtitle/voiceover
   handoff, or verify request.
4. Workbench/Brownfield edits are draft-only / draft-level unless their patch is
   promoted by the owning canonical route.
5. Review / Verify may be called at any stage, but it must fail closed when
   evidence is missing or stale.

## Needs-Context Exit Rule

`needs-context` is a stop state, not a creative invitation. Ask at most two
rounds of 1-3 route-changing questions. If the answer is still ambiguous:

- keep `entry_path` as `needs-context`;
- write the remaining ambiguity into `required_followup_questions`;
- write explicit `assumptions` only for non-route-changing details;
- do not enter branch tools unless the user explicitly approves a bounded
  exploratory action such as material quick inventory.

If material exists and the main blocker is "I do not know what is inside", the
safe fallback is not BUILD; it is `material_scan_decision` plus quick inventory.

## Main Pipeline Decision Tree

Purpose: decide the full video route from intake to delivery.

```text
User asks for video work
  |
  +-- Existing run folder, stuck run, final candidate, or resume request?
  |     -> Inspect pipeline_home.py
  |     -> Follow cursor / next_action
  |     -> Stop on repair, unknown, unresolved review, or stale artifacts
  |
  +-- Whole-video request?
  |     -> Stage 0 Video Intent Planner
  |     -> Write/read project_brief.json, interaction_log.md, video_intent.json
  |     -> If route-changing facts are missing, ask required_followup_questions
  |
  +-- Bounded branch-only request?
        -> Enter the branch decision tree below
        -> Return to main pipeline only through handoff artifacts
```

Stage 0 required decisions:

- `input_state`: `material_available`, `text_available`, `idea_only`, or
  `unknown`.
- `entry_path`: `material-first`, `structure-first`, or `needs-context`.
- `material_scan_decision`: whether material-first should scan all material or
  only a user-specified scope.
- `soundtrack_contract`: song/BGM/mixed/none intent, vocal policy, license and
  fallback policy, speech preservation, and ducking.
- `subtitle_voiceover_contract`: subtitle language, narration, voiceover, and
  handoff target.
- `effect_policy`: whether a bounded effect routes now or waits for segment /
  Brownfield review.

### Stage 0 Decision Order

Decide Stage 0 in this order. The order matters because some child contracts
depend on the entry path but should still be recorded before branch work starts.

1. Decide `input_state`: material, text/story, idea-only, or unknown.
2. Decide `entry_path`:
   - material exists -> `material-first`;
   - no material but text/story/idea exists -> `structure-first`;
   - route-changing facts are missing -> `needs-context`.
   One long source, interview, podcast, lecture, or dialogue highlight still
   enters `material-first`; it then uses the one-source / dialogue sub-branch
   before any cut.
3. If `entry_path = material-first`, fill `material_scan_decision` before any
   material tool: all materials vs user-specified scope, quick inventory first,
   and first action.
4. Fill child intent contracts in parallel with the route, not after BUILD:
   `soundtrack_contract`, `subtitle_voiceover_contract`, `effect_policy`, and
   `communication_intent`.
5. If any child intent is not needed yet, mark it `unspecified` or deferred with
   owner/reason/return point; do not erase it.
6. Write `handoff_packet` to the next owner.

### Branch Insertion Points

audio and effect branches are child lanes of the main route, not separate main
routes. They insert at these points:

- Stage 0: record intent and safe defaults only.
- Before BUILD: run a branch only if BUILD needs a concrete asset, license,
  subtitle/voice handoff, or effect contract.
- During BUILD: consume only branch artifacts that already passed their gate.
- After Verify: if review finds subtitle, loudness, effect, or finishing issues,
  route to Audio Communication, Effect Factory, or Workbench/Brownfield.
- Before Delivery: Review / Verify / Delivery Gate checks that required audio,
  subtitle, music, and effect evidence exists.

If a child branch is optional for the current build, defer it with owner, reason,
and return point. If it is required for the current build, resolve it before
BUILD.

Main route branches:

```text
Stage 0 video_intent.json
  |
  +-- entry_path = material-first
  |     -> Material Map Branch Decision Tree
  |     -> return route: structure/story from material facts, then BUILD
  |
  +-- entry_path = structure-first
  |     -> Story / structure route
  |     -> material_needs.json
  |     -> Material Map or generated-material fallback after delta
  |
  +-- entry_path = needs-context
        -> Ask 1-3 route-changing questions
        -> Do not run branch tools until answer updates video_intent.json
```

### Structure-First Decision Path

Structure-first is not an empty shortcut to generated material. It owns the
upstream story/structure work when no usable material exists yet.

```text
entry_path = structure-first
  -> story / structure route
  -> story_world or story_soul_blueprint
  -> screenplay / beats / section plan
  -> director shot plan
  -> material_needs.json
  -> segment_contract.json or material-ready handoff
  -> Material Map if user later provides material
  -> generated-material fallback only after material delta / need review
  -> story_first_provider_happy_path.py for no-material provider handoff
  -> provider_packet/generated_provider_packet.json
  -> provider_packet/image_agent_handoff/image_agent_prompt_handoff.json
  -> call_image_generation_agent until real provider outputs are supplied
```

The structure route writes the first concrete `material_needs`. Material Map then
proves or disproves those needs. If material remains missing, the explicit
resolution choices are generated candidate fallback, shooting brief, rewrite,
drop, or waiver. Generated candidate fallback must stop at
`call_image_generation_agent` when no real image provider outputs exist but an
image-agent handoff is present. If no image-capable provider is available, report
provider unavailable; do not promote placeholder or text-card images as material.

### BUILD Decision Section

BUILD details live in `docs/build-tool-runner-spec.md`,
`docs/canonical-video-pipeline-route.md`, and the Spec / Contract skill. This
decision tree only decides whether BUILD may be entered.

All BUILD prerequisites are AND conditions. BUILD may begin only after every
applicable item below is satisfied:

- Stage 0 is present and route is not `needs-context`;
- story/design/segment contract exists;
- material needs and accepted material coverage are visible when real material
  is used;
- audio/subtitle/effect child contracts are either resolved, deferred with a
  reason, or assigned to their branch;
- Review / Verify gates are not asking for repair.

Deferred child contracts count as satisfied only when the artifact names the
reason, owner, return point, and a gate confirms the deferral is non-blocking for
the current build. "Deferred" without owner or reason is still unresolved.

If BUILD creates a rough cut, draft preview, failed verify, or user patch request,
the next owner may be Workbench / Brownfield rather than immediate Delivery.

### Single-Source Highlight Closeout

When a material-first sub-route uses one long source video and creates a
highlight preview, do not skip the preview/final boundary.

```text
source_section_map / source_motion_profile / source_material_matrix
  -> reviewed dialogue_edit_script or highlight_selection_plan
  -> rough_cut_plan.json
  -> safe_highlight_cut.py
  -> highlight_cut_report.json + preview mp4
  -> final-product-verify
  -> write_delivery_gate_report.py
  -> package_verified_preview.py
  -> delivery_candidate.mp4 + verified_preview_package.json
  -> operator review writes verified_preview_review_decision.json
  -> if decision=accept_promote
  -> promote_verified_preview.py
  -> final.mp4 + final_promotion_report.json
  -> write_delivery_gate_report.py
  -> pipeline_home.py must report mode=done, cursor=complete
  -> if decision=revise_workbench
  -> workbench_revision_request.json + workbench_handoff.json
  -> preview_timeline.json
  -> Workbench / Brownfield draft patch
```

Rules:

- `delivery_candidate.mp4` is not canonical final output.
- `verified_preview_review_decision.py` is the explicit stop after operator
  review. Valid decisions are `accept_promote`, `revise_workbench`,
  `rebuild_motion_preview`, and `reject`.
- `decision=revise_workbench` writes `workbench_revision_request.json`; this
  request carries the operator notes and suggested Workbench edits. It does not
  mutate `final.mp4`, `timeline_build.json`, or `project_material_map.json`.
- `promote_verified_preview.py` is only allowed after
  `verified_preview_review_decision.json` says `decision=accept_promote`; it
  copies the verified candidate to `final.mp4`.
- Preserve-original-audio highlights may write minimal delivery requirements:
  audio required, narration/music/subtitles not required.
- If the complete delivery gate fails after promotion, return to Stage 5/7
  repair. Do not claim the preview as complete delivery.

Forbidden actions:

- direct-cut from a fuzzy request;
- render `final.mp4` from Stage 0;
- treat `route_judgment.json` as `video_intent.json`;
- treat a Workbench draft, generated candidate, effect preview, or downloaded
  music as canonical without the owning gate.

Handoff artifacts:

- `project_brief.json`
- `interaction_log.md`
- `video_intent.json`
- `handoff_packet`
- branch-specific reports listed below

## Material Map Branch Decision Tree

Purpose: prove what visual/source material exists, what it can satisfy, and what
gaps remain.

```text
Material exists or may exist
  |
  +-- Stage 0 says material_scan_decision.needed = true?
  |     -> tools/material_quick_inventory.py
  |     -> material_inventory_summary.json
  |     -> human/agent reviews the inventory before deeper scan
  |     -> tools/material_understanding_matrix.py when multiple assets need visual/audio evidence before wall verdict
  |     -> material_understanding_matrix.json / contact sheet
  |     -> optional tools/material_wall_verdict_draft.py for one-primary-per-role draft
  |     -> review/edit draft before it becomes material_wall_review_verdict.json
  |
  +-- Need material truth / scene coverage?
  |     -> optional tools/material_first_happy_path.py for no-render full happy path
  |        when the goal is to prove matrix -> draft verdict -> acceptance before editing
  |     -> optional tools/material_first_preview_plan.py for 60-90s review proposal
  |        after matrix and wall verdict draft exist
  |     -> optional tools/rough_cut_storyboard_preview.py when source clips are too large for quick motion preview
  |     -> optional tools/rough_cut_plan_execute.py only after storyboard/material order is accepted
  |     -> material map lifecycle
  |     -> project_material_map.json / per-asset maps
  |     -> material_wall_review_verdict.json when review is needed
  |
  +-- Need scene-to-need proof?
  |     -> material_map_review_apply / lifecycle review apply
  |     -> satisfies edges: scene -> need_id
  |     -> material_delta.json
  |
  +-- One long source / speech-first highlight?
  |     -> source-section-map / source-motion-profile / source-material-matrix
  |     -> correct subtitle or reviewed ASR
  |     -> source-dialogue-script
  |     -> dialogue_edit_script.json review
  |     -> safe_highlight_cut only after script/windows are accepted
  |
  +-- Enough accepted coverage?
  |     -> rough_cut_plan.json if trimming / highlight cut is needed
  |     -> return route: BUILD / structure contract
  |
  +-- Missing or thin must-have needs?
        -> generated candidate fallback, shooting brief, rewrite, drop, or waiver
        -> return route only after fresh delta passes
```

Stop gates:

- inventory summary exists but user has not reviewed scope;
- `await_map_review`;
- missing `satisfies` edges for must-have needs;
- one-source speech-first highlight has no reviewed transcript/script;
- selected dialogue windows cut half sentences or ignore complete sentence flow;
- duplicate/rejected material would enter the timeline;
- generated candidates have not been explicitly reviewed.

Forbidden actions:

- full render;
- silent generated-material promotion;
- treating storyboard or motion preview candidates as canonical delivery;
- treating file names as visual truth when the route requires review evidence;
- continuing to BUILD when material delta says missing/thin without a waiver.

Handoff artifacts:

- `material_inventory_summary.json`
- `materials_db.json`
- `material_understanding_matrix.json`
- `material_understanding_contact_sheet.jpg`
- `material_wall_review_verdict.draft.json` when matrix-assisted drafting is used
- `material_first_happy_path_report.json` when the no-render wrapper is used
- `preview_rough_cut_plan.json` for 60-90 second non-canonical review proposal
- `rough_cut_storyboard_preview_report.json` for cheap still-frame review
- `rough_cut_preview_report.json` for bounded motion preview or fail-closed fallback
- `project_material_map.json`
- `material_wall_review_verdict.json`
- `material_delta.json`
- `rough_cut_plan.json`
- `source_section_map.json`
- `source_material_matrix.json`
- `source_transcript.json`
- `dialogue_edit_script.json`
- `dialogue_highlight_windows.json`
- `material_first_boundary_acceptance_report.json`

Return route:

- to Stage 1/structure when material facts are needed for story shape;
- to BUILD when accepted coverage and contract are ready;
- to generated-material / shooting brief branch when gaps remain;
- to Review / Verify when material evidence is disputed.

### Loop Break Conditions

Material Map and Stage 1/structure may call each other, but the loop is not
open-ended:

- These rules apply in both directions: material-first
  `Material Map -> Stage 1 -> Material Map` and structure-first
  `Stage 1 -> material_needs.json -> Material Map -> Stage 1`.
- Material Map first exposes facts: available scenes, usable ranges, duplicate
  risk, speech/audio clues, and obvious gaps.
- Stage 1/structure consumes those facts to write a story/segment contract and
  concrete `material_needs`.
- Material Map runs again only when the contract introduces new or changed
  `material_needs`, or when Review / Verify flags a material mismatch.
- If a second pass still has missing must-have needs, choose one explicit
  resolution path: generated candidate fallback, shooting brief, rewrite, drop,
  or waiver. Do not bounce back to Stage 1 without a new contract change.

## Effect Factory Branch Decision Tree

Purpose: translate effect intent into reviewable design language, bounded worker
payloads, and evidence that effects rendered as intended.

```text
Effect language appears
  |
  +-- Whole-video fuzzy style only?
  |     -> record in effect_policy
  |     -> wait for segment / Brownfield context
  |
  +-- Bounded effect request?
  |     -> visual_technique_plan.json
  |     -> ask/confirm candidate parameters if ambiguous
  |     -> visual_technique_plan.confirmed.json after review
  |
  +-- Effect is required for story or delivery?
  |     -> effect_capability_review.json
  |     -> effect_design_map.json
  |     -> effect_contract.json
  |     -> backend handoff: Remotion worker or light backend
  |
  +-- Worker output exists?
        -> remotion_prompt_pack.json
        -> remotion_worker_outputs.json
        -> remotion_effect_review.json
        -> effect_review.json
        -> effect_handoff.json
        -> return route: Workbench / BUILD / Verify
```

Use Effect Factory for bounded effects. A bounded effect means the request has
or can quickly confirm: section, duration, story function, visual family, source
refs if any, and review evidence. If those cannot be named, keep it in
`effect_policy` and wait for segment or Brownfield context.

Use Effect Factory for:

- opening title / intro;
- chapter transition;
- lower third or speaker intro;
- highlight overlay;
- emotional visual treatment;
- stylized asset such as fire, lightning, hearts, sakura, memory wall, or
  ceremony light, when the request is bounded enough to review.

Current no-render route acceptance:

```powershell
python tools\effect_factory_route_acceptance.py `
  --out RUN_DIR `
  --request "electric lightning opening with readable title" `
  --effect-role opening_title `
  --duration-sec 4 `
  --json
```

This is the preferred smoke for the complete Effect Factory line. It proves:

```text
semantic request
  -> visual_technique_plan.json
  -> visual_technique_plan.confirmed.json
  -> effect_capability_review.json
  -> effect_intent_plan.json
  -> effect_revision_request.json
  -> timeline_build.json
  -> remotion_prompt_pack.json
  -> remotion_worker_outputs.json
  -> remotion_effect_review.json
  -> effect_handoff.json
  -> effect_factory_route_acceptance_report.json
```

Expected route surface after a pass:

```text
pipeline_home.py --run RUN_DIR --json
cursor=effect_factory_route_acceptance
next=ready_for_human_effect_review_or_pipeline_promotion
final.mp4 must remain absent
```

This smoke does not prove final visual quality. It proves translation,
capability review, worker handoff, review artifact presence, and bounded
handoff. Use a separate preview/render probe for visual-quality judgment.

Stop gates:

- effect parameters are unconfirmed;
- backend cannot render a required effect;
- worker output lacks contact sheet, keyframes, or review evidence;
- the requested effect changes material truth rather than finishing.

Forbidden actions:

- launching Remotion from Stage 0 because a whole video is "cinematic";
- making the effect preview the final video;
- hiding required effects as decorative;
- bypassing `effect_render_verification.json` for planned delivery effects.

Handoff artifacts:

- `visual_technique_plan.json`
- `visual_technique_plan.confirmed.json`
- `effect_capability_review.json`
- `effect_design_map.json`
- `effect_contract.json`
- `remotion_prompt_pack.json`
- `remotion_worker_outputs.json`
- `remotion_effect_review.json`
- `effect_factory_route_acceptance_report.json`
- `effect_review.json`
- `effect_handoff.json`
- `effect_render_verification.json`

Return route:

- to Workbench/Brownfield for draft composition;
- to BUILD when the effect is a planned asset in the segment contract;
- to Review / Verify when rendered evidence is required.

## Workbench / Brownfield Branch Decision Tree

Purpose: apply bounded draft/finishing changes after a run, rough cut, preview,
or review finding exists. Workbench is an editing surface; it is not canonical
truth by itself.

### Workbench Natural Entry Points

Workbench / Brownfield naturally enters after a rough cut, draft preview, failed
verify, or user patch request. It may also enter from a dashboard review when the
user wants to inspect or adjust a non-canonical timeline draft.

```text
User refers to a draft, rough cut, timeline, final candidate, or local fix
  |
  +-- Existing run folder or draft artifacts exist?
  |     -> inspect pipeline_home.py / dashboard state first
  |     -> identify whether the patch changes material truth or finishing only
  |
  +-- Patch changes material truth?
  |     -> return to Material Map / Delta
  |     -> do not write canonical timeline directly
  |
  +-- Patch is finishing-only?
  |     -> Workbench / Brownfield draft patch
  |     -> timeline_patch.json, subtitle_patch.json, audio_cue_patch.json,
  |        or effect_patch.json
  |
  +-- Draft patch reviewed?
        -> rerender draft or handoff to owning branch
        -> return route: Verify / Delivery gate
```

Stop gates:

- no run folder or draft artifact is identified;
- patch would overwrite canonical artifacts without review;
- requested replacement changes accepted material truth;
- subtitle/audio/effect patch lacks its owning branch handoff;
- draft preview exists but verify evidence is missing.

Forbidden actions:

- treating Workbench edits as canonical without promotion;
- editing `final.mp4` in place;
- replacing material-map truth from the UI alone;
- hiding a material, audio, subtitle, or effect issue as a local cosmetic patch.

Handoff artifacts:

- `preview_timeline.json`
- `timeline_patch.json`
- `subtitle_patch.json`
- `audio_cue_patch.json`
- `effect_patch.json`
- `workbench_handoff.json`
- `workbench_review_report.json`

Return route:

- material-changing patch -> Material Map Branch;
- subtitle or voice issue -> Audio Communication Branch / Subtitle Director;
- effect issue -> Effect Factory Branch;
- finishing-only patch -> Review / Verify / Delivery Gate.

## Audio Communication Branch Decision Tree

Purpose: decide what the audience hears and reads: source audio, music,
subtitles, voiceover, narration, and final mix policy.

This branch includes three lanes:

- Source Audio: original speech, ambience, on-camera sound, keep/remove policy.
- Soundtrack: song, BGM, mixed section strategy, source, license, fallback.
- Caption & Voice: subtitles, narration, voiceover, TTS/voice repo handoff.

```text
Audio / subtitle / voice intent appears
  |
  +-- Whole-video request?
  |     -> record communication_intent, soundtrack_contract,
  |        subtitle_voiceover_contract in Stage 0
  |
  +-- Music/song/BGM source is needed?
  |     -> Soundtrack Arranger
  |     -> soundtrack_plan.json
  |     -> music_source_candidates.json
  |     -> sound_license_manifest.json
  |     -> soundtrack_probe_report.json for accepted audio
  |
  +-- Original speech matters?
  |     -> preserve_speech or preserve_if_detected
  |     -> Audio Director owns ducking / normalization / final mix
  |
  +-- Subtitle / narration / voiceover matters?
  |     -> Subtitle Director or Audio Director handoff
  |     -> choose provider policy:
  |        - no voiceover needed -> subtitle_only or no-op
  |        - source speech is primary -> preserve_source_audio
  |        - Chinese/Mandarin narration -> preferred_provider=voxcpm,
  |          fallback_allowed=false by default
  |        - quick allowed fallback -> legacy_tts
  |     -> subtitle_voiceover_handoff.json / narration_manifest.json
  |
  +-- Mix is ready for delivery?
        -> final_audio.wav / audio_mix_report.json
        -> return route: BUILD / Verify / Delivery
```

Common policies:

- If the source video contains important speech, preserve original audio and
  duck music under speech.
- If the section is music-led / MV-like and no speech is needed, source audio may
  be removed or lowered by contract.
- VoxCPM is a provider inside Audio Director, not a separate route. Use
  `tools/voxcpm_runtime_check.py` before execution and
  `tools/voxcpm_voiceover_provider.py` only after the contract requires real
  narration audio. For Mandarin/Chinese voiceover, Stage 0 should prefer
  VoxCPM and fail closed unless the contract explicitly allows fallback.
- Songs with vocals and instrumental BGM are different roles. Role fallback
  requires review.
- Famous songs or YouTube references may be `reference_only` unless the license
  is explicitly acceptable for the run.

Stop gates:

- license/source unknown;
- speech preservation policy missing when the source may contain speech;
- music role fallback happened silently;
- soundtrack probe is missing for accepted downloaded audio when final delivery
  depends on music fit;
- subtitles required but language, source text, or readability evidence is
  missing.
- required voiceover but `narration_manifest.json` or
  `subtitle_voiceover_build_handoff.json` is missing, or
  `voiceover_ready=false`.

Forbidden actions:

- treating Soundtrack Arranger output as final mixed audio;
- letting BGM cover important speech without a ducking policy;
- repairing subtitles inside Soundtrack Arranger;
- using unlicensed/reference-only music as final delivery without an explicit
  waiver.

Handoff artifacts:

- `communication_intent`
- `soundtrack_contract`
- `subtitle_voiceover_contract`
- `soundtrack_plan.json`
- `music_source_candidates.json`
- `sound_license_manifest.json`
- `soundtrack_probe_report.json`
- `audio_director_handoff.json`
- `subtitle_voiceover_handoff.json`
- `audio_mix_report.json`
- `subtitles.srt`

Return route:

- to BUILD when audio/subtitle requirements are resolved or explicitly deferred;
- to Audio Director for mix execution;
- to Subtitle Director for caption/narration handoff;
- to Review / Verify for loudness, ducking, subtitle readability, and delivery
  evidence.

## Review / Verify / Delivery Gate Cross-Cutting Decision Tree

Purpose: prove that a decision, artifact, draft, branch output, or final video is
actually correct. This is a cross-cutting branch, not only the last stage.

```text
Any stage claims "ready", "passed", "final", or "can build"
  |
  +-- Is the claim about route/intake?
  |     -> check Stage 0 package and required_followup_questions
  |
  +-- Is the claim about material truth?
  |     -> inspect material map, delta, satisfies edges, montage/evidence
  |
  +-- Is the claim about contract/build?
  |     -> inspect segment contract, supply review, timeline/build reports
  |
  +-- Is the claim about audio/subtitles?
  |     -> inspect license, probe, ducking, subtitles, mix report
  |
  +-- Is the claim about effects?
  |     -> inspect effect contract, worker outputs, rendered evidence
  |
  +-- Is the claim about final delivery?
        -> delivery gate
        -> fail closed unless final path, verify status, evidence, manifests,
           and known limitations are present
```

Verify can be called from:

- Stage 0 route acceptance;
- Material Map review / material delta;
- Spec / Contract review;
- BUILD timeline review;
- Audio Communication branch;
- Effect Factory branch;
- Workbench/Brownfield patch review;
- final Delivery.

Fail closed when:

- evidence is missing, stale, or refers to the wrong artifact;
- `verify_result.json` says pass but delivery gate finds semantic mismatch;
- timeline clips do not match material map ids or need refs;
- subtitles are text-matched but visually unreadable;
- planned effects are missing rendered evidence;
- audio/music/subtitle requirements are declared but manifests are absent;
- generated material is used without candidate review.

Forbidden actions:

- accepting warnings as pass for complete-video validation;
- relying only on `verify_result.json` when delivery gate has deeper semantic
  checks;
- marking a run complete while reviewer state says revise/block;
- hiding limitations instead of writing them into delivery notes.

Handoff artifacts:

- `verify_result.json`
- `qa_report.json`
- `review_report.md`
- `delivery_gate_report.json`
- `frame_evidence.json`
- `contact_sheet.jpg`
- `effect_render_verification.json`
- `soundtrack_probe_report.json`
- `audio_mix_report.json`
- `run_layout.json`

Return route:

- factual/material failure -> Material Map Branch;
- story/contract mismatch -> Stage 1/Contract;
- finishing-only issue -> Workbench/Brownfield;
- audio issue -> Audio Communication Branch;
- effect issue -> Effect Factory Branch;
- final clean pass -> Delivery.
