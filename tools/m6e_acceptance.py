"""M6e real-case acceptance against the 67th graduation footage.

NOT a unit test — it drives the M6d lifecycle CLI + run_contract on REAL files
(real ffprobe durations, real video sources, real ffmpeg render) to validate the
three entry points the user listed:
  A. existing-material-only  -> stops at requirements discussion (no render)
  B. script-first, insufficient -> shooting brief + BUILD blocked before render
  C. covered (and revision)  -> handoff -> run_contract real render -> final.mp4

Per-asset `satisfies` edges below are the agent's review against
`_腳本素材對照表.md` (the human/agent review step the workflow expects).
"""
import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / ".tmp" / "m6e"          # fixtures live in the gitignored .tmp
FOOT = Path(os.environ.get("M6E_FOOTAGE", r"C:\Users\user\Downloads\微電影素材\_整理後"))
FFPROBE = os.environ.get("FFPROBE", r"C:\Users\user\miniconda3\Library\bin\ffprobe.exe")
PY = sys.executable
sys.path.insert(0, str(REPO))

from video_pipeline_core.material_needs import migrate_material_needs  # noqa: E402

PROJECT = "67th_graduation"
MUSIC = FOOT / "66期學長音樂檔" / "7感性收尾.mp4"

# covered topics -> real video source (verified present)
COVERED = {
    "director_encouragement": (FOOT / "主任勉勵" / "IMG_2118.MOV", "情境鏡頭", "主任對學員的期勉講話", True),
    "birthday": (FOOT / "慶生會" / "IMG_1408.MOV", "情境鏡頭", "結訓期間的慶生會同樂", False),
    "thanks_mentor": (FOOT / "感謝導師" / "67期養成班0326-3.mp4", "情境鏡頭", "學員感謝導師的橋段", True),
}
# script items with NO material (from the cross-reference table) -> the blockers
MISSING = {
    "morning_drill": ("動作鏡頭", "晨操晨跑體能訓練", True, None),    # 02 全缺, must_have, no fallback
    "knot_tying": ("動作鏡頭", "繩結法基本技能操作", True, None),      # 04 缺, must_have, no fallback
    "tbm_ky": ("情境鏡頭", "TBM/KY 現場實務", False, None),           # 06 缺, optional
}


def _dur(path):
    out = subprocess.run([FFPROBE, "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", str(path)], capture_output=True, text=True)
    return float(out.stdout.strip())


def _need(purpose, category, must_have, fallback=None):
    n = {"category": category, "type": "video", "purpose": purpose, "count": 1,
         "fallback_tier": 1, "must_have": must_have}
    if fallback:
        n["fallback_options"] = fallback
    return n


