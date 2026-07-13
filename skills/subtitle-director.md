---
name: subtitle-director
description: 字幕師 Skill。讀音控師輸出的 tts_timing.json，生成 phrase-level 時間同步 SRT，再用 burnsub 燒進影片。已驗證 0ms 漂移、句子邊界自然（按標點切，不會切到詞中間）。
---

# Subtitle Director Skill

## Current Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "subtitle-director",
  "stage_owner": "subtitle_voiceover_handoff",
  "triggers": [
    "subtitle_voiceover_contract requires subtitles, caption readability, narration, or voiceover evidence",
    "subtitles.srt, caption_audit.json, or narration_manifest.json must be accepted before BUILD"
  ],
  "canonical_tools": [
    {
      "tool": "tools/subtitle_voiceover_handoff_accept.py",
      "when": "accept subtitle/voiceover evidence into subtitle_voiceover_handoff_acceptance.json and subtitle_voiceover_build_handoff.json without rendering video",
      "inputs": [
        "subtitle_voiceover_contract",
        "subtitles.srt",
        "caption_audit.json",
        "narration_manifest.json",
        "voiceover_provider_plan.json",
        "voxcpm_runtime_check.json"
      ],
      "outputs": [
        "subtitle_voiceover_handoff_acceptance.json",
        "subtitle_voiceover_build_handoff.json"
      ],
      "stop_if": [
        "required subtitles missing",
        "caption audit failed or missing",
        "required voiceover has no narration manifest",
        "voiceover audio refs are missing",
        "preferred voiceover provider unavailable and fallback is not allowed"
      ],
      "capability_id": "cap.subtitle-director.subtitle-voiceover-handoff-accept.v1",
      "execution_class": "deterministic",
      "capability_role": "operation",
      "loops": [
        "L2"
      ],
      "maturity": "experimental"
    }
  ],
  "supporting_tools": [
    {
      "tool": "tools/subtitle_patch.py",
      "when": "apply reviewed Workbench subtitle text/timing patches without overwriting canonical SRT",
      "inputs": [
        "review_subtitles.srt",
        "subtitles.srt",
        "subtitle_patch.json"
      ],
      "outputs": [
        "patched_draft_subtitles.json"
      ],
      "stop_if": [
        "subtitle id is invalid",
        "patch would overwrite source subtitle file"
      ]
    }
  ],
  "forbidden_tools": [
    "Do not render final.mp4 from Subtitle Director",
    "Do not burn subtitles in the handoff acceptance step",
    "Do not synthesize TTS from subtitle handoff acceptance"
  ],
  "capability_namespace": "cap.subtitle-director.*",
  "capability_lookup_owner": "subtitle-director"
}
<!-- TOOL_CONTRACT_END -->

Use this skill when the route needs subtitles, subtitle readability evidence,
or voiceover/narration evidence after Stage 0/2 declares
`subtitle_voiceover_contract`.

Canonical no-render handoff:

```powershell
python tools\subtitle_voiceover_handoff_accept.py `
  --contract RUN_DIR\subtitle_voiceover_contract.json `
  --caption-audit RUN_DIR\caption_audit.json `
  --subtitles RUN_DIR\subtitles.srt `
  --narration-manifest RUN_DIR\narration_manifest.json `
  --out-dir RUN_DIR `
  --json
```

Inputs:

- `subtitle_voiceover_contract` or equivalent Stage 0 contract
- `subtitles.srt` when subtitles are required
- `caption_audit.json` with `pass=true` when subtitles are required
- `narration_manifest.json` with existing voiceover audio refs when voiceover is required
- `voiceover_provider_plan.json` and `voxcpm_runtime_check.json` when a
  preferred provider such as VoxCPM is requested

Outputs:

- `subtitle_voiceover_handoff_acceptance.json`
- `subtitle_voiceover_build_handoff.json`
- `artifact_manifest.json` flat keys plus nested `artifacts.<key>.path`
  metadata for accepted or blocked subtitle/voiceover evidence

Stop if:

- required subtitles are missing
- `caption_audit.json` is missing or failed
- required voiceover has no narration manifest
- narration manifest does not reference existing audio files
- preferred voiceover provider is unavailable and fallback is not explicitly
  allowed

If fallback is explicitly allowed, the handoff must still record
`provider_status.fallback_used=true`, `fallback_reason`, and the selected
provider. Do not silently swap VoxCPM or another requested provider.

Do not render `final.mp4`, burn subtitles, or synthesize TTS from this handoff
step. TTS/audio execution belongs to `audio-director`; final subtitle burn-in
belongs to BUILD/render after this handoff is accepted.

字幕師負責影片字幕的生成與燒入。  
**核心原則：字幕時間軸由 TTS 決定，不是反過來**。  
路線 A（text-driven）下，TTS 是 ground truth，字幕師只是把 tts_timing.json 翻譯成 SRT。

> **🔴 踩過的坑:`subtitle:"auto"` 只能配真人聲段。** auto = 對該段「原始音訊」跑
> ASR;靜音 stock / 純配樂段沒有人聲 → 空字幕 → `subtitle_accuracy` 直接 0 分
> (convergence dry-run 實證)。規則:`audio.role` 是 `duck`/`diegetic`(致詞/隊呼/
> 現場聲)才能 auto;其餘段給明文字幕或 `none`。BUILD 前 spec_review gate(規則 B3)
> 會把違規擋下來。

---

## 工具位置

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

兩個指令：
```bash
python3 video_tools.py srt      <tts_timing.json>  [--out subtitles.srt]
python3 video_tools.py burnsub  <video> <srt>      [--out output.mp4]
```

---

