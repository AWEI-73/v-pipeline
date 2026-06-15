"""M6e real-case acceptance against the 67th graduation footage — FULLY
reproducible from the repo.

NOT a unit test. Builds a fresh fixture from the real footage (real ffprobe
durations, real video sources, agent-reviewed `satisfies` edges per
`_腳本素材對照表.md`) with RELATIVE `material_map` paths, then drives the shipped
CLIs for all four entry points with assertions. Every CLI subprocess runs from an
UNRELATED cwd to prove the relative `material_map` contract is cwd-independent.

Env: `M6E_FOOTAGE` (footage dir), `FFPROBE` (ffprobe path). Outputs go to the
gitignored `.tmp/m6e/`; real footage and renders are never committed. Exits
non-zero if any entry assertion fails.
"""
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
ROOT = REPO / ".tmp" / "m6e"
FOOT = Path(os.environ.get("M6E_FOOTAGE", r"C:\Users\user\Downloads\微電影素材\_整理後"))
FFPROBE = os.environ.get("FFPROBE", r"C:\Users\user\miniconda3\Library\bin\ffprobe.exe")
PY = sys.executable
VT = str(REPO / "video_tools.py")
sys.path.insert(0, str(REPO))
from video_pipeline_core.material_needs import migrate_material_needs  # noqa: E402

