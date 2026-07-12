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
_SUBTITLE_TEXT_POLICIES = frozenset({"polish", "exact"})


def polish_caption_text(text: str, *, max_chars_per_line: int = 16, max_lines: int = 2) -> str:
    """Clean punctuation and wrap a caption into a bounded reading area."""
    cleaned = _CLEAN_PUNCTUATION.sub("\u3000", str(text).strip())
    cleaned = re.sub(r"[ \t\u3000]+", "\u3000", cleaned).strip(" \t\u3000")
    if not cleaned:
        return ""

    capacity = max_chars_per_line * max_lines
    if len(cleaned) > capacity:
        cleaned = cleaned[: capacity - 1].rstrip(" \t\u3000") + "…"

    # Wrap preferring clause boundaries (the full-width spaces left by punctuation
    # cleaning) so lines never break mid-word (the mid-phrase hard-cut class).
    lines: list[str] = []
    rest = cleaned
    while rest:
        if len(rest) <= max_chars_per_line:
            lines.append(rest)
            break
        window = rest[: max_chars_per_line + 1]
        cut = window.rfind("\u3000")
        if cut < max(2, max_chars_per_line // 3):
            cut = max_chars_per_line          # no usable clause boundary: hard cut
        lines.append(rest[:cut].rstrip("\u3000"))
        rest = rest[cut:].lstrip("\u3000")
    return "\n".join(lines)


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


@contextmanager
def subtitle_srt_file(
    source_path: str,
    *,
    subtitle_text_policy: str = "polish",
    max_chars_per_line: int = 16,
    max_lines: int = 2,
):
    """Yield the SRT path selected by the shared subtitle text policy.

    ``exact`` yields the source path directly so the renderer receives the
    original bytes. ``polish`` retains the established temporary-file flow.
    """
    if subtitle_text_policy not in _SUBTITLE_TEXT_POLICIES:
        raise ValueError(
            f"unknown subtitle text policy: {subtitle_text_policy!r}; "
            "expected 'polish' or 'exact'"
        )

    if subtitle_text_policy == "exact":
        yield str(Path(source_path))
        return

    with polished_srt_file(
        source_path,
        max_chars_per_line=max_chars_per_line,
        max_lines=max_lines,
    ) as rendered:
        yield rendered


def build_ass_style(video_height: int = 1080) -> str:
    """Return the shared bottom-center ASS style.

    libass renders SRT through a default PlayResY=288 coordinate space, NOT
    video pixels - force_style values are resolution-independent. Scaling by
    video height double-applies the scale (FontSize=38 became ~142px
    mid-screen text on the city-lite smoke). FontSize=20/288 is ~7% of frame
    height (~75px at 1080p); MarginV=22/288 sits the block in the lower safe
    area. video_height is kept for call-site compatibility and ignored."""
    return (
        "FontSize=20,Bold=1,PrimaryColour=&H00FFFFFF,"
        "OutlineColour=&H00000000,BackColour=&H80000000,BorderStyle=1,"
        "Outline=1.2,Shadow=0.8,Spacing=0.5,Alignment=2,MarginV=22"
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
