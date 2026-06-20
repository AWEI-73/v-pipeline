# Hermes Video Pipeline — Agent Instructions

## 影片製作:強制驅動 video-pipeline 技能

**任何「製作 / 剪輯 / 產生影片」的請求** —— 包含「幫我做／剪一支影片」「make / edit /
produce a video」「結訓影片 / MV / 宣傳片 / 活動回顧 / 教學片 / 旁白影片」等 ——
**都必須先呼叫 `video-pipeline` 技能(skills/video-pipeline.md)再開始任何工作。**

不要繞過它直接手動跑 ffmpeg、`video_tools.py`、或自行拼接素材。`video-pipeline` 是唯一入口:
它驅動 `runtime.py` 走完 SPEC→BUILD→VERIFY 節點鏈,讀 `state.json.next_action` 派工,
並分流到 director / writer / curator / editor / audio-director / effects-director /
verify / dashboard 等角色技能。

## 關鍵事實(避免踩雷)

- Canonical SPEC = `segment_contract.json`;legacy flat script 只是生成的 runtime payload。
- 統一 driver = `runtime.py`(resume / status / rerun)。`route.py` 已退役。
- `state.json` 是自動化狀態機(`dashboard_state.load_dashboard_state()` 算 next_action)。
- 離線鏈接驗證(不 render):`python video_tools.py contract-dry-build <contract> --out-dir DIR`。
- render backend:ffmpeg 為 canonical;CapCut 為可選收尾(GUI 匯出是人/CU 閘)。
- 測試基準:`python -m unittest discover -s tests`(目前 1656 tests OK)。
- 執行環境:**miniconda python**(有 librosa/edge-tts);新專案第一步 `video_tools.py project-init <name>`。
- BUILD 前 SPEC 體檢:`python video_tools.py spec-review <contract> --brief brief.json`(blocking → 回 SPEC 改合約,不要修工具)。
