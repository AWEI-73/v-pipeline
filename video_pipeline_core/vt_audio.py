"""vt_audio.py — audio-director(TTS/混音/BGM/music-fetch)+ subtitle-director(SRT),
從 video_tools 解耦。共用原語取自 vt_core,避免循環匯入。"""
import os
import sys
import json
import subprocess
import re  # noqa: F401
import shutil
from pathlib import Path  # noqa: F401  (cmd_music_fetch 用 Path(FFMPEG).parent)
from .vt_core import YTDLP, FFMPEG, FFPROBE, run, ToolError, _audio_duration  # noqa: F401

# ── audio-director: TTS + 混音 ──────────────────────────────────────────────

def _split_by_punct(text: str) -> list:
    """按中文標點切句，保留標點在切片末尾"""
    import re
    parts = re.split(r'([，。；！？、])', text)
    phrases, cur = [], ''
    for p in parts:
        cur += p
        if p in '，。；！？、':
            if cur.strip():
                phrases.append(cur.strip())
            cur = ''
    if cur.strip():
        phrases.append(cur.strip())
    return phrases


def _finalize_segment_timing(segment, title, seg_start, speech_end, phrases,
                             segment_index, segment_count, tail_sec=0.4):
    """Close one spoken segment and add breathing room before the next one."""
    tail = float(tail_sec) if segment_index < segment_count - 1 else 0.0
    end = speech_end + tail
    return {
        "segment": segment,
        "title": title,
        "start_sec": round(seg_start, 3),
        "speech_end_sec": round(speech_end, 3),
        "tail_padding_sec": round(tail, 3),
        "end_sec": round(end, 3),
        "duration_sec": round(end - seg_start, 3),
        "phrases": phrases,
    }, end


def _render_silence_mp3(path, duration_sec=0.4):
    """Render a reusable mono 24kHz MP3 silence compatible with Edge TTS."""
    res = subprocess.run([
        FFMPEG, "-y",
        "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono",
        "-t", f"{duration_sec:.3f}",
        "-c:a", "libmp3lame", "-b:a", "48k",
        str(path),
    ], capture_output=True)
    if res.returncode != 0:
        raise ToolError(f"speech-tail silence render failed: {res.stderr.decode(errors='ignore')[:300]}")
    return str(path)




def cmd_tts(args):
    """從劇本 JSON 生成 TTS：按標點切句 → 每句獨立 TTS → 累加時長"""
    import asyncio
    try:
        import edge_tts
    except ImportError:
        raise ToolError("需要 edge-tts: pip install edge-tts --break-system-packages")

    if not os.path.exists(args.script):
        raise ToolError(f"script not found: {args.script}")

    with open(args.script, encoding="utf-8") as f:
        script = json.load(f)

    voice = args.voice or "zh-TW-HsiaoChenNeural"
    outdir = args.outdir or "tts_out"
    os.makedirs(outdir, exist_ok=True)

    async def tts_phrase(text, out_path):
        c = edge_tts.Communicate(text, voice=voice)
        await c.save(out_path)

    async def gen_all():
        all_audio = []
        cursor = 0.0
        timing = {"voice": voice, "segments": []}
        prepared = [(seg, _split_by_punct(seg["text"])) for seg in script]
        prepared = [(seg, phrases) for seg, phrases in prepared if phrases]
        silence_file = None
        silence_duration = 0.4
        if len(prepared) > 1:
            silence_file = _render_silence_mp3(
                os.path.join(outdir, "speech_tail_400ms.mp3"),
                silence_duration,
            )
            silence_duration = _audio_duration(silence_file)

        for seg_index, (seg, phrases) in enumerate(prepared):
            n = seg['segment']
            seg_start = cursor
            seg_phrases = []
            for i, ph in enumerate(phrases, 1):
                mp3 = os.path.join(outdir, f"seg{n}_p{i}.mp3")
                await tts_phrase(ph, mp3)
                dur = _audio_duration(mp3)
                seg_phrases.append({
                    "phrase": i,
                    "text": ph,
                    "audio_file": mp3,
                    "start_sec": round(cursor, 3),
                    "end_sec": round(cursor + dur, 3),
                    "duration_sec": round(dur, 3),
                })
                all_audio.append(mp3)
                cursor += dur
            seg_timing, cursor = _finalize_segment_timing(
                n,
                seg.get("title"),
                seg_start,
                cursor,
                seg_phrases,
                seg_index,
                len(prepared),
                silence_duration,
            )
            if seg_timing["tail_padding_sec"] and silence_file:
                all_audio.append(silence_file)
            timing["segments"].append(seg_timing)

        # 合併音訊
        concat_list = os.path.normpath(os.path.join(outdir, "concat.txt"))
        with open(concat_list, 'w', encoding="utf-8") as f:
            for af in all_audio:
                clean_path = os.path.abspath(af).replace('\\', '/')
                f.write(f"file '{clean_path}'\n")
        voice_out = os.path.join(outdir, "voice.mp3")
        res = subprocess.run([
            FFMPEG, '-y', '-f', 'concat', '-safe', '0', '-i', concat_list,
            '-c', 'copy', voice_out
        ], capture_output=True)
        if res.returncode != 0:
            raise ToolError(f"audio concat failed: {res.stderr.decode(errors='ignore')}")

        total = _audio_duration(voice_out)
        timing["total_duration_sec"] = round(total, 3)
        timing["voice_file"] = voice_out

        with open(os.path.join(outdir, "tts_timing.json"), 'w', encoding="utf-8") as f:
            json.dump(timing, f, ensure_ascii=False, indent=2)
        return timing

    timing = asyncio.run(gen_all())
    print(json.dumps({
        "status": "ok",
        "outdir": outdir,
        "voice_file": timing["voice_file"],
        "timing_file": os.path.join(outdir, "tts_timing.json"),
        "total_duration_sec": timing["total_duration_sec"],
        "segments": len(timing["segments"]),
        "phrases": sum(len(s["phrases"]) for s in timing["segments"]),
    }, ensure_ascii=False))


