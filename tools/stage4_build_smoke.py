"""Validate that Stage 4 build artifacts are coherent before render/final review."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from video_pipeline_core.material_rough_cut import load_json, write_json  # noqa: E402


def _safe_load(path: Path) -> dict:
    if not path.exists():
        return {}
    return load_json(path)


def _num(value, default=0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _clip_identity(clip: dict) -> dict:
    return {
        "segment": clip.get("segment"),
        "source_path": clip.get("source_path"),
        "start_sec": round(_num(clip.get("start_sec")), 3),
        "duration_sec": round(_num(clip.get("duration_sec")), 3),
        "scene_id": clip.get("scene_id"),
    }


def _timeline_identity(clip: dict) -> dict:
    return {
        "segment": clip.get("segment"),
        "source_path": clip.get("source_path"),
        "start_sec": round(_num(clip.get("start_sec")), 3),
        "duration_sec": round(_num(clip.get("duration_sec")), 3),
        "scene_id": clip.get("scene_id"),
    }


def _issue(rule: str, message: str, **extra) -> dict:
    out = {"rule": rule, "message": message}
    out.update(extra)
    return out


def _validate_rough_cut(rough_cut: dict) -> list[dict]:
    issues = []
    if not rough_cut:
        return [_issue("missing_artifact", "rough_cut_plan.json is missing", artifact="rough_cut_plan")]
    if rough_cut.get("ok") is False or rough_cut.get("gaps"):
        for gap in rough_cut.get("gaps") or [{}]:
            issues.append(_issue(
                "rough_cut_gap",
                f"segment {gap.get('segment')} has no usable rough cut: {gap.get('reason')}",
                segment=gap.get("segment"),
                need_id=gap.get("need_id"),
            ))
    for clip in rough_cut.get("clips") or []:
        duration = _num(clip.get("duration_sec"))
        available = _num(clip.get("available_range_sec"), duration)
        start = _num(clip.get("start_sec"))
        if duration <= 0:
            issues.append(_issue(
                "invalid_clip_duration",
                f"segment {clip.get('segment')} duration must be positive",
                segment=clip.get("segment"),
                asset_id=clip.get("asset_id"),
            ))
        if start < 0:
            issues.append(_issue(
                "invalid_clip_start",
                f"segment {clip.get('segment')} start_sec must be non-negative",
                segment=clip.get("segment"),
                asset_id=clip.get("asset_id"),
            ))
        if available and duration - available > 0.001:
            issues.append(_issue(
                "clip_exceeds_available_range",
                f"segment {clip.get('segment')} duration exceeds available range",
                segment=clip.get("segment"),
                asset_id=clip.get("asset_id"),
            ))
    return issues


def _validate_timeline(rough_cut: dict, timeline: dict) -> list[dict]:
    issues = []
    if not timeline:
        return [_issue("missing_artifact", "timeline_build.json is missing", artifact="timeline_build")]
    rough_clips = rough_cut.get("clips") or []
    timeline_clips = timeline.get("clips") or []
    if len(rough_clips) != len(timeline_clips):
        issues.append(_issue(
            "timeline_clip_count_mismatch",
            f"rough cut has {len(rough_clips)} clips but timeline has {len(timeline_clips)}",
        ))
    for index, rough_clip in enumerate(rough_clips):
        if index >= len(timeline_clips):
            break
        rough_id = _clip_identity(rough_clip)
        timeline_id = _timeline_identity(timeline_clips[index])
        if rough_id != timeline_id:
            issues.append(_issue(
                "timeline_mismatch",
                f"timeline clip {index} does not match rough cut",
                index=index,
                rough_cut=rough_id,
                timeline=timeline_id,
            ))
    return issues


def _validate_handoff(rough_cut: dict, handoff: dict) -> list[dict]:
    if not handoff:
        return []
    rejected = set(handoff.get("rejected_asset_ids") or [])
    duplicates = set(handoff.get("duplicate_asset_ids") or [])
    invalid = sorted((rejected | duplicates).intersection(
        clip.get("asset_id") for clip in rough_cut.get("clips") or []
    ))
    if not invalid:
        return []
    return [_issue(
        "invalid_material_asset",
        "rough cut uses rejected or duplicate material assets",
        asset_ids=invalid,
    )]


def build_stage4_report(run_dir: Path) -> dict:
    rough_cut = _safe_load(run_dir / "rough_cut_plan.json")
    timeline = _safe_load(run_dir / "timeline_build.json")
    handoff = _safe_load(run_dir / "material_wall_handoff_report.json")
    clips = rough_cut.get("clips") or []
    timeline_clips = timeline.get("clips") or []

    issues = []
    issues.extend(_validate_rough_cut(rough_cut))
    issues.extend(_validate_timeline(rough_cut, timeline))
    issues.extend(_validate_handoff(rough_cut, handoff))

    return {
        "artifact_role": "stage4_build_smoke_report",
        "version": 1,
        "stage": "stage4_build",
        "ok": not issues,
        "clip_count": len(clips),
        "timeline_clip_count": len(timeline_clips),
        "total_duration_sec": rough_cut.get("total_duration_sec"),
        "asset_ids": [
            clip.get("asset_id")
            for clip in clips
            if clip.get("asset_id")
        ],
        "segments": [
            {
                "segment": clip.get("segment"),
                "asset_id": clip.get("asset_id"),
                "source_path": clip.get("source_path"),
                "start_sec": clip.get("start_sec"),
                "duration_sec": clip.get("duration_sec"),
            }
            for clip in clips
        ],
        "issues": issues,
        "read": [
            "rough_cut_plan.json",
            "timeline_build.json",
            "material_wall_handoff_report.json",
        ],
    }


def run_stage4_build_smoke(run_dir) -> dict:
    root = Path(run_dir).resolve()
    report = build_stage4_report(root)
    write_json(root / "stage4_build_smoke_report.json", report)
    return {
        "ok": bool(report.get("ok")),
        "run_dir": str(root),
        "report": report,
    }


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True, help="build-ready run folder to inspect")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)

    result = run_stage4_build_smoke(args.run)
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"ok={result['ok']} run_dir={result['run_dir']}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
