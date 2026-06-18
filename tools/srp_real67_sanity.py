"""67th real-footage SRP sanity replay.

This is a formalized version of the manual probe used after M6e. It first
rebuilds the M6e real-footage fixture, then renders the same covered subset twice:

* baseline: VD2/SRP1/SRP2/SRP3 disabled, map-ranked retrieval still enabled.
* enhanced: VD2/SRP1/SRP2/SRP3 enabled.

It is intentionally scoped as a sanity check, not a full acceptance test:
the source material is the M6e covered subset (3 accepted scenes), not the full
304-file ingest. Artifacts are written under `.tmp/srp_real67/`.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from srp_acceptance_replay import (  # noqa: E402
    Blocked,
    _probe,
    evaluate_slot,
    frame_descriptor,
    pearson,
    slot_windows,
    summarize_slot_records,
    timeline_signature,
)

OUT_ROOT = REPO / ".tmp" / "srp_real67"
M6E_ROOT = REPO / ".tmp" / "m6e"
DEFAULT_FOOTAGE = Path(r"C:\Users\user\Downloads\微電影素材\_整理後")
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")


def _load_json_loose(path):
    """Load JSON artifacts that may contain literal control chars from captions."""
    return json.loads(Path(path).read_text(encoding="utf-8"), strict=False)


def baseline_script(script):
    out = copy.deepcopy(script)
    out["disable_visual_diversity"] = True
    out["disable_auto_sequence"] = True
    out["disable_auto_opening"] = True
    out["story_arc"] = False
    return out


def enhanced_script(script):
    out = copy.deepcopy(script)
    out["disable_visual_diversity"] = False
    out["disable_auto_sequence"] = False
    out["disable_auto_opening"] = False
    out.pop("story_arc", None)
    return out


def find_music(footage_root, declared=None):
    """Find the 67th music file. A declared path wins; otherwise search the tree."""
    if declared is not None:
        p = Path(declared)
        if p.exists() and p.is_file() and p.stat().st_size > 0:
            return p
        raise Blocked(f"declared music path is not usable: {p}")
    root = Path(footage_root)
    candidates = [p for p in root.rglob("*.mp4")
                  if p.is_file() and p.stat().st_size > 0 and p.name.startswith("7")]
    if not candidates:
        raise Blocked(f"could not find 67th music under {root}")

    def score(p):
        text = f"{p.parent.name} {p.name}"
        return (
            1 if "音" in text or "music" in text.lower() else 0,
            1 if "感" in text or "收尾" in text else 0,
            -len(str(p)),
        )

    return sorted(candidates, key=score, reverse=True)[0]


def run_m6e_fixture(footage_root):
    """Rebuild M6e fixture from real footage; fail closed if it does not pass."""
    env = os.environ.copy()
    env["M6E_FOOTAGE"] = str(Path(footage_root))
    cmd = [sys.executable, str(REPO / "tools" / "m6e_acceptance.py")]
    result = subprocess.run(cmd, cwd=str(REPO), env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise Blocked("M6e fixture rebuild failed:\n"
                      f"STDOUT:\n{result.stdout[-4000:]}\n"
                      f"STDERR:\n{result.stderr[-4000:]}")
    return result


def _extract_frame(video, t, out_path):
    subprocess.run([FFMPEG, "-y", "-ss", f"{max(0.0, float(t)):.3f}",
                    "-i", str(video), "-frames:v", "1", str(out_path)],
                   capture_output=True)
    return out_path if out_path.exists() and out_path.stat().st_size > 0 else None


def _source_descriptors(clip, tmpdir, cache):
    src = clip.get("source")
    if not src:
        return []
    if clip.get("is_photo"):
        key = ("photo", src)
        if key not in cache:
            try:
                cache[key] = frame_descriptor(src)
            except Exception:
                cache[key] = None
        return [cache[key]] if cache[key] else []
    start = float(clip.get("extract_start") or 0.0)
    dur = max(0.0, float(clip.get("extract_dur") or 0.0))
    sample_times = [
        start,
        start + dur * 0.25,
        start + dur / 2.0,
        start + dur * 0.75,
        start + dur,
        start + 0.5,
        start + 1.0,
        start + 2.0,
    ]
    out = []
    seen = set()
    for t in sample_times:
        if t < 0:
            continue
        t = round(t, 3)
        if t in seen:
            continue
        seen.add(t)
        key = ("video", src, t)
        if key not in cache:
            frame = Path(tmpdir) / f"src_{abs(hash(key))}.png"
            extracted = _extract_frame(src, t, frame)
            try:
                cache[key] = frame_descriptor(str(extracted)) if extracted else None
            except Exception:
                cache[key] = None
        if cache[key]:
            out.append(cache[key])
    return out


def real67_slot_verdict(frame_desc, source_desc):
    """67th video-slot verdict.

    The controlled Gemini replay only used photos, where a low-variance final
    frame is usually a fake color card. The 67th real subset includes a legitimate
    bright/near-white source-video card; if the final frame strongly matches its
    own source frame, it should pass even when spatial stdev is below the generic
    photo threshold.
    """
    if isinstance(source_desc, list):
        candidates = [s for s in source_desc if s]
    else:
        candidates = [source_desc] if source_desc else []
    if candidates and frame_desc:
        source_desc = max(
            candidates,
            key=lambda s: pearson(frame_desc.get("gray") or [], s.get("gray") or []),
        )
    else:
        source_desc = None
    base = evaluate_slot(frame_desc, source_desc)
    if base.get("ok") or not frame_desc or not source_desc:
        return base
    corr = pearson(frame_desc.get("gray") or [], source_desc.get("gray") or [])
    if (frame_desc.get("stdev") or 0.0) >= 3.0 and corr >= 0.95:
        return {
            "ok": True,
            "stdev": round(frame_desc.get("stdev") or 0.0, 2),
            "best_correlation": round(corr, 3),
            "reason": "ok: low-variance but source-matched real footage frame",
        }
    base["best_correlation"] = round(corr, 3)
    return base


def actual_slot_windows(plan, segment_durations=None):
    """Map plan slots to final-render windows using actual rendered segment
    durations when available. Plan ``extract_dur`` can differ by a few frames after
    ffmpeg encoding; using real mvseg duration avoids sampling the wrong slot in
    long concatenations."""
    segment_durations = segment_durations or {}
    t, out = 0.0, []
    for c in plan:
        idx = c.get("slot_index")
        d = segment_durations.get(idx)
        if d is None or d <= 0:
            d = float(c.get("extract_dur") or 0.0)
        out.append((c, round(t, 3), round(t + d, 3), round(t + d / 2.0, 3)))
        t += d
    return out


def verify_video_slots(mp4, plan):
    """Slot-level render gate for video/photo sources.

    For each rendered slot, sample the final frame at the slot midpoint and compare
    it with the slot's own source frame/photo. This guards against foreign temp
    clips and solid-color cards without claiming aesthetic quality.
    """
    tmpdir = tempfile.mkdtemp()
    dur = _probe(mp4) or 0.0
    source_cache, records = {}, []
    seg_dir = Path(mp4).parent / "_work"
    segment_durations = {}
    for clip in plan:
        idx = clip.get("slot_index")
        seg = seg_dir / f"mvseg_{idx:03d}.mp4"
        if seg.exists():
            segment_durations[idx] = _probe(seg) or 0.0
    for clip, start, end, mid in actual_slot_windows(plan, segment_durations):
        t = min(mid, max(0.0, dur - 0.05)) if dur > 0 else mid
        final_frame = Path(tmpdir) / f"final_{clip.get('slot_index')}.png"
        extracted = _extract_frame(mp4, t, final_frame)
        frame_desc = frame_descriptor(str(extracted)) if extracted else None
        source_descs = []
        idx = clip.get("slot_index")
        seg = seg_dir / f"mvseg_{idx:03d}.mp4"
        if seg.exists() and segment_durations.get(idx, 0.0) > 0:
            seg_frame = Path(tmpdir) / f"seg_{idx}.png"
            seg_extracted = _extract_frame(seg, segment_durations[idx] / 2.0, seg_frame)
            if seg_extracted:
                try:
                    source_descs.append(frame_descriptor(str(seg_extracted)))
                except Exception:
                    pass
        if not source_descs:
            source_descs.extend(_source_descriptors(clip, tmpdir, source_cache))
        verdict = real67_slot_verdict(frame_desc, source_descs)
        records.append({
            "slot_index": clip.get("slot_index"),
            "segment": clip.get("segment"),
            "opening_role": clip.get("opening_role"),
            "beat_role": clip.get("beat_role"),
            "scene_id": clip.get("scene_id"),
            "source": Path(clip.get("source")).name if clip.get("source") else None,
            "sample_time": round(t, 3),
            "window_start": start,
            "window_end": end,
            **verdict,
        })
    return summarize_slot_records(records)


def _story_slots(plan):
    return [c for c in plan if not c.get("opening_role")]


def _auto_sequence_segments(plan):
    return sorted({c.get("segment") for c in _story_slots(plan)
                   if c.get("sequence_recipe_source") == "auto"})


def _arc_durations(plan):
    out = {}
    for clip in _story_slots(plan):
        role = clip.get("arc_role")
        if role:
            out[role] = round(out.get(role, 0.0) + float(clip.get("extract_dur") or 0.0), 3)
    return out


def compute_real67_report(baseline, enhanced, *, subset_scene_count,
                          baseline_render_sec, enhanced_render_sec,
                          slot_checks):
    b_plan, e_plan = baseline["plan"], enhanced["plan"]
    e_arc = _arc_durations(e_plan)
    return {
        "scope": "67th_real_footage_m6e_covered_subset_srp_sanity",
        "timelines_differ": timeline_signature(b_plan) != timeline_signature(e_plan),
        "durations": {
            "baseline_render_sec": baseline_render_sec,
            "enhanced_render_sec": enhanced_render_sec,
        },
        "cuts": {
            "baseline": baseline.get("cuts"),
            "enhanced": enhanced.get("cuts"),
        },
        "opening": {
            "baseline_status": (baseline.get("opening_plan") or {}).get("status"),
            "enhanced_status": (enhanced.get("opening_plan") or {}).get("status"),
            "baseline_count": sum(1 for c in b_plan if c.get("opening_role")),
            "enhanced_count": sum(1 for c in e_plan if c.get("opening_role")),
        },
        "auto_sequence": {
            "baseline_count": len(_auto_sequence_segments(b_plan)),
            "enhanced_count": len(_auto_sequence_segments(e_plan)),
            "enhanced_segments": _auto_sequence_segments(e_plan),
        },
        "story_arc": {
            "baseline_status": (baseline.get("story_arc_plan") or {}).get("status"),
            "enhanced_status": (enhanced.get("story_arc_plan") or {}).get("status"),
            "enhanced_execution": (enhanced.get("story_arc_plan") or {}).get("execution", {}).get("status"),
            "arc_role_durations": e_arc,
            "climax_exceeds_setup": (
                e_arc.get("climax") is not None
                and e_arc.get("setup") is not None
                and e_arc["climax"] > e_arc["setup"]
            ),
        },
        "slot_render_checks": slot_checks,
        "limitations": {
            "m6e_covered_subset_only": True,
            "covered_scene_count": subset_scene_count,
            "full_ingest": False,
            "note": "This sanity uses the M6e covered subset, not a full 304-file ingest "
                    "and not an aesthetic judgement.",
        },
    }


def report_md(report):
    lines = ["# 67th Real-Footage SRP Sanity", ""]
    lines += [
        f"- Timelines differ: **{report['timelines_differ']}**",
        f"- Baseline render: {report['durations']['baseline_render_sec']}s",
        f"- Enhanced render: {report['durations']['enhanced_render_sec']}s",
        f"- Opening enhanced status: {report['opening']['enhanced_status']} "
        f"({report['opening'].get('enhanced_count', 0)} clip(s))",
        f"- Auto sequence enhanced count: {report['auto_sequence']['enhanced_count']} "
        f"{report['auto_sequence']['enhanced_segments']}",
        f"- Story arc enhanced status: {report['story_arc']['enhanced_status']} / "
        f"{report['story_arc'].get('enhanced_execution')}",
        f"- Climax > setup: {report['story_arc'].get('climax_exceeds_setup')} "
        f"{report['story_arc'].get('arc_role_durations')}",
        "",
        "## Slot Render Checks",
    ]
    for name in ("baseline", "enhanced"):
        check = report["slot_render_checks"].get(name, {})
        lines.append(f"- **{name}**: ok={check.get('ok')} checked="
                     f"{check.get('checked_slots')} failed={check.get('failed_slots')}")
    lim = report["limitations"]
    lines += [
        "",
        "## Boundary",
        f"- This is a covered subset sanity: {lim['m6e_covered_subset_only']} "
        f"({lim['covered_scene_count']} accepted scenes).",
        "- It is not a full 304-file ingest and not an aesthetic score.",
    ]
    return "\n".join(lines) + "\n"


def _serialize(result):
    return {
        "plan": result["plan"],
        "segments": result["segments"],
        "opening_plan": result.get("opening_plan"),
        "story_arc_plan": result.get("story_arc_plan"),
        "cuts": result.get("cuts"),
    }


def _run_variant(name, script, material_map, music, target_sec, max_clips):
    from video_pipeline_core import mv_cut  # noqa: PLC0415

    out_dir = OUT_ROOT / name
    work = out_dir / "_work"
    out_dir.mkdir(parents=True, exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    return mv_cut.run_mv(
        script,
        material_root=None,
        out_path=str(out_dir / "final.mp4"),
        music_path=str(music),
        material_maps=material_map,
        target_sec=target_sec,
        max_clips_per_seg=max_clips,
        skip_render=False,
        mat_dir=str(work),
        verbose=False,
    )


def main(argv=None):
    parser = argparse.ArgumentParser(description="67th real-footage SRP sanity replay")
    parser.add_argument("--footage-root", default=str(DEFAULT_FOOTAGE))
    parser.add_argument("--target-sec", type=float, default=14.0)
    parser.add_argument("--max-clips-per-seg", type=int, default=2)
    parser.add_argument("--music")
    parser.add_argument("--skip-m6e", action="store_true",
                        help="Reuse existing .tmp/m6e fixture instead of rebuilding it.")
    args = parser.parse_args(argv)

    footage_root = Path(args.footage_root)
    if not footage_root.exists():
        raise Blocked(f"footage root does not exist: {footage_root}")
    if not args.skip_m6e:
        run_m6e_fixture(footage_root)

    script_path = M6E_ROOT / "out_C" / "generated_mv_script.json"
    map_path = M6E_ROOT / "out_C" / "project_material_map.json"
    if not script_path.exists() or not map_path.exists():
        raise Blocked("M6e covered artifacts are missing; run without --skip-m6e first")

    script = _load_json_loose(script_path)
    material_map = _load_json_loose(map_path)
    music = find_music(footage_root, args.music)
    subset_scene_count = sum(len(asset.get("scenes") or [])
                             for asset in material_map.get("assets", []))

    if OUT_ROOT.exists():
        shutil.rmtree(OUT_ROOT)
    OUT_ROOT.mkdir(parents=True)

    baseline = _run_variant("baseline", baseline_script(script), material_map,
                            music, args.target_sec, args.max_clips_per_seg)
    enhanced = _run_variant("enhanced", enhanced_script(script), material_map,
                            music, args.target_sec, args.max_clips_per_seg)

    for name, result in (("baseline", baseline), ("enhanced", enhanced)):
        (OUT_ROOT / name / "timeline.json").write_text(
            json.dumps(_serialize(result), ensure_ascii=False, indent=2),
            encoding="utf-8")

    base_mp4 = OUT_ROOT / "baseline" / "final.mp4"
    enh_mp4 = OUT_ROOT / "enhanced" / "final.mp4"
    for p in (base_mp4, enh_mp4):
        if not p.exists() or p.stat().st_size <= 0:
            raise Blocked(f"render did not produce a usable file: {p}")

    slot_checks = {
        "baseline": verify_video_slots(base_mp4, baseline["plan"]),
        "enhanced": verify_video_slots(enh_mp4, enhanced["plan"]),
    }
    for name, check in slot_checks.items():
        if not check["ok"]:
            raise Blocked(f"{name} slot render check failed: {check['failed_slots']}")

    report = compute_real67_report(
        baseline,
        enhanced,
        subset_scene_count=subset_scene_count,
        baseline_render_sec=_probe(base_mp4),
        enhanced_render_sec=_probe(enh_mp4),
        slot_checks=slot_checks,
    )
    if not report["timelines_differ"]:
        raise Blocked("enhanced timeline did not differ from baseline")

    (OUT_ROOT / "comparison_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_ROOT / "comparison_report.md").write_text(report_md(report), encoding="utf-8")

    print(f"[srp-real67] OK artifacts={OUT_ROOT}")
    print(f"[srp-real67] baseline={base_mp4} ({report['durations']['baseline_render_sec']}s)")
    print(f"[srp-real67] enhanced={enh_mp4} ({report['durations']['enhanced_render_sec']}s)")
    print(f"[srp-real67] opening={report['opening']['enhanced_status']} "
          f"auto_seq={report['auto_sequence']['enhanced_count']} "
          f"story_arc={report['story_arc']['enhanced_status']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Blocked as exc:
        print(f"[srp-real67] BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
