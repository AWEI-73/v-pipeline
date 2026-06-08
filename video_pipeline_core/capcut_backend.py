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
import math
import os
import shutil
import subprocess
import sys
import time
import uuid
from pathlib import Path
from typing import Optional, Tuple, Dict, List, Set

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
    
    # Auto-mute newly generated video segments to avoid audio leaks
    mute_all_video_segments(draft)
    
    return draft


def kill_capcut_all():
    """Forcefully terminate all CapCut.exe processes on Windows."""
    import subprocess
    import time
    try:
        subprocess.run(["taskkill", "/F", "/IM", "CapCut.exe"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except Exception:
        pass
    time.sleep(2)


def write_capcut_draft(skeleton_path, timeline, project_dir, *, project_name=None):
    """Write a real CapCut draft folder (draft_content.json + sync) from a skeleton.

    Returns the paths written. The draft folder name is the project name; drop it
    under CapCut's ``com.lveditor.draft`` root to open it in CapCut.
    """
    import shutil
    import time
    
    skeleton_path = Path(skeleton_path)
    skeleton_dir = skeleton_path.parent
    project_dir = Path(project_dir)
    name = project_name or project_dir.name

    # Terminate CapCut if editing under the default com.lveditor.draft root
    if "com.lveditor.draft" in str(project_dir).replace("\\", "/"):
        kill_capcut_all()

    is_full_skeleton = (skeleton_dir / "Timelines").exists()
    if is_full_skeleton:
        if project_dir.exists():
            shutil.rmtree(project_dir)
        shutil.copytree(skeleton_dir, project_dir)
    else:
        project_dir.mkdir(parents=True, exist_ok=True)

    skeleton = json.loads(skeleton_path.read_text(encoding="utf-8"))
    draft = build_capcut_draft(skeleton, timeline, project_name=name)
    new_timeline_id = draft["id"]
    old_timeline_id = skeleton.get("id")

    if is_full_skeleton:
        # Rename timeline subfolder
        timelines_dir = project_dir / "Timelines"
        new_timeline_dir = timelines_dir / new_timeline_id
        if old_timeline_id:
            old_timeline_dir = timelines_dir / old_timeline_id
            if old_timeline_dir.exists():
                old_timeline_dir.rename(new_timeline_dir)
            else:
                for sub in timelines_dir.iterdir():
                    if sub.is_dir() and sub.name != new_timeline_id:
                        sub.rename(new_timeline_dir)
                        break
        else:
            for sub in timelines_dir.iterdir():
                if sub.is_dir() and sub.name != new_timeline_id:
                    sub.rename(new_timeline_dir)
                    break

        # Replace timeline ID references
        for fname in ("timeline_layout.json", "Timelines/project.json", "Timelines/project.json.bak"):
            p = project_dir / fname
            if p.exists():
                content = p.read_text(encoding="utf-8")
                if old_timeline_id:
                    content = content.replace(old_timeline_id, new_timeline_id)
                p.write_text(content, encoding="utf-8")

    # Compact JSON sync for all copies
    blob = json.dumps(draft, ensure_ascii=False, separators=(",", ":"))
    written = []
    
    sync_files = [
        project_dir / "draft_content.json",
        project_dir / "draft_info.json",
        project_dir / "draft_content.json.bak",
        project_dir / "template-2.tmp"
    ]
    if is_full_skeleton:
        new_timeline_dir = timelines_dir / new_timeline_id
        sync_files.extend([
            new_timeline_dir / "draft_content.json",
            new_timeline_dir / "draft_content.json.bak",
            new_timeline_dir / "template-2.tmp"
        ])

    for p in sync_files:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(blob, encoding="utf-8")
        written.append(str(p))

    if is_full_skeleton:
        # Update draft_meta_info.json
        meta_path = project_dir / "draft_meta_info.json"
        new_draft_id = _new_id()
        if meta_path.exists():
            try:
                meta = json.loads(meta_path.read_text(encoding="utf-8"))
                meta["draft_id"] = new_draft_id
                meta["draft_name"] = name
                meta["draft_fold_path"] = str(project_dir).replace("\\", "/")
                meta["tm_duration"] = draft["duration"]
                meta["tm_draft_modified"] = int(time.time() * 1_000_000)
                meta_path.write_text(json.dumps(meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            except Exception:
                pass

        # Register in root_meta_info.json
        root_meta_path = project_dir.parent / "root_meta_info.json"
        if root_meta_path.exists():
            try:
                root_meta = json.loads(root_meta_path.read_text(encoding="utf-8"))
                all_store = root_meta.setdefault("all_draft_store", [])
                
                # Check for existing entry
                entry = next((item for item in all_store if item.get("draft_fold_path") == str(project_dir).replace("\\", "/")), None)
                if not entry:
                    entry = next((item for item in all_store if item.get("draft_name") == name), None)
                
                if entry:
                    entry["draft_id"] = new_draft_id
                    entry["draft_fold_path"] = str(project_dir).replace("\\", "/")
                    entry["draft_json_file"] = str(project_dir / "draft_content.json").replace("\\", "/")
                    entry["draft_cover"] = str(project_dir / "draft_cover.jpg").replace("\\", "/")
                    entry["tm_draft_modified"] = int(time.time() * 1_000_000)
                    entry["tm_duration"] = draft["duration"]
                else:
                    tmpl_entry = next((item for item in all_store if "0608" in item.get("draft_fold_path", "")), None)
                    if not tmpl_entry and all_store:
                        tmpl_entry = all_store[0]
                    if tmpl_entry:
                        new_entry = dict(tmpl_entry)
                        new_entry["draft_id"] = new_draft_id
                        new_entry["draft_name"] = name
                        new_entry["draft_fold_path"] = str(project_dir).replace("\\", "/")
                        new_entry["draft_json_file"] = str(project_dir / "draft_content.json").replace("\\", "/")
                        new_entry["draft_cover"] = str(project_dir / "draft_cover.jpg").replace("\\", "/")
                        new_entry["tm_draft_create"] = int(time.time() * 1_000_000)
                        new_entry["tm_draft_modified"] = int(time.time() * 1_000_000)
                        new_entry["tm_duration"] = draft["duration"]
                        all_store.append(new_entry)
                
                root_meta["draft_ids"] = len(all_store)
                root_meta_path.write_text(json.dumps(root_meta, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
            except Exception:
                pass

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


# ─────────────────────────────────────────────────────────────────────
# CapCut Paths & Configuration
# ─────────────────────────────────────────────────────────────────────

CAPCUT_USER_DATA = Path.home() / "AppData" / "Local" / "CapCut" / "User Data"
DRAFTS_ROOT = CAPCUT_USER_DATA / "Projects" / "com.lveditor.draft"
EFFECT_CACHE = CAPCUT_USER_DATA / "Cache" / "effect"

# ─────────────────────────────────────────────────────────────────────
# 4-Level Mute Logic (M29 lesson — volume=0 alone leaks audio)
# ─────────────────────────────────────────────────────────────────────

def mute_all_video_segments(draft: dict) -> tuple[int, int]:
    """Apply 4-level mute to every video segment + its material.

    Returns:
        (n_segments_muted, n_materials_muted)
    """
    materials_video = draft.get("materials", {}).get("videos", [])
    material_by_id = {m["id"]: m for m in materials_video}

    n_segs = 0
    muted_material_ids = set()

    for tr in draft.get("tracks", []):
        if tr.get("type") != "video":
            continue
        for seg in tr.get("segments", []):
            # Segment-level mute
            seg["volume"] = 0.0
            seg["last_nonzero_volume"] = 0.0
            n_segs += 1

            # Material-level mute (one material can back many segments, dedupe)
            mid = seg.get("material_id")
            if mid and mid not in muted_material_ids:
                if mid in material_by_id:
                    mat = material_by_id[mid]
                    mat["has_audio"] = False
                    mat["has_sound_separated"] = True
                    muted_material_ids.add(mid)

    return n_segs, len(muted_material_ids)


def mute_specific_segments(draft: dict, segment_indices: list[int]) -> int:
    """Mute only specific video segments by index (within video track)."""
    materials_video = draft.get("materials", {}).get("videos", [])
    material_by_id = {m["id"]: m for m in materials_video}

    n = 0
    for tr in draft.get("tracks", []):
        if tr.get("type") != "video":
            continue
        for idx, seg in enumerate(tr.get("segments", [])):
            if idx not in segment_indices:
                continue
            seg["volume"] = 0.0
            seg["last_nonzero_volume"] = 0.0
            mid = seg.get("material_id")
            if mid and mid in material_by_id:
                mat = material_by_id[mid]
                mat["has_audio"] = False
                mat["has_sound_separated"] = True
            n += 1
    return n


def audit_mute_state(draft: dict) -> dict:
    """Verify all video segments are properly 4-level muted.

    Returns:
        {
            'total_segments': int,
            'fully_muted': int,
            'partial_muted': list of (seg_idx, missing_level),
            'success_rate': float (0.0-1.0)
        }
    """
    materials_video = draft.get("materials", {}).get("videos", [])
    material_by_id = {m["id"]: m for m in materials_video}

    total = 0
    fully_muted = 0
    partial = []

    for tr in draft.get("tracks", []):
        if tr.get("type") != "video":
            continue
        for idx, seg in enumerate(tr.get("segments", [])):
            total += 1
            issues = []
            if seg.get("volume", 1.0) != 0.0:
                issues.append("seg.volume")
            if seg.get("last_nonzero_volume", 1.0) != 0.0:
                issues.append("seg.last_nonzero_volume")
            mid = seg.get("material_id")
            if mid in material_by_id:
                mat = material_by_id[mid]
                if mat.get("has_audio", True):
                    issues.append("material.has_audio")
                if not mat.get("has_sound_separated", False):
                    issues.append("material.has_sound_separated")
            if not issues:
                fully_muted += 1
            else:
                partial.append((idx, issues))

    return {
        "total_segments": total,
        "fully_muted": fully_muted,
        "partial_muted": partial,
        "success_rate": fully_muted / max(total, 1),
    }

# ─────────────────────────────────────────────────────────────────────
# CapCut Bundled Fonts & Text Styling Presets
# ─────────────────────────────────────────────────────────────────────

CAPCUT_FONTS = {
    "剪映团子": {
        "effect_id": "7598225001988246801",
        "cache_subdir": "1ecc73e2c3778fc5584e430e53a2560d",
        "font_filename": "font.ttf",
    },
    "capcut_systemfont": {
        "absolute_path": str(Path.home() / "AppData/Local/CapCut/Apps")
    },
}


def get_capcut_font_path(font_name: str) -> str:
    """Resolve full font.ttf path for a CapCut bundled font."""
    if font_name not in CAPCUT_FONTS:
        raise KeyError(f"Unknown CapCut font '{font_name}'. Known: {list(CAPCUT_FONTS.keys())}")
    f = CAPCUT_FONTS[font_name]
    if "absolute_path" in f:
        # Resolve version-specific path dynamically using glob
        apps_dir = Path(f["absolute_path"])
        # Find all ttf/otf files in Apps/*/Resources/Font/SystemFont/
        for p in apps_dir.glob("**/Resources/Font/SystemFont/*zh-hant*"):
            if p.is_file():
                return str(p).replace("\\", "/")
        for p in apps_dir.glob("**/Resources/Font/SystemFont/*.ttf"):
            if p.is_file():
                return str(p).replace("\\", "/")
        return f["absolute_path"]
    path = EFFECT_CACHE / f["effect_id"] / f["cache_subdir"] / f["font_filename"]
    return str(path).replace("\\", "/")


PRESET_STYLES = {
    "white_outline_black": {
        "text_color": "#ffffff",
        "border_color": "#000000",
        "border_width": 0.06,
        "has_shadow": False,
        "fill_color": [1, 1, 1],
        "stroke_color": [0, 0, 0],
        "stroke_width": 0.06,
        "default_font": "剪映团子",
    },
    "white_plain": {
        "text_color": "#ffffff",
        "border_color": "",
        "border_width": 0,
        "has_shadow": False,
        "fill_color": [1, 1, 1],
        "stroke_color": None,
        "stroke_width": 0,
        "default_font": "剪映团子",
    },
    "yellow_highlight_black": {
        "text_color": "#000000",
        "border_color": "#FFD700",
        "border_width": 0.0,
        "has_shadow": False,
        "fill_color": [0, 0, 0],
        "stroke_color": None,
        "stroke_width": 0,
        "default_font": "剪映团子",
        "background_color": [1, 0.84, 0],
    },
    "red_outline_black": {
        "text_color": "#ff0000",
        "border_color": "#000000",
        "border_width": 0.06,
        "has_shadow": False,
        "fill_color": [1, 0, 0],
        "stroke_color": [0, 0, 0],
        "stroke_width": 0.06,
        "default_font": "剪映团子",
    },
    "hao_teaching_primary": {
        "text_color": "#ffffff",
        "border_color": "#000000",
        "border_width": 0.08,
        "has_shadow": False,
        "fill_color": [1.0, 1.0, 1.0],
        "stroke_color": [0.0, 0.0, 0.0],
        "stroke_width": 0.06,
        "background_color": "#000000",
        "background_alpha": 0.7,
        "background_round_radius": 0.4,
        "background_height": 0.28,
        "default_font": "capcut_systemfont",
    },
    "hao_teaching_secondary": {
        "text_color": "#ffffff",
        "border_color": "#000000",
        "border_width": 0.08,
        "has_shadow": False,
        "fill_color": [1.0, 1.0, 1.0],
        "stroke_color": [0.0, 0.0, 0.0],
        "stroke_width": 0.06,
        "background_color": "#000000",
        "background_alpha": 1.0,
        "background_round_radius": 0.0,
        "background_height": 0.14,
        "default_font": "capcut_systemfont",
    },
}


def apply_text_preset(draft: dict, segment_idx: int,
                      preset_name: str = "white_outline_black",
                      font_name: str = None,
                      font_size: int = 15,
                      clear_existing_effects: bool = True) -> dict:
    """Apply CapCut 基礎 tab 預設樣式 to a text segment."""
    if preset_name not in PRESET_STYLES:
        raise KeyError(f"Unknown preset '{preset_name}'. Available: {list(PRESET_STYLES.keys())}")
    preset = PRESET_STYLES[preset_name]
    font = font_name or preset.get("default_font", "剪映团子")
    font_path = get_capcut_font_path(font)

    # Locate text track + segment
    text_tracks = [tr for tr in draft.get("tracks", []) if tr.get("type") == "text"]
    if not text_tracks:
        raise ValueError("No text tracks found")
    segs = text_tracks[0].get("segments", [])
    if segment_idx >= len(segs):
        raise ValueError(f"Segment idx {segment_idx} out of range")
    seg = segs[segment_idx]

    # Locate text material
    texts = draft.get("materials", {}).get("texts", [])
    mat = next((t for t in texts if t["id"] == seg.get("material_id")), None)
    if not mat:
        raise ValueError(f"No text material for segment {segment_idx}")

    # Update material-level fields
    mat["font_path"] = font_path
    mat["text_color"] = preset["text_color"]
    mat["border_color"] = preset.get("border_color", "")
    mat["border_width"] = preset.get("border_width", 0)
    mat["has_shadow"] = preset.get("has_shadow", False)

    try:
        co = json.loads(mat.get("content", "{}"))
    except json.JSONDecodeError:
        co = {"text": "", "styles": []}

    styles = co.setdefault("styles", [])
    if not styles:
        styles.append({"range": [0, len(co.get("text", ""))]})

    for s in styles:
        s["font"] = {"path": font_path, "id": "", "cn_name": "", "tw_name": ""}
        s["size"] = font_size
        s.pop("effectStyle", None)
        s["fill"] = {
            "alpha": 1,
            "content": {
                "render_type": "solid",
                "solid": {"alpha": 1, "color": preset["fill_color"]},
            },
        }
        if preset.get("stroke_color") and preset.get("stroke_width"):
            s["strokes"] = [{
                "width": preset["stroke_width"],
                "content": {
                    "render_type": "solid",
                    "solid": {"alpha": 1, "color": preset["stroke_color"]},
                },
            }]
        else:
            s["strokes"] = []
        s["useLetterColor"] = False

    mat["content"] = json.dumps(co, ensure_ascii=False, separators=(",", ":"))

    # Clear 花字 effect refs (extra_material_refs)
    if clear_existing_effects:
        effect_ids_in_materials = {
            e["id"]: e.get("category_name", "")
            for e in draft.get("materials", {}).get("effects", [])
        }
        new_refs = []
        for ref in seg.get("extra_material_refs", []):
            cat = effect_ids_in_materials.get(ref, "")
            if "text-flower" in cat or "panel-text-flower" in cat:
                continue
            new_refs.append(ref)
        seg["extra_material_refs"] = new_refs

    return mat


def apply_text_preset_to_all(draft: dict, preset_name: str = "white_outline_black",
                             font_name: str = "剪映团子",
                             font_size: int = 15) -> int:
    """Bulk apply same preset to ALL text segments. Returns count modified."""
    text_tracks = [tr for tr in draft.get("tracks", []) if tr.get("type") == "text"]
    if not text_tracks:
        return 0
    n = len(text_tracks[0].get("segments", []))
    for idx in range(n):
        apply_text_preset(draft, idx, preset_name=preset_name,
                         font_name=font_name, font_size=font_size)
    return n


def _is_chinese_text(text: str) -> bool:
    """Detect if text contains Chinese characters (CJK Unified Ideographs)."""
    return any(0x4E00 <= ord(c) <= 0x9FFF for c in text)


def apply_hao_teaching_dual_tier(draft: dict) -> dict:
    """⭐ M68 — Hao 教學長片字幕 PERMANENT WORKFLOW

    自動偵測每個 text material 語言 → apply 對應 preset：
    - 中文 (CJK chars) → hao_teaching_primary (alpha 0.7 / radius 0.4 / height 0.28)
    - 英文 (no CJK) → hao_teaching_secondary (alpha 1.0 / radius 0.0 / height 0.14)
    """
    primary = PRESET_STYLES["hao_teaching_primary"]
    secondary = PRESET_STYLES["hao_teaching_secondary"]
    font_path = get_capcut_font_path(primary["default_font"])

    texts = draft.get("materials", {}).get("texts", [])
    zh_count = 0
    en_count = 0

    for t in texts:
        try:
            co = json.loads(t.get("content", "{}"))
        except json.JSONDecodeError:
            continue
        text = co.get("text", "")
        if not text:
            continue

        preset = primary if _is_chinese_text(text) else secondary
        if preset is primary:
            zh_count += 1
        else:
            en_count += 1

        t["text_color"] = preset["text_color"]
        t["border_color"] = preset["border_color"]
        t["border_width"] = preset["border_width"]
        t["has_shadow"] = preset["has_shadow"]
        t["background_color"] = preset["background_color"]
        t["background_alpha"] = preset["background_alpha"]
        t["background_round_radius"] = preset["background_round_radius"]
        t["background_height"] = preset["background_height"]
        t["font_path"] = font_path

        for s in co.get("styles", []):
            s["font"] = {"path": font_path, "id": "", "cn_name": "", "tw_name": ""}
            s["fill"] = {
                "alpha": 1.0,
                "content": {"render_type": "solid",
                            "solid": {"alpha": 1.0, "color": preset["fill_color"]}},
            }
            s["strokes"] = [{
                "width": preset["stroke_width"],
                "alpha": 1.0,
                "content": {"render_type": "solid",
                            "solid": {"alpha": 1.0, "color": preset["stroke_color"]}},
            }]

        t["content"] = json.dumps(co, ensure_ascii=False, separators=(",", ":"))

    return {"zh_count": zh_count, "en_count": en_count, "total": zh_count + en_count}

# ─────────────────────────────────────────────────────────────────────
# CapCut Effect Application & Swapping
# ─────────────────────────────────────────────────────────────────────

def find_effect_material(draft: dict, effect_id: str) -> Optional[dict]:
    """Find a materials.effects entry by effect_id."""
    effects = draft.get("materials", {}).get("effects", [])
    for e in effects:
        if e.get("effect_id") == effect_id:
            return e
    return None


def get_effect_cache_path(effect_id: str) -> Optional[str]:
    """Resolve disk cache path for a CapCut effect."""
    cache_dir = EFFECT_CACHE / effect_id
    if not cache_dir.exists():
        return None
    subs = [s for s in os.listdir(cache_dir) if (cache_dir / s).is_dir()]
    if not subs:
        return None
    return str(cache_dir / subs[0]).replace("\\", "/")


def apply_effect_to_all_captions(draft: dict, template_effect: dict,
                                 skip_texts: set[str] = None) -> int:
    """Replicate a template effect material to all caption segments."""
    skip_texts = skip_texts or set()
    texts = draft.get("materials", {}).get("texts", [])
    text_tracks = [tr for tr in draft.get("tracks", []) if tr.get("type") == "text"]

    template_id = template_effect["id"]
    reference_refs = None
    for tr in text_tracks:
        for seg in tr.get("segments", []):
            refs = seg.get("extra_material_refs", [])
            if template_id in refs:
                reference_refs = list(refs)
                break
        if reference_refs:
            break

    if not reference_refs:
        raise ValueError("No caption segment uses the template_effect")

    n_processed = 0
    for tr in text_tracks:
        for seg in tr.get("segments", []):
            mat = next((t for t in texts if t["id"] == seg.get("material_id")), None)
            if not mat:
                continue
            co = json.loads(mat.get("content", "{}"))
            text = co.get("text", "")
            if not text or text in skip_texts:
                continue
            if template_id in seg.get("extra_material_refs", []):
                continue

            new_effect = copy.deepcopy(template_effect)
            new_effect["id"] = _new_id()
            draft.setdefault("materials", {}).setdefault("effects", []).append(new_effect)

            new_refs = [new_effect["id"] if r == template_id else r for r in reference_refs]
            seg["extra_material_refs"] = new_refs
            n_processed += 1

    return n_processed


def swap_effect(draft: dict, old_effect_id: str, new_effect_id: str,
                new_effect_name: str = None) -> int:
    """Swap all materials.effects entries with old_effect_id -> new_effect_id."""
    new_cache_path = get_effect_cache_path(new_effect_id)
    if not new_cache_path:
        raise ValueError(f"Effect cache not found for {new_effect_id}")

    n = 0
    for e in draft.get("materials", {}).get("effects", []):
        if e.get("effect_id") == old_effect_id:
            e["effect_id"] = new_effect_id
            e["resource_id"] = new_effect_id
            e["path"] = new_cache_path
            if new_effect_name:
                e["name"] = new_effect_name
            n += 1
    return n


def apply_effect_to_segment(draft: dict, segment_idx: int, effect_id: str,
                            track_type: str = "text",
                            effect_name: str = None) -> dict:
    """Apply an effect (like a bubble or art text) to a segment."""
    cache_path = get_effect_cache_path(effect_id)
    if not cache_path:
        raise ValueError(f"Effect {effect_id} cache not found")

    tracks = [tr for tr in draft.get("tracks", []) if tr.get("type") == track_type]
    if not tracks:
        raise ValueError(f"No {track_type} tracks found")
    segments = tracks[0].get("segments", [])
    if segment_idx >= len(segments):
        raise ValueError(f"Segment idx {segment_idx} out of range")
    seg = segments[segment_idx]

    new_eff = {
        "id": _new_id(),
        "effect_id": effect_id,
        "resource_id": effect_id,
        "third_resource_id": effect_id,
        "name": effect_name or f"effect_{effect_id[:8]}",
        "report_name": effect_name or "",
        "type": "text_effect",
        "sub_type": "",
        "path": cache_path,
        "value": 1.0,
        "visible": True,
        "item_effect_type": 0,
        "category_id": "panel-text-flower",
        "category_name": "panel-text-flower",
        "category_key": "text-flower",
        "platform": "all",
        "request_id": "",
        "source_platform": 0,
        "is_local": False,
        "covers": [],
        "version": "",
        "apply_target_type": 0,
        "formula_id": "",
    }
    draft.setdefault("materials", {}).setdefault("effects", []).append(new_eff)

    refs = seg.setdefault("extra_material_refs", [])
    refs.append(new_eff["id"])

    return new_eff

# ─────────────────────────────────────────────────────────────────────
# Post-Export Finalization (ffmpeg logic)
# ─────────────────────────────────────────────────────────────────────

def escape_textfile_path(p: Path) -> str:
    """ffmpeg textfile= path must escape backslash + colon."""
    return str(p).replace("\\", "/").replace(":", "\\:")


def _probe_duration(media_path) -> float:
    """ffprobe format=duration with returncode check."""
    r = subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
         "-of", "default=nw=1:nk=1", str(media_path)],
        capture_output=True, text=True,
    )
    if r.returncode != 0 or not r.stdout.strip():
        raise RuntimeError(
            f"ffprobe duration failed for {media_path}: "
            f"rc={r.returncode} stderr={r.stderr[-200:]}"
        )
    return float(r.stdout.strip())


def _player_safe_vcodec_flags(fps: int = 30, crf: int = 18) -> list:
    """Conservative player-safe libx264 video flags to avoid player playback glitches."""
    return [
        "-c:v", "libx264", "-crf", str(crf), "-preset", "medium",
        "-bf", "0",
        "-vsync", "cfr", "-r", str(fps),
        "-g", str(fps), "-keyint_min", str(fps), "-sc_threshold", "0",
        "-profile:v", "high", "-level", "4.1", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
    ]


def _bgm_loopfill_chain(bgm_dur: float, total: float, vol: float,
                        fade_in: float, fade_out: float,
                        xfade: float = 1.5, loop_fill: bool = True) -> str:
    """Build ffmpeg audio filter graph chain filling target duration."""
    fo_start = max(0.0, total - fade_out)
    if (bgm_dur >= total) or (not loop_fill):
        end = min(bgm_dur, total)
        return (f"[1:a]atrim=0:{end},afade=t=in:st=0:d={fade_in},"
                f"afade=t=out:st={fo_start}:d={fade_out},volume={vol}[a]")
    advance = max(0.1, bgm_dur - xfade)
    n = max(2, math.ceil((total - xfade) / advance))
    parts = ["[1:a]asplit=" + str(n) + "".join(f"[c{i}]" for i in range(n)) + ";"]
    prev = "c0"
    for i in range(1, n):
        out = f"x{i}"
        parts.append(f"[{prev}][c{i}]acrossfade=d={xfade}:c1=tri:c2=tri[{out}];")
        prev = out
    parts.append(f"[{prev}]atrim=0:{total},afade=t=in:st=0:d={fade_in},"
                 f"afade=t=out:st={fo_start}:d={fade_out},volume={vol}[a]")
    return "".join(parts)


def force_mix_bgm(
    input_mp4: Path,
    output_mp4: Path,
    bgm_path: Path,
    bgm_volume: float = 0.25,
    fade_in_sec: float = 0.5,
    fade_out_sec: float = 2.0,
    duration_sec: Optional[float] = None,
    loop_fill: bool = True,
    no_loop=None,
) -> Path:
    """ffmpeg complete replacement of audio track with BGM only."""
    input_mp4 = Path(input_mp4)
    output_mp4 = Path(output_mp4)
    bgm_path = Path(bgm_path)
    
    if duration_sec is None:
        duration_sec = _probe_duration(input_mp4)

    bgm_source_dur = _probe_duration(bgm_path)
    if no_loop is not None:
        loop_fill = not no_loop

    tmp = output_mp4.with_name(output_mp4.stem + "_tmp.mp4")
    audio_chain = _bgm_loopfill_chain(
        bgm_source_dur, duration_sec, bgm_volume,
        fade_in_sec, fade_out_sec, loop_fill=loop_fill,
    )

    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_mp4),
        "-i", str(bgm_path),
        "-filter_complex", audio_chain,
        "-map", "0:v", "-map", "[a]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        "-movflags", "+faststart",
        str(tmp),
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"force_mix_bgm failed: {result.stderr[-500:]}")

    shutil.move(str(tmp), str(output_mp4))
    return output_mp4


def add_outro_card(
    input_mp4: Path,
    output_mp4: Path,
    title_line: str,
    address_line: str,
    extra_line: Optional[str] = None,
    outro_start_sec: float = -5.0,
    outro_end_sec: Optional[float] = None,
    font_path: str = "C\\:/Windows/Fonts/NotoSansTC-Black.otf",
    text_dir: Optional[Path] = None,
) -> Path:
    """Burn outro card text overlays at the end of the video."""
    input_mp4 = Path(input_mp4)
    output_mp4 = Path(output_mp4)
    
    duration_sec = _probe_duration(input_mp4)

    if outro_end_sec is None:
        outro_end_sec = duration_sec
    if outro_start_sec < 0:
        outro_start_sec = duration_sec + outro_start_sec

    text_dir = text_dir or output_mp4.parent / "_outro_txt"
    text_dir.mkdir(exist_ok=True)
    t_title = text_dir / "outro_title.txt"
    t_address = text_dir / "outro_address.txt"
    t_title.write_text(title_line, encoding="utf-8")
    t_address.write_text(address_line, encoding="utf-8")

    tf_title = escape_textfile_path(t_title)
    tf_address = escape_textfile_path(t_address)

    fade_in = 0.4
    fade_out = 0.5
    alpha_expr = (
        f"if(lt(t,{outro_start_sec}),0,"
        f"if(lt(t,{outro_start_sec + fade_in}),(t-{outro_start_sec})/{fade_in},"
        f"if(gt(t,{outro_end_sec - fade_out}),({outro_end_sec}-t)/{fade_out},1)))"
    )
    enable_expr = f"between(t,{outro_start_sec},{outro_end_sec})"

    fc_parts = [
        f"[0:v]"
        f"drawtext=fontfile='{font_path}':textfile='{tf_title}':"
        f"fontsize=64:fontcolor=#FFD700:"
        f"borderw=4:bordercolor=black@0.8:"
        f"box=1:boxcolor=black@0.7:boxborderw=24:"
        f"x=(w-tw)/2:y=h-380:"
        f"alpha='{alpha_expr}':enable='{enable_expr}',"
        f"drawtext=fontfile='{font_path}':textfile='{tf_address}':"
        f"fontsize=44:fontcolor=white:"
        f"borderw=3:bordercolor=black@0.8:"
        f"box=1:boxcolor=black@0.6:boxborderw=18:"
        f"x=(w-tw)/2:y=h-280:"
        f"alpha='{alpha_expr}':enable='{enable_expr}'"
    ]

    if extra_line:
        t_extra = text_dir / "outro_extra.txt"
        t_extra.write_text(extra_line, encoding="utf-8")
        tf_extra = escape_textfile_path(t_extra)
        fc_parts[0] += (
            f","
            f"drawtext=fontfile='{font_path}':textfile='{tf_extra}':"
            f"fontsize=36:fontcolor=white:"
            f"borderw=2:bordercolor=black@0.8:"
            f"box=1:boxcolor=black@0.5:boxborderw=14:"
            f"x=(w-tw)/2:y=h-200:"
            f"alpha='{alpha_expr}':enable='{enable_expr}'"
        )

    fc_parts[0] += "[v]"
    fc = ";".join(fc_parts)

    tmp = output_mp4.with_name(output_mp4.stem + "_outro_tmp.mp4")
    
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_mp4),
        "-filter_complex", fc,
        "-map", "[v]", "-map", "0:a",
        "-c:v", "libx264", "-crf", "18", "-preset", "medium",
        "-profile:v", "high", "-pix_fmt", "yuv420p",
        "-color_primaries", "bt709", "-color_trc", "bt709", "-colorspace", "bt709",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(tmp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"add_outro_card failed: {result.stderr[-500:]}")

    shutil.move(str(tmp), str(output_mp4))
    return output_mp4


def _parse_silencedetect(stderr: str, total: float) -> float:
    """Parse silencedetect stderr output to find the true end of the voice track."""
    starts, ends = [], []
    for line in stderr.splitlines():
        if "silence_start:" in line:
            try:
                starts.append(float(line.split("silence_start:")[1].strip().split()[0]))
            except (ValueError, IndexError):
                pass
        elif "silence_end:" in line:
            try:
                seg = line.split("silence_end:")[1].strip()
                ends.append(float(seg.split("|")[0].strip().split()[0]))
            except (ValueError, IndexError):
                pass
    if starts:
        last_start = starts[-1]
        trailing = (len(ends) < len(starts))
        if not trailing and ends and (total - ends[-1]) < 0.5:
            trailing = True
        if trailing and 0 < last_start < total:
            return round(last_start, 3)
    return round(total, 3)


def detect_voice_end(
    media_path: Path,
    noise_db: float = -30.0,
    min_silence_sec: float = 2.0,
) -> float:
    """Find voice end time by running ffmpeg silencedetect."""
    media_path = Path(media_path)
    total = _probe_duration(media_path)
    r = subprocess.run(
        ["ffmpeg", "-hide_banner", "-nostats", "-i", str(media_path),
         "-af", f"silencedetect=noise={noise_db}dB:d={min_silence_sec}",
         "-f", "null", "-"],
        capture_output=True, text=True,
    )
    return _parse_silencedetect(r.stderr, total)


def reencode_player_safe(
    input_mp4: Path,
    output_mp4: Path,
    fps: int = 30,
    crf: int = 18,
) -> Path:
    """Reencode MP4 to a player-safe format to prevent glitches in native players."""
    input_mp4 = Path(input_mp4)
    output_mp4 = Path(output_mp4)
    
    tmp = output_mp4.with_name(output_mp4.stem + "_psafe_tmp.mp4")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_mp4),
        *_player_safe_vcodec_flags(fps=fps, crf=crf),
        "-c:a", "copy",
        str(tmp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"reencode_player_safe failed: {result.stderr[-500:]}")
    shutil.move(str(tmp), str(output_mp4))
    return output_mp4


