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

from .material_needs import (
    VALID_STATUSES,
    summarize_satisfaction,
    validate_material_needs,
)


_VD0_LABELS = ("visual_family", "angle_scale", "action_family", "subject")


def _scene_is_captioned(scene):
    # an agent/VLM review produces a caption; this metric measures exactly that
    return bool(scene.get("caption"))


def _scene_has_vd0_label(scene):
    return any(scene.get(axis) for axis in _VD0_LABELS)


def _validate_satisfies(asset_id, index, scene, whitelist):
    """Validate every satisfies edge's structure, need_id, status, and reference.
    whitelist=None means no canonical needs exist — then any edge is a phantom."""
    for edge in scene.get("satisfies") or []:
        ref = f"asset {asset_id!r} scene {index}"
        if not isinstance(edge, dict):
            raise ValueError(f"{ref} satisfies edge must be an object, got {edge!r}")
        nid = edge.get("need_id")
        if not isinstance(nid, str) or not nid.strip():
            raise ValueError(f"{ref} satisfies need_id must be a non-empty string, got {nid!r}")
        status = edge.get("status")
        if status not in VALID_STATUSES:
            raise ValueError(f"{ref} satisfies status must be one of {VALID_STATUSES}, got {status!r}")
        if whitelist is None:
            raise ValueError(
                f"{ref} has a satisfies edge but the project declares no material "
                f"needs — a satisfaction edge cannot reference a non-existent need")
        if nid not in whitelist:
            raise ValueError(f"{ref} satisfies unknown need_id {nid!r} (not in canonical material_needs)")


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
    captioned = 0
    labeled = 0
    seen_ids = set()
    # deterministic order regardless of input/glob ordering
    for material_map in sorted(material_maps or [],
                               key=lambda m: str(m.get("asset_id") or "")):
        asset_id = material_map.get("asset_id")
        if not isinstance(asset_id, str) or not asset_id.strip():
            raise ValueError(f"asset_id must be a non-empty string, got {asset_id!r}")
        if asset_id in seen_ids:
            raise ValueError(f"duplicate asset_id {asset_id!r} — must be unique")
        seen_ids.add(asset_id)
        scenes = material_map.get("scenes") or []
        for index, scene in enumerate(scenes):
            _validate_satisfies(asset_id, index, scene, whitelist)
            scene_count += 1
            if _scene_is_captioned(scene):
                captioned += 1
            if _scene_has_vd0_label(scene):
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
            # renamed for honesty: each measures exactly the named signal, not a
            # broader notion of "reviewed" or full "label coverage".
            "asset_count": len(assets),
            "scene_count": scene_count,
            "captioned_scene_ratio": _ratio(captioned),       # scenes with a caption
            "vd0_labeled_scene_ratio": _ratio(labeled),       # scenes with >=1 VD0 label
        },
    }


def _validate_scene_shape(asset_id, index, scene):
    """A scene must be an object; declared start/end must be real numbers (not
    bool). Zero/negative-length and missing-source scenes are NOT malformed —
    they are valid evidence that the window planner declines to put on the
    timeline (MR1 honesty: skip-don't-crash). Truly malformed shapes fail."""
    ref = f"asset {asset_id!r} scene {index}"
    if not isinstance(scene, dict):
        raise ValueError(f"{ref} must be an object, got {scene!r}")
    for key in ("start", "end"):
        if key in scene and scene[key] is not None:
            value = scene[key]
            if isinstance(value, bool) or not isinstance(value, (int, float)):
                raise ValueError(f"{ref} {key} must be a number, got {value!r}")


def expand_project_material_map(source):
    """Single normalization entry: turn any accepted material-map input into the
    list of per-asset maps that scene retrieval (`rank_scenes`/`plan_ranked_windows`)
    consumes. Accepts, in priority order:

      - a ``project_material_map`` dict (``artifact_role == 'project_material_map'``)
        — its ``assets`` are expanded verbatim (no second scene schema is built);
      - a list of per-asset maps — passed through after shape validation;
      - a single per-asset map dict — wrapped in a one-element list.

    Malformed shapes fail loudly so a typo never becomes "valid material":
    a dict carrying an unknown ``artifact_role`` is rejected; a project asset
    without a non-empty ``asset_id``/``source`` is rejected; any scene whose
    declared ``start``/``end`` is non-numeric is rejected. Sourceless or
    zero-length *scenes* are left for the window planner to skip (they must not
    enter the timeline, but they are not load-time errors)."""
    if source is None:
        return None
    if isinstance(source, dict):
        role = source.get("artifact_role")
        if role == "project_material_map":
            maps = []
            for asset in source.get("assets") or []:
                if not isinstance(asset, dict):
                    raise ValueError(f"project asset must be an object, got {asset!r}")
                asset_id = asset.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id.strip():
                    raise ValueError(
                        f"project asset_id must be a non-empty string, got {asset_id!r}")
                src = asset.get("source")
                if not isinstance(src, str) or not src.strip():
                    raise ValueError(
                        f"project asset {asset_id!r} source must be a non-empty string, got {src!r}")
                scenes = asset.get("scenes") or []
                for index, scene in enumerate(scenes):
                    _validate_scene_shape(asset_id, index, scene)
                maps.append({
                    "asset_id": asset_id,
                    "asset_type": asset.get("asset_type"),
                    "source": src,
                    "duration_sec": asset.get("duration_sec"),
                    "scenes": scenes,                 # verbatim — no re-derivation
                    "speech": asset.get("speech") or [],
                })
            return maps
        if role is not None and role != "material_map":
            raise ValueError(
                f"unknown material-map artifact_role {role!r} — expected "
                f"'project_material_map' or a per-asset map")
        # a single per-asset map
        source = [source]
    maps = []
    for item in source:
        if not isinstance(item, dict):
            raise ValueError(f"per-asset material map must be an object, got {item!r}")
        asset_id = item.get("asset_id")
        for index, scene in enumerate(item.get("scenes") or []):
            _validate_scene_shape(asset_id, index, scene)
        maps.append(item)
    return maps


