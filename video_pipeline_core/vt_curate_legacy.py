"""vt_curate_legacy.py — 舊版小編(whisper analyze / pexels-search curate / rank-local)。
從 video_tools 解耦隔離。⚠️ legacy:與新 curator.py(ingest/caption/match-mv)概念重疊,
之後評估淘汰。共用原語取自 vt_core。"""
import os
import sys
import json
import re  # noqa: F401
import subprocess  # noqa: F401
from .vt_core import FFMPEG, FFPROBE, run, ToolError  # noqa: F401

# ── curator: 小編 ────────────────────────────────────────────────────────

_STOPWORDS = {
    'the', 'a', 'an', 'of', 'in', 'on', 'at', 'to', 'for', 'with', 'by',
    'is', 'are', 'was', 'were', 'be', 'been', 'being', 'and', 'or', 'but',
    'how', 'what', 'why', 'when', 'where', 'who', 'which',
    'this', 'that', 'these', 'those', 'it', 'its', 'as',
    'explained', 'works', 'work',
}


def _tokenize(text: str) -> set:
    """簡單分詞 + 去停用詞 + 小寫化"""
    import re
    words = re.findall(r"[a-zA-Z]{2,}|\d{4}", text.lower())
    return {w for w in words if w not in _STOPWORDS}


def _whisper_transcribe(video_path: str, cache_path: str = None, language: str = None):
    """轉譯影片，回傳 segment 列表 [{start, end, text}]，有 cache 用 cache"""
    if cache_path and os.path.exists(cache_path):
        with open(cache_path, encoding="utf-8") as f:
            return json.load(f)

    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise ToolError("需要 faster-whisper: pip install faster-whisper --break-system-packages")

    # CPU mode + int8 量化（最快，準度夠用做關鍵字比對）
    model = WhisperModel("base", device="cpu", compute_type="int8")
    segments, info = model.transcribe(video_path, language=language, beam_size=1)
    out = [{"start": s.start, "end": s.end, "text": s.text.strip()} for s in segments]

    if cache_path:
        os.makedirs(os.path.dirname(cache_path), exist_ok=True)
        with open(cache_path, 'w', encoding='utf-8') as f:
            json.dump(out, f, ensure_ascii=False, indent=2)
    return out


def _find_best_window(segments: list, query: str, target_sec: float):
    """從 transcript segments 找出最匹配 query 的時間窗口。

    邊界保護：best_start 不會大於 (total_duration - target_sec)，
    確保 (start, start+target) 完全落在素材時長內，避免下游 assemble 剪不到完整段。
    """
    if not segments:
        return None

    total_dur = segments[-1]["end"]
    # 若素材本身比 target 還短，回傳整段
    if total_dur <= target_sec:
        return {"start": 0.0, "end": round(total_dur, 2),
                "score": 0, "excerpt": ' '.join(s["text"] for s in segments)[:200]}

    max_start = total_dur - target_sec  # 最後一個合法 start

    query_tokens = _tokenize(query)
    if not query_tokens:
        return {"start": 0.0, "end": round(target_sec, 2),
                "score": 0, "excerpt": ""}

    # 對每個 segment 算 keyword overlap
    scored = []
    for s in segments:
        st = _tokenize(s["text"])
        overlap = len(st & query_tokens)
        scored.append({"start": s["start"], "end": s["end"], "text": s["text"],
                       "score": overlap})

    # 滑動窗口：跳過會超出邊界的 anchor，避免下游剪不到 target_sec
    best = {"start": 0.0, "end": round(target_sec, 2), "score": -1, "excerpt": ""}
    for i, anchor in enumerate(scored):
        if anchor["start"] > max_start:
            break  # transcript 按時間排序，後面也都會超出
        end_time = anchor["start"] + target_sec
        window_score = 0
        window_text = []
        for s in scored[i:]:
            if s["start"] >= end_time:
                break
            window_score += s["score"]
            window_text.append(s["text"])
        if window_score > best["score"]:
            best = {
                "start": round(anchor["start"], 2),
                "end": round(end_time, 2),
                "score": window_score,
                "excerpt": ' '.join(window_text)[:200],
            }
    return best


def cmd_analyze(args):
    """小編：Whisper 轉譯 + 找最匹配 query 的時間窗口"""
    if not os.path.exists(args.video):
        raise ToolError(f"video not found: {args.video}")

    target = args.target_sec or 20.0
    cache_dir = os.path.join(os.path.dirname(os.path.abspath(args.video)), ".transcripts")
    cache_path = os.path.join(cache_dir, os.path.basename(args.video) + ".json")

    segments = _whisper_transcribe(args.video, cache_path=cache_path,
                                     language=args.language)
    best = _find_best_window(segments, args.query, target)
    if not best:
        raise ToolError("no transcript segments found")

    print(json.dumps({
        "status": "ok",
        "video": args.video,
        "query": args.query,
        "target_sec": target,
        "best_start_sec": best["start"],
        "best_end_sec": best["end"],
        "score": best["score"],
        "excerpt": best["excerpt"],
        "cache_path": cache_path,
    }, ensure_ascii=False))


