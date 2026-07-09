"""Acceptance helpers for Remotion effect draft integration.

These helpers build small, bounded run folders that exercise the existing
Hermes Remotion adapter route:

effect intent -> revision request -> prompt pack -> worker outputs -> review
-> non-canonical ffmpeg composite draft.

They do not write final.mp4 and do not replace the canonical ffmpeg renderer.
"""

from __future__ import annotations

import json
import subprocess
import struct
import zlib
from pathlib import Path
from typing import Any, Mapping

from .effect_revision import ADAPTER_ROUTE
from .platform_tools import resolve_ffmpeg
from .remotion_effects import (
    build_remotion_prompt_pack,
    composite_accepted_remotion_effects,
    run_remotion_worker_smoke,
    validate_remotion_worker_outputs,
)


PROFILE_DURATIONS = {
    "boundary": 24.0,
    "micro": 48.0,
    "real": 72.0,
}

TRAINING_OPENING_PROMPT_PARAMETERS = {
    "effect_goal": "formal_training_opening",
    "tone": ["formal", "warm", "memory_recap"],
    "material_strategy": {
        "hero_source": "reviewed_people_group",
        "avoid_hero_roles": ["title_card"],
        "collage_count": 5,
    },
    "motion_grammar": [
        "collage_depth_reveal",
        "gold_title_sweep",
        "title_punch",
    ],
    "text_hierarchy": {
        "primary": "program_title",
        "secondary": "subtitle",
    },
    "negative_rules": [
        "do_not_cover_faces",
        "avoid_party_style_flash",
        "avoid_random_stock_look",
    ],
}

STORY_TO_MV_TRANSITION_PROMPT_PARAMETERS = {
    "effect_goal": "story_half_to_mv_half_transition",
    "transition_strength": "impact",
    "phase_labels": ["STORY", "MONTAGE"],
    "cut_point": "midpoint_impact",
    "material_strategy": {
        "thumbnail_source": "reviewed_stills",
        "thumbnail_density": "balanced",
        "reject_low_information_refs": True,
    },
    "motion_grammar": [
        "film_rail",
        "thumbnail_acceleration",
        "flash_wipe",
        "hard_cut_bars",
        "midpoint_impact",
    ],
    "negative_rules": [
        "do_not_read_as_static_chapter_card",
        "do_not_obscure_proof_footage",
        "avoid_random_party_flash",
    ],
}


