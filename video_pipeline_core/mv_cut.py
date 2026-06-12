"""MV-cut — beat-driven timeline for the Unified Segment Model (timeline:beat).

Increment ① of the MV-cut build plan (see roadmap "MV-cut 建置計畫"):
turn music beats into a cut grid (per-segment spans/durations) so a no-narration
MV can have its timeline driven by the music instead of by TTS.

Design split (機械 vs 判斷):
- `beats_to_cut_grid` / `grid_durations` are PURE functions (no deps) — the
  judgment about *how* to lay cuts on beats. Unit-tested without any audio/lib.
- `detect_beats` is a thin wrapper over librosa (the commodity beat detector).
  librosa is imported lazily so this module loads even when librosa is absent.
"""
from __future__ import annotations

import os
import subprocess
import sys

from .vt_core import GAP, FIX_TARGET, ToolError  # 統一錯誤/缺口分類(對齊)
from .platform_tools import resolve_ffmpeg, resolve_font, resolve_temp_dir

try:
    FFMPEG = resolve_ffmpeg()
except Exception:
    FFMPEG = "ffmpeg"


def _merge_short_spans(spans, min_len):
    """Merge any (start, end) span shorter than min_len into its neighbour
    (previous; or next if it is the first). Shared by cut-grid and shot logic."""
    merged = []
    for s, e in spans:
        if merged and (e - s) < min_len:
            merged[-1] = (merged[-1][0], e)
        else:
            merged.append((s, e))
    if len(merged) >= 2 and (merged[0][1] - merged[0][0]) < min_len:
        merged[1] = (merged[0][0], merged[1][1])
        merged.pop(0)
    return merged


def beats_to_cut_grid(beat_times, every_n_beats=4, min_seg=1.0, total=None):
    """Turn beat timestamps into MV cut segments (the timeline:beat driver).

    beat_times   : iterable of beat timestamps in seconds (from detect_beats).
    every_n_beats: cut every N beats (4 ≈ one cut per bar in 4/4).
    min_seg      : merge any segment shorter than this into the previous one
                   (avoids 1-frame flicker cuts).
    total        : optional total duration (e.g. song length); the final segment
                   extends to `total` when given, else to the last beat.

    Returns a list of (start, end) tuples in seconds — the cut grid. Each span
    becomes one clip slot; downstream this is the MV-mode analogue of TTS
    `actual_dur`.
    """
    bts = sorted(float(b) for b in beat_times)
    step = max(1, int(every_n_beats))
    if len(bts) < 2:
        start = bts[0] if bts else 0.0
        end = total if total is not None else (bts[-1] if bts else 0.0)
        return [(start, end)] if end > start else []

    bounds = bts[::step]
    end = total if total is not None else bts[-1]
    if bounds[-1] < end:
        bounds = bounds + [end]
    else:
        bounds[-1] = end

    segs = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)
            if bounds[i + 1] > bounds[i]]
    return _merge_short_spans(segs, min_seg)


def grid_durations(grid):
    """Per-segment durations from a cut grid — the bridge to existing actual_dur."""
    return [round(e - s, 3) for s, e in grid]


# ── increment ③: 候選窗評分選段（判斷層；必放守門是你的護城河）──────────────────

def select_windows(candidates, n_slots, must_include=(), min_score=0.0):
    """Pick `n_slots` windows for an MV, **must-include-aware**（必放守門）.

    candidates: list of dicts, each at least {'score': float, 'group': str};
        `group` = source/person/tag used for must-include + diversity
        (e.g. "所長", "拖拉電纜"). Extra keys (win, source...) pass through.
    must_include: groups that MUST appear at least once (所長/必放)。
        **必放 overrides the score floor** — a mandatory-but-boring clip still
        gets in even if its score < min_score (this is the whole point: no
        auto-MV omits the boss).
    Returns (selected, unfilled_must):
      - reserves the best-scoring candidate per must_include group first;
      - fills remaining slots with top-scored candidates whose score>=min_score;
      - unfilled_must = must_include groups with NO candidate at all → hand to
        VERIFY as a gap (await_material / 補拍指引).
    """
    def _by_score(seq):
        return sorted(seq, key=lambda c: c.get("score", 0), reverse=True)

    def _matches(c, g):
        # 必放比對吃「資料夾階層任一層」：group(葉)、tags、或路徑任一段。
        # 解「必放項目/所長看填志願」這種:必放是父層而 group 只取葉層的問題。
        if c.get("group") == g or g in (c.get("tags") or []):
            return True
        return g in (c.get("source") or "")

    selected, used, unfilled = [], set(), []
    # 1) 必放：每個 group 取最高分的一支（不受 min_score 限制）
    for g in must_include:
        cand = next((c for c in _by_score(candidates)
                     if _matches(c, g) and id(c) not in used), None)
        if cand is None:
            unfilled.append(g)
        elif len(selected) < n_slots:
            selected.append(cand)
            used.add(id(cand))
    # 2) 其餘名額：用達標(min_score)的高分候選補滿
    for c in _by_score(candidates):
        if len(selected) >= n_slots:
            break
        if id(c) in used or c.get("score", 0) < min_score:
            continue
        selected.append(c)
        used.add(id(c))
    return selected, unfilled


def _extract_frame(video_path, t, out_path):
    """(I/O) Grab a single frame at time t (seconds) → jpg. Returns bool ok."""
    r = subprocess.run([FFMPEG, "-y", "-ss", f"{t:.3f}", "-i", video_path,
                        "-frames:v", "1", "-q:v", "3", "-vf", "scale=512:-1",
                        out_path], capture_output=True, timeout=60)
    return r.returncode == 0 and os.path.exists(out_path)


# ── 靜止窗預篩(ffmpeg freezedetect,無 VLM 的便宜過濾器)─────────────────────
# 真實學員素材是連續長鏡頭,常有大段三腳架靜止畫面。VLM 評分貴(模型/網路),
# 先用 freezedetect 把「整窗幾乎不動」的窗丟掉,省 VLM call。

def _parse_freeze_ratio(stderr, win_dur):
    """純函式:從 ffmpeg freezedetect stderr 算「凍結秒數佔窗比例」(0~1)。
    解析 freeze_start/freeze_end 配對;只有 start 沒 end → 凍到窗尾。"""
    if not stderr or win_dur <= 0:
        return 0.0
    starts, ends = [], []
    for line in stderr.splitlines():
        if "freeze_start" in line:
            try:
                starts.append(float(line.rsplit(":", 1)[1].strip()))
            except (ValueError, IndexError):
                pass
        elif "freeze_end" in line:
            try:
                ends.append(float(line.rsplit(":", 1)[1].strip()))
            except (ValueError, IndexError):
                pass
    frozen = 0.0
    for i, st in enumerate(starts):
        en = ends[i] if i < len(ends) else win_dur   # 沒 end → 凍到尾
        frozen += max(0.0, min(en, win_dur) - max(st, 0.0))
    return max(0.0, min(1.0, frozen / win_dur))


def window_static_ratio(clip, start, dur, noise=0.003, mindur=0.5):
    """(I/O) 跑 freezedetect 於 [start,start+dur] → 回凍結比例(0~1)。失敗回 0(視為動態,不誤殺)。"""
    r = subprocess.run([FFMPEG, "-ss", f"{start:.3f}", "-t", f"{dur:.3f}", "-i", clip,
                        "-vf", f"freezedetect=n={noise}:d={mindur}", "-map", "0:v:0",
                        "-f", "null", "-"], capture_output=True, text=True, timeout=120)
    return _parse_freeze_ratio(r.stderr or "", dur)


def filter_static_windows(windows, clip, max_static=0.85, _ratio=None):
    """純邏輯(ratio 可注入測試):丟掉「凍結比例 >= max_static」的窗。
    全被丟 → 回原 windows(寧可送 VLM 也不要 0 候選)。"""
    ratio = _ratio or (lambda s, e: window_static_ratio(clip, s, e - s))
    kept = [(s, e) for (s, e) in windows if ratio(s, e) < max_static]
    return kept or list(windows)


def _default_scorer(model):
    """Wrap content_qa.score_segment (lazy import) → fn(frame, desc)->(score,desc,reason)."""
    from . import content_qa  # noqa: PLC0415 — lazy
    def _score(frame, verify_desc):
        return content_qa.score_segment(model, frame, verify_desc, "")
    return _score


def score_windows(video_path, windows, verify_desc, group=None,
                  model="qwen3-vl:4b-instruct", mat_dir=None,
                  _extract=None, _score=None):
    """increment ③ I/O: score each candidate window by grabbing its midpoint
    frame and asking the VLM (content_qa) how well it matches `verify_desc`.
    Returns candidates ready for select_windows: [{win, source, group, score,
    image_desc, reason}]. `_extract`/`_score` are injectable for unit tests so
    the loop is testable without ffmpeg/ollama."""
    extract = _extract or _extract_frame
    score = _score or _default_scorer(model)
    group = group or (os.path.basename(os.path.dirname(video_path)) if video_path else None)
    name = os.path.basename(video_path) if video_path else None  # ④ 渲染要 full path,顯示用 name
    mat_dir = mat_dir or resolve_temp_dir()
    cands = []
    for i, (s, e) in enumerate(windows):
        t = (s + e) / 2.0
        frame = os.path.join(mat_dir, f"mvwin_{name}_{i}.jpg")
        if not extract(video_path, t, frame):
            cands.append({"win": (s, e), "source": video_path, "source_name": name,
                          "group": group, "score": 0.0, "image_desc": None,
                          "reason": "frame_fail"})
            continue
        sc, desc, reason = score(frame, verify_desc)
        cands.append({"win": (s, e), "source": video_path, "source_name": name,
                      "group": group, "score": float(sc), "image_desc": desc,
                      "reason": reason})
    return cands


# ── increment ②: shot 拆解（長片 → shot 清單）─────────────────────────────────

def filter_shots(shots, min_shot=1.0):
    """Clean a shot list (contiguous (start, end) spans from detect_shots):
    fold shots shorter than min_shot into a neighbour so we don't pick tiny
    flicker shots. Pure — testable with synthetic shot lists."""
    spans = sorted((float(s), float(e)) for s, e in shots)
    return _merge_short_spans(spans, min_shot)


