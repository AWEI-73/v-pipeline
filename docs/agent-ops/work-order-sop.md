# 工單制 SOP — 多 Agent 施工作業系統

Date: 2026-07-04
定位:這份文件是本 repo 開發體系的操作手冊。照著做,任何守紀律的
agent(Codex/Opus/其他)都能安全地並行施工,擁有者不需要盯著每一步。
實戰紀錄:2026-07-03 一天內,這套制度跑過 5 個 agent、兩輪三方並行、
一次跨流死鎖,零 merge conflict、零未申報偏差。

## 核心循環

```
需求 → [整合者] 盤點現況(工具驗證,不憑記憶)
     → 寫規格/工單(判斷做完,只留機械執行)
     → 產派工 prompt(自包含,新 session 可冷啟動)
     → [施工者] 依工單施工,報告 append 回工單檔
     → [整合者] 獨立驗收(重跑一切,不採信轉述)
     → 通過 → commit 落地;缺口 → 下一張修正工單(增量,不退版)
```

角色鐵律:整合者不施工,施工者不裁決。跨界矛盾只有整合者能裁,
且裁決必須留痕(寫進報告或規格修訂)。

## 工單解剖(每張必備七件)

1. **Goal + 背景**:為什麼做、前情在哪份文件。
2. **Owner zone**:可改檔案的白名單,精確到路徑。
3. **禁改清單**:明列,含「看似需要也不准碰 → 記報告、跳過」條款。
4. **任務**:依序編號;每個任務含「驗收 = 一條有 exit code 的指令」,
   不接受描述性驗收。行為變更必須 test-first(先有紅測試)。
5. **紀律段**:矛盾記錄不自裁 / 不順手優化 / 殘渣清乾淨 /
   卡死停在最後綠燈 commit。
6. **Commit 訊息**:每個任務指定英文祈使句原文。
7. **Evidence 格式**:報告要附什麼(commit hash、測試尾行原文、
   矛盾清單),append 到哪裡。

### Piece 切割的粒度法則

- 一個 piece = **最小可獨立綠燈的可審查單位**。太細會製造無意義的
  commit 噪音;太粗會讓失敗無法歸因。判準:這個 piece 壞了,
  能不能只退它一個?
- **判斷題整合者先做掉**(讀碼、裁決放哪裡、選哪個方案),
  工單裡只留機械題。範例:「14 個未認領 skill 的 owner」是寫死的
  表格,不是「請自行判斷歸屬」。
- **依賴未落地工作的工單不預寫**——會變的規格就是返工的源頭。
  寫「Phase N 綠燈後再產 Phase N+1 工單」。

### 順序法則

- **儀器先行**:大改之前先造可證偽的檢查(audit/test/smoke),
  先 warn 模式、逐族翻 block。
- **加法先於拆除**:先把新的建好共存,測試斷言跟上,才拆舊的。
- **安全網先於搬遷**:檔案要移動前,先讓「引用完整性測試」存在。

## 派工 prompt 固定結構

```text
你是[角色],負責[工單名]。在 <repo路徑> 施工,[並行狀況說明]。

== 閱讀順序(動工前必讀)==
1. <法律級文件(如 API_CONTRACT)>
2. <你的工單路徑> ——唯一施工依據
3. <必要背景(真相來源測試、前輪報告)>

== 環境 ==
測試一律用:%USERPROFILE%\miniconda3\python.exe
(裸 python 是別的 venv,會炸假 import error)

== 圍欄 ==
<owner zone / 禁改清單,從工單複述最關鍵的>

== 紀律 ==
1. 工單沒寫的不做。不順手優化、不重新命名、不風格正規化。
2. 每 commit 前全套測試綠;[前端加:兩個 guard 綠 + 瀏覽器親眼驗證]。
3. 矛盾:工單有指示照工單;沒有 → 記報告、跳過、繼續。禁止自行裁決。
4. 全套測試疑似跟並行 agent 撞暫存/port:focused 重跑 → 全套重跑
   → 才當真。絕不修別人區域讓自己的測試過。
5. 卡死:停在最後綠燈 commit,寫報告收工。不放寬測試、不碰禁區。
6. 收工時 repo 根目錄無殘渣檔案。

== 收工交付 ==
報告 append 到 <位置>,含:commits、測試尾行原文、矛盾/跳過清單。
報告 commit 訊息:<指定原文>
```

要點:**prompt 必須自包含**(新 session 冷啟動可用),所有經驗教訓
寫成條款而不是依賴 agent 記得。UI 類工作必加「眼見為憑」條款
(教訓:曾有 agent 只驗 class 切換沒驗顯示,把壞功能報成通過)。

## 並行規則(不開 branch 的前提)

1. **檔案級互斥**:每條流一個 owner zone,交集必須為空。
2. **共用檔案歸屬表**:熱點檔案(`video_tools.py`、`docs/INDEX.md`、
   `RUNBOOK.md`、`CLAUDE.md`、共用測試檔)逐一指定唯一 owner。
3. **FROZEN 區**:誰都不准碰的清單(入口文件、registry、runtime)。
   注意教訓:凍結區要跟治理測試對照——若某流的任務必然觸發
   「需要改凍結區才能綠」(如新工具需要 skill 歸屬註冊),
   要嘛預先分配,要嘛明示「留給整合者」。
4. **共用報告檔**:append-only、各自段落、不准重排他人內容。
5. **暫存碰撞協議**:見派工 prompt 紀律第 4 條。
6. 唯一的全域同步點是「commit 前全套綠」——任何一方弄壞共同真相,
   會在自己 commit 前被抓到。

## 驗收協議(整合者)

1. **不採信轉述**:報告裡的每個綠燈,自己重跑。focused + 全儀器 +
   全套(全套丟背景並行進行其他審查)。
2. **逐 commit scope 對照**:`git show --stat` 逐一比對 owner zone。
3. **偏差分類**:已申報且必要(如治理測試強制的一行)→ 採納並記錄;
   未申報 → 全部重查該 agent 的工作。
4. **UI 眼見為憑**:結構用 snapshot/eval 驗、視覺用截圖、
   互動實際點過,console 零紅字。
5. **驗收結論落地**:通過 → commit + memory 更新;缺口 → 增量修正
   工單(不退版),缺口若源於規格盲點,由整合者修規格並明說。

## 本 repo 常備儀器(驗收必跑)

```text
set PY=%USERPROFILE%\miniconda3\python.exe
%PY% -m unittest discover -s tests                     # 全套(~10min)
%PY% video_tools.py e2e-smoke --case stock_story
%PY% video_tools.py e2e-smoke --case single_long_highlight
%PY% video_tools.py registry-audit
%PY% video_tools.py interface-audit
%PY% video_tools.py acceptance-contract
%PY% video_tools.py asset-path-audit <run_dir> --strict
%PY% tools\preflight.py --strict
set PYTHON=%PY%
node tools\workbench_browser_layout_smoke.mjs --artifact-root .tmp\wb_accept_fixture
%PY% tools\workbench_frontend_smoke.py --artifact-root .tmp\wb_accept_fixture --exercise-replace
```

## 已知地雷

- 裸 `python` 指到 hermes venv(缺 numpy/soundfile/cv2)→ 54 個假錯。
- PowerShell 5.1 對原生指令用 `2>&1` 會汙染 exit code。
- 並行全套測試可能撞暫存檔(mv render 已修,其他遵守重跑協議)。
- 探跑會在 repo 根產 `supply_review.json` 類殘渣——收工必清。
- guard 的 layout smoke 用自管模式(`--artifact-root`),
  不要自己起 server 餵 `--url`(SPA proxy 會掛住 networkidle)。
