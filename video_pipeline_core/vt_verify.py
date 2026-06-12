"""vt_verify.py — VERIFY(品管:5 維技術 QA + 內容對齊),從 video_tools 解耦。
共用原語取自 vt_core,避免循環匯入。"""
import os
import sys
import json
import subprocess
from .vt_core import FFMPEG, FFPROBE, run, ToolError, _audio_duration  # noqa: F401

# ── verify: 品管 ──────────────────────────────────────────────────────────

def _verify_script_coverage(script, edit_log):
    """維度1: 每個 script segment 是否都有對應的影片段落"""
    script_segs = {s['segment'] for s in script if 'segment' in s}

    segs = []
    if edit_log and isinstance(edit_log, dict):
        if "clips" in edit_log:
            segs = edit_log["clips"]
        else:
            segs = edit_log.get("segments", [])
    elif isinstance(edit_log, list):
        segs = edit_log

    edit_segs = {s['segment'] for s in segs if isinstance(s, dict) and 'segment' in s}
    missing = script_segs - edit_segs
    score = 100 if not missing else int(100 * (len(script_segs) - len(missing)) / len(script_segs))
    return {
        "score": score,
        "weight": 0.25,
        "note": "all segments present" if not missing else f"missing segments: {sorted(missing)}",
        "fix_target": None if not missing else "editor",
    }


def _verify_duration_fit(timing, edit_log, video_path=None, threshold_ms=300):
    """維度2: 影片段落時長 vs 預期時長，差值 < threshold"""
    tts_durs = {}
    if timing and isinstance(timing, dict) and "segments" in timing:
        tts_durs = {s['segment']: s['duration_sec'] for s in timing['segments']}

    segs = []
    if edit_log and isinstance(edit_log, dict):
        if "clips" in edit_log:
            segs = edit_log["clips"]
        else:
            segs = edit_log.get("segments", [])

    issues = []
    total = 0
    passed = 0
    for s in segs:
        seg = s.get('segment')
        if seg is None:
            continue

        expected = tts_durs.get(seg)
        if expected is None:
            expected = s.get('target_duration_sec') or s.get('duration_sec') or s.get('tts_target_sec')
        if expected is None:
            continue

        total += 1

        # 嘗試探測實際生成的段落片段時長
        actual = None
        if video_path:
            idx = s.get('shot_idx') if s.get('shot_idx') is not None else (seg - 1)
            seg_file = os.path.join(os.path.dirname(video_path), f"mvseg_{idx:03d}.mp4")
            if os.path.exists(seg_file):
                try:
                    actual = _audio_duration(seg_file)
                except Exception:
                    pass

        if actual is None:
            actual = s.get('actual_sec') or s.get('duration_sec') or 0

        diff_ms = abs(actual - expected) * 1000
        if diff_ms < threshold_ms:
            passed += 1
        else:
            issues.append({"segment": seg, "diff_ms": round(diff_ms, 1)})

    # 全體成片總時長驗證
    if video_path and os.path.exists(video_path):
        try:
            actual_total = _audio_duration(video_path)
            timeline_ends = [
                float(s["timeline_out_sec"])
                for s in segs if s.get("timeline_out_sec") is not None
            ]
            expected_total = max(timeline_ends) if timeline_ends else sum(
                tts_durs.get(s['segment'], s.get('target_duration_sec') or s.get('duration_sec') or s.get('tts_target_sec') or 0)
                for s in segs if s.get('segment') is not None
            )
            diff_total_ms = abs(actual_total - expected_total) * 1000
            if diff_total_ms >= threshold_ms:
                issues.append({
                    "segment": "final_video",
                    "note": f"實際成片時長 ({actual_total:.3f}s) 與預期總時長 ({expected_total:.3f}s) 差值 ({diff_total_ms:.1f}ms) 超過閾值 ({threshold_ms}ms)"
                })
                passed = max(0, passed - 1)
                total = max(1, total)
        except Exception:
            pass

    score = int(100 * passed / total) if total else 0
    return {
        "score": score,
        "weight": 0.25,
        "note": f"{passed}/{total} segments within {threshold_ms}ms"
                + (f", issues: {issues}" if issues else ""),
        "fix_target": None if not issues else "editor",
        "issues": issues,
    }


