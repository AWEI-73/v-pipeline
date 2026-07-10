# LOOP pilot L1 driver (manual, session-scoped): builds candidate v1 from
# owner-approved script + agent selects, then renders via repo-owned code.
import copy
import hashlib
import json
import subprocess
import sys
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, r"C:\Users\user\Desktop\video_pipeline")

from video_pipeline_core.beat_cut_composer import (
    compose_beat_cut_montage, write_beat_cut_alignment_report)
from video_pipeline_core.edit_decision_plan import write_product_artifacts
from video_pipeline_core.edit_decision_renderer import render_edit_decision
from video_pipeline_core.graduation_opening_slice import (
    _timeline_from_decision, _write_lifecycle_evidence)
from video_pipeline_core.rendered_product_qa import probe_video, write_rendered_product_qa

REPO = Path(r"C:\Users\user\Desktop\video_pipeline")
SRC_ROOT = Path(r"C:\Users\user\Downloads\微電影素材\_整理後")
PILOT = REPO / ".tmp" / "loop_pilot_0044"
OUT = PILOT / "candidate_v1"
BGM = REPO / ".tmp/canon_67_opening_slice_acceptance/run/assets/bgm.mp3"
SEED_PROBE = REPO / ".tmp/canon_67_opening_slice_acceptance/run/soundtrack_probe_report.json"

MANIFEST = json.load(open(PILOT / "selects_manifest.json", encoding="utf-8"))
TITLE_CODE = "AER01"
MONTAGE_ORDER = ["TWR02", "SPT02", "LIF01", "SPT04", "LIF17", "ACT19",
                 "LIF04", "TWR04", "ACT12", "LIF03", "ACT10", "LIF15",
                 "SPT08", "SPT10", "SPT13"]
# Owner-approved text source: docs/pilots/2026-07-10-opening-0044-script-v1.md
TITLE = "台電67TH養成班"
SUBTITLE = "ON THE LAST PAGE"
POEM = [
    "當風雨熄滅城市最後一盞燈",
    "總有人背起工具，走進風雨裡",
    "從今天起——那個人，是我們",
]
CLOSING_NOTE = "六十七期，全員到齊"


def asset_id(rel: str) -> str:
    return "accepted_" + hashlib.sha1(rel.encode("utf-8")).hexdigest()[:12]


def upright_copy(src: Path, rel: str) -> Path:
    """Apply EXIF orientation; ffmpeg 4.3.1 ignores it and would render sideways."""
    im = Image.open(src)
    fixed = ImageOps.exif_transpose(im)
    if fixed is im:
        return src
    dst_dir = PILOT / "upright"
    dst_dir.mkdir(exist_ok=True)
    dst = dst_dir / (asset_id(rel) + src.suffix.lower())
    fixed.save(dst, quality=95)
    return dst


VIDEO_EXTS = {".mp4", ".mov", ".m4v"}


def photo_record(code: str) -> dict:
    rel = MANIFEST[code].replace("\\", "/")
    src = SRC_ROOT / rel
    if src.suffix.lower() in VIDEO_EXTS:
        vp = probe_video(src)
        return {
            "asset_id": asset_id(rel), "source_path": str(src),
            "source_relative_path": rel, "accepted": True, "kind": "video",
            "is_photo": False, "human_review_status": "accepted",
            "catalog_artifact": "reviewed_catalog_map.json",
            "media_duration_sec": vp.get("duration_sec"),
            "select_code": code, "orientation_corrected": False,
        }
    use = upright_copy(src, rel)
    return {
        "asset_id": asset_id(rel), "source_path": str(use),
        "source_relative_path": rel, "accepted": True, "kind": "image",
        "is_photo": True, "human_review_status": "accepted",
        "catalog_artifact": "reviewed_catalog_map.json",
        "select_code": code,
        "orientation_corrected": use != src,
    }


rel_t = MANIFEST[TITLE_CODE].replace("\\", "/")
title_src = SRC_ROOT / rel_t
tprobe = probe_video(title_src)
title_rec = {
    "asset_id": asset_id(rel_t), "source_path": str(title_src),
    "source_relative_path": rel_t, "accepted": True, "kind": "video",
    "is_photo": False, "human_review_status": "accepted",
    "catalog_artifact": "reviewed_catalog_map.json",
    "media_duration_sec": tprobe.get("duration_sec"),
    "select_code": TITLE_CODE,
}
montage_recs = [photo_record(c) for c in MONTAGE_ORDER]
audio_rec = {
    "asset_id": "bgm", "source_path": str(BGM),
    "source_relative_path": "canon_67_opening_slice_acceptance/run/assets/bgm.mp3",
    "accepted": True, "kind": "audio",
    "human_review_status": "accepted_for_render_rehearsal",
    "catalog_artifact": "soundtrack_probe_report.json",
}

probe = json.load(open(SEED_PROBE, encoding="utf-8"))
beats = list((probe.get("features") or {}).get("beat_times") or [])
montage = compose_beat_cut_montage(montage_recs, beats, window_start=18.0,
                                   window_end=44.0, fps=30,
                                   min_distinct_assets=15)

