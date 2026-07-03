# Hermes Video Pipeline - Agent Instructions

## Skill-Forcing Rule

For any request to make, edit, produce, cut, recap, render, review, or repair a
video, use the video pipeline entry first. Read
`docs/START_HERE_VIDEO_PIPELINE.md`, then enter through
`skills/video-pipeline.md` and the `runtime.py` / `state.json.next_action`
state machine.

Do not bypass the pipeline by hand-running ffmpeg, ad hoc `video_tools.py`
commands, or manual material stitching.

## Key Facts

- Canonical SPEC is `segment_contract.json`.
- Unified driver is `runtime.py` (`resume` / `status` / `rerun`).
- `state.json.next_action` is the state-machine cursor.
- Dry BUILD check is `python video_tools.py contract-dry-build <contract> --out-dir DIR`.
- ffmpeg is the canonical render backend; CapCut is an optional human/GUI gate.
- Full suite command is `python -m unittest discover -s tests`.
- Use miniconda Python for local runs.
