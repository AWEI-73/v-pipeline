# Current Handoff: Hermes Video Pipeline

> **2026-06-08 active work:** the editorial soul layer (narrative blueprint +
> material treatment + editing-intent). For a full-takeover-ready handoff of that
> work see **`archive/HANDOFF_EDITORIAL.md`** (tasks done) and the live overview
> `docs/editorial-layer.md`. This file remains the convergence/runtime anchor.

Updated: 2026-06-06

This file is the clean resume anchor (older WSL-era notes are archived at
`archive/HANDOFF.md`). Read this first, then `roadmap.md`,
`docs/windows-native-migration-spec.md`, `docs/build-tool-runner-spec.md`,
`docs/video-autopilot-tool-integration-spec.md`,
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
- Root Python files: CLI/orchestrator shims (`video_pipeline.py`, `video_tools.py`, `runtime.py`).
- Unified driver: `runtime.py` (resume/status/rerun) is the single state-driven executor. The legacy `route.py` dispatcher was retired 2026-06-10 (zero functional deps; its `await_material`/MV dispatch is reimplemented in `runtime_orchestrator.py`). The `route` skill (`skills/route.md`) now drives `runtime.py`.
- Content QA entry: `video_pipeline.py` calls `python3 -m video_pipeline_core.content_qa`.
- Error routing truth: `video_pipeline.py` aliases `video_pipeline_core.vt_core.FIX_TARGET`.
- Project outputs: external project/run folders; repo-local `.project/active.json` is only a relative pointer.
- Material folders: `materials/raw`, `materials/selected`, `materials/generated`, `materials/stock`.
- VLM policy: `qwen3-vl:4b-instruct` only for gate, content QA, and retry.
- Generated provider policy: Antigravity / assistant_imagegen / codex_imagegen preferred; ComfyUI is deprecated/disabled unless explicitly isolated.
- BUILD runner policy: tool choices live in `build_profile.json`; runner work must write explicit artifacts and manifest entries. See `docs/build-tool-runner-spec.md`.
- Editing/VERIFY tool integration: P1 (verification tool pack, Node 11/12), P1.5 (auto-wire into contract-run), P2 (creator_profile), and P3 (optional CapCut backend) all implemented 2026-06-07/08. ffmpeg stays canonical; CapCut real `.draft` serialization WORKS (skeleton-clone via `templates/0608/`, video track only) and the path is E2E-verified (see COMPLETED section below). Remaining CapCut gap: text/subtitle + audio tracks inside the draft (today BGM/outro are added post-export by `capcut-finalize`). See `docs/build-tool-runner-spec.md`, `docs/video-autopilot-tool-integration-spec.md`, and `docs/decisions/2026-06-08-p3-capcut-optional-backend.md`. Attribution in `THIRD_PARTY_NOTICES.md` (techniques referenced, no code copied).
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
Full test suite: 342 tests pass (100% success)  # 255 + 56 P1 + 9 P1.5 + 11 P2 + 11 P3 tests
```

## COMPLETED — E2E Verify: ffmpeg + CapCut (2026-06-08)

Both render paths verified end-to-end on the `coffee` baseline run.

```text
ffmpeg path (canonical, default):
  final.mp4 → verify score 92.5 PASS
  P1 audit pack (5/5 PASS):
    timeline_invariants.json  — clip trace, duration, overlap, target match
    keyframe_grid.jpg         — 12 samples, 中文字幕無亂碼
    caption_audit.json        — 0 gap / 0 overlap / 0 too-fast
    broll_audit.json          — broll_ratio=0, unique_source=1.0
    visual_audit.json         — 0 mechanical findings
  Known: audio_levels 50 (max 0.0dB 偏大聲) — tunable via --bgm-vol

