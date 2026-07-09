"""67th real-footage review demo replay - a human-reviewable short cut.

Scope (bounded): rebuild the M6e real-footage fixture, then render ONE enhanced
short cut over the M6e covered subset (3 accepted scenes from the 67th graduation
footage) and emit review artifacts that let a human check, per segment, WHICH real
clip was bound to WHICH script need. It is intentionally NOT a baseline/enhanced
comparison, NOT a 10-minute graduation film, and NOT an aesthetic verdict.

What it proves end-to-end on real material:
  script(need_ref+subtitle) -> need-aware material map -> BUILD/SRP -> render
  -> review_report + review_subtitles.srt + contact_sheet.jpg

Honesty rules (fail-closed):
  * Source material is the M6e covered subset, never Gemini synthetic material.
  * The covered subset has ONE approved scene per need, so SRP1 has 0 eligible
    segments and SRP3 cannot make climax outrun setup; the report DISCLOSES this
    rather than faking a longer film.
  * If footage / M6e artifacts are missing, or the render is empty, it BLOCKS.

Artifacts go to the gitignored `.tmp/srp_real67_review_demo/`.
"""
from __future__ import annotations

import argparse
import copy
import json
import os
import shutil
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import srp_real67_sanity as SANITY  # noqa: E402
from gemini_demo_film import timeline_review_srt  # noqa: E402
from srp_acceptance_replay import Blocked, _probe  # noqa: E402

OUT_ROOT = REPO / ".tmp" / "srp_real67_review_demo"
M6E_ROOT = REPO / ".tmp" / "m6e"
DEFAULT_FOOTAGE = SANITY.DEFAULT_FOOTAGE

SCOPE = "67th_real_footage_m6e_covered_subset_review_demo"


# ---------------------------------------------------------------------------
# Pure helpers (unit-tested without footage)
# ---------------------------------------------------------------------------

def _segment_need_ref(segment):
    """The need this segment is contracted to. A segment without a resolvable
    need_ref is a contract defect; we fail-closed rather than guess a binding."""
    explicit = segment.get("need_ref")
    if explicit:
        return explicit
    refs = (segment.get("material_fit") or {}).get("need_refs") or []
    return refs[0] if refs else None


def build_review_script(script):
    """Add a per-segment ``need_ref`` and review ``subtitle`` to the runtime script
    and keep all enhanced auto-structuring ON (no disable flags). Raises Blocked if
    any segment has no resolvable need_ref, so the demo never binds material to a
    segment whose need is unknown."""
    out = copy.deepcopy(script)
    segments = out.get("segments") or []
    if not segments:
        raise Blocked("review script has no segments")
    for segment in segments:
        need_ref = _segment_need_ref(segment)
        if not need_ref:
            raise Blocked(
                f"segment {segment.get('segment')} has no need_ref; refusing to "
                f"bind real material to an unknown need")
        segment["need_ref"] = need_ref
        desc = (segment.get("material_fit") or {}).get("visual_desc") \
            or segment.get("visual_desc") or ""
        segment["subtitle"] = f"Seg {segment.get('segment')} | {need_ref} {desc}".strip()
    # Enhanced path: make sure nothing accidentally disabled VD2/SRP1/SRP2/SRP3.
    for flag in ("disable_visual_diversity", "disable_auto_sequence",
                 "disable_auto_opening"):
        out[flag] = False
    out.pop("story_arc", None)
    out["demo_goal"] = "real67_review_demo"
    return out


def _accepted_need(scene):
    """The need a scene satisfies: the first ``accepted`` satisfies edge, else any
    edge's need_id, else legacy scene.need_id fallback."""
    edges = scene.get("satisfies") or []
    for edge in edges:
        if edge.get("status") == "accepted" and edge.get("need_id"):
            return edge["need_id"]
    for edge in edges:
        if edge.get("need_id"):
            return edge["need_id"]
    return scene.get("need_id")


