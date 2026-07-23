#!/usr/bin/env python
"""Create or validate the V Pipeline -> Workbench landing contract."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from video_pipeline_core.workbench_project import (
    OPTIONAL_ARTIFACTS,
    build_workbench_project,
    validate_workbench_project,
    write_workbench_project,
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    create = sub.add_parser("create", help="Create an immutable Workbench project landing")
    create.add_argument("--project-root", required=True)
    create.add_argument("--project-id", required=True)
    create.add_argument("--display-name", required=True)
    create.add_argument("--timeline", required=True)
    create.add_argument("--material-map", required=True)
    create.add_argument("--candidate-video", required=True)
    for key in sorted(OPTIONAL_ARTIFACTS):
        create.add_argument("--" + key.replace("_", "-"))
    create.add_argument("--overwrite", action="store_true")

    validate = sub.add_parser("validate", help="Validate exact paths and hashes")
    validate.add_argument("--project-root", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "create":
        refs = {
            "timeline": args.timeline,
            "material_map": args.material_map,
            "candidate_video": args.candidate_video,
        }
        for key in sorted(OPTIONAL_ARTIFACTS):
            value = getattr(args, key)
            if value:
                refs[key] = value
        manifest = build_workbench_project(
            project_root=args.project_root,
            project_id=args.project_id,
            display_name=args.display_name,
            artifact_paths=refs,
        )
        path = write_workbench_project(args.project_root, manifest, overwrite=args.overwrite)
        result = validate_workbench_project(args.project_root)
        result["written"] = str(Path(path).resolve())
    else:
        result = validate_workbench_project(args.project_root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