def fixed_windows(total, win=4.0, hop=None, min_seg=1.0):
    """Window a continuous take into candidate spans (the RIGHT primitive for raw
    student footage — see probe: ContentDetector gives no stable shots on
    single-take footage). `win`=window length, `hop`=stride (default=win, i.e.
    non-overlapping). Short tail merged. Pure — testable without video.

    For raw footage the flow is: detect_shots → (continuous) whole clip →
    fixed_windows → VLM-score each window (increment ③) → pick good moments."""
    total = float(total)
    win = float(win)
    hop = float(hop) if hop else win
    if total <= 0 or win <= 0:
        return []
    wins = []
    s = 0.0
    while s < total:
        e = min(s + win, total)
        wins.append((round(s, 3), round(e, 3)))
        if e >= total:
            break
        s += hop
    return _merge_short_spans(wins, min_seg)


def shot_midpoints(shots):
    """Representative timestamp per shot (the frame to grab for VLM scoring in
    increment ③). Midpoint avoids transition frames at the cut boundaries."""
    return [round((s + e) / 2.0, 3) for s, e in shots]


def detect_shots(video_path, threshold=27.0, min_shot=0.0):
    """(I/O) Split a long video into shots via PySceneDetect content detector.
    Returns list of (start, end) seconds. Empty list = no internal cuts found
    (one continuous take). scenedetect imported lazily."""
    from scenedetect import detect, ContentDetector, open_video  # noqa: PLC0415 — lazy
    scenes = detect(video_path, ContentDetector(threshold=threshold))
    shots = [(s.get_seconds(), e.get_seconds()) for s, e in scenes]
    if not shots:
        # 連續長鏡頭(raw 學員素材常見):沒有剪接點 → 整支當一個 shot,
        # 交給上層用 cut_grid(beat/fixed)去開窗,而不是靠剪接偵測。
        dur = open_video(video_path).duration.get_seconds()
        shots = [(0.0, float(dur))]
    return filter_shots(shots, min_shot) if min_shot > 0 else shots


def _shot_stats(shots, total=None):
    """純函式:從 shots [(s,e)...] 算剪輯節奏指標(對照 66 期 gold standard 用)。
    回 {n_shots, median, mean, cuts_per_min, total_dur, dist}。"""
    durs = sorted(max(0.0, e - s) for s, e in shots)
    n = len(durs)
    if n == 0:
        return {"n_shots": 0, "median": 0, "mean": 0, "cuts_per_min": 0,
                "total_dur": total or 0, "dist": {}}
    tot = total if total else sum(durs)
    mid = durs[n // 2] if n % 2 else (durs[n // 2 - 1] + durs[n // 2]) / 2
    dist = {"<1s": sum(1 for d in durs if d < 1),
            "1-3s": sum(1 for d in durs if 1 <= d < 3),
            "3-6s": sum(1 for d in durs if 3 <= d < 6),
            ">6s": sum(1 for d in durs if d >= 6)}
    return {"n_shots": n, "median": round(mid, 2), "mean": round(sum(durs) / n, 2),
            "cuts_per_min": round(n / (tot / 60.0), 1) if tot else 0,
            "total_dur": round(tot, 1), "dist": dist}


# 66 期人工剪輯片 gold standard(roadmap 對照組)實測指標
GOLD_66 = {"n_shots": 368, "median": 1.47, "mean": 2.19, "cuts_per_min": 27.5,
           "total_dur": 804.0, "dist": {"<1s": 113, "1-3s": 197, "3-6s": 41, ">6s": 17}}


def shot_stats(video_path, threshold=27.0):
    """(I/O) 量一支(已剪接)影片的剪輯節奏 → _shot_stats。
    ⚠️ 對 raw 連續長鏡頭無意義(會回 1 shot);用於評估『已剪好』的成片 vs 66 期。"""
    shots = detect_shots(video_path, threshold=threshold)
    return _shot_stats(shots)


def compare_to_gold(stats, gold=None):
    """純函式:把成片節奏 vs 66 期 gold,回各指標比值與評語(收品質里程碑)。"""
    gold = gold or GOLD_66
    def ratio(a, b):
        return round(a / b, 2) if b else None
    return {
        "median_ratio": ratio(stats["median"], gold["median"]),
        "cuts_per_min_ratio": ratio(stats["cuts_per_min"], gold["cuts_per_min"]),
        "pace": ("太慢(剪太少)" if stats["cuts_per_min"] < gold["cuts_per_min"] * 0.6
                 else "太快(剪太碎)" if stats["cuts_per_min"] > gold["cuts_per_min"] * 1.6
                 else "接近 66 期節奏"),
        "ours": stats, "gold": gold,
    }


# ── increment ④: mv-cut renderer（選段 × beat 切點 → 對拍拼接出片）────────────

_MV_VF = ("scale=1920:1080:force_original_aspect_ratio=decrease,"
          "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,setsar=1,fps=30,format=yuv420p")

_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".heic"}


def _video_vf(crop_center=None):
    if not isinstance(crop_center, dict):
        return _MV_VF
    x = min(1.0, max(0.0, float(crop_center.get("x", 0.5))))
    y = min(1.0, max(0.0, float(crop_center.get("y", 0.5))))
    return (
        "scale=1920:1080:force_original_aspect_ratio=increase,"
        f"crop=1920:1080:x='(iw-ow)*{x:.3f}':y='(ih-oh)*{y:.3f}',"
        "setsar=1,fps=30,format=yuv420p"
    )


def _is_image(path):
    return os.path.splitext(path or "")[1].lower() in _IMG_EXTS


def _photo_vf(dur, kenburns=True, treatment=None):
    """靜照→影片片段的 vf。kenburns=緩慢推近(救開場/收尾照片,避免死板靜止);
    否則純 hold(scale+pad)。輸出 1920x1080@30。純函式(回 vf 字串)。"""
    if not kenburns:
        return _MV_VF
    frames = max(1, round((dur or 1.0) * 30))
    # 先上採樣到 4K 再 zoompan 置中緩推,避免低解析照片放大鋸齒/抖動
    mode = (treatment or {}).get("mode", "slow_push")
    motion = {
        "pan_right": "z=1.3:x='if(eq(on,1),0,min(x+3,iw-iw/zoom))':y='ih/2-(ih/zoom/2)'",
        "pan_left": "z=1.3:x='if(eq(on,1),iw-iw/zoom,max(x-3,0))':y='ih/2-(ih/zoom/2)'",
        "detail_push": (
            "z='min(zoom+0.0016,1.4)':x='trunc(iw/2-(iw/zoom/2))':"
            "y='trunc(ih/2-(ih/zoom/2))'"
        ),
    }.get(mode, (
        "z='min(zoom+0.0008,1.25)':x='trunc(iw/2-(iw/zoom/2))':"
        "y='trunc(ih/2-(ih/zoom/2))'"
    ))
    return ("scale=3840:2160:force_original_aspect_ratio=increase,crop=3840:2160,"
            f"zoompan={motion}:d={frames}:s=1920x1080:fps=30,"
            "setsar=1,format=yuv420p")


def _cjk_font():
    try:
        return resolve_font()
    except Exception:
        return None


_CJK_FONT = _cjk_font()


def _drawtext_chain(text, mat_dir, slot_idx):
    """編劇文字層 → ffmpeg drawtext:narrative(全屏故事字卡:暗化+大字置中)+
    label(底置中標籤)+ name_super(左下人名)。CJK 寫進 temp file 避免命令列跳脫。
    回 ',...' 串接到 vf;無文字/無字型回 ''。"""
    if not text or not _CJK_FONT:
        return ""
    ff = _CJK_FONT.replace("\\", "/").replace(":", "\\:")
    parts = []
    if text.get("narrative"):   # 全屏敘事字卡(傳承精技/篤學不倦):暗化背景 + 大字置中
        tf = os.path.join(mat_dir, f"nar_{slot_idx}.txt")
        with open(tf, "w", encoding="utf-8") as f:
            f.write(text["narrative"])
        tf_esc = tf.replace("\\", "/").replace(":", "\\:")
        if text.get("placement") == "lower_third":
            parts.append(f"drawtext=fontfile='{ff}':textfile='{tf_esc}':fontsize=46:fontcolor=white:"
                         f"borderw=3:bordercolor=black@0.8:line_spacing=14:"
                         f"x=(w-text_w)/2:y=h-text_h-140")
        else:
            parts.append("drawbox=x=0:y=0:w=iw:h=ih:color=black@0.5:t=fill")
            parts.append(f"drawtext=fontfile='{ff}':textfile='{tf_esc}':fontsize=72:fontcolor=white:"
                         f"borderw=2:bordercolor=black@0.6:line_spacing=20:"
                         f"x=(w-text_w)/2:y=(h-text_h)/2")
    if text.get("label"):
        tf = os.path.join(mat_dir, f"lbl_{slot_idx}.txt")
        with open(tf, "w", encoding="utf-8") as f:
            f.write(text["label"])
        tf_esc = tf.replace("\\", "/").replace(":", "\\:")
        parts.append(f"drawtext=fontfile='{ff}':textfile='{tf_esc}':fontsize=46:fontcolor=white:"
                     f"borderw=3:bordercolor=black@0.9:x=(w-text_w)/2:y=h-130")
    ns = text.get("name_super")
    if ns and ns.get("text"):
        nm = ns["text"] + ("  " + ns["title"] if ns.get("title") else "")
        tf = os.path.join(mat_dir, f"nm_{slot_idx}.txt")
        with open(tf, "w", encoding="utf-8") as f:
            f.write(nm)
        tf_esc = tf.replace("\\", "/").replace(":", "\\:")
        parts.append(f"drawtext=fontfile='{ff}':textfile='{tf_esc}':fontsize=34:fontcolor=white:"
                     f"borderw=2:bordercolor=black@0.9:x=70:y=h-210")
    return ("," + ",".join(parts)) if parts else ""


def plan_mv(selected, cut_grid):
    """純函式：把 select_windows 選出的窗,對映到 beat cut_grid 的時槽。
    每個 clip 從它「被評分的 window midpoint」置中取 slot 長度(beat 對齊)。
    回傳 render plan：[{source, extract_start, extract_dur, slot_index, slot_dur, group}]。"""
    plan = []
    n = min(len(selected), len(cut_grid))
    for i in range(n):
        cand = selected[i]
        ws, we = cand["win"]
        slot_dur = cut_grid[i][1] - cut_grid[i][0]
        win_mid = (ws + we) / 2.0
        take = min(slot_dur, we - ws)               # 不能超過 window 長度
        start = max(ws, win_mid - take / 2.0)        # 置中於評分的 midpoint
        plan.append({"source": cand.get("source"),
                     "extract_start": round(start, 3), "extract_dur": round(take, 3),
                     "slot_index": i, "slot_dur": round(slot_dur, 3),
                     "group": cand.get("group")})
    return plan


