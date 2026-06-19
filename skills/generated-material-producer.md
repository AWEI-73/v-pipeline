---
name: generated-material-producer
description: Use when MGF1 material_generation_fallback.json must be executed into generated image/video assets, provider outputs, material-map candidate evidence, and quality review. Use for generated-material fallback, Gemini/Antigravity/imagegen provider handoff, or offline test renderer validation.
---

# Generated Material Producer

This skill turns planned generated-material jobs into files and reviewable
material-map evidence.

It is downstream of `skills/material-generation-fallback.md`.

## Core Boundary

Generated assets are never real footage.

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
  -> generated-material-produce creates provider outputs
  -> generated material maps as candidate evidence
  -> material_delta fresh rerun
  -> generated-material-review accepts/rejects candidates
  -> material_delta fresh rerun
  -> BUILD
```

## Command

Offline deterministic renderer:

```powershell
python video_tools.py generated-material-produce material_generation_fallback.json `
  --needs material_needs.json `
  --out-dir generated_materials `
  --renderer test_pil `
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

`test_pil` is an offline deterministic renderer for flow tests. It proves
artifact shape and candidate evidence. It is not final art.

Real provider handoff packet:

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
