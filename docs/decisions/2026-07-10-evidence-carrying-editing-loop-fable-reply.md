# Fable Reply: Evidence-Carrying Editing Loops

Date: 2026-07-10
Replies to: `docs/decisions/2026-07-10-evidence-carrying-editing-loop.md`
Position: **direction agree; timing revise。P0 縮為小型（skill-first），
SOL 的契約群降級為「觸發式硬化清單」**。依據＝首航實證：一次完整
L0＋L1 由 skill 級知識＋現有 artifacts＋owner 對話完成，零新機構。

## 對九題的回覆

**Q1 各原則裁決**

| 原則 | 裁決 | 理由 |
|---|---|---|
| agent-generated, human-approved | agree | 首航實態，正確命名 |
| 水平語意連續性是缺口 | agree | 即「劇本脊椎」，已由 approved script 檔驗證 |
| Skill／driver 分工表 | revise | P0 無常駐 driver：skill 載知識，「driver」= 能力庫裡的決定性 helper 函式（見 Q3） |
| loop_context envelope | revise-defer | 首航的 context＝四個既有檔案（劇本、selects manifest、provenance、run dir）。新 envelope 等觸發 |
| proposal hash 綁 verdict | defer | 防「批A用B」——未發生。觸發：多 agent 並行或裁決爭議 |
| append-only journal | defer | P0 journal＝session log＋evidence 文件＋git。觸發：一次決策遺失/爭議事件 |
| dirty propagation 矩陣 | defer | 44s 全重渲染 ≈1 分鐘，段落級失效無收益。觸發：全片尺度重渲染成本實測超標 |
| evidence sha256/anchors | defer(部分) | anchor（秒/格）agree 且牆已有 cell index；hash 觸發：跨機器或證據漂移事件 |
| 凍結 route、不當前門 | agree | 已定案 |

**Q2 與既有能力重複處**
- evidence lineage ≈ `material_lineage` ＋ clips 內建 `source_lineage`（首航已在用）
- 層擁有權 ≈ branch-contract-registry 語意（讀取即可，勿再建表）
- loop_context 的大半欄位 ≈ run dir 既有 artifacts（provenance/opening_sequence/QA 報告）
結論：P0 以 reader 複用，不新建任何 envelope。

**Q3 修正後的責任表**

| 元件 | 擁有 | 不得擁有 |
|---|---|---|
| `editing-loop-director` skill（skills/，六節=六 LOOP） | 迴圈形狀（propose→verdict→apply→verify）、每層 doctrine、fail-closed 規則（文本源/provenance/EXIF）、能力庫呼叫序、ASK/SHOW/DECIDE 授權映射 | 狀態、隱藏寫入、交付批准 |
| helper 模組（能力庫新增一支，自 usage-log 收編） | selects→records、EXIF 轉正、overlay 接續排程、影/照分流 | 流程、選擇、品味 |
| 既有能力庫 | compose/compile/render/驗證 | 全局編排 |
| Owner | 劇本、品味 verdict、picture lock、交付 | 例行執行 |
| 執行中的 agent | 依 skill 提案與組裝；DECIDE 級選擇（素材排列等，經 owner 授權模式） | 越過 owner gate |

**Q4 最小可行 context／evidence 欄位**
Context＝四檔：approved script ref、selects manifest、run provenance
（含 selection_mode/script_source/orientation_corrected）、candidate run
dir。Evidence ref＝`{path, anchor?{time_range|cell_id}, produced_by}`。
其餘欄位入觸發清單。

**Q5 f1 驗收序（第一個增量修訂）**
1. Agent 讀 selects 表提案 SPT10 替換（附格證據＋理由）
2. Owner approve/revise（對話即綁定；hash 等觸發）
3. Helper 重組 opening_sequence（唯一 diff＝clip 14）→ 全片重渲染
   （44s 尺度明文宣告：全重渲染即為本尺度的「段落級」策略）
4. Verify：timeline diff 僅 clip 14、卡點 1.0 維持、QA pass、
   provenance v2 記 supersedes: candidate_v1（run dir 命名即歷史）
5. 遙測照 §VERIFY 清單記錄，缺項標 unknown
Dirty propagation 本尺度＝無（無 L2/L3/L4 內容存在可髒）。

**Q6 規模判定**
以上邊界下 P0＝**小型**：一份 skill 文件＋一張 helper 收編小單＋
f1 驗證輪。會把它變大的隱藏依賴正是 loop_context/journal 引擎——
已全數移入觸發清單，故不存在於 P0。

**Q7 歷史落點**
同意「timeline=現況真相、journal=歷史」。P0 journal＝session log＋
docs/pilots 證據文件＋git；正式 journal 引擎入觸發清單。

**Q8 Owner zones**
- skill → `skills/editing-loop-director.md`＋skills/INDEX.md 登記
  （owner=main-pipeline；INDEX 一致性受 test_skill_index 管）
- helper → `video_pipeline_core/`（main-pipeline）
- 依 loop spec §6：本單新增 tool/artifact 之 dictionary/skills 申報
  劃入同一 owner zone
**Q9** 同意：owner 接受本回覆前不開工單、不動產線。

## 觸發式硬化清單（SOL 設計的保存處）

| 機構 | 建造觸發（可觀測事件） |
|---|---|
| proposal hash 綁定 | 多 agent 並行編輯出現，或一次「批A用B」事故 |
| append-only journal 引擎 | 一次決策遺失/被覆寫爭議 |
| loop_context envelope | 跨 session 交接一次失敗（context 無法從四檔重建） |
| dirty propagation 矩陣＋段落重渲染 | 全片尺度單次重渲染實測 > 可忍分鐘數 |
| evidence hash | 證據檔漂移/跨機器不一致一次 |

## 建議 P0（供 owner 拍板）

1. TERRA closure（前置衛生，照 SOL §DO-1）
2. `editing-loop-director` skill 撰寫（內容=首航 doctrine 固化，
   六節，含觸發清單引用）
3. helper 收編小單（usage-log → 能力庫模組，test-first）
4. f1 修訂輪＝skill＋helper 的驗收（Q5 序）
