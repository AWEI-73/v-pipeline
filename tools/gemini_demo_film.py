"""Enhanced-only Gemini demo film runner.

Runs the node-shaped flow over the controlled Gemini material:

script/needs -> project material map -> BUILD/SRP -> render -> review report.

This is not a baseline comparison and not a real-footage quality verdict. It is a
single enhanced demo to verify that an agent can fill parameters and drive the
existing pipeline from a material manifest into a rendered film.
"""
from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import srp_acceptance_replay as SRP  # noqa: E402

Blocked = SRP.Blocked
OUT_ROOT = REPO / ".tmp" / "gemini_demo_film"
DEFAULT_GEMINI_ROOT = Path(
    r"C:\Users\user\.gemini\antigravity\brain\b9af86b4-38e1-4748-890b-9e2c7d0a991b")
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")


def select_present_needs(assets, *, min_needs=3):
    present = {a.get("need_id") for a in assets if a.get("need_id") in SRP.NEED_THEME}
    ordered = [nid for nid in SRP.NEED_THEME if nid in present]
    if len(ordered) < min_needs:
        raise Blocked(f"only {len(ordered)} usable needs present (<{min_needs})")
    return ordered


def build_demo_script(needs_present, *, title="Training Graduation Demo"):
    """Build a shallow story script; BUILD/SRP chooses the actual shots."""
    script = SRP.build_script(needs_present, opening_title=title)
    for segment in script["segments"]:
        # Demo target is 60-90s. Keep montage energy, but ask allocation for
        # slightly longer approved shots so SRP1's 2-4 beat compiler does not
        # discard a large number of short slots and collapse the runtime.
        segment["pacing"] = {"preferred_shot_sec": [2.8, 3.4]}
    script["demo_goal"] = "enhanced_only_pipeline_flow"
    script["target_style"] = "energetic_training_graduation_montage"
    return script


def prepare_output_root(root=OUT_ROOT):
    root = Path(root)
    if root.exists():
        shutil.rmtree(root)
    root.mkdir(parents=True)
    return root


def _gen_music(path, dur):
    subprocess.run([
        FFMPEG, "-y", "-f", "lavfi", "-i",
        f"aevalsrc=sin(2*PI*110*t)*0.18 + sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.08)*0.55:"
        f"d={dur}:s=44100",
        str(path),
    ], capture_output=True, check=True)


def _probe(path):
    try:
        return round(float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)], text=True).strip()), 3)
    except Exception:
        return None


def _auto_sequence_segments(plan):
    return sorted({c.get("segment") for c in plan
                   if c.get("sequence_recipe_source") == "auto"})


def _arc_durations(plan):
    out = {}
    for clip in plan:
        if clip.get("opening_role"):
            continue
        role = clip.get("arc_role")
        if role:
            out[role] = round(out.get(role, 0.0) + float(clip.get("extract_dur") or 0.0), 3)
    return out


def compute_demo_report(result, *, asset_count, need_count, requested_target_sec,
                        render_sec, slot_check, assets=None):
    plan = result.get("plan") or []
    opening_count = sum(1 for c in plan if c.get("opening_role"))
    distractors = {a.get("asset_id"): a for a in (assets or []) if a.get("is_distractor")}
    used_distractors = []
    for clip in plan:
        scene_id = clip.get("scene_id") or ""
        asset_id = scene_id.rsplit(":", 1)[0]
        if asset_id in distractors:
            used_distractors.append({
                "asset_id": asset_id,
                "filename": distractors[asset_id].get("filename"),
                "segment": clip.get("segment"),
                "scene_id": scene_id,
                "opening_role": clip.get("opening_role"),
                "beat_role": clip.get("beat_role"),
            })
    return {
        "mode": "enhanced_only_gemini_demo",
        "target": {
            "requested_sec": requested_target_sec,
            "render_sec": render_sec,
            "plan_sec": round(sum(float(c.get("extract_dur") or 0.0) for c in plan), 3),
        },
        "assets": {"asset_count": asset_count, "need_count": need_count},
        "opening": {
            "status": (result.get("opening_plan") or {}).get("status"),
            "clip_count": opening_count,
        },
        "auto_sequence": {
            "count": len(_auto_sequence_segments(plan)),
            "segments": _auto_sequence_segments(plan),
        },
        "story_arc": {
            "status": (result.get("story_arc_plan") or {}).get("status"),
            "execution": (result.get("story_arc_plan") or {}).get("execution", {}).get("status"),
            "arc_role_durations": _arc_durations(plan),
        },
        "slot_render_check": slot_check,
        "distractor_usage": {
            "used": used_distractors,
            "used_count": len(used_distractors),
        },
        "limitations": {
            "synthetic_gemini_material": True,
            "not_real_footage_quality_verdict": True,
            "note": "This validates the node-shaped pipeline flow on controlled synthetic material.",
        },
    }


