"""Uniform whole-timeline evidence for agent/human review of rendered videos.

The packet is a horizontal Reviewer/L5 evidence surface.  It renders a dense,
uniformly sampled wall for story navigation and binds optional soundtrack and
subtitle evidence.  It never turns semantic observations into a technical PASS,
advances the Stage cursor, or claims delivery/creative approval.
"""

from __future__ import annotations

import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Callable, Mapping

from .caption_audit import parse_srt
from .keyframe_grid import probe_duration
from .platform_tools import resolve_ffmpeg


VERSION = 2
DEFAULT_INTERVAL_SEC = 0.5
DEFAULT_WALL_DURATION_SEC = 30.0
DEFAULT_COLUMNS = 10
DEFAULT_CELL_WIDTH = 320
DEFAULT_CELL_HEIGHT = 180
REVIEW_SUBJECT_TYPES = {"current_candidate", "reference_film"}
TEXT_AUTHORITIES = {"asr_draft", "owner_approved", "reference_transcript", "ocr_inferred"}


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _sha256(path: str | Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def uniform_timestamps(duration_sec: float, interval_sec: float = DEFAULT_INTERVAL_SEC) -> list[float]:
    duration = float(duration_sec)
    interval = float(interval_sec)
    if duration <= 0:
        raise ValueError("timeline_review_invalid_duration")
    if interval <= 0:
        raise ValueError("timeline_review_invalid_interval")
    count = int(math.ceil(duration / interval - 1e-9))
    return [round(index * interval, 3) for index in range(count) if index * interval < duration]


def _wall_token(seconds: float) -> str:
    value = float(seconds)
    return str(int(value)) if value.is_integer() else str(value).replace(".", "p")


def render_uniform_timeline_walls(
    video_path: str | Path,
    walls_dir: str | Path,
    *,
    interval_sec: float,
    wall_duration_sec: float,
    expected_page_count: int,
    columns: int = DEFAULT_COLUMNS,
    cell_width: int = DEFAULT_CELL_WIDTH,
    cell_height: int = DEFAULT_CELL_HEIGHT,
    ffmpeg: str | None = None,
    **_unused: Any,
) -> list[Path]:
    """Render dense pages in one ffmpeg pass; one page covers wall_duration_sec."""
    ffmpeg = ffmpeg or resolve_ffmpeg()
    walls = Path(walls_dir)
    walls.mkdir(parents=True, exist_ok=True)
    samples_per_wall = int(round(float(wall_duration_sec) / float(interval_sec)))
    if samples_per_wall <= 0 or abs(samples_per_wall * interval_sec - wall_duration_sec) > 1e-6:
        raise ValueError("timeline_review_wall_interval_mismatch")
    rows = max(1, int(math.ceil(samples_per_wall / max(1, int(columns)))))
    fps = 1.0 / float(interval_sec)
    drawtext = (
        "drawtext=text='%{pts\\:hms}':x=6:y=h-th-6:fontsize=18:"
        "fontcolor=yellow:box=1:boxcolor=black@0.65:boxborderw=4"
    )
    vf = ",".join([
        f"fps=fps={fps:.9f}:start_time=0:round=down",
        f"scale={int(cell_width)}:{int(cell_height)}:force_original_aspect_ratio=decrease",
        f"pad={int(cell_width)}:{int(cell_height)}:(ow-iw)/2:(oh-ih)/2:color=black",
        drawtext,
        f"tile={int(columns)}x{rows}:nb_frames={samples_per_wall}:padding=2:margin=1",
    ])
    pattern = walls / f"wall_{_wall_token(wall_duration_sec)}s_%02d.jpg"
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel", "error",
        "-y",
        "-i", str(video_path),
        "-vf", vf,
        "-an",
        "-vsync", "0",
        "-q:v", "2",
        "-start_number", "1",
        str(pattern),
    ]
    result = subprocess.run(command, capture_output=True, timeout=1800)
    if result.returncode != 0:
        stderr = (result.stderr or b"").decode("utf-8", errors="replace")[-1200:]
        raise RuntimeError(f"timeline_review_wall_render_failed: {stderr}")
    paths = sorted(walls.glob(f"wall_{_wall_token(wall_duration_sec)}s_*.jpg"))
    if len(paths) != int(expected_page_count):
        raise RuntimeError(
            f"timeline_review_page_count_mismatch: expected={expected_page_count} actual={len(paths)}"
        )
    return paths


