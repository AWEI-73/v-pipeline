"""MM1 — Project Material Map V1.

Aggregate the existing per-asset `*.map.json` evidence into ONE project-level
material map (`project_material_map.json`) that agents, BUILD, and a future UI
can read without creating a second source of truth.

Scope (MM1 V1): aggregation + reference integrity + truthful metrics only.
NOT in scope: covered/thin/missing decisions, material_delta, script revision,
BUILD ranking, Dashboard/UI, Node 14, effects. The project map does not replace
per-asset maps — it is their validated aggregate.
"""
from __future__ import annotations

import glob
import json
import os
from pathlib import Path

from .material_needs import summarize_satisfaction, validate_material_needs


_VD0_LABELS = ("visual_family", "angle_scale", "action_family", "subject")


def _scene_is_reviewed(scene):
    # an agent/VLM review produces a caption; that is the canonical review signal
    return bool(scene.get("caption"))


def _scene_has_label(scene):
    return any(scene.get(axis) for axis in _VD0_LABELS)


def build_project_material_map(material_maps, *, needs=None):
    """Aggregate per-asset maps into a deterministic project material map.

    When ``needs`` is given it is validated; every scene-level
    ``satisfies.need_id`` must reference a declared need or the build fails
    (no phantom edges). When ``needs`` is absent the map stays useful as an
    existing-material-first library and satisfaction edges are summarized as-is
    (they were already validated at write time by apply_satisfaction_verdict)."""
    canonical_needs = []
    whitelist = None
    if needs is not None:
        result = validate_material_needs(needs)
        if not result["ok"]:
            raise ValueError(
                "material_needs invalid: " + "; ".join(result["errors"]))
        canonical_needs = result["needs"]
        whitelist = {n["need_id"] for n in canonical_needs}

    assets = []
    scene_count = 0
    reviewed = 0
    labeled = 0
    # deterministic order regardless of input/glob ordering
    for material_map in sorted(material_maps or [],
                               key=lambda m: str(m.get("asset_id") or "")):
        asset_id = material_map.get("asset_id")
        scenes = material_map.get("scenes") or []
        for index, scene in enumerate(scenes):
            for edge in scene.get("satisfies") or []:
                nid = edge.get("need_id")
                if whitelist is not None and nid not in whitelist:
                    raise ValueError(
                        f"asset {asset_id!r} scene {index} satisfies unknown "
                        f"need_id {nid!r} (not in canonical material_needs)")
            scene_count += 1
            if _scene_is_reviewed(scene):
                reviewed += 1
            if _scene_has_label(scene):
                labeled += 1
        assets.append({
            "asset_id": asset_id,
            "asset_type": material_map.get("asset_type"),
            "source": material_map.get("source"),
            "duration_sec": material_map.get("duration_sec"),
            "scenes": scenes,            # verbatim evidence + lineage preserved
            "speech": material_map.get("speech") or [],
        })

    summary = summarize_satisfaction(material_maps)
    satisfaction_summary = {nid: summary[nid] for nid in sorted(summary)}

    def _ratio(part):
        return round(part / scene_count, 4) if scene_count else 0

    return {
        "artifact_role": "project_material_map",
        "version": 1,
        "assets": assets,
        "needs": canonical_needs,
        "satisfaction_summary": satisfaction_summary,
        "metrics": {
            "asset_count": len(assets),
            "scene_count": scene_count,
            "reviewed_scene_ratio": _ratio(reviewed),
            "visual_label_coverage": _ratio(labeled),
        },
    }


def load_asset_maps(maps_dir):
    """Load every `*.map.json` under a directory (deterministic by filename)."""
    maps = []
    for path in sorted(glob.glob(os.path.join(str(maps_dir), "*.map.json"))):
        with open(path, encoding="utf-8") as handle:
            maps.append(json.load(handle))
    return maps


def write_project_material_map(maps_dir, out_path, *, needs_path=None):
    material_maps = load_asset_maps(maps_dir)
    needs = None
    if needs_path and os.path.exists(needs_path):
        with open(needs_path, encoding="utf-8") as handle:
            needs = json.load(handle)
    project_map = build_project_material_map(material_maps, needs=needs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(project_map, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return {"ok": True, "project_material_map": str(path),
            "metrics": project_map["metrics"]}
