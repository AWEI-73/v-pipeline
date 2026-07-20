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
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Mapping

from .caption_audit import parse_srt
from .keyframe_grid import probe_duration
from .platform_tools import resolve_ffmpeg
from .reviewer_registry import build_reviewer_write_contract


VERSION = 2
DEFAULT_INTERVAL_SEC = 0.5
DEFAULT_WALL_DURATION_SEC = 30.0
DEFAULT_COLUMNS = 10
DEFAULT_CELL_WIDTH = 320
DEFAULT_CELL_HEIGHT = 180
REVIEW_SUBJECT_TYPES = {"current_candidate", "reference_film"}
TEXT_AUTHORITIES = {"asr_draft", "owner_approved", "reference_transcript", "ocr_inferred"}
EVIDENCE_MANIFEST_ROLE = "editorial_evidence_manifest"
EVIDENCE_MANIFEST_VERSION = 1
TIMELINE_REVIEW_CAPABILITY_ID = "cap.verify.uniform-timeline-review.v1"
SHA256_HASH_METHOD = "sha256_file_bytes_v1"
_SHA256_RE = re.compile(r"^[0-9a-fA-F]{64}$")


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _decision_context(
    path: str | Path | None,
    *,
    expected_subject_sha256: str,
) -> dict[str, Any]:
    if path is None:
        return {
            "status": "unbound",
            "reason": "decision_context_not_supplied",
        }
    context_path = Path(path)
    payload = _load_json(context_path)
    if not isinstance(payload, Mapping):
        raise ValueError("timeline_review_context_contract_mismatch")
    artifact_role = payload.get("artifact_role")
    if not isinstance(artifact_role, str) or not artifact_role.strip():
        raise ValueError("timeline_review_context_artifact_role_missing")
    locked_truth = payload.get("locked_truth")
    if not isinstance(locked_truth, Mapping):
        raise ValueError("timeline_review_context_locked_truth_missing")
    subject_binding = payload.get("subject_binding")
    binding_source = "subject_binding.subject_sha256"
    if isinstance(subject_binding, Mapping):
        bound_subject_sha256 = subject_binding.get("subject_sha256")
    else:
        input_binding = payload.get("input")
        binding_source = "input.sha256"
        bound_subject_sha256 = input_binding.get("sha256") if isinstance(input_binding, Mapping) else None
    if not isinstance(bound_subject_sha256, str) or not _SHA256_RE.fullmatch(bound_subject_sha256):
        raise ValueError("timeline_review_context_subject_binding_missing")
    if bound_subject_sha256.lower() != expected_subject_sha256.lower():
        raise ValueError("timeline_review_context_subject_mismatch")
    bound: dict[str, Any] = {
        "status": "bound",
        "source": {
            "path": str(path),
            "artifact_role": artifact_role,
            "sha256": _sha256(context_path),
        },
        "subject_binding": {
            "status": "verified",
            "mode": "exact_subject_sha256",
            "subject_sha256": expected_subject_sha256,
            "source_field": binding_source,
        },
        "locked_truth": dict(locked_truth),
    }
    for key in ("finishing_contract", "audio_policy"):
        value = payload.get(key)
        if value is not None:
            if not isinstance(value, Mapping):
                raise ValueError(f"timeline_review_context_{key}_invalid")
            bound[key] = dict(value)
    return bound


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
    expected_candidate_sha256: str | None = None,
) -> dict[str, Any]:
    if path is None:
        return {
            "status": "not_supplied",
            "candidate_binding_status": "unbound_not_supplied",
            "audio_stream_fingerprint": _unbound_fingerprint("soundtrack_probe_not_supplied"),
            "audio_probe_artifact_fingerprint": _unbound_fingerprint("soundtrack_probe_not_supplied"),
            "limitations": ["No soundtrack probe was bound to this review packet."],
        }
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
    probe_source_binding = payload.get("source_binding")
    probe_source_sha256 = (
        probe_source_binding.get("sha256")
        if isinstance(probe_source_binding, Mapping)
        else None
    )
    probe_hash_method = (
        probe_source_binding.get("hash_method")
        if isinstance(probe_source_binding, Mapping)
        else None
    )
    if (
        not isinstance(probe_source_sha256, str)
        or not _SHA256_RE.fullmatch(probe_source_sha256)
        or probe_hash_method != SHA256_HASH_METHOD
    ):
        candidate_binding_status = "unbound_probe_source_binding_missing"
    elif (
        expected_candidate_sha256 is None
        or probe_source_sha256.lower() != expected_candidate_sha256.lower()
    ):
        candidate_binding_status = "unbound_probe_source_mismatch"
    else:
        candidate_binding_status = "bound_exact_candidate"
    return {
        "status": "bound",
        "candidate_binding_status": candidate_binding_status,
        "probe_source_binding": dict(probe_source_binding) if isinstance(probe_source_binding, Mapping) else None,
        "artifact_path": str(probe_path),
        "sha256": _sha256(probe_path),
        "audio_stream_fingerprint": _unbound_fingerprint(
            "soundtrack_probe_json_is_not_audio_stream_fingerprint"
        ),
        "audio_probe_artifact_fingerprint": {
            "status": "bound",
            "sha256": _sha256(probe_path),
            "hash_method": SHA256_HASH_METHOD,
        },
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
            "subtitle_fingerprint": _unbound_fingerprint("srt_not_supplied"),
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
        "subtitle_fingerprint": {"status": "bound", "sha256": _sha256(srt_path), "text_authority": authority},
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
        "editorial_evidence_manifest.json",
        "reviewer_write_contract.json",
        "editorial_review.template.json",
        "timeline_reviewer_findings.template.json",
        "timeline_crop_request.template.json",
    }
    if any((out / name).exists() for name in reserved):
        raise FileExistsError("timeline_review_output_exists")
    walls = out / "walls"
    if walls.exists() and any(walls.glob("wall_*s_*.jpg")):
        raise FileExistsError("timeline_review_output_exists")