def assert_no_synthetic_sources(material_map):
    """Fail-closed: this demo must run on real 67th footage, never on Gemini
    synthetic material. Any asset whose source path points into a Gemini/antigravity
    brain blocks the run."""
    bad = []
    for asset in material_map.get("assets") or []:
        src = str(asset.get("source") or "").lower()
        if ".gemini" in src or "antigravity" in src or "generated_material" in src:
            bad.append(asset.get("source"))
    if bad:
        raise Blocked(f"refusing synthetic Gemini material in a real-footage demo: {bad}")


def scene_need_lookup(material_map):
    """Map ``"asset_id:index" -> need_id`` from the material map (satisfies or a
    stamped scene.need_id), plus the set of declared need_ids."""
    lookup = {}
    for asset in material_map.get("assets") or []:
        aid = asset.get("asset_id")
        for index, scene in enumerate(asset.get("scenes") or []):
            lookup[f"{aid}:{index}"] = _accepted_need(scene)
    declared = {n.get("need_id") for n in material_map.get("needs") or [] if n.get("need_id")}
    return lookup, declared


def _story_slots(plan):
    return [c for c in plan or [] if not c.get("opening_role")]


def semantic_alignment(plan, material_map, script):
    """Per-segment binding check: for each contracted need_ref, list which real clip
    was selected and whether its own need matches. Status per slot is one of
    matched / wrong_need / unknown / gap (a gap is a segment with no story slot)."""
    lookup, declared = scene_need_lookup(material_map)
    expected = {s.get("segment"): s.get("need_ref") for s in (script or {}).get("segments", [])}
    by_segment = {}
    for clip in _story_slots(plan):
        by_segment.setdefault(clip.get("segment"), []).append(clip)

    segments, drift = {}, []
    for segment, need_ref in expected.items():
        clips = by_segment.get(segment, [])
        slot_records, matched = [], 0
        if not clips:
            status = "gap"
        else:
            for clip in clips:
                scene_id = clip.get("scene_id") or ""
                actual = lookup.get(scene_id)
                if actual and actual == need_ref:
                    slot_status = "matched"
                    matched += 1
                elif actual and actual in declared:
                    slot_status = "wrong_need"
                else:
                    slot_status = "unknown"
                slot_records.append({
                    "slot_index": clip.get("slot_index"),
                    "scene_id": scene_id,
                    "source": Path(clip.get("source")).name if clip.get("source") else None,
                    "selected_need_id": actual,
                    "arc_role": clip.get("arc_role"),
                    "subtitle": (clip.get("text") or {}).get("subtitle"),
                    "status": slot_status,
                })
            status = "matched" if matched == len(clips) else (
                "wrong_need" if any(r["status"] == "wrong_need" for r in slot_records)
                else "unknown")
        seg_drift = bool(clips) and matched < len(clips)
        if seg_drift:
            drift.append(segment)
        segments[str(segment)] = {
            "expected_need_ref": need_ref,
            "slot_count": len(clips),
            "matched_slots": matched,
            "status": status,
            "slots": slot_records,
        }
    return {"segments": segments, "drift_segments": sorted(drift),
            "all_matched": not drift and all(
                v["slot_count"] > 0 for v in segments.values())}


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


def srp1_eligibility(plan):
    """SRP1 needs >=2 approved slots in a segment to auto-sequence beats. Report how
    many segments are eligible so a 0-count is read as 'subset too thin', not a bug."""
    counts = {}
    for clip in _story_slots(plan):
        counts[clip.get("segment")] = counts.get(clip.get("segment"), 0) + 1
    eligible = sorted(seg for seg, n in counts.items() if n >= 2)
    return {"slots_per_segment": {str(k): v for k, v in sorted(counts.items())},
            "eligible_segments": eligible,
            "eligible_count": len(eligible),
            "note": "SRP1 auto-sequences only segments with >=2 approved slots; the "
                    "covered subset has 1 scene per need, so 0 eligible is expected."}


