"""Deterministic material-first golden path acceptance helper."""
from __future__ import annotations

import json
import shutil
from pathlib import Path

from PIL import Image

from tools.material_first_boundary_acceptance import run_material_first_boundary_acceptance
from video_pipeline_core.asset_paths import build_asset_path_audit
from video_pipeline_core.material_rough_cut import write_json


SCENARIO_ID = "material-first-golden-path"
FIXTURE_REL = Path("tests") / "fixtures" / "material_first_golden" / "fixture_manifest.json"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _fresh_work_dir(root: Path) -> Path:
    work_dir = root / ".tmp" / "material_first_golden_path"
    if work_dir.exists():
        resolved = work_dir.resolve()
        if ".tmp" not in resolved.parts or "material_first_golden_path" not in resolved.parts:
            raise ValueError(f"refusing to clean non-golden fixture path: {work_dir}")
        shutil.rmtree(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    return work_dir


def _load_manifest() -> dict:
    return _read_json(_repo_root() / FIXTURE_REL)


def _write_jpeg(path: Path, color: list[int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 45), color=tuple(color)).save(path, "JPEG")


def _prepare_fixture(root: Path) -> dict:
    manifest = _load_manifest()
    work_dir = _fresh_work_dir(root)
    source_dir = work_dir / "source"
    for item in manifest.get("media") or []:
        _write_jpeg(source_dir / item["relative_path"], item["color"])
    verdict_path = work_dir / "material_wall_review_verdict.json"
    write_json(verdict_path, manifest["wall_verdict"])
    brief_path = work_dir / "brief.json"
    write_json(brief_path, manifest.get("brief") or {})
    return {
        "manifest": manifest,
        "work_dir": work_dir,
        "source_dir": source_dir,
        "verdict_path": verdict_path,
        "brief_path": brief_path,
        "run_dir": work_dir / "run",
    }


def _check(check_id: str, ok: bool, description: str, *, artifacts=None, metrics=None) -> dict:
    return {
        "id": check_id,
        "ok": bool(ok),
        "description": description,
        "artifacts": artifacts or [],
        "metrics": metrics or {},
    }


def build_material_first_golden_path_report(root: str | Path | None = None) -> dict:
    repo = Path(root or _repo_root()).resolve()
    fixture = _prepare_fixture(repo)
    result = run_material_first_boundary_acceptance(
        fixture["run_dir"],
        source_dir=fixture["source_dir"],
        wall_verdict=fixture["verdict_path"],
        max_assets=len(fixture["manifest"].get("media") or []),
    )
    run_dir = Path(result["run_dir"])
    boundary = result.get("report") or {}
    project_map = _read_json(run_dir / "project_material_map.json") if (run_dir / "project_material_map.json").exists() else {}
    materials_db = _read_json(run_dir / "materials_db.json") if (run_dir / "materials_db.json").exists() else {}
    material_delta = _read_json(run_dir / "material_delta.json") if (run_dir / "material_delta.json").exists() else {}
    rough_cut = _read_json(run_dir / "rough_cut_plan.json") if (run_dir / "rough_cut_plan.json").exists() else {}
    stage4 = _read_json(run_dir / "stage4_build_smoke_report.json") if (run_dir / "stage4_build_smoke_report.json").exists() else {}
    stage5 = _read_json(run_dir / "stage5_final_review_smoke_report.json") if (run_dir / "stage5_final_review_smoke_report.json").exists() else {}
    asset_path_audit = build_asset_path_audit(run_dir, strict=True, repo_root=repo)
    delta_ready = bool(material_delta.get("ok") and material_delta.get("ready_for_build"))
    final_absent = not (run_dir / "final.mp4").exists()
    material_refs = [
        str(entry.get("path") or "")
        for entry in materials_db.get("files") or []
    ]
    project_refs = [
        str(asset.get("source") or "")
        for asset in project_map.get("assets") or []
    ]
    asset_store_refs = material_refs + project_refs
    asset_store_imported = bool(
        len(material_refs) == 3
        and all(ref.startswith("assets/materials/") for ref in asset_store_refs)
        and all((run_dir / ref).exists() for ref in material_refs)
    )

    artifacts = [
        fixture["brief_path"],
        fixture["source_dir"],
        fixture["verdict_path"],
        *(run_dir / ref for ref in material_refs),
        run_dir / "material_first_boundary_acceptance_report.json",
        run_dir / "project_material_map.json",
        run_dir / "material_delta.json",
        run_dir / "material_map_lifecycle.json",
        run_dir / "rough_cut_plan.json",
        run_dir / "timeline_build.json",
        run_dir / "stage4_build_smoke_report.json",
        run_dir / "stage5_final_review_smoke_report.json",
    ]
    rel_artifacts = [_rel(repo, path) for path in artifacts if path.exists()]
    checks = [
        _check(
            "runtime_fixture_generation",
            fixture["source_dir"].exists() and len(list(fixture["source_dir"].rglob("*.jpg"))) == 3,
            "tracked manifest generated the deterministic source media and wall verdict",
            artifacts=[_rel(repo, fixture["brief_path"]), _rel(repo, fixture["source_dir"]), _rel(repo, fixture["verdict_path"])],
            metrics={"fixture_source": "tracked_manifest_runtime_generated_media"},
        ),
        _check(
            "boundary_acceptance",
            bool(boundary.get("ok")),
            "existing material-first boundary acceptance reached Stage 5 review",
            artifacts=[_rel(repo, run_dir / "material_first_boundary_acceptance_report.json")],
            metrics={"next_action": boundary.get("next_action"), "failed_stage": boundary.get("failed_stage")},
        ),
        _check(
            "asset_store_import",
            asset_store_imported,
            "accepted source assets were copied into the run-local material asset store",
            artifacts=[_rel(repo, run_dir / ref) for ref in material_refs if (run_dir / ref).exists()],
            metrics={
                "asset_store": "assets/materials",
                "imported_ref_count": len(material_refs),
                "all_material_refs_run_relative": all(ref.startswith("assets/materials/") for ref in asset_store_refs),
            },
        ),
        _check(
            "asset_path_audit_strict",
            bool(asset_path_audit.get("ok")),
            "material-first golden run has no strict material/build/effect/audio absolute path findings",
            artifacts=[],
            metrics={
                "strict": True,
                "finding_count": asset_path_audit.get("finding_count"),
                "strict_finding_count": asset_path_audit.get("strict_finding_count"),
            },
        ),
        _check(
            "project_material_map",
            len(project_map.get("assets") or []) == 3,
            "project material map contains one accepted asset for opening, training, and closing",
            artifacts=[_rel(repo, run_dir / "project_material_map.json")],
            metrics={"asset_count": len(project_map.get("assets") or [])},
        ),
        _check(
            "material_delta",
            delta_ready,
            "material delta is ok and ready for build",
            artifacts=[_rel(repo, run_dir / "material_delta.json")],
            metrics={"ok": bool(material_delta.get("ok")), "ready_for_build": bool(material_delta.get("ready_for_build"))},
        ),
        _check(
            "stage4_build",
            bool(stage4.get("ok")),
            "stage4 build smoke sees coherent rough cut and timeline artifacts",
            artifacts=[_rel(repo, run_dir / "stage4_build_smoke_report.json")],
            metrics={"clip_count": stage4.get("clip_count"), "timeline_clip_count": stage4.get("timeline_clip_count")},
        ),
        _check(
            "stage5_final_review",
            bool(stage5.get("ok")),
            "stage5 final-review smoke is ready for render or human review",
            artifacts=[_rel(repo, run_dir / "stage5_final_review_smoke_report.json")],
            metrics={"next_action": stage5.get("next_action")},
        ),
        _check(
            "final_delivery_not_claimed",
            final_absent,
            "golden path acceptance is boundary/build-ready only and does not create final.mp4",
            artifacts=[],
            metrics={"final_mp4_absent": final_absent},
        ),
    ]
    failures = [
        {"id": check["id"], "description": check["description"], "metrics": check.get("metrics") or {}}
        for check in checks
        if not check["ok"]
    ]
    report = {
        "artifact_role": "material_first_golden_path_acceptance",
        "version": 1,
        "scenario": SCENARIO_ID,
        "ok": not failures,
        "blocked": bool(failures),
        "next_action": boundary.get("next_action") or "needs-context",
        "fixture_manifest": FIXTURE_REL.as_posix(),
        "fixture_source": "tracked_manifest_runtime_generated_media",
        "source_dir": _rel(repo, fixture["source_dir"]),
        "run_dir": _rel(repo, run_dir),
        "checks": checks,
        "artifacts": sorted(set(rel_artifacts)),
        "failures": failures,
        "metrics": {
            "fixture_source": "tracked_manifest_runtime_generated_media",
            "material_asset_count": len(project_map.get("assets") or []),
            "asset_store_imported": asset_store_imported,
            "asset_path_audit_strict_ok": bool(asset_path_audit.get("ok")),
            "asset_path_audit_strict_finding_count": asset_path_audit.get("strict_finding_count"),
            "rough_clip_count": rough_cut.get("clip_count") or len(rough_cut.get("clips") or []),
            "delta_ready_for_build": delta_ready,
            "boundary_ok": bool(boundary.get("ok")),
            "final_mp4_absent": final_absent,
        },
    }
    write_json(run_dir / "material_first_golden_path_acceptance_report.json", report)
    return report


def write_material_first_golden_path_report(out_path: str | Path, root: str | Path | None = None) -> dict:
    report = build_material_first_golden_path_report(root)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return report
