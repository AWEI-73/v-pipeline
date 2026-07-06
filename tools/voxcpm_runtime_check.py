#!/usr/bin/env python
"""Check local VoxCPM runtime readiness without downloading models."""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from video_pipeline_core.branch_env import bootstrap_branch_env

DEFAULT_VOXCPM_REPO = REPO_ROOT / "reference repo" / "VoxCPM-main"
REQUIRED_IMPORTS = [
    "torch",
    "torchaudio",
    "transformers",
    "soundfile",
    "librosa",
    "huggingface_hub",
]


def _run(command: list[str]) -> dict:
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
        return {
            "returncode": result.returncode,
            "stdout": (result.stdout or "").strip(),
            "stderr": (result.stderr or "").strip(),
        }
    except Exception as exc:  # pragma: no cover - defensive diagnostic
        return {"returncode": -1, "stdout": "", "stderr": str(exc)}


def _module_available(python: str, module: str) -> dict:
    code = (
        "import importlib.util, json; "
        f"m={module!r}; "
        "spec=importlib.util.find_spec(m); "
        "print(json.dumps({'module':m,'available':spec is not None}))"
    )
    result = _run([python, "-c", code])
    try:
        payload = json.loads(result["stdout"])
    except json.JSONDecodeError:
        payload = {"module": module, "available": False}
    payload["returncode"] = result["returncode"]
    payload["stderr"] = result["stderr"][-500:]
    return payload


def build_runtime_report(
    *,
    voxcpm_repo: str | Path = DEFAULT_VOXCPM_REPO,
    python_executable: str | Path | None = None,
) -> dict:
    boot_env = bootstrap_branch_env()
    python = str(Path(python_executable or boot_env.get("VOXCPM_PYTHON") or sys.executable))
    repo = Path(voxcpm_repo)
    cli_path = repo / "src" / "voxcpm" / "cli.py"
    pyproject = repo / "pyproject.toml"
    gpu = _run(["nvidia-smi", "--query-gpu=name,memory.total,driver_version", "--format=csv,noheader"])
    imports = [_module_available(python, module) for module in REQUIRED_IMPORTS]
    missing = [item["module"] for item in imports if not item.get("available")]

    torch_probe = None
    if "torch" not in missing:
        torch_probe = _run(
            [
                python,
                "-c",
                "import json, torch; print(json.dumps({'version': torch.__version__, 'cuda_available': torch.cuda.is_available(), 'cuda': torch.version.cuda, 'device_count': torch.cuda.device_count()}))",
            ]
        )
        try:
            torch_probe["parsed"] = json.loads(torch_probe["stdout"])
        except json.JSONDecodeError:
            torch_probe["parsed"] = None

    ok_to_execute = cli_path.exists() and not missing
    next_action = "execute_voxcpm_probe" if ok_to_execute else "install_voxcpm_runtime_dependencies"
    if not cli_path.exists():
        next_action = "fix_voxcpm_repo_path"

    return {
        "artifact_role": "voxcpm_runtime_check",
        "version": 1,
        "ok_to_execute": ok_to_execute,
        "next_action": next_action,
        "python": python,
        "voxcpm_repo": str(repo),
        "repo_exists": repo.exists(),
        "cli_exists": cli_path.exists(),
        "pyproject_exists": pyproject.exists(),
        "required_imports": imports,
        "missing_modules": missing,
        "gpu": {
            "available": gpu["returncode"] == 0,
            "summary": gpu["stdout"],
            "stderr": gpu["stderr"][-500:],
        },
        "torch_probe": torch_probe,
        "recommended_install": {
            "isolated_runtime": True,
            "env": "set VOXCPM_PYTHON=<path-to-voxcpm-venv-python>",
            "commands": [
                "python -m venv .venv_voxcpm",
                ".venv_voxcpm\\Scripts\\python.exe -m pip install --upgrade pip",
                "$env:SETUPTOOLS_SCM_PRETEND_VERSION_FOR_VOXCPM='0.0.0+local'",
                ".venv_voxcpm\\Scripts\\python.exe -m pip install -e \"reference repo\\VoxCPM-main\"",
                ".venv_voxcpm\\Scripts\\python.exe -m pip install --force-reinstall torch==2.12.1+cu126 torchaudio==2.11.0+cu126 --index-url https://download.pytorch.org/whl/cu126",
            ],
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check VoxCPM local runtime readiness.")
    parser.add_argument("--voxcpm-repo", default=str(DEFAULT_VOXCPM_REPO))
    parser.add_argument("--voxcpm-python", default=None)
    parser.add_argument("--out", default=None)
    args = parser.parse_args(argv)
    report = build_runtime_report(
        voxcpm_repo=args.voxcpm_repo,
        python_executable=args.voxcpm_python,
    )
    text = json.dumps(report, ensure_ascii=False, indent=2)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0 if report["ok_to_execute"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
