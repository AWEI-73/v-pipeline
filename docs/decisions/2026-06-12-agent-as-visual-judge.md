# 2026-06-12 — 視覺裁判改為「主責 agent 親眼看」(agent-as-judge)

## 決策

**放棄「升級視覺裁判」的兩條傳統路**(本地 4b 留任 / 接雲端 vision API),
改為:**判讀點由引擎產出蒙太奇證據後暫停,駕駛中的主責 agent(或其調用的
subagent)親眼看圖、寫回裁決檔,再 resume。**

```text
引擎(確定性)跑到判讀點
  → 產出證據:每支素材一張「場景中點+時間戳烙印」蒙太奇(keyframe_grid 機具,c508f73)
  → 寫 visual_review_request.json + state.next_action = await_visual_review
  → 暫停
主責 agent(video-pipeline skill 規定的步驟;可派 subagent)
  → 讀蒙太奇圖(frontier 模型讀圖,引用格上時間戳)
  → 寫 visual_review_verdict.json(每段:接受/拒絕、選哪些窗、理由)
  → runtime resume
引擎消費 verdict 繼續(裁剪/渲染照舊確定性)
```

## 為什麼

1. **裁判品質**:4b 的 false negative 是實證連環案(注水/辦公室/廚房畫面全
   命中卻打 10 分,D5);蒸餾救援/floor/重試都是在補償弱裁判。駕駛 agent 本身
   就是迴圈裡最強的視覺模型,且**已經在做這件事**(skill-smoke/city-lite 的
   keyframe 複核就是 agent 讀圖抓到字幕 PlayRes 缺陷)。本決策只是把非正式
   慣例升格為正式 gate。
2. **零 API 管理**:無 key、無計費、無上傳第三方(學員素材隱私自動解決)。
3. **成本形狀正確**:蒙太奇批次 = 一支素材一張圖;整個 run 的 BUILD 側判讀
   **合併成一次暫停**(先抓完所有 stock、出齊所有蒙太奇,再停一次),不是逐段停。
4. **架構零新概念**:await_visual_review 與 await_material / await_capcut_export
   是同一個 WAIT 模式;verdict 檔與 manifest/state 同一套稽核軌。

## 模式開關(build_profile.visual_judge)

```text
agent   (目標預設)引擎不內嵌呼叫模型;判讀點=證據+暫停+verdict。
ollama  今日行為(4b 內嵌 gate),降級為「無人值守 autopilot」模式;
        蒸餾救援/off-topic floor/候選重試全保留,作為這條路的保險絲。
none    跳過內容判讀(僅機械審計)。
```

## 判讀點盤點(遷移順序)

```text
V1 stock 選窗(mv 鏈 _plan_stock_segment)   — 量最大、誤殺最多 → 先做
V2 narrative prepick gate(video_pipeline)  — 同 V1 模式
V3 Node 12 content_qa                       — agent 讀成片 grid 寫 verdict
                                              (與 editorial_qa 既有「主流程強模型
                                              複核」規格合流,幾乎是免費的)
素材 ingest(caption-meta)                  — 同模式:每支素材一張蒙太奇 →
                                              agent 寫語意地圖(=長素材理解設計)
```

## 實作備註

- 引擎側改動落在 mv_cut / video_pipeline / dashboard_state(next_action)/
  runtime(await 分支)——**mv_cut 現在 Codex E 批次 WIP 中,V1 排在其落地後**。
- verdict 檔形狀:`{clips:[{segment, accept, picked_windows:[{start,end}],
  reject_reason?, notes}]}`;request 檔帶 montage 路徑 + verify_desc + 候選窗表。
- runtime 在 await_visual_review 時印出:蒙太奇路徑清單 + verdict 檔範本 +
  「讀圖→寫檔→resume」三步指示(與 revise:director 餵工作清單同風格)。
- 駕駛 agent 可派 subagent 讀圖(入口 skill 明文允許),但 verdict 責任在主責 agent。
