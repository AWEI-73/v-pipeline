"""Multi-material understanding matrix before Material Wall decisions.

This module is an observation layer. It collects cheap visual/audio/file
evidence so a reviewer can write better Material Wall decisions; it must not
mark needs covered or promote assets into BUILD by itself.
"""
from __future__ import annotations

import json
import math
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from PIL import Image, ImageDraw

from .platform_tools import resolve_ffmpeg


PHOTO_TYPES = {"photo", "image"}
VIDEO_TYPES = {"video"}
FINAL_EXPORT_MARKERS = ("final", "master", "export", "render", "成品", "輸出", "完稿")
ROLE_KEYWORDS = {
    "opening": ("opening", "intro", "entrance", "establish", "空拍", "入口", "開場"),
    "training": ("training", "practice", "pole", "換桿", "訓練", "實習", "操作", "工安"),
    "interaction": ("interaction", "daily", "互動", "生活", "討論", "花絮"),
    "ceremony": ("ceremony", "graduation", "結訓", "典禮", "頒獎"),
    "closing": ("closing", "ending", "group", "合照", "隊呼", "收尾"),
}


def _write_json(path: Path, payload: Mapping[str, Any]):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _media_type(entry: Mapping[str, Any]) -> str:
    raw = _clean(entry.get("type") or entry.get("asset_type")).lower()
    if raw in PHOTO_TYPES:
        return "photo"
    if raw in VIDEO_TYPES:
        return "video"
    suffix = Path(_clean(entry.get("path"))).suffix.lower()
    if suffix in {".jpg", ".jpeg", ".png", ".heic", ".heif"}:
        return "photo"
    if suffix in {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}:
        return "video"
    return raw or "unknown"


