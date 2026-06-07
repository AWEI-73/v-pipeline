# Video Autopilot Tool Integration Spec

Updated: 2026-06-07
Status: approved for implementation
Source reference: `https://github.com/Hao0321/video-autopilot-kit`
License: MIT; retain attribution for copied or substantially derived code.

## Purpose

Selectively integrate useful editing and verification capabilities inspired by
`video-autopilot-kit` without adopting its project architecture or making
CapCut/Computer Use a required runtime dependency.

The integration must strengthen the existing canonical flow:

```text
segment_contract.json
-> Node Registry / Runtime
-> BUILD artifacts
-> Node 11 Editor Review
-> Node 13 Render Candidate
-> Node 12 Verify
-> Node 14 Revision Route
```

This project remains the orchestration and artifact-contract owner. The external
repository is a tool and technique reference only.

## Source Boundary

Allowed:

- Reimplement generic algorithms and interfaces.
- Adapt MIT-licensed code while retaining attribution.
- Compare behavior against the external repository.
- Keep a separately cloned copy outside this repository for reference.

Not allowed:

- Copy author-specific keyword maps, paths, profiles, or channel assumptions.
- Make the external repository a runtime submodule or required dependency.
- Make CapCut or Computer Use mandatory for the canonical MVP.
- Write CapCut-specific fields into `segment_contract.json`.
- Let a GUI automation result bypass Node 12 verification.

If code is copied or substantially derived, add a concise source attribution in
the module header and preserve the MIT notice in `THIRD_PARTY_NOTICES.md`.

## Integration Priorities

### P1: Verification Tool Pack

Status: implement first.

Goal:
Improve editing quality with deterministic evidence and low-cost visual review.

Capabilities:

1. Keyframe grid/contact sheet generation.
2. B-roll ratio and repeated-source audit.
3. Timeline invariants.
4. Caption gap/overlap audit.
5. Narrative-to-visual alignment evidence.

Node ownership:

| Capability | Node | Skill | Runner |
|---|---|---|---|
| Timeline invariants | 11 Editor Review | `editor_review` | deterministic Python |
| B-roll/repetition audit | 11 Editor Review | `editor_review` / `curator` | deterministic Python |
| Caption timing audit | 11 Editor Review and 12 Verify | `subtitle-director` / `verify` | deterministic Python |
| Keyframe grid | 12 Verify | `verify` / `content_qa` | ffmpeg/ffprobe |
| Visual alignment review | 12 Verify | `content_qa` | configured VLM |

Required artifacts:

```text
timeline_invariants.json
broll_audit.json
caption_audit.json
keyframe_grid.jpg
visual_audit.json
```

These artifacts must be indexed by `artifact_manifest.json` and surfaced by the
dashboard. They are VERIFY evidence, not SPEC truth.

### P2: Creator Profile

Status: implement after P1 is accepted.

Goal:
Store stable creator/channel preferences separately from a single-project brief.

Artifact:

```text
creator_profile.json
```

Suggested fields:

```json
{
  "profile_version": 1,
  "brand": {"name": "", "colors": [], "fonts": [], "logo": null},
  "platform_defaults": {
    "platform": "youtube",
    "aspect_ratio": "16:9",
    "target_length": null
  },
  "subtitle_defaults": {"style": null, "max_chars_per_line": null},
  "editing_defaults": {
    "render_profile": "no_effects",
    "broll_ratio_target": null,
    "max_source_repeats": null
  },
  "audio_defaults": {"music_style": null, "ducking": true},
  "outro_defaults": {}
}
```

Rules:

- Node 0-1 may use this artifact as interactive defaults.
- `brief.json` always overrides creator-profile defaults.
- `segment_contract.json` remains project-specific.
- Runtime must record which defaults were applied.

### P3: Optional CapCut Draft Backend

Status: defer until P1 and P2 are stable.

Goal:
Provide an optional Node 13 Render Candidate backend for richer text, subtitle,
template, and manual finishing workflows.

Policy:

```json
{
  "render_backend": "ffmpeg | capcut_draft | remotion | html_playwright",
  "requires_human_or_computer_use": false
}
```

Required artifacts:

```text
capcut_draft_manifest.json
capcut_export_manifest.json
```

Rules:

- CapCut draft generation may be automated.
- GUI operation/export must be explicitly marked as a human/Computer Use gate.
- CapCut export is always a Render Candidate, never an automatically accepted final.
- Node 12 Verify must run on the exported candidate.
- ffmpeg remains the canonical unattended MVP backend.

## P1 Artifact Contracts

### `timeline_invariants.json`

```json
{
  "artifact_role": "timeline_invariants",
  "version": 1,
  "pass": true,
  "checks": [{
    "name": "clip_trace_present",
    "status": "pass | warn | fail",
    "affected_segments": [],
    "details": ""
  }],
  "next_action": null
}
```

Minimum checks:

- Every timeline item has source trace.
- Invalid negative duration is rejected.
- Unintended track overlap is reported.
- Timeline duration is compatible with the brief/contract.
- Required/must-include segments remain represented.

### `broll_audit.json`

```json
{
  "artifact_role": "broll_audit",
  "version": 1,
  "pass": true,
  "metrics": {
    "broll_ratio": 0.0,
    "unique_source_ratio": 0.0,
    "max_source_repeats": 0
  },
  "findings": [],
  "next_action": null
}
```

Rules must be parameterized through `build_profile.json`, creator profile, or
brief. Do not hardcode one creator's preferred ratio.

### `caption_audit.json`

```json
{
  "artifact_role": "caption_audit",
  "version": 1,
  "pass": true,
  "metrics": {"gap_count": 0, "overlap_count": 0, "too_fast_count": 0},
  "findings": [],
  "next_action": null
}
```

