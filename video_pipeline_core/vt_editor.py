"""vt_editor.py — 剪輯師(assemble + merge-final,檔案層級組裝),從 video_tools 解耦
(= editor skill)。共用原語取自 vt_core。"""
import os
import sys
import json
import subprocess
from .vt_core import FFMPEG, FFPROBE, run, ToolError, _audio_duration  # noqa: F401

# ── editor: 剪輯師指令 ────────────────────────────────────────────────────

def cmd_assemble(args):
    """剪輯師：依 TTS 時長剪每段素材 → 統一 1920x1080 → concat。

    輸入：
      clip_list.json   小編產出，每段含 file + cut_start_sec (+ optional cut_end_sec)
      tts_timing.json  音控師產出，提供每段目標時長

    輸出：rough_cut.mp4（無音軌，純視覺，segment 順序與 clip_list 一致）
    """
    if not os.path.exists(args.clips):
        raise ToolError(f"clip_list.json not found: {args.clips}")
    if not os.path.exists(args.timing):
        raise ToolError(f"tts_timing.json not found: {args.timing}")

    with open(args.clips, encoding="utf-8") as f:
        clips = json.load(f)
    with open(args.timing, encoding="utf-8") as f:
        timing = json.load(f)

    # 建立 segment → tts_duration 對照
    tts_durs = {s['segment']: s['duration_sec'] for s in timing.get('segments', [])}

    segs = clips.get('segments', [])
    if not segs:
        raise ToolError("clip_list.segments is empty")

    out = args.out or "rough_cut.mp4"
    tmpdir = os.path.dirname(os.path.abspath(out)) or "."
    workdir = os.path.join(tmpdir, ".assemble_tmp")
    os.makedirs(workdir, exist_ok=True)

    cut_files = []
    log_segments = []

    for s in segs:
        seg_num = s['segment']
        src = s['file']
        if not os.path.exists(src):
            raise ToolError(f"source file not found: {src}")
        if seg_num not in tts_durs:
            raise ToolError(f"segment {seg_num} not found in tts_timing")

        start = s.get('cut_start_sec', 0.0)
        tts_dur = tts_durs[seg_num]
        end = s.get('cut_end_sec')
        if end is None:
            end = start + tts_dur
        duration = end - start
        if duration <= 0:
            raise ToolError(f"segment {seg_num}: duration must be > 0")

        cut_path = os.path.join(workdir, f"seg{seg_num}_cut.mp4")
        # 用 -ss 在 -i 後（精確 seek）+ -t 控制長度，scale + pad 到 1920x1080，
        # 強制 30fps + setsar=1 避免 concat 時音視頻時間戳跑掉（坑 #5/#16）
        vf = (
            "scale=1920:1080:force_original_aspect_ratio=decrease,"
            "pad=1920:1080:(ow-iw)/2:(oh-ih)/2,"
            "setsar=1"
        )
        cmd = [
            FFMPEG, "-y",
            "-ss", str(start),
            "-i", src,
            "-t", str(duration),
            "-vf", vf,
            "-r", "30", "-vsync", "cfr",
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-an",  # 視覺無音軌，避免跟人聲打架
            cut_path,
        ]
        res = run(cmd)
        if res.returncode != 0:
            raise ToolError(f"cut seg{seg_num} failed: {res.stderr[:300]}")
        actual_dur = _audio_duration(cut_path)  # ffprobe 也可量影片時長
        cut_files.append(cut_path)
        log_segments.append({
            "segment": seg_num,
            "source": src,
            "cut_start_sec": start,
            "tts_target_sec": tts_dur,
            "actual_sec": round(actual_dur, 3),
            "duration_diff_ms": round((actual_dur - tts_dur) * 1000, 1),
        })

    # concat 所有段
    concat_list = os.path.join(workdir, "concat.txt")
    with open(concat_list, 'w', encoding="utf-8") as f:
        for cf in cut_files:
            f.write(f"file '{os.path.abspath(cf)}'\n")
    res = run([
        FFMPEG, "-y", "-f", "concat", "-safe", "0", "-i", concat_list,
        "-c", "copy", out
    ])
    if res.returncode != 0:
        raise ToolError(f"concat failed: {res.stderr[:300]}")

    total = _audio_duration(out)
    expected = sum(d['actual_sec'] for d in log_segments)

    # 寫 edit_log.json
    log_path = out.replace('.mp4', '_edit_log.json')
    with open(log_path, 'w', encoding="utf-8") as f:
        json.dump({
            "output": out,
            "total_duration_sec": round(total, 3),
            "segments": log_segments,
        }, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "status": "ok",
        "file": out,
        "edit_log": log_path,
        "segments": len(log_segments),
        "total_duration_sec": round(total, 3),
        "total_drift_ms": round((total - expected) * 1000, 1),
    }, ensure_ascii=False))


def cmd_merge_final(args):
    """剪輯師最終組合：把音軌 + 字幕套到無音軌的視覺上。

    輸入：
      --visual  rough_cut.mp4（assemble 的輸出，純視覺）
      --audio   final_audio.wav（音控師 mix-audio 的輸出）
      --subs    subtitles.srt（字幕師 srt 的輸出）

    輸出：final.mp4（完整成片）
    """
    for label, path in [("visual", args.visual), ("audio", args.audio), ("subs", args.subs)]:
        if not os.path.exists(path):
            raise ToolError(f"{label} file not found: {path}")

    out = args.out or "final.mp4"

    from pathlib import Path
    from .platform_tools import resolve_font
    font_path = resolve_font()
    if os.path.exists(font_path):
        with open(font_path, 'rb') as f:
            magic = f.read(4)
        if magic[:4] not in (b'OTTO', b'\x00\x01\x00\x00', b'true', b'ttcf'):
            raise ToolError(f"font is not valid TrueType: {font_path}")

    subs_path = str(Path(args.subs).resolve())
    subs_escaped = subs_path.replace("\\", "\\\\").replace(":", "\\:")
    font_dir = str(Path(font_path).parent).replace("\\", "/")
    font_name = Path(font_path).stem

    # D3 字幕美學：加粗 + 柔和投影提升質感與在雜亂畫面上的可讀性
    #   BackColour=&H80000000 = 50% 半透明黑投影；Shadow=1.5 給深度
    #   Outline 由 3 降 to 2（有投影分離，不需過重描邊）
    vf = (
        f"subtitles='{subs_escaped}':fontsdir='{font_dir}':"
        f"force_style='FontName={font_name},FontSize=38,Bold=1,"
        f"PrimaryColour=&H00FFFFFF,OutlineColour=&H00000000,BackColour=&H80000000,"
        f"BorderStyle=1,Outline=2,Shadow=1.5,Spacing=0.5,"
        f"Alignment=2,MarginV=90'"
    )

    cmd = [
        FFMPEG, "-y",
        "-i", args.visual,
        "-i", args.audio,
        "-map", "0:v:0", "-map", "1:a:0",
        "-vf", vf,
        "-c:v", "libx264", "-preset", "medium", "-crf", "23",
        "-c:a", "aac", "-b:a", "192k",
        "-r", "30", "-vsync", "cfr",
        "-ar", "48000", "-ac", "2",
        "-shortest",
        out,
    ]
    res = run(cmd)
    if res.returncode != 0:
        raise ToolError(f"merge-final failed: {res.stderr[:500]}")

    total = _audio_duration(out)
    print(json.dumps({
        "status": "ok",
        "file": out,
        "duration_sec": round(total, 3),
    }, ensure_ascii=False))
