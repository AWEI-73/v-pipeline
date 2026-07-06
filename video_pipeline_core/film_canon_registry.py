"""Film canon registry and product route selector."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from .graduation_film_blueprint_catalog import write_graduation_film_real_source_dry_run


DAILY_KIDS_SECTION_IDS = [
    "opening_memory_hook",
    "daily_life_montage",
    "milestone_moments",
    "cute_funny_moments",
    "family_interaction",
    "closing_memory_note",
]

DAILY_KIDS_MODULE_IDS = [
    "eating",
    "playing",
    "learning",
    "family",
    "outdoor",
    "school",
    "birthday_or_special_event",
    "random_cute_optional",
]

_DAILY_KIDS_TOKENS: dict[str, tuple[str, ...]] = {
    "eating": ("eat", "eating", "meal", "breakfast", "lunch", "dinner", "\u5403", "\u65e9\u9910", "\u5348\u9910"),
    "playing": ("play", "playing", "toy", "blocks", "\u73a9", "\u73a9\u5177"),
    "learning": ("learn", "learning", "word", "draw", "read", "\u5b78", "\u756b", "\u8b80"),
    "family": ("family", "mom", "dad", "grandma", "grandpa", "\u5bb6\u4eba", "\u5abd\u5abd", "\u7238\u7238", "\u963f\u5b24"),
    "outdoor": ("outdoor", "park", "walk", "trip", "\u6236\u5916", "\u516c\u5712", "\u6563\u6b65"),
    "school": ("school", "kindergarten", "class", "\u5b78\u6821", "\u5e7c\u5152\u5712", "\u73ed\u7d1a"),
    "birthday_or_special_event": ("birthday", "cake", "event", "party", "\u751f\u65e5", "\u86cb\u7cd5", "\u6d3b\u52d5"),
    "random_cute_optional": ("cute", "random", "dance", "smile", "\u53ef\u611b", "\u8df3\u821e", "\u7b11"),
}

_MEDIA_EXTENSIONS = {
    ".mp4",
    ".mov",
    ".mkv",
    ".avi",
    ".m4v",
    ".webm",
    ".jpg",
    ".jpeg",
    ".png",
    ".wav",
    ".mp3",
    ".m4a",
}


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def list_supported_film_types() -> list[str]:
    return ["graduation_training_film", "daily_kids_memory_film"]


def get_film_canon_route(film_type: str) -> dict[str, Any]:
    if film_type == "graduation_training_film":
        return {
            "film_type": "graduation_training_film",
            "name": "Graduation Training Film",
            "selector": "graduation_film_blueprint_catalog",
            "artifact_mode": "compatibility_graduation_artifacts",
        }
    if film_type == "daily_kids_memory_film":
        return {
            "film_type": "daily_kids_memory_film",
            "name": "Daily Kids Memory Film",
            "selector": "film_canon_registry",
            "artifact_mode": "common_film_type_artifacts",
        }
    raise ValueError(f"unsupported film_type: {film_type}")


def _scan_materials(source_root: str | Path | None) -> list[dict[str, Any]]:
    if not source_root:
        return []
    root = Path(source_root)
    if not root.exists() or not root.is_dir():
        return []
    resolved = root.resolve()
    materials: list[dict[str, Any]] = []
    for path in resolved.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in _MEDIA_EXTENSIONS:
            continue
        try:
            relative = path.resolve().relative_to(resolved).as_posix()
        except ValueError:
            continue
        materials.append({
            "source_relative_path": relative,
            "file_name": path.name,
            "extension": path.suffix.casefold(),
            "byte_size": path.stat().st_size,
        })
    return sorted(materials, key=lambda item: item["source_relative_path"].casefold())


def _daily_kids_canon() -> dict[str, Any]:
    return {
        "artifact_role": "film_canon",
        "version": 1,
        "film_type": "daily_kids_memory_film",
        "sections": [
            {
                "section_id": section_id,
                "retargetable": section_id in {"opening_memory_hook", "closing_memory_note"},
            }
            for section_id in DAILY_KIDS_SECTION_IDS
        ],
        "catalog_modules": [
            {"module_id": module_id, "required": module_id != "random_cute_optional"}
            for module_id in DAILY_KIDS_MODULE_IDS
        ],
        "rules": [
            "Warm or light music is preferred.",
            "Source laughter or child speech may be preserved if intelligible.",
            "Narration is optional.",
            "Date/place/title captions are useful; full subtitles are not always required.",
            "Human/family review remains required before external sharing.",
        ],
    }


def _daily_kids_module_for(material: Mapping[str, Any]) -> tuple[str, list[str], str]:
    text = f"{material.get('source_relative_path', '')} {material.get('file_name', '')}".casefold()
    for module_id, tokens in _DAILY_KIDS_TOKENS.items():
        matched = [token for token in tokens if token.casefold() in text]
        if matched:
            return module_id, matched, "filename_or_folder_signal"
    return "random_cute_optional", [], "agent_default_random_cute_optional"


def _daily_kids_catalog(source_root: str | Path | None) -> dict[str, Any]:
    materials = _scan_materials(source_root)
    modules = [
        {"module_id": module_id, "material_assignments": [], "coverage_status": "missing_material"}
        for module_id in DAILY_KIDS_MODULE_IDS
    ]
    by_id = {module["module_id"]: module for module in modules}
    for material in materials:
        module_id, signals, reason = _daily_kids_module_for(material)
        by_id[module_id]["material_assignments"].append({
            **material,
            "module_id": module_id,
            "matched_signals": signals,
            "confidence": "medium" if signals else "low",
            "agent_filled": True,
            "authority": "agent_filled",
            "needs_human_confirmation": True,
            "assignment_reason": reason,
        })
        by_id[module_id]["coverage_status"] = "agent_filled_needs_human_confirmation"
    agent_count = sum(len(module["material_assignments"]) for module in modules)
    return {
        "artifact_role": "catalog_map",
        "version": 1,
        "film_type": "daily_kids_memory_film",
        "source_root": _clean(source_root),
        "modules": modules,
        "summary": {
            "module_count": len(modules),
            "material_count": len(materials),
            "media_count": len(materials),
            "agent_filled_count": agent_count,
            "needs_human_confirmation_count": agent_count,
            "missing_module_count": sum(1 for module in modules if not module["material_assignments"]),
        },
    }


def _daily_kids_blueprint(canon: Mapping[str, Any], catalog: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_role": "film_blueprint",
        "version": 1,
        "film_type": "daily_kids_memory_film",
        "theme": "\u6bcf\u5929\u7684\u5c0f\u8a18\u61b6\uff0c\u7d44\u6210\u9577\u5927\u7684\u6a23\u5b50",
        "canon_section_order": [section["section_id"] for section in canon["sections"]],
        "module_order": DAILY_KIDS_MODULE_IDS,
        "music_intent": "warm_light_music",
        "caption_policy": "date_place_title_captions_preferred_full_subtitles_optional",
        "catalog_summary": catalog["summary"],
    }


def _daily_kids_story_shell() -> dict[str, Any]:
    return {
        "artifact_role": "story_shell",
        "version": 1,
        "film_type": "daily_kids_memory_film",
        "title": "\u6bcf\u5929\u90fd\u5728\u9577\u5927",
        "theme": "\u65e5\u5e38\u5c0f\u7247\u6bb5\u7684\u6eab\u6696\u8a18\u61b6",
        "opening_memory_hook": {
            "hook": "\u5f9e\u4e00\u500b\u7b11\u5bb9\u958b\u59cb\uff0c\u770b\u898b\u4e00\u5929\u4e00\u5929\u7684\u9577\u5927",
            "authority": "agent_filled",
            "needs_human_confirmation": True,
        },
        "closing_memory_note": {
            "payoff": "\u9019\u4e9b\u5c0f\u5c0f\u65e5\u5e38\uff0c\u5c31\u662f\u5bb6\u4eba\u60f3\u7559\u4f4f\u7684\u6642\u9593",
            "authority": "agent_filled",
            "needs_human_confirmation": True,
        },
    }


def _representative_paths(catalog: Mapping[str, Any]) -> dict[str, list[str]]:
    return {
        module["module_id"]: [
            item["source_relative_path"]
            for item in (module.get("material_assignments") or [])[:3]
        ]
        for module in catalog.get("modules", [])
    }


def _daily_kids_review_packet(canon: Mapping[str, Any], blueprint: Mapping[str, Any], story: Mapping[str, Any], catalog: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_role": "film_route_review_packet",
        "version": 1,
        "film_type": "daily_kids_memory_film",
        "rendered": False,
        "human_approval_written": False,
        "canon_sections": [section["section_id"] for section in canon["sections"]],
        "catalog_modules": [module["module_id"] for module in catalog["modules"]],
        "catalog_summary": catalog["summary"],
        "representative_source_relative_paths": _representative_paths(catalog),
        "story_shell": {
            "title": story["title"],
            "theme": story["theme"],
            "hook": story["opening_memory_hook"]["hook"],
            "payoff": story["closing_memory_note"]["payoff"],
        },
        "review_required": [
            "family_human_review_before_external_sharing",
            "confirm_agent_filled_catalog_assignments",
            "confirm_laughter_or_child_speech_intelligibility_if_used",
        ],
    }


def _daily_kids_review_markdown(packet: Mapping[str, Any]) -> str:
    module_lines = "\n".join(
        f"- {module}: {packet['catalog_summary']['agent_filled_count'] if module == 'all_agent_filled' else len(packet['representative_source_relative_paths'].get(module) or [])} examples"
        for module in packet["catalog_modules"]
    )
    return "\n".join([
        "# Daily Kids Memory Film Dry Run Review Packet",
        "",
        f"- Film type: {packet['film_type']}",
        f"- Title: {packet['story_shell']['title']}",
        f"- Theme: {packet['story_shell']['theme']}",
        "- Rendered: false",
        "- Human approval written: false",
        "",
        "## Catalog Modules",
        "",
        module_lines,
        "",
        "## Review Caveats",
        "",
        "- Fixture-only route; no real private family material is required.",
        "- Human/family review remains required before external sharing.",
        "- This dry run does not render final.mp4.",
        "- This dry run does not write story_human_review_decision.json.",
        "",
    ])


def write_daily_kids_memory_dry_run(source_root: str | Path | None, out_dir: str | Path) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    canon = _daily_kids_canon()
    catalog = _daily_kids_catalog(source_root)
    blueprint = _daily_kids_blueprint(canon, catalog)
    story = _daily_kids_story_shell()
    packet = _daily_kids_review_packet(canon, blueprint, story, catalog)
    outputs = {
        "film_canon.json": canon,
        "film_blueprint.json": blueprint,
        "story_shell.json": story,
        "catalog_map.json": catalog,
        "review_packet.json": packet,
    }
    for name, artifact in outputs.items():
        (out_root / name).write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (out_root / "review_packet.md").write_text(
        _daily_kids_review_markdown(packet),
        encoding="utf-8",
    )
    return {
        "ok": True,
        "film_type": "daily_kids_memory_film",
        "out_dir": str(out_root),
        "artifacts": [*outputs.keys(), "review_packet.md"],
        "canon_sections": packet["canon_sections"],
        "catalog_modules": packet["catalog_modules"],
        "catalog_summary": catalog["summary"],
        "review_packet": str(out_root / "review_packet.json"),
        "rendered": False,
        "human_approval_written": False,
    }


def write_film_canon_route_dry_run(film_type: str, source_root: str | Path | None, out_dir: str | Path) -> dict[str, Any]:
    route = get_film_canon_route(film_type)
    if route["film_type"] == "graduation_training_film":
        summary = write_graduation_film_real_source_dry_run(source_root, out_dir)
        return {
            **summary,
            "film_type": "graduation_training_film",
            "review_packet": str(Path(out_dir) / "graduation_real_source_review_packet.json"),
        }
    if route["film_type"] == "daily_kids_memory_film":
        return write_daily_kids_memory_dry_run(source_root, out_dir)
    raise ValueError(f"unsupported film_type: {film_type}")