def _unbound_fingerprint(reason: str) -> dict[str, str]:
    return {"status": "unbound", "reason": reason}


def build_evidence_manifest(
    video_path: str | Path,
    *,
    review_subject_type: str,
    source_sha256: str,
    duration_sec: float,
    index: Mapping[str, Any],
    index_path: Path,
    root: Path,
    audio_context: Mapping[str, Any],
    subtitle_context: Mapping[str, Any],
    parent_manifest: Mapping[str, Any] | None = None,
    invalidated_by: list[Mapping[str, Any] | str] | None = None,
) -> dict[str, Any]:
    """Build the immutable evidence manifest carried by a timeline packet."""
    subject = {
        "path": str(video_path),
        "artifact_role": "timeline_review_subject",
        "sha256": source_sha256,
        "hash_method": SHA256_HASH_METHOD,
        "duration_sec": round(float(duration_sec), 3),
        "media_role": review_subject_type,
    }
    source_binding = {
        "subject_sha256": source_sha256,
        "subject_path": str(video_path),
        "hash_method": SHA256_HASH_METHOD,
    }
    evidence_items: list[dict[str, Any]] = []
    evidence_items.append({
        "evidence_id": "timeline_wall_index",
        "kind": "wall_index",
        "path": index_path.relative_to(root).as_posix(),
        "sha256": _sha256(index_path),
        "generator_capability": TIMELINE_REVIEW_CAPABILITY_ID,
        "covered_timeline_window": {"start_sec": 0.0, "end_sec": round(float(duration_sec), 3)},
        "source_binding": source_binding,
        "limitations": list(index.get("limitations") or []),
    })
    for wall in index.get("walls") or []:
        wall_path = root / str(wall["file"])
        evidence_items.append({
            "evidence_id": wall["wall_id"],
            "kind": "timeline_wall",
            "path": wall_path.relative_to(root).as_posix(),
            "sha256": wall.get("sha256") or _sha256(wall_path),
            "generator_capability": TIMELINE_REVIEW_CAPABILITY_ID,
            "covered_timeline_window": {
                "start_sec": wall.get("start_sec"),
                "end_sec": wall.get("end_sec"),
            },
            "source_binding": source_binding,
            "limitations": [
                "Wall cells support story navigation, not exact identity or technical proof."
            ],
        })
    if audio_context.get("candidate_binding_status") == "bound_exact_candidate":
        evidence_items.append({
            "evidence_id": "soundtrack_probe",
            "kind": "audio_probe",
            "path": str(audio_context.get("artifact_path")),
            "sha256": audio_context.get("sha256"),
            "generator_capability": "cap.soundtrack-arranger.soundtrack-probe.v1",
            "covered_timeline_window": {"start_sec": 0.0, "end_sec": round(float(duration_sec), 3)},
            "source_binding": source_binding,
            "candidate_binding_status": audio_context.get("candidate_binding_status"),
            "limitations": list(audio_context.get("limitations") or []),
        })
    if subtitle_context.get("status") == "bound":
        evidence_items.append({
            "evidence_id": "subtitle_binding",
            "kind": "subtitle_binding",
            "path": str(subtitle_context.get("artifact_path")),
            "sha256": subtitle_context.get("sha256"),
            "generator_capability": "cap.verify.uniform-timeline-review.v1",
            "covered_timeline_window": {
                "start_sec": subtitle_context.get("coverage_start_sec") or 0.0,
                "end_sec": subtitle_context.get("coverage_end_sec") or round(float(duration_sec), 3),
            },
            "source_binding": source_binding,
            "limitations": list(subtitle_context.get("limitations") or []),
        })
    return {
        "artifact_role": EVIDENCE_MANIFEST_ROLE,
        "version": EVIDENCE_MANIFEST_VERSION,
        "subject": subject,
        "picture_stream_fingerprint": _unbound_fingerprint("picture_stream_probe_not_supplied"),
        "audio_stream_fingerprint": audio_context.get("audio_stream_fingerprint") or _unbound_fingerprint("soundtrack_probe_not_supplied"),
        "audio_probe_artifact_fingerprint": audio_context.get("audio_probe_artifact_fingerprint") or _unbound_fingerprint("soundtrack_probe_not_supplied"),
        "subtitle_fingerprint": subtitle_context.get("subtitle_fingerprint") or _unbound_fingerprint("srt_not_supplied"),
        "evidence_items": evidence_items,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "generator_version": "timeline_review_packet/2",
        "reuse_policy": {
            "mode": "bounded_manifest_reuse",
            "identical_picture_audio_change": "reuse timeline wall and wall_index evidence; re-probe audio",
            "identical_picture_audio_subtitle_change": "reuse walls and audio; regenerate subtitle binding evidence",
            "identical_picture_audio_and_subtitle_change": "reuse visual evidence; regenerate audio and subtitle evidence",
            "bounded_picture_change": "invalidate only intersecting wall windows and regenerate the wall index when required",
            "unknown_or_mismatched_subject": "fail_closed",
            "required_record": "record reused, regenerated, and invalidated evidence IDs in the child manifest",
        },
        "invalidated_by": list(invalidated_by or []),
        "parent_manifest": parent_manifest,
    }


