---
name: generated-material-producer
description: Use when MGF1 material_generation_fallback.json must be executed into generated image/video assets, provider outputs, material-map candidate evidence, and quality review. Use for generated-material fallback, Gemini/Antigravity/imagegen provider handoff, or offline test renderer validation.
---

# Generated Material Producer

This skill turns planned generated-material jobs into files and reviewable
material-map evidence.

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "generated-material-producer",
  "stage_owner": "generated_material_fallback_branch",
  "triggers": [
    "structure-first 或 material gap 需要生成候選素材",
    "需要驗證 generated material provider mapping、story-to-generated-material flow"
  ],
  "canonical_tools": [
    {
      "tool": "tools/story_first_provider_happy_path.py",
      "when": "no-material/story-first request needs the full safe path to real image provider handoff without test_pil or placeholder cards",
      "inputs": [
        "title/story subject",
        "visual style",
        "target duration",
        "provider list"
      ],
      "outputs": [
        "video_intent.json",
        "story_blueprint/*",
        "material_generation_fallback.json",
        "style_profile.json",
        "provider_packet/generated_provider_packet.json",
        "provider_packet/generated_provider_prompts.md",
        "provider_packet/image_agent_handoff/image_agent_prompt_handoff.json"
      ],
      "stop_if": [
        "pipeline_home does not return call_image_generation_agent",
        "generated_material_production.json exists before provider outputs",
        "final.mp4 exists"
      ],
      "capability_id": "cap.generated-material-producer.story-first-provider-happy-path.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L0"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/generated_material_flow_acceptance.py",
      "when": "驗證 generated material fallback flow，不把生成物直接當 proof material",
      "inputs": [
        "material_generation_fallback.json",
        "material_needs.json"
      ],
      "outputs": [
        "generated_material_flow_acceptance_report.json"
      ],
      "stop_if": [
        "generated asset lacks review path",
        "candidate is treated as accepted material"
      ],
      "capability_id": "cap.generated-material-producer.generated-material-flow-acceptance.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L0"
      ],
      "maturity": "experimental"
    },
    {
      "tool": "tools/story_to_generated_material_e2e.py",
      "when": "驗證 story-first 到 generated-material candidate 的端到端邊界",
      "inputs": [
        "story/brief fixture"
      ],
      "outputs": [
        "story_to_generated_material_e2e_report.json"
      ],
      "stop_if": [
        "provider packet missing",
        "generated candidates skip material-map review"
      ],
      "capability_id": "cap.generated-material-producer.story-to-generated-material-e2e.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [
        "L0"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [],
  "forbidden_tools": [
    "Do not treat generated assets as real footage",
    "Do not satisfy proof-critical material needs without explicit review",
    "Do not render final.mp4 from generated-material acceptance"
  ],
  "capability_namespace": "cap.generated-material-producer.*",
  "capability_lookup_owner": "generated-material-producer"
}
<!-- TOOL_CONTRACT_END -->

Shared hard boundary: read `skills/pipeline-boundary.md`. Stage 0 entry lock
must already be resolved before this skill runs. Do not direct-cut from a fuzzy
request; generated material is a candidate branch, not permission to render.

It is downstream of `skills/material-generation-fallback.md`.

## Core Boundary

Generated assets are never real footage.

**generation is fallback** unless the route is explicitly story-first generated
material, such as storybook, comic, picture-book, synthetic explainer art, or a
declared generated visual style. For existing-material-first teaching,
personal video, event recap, or brand footage routes, generation may provide
diagrams, chapter cards, symbolic inserts, or missing non-proof bridge visuals,
but it must not replace real proof material or satisfy identity-sensitive
events.

Every output must:

- keep `source=generated`
- keep `forbidden_as_truth=true`
- return to material-map as `satisfies.status=candidate`
- require reviewer acceptance before it can count as material coverage
- never satisfy proof-critical, identity-sensitive, official speech, certificate,
  logo, or real-event evidence needs

## Standard Flow

```text
material_needs.json
  -> material-delta proves missing/thin
  -> material-generation-fallback creates jobs
  -> generated-image-provider-packet creates provider jobs
  -> image-agent-prompt-handoff creates executable image-agent prompts
  -> real image provider writes generated_provider_outputs.json
  -> generated-material-import validates provider outputs
  -> generated material maps as candidate evidence
  -> material_delta fresh rerun
  -> generated-material-review accepts/rejects candidates
  -> material_delta fresh rerun
  -> BUILD
```

