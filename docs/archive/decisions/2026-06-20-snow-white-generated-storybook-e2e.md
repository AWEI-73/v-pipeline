# Decision: Generated Storybook Route Is Viable For Template Expansion

Date: 2026-06-20
Status: verified
Scope: story-soul-blueprint / generated-material-producer / material-map / BUILD
Superpowers phase: verify

## SPEC

Requirement:

Use a fully generated, child-safe comic/storybook case to test whether Hermes Video Pipeline can run a longer narrative route from story intent through generated materials, material-map coverage, BUILD, subtitles, and review artifacts. The concrete test case was a Snow White picture-book style story for children, longer than the earlier Cinderella smoke.

Why:

The pipeline is now technically strong enough that the next risk is not only "can it render?" but "can it support reusable story routes?" We need evidence before solidifying generic flows and later template routes. This report records whether generated storybook videos are a valid route, whether this is overkill, and where the real gaps are.

Direction:

Treat generated storybook video as a first-class route:

```text
story brief
  -> story soul / screenplay beats
  -> material_needs
  -> generation fallback
  -> provider packet
  -> generated images as material assets
  -> generated material review
  -> material delta
  -> contract BUILD
  -> subtitles / contact sheet / review report
```

Non-goals:

- Do not claim this is a production-quality children's story template yet.
- Do not make the generated images bypass material-map review.
- Do not hard-code Snow White or Cinderella as canonical templates.
- Do not replace backend ffmpeg BUILD with frontend preview/export.
- Do not treat generated images as final truth before explicit review and fresh delta rerun.

## DO

Files / modules:

- `skills/story-soul-blueprint.md`: upstream story intent and screenplay beat direction.
- `skills/material-generation-fallback.md`: missing-material route into generation jobs.
- `skills/generated-material-producer.md`: provider packet / generated asset import / review boundary.
- `video_tools.py generated-image-provider-packet`: provider handoff artifact.
- `video_tools.py generated-material-import`: generated files into material-map candidates.
- `video_tools.py generated-material-review`: explicit promotion from candidates to accepted material evidence.
- `video_tools.py material-delta`: fresh coverage check.
- `video_tools.py contract-run`: official backend BUILD.

Function-level plan:

The route should remain pipeline-native. Generated images are just another material source after import:

1. Build `material_needs.json` and `material_generation_fallback.json`.
2. Build `generated_provider_packet.json`.
3. Image-capable agent writes concrete files to provider targets.
4. Import generated files into candidate material maps.
5. Review and accept/reject generated material evidence.
6. Rerun material delta.
7. BUILD with `contract-run`.
8. Produce `final.mp4`, `subtitles.srt`, `timeline_build.json`, contact sheet, and review report.

Data / interface changes:

No code or schema change was required for the Snow White case. The important interface rule is procedural:

- never infer generated asset order from "latest N images" when provider calls can be rejected or retried;
- use explicit provider output mapping from job id to target file;
- generated files must enter the material-map route before BUILD.

Migration / compatibility:

This route is compatible with the existing material-map lifecycle. It does not require a new canonical schema. It is suitable for later route templates such as:

- short fairy-tale storybook;
- moral education story;
- picture-book narration;
- comic recap;
- generated explainer panels.

## VERIFY

Pre-checks:

- Image generation was enabled and produced local files.
- Provider packet existed for 18 Snow White material jobs.
- Generated material fallback and needs were already available in `.tmp/snow_white_storybook_e2e`.

Tests:

Manual E2E run, not committed as code:

- `generated-image-provider-packet`: 18 jobs / 18 images.
- `generated-material-import`: `ok=true`, `image_count=18`, `map_count=18`, quality gate passed.
- `generated-material-review`: 18 accepted / 0 rejected.
- `material-delta`: `covered=18`, `thin=0`, `missing=0`, `excess=0`, `ready_for_build=true`.
- `contract-run`: `render_ok=true`, `verify_ok=true`, `workflow_ok=true`.
- Final duration: `270.134s`.
- Final clips: `18`.
- Unique generated sources: `18`.
- Verify score: `88.7`, pass.

Artifacts:

- `.tmp/snow_white_storybook_e2e/final_snow_white_zh.mp4`
- `.tmp/snow_white_storybook_e2e/contact_sheet.jpg`
- `.tmp/snow_white_storybook_e2e/REVIEW_REPORT.md`
- `.tmp/snow_white_storybook_e2e/subtitles.srt`
- `.tmp/snow_white_storybook_e2e/timeline_build.json`

