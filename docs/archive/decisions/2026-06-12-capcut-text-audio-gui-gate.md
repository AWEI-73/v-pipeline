# Decision: Accept CapCut text/audio draft bridge after real GUI load

Date: 2026-06-12
Status: verified
Scope: video_pipeline_core/capcut_backend.py / Node 13
Superpowers phase: verify

## SPEC

Requirement:

Close roadmap E5 by proving that a generated CapCut draft containing video,
editable text, and audio tracks loads in the installed CapCut GUI.

Why:

CapCut draft JSON is version-specific and undocumented. Unit tests and JSON
inspection cannot prove that the installed editor accepts the linked material
graph.

Direction:

Generate a dedicated four-second draft with valid local media paths, then open
it in CapCut 8.7.0.3685 and visually verify all three track types.

Non-goals:

Do not automate export, accept the CapCut render as canonical, or change the
existing ffmpeg-first policy.

## DO

Files / modules:

- `video_pipeline_core/capcut_backend.py`: existing draft writer under test.
- `tests/test_capcut_backend.py`: JSON-level track and material contracts.
- `roadmap.md`: GUI gate status and evidence.

Function-level plan:

Use `write_capcut_draft` with two video clips, two text overlays, and one
explicit BGM source, then load the resulting project from CapCut's draft root.

Data / interface changes:

No production interface changes. The gate validates the existing draft format.

Migration / compatibility:

Verified against installed CapCut version 8.7.0.3685 on Windows.

## VERIFY

Pre-checks:

The generated draft contained two video materials, two text materials, one
audio material, and valid local source paths.

Tests:

`python -m unittest tests.test_capcut_backend -v`

Manual checks:

Opened:
`C:\Users\user\AppData\Local\CapCut\User Data\Projects\com.lveditor.draft\20260612-e5-text-audio-gate`

CapCut loaded the project without error. The timeline displayed two editable
text segments, one audio track, and two video segments. The preview displayed
the text overlay.

Regression risks:

Future CapCut versions may change draft serialization or linked material
requirements, so GUI load remains a required gate after format changes.

## Decision Notes

Accepted because:

The installed target editor consumed the generated project and exposed every
required editable track in its timeline.

Tradeoffs:

The verification is version-specific and visual rather than fully automated.

Open questions:

Whether a later roadmap phase should automate CapCut export remains separate.

## Git / Retrieval

Related files:

- `video_pipeline_core/capcut_backend.py`
- `tests/test_capcut_backend.py`
- `roadmap.md`

Related commits:

None yet.

Graphify anchors:

Node 13, CapCut draft, editable text track, audio track, GUI load gate

Search tags:

decision-log, spec-do-verify, video-pipeline, E5, capcut, gui-gate