def _wall_index(
    video_path: Path,
    *,
    source_sha256: str,
    duration_sec: float,
    interval_sec: float,
    wall_duration_sec: float,
    timestamps: list[float],
    wall_paths: list[Path],
    root: Path,
) -> dict[str, Any]:
    samples_per_wall = int(round(wall_duration_sec / interval_sec))
    walls = []
    for index, path in enumerate(wall_paths):
        page_samples = timestamps[index * samples_per_wall:(index + 1) * samples_per_wall]
        start = index * wall_duration_sec
        walls.append({
            "wall_id": f"wall_{_wall_token(wall_duration_sec)}s_{index + 1:02d}",
            "file": path.relative_to(root).as_posix(),
            "start_sec": round(start, 3),
            "end_sec": round(min(duration_sec, start + wall_duration_sec), 3),
            "first_sample_sec": page_samples[0] if page_samples else None,
            "last_sample_sec": page_samples[-1] if page_samples else None,
            "sample_count": len(page_samples),
            "sha256": _sha256(path),
        })
    return {
        "artifact_role": "uniform_timeline_wall_index",
        "version": VERSION,
        "source_video": str(video_path),
        "source_sha256": source_sha256,
        "source_duration_sec": round(duration_sec, 3),
        "sampling_interval_sec": interval_sec,
        "wall_duration_sec": wall_duration_sec,
        "layout": {
            "columns": DEFAULT_COLUMNS,
            "rows": int(math.ceil(samples_per_wall / DEFAULT_COLUMNS)),
            "full_wall_sample_count": samples_per_wall,
            "cell_order": "left_to_right_then_top_to_bottom",
        },
        "sample_count": len(timestamps),
        "page_count": len(walls),
        "coverage_pass": bool(timestamps) and sum(item["sample_count"] for item in walls) == len(timestamps),
        "walls": walls,
        "limitations": [
            "The wall supports whole-timeline story navigation, not exact identity, speech, or technical-action proof.",
            "Semantic review findings remain candidates until an agent or human verifies the cited source window.",
        ],
    }


def _audio_context(
    path: str | Path | None,
    *,
    expected_duration_sec: float | None = None,
) -> dict[str, Any]:
    if path is None:
        return {"status": "not_supplied", "limitations": ["No soundtrack probe was bound to this review packet."]}
    probe_path = Path(path)
    payload = _load_json(probe_path)
    if not isinstance(payload, Mapping) or payload.get("artifact_role") != "soundtrack_probe_report":
        raise ValueError("soundtrack_probe_contract_mismatch")
    observed_duration = payload.get("duration_sec")
    duration_binding: dict[str, Any] = {"status": "not_checked"}
    if expected_duration_sec is not None:
        try:
            observed = float(observed_duration)
        except (TypeError, ValueError) as exc:
            raise ValueError("soundtrack_probe_duration_missing") from exc
        expected = float(expected_duration_sec)
        tolerance = max(0.25, expected * 0.001)
        delta = abs(observed - expected)
        duration_binding = {
            "status": "match" if delta <= tolerance else "mismatch",
            "expected_duration_sec": round(expected, 3),
            "observed_duration_sec": round(observed, 3),
            "delta_sec": round(delta, 3),
            "tolerance_sec": round(tolerance, 3),
        }
        if delta > tolerance:
            raise ValueError("soundtrack_probe_duration_mismatch")
    features = payload.get("features") if isinstance(payload.get("features"), Mapping) else {}
    beat_times = features.get("beat_times") if isinstance(features.get("beat_times"), list) else []
    return {
        "status": "bound",
        "artifact_path": str(probe_path),
        "sha256": _sha256(probe_path),
        "pass": payload.get("pass"),
        "duration_sec": payload.get("duration_sec"),
        "analysis_depth": payload.get("analysis_depth"),
        "duration_binding": duration_binding,
        "has_audio": features.get("has_audio"),
        "mean_dbfs": features.get("mean_dbfs"),
        "peak_dbfs": features.get("peak_dbfs"),
        "tempo_bpm": features.get("tempo_bpm"),
        "beat_count": len(beat_times),
        "energy_curve": features.get("energy_curve") or [],
        "vocal_analysis": features.get("vocal_analysis") or {},
        "sections": payload.get("sections") or [],
        "sampling_anchors": payload.get("sampling_anchors") or {},
        "limitations": payload.get("limitations") or [],
    }


def _review_subject_context(review_subject_type: str) -> dict[str, Any]:
    subject_type = str(review_subject_type or "").strip()
    if subject_type not in REVIEW_SUBJECT_TYPES:
        raise ValueError("timeline_review_subject_type_invalid")
    if subject_type == "reference_film":
        return {
            "type": subject_type,
            "decision_effect": "non_blocking_reference",
            "review_authority": "reference_observations_only",
            "finding_effect": "reference_observation",
            "canonical_candidate_mutation_allowed": False,
        }
    return {
        "type": subject_type,
        "decision_effect": "candidate_review",
        "review_authority": "candidate_findings_only",
        "finding_effect": "candidate_flag",
        "canonical_candidate_mutation_allowed": False,
    }


