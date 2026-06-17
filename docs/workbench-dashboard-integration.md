# Workbench / Dashboard Integration

This document defines the current frontend/backend boundary for Hermes Video
Pipeline. It is intentionally operational: future agents should use it to decide
where a change belongs before editing code.

## Surfaces

### Dashboard

Dashboard is the read-oriented review surface.

It should show:

- project/run status;
- node and gate status;
- material-map and verification findings;
- whether Workbench draft artifacts exist;
- links or commands that open Workbench.

Dashboard should not author timeline edits. If a user wants to change timing,
source windows, subtitles, audio cues, or effect cues, route them to Workbench.

### Workbench

Workbench is the interactive preview and draft-patch surface.

It can:

- preview the current material composition, not only the final rendered MP4;
- trim approved source windows within safe limits;
- replace a selected clip with a material-map scene;
- edit subtitle draft timing/text;
- add audio cue draft markers;
- add effect intent draft markers;
- save draft patch artifacts;
- create an agent/backend handoff package.

Workbench must not overwrite canonical artifacts.

## Integration Flow

```text
SPEC / contract
-> material map / needs / delta gates
-> BUILD timeline / final render
-> Dashboard review
-> Workbench draft edits
-> timeline_patch.json
   + patched_draft_timeline.json
   + workbench_contract_patch.json
   + workbench_handoff.json
-> Agent review
-> backend rerender / contract revision / reject patch
```

Hard rule:

```text
Workbench can preview and draft. Backend remains responsible for official render.
```

## Artifact Ownership

### Canonical Artifacts

These are backend-owned and must not be overwritten by Workbench:

- `final.mp4`
- canonical `timeline.json`
- canonical contract files
- material-map source files
- delivery/verification gate artifacts

### Workbench Draft Artifacts

Workbench may write these files under the active artifact root:

- `preview_timeline.json`
- `timeline_patch.json`
- `patched_draft_timeline.json`
- `workbench_contract_patch.json`
- `workbench_handoff.json`
- subtitle/audio/effect draft patch files
- optional workbench export files that are explicitly non-canonical

Draft artifacts are evidence for a later agent/backend decision. They are not
automatic truth.

## Backend Consumption

The backend or agent should inspect draft artifacts before official rerender.

Expected decision routes:

- accept patch and rerender from backend;
- convert patch into a contract revision;
- ask for more material;
- reject patch because it violates source windows, material-map identity, or
  current contract constraints;
- route future effect-heavy work to Node 14 / effects workflow.

## Local Commands

Start Workbench against the current real 67th fuller replay artifact:

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
node --check dashboard\workbench_native\workbench_core.js
node tests\workbench_core_smoke.js
python -m unittest tests.test_preview_timeline tests.test_workbench_server tests.test_timeline_patch -q
```

Full regression:

```powershell
python -m unittest discover -s tests -q
```

## Workbench Layout Acceptance

- Left material panel scrolls independently.
- Center preview remains centered for portrait and landscape media.
- Inspector stays usable.
- Timeline area has horizontal access when clips exceed the viewport.
- Track stack remains reachable when lanes overflow vertically.
- No default browser selection border appears around preview media.
- Play controls remain visible.
- Text, audio, and effect lanes are visible as lanes even when empty.

## Safety Rules

- Do not add Dashboard editing behavior.
- Do not let Workbench write canonical artifacts.
- Do not add a new frontend framework for this cleanup.
- Do not make Workbench the official renderer.
- Do not silently translate draft patches into source contract changes.
- Do not bypass M6 material gates or delivery gates.

## Deferred Work

- Full browser NLE behavior.
- Remotion-like final renderer.
- Complex multi-track audio graph.
- Heavy motion graphics / Node 14 effects authoring.
- Material library folder-management workflow.
- Dashboard visual redesign beyond integration clarity.

