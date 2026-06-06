---
name: editor
description: 剪輯師 Skill。依 TTS 時長把每段素材剪到精確長度，scale 統一 1920x1080，concat 成 rough_cut.mp4；最終再把音軌 + 字幕合進去產出成片。只做檔案層級操作（不做內容理解，那是小編的事）。
---

# Editor Skill

> **Canonical-first runtime(see roadmap.md):公開 SPEC 輸入 = `segment_contract.json`。**
> legacy flat script 只能當 adapter 生成的 runtime payload,**不可當 canonical**(見 `contract_adapter.py`)。
> Upstream: contract bundle / assembly_plan;Owns: shot selection + EDL + render;
> Downstream: `build_profile.json` / `generated_asset_requests.json` / `assembly_plan.json` /
> `timeline_build.json` / `artifact_manifest.json`;VERIFY hooks: EDL trace、規格、必放、無靜默 fallback。

> ## Assembly Plan / Shot Selection Contract(Node 9 — contract→execution 交接)
> 吃 Node 1-8 的 contract bundle + 候選 + fallback_route → 產 `assembly_plan`(每段:
> `selected_shots`[source/in/out/duration/order/selection_reason/satisfies{must_include,
> proof_fit,story_fit,audio_fit,text_fit,visual_fit,continuity_fit}/confidence] +
> `rejected_candidates`[+rejection_reason] + `unresolved_requirements` + `execution_route`)。
> **候選排序鐵則:** ①must_include 凌駕畫質(除非不可用)②proof 段 proof_fit 凌駕美感
> ③原音關鍵時 audio_fit 凌駕純音樂偏好 ④文字段顧 text_fit 可讀性 ⑤continuity_fit 防重複構圖/跳接
> ⑥visual_fit 只在前述都滿足後當 tie-break。
> `execution_route.status ∈ ready / needs_fallback / needs_collection / needs_reshoot / needs_review / blocked`。
> **Node 9 不創造新創作意圖**;contract 衝突/無法執行 → route 到 fallback/rewrite/collection/review,不亂猜。
> 必須保留 selection reason 與 rejected alternatives(可稽核)。
>
> ## Timeline Build / Edit Decision List Contract(Node 10 — 執行,非重解釋)
> 吃 `assembly_plan`(ready)→ 產 `timeline_build`/EDL:`settings`(fps/res/sample_rate/target_dur)
> + `items`[source_in/out、timeline_in/out、`track`∈video_main/video_overlay/audio_original/
> audio_music/audio_voiceover/text_overlay/effects、text_overlay、transition、effects、audio_mix、
> 每 item `trace` 回 segment_contract]。**鐵則:Node 10 是執行不是重解釋**——可解機械時間細節,
> 但不得換選段/丟原音/改文字語意/壓 locked 段/套未核可 fallback,除非更新 route + review 狀態。
> (現行 `mv_cut` 的 plan/render_mv_audio 是此契約的 MV 實作;EDL 為其正規化表述。)
>
> ## Render / Export / Delivery Contract(Node 13 — 不可重解釋 timeline)
> 吃驗過的 `timeline_build` → 產交付物 + manifest。`render_mode ∈ preview / review / final /
> segment_debug`。合約欄位:artifact 種類、resolution/fps/codec/audio settings、字幕 burn-in/
> sidecar/both/none、輸出夾/log/縮圖/report 位置、版本命名、來源 timeline/build id、post-render 檢查、
> delivery 狀態。**鐵則:render 不得重解釋 timeline**——若無法照 timeline 執行,必須 fail 或 route 回
> timeline build/review,不得靜默改媒材/字幕/音訊/時長。post-render verify(Node 12)查 artifact 真的
> 可播/規格對/非空白。

剪輯師負責「檔案層級」的影片組合：剪、scale、concat、套音軌、燒字幕。  
**邊界原則（方案 A，2026-05-24 確定）**：剪輯師不做內容理解（不跑 Whisper、不打分、不選素材），只執行小編給的清單。

---

## 工具位置

```
/home/lio730309/.hermes/profiles/video_director/workspace/video_tools.py
```

兩個指令：
```bash
python3 video_tools.py assemble    --clips clip_list.json --timing tts_timing.json [--out rough_cut.mp4]
python3 video_tools.py merge-final --visual VIDEO --audio AUDIO --subs SRT [--out final.mp4]
```

---

## 對應命令
* `[[cmd_cut]]` - 裁剪影片片段（依 start/end 裁剪）。
* `[[cmd_concat]]` - 串接多個影片段落，自動統一解析度至最大尺寸。
* `[[cmd_burnsub]]` - 把 .srt 字幕燒進影片（自動尋找 CJK 字型）。
* `[[cmd_script_run]]` - 劇本驅動全自動剪片（編寫/下載/接合/燒字幕全自動流程，舊版 Streamlit 等效）。
* `[[cmd_title]]` - 在影片上疊加標題文字。
* `[[cmd_assemble]]` - 剪輯師粗剪：依 timing 與 clips 進行裁剪、縮放、並接合產出 rough_cut.mp4。
* `[[cmd_merge_final]]` - 最終合成：結合純視覺影片、音訊檔與字幕 SRT，生成最終成片 final.mp4。
* `[[cmd_kenburns]]` - 照片動畫：把靜態照片變成有 Ken Burns 推鏡的 1080p 影片。

