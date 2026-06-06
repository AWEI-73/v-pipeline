"""vt_effects.py — 特效師(色彩分級/字卡/Ken Burns/拼貼/蒙太奇),從 video_tools 解耦。
共用原語取自 vt_core,避免循環匯入。"""
import os
import json
import random
import subprocess
import tempfile
import shutil
from .vt_core import FFMPEG, FFPROBE, run, ToolError, _audio_duration  # noqa: F401

# ── Ken Burns 照片動畫 ────────────────────────────────────────────────────

def cmd_kenburns(args):
    """把照片變成有 Ken Burns 慢推鏡的 1920x1080 影片"""
    if not os.path.exists(args.photo):
        raise ToolError(f"photo not found: {args.photo}")

    duration = args.duration
    direction = args.direction or "zoom-in"
    out = args.out or args.photo.rsplit('.', 1)[0] + "_kb.mp4"
    fps = 30
    total_frames = int(duration * fps)

    # 5 種預設動畫
    # 用 ffmpeg zoompan filter，s=1920x1080 (output size)
    # z = zoom factor (1.0 = 原始)
    # x, y = 中心點
    zoom_filters = {
        "zoom-in":   f"zoompan=z='min(zoom+0.0015,1.5)':d={total_frames}:s=1920x1080:fps={fps}",
        "zoom-out":  f"zoompan=z='if(eq(on,1),1.5,max(zoom-0.0015,1.0))':d={total_frames}:s=1920x1080:fps={fps}",
        "pan-left":  f"zoompan=z=1.3:x='if(eq(on,1),iw-iw/zoom,x-3)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}",
        "pan-right": f"zoompan=z=1.3:x='if(eq(on,1),0,x+3)':y='ih/2-(ih/zoom/2)':d={total_frames}:s=1920x1080:fps={fps}",
    }
    if direction == "random":
        import random
        direction = random.choice(list(zoom_filters.keys()))
    if direction not in zoom_filters:
        raise ToolError(f"unknown direction: {direction} (choose from zoom-in/zoom-out/pan-left/pan-right/random)")

    vf = zoom_filters[direction]
    cmd = [
        FFMPEG, "-y",
        "-loop", "1", "-i", args.photo,
        "-vf", vf,
        "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-r", str(fps),
        out
    ]
    res = run(cmd)
    if res.returncode != 0:
        raise ToolError(f"kenburns failed: {res.stderr[:400]}")

    actual = _audio_duration(out)
    print(json.dumps({
        "status": "ok",
        "file": out,
        "direction": direction,
        "target_duration_sec": duration,
        "actual_duration_sec": round(actual, 3),
    }, ensure_ascii=False))


# ── 特效師 (effects-director)：色彩分級 / 字卡 ──────────────────────────────

# 情境調色預設（保留 1920x1080 / 30fps / bt709 規格，不改時長）
GRADE_PRESETS = {
    "dusk":    "eq=contrast=1.05:saturation=1.18:brightness=0.01,colorbalance=rs=0.06:bs=-0.06:rm=0.04:bm=-0.04",
    "night":   "eq=contrast=1.10:saturation=0.95:brightness=-0.02,colorbalance=rs=-0.05:bs=0.07:bm=0.05",
    "fire":    "eq=contrast=1.12:saturation=1.28,colorbalance=rs=0.10:gs=0.02:bs=-0.10:rm=0.06:bm=-0.06",
    "warm":    "eq=contrast=1.05:saturation=1.15,colorbalance=rs=0.05:bs=-0.05",
    "cool":    "eq=contrast=1.08:saturation=1.00,colorbalance=bs=0.06:rs=-0.04",
    "neutral": "eq=contrast=1.03:saturation=1.05",
}

_FX_ENCODE = ["-c:v", "libx264", "-preset", "medium", "-crf", "20",
              "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709",
              "-color_primaries", "bt709", "-color_trc", "bt709", "-r", "30", "-an"]


