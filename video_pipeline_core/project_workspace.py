"""project_workspace.py — external project/run workspace helpers.

Repo stays as engine/source. Real project inputs and run outputs live outside
the repo by default under ~/video_pipeline_projects.
"""
import argparse
import json
import os
import re
from datetime import datetime
from pathlib import Path
from pathlib import PurePosixPath


REPO_DIR = Path(__file__).resolve().parents[1]

RUN_LAYOUT = [
    "spec",
    "build",
    "verify",
    "materials/raw",
    "materials/selected",
    "materials/generated",
    "materials/stock",
    "nodes",
    "logs",
    "thumbs",
    "brownfield",
]

RUN_LAYOUT_FOLDERS = {
    "spec": "spec",
    "build": "build",
    "verify": "verify",
    "materials_raw": "materials/raw",
    "materials_selected": "materials/selected",
    "materials_generated": "materials/generated",
    "materials_stock": "materials/stock",
    "nodes": "nodes",
    "logs": "logs",
    "thumbs": "thumbs",
    "brownfield": "brownfield",
}

RUN_ARTIFACT_CLASSES = {
    "canonical": [
        "segment_contract.json",
        "material_needs.json",
        "project_material_map.json",
        "materials_db.json",
        "timeline.json",
        "final.mp4",
        "state.json",
        "artifact_manifest.json",
    ],
    "workbench_draft": [
        "preview_timeline.json",
        "timeline_patch.json",
        "patched_draft_timeline.json",
        "workbench_contract_patch.json",
        "subtitle_patch.json",
        "audio_cue_patch.json",
        "effect_patch.json",
        "workbench_handoff.json",
        "workbench_review_report.json",
        "workbench_review_report.md",
        "workbench_export.mp4",
    ],
    "orchestration": [
        "route_orchestrator_state.json",
        "route_subagent_task.json",
        "route_subagent_result.json",
        "route_orchestrator_acceptance.json",
    ],
    "derived_cache_dirs": [
        "thumbs",
        "workbench_thumbs",
        "workbench_proxy",
    ],
}


def default_project_root():
    raw = os.environ.get("VIDEO_PIPELINE_PROJECT_ROOT")
    if raw:
        return Path(raw).expanduser()
    if os.name == "nt":
        return Path.home() / "Desktop" / "video_project"
    return Path.home() / "video_pipeline_projects"


def slugify(name):
    text = str(name).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = text.strip("-")
    return text or "video-project"


def _repo_project_dir(repo_dir=None):
    base = Path(repo_dir) if repo_dir else REPO_DIR
    return base / ".project"


def _write_json(path, data):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    return path


def _repo_relative(path, *, repo_dir=None):
    base = Path(repo_dir) if repo_dir else REPO_DIR
    rel = os.path.relpath(Path(path).expanduser(), start=base)
    return Path(rel).as_posix()


def _project_pointer(project_dir, active_run=None, *, repo_dir=None):
    project_dir = Path(project_dir).expanduser()
    project_root = project_dir.parent
    payload = {
        "project_root": _repo_relative(project_root, repo_dir=repo_dir),
        "active_project": project_dir.name,
        "active_run": None,
    }
    if active_run:
        active_run = Path(active_run).expanduser()
        try:
            payload["active_run"] = Path(active_run.relative_to(project_dir)).as_posix()
        except ValueError:
            payload["active_run"] = Path(active_run).as_posix()
    return payload


def build_run_layout(project_dir, run_dir):
    project_dir = Path(project_dir).expanduser()
    run_dir = Path(run_dir).expanduser()
    return {
        "artifact_role": "run_layout",
        "version": 1,
        "project_dir": str(project_dir),
        "run_dir": str(run_dir),
        "folders": dict(RUN_LAYOUT_FOLDERS),
        "artifact_classes": {
            key: list(value)
            for key, value in RUN_ARTIFACT_CLASSES.items()
        },
        "policy": {
            "repo_is_engine": True,
            "workbench_is_draft_only": True,
            "official_render_owned_by_backend": True,
            "material_map_is_source_of_truth": True,
        },
    }


def _layout_error(errors, code, message, **extra):
    item = {"code": code, "message": message}
    item.update(extra)
    errors.append(item)


def _safe_layout_rel(value):
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip().replace("\\", "/")
    if ":" in text:
        return None
    path = PurePosixPath(text)
    if path.is_absolute() or ".." in path.parts:
        return None
    return path.as_posix()


