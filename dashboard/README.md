# Dashboard And Workbench

Hermes currently has two frontend surfaces. They are connected, but they do not
have the same responsibility.

## Surfaces

### Dashboard

Dashboard is for review and status:

- pipeline run state;
- node/gate status;
- material-map and verification findings;
- backend artifacts;
- Workbench handoff visibility.

Dashboard should stay read-oriented. It should not become a timeline editor.

### Workbench

Workbench is for interactive draft edits:

- preview the current material composition;
- inspect and trim clips;
- replace clips from the material map;
- edit subtitle drafts;
- add audio cue drafts;
- add effect intent drafts;
- save draft patch/handoff artifacts.

Official rendering still belongs to the backend ffmpeg pipeline.

## Artifact Ownership

Workbench may write draft artifacts such as:

- `preview_timeline.json`
- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- `workbench_handoff.json`

Workbench must not overwrite canonical artifacts such as:

- `final.mp4`
- canonical `timeline.json`
- material-map source files
- source contracts

## Local Run Commands

Start Workbench:

```powershell
python tools\workbench_server.py --artifact-root .tmp\srp_real67_fuller_replay --port 8770
```

Open:

```text
http://localhost:8770/workbench
```

Focused checks:

```powershell
node --check dashboard\workbench_native\workbench.js
node --check dashboard\workbench_native\workbench_api.js
node --check dashboard\workbench_native\workbench_core.js
node tests\workbench_api_smoke.js
node tests\workbench_core_smoke.js
python tools\workbench_frontend_smoke.py --artifact-root .tmp\srp_real67_fuller_replay
python -m unittest tests.test_preview_timeline tests.test_workbench_server tests.test_timeline_patch -q
python -m unittest tests.test_workbench_frontend_smoke -q
```

## Frontend Module Boundary

- `workbench_core.js`: pure deterministic timeline/editing logic.
- `workbench_api.js`: Workbench HTTP API client.
- `workbench.js`: DOM controller, browser preview, and user interaction.

Keep canonical artifact rules in the Python server/backend. Browser modules
should produce draft patches and handoff artifacts, not official pipeline truth.

## Workbench Layout Acceptance

- Left material panel scrolls independently.
- Center preview remains centered for portrait and landscape media.
- Inspector stays usable.
- Timeline area has horizontal access when clips exceed the viewport.
- Track stack remains reachable when lanes overflow vertically.
- Play controls remain visible.
- Text, audio, and effect lanes are visible as lanes even when empty.

## Safety Rules

- Dashboard reads; Workbench drafts.
- Workbench draft artifacts require agent/backend review before official rerender.
- No frontend path should silently rewrite canonical pipeline truth.
- No browser export should be treated as the official final video.

## Known Deferred Work

- Material-library folder organization.
- Richer visual design polish.
- Heavy effects authoring.
- Full multi-track NLE behavior.
- Full preview/output visual parity.
