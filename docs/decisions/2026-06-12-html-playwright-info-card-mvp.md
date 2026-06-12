# Decision: Use Playwright frame capture for the first HTML motion-graphics recipe

Date: 2026-06-12
Status: verified
Scope: video_pipeline_core/motion_graphics.py / Node 14
Superpowers phase: verify

## SPEC

Requirement:

Complete roadmap E4 with one real `html_playwright` recipe that travels from
HTML through frame capture and alpha overlay into the final video.

Why:

`ffmpeg_libass` covers text motion but cannot provide the richer HTML/CSS/JS
vocabulary needed for future infographics and counters.

Direction:

Use a deterministic 1920x1080 HTML info card, Python Playwright with an
installed system browser, transparent PNG frame capture, qtrle alpha MOV
encoding, and ffmpeg overlay at the declared timeline start.

Non-goals:

Do not add Remotion, Blender, browser installation automation, dynamic charts,
or generalized recipe authoring in this phase.

## DO

Files / modules:

- `video_pipeline_core/motion_graphics.py`: HTML writer, Playwright renderer,
  alpha compositor, and safe-backend dispatcher.
- `video_pipeline_core/contract_adapter.py`: dispatch both safe motion-graphics
  backends.
- `tests/test_motion_graphics.py`: backend, renderer, compositor, dispatcher,
  and readable-style contracts.

Function-level plan:

- `_write_html_overlay`: emit deterministic transparent info-card HTML.
- `_render_html_playwright_overlay`: capture declared-duration frames and encode
  an alpha overlay.
- `composite_html_playwright_outputs`: place overlays at `start_sec`.
- `composite_motion_graphics_outputs`: run safe backends in stable order.

Data / interface changes:

The render manifest records `html_path`, `frames_dir`, `frame_count`, `fps`,
overlay path, and final `composited` status.

Migration / compatibility:

Existing `ffmpeg_libass` behavior remains first in the dispatcher. Heavy
backends remain pending and policy-gated.

## VERIFY

Pre-checks:

Python Playwright, system Chrome, and ffmpeg were available. Node Playwright was
not required.

Tests:

`python -m unittest tests.test_motion_graphics -v`

Manual checks:

Real smoke:
`C:\Users\user\Desktop\video_project\skill-smoke\runs\20260612-e4-html-playwright-v2`

The smoke captured 30 transparent frames, encoded an alpha MOV, composited the
final video, and produced a contact sheet plus a 1080p midpoint image. Visual
review confirmed readable lower-third placement and visible fade motion.

Regression risks:

Browser availability, Playwright API compatibility, transparent screenshot
behavior, ffmpeg alpha codec support, and backend ordering.

## Decision Notes

Accepted because:

It proves a second real rendering backend using dependencies already present on
the workstation and keeps the output auditable through intermediate artifacts.

Tradeoffs:

Frame capture is slower and more storage-intensive than direct video rendering.
The MVP intentionally uses a fixed 1920x1080 canvas and one recipe.

Open questions:

Future phases should decide whether to add reusable HTML recipe templates,
counter interpolation, and browser/runtime provisioning.

## Git / Retrieval

Related files:

- `video_pipeline_core/motion_graphics.py`
- `video_pipeline_core/contract_adapter.py`
- `tests/test_motion_graphics.py`
- `roadmap.md`

Related commits:

None yet.

Graphify anchors:

Node 14, motion graphics, html_playwright, info_card, Playwright frame capture,
alpha overlay

Search tags:

decision-log, spec-do-verify, video-pipeline, E4, html-playwright, motion-graphics