def cmd_grade(args):
    """色彩分級：對影片套用情境調色（特效師）。保留規格與時長。"""
    if not os.path.exists(args.input):
        raise ToolError(f"input not found: {args.input}")
    preset = (args.preset or "neutral").lower()
    if preset not in GRADE_PRESETS:
        raise ToolError(f"unknown preset: {preset} (choose from {'/'.join(GRADE_PRESETS)})")
    out = args.out or args.input.rsplit('.', 1)[0] + "_grade.mp4"
    vf = GRADE_PRESETS[preset] + ",format=yuv420p"
    cmd = [FFMPEG, "-y", "-i", args.input, "-vf", vf, *_FX_ENCODE, out]
    res = run(cmd)
    if res.returncode != 0:
        raise ToolError(f"grade failed: {res.stderr[-400:]}")
    print(json.dumps({"status": "ok", "file": out, "preset": preset}, ensure_ascii=False))


def cmd_title_card(args):
    """字卡：在影片開頭疊加標題（淡入→hold→淡出），可選副標。保留規格與時長。"""
    if not os.path.exists(args.input):
        raise ToolError(f"input not found: {args.input}")
    from .platform_tools import resolve_font
    font = resolve_font().replace("\\", "/").replace(":", "\\:")
    out = args.out or args.input.rsplit('.', 1)[0] + "_title.mp4"
    hold = args.hold if args.hold is not None else 2.5
    fin = 0.6
    fade = (f"if(lt(t,{fin}),t/{fin},if(lt(t,{hold}),1,"
            f"if(lt(t,{hold}+{fin}),({hold}+{fin}-t)/{fin},0)))")
    size = args.size or 96
    yoff = "-90" if args.subtitle else ""
    tmp_files = []

    def _textfile(s):
        tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        tf.write(s); tf.close(); tmp_files.append(tf.name)
        return tf.name.replace("\\", "/").replace(":", "\\:")

    parts = [
        f"drawtext=fontfile='{font}':textfile='{_textfile(args.text)}':fontsize={size}:"
        f"fontcolor=white:borderw=4:bordercolor=black@0.55:shadowx=2:shadowy=2:shadowcolor=black@0.5:"
        f"x=(w-text_w)/2:y=(h-text_h)/2{yoff}:alpha='{fade}'"
    ]
    if args.subtitle:
        parts.append(
            f"drawtext=fontfile='{font}':textfile='{_textfile(args.subtitle)}':fontsize={int(size*0.45)}:"
            f"fontcolor=white@0.9:borderw=2:bordercolor=black@0.5:"
            f"x=(w-text_w)/2:y=(h-text_h)/2+70:alpha='{fade}'"
        )
    vf = ",".join(parts) + ",format=yuv420p"
    cmd = [FFMPEG, "-y", "-i", args.input, "-vf", vf, *_FX_ENCODE, out]
    res = run(cmd)
    for f in tmp_files:
        try: os.unlink(f)
        except OSError: pass
    if res.returncode != 0:
        raise ToolError(f"title-card failed: {res.stderr[-400:]}")
    print(json.dumps({"status": "ok", "file": out, "text": args.text}, ensure_ascii=False))