def load_material_db(material_db):
    """THE canonical strict load of a materials_db.json PATH. Returns (payload,
    error). A non-path/empty arg, missing/corrupt DB, non-object top level,
    non-list `files`, or non-object entry is fail-closed (never degraded to
    `{"files": []}`)."""
    if not isinstance(material_db, (str, os.PathLike)) or not str(material_db).strip():
        return None, f"material_db path must be a non-empty path, got {material_db!r}"
    try:
        with open(material_db, encoding="utf-8-sig") as handle:
            payload = json.load(handle)
    except FileNotFoundError:
        return None, f"material_db not found: {material_db}"
    except (OSError, ValueError) as exc:
        return None, f"material_db could not be parsed ({material_db}): {exc}"
    if not isinstance(payload, dict):
        return None, f"material_db top-level must be an object, got {type(payload).__name__}"
    files = payload.get("files")
    if files is not None and not isinstance(files, list):
        return None, f"material_db.files must be a list, got {type(files).__name__}"
    for index, entry in enumerate(files or []):
        if not isinstance(entry, dict):
            return None, f"material_db.files[{index}] must be an object, got {entry!r}"
    return payload, None


def _resolve_map_path(map_path, db_dir):
    path = Path(map_path)
    return path if path.is_absolute() else Path(db_dir) / path


def material_maps_from_db_payload(payload, db_dir):
    """Load the per-asset maps a (validated) db payload references, resolving a
    RELATIVE `material_map` against ``db_dir`` (NEVER the process cwd), then
    canonically normalize via `expand_project_material_map`. Returns (maps, error).
    An absent `material_map` key is skipped (existing-material-first); a declared
    map that is missing / a directory / unreadable / malformed is fail-closed."""
    raw = []
    for entry in (payload or {}).get("files") or []:
        if not isinstance(entry, dict) or "material_map" not in entry:
            continue
        map_path = entry.get("material_map")
        if not isinstance(map_path, str) or not map_path.strip():
            return None, f"material_map must be a non-empty string, got {map_path!r}"
        path = _resolve_map_path(map_path.strip(), db_dir)
        if not path.exists():
            return None, f"declared material_map not found: {map_path}"
        if path.is_dir():
            return None, f"material_map points to a directory, not a file: {map_path}"
        try:
            with path.open(encoding="utf-8-sig") as handle:
                raw.append(json.load(handle))
        except (OSError, ValueError) as exc:
            return None, f"material_map could not be read/parsed ({map_path}): {exc}"
    try:
        return expand_project_material_map(raw), None
    except (TypeError, ValueError) as exc:
        return None, f"material map malformed: {exc}"


def material_maps_from_db(material_db):
    """Canonical end-to-end loader: a materials_db.json PATH → (maps, error).
    Strict DB + db-relative `material_map` resolution + canonical normalization.
    Used by supply-review, the pre-BUILD gate, and the BUILD render path so all
    three see the SAME maps."""
    payload, error = load_material_db(material_db)
    if error:
        return None, error
    return material_maps_from_db_payload(payload, Path(material_db).parent)


def load_asset_maps(maps_dir):
    """Load every `*.map.json` under a directory (deterministic by filename)."""
    maps = []
    for path in sorted(glob.glob(os.path.join(str(maps_dir), "*.map.json"))):
        with open(path, encoding="utf-8-sig") as handle:
            maps.append(json.load(handle))
    return maps


def write_project_material_map(maps_dir, out_path, *, needs_path=None):
    material_maps = load_asset_maps(maps_dir)
    needs = None
    if needs_path is not None:
        # explicitly provided -> it must exist; silently ignoring a typo'd path
        # would build a needs-less map and hide the mistake.
        if not os.path.exists(needs_path):
            raise ValueError(f"needs_path was provided but does not exist: {needs_path}")
        with open(needs_path, encoding="utf-8-sig") as handle:
            needs = json.load(handle)
    project_map = build_project_material_map(material_maps, needs=needs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(project_map, ensure_ascii=False, indent=2),
                    encoding="utf-8")
    return {"ok": True, "project_material_map": str(path),
            "metrics": project_map["metrics"]}
