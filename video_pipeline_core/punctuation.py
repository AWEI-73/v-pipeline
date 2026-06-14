"""BR3 — Music / Sound Punctuation.

Consume the valid cue anchors emitted by BR1 (opening) and BR2 (beat sequences)
and mix actual SFX hits into the rendered audio. A cue is resolved to a real
timeline timestamp by locating the clip whose produced role matches the cue's
anchor; cues whose anchor is absent from the plan are dropped (never invented).
The mix reuses the loudness-preserving sfx filter, so the audio output really
changes.
"""
from __future__ import annotations

import json
import os
import subprocess
import tempfile
from pathlib import Path

from .sfx import ASSET_COUNTS, SFX_VOLUME, build_sfx_filter


def _clip_role(clip):
    return clip.get("opening_role") or clip.get("beat_role")


def _asset_for(cue_type, asset_dir, ordinal):
    kind = cue_type if cue_type in ASSET_COUNTS else "hit"
    variant = 1 + (ordinal % ASSET_COUNTS[kind])
    return os.path.join(str(asset_dir), f"{kind}_{variant}.wav")


def resolve_punctuation_cues(plan, cues, *, asset_dir):
    """Map each cue anchor (a produced sequence role) to a timeline start + asset.
    A cue whose anchor is not present in the plan is dropped (BR1/BR2 contract:
    never point at a non-existent or dropped beat)."""
    starts, cursor = [], 0.0
    for clip in plan or []:
        starts.append(cursor)
        cursor += float(clip.get("extract_dur") or clip.get("duration_sec") or 0.0)

    resolved, dropped, counters = [], [], {}
    for cue in cues or []:
        anchor = cue.get("anchor")
        seg = cue.get("segment")
        idx = None
        for i, clip in enumerate(plan or []):
            if _clip_role(clip) == anchor and (seg is None or clip.get("segment") == seg):
                idx = i
                break
        if idx is None:
            dropped.append({**cue, "reason": f"anchor_missing:{anchor}"})
            continue
        cue_type = cue.get("type", "hit")
        counters[cue_type] = counters.get(cue_type, 0) + 1
        resolved.append({
            "type": cue_type,
            "anchor": anchor,
            "segment": seg,
            "start_sec": round(starts[idx], 3),
            "asset": _asset_for(cue_type, asset_dir, counters[cue_type] - 1),
            "volume": SFX_VOLUME,
        })
    return {"artifact_role": "punctuation_plan", "version": 1,
            "cues": resolved, "dropped": dropped}


def write_punctuation_plan(plan, cues, out_path, *, asset_dir):
    result = resolve_punctuation_cues(plan, cues, asset_dir=asset_dir)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def mix_punctuation_audio(base_audio, punctuation_plan, out_path, *, ffmpeg=None):
    """Mix resolved punctuation hits onto a base AUDIO file via the sfx filter.
    Returns the path; copies base if there is nothing to mix."""
    from .vt_audio import cmd_mix_sfx  # noqa: PLC0415 (reuse the tested mix path)
    import types
    cues = [c for c in (punctuation_plan.get("cues") or [])
            if os.path.exists(c.get("asset", ""))]
    plan_for_sfx = {"cues": cues}
    with tempfile.TemporaryDirectory() as tmp:
        plan_path = os.path.join(tmp, "sfx_plan.json")
        with open(plan_path, "w", encoding="utf-8") as handle:
            json.dump(plan_for_sfx, handle)
        cmd_mix_sfx(types.SimpleNamespace(base=str(base_audio), plan=plan_path,
                                          out=str(out_path)))
    return str(out_path)


def apply_punctuation_to_video(video_path, plan, cues, *, asset_dir, ffmpeg=None):
    """Remux resolved punctuation hits into a rendered video's audio (real output
    change). No usable cues -> the video is left untouched. Returns the resolved
    punctuation plan for tracing."""
    if ffmpeg is None:
        try:
            from .platform_tools import resolve_ffmpeg
            ffmpeg = resolve_ffmpeg()
        except Exception:
            ffmpeg = "ffmpeg"
    resolved = resolve_punctuation_cues(plan, cues, asset_dir=asset_dir)
    usable = [c for c in resolved["cues"] if os.path.exists(c.get("asset", ""))]
    if not usable:
        return resolved
    graph, label = build_sfx_filter(
        [{"start_sec": c["start_sec"], "volume": c["volume"]} for c in usable],
        base_channels=2)
    out_tmp = str(video_path) + ".punct.mp4"
    cmd = [ffmpeg, "-y", "-i", str(video_path)]
    for cue in usable:
        cmd += ["-i", cue["asset"]]
    cmd += ["-filter_complex", graph, "-map", "0:v", "-map", f"[{label}]",
            "-c:v", "copy", "-c:a", "aac", out_tmp]
    result = subprocess.run(cmd, capture_output=True)
    if result.returncode == 0 and os.path.exists(out_tmp):
        os.replace(out_tmp, str(video_path))
    return resolved