def _manifest_fingerprint(manifest: Mapping[str, Any], key: str) -> str | None:
    value = manifest.get(key)
    if not isinstance(value, Mapping) or value.get("status") != "bound":
        return None
    fingerprint = value.get("sha256") or value.get("fingerprint")
    return str(fingerprint) if isinstance(fingerprint, str) and _SHA256_RE.fullmatch(fingerprint) else None


def _validate_manifest_fingerprints(manifest: Mapping[str, Any]) -> None:
    for key in (
        "picture_stream_fingerprint",
        "audio_stream_fingerprint",
        "audio_probe_artifact_fingerprint",
        "subtitle_fingerprint",
    ):
        if key not in manifest:
            continue
        value = manifest.get(key)
        if not isinstance(value, Mapping):
            raise ValueError(f"timeline_review_reuse_{key}_invalid")
        status = value.get("status")
        if status == "bound":
            fingerprint = value.get("sha256") or value.get("fingerprint")
            if not isinstance(fingerprint, str) or not _SHA256_RE.fullmatch(fingerprint):
                raise ValueError(f"timeline_review_reuse_{key}_invalid")
        elif status == "unbound":
            if not isinstance(value.get("reason"), str) or not value.get("reason").strip():
                raise ValueError(f"timeline_review_reuse_{key}_unbound_reason_required")
        else:
            raise ValueError(f"timeline_review_reuse_{key}_invalid")


