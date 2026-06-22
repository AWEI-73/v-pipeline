# Hermes Video Pipeline End-to-End Line

Date: 2026-06-21
Status: canonical narrative line / operator quick map

This document strings the whole pipeline into one readable line. It does not
replace `docs/video-pipeline-operating-map.md`; it is the short route an agent
should hold in mind before opening the detailed stage manual.

## One Sentence

Hermes turns a user intent into a verified video by first deciding input state
and entry path, then producing a story/design contract, proving material truth,
planning and rendering with current evidence, verifying the output, and routing
any fixes through draft or brownfield paths without overwriting canonical truth.

## Full Line

```text
0. Video Intent Planner
   -> decide video type, audience, input_state, entry_path, and follow-up gaps

1. Story / Structure Planner
   -> create the right upstream plan:
      story soul, teaching structure, event recap, memory film, brand short

2. Director Shot Plan
   -> convert intent into beats, shot purposes, subtitles, audio, effects,
      material_needs, and segment contract

3. Material Truth
   -> inspect existing media OR generate/import missing candidate media
   -> create project_material_map and satisfies edges

4. Coverage / Decision Gate
   -> compute material_delta
   -> build only when needs are covered or explicitly revised/waived

5. BUILD Planning
   -> rank windows, avoid bad ranges, apply visual diversity, story arc,
      opening, sequence recipes, subtitles, audio cues, and effect intent

6. Official Render
   -> render through backend ffmpeg / contract-run into canonical final.mp4

7. Verify / Reviewer Layer
   -> verify technical facts and run route-appropriate creative review

8. Workbench Draft Review
   -> inspect and patch draft timeline/material/effect markers without
      overwriting canonical timeline, map, or final

9. Brownfield Edit / Finishing
   -> apply bounded reviewed fixes: subtitles, audio, effects, Remotion adapter,
      small material replacement, or second-build handoff

10. Delivery
   -> ship final.mp4 only with verify evidence, review report, contact sheet,
      known limitations, and artifact manifest
```

## Stage 0 Entry Split

Always decide input state before story depth:

| Entry path | Meaning | First action | Generation policy |
|---|---|---|---|
| `material-first` | Real or partial footage/photos/material exist. | Run Material Map quick inventory. Let existing material constrain the story/design skeleton and reveal gaps. | Fallback only for diagrams, chapter cards, symbolic inserts, or missing non-proof visuals after delta. |
| `structure-first` | No usable material exists, but text, article, outline, script, story, or a developed idea exists. | Clarify story/design/teaching structure first, then derive material needs and generated/captured assets. | Allowed as planned candidate material, still must pass import/review/delta. |
| `needs-context` | The request is too vague to choose a handoff. | Ask focused questions about goal, audience, inputs, length, style, and text/material availability. | Do not generate or build yet. |

Legacy compatibility:

- `existing-material-first` maps to `material-first`.
- `story-first` maps to `structure-first`.
- hybrid is not a primary Stage 0 entry path.
- `hybrid` is not a primary Stage 0 entry path; partial material enters
  `material-first`, then material-delta decides generate, reshoot, shorten,
  rewrite, drop, or waive.
- `Intake` is the old Stage 0 label; use `Video Intent Planner` in new docs and prompts.

## Normal Route

```text
Video Intent Planner
  -> Story / Structure Planner
  -> Director Shot Plan
  -> Material Truth
  -> Coverage Gate
  -> BUILD Planning
  -> Official Render
  -> Verify
  -> Delivery
```

Use this when material and contract are already good enough and no draft edit is
needed.

## Existing-Material Route

```text
Video Intent Planner
  -> Material Map quick inventory
  -> story/design skeleton constrained by available media
  -> Director Shot Plan
  -> Material Map review / satisfies edges
  -> material_delta
  -> BUILD / Verify / Delivery
```

Do not choose generated storybook only because the visual style is comic,
illustrated, or picture-book-like. If material exists, inspect it first.

## Generated-Material Route

```text
Video Intent Planner
  -> Story / Structure Planner
  -> material_needs
  -> initial project_material_map.json
  -> initial material_delta.json with ready_for_build=false
  -> material_generation_fallback.json
  -> generated-image-provider-packet
  -> explicit provider output mapping (job_id -> file)
  -> generated-material-import
  -> generated-material-review
  -> fresh material_delta
  -> BUILD / Verify / Delivery
```

Generated files are candidates until explicit review accepts them. Do not infer
formal route outputs from the newest generated-images folder.

## Workbench / Brownfield Return Loop

```text
Verify finding or human review
  -> Workbench draft patch OR Brownfield Edit request
  -> reviewed patch / effect / subtitle / audio / material replacement
  -> official rerender or non-canonical draft composite
  -> Verify again
  -> Delivery
```

Workbench is a review and draft-edit surface. Brownfield Edit is a bounded fix
route. Neither becomes canonical truth by itself.

## What Must Never Happen

- Do not render from stale material_delta or stale revision artifacts.
- Do not let generated media satisfy needs without import + review.
- Do not let Workbench overwrite canonical `timeline_build.json`,
  `project_material_map.json`, or `final.mp4`.
- Do not treat Remotion preview/draft effects as delivery without review.
- Do not claim success when promised duration or material quantity cannot be
  supported by accepted material.

## Where To Read Next

- Detailed stage/tool map: `docs/video-pipeline-operating-map.md`
- Stable stage definitions: `docs/canonical-video-pipeline-route.md`
- Upstream creative/story route: `docs/upstream-story-route.md`
- Material lifecycle: `docs/material-map-lifecycle.md`
- Reviewer roles: `docs/artifact-reviewer-map.md`
- Current roadmap: `roadmap.md`
