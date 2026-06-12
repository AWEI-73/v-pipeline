# Hermes Video Pipeline — 體系設計(node / skill / tool)

> 自包含文件:不需要看 code 也能理解整套系統。寫作原則是**誠實**——
> 每個能力都標注「已實證 / 已實作未充分驗證 / 鷹架 / 已知缺口」。
> 更新:2026-06-12。測試基準:598 unit tests 全綠。

## 一、這是什麼(以及不是什麼)

一套 **AI agent 驅動的影片自動剪輯生產線**,跑在 Windows 本機
(Python + ffmpeg + 本地 Ollama VLM,可選 CapCut 人工收尾)。

**是**:
- 從「一句話需求」到「通過驗收的成片」的可恢復、可稽核流程;
- 多 agent 協作的工作底盤(Claude / Gemini / Codex 都實際在上面施工過);
- 「合約優先」:每段素材答得出「為什麼選它、哪來的、過了哪些檢查」。

**不是**:
- 不是剪輯軟體(沒有 UI 時間軸;CapCut 是可選的人工收尾出口);
- 不是雲服務(local-first,唯二外部依賴:Pexels/Pixabay 素材 API、edge-tts);
- 表現力尚未到商業片水準(見「已知缺口」——靜照+字幕段仍有「簡報感」)。

## 二、核心哲學(三條,全部有反例教訓支撐)

1. **SPEC 是合約,不是 prompt。** 需求收斂成 normalized JSON
   (`segment_contract.json`,core + 專業 facets,每個 facet 帶 `reason`)。
   太鬆 → BUILD 亂猜;模板填充 → 有「敷衍偵測」gate 直接擋下。
2. **工具確定性,品味在 skill。** Python 工具只做純計算與 I/O,零判斷;
   創作判斷(選材、節奏、文字)寫在 markdown skill 契約裡,由 agent 執行。
   同一份 skill 可被任何能讀 markdown、跑 shell 的 agent 平台使用。
3. **state 驅動,router 在 pipeline 外。** 引擎是「單次確定性執行」;
   `state.json.next_action` 是唯一派工依據,`runtime.py` 讀它決定下一棒。
   所有等待(等素材/等生成圖/等 CapCut 匯出/等視覺裁決)都是顯式 WAIT 狀態,
   隨時可 resume,不會跑一半丟失進度。

## 三、Node 鏈(執行順序與驗收閘)

定義在 `node_registry.py` 的 `NODE_ORDER`;每個 node 掛一個 `verify_fn`,
由 `dashboard_state` 自動評估(done/warn/blocked/missing)→ 聚合出 `next_action`。
**少掛一個 gate 程式直接報錯**——「每個 node 都有驗收」是框架強制的不變式。

| Node | 層 | 產物 | 驗收閘(摘要) |
|---|---|---|---|
| 0 | SPEC | brief.json | 存在 |
| 3 | SPEC | segment_contract.json | schema 驗證 + **spec_review**(見下) |
| 2 | SPEC | material_coverage_map.json | 覆蓋率(stock_first 模式可免) |
| 4-7 | SPEC | contract 六 facets | facets+reasons 齊全 |
| 5 | SPEC | music_structure.json | librosa 節拍分析完成 |
| 8 | route | build_profile.json | profile 合法 / 等生成素材 |
| 9 | BUILD | assembly_plan.json | 計畫存在(含 treatment/shot_slots) |
| 10 | BUILD | timeline_build.json | 每個 clip 有出處 trace |
| 11 | REVIEW | editor_review + 6 項確定性審計 | 決策=approve |
| 13 | DELIVERY | final.mp4(或 CapCut draft) | 已渲染 |
| 12 | VERIFY | verify_result + 審計包 | 技術 QA pass(門檻 80) |
| 14 | ITER | revision_plan / effects 產物 | 只在失敗或特效啟用時 |

**BUILD 前總體檢(spec_review,Node 3 附屬)**:跨 brief+contract 的可執行性
檢查,規則全部來自真實事故(非理論):pacing 自相矛盾、must_include×stock
會靜默掉段、subtitle:auto 配無人聲必得 0 分、CG-bait 搜尋詞、缺 target_length、
mode 推斷陷阱、**敷衍偵測**(全段 pacing 相同/描述複製貼上/佔位 reason,
≥3 訊號共現直接 blocking)。blocking → 回 SPEC 改合約,不進 BUILD。

## 四、Skill 層(17 個角色契約,markdown)

| 類 | skill | 職責 |
|---|---|---|
| 入口 | **video-pipeline** | 唯一強制入口;驅動 runtime、讀 next_action 派工 |
| SPEC | video-workflow / blueprint-interview / spec-contract / director / writer / shooting-brief | 模糊消除→brief→敘事藍圖→合約;facet 各有擁有者 |
| BUILD | curator / editor / audio-director / subtitle-director / effects-director / generative-director | 找料評分 / 組裝 / 配樂混音 / 字幕 / 特效 / 生成素材 |
| 控制 | route / gap-analyzer / dashboard / verify | 派工表 / 缺口路由 / 人類可視化 / 驗收 |

skill 裡累積了**踩坑記錄**(每條都是真實事故+規避法),等於把製程知識
固化給下一個 agent。例:director 的「develop 段別填 establishing(會變一鏡
到底)」、curator 的「搜尋詞寫看得見的物理場景,抽象詞是 CG-bait」。

## 五、Tool 層(確定性引擎,Python)

