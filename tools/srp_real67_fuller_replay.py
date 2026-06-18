"""R67-F1 — 67th Fuller Material Replay.

Builds a FULLER real-footage project material map directly from the 67th graduation
footage tree (`_整理後`) and renders one enhanced review cut targeting >= 60s, so a
human can judge whether the BUILD is thick enough on realistic material volume.

Strategy (honest, no content model, no Gemini):
  * folder == need theme (e.g. `主任勉勵`, `慶生會`, `換桿`);
  * each video in a folder == an asset;
  * each video is sampled into SEVERAL scene windows AWAY FROM the head/tail, and
    each candidate window's mid frame is probed so near-black / fade / transition
    frames are skipped (the defect that left black cells in the first fuller cut);
    this yields 2-3 renderable accepted candidate scenes per need without inventing
    content;
  * a need with < min_candidates accepted scenes is listed as an explicit
    `material_gap`, never silently dropped.

Status (fail-closed, three-valued — `material_gaps` and failed render slots are
FINDINGS, not a clean pass):
  * ``fail``               — < 60s, no final render, or wrong-need (drift) binding;
  * ``pass_with_findings`` — >= 60s and need-correct, but has material_gaps and/or
                             slots that failed the render gate (dark/transition);
  * ``clean_pass``         — >= 60s, need-correct, no gaps, every slot rendered.
The CLI exits 0 only on ``clean_pass``.

Capabilities are attributed from the rendered plan's OWN stamped evidence
(``diversity_selection_reason`` / ``beat_role`` / ``opening_role`` / ``arc_role``) —
NO extra isolation renders, because each extra ``run_mv`` re-runs the expensive
music analysis. Artifacts go to the gitignored `.tmp/srp_real67_fuller_replay/`.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import srp_real67_review_demo as DEMO  # noqa: E402
import srp_real67_sanity as SANITY  # noqa: E402
from srp_real67_review_demo import Blocked, timeline_review_srt  # noqa: E402

OUT_ROOT = REPO / ".tmp" / "srp_real67_fuller_replay"
DEFAULT_FOOTAGE = SANITY.DEFAULT_FOOTAGE
FFMPEG = os.environ.get("FFMPEG", r"C:\Users\user\miniconda3\Library\bin\ffmpeg.exe")
FFPROBE = os.environ.get("FFPROBE", r"C:\Users\user\miniconda3\Library\bin\ffprobe.exe")

SCOPE = "67th_real_footage_fuller_replay"
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".m4v"}
MIN_DURATION_SEC = 60.0

# A graduation story order over real folders; only those with usable video are
# kept, in this order, so SRP3's arc reads setup -> training -> action -> life ->
# resolution rather than an arbitrary directory sort.
CURATED_NEED_ORDER = [
    "主任勉勵", "工安早會", "工安體感", "換桿", "拖拉電纜", "活線作業",
    "洗礙子", "裝桿作業", "班級日常生活", "慶生會", "運動會", "選填志願",
    "捐血相關", "感謝導師", "66期學長空拍影片",
]


# ---------------------------------------------------------------------------
# Pure planning (unit-tested without footage)
# ---------------------------------------------------------------------------

def need_id_for(folder):
    """Deterministic need_id for a folder theme (stable across runs)."""
    return "nd_" + hashlib.sha1(str(folder).encode("utf-8")).hexdigest()[:8]


# A rendered slot whose mid frame is flatter than this (max per-channel spatial
# stdev) reads as a near-black / fade / solid transition card — the slot render gate
# rejects it, so we avoid choosing such windows up front.
BLACK_STDEV = 12.0


def _even_windows(duration, n, *, clip_len=3.5, head_frac=0.12, tail_frac=0.08,
                  min_len=1.5):
    """``n`` evenly spaced ``clip_len`` windows inside ``[head, tail]`` of a clip."""
    duration = float(duration or 0.0)
    n = int(n)
    if duration <= 0 or n <= 0:
        return []
    start = duration * head_frac
    end = duration * (1.0 - tail_frac)
    span = end - start
    if span <= 0:
        return []
    wins = []
    for i in range(n):
        center = start + span * (i + 0.5) / n
        s = max(0.0, center - clip_len / 2.0)
        e = min(duration, s + clip_len)
        if e - s >= min_len:
            wins.append((round(s, 3), round(e, 3)))
    return wins


def _scene_count(duration, max_scenes):
    """Window count scales ~1 per 15s, capped at ``max_scenes`` (min 1)."""
    return max(1, min(int(max_scenes), int(float(duration or 0.0) // 15) + 1))


def scene_windows(duration, *, max_scenes=3, clip_len=3.5, head_frac=0.12,
                  tail_frac=0.08, min_len=1.5):
    """Evenly spaced scene windows inside ``[head, tail]`` of a clip, so we never
    sample the very first seconds (often a title card / fade-in) or the tail."""
    return _even_windows(duration, _scene_count(duration, max_scenes),
                         clip_len=clip_len, head_frac=head_frac,
                         tail_frac=tail_frac, min_len=min_len)


def renderable_windows(source, duration, frame_probe, *, max_scenes=3, clip_len=3.5,
                       black_stdev=BLACK_STDEV, density=3, temporal_corr=0.08):
    """Like ``scene_windows`` but each window is probed via
    ``frame_probe(source, t) -> stdev`` and only non-black/non-transition windows are
    kept. We check head/mid/tail, not only the midpoint, because SRP/beat planning
    may shorten a selected 3.5s scene to its first ~1.5s. If a base window is black,
    a denser pool of alternative windows is tried before that slot is dropped.
    ``frame_probe`` returning ``None`` (unreadable) is treated as not renderable.
    If the probe returns full frame descriptors with ``gray`` vectors, adjacent
    samples must also be structurally related; this avoids cut/fast-motion windows
    that are bright but later fail the source-correlation render gate. Pure given an
    injected ``frame_probe``."""
    target = _scene_count(duration, max_scenes)
    base = _even_windows(duration, target, clip_len=clip_len)
    alts = _even_windows(duration, max(target * int(density), target + 3),
                         clip_len=clip_len)

    def _ok(win):
        s, e = win
        dur = max(0.0, e - s)
        edge = min(0.35, dur / 4.0)
        sample_times = (
            round(s + edge, 3),
            round((s + e) / 2.0, 3),
            round(e - edge, 3),
        )
        descriptors = []
        for t in sample_times:
            probed = frame_probe(source, t)
            if isinstance(probed, dict):
                stdev = probed.get("stdev")
                descriptors.append(probed)
            else:
                stdev = probed
            if stdev is None or stdev < black_stdev:
                return False
        if descriptors and len(descriptors) == len(sample_times):
            for prev, cur in zip(descriptors, descriptors[1:]):
                a, b = prev.get("gray"), cur.get("gray")
                if a is None or b is None:
                    continue
                if SANITY.pearson(a, b) < temporal_corr:
                    return False
        return True

    used, out = set(), []
    for win in base:
        if win not in used and _ok(win):
            out.append(win)
            used.add(win)
            continue
        for alt in alts:                      # black window -> try alternatives
            if alt in used:
                continue
            if _ok(alt):
                out.append(alt)
                used.add(alt)
                break
    return out


def _asset_id(folder, filename):
    stem = Path(filename).stem
    raw = f"{folder}_{stem}"
    safe = "".join(ch if ch.isalnum() else "_" for ch in raw)
    return safe.strip("_") or need_id_for(raw)


def build_need_assets(folder, files, *, max_scenes_per_asset=3, frame_probe=None):
    """Build (assets, candidate_scene_count) for one need from its video files.

    ``files`` is ``[(filename, source_path, duration_sec)]``. Every scene carries an
    ``accepted`` satisfies edge to the folder's need_id (canonical map shape). When
    ``frame_probe`` is given, near-black / transition windows are skipped."""
    nid = need_id_for(folder)
    assets, candidates = [], 0
    for filename, source, duration in files:
        if frame_probe is not None:
            wins = renderable_windows(source, duration, frame_probe,
                                      max_scenes=max_scenes_per_asset)
        else:
            wins = scene_windows(duration, max_scenes=max_scenes_per_asset)
        if not wins:
            continue
        scenes = [{
            "start": s, "end": e, "caption": folder,
            "satisfies": [{"need_id": nid, "status": "accepted"}],
        } for s, e in wins]
        assets.append({
            "asset_id": _asset_id(folder, filename),
            "asset_type": "video",
            "source": source,
            "duration_sec": round(float(duration), 3),
            "scenes": scenes,
        })
        candidates += len(scenes)
    return assets, candidates


def plan_material(folder_index, *, max_needs=12, min_candidates=2,
                  max_scenes_per_asset=3, order=None, frame_probe=None):
    """Turn a resolved folder index into (material_map, needs_plan, gaps).

    ``folder_index`` maps ``folder -> [(filename, source_path, duration_sec)]``.
    ``order`` is the preferred theme order; folders not listed fall after it by
    descending video count. A need whose accepted candidate scenes < min_candidates
    is reported in ``gaps`` (it still participates, but its thinness is disclosed).
    ``frame_probe`` (when given) skips near-black / transition windows."""
    order = order or CURATED_NEED_ORDER
    ranked = [f for f in order if f in folder_index]
    extras = sorted((f for f in folder_index if f not in set(order)),
                    key=lambda f: (-len(folder_index[f]), f))
    sequence = (ranked + extras)[:int(max_needs)]

    all_assets, needs_plan, gaps = [], [], []
    map_assets, map_needs = [], []
    for folder in sequence:
        nid = need_id_for(folder)
        assets, candidates = build_need_assets(
            folder, folder_index[folder], max_scenes_per_asset=max_scenes_per_asset,
            frame_probe=frame_probe)
        if candidates == 0:
            gaps.append({"need_id": nid, "folder": folder, "candidate_scenes": 0,
                         "reason": "no renderable scene windows"})
            continue
        must_have = True
        if candidates < int(min_candidates):
            gaps.append({"need_id": nid, "folder": folder,
                         "candidate_scenes": candidates,
                         "reason": f"only {candidates} accepted scene(s) < "
                                   f"{min_candidates} required"})
        map_assets.extend(assets)
        map_needs.append({"need_id": nid, "category": "情境鏡頭", "type": "video",
                          "purpose": folder, "count": 1, "fallback_tier": 1,
                          "must_have": must_have})
        needs_plan.append({"need_id": nid, "folder": folder,
                           "asset_count": len(assets),
                           "candidate_scenes": candidates,
                           "must_have": must_have})
        all_assets.extend(assets)

    material_map = {"artifact_role": "project_material_map", "version": 1,
                    "assets": map_assets, "needs": map_needs}
    return material_map, needs_plan, gaps


def build_fuller_script(needs_plan):
    """One montage segment per need (in plan order), then DEMO.build_review_script
    stamps need_ref + review subtitle and forces the enhanced path."""
    segments = []
    for i, need in enumerate(needs_plan, start=1):
        folder = need["folder"]
        segments.append({
            "segment": i,
            "visual_desc": folder,
            "audio_role": "music",
            "pace": "fast",
            "material_fit": {"visual_desc": folder, "need_refs": [need["need_id"]]},
        })
    script = {"style": "mv", "segments": segments,
              "music": {"brief": "感性收尾"},
              "title": "67期結訓回顧", "opening_title": "67期結訓回顧"}
    return DEMO.build_review_script(script)


def _diversity_had_labels(reason):
    """A VD2 selection reason shows it actually diversified (rather than just running
    as a tie-break) only when a family/scale preference is non-zero — which requires
    visual_family / angle_scale labels on the candidates."""
    if not isinstance(reason, str):
        return False
    return "family_pref=0" not in reason or "scale_pref=0" not in reason


def attribute_capabilities(plan):
    """Attribute VD2/SRP1/SRP2/SRP3 from the rendered plan's OWN stamped evidence —
    no separate isolation renders (each extra run_mv re-runs the expensive music
    analysis, so isolations are deliberately avoided here):

      * VD2  — ``diversity_selection_reason`` present and not ``diversity_disabled``;
               whether it had visual_family / angle_scale labels to diversify on.
      * SRP1 — clips carrying ``beat_role`` / ``sequence_recipe_source == 'auto'``.
      * SRP2 — any ``opening_role`` clip.
      * SRP3 — any ``arc_role`` clip.
    """
    story = [c for c in plan or [] if not c.get("opening_role")]
    # VD2 can only change the outcome when same-tier candidates carry
    # visual_family / angle_scale (VD0) labels; otherwise it degenerates to the
    # deterministic correctness order (identical selection VD2 on/off). The 67th
    # footage has no VD0 labels, so VD2 is not meaningfully exercised here.
    vd2_labeled = any(c.get("visual_family") or c.get("angle_scale") for c in story)
    vd2_reordered = any(_diversity_had_labels(c.get("diversity_selection_reason"))
                        for c in story)

    auto_segs = sorted({c.get("segment") for c in story
                        if c.get("sequence_recipe_source") == "auto"
                        or c.get("beat_role")})
    opening = sum(1 for c in plan or [] if c.get("opening_role"))
    arc_roles = sorted({c.get("arc_role") for c in story if c.get("arc_role")})

    return {
        "VD2": {
            "active": bool(vd2_labeled and vd2_reordered),
            "evidence": "VD2 reordered same-tier candidates on visual_family/"
            "angle_scale labels" if (vd2_labeled and vd2_reordered) else
            "not meaningfully exercised: the 67th footage has no visual_family/"
            "angle_scale (VD0) labels, so same-tier diversity degenerates to the "
            "deterministic correctness order (identical selection with VD2 on/off)",
        },
        "SRP1": {
            "active": bool(auto_segs),
            "evidence": f"auto beat-sequenced segments {auto_segs}" if auto_segs
            else "no segment had >=2 approved slots to beat-sequence",
        },
        "SRP2": {
            "active": opening > 0,
            "evidence": f"{opening} opening/hook clip(s) inserted before the story",
        },
        "SRP3": {
            "active": bool(arc_roles),
            "evidence": f"story-arc roles assigned: {arc_roles}" if arc_roles
            else "no arc roles assigned",
        },
    }


def compute_fuller_report(result, material_map, script, needs_plan, gaps, *,
                          footage_root, render_sec, slot_check, music_name,
                          capabilities, min_candidates):
    plan = result.get("plan") or []
    alignment = DEMO.semantic_alignment(plan, material_map, script)
    arc = DEMO._arc_durations(plan)
    climax, setup = arc.get("climax"), arc.get("setup")
    opening_count = sum(1 for c in plan if c.get("opening_role"))
    story_slots = sum(1 for c in plan if not c.get("opening_role"))
    duration_ok = bool(render_sec is not None and render_sec >= MIN_DURATION_SEC)
    drift = alignment["drift_segments"]
    slot_ok = bool(slot_check.get("ok"))
    failed_slots = slot_check.get("failed_slots") or []

    # Three-valued status: material_gaps and failed render slots are FINDINGS, not a
    # clean pass; only a < 60s / no-render / wrong-need cut is an outright fail.
    findings = []
    if gaps:
        findings.append(f"{len(gaps)} need(s) below the {min_candidates}-candidate "
                        f"floor: {[g['folder'] for g in gaps]}")
    if not slot_ok:
        findings.append(f"{len(failed_slots)} slot(s) failed the render gate "
                        f"(near-black / transition frames): {failed_slots}")
    if not duration_ok or drift or render_sec is None:
        status = "fail"
        if not duration_ok:
            findings.insert(0, "rendered cut is under 60s (insufficient material)")
        if drift:
            findings.insert(0, f"wrong-need (drift) segments: {drift}")
    elif findings:
        status = "pass_with_findings"
    else:
        status = "clean_pass"
    return {
        "scope": SCOPE,
        "status": status,
        "clean_pass": status == "clean_pass",
        "findings": findings,
        "footage_root": str(footage_root),
        "music": music_name,
        "review_subtitles": "review_subtitles.srt",
        "contact_sheet": "contact_sheet.jpg",
        "final_duration_sec": render_sec,
        "duration_gate": {
            "min_required_sec": MIN_DURATION_SEC,
            "met": duration_ok,
            "status": "ok" if duration_ok else "insufficient_material",
            "note": "" if duration_ok else
                    "Rendered cut is under 60s — NOT a success; the accepted real "
                    "footage / scene windows did not sustain a 60s review cut.",
        },
        "needs": {
            "need_count": len(needs_plan),
            "story_slot_count": story_slots,
            "plan": needs_plan,
            "min_candidates_required": min_candidates,
        },
        "material_gaps": gaps,
        "semantic_alignment": alignment,
        "srp1_segment_sequence": DEMO.srp1_eligibility(plan),
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
        },
        "capabilities_that_changed_build": capabilities,
        "slot_render_check": slot_check,
        "limitations": {
            "folder_is_need_proxy": True,
            "full_ingest": False,
            "ten_minute_film": False,
            "synthetic_material": False,
            "note": "Real 67th footage; folder name is used as the need theme proxy "
                    "(no content model). Not a full ingest, not a 10-minute film, not "
                    "an aesthetic score. A reviewer should still confirm each clip "
                    "visually fits its folder theme.",
        },
    }


def report_md(report):
    a = report["semantic_alignment"]
    dg = report["duration_gate"]
    lines = ["# R67-F1 — 67th Fuller Material Replay", "",
             f"- Scope: `{report['scope']}`",
             f"- **Status: {report['status'].upper()}** "
             f"(clean_pass={report['clean_pass']})",
             f"- Footage root: `{report['footage_root']}`",
             f"- Music: `{report['music']}`",
             f"- Final duration: **{report['final_duration_sec']}s** "
             f"(>= {dg['min_required_sec']}s required → {dg['status']})",
             f"- Needs/segments: {report['needs']['need_count']}, "
             f"story slots: {report['needs']['story_slot_count']}",
             f"- Semantic drift segments: {a['drift_segments']}",
             f"- Review subtitles: `{report['review_subtitles']}` · "
             f"Contact sheet: `{report['contact_sheet']}`"]
    if not dg["met"]:
        lines.append(f"- ⚠ {dg['note']}")
    lines += ["", "## Findings"]
    if report["findings"]:
        lines += [f"- ⚠ {f}" for f in report["findings"]]
    else:
        lines.append("- none — clean pass.")
    lines += ["", "## Per-segment material binding (review this)"]
    for seg, info in sorted(a["segments"].items(), key=lambda kv: int(kv[0])):
        lines.append(f"- **Seg {seg}** expected `{info['expected_need_ref']}` "
                     f"→ status **{info['status']}** ({info['matched_slots']}/{info['slot_count']})")
        for slot in info["slots"]:
            flag = "" if slot["status"] == "matched" else "  REVIEW"
            lines.append(f"    - {slot['scene_id']} ({slot['source']}) "
                         f"need={slot['selected_need_id']} arc={slot['arc_role']}"
                         f"{flag}  [{slot['subtitle']}]")
    lines += ["", "## Material gaps (needs with thin accepted material)"]
    if report["material_gaps"]:
        for g in report["material_gaps"]:
            lines.append(f"- `{g['need_id']}` {g['folder']}: "
                         f"{g['candidate_scenes']} scene(s) — {g['reason']}")
    else:
        lines.append("- none — every need met the candidate-scene floor.")
    caps = report["capabilities_that_changed_build"]
    srp1 = report["srp1_segment_sequence"]
    lines += ["", "## Capability evidence (did BUILD actually change?)"]
    for cap in ("VD2", "SRP1", "SRP2", "SRP3"):
        c = caps.get(cap, {})
        lines.append(f"- **{cap}**: active={c.get('active')} — {c.get('evidence')}")
    lines += [
        f"- SRP1 eligible segments (>=2 slots): {srp1['eligible_count']} "
        f"{srp1['eligible_segments']}",
        f"- SRP2 opening: {report['srp2_opening']['status']} "
        f"({report['srp2_opening']['clip_count']} clips)",
        f"- SRP3 arc: {report['srp3_story_arc']['status']}/"
        f"{report['srp3_story_arc']['execution']}; "
        f"climax>setup={report['srp3_story_arc']['climax_exceeds_setup']} "
        f"{report['srp3_story_arc']['arc_role_durations']}",
        "", "## Render gate",
        f"- Slot render check: ok={report['slot_render_check'].get('ok')} "
        f"checked={report['slot_render_check'].get('checked_slots')} "
        f"failed={report['slot_render_check'].get('failed_slots')}",
        "", "## Boundary",
        "- Real footage; folder name is the need-theme proxy (no content model).",
        "- Not a full ingest; not a 10-minute film; not an aesthetic score."]
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Orchestration (I/O — real run)
# ---------------------------------------------------------------------------

def _probe_duration(path):
    try:
        out = subprocess.run([FFPROBE, "-v", "error", "-show_entries",
                              "format=duration", "-of", "csv=p=0", str(path)],
                             capture_output=True, text=True, timeout=60)
        return float((out.stdout or "").strip())
    except Exception:
        return 0.0


def scan_footage(footage_root):
    """Build ``folder -> [(filename, source_path, duration_sec)]`` for every
    top-level folder that holds usable (non-empty, probeable) video files."""
    footage_root = Path(footage_root)
    index = {}
    for child in sorted(footage_root.iterdir()):
        if not child.is_dir():
            continue
        files = []
        for f in sorted(child.iterdir()):
            if f.suffix.lower() not in VIDEO_EXTS or not f.is_file():
                continue
            if f.stat().st_size <= 0:
                continue
            dur = _probe_duration(f)
            if dur and dur > 0:
                files.append((f.name, str(f), dur))
        if files:
            index[child.name] = files
    return index


def _make_frame_probe():
    """A cached ``(source, t) -> frame descriptor`` probe (None if unreadable), used
    to skip near-black / transition / unstable windows when building the material
    map."""
    import tempfile  # noqa: PLC0415
    cache = {}

    def probe(source, t):
        key = (source, round(float(t), 2))
        if key in cache:
            return cache[key]
        tmp = Path(tempfile.gettempdir()) / f"rfp_{abs(hash(key))}.png"
        extracted = SANITY._extract_frame(source, t, tmp)
        value = None
        if extracted:
            try:
                value = SANITY.frame_descriptor(str(extracted))
            except Exception:
                value = None
            try:
                tmp.unlink()
            except OSError:
                pass
        cache[key] = value
        return value

    return probe


def prepare_music_wav(music_src, out_wav, seconds):
    """Transcode the real music to a trimmed mono WAV once, so every run_mv loads it
    fast via soundfile instead of slowly decoding the source mp4 through audioread."""
    subprocess.run([FFMPEG, "-y", "-t", f"{float(seconds):.2f}", "-i", str(music_src),
                    "-ac", "1", "-ar", "44100", str(out_wav)],
                   capture_output=True, check=True)
    if not Path(out_wav).exists() or Path(out_wav).stat().st_size <= 0:
        raise Blocked(f"music transcode failed: {out_wav}")
    return out_wav


def run_fuller(footage_root, *, target_sec=90.0, max_needs=12, max_clips_per_seg=3,
               min_candidates=2, music=None, out_root=OUT_ROOT):
    from video_pipeline_core import mv_cut  # noqa: PLC0415

    footage_root = Path(footage_root)
    if not footage_root.exists():
        raise Blocked(f"footage root does not exist: {footage_root}")

    index = scan_footage(footage_root)
    if not index:
        raise Blocked(f"no usable video folders under {footage_root}")
    material_map, needs_plan, gaps = plan_material(
        index, max_needs=max_needs, min_candidates=min_candidates,
        max_scenes_per_asset=max_clips_per_seg, frame_probe=_make_frame_probe())
    DEMO.assert_no_synthetic_sources(material_map)
    if len(needs_plan) < 8:
        raise Blocked(f"only {len(needs_plan)} needs with usable video (<8); "
                      f"cannot form a fuller cut. gaps={gaps}")
    script = build_fuller_script(needs_plan)

    out = Path(out_root)
    if out.exists():
        shutil.rmtree(out)
    out.mkdir(parents=True)
    work = out / "_work"
    work.mkdir(parents=True, exist_ok=True)

    music_src = SANITY.find_music(footage_root, music)
    music_wav = prepare_music_wav(music_src, out / "music.wav", target_sec + 12.0)

    common = dict(material_root=None, music_path=str(music_wav),
                  material_maps=material_map, target_sec=target_sec,
                  max_clips_per_seg=max_clips_per_seg, verbose=False)

    result = mv_cut.run_mv(script, out_path=str(out / "final.mp4"),
                           skip_render=False, mat_dir=str(work), **common)
    final = out / "final.mp4"
    if not final.exists() or final.stat().st_size <= 0:
        raise Blocked(f"render produced no usable final.mp4: {final}")

    # Capabilities are attributed from the rendered plan's own stamped evidence —
    # no extra isolation renders (each one re-runs the expensive music analysis).
    capabilities = attribute_capabilities(result["plan"])

    slot_check = SANITY.verify_video_slots(final, result["plan"])
    render_sec = SANITY._probe(final)

    report = compute_fuller_report(
        result, material_map, script, needs_plan, gaps,
        footage_root=footage_root, render_sec=render_sec, slot_check=slot_check,
        music_name=Path(music_src).name, capabilities=capabilities,
        min_candidates=min_candidates)

    DEMO._write_json(out / "generated_mv_script.json", script)
    DEMO._write_json(out / "project_material_map.json", material_map)
    DEMO._write_json(out / "timeline.json", {
        "plan": result["plan"], "segments": result["segments"],
        "opening_plan": result.get("opening_plan"),
        "story_arc_plan": result.get("story_arc_plan"),
        "cuts": result.get("cuts")})
    (out / "review_subtitles.srt").write_text(
        timeline_review_srt(result["plan"]), encoding="utf-8")
    # NOTE: a failed slot is review evidence (a frame that does not clearly show its
    # source — a dark/transition/fast-motion moment), NOT a reason to suppress the
    # report. It is a FINDING (status=pass_with_findings) and the contact sheet is
    # still built so a human can eyeball every flagged slot.
    DEMO.build_contact_sheet(final, result["plan"], out / "contact_sheet.jpg")
    DEMO._write_json(out / "review_report.json", report)
    (out / "review_report.md").write_text(report_md(report), encoding="utf-8")
    return report, out


def main(argv=None):
    parser = argparse.ArgumentParser(description="R67-F1 fuller material replay")
    parser.add_argument("--footage-root", default=str(DEFAULT_FOOTAGE))
    parser.add_argument("--target-sec", type=float, default=90.0)
    parser.add_argument("--max-needs", type=int, default=12)
    parser.add_argument("--max-clips-per-seg", type=int, default=3)
    parser.add_argument("--min-candidates", type=int, default=2)
    parser.add_argument("--music")
    args = parser.parse_args(argv)

    report, out = run_fuller(
        args.footage_root, target_sec=args.target_sec, max_needs=args.max_needs,
        max_clips_per_seg=args.max_clips_per_seg, min_candidates=args.min_candidates,
        music=args.music)
    a = report["semantic_alignment"]
    print(f"[real67-fuller] artifacts={out}")
    print(f"[real67-fuller] status={report['status']} "
          f"final={report['final_duration_sec']}s "
          f"(>= {MIN_DURATION_SEC}s: {report['duration_gate']['met']})")
    print(f"[real67-fuller] needs={report['needs']['need_count']} "
          f"story_slots={report['needs']['story_slot_count']} "
          f"drift={a['drift_segments']} gaps={len(report['material_gaps'])}")
    caps = report["capabilities_that_changed_build"]
    print(f"[real67-fuller] caps active: "
          f"VD2={caps['VD2']['active']} SRP1={caps['SRP1']['active']} "
          f"SRP2={caps['SRP2']['active']} SRP3={caps['SRP3']['active']}")
    print(f"[real67-fuller] slot_render ok={report['slot_render_check']['ok']} "
          f"findings={len(report['findings'])}")
    # exit 0 only on a clean pass; pass_with_findings -> 3; fail -> 1.
    return {"clean_pass": 0, "pass_with_findings": 3}.get(report["status"], 1)


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Blocked as exc:
        print(f"[real67-fuller] BLOCKED: {exc}", file=sys.stderr)
        sys.exit(2)
