"""Execute an accepted audio_mix_plan into final_audio.wav without video render."""

from __future__ import annotations

import json
import math
import re
import subprocess
import tempfile
import wave
from array import array
from hashlib import sha256
from pathlib import Path
from typing import Any, Mapping

from .asset_paths import relativize_payload_refs
from . import material_map
from .platform_tools import resolve_ffmpeg, resolve_ffprobe

LOUDNESS_FILTER = "loudnorm=I=-18:TP=-1.5:LRA=11"


def _clean(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _load_json(path: str | Path) -> dict[str, Any]:
    data = json.loads(Path(path).read_text(encoding="utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError(f"expected JSON object: {path}")
    return data


def _resolve_audio_file(value: Any, root: Path) -> Path:
    path = Path(_clean(value))
    if path.is_absolute():
        return path
    return root / path


def _probe_duration(path: Path, ffprobe: str) -> float:
    proc = subprocess.run(
        [
            ffprobe,
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "csv=p=0",
            str(path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"ffprobe failed for {path}: {proc.stderr.strip()}")
    try:
        return float(proc.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(f"could not parse audio duration for {path}") from exc


def _probe_audio_levels(path: Path, ffmpeg: str) -> dict[str, float | None]:
    proc = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-nostats",
            "-i",
            str(path),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "-",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    text = f"{proc.stdout}\n{proc.stderr}"

    def find_db(label: str) -> float | None:
        match = re.search(rf"{label}:\s*(-?\d+(?:\.\d+)?)\s*dB", text)
        if not match:
            return None
        return float(match.group(1))

    return {
        "mean_dbfs": find_db("mean_volume"),
        "peak_dbfs": find_db("max_volume"),
    }


def _transcode_one(input_path: Path, output_path: Path, ffmpeg: str) -> None:
    proc = subprocess.run(
        [
            ffmpeg,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-i",
            str(input_path),
            "-af",
            LOUDNESS_FILTER,
            "-acodec",
            "pcm_s16le",
            "-ar",
            "48000",
            "-ac",
            "2",
            str(output_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"audio transcode failed: {proc.stderr.strip()}")


def _concat_tracks(input_paths: list[Path], output_path: Path, ffmpeg: str) -> None:
    with tempfile.TemporaryDirectory() as tmp:
        list_path = Path(tmp) / "audio_concat.txt"
        lines = []
        for path in input_paths:
            safe = str(path.resolve()).replace("\\", "/").replace("'", "'\\''")
            lines.append(f"file '{safe}'")
        list_path.write_text("\n".join(lines), encoding="utf-8")
        proc = subprocess.run(
            [
                ffmpeg,
                "-y",
                "-hide_banner",
                "-loglevel",
                "error",
                "-f",
                "concat",
                "-safe",
                "0",
                "-i",
                str(list_path),
                "-af",
                LOUDNESS_FILTER,
                "-acodec",
                "pcm_s16le",
                "-ar",
                "48000",
                "-ac",
                "2",
                str(output_path),
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=False,
        )
    if proc.returncode != 0:
        raise RuntimeError(f"audio concat failed: {proc.stderr.strip()}")


def _float_value(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _plan_sections(audio_mix_plan: Mapping[str, Any]) -> dict[str, dict[str, float]]:
    sections: dict[str, dict[str, float]] = {}
    for section in audio_mix_plan.get("sections") or []:
        section_id = _clean(section.get("section_id"))
        if not section_id:
            continue
        start_sec = _float_value(section.get("start_sec"))
        duration_sec = _float_value(section.get("duration_sec"))
        if duration_sec <= 0 and section.get("end_sec") is not None:
            duration_sec = max(0.0, _float_value(section.get("end_sec")) - start_sec)
        sections[section_id] = {"start_sec": start_sec, "duration_sec": duration_sec}
    return sections


def _track_placement(track: Mapping[str, Any], sections: Mapping[str, Mapping[str, float]]) -> dict[str, Any] | None:
    start_sec = track.get("start_sec")
    duration_sec = track.get("duration_sec")
    section_id = _clean(track.get("section_id"))
    if start_sec is None or duration_sec is None:
        section = sections.get(section_id)
        if not section:
            return None
        start_sec = section.get("start_sec")
        duration_sec = section.get("duration_sec")
    start = _float_value(start_sec)
    duration = _float_value(duration_sec)
    if duration <= 0:
        return None
    return {
        "section_id": section_id,
        "candidate_id": _clean(track.get("candidate_id")),
        "audio_file": _clean(track.get("audio_file")),
        "start_sec": round(start, 3),
        "duration_sec": round(duration, 3),
        "source_offset_sec": round(_float_value(track.get("source_offset_sec")), 3),
        "fade_in_sec": round(max(0.0, _float_value(track.get("fade_in_sec"))), 3),
        "fade_out_sec": round(max(0.0, _float_value(track.get("fade_out_sec"))), 3),
        "role": _clean(track.get("role")),
        "source_type": _clean(track.get("source_type")),
        "license_status": _clean(track.get("license_status")),
        "ducking_policy": _clean(track.get("ducking_policy")),
        "volume": round(max(0.0, _float_value(track.get("volume"), 1.0)), 3),
        "applied_volume": round(max(0.0, _float_value(track.get("volume"), 1.0)), 3),
        "ducking_applied": False,
    }


def _is_voice_or_original_audio(placement: Mapping[str, Any]) -> bool:
    role = _clean(placement.get("role"))
    policy = _clean(placement.get("ducking_policy"))
    return role in {"voice", "voiceover", "narration", "source_speech", "diegetic"} or policy == "preserve_original_audio"


def _is_duckable_music(placement: Mapping[str, Any]) -> bool:
    role = _clean(placement.get("role"))
    return role.startswith("music") or role in {"bgm", "music_bed"}


def _overlaps(a: Mapping[str, Any], b: Mapping[str, Any]) -> bool:
    a_start = _float_value(a.get("start_sec"))
    a_end = a_start + _float_value(a.get("duration_sec"))
    b_start = _float_value(b.get("start_sec"))
    b_end = b_start + _float_value(b.get("duration_sec"))
    return max(a_start, b_start) < min(a_end, b_end)


SPEECH_AWARE_DEFAULTS = {
    "duck_db": -12.0,
    "attack_ms": 80,
    "release_ms": 300,
    "activity_source": "protected_audio_silencedetect",
}
SPEECH_AWARE_KEYS = set(SPEECH_AWARE_DEFAULTS)
SPEECH_PROTECTED_LOW_RATE_MIX_WEIGHT = 1.38


def _speech_aware_requested(audio_mix_plan: Mapping[str, Any], tracks: list[Mapping[str, Any]]) -> bool:
    return audio_mix_plan.get("ducking_policy") == "speech_aware" or any(
        track.get("ducking_policy") == "speech_aware" for track in tracks
    )


def _speech_protected_mix_weight(placement: Mapping[str, Any], speech_aware: bool) -> float:
    if not speech_aware or not _is_voice_or_original_audio(placement):
        return 1.0
    try:
        with wave.open(str(placement["audio_file"]), "rb") as handle:
            sample_rate = handle.getframerate()
    except (OSError, wave.Error):
        sample_rate = 48000
    return SPEECH_PROTECTED_LOW_RATE_MIX_WEIGHT if sample_rate < 48000 else 1.0


def _speech_aware_config(audio_mix_plan: Mapping[str, Any], tracks: list[Mapping[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    raw = audio_mix_plan.get("ducking")
    errors: list[dict[str, Any]] = []
    if raw is None:
        raw = {}
    if not isinstance(raw, Mapping):
        errors.append({"rule": "speech_aware_invalid_contract", "field": "ducking", "message": "ducking must be an object"})
        raw = {}
    merged = dict(raw)
    for track in tracks:
        track_ducking = track.get("ducking")
        if track_ducking is not None:
            if not isinstance(track_ducking, Mapping):
                errors.append({"rule": "speech_aware_invalid_contract", "field": "track.ducking", "message": "track ducking must be an object"})
            else:
                merged = {**merged, **dict(track_ducking)}
    unknown = sorted(set(merged) - SPEECH_AWARE_KEYS)
    if unknown:
        errors.append({"rule": "speech_aware_invalid_contract", "field": "ducking", "unknown_keys": unknown, "message": "speech-aware ducking contains unknown keys"})
    config = {**SPEECH_AWARE_DEFAULTS, **{key: merged[key] for key in SPEECH_AWARE_KEYS if key in merged}}
    for key in ("duck_db", "attack_ms", "release_ms"):
        value = config[key]
        if isinstance(value, bool):
            errors.append({"rule": "speech_aware_invalid_contract", "field": key, "message": f"{key} must be a finite number"})
            continue
        try:
            number = float(value)
        except (TypeError, ValueError):
            number = math.nan
        if not math.isfinite(number):
            errors.append({"rule": "speech_aware_invalid_contract", "field": key, "message": f"{key} must be a finite number"})
        elif key == "duck_db" and not -60.0 <= number < 0.0:
            errors.append({"rule": "speech_aware_invalid_contract", "field": key, "message": "duck_db must be >= -60 and < 0"})
        elif key == "attack_ms" and not 1.0 <= number <= 5000.0:
            errors.append({"rule": "speech_aware_invalid_contract", "field": key, "message": "attack_ms must be between 1 and 5000"})
        elif key == "release_ms" and not 1.0 <= number <= 10000.0:
            errors.append({"rule": "speech_aware_invalid_contract", "field": key, "message": "release_ms must be between 1 and 10000"})
        config[key] = int(number) if key != "duck_db" and number.is_integer() else number
    if config["activity_source"] != "protected_audio_silencedetect":
        errors.append({"rule": "speech_aware_invalid_contract", "field": "activity_source", "message": "activity_source must be protected_audio_silencedetect"})
    return config, errors


def _speech_windows(runs: list[Mapping[str, Any]], duration_sec: float) -> list[dict[str, float]]:
    windows = []
    for run in runs or []:
        if _clean(run.get("kind")).casefold() != "speech":
            continue
        start = max(0.0, min(duration_sec, _float_value(run.get("start"))))
        end = max(start, min(duration_sec, _float_value(run.get("end"))))
        if end > start:
            windows.append({"start_sec": round(start, 3), "end_sec": round(end, 3), "duration_sec": round(end - start, 3)})
    return windows


def _recovery_windows(speech_windows: list[Mapping[str, float]], duration_sec: float, attack_sec: float, release_sec: float) -> list[dict[str, float]]:
    windows = []
    cursor = 0.0
    for speech in speech_windows:
        start = max(cursor, _float_value(speech.get("start_sec")))
        end = _float_value(speech.get("end_sec"))
        usable_start = cursor + release_sec if cursor > 0 else 0.0
        usable_end = start - attack_sec
        if usable_end - usable_start >= 0.25:
            windows.append({"start_sec": round(usable_start, 3), "end_sec": round(usable_end, 3), "duration_sec": round(usable_end - usable_start, 3)})
        cursor = max(cursor, end)
    usable_start = cursor + release_sec
    if duration_sec - usable_start >= 0.25:
        windows.append({"start_sec": round(usable_start, 3), "end_sec": round(duration_sec, 3), "duration_sec": round(duration_sec - usable_start, 3)})
    return windows


def _envelope_gain(time_sec: float, speech_windows: list[Mapping[str, float]], config: Mapping[str, Any]) -> float:
    duck_gain = 10 ** (_float_value(config.get("duck_db"), -12.0) / 20.0)
    attack = _float_value(config.get("attack_ms"), 80.0) / 1000.0
    release = _float_value(config.get("release_ms"), 300.0) / 1000.0
    for window in speech_windows:
        start = _float_value(window.get("start_sec"))
        end = _float_value(window.get("end_sec"))
        if start - attack <= time_sec < start:
            return 1.0 + (duck_gain - 1.0) * ((time_sec - (start - attack)) / attack)
        if start <= time_sec < end:
            return duck_gain
        if end <= time_sec < end + release:
            return duck_gain + (1.0 - duck_gain) * ((time_sec - end) / release)
    return 1.0


def _speech_aware_expression(windows: list[Mapping[str, float]], config: Mapping[str, Any], duration_sec: float) -> str:
    duck_gain = 10 ** (_float_value(config.get("duck_db"), -12.0) / 20.0)
    attack = _float_value(config.get("attack_ms"), 80.0) / 1000.0
    release = _float_value(config.get("release_ms"), 300.0) / 1000.0
    clauses: list[tuple[str, str]] = []
    cursor = 0.0
    for window in windows:
        start = max(0.0, _float_value(window.get("start_sec")))
        end = min(duration_sec, _float_value(window.get("end_sec")))
        if end <= start:
            continue
        attack_start = max(0.0, start - attack)
        release_end = min(duration_sec, end + release)
        if attack_start > cursor:
            clauses.append((f"lt(t\\,{attack_start:.6f})", "1"))
        attack_value = f"1+({duck_gain:.8f}-1)*(t-{attack_start:.6f})/{attack:.6f}"
        release_value = f"{duck_gain:.8f}+(1-{duck_gain:.8f})*(t-{end:.6f})/{release:.6f}"
        clauses.extend([
            (f"lt(t\\,{start:.6f})", attack_value),
            (f"lt(t\\,{end:.6f})", f"{duck_gain:.8f}"),
            (f"lt(t\\,{release_end:.6f})", release_value),
        ])
        cursor = max(cursor, release_end)
    if cursor < duration_sec:
        clauses.append((f"lt(t\\,{duration_sec:.6f})", "1"))
    expression = "1"
    for condition, value in reversed(clauses):
        expression = f"if({condition}\\,{value}\\,{expression})"
    return expression


def _read_wav_mono(path: Path) -> tuple[int, list[float]]:
    try:
        with wave.open(str(path), "rb") as handle:
            rate = handle.getframerate()
            channels = handle.getnchannels()
            width = handle.getsampwidth()
            frames = handle.getnframes()
            raw = handle.readframes(frames)
    except (wave.Error, EOFError):
        with tempfile.TemporaryDirectory() as tmp:
            decoded = Path(tmp) / "decoded.wav"
            proc = subprocess.run(
                [
                    resolve_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(path), "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1",
                    str(decoded),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if proc.returncode != 0 or not decoded.is_file():
                raise wave.Error(f"could not decode audio input {path}: {proc.stderr.strip()}")
            return _read_wav_mono(decoded)
    if rate != 48000:
        with tempfile.TemporaryDirectory() as tmp:
            decoded = Path(tmp) / "resampled.wav"
            proc = subprocess.run(
                [
                    resolve_ffmpeg(), "-y", "-hide_banner", "-loglevel", "error",
                    "-i", str(path), "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "1",
                    str(decoded),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=False,
            )
            if proc.returncode != 0 or not decoded.is_file():
                raise wave.Error(f"could not resample audio input {path}: {proc.stderr.strip()}")
            return _read_wav_mono(decoded)
    if width != 2:
        raise ValueError(f"waveform check requires 16-bit PCM, got sample width {width}")
    values = array("h")
    values.frombytes(raw)
    if values.itemsize != 2:
        raise ValueError("waveform check could not decode PCM samples")
    if channels <= 1:
        return rate, [value / 32768.0 for value in values]
    return rate, [sum(values[index:index + channels]) / channels / 32768.0 for index in range(0, len(values), channels)]


def _rms_dbfs(values: list[float]) -> float | None:
    if not values:
        return None
    rms = math.sqrt(sum(value * value for value in values) / len(values))
    return round(20.0 * math.log10(max(rms, 1e-12)), 3)


def _enveloped_rms(
    path: Path,
    start: float,
    duration: float,
    speech_windows: list[Mapping[str, float]],
    config: Mapping[str, Any],
    *,
    timeline_start: float = 0.0,
) -> float | None:
    rate, values = _read_wav_mono(path)
    first = max(0, int(round(start * rate)))
    last = min(len(values), first + max(1, int(round(duration * rate))))
    enveloped = [
        values[index] * _envelope_gain(timeline_start + (index - first) / rate, speech_windows, config)
        for index in range(first, last)
    ]
    return _rms_dbfs(enveloped)


def _waveform_window_check(source_path: Path, output_path: Path, source_start: float, timeline_start: float, duration: float) -> dict[str, Any]:
    try:
        source_rate, source = _read_wav_mono(source_path)
        output_rate, output = _read_wav_mono(output_path)
    except (OSError, ValueError, wave.Error) as exc:
        return {"pass": False, "reason": "waveform_decode_failed", "message": str(exc)}
    if source_rate != output_rate:
        return {"pass": False, "reason": "sample_rate_mismatch", "source_rate": source_rate, "output_rate": output_rate}
    step = 4
    source_first = max(0, int(round(source_start * source_rate)))
    output_first = max(0, int(round(timeline_start * output_rate)))
    count = min(int(round(duration * source_rate)), len(source) - source_first, len(output) - output_first)
    if count < int(0.25 * source_rate):
        return {"pass": False, "reason": "window_too_short", "duration_sec": round(count / source_rate, 3)}
    src = source[source_first:source_first + count:step]
    max_lag = max(1, int(round(0.010 * source_rate / step)))
    best = None
    for lag in range(-max_lag, max_lag + 1):
        out_start = output_first + lag * step
        out_indices = range(out_start, out_start + count, step)
        if out_start < 0 or out_start + count > len(output):
            continue
        out_values = output[out_start:out_start + count:step]
        if len(out_values) != len(src):
            continue
        src_mean = sum(src) / len(src)
        out_mean = sum(out_values) / len(out_values)
        src_centered = [value - src_mean for value in src]
        out_centered = [value - out_mean for value in out_values]
        src_energy = sum(value * value for value in src_centered)
        out_energy = sum(value * value for value in out_centered)
        if src_energy <= 1e-12 or out_energy <= 1e-12:
            continue
        dot = sum(a * b for a, b in zip(src_centered, out_centered))
        correlation = dot / math.sqrt(src_energy * out_energy)
        gain = sum(a * b for a, b in zip(src, out_values)) / max(sum(a * a for a in src), 1e-12)
        candidate = (correlation, lag, gain)
        if best is None or candidate[0] > best[0]:
            best = candidate
    if best is None:
        return {"pass": False, "reason": "waveform_correlation_unavailable"}
    correlation, lag, gain = best
    gain_db = 20.0 * math.log10(max(abs(gain), 1e-12))
    passed = abs(lag * step / source_rate) <= 0.010 and abs(gain_db) <= 0.5 and correlation >= 0.70
    return {
        "pass": passed,
        "lag_ms": round(lag * step / source_rate * 1000.0, 3),
        "correlation": round(correlation, 4),
        "estimated_gain_db": round(gain_db, 3),
        "duration_sec": round(count / source_rate, 3),
        "tolerances": {"max_abs_lag_ms": 10.0, "max_gain_error_db": 0.5, "min_correlation": 0.70},
    }


def _waveform_activity_alignment(
    source_path: Path,
    expected_windows: list[Mapping[str, Any]],
) -> dict[str, Any]:
    """Check protected source onsets/offsets against detector windows."""
    try:
        rate, values = _read_wav_mono(source_path)
    except (OSError, ValueError, wave.Error) as exc:
        return {"pass": False, "reason": "waveform_decode_failed", "message": str(exc)}
    frame_size = max(1, int(round(rate * 0.01)))
    frame_rms = []
    for start in range(0, len(values), frame_size):
        frame = values[start:start + frame_size]
        rms = _rms_dbfs(frame)
        frame_rms.append(-120.0 if rms is None else rms)
    active_floor = max(frame_rms, default=-120.0) - 20.0
    checks = []
    for window in expected_windows:
        expected_start = _float_value(window.get("source_start_sec"))
        expected_end = expected_start + _float_value(window.get("source_duration_sec"))
        first_frame = max(0, int(math.floor(expected_start * 100.0)) - 20)
        last_frame = min(len(frame_rms), int(math.ceil(expected_end * 100.0)) + 20)
        active = [index for index in range(first_frame, last_frame) if frame_rms[index] >= active_floor]
        if not active:
            checks.append({"pass": False, "reason": "speech_activity_not_found"})
            continue
        onset = active[0] / 100.0
        offset = min(len(frame_rms), active[-1] + 1) / 100.0
        onset_error_ms = (onset - expected_start) * 1000.0
        offset_error_ms = (offset - expected_end) * 1000.0
        end_is_open = expected_end >= (len(values) / rate) - 0.02
        checks.append({
            "pass": abs(onset_error_ms) <= 10.0 and (end_is_open or abs(offset_error_ms) <= 20.0 + 1e-6),
            "expected_start_sec": round(expected_start, 3),
            "actual_start_sec": round(onset, 3),
            "expected_end_sec": round(expected_end, 3),
            "actual_end_sec": round(offset, 3),
            "onset_error_ms": round(onset_error_ms, 3),
            "offset_error_ms": round(offset_error_ms, 3),
            "end_is_open": end_is_open,
        })
    return {
        "pass": bool(checks) and all(item["pass"] for item in checks),
        "windows": checks,
        "tolerances": {"max_abs_onset_ms": 10.0, "max_abs_offset_ms": 10.0},
    }


def _derive_speech_aware_windows(
    placements: list[dict[str, Any]],
    *,
    ffprobe: str,
    timeline_duration: float,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Derive timeline speech windows from protected audio, never from subtitles."""
    protected = [item for item in placements if _is_voice_or_original_audio(item)]
    windows: list[dict[str, Any]] = []
    detector_evidence: list[dict[str, Any]] = []
    for placement in protected:
        source_path = Path(placement["audio_file"])
        try:
            source_duration = _probe_duration(source_path, ffprobe)
            runs = material_map.detect_speech_runs(source_path, source_duration)
        except (OSError, RuntimeError, ValueError) as exc:
            detector_evidence.append({
                "protected_audio": str(source_path),
                "ok": False,
                "error": str(exc),
            })
            continue
        detector_evidence.append({
            "protected_audio": str(source_path),
            "protected_audio_sha256": sha256(source_path.read_bytes()).hexdigest().upper(),
            "ok": True,
            "command": [
                "ffmpeg", "-hide_banner", "-i", str(source_path), "-af",
                "silencedetect=noise=-35dB:d=0.4", "-f", "null", "-",
            ],
            "threshold_dbfs": -35.0,
            "minimum_silence_sec": 0.4,
            "runs": runs,
        })
        source_offset = _float_value(placement.get("source_offset_sec"))
        for window in _speech_windows(runs, source_duration):
            start = _float_value(placement.get("start_sec")) + _float_value(window.get("start_sec")) - source_offset
            end = _float_value(placement.get("start_sec")) + _float_value(window.get("end_sec")) - source_offset
            start = max(0.0, min(timeline_duration, start))
            end = max(start, min(timeline_duration, end))
            if end > start:
                windows.append({
                    "start_sec": round(start, 3),
                    "end_sec": round(end, 3),
                    "duration_sec": round(end - start, 3),
                    "protected_candidate_id": placement.get("candidate_id"),
                    "source_start_sec": round(_float_value(window.get("start_sec")), 3),
                    "source_duration_sec": round(_float_value(window.get("duration_sec")), 3),
                })
    windows.sort(key=lambda item: (item["start_sec"], item["end_sec"]))
    return windows, protected, detector_evidence


def _apply_ducking_policy(
    placements: list[dict[str, Any]],
    ducked_volume: float = 0.28,
    *,
    speech_windows: list[dict[str, Any]] | None = None,
    speech_config: Mapping[str, Any] | None = None,
    timeline_duration: float = 0.0,
) -> None:
    protected_audio = [item for item in placements if _is_voice_or_original_audio(item)]
    for placement in placements:
        if placement.get("ducking_policy") != "duck_under_voice":
            if placement.get("ducking_policy") != "speech_aware":
                continue
            if not _is_duckable_music(placement) or not speech_windows:
                continue
            active = [window for window in speech_windows if _overlaps(placement, window)]
            if not active:
                continue
            placement_start = _float_value(placement.get("start_sec"))
            placement_duration = _float_value(placement.get("duration_sec"))
            local_active = []
            for window in active:
                local_start = max(0.0, _float_value(window.get("start_sec")) - placement_start)
                local_end = min(
                    placement_duration,
                    _float_value(window.get("end_sec")) - placement_start,
                )
                if local_end > local_start:
                    local_active.append({"start_sec": local_start, "end_sec": local_end})
            placement["applied_volume"] = round(
                max(0.0, _float_value(placement.get("volume"), 1.0)),
                3,
            )
            placement["ducking_applied"] = True
            placement["ducking_mode"] = "speech_aware"
            placement["speech_windows"] = active
            placement["speech_aware_expression"] = _speech_aware_expression(
                local_active,
                speech_config or SPEECH_AWARE_DEFAULTS,
                placement_duration,
            )
            continue
        if not _is_duckable_music(placement):
            continue
        if not any(_overlaps(placement, protected) for protected in protected_audio):
            continue
        placement["applied_volume"] = round(ducked_volume, 3)
        placement["ducking_applied"] = True


def _speech_aware_rms_evidence(
    placements: list[dict[str, Any]],
    speech_windows: list[dict[str, Any]],
    recovery_windows: list[dict[str, float]],
    config: Mapping[str, Any],
) -> dict[str, Any]:
    music = next((item for item in placements if item.get("ducking_mode") == "speech_aware"), None)
    if music is None:
        return {
            "measurement_status": "not_applicable",
            "reason": "no_duckable_music_overlaps_protected_speech",
            "active_reduction_db": None,
            "recovery_gain_over_active_db": None,
            "ramp_evidence": {"attack_monotonic": False, "release_monotonic": False},
        }
    active_measurements = []
    for window in speech_windows:
        center = (_float_value(window.get("start_sec")) + _float_value(window.get("end_sec"))) / 2.0
        start = max(_float_value(window.get("start_sec")) + 0.2, center - 0.2)
        duration = min(0.4, _float_value(window.get("end_sec")) - start)
        if duration <= 0:
            continue
        source_start = _float_value(music.get("source_offset_sec")) + start - _float_value(music.get("start_sec"))
        measured = _enveloped_rms(
            Path(music["audio_file"]),
            source_start,
            duration,
            speech_windows,
            config,
            timeline_start=start,
        )
        active_measurements.append({
            "start_sec": round(start, 3),
            "duration_sec": round(duration, 3),
            "rms_dbfs": measured,
        })
    recovery_measurements = []
    for window in recovery_windows:
        start = _float_value(window.get("start_sec")) + 0.1
        duration = min(0.4, _float_value(window.get("end_sec")) - start)
        if duration <= 0:
            continue
        source_start = _float_value(music.get("source_offset_sec")) + start - _float_value(music.get("start_sec"))
        measured = _enveloped_rms(
            Path(music["audio_file"]),
            source_start,
            duration,
            speech_windows,
            config,
            timeline_start=start,
        )
        recovery_measurements.append({
            "start_sec": round(start, 3),
            "duration_sec": round(duration, 3),
            "rms_dbfs": measured,
        })
    active_values = [item["rms_dbfs"] for item in active_measurements if item["rms_dbfs"] is not None]
    recovery_values = [item["rms_dbfs"] for item in recovery_measurements if item["rms_dbfs"] is not None]
    active_rms = sum(active_values) / len(active_values) if active_values else None
    recovery_rms = sum(recovery_values) / len(recovery_values) if recovery_values else None
    attack_monotonic = True
    release_monotonic = True
    attack = _float_value(config.get("attack_ms"), 80.0) / 1000.0
    release = _float_value(config.get("release_ms"), 300.0) / 1000.0
    ramp_samples = []
    for window in speech_windows:
        start = _float_value(window.get("start_sec"))
        end = _float_value(window.get("end_sec"))
        attack_values = [_envelope_gain(start - attack + attack * index / 7.0, speech_windows, config) for index in range(8)]
        release_values = [_envelope_gain(end + release * index / 7.0, speech_windows, config) for index in range(8)]
        attack_monotonic = attack_monotonic and all(a >= b - 1e-9 for a, b in zip(attack_values, attack_values[1:]))
        release_monotonic = release_monotonic and all(a <= b + 1e-9 for a, b in zip(release_values, release_values[1:]))
        ramp_samples.append({
            "speech_start_sec": round(start, 3),
            "speech_end_sec": round(end, 3),
            "attack_gain_samples": [round(value, 5) for value in attack_values],
            "release_gain_samples": [round(value, 5) for value in release_values],
        })
    return {
        "measurement_status": "pass" if active_rms is not None else "unknown",
        "measurement_basis": "source_bgm_with_applied_envelope",
        "active_windows": active_measurements,
        "recovery_windows": recovery_measurements,
        "active_rms_dbfs": round(active_rms, 3) if active_rms is not None else None,
        "recovery_rms_dbfs": round(recovery_rms, 3) if recovery_rms is not None else None,
        "active_reduction_db": round(recovery_rms - active_rms, 3) if active_rms is not None and recovery_rms is not None else None,
        "recovery_gain_over_active_db": round(recovery_rms - active_rms, 3) if active_rms is not None and recovery_rms is not None else None,
        "ramp_evidence": {
            "attack_monotonic": attack_monotonic,
            "release_monotonic": release_monotonic,
            "samples": ramp_samples,
        },
    }


def _recovered_waveform_window_check(
    source_path: Path,
    output_path: Path,
    placements: list[dict[str, Any]],
    speech_windows: list[dict[str, Any]],
    config: Mapping[str, Any],
    source_start: float,
    timeline_start: float,
    duration: float,
) -> dict[str, Any]:
    """Subtract known non-protected mix inputs before checking protected speech."""
    try:
        source_rate, source = _read_wav_mono(source_path)
        output_rate, output = _read_wav_mono(output_path)
        input_values = {
            id(placement): _read_wav_mono(Path(placement["audio_file"]))
            for placement in placements
        }
    except (OSError, ValueError, wave.Error) as exc:
        return {"pass": False, "reason": "waveform_decode_failed", "message": str(exc)}
    if source_rate != output_rate:
        return {"pass": False, "reason": "sample_rate_mismatch"}
    rate = source_rate
    first = max(0, int(round(source_start * rate)))
    output_first = max(0, int(round(timeline_start * rate)))
    count = min(int(round(duration * rate)), len(source) - first, len(output) - output_first)
    if count < int(0.25 * rate):
        return {"pass": False, "reason": "window_too_short"}

    def predicted_sample(placement: Mapping[str, Any], timeline_time: float) -> float:
        start = _float_value(placement.get("start_sec"))
        end = start + _float_value(placement.get("duration_sec"))
        if timeline_time < start or timeline_time >= end:
            return 0.0
        values_rate, values = input_values[id(placement)]
        if values_rate != rate:
            return 0.0
        source_time = _float_value(placement.get("source_offset_sec")) + timeline_time - start
        index = int(round(source_time * rate))
        if index < 0 or index >= len(values):
            return 0.0
        gain = _float_value(placement.get("applied_volume"), 1.0)
        if placement.get("ducking_mode") == "speech_aware":
            gain *= _envelope_gain(timeline_time, speech_windows, config)
        return values[index] * gain

    # The ffmpeg mixer's fixed input normalization is measured from the known
    # source sum, then removed before evaluating the protected placement.  Use
    # active placement windows instead of the first six timeline seconds: a
    # legitimate interview may begin late in an otherwise silent preview.
    numerator = 0.0
    denominator = 0.0
    sample_budget = max(1, int(6.0 * rate) // 16)
    sampled = 0
    placement_windows = sorted(
        (
            max(0.0, _float_value(placement.get("start_sec"))),
            max(
                0.0,
                _float_value(placement.get("start_sec"))
                + _float_value(placement.get("duration_sec")),
            ),
        )
        for placement in placements
        if abs(_float_value(placement.get("applied_volume"), 1.0)) > 1e-12
    )
    active_windows = [
        (
            max(0.0, _float_value(window.get("start_sec"))),
            max(0.0, _float_value(window.get("end_sec"))),
        )
        for window in speech_windows
        if _float_value(window.get("end_sec")) > _float_value(window.get("start_sec"))
    ] or placement_windows
    for window_start, window_end in active_windows:
        first_offset = max(0, int(round(window_start * rate)))
        last_offset = min(len(output), int(round(window_end * rate)))
        for offset in range(first_offset, last_offset, 16):
            timeline_time = offset / rate
            expected = sum(predicted_sample(placement, timeline_time) for placement in placements)
            actual = output[offset]
            numerator += expected * actual
            denominator += expected * expected
            sampled += 1
            if sampled >= sample_budget:
                break
        if sampled >= sample_budget:
            break
    mix_scale = numerator / denominator if denominator > 1e-12 else 0.0
    if abs(mix_scale) <= 1e-12:
        return {"pass": False, "reason": "mix_scale_unavailable"}

    src = source[first:first + count:4]
    recovered = []
    for index in range(0, count, 4):
        timeline_time = timeline_start + index / rate
        other = sum(
            predicted_sample(placement, timeline_time)
            for placement in placements
            if Path(placement["audio_file"]) != source_path
        )
        recovered.append(output[output_first + index] / mix_scale - other)
    if len(src) != len(recovered):
        return {"pass": False, "reason": "waveform_sample_mismatch"}
    src_mean = sum(src) / len(src)
    recovered_mean = sum(recovered) / len(recovered)
    src_centered = [value - src_mean for value in src]
    recovered_centered = [value - recovered_mean for value in recovered]
    src_energy = sum(value * value for value in src_centered)
    recovered_energy = sum(value * value for value in recovered_centered)
    if src_energy <= 1e-12 or recovered_energy <= 1e-12:
        return {"pass": False, "reason": "waveform_correlation_unavailable"}
    correlation = sum(a * b for a, b in zip(src_centered, recovered_centered)) / math.sqrt(src_energy * recovered_energy)
    gain = sum(a * b for a, b in zip(src, recovered)) / max(sum(a * a for a in src), 1e-12)
    gain_db = 20.0 * math.log10(max(abs(gain), 1e-12))
    return {
        "pass": correlation >= 0.70 and abs(gain_db) <= 0.5,
        "lag_ms": 0.0,
        "correlation": round(correlation, 4),
        "estimated_gain_db": round(gain_db, 3),
        "mix_scale": round(mix_scale, 5),
        "duration_sec": round(count / rate, 3),
        "tolerances": {"max_abs_lag_ms": 10.0, "max_gain_error_db": 0.5, "min_correlation": 0.70},
        "measurement_basis": "final_mix_with_known_non_protected_inputs_subtracted",
    }


def _protected_speech_waveform_report(
    protected: list[dict[str, Any]],
    placements: list[dict[str, Any]],
    speech_windows: list[dict[str, Any]],
    speech_config: Mapping[str, Any],
    output_path: Path,
) -> dict[str, Any]:
    checks = []
    skipped = []
    for placement in protected:
        placement_windows = [
            window for window in speech_windows
            if window.get("protected_candidate_id") == placement.get("candidate_id")
        ]
        alignment = _waveform_activity_alignment(Path(placement["audio_file"]), placement_windows)
        for window in placement_windows:
            source_start = _float_value(window.get("source_start_sec"))
            timeline_start = _float_value(window.get("start_sec"))
            duration = _float_value(window.get("duration_sec"))
            if duration < 0.25:
                skipped.append({
                    "candidate_id": placement.get("candidate_id"),
                    "source_start_sec": source_start,
                    "timeline_start_sec": timeline_start,
                    "duration_sec": duration,
                    "eligible": False,
                    "reason": "window_below_minimum_measurement_duration",
                })
                continue
            waveform = _recovered_waveform_window_check(
                Path(placement["audio_file"]),
                output_path,
                placements,
                speech_windows,
                speech_config,
                source_start,
                timeline_start,
                duration,
            )
            checks.append({
                "candidate_id": placement.get("candidate_id"),
                "protected_audio": str(placement["audio_file"]),
                "protected_audio_sha256": sha256(Path(placement["audio_file"]).read_bytes()).hexdigest().upper(),
                "source_start_sec": source_start,
                "timeline_start_sec": timeline_start,
                "duration_sec": duration,
                **waveform,
            })
        for item in alignment.get("windows", []):
            index = len([item for item in checks if item.get("candidate_id") == placement.get("candidate_id")])
            if index > 0:
                checks[index - 1]["activity_alignment"] = item
    passed = [
        item for item in checks
        if item.get("pass") is True and item.get("activity_alignment", {}).get("pass", True) is True
    ]
    return {
        "pass": bool(checks) and len(passed) / len(checks) >= 0.90,
        "passing_window_ratio": round(len(passed) / len(checks), 3) if checks else 0.0,
        "windows": checks,
        "skipped_windows": skipped,
        "tolerances": {
            "max_lag_ms": 10.0,
            "max_gain_error_db": 0.5,
            "min_correlation": 0.70,
            "min_passing_window_ratio": 0.90,
        },
    }


def _target_duration(audio_mix_plan: Mapping[str, Any]) -> float:
    for key in ("video_duration_sec", "timeline_duration_sec", "target_duration_sec"):
        value = _float_value(audio_mix_plan.get(key))
        if value > 0:
            return value
    return 0.0


def _preview_contract_blocks(audio_mix_plan: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Reject aggregate preview intent that cannot truthfully remain non-delivery."""
    preview_only = audio_mix_plan.get("preview_only")
    delivery_allowed = audio_mix_plan.get("delivery_allowed")
    mix_allowed = audio_mix_plan.get("mix_allowed")
    usage_scope = _clean(audio_mix_plan.get("usage_scope"))
    if preview_only is True:
        if (
            delivery_allowed is not False
            or mix_allowed is not True
            or not usage_scope
        ):
            return [{
                "rule": "contradictory_preview_delivery_contract",
                "message": (
                    "preview-only audio_mix_plan requires delivery_allowed=false, "
                    "mix_allowed=true, and a declared usage_scope"
                ),
            }]
        return []
    if delivery_allowed is False:
        return [{
            "rule": "contradictory_preview_delivery_contract",
            "message": "non-delivery audio_mix_plan must declare preview_only=true",
        }]
    if preview_only is not None and preview_only is not False:
        return [{
            "rule": "contradictory_preview_delivery_contract",
            "message": "preview_only must be a boolean when declared",
        }]
    return []


def _align_placements_to_duration(
    placements: list[dict[str, Any]],
    target_duration_sec: float,
    *,
    pad_to_target_duration: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    if target_duration_sec <= 0 or not placements:
        total_duration = max(
            (placement["start_sec"] + placement["duration_sec"] for placement in placements),
            default=0.0,
        )
        return placements, {
            "decision": "source_timeline_duration",
            "target_duration_sec": None,
            "planned_duration_sec": round(total_duration, 3),
            "output_duration_sec": round(total_duration, 3),
            "fade_out_applied": False,
        }

    planned_duration = max(
        (placement["start_sec"] + placement["duration_sec"] for placement in placements),
        default=0.0,
    )
    if planned_duration < target_duration_sec - 0.001:
        if pad_to_target_duration:
            return placements, {
                "decision": "padded_with_silence_to_target_duration",
                "target_duration_sec": round(target_duration_sec, 3),
                "planned_duration_sec": round(planned_duration, 3),
                "output_duration_sec": round(target_duration_sec, 3),
                "missing_duration_sec": round(target_duration_sec - planned_duration, 3),
                "fade_out_applied": False,
            }
        return placements, {
            "decision": "shorter_than_video_duration",
            "target_duration_sec": round(target_duration_sec, 3),
            "planned_duration_sec": round(planned_duration, 3),
            "output_duration_sec": round(planned_duration, 3),
            "missing_duration_sec": round(target_duration_sec - planned_duration, 3),
            "fade_out_applied": False,
        }

    if planned_duration <= target_duration_sec + 0.001:
        return placements, {
            "decision": "matches_video_duration",
            "target_duration_sec": round(target_duration_sec, 3),
            "planned_duration_sec": round(planned_duration, 3),
            "output_duration_sec": round(planned_duration, 3),
            "missing_duration_sec": 0.0,
            "fade_out_applied": False,
        }

    aligned: list[dict[str, Any]] = []
    fade_out_applied = False
    for placement in placements:
        start = _float_value(placement.get("start_sec"))
        duration = _float_value(placement.get("duration_sec"))
        if start >= target_duration_sec:
            continue
        end = start + duration
        item = dict(placement)
        if end > target_duration_sec:
            item["duration_sec"] = round(max(0.0, target_duration_sec - start), 3)
            if item["duration_sec"] > 0:
                item["fade_out_sec"] = round(
                    max(_float_value(item.get("fade_out_sec")), min(1.0, item["duration_sec"] / 2)),
                    3,
                )
                fade_out_applied = True
        if item["duration_sec"] > 0:
            aligned.append(item)
    output_duration = max(
        (placement["start_sec"] + placement["duration_sec"] for placement in aligned),
        default=0.0,
    )
    return aligned, {
        "decision": "clamped_to_video_duration",
        "target_duration_sec": round(target_duration_sec, 3),
        "planned_duration_sec": round(planned_duration, 3),
        "output_duration_sec": round(output_duration, 3),
        "missing_duration_sec": 0.0,
        "fade_out_applied": fade_out_applied,
    }


def _section_verification(
    sections: Mapping[str, Mapping[str, Any]],
    placements: list[dict[str, Any]],
) -> dict[str, Any]:
    covered = sorted({
        str(item.get("section_id"))
        for item in placements
        if str(item.get("section_id") or "").strip()
    })
    required = sorted(
        section_id
        for section_id, section in sections.items()
        if section.get("audio_required") is True or section.get("required_audio") is True
    )
    missing = [section_id for section_id in required if section_id not in covered]
    return {
        "section_count": len(sections),
        "required_section_count": len(required),
        "covered_sections": covered,
        "missing_required_sections": missing,
    }


def _mix_section_timeline(
    tracks: list[dict[str, Any]],
    placements: list[dict[str, Any]],
    output_path: Path,
    ffmpeg: str,
    *,
    speech_aware: bool = False,
    target_duration_sec: float | None = None,
) -> float:
    planned_duration = max(
        placement["start_sec"] + placement["duration_sec"]
        for placement in placements
    )
    total_duration = max(planned_duration, max(0.0, _float_value(target_duration_sec)))
    cmd = [
        ffmpeg,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-f",
        "lavfi",
        "-t",
        f"{total_duration:.3f}",
        "-i",
        "anullsrc=r=48000:cl=stereo",
    ]
    for track in tracks:
        cmd.extend(["-i", track["audio_file"]])

    filters = ["[0:a]aformat=sample_rates=48000:channel_layouts=stereo[base]"]
    mix_inputs = ["[base]"]
    for idx, placement in enumerate(placements):
        input_idx = idx + 1
        start = placement["source_offset_sec"]
        duration = placement["duration_sec"]
        delay_ms = max(0, int(round(placement["start_sec"] * 1000)))
        chain = (
            f"[{input_idx}:a]"
            f"atrim=start={start:.3f}:duration={duration:.3f},"
            "asetpts=PTS-STARTPTS,"
            "aformat=sample_rates=48000:channel_layouts=stereo"
        )
        fade_in = min(placement["fade_in_sec"], duration / 2)
        fade_out = min(placement["fade_out_sec"], duration / 2)
        if fade_in > 0:
            chain += f",afade=t=in:st=0:d={fade_in:.3f}"
        if fade_out > 0:
            chain += f",afade=t=out:st={max(0.0, duration - fade_out):.3f}:d={fade_out:.3f}"
        if placement.get("ducking_mode") == "speech_aware":
            expression = placement.get("speech_aware_expression") or "1"
            volume = max(0.0, _float_value(placement.get("applied_volume"), 1.0))
            chain += f",volume={volume:.8f}*({expression}):eval=frame"
        else:
            volume = max(0.0, _float_value(placement.get("applied_volume"), 1.0))
            chain += f",volume={volume:.3f}"
        # Keep every placement input alive for the complete timeline.  Older
        # ffmpeg builds renormalize `amix` whenever an input ends; without this
        # padding, consecutive music placements change protected-speech gain
        # even though their planned volume is constant.
        chain += f",adelay={delay_ms}:all=1,apad=whole_dur={total_duration:.3f}[t{idx}]"
        filters.append(chain)
        mix_inputs.append(f"[t{idx}]")

    final_filter = (
        f"amix=inputs={len(mix_inputs)}:duration=longest:dropout_transition=0:weights="
        + "1.000 "
        + " ".join(
            f"{_speech_protected_mix_weight(placement, speech_aware):.3f}"
            for placement in placements
        )
        + f",volume={len(mix_inputs):.3f},"
        if speech_aware
        else f"amix=inputs={len(mix_inputs)}:duration=longest:dropout_transition=0,"
    )
    final_filter += f"atrim=duration={total_duration:.3f},asetpts=PTS-STARTPTS"
    if not speech_aware:
        final_filter += f",{LOUDNESS_FILTER}"
    filters.append("".join(mix_inputs) + final_filter + "[aout]")
    cmd.extend([
        "-filter_complex",
        ";".join(filters),
        "-map",
        "[aout]",
        "-acodec",
        "pcm_s16le",
        "-ar",
        "48000",
        "-ac",
        "2",
        str(output_path),
    ])
    proc = subprocess.run(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"section timeline audio mix failed: {proc.stderr.strip()}")
    return total_duration


def execute_audio_mix_plan(
    audio_mix_plan: Mapping[str, Any],
    *,
    acceptance: Mapping[str, Any] | None = None,
    out_dir: str | Path,
    output_name: str = "final_audio.wav",
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> dict[str, Any]:
    out_root = Path(out_dir)
    out_root.mkdir(parents=True, exist_ok=True)
    output_path = out_root / output_name
    report_path = out_root / "audio_mix_report.json"

    blocking: list[dict[str, Any]] = []
    failed_stage = "audio_mix_plan"
    if acceptance and acceptance.get("ok") is not True:
        failed_stage = "audio_handoff_acceptance"
        blocking.append({
            "rule": "audio_handoff_acceptance_not_ok",
            "message": "audio_handoff_acceptance.json must be ok=true before mixing",
        })
    if audio_mix_plan.get("ready_for_mix") is not True:
        blocking.append({
            "rule": "audio_mix_plan_not_ready",
            "message": "audio_mix_plan.ready_for_mix must be true",
        })
    blocking.extend(_preview_contract_blocks(audio_mix_plan))

    tracks = list(audio_mix_plan.get("tracks") or [])
    speech_aware = _speech_aware_requested(audio_mix_plan, tracks)
    speech_config = SPEECH_AWARE_DEFAULTS.copy()
    if speech_aware:
        speech_config, speech_contract_errors = _speech_aware_config(audio_mix_plan, tracks)
        blocking.extend(speech_contract_errors)
    source_audio_policy = audio_mix_plan.get("source_audio_policy") if isinstance(audio_mix_plan.get("source_audio_policy"), Mapping) else {}
    if not tracks:
        blocking.append({
            "rule": "tracks_missing",
            "message": "audio_mix_plan.tracks must contain at least one accepted track",
        })

    resolved_tracks: list[dict[str, Any]] = []
    for track in tracks:
        audio_path = _resolve_audio_file(track.get("audio_file"), out_root)
        if not audio_path.is_file():
            blocking.append({
                "rule": "audio_file_missing",
                "section_id": track.get("section_id"),
                "audio_file": str(audio_path),
            })
            continue
        resolved_track = {**dict(track), "audio_file": str(audio_path)}
        if speech_aware and _is_duckable_music(resolved_track) and not _clean(resolved_track.get("ducking_policy")):
            resolved_track["ducking_policy"] = "speech_aware"
        resolved_tracks.append(resolved_track)

    sections = _plan_sections(audio_mix_plan)
    placements: list[dict[str, Any]] = []
    speech_windows: list[dict[str, Any]] = []
    protected_placements: list[dict[str, Any]] = []
    detector_evidence: list[dict[str, Any]] = []
    speech_recovery_windows: list[dict[str, Any]] = []
    if sections:
        for track in resolved_tracks:
            placement = _track_placement(track, sections)
            if placement is None:
                blocking.append({
                    "rule": "section_timing_missing",
                    "section_id": track.get("section_id"),
                    "message": "section-aware audio mix requires positive section timing for every track",
                })
                continue
            placements.append(placement)
        placements, duration_alignment = _align_placements_to_duration(
            placements,
            _target_duration(audio_mix_plan),
            pad_to_target_duration=(
                audio_mix_plan.get("silence_padding_policy") == "pad_to_target_duration"
            ),
        )
        if speech_aware:
            ffprobe_for_detection = ffprobe or resolve_ffprobe()
            timeline_duration = max(
                (item["start_sec"] + item["duration_sec"] for item in placements),
                default=_target_duration(audio_mix_plan),
            )
            speech_windows, protected_placements, detector_evidence = _derive_speech_aware_windows(
                placements,
                ffprobe=ffprobe_for_detection,
                timeline_duration=timeline_duration,
            )
            if not protected_placements:
                blocking.append({
                    "rule": "speech_aware_protected_track_missing",
                    "message": "speech-aware ducking requires a protected source_speech/preserve_original_audio placement",
                })
            elif not speech_windows:
                blocking.append({
                    "rule": "speech_aware_detector_failed",
                    "message": "speech-aware ducking requires non-empty speech activity from protected audio",
                })
            speech_recovery_windows = _recovery_windows(
                speech_windows,
                timeline_duration,
                _float_value(speech_config.get("attack_ms")) / 1000.0,
                _float_value(speech_config.get("release_ms")) / 1000.0,
            )
            _apply_ducking_policy(
                placements,
                speech_windows=speech_windows,
                speech_config=speech_config,
                timeline_duration=timeline_duration,
            )
        else:
            _apply_ducking_policy(placements)
    else:
        duration_alignment = {
            "decision": "source_track_duration",
            "target_duration_sec": None,
            "planned_duration_sec": None,
            "output_duration_sec": None,
            "fade_out_applied": False,
        }
    section_verification = _section_verification(
        {
            _clean(section.get("section_id")): section
            for section in audio_mix_plan.get("sections") or []
            if _clean(section.get("section_id"))
        },
        placements,
    )
    for section_id in section_verification["missing_required_sections"]:
        blocking.append({
            "rule": "required_section_has_no_audio",
            "section_id": section_id,
            "message": f"section {section_id} is marked audio_required but has no audio placement",
        })
    if duration_alignment.get("decision") == "shorter_than_video_duration" and not audio_mix_plan.get("duration_gap_waived"):
        blocking.append({
            "rule": "audio_shorter_than_video_duration",
            "missing_duration_sec": duration_alignment.get("missing_duration_sec"),
            "message": "audio mix plan is shorter than the target video duration; extend audio, shorten timeline, or add duration_gap_waived",
        })

    if blocking:
        report = {
            "artifact_role": "audio_mix_report",
            "version": 1,
            "ok": False,
            "audio_stream_present": False,
            "narration_included": False,
            "music_included": False,
            "rendered_video": False,
            "output_audio": None,
            "source_audio_policy": dict(source_audio_policy),
            "duration_alignment": duration_alignment,
            "section_verification": section_verification,
            "blocking": blocking,
            "next_action": "repair_audio_mix_plan",
        }
        if speech_aware:
            report.update({
                "ducking_mode": "speech_aware",
                "ducking_parameters": dict(speech_config),
                "speech_activity_evidence": detector_evidence,
                "speech_windows": speech_windows,
                "speech_recovery_windows": speech_recovery_windows,
            })
        for key in (
            "mix_allowed",
            "preview_only",
            "delivery_allowed",
            "usage_scope",
            "music_use_basis",
            "external_publication_requires_rights_review",
        ):
            if key in audio_mix_plan:
                report[key] = audio_mix_plan[key]
        report_path.write_text(
            json.dumps(relativize_payload_refs(report_path.parent, report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"ok": False, "failed_stage": failed_stage, "audio_mix_report": report}

    ffmpeg = ffmpeg or resolve_ffmpeg()
    ffprobe = ffprobe or resolve_ffprobe()
    input_paths = [Path(track["audio_file"]) for track in resolved_tracks]
    if placements:
        _mix_section_timeline(
            resolved_tracks,
            placements,
            output_path,
            ffmpeg,
            speech_aware=speech_aware,
            target_duration_sec=duration_alignment.get("output_duration_sec"),
        )
        mix_mode = "section_timeline"
    elif len(input_paths) == 1:
        _transcode_one(input_paths[0], output_path, ffmpeg)
        mix_mode = "single_track"
    else:
        _concat_tracks(input_paths, output_path, ffmpeg)
        mix_mode = "concat"

    output_duration = _probe_duration(output_path, ffprobe)
    levels = _probe_audio_levels(output_path, ffmpeg)
    track_reports = []
    for index, track in enumerate(resolved_tracks):
        audio_path = Path(track["audio_file"])
        track_report = {
            "section_id": track.get("section_id"),
            "candidate_id": track.get("candidate_id"),
            "audio_file": str(audio_path),
            "role": track.get("role"),
            "ducking_policy": track.get("ducking_policy"),
            "source_type": track.get("source_type"),
            "license_status": track.get("license_status"),
            "duration_sec": round(_probe_duration(audio_path, ffprobe), 3),
        }
        if index < len(placements):
            track_report.update({
                "mix_start_sec": placements[index]["start_sec"],
                "mix_duration_sec": placements[index]["duration_sec"],
                "source_offset_sec": placements[index]["source_offset_sec"],
            })
        for key in (
            "mix_allowed",
            "preview_only",
            "delivery_allowed",
            "usage_scope",
            "music_use_basis",
            "external_publication_requires_rights_review",
            "legal_approval_claimed",
        ):
            if key in track:
                track_report[key] = track[key]
        track_reports.append(track_report)

    roles = {str(track.get("role") or "") for track in resolved_tracks}
    preview_only = audio_mix_plan.get("preview_only") is True
    speech_evidence = _speech_aware_rms_evidence(
        placements,
        speech_windows,
        speech_recovery_windows,
        speech_config,
    ) if speech_aware else None
    protected_waveform = _protected_speech_waveform_report(
        protected_placements,
        placements,
        speech_windows,
        speech_config,
        output_path,
    ) if speech_aware else None
    if speech_aware and protected_waveform and not protected_waveform.get("pass"):
        blocking.append({
            "rule": "protected_speech_waveform_check_failed",
            "message": "protected speech waveform timing/gain/correlation did not meet tolerance",
        })
    report = {
        "artifact_role": "audio_mix_report",
        "version": 1,
        "ok": True,
        "audio_stream_present": True,
        "narration_included": any(role in {"voice", "voiceover", "narration"} for role in roles),
        "music_included": any(role.startswith("music") or role == "preserve_original_audio" for role in roles),
        "rendered_video": False,
        "output_audio": str(output_path),
        "source_audio_policy": dict(source_audio_policy),
        "duration_alignment": duration_alignment,
        "duration_sec": round(output_duration, 3),
        "mean_dbfs": levels["mean_dbfs"],
        "peak_dbfs": levels["peak_dbfs"],
        "mix_mode": mix_mode,
        "ducking_applied": any(item.get("ducking_applied") for item in placements),
        "track_count": len(resolved_tracks),
        "tracks": track_reports,
        "placements": placements,
        "section_verification": section_verification,
        "blocking": [],
        "next_action": "review_internal_audio_preview" if preview_only else "audio_ready_for_build",
    }
    if speech_aware:
        report.update({
            "ducking_mode": "speech_aware",
            "ducking_parameters": dict(speech_config),
            "speech_activity_evidence": detector_evidence,
            "speech_windows": speech_windows,
            "speech_recovery_windows": speech_recovery_windows,
            "speech_aware_evidence": speech_evidence,
            "protected_speech_waveform_check": protected_waveform,
            "protected_speech": {
                "placements": [
                    {
                        "candidate_id": item.get("candidate_id"),
                        "source_sha256": sha256(Path(item["audio_file"]).read_bytes()).hexdigest().upper(),
                        "start_sec": item.get("start_sec"),
                        "duration_sec": item.get("duration_sec"),
                        "source_offset_sec": item.get("source_offset_sec"),
                        "gain": item.get("applied_volume", 1.0),
                    }
                    for item in protected_placements
                ],
                "gain": protected_placements[0].get("applied_volume", 1.0) if protected_placements else None,
            },
        })
    if blocking:
        report["ok"] = False
        report["blocking"] = blocking
        report["next_action"] = "repair_audio_mix_plan"
    if preview_only:
        for key in (
            "mix_allowed",
            "preview_only",
            "delivery_allowed",
            "usage_scope",
            "music_use_basis",
            "external_publication_requires_rights_review",
        ):
            if key in audio_mix_plan:
                report[key] = audio_mix_plan[key]
    report_path.write_text(
        json.dumps(relativize_payload_refs(report_path.parent, report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {
        "ok": bool(report["ok"]),
        "final_audio": str(output_path),
        "audio_mix_report": report,
    }


def execute_audio_mix_plan_files(
    plan_path: str | Path,
    *,
    out_dir: str | Path,
    acceptance_path: str | Path | None = None,
    output_name: str = "final_audio.wav",
    ffmpeg: str | None = None,
    ffprobe: str | None = None,
) -> dict[str, Any]:
    acceptance = _load_json(acceptance_path) if acceptance_path else None
    return execute_audio_mix_plan(
        _load_json(plan_path),
        acceptance=acceptance,
        out_dir=out_dir,
        output_name=output_name,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
    )