def _verify_subtitle_accuracy(script, srt_path):
    """維度3: SRT 內容 vs script.subtitle 字元重疊率"""
    # 提取所有 subtitle / text (字幕) 欄位
    texts = []
    for s in script:
        for field in ('subtitle', 'text'):
            val = s.get(field)
            if val and isinstance(val, str):
                texts.append(val)
    script_combined = ''.join(texts)

    import string
    punct = '，。；！？、 ' + string.punctuation

    if not os.path.exists(srt_path):
        import re
        script_clean = ''.join(c for c in script_combined if c not in punct)
        if not script_clean:
            return {"score": 100, "weight": 0.20, "note": "no subtitles expected and srt not found", "fix_target": None}
        return {"score": 0, "weight": 0.20, "note": "srt not found", "fix_target": "subtitle"}

    with open(srt_path, encoding='utf-8') as f:
        srt_text = f.read()
    # 取 SRT 純文字（去掉序號和時間軸）
    srt_lines = []
    for line in srt_text.split('\n'):
        line = line.strip()
        if not line: continue
        if line.isdigit(): continue
        if '-->' in line: continue
        srt_lines.append(line)
    srt_combined = ''.join(srt_lines)

    # 移除 [Music] 等無意義的標記再比對
    import re
    srt_clean_no_brackets = re.sub(r'\[[^\]]*\]', '', srt_combined)

    # 移除空白和標點以求字元層級比對
    srt_clean = ''.join(c for c in srt_clean_no_brackets if c not in punct)
    script_clean = ''.join(c for c in script_combined if c not in punct)

    if not script_clean:
        if not srt_clean:
            return {
                "score": 100,
                "weight": 0.20,
                "note": "no subtitles expected and none found",
                "fix_target": None
            }
        else:
            return {
                "score": 0,
                "weight": 0.20,
                "note": f"no subtitles expected but found: {srt_clean[:50]}",
                "fix_target": "subtitle"
            }

    # 計算相似度：使用 difflib.SequenceMatcher (編輯距離比對)
    from difflib import SequenceMatcher
    ratio = SequenceMatcher(None, script_clean, srt_clean).ratio()
    score = min(100, int(ratio * 100))
    return {
        "score": score,
        "weight": 0.20,
        "note": f"similarity ratio: {ratio*100:.1f}%",
        "fix_target": None if score >= 90 else "subtitle",
    }


def _verify_audio_levels(video_path):
    """維度4: 音量是否在合理範圍 (-30dB ~ -6dB peak, -25dB ~ -14dB mean)"""
    res = subprocess.run(
        [FFMPEG, '-i', video_path, '-af', 'volumedetect', '-f', 'null', '-'],
        capture_output=True, text=True
    )
    stderr = res.stderr
    import re
    mean_m = re.search(r'mean_volume:\s*(-?[\d.]+)\s*dB', stderr)
    max_m = re.search(r'max_volume:\s*(-?[\d.]+)\s*dB', stderr)
    if not mean_m or not max_m:
        return {"score": 0, "weight": 0.15, "note": "could not detect volume",
                "fix_target": "audio"}
    mean_db = float(mean_m.group(1))
    max_db = float(max_m.group(1))

    notes = []
    score = 100
    if max_db > -3:
        score -= 30; notes.append(f"max {max_db}dB too loud (>-3 = 爆音風險)")
    elif max_db > -6:
        score -= 10; notes.append(f"max {max_db}dB 接近爆音")
    if mean_db < -30:
        score -= 30; notes.append(f"mean {mean_db}dB 太小聲")
    elif mean_db > -12:
        score -= 20; notes.append(f"mean {mean_db}dB 偏大聲")
    if not notes:
        notes = [f"mean {mean_db}dB, max {max_db}dB（合規）"]
    return {
        "score": max(0, score),
        "weight": 0.15,
        "note": "; ".join(notes),
        "fix_target": None if score >= 80 else "audio",
        "mean_db": mean_db, "max_db": max_db,
    }


