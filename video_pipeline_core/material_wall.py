"""Material wall coarse-screening artifacts.

The wall is a cheap first-pass visual review surface: photos are batched into a
contact sheet, videos become one strip per asset with multiple keyframes. It
does not decide material_needs coverage; it only narrows candidates for the
later material-map review.
"""
from __future__ import annotations

import json
import math
import subprocess
import os
from pathlib import Path

from PIL import Image, ImageDraw


COARSE_STATUSES = {"keep", "maybe", "reject", "duplicate"}


def video_frame_budget(duration_sec):
    duration = float(duration_sec or 0)
    if duration <= 15:
        return 3
    if duration <= 60:
        return 6
    if duration <= 300:
        return 9
    return 12


def _load_json(path):
    with Path(path).open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write_json(path, payload):
    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _chunks(items, size):
    size = max(1, int(size or 1))
    for i in range(0, len(items), size):
        yield items[i:i + size]


def _existing_image(path):
    if not path:
        return None
    p = Path(path)
    return str(p) if p.exists() else None


def _photo_evidence(entry):
    return _existing_image(entry.get("display_path")) or _existing_image(entry.get("path"))


def _folder_group(entry):
    tags = entry.get("tags_from_path") or []
    if tags:
        return "/".join(str(tag) for tag in tags if str(tag).strip()) or "(root)"
    source = entry.get("path")
    if source:
        parent = os.path.basename(os.path.dirname(str(source)))
        if parent:
            return parent
    return "(root)"


def _extract_wall_frames(entry, out_dir, budget):
    source = entry.get("path")
    duration = (entry.get("metadata") or {}).get("duration_sec")
    if not source or not Path(source).exists() or not duration:
        return []
    try:
        from .keyframe_grid import select_timestamps
        from .platform_tools import resolve_ffmpeg
        ffmpeg = resolve_ffmpeg()
    except Exception:
        return []

    asset_id = entry.get("id") or "asset"
    frame_dir = Path(out_dir) / "frames" / asset_id
    frame_dir.mkdir(parents=True, exist_ok=True)
    frames = []
    for index, ts in enumerate(select_timestamps(duration, budget)):
        frame_path = frame_dir / f"wall_kf_{index + 1:02d}.jpg"
        if not frame_path.exists():
            result = subprocess.run(
                [
                    ffmpeg,
                    "-y",
                    "-ss",
                    f"{ts:.3f}",
                    "-i",
                    str(source),
                    "-frames:v",
                    "1",
                    "-q:v",
                    "3",
                    "-vf",
                    "scale=512:-1",
                    str(frame_path),
                ],
                capture_output=True,
                timeout=60,
            )
            if result.returncode != 0:
                continue
        if frame_path.exists():
            frames.append({"timestamp_sec": ts, "image_path": str(frame_path)})
    return frames


def _select_video_frames(entry, out_dir, frame_extractor=None):
    frames = [
        frame for frame in (entry.get("keyframes") or [])
        if _existing_image(frame.get("image_path"))
    ]
    budget = video_frame_budget((entry.get("metadata") or {}).get("duration_sec"))
    if len(frames) < budget:
        extractor = frame_extractor or _extract_wall_frames
        extra = [
            frame for frame in (extractor(entry, out_dir, budget) or [])
            if _existing_image(frame.get("image_path"))
        ]
        if len(extra) > len(frames):
            frames = extra
    if len(frames) <= budget:
        return frames
    step = len(frames) / budget
    return [frames[min(len(frames) - 1, int(i * step))] for i in range(budget)]


def _fit_cell(img, size):
    cell_w, cell_h = size
    img = img.convert("RGB")
    img.thumbnail((cell_w, cell_h))
    canvas = Image.new("RGB", (cell_w, cell_h), "white")
    x = (cell_w - img.width) // 2
    y = (cell_h - img.height) // 2
    canvas.paste(img, (x, y))
    return canvas


def _draw_label(draw, xy, text):
    x, y = xy
    draw.rectangle((x, y, x + min(260, 8 + len(text) * 7), y + 18), fill=(0, 0, 0))
    draw.text((x + 4, y + 3), text[:36], fill=(255, 255, 255))


def _make_photo_wall(assets, out_path, *, columns=8, cell_size=(180, 120)):
    cols = max(1, min(columns, len(assets)))
    rows = max(1, math.ceil(len(assets) / cols))
    wall = Image.new("RGB", (cols * cell_size[0], rows * cell_size[1]), "white")
    draw = ImageDraw.Draw(wall)
    for i, asset in enumerate(assets):
        row, col = divmod(i, cols)
        x, y = col * cell_size[0], row * cell_size[1]
        with Image.open(asset["image"]) as img:
            wall.paste(_fit_cell(img, cell_size), (x, y))
        _draw_label(draw, (x + 4, y + 4), asset["asset_id"])
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wall.save(out_path, "JPEG", quality=88)


