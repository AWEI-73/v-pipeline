# Audio Mix — 非零起點 speech-aware ducking 修復

Date: 2026-07-16
Owner zone: `video_pipeline_core/audio_mix_plan_executor.py`,
`tests/test_audio_mix_plan_executor.py`
Trigger: Canon 67 385 秒端到端候選片真實 forward test

## Observed structural failure

當 speech-aware 音樂 placement 從非零 timeline 時間開始時，executor 把
絕對 timeline speech window 直接交給已 `asetpts=PTS-STARTPTS` 的局部音軌
filter。結果 ffmpeg 的 `t` 是 placement-local，但 ducking expression 是
absolute；真實輸出未在預期窗口 duck，protected-speech waveform recovery
因此失敗。

同一分支還把原始 `volume` 改為 `1.0`，使長片分段 BGM 遺失核准的低音量
基準。

第一次修正後的真實長片 forward test 又揭露第二個同源問題：`amix`
使用動態 normalization，再以固定 input count 反乘；前段 placement 結束後
active input count 改變，受保護語音因此被放大約 `+4.4 dB`。固定時間軸
composition 必須使用固定 mix scale，不能隨已結束的 placement 改變。

## Acceptance

1. RED true-shape test covers a non-zero-start music placement, full-timeline
   protected speech, and a baseline music volume below 1.0.
2. ffmpeg expression uses placement-local speech windows while evidence remains
   in absolute timeline coordinates.
3. `applied_volume` preserves the requested baseline volume.
4. Actual mix applies `baseline_volume × speech_envelope`.
5. Protected speech waveform check passes in the true-shape test.
6. Non-overlapping consecutive music placements do not change protected-speech
   gain after an earlier placement ends.
7. Existing audio-mix tests pass.
8. Re-run the frozen Canon 67 mix once into a fresh output root; do not overwrite
   the failed evidence.

No gate weakening, tolerance change, private renderer or acceptance waiver is
allowed.