def trim_to_voice_end(
    input_mp4: Path,
    output_mp4: Path,
    tail_pad_sec: float = 0.0,
    noise_db: float = -30.0,
    min_silence_sec: float = 2.0,
    player_safe: bool = True,
) -> dict:
    """Trim video timeline to the detected voice end (with optional tail pad)."""
    input_mp4 = Path(input_mp4)
    output_mp4 = Path(output_mp4)
    
    total = _probe_duration(input_mp4)
    voice_end = detect_voice_end(input_mp4, noise_db, min_silence_sec)
    cut_at = round(min(voice_end + tail_pad_sec, total), 3)

    vcodec = _player_safe_vcodec_flags() if player_safe else ["-c:v", "copy"]
    tmp = output_mp4.with_name(output_mp4.stem + "_trim_tmp.mp4")
    cmd = [
        "ffmpeg", "-y", "-hide_banner", "-loglevel", "error",
        "-i", str(input_mp4),
        "-t", f"{cut_at}",
        *vcodec,
        "-c:a", "aac", "-b:a", "192k", "-ar", "44100",
        str(tmp),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"trim_to_voice_end failed: {result.stderr[-500:]}")
    shutil.move(str(tmp), str(output_mp4))
    return {
        "original_dur": total,
        "voice_end": voice_end,
        "trimmed_to": cut_at,
        "trimmed_sec": round(total - cut_at, 3),
    }