def _search_candidates(query: str, limit: int = 5):
    """呼叫 search 取候選"""
    res = subprocess.run([
        sys.executable, __file__, "search", query, "--limit", str(limit)
    ], capture_output=True, text=True, timeout=120)
    if res.returncode != 0:
        return []
    try:
        return json.loads(res.stdout)
    except json.JSONDecodeError:
        return []


def _filter_candidates(cands: list):
    """過濾掉太短/太長/talking-head/news"""
    bad = ['news', 'breaking', '新聞', 'shorts', '#shorts', 'live stream',
           'interview', 'podcast']
    out = []
    for c in cands:
        d = c.get('duration') or 0
        if d < 60 or d > 600:
            continue
        title = (c.get('title') or '').lower()
        if any(k in title for k in bad):
            continue
        out.append(c)
    return out


def cmd_curate(args):
    """小編全自動：search + download + analyze + 選最佳 → clip_list.json"""
    for p in [args.script, args.timing]:
        if not os.path.exists(p):
            raise ToolError(f"not found: {p}")

    with open(args.script, encoding="utf-8") as f: script = json.load(f)
    with open(args.timing, encoding="utf-8") as f: timing = json.load(f)
    tts_durs = {s['segment']: s['duration_sec'] for s in timing.get('segments', [])}

    workdir = args.workdir or "curate_out"
    os.makedirs(workdir, exist_ok=True)
    top_n = args.top_n or 1

    clip_segments = []
    for seg in script:
        n = seg['segment']
        query = seg['search_query']
        target_dur = tts_durs.get(n)
        if target_dur is None:
            raise ToolError(f"segment {n}: no tts_timing")

        print(f"\n--- Seg {n}: {seg.get('title')} ---", file=sys.stderr)
        print(f"  query: {query} target={target_dur:.2f}s", file=sys.stderr)

        # 1. search + filter
        cands = _filter_candidates(_search_candidates(query, limit=10))
        if not cands:
            print(f"  ❌ 無候選", file=sys.stderr)
            continue
        cands = cands[:top_n]

        # 2. 對 top_n 個候選 download + analyze
        best_choice = None
        for c in cands:
            print(f"  → download: {c['title'][:60]}", file=sys.stderr)
            raw_path = os.path.join(workdir, f"seg{n}_{c['id']}.mp4")
            if not os.path.exists(raw_path):
                # 下載中段 max(180s, target*6)，給 analyze 足夠的選擇空間，
                # 同時確保 Whisper 找的 best_start + target 不會超出邊界
                total = int(c.get('duration') or 300)
                chunk_dur = max(180, int(target_dur * 6))
                start_sec = int(total * 0.15)
                end_sec = int(min(total, start_sec + chunk_dur))
                s_hms = f"{start_sec // 3600:02d}:{(start_sec % 3600) // 60:02d}:{start_sec % 60:02d}"
                e_hms = f"{end_sec // 3600:02d}:{(end_sec % 3600) // 60:02d}:{end_sec % 60:02d}"
                dl = subprocess.run([
                    sys.executable, __file__, "download", c['url'],
                    "--start", s_hms, "--end", e_hms, "--out", raw_path
                ], capture_output=True, text=True, timeout=300)
                if dl.returncode != 0 or not os.path.exists(raw_path):
                    print(f"     download failed", file=sys.stderr)
                    continue

            # analyze
            print(f"  → analyze (Whisper)...", file=sys.stderr)
            cache_dir = os.path.join(workdir, ".transcripts")
            cache_path = os.path.join(cache_dir, os.path.basename(raw_path) + ".json")
            try:
                segments = _whisper_transcribe(raw_path, cache_path=cache_path,
                                                 language='en')
            except SystemExit:
                continue
            best = _find_best_window(segments, query, target_dur)
            if not best:
                continue
            print(f"     score={best['score']} start={best['start']:.1f}s", file=sys.stderr)

            choice = {
                "file": raw_path,
                "cut_start_sec": best['start'],
                "cut_end_sec": best['end'],
                "metadata": {
                    "url": c['url'],
                    "title": c['title'],
                    "score": best['score'],
                    "excerpt": best['excerpt'][:100],
                },
            }
            if best_choice is None or best['score'] > best_choice['metadata']['score']:
                best_choice = choice

        if best_choice is None:
            print(f"  ❌ 沒有可用素材", file=sys.stderr)
            continue

        best_choice['segment'] = n
        clip_segments.append({
            "segment": n,
            "file": best_choice['file'],
            "cut_start_sec": best_choice['cut_start_sec'],
            "cut_end_sec": best_choice['cut_end_sec'],
            "metadata": best_choice['metadata'],
        })
        print(f"  ✅ 選: {best_choice['metadata']['title'][:50]} @ {best_choice['cut_start_sec']:.1f}s",
              file=sys.stderr)

    out = args.out or os.path.join(workdir, "clip_list.json")
    with open(out, 'w', encoding='utf-8') as f:
        json.dump({"segments": clip_segments}, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "ok",
        "clip_list": out,
        "segments_total": len(script),
        "segments_filled": len(clip_segments),
        "workdir": workdir,
    }, ensure_ascii=False))


