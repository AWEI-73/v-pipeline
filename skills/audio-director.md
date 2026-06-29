---
name: audio-director
description: Use when Hermes needs TTS, voiceover timing, approved music mixing, ducking, original speech preservation, final_audio.wav, tts_timing.json, or audio_mix_report.json after Soundtrack Arranger or SPEC handoff.
---

# Audio Director Skill

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "audio-director",
  "stage_owner": "audio_director_mix_execution",
  "triggers": [
    "audio_mix_plan is ready and must become final_audio.wav",
    "pipeline needs TTS, ducking, original speech preservation, or audio_mix_report"
  ],
  "canonical_tools": [
    {
      "tool": "tools/audio_mix_plan_execute.py",
      "when": "execute accepted audio_mix_plan.json into final_audio.wav and audio_mix_report.json without rendering video; use sections[] for section-aware placement when present",
      "inputs": ["audio_mix_plan.json", "audio_handoff_acceptance.json", "accepted source audio files", "optional sections[] timing", "source_audio_policy"],
      "outputs": ["final_audio.wav", "audio_mix_report.json"],
      "stop_if": ["audio_handoff_acceptance ok=false", "audio_mix_plan ready_for_mix=false", "audio_file missing"]
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/final_av_assemble.py",
      "when": "assemble an already-approved visual video stream with final_audio.wav after BUILD and Audio Director are both complete; write assembly_report.json and do not choose clips, music, voice, subtitles, or effects",
      "inputs": ["approved visual video", "final_audio.wav", "source_audio_policy"],
      "outputs": ["final.mp4", "assembly_report.json"],
      "stop_if": ["visual video missing", "final_audio.wav missing", "audio_mix_report.json missing for required audio", "source_audio_policy is preserve_speech but final_audio.wav has not already mixed protected speech"]
    }
  ],
  "forbidden_tools": [
    "Do not render final.mp4 from Audio Director",
    "Do not mix reference_only or unlicensed music",
    "Do not bypass audio_handoff_acceptance"
  ]
}
<!-- TOOL_CONTRACT_END -->

## Soundtrack Arranger Handoff

`soundtrack-arranger` owns soundtrack intent, source candidates, and license
evidence before this skill executes audio work. Read `soundtrack_plan.json`,
`music_source_candidates.json`, `sound_license_manifest.json`, and
`audio_director_handoff.json` when they exist.

Audio Director then owns TTS, music fetch/use of approved files, ducking,
preserving original speech, `final_audio.wav`, `tts_timing.json`, and
`audio_mix_report.json`. If `sound_license_manifest.json` marks a track as
`reference_only`, placeholder, missing license, or delivery-disallowed, do not
mix it into deliverable output.

For selected deliverable music, require `audio_handoff_acceptance.json` to have
already validated `soundtrack_probe_report.json`. Do not mix a selected BGM/song
track that bypassed the probe gate. The probe is not a genre oracle; it is the
minimum evidence that duration, loudness, sections, and section fit were
inspected before mixing.

`tools/final_av_assemble.py` is a final glue helper only after visual BUILD and
Audio Director are both complete. It may replace source-video audio with the
accepted `final_audio.wav` and write `assembly_report.json`. It must not choose
music, clip timing, voiceover, subtitles, or effects; those decisions must
already exist in upstream artifacts.

When `audio_mix_plan.json` contains `source_audio_policy`, keep it in the
resulting `audio_mix_report.json` and respect it during BUILD handoff:

- `preserve_speech`: include protected original speech or voiceover and duck
  music under it.
- `replace_with_music`: do not preserve source-video audio in the final
  deliverable.
- `mixed`: require section-level placements that state where original speech is
  preserved and where music replaces source audio.

> **Facet 擁有權(Node 3,見 [spec-contract.md](spec-contract.md)):音控師擁有 `audio` facet。**
> 欄位:`role`(music/duck/diegetic)/ `music_intent` / `original_audio_policy` / `voiceover_policy` / `reason`。
> 原則:隊呼/掌聲/演講的**原音可以是該段的情緒核心,不是背景雜音**。

音控師負責影片裡的所有聲音：TTS 配音、BGM 混入、淡入淡出、**MV 的逐段混音計畫**。
在路線 A（旁白 text-driven）流程裡，**音控師先跑**，輸出 `tts_timing.json` 後字幕師與剪輯師才能依時長排字幕與剪素材。
在 **MV 路線（無旁白）** 裡，音控師產**混音計畫**——不是「蓋一首歌」，而是讀每段原音與導演意圖逐段編排。

---