def cmd_title_sequence(args):
    """片頭/片尾：產生獨立的動態標題片段（文字滑入→hold→淡出）於深色底 + 暈影。
    1920x1080/30fps/bt709。--anim slide-up(預設)/fade。可選 --subtitle。"""
    from .platform_tools import resolve_font
    font = resolve_font().replace("\\", "/").replace(":", "\\:")
    out = args.out or "title_sequence.mp4"
    d = float(args.duration)
    anim = (args.anim or "slide-up").lower()
    size = args.size or 120
    fin = 0.8
    bg = args.bg or "0x0d0d1a"
    a_title = f"if(lt(t,{fin}),t/{fin},if(lt(t,{d}-{fin}),1,({d}-t)/{fin}))"
    y_title = (f"(h-text_h)/2-70+70*(1-min(t/{fin}\\,1))" if anim == "slide-up"
               else "(h-text_h)/2-70")
    tmp_files = []

    def _tf(s):
        tf = tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False, encoding="utf-8")
        tf.write(s); tf.close(); tmp_files.append(tf.name)
        return tf.name.replace("\\", "/").replace(":", "\\:")

    parts = [
        f"drawtext=fontfile='{font}':textfile='{_tf(args.text)}':fontsize={size}:"
        f"fontcolor=white:borderw=3:bordercolor=black@0.4:shadowx=2:shadowy=2:shadowcolor=black@0.5:"
        f"x=(w-text_w)/2:y={y_title}:alpha='{a_title}'"
    ]
    if args.subtitle:
        a_sub = (f"if(lt(t,0.4),0,if(lt(t,1.2),(t-0.4)/0.8,"
                 f"if(lt(t,{d}-{fin}),1,({d}-t)/{fin})))")
        parts.append(
            f"drawtext=fontfile='{font}':textfile='{_tf(args.subtitle)}':fontsize={int(size*0.4)}:"
            f"fontcolor=0xffd9a0:x=(w-text_w)/2:y=(h-text_h)/2+90:alpha='{a_sub}'"
        )
    vf = ",".join(parts) + ",vignette=PI/5,format=yuv420p"
    cmd = [FFMPEG, "-y", "-f", "lavfi", "-i",
           f"color=c={bg}:s=1920x1080:d={d}:r=30", "-vf", vf, *_FX_ENCODE, out]
    res = run(cmd)
    for f in tmp_files:
        try: os.unlink(f)
        except OSError: pass
    if res.returncode != 0:
        raise ToolError(f"title-sequence failed: {res.stderr[-400:]}")
    print(json.dumps({"status": "ok", "file": out, "text": args.text,
                      "duration_sec": round(_audio_duration(out), 3)}, ensure_ascii=False))


def cmd_collage(args):
    """多圖拼貼：2-4 張照片裝白框、排成一列，置於深色底上（像結訓片的群像/對比段）。
    輸出 1920x1080/30fps/bt709 影片，含整體緩慢推鏡。"""
    imgs = [p for p in (args.images or []) if os.path.exists(p)]
    if len(imgs) < 1:
        raise ToolError("collage 至少需要 1 張存在的圖")
    imgs = imgs[:4]
    n = len(imgs)
    d = float(args.duration)
    out = args.out or "collage.mp4"
    bg = args.bg or "0x0d0d1a"
    W, H = 1920, 1080
    gap, bw = 44, 5
    if n == 1:                                     # 單圖 framed：置中大相框
        cell_w, cell_h = int(W * 0.52), int(H * 0.80)
    else:
        cell_w = (W - 2 * 90 - (n - 1) * gap) // n
        cell_h = min(int(cell_w * 1.05), 640)      # 略偏方/直，像相框
    y = (H - cell_h) // 2
    total_w = n * cell_w + (n - 1) * gap
    x0 = (W - total_w) // 2                         # 整列置中
    inputs = ["-f", "lavfi", "-i", f"color=c={bg}:s={W}x{H}:d={d}:r=30"]
    for p in imgs:
        inputs += ["-loop", "1", "-t", f"{d}", "-i", p]
    parts = []
    for i in range(n):
        iw, ih = cell_w - bw * 2, cell_h - bw * 2
        parts.append(
            f"[{i+1}:v]scale={iw}:{ih}:force_original_aspect_ratio=increase,"
            f"crop={iw}:{ih},pad={cell_w}:{cell_h}:{bw}:{bw}:color=white,"
            f"setsar=1[c{i}]")
    chain = "[0:v]"
    for i in range(n):
        x = x0 + i * (cell_w + gap)
        nxt = f"[s{i}]" if i < n - 1 else "[base]"
        parts.append(f"{chain}[c{i}]overlay={x}:{y}{nxt}")
        chain = f"[s{i}]"
    parts.append("[base]vignette=PI/6,format=yuv420p[v]")
    fc = ";".join(parts)
    cmd = [FFMPEG, "-y", *inputs, "-filter_complex", fc, "-map", "[v]", *_FX_ENCODE, out]
    res = run(cmd)
    if res.returncode != 0:
        raise ToolError(f"collage failed: {res.stderr[-400:]}")
    print(json.dumps({"status": "ok", "file": out, "images": n,
                      "duration_sec": round(_audio_duration(out), 2)}, ensure_ascii=False))