## Command

For a no-material story request, use the bounded provider handoff wrapper first:

```powershell
python tools\story_first_provider_happy_path.py `
  --out RUN_DIR `
  --title "月光森林裡迷路的小兔子" `
  --style "日式可愛繪本風格" `
  --target-duration 60 `
  --json
```

Expected `pipeline_home.py` result is `mode=waiting`,
`cursor=generated_image_agent`, `next=call_image_generation_agent`. This is the
correct stop point when no image-capable provider has written files yet, but the
run now contains a concrete prompt packet an image-capable agent can execute.
Do not substitute `test_pil` or text-card placeholders for real generated art.

Default route for real work:

```powershell
python video_tools.py generated-image-provider-packet material_generation_fallback.json `
  --style-profile style_profile.json `
  --out-dir provider_packet `
  --providers codex_imagegen,gemini,antigravity

python video_tools.py image-agent-prompt-handoff provider_packet/generated_provider_packet.json `
  --out-dir provider_packet/image_agent_handoff
```

Then an image-capable agent/provider must generate every requested image and
write `generated_provider_outputs.json`. If no provider is available, stop with
`provider_unavailable`; do not create text-card placeholder images.

Test-only deterministic renderer:

```powershell
python video_tools.py generated-material-produce material_generation_fallback.json `
  --needs material_needs.json `
  --out-dir generated_materials `
  --renderer test_pil `
  --allow-test-renderer `
  --provider codex_imagegen
```

Externally generated provider files:

```powershell
python video_tools.py generated-material-import material_generation_fallback.json `
  --needs material_needs.json `
  --provider-outputs generated_provider_outputs.json `
  --style-profile style_profile.json `
  --out-dir generated_materials
```

Outputs:

- `generated_images/*.png`
- `generated_asset_requests.json`
- `generated_asset_outputs.json`
- `generated_asset_manifest.json`
- `generated_material_maps/*.map.json`
- `project_material_map.json`
- `generated_material_quality_review.json`
- `generated_material_production.json`

`test_pil` is an offline deterministic renderer for bounded flow tests only.
It proves artifact shape and candidate evidence. It is not final art, is not
delivery allowed, and must not be used to fill real story, recap, training, or
generated-material gaps. Without `--allow-test-renderer`, the CLI fails closed
and tells the agent to use provider packet/import instead.

Real provider handoff packet details:

```powershell
python video_tools.py generated-image-provider-packet material_generation_fallback.json `
  --style-profile style_profile.json `
  --out-dir provider_packet `
  --providers codex_imagegen,gemini,antigravity
```

This writes:

- `generated_provider_packet.json`
- `generated_provider_prompts.md`
- `generated_provider_outputs.template.json`
- `provider_outputs/` target directory

For final art, an agent must read the packet and call an actual
image-generation tool for every item. If using Codex imagegen, either pass the
explicit generated image files in packet order:

```powershell
python video_tools.py codex-imagegen-provider-fill provider_packet/generated_provider_packet.json `
  --image-files image_001.png image_002.png
```

or omit `--image-files` to use the newest session under
`~/.codex/generated_images`:

```powershell
python video_tools.py codex-imagegen-provider-fill provider_packet/generated_provider_packet.json
```

This copies readable generated images into the packet's deterministic
`target_file` paths and writes `generated_provider_outputs.json`. Then run
`generated-material-import`. Do not use `test_pil` for final art or quality
review beyond flow validation.

Prefer explicit provider output mapping for formal work. The newest session
fallback is allowed only for local smoke, not for formal route acceptance or
final generated-material evidence. If the provider output cannot be mapped by
`job_id -> file`, stop and ask for the mapping.
Canonical grep token: newest session fallback is allowed only for local smoke.

For real images, execute the same jobs through Gemini / Antigravity /
assistant_imagegen / Codex imagegen and write provider outputs like:

```json
{
  "items": [
    {
      "job_id": "gen_hero",
      "file": "provider/hero-a.png",
      "provider": "codex_imagegen",
      "style_anchors": ["watercolor", "soft ink line"],
      "character_anchors": ["lead apprentice", "amber lantern"]
    }
  ]
}
```

