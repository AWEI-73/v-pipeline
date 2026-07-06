"""Safe branch environment bootstrap for provider/runtime tools."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]
KNOWN_BRANCH_ENV_KEYS = {
    "JAMENDO_CLIENT_ID",
    "PIXABAY_API_KEY",
    "YTDLP_PATH",
    "HERMES_DEFAULT_MUSIC_PROVIDER",
    "HERMES_DEFAULT_BGM_PROVIDER",
    "VOXCPM_PYTHON",
}
SECRET_KEYS = {"JAMENDO_CLIENT_ID", "PIXABAY_API_KEY"}


def _parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw_line in path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if key not in KNOWN_BRANCH_ENV_KEYS:
            continue
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
            value = value[1:-1]
        values[key] = value
    return values


def bootstrap_branch_env(
    *,
    repo_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    apply_to_process: bool = False,
) -> dict[str, str]:
    """Return env with known branch values loaded without overwriting existing keys."""

    root = Path(repo_root or REPO_ROOT)
    merged = dict(os.environ if env is None else env)
    for key, value in _parse_dotenv(root / ".env").items():
        if key not in merged or merged.get(key) in {None, ""}:
            merged[key] = value

    if not merged.get("VOXCPM_PYTHON"):
        default_python = root / ".venv_voxcpm" / "Scripts" / "python.exe"
        if default_python.is_file():
            merged["VOXCPM_PYTHON"] = str(default_python)

    if not merged.get("YTDLP_PATH"):
        found = shutil.which("yt-dlp", path=merged.get("PATH")) or shutil.which("yt-dlp.exe", path=merged.get("PATH"))
        if found:
            merged["YTDLP_PATH"] = found

    if apply_to_process:
        for key in KNOWN_BRANCH_ENV_KEYS:
            value = merged.get(key)
            if value and not os.environ.get(key):
                os.environ[key] = value
    return merged


def _tool_version(path: str | None) -> str | None:
    if not path:
        return None
    use_shell = Path(path).suffix.lower() in {".cmd", ".bat"}
    command: list[str] | str = f'"{path}" --version' if use_shell else [path, "--version"]
    try:
        result = subprocess.run(
            command,
            text=True,
            capture_output=True,
            timeout=10,
            encoding="utf-8",
            errors="replace",
            shell=use_shell,
        )
    except OSError:
        return None
    if result.returncode != 0:
        return None
    return (result.stdout or result.stderr or "").strip().splitlines()[0] if (result.stdout or result.stderr) else None


def build_branch_env_probe(
    *,
    repo_root: str | Path | None = None,
    env: Mapping[str, str] | None = None,
    voxcpm_runtime: Mapping[str, object] | None = None,
) -> dict[str, object]:
    root = Path(repo_root or REPO_ROOT)
    merged = bootstrap_branch_env(repo_root=root, env=env)
    jamendo = merged.get("JAMENDO_CLIENT_ID") or ""
    pixabay = merged.get("PIXABAY_API_KEY") or ""
    ytdlp_path = merged.get("YTDLP_PATH")
    probe = {
        "artifact_role": "branch_env_probe",
        "version": 1,
        "repo_root": str(root),
        "voxcpm_python": merged.get("VOXCPM_PYTHON"),
        "voxcpm_runtime_ok": bool((voxcpm_runtime or {}).get("ok_to_execute")),
        "jamendo_client_id_present": bool(jamendo),
        "jamendo_client_id_length": len(jamendo),
        "pixabay_api_key_present": bool(pixabay),
        "pixabay_api_key_length": len(pixabay),
        "yt_dlp_path": ytdlp_path,
        "yt_dlp_version": _tool_version(ytdlp_path),
        "secrets_redacted": True,
        "loaded_keys": sorted(key for key in KNOWN_BRANCH_ENV_KEYS if merged.get(key)),
    }
    # Defensive check: keep accidental future additions from leaking known secrets.
    serialized = json.dumps(probe, ensure_ascii=False)
    if any(secret and secret in serialized for secret in (jamendo, pixabay)):
        probe["secrets_redacted"] = False
    return probe
