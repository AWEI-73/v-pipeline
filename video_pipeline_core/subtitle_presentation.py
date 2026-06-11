"""Deterministic subtitle text and ASS presentation policy."""
from __future__ import annotations

import json
import re
import subprocess
import tempfile
from contextlib import contextmanager
from pathlib import Path


_CLEAN_PUNCTUATION = re.compile(r"[，。；！？、,.!?;:：]+")
_SRT_TIMING = re.compile(r"^\d{2}:\d{2}:\d{2},\d{3}\s+-->\s+\d{2}:\d{2}:\d{2},\d{3}")


def polish_caption_text(text: str, *, max_chars_per_line: int = 16, max_lines: int = 2) -> str:
    """Clean punctuation and wrap a caption into a bounded reading area."""
    cleaned = _CLEAN_PUNCTUATION.sub("\u3000", str(text).strip())
    cleaned = re.sub(r"[ \t\u3000]+", "\u3000", cleaned).strip(" \t\u3000")
    if not cleaned:
        return ""

    capacity = max_chars_per_line * max_lines
    if len(cleaned) > capacity:
        cleaned = cleaned[: capacity - 1].rstrip(" \t\u3000") + "…"

    return "\n".join(
        cleaned[i:i + max_chars_per_line]
        for i in range(0, len(cleaned), max_chars_per_line)
    )


def polish_srt_text(text: str, *, max_chars_per_line: int = 16, max_lines: int = 2) -> str:
    """Polish SRT caption payloads without changing indexes or timing lines."""
    output: list[str] = []
    for block in re.split(r"\r?\n\r?\n", text.strip()):
        lines = block.splitlines()
        timing_index = next((i for i, line in enumerate(lines) if _SRT_TIMING.match(line)), None)
        if timing_index is None or timing_index + 1 >= len(lines):
            output.append(block)
            continue
        caption = " ".join(lines[timing_index + 1:])
        output.append("\n".join(
            lines[:timing_index + 1]
            + [polish_caption_text(
                caption,
                max_chars_per_line=max_chars_per_line,
                max_lines=max_lines,
            )]
        ))
    return "\n\n".join(output) + ("\n" if text.endswith(("\n", "\r")) else "")


def build_ass_style(video_height: int = 1080) -> str:
    """Return the shared bottom-center ASS style scaled from a 1080p baseline."""
    scale = max(int(video_height), 1) / 1080
    font_size = max(16, round(38 * scale))
    margin_v = max(24, round(90 * scale))
    return (
        f"FontSize={font_size},Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=1,"
        f"Outline=2,Shadow=1.5,Spacing=0.5,Alignment=2,MarginV={margin_v}"
    )


def probe_video_height(video_path: str, ffprobe: str = "ffprobe") -> int:
    """Read the first video stream height, falling back to the 1080p baseline."""
    result = subprocess.run(
        [
            str(ffprobe), "-v", "error", "-select_streams", "v:0",
            "-show_entries", "stream=height", "-of", "json", str(video_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return 1080
    try:
        streams = json.loads(result.stdout).get("streams") or []
        return int(streams[0].get("height") or 1080)
    except (ValueError, TypeError, IndexError, json.JSONDecodeError):
        return 1080


@contextmanager
def polished_srt_file(source_path: str, *, max_chars_per_line: int = 16, max_lines: int = 2):
    """Yield a temporary polished SRT path and remove it afterwards."""
    source = Path(source_path)
    polished = polish_srt_text(
        source.read_text(encoding="utf-8-sig"),
        max_chars_per_line=max_chars_per_line,
        max_lines=max_lines,
    )
    tmp = tempfile.NamedTemporaryFile(
        mode="w",
        suffix=".srt",
        encoding="utf-8",
        delete=False,
    )
    try:
        with tmp:
            tmp.write(polished)
        yield tmp.name
    finally:
        Path(tmp.name).unlink(missing_ok=True)
