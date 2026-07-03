from __future__ import annotations

import argparse
import importlib.util
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Callable, Iterable, Mapping, Sequence


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_JSON_OUT = REPO_ROOT / ".tmp" / "preflight.json"
DEFAULT_SUMMARY_OUT = REPO_ROOT / ".tmp" / "preflight.txt"

MIN_PYTHON = (3, 10)
REQUIRED_MODULES = {
    "PIL": "Pillow",
    "cv2": "opencv-python",
    "dotenv": "python-dotenv",
    "edge_tts": "edge-tts",
    "faster_whisper": "faster-whisper",
    "librosa": "librosa",
    "numpy": "numpy",
    "playwright": "playwright",
    "scenedetect": "scenedetect",
}
OPTIONAL_MODULES = {
    "pillow_heif": "HEIF/HEIC image support",
}
REQUIRED_TOOLS = ("ffmpeg", "node", "yt-dlp")
REQUIRED_ENV_KEYS = ("PEXELS_API_KEY",)
OPTIONAL_ENV_KEYS = (
    "PIXABAY_API_KEY",
    "JAMENDO_CLIENT_ID",
    "JAMENDO_CLIENT_SECRET",
    "OLLAMA_URL",
    "FFMPEG",
    "FFPROBE",
    "YTDLP_PATH",
    "M6E_FOOTAGE",
    "MV_ASR_MODEL",
    "VIDEO_PIPELINE_PROJECT_ROOT",
    "VIDEO_PIPELINE_TEMP",
    "VIDEO_PIPELINE_FONT",
    "VOXCPM_BIN",
    "VOXCPM_REPO",
    "VOXCPM_PYTHON",
    "VOXCPM_MODEL_ID",
)


WhichFn = Callable[[str], str | None]
FindSpecFn = Callable[[str], object | None]
RunCommandFn = Callable[[Sequence[str]], str]


def load_env_file(path: Path, env: Mapping[str, str] | None = None) -> dict[str, str]:
    merged = dict(os.environ if env is None else env)
    if not path.exists():
        return merged
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key in merged:
            continue
        value = raw_value.strip().strip('"').strip("'")
        merged[key] = value
    return merged


def _default_run_command(args: Sequence[str]) -> str:
    completed = subprocess.run(
        list(args),
        check=False,
        capture_output=True,
        text=True,
        timeout=10,
    )
    text = (completed.stdout or completed.stderr or "").strip()
    if completed.returncode != 0:
        raise RuntimeError(text or f"{args[0]} exited {completed.returncode}")
    return text


def _version_tuple_to_text(version: Sequence[int]) -> str:
    return ".".join(str(part) for part in version[:3])


def _first_line(text: str) -> str:
    return text.splitlines()[0].strip() if text else ""


def _check_python(version: Sequence[int]) -> dict[str, object]:
    ok = tuple(version[:2]) >= MIN_PYTHON
    return {
        "status": "ok" if ok else "missing",
        "version": _version_tuple_to_text(version),
        "required": f">={MIN_PYTHON[0]}.{MIN_PYTHON[1]}",
    }


def _check_modules(find_spec: FindSpecFn) -> tuple[dict[str, dict[str, str]], list[str]]:
    modules: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    for module, package in REQUIRED_MODULES.items():
        found = find_spec(module) is not None
        modules[module] = {
            "package": package,
            "status": "ok" if found else "missing",
        }
        if not found:
            missing.append(module)
    for module, note in OPTIONAL_MODULES.items():
        found = find_spec(module) is not None
        modules[module] = {
            "package": note,
            "status": "ok" if found else "optional-missing",
        }
    return modules, missing


def _check_tools(which: WhichFn, run_command: RunCommandFn) -> tuple[dict[str, dict[str, str]], list[str]]:
    tools: dict[str, dict[str, str]] = {}
    missing: list[str] = []
    version_args = {
        "ffmpeg": ["ffmpeg", "-version"],
        "node": ["node", "--version"],
        "yt-dlp": ["yt-dlp", "--version"],
    }
    for name in REQUIRED_TOOLS:
        path = which(name)
        if not path:
            tools[name] = {"status": "missing", "path": "", "version": ""}
            missing.append(name)
            continue
        try:
            version = _first_line(run_command(version_args[name]))
        except Exception as exc:  # pragma: no cover - exercised through mocks
            tools[name] = {"status": "error", "path": path, "version": str(exc)}
            missing.append(name)
            continue
        tools[name] = {"status": "ok", "path": path, "version": version}
    return tools, missing


