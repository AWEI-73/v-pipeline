"""platform_tools.py — cross-platform executable and resource resolver.

Centralizes all platform-dependent discovery so runtime modules never
hardcode ``/home/...``, ``~/.local/bin/``, ``/tmp``, or Linux font paths.

Resolution order for executables:
    1. Explicit environment variable (e.g. FFMPEG_PATH)
    2. shutil.which() on PATH
    3. Platform-specific known location
    4. Clear ToolError with setup guidance
"""
import os
import platform
import shutil
import tempfile
from pathlib import Path


def _is_windows():
    return platform.system() == "Windows"


# ---------------------------------------------------------------------------
# Executable resolvers
# ---------------------------------------------------------------------------

def _resolve_executable(env_var, names, known_locations=None, guidance=""):
    """Generic resolver: env → PATH → known locations → ToolError."""
    from .vt_core import ToolError  # lazy to avoid circular import at module level

    # 1. explicit env
    env_val = os.environ.get(env_var)
    if env_val:
        p = Path(env_val)
        if p.is_file():
            return str(p)
        # env was set but path doesn't exist — still honour it so the caller
        # gets a clear error from subprocess rather than a silent fallback.
        return str(p)

    # 2. shutil.which on PATH
    for name in names:
        found = shutil.which(name)
        if found:
            return found

    # 3. platform-specific known locations
    for loc in (known_locations or []):
        if Path(loc).is_file():
            return str(loc)

    # 4. clear error
    raise ToolError(
        f"Cannot find {names[0]}. "
        f"Set {env_var} or add it to PATH.\n{guidance}"
    )


def resolve_python():
    """Return the Python interpreter command for the current platform."""
    if _is_windows():
        return "python"
    return "python3"


def resolve_ffmpeg():
    """Find ffmpeg executable."""
    known = []
    if _is_windows():
        conda_prefix = os.environ.get("CONDA_PREFIX", "")
        if conda_prefix:
            known.append(os.path.join(conda_prefix, "Library", "bin", "ffmpeg.exe"))
    else:
        known.append(os.path.expanduser("~/.local/bin/ffmpeg"))
        known.append("/usr/bin/ffmpeg")

    return _resolve_executable(
        "FFMPEG_PATH",
        ["ffmpeg"],
        known,
        "Install: conda install -c conda-forge ffmpeg  (or download from https://ffmpeg.org/download.html)",
    )


def resolve_ffprobe():
    """Find ffprobe executable."""
    known = []
    if _is_windows():
        conda_prefix = os.environ.get("CONDA_PREFIX", "")
        if conda_prefix:
            known.append(os.path.join(conda_prefix, "Library", "bin", "ffprobe.exe"))
    else:
        known.append(os.path.expanduser("~/.local/bin/ffprobe"))
        known.append("/usr/bin/ffprobe")

    return _resolve_executable(
        "FFPROBE_PATH",
        ["ffprobe"],
        known,
        "Install: conda install -c conda-forge ffmpeg  (ffprobe is included)",
    )


def resolve_ytdlp():
    """Find yt-dlp executable."""
    known = []
    if not _is_windows():
        known.append(os.path.expanduser("~/.local/bin/yt-dlp"))

    return _resolve_executable(
        "YTDLP_PATH",
        ["yt-dlp"],
        known,
        "Install: pip install yt-dlp",
    )


def resolve_ollama():
    """Find ollama executable."""
    known = []
    if _is_windows():
        local_appdata = os.environ.get("LOCALAPPDATA", "")
        if local_appdata:
            known.append(os.path.join(local_appdata, "Programs", "Ollama", "ollama.exe"))
    else:
        known.append("/usr/bin/ollama")
        known.append("/usr/local/bin/ollama")

    return _resolve_executable(
        "OLLAMA_PATH",
        ["ollama"],
        known,
        "Install: download from https://ollama.com",
    )


def resolve_ollama_url():
    """Return Ollama HTTP endpoint."""
    return os.environ.get("OLLAMA_URL", "http://localhost:11434")


def resolve_temp_dir():
    """Return a portable temporary directory path."""
    custom = os.environ.get("VIDEO_PIPELINE_TEMP")
    if custom:
        p = Path(custom)
        p.mkdir(parents=True, exist_ok=True)
        return str(p)
    return tempfile.gettempdir()


def resolve_font():
    """Find a CJK font file for ffmpeg drawtext / subtitle burning.

    Returns the absolute path to a usable font file.
    """
    from .vt_core import ToolError

    # 1. explicit env
    env_font = os.environ.get("VIDEO_PIPELINE_FONT")
    if env_font and Path(env_font).is_file():
        return env_font

    # 2. platform-specific search
    candidates = []
    if _is_windows():
        fonts_dir = Path(os.environ.get("WINDIR", r"C:\Windows")) / "Fonts"
        candidates = [
            fonts_dir / "msjh.ttc",     # 微軟正黑體
            fonts_dir / "msyh.ttc",     # 微軟雅黑
            fonts_dir / "msjhbd.ttc",   # 微軟正黑體 Bold
            fonts_dir / "arial.ttf",    # Arial fallback
        ]
    else:
        candidates = [
            Path(os.path.expanduser("~/.local/share/fonts/wqy-microhei.ttc")),
            Path("/usr/share/fonts/truetype/wqy/wqy-microhei.ttc"),
            Path(os.path.expanduser("~/.local/share/fonts/NotoSansSC-Regular.otf")),
            Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
            Path("/usr/share/fonts/truetype/arphic/uming.ttc"),
        ]

    for c in candidates:
        if c.is_file():
            return str(c)

    raise ToolError(
        "Cannot find a CJK font file. "
        "Set VIDEO_PIPELINE_FONT to the absolute path of a .ttf/.ttc file.\n"
        "Windows: typically C:\\Windows\\Fonts\\msjh.ttc\n"
        "Linux: install fonts-wqy-microhei or set the path manually."
    )