def _seg(num, need_id, visual_desc, *, role="diegetic" if False else "music"):
    return {"segment": num,
            "core": {"section_role": "montage", "story_purpose": f"段{num} 的敘事目的",
                     "timeline_source": "beat"},
            "material_fit": {"visual_desc": visual_desc, "reason": f"用真實素材呈現「{visual_desc}」",
                             "need_refs": [need_id]},
            "audio": {"role": "music", "reason": "鋪底配樂"},
            "visual_style": {"layout": "montage", "pace": "fast", "reason": "結訓回顧節奏"},
            "text_layer": "none"}


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    # ---- needs (covered 3 share identical (project,cat,type,purpose) so need_ids
    #      match across needs_covered and needs_full) -------------------------
    covered_specs = [_need(d, c, mh) for _, (src, c, d, mh) in COVERED.items()]
    missing_specs = [_need(d, c, mh, fb) for (c, d, mh, fb) in MISSING.values()]

    needs_covered = migrate_material_needs({"project": PROJECT, "needs": covered_specs})
    needs_full = migrate_material_needs({"project": PROJECT, "needs": covered_specs + missing_specs})
    (ROOT / "needs_covered.json").write_text(json.dumps(needs_covered, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "needs_full.json").write_text(json.dumps(needs_full, ensure_ascii=False, indent=2), encoding="utf-8")

    cov_ids = {spec["purpose"]: nid for spec, nid in
               zip(covered_specs, [n["need_id"] for n in needs_covered["needs"]])}
    full_ids = {n["purpose"]: n["need_id"] for n in needs_full["needs"]}
    # sanity: covered need_ids identical in both files
    for purpose, nid in cov_ids.items():
        assert full_ids[purpose] == nid, f"need_id drift for {purpose}"

    # ---- per-asset maps for covered topics (real source + ffprobe scene) -----
    maps_dir = ROOT / "maps"          # linked maps (with satisfies) for B/C/D
    raw_dir = ROOT / "maps_raw"       # raw inventory (no satisfies) for entry A
    maps_dir.mkdir(exist_ok=True)
    raw_dir.mkdir(exist_ok=True)
    db_files = []
    for key, (src, cat, desc, mh) in COVERED.items():
        nid = cov_ids[desc]
        dur = _dur(src)
        scene_end = round(min(dur, 6.0), 3)
        scene = {"start": 0.0, "end": scene_end, "caption": desc}
        base = {"asset_id": key, "asset_type": "video", "source": str(src),
                "duration_sec": round(dur, 3)}
        # raw: caption only, NOT yet linked to any need
        (raw_dir / f"{key}.map.json").write_text(
            json.dumps({**base, "scenes": [dict(scene)]}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        # linked: the agent review attached a satisfies edge
        linked_scene = {**scene, "satisfies": [{"need_id": nid, "status": "accepted"}]}
        (maps_dir / f"{key}.map.json").write_text(
            json.dumps({**base, "scenes": [linked_scene]}, ensure_ascii=False, indent=2),
            encoding="utf-8")
        # absolute material_map path: the legacy mv_chain loader resolves it
        # relative-to-cwd (unlike the gate's relative-to-db-dir), so abs is portable
        db_files.append({"path": str(src), "material_map": str((maps_dir / f"{key}.map.json").resolve())})
    (ROOT / "materials_db.json").write_text(
        json.dumps({"files": db_files}, ensure_ascii=False, indent=2), encoding="utf-8")

    # ---- contracts -----------------------------------------------------------
    d = cov_ids
    covered_segments = [
        _seg(1, d["主任對學員的期勉講話"], "主任對學員的期勉講話"),
        _seg(2, d["結訓期間的慶生會同樂"], "結訓期間的慶生會同樂"),
        _seg(3, d["學員感謝導師的橋段"], "學員感謝導師的橋段"),
    ]
    (ROOT / "contract_covered.json").write_text(json.dumps(
        {"style": "mv", "music": {"brief": "感性收尾"}, "material_needs_ref": "needs_covered.json",
         "segments": covered_segments}, ensure_ascii=False, indent=2), encoding="utf-8")

    full_segments = covered_segments + [
        _seg(4, full_ids["晨操晨跑體能訓練"], "晨操晨跑體能訓練"),
        _seg(5, full_ids["繩結法基本技能操作"], "繩結法基本技能操作"),
    ]
    (ROOT / "contract_full_norev.json").write_text(json.dumps(
        {"style": "mv", "music": {"brief": "感性收尾"}, "material_needs_ref": "needs_full.json",
         "segments": full_segments}, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "contract_full.json").write_text(json.dumps(
        {"style": "mv", "music": {"brief": "感性收尾"}, "material_needs_ref": "needs_full.json",
         "revision_decisions_ref": "decisions.json", "segments": full_segments},
        ensure_ascii=False, indent=2), encoding="utf-8")

    # drop + waive the two missing must_have segments (4 晨操, 5 繩結)
    lin = {"reviewer": "director", "reason": "本期未拍到,經導演同意自結訓片移除",
           "at": "2026-06-15T12:00:00"}
    decisions = [
        {"decision_id": "drop_morning", "need_id": full_ids["晨操晨跑體能訓練"],
         "route": "drop_segment", "status": "accepted", "target_segment": 4,
         "waiver": {"reviewer": "director", "reason": "本期無晨操素材,導演同意移除"}, "lineage": lin},
        {"decision_id": "drop_knot", "need_id": full_ids["繩結法基本技能操作"],
         "route": "drop_segment", "status": "accepted", "target_segment": 5,
         "waiver": {"reviewer": "director", "reason": "本期無繩結素材,導演同意移除"}, "lineage": lin},
    ]
    (ROOT / "decisions.json").write_text(json.dumps(decisions, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[fixture] covered need_ids: {cov_ids}")
    print(f"[fixture] music: {MUSIC.exists()}  ({MUSIC})")
    print("[fixture] built needs/maps/db/contracts/decisions in", ROOT)


if __name__ == "__main__":
    main()
