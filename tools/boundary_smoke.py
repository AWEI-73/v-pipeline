"""Run a small pipeline boundary smoke against canonical gates.

This runner is intentionally thin: it prepares fixture input, calls the same
production artifact functions the runtime uses, and records their verdict. It
does not reimplement stage logic.
"""
from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

from video_pipeline_core import material_map_lifecycle
from video_pipeline_core.material_map_review_apply import apply_review_to_maps


def _load_json(path: Path):
    with path.open(encoding="utf-8-sig") as handle:
        return json.load(handle)


def _write_json(path: Path, payload):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _copy_input(stage_dir: Path) -> Path:
    source = stage_dir / "input"
    if not source.exists():
        raise FileNotFoundError(f"boundary input folder not found: {source}")
    work = stage_dir / "actual" / "work"
    if work.exists():
        shutil.rmtree(work)
    shutil.copytree(source, work)
    return work


def _ref(root: Path, config: dict, key: str, default: str) -> Path:
    return root / str(config.get(key) or default)


def _expected_regressions(config: dict, lifecycle: dict) -> list[str]:
    expected = config.get("expected") or {}
    regressions = []
    expected_stage = expected.get("stage")
    if expected_stage and lifecycle.get("stage") != expected_stage:
        regressions.append(
            f"expected lifecycle stage {expected_stage!r}, got {lifecycle.get('stage')!r}"
        )
    if "can_build" in expected and bool(lifecycle.get("can_build")) != bool(expected["can_build"]):
        regressions.append(
            f"expected can_build={bool(expected['can_build'])}, "
            f"got {bool(lifecycle.get('can_build'))}"
        )
    return regressions


def run_boundary(stage_dir):
    stage_dir = Path(stage_dir)
    config_path = stage_dir / "input" / "boundary_config.json"
    config = _load_json(config_path) if config_path.exists() else {}
    stage = config.get("stage")
    if stage != "stage3_review_apply":
        raise ValueError(f"unsupported boundary stage: {stage!r}")

    actual_dir = stage_dir / "actual"
    actual_dir.mkdir(parents=True, exist_ok=True)
    work = _copy_input(stage_dir)

    maps_dir = _ref(work, config, "maps_dir", "maps")
    needs_path = _ref(work, config, "needs", "material_needs.json")
    verdict_path = _ref(work, config, "verdict", "material_map_review_verdict.json")
    material_db_path = _ref(work, config, "material_db", "materials_db.json")
    contract_path = _ref(work, config, "contract", "segment_contract.json")
    project_map_path = actual_dir / "project_material_map.json"

    apply_result = apply_review_to_maps(
        maps_dir,
        needs_path,
        verdict_path,
        project_map_path,
        material_db_path=material_db_path if material_db_path.exists() else None,
        skipped_policy=config.get("skipped_policy"),
    )
    _write_json(actual_dir / "material_map_review_apply_result.json", apply_result)

    lifecycle = material_map_lifecycle.run_lifecycle(
        out_dir=actual_dir / "lifecycle",
        needs_ref=needs_path,
        material_db_ref=material_db_path,
        contract_ref=contract_path,
    )
    _write_json(actual_dir / "material_map_lifecycle.json", lifecycle)

    regressions = _expected_regressions(config, lifecycle)
    report = {
        "artifact_role": "boundary_report",
        "version": 1,
        "stage": stage,
        "gate_source": "material_map_lifecycle",
        "gate_status": lifecycle.get("stage"),
        "pass": not regressions,
        "regressions": regressions,
        "refs": {
            "work": str(work),
            "apply_result": str(actual_dir / "material_map_review_apply_result.json"),
            "lifecycle": str(actual_dir / "material_map_lifecycle.json"),
        },
    }
    _write_json(actual_dir / "boundary_report.json", report)
    return report


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("stage_dir")
    args = parser.parse_args(argv)
    report = run_boundary(args.stage_dir)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
