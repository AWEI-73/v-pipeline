---
name: brownfield-edit
description: Use when editing an existing Hermes draft, rough cut, final candidate, Workbench patch, VERIFY gap, local finishing request, subtitle patch, volume repair, clip replacement, or non-canonical preview without changing story/material truth.
---

# Brownfield Edit Route

Brownfield Edit is the fast local patch route for an existing pipeline result.
Use it after a draft/final candidate, Workbench patch, VERIFY gap, or effect gap
already exists. It is not the canonical story/material pipeline.

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "brownfield-edit",
  "stage_owner": "brownfield_workbench_patch_route",
  "triggers": [
    "使用者要調整既有 draft、換片段、改字幕、補特效、重做局部預覽",
    "Workbench patch、VERIFY gap、effect gap 已存在，需要非 canonical 修補"
  ],
  "canonical_tools": [
    {
      "tool": "tools/workbench_handoff.py",
      "when": "將 Workbench draft edits 打包成可審查 handoff",
      "inputs": [
        "workbench draft state",
        "run folder"
      ],
      "outputs": [
        "workbench_handoff.json"
      ],
      "stop_if": [
        "draft references stale material or canonical artifact directly"
      ],
      "capability_id": "cap.brownfield-edit.workbench-handoff.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/workbench_patch_to_contract.py",
      "when": "把已審查 Workbench patch 轉成 contract patch candidate",
      "inputs": [
        "reviewed workbench patch",
        "segment_contract.json"
      ],
      "outputs": [
        "contract_patch.json"
      ],
      "stop_if": [
        "patch changes canonical truth without review"
      ],
      "capability_id": "cap.brownfield-edit.workbench-patch-to-contract.v1",
      "execution_class": "deterministic",
      "capability_role": "adapter",
      "loops": [
        "L5"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/workbench_draft_rerender.py",
      "when": "產生非 canonical draft preview 供人工/agent review",
      "inputs": [
        "validated workbench handoff",
        "draft patch"
      ],
      "outputs": [
        "draft preview video",
        "draft render report"
      ],
      "stop_if": [
        "caller expects final.mp4 or canonical delivery"
      ],
      "capability_id": "cap.brownfield-edit.workbench-draft-rerender.v1",
      "execution_class": "deterministic",
      "capability_role": "review",
      "loops": [
        "L5"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/timeline_patch.py",
      "when": "產生 timeline 局部 draft patch",
      "inputs": [
        "timeline edit request",
        "timeline context"
      ],
      "outputs": [
        "timeline_patch.json"
      ],
      "stop_if": [
        "target segment cannot be resolved"
      ]
    },
    {
      "tool": "tools/subtitle_patch.py",
      "when": "產生字幕局部 draft patch",
      "inputs": [
        "subtitle edit request",
        "subtitle context"
      ],
      "outputs": [
        "subtitle_patch.json"
      ],
      "stop_if": [
        "subtitle would exceed safe area or line policy"
      ]
    },
    {
      "tool": "tools/effect_patch.py",
      "when": "產生局部特效 draft patch",
      "inputs": [
        "effect edit request",
        "effect context"
      ],
      "outputs": [
        "effect_patch.json"
      ],
      "stop_if": [
        "effect is required but lacks review evidence"
      ]
    },
    {
      "tool": "tools/preview_timeline.py",
      "when": "預覽 timeline 結構與 draft impact，不作正式 render",
      "inputs": [
        "timeline or contract"
      ],
      "outputs": [
        "preview timeline report"
      ],
      "stop_if": [
        "timeline cannot be parsed"
      ]
    },
    {
      "tool": "tools/workbench_export.py",
      "when": "匯出 Workbench draft/review artifacts",
      "inputs": [
        "workbench state"
      ],
      "outputs": [
        "workbench export package"
      ],
      "stop_if": [
        "export would overwrite canonical artifacts"
      ]
    },
    {
      "tool": "tools/workbench_review_report.py",
      "when": "將 Workbench draft 轉成 review report",
      "inputs": [
        "workbench state",
        "draft artifacts"
      ],
      "outputs": [
        "workbench_review_report.json"
      ],
      "stop_if": [
        "draft evidence missing"
      ]
    },
    {
      "tool": "tools/workbench_thumbs.py",
      "when": "產生 Workbench 用縮圖與可視 review refs",
      "inputs": [
        "media refs"
      ],
      "outputs": [
        "thumbnail artifacts"
      ],
      "stop_if": [
        "source media missing"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not use Brownfield as first response to a fuzzy new video request",
    "Do not write final.mp4 from a draft rerender",
    "Do not promote draft patches without backend/agent review"
  ],
  "capability_namespace": "cap.brownfield-edit.*",
  "capability_lookup_owner": "brownfield-edit"
}
<!-- TOOL_CONTRACT_END -->

Shared hard boundary: read `skills/pipeline-boundary.md`. Stage 0 entry lock
still applies if the request is a new fuzzy video request. Do not direct-cut
from a fuzzy request; Brownfield starts only from an existing reviewed candidate,
gap, or draft patch.

## Purpose

Turn a local problem into a reviewed artifact that can be consumed by a second
`contract-run`.

Typical inputs:

- Workbench draft patches (`timeline_patch.json`, `subtitle_patch.json`,
  `audio_cue_patch.json`, `effect_patch.json`)
- `light_effects_baseline_review.json`
- `effect_revision_request.json`
- `effect_recipe_patch.json`
- local effect asset / sfx / overlay additions

Typical outputs:

- non-canonical preview render from a draft
- draft patch artifact
- reviewed artifact
- second `contract-run` handoff
- Remotion prompt pack / worker-output review artifact for prompt-driven effects

## Hard Boundaries

- do not rewrite the blueprint.
- Do not rewrite the story contract wholesale.
- Do not overwrite canonical artifacts directly.
- Do not claim browser preview equals final render.
- Do not use Brownfield as a backdoor to satisfy story evidence material.
- Do not mark a `material_need` covered from a new story asset unless it goes
  through material-map review and receives a reviewed `satisfies` edge.

## Asset Addition Rule

Brownfield may handle incremental assets only when they are local finishing
assets:

- effect asset / sfx / overlay
- transition plate
- title texture
- lower-third plate
- light leak or particle overlay

These assets may be imported as effect assets or referenced by effect patches.
They are not real-event evidence and must not satisfy material-map coverage.

If the added asset is story evidence material, route it through the material-map
lifecycle instead:

```text
new story asset
-> material-map import / review
-> satisfies edge
-> fresh material delta
-> BUILD handoff
```

## Route

```text
VERIFY gap / Workbench patch / effect gap
-> Brownfield request
-> draft patch
-> optional incremental effect-asset import
-> reviewed artifact
-> second contract-run
-> VERIFY again
```

The route is fast because it is local and bounded. It is not fast because it
skips review.

## Dirty-Layer Rule

Classify the finding before rerunning anything:

- rendered pixels contradict a unit label or Material Map truth: picture and
  text/effect are dirty; preserve audio only when time boundaries and speech
  placement are unchanged;
- remove or replace a repeated clip with equal duration: picture is dirty;
  audio/text may remain clean only after timecode read-back proves no shift;
- change music color, gain or ducking: audio is dirty; picture stays clean;
- when a formal speech/interview segment pumps between sentences, replace
  activity-driven `speech_aware` with placement-driven `speech_segment` and
  rerender only the audio layer; keep picture/text clean when timing is unchanged;
- change only motif scope or a title lifecycle: effect/text is dirty; do not
  reopen story or material truth.

After the bounded rerun, return through Stage 7 and inspect a 0.5-second
whole-timeline wall. A patch is not accepted merely because its local window
looks correct; the wall must also show that the fix did not create a repeated
unit, wrong label or out-of-scope motif elsewhere.

## Current Tool Mapping

- Workbench draft validation: `workbench-handoff-validate`
- Workbench non-canonical preview: `workbench-draft-rerender`
- Effect gap request: `effect-revision-request`
- Effect draft patch: `effect-revision-draft`
- Reviewed apply: `effect-revision-apply`
- Remotion prompt jobs for adapter-route effect gaps: `remotion-prompt-pack`
- Remotion worker-output validation for Workbench review:
  `remotion-worker-outputs`
- Optional worker smoke for a configured Remotion command: `remotion-worker-smoke`
- Optional local worker command for true Remotion acceptance:
  `tools/remotion_worker_bridge.mjs`
- Non-canonical accepted-output draft composite: `remotion-composite-draft`

Node14 remains a legacy implementation node inside Brownfield Edit. Treat
`effect_revision_request.json` and `effect_recipe_patch.json` as compatible
Brownfield artifacts, not as a separate main pipeline.

## Remotion Prompt-Driven Effects

Use Remotion inside Brownfield only after an effect gap exists or a user asks
for a finishing effect that the ffmpeg-safe route cannot express.

```text
effect_revision_request.json
-> remotion_prompt_pack.json
-> Remotion-capable worker writes remotion_worker_outputs.json + media files
   (local acceptance may use tools/remotion_worker_bridge.mjs)
-> remotion_effect_review.json
-> Workbench / human review
-> remotion-composite-draft (optional non-canonical preview)
-> reviewed artifact
-> second contract-run / ffmpeg composite
```

Rules:

- Prompt is payload, not pipeline logic.
- Do not run Remotion during normal BUILD.
- Do not accept Remotion output into canonical delivery without review.
- Do not use Remotion output as story material evidence.
- Do not write Remotion composites to `final.mp4`; use draft output names until
  a later explicit apply step promotes them.
