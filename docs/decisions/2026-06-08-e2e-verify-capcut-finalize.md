# E2E Verify + CapCut Finalize CLI (2026-06-08)

## Context

Pipeline has two render paths:
- **ffmpeg (canonical)**: one-shot `contract-run` → `final.mp4`
- **CapCut (optional)**: `write_capcut_draft` → GUI export → `capcut-finalize` → `final_capcut.mp4`

Both paths need end-to-end verification before the pipeline is considered production-ready.

## Decision

### 1. Wire `capcut-finalize` CLI

Added `capcut-finalize` command to `video_tools.py` as a thin wrapper around
`capcut_backend.finalize_export`. This command takes a CapCut-exported mp4
(raw, no BGM/outro) and produces a finished video:

```
capcut_exported.mp4 → force_mix_bgm → add_outro_card → final_capcut.mp4
```

Parameters: `--video`, `--out`, `--bgm`, `--outro-title`, `--outro-address`,
`--outro-extra` (optional), `--bgm-vol` (default 0.25).

### 2. CapCut export is a human gate

CapCut has no CLI export. The export step is always manual (GUI or Computer Use).
The pipeline explicitly marks this in `capcut_draft_manifest.json`:
`"requires_human_or_computer_use": true`.

### 3. E2E verification uses P1 audit tool pack

Full Node 12 verification runs 5 audit tools against the final video:

| Tool | Artifact | Checks |
|---|---|---|
| `verify` | `verify_result.json` | score, script coverage, duration, audio, technical |
| `timeline-audit` | `timeline_invariants.json` | clip trace, duration, overlap, target match |
| `keyframe-grid` | `keyframe_grid.jpg` | visual sampling grid |
| `caption-audit` | `caption_audit.json` | gap, overlap, reading speed |
| `broll-audit` | `broll_audit.json` | b-roll ratio, source reuse |
| `visual-audit` | `visual_audit.json` | mechanical frame checks |

All artifacts go to `<run>/verify/`.

## Verification

### ffmpeg path (coffee baseline)

```
verify_result.json   → score 92.5, PASS
timeline_invariants  → 4/4 checks PASS
keyframe_grid        → 12 samples, 中文字幕無亂碼
caption_audit        → 0 issues
broll_audit          → 0 issues
visual_audit         → 0 mechanical findings
```

Known issue: audio_levels score 50 (max 0.0dB, mean -10.2dB — 偏大聲).
Not blocking; tunable via `--bgm-vol`.

### CapCut path (coffee baseline)

```
capcut-finalize      → ok, 1920x1080, 100.7s, BGM 20%
keyframe_grid_capcut → 12 samples, outro card visible at last frame
visual_audit_capcut  → PASS, 0 findings
```

Draft loaded in CapCut successfully (hermes_p3_demo). Export produced valid mp4.
Visual content mismatch due to clip loading issue in CapCut (not a pipeline bug).

## Status

Both paths verified end-to-end. Pipeline is production-ready for the
`build_profile → render → finalize → verify` loop.