PROJECT = "67th_graduation"
MUSIC = FOOT / "66期學長音樂檔" / "7感性收尾.mp4"
COVERED = {
    "director_encouragement": (FOOT / "主任勉勵" / "IMG_2118.MOV", "情境鏡頭", "主任對學員的期勉講話", True),
    "birthday": (FOOT / "慶生會" / "IMG_1408.MOV", "情境鏡頭", "結訓期間的慶生會同樂", False),
    "thanks_mentor": (FOOT / "感謝導師" / "67期養成班0326-3.mp4", "情境鏡頭", "學員感謝導師的橋段", True),
}
MISSING = {
    "morning_drill": ("動作鏡頭", "晨操晨跑體能訓練", True, None),
    "knot_tying": ("動作鏡頭", "繩結法基本技能操作", True, None),
    "tbm_ky": ("情境鏡頭", "TBM/KY 現場實務", False, None),
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


def _seg(num, need_id, visual_desc):
    return {"segment": num,
            "core": {"section_role": "montage", "story_purpose": f"段{num} 的敘事目的",
                     "timeline_source": "beat"},
            "material_fit": {"visual_desc": visual_desc, "reason": f"用真實素材呈現「{visual_desc}」",
                             "need_refs": [need_id]},
            "audio": {"role": "music", "reason": "鋪底配樂"},
            "visual_style": {"layout": "montage", "pace": "fast", "reason": "結訓回顧節奏"},
            "text_layer": "none"}


def build_fixture():
    if ROOT.exists():
        shutil.rmtree(ROOT)                     # never trust prior .tmp/m6e artifacts
    ROOT.mkdir(parents=True)
    covered_specs = [_need(d, c, mh) for _, (src, c, d, mh) in COVERED.items()]
    missing_specs = [_need(d, c, mh, fb) for (c, d, mh, fb) in MISSING.values()]
    needs_covered = migrate_material_needs({"project": PROJECT, "needs": covered_specs})
    needs_full = migrate_material_needs({"project": PROJECT, "needs": covered_specs + missing_specs})
    (ROOT / "needs_covered.json").write_text(json.dumps(needs_covered, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "needs_full.json").write_text(json.dumps(needs_full, ensure_ascii=False, indent=2), encoding="utf-8")
    cov_ids = {spec["purpose"]: nid for spec, nid in
               zip(covered_specs, [n["need_id"] for n in needs_covered["needs"]])}
    full_ids = {n["purpose"]: n["need_id"] for n in needs_full["needs"]}

    maps_dir = ROOT / "maps"
    raw_dir = ROOT / "maps_raw"
    maps_dir.mkdir(); raw_dir.mkdir()
    db_files = []
    for key, (src, cat, desc, mh) in COVERED.items():
        nid = cov_ids[desc]
        scene = {"start": 0.0, "end": round(min(_dur(src), 6.0), 3), "caption": desc}
        base = {"asset_id": key, "asset_type": "video", "source": str(src),
                "duration_sec": round(_dur(src), 3)}
        (raw_dir / f"{key}.map.json").write_text(
            json.dumps({**base, "scenes": [dict(scene)]}, ensure_ascii=False, indent=2), encoding="utf-8")
        (maps_dir / f"{key}.map.json").write_text(json.dumps(
            {**base, "scenes": [{**scene, "satisfies": [{"need_id": nid, "status": "accepted"}]}]},
            ensure_ascii=False, indent=2), encoding="utf-8")
        # RELATIVE material_map path (no absolute workaround) — resolved against db dir
        db_files.append({"path": str(src), "material_map": f"maps/{key}.map.json"})
    (ROOT / "materials_db.json").write_text(
        json.dumps({"files": db_files}, ensure_ascii=False, indent=2), encoding="utf-8")

    d = cov_ids
    covered_segments = [_seg(1, d["主任對學員的期勉講話"], "主任對學員的期勉講話"),
                        _seg(2, d["結訓期間的慶生會同樂"], "結訓期間的慶生會同樂"),
                        _seg(3, d["學員感謝導師的橋段"], "學員感謝導師的橋段")]
    (ROOT / "contract_covered.json").write_text(json.dumps(
        {"style": "mv", "music": {"brief": "感性收尾"}, "material_needs_ref": "needs_covered.json",
         "segments": covered_segments}, ensure_ascii=False, indent=2), encoding="utf-8")
    full_segments = covered_segments + [_seg(4, full_ids["晨操晨跑體能訓練"], "晨操晨跑體能訓練"),
                                        _seg(5, full_ids["繩結法基本技能操作"], "繩結法基本技能操作")]
    (ROOT / "contract_full_norev.json").write_text(json.dumps(
        {"style": "mv", "music": {"brief": "感性收尾"}, "material_needs_ref": "needs_full.json",
         "segments": full_segments}, ensure_ascii=False, indent=2), encoding="utf-8")
    (ROOT / "contract_full.json").write_text(json.dumps(
        {"style": "mv", "music": {"brief": "感性收尾"}, "material_needs_ref": "needs_full.json",
         "revision_decisions_ref": "decisions.json", "segments": full_segments},
        ensure_ascii=False, indent=2), encoding="utf-8")
    lin = {"reviewer": "director", "reason": "本期未拍到,經導演同意自結訓片移除", "at": "2026-06-15T12:00:00"}
    (ROOT / "decisions.json").write_text(json.dumps([
        {"decision_id": "drop_morning", "need_id": full_ids["晨操晨跑體能訓練"], "route": "drop_segment",
         "status": "accepted", "target_segment": 4,
         "waiver": {"reviewer": "director", "reason": "本期無晨操素材,導演同意移除"}, "lineage": lin},
        {"decision_id": "drop_knot", "need_id": full_ids["繩結法基本技能操作"], "route": "drop_segment",
         "status": "accepted", "target_segment": 5,
         "waiver": {"reviewer": "director", "reason": "本期無繩結素材,導演同意移除"}, "lineage": lin},
    ], ensure_ascii=False, indent=2), encoding="utf-8")
    return cov_ids


def _last_json(text):
    """Return the LAST top-level JSON object in text (stdout may contain several)."""
    decoder = json.JSONDecoder()
    idx, last, n = 0, {}, len(text)
    while idx < n:
        brace = text.find("{", idx)
        if brace < 0:
            break
        try:
            obj, end = decoder.raw_decode(text, brace)
            last, idx = obj, end
        except json.JSONDecodeError:
            idx = brace + 1
    return last


def _lifecycle(out, **kw):
    """Run material-map-lifecycle from an UNRELATED cwd (proves cwd-independence)."""
    args = [PY, VT, "material-map-lifecycle", "--out-dir", str(ROOT / out)]
    for k, v in kw.items():
        args += [f"--{k.replace('_', '-')}", str(v)]
    with tempfile.TemporaryDirectory() as alien_cwd:
        r = subprocess.run(args, cwd=alien_cwd, capture_output=True, text=True)
    return _last_json(r.stdout), r.returncode


def _contract_run(contract, out, *, expect_ok):
    args = [PY, VT, "contract-run", str(ROOT / contract), "--material-db", str(ROOT / "materials_db.json"),
            "--out", str(ROOT / out / "final.mp4"), "--music", str(MUSIC),
            "--mat-dir", str(ROOT / out), "--quiet"]
    (ROOT / out).mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as alien_cwd:
        r = subprocess.run(args, cwd=alien_cwd, capture_output=True, text=True)
    return _last_json(r.stdout), r.returncode


def _check(cond, msg):
    print(("  PASS " if cond else "  FAIL ") + msg)
    if not cond:
        _check.failed = True


def main():
    _check.failed = False
    assert FOOT.exists(), f"footage not found: {FOOT} (set M6E_FOOTAGE)"
    cov = build_fixture()
    print(f"[fixture] relative material_map; covered need_ids: {cov}")

    print("ENTRY A — existing-material (raw maps, no needs)")
    rep, _ = _lifecycle("out_A", maps_dir=ROOT / "maps_raw")
    _check(rep.get("stage") == "await_requirements_discussion", f"stage={rep.get('stage')}")
    _check(not (ROOT / "out_A" / "final.mp4").exists(), "no final.mp4")

    print("ENTRY B — script-first, insufficient material")
    rep, _ = _lifecycle("out_B", needs=ROOT / "needs_full.json", material_db=ROOT / "materials_db.json")
    _check(rep.get("stage") == "await_material", f"stage={rep.get('stage')}")
    _check((ROOT / "out_B" / "shooting_brief.json").exists(), "shooting_brief.json written")
    res, rc = _contract_run("contract_full_norev.json", "out_B", expect_ok=False)
    _check(res.get("stage") == "material_delta" and rc != 0, f"BUILD blocked (stage={res.get('stage')}, rc={rc})")
    _check(not (ROOT / "out_B" / "final.mp4").exists(), "no final.mp4 (blocked before render)")

    print("ENTRY C — covered -> build_ready -> real render")
    rep, _ = _lifecycle("out_C", needs=ROOT / "needs_covered.json",
                        material_db=ROOT / "materials_db.json", contract=ROOT / "contract_covered.json")
    _check(rep.get("stage") == "build_ready", f"stage={rep.get('stage')}")
    res, rc = _contract_run("contract_covered.json", "out_C", expect_ok=True)
    final_c = ROOT / "out_C" / "final.mp4"
    _check(rc == 0 and final_c.exists() and final_c.stat().st_size > 0, f"final.mp4 rendered (rc={rc})")
    _check(bool(res.get("render_ok")) and bool(res.get("verify_ok")), "render_ok + verify_ok")

    print("ENTRY D — revision (drop+waive 2 missing must_have) -> real render")
    rep, _ = _lifecycle("out_D", needs=ROOT / "needs_full.json", material_db=ROOT / "materials_db.json",
                        contract=ROOT / "contract_full.json", decisions=ROOT / "decisions.json")
    _check(rep.get("stage") == "build_ready", f"stage={rep.get('stage')}")
    revised = json.loads((ROOT / "out_D" / "revised_segment_contract.json").read_text(encoding="utf-8"))
    _check([s["segment"] for s in revised["segments"]] == [1, 2, 3], "revised dropped seg 4,5")
    res, rc = _contract_run("contract_full.json", "out_D", expect_ok=True)
    final_d = ROOT / "out_D" / "final.mp4"
    _check(rc == 0 and final_d.exists() and final_d.stat().st_size > 0, f"revised final.mp4 rendered (rc={rc})")

    print("RESULT:", "FAIL" if _check.failed else "PASS — all four entries on real footage")
    sys.exit(1 if _check.failed else 0)


if __name__ == "__main__":
    main()