The import tool copies validated files into the generated-material output
directory and writes the standard manifest/map/review artifacts.

`generated_material_quality_review.json` must be read before promoting any
generated candidate. Each item carries a deterministic rubric:

- `story_fit`: prompt supports the declared story function and required visual
  labels.
- `style_consistency`: project style anchors and palette are present.
- `character_continuity`: declared character/prop anchors stay consistent.
- `camera_language`: prompt includes shot/angle/lens/composition language.
- `truth_boundary`: output remains clearly marked as generated, not real proof.
- `need_coverage`: the generated candidate maps back to the intended `need_id`
  as a candidate satisfies edge.

Any failed rubric dimension keeps the quality gate false. A passing rubric still
does not accept material; it only permits the candidate map to proceed to
explicit review.

Explicit review / promotion:

```powershell
python video_tools.py generated-material-review project_material_map.json `
  --needs material_needs.json `
  --verdict generated_material_review.json `
  --out reviewed_project_material_map.json
```

Review verdict:

```json
{
  "artifact_role": "generated_material_review",
  "version": 1,
  "reviewer": "director-agent",
  "at": "2026-06-19T00:00:00+08:00",
  "decisions": [
    {
      "asset_id": "generated_a",
      "scene_index": 0,
      "need_id": "nd_panel",
      "status": "accepted",
      "reason": "matches story beat and style anchors"
    }
  ]
}
```

Only explicit `accepted` decisions can make a generated candidate count as
coverage. `rejected` decisions remain visible but do not satisfy delta.

## Prompt Design Rules

Use the reference repo as inspiration, not dependency:

- `reference repo/ai-media-generator-main/references/concept-first-prompting.md`
- `reference repo/ai-media-generator-main/templates/storyboard.md`
- `reference repo/ai-media-generator-main/references/quality-control.md`

Condensed rules:

1. Concept first: every generated asset must serve one story function.
2. Storyboard second: split long needs into panels/shots with setup, turn, payoff.
3. Visual anchors: keep repeated style, palette, role, subject, and setting.
4. Camera language: include angle/scale/lens or composition terms.
5. Quality control: reject fake text/logo, warped hands, inconsistent character,
   unrelated subject, or anything that looks like fabricated documentary proof.

## Review Gates

Pass only if:

- prompt includes story function or clear concept hook
- visual_family / angle_scale / action_family are present
- negative_prompt blocks text/logo/watermark/fake proof where relevant
- generated material map has candidate satisfies edge
- quality review score is acceptable
- provider outputs match required `style_anchors` and `character_anchors` when
  a style profile declares them
- generated candidates are promoted only by explicit reviewer decisions with a
  non-empty reason

Fail or send back to generation if:

- prompt is generic (`nice image`, `beautiful training scene`)
- it could be mistaken for real footage
- it lacks camera/shot language
- it does not match the need_id purpose
- it creates fake official evidence
- the provider output is missing, unreadable, undersupplied for `panel_count`,
  or mismatches the declared style/character anchors
- the review target is not a generated candidate, references unknown need/asset,
  lacks reviewer/reason, or uses any status other than accepted/rejected

## Practical Use

Good targets:

- comic/photo story panels
- symbolic memory inserts
- chapter-card backgrounds
- object bridges
- generic spaces with no signage
- non-identifying reenactment hands/details

Bad targets:

- real teacher/director speech
- real trainee reaction proof
- official certificate/logo/name badge
- actual event timeline proof
- anything where the audience must trust it happened

## Storyboard Panel-Locked Mode

Use `storyboard_panel_locked=true` when the generated material is a comic,
picture-book, storyboard, or narrated panel sequence where each image is a
specific story beat.

In this mode:

- one panel maps to one intended story beat or narration segment;
- do not auto-fill a long narration segment with other panels from the same
  need just because they are accepted material;
- if narration is longer than the panel's default duration, extend the panel's
  duration or its Ken Burns treatment;
- if one panel cannot carry the narration, request or generate more panels
  before BUILD;
- subtitles, voiceover, and panel order must stay aligned.

Use normal BUILD auto-fill only for MV/event recap material where multiple
accepted shots from the same need are interchangeable enough to cover duration.

Practical rule:

```text
comic/storybook/panel narration -> panel-locked, stretch panel or generate more
event MV/recap montage           -> auto-fill accepted shots is allowed
```
