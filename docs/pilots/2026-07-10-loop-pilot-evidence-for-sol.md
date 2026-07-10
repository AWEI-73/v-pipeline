# LOOP 首航證據包（交 SOL 規劃下一輪）

日期：2026-07-10
性質：手動 L0＋L1 價值實驗的完整證據與需求交接。實驗由 owner 裁決、
Claude(Fable) 擔任人肉 loop driver，全程零 route runner、零 repo 產線
程式碼修改。本文件為 SOL 規劃後續工單的事實基礎。

## 1. 實驗設計與判定

- 命題：同素材池、同音樂、同渲染器之下，「感知選材＋人工文本紀律＋
  人的裁決」能否讓 0:00–0:44 開場成片可辨地變好？
- 對照組：2026-07-10 route 版切片（TERRA，`catalog[0:16]` 選材）。
- 判定：**成立**。owner 實看後 verdict＝本階段通過（殘餘 finding f1）。

| 指標 | 對照組 | LOOP v1 |
|---|---|---|
| 開場鏡頭 | 舞台三人照(pillarbox) | 桿場空拍建立鏡頭(影片) |
| 蒙太奇視覺家族 | 1 | ≥12 |
| 詩卡文字 | 錯字＋三行疊影 | 零錯零疊影 |
| 卡點 within-1-frame | 1.0 | 1.0（維持） |
| 時長 / rendered QA | 44.024s / pass | 44.024s / pass（維持） |
| 文本來源 | 感知轉錄（污染） | owner 批准之劇本檔 |

## 2. 證據清單（全部可獨立核驗）

劇本／文本源（fail-closed 唯一來源）：
- `docs/pilots/2026-07-10-opening-0044-script-v1.md`（狀態 APPROVED，
  owner 三項裁決記錄在檔頭）

選材層：
- `.tmp/loop_pilot_0044/selects_{AER,GA,SPT,TWR,ACT,LIF}.png`（6 張
  帶索引候選表，135 格）
- `.tmp/loop_pilot_0044/selects_manifest.json`（代號→素材相對路徑）
- `.tmp/loop_pilot_0044/accepted_flat.json`（222 個 accepted 資產攤平）
- 選材決定：AER01 建立鏡頭＋15 張三樂章（記錄於 provenance）

成片與門檻：
- `.tmp/loop_pilot_0044/candidate_v1/run/final.mp4`（44.024s，
  H.264 1920x1080＋AAC）
- `.tmp/loop_pilot_0044/candidate_v1/beat_cut_alignment_report.json`
  （within_one_frame_ratio=1.0）
- `.tmp/loop_pilot_0044/candidate_v1/rendered_qa/rendered_product_qa.json`
  （pass=true, blocking=0）
- `.tmp/loop_pilot_0044/candidate_v1/run/title_effect_lifecycle_qa.json`
  ＋ `run/lifecycle_contact_sheet.jpg`（字卡正確性之視覺證據）
- `.tmp/loop_pilot_0044/candidate_v1/source_provenance.json`
  （selection_mode=owner_delegated_agent_selects、script_source 指向
  劇本檔、orientation_corrected 逐張記錄、reference film 未使用）

感知複驗：
- `.tmp/loop_pilot_0044/candidate_v1_perception/`（coverage pass、
  gap 0、牆 5 頁——蒙太奇多樣性之機器可核證據）

對照組證據（品質失敗根因）：
- `.tmp/canon_67_opening_slice_acceptance/run/lifecycle_contact_sheet.jpg`
  （錯字疊影實況）
- `.tmp/canon_67_opening_slice_acceptance/run/edit_decision_plan.json`
  （詩卡窗口重疊根因：11.2/13.2/15.2 全部收在 18.0、同一錨點）
- `video_pipeline_core/graduation_opening_slice.py:414`
  （`catalog[0]`/`catalog[1:16]`——無選擇之選材）

Driver 使用紀錄（未來 loop_driver 的需求來源）：
- `docs/pilots/pilot-driver-v1-usage-log.py`（本輪人肉 driver 全文，
  非產線程式碼；它手工完成的每件事＝driver MVP 功能清單）

## 3. Findings 佇列（帳本）

| # | Finding | class | owner_capability |
|---|---|---|---|
| f1 | 樂章三收尾三張同場地（SPT08/10/13）重複感 | taste | picture（下輪 L1） |
| f2 | 打字機缺「快打完＋hold」節奏把手 | objective | text/L4 |
| f3 | 文字樣式僅中央大字，無小字/角落樣式 | objective | text/L4 |
| f4 | 候選表編號因 EXIF 旋轉錯位（LIF17→揹人）；牆/表需吃 EXIF | objective | perception/L0 |
| f5 | 「廣場邊框論」：字卡系統＝靈魂載體，L2/L4 模板家族立案依據 | taste→strategy | effects+text |

## 4. Driver MVP 需求（從使用紀錄提取，非猜測）

人肉 driver 本輪被迫手工完成、應固化的動作：
1. selects 代號 → 帶 lineage 的資產紀錄（照片/影片分流、
   media_duration probe、EXIF 轉正拷貝）
2. opening_sequence 組裝（clip 排程、overlay 接續窗口、hard-cut 表）
3. 依序呼叫能力庫：compose → compile → render → 卡點/lifecycle/QA
4. 產出 provenance（selection_mode、script_source、逐張 correction）
5. 每輪 verdict 後的段落級重做（本輪未觸發，f1 將是第一個用例）

明確不做：狀態機、next_action 詞彙、跨 session 持久化（timeline＋
session log 之外）、自主迭代（每輪必須有人裁決）。

## 5. 建議之後續工單（SOL 定奪）

A.（先行，小）TERRA 分支 closure：artifact dictionary 登記
   `render_handoff.json`、兩支 tools 的 skill ownership、提交停損時
   未提交之 Piece 5 與精度修復、確認後清除根目錄殘渣 `r`、
   重跑 focused＋full suite。精神同 2026-07-09 cleanup 慣例：
   新 tool/artifact 之申報應劃入同一 owner zone（三次同類失敗的
   結構修正，已寫入 loop spec §6）。
B. loop_driver MVP：以 §4 清單為範圍、
   `docs/construction-guides/2026-07-10-editing-loop-product-spec.md`
   為終態參考。驗收＝用 driver 重跑本輪同輸入，產物等值＋f1 修正輪
   可在 driver 內完成。
C. findings f2–f4 各自入對應能力庫的小單。

## 6. 遙測與成本觀察

- Owner 裁決次數：3（劇本 1、選材委任 1、成片 verdict 1）；
  每次數分鐘級。
- 中途錯誤：2（import 名、影片素材分流），均為資料層，數分鐘修復。
- Token 形狀：感知資產全程復用（正典牆、候選表一次生成多次引用）、
  單次渲染一次過、無工單/報告/全量測試的往返稅。與 route 世界同段
  0–44s 產出相比（多張工單＋報告＋二次全量suite＋stop-loss 往返），
  本輪成本量級明顯更低——「多段 LOOP＋人在迴圈」的設計意圖被成本
  數據支持。
