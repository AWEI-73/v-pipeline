# Hermes Video Pipeline - Agent Instructions

## Skill-Forcing Rule

For any request to make, edit, produce, cut, recap, render, review, or repair a
video, use the sole operational entry first: read `RUNBOOK.md`, then
`HANDOFF_CURRENT.md` for live or IDLE state. Use
`skills/video-pipeline-route.md` as the operator router. Load
`docs/START_HERE_VIDEO_PIPELINE.md` only when route vocabulary is needed.

Do not bypass the pipeline by hand-running ffmpeg, ad hoc `video_tools.py`
commands, or manual material stitching.

## Key Facts

- Canonical SPEC is `segment_contract.json`.
- `tools/pipeline_home.py --run RUN_DIR --json` is the first reader for an
  existing run.
- `runtime.py` (`resume` / `status` / `rerun`) is the compatibility runtime
  driver only after the operator route selects an active canonical Node run.
- `state.json.next_action` is a per-run runtime cursor, not the repository boot
  entry or the source of IDLE state.
- Dry BUILD check is `python video_tools.py contract-dry-build <contract> --out-dir DIR`.
- ffmpeg is the canonical render backend; CapCut is an optional human/GUI gate.
- Full suite command is `python -m unittest discover -s tests`.
- Use miniconda Python for local runs.
- Bootstrap and first-run setup: `docs/setup/setup-and-first-run.md`.
