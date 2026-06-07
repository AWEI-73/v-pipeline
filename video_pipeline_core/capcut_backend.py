"""capcut_backend.py — P3 optional Node 13 render-candidate backend.

CapCut is an OPTIONAL finishing backend, never the canonical MVP path (ffmpeg
remains that). This module is deliberately version-independent: it produces a
*provider-neutral* draft manifest describing what CapCut should assemble, plus an
export manifest that treats any CapCut output as a Render Candidate which MUST
pass Node 12 verification.

It does NOT write CapCut's proprietary, version-specific ``.draft`` files. That
serialization is a separate, version-gated step (`draft_serialization.status =
"pending"`) that requires a confirmed installed CapCut version — see
docs/decisions for the design-review note. Building it blind would guess at a
private format, which the integration spec forbids.

Source: concept inspired by https://github.com/Hao0321/video-autopilot-kit
(MIT) capcut helpers; reimplemented generically, no proprietary format or
author-specific code copied.
"""
import json
from pathlib import Path

_EXPORT_METHODS = ("human", "computer_use")


def _clips(timeline):
    if isinstance(timeline, list):
        return timeline
    if isinstance(timeline, dict):
        return timeline.get("clips") or []
    return []


def build_draft_manifest(timeline, *, project_name=None, fps=30, resolution="1920x1080"):
    """Build a provider-neutral CapCut draft manifest from a timeline_build.

    The manifest is a portable description (video items, text overlays, audio
    policy). Converting it to CapCut's proprietary .draft format is a separate
    version-gated step recorded under ``draft_serialization``.
    """
    clips = _clips(timeline)
    video_track = []
    text_overlays = []
    audio_cues = []
    for c in clips:
        start = c.get("start_sec")
        end = c.get("end_sec")
        video_track.append({
            "segment": c.get("segment"),
            "source_path": c.get("source_path") or c.get("file"),
            "source_in_sec": start,
            "source_out_sec": end,
            "timeline_in_sec": c.get("timeline_in_sec"),
            "duration_sec": c.get("duration_sec"),
        })
        text = c.get("text_overlay")
        if text and text != "none":
            text_overlays.append({
                "segment": c.get("segment"),
                "text": text,
                "timeline_in_sec": c.get("timeline_in_sec"),
                "duration_sec": c.get("duration_sec"),
            })
        if c.get("audio_policy"):
            audio_cues.append({
                "segment": c.get("segment"),
                "audio_policy": c.get("audio_policy"),
                "timeline_in_sec": c.get("timeline_in_sec"),
            })

    return {
        "artifact_role": "capcut_draft_manifest",
        "version": 1,
        "backend": "capcut_draft",
        "requires_human_or_computer_use": True,
        "project": {"name": project_name, "fps": fps, "resolution": resolution},
        "video_track": video_track,
        "text_overlays": text_overlays,
        "audio_cues": audio_cues,
        "draft_serialization": {
            "status": "pending",
            "reason": "writing CapCut's proprietary .draft requires a confirmed "
                      "installed CapCut version and draft format (design review).",
        },
        "next_action": None,
    }


def record_export(draft_manifest, exported_video, *, export_method="human"):
    """Record a CapCut export as a Render Candidate (never an accepted final).

    The GUI export is a human / Computer-Use gate; the result must still go
    through Node 12 verification before it can be accepted.
    """
    if export_method not in _EXPORT_METHODS:
        raise ValueError(f"export_method must be one of {_EXPORT_METHODS}")
    return {
        "artifact_role": "capcut_export_manifest",
        "version": 1,
        "backend": "capcut_draft",
        "exported_video": str(exported_video),
        "export_method": export_method,
        "render_candidate": True,
        "accepted": False,
        "requires_node12_verify": True,
        "source_project": (draft_manifest or {}).get("project"),
        "next_action": "node_12_verify",
    }


def write_draft_manifest(timeline, out_path, **kwargs):
    manifest = build_draft_manifest(timeline, **kwargs)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return {"ok": True, "capcut_draft_manifest": str(out_path), "manifest": manifest}


def write_export_manifest(draft_manifest, exported_video, out_path, *, export_method="human"):
    manifest = record_export(draft_manifest, exported_video, export_method=export_method)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)
    return {"ok": True, "capcut_export_manifest": str(out_path), "manifest": manifest}