TITLE_IN = 2.0
title_clip = {
    "id": "opening_title_aerial", "section": "title",
    "asset_id": title_rec["asset_id"], "source": rel_t, "source_path": rel_t,
    "source_relative_path": rel_t, "source_type": "video", "is_photo": False,
    "in_seconds": TITLE_IN, "out_seconds": TITLE_IN + 11.0,
    "duration_sec": 11.0, "timeline_in_sec": 0.0, "timeline_out_sec": 11.0,
    "treatment": "establishing_aerial",
    "source_lineage": {"asset_id": title_rec["asset_id"],
                       "source_relative_path": rel_t, "accepted": True,
                       "human_review_status": "accepted",
                       "catalog_artifact": "reviewed_catalog_map.json"},
}
poetry_clip = {
    "id": "opening_poetry_card", "section": "poetry_card",
    "source_type": "generated_background", "generated_background": {"color": "black"},
    "in_seconds": 0.0, "out_seconds": 7.0, "duration_sec": 7.0,
    "timeline_in_sec": 11.0, "timeline_out_sec": 18.0,
    "source_lineage": {"generated": True, "reason": "explicit_black_poetry_card"},
}
montage_clips = []
for clip in montage["clips"]:
    item = dict(clip)
    item["source"] = item["source_relative_path"]
    item["source_path"] = item["source_relative_path"]
    item["accepted"] = True
    montage_clips.append(item)

last_start = montage_clips[-1]["timeline_in_sec"]
P1, P2 = 11.0 + 7.0 / 3.0, 11.0 + 14.0 / 3.0
overlays = [
    {"id": "opening_title_text", "kind": "text",
     "text": {"main": TITLE, "subtitle": SUBTITLE},
     "treatment": "progressive_typewriter", "start_sec": 0.0, "end_sec": 11.0},
    {"id": "poem_line_1", "kind": "text", "text": {"main": POEM[0]},
     "treatment": "progressive_typewriter", "start_sec": 11.0, "end_sec": round(P1, 3)},
    {"id": "poem_line_2", "kind": "text", "text": {"main": POEM[1]},
     "treatment": "progressive_typewriter", "start_sec": round(P1, 3), "end_sec": round(P2, 3)},
    {"id": "poem_line_3", "kind": "text", "text": {"main": POEM[2]},
     "treatment": "progressive_typewriter", "start_sec": round(P2, 3), "end_sec": 18.0},
    {"id": "closing_note", "kind": "text", "text": {"main": CLOSING_NOTE},
     "treatment": "progressive_typewriter",
     "start_sec": round(last_start + 0.5, 3), "end_sec": 44.0},
]
transitions = [{"type": "hard_cut", "at_sec": 11.0}, {"type": "hard_cut", "at_sec": 18.0}]
transitions.extend({"type": "hard_cut", "at_sec": c["timeline_out_sec"]}
                   for c in montage_clips[:-1])

opening = {
    "artifact_role": "opening_sequence", "version": 2,
    "settings": {"fps": 30, "resolution": "1920x1080"},
    "clips": [title_clip, poetry_clip, *montage_clips],
    "overlays": overlays, "transitions": transitions, "montage": montage,
}

OUT.mkdir(parents=True, exist_ok=False)
run = OUT / "run"
run.mkdir()


def wjson(path: Path, payload: dict):
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
                    encoding="utf-8")


wjson(run / "opening_sequence.json", opening)
wjson(run / "rough_cut_plan.json",
      {"artifact_role": "rough_cut_plan", "ok": True, "clips": [], "gaps": []})
wjson(run / "audio_director_handoff.json", {
    "artifact_role": "audio_director_handoff", "ready_for_audio_director": True,
    "selected_audio_files": [{"candidate_id": "bgm", "section_id": "opening",
                              "audio_file": "bgm",
                              "source_type": "accepted_seed_soundtrack",
                              "music_role": "opening_bgm"}]})
sanitized = copy.deepcopy(probe)
sanitized["audio_file"] = "assets/bgm.mp3"
sanitized["source_seed_artifact"] = "soundtrack_probe_report.json"
wjson(run / "soundtrack_probe_report.json", sanitized)
wjson(OUT / "source_provenance.json", {
    "artifact_role": "opening_slice_source_provenance", "version": 1,
    "selection_mode": "owner_delegated_agent_selects",
    "script_source": "docs/pilots/2026-07-10-opening-0044-script-v1.md",
    "selected_title_asset": {"code": TITLE_CODE, "rel": rel_t},
    "selected_montage_assets": [
        {"code": r["select_code"], "rel": r["source_relative_path"],
         "orientation_corrected": r.get("orientation_corrected", False)}
        for r in montage_recs],
    "reference_film_selected_as_footage": False,
})

artifacts = write_product_artifacts(run)
decision = artifacts["edit_decision_plan"]
request = {"fps": 30, "resolution": "1920x1080"}
timeline = _timeline_from_decision(decision, request)
result = render_edit_decision(decision, timeline, run_dir=run,
                              accepted_inputs=[title_rec, *montage_recs, audio_rec])
print("render ok:", result.get("ok"))

persisted = json.load(open(run / "timeline_build.json", encoding="utf-8"))
beat_report = write_beat_cut_alignment_report(
    persisted, sanitized, window_start=18.0, window_end=44.0, fps=30,
    out_path=OUT / "beat_cut_alignment_report.json")
print("beat pass:", beat_report.get("pass"),
      "ratio:", beat_report.get("within_one_frame_ratio"))
lifecycle = _write_lifecycle_evidence(run, list(decision.get("overlays") or []), 30)
print("lifecycle pass:", lifecycle.get("pass"))
qa = write_rendered_product_qa(run, OUT / "rendered_qa")
print("rendered qa:", qa.get("pass"), "blocking:", len(qa.get("blocking") or []))
fp = probe_video(run / "final.mp4")
print("duration:", fp.get("duration_sec"))
print("DONE ->", OUT)
