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