def _bgm_loop_chain(voice_dur, bgm_dur, crossfade_sec=2.5, max_copies=12,
                    bgm_offset=0.0):
    """純函式:回 (filter_chain_prefix, bgm_source_label)。

    BGM 比片短時需要 loop——但 aloop 是硬接縫(曲尾高潮跳回曲頭安靜開場),
    改用 N 份輸入以 acrossfade 串接(輸入 index 1..N 都是同一支 bgm 檔)。
    BGM 夠長(或無效時長)→ 回 ('', '1:a') 維持單輸入原行為。"""
    if not bgm_dur or bgm_dur <= 0:
        return "", "1:a"
    offset = max(0.0, min(float(bgm_offset or 0.0), max(0.0, bgm_dur - 0.5)))
    source_dur = max(0.5, bgm_dur - offset)
    trim_parts = []

    def source_label(input_index):
        if not offset:
            return f"{input_index}:a"
        label = f"bgmoff{input_index}"
        trim_parts.append(
            f"[{input_index}:a]atrim=start={offset:.3f},asetpts=PTS-STARTPTS[{label}];"
        )
        return label

    if voice_dur <= source_dur:
        if not offset:
            return "", "1:a"
        label = source_label(1)
        return "".join(trim_parts), label
    xf = min(crossfade_sec, max(0.5, source_dur / 3))
    effective = max(0.5, source_dur - xf)
    import math  # noqa: PLC0415
    n = 1 + math.ceil((voice_dur - source_dur) / effective)
    n = min(max_copies, max(2, n))
    parts = []
    prev = source_label(1)
    for k in range(2, n + 1):
        label = f"bgmlp{k - 1}"
        parts.append(f"[{prev}][{source_label(k)}]acrossfade=d={xf:.2f}[{label}];")
        prev = label
    return "".join(trim_parts + parts), prev


