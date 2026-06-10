#!/usr/bin/env python3
"""
video_pipeline.py — end-to-end orchestrator with VLM pre-pick gate (P1-1)
"""
import argparse
import base64
import datetime
import json
import math
import os
import shutil
import subprocess
import sys
import traceback
import urllib.parse
import urllib.request

from video_pipeline_core.vt_core import FIX_TARGET

def _load_dotenv(path):
    """Minimal .env loader (no external deps). KEY=VALUE per line; '#' comments.
    Does NOT override variables already present in the environment."""
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
    except FileNotFoundError:
        pass


# Secrets come from env / .env only — never hardcoded (keys must not enter git).
# Priority: real env var > project .env > video_director profile .env.
_HERE = os.path.dirname(os.path.abspath(__file__))
_load_dotenv(os.path.join(_HERE, ".env"))
# Platform-portable profile dotenv: check platform-specific profile dir.
import platform as _plat
if _plat.system() != "Windows":
    _load_dotenv("/home/lio730309/.hermes/profiles/video_director/.env")
for _req in ("PEXELS_API_KEY", "PIXABAY_API_KEY"):
    if not os.environ.get(_req):
        print(f"[warn] {_req} not set — material search will fail. "
              f"Add it to {_HERE}/.env (copy .env.example).", file=sys.stderr)
# No longer inject Linux-only PATH; platform_tools.resolve_* handles discovery.

# Single source of truth: run the repo copy of video_tools.py (the workspace
# copy was a stale snapshot — its drift silently dropped D3/effects changes).
TOOLS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "video_tools.py")
CONTENT_QA_MODULE = "video_pipeline_core.content_qa"

from video_pipeline_core.platform_tools import (
    resolve_ffmpeg as _resolve_ffmpeg,
    resolve_ffprobe as _resolve_ffprobe,
    resolve_python as _resolve_python,
)
try:
    FFMPEG = _resolve_ffmpeg()
except Exception:
    FFMPEG = "ffmpeg"
try:
    FFPROBE = _resolve_ffprobe()
except Exception:
    FFPROBE = "ffprobe"
_PYTHON = _resolve_python()


def vprint(msg, verbose):
    if verbose: print(msg, file=sys.stderr)


def atomic_write_json(path, obj):
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=2)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def run_tool(args, verbose=False):
    res = subprocess.run([_PYTHON, TOOLS, *args], capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"tool {args[0]} failed (code {res.returncode}):\nSTDOUT: {res.stdout.strip()}\nSTDERR: {res.stderr.strip()}")
    vprint(f"  [tool {args[0]}] ok", verbose)
    return res.stdout


def run_content_qa(outdir, model, weight, verbose=False, no_strict=False):
    """Run content_qa.py — injects content_alignment dim into qa_report.json and
    recomputes weighted score/pass. Returns parsed stdout summary dict
    (status, avg_score, min_score, low_segments, total_segments)."""
    cmd = [_PYTHON, "-m", CONTENT_QA_MODULE, outdir, "--model", model, "--weight", str(weight)]
    if no_strict:
        cmd.append("--no-strict")
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"content_qa failed: {(res.stderr or '')[:600]}")
    if verbose and res.stderr:
        print(res.stderr.rstrip(), file=sys.stderr)
    try:
        return json.loads(res.stdout.strip().splitlines()[-1])
    except Exception:
        return {"status": "unparsed", "low_segments": []}


def dur(path):
    return float(subprocess.check_output([
        FFPROBE, '-v', 'error', '-show_entries', 'format=duration',
        '-of', 'default=noprint_wrappers=1:nokey=1', path]).decode().strip())


def extract_tiled_frames(src, duration, out_path, num_samples=3, start_offset=0.0):
    import tempfile
    duration = float(duration or 0)
    if duration <= 0 or num_samples <= 0:
        return
    timestamps = [start_offset + duration * (i + 0.5) / num_samples for i in range(num_samples)]
    with tempfile.TemporaryDirectory() as tmp:
        frame_paths = []
        cell_width, cell_height = 480, 270
        scale_vf = f"scale={cell_width}:{cell_height}:force_original_aspect_ratio=decrease," \
                   f"pad={cell_width}:{cell_height}:(ow-iw)/2:(oh-ih)/2,setsar=1"
        for i, ts in enumerate(timestamps):
            frame = os.path.join(tmp, f"seq_{i:03d}.jpg")
            r = subprocess.run([
                FFMPEG, "-y", "-ss", f"{ts:.3f}", "-i", str(src),
                "-frames:v", "1", "-q:v", "2", "-vf", scale_vf, frame
            ], capture_output=True)
            if r.returncode == 0 and os.path.exists(frame):
                frame_paths.append(frame)
        if frame_paths:
            tile_cols = len(frame_paths)
            tile_rows = 1
            subprocess.run([
                FFMPEG, "-y", "-framerate", "1", "-i", os.path.join(tmp, "seq_%03d.jpg"),
                "-vf", f"tile={tile_cols}x{tile_rows}", "-frames:v", "1", str(out_path)
            ], capture_output=True)


def probe_video(path):
    """Return dict with pix_fmt, color_range, avg_frame_rate, width, height, duration."""
    out = subprocess.check_output([
        FFPROBE, '-v', 'error', '-select_streams', 'v:0',
        '-show_entries', 'stream=pix_fmt,color_range,avg_frame_rate,width,height:format=duration',
        '-of', 'json', path]).decode()
    j = json.loads(out)
    st = (j.get("streams") or [{}])[0]
    fmt = j.get("format", {})
    fr_num, _, fr_den = (st.get("avg_frame_rate") or "0/1").partition("/")
    try: fps = float(fr_num) / max(float(fr_den or 1), 1e-9)
    except Exception: fps = 0
    return {
        "pix_fmt": st.get("pix_fmt"),
        "color_range": st.get("color_range"),
        "fps": round(fps, 3),
        "width": st.get("width"), "height": st.get("height"),
        "duration": float(fmt.get("duration", 0)),
    }


def precompose_gate(seg_paths, script, actual_dur, xfade, tol=0.3):
    """P1-2 pre-compose gate. Returns dict {ok, issues}. Raises if fatal."""
    issues = []
    seg_ids = [s["segment"] for s in script]
    if len(seg_paths) != len(seg_ids):
        issues.append(f"seg_count_mismatch: paths={len(seg_paths)} script={len(seg_ids)}")
    last_id = seg_ids[-1] if seg_ids else None
    expected_pix = "yuv420p"
    expected_range = "tv"
    expected_fps = 30.0
    expected_w, expected_h = 1920, 1080
    for n, p in zip(seg_ids, seg_paths):
        if not (p and os.path.exists(p) and os.path.getsize(p) > 0):
            issues.append(f"seg{n}: file_missing_or_empty path={p}")
            continue
        try:
            info = probe_video(p)
        except Exception as e:
            issues.append(f"seg{n}: probe_failed {type(e).__name__}")
            continue
        target_len = actual_dur[n] + (0 if n == last_id else xfade)
        diff = abs(info["duration"] - target_len)
        if diff > tol:
            issues.append(f"seg{n}: duration {info['duration']:.3f}s != target {target_len:.3f}s (Δ{diff*1000:.0f}ms > {tol*1000:.0f}ms)")
        if info["pix_fmt"] != expected_pix:
            issues.append(f"seg{n}: pix_fmt={info['pix_fmt']} != {expected_pix}")
        if info["color_range"] not in (expected_range, "tv"):
            issues.append(f"seg{n}: color_range={info['color_range']} != tv")
        if info["fps"] and abs(info["fps"] - expected_fps) > 0.5:
            issues.append(f"seg{n}: fps={info['fps']} != {expected_fps}")
        if info["width"] != expected_w or info["height"] != expected_h:
            issues.append(f"seg{n}: size={info['width']}x{info['height']} != {expected_w}x{expected_h}")
    return {"ok": not issues, "issues": issues}


def pixabay_search(query, kind, limit=20):
    """Return Pexels-compatible candidate dicts from Pixabay. kind in {'video','photo'}."""
    key = os.environ.get("PIXABAY_API_KEY", "").strip()
    if not key:
        return []
    q = urllib.parse.quote(query)
    per_page = min(max(limit, 3), 50)
    if kind == "video":
        url = f"https://pixabay.com/api/videos/?key={key}&q={q}&per_page={per_page}"
    else:
        url = f"https://pixabay.com/api/?key={key}&q={q}&image_type=photo&per_page={per_page}"
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            data = json.loads(r.read().decode())
    except Exception:
        return []
    out = []
    for h in data.get("hits", []):
        if kind == "video":
            vids = h.get("videos", {})
            v = vids.get("medium") or vids.get("large") or vids.get("small") or vids.get("tiny") or {}
            if not v.get("url"):
                continue
            out.append({
                "source": "pixabay", "id": h.get("id"),
                "alt": h.get("tags", ""), "user": h.get("user", ""),
                "url": h.get("pageURL", ""),
                "duration": h.get("duration", 0),
                "width": v.get("width", 0), "height": v.get("height", 0),
                "thumbnail_url": v.get("thumbnail", ""),
                "download_url": v.get("url", ""),
            })
        else:
            out.append({
                "source": "pixabay", "id": h.get("id"),
                "alt": h.get("tags", ""), "user": h.get("user", ""),
                "url": h.get("pageURL", ""),
                "width": h.get("imageWidth", 0), "height": h.get("imageHeight", 0),
                "thumbnail_url": h.get("previewURL") or h.get("webformatURL"),
                "download_url": h.get("largeImageURL") or h.get("webformatURL"),
            })
    return out


