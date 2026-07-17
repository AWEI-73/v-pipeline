"""Cheap material inventory summary for Stage 0 material-first intake."""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping


IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".gif", ".heic", ".heif"}
VIDEO_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".webm"}
AUDIO_EXTS = {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg", ".webm"}


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _kind(path: Path) -> str:
    suffix = path.suffix.casefold()
    if suffix in IMAGE_EXTS:
        return "image"
    if suffix in VIDEO_EXTS:
        return "video"
    if suffix in AUDIO_EXTS:
        return "audio"
    return "other"


def _scope_tokens(value: str) -> list[str]:
    if not value:
        return []
    normalized = value.replace("\n", ";").replace(",", ";")
    return [item.strip().strip('"') for item in normalized.split(";") if item.strip()]


def _resolve_scope_roots(source_dir: Path, decision: Mapping[str, Any]) -> tuple[str, list[Path], list[str]]:
    mode = _clean(decision.get("default_scope")) or "all_materials"
    user_scope = _clean(decision.get("user_scope"))
    if mode != "user_specified" or not user_scope:
        return "all_materials", [source_dir], []

    roots: list[Path] = []
    missing: list[str] = []
    for token in _scope_tokens(user_scope):
        candidate = Path(token)
        if not candidate.is_absolute():
            candidate = source_dir / candidate
        candidate = candidate.resolve()
        if candidate.exists():
            roots.append(candidate)
        else:
            missing.append(token)
    return "user_specified", roots or [source_dir], missing


def _iter_files(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    seen: set[Path] = set()
    for root in roots:
        if root.is_file():
            files = [root]
        else:
            files = [item for item in root.rglob("*") if item.is_file()]
        for item in files:
            resolved = item.resolve()
            if resolved not in seen:
                seen.add(resolved)
                out.append(resolved)
    return sorted(out, key=lambda p: str(p).casefold())


def _folder_key(source_dir: Path, path: Path) -> str:
    try:
        rel = path.relative_to(source_dir)
    except ValueError:
        return "."
    parent = rel.parent
    if str(parent) in {"", "."}:
        return "."
    return parent.parts[0]


def build_material_inventory_summary(
    source_dir: str | Path,
    *,
    material_scan_decision: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    source = Path(source_dir).resolve()
    if not source.exists():
        raise FileNotFoundError(source)
    decision = dict(material_scan_decision or {})
    mode, roots, missing_scope = _resolve_scope_roots(source, decision)
    files = _iter_files(roots)

    kind_counts = Counter(_kind(path) for path in files)
    total_bytes = sum(path.stat().st_size for path in files)
    folder_stats: dict[str, Counter] = defaultdict(Counter)
    duplicate_keys: dict[tuple[str, int], list[str]] = defaultdict(list)
    long_video_candidates: list[dict[str, Any]] = []
    audio_track_candidates: list[dict[str, Any]] = []

    for path in files:
        kind = _kind(path)
        folder_stats[_folder_key(source, path)][kind] += 1
        folder_stats[_folder_key(source, path)]["total"] += 1
        size = path.stat().st_size
        duplicate_keys[(path.name.casefold(), size)].append(str(path))
        if kind == "video":
            if size >= 100 * 1024 * 1024:
                long_video_candidates.append({"path": str(path), "reason": "large_video_file"})
            audio_track_candidates.append({"path": str(path), "reason": "video_may_have_source_audio"})

    possible_duplicates = [
        {"key": name, "size_bytes": size, "paths": paths}
        for (name, size), paths in duplicate_keys.items()
        if len(paths) > 1
    ]
    folder_summary = []
    for folder, stats in sorted(folder_stats.items(), key=lambda item: item[0].casefold()):
        folder_summary.append({
            "folder": folder,
            "total_files": int(stats["total"]),
            "image_count": int(stats["image"]),
            "video_count": int(stats["video"]),
            "audio_count": int(stats["audio"]),
            "other_count": int(stats["other"]),
        })

    questions = []
    if mode == "all_materials":
        questions.append("要全量深篩，還是先只看某些資料夾 / 檔案？")
    if kind_counts["video"]:
        questions.append("影片原音是否重要：要保留講話/掌聲/口令，還是可改由配樂覆蓋？")
    if len(folder_summary) > 1:
        questions.append("資料夾分類是否可信？哪些資料夾一定要優先使用或排除？")

    return {
        "artifact_role": "material_inventory_summary",
        "version": 1,
        "ok": True,
        "source_dir": str(source),
        "scope": {
            "mode": mode,
            "resolved_roots": [str(path) for path in roots],
            "missing_scope_items": missing_scope,
        },
        "scan_depth": _clean(decision.get("scan_depth")) or "quick_inventory_first",
        "counts": {
            "total_files": len(files),
            "images": int(kind_counts["image"]),
            "videos": int(kind_counts["video"]),
            "audio": int(kind_counts["audio"]),
            "other": int(kind_counts["other"]),
            "total_bytes": total_bytes,
        },
        "folder_summary": folder_summary,
        "long_video_candidates": long_video_candidates,
        "audio_track_candidates": audio_track_candidates,
        "possible_duplicates": possible_duplicates,
        "suggested_followup_questions": questions,
        "recommended_next_actions": [
            "review_material_inventory_summary",
            "continue_to_material_map_deep_review",
        ],
        "limitations": [
            "Quick inventory only reads filesystem metadata and extensions.",
            "It does not verify visual content, audio content, or exact video duration.",
        ],
    }


def write_material_inventory_summary(
    source_dir: str | Path,
    out_path: str | Path,
    *,
    material_scan_decision: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    payload = build_material_inventory_summary(
        source_dir,
        material_scan_decision=material_scan_decision,
    )
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return payload
