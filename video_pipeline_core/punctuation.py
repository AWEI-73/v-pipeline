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
    return clip.get("opening_role") or clip.get("beat_role") or clip.get("ending_role")


def _asset_for(cue_type, asset_dir, ordinal):
    kind = cue_type if cue_type in ASSET_COUNTS else "hit"
    variant = 1 + (ordinal % ASSET_COUNTS[kind])
    return os.path.join(str(asset_dir), f"{kind}_{variant}.wav")


def _timeline_starts(plan):
    """Mirror mv_cut._build_transition_filter's contiguous-segment grouping.

    Clips inside one segment group concatenate without overlap. An incoming
    group may overlap the accumulated timeline by no more than the declared
    transition, the current timeline duration, or the incoming group duration.
    """
    plan = list(plan or [])
    starts = [0.0] * len(plan)
    groups = []
    for index, clip in enumerate(plan):
        duration = float(clip.get("extract_dur") or clip.get("duration_sec") or 0.0)
        if not groups or groups[-1]["segment"] != clip.get("segment"):
            groups.append({
                "segment": clip.get("segment"),
                "indices": [index],
                "duration": duration,
                "transition": clip.get("transition"),
                "transition_duration": float(clip.get("transition_duration") or 0.5),
            })
        else:
            groups[-1]["indices"].append(index)
            groups[-1]["duration"] += duration

    cursor = 0.0
    for group_index, group in enumerate(groups):
        overlap = 0.0
        if group_index > 0 and group["transition"] in {"dissolve", "crossfade", "xfade"}:
            overlap = min(group["transition_duration"], cursor, group["duration"])
        group_start = max(0.0, cursor - overlap)
        clip_cursor = group_start
        for index in group["indices"]:
            starts[index] = round(clip_cursor, 3)
            clip = plan[index]
            clip_cursor += float(clip.get("extract_dur") or clip.get("duration_sec") or 0.0)
        cursor = group_start + group["duration"]
    return starts


def resolve_punctuation_cues(plan, cues, *, asset_dir):
    """Map each cue anchor (a produced sequence role) to a timeline start + asset.
    A cue whose anchor is not present in the plan is dropped (BR1/BR2 contract:
    never point at a non-existent or dropped beat)."""
    starts = _timeline_starts(plan)

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


class PunctuationMixError(RuntimeError):
    """Raised when the punctuation remux is attempted but does not produce a
    valid output — callers must treat this as an explicit failure, never as a
    successful mix."""


def apply_punctuation_to_video(video_path, plan, cues, *, asset_dir, ffmpeg=None):
    """Remux resolved punctuation hits into a rendered video's audio (real output
    change). Returns a structured result {status, cues_mixed, cues, dropped,
    error}: `no_cues` when nothing is usable (video untouched), `ok` on a
    verified remux. A non-zero ffmpeg exit or a missing output raises
    PunctuationMixError — it must never be reported as mixed cues."""
    if ffmpeg is None:
        try:
            from .platform_tools import resolve_ffmpeg
            ffmpeg = resolve_ffmpeg()
        except Exception:
            ffmpeg = "ffmpeg"
    resolved = resolve_punctuation_cues(plan, cues, asset_dir=asset_dir)
    usable = [c for c in resolved["cues"] if os.path.exists(c.get("asset", ""))]
    if not usable:
        return {"artifact_role": "punctuation_result", "status": "no_cues",
                "cues_mixed": 0, "cues": resolved["cues"],
                "dropped": resolved["dropped"], "error": None}
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
    if result.returncode != 0 or not os.path.exists(out_tmp):
        if os.path.exists(out_tmp):
            os.remove(out_tmp)
        stderr = (result.stderr or b"").decode(errors="ignore")[-400:]
        raise PunctuationMixError(
            f"punctuation remux failed (rc={result.returncode}): {stderr}")
    os.replace(out_tmp, str(video_path))
    return {"artifact_role": "punctuation_result", "status": "ok",
            "cues_mixed": len(usable), "cues": resolved["cues"],
            "dropped": resolved["dropped"], "error": None}