def cmd_rank_local(args):
    """讀含 vision_score 的 materials_db.json，配對 material_needs → clip_list.json

    vision_score 結構（由 agent 看圖填入）：
      {
        "by_need": {"1.1": 8, "2.3": 9, ...},   各 need 的 0-10 分
        "best_need": "2.3",
        "description": "...",
        "quality_flags": ["high_quality", "action_shot", ...]
      }
    """
    if not os.path.exists(args.db):
        raise ToolError(f"db not found: {args.db}")
    if not os.path.exists(args.needs):
        raise ToolError(f"needs not found: {args.needs}")

    with open(args.db, encoding="utf-8") as f: db = json.load(f)
    with open(args.needs, encoding="utf-8") as f: needs = json.load(f)

    files = db.get('files', [])
    scored = [f for f in files if f.get('vision_score')]
    if not scored:
        raise ToolError(f"materials_db has no vision_score yet — agent 須先看圖填分")

    # 對每個 need 找最高分材料
    used_files = set()
    assignments = []
    no_match = []

    # 先處理 must_have，再處理 nice_to_have
    flat_needs = []
    for seg in needs.get('segments', []):
        for n in seg.get('needs', []):
            flat_needs.append({
                "segment": seg['segment'],
                "section": seg.get('section'),
                "need_id": n['id'],
                "category": n.get('category'),
                "type": n.get('type'),
                "purpose": n.get('purpose'),
                "count": n.get('count', 1),
                "duration_each": n.get('duration_each'),
                "must_have": n.get('must_have', False),
                "fallback_tier": n.get('fallback_tier', 1),
            })
    flat_needs.sort(key=lambda x: (not x['must_have'], x['fallback_tier']))

    for need in flat_needs:
        nid = need['need_id']
        candidates = []
        for fobj in files:
            if fobj['id'] in used_files:
                continue
            vs = fobj.get('vision_score')
            if not vs: continue
            score = vs.get('by_need', {}).get(nid)
            if score is None: continue
            candidates.append({
                "id": fobj['id'],
                "score": score,
                "file": fobj,
            })
        candidates.sort(key=lambda x: -x['score'])

        if not candidates or candidates[0]['score'] < 5:
            no_match.append({"need_id": nid, "must_have": need['must_have'],
                              "best_available": candidates[0]['score'] if candidates else None})
            continue

        # 取 top-N 對應 count
        picks = candidates[:need['count']]
        for p in picks:
            used_files.add(p['id'])
        assignments.append({
            "need": need,
            "picks": [{
                "id": p['id'],
                "path": p['file']['path'],
                "type": p['file']['type'],
                "score": p['score'],
                "description": p['file']['vision_score'].get('description', ''),
            } for p in picks],
        })

    out = args.out or "clip_list.json"

    # 同時產生剪輯師可吃的 clip_list（影片格式）
    clip_segments = []
    seen_segments = {}
    for a in assignments:
        seg_num = a['need']['segment']
        if seg_num not in seen_segments:
            seen_segments[seg_num] = []
        for p in a['picks']:
            seen_segments[seg_num].append({
                "need_id": a['need']['need_id'],
                "file": p['path'],
                "type": p['type'],
                "score": p['score'],
                "description": p['description'],
            })

    for seg_num in sorted(seen_segments.keys()):
        clip_segments.append({
            "segment": seg_num,
            "picks": seen_segments[seg_num],
        })

    output = {
        "based_on_db": args.db,
        "based_on_needs": args.needs,
        "total_needs": len(flat_needs),
        "matched": len(assignments),
        "unmatched": len(no_match),
        "unmatched_details": no_match,
        "assignments": assignments,
        "clip_segments": clip_segments,
    }
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    must_have_unmatched = [n for n in no_match
                           if any(fn['need_id'] == n['need_id'] and fn['must_have']
                                  for fn in flat_needs)]

    print(json.dumps({
        "status": "ok",
        "out": out,
        "needs_total": len(flat_needs),
        "matched": len(assignments),
        "unmatched": len(no_match),
        "must_have_missing": len(must_have_unmatched),
    }, ensure_ascii=False))