def _load_run_layout(layout_path, errors):
    if not layout_path.is_file():
        _layout_error(errors, "missing_layout", "run_layout.json is missing")
        return None
    try:
        payload = json.loads(layout_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        _layout_error(errors, "malformed_layout", f"run_layout.json is malformed: {exc}")
        return None
    except OSError as exc:
        _layout_error(errors, "unreadable_layout", f"run_layout.json is unreadable: {exc}")
        return None
    if not isinstance(payload, dict):
        _layout_error(errors, "invalid_layout_shape", "run_layout.json must be a JSON object")
        return None
    return payload


def validate_run_layout(run_dir):
    """Validate run_layout.json and artifact ownership for a run directory."""
    run_dir = Path(run_dir).expanduser()
    layout_path = run_dir / "run_layout.json"
    errors = []
    warnings = []
    folder_report = {}
    present_artifacts = {
        "canonical": [],
        "workbench_draft": [],
        "orchestration": [],
        "derived_cache_dirs": [],
    }

    layout = _load_run_layout(layout_path, errors)
    if layout is None:
        return {
            "artifact_role": "run_layout_validation",
            "version": 1,
            "ok": False,
            "run_dir": str(run_dir),
            "layout_path": str(layout_path),
            "errors": errors,
            "warnings": warnings,
            "folders": folder_report,
            "present_artifacts": present_artifacts,
        }

    if layout.get("artifact_role") != "run_layout":
        _layout_error(errors, "invalid_artifact_role", "artifact_role must be run_layout")
    if layout.get("version") != 1:
        _layout_error(errors, "invalid_version", "run_layout version must be 1")

    declared_run = layout.get("run_dir")
    if isinstance(declared_run, str) and declared_run.strip():
        try:
            if Path(declared_run).expanduser().resolve() != run_dir.resolve():
                warnings.append({
                    "code": "run_dir_mismatch",
                    "message": "run_layout run_dir differs from the validated directory",
                    "declared": declared_run,
                })
        except OSError:
            warnings.append({
                "code": "run_dir_unresolvable",
                "message": "declared run_dir could not be resolved",
                "declared": declared_run,
            })

    folders = layout.get("folders")
    if not isinstance(folders, dict):
        _layout_error(errors, "invalid_folders_shape", "folders must be an object")
        folders = {}
    for key, rel in sorted(folders.items()):
        safe = _safe_layout_rel(rel)
        if safe is None:
            _layout_error(
                errors,
                "unsafe_folder_path",
                "folder path must be a non-empty relative path inside the run directory",
                key=key,
                value=rel,
            )
            folder_report[str(key)] = {"path": rel, "status": "unsafe"}
            continue
        path = run_dir / safe
        if not path.exists():
            _layout_error(errors, "missing_folder", "declared folder is missing", key=key, path=safe)
            status = "missing"
        elif not path.is_dir():
            _layout_error(errors, "folder_path_not_directory", "declared folder is not a directory", key=key, path=safe)
            status = "not_directory"
        else:
            status = "ok"
        folder_report[str(key)] = {"path": safe, "status": status}

    classes = layout.get("artifact_classes")
    if not isinstance(classes, dict):
        _layout_error(errors, "invalid_artifact_classes_shape", "artifact_classes must be an object")
        classes = {}

    owners = {}
    for class_name in ("canonical", "workbench_draft", "orchestration", "derived_cache_dirs"):
        entries = classes.get(class_name)
        if not isinstance(entries, list):
            _layout_error(errors, "invalid_artifact_class", f"{class_name} must be a list", class_name=class_name)
            continue
        for raw in entries:
            safe = _safe_layout_rel(raw)
            if safe is None:
                _layout_error(
                    errors,
                    "unsafe_artifact_path",
                    "artifact path must be a non-empty relative path inside the run directory",
                    class_name=class_name,
                    value=raw,
                )
                continue
            previous = owners.setdefault(safe, class_name)
            if previous != class_name:
                _layout_error(
                    errors,
                    "duplicate_artifact_owner",
                    "artifact path is owned by multiple classes",
                    path=safe,
                    first_owner=previous,
                    second_owner=class_name,
                )
            path = run_dir / safe
            if class_name == "derived_cache_dirs":
                if path.exists():
                    if path.is_dir():
                        present_artifacts[class_name].append(safe)
                    else:
                        _layout_error(
                            errors,
                            "cache_path_not_directory",
                            "derived cache path exists but is not a directory",
                            path=safe,
                        )
                continue
            if path.exists():
                present_artifacts[class_name].append(safe)

    for key in present_artifacts:
        present_artifacts[key] = sorted(set(present_artifacts[key]))

    return {
        "artifact_role": "run_layout_validation",
        "version": 1,
        "ok": not errors,
        "run_dir": str(run_dir),
        "layout_path": str(layout_path),
        "errors": errors,
        "warnings": warnings,
        "folders": folder_report,
        "present_artifacts": present_artifacts,
    }


def resolve_active_pointer(active, *, repo_dir=None):
    base = Path(repo_dir) if repo_dir else REPO_DIR
    root = Path(active["project_root"]).expanduser()
    if not root.is_absolute():
        root = base / root
    project_dir = root / active["active_project"]
    run_rel = active.get("active_run")
    run_dir = project_dir / Path(run_rel) if run_rel else None
    return project_dir, run_dir


def write_active_project(project_dir, *, repo_dir=None, active_run=None):
    project_dir = Path(project_dir).expanduser()
    payload = _project_pointer(project_dir, active_run=active_run, repo_dir=repo_dir)
    _write_json(_repo_project_dir(repo_dir) / "active.json", payload)
    return payload


def init_project(name, *, root=None, repo_dir=None):
    root = Path(root).expanduser() if root else default_project_root()
    slug = slugify(name)
    project_dir = root / slug
    for rel in ("input", "input/materials", "runs"):
        (project_dir / rel).mkdir(parents=True, exist_ok=True)
    active = write_active_project(project_dir, repo_dir=repo_dir, active_run=None)
    return {
        "status": "ok",
        "project_name": name,
        "project_slug": slug,
        "project_dir": str(project_dir),
        "input_dir": str(project_dir / "input"),
        "materials_dir": str(project_dir / "input" / "materials"),
        "runs_dir": str(project_dir / "runs"),
        "active": active,
    }


def create_run_dir(project_dir, *, label=None, repo_dir=None, timestamp=None):
    project_dir = Path(project_dir).expanduser()
    ts = timestamp or datetime.now().strftime("%Y%m%d-%H%M%S")
    suffix = f"-{slugify(label)}" if label else ""
    run_dir = project_dir / "runs" / f"{ts}{suffix}"
    for rel in RUN_LAYOUT:
        (run_dir / rel).mkdir(parents=True, exist_ok=True)
    _write_json(run_dir / "run_layout.json", build_run_layout(project_dir, run_dir))
    from video_pipeline_core.route_orchestrator import initial_state
    _write_json(run_dir / "route_orchestrator_state.json", initial_state())
    active = write_active_project(project_dir, repo_dir=repo_dir, active_run=run_dir)
    return {
        "status": "ok",
        "project_dir": str(project_dir),
        "run_dir": str(run_dir),
        "materials_dir": str(run_dir / "materials"),
        "selected_materials_dir": str(run_dir / "materials" / "selected"),
        "generated_dir": str(run_dir / "materials" / "generated"),
        "stock_materials_dir": str(run_dir / "materials" / "stock"),
        "spec_dir": str(run_dir / "spec"),
        "build_dir": str(run_dir / "build"),
        "verify_dir": str(run_dir / "verify"),
        "nodes_dir": str(run_dir / "nodes"),
        "thumbs_dir": str(run_dir / "thumbs"),
        "logs_dir": str(run_dir / "logs"),
        "brownfield_dir": str(run_dir / "brownfield"),
        "active": active,
    }


def _cmd_init(args):
    return init_project(args.name, root=args.root)


def _cmd_new_run(args):
    project_dir = args.project
    if not project_dir:
        active_path = _repo_project_dir() / "active.json"
        if not active_path.exists():
            raise SystemExit("No active project. Run project-init first or pass --project.")
        with active_path.open(encoding="utf-8") as f:
            project_dir, _run_dir = resolve_active_pointer(json.load(f))
    return create_run_dir(project_dir, label=args.label)


def cmd_project_init(args):
    result = _cmd_init(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_project_new_run(args):
    result = _cmd_new_run(args)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def main(argv=None):
    parser = argparse.ArgumentParser(description="video project workspace helper")
    sub = parser.add_subparsers(dest="cmd")
    p_init = sub.add_parser("init")
    p_init.add_argument("name")
    p_init.add_argument("--root")
    p_run = sub.add_parser("new-run")
    p_run.add_argument("--project")
    p_run.add_argument("--label")
    args = parser.parse_args(argv)
    if args.cmd == "init":
        result = _cmd_init(args)
    elif args.cmd == "new-run":
        result = _cmd_new_run(args)
    else:
        parser.print_help()
        raise SystemExit(2)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    main()