> **選曲紀律(2026-06-12,city-day 實聽教訓)**:口白片 BGM 應選 **長度 ≥ 片長**
> 或結構平緩可 loop 的曲子。短曲會被 loop 補滿(現已 acrossfade 軟接,但
> epic 類曲式「高潮接開場」即使軟接也聽得出來);65bpm 史詩企業曲配 calm
> 紀錄片這種 tone 錯配,任何混音都救不回——選曲先對 tone,再對長度。

## MV 混音計畫（路線 MV，2026-06-03）

> **選曲低風險（一首對味 + 人核可）；但「音樂 × 原音」的編排是判定影片好壞的關鍵。**
> 隨便把音樂蓋上去會毀掉隊呼/掌聲/致詞。音控師要看素材原音 + 編劇導演方向 → 逐段決定 `audio_role`。

### 逐段 `audio_role`（統一段落模型的音訊輸出頻道）

| role | 用於 | 行為（已由 `mv_cut._mv_music_mix` 實作） |
|---|---|---|
| `music` | 中間快剪 montage（無有用原音） | 只有音樂當主音軌（全音量） |
| `duck` | 致詞 / 有人講話 | 保留原音 + 音樂用 `sidechaincompress` 在講話時自動壓低（原音為主） |
| `diegetic` | **隊呼 / 掌聲 / 宣誓（原音即高潮）** | 保留原音、音樂讓位（隨便加音樂會毀掉這裡） |

- **預設由 kind 推**：montage→`music`；hold + keep_audio→`duck`/`diegetic`。
- `duck`/`diegetic` 段在 `run_mv` 會自動 `keep_audio=True`（保留原音）。
- 實作:`render_mv_audio` → 有原音段用 sidechain ducking，全 montage 音樂直接當主軌。
- 講話段標 `subtitle:"auto"` → ASR(faster-whisper) 轉錄原音燒字幕（`MV_ASR_MODEL` 可換大模型）。

### 音控師的混音計畫產物（交接物）

對每段給：`audio_role` + 是否 `keep_audio` + 音樂 brief（情緒/曲風，寫進劇本頂層 `music`）。
**VERIFY 會檢查**（`mv_cut.audio_qa`，dashboard 顯示 audio_pairing）：
- 致詞段(subtitle:auto)有沒有保留原音（沒有 → 字幕沒聲源、被音樂蓋過）。
- diegetic 段有沒有保留原音。

### 已知陷阱（MV）
- **diegetic 段絕不可讓音樂蓋過**：隊呼/宣誓的原音就是高潮。標 `diegetic` + `keep_audio`。
- **音樂要最先選**：beat-driven MV 中 音樂→tempo→cut_grid→剪輯節奏，所以音樂先定骨架（導演出 brief、音控執行 `music-fetch`）。結訓片要熱血，鋼琴 placeholder 是錯的。
- `music-fetch` 用 `ytsearchN` + 時長窗（30s–10min），避免抓到數小時混音。

---

## 工具位置

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

兩個指令：
```bash
python3 video_tools.py tts        <script.json> [--voice ...] [--outdir DIR]
python3 video_tools.py mix-audio  --voice voice.mp3 [--bgm bgm.mp3] [--bgm-vol N] [--out final_audio.wav]
```

---

## 對應命令
* `[[cmd_tts]]` - 音控師：按標點切句，每句獨立進行 edge-tts 生成，合併人聲並產出 tts_timing.json。
* `[[cmd_mix_audio]]` - 混合人聲與背景音樂 (BGM)，提供自動淡入淡出並限制防爆音。

---

---

## 流程

```
script.json
   │
   ▼
[tts]         按標點切句 → 每句獨立 TTS → 累加時長
   │
   ├──> tts/seg{N}_p{i}.mp3     每句獨立音檔
   ├──> voice.mp3                合併後完整人聲
   └──> tts_timing.json          給字幕師 + 剪輯師
   │
   ▼
[mix-audio]   人聲 + (可選 BGM) → 加淡入淡出 → WAV 輸出
   │
   └──> final_audio.wav          最終音軌（剪輯師組裝最後一步用）
```

---

## 指令 1：tts

### 用法
```bash
python3 video_tools.py tts script.json \
  --voice zh-TW-HsiaoChenNeural \
  --outdir /workspace/audio_out
```

### 預設值
- `--voice`：`zh-TW-HsiaoChenNeural`（HsiaoChen 女聲）
- `--outdir`：`tts_out`

### 可用聲音（zh-TW）
- `zh-TW-HsiaoChenNeural` — 女聲，溫和清晰（預設）
- `zh-TW-HsiaoYuNeural` — 女聲，較活潑
- `zh-TW-YunJheNeural` — 男聲，沉穩

完整清單：`edge-tts --list-voices | grep zh-TW`