def fetch_photo_candidates(search_query, verbose):
    """Fetch photo candidates from Pexels and Pixabay."""
    try:
        res = run_tool(["pexels-search", search_query, "--type", "photo", "--limit", "20"], verbose)
        pex = json.loads(res).get("candidates", [])
        for c in pex:
            c.setdefault("source", "pexels")
    except Exception:
        pex = []
    try:
        pix = pixabay_search(search_query, "photo", limit=20)
    except Exception:
        pix = []
    return pex + pix


def score_candidate(c, query, target_dur, is_video):
    kws = [k.lower() for k in query.split() if len(k) > 2]
    blob = " ".join(str(c.get(k) or "") for k in ("alt", "url", "user")).lower()
    kw_hits = sum(1 for k in kws if k in blob)
    s = kw_hits * 10
    reasons = [f"kw_match={kw_hits}/{len(kws)}"]
    if is_video:
        d = c.get("duration", 0)
        if d >= target_dur + 1:
            over = d - target_dur
            s += max(0, 10 - over * 0.3)
            reasons.append(f"dur={d}s")
        else:
            s -= 100
            reasons.append(f"DUR_SHORT={d}<{target_dur+1}")
    else:
        w = c.get("width", 0)
        if w >= 4000: s += 5; reasons.append(f"hires={w}")
        elif w >= 2000: s += 2
    return s, "|".join(reasons)


def _seg_target_len(n, script, actual_dur, xfade):
    """Real render target for segment n: TTS actual duration + xfade tail
    (the last segment has no tail). Single source of truth — render_* and the
    candidate picker must agree, or video stock gets selected against the wrong
    length and the precompose gate / render hard-fails (Longform Duration Policy)."""
    is_last = (n == script[-1]["segment"])
    return actual_dur[n] + (0 if is_last else xfade)


def _filter_video_candidates(cands, target_len):
    """Keep video candidates at least 1s longer than the real render target.
    Keyed off TTS `target_len`, NOT script `duration_sec` — the 5-min stress test
    showed TTS narration runs longer than the scripted estimate, so filtering by
    the script value let through clips that were physically too short to render."""
    return [c for c in cands if (c.get("duration") or 0) >= target_len + 1]


def _video_fill_plan(raw_d, target_len, tol=0.05):
    """Decide how to make a raw video clip fill the render target without aborting.

    Longform Duration Policy fallback ladder (after "pick a longer candidate"):
    a clip shorter than target must be recovered, never crash the pipeline.
      - raw long enough  → trim (centered window)
      - raw short        → loop (-stream_loop N) then trim to target
    Returns {"mode": "trim"|"loop", "loops": int, "start": float}."""
    if raw_d >= target_len - tol:
        start = max(0.0, (raw_d - target_len) / 2)
        return {"mode": "trim", "loops": 0, "start": round(start, 3)}
    # need to repeat the clip enough times to cover target, then trim exact
    loops = max(1, math.ceil(target_len / max(raw_d, 0.1)) - 1)
    return {"mode": "loop", "loops": loops, "start": 0.0}


def _bgm_plan(script_bgm):
    """Classify a script `bgm` field into a resolution plan.
      dict {"query"/"mood",...} → ("fetch", payload)  real music via music-fetch
      str  (mood name or path)  → ("local", name)     placeholder lib / existing file
      falsy                     → ("none", None)
    """
    if not script_bgm:
        return ("none", None)
    if isinstance(script_bgm, dict):
        return ("fetch", script_bgm)
    return ("local", script_bgm)


# fix_class → 該回哪一功能層修（VERIFY 發類別、route 依此回層；見 skills/route.md）。
# 單一真相在 vt_core，這裡保留舊名 alias，避免既有 tests/agent prompt 斷掉。
_FIX_TARGET = FIX_TARGET


class RecoverableBuildError(Exception):
    """一段 BUILD 失敗，但**不該炸掉整片**——記成 build block、出片用 placeholder，
    再由 state→route 決定回哪一層。`fix_class` ∈ material|spec|human（見 _FIX_TARGET）。
    `segment=0` 表示整片級（如 precompose gate），交人工 review。"""
    def __init__(self, segment, reason, fix_class="material"):
        super().__init__(reason)
        self.segment = segment
        self.reason = reason
        self.fix_class = fix_class


def _parse_yn(raw):
    """Parse a VLM yes/no/somewhat answer in English OR Chinese."""
    r = raw.strip(); rl = r.lower()
    if r[:1] in ("是", "對") or rl.startswith("yes"): return "yes"
    if r[:1] in ("否", "不", "沒") or rl.startswith("no"): return "no"
    if "部分" in r or "somewhat" in rl or "partial" in rl or "有點" in r or "稍微" in r:
        return "somewhat"
    # negation must beat the substring it contains (e.g. 不符合 contains 符合)
    if "不符" in r or "沒有" in r or "no" in rl: return "no"
    if "符合" in r or "相符" in r or "yes" in rl: return "yes"
    return "unknown"


def _ollama_vlm_yn(model, image_path, prompt, np=10, ollama_url=None):
    if ollama_url is None:
        ollama_url = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    body = json.dumps({
        "model": model, "prompt": prompt, "images": [b64], "stream": False,
        "options": {"temperature": 0.0, "num_predict": np},
    }).encode()
    import time as _t
    last_err = None
    # 4 attempts with exponential backoff (2/4/8s) absorb Ollama cold-load
    # latency where the configured VLM transiently 5xx's while loading weights.
    for attempt in range(4):
        try:
            req = urllib.request.Request(
                f"{ollama_url}/api/generate", data=body,
                headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(req, timeout=120) as r:
                raw = json.loads(r.read().decode()).get("response", "").strip().lower()
            return _parse_yn(raw)
        except Exception as e:
            last_err = type(e).__name__
            if attempt < 3:
                _t.sleep(2 ** (attempt + 1))
    return f"error:{last_err}"


def _download_thumb(url, dst_path):
    if os.path.exists(dst_path):
        return dst_path
    os.makedirs(os.path.dirname(dst_path), exist_ok=True)
    try:
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                          "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "image/webp,image/jpeg,image/*,*/*;q=0.8",
        })
        with urllib.request.urlopen(req, timeout=30) as r:
            data = r.read()
        with open(dst_path, "wb") as f: f.write(data)
        return dst_path
    except Exception:
        return None


def _vlm_check_one(seg_n, query, cand, cand_idx, thumbs_dir, model, verbose, tag="", verify_desc=None):
    """Return (verdict, thumb_path). verdict in {yes,no,somewhat,unknown,no_thumb,download_fail,error:*}.

    Verification matches the image against a Chinese VISUAL description
    (visual_desc, else narration text) rather than the search keyword: a concrete
    visual spec is what 4b can actually judge against. Falls back to the keyword
    query when no description is available. (D5)"""
    thumb_url = cand.get("thumbnail_url") or cand.get("download_url")
    if not thumb_url:
        return "no_thumb", None
    suffix = f"_{tag}" if tag else ""
    thumb_path = f"{thumbs_dir}/seg{seg_n}_c{cand_idx}{suffix}.jpg"
    if not _download_thumb(thumb_url, thumb_path):
        return "download_fail", None
    if verify_desc:
        prompt = (f"這張圖適不適合當以下畫面描述的配圖？\n"
                  f"畫面：「{verify_desc}」\n只回答 是、否、或 部分。")
    else:
        prompt = f"Does this image primarily show {query}? Answer only yes or no."
    v = _ollama_vlm_yn(model, thumb_path, prompt)
    if verbose:
        print(f"  prepick seg{seg_n} c{cand_idx}{suffix}: {v}", file=sys.stderr)
    return v, thumb_path


def _has_cjk(s):
    return any("一" <= c <= "鿿" for c in s)


def _simplify_query(q):
    """Generate up to 2 simpler queries from the original.

    English: last 2-3 words, first 2 words (whitespace tokens).
    CJK (no real word boundaries): degrade by whitespace tokens, else by
    character bigrams, so the fallback search still has something to try
    instead of producing garbage word-slices. (D2)
    """
    words = [w for w in q.split() if w.strip()]
    out = []
    if _has_cjk(q):
        if len(words) >= 2:
            # try each whitespace-separated chunk on its own
            out.extend(words[:3])
        else:
            chars = [c for c in q if not c.isspace()]
            if len(chars) >= 4:
                # leading and trailing character bigrams
                out.append("".join(chars[:2]))
                out.append("".join(chars[-2:]))
    else:
        if len(words) >= 4:
            out.append(" ".join(words[-3:]))
        if len(words) >= 3:
            out.append(" ".join(words[:2]))
    seen = set(); uniq = []
    for s in out:
        if s and s != q and s not in seen:
            seen.add(s); uniq.append(s)
    return uniq


