#!/usr/bin/env python
"""Bounded test-tier runner for the video pipeline repo.

The goal is not to replace unittest or node. This module gives agents a stable
machine-readable set of focused test tiers so routine changes do not require
guessing which commands to run before full regression.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Callable, Dict, List, Optional

ARTIFACT_ROLE = "test_tier_manifest"
SCHEMA_VERSION = 1

TEST_TIERS: Dict[str, Dict[str, object]] = {
    "backend-smoke": {
        "description": "Fast backend contract/workspace command-surface smoke tests.",
        "commands": [
            ["python", "-m", "unittest", "tests.test_video_tools_command_catalog", "-q"],
            ["python", "-m", "unittest", "tests.test_project_workspace", "tests.test_workbench_handoff", "-q"],
        ],
    },
    "workbench": {
        "description": "Workbench Python, native JS, and SPA-shell boundary smoke tests.",
        "commands": [
            ["python", "-m", "unittest", "tests.test_preview_timeline", "tests.test_timeline_patch", "tests.test_workbench_server", "-q"],
            ["python", "-m", "unittest", "tests.test_workbench_frontend_smoke", "tests.test_workbench_review_report", "-q"],
            ["node", "tests/dashboard_spa_render_smoke.mjs"],
            ["node", "tests/dashboard_i18n_smoke.mjs"],
            ["node", "tests/workbench_api_smoke.js"],
            ["node", "tests/workbench_core_smoke.js"],
            ["node", "tests/workbench_materials_smoke.js"],
        ],
        "optional_checks": [
            {
                "name": "workbench-browser-layout",
                "description": (
                    "Real browser guard for the protected native monitor, playback controls, and four lanes. "
                    "Use --artifact-root for native-direct checks, or --url against "
                    "the merged /workbench route to also verify the SPA iframe shell."
                ),
                "command": ["node", "tools/workbench_browser_layout_smoke.mjs", "--artifact-root", "<run-folder>"],
                "merged_spa_command": ["node", "tools/workbench_browser_layout_smoke.mjs", "--url", "http://localhost:8765/workbench"],
            },
            {
                "name": "workbench-frontend-fixture",
                "description": (
                    "Self-contained fast HTML/API smoke fixture for protected monitor, playback controls, "
                    "four lanes, draft writes, and replace_clip. --init-fixture refuses non-empty folders "
                    "unless --force-init-fixture is used on a disposable scratch path."
                ),
                "command": ["python", "tools/workbench_frontend_smoke.py", "--artifact-root", ".tmp/workbench_frontend_smoke_fixture", "--init-fixture"],
                "replace_command": ["python", "tools/workbench_frontend_smoke.py", "--artifact-root", ".tmp/workbench_frontend_smoke_fixture", "--exercise-replace"],
            },
        ],
    },
    "material-map": {
        "description": "Material-map lifecycle, delta, lineage, and retrieval tests.",
        "commands": [
            ["python", "-m", "unittest", "tests.test_material_needs", "tests.test_material_lineage", "-q"],
            ["python", "-m", "unittest", "tests.test_material_delta", "tests.test_material_delta_gate", "-q"],
            ["python", "-m", "unittest", "tests.test_material_map_lifecycle", "tests.test_map_retrieval_wiring", "-q"],
        ],
    },
    "render-e2e": {
        "description": "Heavier render and replay acceptance tests.",
        "commands": [
            ["python", "-m", "unittest", "tests.test_workbench_export", "tests.test_workbench_draft_rerender", "-q"],
            ["python", "-m", "unittest", "tests.test_srp_acceptance_replay", "tests.test_srp_real67_fuller_replay", "-q"],
        ],
    },
    "full": {
        "description": "Complete regression suite.",
        "commands": [
            ["python", "-m", "unittest", "discover", "-s", "tests", "-q"],
        ],
    },
}


def build_test_tier_manifest() -> dict:
    return {
        "artifact_role": ARTIFACT_ROLE,
        "version": SCHEMA_VERSION,
        "tier_count": len(TEST_TIERS),
        "tiers": {
            name: {
                "description": spec["description"],
                "commands": spec["commands"],
                "optional_checks": spec.get("optional_checks", []),
            }
            for name, spec in sorted(TEST_TIERS.items())
        },
    }


def _default_runner(command: List[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    stable_temp = root / ".tmp" / "test-temp"
    stable_temp.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMP"] = str(stable_temp)
    env["TEMP"] = str(stable_temp)
    return subprocess.run(command, cwd=root, env=env).returncode


def run_test_tier(
    tier: str,
    *,
    dry_run: bool = False,
    runner: Optional[Callable[[List[str]], int]] = None,
) -> dict:
    manifest = build_test_tier_manifest()
    tiers = manifest["tiers"]
    if tier not in tiers:
        raise ValueError(f"unknown test tier: {tier}")
    commands = [list(cmd) for cmd in tiers[tier]["commands"]]
    optional_checks = list(tiers[tier].get("optional_checks") or [])
    result = {
        "artifact_role": "test_tier_run",
        "version": 1,
        "tier": tier,
        "dry_run": bool(dry_run),
        "ok": True,
        "command_count": len(commands),
        "commands": commands,
        "optional_checks": optional_checks,
        "results": [],
    }
    if dry_run:
        return result

    execute = runner or _default_runner
    for index, command in enumerate(commands):
        code = int(execute(command))
        result["results"].append({"index": index, "command": command, "exit_code": code})
        if code != 0:
            result["ok"] = False
            result["failed_command_index"] = index
            result["exit_code"] = code
            return result
    result["exit_code"] = 0
    return result


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="List or run bounded video pipeline test tiers")
    parser.add_argument("--tier", help="tier to run; omit to print manifest")
    parser.add_argument("--dry-run", action="store_true", help="print commands without executing")
    parser.add_argument("--out", help="write JSON report")
    args = parser.parse_args(argv)

    try:
        payload = run_test_tier(args.tier, dry_run=args.dry_run) if args.tier else build_test_tier_manifest()
    except ValueError as exc:
        print(f"[test_tiers] {exc}", file=sys.stderr)
        return 2

    text = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0 if payload.get("ok", True) else int(payload.get("exit_code", 1))


if __name__ == "__main__":
    raise SystemExit(main())
