# Hermes Video Pipeline

Hermes is an agent-first video pipeline. Agents enter through route documents,
produce explicit JSON artifacts, build videos through deterministic tools, and
resume from `state.json.next_action` instead of improvising one-off edits.

## Quick Start

1. Install Windows prerequisites: Miniconda Python, ffmpeg, and Node.js.
2. Install Python dependencies: `& "$env:USERPROFILE\miniconda3\python.exe" -m pip install -r requirements.txt`.
3. Create `.env` from `.env.example` and fill local keys.
4. Verify: `& "$env:USERPROFILE\miniconda3\python.exe" tools/preflight.py --strict`.
5. For agents, read `docs/START_HERE_VIDEO_PIPELINE.md` before acting.

Detailed setup and first-run notes live in
`docs/setup/setup-and-first-run.md`.

## Verification

Run these from the repository root with miniconda Python:

```powershell
& "$env:USERPROFILE\miniconda3\python.exe" tools/preflight.py --strict
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py e2e-smoke --case stock_story
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py e2e-smoke --case single_long_highlight
& "$env:USERPROFILE\miniconda3\python.exe" video_tools.py registry-audit
& "$env:USERPROFILE\miniconda3\python.exe" -m unittest discover -s tests
```

The full suite is the commit gate for construction work.

## Agent Entrypoint

Agents must start with `docs/START_HERE_VIDEO_PIPELINE.md`. Rule Zero there is
the working boundary: do not bypass the route with hand-run ffmpeg,
ad hoc `video_tools.py` commands, or manual material stitching.

For a first video request, point the coding agent at
`docs/START_HERE_VIDEO_PIPELINE.md` and ask for the video. The agent should
route the request through `skills/video-pipeline.md`, `runtime.py`, and the
current run's `state.json.next_action`.

## Storybook Placeholder

The storybook route is present as a pipeline shape, but demo videos, model cost
notes, and owner-approved examples are still pending. Until those are filled,
storybook work should follow the same route discipline as every other video:
Stage 0 intent, material/generation handoff, explicit review, build, and verify.

## Repository Map

- `video_pipeline_core/` - implementation modules.
- `tools/` - standalone operational scripts.
- `video_tools.py` - legacy-compatible command surface.
- `runtime.py` - unified resume/status/rerun driver.
- `skills/` - agent role contracts.
- `docs/START_HERE_VIDEO_PIPELINE.md` - canonical agent/operator entrypoint.
- `docs/INDEX.md` - broader documentation map.
- `docs/setup/` - bootstrap, first-run, and distribution notes.

## Distribution

Release contents and exclusions are documented in
`docs/setup/distribution-manifest.md`. Packaging mechanism and license selection
are owner decisions.