def _manifest_subject_identity(manifest: Mapping[str, Any]) -> tuple[Any, ...] | None:
    subject = manifest.get("subject")
    if not isinstance(subject, Mapping):
        return None
    required = (subject.get("path"), subject.get("artifact_role"), subject.get("media_role"), subject.get("duration_sec"))
    if any(value in (None, "") for value in required):
        return None
    return required


def _window_bounds(value: Any) -> tuple[float, float] | None:
    if isinstance(value, Mapping):
        start, end = value.get("start_sec"), value.get("end_sec")
    elif isinstance(value, (list, tuple)) and len(value) == 2:
        start, end = value
    else:
        return None
    try:
        return float(start), float(end)
    except (TypeError, ValueError):
        return None


def plan_evidence_reuse(
    previous_manifest: Mapping[str, Any],
    current_manifest: Mapping[str, Any],
    *,
    changed_picture_window: Mapping[str, Any] | list[float] | tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Plan bounded reuse from an immutable manifest without copying stale evidence."""
    if not isinstance(previous_manifest, Mapping) or not isinstance(current_manifest, Mapping):
        raise ValueError("timeline_review_reuse_manifest_invalid")
    if previous_manifest.get("artifact_role") != EVIDENCE_MANIFEST_ROLE or current_manifest.get("artifact_role") != EVIDENCE_MANIFEST_ROLE:
        raise ValueError("timeline_review_reuse_manifest_contract_mismatch")
    _validate_manifest_fingerprints(previous_manifest)
    _validate_manifest_fingerprints(current_manifest)
    if _manifest_subject_identity(previous_manifest) != _manifest_subject_identity(current_manifest):
        raise ValueError("timeline_review_reuse_subject_mismatch")
    previous_subject = previous_manifest.get("subject") or {}
    current_subject = current_manifest.get("subject") or {}
    if previous_subject.get("sha256") == current_subject.get("sha256"):
        for key in (
            "picture_stream_fingerprint",
            "audio_stream_fingerprint",
            "audio_probe_artifact_fingerprint",
            "subtitle_fingerprint",
        ):
            previous = previous_manifest.get(key)
            current = current_manifest.get(key)
            if previous != current:
                raise ValueError("timeline_review_reuse_subject_hash_mismatch")
    picture_previous = _manifest_fingerprint(previous_manifest, "picture_stream_fingerprint")
    picture_current = _manifest_fingerprint(current_manifest, "picture_stream_fingerprint")
    if not picture_previous or not picture_current:
        raise ValueError("timeline_review_reuse_picture_fingerprint_unknown")
    previous_items = previous_manifest.get("evidence_items")
    current_items = current_manifest.get("evidence_items")
    if not isinstance(previous_items, list) or not isinstance(current_items, list):
        raise ValueError("timeline_review_reuse_evidence_items_missing")
    previous_ids = [str(item.get("evidence_id")) for item in previous_items if isinstance(item, Mapping) and item.get("evidence_id")]
    current_ids = {str(item.get("evidence_id")) for item in current_items if isinstance(item, Mapping) and item.get("evidence_id")}
    audio_evidence_present = any(
        isinstance(item, Mapping) and str(item.get("kind")) in {"audio_probe", "audio_binding"}
        for item in [*previous_items, *current_items]
    )
    if audio_evidence_present and (
        _manifest_fingerprint(previous_manifest, "audio_stream_fingerprint") is None
        or _manifest_fingerprint(current_manifest, "audio_stream_fingerprint") is None
    ):
        raise ValueError("timeline_review_reuse_audio_fingerprint_unknown")
    reused: list[str] = []
    regenerated: list[str] = []
    invalidated: list[str] = []
    picture_changed = picture_previous != picture_current
    if not picture_changed:
        audio_changed = _manifest_fingerprint(previous_manifest, "audio_stream_fingerprint") != _manifest_fingerprint(current_manifest, "audio_stream_fingerprint")
        subtitle_changed = _manifest_fingerprint(previous_manifest, "subtitle_fingerprint") != _manifest_fingerprint(current_manifest, "subtitle_fingerprint")
        if audio_changed and subtitle_changed:
            if _manifest_fingerprint(previous_manifest, "audio_stream_fingerprint") is None or _manifest_fingerprint(current_manifest, "audio_stream_fingerprint") is None:
                raise ValueError("timeline_review_reuse_audio_fingerprint_unknown")
            if _manifest_fingerprint(previous_manifest, "subtitle_fingerprint") is None or _manifest_fingerprint(current_manifest, "subtitle_fingerprint") is None:
                raise ValueError("timeline_review_reuse_subtitle_fingerprint_unknown")
            regenerated_kinds = {"soundtrack_probe", "audio_binding", "subtitle_binding"}
            reused = [item_id for item_id in previous_ids if item_id in current_ids and item_id not in regenerated_kinds]
            regenerated = [item_id for item_id in current_ids if item_id in regenerated_kinds]
            reason = "identical_picture_audio_and_subtitle_change"
        elif audio_changed:
            if _manifest_fingerprint(previous_manifest, "audio_stream_fingerprint") is None or _manifest_fingerprint(current_manifest, "audio_stream_fingerprint") is None:
                raise ValueError("timeline_review_reuse_audio_fingerprint_unknown")
            reused = [item_id for item_id in previous_ids if item_id in current_ids and item_id not in {"soundtrack_probe", "audio_binding"}]
            regenerated = [item_id for item_id in current_ids if item_id in {"soundtrack_probe", "audio_binding"}]
            reason = "identical_picture_audio_only_change"
        elif subtitle_changed:
            reused = [item_id for item_id in previous_ids if item_id in current_ids and item_id not in {"subtitle_binding"}]
            regenerated = [item_id for item_id in current_ids if item_id == "subtitle_binding"]
            reason = "identical_picture_audio_subtitle_only_change"
        else:
            reused = [item_id for item_id in previous_ids if item_id in current_ids]
            reason = "identical_picture_audio_subtitle"
    else:
        bounds = _window_bounds(changed_picture_window)
        if bounds is None:
            raise ValueError("timeline_review_reuse_picture_change_window_required")
        picture_wall_invalidated = False
        for item in previous_items:
            if not isinstance(item, Mapping) or not item.get("evidence_id"):
                continue
            item_id = str(item["evidence_id"])
            item_bounds = _window_bounds(item.get("covered_timeline_window"))
            intersects = bool(item_bounds and item.get("kind") == "timeline_wall" and max(bounds[0], item_bounds[0]) < min(bounds[1], item_bounds[1]))
            if intersects:
                invalidated.append(item_id)
                picture_wall_invalidated = True
            elif item_id in current_ids:
                reused.append(item_id)
        if picture_wall_invalidated and "timeline_wall_index" in previous_ids:
            invalidated.append("timeline_wall_index")
        regenerated = [item_id for item_id in current_ids if item_id in invalidated]
        reason = "bounded_picture_change"
    return {
        "status": "reuse_planned",
        "reason": reason,
        "parent_manifest": previous_manifest.get("subject", {}).get("sha256"),
        "reused_evidence_ids": sorted(set(reused)),
        "regenerated_evidence_ids": sorted(set(regenerated)),
        "invalidated_evidence_ids": sorted(set(invalidated)),
        "fail_closed_on_unknown": True,
    }


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
    context_path: str | Path | None = None,
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
    source_sha = _sha256(video)
    decision_context = _decision_context(
        context_path,
        expected_subject_sha256=source_sha,
    )
    reviewer_write_contract = build_reviewer_write_contract()
    # Validate bound context before the expensive wall render so a bad track
    # cannot leave a plausible-looking partial evidence root behind.
    audio_context = _audio_context(
        soundtrack_probe_path,
        expected_duration_sec=duration,
        expected_candidate_sha256=source_sha,
    )
    subtitle_context = _subtitle_context(srt_path, text_authority=text_authority)
    out.mkdir(parents=True, exist_ok=True)
    reviewer_write_contract_path = out / "reviewer_write_contract.json"
    _write_json(reviewer_write_contract_path, reviewer_write_contract)
    reviewer_write_contract_sha = _sha256(reviewer_write_contract_path)
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
    evidence_manifest = build_evidence_manifest(
        video,
        review_subject_type=review_subject_type,
        source_sha256=source_sha,
        duration_sec=duration,
        index=index,
        index_path=index_path,
        root=out,
        audio_context=audio_context,
        subtitle_context=subtitle_context,
    )
    evidence_manifest_path = out / "editorial_evidence_manifest.json"
    _write_json(evidence_manifest_path, evidence_manifest)
    evidence_manifest_sha = _sha256(evidence_manifest_path)

    packet = {
        "artifact_role": "timeline_review_packet",
        "version": VERSION,
        "status": "ready_for_agent_review",
        "review_subject": review_subject,
        "source": {
            "video_path": str(video),
            "sha256": source_sha,
            "hash_method": SHA256_HASH_METHOD,
            "duration_sec": round(duration, 3),
        },
        "subject": evidence_manifest["subject"],
        "decision_context": decision_context,
        "decision_context_ref": decision_context.get("source") or {
            "status": "unbound",
            "reason": decision_context.get("reason", "decision_context_not_supplied"),
        },
        "evidence_manifest": evidence_manifest,
        "evidence_manifest_ref": {
            "path": str(evidence_manifest_path),
            "sha256": evidence_manifest_sha,
        },
        "reviewer_write_contract_ref": {
            "path": str(reviewer_write_contract_path),
            "sha256": reviewer_write_contract_sha,
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
            "audio_binding": {
                "field": "review_tracks.audio.candidate_binding_status",
                "required_for_mix_ducking_music_claims": "bound_exact_candidate",
                "unbound_statuses": [
                    "unbound_probe_source_binding_missing",
                    "unbound_probe_source_mismatch",
                    "unbound_not_supplied",
                ],
            },
            "classification_rules": {
                "rendered_pixel_material_truth_mismatch": "objective",
                "adjacent_low_information_semantic_repeat": "structural_candidate",
            },
            "decision_lock_policy": {
                "full_context": "read_locks_before_proposing_fixes",
                "cold_start": "record_audience_visible_findings_before_lock_classification",
                "required_finding_field": "requires_reopen",
                "lock_conflict_policy": "preserve_conflict_and_require_reopen",
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
            "findings_template": str(out / "editorial_review.template.json"),
            "write_contract": str(reviewer_write_contract_path),
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
    findings_template = dict(reviewer_write_contract["minimal_valid_example"])
    findings_template.update({
        "packet_path": str(packet_path),
        "packet_sha256": packet_sha,
        "review_subject": review_subject,
        "subject": evidence_manifest["subject"],
        "binding_contract_version": 1,
        "reviewed_subject_sha256": source_sha,
        "applies_to_candidate_sha256": source_sha,
        "subject_hash_method": SHA256_HASH_METHOD,
        "evidence_manifest": evidence_manifest,
        "decision_context": decision_context,
        "decision_context_ref": packet["decision_context_ref"],
        "inspection_scope": {
            "timeline_windows": [[0.0, round(duration, 3)]],
            "wall_ids": [wall["wall_id"] for wall in index["walls"]],
        },
        "not_inspected": ["source-frame identity, continuous playback, and dedicated technical QA unless separately cited"],
    })
    crop_template = {
        "artifact_role": "timeline_crop_request",
        "version": VERSION,
        "status": "PENDING_AGENT_REVIEW",
        "packet_path": str(packet_path),
        "packet_sha256": packet_sha,
        "requests": [],
    }
    _write_json(out / "editorial_review.template.json", findings_template)
    _write_json(out / "timeline_crop_request.template.json", crop_template)
    return {**packet, "packet_path": str(packet_path), "packet_sha256": packet_sha}