### 輸出：tts_timing.json
```json
{
  "voice": "zh-TW-HsiaoChenNeural",
  "voice_file": "/workspace/audio_out/voice.mp3",
  "total_duration_sec": 89.52,
  "segments": [
    {
      "segment": 1,
      "title": "開頭",
      "start_sec": 0.0,
      "end_sec": 18.55,
      "duration_sec": 18.55,
      "phrases": [
        {
          "phrase": 1,
          "text": "一九五零年圖靈提出了機器能否思考這個問題，",
          "audio_file": "/workspace/audio_out/seg1_p1.mp3",
          "start_sec": 0.0,
          "end_sec": 4.8,
          "duration_sec": 4.8
        }
      ]
    }
  ]
}
```

### 設計重點：為什麼按標點切句而不用 word-level
- edge-tts 對中文沒有 word boundary（僅 sentence boundary）
- WhisperX 的中文 word alignment 模型不明確支援
- **按標點切句 → 每句獨立 TTS → 累加時長**：實測 0ms 誤差
- 詳見 vault：`projects/video-agent-pipeline/tool-verification-log.md`

---

## 指令 2：mix-audio

### 用法

**無 BGM**（純人聲 + 淡入淡出）：
```bash
python3 video_tools.py mix-audio \
  --voice /workspace/audio_out/voice.mp3 \
  --out /workspace/final_audio.wav
```

**有 BGM**：
```bash
python3 video_tools.py mix-audio \
  --voice /workspace/audio_out/voice.mp3 \
  --bgm /workspace/bgm/ambient_pad.mp3 \
  --bgm-vol 0.10 \
  --out /workspace/final_audio.wav
```

### 預設值
- `--bgm-vol`：`0.10`（10% volume）
- `--out`：`final_audio.wav`

### BGM 音量參考（依 ffmpeg-pitfalls #21）
- 有人聲段：`0.08 ~ 0.12`（8–12%）
- 純畫面段：`0.30 ~ 0.40`（30–40%）

> 目前 mix-audio 是全片同音量，未做依「人聲有/無」的自動 ducking。  
> 若劇本沒有大段純畫面（路線 A 大多是滿版人聲），這樣已經夠用。

### 淡入淡出設定
- 人聲：0.3s 淡入 / 1.0s 淡出
- BGM：1.0s 淡入 / 1.5s 淡出
- 最後加 `alimiter` 防爆音（limit=0.95）

---

## 與其他 Skill 的銜接

### 上游
- `編劇 Skill` 產出 `script.json`（路線 A 下，text 字數會被 TTS 決定實際長度）

### 下游
- `字幕師 Skill`：讀 `tts_timing.json` → 產出 SRT
- `剪輯師 Skill`：讀 `tts_timing.json` 的 `segments[].duration_sec` → 剪每段素材到精確時長
- `最終組合`：用 `final_audio.wav` 取代 rough_cut.mp4 的原始音軌

---

## 已知陷阱

### #21 BGM 音量
語音段 BGM 超過 12% 會明顯蓋過人聲，但這套用 amix 全片混音不會自動分段調整。  
**建議**：若有大段純畫面，先用 ffmpeg 切兩段分別混音再 concat。

### amix normalize 陷阱（本實作已修）
ffmpeg `amix` 預設 `normalize=1`，會自動降低所有輸入避免爆音 → 結果人聲反而變小。  
**已修**：filter 中使用 `amix=...:normalize=0` + `alimiter=limit=0.95` 防爆音。

### #23 BGM 來源音量不一致
不同 BGM 檔案基線音量可能差很大，同樣的 `--bgm-vol 0.10` 出來效果不同。  
**建議**：BGM 加進 vault 前先用 `ffmpeg -af loudnorm` 統一 -23 LUFS。

### TTS 句子過短會聽起來突兀
切句後若一句只剩 1-2 個字（例如「啊。」），TTS 出來會像唸錯。  
**建議**：編劇時避免單字短句。

---

## 實測結果（2026-05-24）

| 測試 | 結果 |
|------|------|
| 89s 腳本（28 phrases）TTS 生成 | ✅ 0ms 漂移 |
| 純人聲混音（含淡入淡出） | ✅ mean -22.9dB, max -7.5dB |
| 人聲 + BGM 12% 混音 | ✅ mean -22.5dB, max -7.1dB（人聲不被壓低）|

成品：`/workspace/v2_with_bgm.mp4`（89.5s 含 TTS + BGM + 字幕）

---

## 對應的 vault 文件
- `projects/video-agent-pipeline/roadmap.md` Phase 2
- `projects/video-agent-pipeline/skill-interface-contracts.md` — tts_timing.json 格式
- `projects/video-agent-pipeline/ffmpeg-pitfalls-reference.md` — #21 / #23 / #28 / #29
- `projects/video-agent-pipeline/tool-verification-log.md` — edge-tts 驗證