def _subtitle_context(
    path: str | Path | None,
    *,
    text_authority: str | None,
) -> dict[str, Any]:
    if path is None:
        if text_authority is not None:
            raise ValueError("timeline_review_text_authority_without_srt")
        return {
            "status": "not_supplied",
            "text_authority": None,
            "limitations": ["No SRT was bound to this review packet."],
        }
    authority = str(text_authority or "").strip()
    if not authority:
        raise ValueError("timeline_review_text_authority_required")
    if authority not in TEXT_AUTHORITIES:
        raise ValueError("timeline_review_text_authority_invalid")
    srt_path = Path(path)
    cues = parse_srt(srt_path.read_text(encoding="utf-8-sig"))
    return {
        "status": "bound",
        "text_authority": authority,
        "artifact_path": str(srt_path),
        "sha256": _sha256(srt_path),
        "cue_count": len(cues),
        "coverage_start_sec": cues[0]["start_sec"] if cues else None,
        "coverage_end_sec": cues[-1]["end_sec"] if cues else None,
        "cues": cues,
        "limitations": [
            "SRT timing/text is review context; rendered pixel equality and source-speech accuracy need their dedicated QA artifacts."
        ],
    }


def _guard_fresh_output(out: Path) -> None:
    reserved = {
        "wall_index.json",
        "timeline_review_packet.json",
        "timeline_reviewer_findings.template.json",
        "timeline_crop_request.template.json",
    }
    if any((out / name).exists() for name in reserved):
        raise FileExistsError("timeline_review_output_exists")
    walls = out / "walls"
    if walls.exists() and any(walls.glob("wall_*s_*.jpg")):
        raise FileExistsError("timeline_review_output_exists")