---

---

## 流程

```
clip_list.json (小編輸出) ──┐
                            │
tts_timing.json (音控師) ───┤
                            ▼
                       [assemble]
                            │
                            ▼
                    rough_cut.mp4 (純視覺，無音軌)
                            │
final_audio.wav (音控師) ───┤
subtitles.srt (字幕師) ─────┤
                            ▼
                      [merge-final]
                            │
                            ▼
                       final.mp4 (成片)
```

---

## 指令 1：assemble

### 用法
```bash
python3 video_tools.py assemble \
  --clips /workspace/clip_list.json \
  --timing /workspace/audio_out/tts_timing.json \
  --out /workspace/rough_cut.mp4
```

### 做什麼
對 `clip_list.json` 裡每段素材：
1. 從 `cut_start_sec` 開始
2. 剪 `tts_timing[segment].duration_sec` 秒（或 `cut_end_sec` 指定）
3. scale 到 1920x1080 + 黑邊 padding（保持原比例不變形）
4. 強制 30fps + CFR + setsar=1（避免坑 #5/#16 concat 時間戳跑掉）
5. 移除原音軌（避免跟 TTS 打架）

最後把所有段 concat。

### 輸出
- `rough_cut.mp4` — 純視覺，總時長 ≈ TTS 總時長
- `rough_cut_edit_log.json` — 每段實際時長、漂移統計

### edit_log.json 範例
```json
{
  "output": "/workspace/rough_cut.mp4",
  "total_duration_sec": 89.599,
  "segments": [
    {
      "segment": 1,
      "source": "/workspace/materials/seg1.mp4",
      "cut_start_sec": 0.0,
      "tts_target_sec": 18.552,
      "actual_sec": 18.62,
      "duration_diff_ms": 68.0
    }
  ]
}
```

`duration_diff_ms` < 50ms 都算合格，超過要查素材是否 keyframe 太稀疏。

---

## 指令 2：merge-final

### 用法
```bash
python3 video_tools.py merge-final \
  --visual /workspace/rough_cut.mp4 \
  --audio /workspace/final_audio.wav \
  --subs /workspace/subtitles.srt \
  --out /workspace/final.mp4
```

### 做什麼
1. 把 `final_audio.wav` 取代 `rough_cut.mp4` 的（空）音軌
2. 用 ffmpeg subtitles filter 把 `subtitles.srt` 燒進畫面
3. 用 `-shortest` 避免音視頻長度不一致時拖尾
4. 強制 30fps CFR + 48kHz stereo + AAC 192k（依坑 #30 相容性規格）

字型：WQY Microhei（`~/.local/share/fonts/wqy-microhei.ttc`），開頭驗證 TrueType magic bytes，避開假字型雷。

---

## 邊界：剪輯師「不做」什麼

| 任務 | 該誰做 |
|------|-------|
| YouTube 搜尋 / 下載 / metadata | 小編 |
| Whisper 轉譯 / 找最匹配時段 | 小編 |
| BGM 混音 | 音控師 |
| SRT 時間軸計算 | 音控師（tts）→ 字幕師（srt） |
| 字數驗證 / 評分 | VERIFY |

剪輯師只執行「給我檔案路徑跟時間，我剪我接」。  
這個邊界讓未來小編加 Vision API 不會碰到剪輯師。

---

## 已知陷阱

### #5 codec 不一致
不同來源的素材 codec 可能不同，直接 concat 會跑掉。  
**本實作**：每段先用 `libx264 -r 30 -vsync cfr -c:v libx264` 統一輸出再 concat。

### #11 直橫比混搭
9:16 直片混 16:9 橫片視覺很跳。  
**本實作**：`scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2` 統一輸出 16:9，直片自動加左右黑邊。

### #16 Non-monotonic DTS
concat 時 ffmpeg 警告，可忽略，不影響播放。

### #18 xfade 黑幕（未踩）
本實作刻意只用 concat demuxer，不串接多個 xfade，避開這個雷。  
若未來要加淡入淡出轉場，必須改用其他方式。

### #30 相容性輸出參數
merge-final 強制 `-r 30 -vsync cfr -ar 48000 -ac 2`，確保 Premiere/CapCut 等剪輯軟體能讀。

---

## 實測結果（2026-05-24）

| 測試 | 結果 |
|------|------|
| 4 段素材 assemble | ✅ 89.599s，drift -1.0ms |
| merge-final 套音軌 + 字幕 | ✅ 89.498s，H264+AAC，1920x1080 |
| 跟舊版 test script 比對 | ✅ 視覺一致，pipeline 等效 |

成品：`workspace/v3_skill_final.mp4`

---

## 對應的 vault 文件
- `projects/video-agent-pipeline/roadmap.md` Phase 1
- `projects/video-agent-pipeline/skill-interface-contracts.md` — clip_list.json 格式
- `projects/video-agent-pipeline/ffmpeg-pitfalls-reference.md` — #5 / #11 / #16 / #18 / #30
