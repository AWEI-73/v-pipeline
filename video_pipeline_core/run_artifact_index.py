"""Classify run-folder artifacts for human review and UI handoff."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


ARTIFACT_CLASSES = ("decision", "contract", "handoff", "evidence", "asset", "debug")


DECISION_NAMES = {
    "video_intent.json",
    "material_delta.json",
    "material_generation_fallback.json",
    "material_first_boundary_acceptance_report.json",
    "material_map_lifecycle.json",
    "supply_review.json",
    "effect_capability_review.json",
    "effect_factory_route_acceptance_report.json",
    "soundtrack_flow_acceptance_report.json",
    "audio_handoff_acceptance.json",
    "subtitle_voiceover_handoff_acceptance.json",
    "story_first_provider_happy_path_report.json",
    "highlight_selection_plan.json",
    "highlight_cut_report.json",
    "delivery_gate.json",
    "verified_preview_package.json",
    "final_promotion_report.json",
    "final_product_verify_bundle.json",
    "verify_result.json",
    "state.json",
}

CONTRACT_NAMES = {
    "project_brief.json",
    "project_material_map.json",
    "reviewed_project_material_map.json",
    "materials_db.json",
    "material_needs.json",
    "creative_concept.json",
    "director_shot_plan.json",
    "generation_manifest.json",
    "screenplay_beats.json",
    "story_world.json",
    "generated_provider_outputs.template.json",
    "effect_contract.json",
    "segment_contract.json",
    "soundtrack_plan.json",
    "sound_license_manifest.json",
    "music_manifest.json",
    "audio_mix_plan.json",
    "narration_manifest.json",
    "subtitle_voiceover_contract.json",
    "rough_cut_plan.json",
    "source_timeline_map.json",
    "effect_intent_plan.json",
    "visual_technique_plan.json",
    "visual_technique_plan.confirmed.json",
    "voiceover_provider_plan.json",
    "delivery_requirements.json",
}

HANDOFF_SUFFIXES = (
    "_handoff.json",
    "_build_handoff.json",
)

HANDOFF_NAMES = {
    "generated_provider_packet.json",
}

EVIDENCE_HINTS = (
    "review",
    "audit",
    "probe",
    "contact_sheet",
    "montage",
    "diagnostic",
    "matrix",
    "verdict",
    "transcript",
    "asr",
)

EVIDENCE_MEDIA_HINTS = (
    "contact_sheet",
    "montage",
)

EVIDENCE_NAMES = {
    "generated_provider_prompts.md",
    "image_agent_prompt.md",
    "audio_mix_report.json",
}

ASSET_EXTENSIONS = {
    ".mp3",
    ".mp4",
    ".mov",
    ".wav",
    ".webm",
    ".m4a",
    ".png",
    ".jpg",
    ".jpeg",
    ".webp",
    ".srt",
}

DEBUG_HINTS = (
    ".tmp",
    "tmp",
    "temp",
    "debug",
    "raw",
    "frames",
    "remotion_project",
    "node_modules",
)


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def classify_artifact(path: Path, root: Path) -> str:
    """Return the artifact class for a path inside a run folder."""
    rel = _rel(path, root)
    lower_name = path.name.lower()
    lower_rel = rel.lower()
    path_parts = lower_rel.split("/")

    if any(part in path_parts for part in DEBUG_HINTS) or any(part.endswith("_frames") for part in path_parts):
        return "debug"
    if lower_name in DECISION_NAMES:
        return "decision"
    if lower_name in CONTRACT_NAMES:
        return "contract"
    if lower_name in HANDOFF_NAMES or lower_name.endswith(HANDOFF_SUFFIXES):
        return "handoff"
    if any(hint in lower_name for hint in EVIDENCE_MEDIA_HINTS):
        return "evidence"
    if lower_name in EVIDENCE_NAMES:
        return "evidence"
    if path.suffix.lower() in ASSET_EXTENSIONS:
        return "asset"
    if any(hint in lower_name for hint in EVIDENCE_HINTS):
        return "evidence"
    if lower_name in {
        "source_section_map.json",
        "source_motion_profile.json",
        "source_material_matrix.json",
        "source_soundtrack_probe_report.json",
    }:
        return "evidence"
    if lower_name == "artifact_manifest.json":
        return "contract"
    return "debug"


def build_run_artifact_index(run_dir: str | Path) -> dict[str, Any]:
    root = Path(run_dir).resolve()
    if not root.exists() or not root.is_dir():
        raise FileNotFoundError(f"run folder not found: {root}")

    classes: dict[str, list[dict[str, Any]]] = {name: [] for name in ARTIFACT_CLASSES}
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == "run_artifact_index.json":
            continue
        artifact_class = classify_artifact(path, root)
        stat = path.stat()
        classes[artifact_class].append({
            "path": _rel(path, root),
            "size_bytes": stat.st_size,
        })

    return {
        "artifact_role": "run_artifact_index",
        "version": 1,
        "run_dir": str(root),
        "classes": classes,
        "review_priority": ["decision", "contract", "handoff", "evidence"],
        "noise_classes": ["asset", "debug"],
    }


def write_run_artifact_index(run_dir: str | Path, out_path: str | Path | None = None) -> dict[str, Any]:
    index = build_run_artifact_index(run_dir)
    out = Path(out_path) if out_path is not None else Path(run_dir) / "run_artifact_index.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(index, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return index