def build_timeline_review_packet(
    video_path: str | Path,
    out_dir: str | Path,
    *,
    review_subject_type: str,
    interval_sec: float = DEFAULT_INTERVAL_SEC,
    wall_duration_sec: float = DEFAULT_WALL_DURATION_SEC,
    soundtrack_probe_path: str | Path | None = None,
    srt_path: str | Path | None = None,
    text_authority: str | None = None,
    duration_sec: float | None = None,
    wall_renderer: Callable[..., list[Path]] | None = None,
) -> dict[str, Any]:
    video = Path(video_path)
    if not video.is_file():
        raise FileNotFoundError(video)
    out = Path(out_dir)
    _guard_fresh_output(out)
    duration = float(duration_sec if duration_sec is not None else probe_duration(video))
    review_subject = _review_subject_context(review_subject_type)
    # Validate bound context before the expensive wall render so a bad track
    # cannot leave a plausible-looking partial evidence root behind.
    audio_context = _audio_context(soundtrack_probe_path, expected_duration_sec=duration)
    subtitle_context = _subtitle_context(srt_path, text_authority=text_authority)
    out.mkdir(parents=True, exist_ok=True)
    walls_dir = out / "walls"
    walls_dir.mkdir(parents=True, exist_ok=True)
    timestamps = uniform_timestamps(duration, interval_sec)
    samples_per_wall = int(round(float(wall_duration_sec) / float(interval_sec)))
    if samples_per_wall <= 0 or abs(samples_per_wall * interval_sec - wall_duration_sec) > 1e-6:
        raise ValueError("timeline_review_wall_interval_mismatch")
    expected_pages = int(math.ceil(len(timestamps) / samples_per_wall))
    renderer = wall_renderer or render_uniform_timeline_walls
    wall_paths = [Path(path) for path in renderer(
        video,
        walls_dir,
        interval_sec=float(interval_sec),
        wall_duration_sec=float(wall_duration_sec),
        expected_page_count=expected_pages,
        columns=DEFAULT_COLUMNS,
        cell_width=DEFAULT_CELL_WIDTH,
        cell_height=DEFAULT_CELL_HEIGHT,
    )]
    source_sha = _sha256(video)
    index = _wall_index(
        video,
        source_sha256=source_sha,
        duration_sec=duration,
        interval_sec=float(interval_sec),
        wall_duration_sec=float(wall_duration_sec),
        timestamps=timestamps,
        wall_paths=wall_paths,
        root=out,
    )
    if not index["coverage_pass"] or len(wall_paths) != expected_pages:
        raise RuntimeError("timeline_review_coverage_failed")
    index_path = out / "wall_index.json"
    _write_json(index_path, index)

    packet = {
        "artifact_role": "timeline_review_packet",
        "version": VERSION,
        "status": "ready_for_agent_review",
        "review_subject": review_subject,
        "source": {
            "video_path": str(video),
            "sha256": source_sha,
            "duration_sec": round(duration, 3),
        },
        "uniform_timeline_wall": {
            "index_path": str(index_path),
            "index_sha256": _sha256(index_path),
            "sampling_interval_sec": float(interval_sec),
            "wall_duration_sec": float(wall_duration_sec),
            "sample_count": len(timestamps),
            "page_count": len(wall_paths),
            "coverage_pass": True,
            "page_paths": [str(path) for path in wall_paths],
        },
        "review_tracks": {
            "audio": audio_context,
            "subtitles": subtitle_context,
        },
        "reviewer_contract": {
            "authority": review_subject["review_authority"],
            "decision_effect": review_subject["decision_effect"],
            "required_inspection": "all_wall_pages",
            "finding_classes": ["objective", "structural_candidate", "taste"],
            "visible_evidence_precedence": [
                "rendered_pixels_over_declared_metadata_for_visible_content",
                "source_hash_binding_over_asset_id_or_filename_for_source_identity",
            ],
            "classification_rules": {
                "rendered_pixel_material_truth_mismatch": "objective",
                "adjacent_low_information_semantic_repeat": "structural_candidate",
            },
            "effect_boundary": {
                "review_output": "effect_observations_only",
                "effect_factory_handoff_allowed": False,
                "request_requires": "owner_or_integrator_verdict_and_separate_effect_contract",
                "observation_schema": [
                    "observation_id",
                    "time_range",
                    "story_role",
                    "visible_primitives",
                    "motion_evidence",
                    "confidence",
                    "evidence_refs",
                ],
            },
            "questions": [
                "Where do the visible story chapters and activity families actually change?",
                "Do adjacent shots repeat the same event, angle, or information without a visible progression reason?",
                "Do non-adjacent sections repeat the same semantic event without a declared callback reason?",
                "Do rendered pixels contradict the declared asset, chapter, activity label, or Material Map truth? If so, treat the pixels as primary visible evidence and flag the contradiction rather than rationalizing it from metadata.",
                "Do title/subtitle windows appear aligned with the visible chapter or speech context?",
                "Do soundtrack sections, energy changes, speech starts, and visible picture transitions support or contradict each other?",
                "Which time windows need source-frame crop, continuous playback, ASR, or human taste review?",
            ],
            "must_not_claim": [
                "creative approval",
                "delivery readiness",
                "identity or exact technical-term truth from wall cells alone",
                "music or subtitle correctness when the corresponding track evidence is not bound",
                "candidate failure or canonical mutation from a reference-film observation",
                "effect-factory request or handoff from a visible-effect observation alone",
            ],
        },
        "review_outputs": {
            "findings_template": str(out / "timeline_reviewer_findings.template.json"),
            "crop_request_template": str(out / "timeline_crop_request.template.json"),
        },
        "limitations": [
            "This packet makes semantic structure review cheaper; it does not replace deterministic media QA.",
            "Reviewer findings are flags until their cited coordinates are independently confirmed.",
        ],
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }
    packet_path = out / "timeline_review_packet.json"
    _write_json(packet_path, packet)
    packet_sha = _sha256(packet_path)
    findings_template = {
        "artifact_role": "timeline_reviewer_findings",
        "version": VERSION,
        "status": "PENDING_AGENT_REVIEW",
        "packet_path": str(packet_path),
        "packet_sha256": packet_sha,
        "review_subject": review_subject,
        "finding_effect": review_subject["finding_effect"],
        "reviewer": {"type": None, "id": None},
        "inspection": {"all_walls_reviewed": False, "wall_ids": []},
        "chapter_candidates": [],
        "text_windows": [],
        "effect_observations": [],
        "effect_request_status": "NOT_AUTHORIZED",
        "findings": [],
        "overall": {
            "story_structure": "UNKNOWN",
            "audio_picture_alignment": "UNKNOWN",
            "subtitle_picture_alignment": "UNKNOWN",
        },
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }
    crop_template = {
        "artifact_role": "timeline_crop_request",
        "version": VERSION,
        "status": "PENDING_AGENT_REVIEW",
        "packet_path": str(packet_path),
        "packet_sha256": packet_sha,
        "requests": [],
    }
    _write_json(out / "timeline_reviewer_findings.template.json", findings_template)
    _write_json(out / "timeline_crop_request.template.json", crop_template)
    return {**packet, "packet_path": str(packet_path), "packet_sha256": packet_sha}
