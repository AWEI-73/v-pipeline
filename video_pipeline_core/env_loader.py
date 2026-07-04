from __future__ import annotations

import os
from pathlib import Path
from typing import Mapping


REPO_ROOT = Path(__file__).resolve().parents[1]


def load_env_file(path: str | Path | None = None, env: Mapping[str, str] | None = None) -> dict[str, str]:
    """Merge a dotenv file into an env mapping without overriding existing keys."""
    env_path = Path(path) if path is not None else REPO_ROOT / ".env"
    merged = dict(os.environ if env is None else env)
    if not env_path.exists():
        return merged
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, raw_value = line.split("=", 1)
        key = key.strip()
        if not key or key in merged:
            continue
        merged[key] = raw_value.strip().strip('"').strip("'")
    return merged


def apply_dotenv(path: str | Path | None = None) -> dict[str, str]:
    """Load repo dotenv values into os.environ for keys not already present."""
    merged = load_env_file(path)
    for key, value in merged.items():
        os.environ.setdefault(key, value)
    return dict(os.environ)


def getenv(key: str, default: str | None = None) -> str | None:
    apply_dotenv()
    return os.environ.get(key, default)