Manual checks:

- Contact sheet review showed the final corrected sequence:
  castle Snow White -> queen mirror -> forest escape -> fear in forest -> cottage -> cleaning -> miners return -> shared meal -> happy forest daily life -> disguised queen -> warning -> apple -> sleep -> watch -> prince arrival -> waking -> farewell -> hopeful ending.
- Chinese subtitles were verified after correcting the shell encoding issue.
- Generated visuals were child-safe and mostly coherent in watercolor/comic style.

Regression risks:

- Provider order risk: rejected image generations can shift "latest N files". This caused the first Snow White render to map N01 incorrectly. The corrected route must rely on provider outputs, not filesystem recency.
- Encoding risk: writing Chinese text through PowerShell literals can turn subtitles into `????`. Use UTF-8 artifacts and verify SRT text before accepting a run.
- Template-pacing risk: one image per 15 seconds is stable for storybook review, but can feel static. Production templates need richer pacing rules.
- Camera-language risk: generated-material review repeatedly flagged `camera_language_weak`; the flow works, but the upstream prompt/shot plan needs stronger director language.

## Decision Notes

Accepted because:

The route proved the core contract works for generated picture-book videos:

- missing materials can be generated;
- generated assets can become material-map candidates;
- explicit review can promote them;
- delta can prove coverage;
- BUILD can produce a longer Chinese-subtitled story video.

This is not "憭扳?撠" for the project direction. It may look heavy for a single simple fairy tale, but the point of Hermes is not one-off rendering. The value appears when the same lifecycle supports many routes with predictable gates:

- user gives story intent;
- agent asks for missing creative/material information;
- generated materials are traceable;
- review catches mismatches;
- BUILD is reproducible;
- Workbench can later adjust without overwriting truth.

Tradeoffs:

- The route is heavier than a simple image slideshow script.
- The extra weight buys material truth, reviewability, reruns, subtitles, and future template reuse.
- For a throwaway 30-second slideshow, this pipeline is overkill.
- For reusable children's story series, training stories, course explainers, or branded generated videos, it is appropriate.

Open questions:

- How much of the story-soul layer should become interactive skill behavior versus reusable templates?
- Should storybook routes default to 10-15 second panels, or should they require per-beat pacing?
- How should image prompt packets enforce stronger camera language and character consistency?
- When should a route request more panels instead of longer panel duration?
- Should narration audio/TTS become mandatory for storybook routes, or remain optional with subtitles first?

## Route Solidification Guidance

Current conclusion:

Start with a generic generated-story route, then layer templates on top.

Recommended route hierarchy:

```text
Universal Video Flow
  -> Story / Explainer / Event / Training route
    -> Storybook generated-panel route
      -> fairy tale template
      -> moral lesson template
      -> comic recap template
```

Generic route rules:

- Generated assets are not special; after import they are material assets.
- Generated assets must be reviewed before accepted.
- Fresh material delta must run after review.
- BUILD should use `storyboard_panel_locked=true` for picture-book/comic routes.
- Long narration should either lengthen panels intentionally or request additional panels; it should not auto-fill unrelated panels.

Template-route requirements:

- story world / character bible;
- narrative device;
- beat list with emotional progression;
- director shot plan with camera language;
- material needs with count and visual family;
- generation prompt pack with style and character anchors;
- review checklist for story, style, safety, and subtitle readability.

## Git / Retrieval

Related files:

- `docs/archive/decisions/2026-06-19-story-soul-blueprint.md`
- `docs/archive/decisions/2026-06-19-storyboard-panel-lock.md`
- `docs/archive/decisions/2026-06-18-material-generation-fallback.md`
- `docs/archive/decisions/2026-06-18-generated-material-producer.md`
- `skills/story-soul-blueprint.md`
- `skills/material-generation-fallback.md`
- `skills/generated-material-producer.md`
- `video_tools.py`

Related commits:

- None for this report at creation time. The Snow White run was an artifact-only `.tmp` validation and did not modify production code.

Graphify anchors:

- generated storybook route
- material generation fallback
- provider packet
- generated material review
- material delta
- story template route
- storyboard panel lock

Search tags:

`decision-log`, `spec-do-verify`, `generated-storybook`, `snow-white-e2e`, `material-generation-fallback`, `story-template-route`, `video-pipeline`