- **driver**:`runtime.py`(run/resume/status/rerun)——唯一入口,前代
  `route.py` 已退役。`video_tools.py` 是 60+ 子命令的工具箱(可單獨呼叫)。
- **兩條渲染鏈**(同一份 canonical contract 經 adapter 餵入):
  - **MV 鏈**(音樂驅動):節拍→切刀網格;brief 的 target_length 裁總長。
  - **narrative 鏈**(口白驅動):TTS 時長=時間軸 ground truth;素材配口白、
    字幕由 TTS timing 生成、BGM crossfade-loop 裁到口白長。
- **素材處理**(「素材是庫,不是段」):一支下載素材開多個時間窗、
  一張照片展開多個 crop/push 鏡頭;場景偵測(PySceneDetect)+ 對拍切點吸附。
- **離線驗證**:`contract-dry-build` 不渲染、不下載,直接物化 Node 8-11
  artifacts 驗整條接線(秒級)。

## 六、素材來源合約(三源 + 誠實規則)

```
source = stock(Pexels/Pixabay)| local(使用者/學員自有)| generated(AI 產圖)
```
- **誠實規則(硬性)**:must_include / identity / proof 段**禁止** stock 與
  generated 替代——寧可停下要求補拍,不靜默用泛用素材冒充真實。
- generated 產物永久標記 `forbidden_as_truth`,manifest 記錄出身;
  request 的 prompt 標記「種子,須經 token-stack 擴寫」防止裸描述直餵圖模型。

## 七、視覺判讀體系(三代演進,現役=agent-as-judge)

1. **本地 4b VLM 內嵌 gate**(第一代):便宜但實證誤殺率高
   (多子句中文描述會被逐條摳字判否)。加了主詞句蒸餾救援、off-topic
   絕對低標、候選自動重試三層補償後堪用。**保留為無人值守 autopilot 模式**。
2. **確定性審計**(一直都在):時長/重疊/音量/黑幀/b-roll 比例/字幕對齊/
   視覺疲勞/treatment 合規——機械規則,毫秒級,不依賴任何模型。
3. **agent-as-judge(現役預設)**:引擎在判讀點產出「場景中點+時間戳烙印」
   蒙太奇圖並暫停(`await_visual_review`);**駕駛中的 frontier agent 親眼
   讀圖**寫裁決檔再 resume。一個 run 只停一次(批次)。已實戰一輪:
   agent 一眼拒掉「關鍵字命中但概念全錯」的素材——4b 會放行的那種。
   無 API 費、素材不出本機(學員隱私)。

## 八、已實證的能力(有 run 記錄與數字,非宣稱)

| 實證 | 數字 |
|---|---|
| MV 鏈 35s 全 stock 成片 | verify 91.5 PASS、editorial_qa 94、目標 35s 實出 34.4s |
| narrative 鏈 5 分鐘 21 段口白片(TTS+BGM+字幕) | 297.6s、qa 88.6、誠實判 3 段需補拍並給指引 |
| canonical contract → 口白片 | qa 97 |
| 字幕視覺(置中下/去標點/子句斷行) | 成片抽幀人眼驗證 |
| spec_review 對真實合約的攔截 | 多次正確 blocking(含攔住寫合約的 agent 本人) |
| agent-as-judge 完整迴圈 | 蒙太奇→裁決→resume→「approved windows」重建 |
| 生成素材線(請求→等待→回填) | 走到 wait gate,閉環驗證進行中 |

## 九、誠實的現狀分級

**已實作、驗證薄**(跑過但樣本少):CapCut draft 的 text/audio 軌
(GUI 載入驗過一次)、html_playwright 資訊卡 MVP(一個配方)、
照片多幕展開、注意力預算進 BUILD 分配。

**鷹架階段**(架子在、內容少):motion_graphics 特效配方庫
(E1 基準實測:7 個 planned effects 0 個 rendered → 正在補配方)、
素材蒙太奇理解(E7 進行中)。

**已知缺口(設計上承認,未解)**:
- **表現力天花板**:畫面內動態/合成仍弱,靜照+字幕段有「簡報感」——
  這是當前主攻方向(特效階段)的存在理由;
- **單一 BGM 軌**:無章節換曲(概念欄位有、render 不消費);
- **長素材理解**:30 分鐘原始錄影找亮點還不行(設計已定:蒙太奇語意地圖);
- **narrative 鏈核心是 legacy 引擎**:canonical contract 經 adapter 餵入可用,
  但內部未重構,soul 層(treatment/pacing 文法)只有 MV 鏈完整消費;
- **環境脆性**:綁 miniconda python(librosa/edge-tts)、Windows 路徑慣性、
  ffmpeg 4.3 的若干濾鏡怪癖(已逐一繞開但未升級);
- **無 UI**:審查靠 dashboard HTML(唯讀)+ agent 讀圖;「審查+補丁面板」
  (換候選/調窗寫回)是規劃中、未動工。

## 十、與市面工具的差異(克制版)

市面 AI 剪輯工具(含 agent 操作 CapCut 類 skill)的強項是單線體驗;
本系統的差異不在剪輯本身,在**生產線屬性**:可恢復(任意點 resume)、
可稽核(每刀有出處與檢查記錄)、可協作(多 agent 在同一狀態機上接力)、
誠實性(生成/實拍分離、缺料停下而非冒充)。代價是上手複雜度與
表現力暫時落後——這是有意識的取捨,不是還沒發現。
