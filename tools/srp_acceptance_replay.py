"""Controlled SRP Acceptance Replay — reproducible BUILD-thickness validation.

Drives `run_mv` TWICE over the SAME controlled Gemini material map / script /
music / target_sec:

  * baseline  — SRP1/SRP2/SRP3/VD2 auto structuring OFF (existing disable flags),
                but map-ranked retrieval + photo renderability kept (so both runs
                edit the same real photos).
  * enhanced  — VD2 + SRP1 + SRP2 + SRP3 ON.

It renders both with real ffmpeg, writes both timelines, and emits a comparison
report (json + md) that attributes which capability actually changed the
timeline/render. It does NOT score aesthetics; it produces an objective viewing
checklist. If the Gemini material is missing / unreadable / insufficient to form a
fair baseline↔enhanced pair, it BLOCKS (non-zero exit) rather than faking success.

This is NOT a unit test and adds NO new editing capability — it only composes the
existing M6 + VD2 + Photo renderability + SRP1/SRP2/SRP3/AR1 path. Artifacts go to
the gitignored `.tmp/srp_acceptance/`; the Gemini photos are never copied/committed.

Run:
  python tools/srp_acceptance_replay.py \
      --gemini-root "C:\\Users\\user\\.gemini\\antigravity\\brain\\b9af86b4-...-...""
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))

OUT_ROOT = REPO / ".tmp" / "srp_acceptance"
FFMPEG = os.environ.get("FFMPEG", "ffmpeg")
FFPROBE = os.environ.get("FFPROBE", "ffprobe")

# Deterministic per-need theme token (a single \w token, so material_retrieval's
# text score routes each segment to its need's assets and ties within a need).
NEED_THEME = {
    "N01": "morning_assembly",
    "N02": "endurance_run",
    "N03": "cliff_rope_rescue",
    "N04": "stretcher_carry",
    "N05": "night_forest_search",
    "N06": "final_exam",
    "N07": "graduation_ceremony",
}
NEED_DESC = {
    "N01": "morning_assembly trainees gear up at dawn",
    "N02": "endurance_run team running mountain path",
    "N03": "cliff_rope_rescue climbing and rope work",
    "N04": "stretcher_carry team carrying casualty down",
    "N05": "night_forest_search flashlight search at night",
    "N06": "final_exam high pressure rescue operation",
    "N07": "graduation_ceremony certificate and group photo",
}


class Blocked(Exception):
    """Raised when the controlled material cannot form a fair acceptance pair."""


# ---------------------------------------------------------------------------
# Material map / script construction (pure, unit-testable)
# ---------------------------------------------------------------------------

def _need_of_similar(filename):
    """Map an `intentionally_similar_to` filename (e.g. n01_assembly_wide_01.png)
    to its need theme, so a near-duplicate distractor competes in that need."""
    prefix = str(filename or "")[:3].lower()
    if len(prefix) == 3 and prefix[0] == "n" and prefix[1:].isdigit():
        return f"N{prefix[1:]}"
    return None


def asset_theme(entry):
    """Theme token for an asset: its need theme, or (for a near-duplicate
    distractor) the theme of the asset it imitates, else None (off-topic)."""
    nid = entry.get("need_id")
    if nid in NEED_THEME:
        return NEED_THEME[nid]
    sim_need = _need_of_similar(entry.get("intentionally_similar_to"))
    if sim_need in NEED_THEME:
        return NEED_THEME[sim_need]
    return None


def build_caption(entry):
    """Searchable caption: theme token (when on-topic) + subject. Off-topic
    distractors get only their subject, so they score 0 for every segment."""
    theme = asset_theme(entry)
    subject = str(entry.get("subject") or "").replace("_", " ").strip()
    return f"{theme} {subject}".strip() if theme else (subject or "untitled")


def resolve_assets(manifest, gemini_root):
    """Resolve every manifest entry to an absolute, readable, non-empty path.
    Returns (assets, problems): assets are usable asset records; problems lists
    unreadable/missing files (reported, never silently dropped into success)."""
    gemini_root = Path(gemini_root)
    assets, problems = [], []
    for entry in manifest:
        fn = entry.get("filename")
        if not fn:
            problems.append({"filename": fn, "reason": "missing filename"})
            continue
        path = (gemini_root / fn).resolve()
        if not path.exists():
            problems.append({"filename": fn, "reason": "file not found"})
            continue
        if path.stat().st_size <= 0:
            problems.append({"filename": fn, "reason": "empty file"})
            continue
        asset_id = Path(fn).stem
        assets.append({
            "asset_id": asset_id,
            "filename": fn,
            "source": str(path),
            "need_id": entry.get("need_id"),
            "theme": asset_theme(entry),
            "caption": build_caption(entry),
            "visual_family": entry.get("visual_family"),
            "angle_scale": entry.get("angle_scale"),
            "asset_type": "photo",
            "must_have": bool(entry.get("must_have")),
            "is_distractor": entry.get("need_id") == "DISTRACTOR",
        })
    return assets, problems


def build_material_map(assets):
    """Build a canonical project_material_map (one photo scene per asset). No new
    schema — exactly the shape `expand_project_material_map` already accepts."""
    out = []
    for a in assets:
        out.append({
            "asset_id": a["asset_id"],
            "source": a["source"],
            "asset_type": "photo",
            "scenes": [{
                "start": 0.0, "end": 0.0,
                "caption": a["caption"],
                "visual_family": a["visual_family"],
                "angle_scale": a["angle_scale"],
            }],
        })
    return {"artifact_role": "project_material_map", "version": 1, "assets": out}


def build_script(needs_present, *, opening_title="期末結訓回顧"):
    """One montage segment per present need (N01..N07 order). visual_desc carries
    the need theme token so retrieval routes each segment to its need's assets.
    A MANUAL `pace: fast` (director SPEC, not an auto planner) makes each chapter a
    multi-shot montage in BOTH variants, so VD2/SRP1 have room to act independently
    of SRP3 — keeping per-capability attribution honest."""
    segments = []
    for i, nid in enumerate(needs_present, start=1):
        segments.append({
            "segment": i,
            "need_ref": nid,
            "visual_desc": NEED_DESC.get(nid, nid),
            "audio_role": "music",
            "pace": "fast",
        })
    return {"segments": segments, "title": opening_title,
            "opening_title": opening_title}


def variant_script(script, *, vd2, srp1, srp2, srp3):
    """Toggle the four auto-structuring capabilities via the minimal disable flags
    (map-ranked retrieval + photo renderability always stay on)."""
    import copy
    s = copy.deepcopy(script)
    s["disable_visual_diversity"] = not vd2
    s["disable_auto_sequence"] = not srp1
    s["disable_auto_opening"] = not srp2
    if not srp3:
        s["story_arc"] = False
    return s


def baseline_script(script):
    return variant_script(script, vd2=False, srp1=False, srp2=False, srp3=False)


def enhanced_script(script):
    return variant_script(script, vd2=True, srp1=True, srp2=True, srp3=True)


# ---------------------------------------------------------------------------
# Report computation (pure, unit-testable)
# ---------------------------------------------------------------------------

def _story_slots(plan):
    return [c for c in plan if not c.get("opening_role")]


def _round(x):
    return round(float(x or 0.0), 3)


def seg_durations(plan):
    out = {}
    for c in _story_slots(plan):
        sid = c.get("segment")
        out[sid] = _round(out.get(sid, 0.0) + float(c.get("extract_dur") or 0.0))
    return out


def consecutive_family_repeats(plan):
    """Count adjacent story slots sharing a visual_family (lower = more diverse)."""
    fams = [c.get("visual_family") for c in _story_slots(plan)]
    return sum(1 for a, b in zip(fams, fams[1:]) if a and a == b)


def photo_video_counts(plan):
    photo = sum(1 for c in plan if c.get("is_photo"))
    return {"photo": photo, "video": len(plan) - photo, "total": len(plan)}


def gap_count(segments):
    return sum(1 for e in segments
               if e.get("picked_scores") in ([], ["GAP"], ["GAP".lower()])
               or e.get("clips_found") == 0)


def selected_scene_ids_by_segment(plan):
    out = {}
    for c in _story_slots(plan):
        out.setdefault(c.get("segment"), set()).add(c.get("scene_id"))
    return out


def auto_sequence_segments(plan):
    return sorted({c.get("segment") for c in _story_slots(plan)
                   if c.get("sequence_recipe_source") == "auto"})


def opening_clip_count(plan):
    return sum(1 for c in plan if c.get("opening_role"))


def arc_role_durations(plan):
    """Sum story duration per arc_role (from the stamped slot trace)."""
    out = {}
    for c in _story_slots(plan):
        role = c.get("arc_role")
        if role:
            out[role] = _round(out.get(role, 0.0) + float(c.get("extract_dur") or 0.0))
    return out


def timeline_signature(plan):
    """A comparable signature of the timeline: ordered tuples of
    (segment, scene_id, dur, beat_role, opening_role). beat_role/opening_role are
    included so a structural change (SRP1 beat sequencing / SRP2 opening) is
    captured even when the picked scene_ids/durations are unchanged."""
    return [[c.get("segment"), c.get("scene_id"), _round(c.get("extract_dur")),
             c.get("beat_role"), c.get("opening_role")] for c in plan]


def compute_report(baseline, enhanced, assets, *, baseline_probe=None,
                   enhanced_probe=None, isolations=None):
    """Build the comparison report dict from the two rendered run_mv results plus
    optional single-capability isolation results (planning-only) for HONEST
    per-capability attribution: a capability is `active` iff toggling ONLY it on
    top of the baseline changes the timeline signature."""
    b_plan, e_plan = baseline["plan"], enhanced["plan"]
    b_segdur, e_segdur = seg_durations(b_plan), seg_durations(e_plan)
    isolations = isolations or {}
    b_sig = timeline_signature(b_plan)
    e_sig = timeline_signature(e_plan)

    def _isolated_diff(cap):
        res = isolations.get(cap)
        if res is None:
            return None
        return timeline_signature(res["plan"]) != b_sig

    # VD2: per-segment selected scene_id SETS differing (baseline vs +VD2-only)
    vd2_res = isolations.get("VD2")
    vd2_changed_segments = []
    if vd2_res is not None:
        b_sel = selected_scene_ids_by_segment(b_plan)
        v_sel = selected_scene_ids_by_segment(vd2_res["plan"])
        vd2_changed_segments = sorted(
            s for s in set(b_sel) | set(v_sel) if b_sel.get(s) != v_sel.get(s))

    e_arc = arc_role_durations(e_plan)
    climax = e_arc.get("climax")
    setup = e_arc.get("setup")

    capabilities = {
        "VD2_visual_diversity": {
            "active": bool(_isolated_diff("VD2")),
            "evidence": (f"+VD2-only changes selection in segments "
                         f"{vd2_changed_segments}" if vd2_changed_segments
                         else "+VD2-only did not change selection (no same-tier tie "
                              "resolved differently on this material)"),
        },
        "SRP1_segment_sequence": {
            "active": bool(_isolated_diff("SRP1")),
            "evidence": f"+SRP1-only auto beat sequences in segments "
                        f"{auto_sequence_segments((isolations.get('SRP1') or enhanced)['plan'])}; "
                        f"enhanced sequences in {auto_sequence_segments(e_plan)}",
        },
        "SRP2_opening": {
            "active": bool(_isolated_diff("SRP2")),
            "evidence": f"opening clips: baseline={opening_clip_count(b_plan)}, "
                        f"+SRP2-only={opening_clip_count((isolations.get('SRP2') or enhanced)['plan'])}, "
                        f"enhanced={opening_clip_count(e_plan)}",
        },
        "SRP3_story_arc": {
            "active": bool(_isolated_diff("SRP3")),
            "evidence": f"enhanced climax_duration={climax} vs setup_duration={setup}",
        },
    }

    def _used(plan):
        return sorted({c.get("scene_id", "").rsplit(":", 1)[0]
                       for c in _story_slots(plan) if c.get("scene_id")})

    return {
        "material": {
            "asset_count": len(assets),
            "needs": sorted({a["need_id"] for a in assets if a["need_id"]}),
            "distractors": [a["filename"] for a in assets if a["is_distractor"]],
            "used_assets_baseline": _used(b_plan),
            "used_assets_enhanced": _used(e_plan),
            "family_distribution": _distribution(assets, "visual_family"),
            "angle_distribution": _distribution(assets, "angle_scale"),
            "asset_type_distribution": _distribution(assets, "asset_type"),
            "assets": [{"asset_id": a["asset_id"], "need_id": a["need_id"],
                        "visual_family": a["visual_family"],
                        "angle_scale": a["angle_scale"],
                        "asset_type": a["asset_type"],
                        "is_distractor": a["is_distractor"]} for a in assets],
        },
        "total_duration": {
            "baseline_plan_sec": _round(sum(b_segdur.values())
                                        + sum(c.get("extract_dur") or 0
                                              for c in b_plan if c.get("opening_role"))),
            "enhanced_plan_sec": _round(sum(_round(c.get("extract_dur")) for c in e_plan)),
            "baseline_render_sec": baseline_probe,
            "enhanced_render_sec": enhanced_probe,
        },
        "story_segment_allocation": {
            "baseline": b_segdur, "enhanced": e_segdur,
        },
        "opening_inserted": {
            "baseline": opening_clip_count(b_plan) > 0,
            "enhanced": opening_clip_count(e_plan) > 0,
            "enhanced_opening_plan": (enhanced.get("opening_plan") or {}).get("status"),
        },
        "auto_sequence_count": {
            "baseline": len(auto_sequence_segments(b_plan)),
            "enhanced": len(auto_sequence_segments(e_plan)),
            "enhanced_segments": auto_sequence_segments(e_plan),
        },
        "story_arc_plan": {
            "baseline_status": (baseline.get("story_arc_plan") or {}).get("status"),
            "enhanced_status": (enhanced.get("story_arc_plan") or {}).get("status"),
            "enhanced_execution": (enhanced.get("story_arc_plan") or {}).get("execution", {}).get("status"),
            "enhanced_roles": [(h.get("segment_ref"), h.get("arc_role"))
                               for h in (enhanced.get("story_arc_plan") or {}).get("segment_hints", [])],
        },
        "visual_family_consecutive_repeats": {
            "baseline": consecutive_family_repeats(b_plan),
            "enhanced": consecutive_family_repeats(e_plan),
        },
        "photo_video": {
            "baseline": photo_video_counts(b_plan),
            "enhanced": photo_video_counts(e_plan),
        },
        "gap_count": {
            "baseline": gap_count(baseline["segments"]),
            "enhanced": gap_count(enhanced["segments"]),
        },
        "srp3_climax_vs_setup": {
            "climax_duration": climax, "setup_duration": setup,
            "climax_exceeds_setup": (climax is not None and setup is not None
                                     and climax > setup),
            "arc_role_durations": e_arc,
        },
        "timelines_differ": b_sig != e_sig,
        "capabilities_that_changed_build": capabilities,
        "viewing_checklist": [
            "Does the enhanced cut open with a hook montage before the story? "
            f"(opening clips: {opening_clip_count(e_plan)})",
            "Within a chapter, do shots vary in angle/subject rather than repeat? "
            f"(consecutive same-family: enhanced={consecutive_family_repeats(e_plan)}, "
            f"baseline={consecutive_family_repeats(b_plan)})",
            "Do the climax chapters feel longer / denser than the setup? "
            f"(climax={climax}s vs setup={setup}s)",
            "Do per-chapter shots progress (context -> action -> payoff) in enhanced? "
            f"(auto sequences: {auto_sequence_segments(e_plan)})",
            "Are both cuts free of off-topic / GAP filler? "
            f"(GAP: baseline={gap_count(baseline['segments'])}, "
            f"enhanced={gap_count(enhanced['segments'])})",
        ],
    }


def _distribution(assets, key):
    out = {}
    for a in assets:
        out[a.get(key)] = out.get(a.get(key), 0) + 1
    return out


def report_md(report):
    L = ["# Controlled SRP Acceptance Replay — Comparison Report", ""]
    m = report["material"]
    L += [f"- Assets used: **{m['asset_count']}** across needs {m['needs']}",
          f"- Distractors present: {m['distractors']}",
          f"- visual_family distribution: {m['family_distribution']}",
          f"- angle_scale distribution: {m['angle_distribution']}",
          f"- asset_type distribution: {m['asset_type_distribution']}", ""]
    td = report["total_duration"]
    L += ["## Total duration",
          f"- baseline plan: {td['baseline_plan_sec']}s  render: {td['baseline_render_sec']}s",
          f"- enhanced plan: {td['enhanced_plan_sec']}s  render: {td['enhanced_render_sec']}s", ""]
    L += ["## Story segment duration allocation",
          f"- baseline: {report['story_segment_allocation']['baseline']}",
          f"- enhanced: {report['story_segment_allocation']['enhanced']}", ""]
    L += ["## Capability effects (did BUILD actually change?)"]
    for name, cap in report["capabilities_that_changed_build"].items():
        L.append(f"- **{name}**: {'ACTIVE' if cap['active'] else 'no observable effect'} "
                 f"— {cap['evidence']}")
    L += ["",
          f"- **Timelines differ (baseline vs enhanced):** "
          f"{report['timelines_differ']}",
          f"- Opening inserted: baseline={report['opening_inserted']['baseline']}, "
          f"enhanced={report['opening_inserted']['enhanced']}",
          f"- Auto sequences: baseline={report['auto_sequence_count']['baseline']}, "
          f"enhanced={report['auto_sequence_count']['enhanced']} "
          f"{report['auto_sequence_count']['enhanced_segments']}",
          f"- story_arc_plan: baseline={report['story_arc_plan']['baseline_status']}, "
          f"enhanced={report['story_arc_plan']['enhanced_status']} "
          f"/ exec={report['story_arc_plan']['enhanced_execution']}",
          f"- SRP3 climax vs setup: {report['srp3_climax_vs_setup']}",
          f"- visual_family consecutive repeats: "
          f"baseline={report['visual_family_consecutive_repeats']['baseline']}, "
          f"enhanced={report['visual_family_consecutive_repeats']['enhanced']}",
          f"- photo/video: baseline={report['photo_video']['baseline']}, "
          f"enhanced={report['photo_video']['enhanced']}",
          f"- GAP: baseline={report['gap_count']['baseline']}, "
          f"enhanced={report['gap_count']['enhanced']}", ""]
    L += ["## Viewing checklist (objective — no aesthetic score)"]
    for item in report["viewing_checklist"]:
        L.append(f"- [ ] {item}")
    L.append("")
    return "\n".join(L)


# ---------------------------------------------------------------------------
# Orchestration (I/O — exercised by the manual replay, not unit tests)
# ---------------------------------------------------------------------------

def _gen_music(path, dur):
    subprocess.run([FFMPEG, "-y", "-f", "lavfi", "-i",
                    f"aevalsrc=sin(2*PI*440*t)*lt(mod(t\\,0.5)\\,0.06):d={dur}:s=44100",
                    str(path)], capture_output=True, check=True)


def _probe(path):
    try:
        return round(float(subprocess.check_output(
            [FFPROBE, "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", str(path)], text=True).strip()), 3)
    except Exception:
        return None


def _serialize_timeline(result):
    return {
        "plan": result["plan"],
        "segments": result["segments"],
        "opening": result.get("opening"),
        "opening_plan": result.get("opening_plan"),
        "ending": result.get("ending"),
        "story_arc_plan": result.get("story_arc_plan"),
        "cuts": result.get("cuts"),
    }


def main(argv=None):
    ap = argparse.ArgumentParser(description="Controlled SRP acceptance replay")
    ap.add_argument("--gemini-root", required=True)
    ap.add_argument("--target-sec", type=float, default=21.0)
    ap.add_argument("--music-sec", type=float, default=26.0)
    ap.add_argument("--max-clips-per-seg", type=int, default=2)
    args = ap.parse_args(argv)

    from video_pipeline_core import mv_cut

    root = Path(args.gemini_root)
    manifest_path = root / "generated_material_manifest.json"
    if not manifest_path.exists():
        raise Blocked(f"manifest not found: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    assets, problems = resolve_assets(manifest, root)
    needs_present = [n for n in NEED_THEME if any(a["need_id"] == n for a in assets)]
    if len(needs_present) < 3:
        raise Blocked(f"only {len(needs_present)} usable needs (<3); cannot form an "
                      f"arc. problems={problems}")
    usable_needs = [n for n in needs_present
                    if sum(1 for a in assets if a["need_id"] == n) >= 1]
    if len(usable_needs) < 3:
        raise Blocked(f"insufficient per-need material; problems={problems}")

    material_map = build_material_map(assets)
    script = build_script(needs_present)

    out = OUT_ROOT
    (out / "baseline").mkdir(parents=True, exist_ok=True)
    (out / "enhanced").mkdir(parents=True, exist_ok=True)
    music = out / "music.wav"
    _gen_music(music, args.music_sec)

    common = dict(material_root=None, music_path=str(music),
                  material_maps=material_map, target_sec=args.target_sec,
                  max_clips_per_seg=args.max_clips_per_seg, verbose=False)

    # Rendered pair: baseline (all off) and enhanced (all on).
    base_res = mv_cut.run_mv(baseline_script(script), out_path=str(out / "baseline" / "final.mp4"),
                             skip_render=False, **common)
    enh_res = mv_cut.run_mv(enhanced_script(script), out_path=str(out / "enhanced" / "final.mp4"),
                            skip_render=False, **common)

    # Planning-only isolation runs (no render) for honest per-capability attribution.
    toggles = {"VD2": dict(vd2=True, srp1=False, srp2=False, srp3=False),
               "SRP1": dict(vd2=False, srp1=True, srp2=False, srp3=False),
               "SRP2": dict(vd2=False, srp1=False, srp2=True, srp3=False),
               "SRP3": dict(vd2=False, srp1=False, srp2=False, srp3=True)}
    isolations = {cap: mv_cut.run_mv(variant_script(script, **flags),
                                     out_path=str(out / f"_iso_{cap}.mp4"),
                                     skip_render=True, **common)
                  for cap, flags in toggles.items()}

    for name, res in (("baseline", base_res), ("enhanced", enh_res)):
        (out / name / "timeline.json").write_text(
            json.dumps(_serialize_timeline(res), ensure_ascii=False, indent=2),
            encoding="utf-8")

    base_mp4 = out / "baseline" / "final.mp4"
    enh_mp4 = out / "enhanced" / "final.mp4"
    for mp4 in (base_mp4, enh_mp4):
        if not mp4.exists() or mp4.stat().st_size <= 0:
            raise Blocked(f"render produced no usable file: {mp4}")

    report = compute_report(base_res, enh_res, assets,
                            baseline_probe=_probe(base_mp4),
                            enhanced_probe=_probe(enh_mp4),
                            isolations=isolations)
    report["material"]["unreadable_problems"] = problems
    (out / "comparison_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    (out / "comparison_report.md").write_text(report_md(report), encoding="utf-8")

    if not report["timelines_differ"]:
        raise Blocked("enhanced timeline did not differ from baseline — BUILD "
                      "thickness produced no observable change")

    print(f"[srp-replay] OK. artifacts in {out}")
    print(f"[srp-replay] timelines_differ={report['timelines_differ']} "
          f"opening={report['opening_inserted']['enhanced']} "
          f"auto_seq={report['auto_sequence_count']['enhanced']} "
          f"climax>setup={report['srp3_climax_vs_setup']['climax_exceeds_setup']}")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Blocked as exc:
        print(f"[srp-replay] BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
