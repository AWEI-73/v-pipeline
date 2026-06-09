# 修復跨平台路徑拼接與品管硬編碼技術債

- 日期：2026-06-09
- 狀態：已完成
- 相關：編排與路由層 (`route.py`)、驗證與品管層 (`vt_verify.py`)

## 背景

在代碼庫檢視與分析過程中，發現了幾項顯著的低風險技術債：
1. **跨平台路徑拼接問題**：在 `route.py` 中，部分路徑是透過簡單的 `f"{args.out}/..."` 字串格式化進行拼接，而非使用 Python 標準的 `os.path.join`，這在混合環境（Windows + WSL）下可能引發斜線方向不一致的隱患。
2. **硬編碼的技術品質品管驗證**：在 `vt_verify.py` 的 `_verify_technical_quality` 中，預期影片解析度和影格率硬編碼為 `1920x1080` 及 `30fps`。當未來需要產出其他解析度或影格率的影片（例如直式短影音 1080x1920 / 60fps）時，會直接導致品管扣分。
3. **MV 模式缺失依賴檢測**：在 `route.py` 中執行 MV 模式時，未預先檢查 `librosa` 等可選的重量級依賴，一旦缺庫，會導致渲染進行到一半才突然崩潰。

## 決策

1. **路徑規格化**：將 `route.py` 中所有以字串插值拼接的路徑更換為 `os.path.join`。
2. **動態載入品質參數**：將 `_verify_technical_quality` 與 `cmd_verify` 改為動態載入。首先嘗試尋找專案運行目錄或劇本目錄下的 `build_profile.json`，若該檔存在且定義了 `target_width`、`target_height` 或 `target_fps`，則動態套用；若不存在，則相容地 Fallback 到原本的 `1920`、`1080` 與 `30`。
3. **可選依賴預檢**：在 `route.py` 的 `main()` 中，若 args 有指定 `--mv`，則預先嘗試 `import librosa, soundfile`。如果缺少該套件，立刻退出並輸出明確的 `pip install` 安裝指引，而非中途崩潰。

## 實作

- 修改 [route.py](file:///c:/Users/user/Desktop/video_pipeline/route.py) 的 `_load_state` 與 `main` 路徑處理。
- 修改 [video_pipeline_core/vt_verify.py](file:///c:/Users/user/Desktop/video_pipeline/video_pipeline_core/vt_verify.py) 的 `_verify_technical_quality` 及 `cmd_verify` 函式。
- 單元測試套件執行 `python -m unittest discover tests -v` 全數順利通過（OK，無 Regression）。
