"""Build a lightweight soundtrack probe report for agent-readable music review."""

from __future__ import annotations

import json
import math
import re
import subprocess
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw


def _run_text(cmd: list[str]) -> tuple[str, str]:
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        raise RuntimeError((proc.stderr or proc.stdout or "command failed").strip())
    return proc.stdout or "", proc.stderr or ""


def _find_float(pattern: str, text: str) -> float | None:
    match = re.search(pattern, text)
    return float(match.group(1)) if match else None


def _load_media_probe(audio_path: Path, ffprobe: str) -> dict[str, Any]:
    stdout, _stderr = _run_text([
        ffprobe,
        "-v", "error",
        "-show_entries", "format=duration:stream=codec_type,codec_name,duration",
        "-of", "json",
        str(audio_path),
    ])
    payload = json.loads(stdout or "{}")
    return payload if isinstance(payload, dict) else {}


def _duration_seconds(probe: dict[str, Any]) -> float:
    candidates: list[Any] = [((probe.get("format") or {}) if isinstance(probe.get("format"), dict) else {}).get("duration")]
    for stream in probe.get("streams") or []:
        if isinstance(stream, dict) and stream.get("codec_type") == "audio":
            candidates.append(stream.get("duration"))
    for value in candidates:
        try:
            duration = float(value)
        except (TypeError, ValueError):
            continue
        if duration > 0:
            return duration
    return 0.0


def _audio_codec(probe: dict[str, Any]) -> str | None:
    for stream in probe.get("streams") or []:
        if isinstance(stream, dict) and stream.get("codec_type") == "audio":
            codec = stream.get("codec_name")
            return str(codec) if codec else None
    return None


def _has_audio_stream(probe: dict[str, Any]) -> bool:
    return _audio_codec(probe) is not None


def _volume_features(audio_path: Path, ffmpeg: str) -> dict[str, float | None]:
    _stdout, stderr = _run_text([
        ffmpeg,
        "-hide_banner",
        "-i", str(audio_path),
        "-af", "volumedetect",
        "-vn", "-sn", "-dn",
        "-f", "null",
        "NUL",
    ])
    return {
        "mean_dbfs": _find_float(r"mean_volume:\s*(-?\d+(?:\.\d+)?) dB", stderr),
        "peak_dbfs": _find_float(r"max_volume:\s*(-?\d+(?:\.\d+)?) dB", stderr),
    }


def _silence_features(audio_path: Path, ffmpeg: str, duration_sec: float) -> dict[str, Any]:
    _stdout, stderr = _run_text([
        ffmpeg,
        "-hide_banner",
        "-i", str(audio_path),
        "-af", "silencedetect=noise=-35dB:d=0.7",
        "-vn", "-sn", "-dn",
        "-f", "null",
        "NUL",
    ])
    silence_durations = [float(value) for value in re.findall(r"silence_duration:\s*([0-9.]+)", stderr)]
    total = round(sum(silence_durations), 3)
    return {
        "silence_event_count": len(silence_durations),
        "silence_total_sec": total,
        "silence_ratio": round(total / duration_sec, 3) if duration_sec else None,
    }