def prepick_vlm_filter(seg_n, query, scored_top, candidates_list, thumbs_dir, model, verbose,
                       is_video=False, target_dur=0, fallback_search=True, verify_desc=None):
    verdicts = {}
    survivors = []
    for entry in scored_top:
        cand_idx = entry[0]
        cand = candidates_list[cand_idx - 1]
        v, _ = _vlm_check_one(seg_n, query, cand, cand_idx, thumbs_dir, model, verbose, verify_desc=verify_desc)
        verdicts[str(cand_idx)] = v
        if v != "no":
            survivors.append(cand_idx)
    if survivors:
        return survivors, verdicts, None

    if not fallback_search:
        verdicts["_fallback"] = "all_rejected_use_top_text"
        return [scored_top[0][0]], verdicts, None

    for alt_query in _simplify_query(query):
        if verbose:
            print(f"  prepick seg{seg_n} fallback query: '{alt_query}'", file=sys.stderr)
        kind = "video" if is_video else "photo"
        pex_alt, pix_alt = [], []
        try:
            res = run_tool(["pexels-search", alt_query, "--type", kind, "--limit", "10"], False)
            pex_alt = json.loads(res).get("candidates", [])
            for c in pex_alt: c.setdefault("source", "pexels")
        except Exception:
            pass
        try:
            pix_alt = pixabay_search(alt_query, kind, limit=10)
        except Exception:
            pass
        new_cands = pex_alt + pix_alt
        if is_video:
            new_cands = [c for c in new_cands if (c.get("duration") or 0) >= target_dur + 1]
        for nc in new_cands[:4]:
            extra_idx = len(candidates_list) + 1
            candidates_list.append(nc)
            v, _ = _vlm_check_one(seg_n, query, nc, extra_idx, thumbs_dir, model, verbose,
                                  tag=f"alt{len([k for k in verdicts if k.startswith('_alt_')])+1}",
                                  verify_desc=verify_desc)
            verdicts[f"_alt_{alt_query}_c{extra_idx}"] = v
            if v == "yes":
                verdicts["_fallback"] = f"recovered_via:{alt_query}"
                return [extra_idx], verdicts, alt_query
    verdicts["_fallback"] = "all_rejected_use_top_text"
    return [scored_top[0][0]], verdicts, None


def pick_or_load(script, outdir, verbose, vlm_gate=True, vlm_model="qwen3-vl:4b-instruct",
                 actual_dur=None, xfade=0.0):
    # Longform Duration Policy: when TTS timing is known, select video stock
    # against the real render target (actual_dur[n]+xfade). Falls back to the
    # scripted duration_sec when actual_dur is absent (e.g. unit tests).
    def _target(s):
        if actual_dur is not None and s["segment"] in actual_dur:
            return _seg_target_len(s["segment"], script, actual_dur, xfade)
        return s["duration_sec"]
    picks_path = f"{outdir}/picks.json"
    cands_path = f"{outdir}/candidates.json"
    if os.path.exists(picks_path) and os.path.exists(cands_path):
        with open(picks_path, encoding="utf-8") as f: pj = json.load(f)
        with open(cands_path, encoding="utf-8") as f: cj = json.load(f)
        return cj, pj["picks"]
    candidates = {}
    for s in script:
        if s.get("kind") == "title" or s.get("source") == "local":
            continue  # 片頭/片尾、學員自有素材：不搜 stock
        n = str(s["segment"])
        is_video = s["media_pref"] == "video"
        kind = "video" if is_video else "photo"
        res = run_tool(["pexels-search", s["search_query"], "--type", kind, "--limit", "20"], verbose)
        pex = json.loads(res).get("candidates", [])
        for c in pex:
            c.setdefault("source", "pexels")
        pix = pixabay_search(s["search_query"], kind, limit=20)
        cands = pex + pix
        if is_video:
            valid = _filter_video_candidates(cands, _target(s))
            cands = valid if len(valid) >= 3 else cands[:8]
        candidates[n] = {
            "segment": s["segment"], "title": s["title"], "media_pref": s["media_pref"],
            "query": s["search_query"], "target_duration_sec": round(_target(s), 3),
            "cultural_specificity": s.get("cultural_specificity", "universal"),
            "verify_desc": s.get("visual_desc") or s.get("text", ""),
            "sources": {"pexels": len(pex), "pixabay": len(pix)},
            "candidates": cands[:8],
        }
        if verbose:
            print(f"  seg{n} candidates: pexels={len(pex)} pixabay={len(pix)} kept={len(cands[:8])}", file=sys.stderr)
    thumbs_dir = f"{outdir}/prepick_thumbs"
    picks = {}
    pick_log = {}
    for n, seg in candidates.items():
        is_video = seg["media_pref"] == "video"
        target = seg["target_duration_sec"]
        scored = [(i+1, *score_candidate(c, seg["query"], target, is_video))
                  for i, c in enumerate(seg["candidates"])]
        scored.sort(key=lambda x: x[1], reverse=True)
        vlm_verdicts = {}
        recovered_query = None
        if vlm_gate:
            top_n = scored[:5]
            survivors, vlm_verdicts, recovered_query = prepick_vlm_filter(
                int(n), seg["query"], top_n, seg["candidates"],
                thumbs_dir, vlm_model, verbose,
                is_video=is_video, target_dur=target, fallback_search=True,
                verify_desc=seg.get("verify_desc"))
            if recovered_query:
                seg["candidates"] = seg["candidates"]
                final_ranking = [(survivors[0], 999, f"recovered:{recovered_query}")]
            else:
                final_ranking = [s for s in scored if s[0] in survivors]
        else:
            survivors = [p for p, _, _ in scored]
            final_ranking = scored
        winner = final_ranking[0]
        picks[n] = winner[0]
        pick_log[n] = {
            "pick": winner[0],
            "text_score": winner[1],
            "text_reason": winner[2],
            "all_text_scores": [(p, sc, r) for p, sc, r in scored],
            "vlm_gate_enabled": vlm_gate,
            "vlm_verdicts": vlm_verdicts,
            "rejected_by_vlm": [p for p, _, _ in scored[:5] if p not in survivors],
            "recovered_query": recovered_query,
        }
    atomic_write_json(picks_path, {
        "_mode": "text-score + prepick-vlm-gate" if vlm_gate else "deterministic-text-score",
        "_vlm_model": vlm_model if vlm_gate else None,
        "picks": picks, "log": pick_log,
    })
    atomic_write_json(cands_path, candidates)
    return candidates, picks


# 統一段落規格：scale/pad 到 1920x1080 + bt709 色彩
SEG_VF = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,"
          "colorspace=all=bt709:iall=bt470bg:range=tv:irange=pc:fast=1,"
          "format=yuv420p")
SEG_VENC = ['-r', '30', '-vsync', 'cfr', '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
            '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-colorspace', 'bt709',
            '-color_primaries', 'bt709', '-color_trc', 'bt709', '-an']
_PHOTO_EXT = ("jpg", "jpeg", "png", "webp", "heic", "heif", "bmp")


def _kb_direction(n, s):
    """Ken Burns 方向：段落 effects.kenburns 覆寫 > 預設交替（奇 zoom-in / 偶 pan-right）。"""
    return (s.get("effects") or {}).get("kenburns") or ("zoom-in" if n % 2 == 1 else "pan-right")


def render_segment(n, s, chosen, target_len, mat_dir, verbose):
    out = f"{mat_dir}/seg{n}.mp4"
    if s["media_pref"] == "video":
        raw = f"{mat_dir}/seg{n}_raw.mp4"
        if not os.path.exists(raw):
            if os.path.exists(chosen["download_url"]):
                shutil.copy(chosen["download_url"], raw)
            else:
                run_tool(["pexels-download", chosen["download_url"], "--out", raw], verbose)
        raw_d = dur(raw)
        # Longform Duration Policy: a clip shorter than target loops instead of
        # crashing the pipeline (the picker already preferred longer candidates).
        plan = _video_fill_plan(raw_d, target_len)
        if plan["mode"] == "loop":
            if verbose:
                print(f"  seg{n} raw {raw_d:.2f}s < target {target_len:.2f}s "
                      f"→ loop x{plan['loops']+1} to fill", file=sys.stderr)
            cmd = [FFMPEG, '-y', '-stream_loop', str(plan["loops"]), '-i', raw,
                   '-t', f"{target_len:.3f}", '-vf', SEG_VF, *SEG_VENC, out]
        else:
            cmd = [FFMPEG, '-y', '-ss', f"{plan['start']:.3f}", '-i', raw, '-t', f"{target_len:.3f}",
                   '-vf', SEG_VF, *SEG_VENC, out]
    else:
        photo = f"{mat_dir}/seg{n}_photo.jpg"
        if not os.path.exists(photo):
            if os.path.exists(chosen["download_url"]):
                shutil.copy(chosen["download_url"], photo)
            else:
                run_tool(["pexels-download", chosen["download_url"], "--out", photo], verbose)
        kb_tmp = f"{mat_dir}/seg{n}_kb_tmp.mp4"
        run_tool(["kenburns", photo, "--duration", f"{target_len:.3f}",
                  "--direction", _kb_direction(n, s), "--out", kb_tmp], verbose)
        cmd = [FFMPEG, '-y', '-i', kb_tmp, '-vf', SEG_VF, *SEG_VENC, out]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"seg{n} encode: {res.stderr[-400:]}")
    if s["media_pref"] != "video" and os.path.exists(f"{mat_dir}/seg{n}_kb_tmp.mp4"):
        os.remove(f"{mat_dir}/seg{n}_kb_tmp.mp4")
    return out