def _write_json(path: Path, payload: Mapping[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def _effect(effect_id: str, role: str, intent: str, segment: str,
            duration_sec: float, *, visual_language: list[str],
            required_for_story: bool = True,
            template_id: str | None = None,
            display_text: str | None = None,
            subtitle_text: str | None = None,
            presentation: Mapping[str, Any] | None = None,
            prompt_parameters: Mapping[str, Any] | None = None) -> dict[str, Any]:
    effect = {
        "effect_id": effect_id,
        "role": role,
        "intent": intent,
        "intensity": "medium" if required_for_story else "low",
        "target": {"beat_id": f"beat_{segment}", "segment_id": segment},
        "visual_language": visual_language,
        "required_for_story": required_for_story,
        "must_preserve_proof": False,
        "allowed_backends": ["remotion_preview", "remotion_render"],
        "fallback": "simple fade",
        "duration_sec": duration_sec,
    }
    if template_id:
        effect["template_id"] = template_id
    if display_text:
        effect["display_text"] = display_text
    if subtitle_text:
        effect["subtitle_text"] = subtitle_text
    if presentation:
        effect["presentation"] = dict(presentation)
    if prompt_parameters:
        effect["prompt_parameters"] = json.loads(json.dumps(prompt_parameters, ensure_ascii=False))
    return effect


def _chapter_transition_effect() -> dict[str, Any]:
    return _effect(
        "fx_chapter_transition_01",
        "chapter_transition",
        "bridge from training story into memory montage",
        "transition_01",
        1.8,
        visual_language=["story to montage transition", "impact wipe", "film rail"],
        template_id="film_strip_transition_card",
        display_text="故事開始加速",
        subtitle_text="從故事段進入節奏蒙太奇",
        presentation={
            "variant": "story_to_mv_film_transition",
            "motion_energy": "high",
            "thumbnail_density": "balanced",
        },
        prompt_parameters=STORY_TO_MV_TRANSITION_PROMPT_PARAMETERS,
    )


def build_acceptance_fixture(profile: str) -> dict[str, Any]:
    """Return neutral route artifacts for a small Remotion acceptance run."""
    if profile not in PROFILE_DURATIONS:
        raise ValueError(f"unknown profile: {profile}")
    total = PROFILE_DURATIONS[profile]
    effects = [_chapter_transition_effect()]
    clips = [
        {"segment": "base_a", "timeline_in_sec": 0.0, "timeline_out_sec": 10.0},
        {"segment": "transition_01", "timeline_in_sec": 10.0, "timeline_out_sec": 11.8},
        {"segment": "base_b", "timeline_in_sec": 11.8, "timeline_out_sec": total},
    ]
    if profile in {"micro", "real"}:
        effects.insert(0, _effect(
            "fx_title_intro_01",
            "title_card",
            "open the short with a clean training recap title",
            "title_01",
            4.0,
            visual_language=["black collage", "yellow title", "formal training opening"],
            template_id="training_opening_title",
            display_text="67TH TRAINING",
            subtitle_text="ON THE LAST PAGE",
            presentation={
                "variant": "cinematic_collage_reveal",
                "motion_energy": "high",
                "title_hierarchy": "hero",
                "hero_media_policy": "avoid_title_bearing",
            },
            prompt_parameters=TRAINING_OPENING_PROMPT_PARAMETERS,
        ))
        effects.append(_effect(
            "fx_lower_third_01",
            "lower_third",
            "identify the training cohort without covering the proof image",
            "lower_01",
            4.0,
            visual_language=["lower third", "subtle slide", "readable label"],
            required_for_story=False,
        ))
        clips = [
            {"segment": "title_01", "timeline_in_sec": 0.0, "timeline_out_sec": 4.0},
            {"segment": "base_a", "timeline_in_sec": 4.0, "timeline_out_sec": 18.0},
            {"segment": "transition_01", "timeline_in_sec": 18.0, "timeline_out_sec": 19.8},
            {"segment": "base_b", "timeline_in_sec": 19.8, "timeline_out_sec": total},
            {"segment": "lower_01", "timeline_in_sec": 8.0, "timeline_out_sec": 12.0},
        ]
    if profile == "real":
        effects.append(_effect(
            "fx_highlight_overlay_01",
            "overlay",
            "briefly highlight the shift from effort to achievement",
            "highlight_01",
            3.0,
            visual_language=["soft highlight", "warm pulse", "restrained emphasis"],
            required_for_story=False,
        ))
        clips.append({"segment": "highlight_01", "timeline_in_sec": 32.0, "timeline_out_sec": 35.0})

    requests = []
    for effect in effects:
        segment = effect["target"]["segment_id"]
        requests.append({
            "request_id": f"fxrev_{effect['effect_id']}",
            "effect_id": f"{effect['effect_id']}_gap",
            "source_effect_id": effect["effect_id"],
            "segment": segment,
            "operation": "external_effect",
            "route": ADAPTER_ROUTE,
            "reason": "acceptance run requires Remotion-quality bounded effect asset",
            "status": "pending",
        })

    return {
        "effect_intent_plan": {
            "artifact_role": "effect_intent_plan",
            "version": 1,
            "effects": effects,
        },
        "effect_revision_request": {
            "artifact_role": "effect_revision_request",
            "version": 1,
            "status": "pending",
            "summary": {"request_count": len(requests)},
            "requests": requests,
        },
        "timeline_build": {
            "artifact_role": "timeline_build",
            "version": 1,
            "duration_sec": total,
            "clips": clips,
        },
    }


def render_synthetic_base_video(path: str | Path, duration_sec: float, *,
                                ffmpeg: str | None = None) -> Path:
    """Render a small synthetic base clip for non-canonical composite tests."""
    ffmpeg = ffmpeg or resolve_ffmpeg()
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    command = [
        ffmpeg, "-y",
        "-f", "lavfi",
        "-i", f"testsrc2=duration={duration_sec}:size=1920x1080:rate=30",
        "-f", "lavfi",
        "-i", f"sine=frequency=440:duration={duration_sec}:sample_rate=48000",
        "-shortest",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-movflags", "+faststart",
        str(path),
    ]
    proc = subprocess.run(command, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0 or not path.is_file():
        raise RuntimeError(f"base video render failed: {(proc.stderr or '')[-800:]}")
    return path


def _png_chunk(kind: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + kind
        + data
        + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)
    )


def _write_png(path: Path, width: int, height: int, pixels: bytes) -> None:
    raw = bytearray()
    row_bytes = width * 3
    for y in range(height):
        raw.append(0)
        start = y * row_bytes
        raw.extend(pixels[start:start + row_bytes])
    payload = (
        b"\x89PNG\r\n\x1a\n"
        + _png_chunk(b"IHDR", struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0))
        + _png_chunk(b"IDAT", zlib.compress(bytes(raw), 6))
        + _png_chunk(b"IEND", b"")
    )
    path.write_bytes(payload)


def _write_acceptance_still(path: Path, *, seed: int, ffmpeg: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    width, height = 960, 540
    palettes = [
        ((40, 57, 74), (180, 195, 178), (236, 209, 92)),
        ((46, 50, 62), (105, 132, 156), (222, 226, 218)),
        ((35, 43, 38), (138, 156, 116), (238, 198, 88)),
        ((55, 48, 46), (158, 130, 104), (235, 218, 170)),
    ]
    dark, mid, accent = palettes[(seed - 1) % len(palettes)]
    pixels = bytearray(width * height * 3)
    for y in range(height):
        y_mix = y / max(1, height - 1)
        for x in range(width):
            x_mix = x / max(1, width - 1)
            vignette = 1 - min(0.42, ((x_mix - 0.5) ** 2 + (y_mix - 0.5) ** 2) * 1.8)
            stripe = 0.08 if ((x + seed * 23) // 78) % 2 == 0 else 0.0
            card = (
                width * 0.18 < x < width * 0.82
                and height * 0.22 < y < height * 0.70
            )
            r = dark[0] * (1 - x_mix) + mid[0] * x_mix
            g = dark[1] * (1 - x_mix) + mid[1] * x_mix
            b = dark[2] * (1 - x_mix) + mid[2] * x_mix
            r = r * (0.78 + 0.18 * y_mix + stripe)
            g = g * (0.78 + 0.18 * y_mix + stripe)
            b = b * (0.78 + 0.18 * y_mix + stripe)
            if card:
                r = r * 0.72 + accent[0] * 0.28
                g = g * 0.72 + accent[1] * 0.28
                b = b * 0.72 + accent[2] * 0.28
            if abs(x - width * 0.50) < 4 and height * 0.18 < y < height * 0.78:
                r, g, b = accent
            idx = (y * width + x) * 3
            pixels[idx] = max(0, min(255, int(r * vignette)))
            pixels[idx + 1] = max(0, min(255, int(g * vignette)))
            pixels[idx + 2] = max(0, min(255, int(b * vignette)))
    _write_png(path, width, height, bytes(pixels))
    if not path.is_file():
        raise RuntimeError("acceptance still render failed")
    return path


def _acceptance_collage_refs(run_dir: Path, *, ffmpeg: str) -> list[dict[str, Any]]:
    media_dir = run_dir / "acceptance_media"
    specs = [
        ("opening_group", "Opening group reference", "people_group", False),
        ("training_context", "Training context reference", "reviewed_material", False),
        ("work_scene", "Work scene reference", "reviewed_material", False),
        ("title_plate", "Title plate reference", "title_card", True),
    ]
    refs = []
    for index, (ref_id, label, visual_role, contains_title) in enumerate(specs, start=1):
        still = _write_acceptance_still(media_dir / f"{ref_id}.png", seed=index, ffmpeg=ffmpeg)
        refs.append({
            "ref_id": ref_id,
            "path": str(still),
            "label": label,
            "visual_role": visual_role,
            "contains_title": contains_title,
        })
    return refs


def _attach_acceptance_collage_refs(fixture: dict[str, Any], refs: list[dict[str, Any]]) -> None:
    for effect in fixture["effect_intent_plan"]["effects"]:
        if effect.get("template_id") in {"training_opening_title", "film_strip_transition_card"}:
            effect["collage_media_refs"] = json.loads(json.dumps(refs, ensure_ascii=False))


def write_contact_sheet(video_path: str | Path, out_path: str | Path, *,
                        ffmpeg: str | None = None) -> Path:
    video_path = Path(video_path)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    from .keyframe_grid import probe_duration
    from .montage_wall import write_montage_wall
    from .sampling_coverage import write_sampling_coverage_report
    from .sampling_planner import write_sampling_plan

    duration = probe_duration(video_path)
    shots = [{"shot_id": "render", "start_sec": 0.0, "end_sec": max(duration, 0.001)}]
    plan_path = out_path.with_suffix(".sampling_plan.json")
    coverage_path = out_path.with_suffix(".sampling_coverage_report.json")
    sidecar_path = out_path.with_suffix(".json")
    write_sampling_plan(video_path, shots, plan_path)
    write_sampling_coverage_report(plan_path, shots, coverage_path, max_gap_sec=max(duration + 1.0, 4.0))
    write_montage_wall(video_path, plan_path, coverage_path, out_path, sidecar_path, profile="timeline_wall")
    if not out_path.is_file() or out_path.stat().st_size <= 0:
        raise RuntimeError(f"contact sheet failed: {out_path}")
    return out_path


def accept_all_review_items(review: Mapping[str, Any], *, reviewer: str,
                            reason: str) -> dict[str, Any]:
    accepted = json.loads(json.dumps(review, ensure_ascii=False))
    accepted["status"] = "accepted"
    for item in accepted.get("items") or []:
        item["status"] = "accepted"
        item["review"] = {
            "decision": "accept",
            "reviewer": reviewer,
            "reason": reason,
        }
    return accepted


def run_remotion_transition_acceptance(run_dir: str | Path, *,
                                       profile: str = "boundary",
                                       real_worker_command: str | None = None,
                                       ffmpeg: str | None = None) -> dict[str, Any]:
    """Run a bounded Remotion transition acceptance scenario."""
    run_dir = Path(run_dir)
    run_dir.mkdir(parents=True, exist_ok=True)
    ffmpeg = ffmpeg or resolve_ffmpeg()
    fixture = build_acceptance_fixture(profile)
    duration = PROFILE_DURATIONS[profile]
    _attach_acceptance_collage_refs(
        fixture,
        _acceptance_collage_refs(run_dir, ffmpeg=ffmpeg),
    )

    effect_intent_path = _write_json(run_dir / "effect_intent_plan.json", fixture["effect_intent_plan"])
    revision_request_path = _write_json(run_dir / "effect_revision_request.json", fixture["effect_revision_request"])
    timeline_path = _write_json(run_dir / "timeline_build.json", fixture["timeline_build"])

    base_video = render_synthetic_base_video(run_dir / "base_draft.mp4", duration, ffmpeg=ffmpeg)
    pack = build_remotion_prompt_pack(
        fixture["effect_revision_request"],
        fixture["effect_intent_plan"],
        timeline=fixture["timeline_build"],
        output_dir="remotion_effects",
    )
    prompt_pack_path = _write_json(run_dir / "remotion_prompt_pack.json", pack)

    worker_outputs = run_remotion_worker_smoke(
        pack,
        run_dir / "remotion_effects",
        command_template=real_worker_command,
    )
    real_worker = bool(real_worker_command)
    for item in worker_outputs.get("jobs") or []:
        if (
            real_worker
            and item.get("status") == "rendered"
            and Path(item.get("preview_file", "")).is_file()
        ):
            evidence = write_contact_sheet(
                item["preview_file"],
                Path(item["preview_file"]).with_name(f"{Path(item['preview_file']).stem}_contact_sheet.jpg"),
                ffmpeg=ffmpeg,
            )
            item["evidence_refs"] = list(item.get("evidence_refs") or []) + [str(evidence)]
    worker_outputs_path = _write_json(run_dir / "remotion_worker_outputs.json", worker_outputs)

    validation = validate_remotion_worker_outputs(worker_outputs, pack)
    if not validation["ok"]:
        report = {
            "artifact_role": "remotion_transition_acceptance_report",
            "version": 1,
            "ok": False,
            "profile": profile,
            "failed_stage": "remotion_worker_outputs",
            "errors": validation.get("errors") or [],
            "next_action": "fix_remotion_worker_outputs",
            "artifacts": {
                "effect_intent_plan": str(effect_intent_path),
                "effect_revision_request": str(revision_request_path),
                "timeline_build": str(timeline_path),
                "base_video": str(base_video),
                "remotion_prompt_pack": str(prompt_pack_path),
                "remotion_worker_outputs": str(worker_outputs_path),
            },
        }
        _write_json(run_dir / "remotion_transition_acceptance_report.json", report)
        return report

    review_pending = validation["review_artifact"]
    _write_json(run_dir / "remotion_effect_review.pending.json", review_pending)
    review = accept_all_review_items(
        review_pending,
        reviewer="remotion-transition-acceptance",
        reason="bounded acceptance run: effect assets rendered and have evidence refs",
    )
    review_path = _write_json(run_dir / "remotion_effect_review.json", review)
    composite_report = composite_accepted_remotion_effects(
        review,
        base_video,
        run_dir / "remotion_composite_draft.mp4",
        ffmpeg=ffmpeg,
        dry_run=not real_worker,
    )
    composite_report_path = _write_json(run_dir / "remotion_composite_draft_report.json", composite_report)
    composite_sheet = None
    if real_worker:
        composite_sheet = write_contact_sheet(
            composite_report["out"],
            run_dir / "remotion_composite_draft_contact_sheet.jpg",
            ffmpeg=ffmpeg,
        )
    final_path = run_dir / "final.mp4"
    report = {
        "artifact_role": "remotion_transition_acceptance_report",
        "version": 1,
        "ok": True,
        "profile": profile,
        "duration_sec": duration,
        "job_count": pack["summary"]["job_count"],
        "rendered_count": worker_outputs["summary"]["rendered_count"],
        "failed_stage": None,
        "next_action": "review_noncanonical_draft_then_promote_rules",
        "canonical_final_exists": final_path.exists(),
        "artifacts": {
            "effect_intent_plan": str(effect_intent_path),
            "effect_revision_request": str(revision_request_path),
            "timeline_build": str(timeline_path),
            "base_video": str(base_video),
            "remotion_prompt_pack": str(prompt_pack_path),
            "remotion_worker_outputs": str(worker_outputs_path),
            "remotion_effect_review": str(review_path),
            "remotion_composite_draft": composite_report["out"],
            "remotion_composite_draft_report": str(composite_report_path),
            "remotion_composite_draft_contact_sheet": str(composite_sheet) if composite_sheet else None,
        },
        "review_notes": [
            "non-canonical draft only; final.mp4 must remain absent",
            "synthetic base video isolates transition/effect wiring from material-map quality",
        ],
    }
    _write_json(run_dir / "remotion_transition_acceptance_report.json", report)
    return report