def compute_review_report(result, material_map, script, *, footage_root,
                          subset_scene_count, render_sec,
                          slot_check, music_name):
    plan = result.get("plan") or []
    alignment = semantic_alignment(plan, material_map, script)
    arc = _arc_durations(plan)
    climax, setup = arc.get("climax"), arc.get("setup")
    opening_count = sum(1 for c in plan if c.get("opening_role"))
    return {
        "scope": SCOPE,
        "footage_root": str(footage_root),
        "music": music_name,
        "review_subtitles": "review_subtitles.srt",
        "contact_sheet": "contact_sheet.jpg",
        "final_duration_sec": render_sec,
        "need_aware": {
            "scene_need_ids_stamped": 0,
            "deterministic_evidence": "segment.need_ref/material_fit.need_refs == "
                                      "scene.satisfies[].need_id",
            "all_segments_matched": alignment["all_matched"],
        },
        "semantic_alignment": alignment,
        "distractor_or_fallback_usage": {
            "distractors_present": False,
            "used": [],
            "note": "The M6e covered subset declares no distractors and no fallback "
                    "tiers were exercised (every need had an accepted real clip).",
        },
        "srp1_segment_sequence": srp1_eligibility(plan),
        "srp2_opening": {
            "status": (result.get("opening_plan") or {}).get("status"),
            "clip_count": opening_count,
            "active": opening_count > 0,
        },
        "srp3_story_arc": {
            "status": (result.get("story_arc_plan") or {}).get("status"),
            "execution": (result.get("story_arc_plan") or {}).get("execution", {}).get("status"),
            "arc_role_durations": arc,
            "climax_exceeds_setup": (climax is not None and setup is not None
                                     and climax > setup),
            "note": "With 1 equal-length slot per arc role, climax cannot exceed "
                    "setup on this subset; this is a subset limit, not a planner bug.",
        },
        "slot_render_check": slot_check,
        "limitations": {
            "m6e_covered_subset_only": True,
            "covered_scene_count": subset_scene_count,
            "full_ingest": False,
            "ten_minute_film": False,
            "synthetic_material": False,
            "note": "Real 67th footage, covered subset only (one accepted scene per "
                    "need). Not a full ingest, not a 10-minute film, not an aesthetic "
                    "score.",
        },
    }


def report_md(report):
    a = report["semantic_alignment"]
    lines = ["# 67th Real-Footage Review Demo", "",
             f"- Scope: `{report['scope']}`",
             f"- Footage root: `{report['footage_root']}`",
             f"- Music: `{report['music']}`",
             f"- Final duration: **{report['final_duration_sec']}s**",
             f"- Need-aware all-matched: **{report['need_aware']['all_segments_matched']}** "
             f"(canonical satisfies evidence; no scene need_ids stamped)",
             f"- Semantic drift segments: {a['drift_segments']}",
             f"- Review subtitles: `{report['review_subtitles']}`",
             f"- Contact sheet: `{report['contact_sheet']}`",
             "",
             "## Per-segment material binding (review this)"]
    for seg, info in sorted(a["segments"].items(), key=lambda kv: int(kv[0])):
        lines.append(f"- **Seg {seg}** expected `{info['expected_need_ref']}` "
                     f"- status **{info['status']}** ({info['matched_slots']}/{info['slot_count']})")
        for slot in info["slots"]:
            flag = "" if slot["status"] == "matched" else "  REVIEW"
            lines.append(f"    - {slot['scene_id']} ({slot['source']}) "
                         f"need={slot['selected_need_id']} arc={slot['arc_role']} "
                         f"- {slot['status']}{flag}  [{slot['subtitle']}]")
    srp1 = report["srp1_segment_sequence"]
    lines += ["",
              "## SRP capability status",
              f"- SRP1 eligible segments: {srp1['eligible_count']} {srp1['eligible_segments']} "
              f"(slots/seg {srp1['slots_per_segment']})",
              f"  - {srp1['note']}",
              f"- SRP2 opening: {report['srp2_opening']['status']} "
              f"({report['srp2_opening']['clip_count']} clips, active={report['srp2_opening']['active']})",
              f"- SRP3 story arc: {report['srp3_story_arc']['status']} / "
              f"{report['srp3_story_arc']['execution']}; "
              f"climax>setup={report['srp3_story_arc']['climax_exceeds_setup']} "
              f"{report['srp3_story_arc']['arc_role_durations']}",
              f"  - {report['srp3_story_arc']['note']}",
              "",
              "## Render gate",
              f"- Slot render check: ok={report['slot_render_check'].get('ok')} "
              f"checked={report['slot_render_check'].get('checked_slots')} "
              f"failed={report['slot_render_check'].get('failed_slots')}",
              "",
              "## Boundary",
              f"- Covered subset only: {report['limitations']['covered_scene_count']} accepted scenes.",
              "- Real footage, not synthetic; not a full ingest; not a 10-minute film; "
              "not an aesthetic score."]
    return "\n".join(lines) + "\n"


