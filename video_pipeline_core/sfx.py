"""Deterministic SFX punctuation planning and ffmpeg filter construction."""
import json
from pathlib import Path


SFX_VOLUME = 0.15
ASSET_COUNTS = {"whoosh": 2, "hit": 2, "riser": 2}


def _has_title_card(segment):
    effects = segment.get("effects") or {}
    text_layer = segment.get("text_layer")
    return bool(effects.get("title_card") or (
        isinstance(text_layer, dict) and text_layer.get("label")
    ))


def plan_sfx_cues(script, timing, asset_dir):
    starts = {x["segment"]: float(x.get("start_sec") or 0)
              for x in timing.get("segments", [])}
    counters = {kind: 0 for kind in ASSET_COUNTS}
    cues = []
    previous_title = script[0].get("title") if script else None
    for index, segment in enumerate(script):
        segment_id = segment.get("segment")
        start = round(starts.get(segment_id, 0.0), 3)
        cue_types = []
        title = segment.get("title")
        if index > 0 and title != previous_title:
            cue_types.append("whoosh")
        if _has_title_card(segment):
            cue_types.append("hit")
        for kind in cue_types:
            counters[kind] += 1
            variant = 1 + ((counters[kind] - 1) % ASSET_COUNTS[kind])
            cues.append({
                "type": kind,
                "segment": segment_id,
                "start_sec": start,
                "volume": SFX_VOLUME,
                "asset": str(Path(asset_dir) / f"{kind}_{variant}.wav"),
            })
        previous_title = title
    return {"artifact_role": "sfx_plan", "version": 1, "cues": cues}


def write_sfx_plan(script, timing, asset_dir, out_path):
    plan = plan_sfx_cues(script, timing, asset_dir)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(plan, ensure_ascii=False, indent=2), encoding="utf-8")
    return plan


def build_sfx_filter(cues, base_channels=2):
    # Bundled ffmpeg has no amix normalize=0, so amix lowers the base as cue
    # inputs are added. Merge stereo channels, then pan-sum them explicitly.
    # Base channel handling depends on its layout: a mono voice-only base
    # needs pan c0|c0 (full-gain duplicate; aformat upmix would lose 3dB),
    # while a stereo voice+BGM base needs aformat passthrough (pan c0|c0
    # would discard the right channel and collapse the stereo image).
    parts = []
    labels = []
    total_inputs = len(cues) + 1
    if int(base_channels) == 1:
        parts.append("[0:a]pan=stereo|c0=c0|c1=c0[base]")
    else:
        parts.append("[0:a]aformat=channel_layouts=stereo[base]")
    for i, cue in enumerate(cues, 1):
        label = f"sfx{i}"
        delay_ms = int(round(float(cue.get("start_sec") or 0) * 1000))
        volume = float(cue.get("volume", SFX_VOLUME))
        parts.append(
            f"[{i}:a]volume={volume:.3f},adelay={delay_ms}|{delay_ms},"
            f"aformat=channel_layouts=stereo,apad[{label}]"
        )
        labels.append(f"[{label}]")
    inputs = "[base]" + "".join(labels)
    left = "+".join(f"c{i * 2}" for i in range(total_inputs))
    right = "+".join(f"c{i * 2 + 1}" for i in range(total_inputs))
    parts.append(
        f"{inputs}amerge=inputs={total_inputs}[sfxmerged];"
        f"[sfxmerged]pan=stereo|c0={left}|c1={right},aresample=48000[sfxmixed]"
    )
    return ";".join(parts), "sfxmixed"
