"""Execute an accepted audio_mix_plan into final_audio.wav without video render."""

from __future__ import annotations

import json
import re
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Mapping

from .asset_paths import relativize_payload_refs
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
        "start_sec": round(start, 3),
        "duration_sec": round(duration, 3),
        "source_offset_sec": round(_float_value(track.get("source_offset_sec")), 3),
        "fade_in_sec": round(max(0.0, _float_value(track.get("fade_in_sec"))), 3),
        "fade_out_sec": round(max(0.0, _float_value(track.get("fade_out_sec"))), 3),
        "role": _clean(track.get("role")),
        "ducking_policy": _clean(track.get("ducking_policy")),
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


def _apply_ducking_policy(placements: list[dict[str, Any]], ducked_volume: float = 0.28) -> None:
    protected_audio = [item for item in placements if _is_voice_or_original_audio(item)]
    for placement in placements:
        if placement.get("ducking_policy") != "duck_under_voice":
            continue
        if not _is_duckable_music(placement):
            continue
        if not any(_overlaps(placement, protected) for protected in protected_audio):
            continue
        placement["applied_volume"] = round(ducked_volume, 3)
        placement["ducking_applied"] = True


def _target_duration(audio_mix_plan: Mapping[str, Any]) -> float:
    for key in ("video_duration_sec", "timeline_duration_sec", "target_duration_sec"):
        value = _float_value(audio_mix_plan.get(key))
        if value > 0:
            return value
    return 0.0


def _align_placements_to_duration(
    placements: list[dict[str, Any]],
    target_duration_sec: float,
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
) -> float:
    total_duration = max(
        placement["start_sec"] + placement["duration_sec"]
        for placement in placements
    )
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
        volume = max(0.0, _float_value(placement.get("applied_volume"), 1.0))
        chain += f",volume={volume:.3f}"
        chain += f",adelay={delay_ms}:all=1[t{idx}]"
        filters.append(chain)
        mix_inputs.append(f"[t{idx}]")

    filters.append(
        "".join(mix_inputs)
        + f"amix=inputs={len(mix_inputs)}:duration=longest:dropout_transition=0,"
        + f"atrim=duration={total_duration:.3f},"
        + f"asetpts=PTS-STARTPTS,{LOUDNESS_FILTER}[aout]"
    )
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

    tracks = list(audio_mix_plan.get("tracks") or [])
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
        resolved_tracks.append({**dict(track), "audio_file": str(audio_path)})

    sections = _plan_sections(audio_mix_plan)
    placements: list[dict[str, Any]] = []
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
        )
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
        report_path.write_text(
            json.dumps(relativize_payload_refs(report_path.parent, report), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {"ok": False, "failed_stage": failed_stage, "audio_mix_report": report}

    ffmpeg = ffmpeg or resolve_ffmpeg()
    ffprobe = ffprobe or resolve_ffprobe()
    input_paths = [Path(track["audio_file"]) for track in resolved_tracks]
    if placements:
        _mix_section_timeline(resolved_tracks, placements, output_path, ffmpeg)
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
        track_reports.append(track_report)

    roles = {str(track.get("role") or "") for track in resolved_tracks}
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
        "next_action": "audio_ready_for_build",
    }
    report_path.write_text(
        json.dumps(relativize_payload_refs(report_path.parent, report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return {"ok": True, "final_audio": str(output_path), "audio_mix_report": report}


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
