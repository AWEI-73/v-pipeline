"""Deterministic M4 same-case replay metrics and acceptance checks."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

from .broll_audit import audit_broll
from .new_visual_information_audit import audit_new_visual_information
from .platform_tools import resolve_ffprobe


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


def _check_storybook_stock(root: Path) -> dict:
    run = root / "runs" / "storybook-stock-story" / "runs" / "20260704-storybook-stock-story-probe"
    timeline_path = run / "timeline_build.json"
    music_path = run / "music_structure.json"
    final_path = run / "final.mp4"
    verify_path = run / "verify_result.json"
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
            "timeline_clip_count": len(clips),
            "music_section_count": len(sections),
            "final_streams": streams,
            "verify_pass": bool(verify.get("pass")),
        },
    }


def _check_material_intake(root: Path) -> dict:
    fixture = root / ".tmp" / "r3_acceptance_probe"
    missing_refusal = _read_json(fixture / "case1_missing_material_folder" / "material_first_source_refusal.json")
    target_review = _read_json(fixture / "case2_target_length_5h" / "spec_review.json")
    aspect_intent = _read_json(fixture / "case3_aspect_ratio_32_9" / "video_intent.json")
    bad_candidates = _read_json(fixture / "case4_darwin_bad_mp4" / "materials_db.source_candidates.json")
    bad_refusal = _read_json(fixture / "case4_darwin_bad_mp4" / "material_first_source_refusal.json")
    artifacts = [
        fixture / "case1_missing_material_folder" / "material_first_source_refusal.json",
        fixture / "case2_target_length_5h" / "spec_review.json",
        fixture / "case3_aspect_ratio_32_9" / "video_intent.json",
        fixture / "case4_darwin_bad_mp4" / "materials_db.source_candidates.json",
        fixture / "case4_darwin_bad_mp4" / "material_first_source_refusal.json",
    ]
    target_sec = target_review.get("stats", {}).get("target_sec")
    questions = aspect_intent.get("required_followup_questions") or []
    rejects = bad_candidates.get("rejects") or []
    metrics = {
        "missing_folder_needs_context": missing_refusal.get("next_action") == "needs-context",
        "target_length_5h_sec": target_sec,
        "unsupported_aspect_needs_context": aspect_intent.get("entry_path") == "needs-context" and bool(questions),
        "bad_mp4_rejected": any(item.get("reason") == "invalid_media" for item in rejects),
        "bad_mp4_refusal_needs_context": bad_refusal.get("next_action") == "needs-context",
    }
    return {
        "id": "material_intake_boundary",
        "ok": all(bool(value) for value in metrics.values() if not isinstance(value, (int, float))) and target_sec == 18000.0,
        "description": "material intake replay covers missing folder, 5h target parsing, unsupported aspect ratio, and corrupt mp4 rejection",
        "artifacts": [_rel(root, path) for path in artifacts],
        "metrics": metrics,
    }


def _check_delivery_placeholder_guard(root: Path) -> dict:
    gate_path = root / "video_pipeline_core" / "delivery_gate.py"
    test_path = root / "tests" / "test_delivery_gate.py"
    gate_text = gate_path.read_text(encoding="utf-8")
    test_text = test_path.read_text(encoding="utf-8")
    has_gate = "final.mp4 is not a valid playable media file" in gate_text
    has_test = "test_complete_video_gate_blocks_placeholder_final_with_clear_finding" in test_text
    return {
        "id": "delivery_placeholder_stream_guard",
        "ok": has_gate and has_test,
        "description": "delivery gate has a placeholder final.mp4 stream guard with focused regression evidence",
        "artifacts": [_rel(root, gate_path), _rel(root, test_path)],
        "metrics": {
            "guard_message_present": has_gate,
            "placeholder_regression_test_present": has_test,
        },
    }


def _check_dotenv_provider_visibility(root: Path) -> dict:
    files = [
        root / "video_tools.py",
        root / "tools" / "preflight.py",
        root / "video_pipeline_core" / "vt_stock.py",
        root / "video_pipeline_core" / "soundtrack_providers.py",
        root / "video_pipeline_core" / "env_loader.py",
    ]
    contents = {path: path.read_text(encoding="utf-8") for path in files}
    metrics = {
        "video_tools_applies_dotenv": "apply_dotenv" in contents[files[0]],
        "preflight_uses_env_loader": "load_env_file" in contents[files[1]],
        "stock_uses_env_loader": "env_loader import getenv" in contents[files[2]],
        "soundtrack_uses_env_loader": "env_loader import load_env_file" in contents[files[3]],
        "env_loader_exists": "def apply_dotenv" in contents[files[4]],
    }
    return {
        "id": "dotenv_provider_visibility",
        "ok": all(metrics.values()),
        "description": "provider/preflight paths share the centralized dotenv loader without live provider calls",
        "artifacts": [_rel(root, path) for path in files],
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
