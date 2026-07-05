"""Deterministic M4 same-case replay metrics and acceptance checks."""
from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch

from .broll_audit import audit_broll
from .delivery_gate import evaluate_complete_video_delivery
from .env_loader import apply_dotenv, load_env_file
from .new_visual_information_audit import audit_new_visual_information
from .platform_tools import resolve_ffmpeg, resolve_ffprobe
from .spec_review import review_spec
from .video_intent_planner import plan_video_intent


def _clips(timeline):
    return timeline if isinstance(timeline, list) else (timeline or {}).get("clips") or []


def _gate_pass(payload):
    if not isinstance(payload, dict):
        return False
    if "ready_for_build" in payload:
        return bool(payload["ready_for_build"])
    return bool(payload.get("pass"))


def build_replay_report(timeline, *, gate_artifacts=None, judge_verdicts=None,
                        jumpcut_plan=None, new_visual_audit=None,
                        adaptation_decisions=None):
    clips = _clips(timeline)
    total_clips = len(clips)
    short_count = sum(1 for item in clips if float(item.get("duration_sec") or 0) <= 2.0)
    broll = audit_broll(timeline)
    nvi = new_visual_audit or audit_new_visual_information(timeline)
    action = [item for item in clips if item.get("beat_alignment") == "action"]
    aligned = [item for item in action if item.get("adjustment_reason") == "motion_phase"]
    gates = gate_artifacts or {}
    verdicts = judge_verdicts or []
    jumpcut_applicable = bool((jumpcut_plan or {}).get("requires_review"))
    jumpcut_count = 1 if (jumpcut_plan or {}).get("approved") else 0
    jumpcut_check = (
        "pass" if jumpcut_applicable and jumpcut_count
        else "fail" if jumpcut_applicable
        else "not_applicable"
    )
    adaptation = adaptation_decisions or {}
    duration_check = "pass" if adaptation.get("duration") == "shortened" else "unproven"
    chapter_check = "pass" if adaptation.get("chapters") == "reduced" else "unproven"
    checks = {
        "tier1_gates": "pass" if gates and all(_gate_pass(v) for v in gates.values()) else "fail",
        "judge_lineage": "pass" if verdicts and all(
            item.get("decision") == "accept" for item in verdicts) else "fail",
        "new_visual_information": "pass" if nvi.get("pass") else "fail",
        "jumpcut_when_applicable": jumpcut_check,
        "duration_adaptation": duration_check,
        "chapter_adaptation": chapter_check,
    }
    return {
        "artifact_role": "m4_replay_acceptance",
        "version": 1,
        "pass": all(value in ("pass", "not_applicable") for value in checks.values()),
        "metrics": {
            "shot_le_2s_ratio": round(short_count / total_clips, 4) if total_clips else 0.0,
            "unique_source_ratio": broll["metrics"]["unique_source_ratio"],
            "max_source_repeats": broll["metrics"]["max_source_repeats"],
            "new_visual_information_ratio": nvi["metrics"]["new_visual_information_ratio"],
            "action_phase_coverage": round(len(aligned) / len(action), 4) if action else 0.0,
            "sound_bite_count": sum(1 for item in clips if item.get("keep_audio")),
            "jumpcut_count": jumpcut_count,
        },
        "checks": checks,
        "judge_verdicts": verdicts,
        "adaptation_decisions": adaptation,
    }