def report_md(report):
    lines = [
        "# Gemini Demo Film Report",
        "",
        f"- Mode: `{report['mode']}`",
        f"- Target: requested {report['target']['requested_sec']}s, "
        f"rendered {report['target']['render_sec']}s, plan {report['target'].get('plan_sec')}s",
        f"- Assets: {report['assets']['asset_count']} across "
        f"{report['assets']['need_count']} needs",
        f"- Opening: {report['opening']['status']} ({report['opening']['clip_count']} clips)",
        f"- Auto sequences: {report['auto_sequence']['count']} "
        f"{report['auto_sequence']['segments']}",
        f"- Story arc: {report['story_arc']['status']} / "
        f"{report['story_arc']['execution']} {report['story_arc']['arc_role_durations']}",
        f"- Slot render check: ok={report['slot_render_check'].get('ok')} "
        f"checked={report['slot_render_check'].get('checked_slots')} "
        f"failed={report['slot_render_check'].get('failed_slots')}",
        f"- Distractors used: {report.get('distractor_usage', {}).get('used', [])}",
        "",
        "## Boundary",
        "- Uses synthetic Gemini material, not 67th real footage.",
        "- This is not a real-footage quality verdict and not an aesthetic score.",
    ]
    return "\n".join(lines) + "\n"


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def run_demo(gemini_root, *, target_sec=75.0, music_sec=None, max_clips_per_seg=2,
             out_root=OUT_ROOT):
    from video_pipeline_core import mv_cut  # noqa: PLC0415

    gemini_root = Path(gemini_root)
    manifest_path = gemini_root / "generated_material_manifest.json"
    if not manifest_path.exists():
        raise Blocked(f"manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    assets, problems = SRP.resolve_assets(manifest, gemini_root)
    SRP.assert_declared_present(problems)
    needs = select_present_needs(assets)
    material_map = SRP.build_material_map(assets)
    script = build_demo_script(needs)

    out = prepare_output_root(out_root)
    music = out / "music.wav"
    _gen_music(music, music_sec or target_sec + 8.0)
    work = out / "_work"
    work.mkdir(parents=True, exist_ok=True)

    result = mv_cut.run_mv(
        script,
        material_root=None,
        out_path=str(out / "final.mp4"),
        music_path=str(music),
        material_maps=material_map,
        target_sec=target_sec,
        max_clips_per_seg=max_clips_per_seg,
        skip_render=False,
        mat_dir=str(work),
        verbose=False,
    )
    final = out / "final.mp4"
    if not final.exists() or final.stat().st_size <= 0:
        raise Blocked(f"render produced no usable final: {final}")

    slot_check = SRP.verify_slots(final, result["plan"])
    SRP.assert_slots(slot_check, "gemini-demo")

    report = compute_demo_report(
        result,
        asset_count=len(assets),
        need_count=len(needs),
        requested_target_sec=target_sec,
        render_sec=_probe(final),
        slot_check=slot_check,
        assets=assets,
    )

    _write_json(out / "generated_mv_script.json", script)
    _write_json(out / "project_material_map.json", material_map)
    _write_json(out / "timeline.json", {
        "plan": result["plan"],
        "segments": result["segments"],
        "opening_plan": result.get("opening_plan"),
        "story_arc_plan": result.get("story_arc_plan"),
        "cuts": result.get("cuts"),
    })
    _write_json(out / "review_report.json", report)
    (out / "review_report.md").write_text(report_md(report), encoding="utf-8")
    return report


def main(argv=None):
    parser = argparse.ArgumentParser(description="Run enhanced-only Gemini demo film")
    parser.add_argument("--gemini-root", default=str(DEFAULT_GEMINI_ROOT))
    parser.add_argument("--target-sec", type=float, default=75.0)
    parser.add_argument("--music-sec", type=float)
    parser.add_argument("--max-clips-per-seg", type=int, default=2)
    args = parser.parse_args(argv)
    report = run_demo(args.gemini_root, target_sec=args.target_sec,
                      music_sec=args.music_sec,
                      max_clips_per_seg=args.max_clips_per_seg)
    print(f"[gemini-demo] OK artifacts={OUT_ROOT}")
    print(f"[gemini-demo] final={OUT_ROOT / 'final.mp4'} ({report['target']['render_sec']}s)")
    print(f"[gemini-demo] opening={report['opening']['status']} "
          f"auto_seq={report['auto_sequence']['count']} "
          f"story_arc={report['story_arc']['status']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Blocked as exc:
        print(f"[gemini-demo] BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