The audit must distinguish intended no-caption intervals, subtitles/narrative,
and labels/name supers that are not subtitles.

### `keyframe_grid.jpg` and `visual_audit.json`

Keyframe grid rules:

- Generate a stable, deterministic sample grid from the Render Candidate.
- Record timestamps and layout metadata in `visual_audit.json`.
- Permit mechanical-only mode without a VLM.
- If VLM review runs, use configured model routing and record model/provider.
- VLM findings are review evidence and cannot invent SPEC requirements.

```json
{
  "artifact_role": "visual_audit",
  "version": 1,
  "grid": "keyframe_grid.jpg",
  "samples": [{"timestamp_sec": 0.0, "cell": 1}],
  "mechanical_findings": [],
  "model_review": {
    "provider": "ollama",
    "model": "qwen3-vl:4b-instruct",
    "findings": []
  },
  "next_action": null
}
```

## Runtime and Route Behavior

P1 tools must not create a second orchestration system.

```text
Node 11 produces deterministic audit artifacts
-> blocking findings route to Node 9/10 or human review
-> Node 13 produces Render Candidate
-> Node 12 generates keyframe grid and formal VERIFY artifacts
-> failures route through existing next_action/fix_class taxonomy
```

Suggested routing:

| Finding | `fix_class` | Route |
|---|---|---|
| Missing trace / bad timeline overlap | `spec` or `human` | Node 10 / editor review |
| Excessive repeated source | `material` | curator / Node 2 or Node 8 |
| Caption timing issue | `spec` | subtitle/editor correction |
| Visual mismatch | `spec` or `material` | director or curator |
| Mechanical render defect | `human` or build-specific | Node 13 rerender |

`runtime_orchestrator.py` should consume artifacts and route results; it should
not contain the audit algorithms.

## Proposed Module Boundaries

Create focused modules under `video_pipeline_core/`:

```text
timeline_invariants.py
broll_audit.py
caption_audit.py
keyframe_grid.py
visual_audit.py
creator_profile.py              # P2
capcut_backend.py               # P3, deferred
```

Expose stable CLI shims through `video_tools.py` only when needed:

```text
timeline-audit
broll-audit
caption-audit
keyframe-grid
visual-audit
creator-profile                 # P2
capcut-draft                    # P3
```

Do not add another root-level god module.

## Build Profile Additions

P1 may extend `build_profile.json` with optional policy only:

```json
{
  "verification_tools": {
    "timeline_invariants": true,
    "broll_audit": true,
    "caption_audit": true,
    "keyframe_grid": true,
    "visual_audit": true
  },
  "broll_policy": {"target_ratio": null, "max_source_repeats": null},
  "keyframe_grid": {"sample_count": 12, "columns": 4}
}
```

Defaults must remain compatible with current projects.

## Implementation Sequence

### Milestone P1-A: Deterministic Audits

Build:

- Implement timeline invariants.
- Implement B-roll/repeated-source audit.
- Implement caption timing audit.
- Write manifest integration.
- Surface results in dashboard Node 11/12.

Verify:

- Unit test each audit with pass/warn/fail fixtures.
- Confirm existing coffee project can run without enabling new tools.
- Confirm enabled audits produce stable JSON artifacts.

### Milestone P1-B: Keyframe Grid and Visual Audit

Build:

- Implement deterministic ffmpeg keyframe grid generation.
- Write sample timestamps into `visual_audit.json`.
- Add optional configured VLM review.
- Integrate with Node 12.

Verify:

- Grid image exists and is non-empty.
- Timestamp count matches cells.
- Mechanical-only mode works without Ollama.
- Qwen 4B route is optional and produces model lineage when enabled.

### Milestone P2: Creator Profile

Build and verify only after P1 acceptance.

### Milestone P3: CapCut Backend

Build only after a separate design review confirms installed CapCut version,
supported draft format, GUI/Computer Use responsibility, failure recovery, and
export verification.

## Acceptance Criteria

P1 is complete only when:

```text
all new artifacts have schemas and manifest entries
Node 11/12 surface findings and route actions
no existing no-effects run changes behavior when tools are disabled
mechanical-only Verify works without Ollama
full Windows test suite passes
one real Render Candidate produces a usable keyframe grid and audit bundle
```

P2 and P3 are not required for P1 completion.

## Verification Commands

```powershell
cd C:\Users\user\Desktop\video_pipeline
python -m unittest tests.test_timeline_invariants tests.test_broll_audit tests.test_caption_audit -v
python -m unittest tests.test_keyframe_grid tests.test_visual_audit -v
python -m unittest tests.test_dashboard_state tests.test_runtime -v
python -m unittest discover -s tests -p "test_*.py"
git diff --check
```

Manual verification:

```powershell
python video_tools.py keyframe-grid <render-candidate.mp4> --out <run>\keyframe_grid.jpg
python runtime.py status --project coffee
```

## Claude Code Handoff

Read in this order:

```text
HANDOFF_CURRENT.md
ROADMAP.md
docs/build-tool-runner-spec.md
docs/video-autopilot-tool-integration-spec.md
docs/superpowers/plans/2026-06-07-video-autopilot-tool-integration.md
graphify-out/GRAPH_REPORT.md
video_pipeline_core/node_registry.py
video_pipeline_core/runtime_orchestrator.py
video_pipeline_core/dashboard_state.py
```

Implementation mode:

```text
brownfield small-step
TDD
P1 only
one independently verified audit module per commit
```

Do not:

```text
implement P2/P3 while P1 is unfinished
clone external source inside the production package
make CapCut mandatory
expand segment_contract.json with provider/backend details
change existing Runtime behavior when verification tools are disabled
claim completion without a real keyframe-grid smoke test
```