def _verify_technical_quality(video_path, expected_w=1920, expected_h=1080, expected_fps=30):
    """維度5: 解析度、framerate、有音軌、有視軌、無黑幀"""
    res = subprocess.run([
        FFPROBE, '-v', 'error', '-show_entries',
        'stream=codec_type,codec_name,width,height,r_frame_rate',
        '-show_entries', 'format=duration',
        '-of', 'json', video_path
    ], capture_output=True, text=True)
    info = json.loads(res.stdout)
    streams = info.get('streams', [])
    has_v = any(s['codec_type'] == 'video' for s in streams)
    has_a = any(s['codec_type'] == 'audio' for s in streams)
    v = next((s for s in streams if s['codec_type'] == 'video'), None)

    notes = []
    score = 100
    if not has_v: score -= 50; notes.append("no video stream")
    if not has_a: score -= 30; notes.append("no audio stream")
    if v:
        w, h = v.get('width'), v.get('height')
        if (w, h) != (expected_w, expected_h):
            score -= 20; notes.append(f"resolution {w}x{h} (expected {expected_w}x{expected_h})")
        # framerate check
        fr = v.get('r_frame_rate', '0/1')
        try:
            num, den = fr.split('/')
            fps = float(num) / float(den)
            if abs(fps - expected_fps) > 1:
                score -= 10; notes.append(f"framerate {fps:.2f} (expected {expected_fps})")
        except (ValueError, ZeroDivisionError):
            pass
    if not notes:
        notes = [f"streams OK, {expected_w}x{expected_h} {expected_fps}fps"]
    return {
        "score": max(0, score),
        "weight": 0.15,
        "note": "; ".join(notes),
        "fix_target": None if score >= 80 else "editor",
    }


def cmd_verify(args):
    """VERIFY：對成片做 5 維度評分 + 路由修正指示"""
    for label, path in [("script", args.script), ("timing", args.timing),
                        ("edit-log", args.edit_log), ("srt", args.srt),
                        ("video", args.video)]:
        if not os.path.exists(path):
            raise ToolError(f"{label} file not found: {path}")

    with open(args.script, encoding="utf-8") as f: script = json.load(f)
    if isinstance(script, dict) and "segments" in script:
        script = script["segments"]
    with open(args.timing, encoding="utf-8") as f: timing = json.load(f)
    with open(args.edit_log, encoding="utf-8") as f: edit_log = json.load(f)

    # 嘗試載入 build_profile.json 取得預期解析度與影格率
    expected_w, expected_h, expected_fps = 1920, 1080, 30
    profile_path = None
    candidates = []
    if args.script:
        candidates.append(os.path.join(os.path.dirname(args.script), "build_profile.json"))
    if args.out:
        candidates.append(os.path.join(os.path.dirname(args.out), "build_profile.json"))
        candidates.append(os.path.join(args.out, "build_profile.json"))
    candidates.append("build_profile.json")

    for path_candidate in candidates:
        if path_candidate and os.path.exists(path_candidate):
            profile_path = path_candidate
            break

    if profile_path:
        try:
            with open(profile_path, encoding="utf-8") as f:
                profile_data = json.load(f)
                if isinstance(profile_data, dict):
                    if "target_width" in profile_data:
                        expected_w = int(profile_data["target_width"])
                    if "target_height" in profile_data:
                        expected_h = int(profile_data["target_height"])
                    if "target_fps" in profile_data:
                        expected_fps = int(profile_data["target_fps"])
        except Exception:
            pass

    dims = {
        "script_coverage":   _verify_script_coverage(script, edit_log),
        "duration_fit":      _verify_duration_fit(timing, edit_log, video_path=args.video),
        "subtitle_accuracy": _verify_subtitle_accuracy(script, args.srt),
        "audio_levels":      _verify_audio_levels(args.video),
        "technical_quality": _verify_technical_quality(args.video, expected_w, expected_h, expected_fps),
    }

    # 加權總分
    total_score = sum(d['score'] * d['weight'] for d in dims.values())

    # 列出需要修正的項目
    issues = []
    for name, d in dims.items():
        if d.get('fix_target') and d['score'] < 80:
            issues.append({
                "dimension": name,
                "score": d['score'],
                "detail": d['note'],
                "fix_target": d['fix_target'],
            })

    threshold = args.threshold if args.threshold else 80
    qa = {
        "video": args.video,
        "timestamp": _now_iso(),
        "score": round(total_score, 1),
        "pass": total_score >= threshold,
        "threshold": threshold,
        "dimensions": dims,
        "issues": issues,
    }
    out = args.out or "qa_report.json"
    with open(out, 'w', encoding='utf-8') as f:
        json.dump(qa, f, ensure_ascii=False, indent=2)

    # 螢幕摘要
    summary = {
        "status": "ok",
        "qa_report": out,
        "score": qa["score"],
        "pass": qa["pass"],
        "dimensions": {k: v['score'] for k, v in dims.items()},
        "issue_count": len(issues),
    }
    print(json.dumps(summary, ensure_ascii=False))


def _now_iso():
    from datetime import datetime
    return datetime.now().strftime('%Y-%m-%dT%H:%M:%S')