def _check_env(env: Mapping[str, str]) -> dict[str, object]:
    present = sorted(k for k in REQUIRED_ENV_KEYS + OPTIONAL_ENV_KEYS if env.get(k))
    missing_required = sorted(k for k in REQUIRED_ENV_KEYS if not env.get(k))
    missing_optional = sorted(k for k in OPTIONAL_ENV_KEYS if not env.get(k))
    return {
        "present_keys": present,
        "missing_keys": missing_required,
        "missing_optional_keys": missing_optional,
    }


def check_environment(
    *,
    env: Mapping[str, str] | None = None,
    python_version: Sequence[int] | None = None,
    which: WhichFn = shutil.which,
    find_spec: FindSpecFn = importlib.util.find_spec,
    run_command: RunCommandFn = _default_run_command,
) -> dict[str, object]:
    env_map = load_env_file(REPO_ROOT / ".env") if env is None else dict(env)
    version = tuple(sys.version_info[:3] if python_version is None else python_version)

    python = _check_python(version)
    modules, missing_modules = _check_modules(find_spec)
    tools, missing_tools = _check_tools(which, run_command)
    environment = _check_env(env_map)

    hard_failures: list[str] = []
    if python["status"] != "ok":
        hard_failures.append("python")
    hard_failures.extend(f"module:{name}" for name in missing_modules)
    hard_failures.extend(f"tool:{name}" for name in missing_tools)
    warnings = [f"env:{name}" for name in environment["missing_keys"]]

    return {
        "status": "error" if hard_failures else ("warning" if warnings else "ok"),
        "strict_pass": not hard_failures and not warnings,
        "hard_failures": hard_failures,
        "warnings": warnings,
        "python": python,
        "modules": modules,
        "tools": tools,
        "environment": environment,
    }


def render_summary(result: Mapping[str, object]) -> str:
    lines = ["Capability summary", f"status: {result['status']}"]
    python = result["python"]
    assert isinstance(python, Mapping)
    lines.append(f"python: {python['status']} ({python['version']}, required {python['required']})")
    tools = result["tools"]
    assert isinstance(tools, Mapping)
    for name in REQUIRED_TOOLS:
        item = tools[name]
        assert isinstance(item, Mapping)
        version = f" - {item['version']}" if item.get("version") else ""
        lines.append(f"{name}: {item['status']}{version}")
    modules = result["modules"]
    assert isinstance(modules, Mapping)
    missing_modules = [
        name
        for name, item in modules.items()
        if isinstance(item, Mapping) and item.get("status") == "missing"
    ]
    lines.append("python modules: ok" if not missing_modules else f"python modules missing: {', '.join(missing_modules)}")
    environment = result["environment"]
    assert isinstance(environment, Mapping)
    missing_keys = environment.get("missing_keys") or []
    if missing_keys:
        lines.append(f"missing required env keys: {', '.join(missing_keys)}")
    else:
        lines.append("required env keys: present")
    optional_missing = environment.get("missing_optional_keys") or []
    if optional_missing:
        lines.append(f"missing optional env keys: {', '.join(optional_missing)}")
    return "\n".join(lines) + "\n"


def _write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _parse_args(argv: Iterable[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Check local video pipeline bootstrap capabilities.")
    parser.add_argument("--strict", action="store_true", help="Exit 1 on missing hard requirements or required env keys.")
    parser.add_argument("--json-out", type=Path, default=DEFAULT_JSON_OUT, help="Path for machine-readable JSON summary.")
    parser.add_argument("--summary-out", type=Path, default=DEFAULT_SUMMARY_OUT, help="Path for human-readable summary.")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(
    argv: Iterable[str] | None = None,
    *,
    env: Mapping[str, str] | None = None,
    python_version: Sequence[int] | None = None,
    which: WhichFn = shutil.which,
    find_spec: FindSpecFn = importlib.util.find_spec,
    run_command: RunCommandFn = _default_run_command,
) -> int:
    args = _parse_args(argv)
    result = check_environment(
        env=env,
        python_version=python_version,
        which=which,
        find_spec=find_spec,
        run_command=run_command,
    )
    json_text = json.dumps(result, indent=2, sort_keys=True)
    summary = render_summary(result)
    _write_text(args.json_out, json_text + "\n")
    _write_text(args.summary_out, summary)
    print(summary, end="")
    return 1 if args.strict and not result["strict_pass"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