def _make_video_wall(assets, out_path, *, frame_size=(160, 90), label_width=160):
    max_frames = max(len(asset["frames"]) for asset in assets)
    width = label_width + max_frames * frame_size[0]
    height = len(assets) * frame_size[1]
    wall = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(wall)
    for row, asset in enumerate(assets):
        y = row * frame_size[1]
        _draw_label(draw, (4, y + 4), asset["asset_id"])
        for col, frame in enumerate(asset["frames"]):
            x = label_width + col * frame_size[0]
            with Image.open(frame["image_path"]) as img:
                wall.paste(_fit_cell(img, frame_size), (x, y))
            ts = frame.get("timestamp_sec")
            if ts is not None:
                _draw_label(draw, (x + 4, y + 4), f"{float(ts):.1f}s")
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    wall.save(out_path, "JPEG", quality=88)


def build_material_wall_request(db, out_dir, *, photo_batch_size=60, video_batch_size=10,
                                _frame_extractor=None):
    out_dir = Path(out_dir)
    batches = []
    verdict_assets = []

    photos = []
    videos = []
    candidate_groups = {}
    for entry in (db or {}).get("files") or []:
        asset_id = entry.get("id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            continue
        group = _folder_group(entry)
        candidate_groups.setdefault(group, []).append(asset_id)
        if entry.get("type") == "photo":
            image = _photo_evidence(entry)
            if image:
                photos.append({
                    "asset_id": asset_id,
                    "source": entry.get("path"),
                    "image": image,
                    "folder_group": group,
                })
        elif entry.get("type") == "video":
            frames = _select_video_frames(entry, out_dir, frame_extractor=_frame_extractor)
            if frames:
                videos.append({
                    "asset_id": asset_id,
                    "source": entry.get("path"),
                    "duration_sec": (entry.get("metadata") or {}).get("duration_sec"),
                    "frames": frames,
                    "folder_group": group,
                })

    candidate_groups = {
        group: sorted(ids) for group, ids in sorted(candidate_groups.items())
        if ids
    }
    for asset in photos + videos:
        siblings = candidate_groups.get(asset["folder_group"], [])
        asset["sibling_asset_ids"] = [value for value in siblings if value != asset["asset_id"]]

    for index, group in enumerate(_chunks(photos, photo_batch_size), start=1):
        wall_image = out_dir / f"photo_wall_{index:02d}.jpg"
        _make_photo_wall(group, wall_image)
        batches.append({
            "batch_id": f"photo_wall_{index:02d}",
            "type": "photo_wall",
            "wall_image": str(wall_image),
            "assets": group,
        })

    for index, group in enumerate(_chunks(videos, video_batch_size), start=1):
        wall_image = out_dir / f"video_wall_{index:02d}.jpg"
        _make_video_wall(group, wall_image)
        batches.append({
            "batch_id": f"video_wall_{index:02d}",
            "type": "video_wall",
            "wall_image": str(wall_image),
            "assets": group,
        })

    for asset in photos + videos:
        verdict_assets.append({
            "asset_id": asset["asset_id"],
            "coarse_status": None,
            "visual_role": [],
            "quality": None,
            "duplicate_of": None,
            "usable_ranges": [],
            "notes": None,
        })

    return {
        "artifact_role": "material_wall_request",
        "version": 1,
        "next_action": "await_material_wall_review",
        "policy": {
            "photo_batch_size": int(photo_batch_size),
            "video_batch_size": int(video_batch_size),
            "video_frame_budget": {
                "0-15s": 3,
                "15-60s": 6,
                "60-300s": 9,
                "300s+": 12,
            },
        },
        "candidate_groups": candidate_groups,
        "batches": batches,
        "verdict_template": {
            "artifact_role": "material_wall_review_verdict",
            "version": 1,
            "assets": verdict_assets,
        },
    }


def write_material_wall_request(db_path, out_dir, out_path, *, photo_batch_size=60,
                                video_batch_size=10, limit=None):
    db = _load_json(db_path) if not isinstance(db_path, dict) else db_path
    if limit is not None:
        db = dict(db)
        db["files"] = list(db.get("files") or [])[:max(0, int(limit))]
    request = build_material_wall_request(
        db,
        out_dir,
        photo_batch_size=photo_batch_size,
        video_batch_size=video_batch_size,
    )
    _write_json(out_path, request)
    return {
        "ok": True,
        "material_wall_request": str(Path(out_path)),
        "batch_count": len(request["batches"]),
        "asset_count": len(request["verdict_template"]["assets"]),
    }


def _wall_asset_ids(request):
    ids = []
    seen = set()
    for batch in (request or {}).get("batches") or []:
        for asset in batch.get("assets") or []:
            asset_id = asset.get("asset_id") if isinstance(asset, dict) else None
            if isinstance(asset_id, str) and asset_id and asset_id not in seen:
                ids.append(asset_id)
                seen.add(asset_id)
    return ids


def slice_material_db_from_wall_request(db, request):
    """Return a DB copy limited to assets that appeared in a wall request."""
    ids = set(_wall_asset_ids(request))
    if not ids:
        raise ValueError("material wall request does not contain any asset ids")
    sliced = dict(db or {})
    sliced["files"] = [
        entry for entry in (db or {}).get("files") or []
        if entry.get("id") in ids
    ]
    return sliced


def slice_material_db_from_wall_request_file(db_path, request_path, out_path):
    sliced = slice_material_db_from_wall_request(_load_json(db_path), _load_json(request_path))
    _write_json(out_path, sliced)
    return {
        "ok": True,
        "materials_db": str(Path(out_path)),
        "asset_count": len(sliced.get("files") or []),
    }


def apply_material_wall_review(db, verdict):
    by_id = {
        entry.get("id"): entry for entry in (db or {}).get("files") or []
        if entry.get("id")
    }
    visual_ids = {
        entry.get("id") for entry in (db or {}).get("files") or []
        if entry.get("id") and entry.get("type") in {"photo", "video"}
    }
    verdict_items = (verdict or {}).get("assets") or []
    indexed = {}
    for index, item in enumerate(verdict_items):
        if not isinstance(item, dict):
            raise ValueError(f"material wall verdict asset {index} must be an object")
        asset_id = item.get("asset_id")
        if asset_id not in by_id:
            raise ValueError(f"material wall verdict asset {index} references unknown asset_id {asset_id!r}")
        if asset_id in indexed:
            raise ValueError(f"duplicate material wall decision for asset_id {asset_id!r}")
        indexed[asset_id] = item

    missing = sorted(visual_ids - set(indexed))
    if missing:
        raise ValueError(f"missing material wall decision for asset(s): {missing}")

    for asset_id in sorted(indexed):
        item = indexed[asset_id]
        status = item.get("coarse_status")
        if status not in COARSE_STATUSES:
            raise ValueError(
                f"material wall verdict asset {asset_id!r} has invalid coarse_status {status!r}")
        visual_evidence = item.get("visual_evidence")
        if status in {"keep", "maybe"} and not (
            isinstance(visual_evidence, list)
            and any(isinstance(value, str) and value.strip() for value in visual_evidence)
        ):
            raise ValueError(
                f"material wall verdict asset {asset_id!r} with {status!r} "
                f"requires non-empty visual_evidence")
        why_not_selected = item.get("why_not_selected")
        if status in {"reject", "duplicate"} and not (
            isinstance(why_not_selected, str) and why_not_selected.strip()
        ):
            raise ValueError(
                f"material wall verdict asset {asset_id!r} with {status!r} "
                f"requires why_not_selected")
        duplicate_of = item.get("duplicate_of")
        if status == "duplicate" and duplicate_of not in by_id:
            raise ValueError(
                f"material wall verdict asset {asset_id!r} duplicate_of must "
                f"reference an existing asset_id")
        entry = by_id[asset_id]
        entry["material_wall_review"] = {
            "coarse_status": status,
            "visual_role": item.get("visual_role") or [],
            "quality": item.get("quality"),
            "duplicate_of": item.get("duplicate_of"),
            "usable_ranges": item.get("usable_ranges") or [],
            "visual_evidence": visual_evidence or [],
            "why_not_selected": why_not_selected,
            "notes": item.get("notes"),
            "reviewer": verdict.get("reviewer"),
            "at": verdict.get("at"),
        }
        entry["selected_for_material_map"] = status in {"keep", "maybe"}
    return db


def apply_material_wall_review_file(db_path, verdict_path, out_path):
    reviewed = apply_material_wall_review(_load_json(db_path), _load_json(verdict_path))
    _write_json(out_path, reviewed)
    selected = sum(1 for item in reviewed.get("files", []) if item.get("selected_for_material_map"))
    reviewed_count = sum(1 for item in reviewed.get("files", []) if item.get("material_wall_review"))
    return {
        "ok": True,
        "materials_db": str(Path(out_path)),
        "reviewed": reviewed_count,
        "selected_for_material_map": selected,
    }