def render_local(n, s, script, actual_dur, xfade, mat, verbose):
    """三源素材之一：source=local → 用學員自有素材檔（圖或影片），不搜 stock。
    照片走 Ken Burns、影片中段裁切，統一規格。不評 content_qa（人已選定）。"""
    f = s.get("file") or s.get("local_file")
    if not f or not os.path.exists(f):
        # 學員素材還沒到位：可恢復 → 出 placeholder、state 走 await_material（別炸全片）
        raise RecoverableBuildError(n, f"source=local 素材未到位：{f}", "material")
    target_len = _seg_target_len(n, script, actual_dur, xfade)
    out = f"{mat}/seg{n}.mp4"
    ext = f.rsplit(".", 1)[-1].lower()
    if ext in _PHOTO_EXT:
        kb = f"{mat}/seg{n}_kb_tmp.mp4"
        run_tool(["kenburns", f, "--duration", f"{target_len:.3f}",
                  "--direction", _kb_direction(n, s), "--out", kb], verbose)
        cmd = [FFMPEG, '-y', '-i', kb, '-vf', SEG_VF, *SEG_VENC, out]
    else:
        raw_d = dur(f)
        start = max(0, (raw_d - target_len) / 2) if raw_d >= target_len else 0
        loop = [] if raw_d >= target_len else ['-stream_loop', '-1']  # 短片循環補滿
        cmd = [FFMPEG, '-y', *loop, '-ss', f"{start:.3f}", '-i', f, '-t', f"{target_len:.3f}",
               '-vf', SEG_VF, *SEG_VENC, out]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"seg{n} local encode: {res.stderr[-400:]}")
    if os.path.exists(f"{mat}/seg{n}_kb_tmp.mp4"):
        os.remove(f"{mat}/seg{n}_kb_tmp.mp4")
    return apply_effects(n, s, out, mat, verbose)


def render_placeholder(n, s, script, actual_dur, xfade, mat, reason, verbose):
    """被 build block 的段落仍需一段可組合的片（誠實出片 + state 標 block_reason）。
    重用 title-sequence 當中性卡片，時長對齊該段 TTS。"""
    target_len = _seg_target_len(n, script, actual_dur, xfade)
    out = f"{mat}/seg{n}.mp4"
    run_tool(["title-sequence", "--text", s.get("title", f"段落 {n}"),
              "--subtitle", "（素材待補）", "--duration", f"{target_len:.3f}",
              "--anim", "fade", "--out", out], verbose)
    return out


def render_framed(n, s, script, candidates, picks, actual_dur, xfade, mat, verbose):
    """layout=framed：單張照片置中裝相框於深色底（像參考片的相框卡片，非全屏）。用該段單一 pick。"""
    target_len = _seg_target_len(n, script, actual_dur, xfade)
    chosen = candidates[str(n)]["candidates"][picks[str(n)] - 1]
    photo = f"{mat}/seg{n}_photo.jpg"
    if not os.path.exists(photo):
        run_tool(["pexels-download", chosen["download_url"], "--out", photo], verbose)
    out = f"{mat}/seg{n}.mp4"
    run_tool(["collage", "--images", photo, "--duration", f"{target_len:.3f}", "--out", out], verbose)
    return apply_effects(n, s, out, mat, verbose)


# 風格 → 轉場質感（編劇宣告 style，特效師據此給預設轉場政策）。
#   narrative（劇情/敘事）：極短 xfade ≈ 硬切，只允許 fade/dissolve（華麗轉場會破壞沉浸）
#   mv（主題/MV/旅遊 reel）：正常 xfade，尊重每段轉場（slide/wipe/circle 等節奏感）
#   promo：介於兩者
STYLE_XFADE = {"narrative": 0.12, "mv": 0.40, "promo": 0.30}
STYLE_DEFAULT_TRANSITION = {"narrative": "fade", "mv": "fade", "promo": "fade"}
NARRATIVE_ALLOWED = {"fade", "dissolve"}


def resolve_transition(s, style):
    """每段切入轉場：段落 effects.transition 覆寫 > style 預設。
    'cut'(硬切) → fade（narrative 的 xfade 已極短，視覺等同硬切）。
    narrative 風格收斂掉 slide/wipe/circle 等華麗轉場。"""
    t = (s.get("effects") or {}).get("transition") or STYLE_DEFAULT_TRANSITION.get(style, "fade")
    if t == "cut":
        t = "fade"
    if style == "narrative" and t not in NARRATIVE_ALLOWED:
        t = "fade"
    return t


# xfade 安全轉場白名單（避開 fadeblack 等黑幕坑）。未知值退回 fade。
ALLOWED_TRANSITIONS = {
    "fade", "wipeleft", "wiperight", "wipeup", "wipedown",
    "slideleft", "slideright", "slideup", "slidedown",
    "circleopen", "circleclose", "dissolve", "smoothleft", "smoothright",
    "radial", "diagtl", "diagtr", "diagbl", "diagbr",
}


def build_filter_chain(actual_durs, xfade, transitions=None, durations=None):
    """每個邊界 i-1 = 第 i 段切入：可有各自的轉場型(transitions)與 xfade 時長(durations)。
    offset 只跟前段 TTS 累加有關、與 xfade 時長無關，所以逐段混風格(durations 不同)時
    總長不變——前提是每段渲染留的尾巴 >= 該邊界 xfade 時長（pipeline 用統一 max 尾巴）。"""
    parts = []
    prev = "[0:v]"
    for i in range(1, len(actual_durs)):
        offset = sum(actual_durs[k] for k in range(i))
        label = f"[v{i}]"
        tr = "fade"
        if transitions and i - 1 < len(transitions) and transitions[i - 1] in ALLOWED_TRANSITIONS:
            tr = transitions[i - 1]
        d = durations[i - 1] if (durations and i - 1 < len(durations)) else xfade
        parts.append(f"{prev}[{i}:v]xfade=transition={tr}:duration={d}:offset={offset:.3f}{label}")
        prev = label
    return ";".join(parts), prev.strip("[]")


def apply_effects(n, s, path, mat, verbose):
    """特效師：對已渲染段套用 grade（色彩分級）→ title_card（字卡）。
    保留規格與時長，回傳最終檔路徑。effects 欄位皆選填，無則原樣回傳。"""
    fx = s.get("effects") or {}
    cur = path
    grade = fx.get("grade")
    if grade:
        out = f"{mat}/seg{n}_grade.mp4"
        run_tool(["grade", cur, "--preset", str(grade), "--out", out], verbose)
        cur = out
    title = fx.get("title_card")
    if title:
        text = title.get("text") if isinstance(title, dict) else str(title)
        out = f"{mat}/seg{n}_title.mp4"
        cmd = ["title-card", cur, "--text", text, "--out", out]
        if isinstance(title, dict) and title.get("subtitle"):
            cmd += ["--subtitle", title["subtitle"]]
        run_tool(cmd, verbose)
        cur = out
    if cur != path:
        vprint(f"  seg{n} effects: {','.join(k for k in ('grade','title_card') if fx.get(k))}", verbose)
    return cur


def _rendered_path(n, s, mat):
    """Deterministic FINAL path a segment renders to (mirrors apply_effects'
    chaining: grade→title_card, title_card last). Lets --only-seg reuse a prior
    run's rendered files for non-target segments without re-encoding.
    title/local segs skip apply_effects → always seg{n}.mp4."""
    if s.get("kind") == "title" or s.get("source") == "local":
        return f"{mat}/seg{n}.mp4"
    fx = s.get("effects") or {}
    if fx.get("title_card"):
        return f"{mat}/seg{n}_title.mp4"
    if fx.get("grade"):
        return f"{mat}/seg{n}_grade.mp4"
    return f"{mat}/seg{n}.mp4"


def render_one(n, script, candidates, picks, actual_dur, xfade, mat, verbose, fresh=False):
    """Render a single segment from its current pick. fresh=True clears cached
    raw/photo/output so a re-picked (different) candidate is downloaded anew."""
    s = next(x for x in script if x["segment"] == n)
    target_len = _seg_target_len(n, script, actual_dur, xfade)
    chosen = candidates[str(n)]["candidates"][picks[str(n)] - 1]
    if fresh:
        for stale in (f"{mat}/seg{n}.mp4", f"{mat}/seg{n}_raw.mp4",
                      f"{mat}/seg{n}_photo.jpg", f"{mat}/seg{n}_kb_tmp.mp4",
                      f"{mat}/seg{n}_grade.mp4", f"{mat}/seg{n}_title.mp4"):
            if os.path.exists(stale):
                os.remove(stale)
    base = render_segment(n, s, chosen, target_len, mat, verbose)
    return apply_effects(n, s, base, mat, verbose)


def render_title(n, s, script, actual_dur, xfade, mat, verbose):
    """片頭/片尾段（kind=title）：生成動態標題片段，時長對齊該段 TTS（旁白可當配音）。
    不搜素材、不評 content_qa。"""
    target_len = _seg_target_len(n, script, actual_dur, xfade)
    ts = s.get("title_sequence") or {}
    out = f"{mat}/seg{n}.mp4"
    cmd = ["title-sequence",
           "--text", ts.get("text") or s.get("title", ""),
           "--duration", f"{target_len:.3f}", "--out", out]
    if ts.get("subtitle"): cmd += ["--subtitle", ts["subtitle"]]
    if ts.get("anim"):     cmd += ["--anim", ts["anim"]]
    if ts.get("bg"):       cmd += ["--bg", ts["bg"]]
    if ts.get("size"):     cmd += ["--size", str(ts["size"])]
    run_tool(cmd, verbose)
    return out


def render_collage(n, s, script, candidates, actual_dur, xfade, mat, verbose):
    """多圖拼貼段（layout=collage）：下載該段 top-N 照片候選、組成裝框拼貼。
    不評 content_qa（拼貼是設計版面，非單圖對題判斷）。"""
    target_len = _seg_target_len(n, script, actual_dur, xfade)
    cn = int((s.get("effects") or {}).get("collage_n") or s.get("collage_n") or 3)
    cands = candidates[str(n)]["candidates"]
    photo_cands = [c for c in cands if c.get("download_url")][:cn]
    if len(photo_cands) == 0:
        raise RecoverableBuildError(n, f"seg{n} collage 無可用候選照片", "material")
    if len(photo_cands) == 1:
        # 只有 1 張：collage 工具吃單圖會退成置中卡片（=framed），可恢復、不炸片
        vprint(f"  seg{n} collage 候選不足（1 張）→ 降級單圖卡片", verbose)
    imgs = []
    for i, c in enumerate(photo_cands):
        photo = f"{mat}/seg{n}_col{i}.jpg"
        if not os.path.exists(photo):
            run_tool(["pexels-download", c["download_url"], "--out", photo], verbose)
        imgs.append(photo)
    out = f"{mat}/seg{n}.mp4"
    run_tool(["collage", "--images", *imgs, "--duration", f"{target_len:.3f}", "--out", out], verbose)
    return apply_effects(n, s, out, mat, verbose)