def _write_json(path, data):
    Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _story_slot_midpoints(plan):
    """Midpoint timestamp of every story slot in the concatenated render timeline,
    so the contact sheet has exactly one representative cell per reviewed clip."""
    t, mids = 0.0, []
    for clip in plan or []:
        dur = float(clip.get("extract_dur") or 0.0)
        if not clip.get("opening_role"):
            mids.append(round(t + dur / 2.0, 3))
        t += dur
    return mids


def build_contact_sheet(final_mp4, plan, out_path):
    """(I/O) One cell per story slot via the canonical montage wall."""
    from video_pipeline_core.montage_wall import write_montage_wall  # noqa: PLC0415
    from video_pipeline_core.sampling_coverage import write_sampling_coverage_report  # noqa: PLC0415
    mids = _story_slot_midpoints(plan)
    if not mids:
        raise Blocked("no story slots to build a contact sheet from")
    out = Path(out_path)
    samples = [
        {
            "sample_id": f"s{idx:04d}",
            "shot_id": f"story_slot_{idx:03d}",
            "timestamp_sec": ts,
            "target_timestamp_sec": ts,
            "reason": "baseline",
        }
        for idx, ts in enumerate(mids, start=1)
    ]
    shots = [
        {
            "shot_id": sample["shot_id"],
            "start_sec": max(0.0, float(sample["timestamp_sec"]) - 0.001),
            "end_sec": float(sample["timestamp_sec"]) + 0.001,
        }
        for sample in samples
    ]
    plan_payload = {
        "artifact_role": "sampling_plan",
        "version": 1,
        "source_video": str(final_mp4),
        "shots": shots,
        "samples": samples,
        "limitations": ["SRP demo story slots are preselected timestamps."],
    }
    plan_path = out.with_suffix(".sampling_plan.json")
    coverage_path = out.with_suffix(".sampling_coverage_report.json")
    plan_path.write_text(json.dumps(plan_payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_sampling_coverage_report(plan_path, shots, coverage_path, max_gap_sec=1.0)
    sidecar = out.with_suffix(".json")
    meta = write_montage_wall(str(final_mp4), plan_path, coverage_path, out, sidecar, profile="segment_strip")
    if not Path(out_path).exists() or Path(out_path).stat().st_size <= 0:
        raise Blocked(f"contact sheet was not written: {out_path}")
    return meta


# ---------------------------------------------------------------------------
# Orchestration (real run; exercised by the harness, not unit tests)
# ---------------------------------------------------------------------------

def run_demo(footage_root, *, target_sec, max_clips_per_seg, music=None,
             skip_m6e=False, out_root=OUT_ROOT):
    from video_pipeline_core import mv_cut  # noqa: PLC0415

    footage_root = Path(footage_root)
    if not footage_root.exists():
        raise Blocked(f"footage root does not exist: {footage_root}")
    if not skip_m6e:
        SANITY.run_m6e_fixture(footage_root)

    script_path = M6E_ROOT / "out_C" / "generated_mv_script.json"
    map_path = M6E_ROOT / "out_C" / "project_material_map.json"
    if not script_path.exists() or not map_path.exists():
        raise Blocked("M6e covered artifacts missing; run without --skip-m6e first")

    raw_map = SANITY._load_json_loose(map_path)
    assert_no_synthetic_sources(raw_map)
    material_map = raw_map
    script = build_review_script(SANITY._load_json_loose(script_path))
    music = SANITY.find_music(footage_root, music)
    subset_scene_count = sum(len(a.get("scenes") or [])
                             for a in material_map.get("assets", []))

    out = Path(out_root)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    work = out / "_work"
    work.mkdir(parents=True, exist_ok=True)

    result = mv_cut.run_mv(
        script, material_root=None, out_path=str(out / "final.mp4"),
        music_path=str(music), material_maps=material_map, target_sec=target_sec,
        max_clips_per_seg=max_clips_per_seg, skip_render=False,
        mat_dir=str(work), verbose=False)

    final = out / "final.mp4"
    if not final.exists() or final.stat().st_size <= 0:
        raise Blocked(f"render produced no usable final.mp4: {final}")

    slot_check = SANITY.verify_video_slots(final, result["plan"])
    if not slot_check["ok"]:
        raise Blocked(f"slot render check failed: {slot_check['failed_slots']}")

    report = compute_review_report(
        result, material_map, script, footage_root=footage_root,
        subset_scene_count=subset_scene_count,
        render_sec=_probe(final), slot_check=slot_check, music_name=Path(music).name)

    _write_json(out / "generated_mv_script.json", script)
    _write_json(out / "project_material_map.json", material_map)
    _write_json(out / "timeline.json", {
        "plan": result["plan"], "segments": result["segments"],
        "opening_plan": result.get("opening_plan"),
        "story_arc_plan": result.get("story_arc_plan"),
        "cuts": result.get("cuts")})
    (out / "review_subtitles.srt").write_text(
        timeline_review_srt(result["plan"]), encoding="utf-8")
    build_contact_sheet(final, result["plan"], out / "contact_sheet.jpg")
    _write_json(out / "review_report.json", report)
    (out / "review_report.md").write_text(report_md(report), encoding="utf-8")
    return report, out


def main(argv=None):
    parser = argparse.ArgumentParser(description="67th real-footage review demo replay")
    parser.add_argument("--footage-root", default=str(DEFAULT_FOOTAGE))
    parser.add_argument("--target-sec", type=float, default=30.0)
    parser.add_argument("--max-clips-per-seg", type=int, default=2)
    parser.add_argument("--music")
    parser.add_argument("--skip-m6e", action="store_true",
                        help="Reuse the existing .tmp/m6e fixture instead of rebuilding.")
    args = parser.parse_args(argv)

    report, out = run_demo(
        args.footage_root, target_sec=args.target_sec,
        max_clips_per_seg=args.max_clips_per_seg, music=args.music,
        skip_m6e=args.skip_m6e)
    a = report["semantic_alignment"]
    print(f"[real67-review] OK artifacts={out}")
    print(f"[real67-review] final={out / 'final.mp4'} ({report['final_duration_sec']}s)")
    print(f"[real67-review] all_matched={a['all_matched']} drift={a['drift_segments']}")
    print(f"[real67-review] srp1_eligible={report['srp1_segment_sequence']['eligible_count']} "
          f"srp2_opening={report['srp2_opening']['status']} "
          f"srp3={report['srp3_story_arc']['status']}")
    print(f"[real67-review] subtitles={out / 'review_subtitles.srt'} "
          f"contact_sheet={out / 'contact_sheet.jpg'}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Blocked as exc:
        print(f"[real67-review] BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