def _duration(entry: Mapping[str, Any]) -> float:
    metadata = entry.get("metadata") if isinstance(entry.get("metadata"), Mapping) else {}
    try:
        return float(metadata.get("duration_sec") or entry.get("duration_sec") or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _text_hint(entry: Mapping[str, Any]) -> str:
    parts = []
    path = _clean(entry.get("path"))
    if path:
        parts.append(path)
    tags = entry.get("tags_from_path") or []
    if isinstance(tags, list):
        parts.extend(str(tag) for tag in tags)
    caption = _clean(entry.get("vlm_caption") or entry.get("caption"))
    if caption:
        parts.append(caption)
    return " / ".join(parts).lower()


def _role_hints(entry: Mapping[str, Any]) -> list[str]:
    text = _text_hint(entry)
    roles = []
    for role, keywords in ROLE_KEYWORDS.items():
        if any(keyword.lower() in text for keyword in keywords):
            roles.append(role)
    return roles


def _risk_flags(entry: Mapping[str, Any], seen_names: set[str]) -> list[str]:
    path = Path(_clean(entry.get("path")))
    text = str(path).lower()
    flags = []
    if any(marker.lower() in text for marker in FINAL_EXPORT_MARKERS):
        flags.append("looks_like_finished_export")
    if path.name.lower() in seen_names:
        flags.append("possible_duplicate_name")
    if path and not path.is_file():
        flags.append("source_missing")
    if _media_type(entry) == "unknown":
        flags.append("unsupported_media_type")
    return flags


def _timestamps(duration_sec: float, frame_budget: int) -> list[float]:
    if duration_sec <= 0:
        return [0.0]
    count = max(1, int(frame_budget or 1))
    if count == 1:
        return [round(duration_sec / 2.0, 3)]
    step = duration_sec / (count + 1)
    return [round(step * (index + 1), 3) for index in range(count)]


def _extract_frame(source: str | Path, timestamp_sec: float, out_path: str | Path) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    proc = subprocess.run(
        [
            resolve_ffmpeg(),
            "-y",
            "-ss",
            f"{float(timestamp_sec):.3f}",
            "-i",
            str(source),
            "-frames:v",
            "1",
            "-q:v",
            "3",
            "-vf",
            "scale=512:-1",
            str(out),
        ],
        capture_output=True,
        text=True,
        timeout=120,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or "frame extraction failed")
    return str(out)


def _audio_evidence(entry: Mapping[str, Any]) -> dict[str, Any]:
    media_type = _media_type(entry)
    if media_type != "video":
        return {
            "available": False,
            "source": "not_video",
            "rough_audio_type": "none",
        }
    return {
        "available": True,
        "source": "container_unprobed",
        "rough_audio_type": "unknown_until_soundtrack_probe_or_asr",
        "recommendation": "run soundtrack_probe or ASR only for selected/reviewed assets",
    }


def _contact_sheet(assets: list[dict[str, Any]], out_path: Path) -> str:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    thumbs = []
    for asset in assets:
        visual = asset.get("visual_evidence") or {}
        photo = visual.get("photo")
        frames = visual.get("keyframes") or []
        image = photo or (frames[0].get("image_path") if frames else None)
        if image:
            thumbs.append((asset.get("asset_id"), image))

    if not thumbs:
        Image.new("RGB", (640, 180), "#f6f7fb").save(out_path)
        return str(out_path)

    thumb_w, thumb_h, label_h = 180, 102, 28
    cols = min(5, max(1, len(thumbs)))
    rows = math.ceil(len(thumbs) / cols)
    sheet = Image.new("RGB", (cols * thumb_w, rows * (thumb_h + label_h)), "#f6f7fb")
    draw = ImageDraw.Draw(sheet)
    for index, (asset_id, image_path) in enumerate(thumbs):
        x = (index % cols) * thumb_w
        y = (index // cols) * (thumb_h + label_h)
        try:
            img = Image.open(image_path).convert("RGB")
            img.thumbnail((thumb_w, thumb_h))
            sheet.paste(img, (x + (thumb_w - img.width) // 2, y + (thumb_h - img.height) // 2))
        except Exception:
            draw.rectangle([x, y, x + thumb_w - 1, y + thumb_h - 1], fill="#d9dee8")
            draw.text((x + 8, y + 42), "preview unavailable", fill="#526070")
        draw.rectangle([x, y + thumb_h, x + thumb_w - 1, y + thumb_h + label_h - 1], fill="#ffffff")
        draw.text((x + 8, y + thumb_h + 7), str(asset_id)[:24], fill="#172033")
    sheet.save(out_path, "JPEG", quality=88)
    return str(out_path)


def _asset_entry(
    entry: Mapping[str, Any],
    *,
    out_dir: Path,
    frame_budget: int,
    frame_extractor: Callable[[str | Path, float, str | Path], str] | None,
    seen_names: set[str],
) -> dict[str, Any]:
    asset_id = _clean(entry.get("id") or entry.get("asset_id"))
    path = _clean(entry.get("path") or entry.get("source_path"))
    media_type = _media_type(entry)
    duration = _duration(entry)
    risk_flags = _risk_flags(entry, seen_names)
    if path:
        seen_names.add(Path(path).name.lower())

    visual: dict[str, Any] = {
        "caption_hint": _clean(entry.get("vlm_caption") or entry.get("caption")),
        "evidence_level": "file_and_frame_observation",
    }
    if media_type == "photo":
        visual["photo"] = path
    elif media_type == "video" and path and Path(path).is_file():
        frames = []
        for index, ts in enumerate(_timestamps(duration, frame_budget), start=1):
            frame_path = out_dir / "material_understanding_frames" / asset_id / f"kf_{index:02d}.jpg"
            try:
                image_path = (frame_extractor or _extract_frame)(path, ts, frame_path)
                frames.append({"timestamp_sec": ts, "image_path": str(image_path)})
            except Exception as exc:
                risk_flags.append("frame_extraction_failed")
                frames.append({"timestamp_sec": ts, "error": str(exc)})
                break
        visual["keyframes"] = frames
    else:
        visual["keyframes"] = []

    return {
        "asset_id": asset_id,
        "source_path": path,
        "media_type": media_type,
        "duration_sec": duration,
        "folder_tags": entry.get("tags_from_path") or [],
        "role_hints": _role_hints(entry),
        "risk_flags": sorted(set(risk_flags)),
        "visual_evidence": visual,
        "audio_evidence": _audio_evidence(entry),
        "decision_scope": "observation_only_not_material_truth",
        "next_review_action": "review_material_wall_decision",
    }


def build_material_understanding_matrix(
    materials_db: Mapping[str, Any],
    *,
    out_dir: str | Path,
    max_assets: int = 24,
    frame_budget: int = 3,
    frame_extractor: Callable[[str | Path, float, str | Path], str] | None = None,
) -> dict[str, Any]:
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    files = [
        item for item in (materials_db.get("files") or [])
        if isinstance(item, Mapping) and _clean(item.get("id") or item.get("asset_id"))
    ][:max(1, int(max_assets or 1))]

    seen_names: set[str] = set()
    assets = [
        _asset_entry(
            item,
            out_dir=out,
            frame_budget=frame_budget,
            frame_extractor=frame_extractor,
            seen_names=seen_names,
        )
        for item in files
    ]
    contact_sheet = _contact_sheet(assets, out / "material_understanding_contact_sheet.jpg")
    matrix = {
        "artifact_role": "material_understanding_matrix",
        "version": 1,
        "asset_count": len(assets),
        "source_artifact": materials_db.get("artifact_role") or "materials_db",
        "visual": {
            "contact_sheet": str(contact_sheet),
            "frames_dir": str(out / "material_understanding_frames"),
        },
        "assets": assets,
        "next_action": "write_or_review_material_wall_verdict",
        "limitations": [
            "Role hints come from filenames/folders/captions and are not material truth.",
            "Audio evidence is rough until selected assets receive soundtrack_probe or ASR.",
            "Material needs are not covered until Material Wall/Map review applies accepted edges.",
        ],
    }
    _write_json(out / "material_understanding_matrix.json", matrix)
    return matrix


def build_material_understanding_matrix_file(
    materials_db_path: str | Path,
    *,
    out_dir: str | Path,
    max_assets: int = 24,
    frame_budget: int = 3,
) -> dict[str, Any]:
    db = json.loads(Path(materials_db_path).read_text(encoding="utf-8-sig"))
    return build_material_understanding_matrix(
        db,
        out_dir=out_dir,
        max_assets=max_assets,
        frame_budget=frame_budget,
    )
