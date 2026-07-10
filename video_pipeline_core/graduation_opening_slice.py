"""Canon 67 opening-slice assembly and technical-review acceptance."""

from __future__ import annotations

import copy
import hashlib
import json
import subprocess
from pathlib import Path
from typing import Any, Mapping

from PIL import Image

from .beat_cut_composer import compose_beat_cut_montage, write_beat_cut_alignment_report
from .edit_decision_plan import write_product_artifacts
from .edit_decision_renderer import EditDecisionRenderError, render_edit_decision
from .platform_tools import resolve_ffmpeg
from .rendered_product_qa import probe_video, write_rendered_product_qa
from .title_effect_lifecycle_qa import write_title_effect_lifecycle_qa_for_run


REFERENCE_FILM_NAME = "67期結訓影片-終.mp4"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


class OpeningSliceError(ValueError):
    """Raised when the requested technical opening candidate cannot be built."""


def _write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OpeningSliceError(f"cannot load {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise OpeningSliceError(f"{path.name} must contain a JSON object")
    return payload


def _number(value: Any, field: str) -> float:
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise OpeningSliceError(f"{field} must be numeric") from exc


def _request(path: str | Path) -> dict[str, Any]:
    payload = _load_json(Path(path))
    if not str(payload.get("title") or "").strip() or not str(payload.get("subtitle") or "").strip():
        raise OpeningSliceError("request requires title and subtitle")
    poems = payload.get("poem_lines")
    if not isinstance(poems, list) or len(poems) != 3 or not all(str(line).strip() for line in poems):
        raise OpeningSliceError("request requires exactly three poem lines")
    if _number(payload.get("fps"), "request.fps") != 30:
        raise OpeningSliceError("request.fps must be 30")
    if str(payload.get("resolution") or "") != "1920x1080":
        raise OpeningSliceError("request.resolution must be 1920x1080")
    if _number(payload.get("target_duration_sec"), "request.target_duration_sec") != 44:
        raise OpeningSliceError("request.target_duration_sec must be 44")
    segments = payload.get("segments")
    expected = {"title": (0.0, 11.0), "poetry_card": (11.0, 18.0), "montage": (18.0, 44.0)}
    if not isinstance(segments, Mapping):
        raise OpeningSliceError("request.segments is required")
    for name, (start, end) in expected.items():
        segment = segments.get(name)
        if not isinstance(segment, Mapping) or _number(segment.get("start_sec"), f"segments.{name}.start_sec") != start or _number(segment.get("end_sec"), f"segments.{name}.end_sec") != end:
            raise OpeningSliceError(f"request segment {name} must be {start}-{end}")
    return payload


def _asset_id(relative_path: str) -> str:
    return "accepted_" + hashlib.sha1(relative_path.encode("utf-8")).hexdigest()[:12]


def _accepted_photo_catalog(seed_run: Path, source_root: Path) -> tuple[list[dict[str, Any]], int]:
    catalog = _load_json(seed_run / "reviewed_catalog_map.json")
    if not source_root.is_dir():
        raise OpeningSliceError("source_root does not exist or is not a directory")
    records: list[dict[str, Any]] = []
    seen: set[str] = set()
    accepted_existing = 0
    for module in catalog.get("modules") or []:
        if not isinstance(module, Mapping):
            continue
        for assignment in module.get("reviewed_assignments") or []:
            if not isinstance(assignment, Mapping) or assignment.get("human_review_status") != "accepted":
                continue
            relative = str(assignment.get("source_relative_path") or "").replace("\\", "/")
            if not relative or Path(relative).name == REFERENCE_FILM_NAME:
                continue
            source = source_root / Path(relative)
            if not source.is_file():
                continue
            accepted_existing += 1
            if source.suffix.lower() not in IMAGE_EXTENSIONS or relative in seen:
                continue
            seen.add(relative)
            records.append({
                "asset_id": _asset_id(relative),
                "source_path": str(source),
                "source_relative_path": relative,
                "accepted": True,
                "kind": "image",
                "is_photo": True,
                "human_review_status": "accepted",
                "catalog_artifact": "reviewed_catalog_map.json",
                "module_id": assignment.get("module_id") or module.get("module_id"),
            })
    return records, accepted_existing


def _audio_input(seed_run: Path) -> tuple[dict[str, Any], dict[str, Any]]:
    probe = _load_json(seed_run / "soundtrack_probe_report.json")
    beats = ((probe.get("features") or {}).get("beat_times"))
    if probe.get("pass") is not True or not isinstance(beats, list) or not beats:
        raise OpeningSliceError("seed soundtrack probe lacks accepted beat grid")
    source_value = str(probe.get("audio_file") or "")
    source = Path(source_value)
    if not source.is_absolute():
        source = Path(__file__).resolve().parents[1] / source
    if not source.is_file():
        raise OpeningSliceError("seed soundtrack audio file is unavailable")
    audio = {
        "asset_id": "bgm",
        "source_path": str(source),
        "source_relative_path": "soundtrack_probe_report.json:audio_file",
        "accepted": True,
        "kind": "audio",
        "human_review_status": "accepted_for_render_rehearsal",
        "catalog_artifact": "soundtrack_probe_report.json",
    }
    sanitized = copy.deepcopy(probe)
    sanitized["audio_file"] = "assets/bgm" + source.suffix.lower()
    sanitized["source_seed_artifact"] = "soundtrack_probe_report.json"
    return audio, sanitized


def _opening_sequence(request: Mapping[str, Any], title_asset: Mapping[str, Any], montage_assets: list[dict[str, Any]], beat_grid: list[float]) -> dict[str, Any]:
    montage = compose_beat_cut_montage(
        montage_assets,
        beat_grid,
        window_start=18.0,
        window_end=44.0,
        fps=30,
        min_distinct_assets=15,
    )
    title_clip = {
        "id": "opening_title_photo",
        "section": "title",
        "asset_id": title_asset["asset_id"],
        "source": title_asset["source_relative_path"],
        "source_path": title_asset["source_relative_path"],
        "source_relative_path": title_asset["source_relative_path"],
        "source_type": "image",
        "is_photo": True,
        "in_seconds": 0.0,
        "out_seconds": 11.0,
        "duration_sec": 11.0,
        "timeline_in_sec": 0.0,
        "timeline_out_sec": 11.0,
        "treatment": "photo_title_treatment",
        "source_lineage": {
            "asset_id": title_asset["asset_id"],
            "source_relative_path": title_asset["source_relative_path"],
            "accepted": True,
            "human_review_status": "accepted",
            "catalog_artifact": "reviewed_catalog_map.json",
        },
    }
    poetry_card = {
        "id": "opening_poetry_card",
        "section": "poetry_card",
        "source_type": "generated_background",
        "generated_background": {"color": "black"},
        "in_seconds": 0.0,
        "out_seconds": 7.0,
        "duration_sec": 7.0,
        "timeline_in_sec": 11.0,
        "timeline_out_sec": 18.0,
        "source_lineage": {"generated": True, "reason": "explicit_black_poetry_card"},
    }
    montage_clips: list[dict[str, Any]] = []
    for clip in montage["clips"]:
        item = dict(clip)
        item["source"] = item["source_relative_path"]
        item["source_path"] = item["source_relative_path"]
        item["accepted"] = True
        montage_clips.append(item)
    overlays = [
        {
            "id": "opening_title_text",
            "kind": "text",
            "text": {"main": request["title"], "subtitle": request["subtitle"]},
            "treatment": "progressive_typewriter",
            "start_sec": 0.0,
            "end_sec": 11.0,
        },
        {
            "id": "poem_line_1",
            "kind": "text",
            "text": {"main": request["poem_lines"][0]},
            "treatment": "progressive_typewriter",
            "start_sec": 11.2,
            "end_sec": 18.0,
        },
        {
            "id": "poem_line_2",
            "kind": "text",
            "text": {"main": request["poem_lines"][1]},
            "treatment": "progressive_typewriter",
            "start_sec": 13.2,
            "end_sec": 18.0,
        },
        {
            "id": "poem_line_3",
            "kind": "text",
            "text": {"main": request["poem_lines"][2]},
            "treatment": "progressive_typewriter",
            "start_sec": 15.2,
            "end_sec": 18.0,
        },
    ]
    transitions = [{"type": "hard_cut", "at_sec": 11.0}, {"type": "hard_cut", "at_sec": 18.0}]
    transitions.extend(
        {"type": "hard_cut", "at_sec": clip["timeline_out_sec"]}
        for clip in montage_clips[:-1]
    )
    return {
        "artifact_role": "opening_sequence",
        "version": 2,
        "settings": {"fps": request["fps"], "resolution": request["resolution"]},
        "clips": [title_clip, poetry_card, *montage_clips],
        "overlays": overlays,
        "transitions": transitions,
        "montage": montage,
    }


def _timeline_from_decision(decision: Mapping[str, Any], request: Mapping[str, Any]) -> dict[str, Any]:
    clips = [dict(clip) for clip in decision.get("cuts") or []]
    if not clips:
        raise OpeningSliceError("canonical edit decision contains no cuts")
    return {
        "timeline_build_version": 1,
        "settings": dict(decision.get("settings") or {}),
        "clips": clips,
        "overlays": [dict(item) for item in decision.get("overlays") or []],
        "transitions": [dict(item) for item in decision.get("transitions") or []],
    }


def _extract_frame(run: Path, timestamp: float, output_ref: str) -> None:
    completed = subprocess.run(
        [resolve_ffmpeg(), "-y", "-ss", f"{timestamp:.3f}", "-i", "final.mp4", "-frames:v", "1", output_ref],
        cwd=run,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if completed.returncode != 0 or not (run / output_ref).is_file():
        raise OpeningSliceError(f"could not extract rendered frame {output_ref}: {(completed.stderr or '')[-400:]}")


def _contact_sheet(run: Path, frame_refs: list[str]) -> str:
    images: list[Image.Image] = []
    try:
        for ref in frame_refs:
            with Image.open(run / ref) as image:
                frame = image.convert("RGB")
                frame.thumbnail((480, 270))
                images.append(frame.copy())
        if not images:
            raise OpeningSliceError("no lifecycle frames for contact sheet")
        width, height = 480, 270
        columns = 3
        rows = (len(images) + columns - 1) // columns
        sheet = Image.new("RGB", (columns * width, rows * height), "black")
        for index, image in enumerate(images):
            x = (index % columns) * width + (width - image.width) // 2
            y = (index // columns) * height + (height - image.height) // 2
            sheet.paste(image, (x, y))
        ref = "lifecycle_contact_sheet.jpg"
        sheet.save(run / ref, format="JPEG", quality=90)
        return ref
    finally:
        for image in images:
            image.close()


def _write_lifecycle_evidence(run: Path, overlays: list[dict[str, Any]], fps: int) -> dict[str, Any]:
    frames_dir = run / "lifecycle_frames"
    frames_dir.mkdir(parents=True, exist_ok=True)
    effect_records: list[dict[str, Any]] = []
    all_frames: list[str] = []
    for overlay in overlays:
        effect_id = str(overlay["id"])
        start = float(overlay["start_sec"])
        end = float(overlay["end_sec"])
        frame_times = {
            "enter": min(end - (1.0 / fps), start + max(0.2, 2.0 / fps)),
            "hold": (start + end) / 2.0,
            "exit": max(start + (1.0 / fps), end - max(0.2, 2.0 / fps)),
        }
        evidence: dict[str, str] = {}
        for phase, timestamp in frame_times.items():
            ref = f"lifecycle_frames/{effect_id}_{phase}.jpg"
            _extract_frame(run, timestamp, ref)
            evidence[phase] = ref
            all_frames.append(ref)
        effect_records.append({
            "effect_id": effect_id,
            "start_sec": start,
            "end_sec": end,
            "evidence_frame": evidence["hold"],
            "evidence_frames": list(evidence.values()),
            "evidence": {
                "start_frame": evidence["enter"],
                "frame": evidence["hold"],
                "end_frame": evidence["exit"],
            },
        })
    contact_sheet = _contact_sheet(run, all_frames)
    _write_json(run / "title_effect_lifecycle_plan.json", {
        "artifact_role": "title_effect_lifecycle_plan",
        "version": 1,
        "effects": effect_records,
    })
    report = write_title_effect_lifecycle_qa_for_run(run)
    report["effects"] = effect_records
    report["frame_evidence"] = all_frames
    report["rendered_frame_evidence"] = all_frames
    report["contact_sheet"] = contact_sheet
    _write_json(run / "title_effect_lifecycle_qa.json", report)
    if report.get("pass") is not True:
        raise OpeningSliceError("title lifecycle QA failed")
    return report


def validate_opening_slice_acceptance(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Evaluate the no-promotion technical gates for this bounded opening."""
    blocking: list[dict[str, Any]] = []
    fps = float(payload.get("fps") or 30.0)
    tolerance = 1.0 / fps

    def block(rule: str, message: str) -> None:
        blocking.append({"rule": rule, "message": message})

    if abs(float(payload.get("duration_sec") or 0.0) - 44.0) > tolerance:
        block("duration_out_of_tolerance", "candidate duration differs from 44 seconds by more than one frame")
    if payload.get("has_video_stream") is not True:
        block("missing_video_stream", "candidate lacks a video stream")
    if payload.get("has_audio_stream") is not True:
        block("missing_audio_stream", "candidate lacks an audio stream")
    if int(payload.get("montage_distinct_asset_count") or 0) < 15:
        block("insufficient_montage_assets", "montage uses fewer than 15 distinct accepted assets")
    beat = payload.get("beat_alignment") or {}
    if beat.get("pass") is not True or float(beat.get("within_one_frame_ratio") or 0.0) != 1.0:
        block("beat_alignment_failed", "intended montage cut boundaries are not all within one frame")
    if (payload.get("rendered_qa") or {}).get("pass") is not True:
        block("rendered_qa_failed", "rendered product QA did not pass")
    title_qa = payload.get("title_effect_lifecycle_qa") or {}
    evidence = title_qa.get("frame_evidence") or title_qa.get("rendered_frame_evidence") or title_qa.get("sampled_frames")
    if title_qa.get("pass") is not True or not isinstance(evidence, list) or not evidence or not title_qa.get("contact_sheet"):
        block("title_effect_evidence_missing", "title/poem lifecycle QA lacks rendered enter-hold-exit frame evidence")
    if payload.get("required_artifacts_present") is not True:
        block("required_artifact_missing", "opening slice required artifact is missing")
    if payload.get("reference_film_used") is True:
        block("reference_film_used", "reference film was selected as candidate footage")
    if payload.get("all_sources_accepted") is not True:
        block("unaccepted_source_used", "candidate uses a source outside the accepted catalog")
    if payload.get("final_delivery_claimed") is not False:
        block("delivery_claim_not_false", "technical rehearsal must keep final_delivery_claimed=false")
    if payload.get("human_creative_approval") is not False:
        block("creative_approval_not_false", "technical rehearsal must keep human_creative_approval=false")
    return {
        "artifact_role": "opening_slice_acceptance",
        "version": 1,
        "pass": not blocking,
        "blocking": blocking,
        "duration_sec": payload.get("duration_sec"),
        "fps": fps,
        "duration_tolerance_sec": tolerance,
        "montage_distinct_asset_count": payload.get("montage_distinct_asset_count"),
        "beat_alignment": beat,
        "rendered_qa_pass": (payload.get("rendered_qa") or {}).get("pass"),
        "human_creative_approval": False,
        "final_delivery_claimed": False,
    }


def run_graduation_opening_slice(
    *,
    seed_run: str | Path,
    source_root: str | Path,
    request_path: str | Path,
    out_dir: str | Path,
) -> dict[str, Any]:
    """Build one fresh technical-review 0:00-0:44 opening candidate."""
    seed = Path(seed_run)
    source = Path(source_root)
    out = Path(out_dir)
    if out.exists():
        raise OpeningSliceError(f"output root already exists; preserve it and choose a fresh root: {out}")
    request = _request(request_path)
    catalog, accepted_existing = _accepted_photo_catalog(seed, source)
    if len(catalog) < 16:
        raise OpeningSliceError(f"real accepted non-reference photo count is {len(catalog)}; need at least 16")
    audio_input, soundtrack_probe = _audio_input(seed)
    title_asset = catalog[0]
    montage_assets = catalog[1:16]
    opening = _opening_sequence(request, title_asset, montage_assets, list((soundtrack_probe.get("features") or {}).get("beat_times") or []))
    out.mkdir(parents=True, exist_ok=False)
    run = out / "run"
    run.mkdir()
    _write_json(out / "source_provenance.json", {
        "artifact_role": "opening_slice_source_provenance",
        "version": 1,
        "seed_artifacts": ["reviewed_catalog_map.json", "soundtrack_probe_report.json"],
        "accepted_nonreference_existing_count": accepted_existing,
        "selected_title_asset": {key: title_asset[key] for key in ("asset_id", "source_relative_path", "human_review_status", "catalog_artifact")},
        "selected_montage_assets": [
            {key: asset[key] for key in ("asset_id", "source_relative_path", "human_review_status", "catalog_artifact")}
            for asset in montage_assets
        ],
        "reference_film_filename": REFERENCE_FILM_NAME,
        "reference_film_selected_as_footage": False,
    })
    _write_json(run / "opening_sequence.json", opening)
    _write_json(run / "rough_cut_plan.json", {"artifact_role": "rough_cut_plan", "ok": True, "clips": [], "gaps": []})
    _write_json(run / "audio_director_handoff.json", {
        "artifact_role": "audio_director_handoff",
        "ready_for_audio_director": True,
        "selected_audio_files": [{"candidate_id": "bgm", "section_id": "opening", "audio_file": "bgm", "source_type": "accepted_seed_soundtrack", "music_role": "opening_bgm"}],
    })
    _write_json(run / "soundtrack_probe_report.json", soundtrack_probe)
    artifacts = write_product_artifacts(run)
    decision = artifacts["edit_decision_plan"]
    timeline = _timeline_from_decision(decision, request)
    accepted_inputs = [title_asset, *montage_assets, audio_input]
    try:
        render_result = render_edit_decision(decision, timeline, run_dir=run, accepted_inputs=accepted_inputs)
    except EditDecisionRenderError as exc:
        raise OpeningSliceError(str(exc)) from exc
    persisted_timeline = _load_json(run / "timeline_build.json")
    beat_report = write_beat_cut_alignment_report(
        persisted_timeline,
        soundtrack_probe,
        window_start=18.0,
        window_end=44.0,
        fps=30,
        out_path=out / "beat_cut_alignment_report.json",
    )
    lifecycle = _write_lifecycle_evidence(run, list(decision.get("overlays") or []), 30)
    rendered_qa = write_rendered_product_qa(run, out / "rendered_qa")
    probe = probe_video(run / "final.mp4")
    streams = probe.get("streams") or []
    has_video = any(stream.get("codec_type") == "video" for stream in streams if isinstance(stream, Mapping))
    has_audio = any(stream.get("codec_type") == "audio" for stream in streams if isinstance(stream, Mapping))
    creative_packet = out / "creative_review_packet.md"
    creative_packet.write_text(
        "# Canon 67 Opening Slice Creative Review Packet\n\n"
        "- Candidate scope: technical rehearsal only\n"
        "- human_creative_approval=false\n"
        "- final_delivery_claimed=false\n"
        "- Review the rendered title, poetry-card progression, montage rhythm, and source appropriateness.\n",
        encoding="utf-8",
    )
    required_paths = [
        run / "edit_decision_plan.json",
        run / "timeline_build.json",
        run / "render_handoff.json",
        run / "final.mp4",
        out / "beat_cut_alignment_report.json",
        out / "rendered_qa" / "rendered_product_qa.json",
        run / "title_effect_lifecycle_qa.json",
        run / "lifecycle_contact_sheet.jpg",
        creative_packet,
    ]
    handoff = _load_json(run / "render_handoff.json")
    acceptance_input = {
        "duration_sec": probe.get("duration_sec"),
        "fps": 30,
        "has_video_stream": has_video,
        "has_audio_stream": has_audio,
        "montage_distinct_asset_count": len({clip.get("asset_id") for clip in persisted_timeline.get("clips") or [] if clip.get("section") == "montage"}),
        "beat_alignment": beat_report,
        "rendered_qa": rendered_qa,
        "title_effect_lifecycle_qa": lifecycle,
        "required_artifacts_present": all(path.is_file() for path in required_paths),
        "reference_film_used": any(REFERENCE_FILM_NAME in str(clip.get("source_relative_path") or clip.get("source_path") or "") for clip in persisted_timeline.get("clips") or []),
        "all_sources_accepted": all(
            (clip.get("source_type") == "generated_background") or bool((clip.get("source_lineage") or {}).get("accepted"))
            for clip in persisted_timeline.get("clips") or []
        ),
        "human_creative_approval": False,
        "final_delivery_claimed": handoff.get("final_delivery_claimed"),
    }
    acceptance = validate_opening_slice_acceptance(acceptance_input)
    acceptance.update({
        "output_root": str(out),
        "run_dir": "run",
        "render_result": {"ok": render_result.get("ok"), "final_mp4": "run/final.mp4"},
        "required_artifacts": [str(path.relative_to(out)).replace("\\", "/") for path in required_paths],
        "source_provenance": "source_provenance.json",
        "title_lifecycle_contact_sheet": "run/lifecycle_contact_sheet.jpg",
    })
    _write_json(out / "opening_slice_acceptance.json", acceptance)
    return acceptance