## 對應命令
* `[[cmd_subtitle]]` - 轉譯影片，並使用 faster-whisper 產生字幕檔 .srt（適用於非劇本驅動的外部素材）。
* `[[cmd_mksrt]]` - 從劇本 JSON 直接生成中文 .srt 字幕檔（舊版靜態 per-segment 字幕）。
* `[[cmd_srt]]` - 從 tts_timing.json 生成 phrase-level 時間同步的 SRT 字幕檔（新版同步字幕）。
* `[[cmd_burnsub]]` - 把 .srt 字幕燒入影片（支援中文渲染與字型 magic bytes 安全驗證）。

---

---

## 流程

```
[音控師 tts] ──> tts_timing.json
                       │
                       ▼
                  [srt 指令]      生成 phrase-level SRT
                       │
                       └──> subtitles.srt
                                  │
[剪輯師] ──> final_video.mp4 ─────┤
                                  ▼
                            [burnsub 指令]   字幕燒入影片
                                  │
                                  └──> final_subbed.mp4
```

---

## 指令 1：srt（生成同步字幕）

### 用法
```bash
python3 video_tools.py srt /workspace/audio_out/tts_timing.json \
  --out /workspace/subtitles.srt
```

### 輸出
- 標準 SRT 格式
- 每個 phrase 一條字幕（不是每個 segment 一條）
- 時間軸完全對齊 tts_timing.json 的 `start_sec` / `end_sec`

### 範例
```
1
00:00:00,000 --> 00:00:04,800
一九五零年圖靈提出了機器能否思考這個問題，

2
00:00:04,800 --> 00:00:08,328
正式揭開人工智慧研究的序幕。
```

### 設計重點

**為什麼是 phrase-level 而不是 segment-level？**

舊版 `mksrt` 指令是把整個 segment 的 text 當成一條字幕顯示 18 秒，問題：
- 觀眾來不及讀完一長串文字
- 字幕跟旁白脫鉤，明明只說了前半句卻顯示整段

新版 `srt` 指令按標點切句，每句一條字幕：
- 自然停頓點（標點＝呼吸點）
- 字幕跟著旁白節奏走
- 已驗證 0ms 漂移（vault tool-verification-log.md）

**為什麼不會切到句中？**

`split_by_punct()` 函式（在音控師 `tts` 指令裡）只在「，。；！？、」這些標點切，標點本身留在前一句末尾。所以每個 phrase 都是一個完整意群。

---

## 指令 2：burnsub（字幕燒入影片）

### 用法
```bash
python3 video_tools.py burnsub /workspace/v2_with_bgm.mp4 \
  /workspace/subtitles.srt \
  --out /workspace/v2_final_subbed.mp4
```

### 內建設定
- 字型：WQY Microhei（`~/.local/share/fonts/wqy-microhei.ttc`）
- 字型驗證：開頭 4 bytes 必須是 TrueType magic（避免下載到 HTML 假檔）
- 樣式：白字 + 黑邊 3px + 底部 80px margin

### 已知陷阱
- 若字型路徑錯或檔案壞 → ffmpeg subtitles filter 會 silent fallback 到醜字型
- 已加 magic bytes 驗證，下載假字型會立即報錯（之前踩過 NotoSansSC HTML 假檔的雷）

---

## 與其他 Skill 的銜接

### 上游
- `音控師 Skill`：必須先跑 `tts` 產出 `tts_timing.json`
- `剪輯師 Skill`：產出帶人聲的影片（音訊與字幕時間軸對齊）

### 下游
- `VERIFY Skill`：讀 SRT 跟 script.json text 比對「字幕準確率」維度
- 最終成片

---

## 不在這個 Skill 範圍內的事

避免邊界蔓延，這些不歸字幕師管：

| 不做 | 該誰做 |
|------|--------|
| TTS 時間軸計算 | 音控師（tts 指令） |
| 從音訊轉譯產生字幕 | `subtitle` 指令（Whisper），但路線 A 下用不到 |
| 雙語字幕 / 翻譯 | 編劇 Skill 寫 script 時就要決定 |
| 字幕樣式動態調整（按段落變色等） | 剪輯師最終組合時做 |

---

## 已知陷阱

### #9 字幕切句邊界
原始 ffmpeg-pitfalls：「LLM 產的字幕可能在句子中間切斷」  
**本實作不存在這問題**：phrase 來源是 `split_by_punct()`，切點一律在標點後。

### #14 ffmpeg freetype（已解）
macOS Homebrew ffmpeg 缺 freetype → 中文字渲染失敗。  
**本環境**：WSL 用 yt-dlp 的 FFmpeg-Builds 靜態 binary，內含 freetype，無此問題。

### NotoSansSC 假檔（已解）
GitHub LFS 直接下載 .otf 可能是 HTML 頁面。  
**已修**：burnsub 開頭驗證 TrueType magic bytes（OTTO / 00010000 / true）。

### 長句子顯示
若一個 phrase 超過 25 字，在 1080p 畫面上字幕會跨兩行（自動換行），時長未必夠讀完。  
**建議**：編劇寫腳本時，標點之間不要超過 20 字。

---

## 實測結果（2026-05-24）

| 測試 | 結果 |
|------|------|
| v2 腳本 89.5s 生成 SRT | ✅ 28 phrases，0ms 漂移 |
| 燒入 v2 視覺 | ✅ WQY Microhei，白字黑邊，可讀性高 |
| 句子邊界 | ✅ 100% 在標點後切 |

---

## 對應的 vault 文件
- `projects/video-agent-pipeline/roadmap.md` Phase 3
- `projects/video-agent-pipeline/skill-interface-contracts.md` — subtitles.srt 規範
- `projects/video-agent-pipeline/ffmpeg-pitfalls-reference.md` — #9 / #14 / #26
- `projects/video-agent-pipeline/tool-verification-log.md`
