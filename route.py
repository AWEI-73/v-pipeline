#!/usr/bin/env python3
"""route.py — 編排層 dispatcher（route skill 的執行體，step 3/3）。

讀 `<out>/state.json` 的 `next_action` 派工，router 在 pipeline **外面**，
pipeline 維持「單次確定性引擎」：

  無 state          → 完整 build（首輪）
  next_action null  → 完成，出片
  await_material    → 偵測學員素材到位（material-dir 內 seg{n}_user.*）：
                       到位則該段轉 source=local、`--only-seg n` 重渲那段；
                       未到位則印補拍指引、停下等素材
  retry:curator(…)  → pipeline 內部重試已用盡仍未達標 → 交人工換源/補拍
  review            → 交人工

把「讀 state→決定下一棒」從寫死控制流抽成可檢視、可恢復的外層迴圈。
"""
import argparse
import json
import os
import subprocess
import sys
import io

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except (AttributeError, io.UnsupportedOperation):
        pass

HERE = os.path.dirname(os.path.abspath(__file__))
_PHOTO_EXT = {"jpg", "jpeg", "png", "webp", "bmp"}
_VIDEO_EXT = {"mp4", "mov", "mkv", "webm", "m4v"}


def _load_state(outdir):
    p = os.path.join(outdir, "state.json")
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8") as f:
        return json.load(f)


def _run_pipeline(script_path, outdir, only_seg=None, verbose=False):
    from video_pipeline_core.platform_tools import resolve_python
    python_exe = resolve_python()
    runner_py = os.path.join(HERE, "run_with_ollama.py")
    cmd = [python_exe, runner_py, script_path, "--out", outdir]
    if only_seg:
        cmd += ["--only-seg", ",".join(str(n) for n in only_seg)]
    if verbose:
        cmd += ["--verbose"]
    return subprocess.run(cmd).returncode


def _run_mv(script_path, outdir, material_db, music, verbose=False):
    """MV 模式:route 驅動 canonical adapter 或 legacy mv_chain,寫 state.json 到 outdir。
    (旁白線走 _run_pipeline;MV 線走這裡——roadmap #7 route↔MV)。"""
    os.makedirs(outdir, exist_ok=True)
    with open(script_path, encoding="utf-8") as f:
        script = json.load(f)
    out_mp4 = os.path.join(outdir, "final.mp4")
    if _looks_like_segment_contract(script):
        from video_pipeline_core import contract_adapter  # noqa: PLC0415
        result = contract_adapter.run_contract(
            script_path,
            material_db=material_db,
            out_path=out_mp4,
            music_path=music,
            mat_dir=outdir,
            verbose=verbose,
        )
        return 0 if result.get("ok") else 1
    from video_pipeline_core import mv_cut  # noqa: PLC0415 — lazy(避免非 MV 情境載入 librosa 等)
    mv_cut.mv_chain(script, material_db, out_mp4, music_path=music,
                    mat_dir=outdir, verbose=verbose)
    return 0


def _looks_like_segment_contract(payload):
    segments = payload.get("segments") if isinstance(payload, dict) else None
    if not isinstance(segments, list) or not segments:
        return False
    first = segments[0]
    return isinstance(first, dict) and "core" in first and "material_fit" in first


def _report_mv_review(state):
    """印 MV state 的人工複核點(gap/必放/bookend)= 人在迴圈的接點。"""
    for b in state.get("blocking", []):
        print(f"   ⚠ seg{b['segment']}: {b['reason']}")
    for r in state.get("review_points", []):
        print(f"   👁 seg{r['segment']}: {r['reason']}")
    aq = (state.get("qa") or {}).get("audio_issues") or []
    for a in aq:
        print(f"   🔊 seg{a['segment']}: {a['message']}")


def _find_material(material_dir, n):
    """找學員素材 seg{n}_user.* 或 seg{n}.*（圖或影片）。"""
    if not material_dir or not os.path.isdir(material_dir):
        return None
    want = (f"seg{n}_user", f"seg{n}")
    for fn in sorted(os.listdir(material_dir)):
        base, _, ext = fn.rpartition(".")
        if ext.lower() in (_PHOTO_EXT | _VIDEO_EXT) and base.lower() in want:
            return os.path.join(material_dir, fn)
    return None