def _music_features(audio_path: Path) -> dict[str, Any]:
    try:
        import librosa  # type: ignore
        import numpy as np  # type: ignore
    except Exception:
        return {}
    try:
        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        if len(y) == 0:
            return {}
        tempo, beats = librosa.beat.beat_track(y=y, sr=sr)
        beat_times = librosa.frames_to_time(beats, sr=sr)
        rms = librosa.feature.rms(y=y, frame_length=2048, hop_length=2048)[0]
        times = librosa.frames_to_time(range(len(rms)), sr=sr, hop_length=2048)
        curve = []
        bucket = 4.0
        max_rms = float(np.max(rms)) if len(rms) else 0.0
        bucket_count = int(max(1, (times[-1] if len(times) else 0.0) // bucket + 1))
        for index in range(bucket_count):
            start = index * bucket
            end = start + bucket
            values = [float(value) for value, ts in zip(rms, times) if start <= float(ts) < end]
            if not values:
                continue
            avg = sum(values) / len(values)
            curve.append({
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "rms": round(avg, 6),
                "relative_energy": round(avg / max_rms, 3) if max_rms else None,
            })
        tempo_value = float(tempo[0] if hasattr(tempo, "__len__") else tempo)
        tags = []
        if tempo_value >= 120:
            tags.append("fast_tempo")
        elif tempo_value <= 80:
            tags.append("slow_tempo")
        if curve and max((item.get("relative_energy") or 0.0) for item in curve) >= 0.75:
            tags.append("has_energy_peaks")
        return {
            "tempo_bpm": round(tempo_value, 3),
            "beat_times": [round(float(item), 3) for item in beat_times[:256]],
            "energy_curve": curve,
            "semantic_tags": tags,
        }
    except Exception as exc:
        return {"music_feature_error": str(exc)}


def _sampling_anchors(features: dict[str, Any], *, duration_sec: float | None = None) -> dict[str, list[float]]:
    beat_times = features.get("beat_times") if isinstance(features.get("beat_times"), list) else []
    energy_curve = features.get("energy_curve") if isinstance(features.get("energy_curve"), list) else []
    vocal = features.get("vocal_analysis") if isinstance(features.get("vocal_analysis"), dict) else {}
    speech_segments = vocal.get("segments") if isinstance(vocal.get("segments"), list) else []
    if not isinstance(duration_sec, (int, float)) or duration_sec <= 0:
        duration_sec = _duration_from_features(features, beat_times, energy_curve)

    def _clamp(value: float) -> float:
        # The last analysis window may overrun the media end; an anchor
        # beyond the track is unreachable by any sample.
        return round(min(max(float(value), 0.0), float(duration_sec)), 3)

    energy_peaks: list[float] = []
    energy_drops: list[float] = []
    values = [
        float(item.get("relative_energy"))
        for item in energy_curve
        if isinstance(item, dict) and isinstance(item.get("relative_energy"), (int, float))
    ]
    peak_threshold = _percentile(values, 0.85)
    drop_threshold = _percentile(values, 0.15)
    for item in energy_curve:
        if not isinstance(item, dict):
            continue
        relative = item.get("relative_energy")
        if not isinstance(relative, (int, float)):
            continue
        start = float(item.get("start_sec") or 0.0)
        end = float(item.get("end_sec") or start)
        midpoint = round((start + end) / 2.0, 3)
        if peak_threshold is not None and relative >= max(peak_threshold, 0.08):
            energy_peaks.append(midpoint)
        if drop_threshold is not None and relative <= drop_threshold and relative <= 0.12:
            energy_drops.append(midpoint)

    speech_starts = []
    for item in speech_segments:
        if isinstance(item, dict):
            try:
                speech_starts.append(round(float(item.get("start_sec")), 3))
            except (TypeError, ValueError):
                continue

    return {
        "beat_times": _density_cap([_clamp(item) for item in beat_times if isinstance(item, (int, float))], duration_sec, per_minute=24, minimum=128),
        "energy_peaks": _density_cap([_clamp(item) for item in energy_peaks], duration_sec, per_minute=8, minimum=64),
        "energy_drops": _density_cap([_clamp(item) for item in energy_drops], duration_sec, per_minute=8, minimum=64),
        "speech_starts": _density_cap([_clamp(item) for item in speech_starts], duration_sec, per_minute=24, minimum=128),
    }


def _duration_from_features(features: dict[str, Any], beat_times: list[Any], energy_curve: list[Any]) -> float:
    try:
        duration = float(features.get("duration_sec") or 0.0)
    except (TypeError, ValueError):
        duration = 0.0
    if duration > 0:
        return duration
    curve_ends = [
        float(item.get("end_sec"))
        for item in energy_curve
        if isinstance(item, dict) and isinstance(item.get("end_sec"), (int, float))
    ]
    beat_values = [float(item) for item in beat_times if isinstance(item, (int, float))]
    return max([0.0, *curve_ends, *beat_values])


def _density_cap(values: list[float], duration_sec: float, *, per_minute: float, minimum: int) -> list[float]:
    if not values:
        return []
    minutes = max(duration_sec / 60.0, 1.0)
    cap = max(minimum, int(math.ceil(minutes * per_minute)))
    return values[:cap]


def _percentile(values: list[float], fraction: float) -> float | None:
    if not values:
        return None
    ordered = sorted(values)
    index = min(len(ordered) - 1, max(0, int(math.ceil(len(ordered) * fraction)) - 1))
    return ordered[index]


def _write_mel_spectrogram(audio_path: Path, out_path: str | Path) -> str:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    try:
        if audio_path.stat().st_size < 1024:
            raise ValueError("audio file too small for spectrogram")
        import librosa  # type: ignore
        import numpy as np  # type: ignore

        y, sr = librosa.load(str(audio_path), sr=22050, mono=True)
        mel = librosa.feature.melspectrogram(y=y, sr=sr, n_mels=64)
        db = librosa.power_to_db(mel, ref=np.max)
        norm = (db - db.min()) / (db.max() - db.min() or 1.0)
        arr = (norm * 255).astype("uint8")
        image = Image.fromarray(arr).resize((640, 180)).convert("RGB")
    except Exception:
        image = Image.new("RGB", (640, 180), "#101820")
        draw = ImageDraw.Draw(image)
        draw.text((16, 78), "mel spectrogram unavailable", fill="#ffe66d")
    image.save(out)
    return str(out)


def _instrumental_windows(vocal_segments: list[dict[str, Any]], duration_sec: float, min_window_sec: float = 4.0) -> list[dict[str, float]]:
    windows: list[dict[str, float]] = []
    cursor = 0.0
    for segment in sorted(vocal_segments, key=lambda item: float(item.get("start_sec") or 0.0)):
        start = float(segment.get("start_sec") or 0.0)
        end = float(segment.get("end_sec") or start)
        if start - cursor >= min_window_sec:
            windows.append({"start_sec": round(cursor, 3), "end_sec": round(start, 3)})
        cursor = max(cursor, end)
    if duration_sec - cursor >= min_window_sec:
        windows.append({"start_sec": round(cursor, 3), "end_sec": round(duration_sec, 3)})
    return windows


def _vocal_density(vocal_ratio: float) -> str:
    if vocal_ratio >= 0.45:
        return "high"
    if vocal_ratio >= 0.18:
        return "medium"
    if vocal_ratio > 0:
        return "low"
    return "none"


def _asr_vocal_analysis(
    audio_path: Path,
    *,
    duration_sec: float,
    asr_model: str = "small",
    language: str | None = None,
) -> dict[str, Any]:
    try:
        from faster_whisper import WhisperModel  # type: ignore
    except Exception as exc:
        return {
            "has_vocals": "unknown",
            "method": "faster_whisper_unavailable",
            "error": str(exc),
        }
    try:
        model = WhisperModel(asr_model, device="cpu", compute_type="int8")
        lang = None if not language or language == "auto" else language
        segments_iter, info = model.transcribe(str(audio_path), language=lang, vad_filter=True, beam_size=1)
        segments = []
        vocal_total = 0.0
        texts = []
        for raw in segments_iter:
            text = str(getattr(raw, "text", "") or "").strip()
            start = float(getattr(raw, "start", 0.0) or 0.0)
            end = float(getattr(raw, "end", start) or start)
            if not text or end <= start:
                continue
            vocal_total += end - start
            texts.append(text)
            segments.append({
                "start_sec": round(start, 3),
                "end_sec": round(end, 3),
                "text": text,
            })
        vocal_ratio = round(vocal_total / duration_sec, 3) if duration_sec else 0.0
        return {
            "has_vocals": bool(segments),
            "method": "faster_whisper",
            "model": asr_model,
            "language": getattr(info, "language", None) or language or "unknown",
            "vocal_density": _vocal_density(vocal_ratio),
            "vocal_ratio": vocal_ratio,
            "segments": segments,
            "instrumental_windows": _instrumental_windows(segments, duration_sec),
            "transcript_preview": " ".join(texts)[:240],
        }
    except Exception as exc:
        return {
            "has_vocals": "unknown",
            "method": "faster_whisper_error",
            "model": asr_model,
            "error": str(exc),
        }


def _sections(duration_sec: float) -> list[dict[str, Any]]:
    if duration_sec <= 0:
        return []
    if duration_sec < 24:
        return [{"start_sec": 0.0, "end_sec": round(duration_sec, 3), "role": "full_track", "energy": "unknown"}]
    intro_end = min(20.0, duration_sec * 0.2)
    build_end = min(duration_sec * 0.55, duration_sec - 12.0)
    climax_end = min(duration_sec * 0.85, duration_sec)
    sections = [
        (0.0, intro_end, "intro", "low_to_medium"),
        (intro_end, build_end, "build", "medium"),
        (build_end, climax_end, "candidate_climax", "medium_to_high"),
        (climax_end, duration_sec, "outro_or_resolve", "falling_or_unknown"),
    ]
    return [
        {
            "start_sec": round(start, 3),
            "end_sec": round(end, 3),
            "role": role,
            "energy": energy,
        }
        for start, end, role, energy in sections
        if end - start > 0.5
    ]


def _editing_fit(features: dict[str, Any]) -> dict[str, str]:
    silence_ratio = features.get("silence_ratio")
    peak = features.get("peak_dbfs")
    mean = features.get("mean_dbfs")
    if isinstance(silence_ratio, (int, float)) and silence_ratio > 0.45:
        return {"montage": "low", "speech_underlay": "medium", "ending_reflection": "medium"}
    if isinstance(mean, (int, float)) and mean > -20 and isinstance(peak, (int, float)) and peak > -6:
        return {"montage": "medium", "speech_underlay": "low", "ending_reflection": "low_to_medium"}
    return {"montage": "medium", "speech_underlay": "unknown", "ending_reflection": "medium"}


def _section_fit(features: dict[str, Any], sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    tempo = features.get("tempo_bpm")
    beat_times = features.get("beat_times") if isinstance(features.get("beat_times"), list) else []
    vocal = features.get("vocal_analysis") if isinstance(features.get("vocal_analysis"), dict) else {}
    has_vocals = vocal.get("has_vocals") is True
    vocal_density = str(vocal.get("vocal_density") or "unknown")
    duration = max(float(sections[-1]["end_sec"]), 1.0) if sections else 1.0
    beat_density = len(beat_times) / duration
    fast = isinstance(tempo, (int, float)) and tempo >= 115
    dense = beat_density >= 1.2
    intro = sections[0] if sections else {"start_sec": 0.0, "end_sec": 0.0}
    climax = next((item for item in sections if item.get("role") == "candidate_climax"), sections[-1] if sections else intro)
    outro = sections[-1] if sections else intro
    speech_fit = "low" if has_vocals and vocal_density in {"medium", "high"} else ("medium" if has_vocals else "high")
    speech_reason = (
        "vocal-heavy music can conflict with source speech or voiceover"
        if has_vocals and vocal_density in {"medium", "high"}
        else "no detected vocal load, so it is safer under speech if mixed quietly"
    )
    montage_fit = "high" if fast and dense else ("medium" if fast or dense else "low")
    warm_fit = "medium" if not fast else "low_to_medium"
    return [
        {
            "video_section": "opening_intro",
            "fit": "medium",
            "music_window": f"{intro['start_sec']}-{intro['end_sec']}s",
            "reason": "intro section is safest for opening setup",
        },
        {
            "video_section": "hotblooded_montage",
            "fit": montage_fit,
            "music_window": f"{climax['start_sec']}-{climax['end_sec']}s",
            "reason": "fit based on tempo and beat density",
        },
        {
            "video_section": "warm_story",
            "fit": warm_fit,
            "music_window": f"{intro['start_sec']}-{climax['start_sec']}s",
            "reason": "lower or build sections are safer for story setup",
        },
        {
            "video_section": "speech_underlay",
            "fit": speech_fit,
            "music_window": None,
            "reason": speech_reason,
        },
        {
            "video_section": "ending_reflection",
            "fit": "medium",
            "music_window": f"{outro['start_sec']}-{outro['end_sec']}s",
            "reason": "last section can support resolution if energy falls or holds",
        },
    ]


def build_soundtrack_probe(
    audio_path: str | Path,
    *,
    ffprobe: str = "ffprobe",
    ffmpeg: str = "ffmpeg",
    enable_asr: bool = False,
    asr_model: str = "small",
    language: str | None = None,
    spectrogram_path: str | Path | None = None,
) -> dict[str, Any]:
    path = Path(audio_path)
    if not path.is_file():
        raise FileNotFoundError(path)
    probe = _load_media_probe(path, ffprobe)
    duration = round(_duration_seconds(probe), 3)
    if not _has_audio_stream(probe):
        sections = _sections(duration)
        payload = {
            "artifact_role": "soundtrack_probe_report",
            "version": 1,
            "pass": duration > 0,
            "audio_file": str(path),
            "duration_sec": duration,
            "analysis_depth": "no_audio_stream",
            "features": {
                "has_audio": False,
                "codec": None,
                "mean_dbfs": None,
                "peak_dbfs": None,
                "silence_event_count": 0,
                "silence_total_sec": 0,
                "silence_ratio": None,
                "tempo_bpm": None,
                "beat_times": [],
                "energy_curve": [],
                "vocal_analysis": {
                    "has_vocals": False,
                    "method": "no_audio_stream",
                },
                "semantic_tags": ["no_audio_stream"],
            },
            "sections": sections,
            "editing_fit": {
                "montage": "visual_only",
                "speech_underlay": "not_applicable",
                "ending_reflection": "visual_only",
            },
            "section_fit": [],
            "recommended_usage": [],
            "sampling_anchors": {
                "beat_times": [],
                "energy_peaks": [],
                "energy_drops": [],
                "speech_starts": [],
            },
            "limitations": [
                "Input media has no audio stream; audio/music decisions must be supplied by the Soundtrack branch or left silent intentionally.",
                "Visual source analysis may continue, but this report cannot judge music, speech, or vocal content.",
            ],
        }
        if spectrogram_path:
            payload["spectrogram"] = {"path": _write_mel_spectrogram(path, spectrogram_path)}
        return payload
    features: dict[str, Any] = {
        "has_audio": True,
        "codec": _audio_codec(probe),
        "duration_sec": duration,
        **_volume_features(path, ffmpeg),
        **_silence_features(path, ffmpeg, duration),
        "tempo_bpm": None,
        "beat_times": [],
        "energy_curve": [],
        "vocal_analysis": {
            "has_vocals": "unknown",
            "method": "not_run",
        },
        "semantic_tags": [],
    }
    music_features = _music_features(path)
    if music_features:
        for key, value in music_features.items():
            if value not in (None, [], {}, ""):
                features[key] = value
    if enable_asr:
        features["vocal_analysis"] = _asr_vocal_analysis(
            path,
            duration_sec=duration,
            asr_model=asr_model,
            language=language,
        )
    sections = _sections(duration)
    editing_fit = _editing_fit(features)
    section_fit = _section_fit(features, sections)
    passed = duration > 0 and bool(sections) and bool(editing_fit)
    analysis_depth = "basic_ffmpeg"
    if music_features:
        analysis_depth += "+music_features"
    if enable_asr:
        analysis_depth += "+vocal_asr"
    payload = {
        "artifact_role": "soundtrack_probe_report",
        "version": 1,
        "pass": passed,
        "audio_file": str(path),
        "duration_sec": duration,
        "analysis_depth": analysis_depth,
        "features": features,
        "sections": sections,
        "editing_fit": editing_fit,
        "section_fit": section_fit,
        "sampling_anchors": _sampling_anchors(features, duration_sec=duration),
        "recommended_usage": [
            {
                "video_section": "montage",
                "music_window": f"{sections[2]['start_sec']}-{sections[2]['end_sec']}s" if len(sections) >= 3 else f"0-{duration}s",
                "reason": "basic probe marks this as a candidate high-energy or central section",
            }
        ] if sections else [],
        "limitations": [
            "No source separation or CLAP semantic model was run.",
            "ASR is optional and may be inaccurate for dense singing or mixed music.",
            "Use this as a Stage 0.5 / Soundtrack Arranger decision aid, not a final music-quality judgement.",
        ],
    }
    if spectrogram_path:
        payload["spectrogram"] = {"path": _write_mel_spectrogram(path, spectrogram_path)}
    return payload


def write_soundtrack_probe(
    audio_path: str | Path,
    out_path: str | Path,
    *,
    ffprobe: str = "ffprobe",
    ffmpeg: str = "ffmpeg",
    enable_asr: bool = False,
    asr_model: str = "small",
    language: str | None = None,
    spectrogram_path: str | Path | None = None,
) -> dict[str, Any]:
    payload = build_soundtrack_probe(
        audio_path,
        ffprobe=ffprobe,
        ffmpeg=ffmpeg,
        enable_asr=enable_asr,
        asr_model=asr_model,
        language=language,
        spectrogram_path=spectrogram_path,
    )
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return payload
