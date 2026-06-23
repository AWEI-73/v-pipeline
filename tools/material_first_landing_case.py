"""Build a deterministic material-first boundary acceptance run folder."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.boundary_smoke import run_boundary  # noqa: E402
from video_pipeline_core import material_map_lifecycle  # noqa: E402
from video_pipeline_core.material_wall import apply_material_wall_review, write_material_wall_request  # noqa: E402
from video_pipeline_core.material_map_review_apply import apply_review_to_maps  # noqa: E402
from video_pipeline_core.material_rough_cut import build_rough_cut_plan, load_json, write_json  # noqa: E402

MEDIA_EXTS = {".mp4", ".mov", ".m4v", ".avi", ".mkv", ".jpg", ".jpeg", ".png", ".heic", ".heif"}
PHOTO_EXTS = {".jpg", ".jpeg", ".png", ".heic", ".heif"}
FINAL_MASTER_MARKERS = (
    "最終版",
    "final",
    "master",
    "export",
    "render",
    "結訓影片-終",
)
NEEDS = [
    ("nd_opening", "opening", "establish the training/event opening"),
    ("nd_training", "training", "show learning or practice"),
    ("nd_closing", "closing", "close with group energy or completion"),
]
NEED_KEYWORDS = {
    "nd_opening": ("進場", "片頭", "開頭", "空拍", "早會", "工安早會"),
    "nd_training": (
        "實習",
        "訓練",
        "工安體感",
        "活線",
        "拖拉電纜",
        "裝桿",
        "洗礙子",
        "換桿",
        "基本",
        "丙級",
    ),
    "nd_closing": ("主任勉勵", "主任", "感謝導師", "結尾", "隊呼", "合照", "運動會", "慶生"),
}


def _copytree_contents(source: Path, target: Path):
    target.mkdir(parents=True, exist_ok=True)
    for item in source.iterdir():
        destination = target / item.name
        if item.is_dir():
            if destination.exists():
                shutil.rmtree(destination)
            shutil.copytree(item, destination)
        else:
            shutil.copy2(item, destination)


def _is_final_master_candidate(path: Path) -> bool:
    text = path.name.lower()
    return any(marker.lower() in text for marker in FINAL_MASTER_MARKERS)


def _material_caption(source_root: Path, path: Path) -> str:
    rel = path.relative_to(source_root)
    parts = [part for part in rel.parts[:-1]]
    stem = path.stem
    tokens = " / ".join(parts + [stem])
    return f"folder/file hint: {tokens}"


def _scan_source_materials(source_dir: Path, *, max_assets: int) -> dict:
    candidates = []
    skipped = []
    for path in sorted(source_dir.rglob("*")):
        if not path.is_file() or path.suffix.lower() not in MEDIA_EXTS:
            continue
        if _is_final_master_candidate(path):
            skipped.append({"path": str(path), "reason": "looks like final/master export"})
            continue
        candidates.append(path)

    selected_paths = _select_source_paths(source_dir, candidates, max_assets=max_assets)
    selected_set = {str(path) for path in selected_paths}
    for path in candidates:
        if str(path) not in selected_set:
            skipped.append({"path": str(path), "reason": "not selected for bounded dry run"})

    files = []
    for counter, path in enumerate(selected_paths, start=1):
        asset_id = f"real_{counter:04d}"
        is_photo = path.suffix.lower() in PHOTO_EXTS
        files.append({
            "id": asset_id,
            "path": str(path),
            "type": "photo" if is_photo else "video",
            "format": path.suffix.lower().lstrip("."),
            "tags_from_path": list(path.relative_to(source_dir).parts[:-1]),
            "size_bytes": path.stat().st_size,
            "metadata": {"duration_sec": 4.0 if is_photo else 8.0},
            "vlm_caption": _material_caption(source_dir, path),
            "caption_source": "folder_file_hint_dry_run",
        })
    return {
        "artifact_role": "materials_db",
        "source_dir": str(source_dir),
        "total": len(files),
        "files": files,
        "skipped": skipped,
    }


def _path_hint(source_root: Path, path: Path) -> str:
    try:
        rel = path.relative_to(source_root)
    except ValueError:
        rel = path
    return "/".join(rel.parts)


def _score_for_need(source_root: Path, path: Path, need_id: str) -> tuple[int, int, int, str]:
    hint = _path_hint(source_root, path)
    score = 0
    for keyword in NEED_KEYWORDS.get(need_id, ()):
        if keyword and keyword in hint:
            score += 10
    # Prefer shorter path hints when scores tie; they are usually explicit folders.
    photo_penalty = 1 if path.suffix.lower() in PHOTO_EXTS else 0
    return (-score, photo_penalty, len(hint), hint)


def _select_source_paths(source_root: Path, candidates: list[Path], *, max_assets: int) -> list[Path]:
    selected = []
    used = set()
    for need_id, _kind, _purpose in NEEDS:
        ranked = [
            path for path in sorted(candidates, key=lambda item: _score_for_need(source_root, item, need_id))
            if str(path) not in used
        ]
        if ranked:
            chosen = ranked[0]
            selected.append(chosen)
            used.add(str(chosen))
    for path in candidates:
        if len(selected) >= max_assets:
            break
        if str(path) in used:
            continue
        selected.append(path)
        used.add(str(path))
    return selected[:max_assets]


def _selected_wall_review_db(reviewed: dict) -> dict:
    selected = [
        entry for entry in reviewed.get("files") or []
        if entry.get("selected_for_material_map") is True
    ]
    out = dict(reviewed)
    out["files"] = selected
    out["total"] = len(selected)
    return out


def _write_source_case_inputs(run_dir: Path, source_dir: Path, *, max_assets: int, wall_verdict=None):
    db = _scan_source_materials(source_dir, max_assets=max_assets)
    wall_dir = run_dir / "verify" / "material_wall"
    write_material_wall_request(
        db,
        wall_dir,
        wall_dir / "material_wall_request.json",
        limit=max_assets,
    )
    if wall_verdict:
        write_json(run_dir / "materials_db.source_candidates.json", db)
        reviewed = apply_material_wall_review(db, load_json(wall_verdict))
        write_json(run_dir / "materials_db.wall_reviewed.json", reviewed)
        db = _selected_wall_review_db(reviewed)
    if len(db["files"]) < 3:
        raise ValueError("source folder dry run requires at least 3 usable media files")
    maps_dir = run_dir / "maps"
    maps_dir.mkdir(parents=True, exist_ok=True)
    write_json(run_dir / "material_needs.json", {
        "artifact_role": "material_needs",
        "version": 1,
        "project": "material_first_real_dry",
        "needs": [
            {
                "need_id": need_id,
                "category": "scene",
                "type": kind,
                "purpose": purpose,
                "count": 1,
                "fallback_tier": 1,
                "must_have": True,
            }
            for need_id, kind, purpose in NEEDS
        ],
    })

    decisions = []
    for index, (entry, (need_id, _kind, _purpose)) in enumerate(zip(db["files"], NEEDS)):
        scene = {
            "start": 0.0,
            "end": 4.0 if entry["type"] == "photo" else 8.0,
            "midpoint": 2.0 if entry["type"] == "photo" else 4.0,
            "kind": "still" if entry["type"] == "photo" else "video",
            "caption": entry["vlm_caption"],
            "map_mode": "source_folder_dry_run",
        }
        material_map = {
            "artifact_role": "material_map",
            "version": 1,
            "asset_id": entry["id"],
            "asset_type": entry["type"],
            "source": entry["path"],
            "duration_sec": 4.0 if entry["type"] == "photo" else 8.0,
            "map_mode": "source_folder_dry_run",
            "scenes": [scene],
            "speech": [],
        }
        map_path = maps_dir / f"{entry['id']}.map.json"
        write_json(map_path, material_map)
        entry["material_map"] = str(map_path)
        entry["material_map_status"] = "mapped"
        decisions.append({
            "asset_id": entry["id"],
            "scene_index": 0,
            "need_id": need_id,
            "status": "accepted",
            "visual_evidence": [entry["vlm_caption"]],
            "reviewer": "material_first_landing_case:folder_hint",
        })

    write_json(run_dir / "materials_db.json", db)
    write_json(run_dir / "material_map_review_verdict.json", {
        "artifact_role": "material_map_review_verdict",
        "version": 1,
        "reviewer": "material_first_landing_case:folder_hint",
        "decisions": decisions,
    })
    write_json(run_dir / "segment_contract.json", {
        "material_needs_ref": "material_needs.json",
        "segments": [
            {
                "segment": index + 1,
                "requested_duration_sec": 4.0,
                "core": {
                    "section_role": kind,
                    "story_purpose": purpose,
                    "timeline_source": "fixed",
                },
                "material_fit": {
                    "visual_desc": purpose,
                    "reason": "dry boundary segment binds to reviewed material-map need",
                    "need_refs": [need_id],
                },
                "audio": {"role": "music", "reason": "dry boundary skips audio render"},
                "visual_style": {"layout": "single", "pace": "hold", "reason": "reviewable rough cut"},
                "text_layer": "none",
            }
            for index, (need_id, kind, purpose) in enumerate(NEEDS)
        ],
    })


def run_material_first_landing_case(run_dir, *, source_dir=None, max_assets=12, wall_verdict=None) -> dict:
    run_dir = Path(run_dir).resolve()
    if run_dir.exists():
        shutil.rmtree(run_dir)
    run_dir.mkdir(parents=True)

    source_mode = bool(source_dir)
    if source_mode:
        _write_source_case_inputs(
            run_dir,
            Path(source_dir).resolve(),
            max_assets=max_assets,
            wall_verdict=wall_verdict,
        )
    else:
        repo = Path(__file__).resolve().parents[1]
        fixture_input = repo / "examples" / "boundary_fixtures" / "stage3_review_apply" / "input"
        _copytree_contents(fixture_input, run_dir)

    write_json(run_dir / "video_intent.json", {
        "artifact_role": "video_intent",
        "entry_path": "material-first",
        "video_type": "graduation-event",
        "goal": "prove existing material can move from map review to rough timeline",
    })

    apply_review_to_maps(
        run_dir / "maps",
        run_dir / "material_needs.json",
        run_dir / "material_map_review_verdict.json",
        run_dir / "project_material_map.json",
        material_db_path=run_dir / "materials_db.json",
    )
    lifecycle = material_map_lifecycle.run_lifecycle(
        out_dir=run_dir,
        needs_ref=run_dir / "material_needs.json",
        material_db_ref=run_dir / "materials_db.json",
        contract_ref=run_dir / "segment_contract.json",
    )
    write_json(run_dir / "material_map_lifecycle.json", lifecycle)

    rough = build_rough_cut_plan(
        load_json(run_dir / "segment_contract.json"),
        load_json(run_dir / "project_material_map.json"),
    )
    write_json(run_dir / "rough_cut_plan.json", rough)
    write_json(run_dir / "timeline_build.json", rough["timeline_build"])
    write_json(run_dir / "editor_review.json", {
        "artifact_role": "editor_review",
        "decision": "human_review",
        "reason": "rough timeline is ready for review; render is intentionally skipped",
    })

    stage_dir = run_dir / "_stage5_boundary"
    input_dir = stage_dir / "input"
    input_dir.mkdir(parents=True)
    for name in ("rough_cut_plan.json", "timeline_build.json", "editor_review.json"):
        shutil.copy2(run_dir / name, input_dir / name)
    write_json(input_dir / "boundary_config.json", {
        "stage": "stage5_final_review",
        "expected": {"pass": True},
    })
    report = run_boundary(stage_dir)
    write_json(run_dir / "boundary_report.json", report)

    return {
        "ok": bool(lifecycle.get("can_build") and rough.get("ok") and report.get("pass")),
        "run_dir": str(run_dir),
        "lifecycle_stage": lifecycle.get("stage"),
        "rough_clip_count": rough.get("clip_count"),
        "boundary_pass": report.get("pass"),
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True, help="run folder to create")
    parser.add_argument("--source-dir", help="real material folder for source-folder dry run")
    parser.add_argument("--max-assets", type=int, default=12)
    parser.add_argument("--wall-verdict", help="optional material_wall_review_verdict.json to bound mapping")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    result = run_material_first_landing_case(
        args.out,
        source_dir=args.source_dir,
        max_assets=args.max_assets,
        wall_verdict=args.wall_verdict,
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} run_dir={result['run_dir']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
