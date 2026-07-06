"""Graduation film canon, blueprint, and training catalog dry-run helpers."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping


CANON_SECTION_IDS = [
    "opening_story",
    "training_mv_catalog",
    "supervisor_speech",
    "teacher_class_intro",
    "closing_story",
]

TRAINING_MODULE_IDS = [
    "basic_training",
    "advanced_training",
    "certification",
    "physical_activity",
    "encouragement_activity",
    "daily_life_optional",
    "supervisor_speech",
    "teacher_class_intro",
    "closing_story",
    "special_activity",
]

_MODULE_TOKENS: dict[str, tuple[str, ...]] = {
    "basic_training": ("basic", "foundation", "drill", "\u57fa\u790e", "\u57fa\u672c", "\u5de5\u5b89", "\u9ad4\u611f", "\u62d6\u62c9\u96fb\u7e9c"),
    "advanced_training": ("advanced", "high-risk", "teamwork", "tactical", "\u9032\u968e", "\u9ad8\u968e", "\u63db\u687f", "\u6d3b\u7dda", "\u767b\u9ad8"),
    "certification": ("cert", "certification", "test", "exam", "award", "license", "\u6aa2\u5b9a", "\u6e2c\u9a57", "\u8b49\u7167", "\u8a8d\u8b49", "\u9812\u734e"),
    "physical_activity": ("physical", "rope", "run", "fitness", "\u9ad4\u80fd", "\u904b\u52d5"),
    "encouragement_activity": ("encouragement", "cheer", "morale", "\u52f5\u9032", "\u9f13\u52f5", "\u58eb\u6c23"),
    "daily_life_optional": ("daily", "life", "breakfast", "lunch", "dorm", "\u751f\u6d3b", "\u65e5\u5e38", "\u65e9\u9910", "\u5348\u9910", "\u5bbf\u820d"),
    "supervisor_speech": ("\u4e3b\u4efb", "\u4e3b\u7ba1", "\u52c9\u52f5", "\u81f4\u8a5e"),
    "teacher_class_intro": ("\u8001\u5e2b", "\u5c0e\u5e2b", "\u6559\u5e2b", "\u73ed\u7d1a", "\u5404\u73ed"),
    "closing_story": ("\u611f\u8b1d", "\u7d50\u5c3e", "\u7562\u696d", "\u7d50\u8a13"),
    "special_activity": ("special", "event", "activity", "night", "\u7279\u5225", "\u6d3b\u52d5"),
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

_ARTIFACT_NAMES = [
    "graduation_film_canon.json",
    "graduation_film_blueprint.json",
    "story_shell.json",
    "training_catalog_map.json",
    "story_retargeting_notes.json",
    "graduation_dry_run_review_packet.md",
    "graduation_dry_run_review_packet.json",
]

_REAL_SOURCE_ARTIFACT_NAMES = [
    "graduation_film_canon.json",
    "graduation_film_blueprint_A.json",
    "graduation_film_blueprint_B.json",
    "story_shell_A.json",
    "story_shell_B.json",
    "training_catalog_map.real_source.json",
    "story_retarget_diff_A_to_B.json",
    "production_readiness_plan.json",
    "opener_closer_design_handoff.json",
    "audio_subtitle_review_requirements.json",
    "graduation_real_source_review_packet.md",
    "graduation_real_source_review_packet.json",
]


def _clean(value: Any, default: str = "") -> str:
    if value is None:
        return default
    text = str(value).strip()
    return text or default


def _fixture_title(brief: Mapping[str, Any]) -> str:
    return _clean(brief.get("title"), "\u7d50\u8a13\u5f71\u7247\u6545\u4e8b\u6bbc")


def _fixture_theme(brief: Mapping[str, Any]) -> str:
    return _clean(brief.get("theme") or brief.get("story_theme"), "\u5f9e\u8a13\u7df4\u5230\u6210\u9577")


def graduation_film_canon() -> dict[str, Any]:
    sections = [
        {
            "section_id": "opening_story",
            "role": "story_shell_opening",
            "retargetable": True,
            "rule": "\u6545\u4e8b\u5f0f\u958b\u5834\uff0c\u4e0d\u662f\u7d14\u767d\u5b57\u5361",
        },
        {
            "section_id": "training_mv_catalog",
            "role": "longest_body_section",
            "retargetable": False,
            "rule": "\u6700\u9577\u4e3b\u9ad4\uff1b\u4ee5\u8a13\u7df4\u6a21\u7d44\u76ee\u9304\u7d44\u7e54\u7d20\u6750",
        },
        {
            "section_id": "supervisor_speech",
            "role": "source_speech_section",
            "retargetable": False,
            "rule": "\u4fdd\u7559\u6709\u7528\u7684\u771f\u5be6\u81f4\u8a5e\uff0c\u9700\u5b57\u5e55\u8207\u53ef\u61c2\u5ea6\u8b49\u64da",
        },
        {
            "section_id": "teacher_class_intro",
            "role": "readable_identity_section",
            "retargetable": False,
            "rule": "\u53ef\u7528\u97f3\u6a02\u8207\u6548\u679c\uff0c\u4f46\u5e2b\u9577\u8207\u73ed\u7d1a\u8cc7\u8a0a\u5fc5\u9808\u53ef\u8b80",
        },
        {
            "section_id": "closing_story",
            "role": "story_shell_closing",
            "retargetable": True,
            "rule": "\u6545\u4e8b\u5f0f\u6536\u675f\uff0c\u4e0d\u662f\u7d14\u767d\u5b57\u5361",
        },
    ]
    modules = [
        {
            "module_id": module_id,
            "required": module_id != "daily_life_optional",
            "extensible": module_id == "special_activity",
        }
        for module_id in TRAINING_MODULE_IDS
    ]
    return {
        "artifact_role": "graduation_film_canon",
        "version": 1,
        "sections": sections,
        "longest_body_section": "training_mv_catalog",
        "training_mv_catalog": {
            "section_id": "training_mv_catalog",
            "music_policy": "hot_blooded_music_mainly_here",
            "modules": modules,
        },
        "retargeting_policy": {
            "stable_core": ["training_mv_catalog"],
            "retargetable_shell": ["opening_story", "closing_story", "transition_logic", "module_ordering_emphasis"],
        },
    }


def _scan_source_materials(source_root: str | Path | None) -> list[dict[str, Any]]:
    if not source_root:
        return []
    root = Path(source_root)
    if not root.exists() or not root.is_dir():
        return []
    resolved_root = root.resolve()
    materials: list[dict[str, Any]] = []
    for path in resolved_root.rglob("*"):
        if not path.is_file() or path.suffix.casefold() not in _MEDIA_EXTENSIONS:
            continue
        try:
            relative_path = path.resolve().relative_to(resolved_root).as_posix()
        except ValueError:
            continue
        materials.append({
            "source_relative_path": relative_path,
            "file_name": path.name,
            "extension": path.suffix.casefold(),
            "byte_size": path.stat().st_size,
        })
    return sorted(materials, key=lambda item: item["source_relative_path"].casefold())


def _module_for_material(material: Mapping[str, Any]) -> tuple[str, list[str], str]:
    text = f"{material.get('source_relative_path', '')} {material.get('file_name', '')}".casefold()
    matches: list[tuple[str, list[str]]] = []
    for module_id, tokens in _MODULE_TOKENS.items():
        matched = [token for token in tokens if token.casefold() in text]
        if matched:
            matches.append((module_id, matched))
    if matches:
        module_id, matched = matches[0]
        return module_id, matched, "filename_or_folder_signal"
    return "special_activity", [], "agent_default_special_activity"


def _modules_for_material(material: Mapping[str, Any]) -> list[tuple[str, list[str], str]]:
    text = f"{material.get('source_relative_path', '')} {material.get('file_name', '')}".casefold()
    matches: list[tuple[str, list[str], str]] = []
    for module_id, tokens in _MODULE_TOKENS.items():
        matched = [token for token in tokens if token.casefold() in text]
        if matched:
            matches.append((module_id, matched, "filename_or_folder_signal"))
    if matches:
        return matches
    return [("special_activity", [], "agent_default_special_activity")]


def _training_catalog_map(source_root: str | Path | None) -> dict[str, Any]:
    materials = _scan_source_materials(source_root)
    modules = [
        {
            "module_id": module_id,
            "material_assignments": [],
            "coverage_status": "missing_material",
        }
        for module_id in TRAINING_MODULE_IDS
    ]
    by_id = {module["module_id"]: module for module in modules}
    agent_filled_count = 0
    for material in materials:
        for module_id, signals, reason in _modules_for_material(material):
            assignment = {
                **material,
                "module_id": module_id,
                "matched_signals": signals,
                "confidence": "medium" if signals else "low",
                "agent_filled": True,
                "authority": "agent_filled",
                "needs_human_confirmation": True,
                "assignment_reason": reason,
            }
            by_id[module_id]["material_assignments"].append(assignment)
            by_id[module_id]["coverage_status"] = "agent_filled_needs_human_confirmation"
            agent_filled_count += 1
    return {
        "artifact_role": "training_catalog_map",
        "version": 1,
        "source_root": _clean(source_root),
        "modules": modules,
        "summary": {
            "module_count": len(modules),
            "material_count": len(materials),
            "media_count": len(materials),
            "agent_filled_count": agent_filled_count,
            "needs_human_confirmation_count": agent_filled_count,
            "missing_module_count": sum(1 for module in modules if not module["material_assignments"]),
        },
    }


def _graduation_blueprint(brief: Mapping[str, Any], canon: Mapping[str, Any], catalog: Mapping[str, Any]) -> dict[str, Any]:
    theme = _fixture_theme(brief)
    return {
        "artifact_role": "graduation_film_blueprint",
        "version": 1,
        "film_type": "graduation_training_film",
        "theme": theme,
        "canon_section_order": [section["section_id"] for section in canon["sections"]],
        "training_mv_catalog": {
            "section_id": "training_mv_catalog",
            "longest_body_section": True,
            "module_count": catalog["summary"]["module_count"],
            "module_order": TRAINING_MODULE_IDS,
            "music_intent": "hot_blooded_training_mv",
        },
        "section_blueprints": [
            {
                "section_id": "opening_story",
                "purpose": "\u5efa\u7acb\u4e3b\u984c\u8207\u60c5\u611f\u5165\u53e3",
                "retargetable": True,
            },
            {
                "section_id": "training_mv_catalog",
                "purpose": "\u7528\u6700\u9577\u7bc7\u5e45\u5448\u73fe\u8a13\u7df4\u76ee\u9304",
                "retargetable": False,
            },
            {
                "section_id": "supervisor_speech",
                "purpose": "\u4fdd\u7559\u6709\u50f9\u503c\u7684\u73fe\u5834\u8a71\u8a9e",
                "requires": ["source_speech_intelligibility", "subtitles"],
                "retargetable": False,
            },
            {
                "section_id": "teacher_class_intro",
                "purpose": "\u6e05\u695a\u4ecb\u7d39\u5e2b\u9577\u8207\u73ed\u7d1a",
                "requires": ["readability_review"],
                "retargetable": False,
            },
            {
                "section_id": "closing_story",
                "purpose": "\u56de\u6536\u4e3b\u984c\u8207\u7562\u696d\u611f",
                "retargetable": True,
            },
        ],
    }


def _story_shell(brief: Mapping[str, Any]) -> dict[str, Any]:
    title = _fixture_title(brief)
    theme = _fixture_theme(brief)
    return {
        "artifact_role": "story_shell",
        "version": 1,
        "title": title,
        "theme": theme,
        "opening_story": {
            "hook": f"{title}: {theme}",
            "authority": "agent_filled",
            "needs_human_confirmation": True,
        },
        "closing_story": {
            "payoff": "\u628a\u8a13\u7df4\u7d2f\u7a4d\u8f49\u6210\u7d50\u8a13\u5f8c\u7684\u524d\u9032\u611f",
            "authority": "agent_filled",
            "needs_human_confirmation": True,
        },
        "retargetable_without_changing_canon": True,
    }


def _story_shell_variant(label: str, theme: str) -> dict[str, Any]:
    title = f"\u7d50\u8a13\u5f71\u7247\u6545\u4e8b\u7248\u672c {label}"
    if label == "A":
        hook = "\u5f9e\u65b0\u4eba\u7b2c\u4e00\u6b21\u8d70\u9032\u73fe\u5834\uff0c\u5230\u80fd\u627f\u64d4\u4efb\u52d9\u7684\u73fe\u5834\u4eba\u54e1"
        payoff = "\u628a\u8a13\u7df4\u4e2d\u7684\u6bcf\u4e00\u6b21\u7df4\u7fd2\uff0c\u843d\u5230\u672a\u4f86\u73fe\u5834\u7684\u8cac\u4efb\u611f"
    else:
        hook = "5.5 \u500b\u6708\u7684\u91cd\u8907\u7df4\u7fd2\uff0c\u662f\u70ba\u4e86\u8b93\u5b89\u5168\u6210\u70ba\u7b2c\u4e00\u500b\u53cd\u61c9"
        payoff = "\u7d50\u8a13\u4e0d\u662f\u7d42\u9ede\uff0c\u662f\u628a\u5b89\u5168\u8b8a\u6210\u53cd\u5c04\u7684\u958b\u59cb"
    return {
        "artifact_role": "story_shell",
        "version": 1,
        "variant": label,
        "title": title,
        "theme": theme,
        "opening_story": {
            "hook": hook,
            "authority": "agent_filled",
            "needs_human_confirmation": True,
        },
        "closing_story": {
            "payoff": payoff,
            "authority": "agent_filled",
            "needs_human_confirmation": True,
        },
        "retargetable_without_changing_canon": True,
    }


def _story_retargeting_notes(canon: Mapping[str, Any]) -> dict[str, Any]:
    policy = canon["retargeting_policy"]
    return {
        "artifact_role": "story_retargeting_notes",
        "version": 1,
        "retargetable_parts": list(policy["retargetable_shell"]),
        "stable_parts": list(policy["stable_core"]),
        "rules": [
            "Retarget opening and closing story before changing the training catalog.",
            "Retarget module ordering or emphasis only when material still fits the catalog.",
            "Do not treat agent-filled assignments as human-approved.",
        ],
    }


def _module_counts(catalog: Mapping[str, Any]) -> dict[str, int]:
    return {
        module["module_id"]: len(module.get("material_assignments") or [])
        for module in catalog.get("modules", [])
    }


def _representative_paths(catalog: Mapping[str, Any], limit: int = 3) -> dict[str, list[str]]:
    reps: dict[str, list[str]] = {}
    for module in catalog.get("modules", []):
        reps[module["module_id"]] = [
            item["source_relative_path"]
            for item in (module.get("material_assignments") or [])[:limit]
        ]
    return reps


def _source_preflight(source_root: str | Path | None, catalog: Mapping[str, Any]) -> dict[str, Any]:
    root = Path(source_root) if source_root else Path("")
    exists = bool(source_root) and root.exists()
    is_dir = exists and root.is_dir()
    file_count = 0
    if is_dir:
        file_count = sum(1 for path in root.rglob("*") if path.is_file())
    return {
        "source_root": _clean(source_root),
        "exists": exists,
        "is_dir": is_dir,
        "file_count": file_count,
        "media_count": catalog["summary"]["material_count"],
    }


def _retarget_diff(canon: Mapping[str, Any], shell_a: Mapping[str, Any], shell_b: Mapping[str, Any], catalog: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_role": "story_retarget_diff_A_to_B",
        "version": 1,
        "canon_unchanged": [section["section_id"] for section in canon["sections"]] == CANON_SECTION_IDS,
        "catalog_reuse": "mostly_reusable",
        "catalog_reusable_module_count": sum(1 for count in _module_counts(catalog).values() if count > 0),
        "changed_sections": ["opening_story", "closing_story"],
        "changed_story_fields": ["theme", "opening_story.hook", "closing_story.payoff"],
        "module_order_or_emphasis_changes": [
            {
                "variant": "A",
                "emphasis": ["basic_training", "advanced_training", "supervisor_speech"],
            },
            {
                "variant": "B",
                "emphasis": ["basic_training", "certification", "closing_story"],
            },
        ],
        "human_approval_reusable": False,
        "future_artifacts_to_regenerate": [
            "graduation_film_blueprint_A.json",
            "graduation_film_blueprint_B.json",
            "story_shell_A.json",
            "story_shell_B.json",
            "story_to_material_map.json",
            "narration_manifest.json",
            "subtitles.srt",
            "review_packet",
        ],
        "summary": {
            "from_theme": shell_a["theme"],
            "to_theme": shell_b["theme"],
            "catalog_map_reuse": "mostly reusable after human confirmation",
        },
    }


def _production_readiness_plan(catalog: Mapping[str, Any]) -> dict[str, Any]:
    summary = catalog["summary"]
    return {
        "artifact_role": "production_readiness_plan",
        "version": 1,
        "ready_for_render": False,
        "requires_human_review": True,
        "blocking_reviews_before_production": [
            "confirm_agent_filled_training_catalog_assignments",
            "choose_story_shell_A_or_B_or_retarget",
            "confirm_supervisor_speech_intelligibility",
            "confirm_teacher_class_intro_readability",
            "confirm_opening_closing_design_direction",
        ],
        "catalog_summary": summary,
        "next_production_handoffs": [
            "material_map_review",
            "opener_closer_design_handoff",
            "audio_subtitle_review_requirements",
        ],
    }


def _opener_closer_design_handoff(shell_a: Mapping[str, Any], shell_b: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "artifact_role": "opener_closer_design_handoff",
        "version": 1,
        "sections": ["opening_story", "closing_story"],
        "design_rules": [
            "\u958b\u982d\u548c\u7d50\u5c3e\u662f\u6545\u4e8b\u5916\u6bbc\uff0c\u4e0d\u662f\u7d14\u767d\u5b57\u5361",
            "\u53ef\u4ee5\u56e0\u4e3b\u984c\u91cd\u5b9a\u5411\uff0c\u4f46\u4e0d\u61c9\u6539\u6389\u8a13\u7df4\u76ee\u9304\u6838\u5fc3",
        ],
        "story_shell_options": [
            {"variant": "A", "theme": shell_a["theme"], "hook": shell_a["opening_story"]["hook"], "payoff": shell_a["closing_story"]["payoff"]},
            {"variant": "B", "theme": shell_b["theme"], "hook": shell_b["opening_story"]["hook"], "payoff": shell_b["closing_story"]["payoff"]},
        ],
        "human_choice_required": True,
    }


def _audio_subtitle_review_requirements(catalog: Mapping[str, Any]) -> dict[str, Any]:
    counts = _module_counts(catalog)
    return {
        "artifact_role": "audio_subtitle_review_requirements",
        "version": 1,
        "requires_supervisor_speech_subtitles": counts.get("supervisor_speech", 0) > 0,
        "requires_teacher_class_intro_readability": counts.get("teacher_class_intro", 0) > 0,
        "requires_source_speech_intelligibility_review": counts.get("supervisor_speech", 0) > 0,
        "music_policy": "hot_blooded_music_mainly_training_mv_catalog",
        "review_items": [
            "source speech intelligibility",
            "subtitle readability for supervisor speech",
            "teacher/class introduction readability",
            "music/narration/source-speech balance",
        ],
    }


def _review_packet_markdown(artifacts: Mapping[str, Any]) -> str:
    canon = artifacts["graduation_film_canon"]
    blueprint = artifacts["graduation_film_blueprint"]
    catalog = artifacts["training_catalog_map"]
    story_shell = artifacts["story_shell"]
    sections = ", ".join(section["section_id"] for section in canon["sections"])
    module_lines = "\n".join(
        f"- {module['module_id']}: {len(module['material_assignments'])} agent-filled assignments"
        for module in catalog["modules"]
    )
    return "\n".join([
        "# Graduation Film Dry Run Review Packet",
        "",
        f"- Title: {story_shell['title']}",
        f"- Theme: {blueprint['theme']}",
        f"- Canon sections: {sections}",
        f"- Longest body section: {canon['longest_body_section']}",
        f"- Agent-filled assignments: {catalog['summary']['agent_filled_count']}",
        f"- Needs human confirmation: {catalog['summary']['needs_human_confirmation_count']}",
        "- Rendered: false",
        "- Human approval written: false",
        "",
        "## Training Catalog Modules",
        "",
        module_lines,
        "",
        "## Review Caveats",
        "",
        "- Agent-filled catalog assignments require human confirmation.",
        "- This dry run does not render final.mp4.",
        "- This dry run does not write story_human_review_decision.json.",
        "",
    ])


def _real_source_review_packet_markdown(artifacts: Mapping[str, Any]) -> str:
    packet = artifacts["graduation_real_source_review_packet"]
    counts = packet["module_counts"]
    reps = packet["representative_source_relative_paths"]
    module_lines = "\n".join(
        f"- {module_id}: {count}; examples: {', '.join(reps.get(module_id) or ['none'])}"
        for module_id, count in counts.items()
    )
    return "\n".join([
        "# Graduation Real-Source Catalog Retarget Dry Run",
        "",
        f"- Source root: {packet['source_preflight']['source_root']}",
        f"- Source exists/is_dir: {packet['source_preflight']['exists']} / {packet['source_preflight']['is_dir']}",
        f"- File count: {packet['source_preflight']['file_count']}",
        f"- Media count: {packet['source_preflight']['media_count']}",
        f"- Story A: {packet['story_shells']['A']['theme']}",
        f"- Story B: {packet['story_shells']['B']['theme']}",
        f"- Retarget changed sections: {', '.join(packet['retarget_summary']['changed_sections'])}",
        "- Rendered: false",
        "- Human approval written: false",
        "",
        "## Module Counts And Examples",
        "",
        module_lines,
        "",
        "## Next Production Handoffs",
        "",
        "\n".join(f"- {item}" for item in packet["next_production_handoffs"]),
        "",
        "## Review Caveats",
        "",
        "- Agent-filled catalog assignments require human confirmation.",
        "- Human approval cannot be reused across A/B retargeted story shells.",
        "- This dry run does not render final.mp4.",
        "- This dry run does not write story_human_review_decision.json.",
        "",
    ])


def build_graduation_film_dry_run(
    brief: Mapping[str, Any] | None = None,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    payload = dict(brief or {})
    canon = graduation_film_canon()
    catalog = _training_catalog_map(source_root)
    blueprint = _graduation_blueprint(payload, canon, catalog)
    story_shell = _story_shell(payload)
    notes = _story_retargeting_notes(canon)
    packet = {
        "artifact_role": "graduation_dry_run_review_packet",
        "version": 1,
        "rendered": False,
        "human_approval_written": False,
        "canon_sections": [section["section_id"] for section in canon["sections"]],
        "blueprint_theme": blueprint["theme"],
        "story_shell": {
            "title": story_shell["title"],
            "hook": story_shell["opening_story"]["hook"],
            "payoff": story_shell["closing_story"]["payoff"],
        },
        "training_catalog_summary": catalog["summary"],
        "review_required": ["catalog_assignments", "story_shell", "module_ordering_emphasis"],
    }
    return {
        "graduation_film_canon": canon,
        "graduation_film_blueprint": blueprint,
        "story_shell": story_shell,
        "training_catalog_map": catalog,
        "story_retargeting_notes": notes,
        "graduation_dry_run_review_packet": packet,
        "graduation_dry_run_review_packet_md": _review_packet_markdown({
            "graduation_film_canon": canon,
            "graduation_film_blueprint": blueprint,
            "story_shell": story_shell,
            "training_catalog_map": catalog,
        }),
    }


def build_graduation_film_real_source_dry_run(source_root: str | Path) -> dict[str, Any]:
    canon = graduation_film_canon()
    catalog = _training_catalog_map(source_root)
    shell_a = _story_shell_variant("A", "\u5f9e\u65b0\u4eba\u5230\u73fe\u5834\u4eba\u54e1")
    shell_b = _story_shell_variant("B", "5.5 \u500b\u6708\uff0c\u628a\u5b89\u5168\u8b8a\u6210\u53cd\u5c04")
    blueprint_a = _graduation_blueprint({"theme": shell_a["theme"], "title": shell_a["title"]}, canon, catalog)
    blueprint_b = _graduation_blueprint({"theme": shell_b["theme"], "title": shell_b["title"]}, canon, catalog)
    diff = _retarget_diff(canon, shell_a, shell_b, catalog)
    readiness = _production_readiness_plan(catalog)
    design_handoff = _opener_closer_design_handoff(shell_a, shell_b)
    audio_requirements = _audio_subtitle_review_requirements(catalog)
    preflight = _source_preflight(source_root, catalog)
    packet = {
        "artifact_role": "graduation_real_source_review_packet",
        "version": 1,
        "rendered": False,
        "human_approval_written": False,
        "source_preflight": preflight,
        "canon_sections": [section["section_id"] for section in canon["sections"]],
        "module_counts": _module_counts(catalog),
        "representative_source_relative_paths": _representative_paths(catalog),
        "story_shells": {
            "A": {
                "title": shell_a["title"],
                "theme": shell_a["theme"],
                "hook": shell_a["opening_story"]["hook"],
                "payoff": shell_a["closing_story"]["payoff"],
            },
            "B": {
                "title": shell_b["title"],
                "theme": shell_b["theme"],
                "hook": shell_b["opening_story"]["hook"],
                "payoff": shell_b["closing_story"]["payoff"],
            },
        },
        "retarget_summary": {
            "changed_sections": diff["changed_sections"],
            "catalog_reuse": diff["catalog_reuse"],
            "human_approval_reusable": diff["human_approval_reusable"],
            "future_artifacts_to_regenerate": diff["future_artifacts_to_regenerate"],
        },
        "next_production_handoffs": readiness["next_production_handoffs"],
    }
    artifacts = {
        "graduation_film_canon": canon,
        "graduation_film_blueprint_A": blueprint_a,
        "graduation_film_blueprint_B": blueprint_b,
        "story_shell_A": shell_a,
        "story_shell_B": shell_b,
        "training_catalog_map": catalog,
        "story_retarget_diff_A_to_B": diff,
        "production_readiness_plan": readiness,
        "opener_closer_design_handoff": design_handoff,
        "audio_subtitle_review_requirements": audio_requirements,
        "graduation_real_source_review_packet": packet,
    }
    artifacts["graduation_real_source_review_packet_md"] = _real_source_review_packet_markdown(artifacts)
    return artifacts


def write_graduation_film_dry_run(
    brief: Mapping[str, Any] | None,
    out_dir: str | Path,
    *,
    source_root: str | Path | None = None,
) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    artifacts = build_graduation_film_dry_run(brief, source_root=source_root)
    json_outputs = {
        "graduation_film_canon.json": artifacts["graduation_film_canon"],
        "graduation_film_blueprint.json": artifacts["graduation_film_blueprint"],
        "story_shell.json": artifacts["story_shell"],
        "training_catalog_map.json": artifacts["training_catalog_map"],
        "story_retargeting_notes.json": artifacts["story_retargeting_notes"],
        "graduation_dry_run_review_packet.json": artifacts["graduation_dry_run_review_packet"],
    }
    for name, artifact in json_outputs.items():
        (out_root / name).write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (out_root / "graduation_dry_run_review_packet.md").write_text(
        artifacts["graduation_dry_run_review_packet_md"],
        encoding="utf-8",
    )
    return {
        "ok": True,
        "out_dir": str(out_root),
        "artifacts": list(_ARTIFACT_NAMES),
        "canon_sections": artifacts["graduation_dry_run_review_packet"]["canon_sections"],
        "training_catalog_summary": artifacts["training_catalog_map"]["summary"],
        "rendered": False,
        "human_approval_written": False,
    }


def write_graduation_film_real_source_dry_run(source_root: str | Path, out_dir: str | Path) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    artifacts = build_graduation_film_real_source_dry_run(source_root)
    json_outputs = {
        "graduation_film_canon.json": artifacts["graduation_film_canon"],
        "graduation_film_blueprint_A.json": artifacts["graduation_film_blueprint_A"],
        "graduation_film_blueprint_B.json": artifacts["graduation_film_blueprint_B"],
        "story_shell_A.json": artifacts["story_shell_A"],
        "story_shell_B.json": artifacts["story_shell_B"],
        "training_catalog_map.real_source.json": artifacts["training_catalog_map"],
        "story_retarget_diff_A_to_B.json": artifacts["story_retarget_diff_A_to_B"],
        "production_readiness_plan.json": artifacts["production_readiness_plan"],
        "opener_closer_design_handoff.json": artifacts["opener_closer_design_handoff"],
        "audio_subtitle_review_requirements.json": artifacts["audio_subtitle_review_requirements"],
        "graduation_real_source_review_packet.json": artifacts["graduation_real_source_review_packet"],
    }
    for name, artifact in json_outputs.items():
        (out_root / name).write_text(
            json.dumps(artifact, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
    (out_root / "graduation_real_source_review_packet.md").write_text(
        artifacts["graduation_real_source_review_packet_md"],
        encoding="utf-8",
    )
    packet = artifacts["graduation_real_source_review_packet"]
    return {
        "ok": True,
        "out_dir": str(out_root),
        "artifacts": list(_REAL_SOURCE_ARTIFACT_NAMES),
        "source_preflight": packet["source_preflight"],
        "module_counts": packet["module_counts"],
        "representative_source_relative_paths": packet["representative_source_relative_paths"],
        "story_shells": packet["story_shells"],
        "retarget_summary": packet["retarget_summary"],
        "rendered": False,
        "human_approval_written": False,
    }
