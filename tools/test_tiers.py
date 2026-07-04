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
    "dev": {
        "description": "Routine inner-loop checks for command-surface and route contract edits.",
        "intended_use": "routine inner-loop development before escalating to focused owner tests",
        "commands": [
            ["python", "-m", "unittest", "tests.test_video_tools_command_catalog", "tests.test_test_tiers", "-q"],
            ["python", "video_tools.py", "interface-audit"],
        ],
    },
    "backend-smoke": {
        "description": "Fast backend contract/workspace command-surface smoke tests.",
        "intended_use": "backend command-surface edits before broader route or branch tests",
        "commands": [
            ["python", "-m", "unittest", "tests.test_video_tools_command_catalog", "-q"],
            ["python", "-m", "unittest", "tests.test_project_workspace", "tests.test_workbench_handoff", "-q"],
        ],
    },
    "workbench": {
        "description": "Workbench Python, native JS, and SPA-shell boundary smoke tests.",
        "intended_use": "Workbench or Dashboard frontend/backend boundary edits",
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
        "intended_use": "Material Map branch edits before render or full acceptance",
        "commands": [
            ["python", "-m", "unittest", "tests.test_material_needs", "tests.test_material_lineage", "-q"],
            ["python", "-m", "unittest", "tests.test_material_delta", "tests.test_material_delta_gate", "-q"],
            ["python", "-m", "unittest", "tests.test_material_map_lifecycle", "tests.test_map_retrieval_wiring", "-q"],
        ],
    },
    "render-e2e": {
        "description": "Heavier render and replay acceptance tests.",
        "intended_use": "render, replay, or Workbench rerender changes before full regression",
        "commands": [
            ["python", "-m", "unittest", "tests.test_workbench_export", "tests.test_workbench_draft_rerender", "-q"],
            ["python", "-m", "unittest", "tests.test_srp_acceptance_replay", "tests.test_srp_real67_fuller_replay", "-q"],
        ],
    },
    "work-order-acceptance": {
        "description": "Standard supervisor handoff gate for work-order completion.",
        "intended_use": "before work-order handoff or reviewer transfer, after focused owner tests pass",
        "commands": [
            ["python", "video_tools.py", "e2e-smoke", "--case", "stock_story"],
            ["python", "video_tools.py", "e2e-smoke", "--case", "single_long_highlight"],
            ["python", "video_tools.py", "registry-audit"],
            ["python", "video_tools.py", "interface-audit"],
        ],
        "optional_checks": [
            {
                "name": "strict-asset-path-audit",
                "description": "Run on a fresh smoke-produced run dir when a work order touches artifact manifests or run outputs.",
                "command": ["python", "video_tools.py", "asset-path-audit", "--strict", "<run-folder>"],
            },
            {
                "name": "full-regression",
                "description": "Required before commit for broad/shared behavior changes and final supervisor reports.",
                "command": ["python", "-m", "unittest", "discover", "-s", "tests"],
            },
        ],
    },
    "full": {
        "description": "Complete regression suite.",
        "intended_use": "final pre-commit or CI gate, not the routine inner loop for every edit",
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
                "intended_use": spec["intended_use"],
                "commands": spec["commands"],
                "optional_checks": spec.get("optional_checks", []),
            }
            for name, spec in sorted(TEST_TIERS.items())
        },
    }


def _normalize_command(command: List[str]) -> List[str]:
    if command and Path(command[0]).name.lower() in {"python", "python.exe"}:
        return [sys.executable, *command[1:]]
    return list(command)


def _default_runner(command: List[str]) -> int:
    root = Path(__file__).resolve().parent.parent
    stable_temp = root / ".tmp" / "test-temp"
    stable_temp.mkdir(parents=True, exist_ok=True)
    env = os.environ.copy()
    env["TMP"] = str(stable_temp)
    env["TEMP"] = str(stable_temp)
    return subprocess.run(_normalize_command(command), cwd=root, env=env).returncode


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
