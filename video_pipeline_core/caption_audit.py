"""caption_audit.py — Node 11/12 caption timing audit (P1-A).

Audits on-screen caption timing for overlap, oversized gaps, and excessive
reading speed. Crucially it distinguishes:

* subtitles / narrative  -> audited as captions
* labels / name supers   -> screen decoration, NOT subtitles, never audited here
* intended no-caption intervals -> excluded from gap findings

Pure and deterministic; consumes already-parsed caption events. Output follows
the ``caption_audit.json`` contract.

Source: technique inspired by https://github.com/Hao0321/video-autopilot-kit
(MIT); reimplemented for this project's artifact contracts.
"""
import json
import re
from pathlib import Path

# Caption kinds that represent actual reading-track subtitles.
_DEFAULT_SUBTITLE_KINDS = ("subtitle", "narrative")

_SRT_TIME = re.compile(
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})\s*-->\s*"
    r"(\d{1,2}):(\d{2}):(\d{2})[,.](\d{1,3})"
)


def _srt_seconds(h, m, s, ms):
    return int(h) * 3600 + int(m) * 60 + int(s) + int(ms) / 1000.0


def parse_srt(text, *, kind="subtitle"):
    """Parse an SRT subtitle file into caption events.

    Returns ``[{start_sec, end_sec, text, kind}]``. SRT carries only reading-track
    subtitles, so every cue is tagged as ``subtitle`` (labels/name supers live in
    the script/timeline, never in the SRT, so they cannot be mistaken here).
    """
    events = []
    for block in re.split(r"\n\s*\n", (text or "").strip()):
        lines = [ln for ln in block.splitlines() if ln.strip() != ""]
        tc_idx = next((i for i, ln in enumerate(lines) if "-->" in ln), None)
        if tc_idx is None:
            continue
        match = _SRT_TIME.search(lines[tc_idx])
        if not match:
            continue
        g = match.groups()
        start = _srt_seconds(*g[0:4])
        end = _srt_seconds(*g[4:8])
        text_body = " ".join(lines[tc_idx + 1:]).strip()
        events.append({"start_sec": start, "end_sec": end,
                       "text": text_body, "kind": kind})
    return events


def _finding(check, level, message, *, fix_class="spec", affected=None,
             next_route="subtitle_or_editor_correction"):
    return {
        "check": check,
        "level": level,
        "message": message,
        "affected": affected or [],
        "fix_class": fix_class,
        "next_route": next_route,
    }


def _subtitle_events(captions, subtitle_kinds):
    events = []
    for c in captions or []:
        kind = c.get("kind", "subtitle")
        if kind not in subtitle_kinds:
            continue
        start = c.get("start_sec")
        end = c.get("end_sec")
        if start is None or end is None:
            continue
        events.append({
            "start_sec": float(start),
            "end_sec": float(end),
            "text": c.get("text") or "",
        })
    events.sort(key=lambda e: e["start_sec"])
    return events


def _in_intended_silence(gap_start, gap_end, intervals):
    for lo, hi in intervals or []:
        if float(lo) <= gap_start and gap_end <= float(hi):
            return True
    return False


def audit_captions(captions, *, subtitle_kinds=None, max_gap_sec=None,
                   max_chars_per_sec=None, intended_silence_intervals=None,
                   overlap_tolerance_sec=0.05):
    """Audit caption timing and return the artifact payload."""
    subtitle_kinds = tuple(subtitle_kinds) if subtitle_kinds is not None else _DEFAULT_SUBTITLE_KINDS
    events = _subtitle_events(captions, subtitle_kinds)

    findings = []
    overlap_count = 0
    gap_count = 0
    too_fast_count = 0

    # Overlap (always checked: two subtitles on screen at once is a real defect).
    for prev, cur in zip(events, events[1:]):
        if cur["start_sec"] + overlap_tolerance_sec < prev["end_sec"]:
            overlap_count += 1
            findings.append(_finding(
                "overlap", "fail",
                f"subtitle at {cur['start_sec']:.2f}s overlaps previous ending at "
                f"{prev['end_sec']:.2f}s",
                affected=[cur["start_sec"]],
            ))

    # Gaps (only when a threshold is supplied; intended silence is excluded).
    if max_gap_sec is not None:
        for prev, cur in zip(events, events[1:]):
            gap = cur["start_sec"] - prev["end_sec"]
            if gap > float(max_gap_sec) and not _in_intended_silence(
                    prev["end_sec"], cur["start_sec"], intended_silence_intervals):
                gap_count += 1
                findings.append(_finding(
                    "gap", "warn",
                    f"uncaptioned gap of {gap:.2f}s between {prev['end_sec']:.2f}s "
                    f"and {cur['start_sec']:.2f}s",
                    affected=[prev["end_sec"]],
                ))

    # Reading speed (only when a ceiling is supplied).
    if max_chars_per_sec is not None:
        for e in events:
            dur = e["end_sec"] - e["start_sec"]
            n = len(e["text"].strip())
            if dur <= 0:
                if n > 0:
                    too_fast_count += 1
                    findings.append(_finding(
                        "too_fast", "warn",
                        f"caption at {e['start_sec']:.2f}s has non-positive duration",
                        affected=[e["start_sec"]],
                    ))
                continue
            cps = n / dur
            if cps > float(max_chars_per_sec):
                too_fast_count += 1
                findings.append(_finding(
                    "too_fast", "warn",
                    f"caption at {e['start_sec']:.2f}s reads at {cps:.1f} chars/s "
                    f"(ceiling {float(max_chars_per_sec):.1f})",
                    affected=[e["start_sec"]],
                ))

    has_fail = any(f["level"] == "fail" for f in findings)
    next_action = "subtitle_or_editor_correction" if has_fail else None
    return {
        "artifact_role": "caption_audit",
        "version": 1,
        "pass": not has_fail,
        "metrics": {
            "gap_count": gap_count,
            "overlap_count": overlap_count,
            "too_fast_count": too_fast_count,
        },
        "findings": findings,
        "next_action": next_action,
    }


def write_caption_audit(captions, out_path, **kwargs):
    """Audit ``captions`` and write the stable ``caption_audit.json``."""
    result = audit_captions(captions, **kwargs)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    return {"ok": True, "caption_audit": str(out_path), "result": result}