def render_mv(plan, music_path, out_path, mat_dir=None):
    """(I/O) increment ④：依 plan 從各原片抽段 → 統一 1920x1080 → 硬切拼接(對拍)
    → 鋪音樂(trim 到視覺長度)→ out_path。回傳 out_path。"""
    mat_dir = mat_dir or resolve_temp_dir()
    segs = []
    for p in plan:
        seg = os.path.join(mat_dir, f"mvseg_{p['slot_index']:03d}.mp4")
        r = subprocess.run([FFMPEG, "-y", "-ss", f"{p['extract_start']:.3f}",
                            "-i", p["source"], "-t", f"{p['extract_dur']:.3f}",
                            "-vf", _MV_VF, "-an", "-c:v", "libx264", "-preset", "medium",
                            "-crf", "20", "-pix_fmt", "yuv420p", seg],
                           capture_output=True, timeout=180)
        if r.returncode == 0 and os.path.exists(seg):
            segs.append(seg)
    if not segs:
        raise ToolError("render_mv: no segments rendered")
    listf = os.path.normpath(os.path.join(mat_dir, "mv_concat.txt"))
    with open(listf, "w") as f:
        for s in segs:
            clean_path = os.path.abspath(s).replace('\\', '/')
            f.write(f"file '{clean_path}'\n")   # 絕對路徑:避免 concat 相對路徑雙重前綴
    visual = os.path.join(mat_dir, "mv_visual.mp4")
    subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listf,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", visual], capture_output=True, timeout=600)
    cmd = [FFMPEG, "-y", "-i", visual]
    if music_path and os.path.exists(music_path):
        cmd += ["-i", music_path, "-map", "0:v:0", "-map", "1:a:0",
                "-c:v", "copy", "-c:a", "aac", "-shortest", out_path]
    else:
        cmd += ["-c:v", "copy", out_path]
    subprocess.run(cmd, capture_output=True, timeout=180)
    return out_path


# ── 劇本驅動跑全鏈（run_mv）─────────────────────────────────────────────────

def _stack_items(s):
    """Return the enumeration item list when a segment opts into a photo stack
    (material_treatment.treatment=photo_stack_beat or editing_intent.content_pattern
    =enumeration with declared items), else None. Opt-in: absent => unchanged."""
    mt = s.get("material_treatment") or {}
    ei = s.get("editing_intent") or {}
    is_stack = mt.get("treatment") == "photo_stack_beat" or ei.get("content_pattern") == "enumeration"
    items = mt.get("items") or []
    return list(items) if (is_stack and items) else None


def allocate_segments(segments, total_dur, fast_clip=1.5, stack_shot_sec=0.8):
    """純函式:把音樂總長分給各段 → 每段幾個 clip、每 clip 多長。
    montage/pace:fast → 多個快剪(~fast_clip 秒,預設 1.5≈66 期中位 1.47);
    hold/opening/closing/title/單圖 → 1 個長 clip。
    photo_stack_beat(列舉)→ n_clips = 項目數,每張 ≈ `stack_shot_sec`(對拍快堆疊,
    不平分整段預算),所以列舉段是「1 拍 1 張」的快剪而非長 hold。
    **pacing 調勻**:段可宣告 `weight`(預設 1.0=等分)讓 hold(隊呼長 hold)拿更多時間,
    montage 維持快剪。回傳 [{segment, n_clips, clip_dur, budget}]。"""
    n = len(segments)
    if n == 0 or total_dur <= 0:
        return []
    weights = [max(0.1, float(s["weight"])) if s.get("weight") is not None else 1.0
               for s in segments]
    wsum = sum(weights) or 1.0
    out = []
    for s, w in zip(segments, weights):
        kind = s.get("kind")
        budget = total_dur * w / wsum
        is_fast = (s.get("layout") == "montage") or (s.get("pace") == "fast")
        attention = s.get("attention_budget") or {}
        attention_forces_cut = attention.get("owner") in {"music", "visual"}
        single = (
            kind in ("opening", "closing", "title")
            or (bool(s.get("hold")) and not attention_forces_cut)
            or (not is_fast and not attention_forces_cut)
        )
        # Contract pacing wins over the global fast_clip default: a segment
        # declaring preferred_shot_sec=[4,8] wants ~6s shots, not 1.5s — this is
        # what keeps engine allocation in step with Node 9 shot_slots.
        shot_sec = fast_clip
        pref = (
            attention.get("shot_sec")
            if attention_forces_cut
            else (s.get("pacing") or {}).get("preferred_shot_sec")
        )
        if pref:
            try:
                if isinstance(pref, (list, tuple)) and len(pref) >= 2:
                    shot_sec = (float(pref[0]) + float(pref[1])) / 2
                else:
                    shot_sec = float(pref[0] if isinstance(pref, (list, tuple)) else pref)
            except (TypeError, ValueError):
                shot_sec = fast_clip
            shot_sec = max(0.5, shot_sec)
        n_clips = 1 if single else max(1, round(budget / shot_sec))
        min_shots = int((s.get("anti_presentation_plan") or {}).get("min_shots") or 0)
        if min_shots:
            n_clips = max(n_clips, min_shots)
        stack = _stack_items(s)
        if stack:                       # 列舉:每項一張、每張 ≈ 一拍(beat-fast)
            n_clips = max(1, len(stack))
            clip_dur = round(stack_shot_sec, 3)
        else:
            clip_dur = round(budget / n_clips, 3)
        out.append({"segment": s.get("segment"), "n_clips": n_clips,
                    "clip_dur": clip_dur, "budget": round(budget, 3)})
    return out


def find_clips(material_root, material_hint, exts=None):
    """(I/O) 找 material_root 底下、路徑含 material_hint 的影片(scoping)。"""
    exts = exts or {".mp4", ".mov", ".m4v", ".avi", ".mkv"}
    hint = (material_hint or "").replace("/", os.sep)
    hits = []
    for dp, _, fs in os.walk(material_root):
        for f in fs:
            if os.path.splitext(f)[1].lower() in exts:
                full = os.path.join(dp, f)
                if hint and hint in full:
                    hits.append(full)
    return sorted(hits)


def find_photos(material_root, material_hint):
    """(I/O) 找 material_root 底下、路徑含 material_hint 的照片(救開場/收尾 bookend)。"""
    return find_clips(material_root, material_hint, exts=_IMG_EXTS)


# ── per-段選段規劃器(從 run_mv 解耦:每個分支=可獨立 review/測的節點)──────────
# 每個 planner 回 (slots, per_seg_entry, msgs);slots 不含 slot_index(由 run_mv 統一指派),
# 純規劃、不渲染。三種來源:matched(match-mv 已配)/ stock(Pexels)/ live(現場 VLM 評分)。

def _windows_from_clip(path, n_clips, clip_dur, keep_audio, text=None, segment=None):
    """一支已選定 clip → 對拍 slots(照片=1 still kenburns;影片=fixed_windows 開窗)。
    回 slots(無 slot_index)。n_clips<=0 回空。"""
    if n_clips <= 0:
        return []
    if _is_image(path):
        modes = ("slow_push", "pan_right", "detail_push", "pan_left")
        return [{
            "source": path,
            "extract_start": 0.0,
            "extract_dur": round(clip_dur, 3),
            "keep_audio": False,
            "text": text,
            "segment": segment,
            "is_photo": True,
            "photo_variant": i + 1,
            "still_treatment": {"mode": modes[i % len(modes)], "reason": "photo_multi_shot"},
        } for i in range(n_clips)]
    slots = []
    shots = detect_shots(path)
    wins = fixed_windows(shots[0][1] if shots else 0, win=max(2.0, clip_dur))
    for ws, we in wins:
        if len(slots) >= n_clips:
            break
        take = min(clip_dur, we - ws)
        start = max(ws, (ws + we) / 2 - take / 2)
        slots.append({"source": path, "extract_start": round(start, 3),
                      "extract_dur": round(take, 3), "keep_audio": keep_audio,
                      "text": text, "segment": segment})
    return slots


def _apply_anti_presentation_plan(slots, segment):
    """Apply Node 9 anti-presentation directives to concrete render slots."""
    plan = segment.get("anti_presentation_plan") or {}
    modes = plan.get("still_treatment_modes") or []
    placement = plan.get("text_placement")
    for index, slot in enumerate(slots):
        if slot.get("is_photo") and modes:
            slot["still_treatment"] = {
                "mode": modes[index % len(modes)],
                "reason": "anti_presentation_rotation",
            }
        if placement:
            text = slot.get("text")
            if not isinstance(text, dict):
                text = {}
                slot["text"] = text
            text["placement"] = placement
    return slots


def _plan_matched_segment(s, a, clip_by_seg, seg_text, keep_audio, _winfn=None):
    """local 段:用 match-mv 已配好的 clip 開窗(不 live 重評)。`_winfn` 可注入測試。"""
    winfn = _winfn or _windows_from_clip
    vd = s.get("visual_desc", "")
    paths = [p["path"] for p in clip_by_seg.get(s.get("segment"), {}).get("picks", [])]
    if not paths and s.get("file"):
        paths = [s["file"]]
    slots = []
    for path in paths:
        slots += winfn(path, a["n_clips"] - len(slots), a["clip_dur"], keep_audio,
                       text=seg_text, segment=s.get("segment"))
        if len(slots) >= a["n_clips"]:
            break
    for slot in slots:
        slot["provider"] = "local"
    entry = {"segment": s.get("segment"), "visual_desc": vd, "source": "local(matched)",
             "provider": "local",
             "clips_found": len(paths), "n_clips": a["n_clips"],
             "picked_scores": ["matched"] * len(slots) or [GAP]}
    msg = (f"  seg{s.get('segment')} '{vd[:18]}' ← match-mv clip x{len(paths)} → "
           f"{len(slots)} slots" + (" GAP" if not slots else ""))
    return slots, entry, [msg]