def finalize_export(
    capcut_export_mp4: Path,
    final_mp4: Path,
    bgm_path: Path,
    outro_title: str,
    outro_address: str,
    outro_extra: Optional[str] = None,
    bgm_volume: float = 0.25,
) -> dict:
    """One-shot BGM mix + Outro card addition finalizer."""
    capcut_export_mp4 = Path(capcut_export_mp4)
    final_mp4 = Path(final_mp4)
    bgm_path = Path(bgm_path)
    
    print(f"  [1/2] force-mix BGM ({bgm_volume * 100:.0f}% vol)...")
    intermediate = final_mp4.with_name(final_mp4.stem + "_bgm_only.mp4")
    force_mix_bgm(capcut_export_mp4, intermediate, bgm_path, bgm_volume=bgm_volume)

    print(f"  [2/2] add outro card...")
    add_outro_card(intermediate, final_mp4,
                   title_line=outro_title,
                   address_line=outro_address,
                   extra_line=outro_extra)
    intermediate.unlink(missing_ok=True)

    result = subprocess.run(
        ["ffprobe", "-v", "error", "-show_format", "-show_streams", str(final_mp4)],
        capture_output=True, text=True
    )
    stats = {}
    for line in result.stdout.splitlines():
        for k in ("width=", "height=", "duration=", "bit_rate=", "size="):
            if line.startswith(k):
                stats.setdefault(k.rstrip("="), line.split("=", 1)[1])
                break
    stats["file_size_mb"] = final_mp4.stat().st_size // 1024 // 1024
    return stats