def cmd_montage(args):
    """快切蒙太奇：N 張照片在一段內快速輪播（各帶 Ken Burns 慢推 + 快轉場），
    像 MV 的照片牆。輸出 1920x1080/30fps/bt709，總長=duration。"""
    imgs = [p for p in (args.images or []) if os.path.exists(p)]
    if len(imgs) < 2:
        raise ToolError(f"montage 需要至少 2 張存在的圖（給了 {len(imgs)}）")
    imgs = imgs[:8]
    n = len(imgs)
    d = float(args.duration)
    out = args.out or "montage.mp4"
    per = d / n                                    # 每張 solo 時間
    ov = min(0.45, per / 3)                         # 快轉場重疊
    clip = per + ov                                 # 每張 clip 長（含尾巴給 xfade）
    W, H = 1920, 1080
    zdirs = ["zoom-in", "pan-right", "zoom-out", "pan-left"]
    tmpd = tempfile.mkdtemp(prefix="montage_")
    clips = []
    try:
        for i, p in enumerate(imgs):
            cf = int((clip + 0.1) * 30)
            zp = {
                "zoom-in":  f"zoompan=z='min(zoom+0.0015,1.35)':d={cf}:s={W}x{H}:fps=30",
                "zoom-out": f"zoompan=z='if(eq(on,1),1.35,max(zoom-0.0015,1.0))':d={cf}:s={W}x{H}:fps=30",
                "pan-right":f"zoompan=z=1.25:x='if(eq(on,1),0,x+2)':y='ih/2-(ih/zoom/2)':d={cf}:s={W}x{H}:fps=30",
                "pan-left": f"zoompan=z=1.25:x='if(eq(on,1),iw-iw/zoom,x-2)':y='ih/2-(ih/zoom/2)':d={cf}:s={W}x{H}:fps=30",
            }[zdirs[i % len(zdirs)]]
            c = f"{tmpd}/m{i}.mp4"
            kc = [FFMPEG, "-y", "-loop", "1", "-i", p,
                  "-vf", f"scale={W}:{H}:force_original_aspect_ratio=increase,crop={W}:{H},{zp}",
                  "-t", f"{clip + 0.1:.3f}", "-c:v", "libx264", "-preset", "fast", "-crf", "20",
                  "-pix_fmt", "yuv420p", "-r", "30", c]
            if run(kc).returncode != 0:
                raise ToolError(f"montage kenburns 第 {i} 張失敗")
            clips.append(c)
        inputs = []
        for c in clips:
            inputs += ["-i", c]
        parts = []
        chain = "[0:v]"
        for i in range(1, n):
            offset = i * per
            lbl = f"[x{i}]" if i < n - 1 else "[pre]"
            parts.append(f"{chain}[{i}:v]xfade=transition=fade:duration={ov:.3f}:offset={offset:.3f}{lbl}")
            chain = f"[x{i}]"
        parts.append("[pre]format=yuv420p[v]")
        fc = ";".join(parts)
        # xfade-concat overshoots by ~ov+0.1 (last clip carries a tail for the
        # final transition); trim to exactly `d` so the precompose gate passes.
        cmd = [FFMPEG, "-y", *inputs, "-filter_complex", fc, "-map", "[v]",
               "-t", f"{d:.3f}", *_FX_ENCODE, out]
        res = run(cmd)
        if res.returncode != 0:
            raise ToolError(f"montage concat failed: {res.stderr[-400:]}")
    finally:
        shutil.rmtree(tmpd, ignore_errors=True)
    print(json.dumps({"status": "ok", "file": out, "images": n,
                      "per_photo_sec": round(per, 2),
                      "duration_sec": round(_audio_duration(out), 2)}, ensure_ascii=False))
