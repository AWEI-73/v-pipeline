# 2026-06-08 — P3: CapCut as an optional render backend

Status: accepted (scaffolding); real `.draft` serialization now implemented — see
`2026-06-08-p3-capcut-draft-serializer.md` (CapCut v171 installed; clone-skeleton
serializer built). The "deferred" note below applied only while CapCut was absent.

## Context

The roadmap's P3 milestone explores CapCut as an optional Node 13 render-candidate
backend for richer text/template/manual finishing. The integration spec requires
a separate design review before building, confirming the installed CapCut version,
supported draft format, GUI/Computer-Use responsibility, failure recovery, and
export verification.

## Design-review finding

CapCut is **not installed** on the current Windows machine (no `Program Files`,
`LocalAppData`, or `Programs` install; no draft folder found). Therefore the
proprietary, version-specific `.draft` format cannot be confirmed or tested here.
Writing a `.draft` serializer blind would guess at a private format — which the
spec forbids.

## Decision

Build the **version-independent optional-backend framework** now; gate the real
`.draft` serialization on a confirmed CapCut install.

Built (safe, tested):
- `build_profile.render_backend` (`ffmpeg|capcut_draft|remotion|html_playwright`,
  default `ffmpeg`) + `requires_human_or_computer_use` (default `false`).
- `video_pipeline_core/capcut_backend.py`:
  - `capcut_draft_manifest.json` — a provider-neutral description of the timeline
    (video items, text overlays, audio cues). `draft_serialization.status =
    "pending"` marks the version-gated boundary.
  - `capcut_export_manifest.json` — records any CapCut export as a Render
    Candidate (`accepted=false`, `requires_node12_verify=true`); GUI export is a
    human/Computer-Use gate.
- `capcut-draft` CLI; `contract-run` emits the draft manifest only when
  `render_backend == "capcut_draft"` (inert by default). Both artifacts are
  indexed in `artifact_manifest.json` and Node 13 `outputs`.

Deferred until CapCut is installed and its version/format confirmed:
- Serializing `capcut_draft_manifest.json` into CapCut's real `.draft` files.
- Driving/exporting via the CapCut GUI (human or Computer Use).

## Invariants preserved

- ffmpeg remains the canonical unattended MVP backend.
- `segment_contract.json` carries no CapCut-specific fields.
- A CapCut export is never an automatically accepted final — Node 12 verifies it.
- No proprietary format or author-specific code was copied from the MIT reference
  kit (techniques only). See `THIRD_PARTY_NOTICES.md`.

## Revisit when

The user installs CapCut and wants real draft export. Then: confirm the draft
schema for that version, implement the serializer behind `draft_serialization`,
and define the GUI/Computer-Use export + failure recovery path.
