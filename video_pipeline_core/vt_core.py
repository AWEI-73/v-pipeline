"""vt_core.py — video tools 共用底層原語(無領域邏輯)。
拆出讓 video_tools.py / curator.py 共用而不循環匯入。"""
import os
import subprocess


# ---------------------------------------------------------------------------
# Executable paths: resolved lazily via platform_tools so missing tools only
# error when a runner actually invokes them, not at import time.
# ---------------------------------------------------------------------------
class _LazyTool:
    """Descriptor that resolves on first access and caches the result."""
    def __init__(self, resolver_name):
        self._resolver = resolver_name
        self._value = None

    def __set_name__(self, owner, name):
        self._attr = name

    def resolve(self):
        if self._value is None:
            from . import platform_tools
            self._value = getattr(platform_tools, self._resolver)()
        return self._value


class _ToolPaths:
    ffmpeg = _LazyTool("resolve_ffmpeg")
    ffprobe = _LazyTool("resolve_ffprobe")
    ytdlp = _LazyTool("resolve_ytdlp")


_tools = _ToolPaths()


def _get_ffmpeg():
    return _tools.ffmpeg.resolve()

def _get_ffprobe():
    return _tools.ffprobe.resolve()

def _get_ytdlp():
    return _tools.ytdlp.resolve()


# Module-level names kept for backward compatibility with all importers.
# They are now properties of a lazy proxy; direct string usage (e.g. in
# subprocess lists) goes through the functions above.  However, many
# existing call sites do ``from .vt_core import FFMPEG`` and use the name
def run(cmd, capture=True):
    return subprocess.run(cmd, capture_output=capture, text=True)


# ── 錯誤分類單一真相(對齊用)──────────────────────────────────────────────
# 全專案統一的「壞了該回哪一層修」分類。route/dashboard 依此分流。
# video_pipeline.RecoverableBuildError 也用同一組 key;收斂時讓它 import 這裡即可。
# directly.  To keep those working without changing every call site at once,
# we eagerly resolve here but tolerate missing tools (set to a sentinel that
# will produce a clear subprocess error if actually used).
FIX_CLASSES = ("material", "spec", "human")
FIX_TARGET = {"material": "curator", "spec": "director", "human": None}
GAP = "GAP"   # 選段缺口 sentinel(取代散落各處的魔術字串 "GAP")

# Node 8 缺口 fallback 路由(誠實性合約;與 fix_class 互補:fix_class=誰修,route=做什麼)
FALLBACK_ROUTES = ("none", "collect_material", "reshoot", "generated", "stock_bridge",
                   "text_bridge", "script_rewrite", "drop_segment", "dashboard_review")


class ToolError(RuntimeError):
    """video tools 統一錯誤。`fix_class`(material/spec/human)可選,讓 route/dashboard
    像 RecoverableBuildError 一樣分流;不帶則為一般 CLI 錯誤(向後相容)。"""
    def __init__(self, message, fix_class=None):
        super().__init__(message)
        self.fix_class = fix_class

    @property
    def fix_target(self):
        return FIX_TARGET.get(self.fix_class)


try:
    FFMPEG = _get_ffmpeg()
except Exception:
    FFMPEG = "ffmpeg"   # fallback — subprocess will give a clear OS error

try:
    FFPROBE = _get_ffprobe()
except Exception:
    FFPROBE = "ffprobe"

try:
    YTDLP = _get_ytdlp()
except Exception:
    YTDLP = "yt-dlp"


def _audio_duration(path):
    """用 ffprobe 取得媒體長度(秒)。共用底層原語。"""
    out = subprocess.check_output([
        FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', path
    ]).decode().strip()
    return float(out)