def cmd_mix_audio(args):
    """混合人聲 + BGM：BGM 降到指定音量，含淡入淡出"""
    if not os.path.exists(args.voice):
        raise ToolError(f"voice file not found: {args.voice}")

    voice = args.voice
    bgm = args.bgm
    out = args.out or "final_audio.wav"
    bgm_vol = args.bgm_vol if args.bgm_vol is not None else 0.10

    voice_dur = _audio_duration(voice)

    # 沒 BGM：人聲直接轉 WAV + 淡入淡出
    if not bgm:
        fade_filter = f"afade=t=in:st=0:d=0.5,afade=t=out:st={max(0, voice_dur-1):.3f}:d=1"
        cmd = [
            FFMPEG, '-y', '-i', voice,
            '-af', fade_filter,
            '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '2', out
        ]
        res = run(cmd)
        if res.returncode != 0:
            raise ToolError(f"voice-only mix failed: {res.stderr[:300]}")
        print(json.dumps({"status": "ok", "file": out, "bgm": None,
                          "duration_sec": round(voice_dur, 3)}))
        return

    if not os.path.exists(bgm):
        raise ToolError(f"bgm file not found: {bgm}")

    # 有 BGM:loop 到人聲長度 + 淡入淡出再混音(normalize=0 避免壓低人聲)。
    # Loop 用 acrossfade 串副本,不用 aloop 硬接——122.9s 的曲被硬 loop 進 297s 的
    # 片時,曲尾高潮直接跳回曲頭安靜開場,聽感像壞掉(city-day 5min 實聽教訓)。
    bgm_dur = _audio_duration(bgm)
    bgm_offset = max(0.0, float(getattr(args, "bgm_offset", 0.0) or 0.0))
    loop_chain, bsrc = _bgm_loop_chain(voice_dur, bgm_dur, bgm_offset=bgm_offset)
    n_bgm_inputs = max(1, loop_chain.count("acrossfade") + 1)
    # aformat:acrossfade 串出來的流會丟 channel layout,sidechaincompress 會拒收
    bfin = f"atrim=duration={voice_dur:.3f},aformat=channel_layouts=stereo"
    bfade = f"afade=t=in:st=0:d=1,afade=t=out:st={max(0, voice_dur-1.5):.3f}:d=1.5"
    vfade = (f"afade=t=in:st=0:d=0.3,afade=t=out:st={max(0, voice_dur-1):.3f}:d=1,"
             f"aformat=channel_layouts=stereo")
    if args.duck:
        # sidechain ducking：人聲說話時自動壓低音樂。BGM 基準可大聲些（預設 0.28）
        dvol = args.bgm_vol if args.bgm_vol is not None else 0.28
        bgm_vol = dvol
        fc = (
            f"{loop_chain}[{bsrc}]{bfin},volume={dvol},{bfade},aformat=channel_layouts=stereo[bgmraw];"
            f"[0:a]{vfade}[v];[v]asplit=2[v1][vkeyraw];"
            f"[vkeyraw]aformat=channel_layouts=stereo[vkey];"
            f"[bgmraw][vkey]sidechaincompress=threshold=0.02:ratio=8:attack=15:release=350[bgmduck];"
            f"[v1][bgmduck]amix=inputs=2:duration=first:dropout_transition=0,"
            f"alimiter=limit=0.95,aresample=48000[mixed]"
        )
    else:
        fc = (
            f"{loop_chain}[{bsrc}]{bfin},volume={bgm_vol},{bfade}[bgm];"
            f"[0:a]{vfade}[v];"
            f"[v][bgm]amix=inputs=2:duration=first:dropout_transition=0,"
            f"alimiter=limit=0.95,aresample=48000[mixed]"
        )

    cmd = [FFMPEG, '-y', '-i', voice]
    for _ in range(n_bgm_inputs):
        cmd += ['-i', bgm]
    cmd += [
        '-filter_complex', fc,
        '-map', '[mixed]',
        '-acodec', 'pcm_s16le', '-ar', '48000', '-ac', '2',
        out
    ]
    res = run(cmd)
    if res.returncode != 0:
        raise ToolError(f"mix-audio failed: {res.stderr[:500]}")

    print(json.dumps({
        "status": "ok",
        "file": out,
        "voice": voice,
        "bgm": bgm,
        "bgm_volume": bgm_vol,
        "bgm_offset_sec": round(bgm_offset, 3),
        "duration_sec": round(voice_dur, 3),
    }))


