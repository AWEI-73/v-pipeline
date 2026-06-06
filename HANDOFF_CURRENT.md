# Current Handoff: Hermes Video Pipeline

Updated: 2026-06-06

This file is the clean resume anchor when `HANDOFF.md` contains older encoded
notes. Read this first, then `roadmap.md`,
`docs/windows-native-migration-spec.md`, `docs/build-tool-runner-spec.md`,
`README.md`, and `RUNBOOK.md`.

## Active Development Location

```text
Primary Windows source:
  C:\Users\user\Desktop\video_pipeline

Windows project/output root:
  C:\Users\user\Desktop\video_project

WSL reference source:
  \\wsl$\Ubuntu-24.04\home\lio730309\video_pipeline
```

Windows is the primary development target. WSL is a read-only behavioral
reference during migration unless the user explicitly requests a WSL change.
Do not develop both copies independently.

## Current Alignment

- Canonical SPEC entry: `segment_contract.json`.
- Legacy `script.json`: runtime payload only, not the public SPEC direction.
- Runtime package entry: implementation modules live in `video_pipeline_core/`.
- Root Python files: CLI/orchestrator shims (`video_pipeline.py`, `video_tools.py`, `route.py`).
- Content QA entry: `video_pipeline.py` calls `python3 -m video_pipeline_core.content_qa`.
- Error routing truth: `video_pipeline.py` aliases `video_pipeline_core.vt_core.FIX_TARGET`.
- Project outputs: external project/run folders; repo-local `.project/active.json` is only a relative pointer.
- Material folders: `materials/raw`, `materials/selected`, `materials/generated`, `materials/stock`.
- VLM policy: `qwen3-vl:4b-instruct` only for gate, content QA, and retry.
- Generated provider policy: Antigravity / assistant_imagegen / codex_imagegen preferred; ComfyUI is deprecated/disabled unless explicitly isolated.
- BUILD runner policy: tool choices live in `build_profile.json`; runner work must write explicit artifacts and manifest entries. See `docs/build-tool-runner-spec.md`.
- Migration policy: move from WSL to Windows in small verified steps. See `docs/windows-native-migration-spec.md`.

## Windows Migration State

```text
W0 source/output boundaries: completed
W1 cross-platform resolver: completed
W2 remove hardcoded Linux paths: completed
W3 replace Bash orchestration: completed
W4 external tool native smoke: completed
W5 canonical no-effects Windows E2E: completed
W6 route/dashboard monitoring: completed
W7 Windows Graphify rebuild: completed
```

Current Windows evidence:

```text
Python 3.10.16
video_tools.py --help: pass
Full test suite: 255 tests pass (100% success)
```

## Latest Graphify

Source-only graphify skill run, excluding output/media/archive folders:

```text
120 files · ~82,119 words
1188 nodes
1561 edges
122 communities
95% EXTRACTED / 5% INFERRED / 0% AMBIGUOUS
Import cycles: none
Edge diagnostic: no dangling / duplicate / endpoint-collapsed edges
```

God nodes still worth watching:

```text
ToolError
run()
pipeline()
_audio_duration()
run_tool()
compose_and_qa()
```

## Node To Skill To Artifact Spine

| Node | Layer | Skill | Primary Artifact |
|---|---|---|---|
| 0-1 | SPEC | `video-workflow`, `director`, `writer` | `brief.json` |
| 2 | SPEC/BUILD-facing | `curator`, `gap-analyzer` | `material_coverage_map.json` |
| 3 | SPEC | `spec-contract` | `segment_contract.json` |
| 4-7 | SPEC facets | `writer`, `audio-director`, `effects-director`, `director`, `curator` | contract facets |
| 8 | SPEC route | `gap-analyzer`, `generative-director`, `route` | `fallback_route.json`, `build_profile.json`, `generated_asset_requests.json` |
| 9 | BUILD | `editor` | `assembly_plan.json` |
| 10 | BUILD | `editor` | `timeline_build.json` |
| 11 | REVIEW | `editor_review`, `dashboard` | `editor_review.json` |
| 12 | VERIFY | `verify`, `content_qa` | `qa_report.json`, `content_qa.json`, `verify_result.json`, `state.json` |
| 13 | DELIVERY | `editor`, `verify` | `final.mp4`, `artifact_manifest.json` |
| 14 | ITERATION | `route`, `editor`, `verify`, `dashboard` | `revision_plan.json` |

## Verification Baseline

```powershell
cd C:\Users\user\Desktop\video_pipeline
python -m unittest discover -s tests -v
```

Latest WSL full-suite reference: `236 tests OK`.
Current Windows baseline: `255 tests OK` (100% success).