def render_montage(n, s, script, candidates, actual_dur, xfade, mat, verbose):
    """快切蒙太奇段（layout=montage）：下載 top-N 照片，組成一段內快速輪播（MV 照片牆）。
    不評 content_qa（設計版面，非單圖對題判斷）。"""
    target_len = _seg_target_len(n, script, actual_dur, xfade)
    mn = int((s.get("effects") or {}).get("montage_n") or s.get("montage_n") or 6)
    cands = [c for c in candidates[str(n)]["candidates"] if c.get("download_url")][:mn]
    if len(cands) == 0:
        raise RecoverableBuildError(n, f"seg{n} montage 無可用候選照片", "material")
    imgs = []
    for i, c in enumerate(cands):
        photo = f"{mat}/seg{n}_mon{i}.jpg"
        if not os.path.exists(photo):
            run_tool(["pexels-download", c["download_url"], "--out", photo], verbose)
        imgs.append(photo)
    out = f"{mat}/seg{n}.mp4"
    if len(imgs) == 1:
        # montage 需要 >=2 張；只有 1 張時降級成單圖卡片（collage 吃單圖），可恢復不炸片
        vprint(f"  seg{n} montage 候選不足（1 張）→ 降級單圖卡片", verbose)
        run_tool(["collage", "--images", imgs[0], "--duration", f"{target_len:.3f}", "--out", out], verbose)
    else:
        run_tool(["montage", "--images", *imgs, "--duration", f"{target_len:.3f}", "--out", out], verbose)
    return apply_effects(n, s, out, mat, verbose)


def repick_segment(n, seg, exclude, thumbs_dir, model, verbose):
    """Re-pick material for a failing segment, excluding already-rejected picks.
    Re-runs the VLM pre-pick gate with the configured retry model over remaining
    candidates; uses _simplify_query fallback search when needed.
    Returns (new_pick_idx, verdicts, recovered_query) or (None, verdicts, None)
    when survivors are exhausted (e.g. stock library ceiling)."""
    cands = seg["candidates"]
    is_video = seg["media_pref"] == "video"
    target = seg["target_duration_sec"]
    scored = [(i + 1, *score_candidate(c, seg["query"], target, is_video))
              for i, c in enumerate(cands)]
    scored = [s for s in scored if s[0] not in exclude]
    scored.sort(key=lambda x: x[1], reverse=True)
    if not scored:
        return None, {"_repick": "candidates_exhausted"}, None
    top_n = scored[:5]
    survivors, verdicts, recovered = prepick_vlm_filter(
        n, seg["query"], top_n, cands, thumbs_dir, model, verbose,
        is_video=is_video, target_dur=target, fallback_search=True,
        verify_desc=seg.get("verify_desc"))
    if verdicts.get("_fallback") == "all_rejected_use_top_text":
        return None, verdicts, recovered
    survivors = [s for s in survivors if s not in exclude]
    if not survivors:
        return None, verdicts, recovered
    return survivors[0], verdicts, recovered


def try_comfy_generation(n, seg, outdir, verbose):
    """
    Attempt to generate an asset using ComfyUI as a fallback.
    Returns the new_pick index (1-based) if successful, otherwise None.
    """
    if os.environ.get("COMFYUI_ENABLED", "false").lower() != "true":
        if verbose:
            print(f"[Fallback] ComfyUI generation disabled (COMFYUI_ENABLED is not 'true'). Skipping ComfyUI fallback.", file=sys.stderr)
        return None
    try:
        import comfy_agent
        # Define output path
        gen_dir = os.path.join(outdir, "materials", "generated")
        os.makedirs(gen_dir, exist_ok=True)
        out_path = os.path.join(gen_dir, f"seg{n}_gen.png")
        
        visual_desc = seg.get("verify_desc") or seg.get("query")
        if not visual_desc:
            if verbose:
                print(f"[ComfyUI Fallback] Segment {n} lacks visual description or query.", file=sys.stderr)
            return None
            
        if verbose:
            print(f"[ComfyUI Fallback] Starting generation for segment {n}...", file=sys.stderr)
        
        # Call comfy_agent to generate the asset
        saved_path = comfy_agent.generate_for_segment(
            seg_n=str(n),
            visual_desc=visual_desc,
            out_path=out_path,
            verbose=verbose
        )
        if saved_path and os.path.exists(saved_path) and os.path.getsize(saved_path) > 0:
            # Create a candidate entry
            new_cand = {
                "source": "generated",
                "id": f"generated_{n}",
                "alt": visual_desc,
                "user": "comfyui_agent",
                "url": "local://generated",
                "width": 768,
                "height": 432,
                "download_url": os.path.abspath(saved_path),
            }
            # Append to candidates list
            seg["candidates"].append(new_cand)
            # Index is length of candidates (1-based)
            new_pick = len(seg["candidates"])
            if verbose:
                print(f"[ComfyUI Fallback] Segment {n} successfully generated and added as candidate {new_pick}.", file=sys.stderr)
            return new_pick
    except Exception as e:
        if verbose:
            print(f"[ComfyUI Fallback] Segment {n} generation failed: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            
    return None


def collect_fix_actions(qa, outdir):
    """Map verify/content_qa issues to retry actions via fix_target routing.
    Returns {"repick_segs": [...], "remix": bool}. Only content_alignment
    (per-seg, fix_target=curator) and audio_levels (remix) are auto-actionable;
    other dimensions are structural and break the loop."""
    repick = set()
    remix = False
    for iss in qa.get("issues", []):
        dim = iss.get("dimension")
        ft = iss.get("fix_target")
        if dim == "content_alignment" or ft == "curator":
            try:
                cq = json.load(open(f"{outdir}/content_qa.json", encoding="utf-8"))
                for p in cq.get("segments", []):
                    if p.get("score") is not None and p["score"] < 60:
                        repick.add(p["segment"])
            except Exception:
                pass
        elif dim == "audio_levels" or ft == "audio":
            remix = True
    return {"repick_segs": sorted(repick), "remix": remix}


def compose_and_qa(script, seg_paths, actual_dur, xfade, outdir, script_path,
                   timing, cqa_model, cqa_weight, verbose, no_strict=False,
                   transitions=None, durations=None):
    """Steps 5b–10 + content_qa: precompose gate → xfade concat → merge-final →
    thumbnails → verify → content_qa → reread qa_report. Idempotent per attempt.
    Returns (qa, cqa_summary, gate)."""
    vprint("  [5b] pre-compose gate", verbose)
    gate = precompose_gate(seg_paths, script, actual_dur, xfade)
    atomic_write_json(f"{outdir}/precompose_gate.json", gate)
    if not gate["ok"]:
        for iss in gate["issues"]:
            vprint(f"    GATE FAIL: {iss}", verbose)
        # 組合前規格/時長關卡未過：不炸 stacktrace，升級為可恢復 → state review（人工查 gate.json）。
        # loop-fill + SEG_VF/VENC 之後此關卡幾乎不會觸發；真觸發代表異常，交人工最安全。
        raise RecoverableBuildError(
            0, f"precompose gate failed ({len(gate['issues'])} issues); see {outdir}/precompose_gate.json",
            "human")
    vprint(f"    gate ok ({len(seg_paths)} segs validated)", verbose)

    vprint("  [6] xfade concat", verbose)
    seg_ids = [s["segment"] for s in script]
    actual_list = [actual_dur[n] for n in seg_ids]
    # 每段切入轉場型 + xfade 時長由 pipeline 依逐段 style 算好傳入（支援逐段混風格）
    fc, last_label = build_filter_chain(actual_list, xfade, transitions, durations)
    inputs = []
    for p in seg_paths:
        inputs += ['-i', p]
    visual = f"{outdir}/polished_visual.mp4"
    cmd = [FFMPEG, '-y'] + inputs + [
        '-filter_complex', fc, '-map', f"[{last_label}]",
        '-c:v', 'libx264', '-preset', 'medium', '-crf', '20',
        '-pix_fmt', 'yuv420p', '-color_range', 'tv', '-colorspace', 'bt709',
        '-color_primaries', 'bt709', '-color_trc', 'bt709',
        '-movflags', '+faststart', '-an', visual]
    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"xfade concat: {res.stderr[-600:]}")

    edit_log = {
        "output": visual, "total_duration_sec": dur(visual),
        "segments": [{"segment": n, "source": seg_paths[i], "cut_start_sec": 0,
                      "tts_target_sec": actual_dur[n], "actual_sec": actual_dur[n],
                      "duration_diff_ms": 0} for i, n in enumerate(seg_ids)]
    }
    with open(f"{outdir}/edit_log.json", "w", encoding="utf-8") as f:
        json.dump(edit_log, f, ensure_ascii=False, indent=2)

    vprint("  [8] merge-final", verbose)
    final = f"{outdir}/final.mp4"
    run_tool(["merge-final", "--visual", visual, "--audio", f"{outdir}/final_audio.wav",
              "--subs", f"{outdir}/subtitles.srt", "--out", final], verbose)

    # content_qa 評的是「素材對不對題」，應看基底原片（grade/字卡/字幕前），
    # 否則美學調色（如 dusk 變紅）會跟 visual_desc 的顏色描述打架、壓低分數。
    vprint("  [9] thumbnails (base segments, pre-effects)", verbose)
    mat_dir = f"{outdir}/materials"
    # Build a quick lookup: segment id → script entry (for layout check)
    script_by_seg = {s["segment"]: s for s in script}
    cursor = 0
    for sd in timing["segments"]:
        n = sd["segment"]
        seg_dur = sd["duration_sec"]
        out_frame_path = f"{outdir}/final_frame_{n}.jpg"
        base = f"{mat_dir}/seg{n}.mp4"
        if os.path.exists(base):
            src = base
            offset = 0.0
        else:
            src = final
            offset = cursor

        # For montage/collage segments, tile 3~5 representative keyframes
        seg_script = script_by_seg.get(n, {})
        layout = seg_script.get("layout")
        tiled = False
        if layout in ("montage", "collage") and seg_dur > 0:
            num_samples = 5 if seg_dur >= 8 else 3
            try:
                extract_tiled_frames(src, seg_dur, out_frame_path,
                                     num_samples=num_samples,
                                     start_offset=offset)
                if os.path.exists(out_frame_path):
                    tiled = True
                    vprint(f"    seg{n} [{layout}] tiled {num_samples} frames", verbose)
            except Exception as e:
                vprint(f"    seg{n} [{layout}] tiling failed ({e}), fallback to single frame", verbose)

        # Fallback: single midpoint frame (default for non-montage segments)
        if not tiled:
            mid = (offset + seg_dur / 2) if src == final else dur(base) / 2
            subprocess.run([FFMPEG, '-y', '-ss', f"{mid:.3f}", '-i', src,
                            '-frames:v', '1', '-update', '1', '-q:v', '2',
                            out_frame_path], capture_output=True)

        cursor += seg_dur

    vprint("  [10] verify (technical)", verbose)
    run_tool(["verify", "--script", script_path,
              "--timing", f"{outdir}/audio/tts_timing.json",
              "--edit-log", f"{outdir}/edit_log.json",
              "--srt", f"{outdir}/subtitles.srt",
              "--video", final,
              "--out", f"{outdir}/qa_report.json"], verbose)

    vprint("  [11] content_qa (content_alignment)", verbose)
    cqa = run_content_qa(outdir, cqa_model, cqa_weight, verbose, no_strict)

    with open(f"{outdir}/qa_report.json", encoding="utf-8") as f:
        qa = json.load(f)
    return qa, cqa, gate