def cmd_mix_sfx(args):
    """Mix a deterministic SFX cue plan onto an existing final-audio base."""
    from .sfx import build_sfx_filter

    if not os.path.exists(args.base):
        raise ToolError(f"base audio not found: {args.base}")
    if not os.path.exists(args.plan):
        raise ToolError(f"sfx plan not found: {args.plan}")
    with open(args.plan, encoding="utf-8") as f:
        plan = json.load(f)
    cues = plan.get("cues") or []
    out = args.out or "final_audio.wav"
    if not cues:
        shutil.copy(args.base, out)
        print(json.dumps({"status": "ok", "file": out, "cues": 0}))
        return
    for cue in cues:
        if not os.path.exists(cue.get("asset", "")):
            raise ToolError(f"sfx asset not found: {cue.get('asset')}")
    graph, label = build_sfx_filter(cues)
    cmd = [FFMPEG, "-y", "-i", args.base]
    for cue in cues:
        cmd += ["-i", cue["asset"]]
    cmd += [
        "-filter_complex", graph, "-map", f"[{label}]",
        "-acodec", "pcm_s16le", "-ar", "48000", "-ac", "2", out,
    ]
    res = run(cmd)
    if res.returncode != 0:
        raise ToolError(f"sfx mix failed: {res.stderr[:500]}")
    print(json.dumps({"status": "ok", "file": out, "cues": len(cues)}))


# ── subtitle-director: 從 tts_timing.json 生成同步 SRT ─────────────────────