# Stock honesty floor: a clip whose BEST window scores below this is off-topic
# (rubric 10/15); windows at 40 ("loosely related") are legitimate stock B-roll.
_STOCK_OFF_TOPIC_FLOOR = 25.0
# How many next-most-relevant candidates to try after a VLM rejection before GAP.
_STOCK_VLM_RETRIES = 2


def _distill_subject(desc):
    """主詞句蒸餾——canonical 實作住在 content_qa(與 scorer 同居,兩鏈共用)。"""
    from .content_qa import distill_subject  # noqa: PLC0415
    return distill_subject(desc)


def _plan_stock_segment(s, a, seg_text, mat_dir, _fetch=None, _winfn=None,
                        model=None, min_score=0, prefilter_static=True, _scorefn=None,
                        visual_judge="ollama", visual_verdict=None, _gridfn=None):
    """stock 橋段:Pexels 抓片(抓不到→GAP 不炸,可恢復)。`_fetch`/`_winfn`/`_scorefn`
    可注入測試。

    素材裁剪 = 內容驅動(與 live 段同一套機具):下載素材先開候選窗
    (detect_shots+fixed_windows+靜止預篩),`model` 給定時用 VLM 對 `visual_desc`
    逐窗評分(score_windows),選最好的 n 窗按時間序組回——
    - VLM 判全部窗低於 min_score → 誠實 GAP(疑離題,走可恢復路由換 query/generated);
    - VLM 不可用(Ollama 掛/例外) → 退回機械開窗(_windows_from_clip,無內容判斷);
    - model=None → 直接機械開窗(向後相容)。
    窗不夠 n 刀時循環複用(重複交給 broll_audit 盯);機械開窗也失敗 → 單一全預算 slot。"""
    vd = s.get("visual_desc", "")
    query = s.get("search_query") or vd
    stock = os.path.join(mat_dir, f"mvstock_{s.get('segment')}.mp4")
    msgs = []
    n_clips = max(1, int(a.get("n_clips") or 1))
    slots = []
    picked_scores = None
    if _fetch is None:
        from .vt_stock import fetch_stock_video_with_provider as _default_fetch
        _fetch = _default_fetch

    def _try_fetch(skip):
        """回 (path|None, provider|None, exhausted)。exhausted=fetcher 不支援 skip。"""
        try:
            res = _fetch(query, stock, min_dur=0, skip=skip) if skip else _fetch(query, stock, min_dur=0)
        except TypeError:
            return None, None, True     # 注入的舊式 fetcher 不吃 skip → 無更多候選
        except Exception as _e:
            msgs.append(f"  seg{s.get('segment')} [stock] fetch 失敗(可恢復→GAP): {str(_e)[:60]}")
            return None, None, False
        if isinstance(res, tuple):
            return res[0], res[1], False
        return res, ("pexels" if res else None), False

    if visual_judge == "agent":
        got, provider, _exhausted = _try_fetch(0)
        verdict_action = (visual_verdict or {}).get("action")
        verdict_accepts = (visual_verdict or {}).get("accept") or verdict_action in ("accept", "needs_patch")
        if got and visual_verdict and verdict_accepts:
            patch = visual_verdict.get("patch") or {}
            for window in visual_verdict.get("picked_windows") or []:
                ws, we = float(window["start"]), float(window["end"])
                take = min(float(a["clip_dur"]), we - ws)
                start = max(ws, (ws + we) / 2 - take / 2)
                slot = {
                    "source": got,
                    "extract_start": round(start, 3),
                    "extract_dur": round(take, 3),
                    "keep_audio": False,
                    "text": seg_text,
                    "segment": s.get("segment"),
                    "provider": provider or "pexels",
                }
                if patch.get("type") == "crop":
                    slot["crop_center"] = dict(patch.get("hint") or {})
                elif patch.get("type") == "treatment":
                    slot["still_treatment"] = dict(patch.get("hint") or {})
                slots.append(slot)
            patched = visual_verdict.get("action") == "needs_patch"
            entry = {
                "segment": s.get("segment"),
                "visual_desc": vd,
                "source": "stock",
                "provider": provider or "pexels",
                "clips_found": 1,
                "n_clips": len(slots),
                "picked_scores": ["agent_patch" if patched else "agent"] * len(slots),
                "patch": patch if patched else None,
            }
            msgs.append(f"  seg{s.get('segment')} [stock] agent verdict accepted {len(slots)} window(s)")
            return slots, entry, msgs
        if got and visual_verdict and not verdict_accepts:
            entry = {
                "segment": s.get("segment"),
                "visual_desc": vd,
                "source": "stock",
                "provider": provider or "pexels",
                "clips_found": 1,
                "n_clips": n_clips,
                "picked_scores": [GAP],
                "reject_reason": visual_verdict.get("reject_reason"),
            }
            msgs.append(f"  seg{s.get('segment')} [stock] agent verdict rejected candidate")
            return [], entry, msgs
        if got:
            if _gridfn is None:
                from .keyframe_grid import generate_keyframe_grid as _gridfn
            review_dir = os.path.join(mat_dir, "visual_review")
            montage = os.path.join(review_dir, f"seg{s.get('segment')}_stock.jpg")
            grid = _gridfn(got, montage, sample_count=max(8, n_clips * 4))
            entry = {
                "segment": s.get("segment"),
                "visual_desc": vd,
                "verify_desc": vd or query,
                "source": "stock",
                "provider": provider or "pexels",
                "candidate": got,
                "montage": grid.get("grid_path") or montage,
                "samples": grid.get("samples") or [],
                "clips_found": 1,
                "n_clips": n_clips,
                "pending_visual_review": True,
                "picked_scores": ["PENDING_VISUAL_REVIEW"],
            }
            msgs.append(f"  seg{s.get('segment')} [stock] awaiting agent visual review")
            return [], entry, msgs

        entry = {
            "segment": s.get("segment"),
            "visual_desc": vd,
            "source": "stock",
            "provider": None,
            "clips_found": 0,
            "n_clips": n_clips,
            "picked_scores": [GAP],
        }
        return [], entry, msgs

    def _score_clip(path):
        """VLM 評窗一支素材。回 list=接受(選好的窗)/ []=離題拒用 / None=VLM 不可用。
        兩段式:先用完整 visual_desc;全低於 floor 再用「主詞句蒸餾」救援——
        導演式多子句描述(螺旋/冒泡/蒸氣)會讓 4b 逐條摳字全判否(D5),但 stock
        B-roll 的選窗只需要主體級匹配(skill-smoke seg3 false-reject 實證)。"""
        try:
            shots = detect_shots(path)
            total = shots[0][1] if shots else 0
            wins = fixed_windows(total, win=max(2.0, a["clip_dur"]))
            if prefilter_static:
                wins = filter_static_windows(wins, path) or wins
            cap = max(6, n_clips * 2)            # bound VLM cost per stock clip
            if len(wins) > cap:
                step = max(1, len(wins) // cap)
                wins = wins[::step][:cap]
            if not wins:
                return None
            for verify_desc in (vd or query or "", _distill_subject(vd or query or "")):
                if not verify_desc:
                    continue
                cands = score_windows(path, wins, verify_desc, model=model,
                                      mat_dir=mat_dir, _score=_scorefn)
                # 選窗=相對排名(top-n);誠實拒用=絕對低標。rubric:100/75=主體命中、
                # 60=on-topic、40=鬆散相關(stock B-roll 可用)、10/15=離題。
                best = max((c.get("score") or 0) for c in cands) if cands else 0
                if best >= _STOCK_OFF_TOPIC_FLOOR:
                    sel, _unf = select_windows(cands, n_slots=n_clips, min_score=0)
                    sel.sort(key=lambda c: c["win"][0])   # 時間序組回(敘事順向)
                    return sel
            return []                    # 連蒸餾主詞句都不過 → 真離題
        except Exception as _e:
            msgs.append(f"  seg{s.get('segment')} [stock] VLM 評窗不可用(退回機械開窗): "
                        f"{str(_e)[:60]}")
            return None

    # 1) 抓素材(+VLM 拒絕時往下試相關性次高的候選,最多 _STOCK_VLM_RETRIES 次)
    got = provider = None
    scored = None    # None=未評(跳過/失敗);list=接受;[]=評了且拒用
    rejected_candidates = 0
    for attempt in range(_STOCK_VLM_RETRIES + 1):
        got, provider, exhausted = _try_fetch(attempt)
        if not got:
            if attempt > 0:
                got = None              # 沒有下一個候選了
            break
        if not model:
            break                       # 機械路徑無判官,不重試
        scored = _score_clip(got)
        if scored is None or scored:
            break                       # VLM 不可用(退機械)或已接受
        rejected_candidates += 1
        msgs.append(f"  seg{s.get('segment')} [stock] 候選#{attempt + 1} 被 VLM 判離題,"
                    f"試下一個候選…")
        if exhausted:
            break
    vlm_rejected = (scored == [])

    if got and scored:
        for cand in scored[:n_clips]:
            ws, we = cand["win"]
            take = min(a["clip_dur"], we - ws)
            start = max(ws, (ws + we) / 2 - take / 2)
            slots.append({"source": got, "extract_start": round(start, 3),
                          "extract_dur": round(take, 3), "keep_audio": False,
                          "text": seg_text, "segment": s.get("segment"),
                          "provider": provider or "pexels"})
        i = 0
        while slots and len(slots) < n_clips:   # 窗不夠 → 循環複用
            slots.append(dict(slots[i % len(slots)]))
            i += 1
        picked_scores = [round(c["score"]) for c in scored[:n_clips]]
        msgs.append(f"  seg{s.get('segment')} [stock] VLM 評窗 picked={picked_scores}")
    elif vlm_rejected:
        # 2) 試過的候選(含主詞句蒸餾救援)全部低於 off-topic floor → 誠實 GAP
        #    (走既有可恢復路由:換 search_query / 改 generated),不硬用。
        msgs.append(f"  seg{s.get('segment')} [stock] {rejected_candidates} 個候選全被 VLM "
                    f"判離題(floor={_STOCK_OFF_TOPIC_FLOOR})→ GAP(換 query 或走 generated)")
    elif got:
        # 3) 機械開窗(VLM 未啟用/不可用):多 shot 段照樣切窗,不要一鏡到底。
        if n_clips > 1:
            winfn = _winfn or _windows_from_clip
            try:
                wins = winfn(got, n_clips, a["clip_dur"], False,
                             text=seg_text, segment=s.get("segment"))
            except Exception:
                wins = []
            if wins:
                i = 0
                while len(wins) < n_clips:      # 窗不夠 n 刀 → 循環複用
                    wins.append(dict(wins[i % len(wins)]))
                    i += 1
                for w in wins:
                    w["provider"] = provider or "pexels"
                slots = wins
        if not slots:  # 單 shot 段,或開窗失敗的回退
            slots.append({"source": got, "extract_start": 0.0, "extract_dur": round(a["budget"], 3),
                          "keep_audio": False, "text": seg_text, "segment": s.get("segment"),
                          "provider": provider or "pexels"})

    got_usable = bool(got) and not vlm_rejected
    entry = {"segment": s.get("segment"), "visual_desc": vd, "source": "stock",
             "provider": provider or "pexels" if got_usable else None,
             "clips_found": 1 if got else 0, "n_clips": len(slots) if got_usable else n_clips,
             "picked_scores": (picked_scores or ["stock"] * len(slots)) if got_usable else [GAP]}
    if vlm_rejected:
        entry["vlm_rejected"] = True
    msgs.append(f"  seg{s.get('segment')} [stock] '{vd[:16]}' q={s.get('search_query')} "
                f"-> {'ok' if got_usable else 'GAP'}")
    return slots, entry, msgs


def _plan_stock_stack_segment(s, a, mat_dir, items, _fetch_photo=None):
    """photo_stack_beat 列舉段:每個項目抓一張 stock 照片 → N 個帶『品名 label』的
    still slot(per-item label)。抓不到 → 該項 GAP,不炸(可恢復)。`_fetch_photo` 可注入測試。"""
    if _fetch_photo is None:
        from .vt_stock import fetch_stock_photo as _fetch_photo
    vd = s.get("visual_desc", "")
    base_q = s.get("search_query") or vd
    slots, scores, msgs = [], [], []
    for i, item in enumerate(items):
        out = os.path.join(mat_dir, f"mvstack_{s.get('segment')}_{i}.jpg")
        q = (f"{base_q} {item}").strip()
        got, provider = None, None
        try:
            got, provider = _fetch_photo(q, out)
        except Exception as _e:
            msgs.append(f"  seg{s.get('segment')} [stack] '{item}' fetch 失敗(→GAP): {str(_e)[:40]}")
        if got:
            slots.append({"source": got, "extract_start": 0.0,
                          "extract_dur": round(a["clip_dur"], 3), "keep_audio": False,
                          "text": {"label": str(item)}, "segment": s.get("segment"),
                          "is_photo": True, "kenburns": True,
                          "provider": provider or "pexels-photo"})
            scores.append("stack")
        else:
            scores.append(GAP)
    entry = {"segment": s.get("segment"), "visual_desc": vd, "source": "stock(stack)",
             "provider": "pexels-photo", "clips_found": len(slots), "n_clips": len(items),
             "treatment": "photo_stack_beat", "picked_scores": scores or [GAP]}
    msgs.append(f"  seg{s.get('segment')} [stack] {len(slots)}/{len(items)} stills "
                f"items={items}")
    return slots, entry, msgs


def _plan_live_segment(s, a, material_root, seg_text, keep_audio, *, model, mat_dir,
                       max_clips_per_seg, windows_per_clip, min_score, prefilter_static):
    """live 段:find_clips/photos → (照片 still) 或 (開窗→靜止預篩→VLM 評分→必放選段)。"""
    vd = s.get("visual_desc", "")
    clips = find_clips(material_root, s.get("material_hint", ""))[:max_clips_per_seg]
    photos = find_photos(material_root, s.get("material_hint", ""))
    msgs = []
    # 照片段(bookend:media=photo / opening|closing|title,或無影片只有照片)= 高權重 slot
    want_photo = (s.get("media") == "photo" or s.get("kind") in ("opening", "closing", "title")
                  or (not clips and photos))
    if want_photo and photos:
        kb = bool(s.get("kenburns", True))
        chosen = photos[:a["n_clips"]]
        slots = [{"source": ph, "extract_start": 0.0, "extract_dur": round(a["clip_dur"], 3),
                  "keep_audio": False, "text": seg_text, "segment": s.get("segment"),
                  "is_photo": True, "kenburns": kb, "provider": "local"} for ph in chosen]
        entry = {"segment": s.get("segment"), "visual_desc": vd, "source": "local(photo)",
                 "provider": "local",
                 "clips_found": len(photos), "n_clips": a["n_clips"],
                 "picked_scores": ["photo"] * len(chosen) or [GAP]}
        msgs.append(f"  seg{s.get('segment')} '{vd[:18]}' [photo] photos={len(photos)} "
                    f"→ {len(chosen)} stills")
        return slots, entry, msgs
    cands = []
    for c in clips:
        shots = detect_shots(c)
        wins = fixed_windows(shots[0][1] if shots else 0, win=max(2.0, a["clip_dur"]))
        if prefilter_static:   # 丟掉幾乎不動的窗,省 VLM call(全靜 → 留原窗)
            kept = filter_static_windows(wins, c)
            if len(kept) < len(wins):
                msgs.append(f"    [prefilter] {os.path.basename(c)} 靜止窗 "
                            f"{len(wins)-len(kept)}/{len(wins)} 丟棄")
            wins = kept
        step = max(1, len(wins) // windows_per_clip)
        cands += score_windows(c, wins[::step][:windows_per_clip], vd, model=model, mat_dir=mat_dir)
    sel, _unf = select_windows(cands, n_slots=a["n_clips"],
                               must_include=([s["must_include"]] if s.get("must_include") else []),
                               min_score=min_score)   # 不對題的丟掉;必放仍 override
    scores = [round(x["score"]) for x in sel]
    slots = []
    for cand in sel[:a["n_clips"]]:
        ws, we = cand["win"]
        take = min(a["clip_dur"], we - ws)
        start = max(ws, (ws + we) / 2 - take / 2)
        slots.append({"source": cand["source"], "extract_start": round(start, 3),
                      "extract_dur": round(take, 3), "keep_audio": keep_audio,
                      "text": seg_text, "segment": s.get("segment"),
                      "provider": "local"})
    entry = {"segment": s.get("segment"), "visual_desc": vd, "provider": "local", "clips_found": len(clips),
             "n_clips": a["n_clips"], "picked_scores": scores}
    msgs.append(f"  seg{s.get('segment')} '{vd[:18]}' hint={s.get('material_hint')} "
                f"clips={len(clips)} picked={scores}")
    return slots, entry, msgs


def trim_beats_to_target(beats, target_sec):
    """純函式:把 beat 列裁到 target 內(取最後一個 <= target 的 beat,保持對拍)。

    音樂長度只該定「節奏」,不該定「總長」——brief 的 target_length 才是總長
    (ai-video soul-v5:122.9s 音樂把 45s 的片撐成 123s,8 個 pacing fail 全由此
    連鎖)。target 無效/不小於音樂長度時原樣返回。至少保留 2 個 beat。"""
    if not beats or not target_sec or target_sec <= 0:
        return list(beats or [])
    if target_sec >= beats[-1]:
        return list(beats)
    kept = [b for b in beats if b <= target_sec]
    if len(kept) < 2:
        kept = list(beats[:2])
    return kept


def run_mv(script, material_root, out_path, music_path=None,
           model="qwen3-vl:4b-instruct", mat_dir=None, max_clips_per_seg=2,
           windows_per_clip=2, min_score=60, clip_list=None, prefilter_static=True,
           verbose=True, skip_render=False, target_sec=None, burn_text=True,
           visual_judge="ollama"):
    """clip_list(match-mv 結果)給定時:local 段用「已配好+人複核」的 clip,不 live 重評
    (roadmap #0 接線)。未給則 fallback live 評分。stock 段一律 Pexels。"""
    """劇本驅動跑全鏈(v0):音樂先→cut_grid 分段→per-段 visual_desc 評窗(鑑別力)
    →選最佳→對拍/長 hold 組裝→audio_role 混音→render。回傳 {out, plan, per_seg}。"""
    def vp(*a):
        if verbose:
            print(*a)

    mat_dir = mat_dir or resolve_temp_dir()
    segs = script.get("segments") or []
    # 1) 音樂先(定總長/節奏)。v0:music_path 由呼叫端先用 music-fetch 抓好傳入。
    if not music_path:
        raise ToolError("run_mv v0 需要 music_path(先用 music-fetch 依 brief 抓好再傳入)")
    _tempo, _beats = detect_beats(music_path)
    music_dur = _beats[-1] if _beats else 0
    _beats = trim_beats_to_target(_beats, target_sec)
    total_dur = _beats[-1] if _beats else 0
    if target_sec and total_dur < music_dur:
        vp(f"[music] {os.path.basename(music_path)} {round(music_dur,1)}s tempo={round(_tempo)} "
           f"→ trimmed to target {round(total_dur,1)}s (brief target_length)")
    else:
        vp(f"[music] {os.path.basename(music_path)} {round(total_dur,1)}s tempo={round(_tempo)}")

    # 2) 時長分配(列舉堆疊用「一拍」長度 → 對拍快剪)
    beat_sec = (60.0 / _tempo) if _tempo else 0.8
    stack_shot_sec = max(0.4, min(beat_sec, 1.2))
    alloc = allocate_segments(segs, total_dur, stack_shot_sec=stack_shot_sec)
    clip_by_seg = {as_["segment"]: as_ for as_ in (clip_list or {}).get("assignments", [])}
    visual_verdicts = {}
    if visual_judge == "agent":
        from .visual_review import load_verdict
        visual_verdicts = load_verdict(os.path.join(mat_dir, "visual_review_verdict.json"))

    # 3) per-段:派工給對應 planner(matched / stock / live),收 slots+entry
    plan, per_seg = [], []
    for s, a in zip(segs, alloc):
        keep_audio = bool(s.get("hold") or s.get("keep_audio")
                          or s.get("audio_role") in ("duck", "diegetic"))
        seg_text = {"label": s.get("label"), "name_super": s.get("name_super"),
                    "subtitle": s.get("subtitle"), "narrative": s.get("narrative")}  # 編劇文字層
        stack_items = _stack_items(s)
        if clip_list is not None and s.get("source") != "stock":
            slots, entry, msgs = _plan_matched_segment(s, a, clip_by_seg, seg_text, keep_audio)
        elif s.get("source") == "stock" and stack_items:
            slots, entry, msgs = _plan_stock_stack_segment(s, a, mat_dir, stack_items)
            # Snapping stack still cut times to actual music beat grid timestamps
            if _beats:
                current_time = sum(sl.get("extract_dur", 0.0) for sl in plan)
                # Find the closest beat index to current_time
                k = min(range(len(_beats)), key=lambda idx: abs(_beats[idx] - current_time))
                for i, sl in enumerate(slots):
                    if k + i + 1 < len(_beats):
                        if i == 0:
                            dur = _beats[k + 1] - current_time
                        else:
                            dur = _beats[k + i + 1] - _beats[k + i]
                        if dur > 0.1:
                            sl["extract_dur"] = round(dur, 3)
                        else:
                            sl["extract_dur"] = round(_beats[k + i + 1] - _beats[k + i], 3)
                    else:
                        sl["extract_dur"] = round(a["clip_dur"], 3)
        elif s.get("source") == "stock":
            slots, entry, msgs = _plan_stock_segment(
                s, a, seg_text, mat_dir,
                model=model, min_score=min_score, prefilter_static=prefilter_static,
                visual_judge=visual_judge, visual_verdict=visual_verdicts.get(s.get("segment")))
        else:
            slots, entry, msgs = _plan_live_segment(
                s, a, material_root, seg_text, keep_audio, model=model, mat_dir=mat_dir,
                max_clips_per_seg=max_clips_per_seg, windows_per_clip=windows_per_clip,
                min_score=min_score, prefilter_static=prefilter_static)
        _apply_anti_presentation_plan(slots, s)
        reason_str = None
        for r_path in [
            lambda: s.get("material_fit", {}).get("reason"),
            lambda: s.get("visual_style", {}).get("reason"),
            lambda: s.get("editing_grammar", {}).get("reason"),
            lambda: s.get("text_layer", {}).get("reason"),
            lambda: s.get("reason")
        ]:
            try:
                val = r_path()
                if val and isinstance(val, str) and val.strip():
                    reason_str = val.strip()
                    break
            except Exception:
                pass

        for sl in slots:                 # slot_index 在這裡統一順序指派
            sl["slot_index"] = len(plan)
            if s.get("attention_budget"):
                sl["attention_budget"] = s["attention_budget"]
            if s.get("creative_exception"):
                sl["creative_exception"] = s["creative_exception"]
            if sl is slots[0]:
                visual_style = s.get("visual_style") or s.get("raw_visual_style") or {}
                transition = visual_style.get("transition")
                if transition in {"dissolve", "crossfade", "xfade"}:
                    sl["transition"] = transition
                    sl["transition_duration"] = float(visual_style.get("transition_duration") or 0.5)
            if reason_str:
                sl.setdefault("shot_reason", reason_str)
                sl.setdefault("reason", reason_str)
            plan.append(sl)
        per_seg.append(entry)
        for m in msgs:
            vp(m)
    # 4) render(audio_role:keep_audio 段保留原音 + 音樂墊底)
    pending_visual_review = [entry for entry in per_seg if entry.get("pending_visual_review")]
    if pending_visual_review:
        from .visual_review import write_request
        write_request(pending_visual_review, os.path.join(mat_dir, "visual_review_request.json"))

    from .edit_artifacts import snap_render_plan_to_motion  # noqa: PLC0415
    plan = snap_render_plan_to_motion(plan)

    if not skip_render and not pending_visual_review:
        render_mv_audio(plan, music_path, out_path, mat_dir=mat_dir, burn_text=burn_text)
    elif skip_render:
        vp("[mv_cut] skip_render is True. Skipping render_mv_audio.")
    else:
        vp("[mv_cut] awaiting visual review. Skipping render_mv_audio.")
    # 5) 寫 state.json 給 dashboard(node-timeline 可視化:SPEC+選段+缺口)
    try:
        build_mv_state(script, per_seg, out_path, music_path=music_path, plan=plan)
    except Exception as _e:
        vp(f"[state] build_mv_state failed (non-fatal): {_e}")
    return {"out": out_path, "segments": per_seg, "cuts": len(plan), "plan": plan,
            "awaiting_visual_review": bool(pending_visual_review)}


def _srt_ts(t):
    h = int(t // 3600); m = int((t % 3600) // 60); s = t % 60
    return f"{h:02d}:{m:02d}:{s:06.3f}".replace(".", ",")


# ASR 模型可調(roadmap:換大模型提升品質)。預設 small(CPU 友善);
# 升級 `export MV_ASR_MODEL=medium`(或 large-v3,中文演講字幕更準,較慢)。
_ASR_MODEL = os.environ.get("MV_ASR_MODEL", "small")
_WHISPER = {}   # model_size → WhisperModel(換模型也能切)


def _asr_srt(clip, out_srt, model_size=None, lang="zh"):
    """(I/O) faster-whisper 轉錄 clip 原音 → SRT(時間軸相對 clip)。回 srt 或 None。
    model_size 預設讀 MV_ASR_MODEL 環境變數(預設 small)。"""
    from faster_whisper import WhisperModel  # noqa: PLC0415 — lazy
    model_size = model_size or _ASR_MODEL
    if model_size not in _WHISPER:
        _WHISPER[model_size] = WhisperModel(model_size, device="cpu", compute_type="int8")
    model = _WHISPER[model_size]
    try:
        segs, _info = model.transcribe(clip, language=lang, vad_filter=True)
    except Exception:
        return None
    lines, i = [], 1
    for s in segs:
        txt = (s.text or "").strip()
        if txt:
            lines.append(f"{i}\n{_srt_ts(s.start)} --> {_srt_ts(s.end)}\n{txt}\n")
            i += 1
    if not lines:
        return None
    with open(out_srt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_srt


def _burn_asr_subtitle(seg_mp4, mat_dir, idx):
    """(I/O) 對講話段 clip 跑 ASR → 燒演講字幕(CJK)。回 subbed 路徑或 None。"""
    srt = os.path.join(mat_dir, f"asr_{idx}.srt")
    if not _asr_srt(seg_mp4, srt):
        return None
    out = os.path.join(mat_dir, f"mvseg_{idx:03d}_sub.mp4")
    srt_escaped = srt.replace("\\", "\\\\").replace(":", "\\:")
    vf = f"subtitles='{srt_escaped}'"
    if _CJK_FONT:
        font_dir = os.path.dirname(_CJK_FONT).replace("\\", "/").replace(":", "\\:")
        vf += (f":fontsdir='{font_dir}':force_style="
               f"'FontName={os.path.splitext(os.path.basename(_CJK_FONT))[0]},"
               f"FontSize=20,Bold=1,Outline=2,Shadow=1,MarginV=60'")
    r = subprocess.run([FFMPEG, "-y", "-i", seg_mp4, "-vf", vf, "-c:v", "libx264",
                        "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "copy", out], capture_output=True, timeout=240)
    return out if (r.returncode == 0 and os.path.exists(out)) else None


def audio_qa(segments):
    """純函式:MV 音訊搭配 QA(verify 的音訊維度,roadmap #6)。
    檢查原音/音樂編排一致性——抓「該保留原音卻沒保留→被音樂蓋掉」這類 garbage-in。
    回 {dimension, score, issues}。"""
    issues = []
    for s in segments or []:
        n = s.get("segment")
        role = s.get("audio_role")
        keeps = bool(s.get("hold") or s.get("keep_audio") or role in ("duck", "diegetic"))
        if s.get("subtitle") == "auto" and not keeps:
            issues.append({"segment": n, "level": "error",
                           "message": "subtitle:auto(有人講話要字幕)但未保留原音"
                                      "(設 audio_role=duck/diegetic 或 keep_audio)→ 字幕沒聲源、音樂會蓋過"})
        if role == "diegetic" and not keeps:
            issues.append({"segment": n, "level": "error",
                           "message": "diegetic(原音即高潮:隊呼/掌聲)卻沒保留原音"})
    errors = [i for i in issues if i["level"] == "error"]
    return {"dimension": "audio_pairing", "score": max(0, 100 - 25 * len(errors)),
            "issues": issues}


def build_mv_state(script, per_seg, out_path, music_path=None, plan=None):
    """把 MV 段落寫成 dashboard 認得的 state.json(放在 out_path 同目錄)。
    純函式 → state dict;附帶寫檔。每段帶 SPEC(visual_desc/layout/must_include/audio_role)
    + BUILD(選了哪支 clip/幾 slot/時長)+ 時間軸(start/dur)+ status(done/blocked)+ gap→blocking,
    讓 dashboard node-timeline 可視化(SPEC→BUILD→VERIFY 三層 + 段落時間)。"""
    import datetime
    segments, blocking, review_points = [], [], []
    sscript = script.get("segments", [])
    _aq = audio_qa(sscript)   # 音訊搭配 QA(verify 音訊維度)
    # 由 plan slots 推每段時間軸(start/dur)+ BUILD(選了哪支 clip)。plan 依出片順序排。
    seg_slots = {}  # segment → {"dur":float, "n":int, "clips":[basename...]}
    cursor = {}     # segment → start(累進,依 plan 出現順序)
    running = 0.0
    for sl in (plan or []):
        sid = sl.get("segment")
        if sid not in cursor:
            cursor[sid] = running
        ent = seg_slots.setdefault(sid, {"dur": 0.0, "n": 0, "clips": []})
        ent["dur"] += sl.get("extract_dur") or 0.0
        ent["n"] += 1
        bn = os.path.basename(sl.get("source") or "")
        if bn and bn not in ent["clips"]:
            ent["clips"].append(bn)
        running += sl.get("extract_dur") or 0.0
    for ps in per_seg:
        sid = ps.get("segment")
        s = next((x for x in sscript if x.get("segment") == sid), {})
        picked = ps.get("picked_scores") or []
        pending_visual_review = bool(ps.get("pending_visual_review"))
        gap = not pending_visual_review and ((len(picked) == 0) or picked == [GAP])
        slot = seg_slots.get(sid, {})
        segments.append({
            "segment": sid, "title": (ps.get("visual_desc") or "")[:30],
            "kind": s.get("kind") or ps.get("source") or "mv",
            "source": ps.get("source") or s.get("source", "local"),
            "provider": ps.get("provider"),
            "layout": s.get("layout"),
            "status": "pending_review" if pending_visual_review else ("blocked" if gap else "done"),
            "score": None if gap else len([x for x in picked if x not in (GAP, "stock")]) or None,
            "label": s.get("label"), "name_super": s.get("name_super"),
            "audio_role": s.get("audio_role"), "subtitle": s.get("subtitle"),
            "narrative": s.get("narrative"),
            "visual_desc": ps.get("visual_desc"),
            "must_include": s.get("must_include"),
            # BUILD 層:選了哪支原片(basename)+ 切幾 slot
            "picked_clips": slot.get("clips") or None,
            "n_slots": slot.get("n") or None,
            # 時間軸:段落 start/dur(秒)讓 node-timeline 可比例排列
            "start": round(cursor[sid], 2) if sid in cursor else None,
            "dur": round(slot.get("dur", 0.0), 2) if slot.get("dur") else None,
            "fix_class": "material" if gap else None,
            "fix_target": FIX_TARGET["material"] if gap else None,
        })
        if gap:
            mi = s.get("must_include")
            desc = (ps.get("visual_desc") or "")[:18]
            if mi:
                reason = f"必放『{mi}』無素材(must_include unfilled)"
            elif s.get("media") == "photo" or s.get("kind") in ("opening", "closing"):
                reason = f"無照片/素材對應「{desc}」(bookend,最重要)"
            else:
                reason = f"無素材對應「{desc}」"
            blocking.append({"segment": sid, "reason": reason})
        # 高權重 bookend / needs_review → 列入「建議人工複核」(roadmap:開場收尾一定複核)
        if s.get("kind") in ("opening", "closing", "title"):
            review_points.append({"segment": sid,
                                  "reason": "開場/收尾/字卡=高權重 slot,建議人工複核選段"})
        elif s.get("needs_review"):
            review_points.append({"segment": sid, "reason": "劇本標記 needs_review"})
    state = {
        "schema_version": 1, "mode": "mv",
        "created_at": datetime.datetime.now().isoformat(timespec="seconds"),
        "style": script.get("style"), "bgm": (script.get("music") or {}).get("brief"),
        "total_dur": round(running, 2) if plan else None,
        "final": out_path if os.path.exists(out_path) else None,
        "pass": not blocking, "attempts_used": 0,
        "qa": {"score": None, "content_alignment": None,
               "audio_pairing": _aq["score"], "audio_issues": _aq["issues"]},
        "stages": [{"name": n, "status": "done"} for n in
                   ("music", "match", "render")],
        "segments": segments, "blocking": blocking, "review_points": review_points,
        "gate_review": None,
        "next_action": ("await_visual_review" if any(
            ps.get("pending_visual_review") for ps in per_seg
        ) else ("await_material" if blocking else None)),
    }
    sp = os.path.join(os.path.dirname(out_path) or ".", "state.json")
    with open(sp, "w", encoding="utf-8") as f:
        import json as _json
        _json.dump(state, f, ensure_ascii=False, indent=2)
    return state


def mv_chain(script, material_db, out_path, music_path=None, mat_dir=None, verbose=True,
             skip_render=False, target_sec=None, burn_text=True, visual_judge="ollama"):
    """單一入口(roadmap #0 接線):material_db × 劇本 → match-mv → render。
    把 curator 理解(caption)+ 比對 + 渲染串成一條;render 吃 match 結果,不 live 重評。
    前置:material_db 須先 `ingest-meta` + `caption-meta`。stock 段仍由 run_mv 抓 Pexels。"""
    import json as _json
    import video_tools  # noqa: PLC0415
    mat_dir = mat_dir or resolve_temp_dir()
    if isinstance(material_db, str):
        with open(material_db, encoding="utf-8") as f:
            material_db = _json.load(f)
    segs = script.get("segments") or []
    matched = video_tools.match_script_to_material(segs, material_db.get("files", []))
    if verbose:
        for as_ in matched["assignments"]:
            tag = GAP if as_["gap"] else f"{as_['picks'][0]['score']}"
            print(f"  [match] seg{as_['segment']} [{tag}] {as_['visual_desc'][:16]}")
    res = run_mv(script, None, out_path, music_path=music_path,
                 clip_list=matched, mat_dir=mat_dir, verbose=verbose, skip_render=skip_render,
                 target_sec=target_sec, burn_text=burn_text, visual_judge=visual_judge)
    res["match"] = matched
    return res


def _mv_music_mix(have_keep_audio, music_vol=0.7):
    """純函式:回 (filter_complex|None, audio_map)。audio_role 真混音(取代 v0 固定低音量):
    - 有原音段(duck/diegetic:致詞/隊呼/掌聲)→ `sidechaincompress` 讓音樂在原音出現時
      自動讓位(原音為主、音樂墊底),原音靜默處音樂自動回到 music_vol。
    - 全 montage(無原音)→ 音樂直接當主音軌(全音量)。
    輸入約定:input0=拼好的 AV、input1=音樂。"""
    if have_keep_audio:
        fc = ("[0:a]asplit=2[a0][ak];"
              f"[1:a]volume={music_vol}[m];"
              "[m][ak]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=400[md];"
              "[a0][md]amix=inputs=2:duration=first:dropout_transition=0[a]")
        return fc, "[a]"
    return None, "1:a:0"   # 純 montage:音樂即主音軌


def _build_transition_filter(plan):
    """Build a mixed direct-cut/xfade graph from contiguous segment groups."""
    if not plan:
        return "", None, None
    parts = []
    for idx in range(len(plan)):
        parts.extend([
            f"[{idx}:v]settb=AVTB,setpts=PTS-STARTPTS[v{idx}]",
            f"[{idx}:a]aresample=44100,asetpts=PTS-STARTPTS[a{idx}]",
        ])

    groups = []
    for idx, slot in enumerate(plan):
        if not groups or groups[-1]["segment"] != slot.get("segment"):
            groups.append({
                "segment": slot.get("segment"),
                "indices": [idx],
                "duration": float(slot.get("extract_dur") or 0.0),
                "transition": slot.get("transition"),
                "transition_duration": float(slot.get("transition_duration") or 0.5),
            })
        else:
            groups[-1]["indices"].append(idx)
            groups[-1]["duration"] += float(slot.get("extract_dur") or 0.0)

    for group_idx, group in enumerate(groups):
        indices = group["indices"]
        if len(indices) == 1:
            group["video_label"] = f"[v{indices[0]}]"
            group["audio_label"] = f"[a{indices[0]}]"
            continue
        video_label = f"[vg{group_idx}]"
        audio_label = f"[ag{group_idx}]"
        parts.append(
            "".join(f"[v{idx}][a{idx}]" for idx in indices)
            + f"concat=n={len(indices)}:v=1:a=1{video_label}{audio_label}"
        )
        group["video_label"] = video_label
        group["audio_label"] = audio_label

    current_v = groups[0]["video_label"]
    current_a = groups[0]["audio_label"]
    current_duration = groups[0]["duration"]
    for group_idx, group in enumerate(groups[1:], start=1):
        next_v = group["video_label"]
        next_a = group["audio_label"]
        out_v = f"[vt{group_idx}]"
        out_a = f"[at{group_idx}]"
        if group.get("transition") in {"dissolve", "crossfade", "xfade"}:
            duration = min(group["transition_duration"], current_duration, group["duration"])
            offset = max(0.0, current_duration - duration)
            parts.append(
                f"{current_v}{next_v}xfade=transition=fade:duration={duration:.3f}:"
                f"offset={offset:.3f}{out_v}"
            )
            parts.append(f"{current_a}{next_a}acrossfade=d={duration:.3f}{out_a}")
            current_duration += group["duration"] - duration
        else:
            parts.append(f"{current_v}{next_v}concat=n=2:v=1:a=0{out_v}")
            parts.append(f"{current_a}{next_a}concat=n=2:v=0:a=1{out_a}")
            current_duration += group["duration"]
        current_v, current_a = out_v, out_a
    return ";".join(parts), current_v, current_a


def _render_segment_sequence(segs, plan, output_path):
    """Render segment files with explicit transitions, otherwise return False."""
    if not any(slot.get("transition") in {"dissolve", "crossfade", "xfade"} for slot in plan):
        return False
    graph, video_label, audio_label = _build_transition_filter(plan)
    command = [FFMPEG, "-y"]
    for seg in segs:
        command += ["-i", seg]
    command += [
        "-filter_complex", graph,
        "-map", video_label,
        "-map", audio_label,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
        "-c:a", "aac", output_path,
    ]
    result = subprocess.run(command, capture_output=True, timeout=600)
    if result.returncode != 0 or not os.path.exists(output_path):
        stderr = result.stderr.decode(errors="ignore") if isinstance(result.stderr, bytes) else result.stderr
        raise ToolError(f"render_mv_audio: xfade sequence failed: {stderr[-1200:]}")
    return True


def _has_audio_stream(path):
    from .vt_core import FFPROBE

    result = subprocess.run([
        FFPROBE, "-v", "error", "-select_streams", "a:0",
        "-show_entries", "stream=index", "-of", "csv=p=0", path,
    ], capture_output=True, text=True)
    return result.returncode == 0 and bool(result.stdout.strip())


def render_mv_audio(plan, music_path, out_path, mat_dir=None, music_vol=0.7, burn_text=True):
    """(I/O) render plan → 對拍/長段拼接 + audio_role 真混音。
    keep_audio 段(duck/diegetic)保留原音、其餘補靜音;末段用 sidechain ducking
    讓音樂在原音(致詞/隊呼)時讓位(見 `_mv_music_mix`)。"""
    mat_dir = mat_dir or resolve_temp_dir()
    segs = []
    for p in plan:
        seg = os.path.join(mat_dir, f"mvseg_{p['slot_index']:03d}.mp4")
        text_filter = _drawtext_chain(p.get("text"), mat_dir, p["slot_index"]) if burn_text else ""
        vf = _video_vf(p.get("crop_center")) + text_filter
        if p.get("is_photo"):
            # 照片→still 影片片段:loop 1 張 + kenburns 緩推 + 靜音(照片無原音)。
            # ⚠️ -t 必須放在 filter 之後當「輸出」上限(放 -i 前會與 zoompan d= 相乘爆長)。
            pvf = _photo_vf(
                p["extract_dur"],
                kenburns=p.get("kenburns", True),
                treatment=p.get("still_treatment"),
            ) \
                + text_filter
            cmd = [FFMPEG, "-y", "-loop", "1", "-i", p["source"],
                   "-f", "lavfi", "-t", f"{p['extract_dur']:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
                   "-vf", pvf, "-t", f"{p['extract_dur']:.3f}", "-r", "30",
                   "-map", "0:v:0", "-map", "1:a:0",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-ar", "44100", "-ac", "2", seg]
        elif p.get("keep_audio"):
            actual_dur = 0.0
            has_audio = _has_audio_stream(p["source"])
            if has_audio:
                try:
                    from .vt_core import _audio_duration
                    actual_dur = _audio_duration(p["source"])
                except Exception:
                    pass
            if not has_audio:
                cmd = [FFMPEG, "-y", "-ss", f"{p['extract_start']:.3f}", "-i", p["source"],
                       "-f", "lavfi", "-t", f"{p['extract_dur']:.3f}", "-i",
                       "anullsrc=r=44100:cl=stereo",
                       "-t", f"{p['extract_dur']:.3f}", "-vf", vf,
                       "-map", "0:v:0", "-map", "1:a:0",
                       "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                       "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", seg]
            else:
                rem_dur = max(0.1, actual_dur - p["extract_start"])
                expected = p["extract_dur"]
                input_opts = []
                if rem_dur < expected:
                    import math
                    loops = int(math.ceil(expected / rem_dur)) - 1
                    if loops > 0:
                        input_opts += ["-stream_loop", str(loops)]

                cmd = [FFMPEG, "-y"] + input_opts + [
                    "-ss", f"{p['extract_start']:.3f}", "-i", p["source"],
                    "-t", f"{p['extract_dur']:.3f}", "-vf", vf,
                    "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-ar", "44100", "-ac", "2", seg,
                ]
        else:
            actual_dur = 0.0
            try:
                from .vt_core import _audio_duration
                actual_dur = _audio_duration(p["source"])
            except Exception:
                pass
            rem_dur = max(0.1, actual_dur - p["extract_start"])
            expected = p["extract_dur"]
            input_opts = []
            if actual_dur > 0 and rem_dur < expected:
                import math
                loops = int(math.ceil(expected / rem_dur)) - 1
                if loops > 0:
                    input_opts += ["-stream_loop", str(loops)]

            cmd = [FFMPEG, "-y"] + input_opts + ["-ss", f"{p['extract_start']:.3f}", "-i", p["source"],
                   "-f", "lavfi", "-t", f"{p['extract_dur']:.3f}", "-i", "anullsrc=r=44100:cl=stereo",
                   "-t", f"{p['extract_dur']:.3f}", "-vf", vf, "-map", "0:v:0", "-map", "1:a:0",
                   "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                   "-c:a", "aac", "-ar", "44100", "-ac", "2", seg]
        r = subprocess.run(cmd, capture_output=True, timeout=180)
        if r.returncode != 0:
            print(f"[error] ffmpeg failed for slot {p['slot_index']}. Cmd: {' '.join(cmd)}", file=sys.stderr)
            print(f"[stderr]: {r.stderr.decode(errors='ignore')}", file=sys.stderr)
        if r.returncode == 0 and os.path.exists(seg):
            # 講話段(subtitle:"auto")→ ASR 轉錄原音 + 燒演講字幕
            if (p.get("text") or {}).get("subtitle") == "auto" and p.get("keep_audio"):
                subbed = _burn_asr_subtitle(seg, mat_dir, p["slot_index"])
                if subbed:
                    seg = subbed
            segs.append(seg)
    if not segs:
        raise ToolError("render_mv_audio: no segments rendered")
    listf = os.path.normpath(os.path.join(mat_dir, "mv_concat.txt"))
    with open(listf, "w") as f:
        for s in segs:
            # ⚠️ 用絕對路徑:ffmpeg concat 把相對 entry 解析成「相對 list 檔所在目錄」,
            # mat_dir 是相對路徑時會變成 mat_dir/mat_dir/... 雙重前綴而開不了檔。
            clean_path = os.path.abspath(s).replace('\\', '/')
            f.write(f"file '{clean_path}'\n")
    av = os.path.join(mat_dir, "mv_av.mp4")
    if not _render_segment_sequence(segs, plan, av):
        subprocess.run([FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", listf,
                        "-c:v", "libx264", "-preset", "medium", "-crf", "20", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", av], capture_output=True, timeout=600)
    have_keep = any(p.get("keep_audio") for p in plan)
    fc, amap = _mv_music_mix(have_keep, music_vol=music_vol)
    cmd = [FFMPEG, "-y", "-i", av, "-i", music_path]
    if fc:
        cmd += ["-filter_complex", fc]
    cmd += ["-map", "0:v:0", "-map", amap, "-c:v", "copy", "-c:a", "aac", "-shortest", out_path]
    subprocess.run(cmd, capture_output=True, timeout=180)
    return out_path


# ── MV 劇本 schema（v0）+ validate ───────────────────────────────────────────
# 統一段落模型的 MV 模式。MVP:只收已討論定案的欄位,實測後再擴。
MV_KINDS = {"opening", "closing", "title", "montage", "music"}
MV_LAYOUTS = {"montage", "collage", "framed"}
MV_PACE = {"fast", "hold"}
MV_AUDIO_ROLES = {"music", "duck", "diegetic"}   # music=只音樂 / duck=原音+壓低音樂 / diegetic=原音為主


def validate_mv_script(script):
    """純函式:驗 MV 劇本 v0 schema。回傳 {status, can_run, errors, warnings, issues}。
    結訓核心:必放段(致詞/隊呼)應 hold+keep_audio,開場/收尾應 needs_review。"""
    issues = []
    def add(seg, field, level, msg):
        issues.append({"segment": seg, "field": field, "level": level, "message": msg})

    if not isinstance(script, dict):
        add(0, "root", "error", "MV 劇本應是 {style, music, segments} 物件")
        return _mv_result(issues)

    if script.get("style") != "mv":
        add(0, "style", "warning", "MV 模式建議 style='mv'")
    music = script.get("music")
    if isinstance(music, dict) and not (music.get("brief") or music.get("query")):
        add(0, "music", "error", "music 需要 brief 或 query(導演音樂方向)")

    segs = script.get("segments") or []
    if len(segs) < 2:
        add(0, "segments", "error", "至少 2 段")

    for s in segs:
        n = s.get("segment", "?")
        kind = s.get("kind")
        if kind and kind not in MV_KINDS:
            add(n, "kind", "error", f"未知 kind '{kind}'（可:{'/'.join(sorted(MV_KINDS))}）")
        if kind not in ("title", "music") and not s.get("visual_desc"):
            add(n, "visual_desc", "error", "MV 段需要 visual_desc（選段靶）")
        if s.get("layout") and s["layout"] not in MV_LAYOUTS:
            add(n, "layout", "error", f"未知 layout '{s['layout']}'")
        if s.get("pace") and s["pace"] not in MV_PACE:
            add(n, "pace", "error", f"未知 pace '{s['pace']}'（可:{'/'.join(sorted(MV_PACE))}）")
        ar = s.get("audio_role")
        if ar and ar not in MV_AUDIO_ROLES:
            add(n, "audio_role", "error", f"未知 audio_role '{ar}'（可:{'/'.join(sorted(MV_AUDIO_ROLES))}）")
        ns = s.get("name_super")
        if ns is not None and not (isinstance(ns, dict) and ns.get("text")):
            add(n, "name_super", "error", "name_super 需 {text, ...}")
        # 螢幕文字層(編劇):label 標籤 / narrative 敘事字卡 / subtitle 演講字幕(可 'auto'→ASR)
        for tf in ("label", "narrative", "subtitle"):
            if s.get(tf) is not None and not isinstance(s[tf], str):
                add(n, tf, "error", f"{tf} 應是字串")
        # 結訓慣例 warnings
        if kind in ("opening", "closing") and not s.get("needs_review"):
            add(n, "needs_review", "warning", f"{kind} 是高權重段,建議 needs_review=true（人工複核）")
        if s.get("must_include") and not (s.get("keep_audio") or s.get("hold")):
            add(n, "keep_audio", "warning", "必放段(常為致詞/隊呼)通常要 keep_audio/hold 保留原音")
        if s.get("audio_role") in ("duck", "diegetic") and not s.get("subtitle"):
            add(n, "subtitle", "warning", "講話/原音段建議加 subtitle 演講字幕（可 'auto' 走 ASR）")
    return _mv_result(issues)


def _mv_result(issues):
    errors = sum(1 for i in issues if i["level"] == "error")
    warnings = sum(1 for i in issues if i["level"] == "warning")
    return {"status": "error" if errors else ("warning" if warnings else "ok"),
            "can_run": errors == 0, "errors": errors, "warnings": warnings,
            "issues": issues}


def detect_beats(audio_path):
    """(I/O) Detect tempo + beat timestamps from an audio file via librosa.
    Returns (tempo_bpm: float, beat_times: list[float] in seconds).
    librosa imported lazily so the pure functions above work without it."""
    import librosa  # noqa: PLC0415 — lazy by design
    y, sr = librosa.load(audio_path, mono=True)
    tempo, beat_frames = librosa.beat.beat_track(y=y, sr=sr)
    beat_times = librosa.frames_to_time(beat_frames, sr=sr)
    try:
        import numpy as np
        tempo_val = float(np.atleast_1d(tempo)[0])
    except Exception:
        tempo_val = float(tempo)
    return tempo_val, [float(t) for t in beat_times]


if __name__ == "__main__":
    import json
    import sys
    if len(sys.argv) < 2:
        print("usage: python mv_cut.py <audio> [every_n_beats] [min_seg]\n"
              "       python mv_cut.py validate <mv_script.json>", file=sys.stderr)
        sys.exit(1)
    if sys.argv[1] == "validate":
        with open(sys.argv[2], encoding="utf-8") as f:
            res = validate_mv_script(json.load(f))
        print(json.dumps(res, ensure_ascii=False, indent=2))
        sys.exit(0 if res["can_run"] else 1)
    tempo, beats = detect_beats(sys.argv[1])
    every = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    min_seg = float(sys.argv[3]) if len(sys.argv) > 3 else 1.0
    grid = beats_to_cut_grid(beats, every_n_beats=every, min_seg=min_seg)
    print(json.dumps({
        "tempo_bpm": round(tempo, 1), "beats": len(beats),
        "every_n_beats": every, "segments": len(grid),
        "durations": grid_durations(grid),
        "grid": [[round(s, 3), round(e, 3)] for s, e in grid],
    }, ensure_ascii=False))