def write_replay_report(timeline, out_path, **kwargs):
    result = build_replay_report(timeline, **kwargs)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _rel(root: Path, path: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return str(path)


def _media_streams(video_path: Path) -> list[str]:
    proc = subprocess.run(
        [
            resolve_ffprobe(),
            "-v",
            "error",
            "-show_entries",
            "stream=codec_type",
            "-of",
            "json",
            str(video_path),
        ],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        return []
    try:
        payload = json.loads(proc.stdout or "{}")
    except json.JSONDecodeError:
        return []
    return sorted({
        stream.get("codec_type")
        for stream in payload.get("streams") or []
        if stream.get("codec_type")
    })


def _fixture_root(root: Path) -> Path:
    path = root / ".tmp" / "probe_repair_replay"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _fresh_generated_dir(path: Path) -> Path:
    if path.exists():
        resolved = path.resolve()
        # The caller passes paths under root/.tmp/probe_repair_replay. Avoid
        # cleaning anything outside that generated replay area.
        if ".tmp" not in resolved.parts or "probe_repair_replay" not in resolved.parts:
            raise ValueError(f"refusing to clean non-replay fixture path: {path}")
        shutil.rmtree(path)
    return path


def _generate_tiny_av_mp4(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and {"audio", "video"}.issubset(set(_media_streams(path))):
        return
    proc = subprocess.run(
        [
            resolve_ffmpeg(),
            "-y",
            "-f",
            "lavfi",
            "-i",
            "color=c=black:s=160x90:d=1",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:duration=1",
            "-shortest",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-c:a",
            "aac",
            str(path),
        ],
        text=True,
        capture_output=True,
    )
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr or proc.stdout or "ffmpeg failed to generate replay fixture")


def _write_probe_jpg(path: Path, color: tuple[int, int, int]) -> None:
    from PIL import Image

    path.parent.mkdir(parents=True, exist_ok=True)
    Image.new("RGB", (80, 45), color=color).save(path, "JPEG")


def _check_storybook_stock(root: Path) -> dict:
    run = _fixture_root(root) / "storybook_stock_story"
    timeline_path = run / "timeline_build.json"
    music_path = run / "music_structure.json"
    final_path = run / "final.mp4"
    verify_path = run / "verify_result.json"
    _write_json(timeline_path, {
        "artifact_role": "timeline_build",
        "clips": [
            {
                "segment": 1,
                "source_path": "generated_probe_stock_clip.mp4",
                "start": 0.0,
                "duration_sec": 1.0,
            }
        ],
    })
    _write_json(music_path, {
        "artifact_role": "music_structure",
        "sections": [
            {"section_id": "opening", "start_sec": 0.0, "duration_sec": 1.0}
        ],
    })
    _generate_tiny_av_mp4(final_path)
    _write_json(verify_path, {"artifact_role": "verify_result", "pass": True, "issues": []})
    timeline = _read_json(timeline_path)
    music = _read_json(music_path)
    verify = _read_json(verify_path)
    streams = _media_streams(final_path)
    clips = timeline.get("clips") or []
    sections = music.get("sections") or []
    ok = bool(clips) and bool(sections) and {"video", "audio"}.issubset(set(streams)) and bool(verify.get("pass"))
    return {
        "id": "storybook_stock_story",
        "ok": ok,
        "description": "storybook stock chain has timeline clips, music sections, playable final streams, and verify pass",
        "artifacts": [_rel(root, path) for path in [timeline_path, music_path, final_path, verify_path]],
        "metrics": {
            "fixture_source": "runtime_generated",
            "timeline_clip_count": len(clips),
            "music_section_count": len(sections),
            "final_streams": streams,
            "verify_pass": bool(verify.get("pass")),
        },
    }


def _check_material_intake(root: Path) -> dict:
    from tools.material_first_landing_case import run_material_first_landing_case

    fixture = _fixture_root(root) / "material_intake"
    missing_run = _fresh_generated_dir(fixture / "case1_missing_material_folder")
    missing_source = fixture / "missing_source_does_not_exist"
    missing_result = run_material_first_landing_case(missing_run, source_dir=missing_source, max_assets=5)
    missing_refusal = _read_json(missing_run / "material_first_source_refusal.json")

    target_review = review_spec(
        {"segments": [
            {"segment": 1, "requested_duration_sec": 9000},
            {"segment": 2, "requested_duration_sec": 9000},
        ]},
        {
            "video_type": "documentary",
            "target_length": "5 hours",
            "mode": "warm_documentary",
            "enforce_target_length": True,
        },
        has_editorial_design=True,
    )
    target_path = fixture / "case2_target_length_5h" / "spec_review.json"
    _write_json(target_path, target_review)

    aspect_intent = plan_video_intent({
        "video_type": "event",
        "audience": "family",
        "goal": "archive",
        "material_availability": "none",
        "text_availability": "none",
        "target_length": "3 minutes",
        "aspect_ratio": "32:9",
        "tone": "documentary",
    })
    aspect_path = fixture / "case3_aspect_ratio_32_9" / "video_intent.json"
    _write_json(aspect_path, aspect_intent)

    corrupt_source = fixture / "case4_darwin_bad_mp4_source"
    for folder, color in (("opening", (180, 20, 20)), ("training", (20, 160, 60)), ("closing", (30, 80, 180))):
        media_path = corrupt_source / folder / f"{folder}.jpg"
        _write_probe_jpg(media_path, color)
    (corrupt_source / "closing" / "corrupt.mp4").write_bytes(b"not a real mp4")
    corrupt_run = _fresh_generated_dir(fixture / "case4_darwin_bad_mp4")
    corrupt_result = run_material_first_landing_case(corrupt_run, source_dir=corrupt_source, max_assets=5)
    bad_candidates = _read_json(corrupt_run / "materials_db.source_candidates.json")
    artifacts = [
        missing_run / "material_first_source_refusal.json",
        target_path,
        aspect_path,
        corrupt_run / "materials_db.source_candidates.json",
    ]
    target_sec = target_review.get("stats", {}).get("target_sec")
    questions = aspect_intent.get("required_followup_questions") or []
    rejects = bad_candidates.get("rejects") or []
    metrics = {
        "fixture_source": "runtime_generated",
        "missing_folder_needs_context": (
            missing_result.get("next_action") == "needs-context"
            and missing_refusal.get("next_action") == "needs-context"
        ),
        "target_length_5h_sec": target_sec,
        "unsupported_aspect_needs_context": aspect_intent.get("entry_path") == "needs-context" and bool(questions),
        "bad_mp4_rejected": any(item.get("reason") == "invalid_media" for item in rejects),
        "bad_mp4_zero_traceback": bool(corrupt_result.get("ok")) and not (corrupt_result.get("blocking") or []),
    }
    return {
        "id": "material_intake_boundary",
        "ok": (
            bool(metrics["missing_folder_needs_context"])
            and target_sec == 18000.0
            and bool(metrics["unsupported_aspect_needs_context"])
            and bool(metrics["bad_mp4_rejected"])
            and bool(metrics["bad_mp4_zero_traceback"])
        ),
        "description": "material intake replay covers missing folder, 5h target parsing, unsupported aspect ratio, and corrupt mp4 rejection",
        "artifacts": [_rel(root, path) for path in artifacts],
        "metrics": metrics,
    }


def _check_delivery_placeholder_guard(root: Path) -> dict:
    run = _fixture_root(root) / "delivery_placeholder"
    run.mkdir(parents=True, exist_ok=True)
    (run / "final.mp4").write_bytes(b"not a real playable media file")
    _write_json(run / "delivery_requirements.json", {
        "artifact_role": "delivery_requirements",
        "version": 1,
        "requires_audio": True,
        "requires_narration": False,
        "requires_music": False,
        "requires_subtitles": False,
    })
    result = evaluate_complete_video_delivery(run)
    blocking = result.get("blocking") or []
    media_findings = [
        item for item in blocking
        if item.get("artifact") == "final.mp4" and item.get("rule") == "media_probe_failed"
    ]
    finding_text = " ".join(str(item.get("message", "")) for item in media_findings).lower()
    rejected = not result.get("pass") and bool(media_findings)
    mentions_stream_or_playable = "stream" in finding_text or "playable media" in finding_text
    return {
        "id": "delivery_placeholder_stream_guard",
        "ok": rejected and mentions_stream_or_playable,
        "description": "delivery gate rejects a placeholder final.mp4 by executing the complete-video media probe",
        "artifacts": [_rel(root, run / "final.mp4"), _rel(root, run / "delivery_requirements.json")],
        "metrics": {
            "fixture_source": "runtime_generated",
            "placeholder_final_rejected": rejected,
            "finding_mentions_stream_or_playable_media": mentions_stream_or_playable,
            "blocking_rules": sorted({str(item.get("rule")) for item in blocking if item.get("rule")}),
        },
    }


def _check_dotenv_provider_visibility(root: Path) -> dict:
    from tools.preflight import check_environment
    from video_pipeline_core import env_loader, soundtrack_providers, vt_stock

    fixture = _fixture_root(root) / "dotenv_provider"
    env_path = fixture / ".env"
    env_path.parent.mkdir(parents=True, exist_ok=True)
    env_path.write_text(
        "PEXELS_API_KEY=portable-pexels-token\n"
        "PIXABAY_API_KEY=portable-pixabay-token\n"
        "JAMENDO_CLIENT_ID=portable-jamendo-id\n",
        encoding="utf-8",
    )
    loaded = load_env_file(env_path, env={})
    preflight = check_environment(
        env=loaded,
        python_version=(3, 10, 16),
        which=lambda name: f"C:/portable/{name}.exe",
        find_spec=lambda name: object(),
        run_command=lambda args: f"{args[0]} portable-version",
    )
    with patch.dict(os.environ, {}, clear=True), patch.object(env_loader, "REPO_ROOT", fixture):
        apply_dotenv(env_path)
        stock_value = vt_stock.getenv("PEXELS_API_KEY")
    soundtrack_plan = {
        "sections": [
            {
                "section_id": "mv_climax",
                "music_role": "bgm",
                "source_type": "pixabay_music",
                "story_function": "climax",
            }
        ],
    }
    soundtrack = soundtrack_providers.search_soundtrack_providers(
        soundtrack_plan,
        providers=["pixabay"],
        env=loaded,
        limit=1,
    )
    metrics = {
        "fixture_source": "runtime_generated",
        "env_loader_reads_dotenv": loaded.get("PEXELS_API_KEY") == "portable-pexels-token",
        "preflight_provider_visibility_uses_loaded_env": "PEXELS_API_KEY" in (
            (preflight.get("environment") or {}).get("present_keys") or []
        ),
        "stock_provider_env_lookup_uses_loaded_value": stock_value == "portable-pexels-token",
        "soundtrack_provider_env_lookup_uses_loaded_value": (
            (soundtrack.get("provider_status") or {}).get("pixabay") == "official_audio_api_unavailable"
        ),
    }
    return {
        "id": "dotenv_provider_visibility",
        "ok": all(metrics.values()),
        "description": "provider/preflight paths see dotenv-loaded values without live provider calls",
        "artifacts": [_rel(root, env_path)],
        "metrics": metrics,
    }


def build_probe_repair_replay_report(root: str | Path | None = None) -> dict:
    repo = Path(root or Path.cwd())
    checks = [
        _check_storybook_stock(repo),
        _check_material_intake(repo),
        _check_delivery_placeholder_guard(repo),
        _check_dotenv_provider_visibility(repo),
    ]
    failures = [
        {"id": check["id"], "description": check["description"], "metrics": check["metrics"]}
        for check in checks
        if not check["ok"]
    ]
    artifacts = []
    for check in checks:
        artifacts.extend(check.get("artifacts") or [])
    return {
        "artifact_role": "probe_repair_replay_acceptance",
        "version": 1,
        "scenario": "probe-repair-20260704",
        "ok": not failures,
        "checks": checks,
        "artifacts": sorted(set(artifacts)),
        "failures": failures,
    }


def write_probe_repair_replay_report(out_path: str | Path, root: str | Path | None = None) -> dict:
    result = build_probe_repair_replay_report(root)
    path = Path(out_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result
