"""Run the no-render material-first happy path from source folder to review handoff."""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from tools.material_first_boundary_acceptance import run_material_first_boundary_acceptance  # noqa: E402
from tools.material_first_landing_case import _scan_source_materials  # noqa: E402
from video_pipeline_core.material_first_preview_plan import build_preview_plan  # noqa: E402
from video_pipeline_core.material_rough_cut import write_json  # noqa: E402
from video_pipeline_core.material_understanding_matrix import build_material_understanding_matrix  # noqa: E402
from video_pipeline_core.material_wall_verdict_draft import build_wall_verdict_draft  # noqa: E402


def _rewrite_matrix_paths(matrix_path: Path, *, old_dir: Path, new_dir: Path) -> None:
    payload = json.loads(matrix_path.read_text(encoding="utf-8-sig"))

    def rewrite(value):
        if not value:
            return value
        path = Path(str(value))
        try:
            rel = path.resolve().relative_to(old_dir.resolve())
        except ValueError:
            return value
        return str((new_dir / rel).resolve())

    visual = payload.get("visual") if isinstance(payload.get("visual"), dict) else {}
    if visual:
        visual["contact_sheet"] = rewrite(visual.get("contact_sheet"))
        visual["frames_dir"] = rewrite(visual.get("frames_dir"))
    for asset in payload.get("assets") or []:
        if not isinstance(asset, dict):
            continue
        evidence = asset.get("visual_evidence") if isinstance(asset.get("visual_evidence"), dict) else {}
        if evidence.get("photo"):
            evidence["photo"] = rewrite(evidence.get("photo"))
        for frame in evidence.get("keyframes") or []:
            if isinstance(frame, dict) and frame.get("image_path"):
                frame["image_path"] = rewrite(frame.get("image_path"))
    write_json(matrix_path, payload)


def run_material_first_happy_path(
    run_dir,
    *,
    source_dir,
    max_assets=12,
    frame_budget=3,
    roles=None,
    preview_target_duration_sec=72.0,
) -> dict:
    root = Path(run_dir).resolve()
    source = Path(source_dir).resolve()
    if root.exists():
        shutil.rmtree(root)
    prep = root.parent / f"{root.name}._prep"
    if prep.exists():
        shutil.rmtree(prep)
    prep.mkdir(parents=True)

    required_roles = roles or ["opening", "training", "closing"]
    materials_db = _scan_source_materials(source, max_assets=int(max_assets))
    materials_db_path = prep / "materials_db.source_candidates.json"
    write_json(materials_db_path, materials_db)

    matrix_dir = prep / "material_understanding"
    matrix = build_material_understanding_matrix(
        materials_db,
        out_dir=matrix_dir,
        max_assets=int(max_assets),
        frame_budget=int(frame_budget),
    )
    verdict_path = prep / "material_wall_review_verdict.draft.json"
    verdict = build_wall_verdict_draft(
        matrix,
        out_path=verdict_path,
        required_roles=required_roles,
    )
    preview = build_preview_plan(
        matrix,
        verdict,
        target_duration_sec=float(preview_target_duration_sec),
        min_duration_sec=60.0,
        max_duration_sec=90.0,
        clip_duration_sec=6.0,
        roles=required_roles,
    )
    preview_path = prep / "preview_rough_cut_plan.json"
    write_json(preview_path, preview)

    acceptance = run_material_first_boundary_acceptance(
        root,
        source_dir=source,
        wall_verdict=verdict_path,
        max_assets=int(max_assets),
    )
    if root.exists():
        shutil.copy2(materials_db_path, root / "materials_db.source_candidates.json")
        shutil.copytree(matrix_dir, root / "material_understanding", dirs_exist_ok=True)
        _rewrite_matrix_paths(
            root / "material_understanding" / "material_understanding_matrix.json",
            old_dir=matrix_dir,
            new_dir=root / "material_understanding",
        )
        shutil.copy2(verdict_path, root / "material_wall_review_verdict.draft.json")
        shutil.copy2(preview_path, root / "preview_rough_cut_plan.json")
    shutil.rmtree(prep, ignore_errors=True)

    report = acceptance.get("report") or {}
    summary = {
        "artifact_role": "material_first_happy_path_report",
        "version": 1,
        "ok": bool(acceptance.get("ok")),
        "run_dir": str(root),
        "source_dir": str(source),
        "materials_db": str(root / "materials_db.source_candidates.json"),
        "matrix": str(root / "material_understanding" / "material_understanding_matrix.json"),
        "contact_sheet": str(root / "material_understanding" / "material_understanding_contact_sheet.jpg"),
        "wall_verdict_draft": str(root / "material_wall_review_verdict.draft.json"),
        "preview_rough_cut_plan": str(root / "preview_rough_cut_plan.json"),
        "preview_duration_sec": preview.get("total_duration_sec"),
        "preview_clip_count": preview.get("clip_count"),
        "primary_selection": verdict.get("primary_selection") or {},
        "acceptance_report": str(root / "material_first_boundary_acceptance_report.json"),
        "next_action": report.get("next_action"),
        "failed_stage": report.get("failed_stage"),
        "rendered": (root / "final.mp4").exists(),
        "limitations": [
            "This wrapper does not render final.mp4.",
            "The wall verdict is a draft and remains reviewable.",
            "Material truth still belongs to Material Map / review apply / delivery gates.",
        ],
    }
    write_json(root / "material_first_happy_path_report.json", summary)
    return summary


def _roles(value: str) -> list[str]:
    return [part.strip() for part in str(value or "").split(",") if part.strip()]


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True, help="run folder to create")
    parser.add_argument("--source-dir", required=True, help="source material folder")
    parser.add_argument("--max-assets", type=int, default=12)
    parser.add_argument("--frame-budget", type=int, default=3)
    parser.add_argument("--roles", default="opening,training,closing")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_material_first_happy_path(
        args.out,
        source_dir=args.source_dir,
        max_assets=args.max_assets,
        frame_budget=args.frame_budget,
        roles=_roles(args.roles),
    )
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} next_action={result.get('next_action')} run_dir={result['run_dir']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