# ---- state.json：統一執行狀態（編排升級第一步，觀測層）----
# 把散落的 qa_report/content_qa/decision_log/effects_log 收成「單一真相」。
# 此版只觀測（pipeline 末尾附帶寫出），不改控制流；之後 route skill 讀它派工。
STATE_SCHEMA_VERSION = 1
_STAGE_NAMES = ["tts", "srt", "mix_audio", "pick", "render",
                "precompose_gate", "concat", "merge_final", "verify", "content_qa"]


def _seg_kind(s):
    """非評分段的種類標記（與 content_qa 跳過邏輯一致）；scored 段回 None。"""
    if s.get("kind") == "title": return "title"
    if s.get("source") == "local": return "local"
    if s.get("layout") in ("collage", "montage"): return s["layout"]
    return None


def build_state(script, outdir, style, bgm, qa, unfixable, attempt, final,
                build_blocks=None, gate_review=None):
    """從記憶體狀態 + 已落地 artifact 合成 `state.json`（執行進度的單一真相）。
    script=純 segments list；unfixable={seg:reason}；qa=qa_report dict。
    build_blocks={seg:{reason,fix_class}}=可恢復 BUILD 失敗（出 placeholder 的段）；
    gate_review=整片級 precompose gate 失敗原因（→ review）。
    每段帶 `fix_class` ∈ material|spec|human，讓 route 知道回哪一層（見 skills/route.md）。"""
    build_blocks = build_blocks or {}
    final_exists = os.path.exists(final)
    # 逐段對題分數從 content_qa.json 撈（已寫出）
    cq_scores = {}
    cq_path = f"{outdir}/content_qa.json"
    if os.path.exists(cq_path):
        try:
            with open(cq_path, encoding="utf-8") as f:
                cq_data = json.load(f)
            for p in (cq_data.get("segments") or []):
                cq_scores[p["segment"]] = p.get("score")
        except Exception:
            pass
    all_rejected_fallback = set()
    picks_path = f"{outdir}/picks.json"
    if os.path.exists(picks_path):
        try:
            with open(picks_path, encoding="utf-8") as f:
                pick_data = json.load(f)
            for seg_id, log in (pick_data.get("log") or {}).items():
                verdicts = log.get("vlm_verdicts") or {}
                if verdicts.get("_fallback") == "all_rejected_use_top_text":
                    all_rejected_fallback.add(int(seg_id))
        except Exception:
            pass
    segments = []
    for s in script:
        n = s["segment"]
        kind = _seg_kind(s)
        score = cq_scores.get(n)
        block_reason = None
        if n in build_blocks:
            status = "blocked"                       # 可恢復 BUILD 失敗：出 placeholder
            fix_class = build_blocks[n].get("fix_class", "material")
            block_reason = build_blocks[n].get("reason")
        elif n in unfixable:
            status = "unfixable"; fix_class = "material"   # stock 天花板 → 補拍/換源
            block_reason = unfixable[n]
        elif n in all_rejected_fallback:
            status = "needs_review"; fix_class = "material"  # 全候選被拒 → 換源（curator）
            block_reason = "all stock candidates rejected by VLM; top text-score fallback used"
        elif kind is not None or score is None or score >= 60:
            status = "done"; fix_class = None        # 設計版面/片頭/本地素材不評分；或已達標
        else:
            status = "low"; fix_class = "material"    # 對題分低 → 換素材
        seg = {"segment": n, "title": s.get("title", ""),
               "kind": kind or "scored", "source": s.get("source", "stock"),
               "layout": s.get("layout"), "status": status, "score": score,
               "fix_class": fix_class, "fix_target": _FIX_TARGET.get(fix_class)}
        if block_reason:
            seg["block_reason"] = block_reason
        segments.append(seg)
    # blocking = 需要外部素材的段（unfixable 補拍 + build_block material）
    block_material = {n: build_blocks[n]["reason"] for n in build_blocks
                      if build_blocks[n].get("fix_class") == "material"}
    blocking = [{"segment": n, "reason": r}
                for n, r in sorted({**unfixable, **block_material}.items())]
    qa_pass = bool(qa.get("pass"))
    low = [x["segment"] for x in segments if x["status"] == "low"]
    needs_review = [x["segment"] for x in segments if x["status"] == "needs_review"]
    spec_segs = [x["segment"] for x in segments if x["fix_class"] == "spec"]
    # 優先序：整片 gate review > 缺料 await_material > spec 改寫 > pass > 低分重試 > review。
    # blocking 優先於 pass：帶缺口出片仍回 await_material（給編排層改進路徑）。
    if gate_review:
        next_action = "review"                    # precompose gate 整片級失敗
    elif blocking:
        next_action = "await_material"            # 缺口已輸出補拍指引，等學員素材/換源
    elif spec_segs:
        next_action = f"revise:director(seg={spec_segs})"   # SPEC 選錯 → 回導演（route 未來消費）
    elif qa_pass:
        next_action = "review" if needs_review else None
    elif low:
        next_action = f"retry:curator(seg={low})"
    else:
        next_action = "review"
    state = {
        "schema_version": STATE_SCHEMA_VERSION,
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "outdir": outdir, "style": style, "bgm": bgm or None,
        "final": final if final_exists else None,
        "pass": qa_pass, "attempts_used": attempt,
        "qa": {"score": qa.get("score"),
               "content_alignment": ((qa.get("dimensions") or {}).get("content_alignment") or {}).get("score")},
        "stages": [{"name": st, "status": "done" if final_exists else "unknown"} for st in _STAGE_NAMES],
        "segments": segments,
        "blocking": blocking,
        "gate_review": gate_review,
        "next_action": next_action,
    }
    atomic_write_json(f"{outdir}/state.json", state)
    return state


