#!/usr/bin/env python3
"""runtime.py — Unified Runtime Orchestrator for video pipeline.

Controls continuous execution, checkpointing, and automatic recovery of video projects.
"""
import sys
import argparse
from pathlib import Path

# Add the repo root to sys.path
REPO_ROOT = Path(__file__).resolve().parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

if sys.platform == "win32":
    import io
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation):
        pass

from video_pipeline_core.runtime_orchestrator import run_orchestrator, print_status, rerun_node

def main():
    ap = argparse.ArgumentParser(description="runtime.py — Unified Runtime Orchestrator for video pipeline")
    sub = ap.add_subparsers(dest="command", required=True)

    p_run = sub.add_parser("run", help="Run the pipeline for a project or run folder")
    p_run.add_argument("--project", help="Project name/slug")
    p_run.add_argument("--contract", help="Optional canonical segment contract JSON path")
    p_run.add_argument("--brief", help="Optional brief JSON path")
    p_run.add_argument("--music", help="Optional background music path")
    p_run.add_argument("--material-db", help="Optional materials database JSON path")
    p_run.add_argument("--verbose", action="store_true")

    p_status = sub.add_parser("status", help="Get project node status details")
    p_status.add_argument("--project", help="Project name/slug")

    p_resume = sub.add_parser("resume", help="Resume continuous loop execution")
    p_resume.add_argument("--project", help="Project name/slug")
    p_resume.add_argument("--contract", help="Optional canonical segment contract JSON path")
    p_resume.add_argument("--brief", help="Optional brief JSON path")
    p_resume.add_argument("--music", help="Optional background music path")
    p_resume.add_argument("--material-db", help="Optional materials database JSON path")
    p_resume.add_argument("--verbose", action="store_true")

    p_rerun = sub.add_parser("rerun", help="Rerun pipeline from a specified node ID")
    p_rerun.add_argument("--node", required=True, help="Node label/ID to rerun (e.g. 10 or 12)")
    p_rerun.add_argument("--project", help="Project name/slug")
    p_rerun.add_argument("--contract", help="Optional canonical segment contract JSON path")
    p_rerun.add_argument("--brief", help="Optional brief JSON path")
    p_rerun.add_argument("--music", help="Optional background music path")
    p_rerun.add_argument("--material-db", help="Optional materials database JSON path")
    p_rerun.add_argument("--verbose", action="store_true")

    args = ap.parse_args()

    if args.command in ("run", "resume"):
        run_orchestrator(args.project, args)
    elif args.command == "status":
        print_status(args.project)
    elif args.command == "rerun":
        rerun_node(args.node, args.project, args)


if __name__ == "__main__":
    main()