CapCut path (optional, render_backend=capcut_draft):
  hermes_p3_demo draft loaded in CapCut ✓
  User exported capcut_exported.mp4 from CapCut GUI ✓
  capcut-finalize (BGM 20% + outro card) → final_capcut.mp4 ✓
  visual_audit PASS, keyframe_grid generated ✓
  CapCut export is always a human/CU gate (no CLI export).

CLI commands verified:
  video_tools.py capcut-finalize --video X --out Y --bgm Z --outro-title --outro-address
  video_tools.py verify / timeline-audit / keyframe-grid / caption-audit / broll-audit / visual-audit

Decision log: docs/decisions/2026-06-08-e2e-verify-capcut-finalize.md
Commit: 4d0c96c
```

## P1 Verification Tool Pack State (2026-06-07)

```text
timeline_invariants.py / timeline-audit  -> timeline_invariants.json  (Node 11)  done
broll_audit.py         / broll-audit     -> broll_audit.json          (Node 11)  done
caption_audit.py       / caption-audit   -> caption_audit.json        (Node 11/12) done (reads subtitles.srt via --srt)
keyframe_grid.py       / keyframe-grid   -> keyframe_grid.jpg         (Node 12)  done (ffmpeg; fails loudly if no frames)
visual_audit.py        / visual-audit    -> visual_audit.json         (Node 12)  done (mechanical; optional VLM)
manifest/dashboard/registry/runtime integration: done (audits inert when absent)
P3 capcut (optional): build_profile.render_backend (default ffmpeg) + capcut_backend.py — provider-neutral
  capcut_draft_manifest + export-as-render-candidate (accepted=False, Node 12 verify required, human/CU gate).
  Real .draft serialization WORKS: build_capcut_draft skeleton-clone (templates/0608 full CapCut project,
  rebuilds the video track per clip, ID remap + meta sync); E2E-verified in CapCut GUI 2026-06-08.
  ffmpeg stays canonical. capcut-draft CLI; contract-run emits draft only when render_backend=capcut_draft.
  Gap: text/audio tracks inside the draft (BGM/outro currently post-export via capcut-finalize).
  See docs/decisions/2026-06-08-p3-capcut-optional-backend.md
P2 creator_profile: creator_profile.py + creator-profile CLI; brief overrides creator defaults;
  contract-run --creator-profile fills build_profile broll_policy + writes creator_profile_applied.json (manifest-indexed)
P1.5 auto-wire: contract-run auto-produces enabled audits via build_profile.verification_tools (default OFF)
One-click smoke (all tools on, real video): 5/5 artifacts written in one pass; broll fail->curator; keyframe_grid ~80 KB
Graphify: REBUILT 2026-06-08 (source-only) after P1/P1.5 — see graphify-out/
```

## Latest Graphify (2026-06-08, post P1/P1.5)

Source-only rebuild (excludes run outputs/media/_fullpool/archives and the
external video-autopilot-kit-main/ reference clone):

```text
121 source files (73 code + 48 docs) · ~94,734 words
1346 nodes · 1992 edges · 115 communities
extraction: AST (1108 code nodes) + 3 semantic doc subagents (240 nodes)
P1 modules + integration captured; hyperedge "P1 Verification Tool Pack (Node 11/12)" present
god nodes still: ToolError(56), run(), load_dashboard_state(), pipeline(), run_tool(), _audio_duration()
new god node: "Video Autopilot Tool Integration Spec" (14 edges) — P1 work is well-connected
```

### Codex review (2026-06-07) — findings addressed in P1.5

```text
[P1] contract-run did not auto-produce audits  -> FIXED (build_profile.verification_tools, default OFF)
[P2] caption-audit didn't read subtitles.srt   -> FIXED (parse_srt + --srt)
[P2] keyframe-grid too lenient on empty output  -> FIXED (CLI fails when no frames)
[P2] timeline_invariants shape narrow (items/tracks) -> deferred future-proofing; current canonical shape is clips
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
Current Windows baseline: `342 tests OK` (100% success; 255 + 56 P1 + 9 P1.5 + 11 P2 + 11 P3 tests).