def pipeline(script_path, outdir, bgm, xfade, verbose, vlm_gate=True, vlm_model="qwen3-vl:4b-instruct",
             retry=True, max_retries=2, vlm_model_retry="qwen3-vl:4b-instruct", cqa_weight=0.30,
             no_strict=False, style=None, only_seg=None):
    # --only-seg：只重渲指定段（吃改過的 effects/layout/montage_n），其餘段沿用上一輪
    # 已渲染檔案，省去重渲全部。假設 timeline（時長/style/轉場）不變；要改旁白文字或
    # 重搜素材請跑完整流程。需先有一次完整 run（picks/candidates 已快取）。
    only_seg = set(only_seg) if only_seg else None
    if only_seg is not None:
        retry = False  # 定向手動重渲，不跑自省重試迴圈
    os.makedirs(outdir, exist_ok=True)
    mat = f"{outdir}/materials"; os.makedirs(mat, exist_ok=True)
    # script 可為純 segments list（legacy）或 {style, segments} wrapper（編劇宣告風格）
    with open(script_path, encoding="utf-8") as f: raw = json.load(f)
    if isinstance(raw, dict):
        script = raw.get("segments", [])
        script_style = raw.get("style", "narrative")
        script_bgm = raw.get("bgm")
    else:
        script, script_style, script_bgm = raw, "narrative", None
    if not script: raise RuntimeError("empty script")
    style = (style or script_style or "narrative").lower()
    # BGM 解析：CLI --bgm 路徑優先；否則看 script 的 bgm 欄位。
    #   dict {"query","source"}  → music-fetch 抓真曲到 outdir/bgm_track.mp3（真實配樂）
    #   str（情境名/路徑）        → bgm/<mood>.mp3 placeholder 或既有檔案
    if not bgm and script_bgm:
        kind, payload = _bgm_plan(script_bgm)
        if kind == "fetch":
            q = payload.get("query") or payload.get("mood") or ""
            src = payload.get("source", "yt")
            track = f"{outdir}/bgm_track.mp3"
            extra = ["--max-dur", str(payload["max_dur"])] if payload.get("max_dur") else []
            try:
                run_tool(["music-fetch", q, "--source", src, "--out", track, *extra], verbose)
                bgm = track if os.path.exists(track) else ""
            except Exception as e:  # 配樂非關鍵路徑：抓不到就靜音收尾，不擋出片
                vprint(f"[0] bgm fetch 失敗，略過配樂：{e}", verbose)
                bgm = ""
            if bgm:
                vprint(f"[0] bgm fetch ({src}): {q} -> {bgm}", verbose)
        elif kind == "local":
            lib = os.path.join(_HERE, "bgm", f"{payload}.mp3")
            bgm = lib if os.path.exists(lib) else (payload if os.path.exists(payload) else "")
            if bgm:
                vprint(f"[0] bgm={payload} -> {bgm}", verbose)
    user_xfade = xfade  # CLI --xfade（None=依 style）
    # 逐段可覆寫 style（前段敘事→中段 mv→結尾敘事 的混風格剪輯）
    def _seg_style(s): return (s.get("style") or style).lower()
    def _seg_xfade(s):
        if user_xfade is not None:
            return user_xfade
        return (s.get("effects") or {}).get("transition_duration") or STYLE_XFADE.get(_seg_style(s), 0.40)
    boundary_durations = [_seg_xfade(s) for s in script[1:]]
    boundary_transitions = [resolve_transition(s, _seg_style(s)) for s in script[1:]]
    # 渲染統一留「最大邊界時長」的尾巴，concat 時各邊界用各自時長（offset 與時長無關）
    xfade = max(boundary_durations + [0.12]) if boundary_durations else (user_xfade or 0.40)
    # 寫純 segments list 給下游工具（tts/verify/content_qa 不需懂 wrapper）
    script_path = f"{outdir}/script.json"
    atomic_write_json(script_path, script)
    vprint(f"[0] style={style}  xfade={xfade}s", verbose)

    vprint("[1] TTS", verbose)
    run_tool(["tts", script_path, "--outdir", f"{outdir}/audio"], verbose)
    with open(f"{outdir}/audio/tts_timing.json", encoding="utf-8") as f: timing = json.load(f)
    actual_dur = {s["segment"]: s["duration_sec"] for s in timing["segments"]}

    vprint("[2] SRT", verbose)
    run_tool(["srt", f"{outdir}/audio/tts_timing.json", "--out", f"{outdir}/subtitles.srt"], verbose)

    vprint("[3] mix-audio", verbose)
    if bgm and os.path.exists(bgm):
        run_tool(["mix-audio", "--voice", f"{outdir}/audio/voice.mp3",
                  "--bgm", bgm, "--duck",
                  "--out", f"{outdir}/final_audio.wav"], verbose)
    else:
        shutil.copy(f"{outdir}/audio/voice.mp3", f"{outdir}/final_audio.wav")

    # ---- material pick + render + QA, with self-reflection retry loop (P2-3) ----
    thumbs_dir = f"{outdir}/prepick_thumbs"
    seg_ids = [s["segment"] for s in script]

    if only_seg is not None and not (os.path.exists(f"{outdir}/picks.json")
                                     and os.path.exists(f"{outdir}/candidates.json")):
        raise RuntimeError("--only-seg 需要先有一次完整 run（picks.json/candidates.json 快取）")

    vprint(f"[4] gather + pick (vlm_gate={vlm_gate}, model={vlm_model if vlm_gate else '-'})", verbose)
    candidates, picks = pick_or_load(script, outdir, verbose, vlm_gate=vlm_gate, vlm_model=vlm_model,
                                     actual_dur=actual_dur, xfade=xfade)

    vprint("[5] render segments" + (f" (--only-seg {sorted(only_seg)})" if only_seg else ""), verbose)
    path_by_seg = {}
    build_blocks = {}   # {seg: {reason, fix_class}} — 可恢復的 BUILD 失敗（出 placeholder，不炸片）

    def _render_seg(n, s):
        if s.get("kind") == "title":
            return render_title(n, s, script, actual_dur, xfade, mat, verbose)
        if s.get("source") == "local":
            return render_local(n, s, script, actual_dur, xfade, mat, verbose)
        if s.get("layout") == "collage":
            return render_collage(n, s, script, candidates, actual_dur, xfade, mat, verbose)
        if s.get("layout") == "montage":
            return render_montage(n, s, script, candidates, actual_dur, xfade, mat, verbose)
        if s.get("layout") == "framed":
            return render_framed(n, s, script, candidates, picks, actual_dur, xfade, mat, verbose)
        return render_one(n, script, candidates, picks, actual_dur, xfade, mat, verbose)

    for s in script:
        n = s["segment"]
        if only_seg is not None and n not in only_seg:
            rp = _rendered_path(n, s, mat)
            if os.path.exists(rp):
                path_by_seg[n] = rp
                vprint(f"  seg{n} ↺ 沿用 {os.path.basename(rp)}", verbose)
                continue
            vprint(f"  seg{n} ↺ 沿用檔不存在，照常渲染", verbose)
        try:
            path_by_seg[n] = _render_seg(n, s)
        except RecoverableBuildError as e:
            build_blocks[n] = {"reason": e.reason, "fix_class": e.fix_class}
            vprint(f"  seg{n} BUILD block ({e.fix_class}): {e.reason} → placeholder", verbose)
            path_by_seg[n] = render_placeholder(n, s, script, actual_dur, xfade, mat, e.reason, verbose)
        vprint(f"  seg{n} → {dur(path_by_seg[n]):.2f}s", verbose)
    seg_paths = [path_by_seg[n] for n in seg_ids]

    exclude = {n: set() for n in seg_ids}
    unfixable = {}
    attempts = []
    cur_bgm_vol = 0.12

    def _picklog(n):
        try:
            pj = json.load(open(f"{outdir}/picks.json", encoding="utf-8"))
            return pj.get("log", {}).get(str(n), {})
        except Exception:
            return {}

    def _snapshot(attempt, qa, gate, fix_actions):
        try:
            cqj = json.load(open(f"{outdir}/content_qa.json", encoding="utf-8"))
        except Exception:
            cqj = {}
        attempts.append({
            "attempt": attempt,
            "picks": {str(n): {"pick": picks[str(n)],
                               **{k: _picklog(n).get(k) for k in
                                  ("text_score", "text_reason", "vlm_verdicts", "recovered_query")}}
                      for n in seg_ids if str(n) in picks},
            "precompose_gate": gate,
            "qa": {"score": qa.get("score"), "pass": qa.get("pass"),
                   "dimensions": {k: {"score": v.get("score"), "weight": v.get("weight"),
                                      "note": v.get("note"), "fix_target": v.get("fix_target")}
                                  for k, v in qa.get("dimensions", {}).items()}},
            "content_alignment": {
                "avg": cqj.get("summary", {}).get("avg_score"),
                "min": cqj.get("summary", {}).get("min_score"),
                "per_seg": [{"segment": p.get("segment"), "score": p.get("score"),
                             "image_desc": p.get("image_desc")} for p in cqj.get("segments", [])]},
            "fix_actions": fix_actions,
        })

    gate_review = None   # precompose gate 整片級失敗 → 走 review（不炸 stacktrace）
    attempt = 0
    try:
        qa, cqa, gate = compose_and_qa(script, seg_paths, actual_dur, xfade, outdir,
                                       script_path, timing, vlm_model, cqa_weight, verbose, no_strict,
                                       boundary_transitions, boundary_durations)
    except RecoverableBuildError as e:
        gate_review = e.reason
        vprint(f"[gate] {e.reason} → state review（不中斷）", verbose)
        qa, cqa, gate = {"pass": False, "score": 0, "issues": []}, {}, {"ok": False}
    _snapshot(attempt, qa, gate, None)

    while retry and not gate_review and not qa.get("pass") and attempt < max_retries:
        actions = collect_fix_actions(qa, outdir)
        actions["repick_segs"] = [n for n in actions["repick_segs"] if n not in unfixable]
        if not actions["repick_segs"] and not actions["remix"]:
            vprint(f"[retry] no actionable fix_target; stopping at attempt {attempt}", verbose)
            break
        attempt += 1
        vprint(f"[retry attempt {attempt}] repick={actions['repick_segs']} remix={actions['remix']}", verbose)
        for n in actions["repick_segs"]:
            seg = candidates[str(n)]
            is_video = (seg.get("media_pref") == "video")
            # D2: 中文/在地/抽象語意段落，西方 video stock 命中率極低；
            # 直接跳過 video 重挑，走 photo fallback（Ken Burns）省一輪。
            cult = (seg.get("cultural_specificity") or "universal").lower()
            skip_video = cult in ("local", "abstract")

            new_pick = None
            if is_video and skip_video:
                vprint(f"  [retry] seg{n} cultural_specificity={cult}；跳過西方 video stock，直接走 PHOTO fallback。", verbose)
            elif is_video:
                exclude[n].add(picks[str(n)])
                new_pick, _verdicts, _rec = repick_segment(
                    n, seg, exclude[n], thumbs_dir, vlm_model_retry, verbose)

            if new_pick is None:
                if is_video:
                    vprint(f"  [retry] seg{n} video candidates exhausted or rejected. Falling back to PHOTO mode.", verbose)
                    seg["media_pref"] = "photo"
                    s_item = next(x for x in script if x["segment"] == n)
                    s_item["media_pref"] = "photo"
                    
                    photo_cands = fetch_photo_candidates(seg["query"], verbose)
                    seg["candidates"] = photo_cands[:8]
                    exclude[n] = set()
                    
                    new_pick, _verdicts, _rec = repick_segment(
                        n, seg, exclude[n], thumbs_dir, vlm_model_retry, verbose)
                    
                    if new_pick is None:
                        vprint(f"  [retry] seg{n} stock photo candidates also exhausted. Trying ComfyUI generation fallback...", verbose)
                        new_pick = try_comfy_generation(n, seg, outdir, verbose)
                        if new_pick is None:
                            title = seg.get("title", "")
                            query = seg.get("query", "")
                            dur_sec = int(seg.get("target_duration_sec", 5))
                            guidance = f"{title}: 已暫用後備畫面。建議補拍：{query}特寫/空鏡，中景，時長 {dur_sec} 秒，命名為 seg{n}_user.mp4"
                            unfixable[n] = guidance
                            vprint(f"  seg{n} unfixable — video & photo fallback both failed, and ComfyUI generation failed", verbose)
                            continue
                else:
                    vprint(f"  [retry] seg{n} stock photo candidates exhausted. Trying ComfyUI generation fallback...", verbose)
                    new_pick = try_comfy_generation(n, seg, outdir, verbose)
                    if new_pick is None:
                        title = seg.get("title", "")
                        query = seg.get("query", "")
                        dur_sec = int(seg.get("target_duration_sec", 5))
                        guidance = f"{title}: 已暫用後備畫面。建議補拍：{query}特寫/空鏡，中景，時長 {dur_sec} 秒，命名為 seg{n}_user.mp4"
                        unfixable[n] = guidance
                        vprint(f"  seg{n} unfixable — photo candidates exhausted, and ComfyUI generation failed", verbose)
                        continue
            
            picks[str(n)] = new_pick
            path_by_seg[n] = render_one(n, script, candidates, picks, actual_dur, xfade, mat, verbose, fresh=True)
            vprint(f"  seg{n} repicked ({seg['media_pref']}) → cand {new_pick} ({dur(path_by_seg[n]):.2f}s)", verbose)
            
        if actions["remix"]:
            cur_bgm_vol = round(max(0.04, cur_bgm_vol - 0.04), 2)
            if bgm and os.path.exists(bgm):
                vprint(f"  remix bgm-vol={cur_bgm_vol}", verbose)
                run_tool(["mix-audio", "--voice", f"{outdir}/audio/voice.mp3",
                          "--bgm", bgm, "--bgm-vol", str(cur_bgm_vol),
                          "--out", f"{outdir}/final_audio.wav"], verbose)
        seg_paths = [path_by_seg[n] for n in seg_ids]
        try:
            qa, cqa, gate = compose_and_qa(script, seg_paths, actual_dur, xfade, outdir,
                                           script_path, timing, vlm_model, cqa_weight, verbose, no_strict,
                                           boundary_transitions, boundary_durations)
        except RecoverableBuildError as e:
            gate_review = e.reason
            vprint(f"[gate] {e.reason} → state review（不中斷）", verbose)
            break
        _snapshot(attempt, qa, gate, actions)

    # Write Material Gap & Shooting Guidance to qa_report.json and console
    if unfixable:
        print("\n" + "="*60, file=sys.stderr)
        print("⚠️  【素材缺口與拍攝指引】 ⚠️", file=sys.stderr)
        print("="*60, file=sys.stderr)
        for n, r in sorted(unfixable.items()):
            print(f"  - {r}", file=sys.stderr)
        print("="*60 + "\n", file=sys.stderr)
        
        qa_path = f"{outdir}/qa_report.json"
        if os.path.exists(qa_path):
            try:
                with open(qa_path, encoding="utf-8") as f:
                    qa_report = json.load(f)
                qa_report["material_gap_guidance"] = [
                    {"segment": n, "guidance": r} for n, r in sorted(unfixable.items())
                ]
                atomic_write_json(qa_path, qa_report)
            except Exception as e:
                vprint(f"Failed to write guidance to qa_report.json: {e}", verbose)

    # Check if all remaining issues are content_alignment on unfixable segments
    if not qa.get("pass") and unfixable:
        remaining_issues = []
        for iss in qa.get("issues", []):
            if iss.get("dimension") == "content_alignment":
                cq_path = f"{outdir}/content_qa.json"
                if os.path.exists(cq_path):
                    try:
                        cq = json.load(open(cq_path, encoding="utf-8"))
                        failed_segs = [p["segment"] for p in cq.get("segments", []) if p.get("score") is not None and p["score"] < 60]
                        if all(fs in unfixable for fs in failed_segs):
                            continue
                    except Exception:
                        pass
            remaining_issues.append(iss)
        
        if not remaining_issues:
            vprint("[warning] Pipeline passed with material gap warnings.", verbose)
            qa["pass"] = True

    final = f"{outdir}/final.mp4"
    decision_log = {
        "script": script_path, "vlm_model": vlm_model, "vlm_model_retry": vlm_model_retry,
        "retry_enabled": retry, "max_retries": max_retries, "attempts_used": attempt,
        "final_pass": bool(qa.get("pass")),
        "unfixable_segments": [{"segment": n, "reason": r} for n, r in sorted(unfixable.items())],
        "attempts": attempts,
    }
    atomic_write_json(f"{outdir}/decision_log.json", decision_log)

    # 特效師軌跡：逐段 grade/title_card + 段間 transition（記錄「實際渲染」的解析後轉場+時長）
    effects_log = {
        "style": style,
        "segments": [{"segment": s["segment"],
                      "style": _seg_style(s),
                      "grade": (s.get("effects") or {}).get("grade"),
                      "title_card": (s.get("effects") or {}).get("title_card"),
                      "transition_in": (boundary_transitions[i - 1] if i >= 1 else None),
                      "xfade_sec": (boundary_durations[i - 1] if i >= 1 else None)}
                     for i, s in enumerate(script)],
    }
    atomic_write_json(f"{outdir}/effects_log.json", effects_log)

    # state.json：統一執行狀態（編排升級觀測層；不影響控制流）
    try:
        build_state(script, outdir, style, bgm, qa, unfixable, attempt, final,
                    build_blocks=build_blocks, gate_review=gate_review)
    except Exception as e:
        vprint(f"[state] build_state failed (non-fatal): {e}", verbose)

    return {
        "status": "ok" if qa.get("pass") else "qa_fail",
        "final": final, "duration_sec": round(dur(final), 2),
        "tts_total_sec": round(sum(actual_dur.values()), 2),
        "segments": len(script),
        "qa_score": qa.get("score"), "qa_pass": qa.get("pass"),
        "qa_issues": len(qa.get("issues", [])),
        "attempts_used": attempt,
        "unfixable_segments": sorted(unfixable.keys()),
        "qa_report": f"{outdir}/qa_report.json",
        "decision_log": f"{outdir}/decision_log.json",
        "state": f"{outdir}/state.json",
    }


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("--out", required=True)
    ap.add_argument("--bgm", default="")
    ap.add_argument("--xfade", type=float, default=None,
                    help="轉場 xfade 秒數；預設依 style（narrative 0.12 / mv 0.40 / promo 0.30）")
    ap.add_argument("--style", default=None,
                    help="narrative（敘事，硬切感）/ mv（主題，平滑節奏轉場）/ promo；覆寫 script 內 style")
    ap.add_argument("--no-vlm-gate", action="store_true")
    ap.add_argument("--vlm-model", default="qwen3-vl:4b-instruct")
    ap.add_argument("--no-retry", action="store_true", help="disable P2-3 self-reflection retry loop")
    ap.add_argument("--max-retries", type=int, default=2)
    ap.add_argument("--vlm-model-retry", default="qwen3-vl:4b-instruct",
                    help="VLM model for retry re-pick gate (default: qwen3-vl:4b-instruct)")
    ap.add_argument("--content-qa-weight", type=float, default=0.30)
    ap.add_argument("--no-strict", action="store_true", help="disable strict segment-level gate in content QA")
    ap.add_argument("--only-seg", default=None,
                    help="只重渲指定段（逗號分隔，如 5 或 4,5,8），其餘段沿用上一輪渲染檔；"
                         "吃改過的 effects/layout，省去重渲全部。需先有一次完整 run。")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()
    only_seg = None
    if args.only_seg:
        only_seg = [int(x) for x in str(args.only_seg).replace(" ", "").split(",") if x]
    try:
        summary = pipeline(args.script, args.out, args.bgm, args.xfade, args.verbose,
                           vlm_gate=not args.no_vlm_gate, vlm_model=args.vlm_model,
                           retry=not args.no_retry, max_retries=args.max_retries,
                           vlm_model_retry=args.vlm_model_retry, cqa_weight=args.content_qa_weight,
                           no_strict=args.no_strict, style=args.style, only_seg=only_seg)
        print(json.dumps(summary, ensure_ascii=False))
        sys.exit(0 if summary["qa_pass"] else 1)
    except Exception as e:
        err = {"status": "error", "error": str(e), "traceback": traceback.format_exc()[-800:]}
        print(json.dumps(err, ensure_ascii=False))
        sys.exit(2)
