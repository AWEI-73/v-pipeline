#!/usr/bin/env python
"""Build an Agent-readable review report for Workbench draft edits.

The report is a draft artifact. It summarizes human/Workbench edits so an Agent
can decide whether to rerender, reject, or convert the edits into a contract
revision. It never mutates canonical timeline, contract, material-map, or final
render artifacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

ARTIFACT_ROLE = "workbench_review_report"
SCHEMA_VERSION = 1

JSON_OUT = "workbench_review_report.json"
MD_OUT = "workbench_review_report.md"


def _load_json(path: Path) -> Optional[Any]:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _plan_of(timeline: Optional[Any]) -> List[Dict[str, Any]]:
    if isinstance(timeline, list):
        return [c for c in timeline if isinstance(c, dict)]
    if isinstance(timeline, dict):
        for key in ("plan", "clips", "slots"):
            value = timeline.get(key)
            if isinstance(value, list):
                return [c for c in value if isinstance(c, dict)]
    return []


def _load_base_timeline(root: Path) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    for name in ("draft_timeline.json", "timeline.json", "timeline_build.json"):
        path = root / name
        data = _load_json(path)
        plan = _plan_of(data)
        if plan:
            return plan, name
    return [], None


def _index_by_slot(plan: List[Dict[str, Any]]) -> Dict[Any, Dict[str, Any]]:
    out: Dict[Any, Dict[str, Any]] = {}
    for i, clip in enumerate(plan):
        out[clip.get("slot_index", i)] = clip
    return out


def _patch_ops(root: Path, filename: str) -> List[Dict[str, Any]]:
    data = _load_json(root / filename)
    if not isinstance(data, dict):
        return []
    patches = data.get("patches")
    if not isinstance(patches, list):
        return []
    return [p for p in patches if isinstance(p, dict)]


def _timeline_edit(op: Dict[str, Any], base_by_slot: Dict[Any, Dict[str, Any]]) -> Dict[str, Any]:
    kind = op.get("op")
    slot_index = op.get("slot_index")
    base = base_by_slot.get(slot_index, {})
    after = op.get("after") if isinstance(op.get("after"), dict) else {}
    common = {
        "layer": "timeline",
        "op": kind,
        "slot_index": slot_index,
        "segment": base.get("segment") or base.get("segment_id"),
        "scene_id": base.get("scene_id"),
        "source": base.get("source"),
    }
    if kind == "set_duration":
        common["before"] = {"duration_sec": base.get("slot_dur") or base.get("duration_sec")}
        common["after"] = {"duration_sec": after.get("duration_sec")}
    elif kind == "set_source_window":
        common["before"] = {
            "source_start_sec": base.get("extract_start"),
            "source_duration_sec": base.get("extract_dur"),
        }
        common["after"] = {
            "source_start_sec": after.get("source_start_sec"),
            "source_duration_sec": after.get("source_duration_sec"),
        }
    elif kind == "replace_clip":
        common["before"] = {
            "asset_id": base.get("asset_id"),
            "scene_id": base.get("scene_id"),
            "source": base.get("source"),
        }
        common["after"] = {
            "asset_id": after.get("asset_id"),
            "scene_index": after.get("scene_index", 0),
            "duration_sec": after.get("duration_sec"),
        }
    elif kind == "move_clip":
        common["before"] = {"slot_index": slot_index}
        common["after"] = {"new_index": after.get("new_index")}
    else:
        common["before"] = {}
        common["after"] = after
    return common


def _layer_edit(layer: str, op: Dict[str, Any]) -> Dict[str, Any]:
    out = {
        "layer": layer,
        "op": op.get("op"),
        "id": op.get("subtitle_id") or op.get("cue_id") or op.get("effect_id"),
        "before": op.get("before") if isinstance(op.get("before"), dict) else {},
        "after": op.get("after") if isinstance(op.get("after"), dict) else {},
    }
    return out


def build_review_report(artifact_root: str) -> Dict[str, Any]:
    """Build a draft-only review report from Workbench patch artifacts."""
    root = Path(artifact_root)
    plan, base_ref = _load_base_timeline(root)
    base_by_slot = _index_by_slot(plan)

    timeline_ops = _patch_ops(root, "timeline_patch.json")
    subtitle_ops = _patch_ops(root, "subtitle_patch.json")
    audio_ops = _patch_ops(root, "audio_cue_patch.json")
    effect_ops = _patch_ops(root, "effect_patch.json")

    edits: List[Dict[str, Any]] = []
    edits.extend(_timeline_edit(op, base_by_slot) for op in timeline_ops)
    edits.extend(_layer_edit("subtitle", op) for op in subtitle_ops)
    edits.extend(_layer_edit("audio", op) for op in audio_ops)
    edits.extend(_layer_edit("effect", op) for op in effect_ops)

    summary = {
        "timeline_edits": len(timeline_ops),
        "duration_edits": sum(1 for op in timeline_ops if op.get("op") == "set_duration"),
        "source_window_edits": sum(1 for op in timeline_ops if op.get("op") == "set_source_window"),
        "replacement_edits": sum(1 for op in timeline_ops if op.get("op") == "replace_clip"),
        "move_edits": sum(1 for op in timeline_ops if op.get("op") == "move_clip"),
        "subtitle_edits": len(subtitle_ops),
        "audio_cues": sum(1 for op in audio_ops if op.get("op") == "add_cue"),
        "effect_intents": sum(1 for op in effect_ops if op.get("op") == "add_effect"),
    }

    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": SCHEMA_VERSION,
        "ok": True,
        "status": "changes_present" if edits else "no_changes",
        "canonical_changed": False,
        "base_timeline_ref": base_ref,
        "summary": summary,
        "edits": edits,
        "next_action": "agent_review_and_rerender_or_reject" if edits else "none",
    }


def _markdown(report: Dict[str, Any]) -> str:
    summary = report.get("summary") or {}
    lines = [
        "# Workbench Review Report",
        "",
        f"status: {report.get('status')}",
        "canonical_changed: false",
        f"base_timeline_ref: {report.get('base_timeline_ref') or 'none'}",
        "",
        "## Summary",
        "",
    ]
    for key in (
        "timeline_edits",
        "duration_edits",
        "source_window_edits",
        "replacement_edits",
        "move_edits",
        "subtitle_edits",
        "audio_cues",
        "effect_intents",
    ):
        lines.append(f"- {key}: {summary.get(key, 0)}")
    lines.extend(["", "## Edits", ""])
    edits = report.get("edits") or []
    if not edits:
        lines.append("- no draft edits")
    for edit in edits:
        lines.append(
            f"- {edit.get('layer')} / {edit.get('op')} "
            f"slot={edit.get('slot_index', 'n/a')} segment={edit.get('segment', 'n/a')}"
        )
    lines.append("")
    return "\n".join(lines)


def write_review_report(
    artifact_root: str,
    json_name: str = JSON_OUT,
    md_name: str = MD_OUT,
) -> Dict[str, Any]:
    """Write draft JSON and Markdown reports. Canonical artifacts are untouched."""
    root = Path(artifact_root)
    report = build_review_report(artifact_root)
    json_path = root / json_name
    md_path = root / md_name
    json_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    md_path.write_text(_markdown(report), encoding="utf-8")
    return {
        "ok": True,
        "json": json_path.name,
        "markdown": md_path.name,
        "summary": report["summary"],
    }


def _cmd_build(args: argparse.Namespace) -> int:
    result = write_review_report(args.artifact_root, args.out_json, args.out_md)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Build a Workbench draft review report")
    parser.add_argument("--artifact-root", required=True)
    parser.add_argument("--out-json", default=JSON_OUT)
    parser.add_argument("--out-md", default=MD_OUT)
    args = parser.parse_args(argv)
    return _cmd_build(args)


if __name__ == "__main__":
    raise SystemExit(main())
