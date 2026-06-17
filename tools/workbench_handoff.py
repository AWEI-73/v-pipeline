#!/usr/bin/env python
"""Hermes-native workbench: unified save / Agent handoff (Layer 4).

Builds ``workbench_handoff.json`` -- a single index the Agent reads to pick up a
human fine-tuning session: which draft patch artifacts exist and a per-layer edit
summary. It references only draft artifacts and never canonical files.
"""
from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional

ARTIFACT_ROLE = "workbench_handoff"
SCHEMA_VERSION = 1

# draft artifact name -> handoff key
DRAFT_ARTIFACTS = {
    "timeline_patch": "timeline_patch.json",
    "patched_draft_timeline": "patched_draft_timeline.json",
    "workbench_contract_patch": "workbench_contract_patch.json",
    "subtitle_patch": "subtitle_patch.json",
    "audio_cue_patch": "audio_cue_patch.json",
    "effect_patch": "effect_patch.json",
    "workbench_review_report": "workbench_review_report.json",
    "workbench_review_report_md": "workbench_review_report.md",
}


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _artifact_detail(path: Path) -> Dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": path.name,
        "size_bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def _count_ops(patch: Optional[Dict[str, Any]], op_filter: Optional[str] = None) -> int:
    if not isinstance(patch, dict):
        return 0
    ops = patch.get("patches") or []
    if op_filter is None:
        return len(ops)
    return sum(1 for o in ops if isinstance(o, dict) and o.get("op") == op_filter)


def build_handoff(artifact_root: str) -> Dict[str, Any]:
    """Scan the root for draft artifacts and produce the handoff index."""
    root = Path(artifact_root)
    present: Dict[str, str] = {}
    details: Dict[str, Dict[str, Any]] = {}
    for key, name in DRAFT_ARTIFACTS.items():
        path = root / name
        if path.is_file():
            present[key] = name
            details[key] = _artifact_detail(path)

    timeline_patch = _load_json(root / DRAFT_ARTIFACTS["timeline_patch"])
    subtitle_patch = _load_json(root / DRAFT_ARTIFACTS["subtitle_patch"])
    audio_cue_patch = _load_json(root / DRAFT_ARTIFACTS["audio_cue_patch"])
    effect_patch = _load_json(root / DRAFT_ARTIFACTS["effect_patch"])

    summary = {
        "timeline_edits": _count_ops(timeline_patch),
        "subtitle_edits": _count_ops(subtitle_patch),
        "audio_cues": _count_ops(audio_cue_patch, "add_cue"),
        "effect_intents": _count_ops(effect_patch, "add_effect"),
    }

    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": SCHEMA_VERSION,
        "artifacts": present,
        "artifact_details": details,
        "summary": summary,
        "next_action": "agent_review_and_render_preview",
    }