def _route_mv(args):
    """MV 派工:無 state→跑 mv_chain;有 state→依 next_action 報告複核點。
    MV 缺口(gap/必放/bookend)需要新素材進 material_db,故 route 不自動回填,
    而是把人工複核點清楚列出(人在迴圈的接點)。"""
    if not args.material_db or not args.music:
        print("[route:mv] 需要 --material-db 與 --music(先 ingest-meta+caption-meta 建 db、music-fetch 抓樂)")
        return 2
    state = _load_state(args.out)
    if state is None:
        print("[route:mv] 無 state → 跑 mv_chain(match-mv → render)")
        _run_mv(args.script, args.out, args.material_db, args.music, verbose=args.verbose)
        state = _load_state(args.out)
        if state is None:
            print("[route:mv] mv_chain 未產出 state")
            return 1
    na = state.get("next_action")
    print(f"[route:mv] next_action={na}  final={state.get('final')}")
    if na == "await_material":
        print("[route:mv] ⏳ 有缺口/必放未滿,需補素材進 material_db(人工複核):")
        _report_mv_review(state)
        return 0
    print(f"[route:mv] ✅ 出片(audio_pairing={state.get('qa', {}).get('audio_pairing')})。建議複核:")
    _report_mv_review(state)
    return 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", required=True)
    ap.add_argument("--material-dir", default=None,
                    help="學員素材夾；含 seg{n}_user.jpg/mp4 則該段轉 local 重渲")
    ap.add_argument("--max-rounds", type=int, default=4)
    ap.add_argument("--mv", action="store_true",
                    help="MV 模式:驅動 mv_chain(match-mv→render)而非旁白 pipeline")
    ap.add_argument("--material-db", default=None, help="MV 模式:material_db.json(curator 產)")
    ap.add_argument("--music", default=None, help="MV 模式:背景音樂檔(先 music-fetch 抓好)")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    with open(args.script, encoding="utf-8") as f:
        raw = json.load(f)
    wrapper = raw if isinstance(raw, dict) else {"segments": raw}
    work_script = args.script

    if args.mv:
        try:
            import librosa
            import soundfile
        except ImportError as e:
            print(f"[route:mv] ⚠️ 缺少 MV 模式必要的音訊處理套件: {e}")
            print("   請先執行 `pip install librosa soundfile` 以啟用 MV 模式。")
            return 1
        return _route_mv(args)

    for rnd in range(1, args.max_rounds + 1):
        state = _load_state(args.out)
        if state is None:
            print(f"[route] round {rnd}: 無 state → 完整 build")
            _run_pipeline(work_script, args.out, verbose=args.verbose)
            continue

        na = state.get("next_action")
        print(f"[route] round {rnd}: next_action={na}")

        if na is None:
            print(f"[route] ✅ 完成：{state.get('final')}  (qa={state.get('qa', {}).get('score')})")
            return 0

        if na == "await_material":
            blocking = state.get("blocking", [])
            arrived = [(b["segment"], _find_material(args.material_dir, b["segment"]))
                       for b in blocking]
            arrived = [(n, f) for n, f in arrived if f]
            if arrived:
                by_id = {s["segment"]: s for s in wrapper.get("segments", [])}
                for n, f in arrived:
                    by_id[n]["source"] = "local"
                    by_id[n]["file"] = os.path.abspath(f)
                    print(f"[route] seg{n} 學員素材到位 → source=local ({os.path.basename(f)})")
                work_script = os.path.join(args.out, "script_routed.json")
                with open(work_script, "w") as fh:
                    json.dump(wrapper, fh, ensure_ascii=False, indent=2)
                _run_pipeline(work_script, args.out,
                              only_seg=[n for n, _ in arrived], verbose=args.verbose)
                continue
            print("[route] ⏳ 等待學員素材（補拍指引）：")
            for b in blocking:
                print(f"   - seg{b['segment']}: {b['reason']}")
            return 0

        if na.startswith("retry:curator"):
            print(f"[route] ⚠️ pipeline 內部重試已用盡仍未達標：{na}")
            print("   → 需換素材源/補拍，或人工調整 search_query。")
            return 0

        print(f"[route] next_action={na} → 交人工 review")
        return 0

    print(f"[route] 達 max-rounds={args.max_rounds} 上限，停止")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