def _fmt_srt_time(seconds: float) -> str:
    """秒數轉 SRT 時間戳 HH:MM:SS,mmm"""
    ms_total = int(round(seconds * 1000))
    h, ms_total = divmod(ms_total, 3600000)
    m, ms_total = divmod(ms_total, 60000)
    s, ms = divmod(ms_total, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def cmd_srt(args):
    """從 tts_timing.json 生成 phrase-level 時間同步 SRT。

    跟舊版 mksrt（靜態 per-segment）不同：
    - mksrt：每個 segment 一條字幕，整段顯示同一句（不準）
    - srt：每個 phrase 一條字幕，時間軸對齊 TTS 實際長度（已驗證 0ms 漂移）
    """
    if not os.path.exists(args.timing):
        raise ToolError(f"tts_timing.json not found: {args.timing}")

    with open(args.timing, encoding="utf-8") as f:
        timing = json.load(f)

    out = args.out or "subtitles.srt"
    lines = []
    idx = 1
    phrase_count = 0
    seg_count = 0

    for seg in timing.get("segments", []):
        seg_count += 1
        for ph in seg.get("phrases", []):
            lines.append(str(idx))
            lines.append(
                f"{_fmt_srt_time(ph['start_sec'])} --> {_fmt_srt_time(ph['end_sec'])}"
            )
            lines.append(ph['text'])
            lines.append('')
            idx += 1
            phrase_count += 1

    if phrase_count == 0:
        raise ToolError("no phrases found in timing file")

    with open(out, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

    print(json.dumps({
        "status": "ok",
        "file": out,
        "segments": seg_count,
        "phrases": phrase_count,
        "total_duration_sec": timing.get("total_duration_sec"),
        "voice": timing.get("voice"),
    }, ensure_ascii=False))


# ── BGM 情境庫：ffmpeg 合成氛圍墊樂（placeholder，可換真曲）─────────────────
# 每個情境 = 一組和弦頻率(Hz) + lowpass(柔化) + tremolo 速率(律動)。
# 產出無尾巴淡出的持續 pad（給 mix-audio 自行 loop + 全曲淡入淡出）。
BGM_MOODS = {
    "calm":      ([220.00, 261.63, 329.63], 900, 0.12),   # Am 安靜
    "warm":      ([261.63, 329.63, 392.00], 1100, 0.10),  # C 溫暖
    "emotional": ([293.66, 349.23, 440.00], 1000, 0.10),  # Dm 情感
    "energetic": ([220.00, 277.18, 329.63], 1600, 0.50),  # A 有節奏
    "tense":     ([110.00, 146.83, 164.81], 700, 0.20),   # 低沉緊張
    "bright":    ([329.63, 415.30, 493.88], 1800, 0.15),  # E 明亮
    "night":     ([164.81, 196.00, 246.94], 800, 0.10),   # 低 E 夜色
}


def cmd_gen_bgm(args):
    """合成一段情境氛圍墊樂（placeholder）。真曲可直接覆蓋 bgm/<mood>.mp3。"""
    mood = (args.mood or "calm").lower()
    if mood not in BGM_MOODS:
        raise ToolError(f"unknown mood: {mood} (choose from {'/'.join(BGM_MOODS)})")
    freqs, lp, trem = BGM_MOODS[mood]
    d = args.duration or 60
    out = args.out or f"bgm/{mood}.mp3"
    d_out = os.path.dirname(out)
    if d_out:
        os.makedirs(d_out, exist_ok=True)
    inputs = []
    for f in freqs:
        inputs += ["-f", "lavfi", "-i", f"sine=frequency={f}:duration={d}"]
    n = len(freqs)
    mix = "".join(f"[{i}]" for i in range(n)) + f"amix=inputs={n}"
    fc = (f"{mix},tremolo=f={trem}:d=0.4,lowpass=f={lp},"
          f"aecho=0.8:0.6:60|110:0.3|0.2,alimiter=limit=0.9")
    cmd = [FFMPEG, "-y", *inputs, "-filter_complex", fc,
           "-ac", "2", "-ar", "44100", "-b:a", "128k", out]
    res = run(cmd)
    if res.returncode != 0:
        raise ToolError(f"gen-bgm failed: {res.stderr[-300:]}")
    print(json.dumps({"status": "ok", "file": out, "mood": mood,
                      "duration_sec": round(_audio_duration(out), 2)}, ensure_ascii=False))


def _music_ytdlp_cmd(query, out_base, ffdir, max_dur=None, min_dur=30, n=5):
    """Build the yt-dlp command that grabs the first *duration-suitable* search hit
    as an mp3. `out_base` has NO extension — the audio post-processor appends `.mp3`.

    ytsearch1 was too fragile: 1 result → if it's a 3-hour mix or gets filtered, you
    get nothing. Now: ytsearchN + a duration window (floor `min_dur` to skip stings,
    ceiling `max_dur` or 600s to skip multi-hour mixes) + `--max-downloads 1` so it
    downloads the first match and stops (yt-dlp exits 101 on the cap — caller checks
    file existence, not returncode)."""
    hi = int(max_dur) if max_dur else 600   # 預設上限 10 分鐘,避免抓到數小時混音
    flt = f"duration > {int(min_dur)} & duration < {hi}"
    return [YTDLP, f"ytsearch{int(n)}:{query}",
            "-x", "--audio-format", "mp3", "--audio-quality", "0",
            "--no-playlist", "--no-warnings",
            "--match-filter", flt, "--max-downloads", "1",
            "-o", f"{out_base}.%(ext)s",
            "--ffmpeg-location", ffdir]


def cmd_music_fetch(args):
    """抓真實背景音樂（取代 gen-bgm 合成 placeholder）。

    source=yt（預設、可運作）：yt-dlp 搜尋 + 抽音訊成 mp3。學員/私用情境足夠。
    source=jamendo：真正免版稅 API 的 provider 接縫——需 JAMENDO_CLIENT_ID，尚未啟用。
    （Pixabay 沒有公開 music API，音樂只在網站，故不接 Pixabay。）"""
    source = (args.source or "yt").lower()
    query = args.query
    out = args.out or f"music_{source}.mp3"
    out_base = out[:-4] if out.lower().endswith(".mp3") else out
    out_dir = os.path.dirname(out_base)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    if source == "yt":
        cmd = _music_ytdlp_cmd(query, out_base, str(Path(FFMPEG).parent), args.max_dur)
        res = run(cmd)
        final = f"{out_base}.mp3"
        if not os.path.exists(final):
            cap = int(args.max_dur) if args.max_dur else 600
            hint = (f"（時長過濾 30s–{cap}s 可能把前 5 個結果都濾掉了，"
                    "放寬 --max-dur 或改用較短的搜尋詞）")
            err = (res.stderr or "").strip()[-300:]
            raise ToolError(f"music-fetch yt 沒有產出檔案{hint}。{('yt-dlp: ' + err) if err else ''}")
        print(json.dumps({"status": "ok", "file": final, "source": "yt",
                          "query": query, "duration_sec": round(_audio_duration(final), 2)},
                         ensure_ascii=False))
    elif source == "jamendo":
        raise ToolError("source=jamendo 需 JAMENDO_CLIENT_ID 與整合（免版稅 API provider 接縫，"
                        "尚未啟用）。目前可用 source=yt。")
    else:
        raise ToolError(f"unknown music source: {source}（可用：yt / jamendo）")
