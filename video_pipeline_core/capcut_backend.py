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
import copy
import json
import uuid
from pathlib import Path

_EXPORT_METHODS = ("human", "computer_use")

# CapCut stores all times in microseconds.
_US = 1_000_000


def _us(seconds):
    return int(round(float(seconds or 0) * _US))


def _new_id():
    return str(uuid.uuid4()).upper()


def _material_bucket_index(materials):
    """Map every material id -> the bucket (list key) it lives in."""
    index = {}
    for bucket, items in materials.items():
        if isinstance(items, list):
            for m in items:
                if isinstance(m, dict) and m.get("id"):
                    index[m["id"]] = bucket
    return index


def build_capcut_draft(skeleton, timeline, *, project_name=None):
    """Build a real CapCut draft dict by cloning a skeleton draft per clip.

    ``skeleton`` is a real ``draft_content.json`` (one CapCut-generated project)
    used as the structural template — this is the robust approach the reference
    kit uses, because a from-scratch draft would have to reproduce CapCut's whole
    UUID-linked material graph. For each clip we clone the template video material
    and segment (plus the segment's ``extra_material_refs`` siblings), assign fresh
    UUIDs, and set source/target time ranges in microseconds.

    Validation note: the generated draft must still be opened in CapCut to confirm
    it loads (the format is version-specific and undocumented).
    """
    draft = copy.deepcopy(skeleton)
    materials = draft.setdefault("materials", {})
    clips = timeline.get("clips") if isinstance(timeline, dict) else (timeline or [])

    # Locate the first video track + its template segment + template material.
    video_track = next((t for t in draft.get("tracks", []) if t.get("type") == "video"), None)
    if video_track is None or not video_track.get("segments"):
        raise ValueError("skeleton has no video track/segment to use as a template")
    tmpl_seg = copy.deepcopy(video_track["segments"][0])
    vids = materials.get("videos") or []
    tmpl_mat = copy.deepcopy(vids[0]) if vids else None
    if tmpl_mat is None:
        raise ValueError("skeleton has no video material to use as a template")

    bucket_index = _material_bucket_index(materials)

    # Reset the video track + video material bucket; we rebuild them per clip.
    materials["videos"] = []
    new_segments = []
    cursor = 0

    for i, clip in enumerate(clips):
        dur = _us(clip.get("duration_sec"))
        src_in = _us(clip.get("start_sec") or clip.get("source_in_sec") or 0)

        mat = copy.deepcopy(tmpl_mat)
        mat["id"] = _new_id()
        mat["path"] = (clip.get("source_path") or clip.get("file") or "").replace("\\", "/")
        mat["duration"] = dur
        mat["material_name"] = Path(mat["path"]).name if mat["path"] else mat.get("material_name", "")
        materials["videos"].append(mat)

        seg = copy.deepcopy(tmpl_seg)
        seg["id"] = _new_id()
        seg["material_id"] = mat["id"]
        # Clone each extra-material sibling so the segment is self-contained.
        new_refs = []
        for ref in tmpl_seg.get("extra_material_refs", []):
            bucket = bucket_index.get(ref)
            if not bucket:
                continue
            src_mat = next((m for m in skeleton["materials"][bucket] if m.get("id") == ref), None)
            if src_mat is None:
                continue
            clone = copy.deepcopy(src_mat)
            clone["id"] = _new_id()
            materials.setdefault(bucket, []).append(clone)
            new_refs.append(clone["id"])
        seg["extra_material_refs"] = new_refs
        seg["source_timerange"] = {"start": src_in, "duration": dur}
        seg["target_timerange"] = {"start": cursor, "duration": dur}
        seg["render_index"] = i
        new_segments.append(seg)
        cursor += dur

    video_track["segments"] = new_segments
    draft["duration"] = cursor
    draft["id"] = _new_id()
    if project_name is not None:
        draft["name"] = project_name
    return draft


def write_capcut_draft(skeleton_path, timeline, project_dir, *, project_name=None):
    """Write a real CapCut draft folder (draft_content.json + sync) from a skeleton.

    Returns the paths written. The draft folder name is the project name; drop it
    under CapCut's ``com.lveditor.draft`` root to open it in CapCut.
    """
    skeleton = json.loads(Path(skeleton_path).read_text(encoding="utf-8"))
    project_dir = Path(project_dir)
    project_dir.mkdir(parents=True, exist_ok=True)
    name = project_name or project_dir.name
    draft = build_capcut_draft(skeleton, timeline, project_name=name)

    # CapCut writes compact JSON; mismatched copies cause silent rollback, so we
    # write the canonical content + info copy with matching bytes.
    blob = json.dumps(draft, ensure_ascii=False, separators=(",", ":"))
    written = []
    for fname in ("draft_content.json", "draft_info.json"):
        p = project_dir / fname
        p.write_text(blob, encoding="utf-8")
        written.append(str(p))
    return {"ok": True, "project_dir": str(project_dir), "written": written,
            "clip_count": len(draft["tracks"][0]["segments"]) if draft.get("tracks") else 0}


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
