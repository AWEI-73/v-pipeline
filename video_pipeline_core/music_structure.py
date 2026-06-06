"""music_structure.py — V3 P1 music timing artifact.

Turn detected tempo/beats into a small JSON artifact that Node 5/7/9/10 can
consume without re-running audio analysis or rereading long logs.
"""
import json
from pathlib import Path


def _fmt_mmss(seconds):
    seconds = max(0.0, float(seconds))
    total_tenths = int(round(seconds * 10))
    tenths = total_tenths % 10
    total_secs = total_tenths // 10
    mm = total_secs // 60
    ss = total_secs % 60
    return f"{mm:02d}:{ss:02d}.{tenths}"


def _density_hint(duration, beats):
    if duration <= 0:
        return "low"
    bps = max(0, len(beats) - 1) / duration
    if bps >= 2.2:
        return "high"
    if bps >= 1.0:
        return "medium"
    return "low"


def build_music_structure(tempo_bpm, beat_times, *, source_audio=None, every_n_beats=4):
    """Pure builder: tempo/beats -> normalized music_structure.json shape."""
    beats = [round(float(b), 3) for b in sorted(beat_times or [])]
    step = max(1, int(every_n_beats))
    sections = []
    for idx, start_i in enumerate(range(0, max(0, len(beats) - 1), step), 1):
        end_i = min(start_i + step, len(beats) - 1)
        start = beats[start_i]
        end = beats[end_i]
        if end <= start:
            continue
        sec_beats = beats[start_i:end_i + 1]
        dur = round(end - start, 3)
        sections.append({
            "index": idx,
            "name": f"Section {idx}",
            "description": "beat-derived music section",
            "Start_Time": _fmt_mmss(start),
            "End_Time": _fmt_mmss(end),
            "start_sec": start,
            "end_sec": end,
            "duration_sec": dur,
            "beat_count": len(sec_beats),
            "energy_score": None,
            "cut_density_hint": _density_hint(dur, sec_beats),
            "source": "beat_grid",
            "confidence": 0.6,
        })

    return {
        "music_structure_version": 1,
        "source_audio": str(source_audio) if source_audio is not None else None,
        "source": "librosa",
        "tempo_bpm": round(float(tempo_bpm), 3),
        "beat_count": len(beats),
        "beats": beats,
        "every_n_beats": step,
        "sections": sections,
    }


def write_music_structure(audio_path, out_path, *, detector=None, every_n_beats=4):
    """Detect beats and write music_structure.json. Detector is injectable for tests."""
    if detector is None:
        from .mv_cut import detect_beats  # noqa: PLC0415
        detector = detect_beats
    tempo, beats = detector(str(audio_path))
    structure = build_music_structure(
        tempo,
        beats,
        source_audio=str(audio_path),
        every_n_beats=every_n_beats,
    )
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as f:
        json.dump(structure, f, ensure_ascii=False, indent=2)
    return {"ok": True, "music_structure": str(out_path), "structure": structure}
