# Hermes｜剪輯品質補強與能力派工收斂設計

Date: 2026-07-12  
Status: approved direction; written-spec review revision 1
Scope: Canon 67 39 秒 internal-review forward test，以及 Hermes 全 repo 的工具能力檢索與孤兒防護

## 1. 背景與已知事實

Canon 67 的 39 秒訪談候選片已完成 L0–L5 技術閉環：完整測試曾以
`2655 tests / exit 0` 通過，候選片 SHA-256 為
`FE4366FC7D6C308442FD7A21CFFC40D6E33404D50FD0CAFEE3CAFBAD5834F5E2`。
Owner 認為候選片整體可接受，但提出兩項真實修訂：

1. 主任人聲出現時，BGM 應依語音實際活動動態降低，而不是整段固定音量。
2. 訪談 cutaway 應避免相似場景／同一素材家族反覆出現。

Repo 已具備大量相關零件，但接線不完整：

- `material_retrieval.select_diverse_ranked_scenes()` 已能依
  `visual_family`、`angle_scale`、history 與來源次數偏好多樣性；
- `semantic_novelty_audit` 已能以 dHash 找出「不同檔案、相同可見構圖」；
- 39 秒 Wave R 的 L0/L1 是 agent 直接產生 selects provenance 與
  `rough_cut_plan.json`，未走上述正式 Material Map 選片鏈；
- `audio_mix_plan_executor._apply_ducking_policy()` 目前只在語音配置重疊時，
  把 BGM 整段設為固定 `0.28`，並非依語音能量變化的 ducking；
- 29 個 Skill 已有 ownership index；11 個 operational Skill 的
  `TOOL_CONTRACT` 已認領 107/107 支 `tools/*.py`；`video_tools.py` 有
  149 個已分類 command 與 14 個 workflow；
- 現有登記與 SOP 主要集中在大型 Domain Skill，Agent 為了找單一工具，
  常須載入數百行內容，也可能直接繞過已存在的能力。

本設計以這些已觀察到的失敗為依據，不建立推測性的第二套調度系統。

## 2. 目標

同一個長任務依序完成：

```text
Wave A1：L0/L1 cutaway 去重與多樣性正式接線
Wave A2：L3 speech-aware ducking
Wave A3：新的 39 秒整合候選片與 L5 review evidence
Wave B：Tool → Capability Card → Domain Skill → Director Skill 四層收斂
```

完成後應達成：

1. 39 秒候選片不再因 Editing Loop 捷徑繞過 Material Map 多樣性能力。
2. BGM 音量會依主任實際語音活動平滑降低／恢復，且保留原始講話連續性。
3. 工具只在 owning Domain Skill 的 `TOOL_CONTRACT` 登記一次。
4. Agent 可透過唯一唯讀入口，以 owner、LOOP、關鍵字或 capability ID
   查到少量、可執行的能力卡，不必讀完整大型 Skill。
5. 新工具、重複 owner、斷裂 capability、失效 Director 引用與未分類 command
   都由既有 audit 體系 fail closed。
6. 不增加新的 route runner、registry database 或自動決策 orchestrator。

Wave A 的 objective／technical evidence 全綠即足以進入 Wave B；owner 的 picture、
audio 與 final taste verdict 合併到整個 campaign 的最終 gate，不阻塞純機械的
registry convergence。這不構成 creative approval。

## 3. 非目標

- 不重寫 Material Map、Audio Director、V Pipeline 或 Editing Loop。
- 不把 107 支工具拆成 107 個 Skill。
- 不搬動或全面重新命名既有工具。
- 不建立常駐服務、資料庫、embedding search 或 LLM registry router。
- 不把能力選擇、畫面品味、音樂品味或 final approval 機械化。
- 不擴張成 9.4 分鐘完整影片。
- 不改變 preview-only 音樂的授權／delivery gate。
- 不要求 owner 觀看人工 A/B 對照；舊片只作 immutable regression baseline。

## 4. 核心架構裁決

### 4.1 四層分工

| 層 | 責任 | 不負責 |
| --- | --- | --- |
| Tool | 確定性執行、讀寫既定 artifacts | 判斷使用者真正想要什麼 |
| Capability Card | 說明何時用、輸入輸出、stop-if、LOOP、成熟度 | 執行 route 或做品味判斷 |
| Domain Skill | 擁有專業 SOP、canonical tool ownership 與部門邊界 | 複製其他部門 SOP |
| Director Skill | 根據 intent／finding 選擇 capability ID、維持 owner gate | 重新擁有底層工具 |

Registry 負責「線是否完整」；Skill／Agent 負責「這次該走哪條線」。

### 4.2 唯一寫入與唯一查詢

唯一寫入來源是 owning Domain Skill 的既有 `TOOL_CONTRACT` block。
全域索引、Domain view 與 LOOP view 都由查詢 command 在執行時從 live
contracts deterministic 建立於記憶體；repo 不提交生成 catalog／Markdown
目錄。`--out` 只可寫入當次 run evidence，不得成為新 truth source。

唯一唯讀檢索入口為新的 `video_tools.py dispatch-capabilities` command：

```powershell
python video_tools.py dispatch-capabilities --owner material-map
python video_tools.py dispatch-capabilities --loop L3
python video_tools.py dispatch-capabilities --query "speech ducking"
python video_tools.py dispatch-capabilities --id cap.audio-director.audio-mix-plan-execute.v1
```

此 command 只解析與查詢，不執行工具、不變更 route、不選擇下一步。

### 4.3 不建立第三份 parser

目前 `tools/skill_tool_contract_audit.py` 與
`tools/pipeline_interface_discovery.py` 都會解析 `TOOL_CONTRACT`。
施工時須先把共用解析／正規化抽到單一 owner module，再由 audit、interface
discovery 與 dispatch catalog 共用。不得複製第三份 regex／JSON loader。

## 5. Wave A1｜Material Map 去重與多樣性接線

### 5.1 L0 正規化

Editing Loop L0 已產生的 `observed_content`、`assigned_story_function`、
evidence coordinates 與 blind spots，必須轉成既有 Project Material Map
可消費的 scene evidence，而不是只留在 run-local provenance。

至少攜帶：

- stable asset／scene identity；
- source window；
- caption／observed content；
- `visual_family`；
- `angle_scale`；
- `action_family`；
- `subject`；
- story／sequence function；
- evidence refs 與判斷盲區。

沒有可證實標籤時保持缺值；不得由檔名冒充視覺真相。

### 5.2 L1 正式選片

當正式 Material Map scene evidence 存在時，L1／rough-cut proposal 必須調用
既有 scene ranking＋diversity selector，而不是直接依 catalog 或 agent 手排順序
寫入 plan。

規則：

1. `talking_head` 為語音敘事錨點，不受 cutaway source-repeat ceiling 約束。
2. cutaway 在有足夠合格替代素材時，預設同 source／visual family 不重複。
3. 若供給不足而必須 fallback，plan 必須記錄
   `diversity_fallback_reason`，不得靜默越過 ceiling。
4. 同一 source 的不同時間窗不自動等於重複；最終仍以 visual family、構圖與
   故事功能判斷。
5. `semantic_novelty_audit` 在 L1 preview 後執行；FAIL 轉為 L1 finding，
   指向受影響 stable segment，不自動建立 route runner。
6. Audit 無 render／hash 不可用時必須申報 UNKNOWN／skipped reason，不能 PASS。

### 5.3 相容性

- 無 Material Map、無 VD 標籤的 legacy 路徑保持既有行為。
- 既有 `disable_visual_diversity` 控制保持相容。
- 現有 source-repeat 行為不得被全域硬改成「每個檔案只能用一次」。

## 6. Wave A2｜Speech-aware Ducking

### 6.1 行為要求

現有 `duck_under_voice` legacy policy 保持可讀；新行為必須在 opt-in 的
speech-aware policy 下依實際 protected speech activity 產生動態音量變化：

- 語音活動前平滑 attack；
- 語音期間 BGM 保持在設定 ceiling／floor 內；
- 語音停頓後平滑 release；
- 不得改變主任原始語音的時間、文字或順序；
- 不得把 cutaway source audio 混入；
- 音訊長度必須仍與 candidate 視訊相符；
- report 必須記錄 ducking mode、參數、受影響窗口、實際 applied evidence，
  不能只寫 `ducking_applied=true`。

具體可採 sidechain 或由上游 speech evidence 產生 envelope；public contract 以
可測量行為為準，不把某個 ffmpeg filter 名稱寫死為產品介面。

### 6.1.1 最小可量測契約

新 policy 必須明文攜帶並在 report 回讀：

- `ducking_mode=speech_aware`；
- `duck_db`，預設 `-12.0 dB`；
- `attack_ms`，預設 `80 ms`；
- `release_ms`，預設 `300 ms`；
- speech threshold／來源證據；
- protected speech placements 的原始 start、duration 與 gain；
- 至少一組 active-speech window 與一組可用時的 inactive／recovery window
  量測；沒有真實 recovery window 時明文 `not_applicable`，不得捏造 PASS。

合成 fixture 至少包含 6 秒連續 BGM，以及 `1.0–2.0s`、`4.0–5.0s` 兩段
protected speech activity。GREEN 必須證明：

1. active window 的 BGM RMS 比相鄰 silent／recovery window 至少低 `8 dB`；
2. 兩段語音之間的 recovery window 比 active window 至少高 `4 dB`；
3. protected speech placement 的 start／duration／gain `1.0` 未被改寫；
4. output duration 與 target 相差不超過 `20 ms`；
5. attack／release 皆為非零並與 plan/report 相等；
6. final peak 仍符合既有 audio/delivery threshold。

這些是 focused fixture 的客觀門檻；真實 39 秒候選片另記人耳 taste 為 UNKNOWN
直到 owner 聆聽。

### 6.2 音樂人聲衝突

若 soundtrack probe 已提供 BGM vocal windows，與 source speech 重疊時必須：

- 在 preview report 明確標示 overlap；
- 套用較強 attenuation 或輸出 owner-taste finding；
- probe 不存在時申報 UNKNOWN，不得宣稱無衝突。

這不改變音樂權利政策；`preview_only=true`、`delivery_allowed=false` 繼續由
既有 delivery gate fail closed。

### 6.3 相容性

- 沒有新 policy 的舊 mix plan 保持目前固定音量行為。
- Legacy tests 與 byte／artifact shape 不因新 opt-in 功能改變。
- 不在 hot render path 重做 ASR；可消費既有 speech evidence 或實際音訊能量。

## 7. Wave A3｜39 秒 Forward Test

舊候選片與 Wave R artifacts 全部唯讀；新工作使用新的 run root，保留舊
candidate hash 作 regression baseline，但不要求 owner 看人工 A/B。

新的候選片只允許以下語意差異：

- 指定 cutaway 選擇／排列因正式 diversity 接線而改變；
- BGM 音量 envelope 因 speech-aware ducking 而改變。

以下必須保持：

- 主任 source speech 0.00–39.34s 連續；
- owner-approved 12 cue 字幕文字與時間；
- lower-third 內容、位置與 lifecycle；
- 39.34 秒目標與 H.264／AAC profile；
- `human_creative_approval=false`；
- `final_delivery_claimed=false`；
- preview-only audio delivery rejection。

完成 fresh rendered QA、final verify、semantic novelty、subtitle equality、
audio evidence 與 L5 packet 後，記錄 owner taste 為 pending，但允許以 objective
PASS 進入 Wave B。整個 campaign 最後才停在一次 consolidated owner verdict。

## 8. Wave B｜單一註冊與生成式檢索

### 8.1 Capability ID

每個 canonical/public tool entry 必須有不可變的語意 ID：

```text
cap.<owner-skill>.<tool-or-public-action>.v<major>
```

例如：

```text
cap.material-map.material-quick-inventory.v1
cap.material-map.visual-diversity-select.v1
cap.audio-director.speech-aware-duck.v1
cap.verify.semantic-novelty.v1
```

ID 同時是註冊編號與 join key，不使用自動遞增流水號。更名不改 ID；不相容
契約才升 major version。第一版不另建顯示流水號。

### 8.2 TOOL_CONTRACT 最小增量

保留既有 `tool`、`when`、`inputs`、`outputs`、`stop_if`。canonical tool entry
新增：

```json
{
  "capability_id": "cap.material-map.visual-diversity-select.v1",
  "loops": ["L0", "L1"],
  "maturity": "bounded",
  "certified_scope": "Canon 67 39s cutaway forward test"
}
```

規則：

- canonical/public entry：必須有 capability ID、LOOP／stage 與 maturity；
- supporting/internal/diagnostic：必須有 owner，但不強迫成為 Director entry；
- maturity 詞彙固定為 `experimental | bounded | certified | legacy`；
- `certified_scope` 不得比真實 evidence 更廣；
- 既有 canonical entries 必須在本次 migration 全數獲得 deterministic ID，
  不留下永久 legacy exemption。

### 8.3 Domain 與 Director 檢索

Domain Skill 只需在短入口聲明自身 namespace／lookup hint，不複製工具卡：

```yaml
capability_namespace: cap.material-map.*
capability_lookup_owner: material-map
```

Editing Loop Director 以 capability ID／namespace 表達 L0–L5 需要的能力；
它是 consumer，不得重新宣稱 canonical ownership。

### 8.4 Query 行為

`dispatch-capabilities` 支援：

- `--id`：精確一筆；不存在 exit 1；
- `--owner`：Domain view；
- `--loop`：L0–L5 view；
- `--query`：對 ID、tool、when、inputs、outputs 與 owner 做 deterministic
  token match；
- `--json`／`--out`：機器輸出；預設為精簡 human view。查詢每次都從 live
  `TOOL_CONTRACT` 建立 catalog；`--out` 只是 run-local snapshot。

查詢無結果 exit 1；歧義結果必須全部列出，不由 catalog 猜唯一答案。

### 8.5 Workbench 相容性

Capability catalog 是 control-plane metadata；Workbench 既有 artifacts 與
patch／review data plane 不變：

- 不修改 `rough_cut_plan.json`、`preview_timeline.json`、
  `audio_mix_report.json`、`timeline_patch.json`、`subtitle_patch.json`、
  `audio_cue_patch.json`、`effect_patch.json` 或 `workbench_handoff.json` 的
  必填 schema；
- capability ID 不得成為 Workbench 讀取既有 run／draft 的必要欄位；
- Workbench 未來可選擇以唯讀方式查 `dispatch-capabilities`，但本 campaign
  不把它接成 Workbench runtime dependency；
- 不改 `workbench-brownfield` branch ownership、既有 canonical outputs、
  promotion gate 或 draft-only 邊界；
- 既有無 capability metadata 的 Workbench artifacts 必須持續可讀。

因此未來把 run 或 handoff 交給 Workbench 讀取時，新增 catalog 可完全忽略；
它只幫 Agent 找到正確工廠能力，不改影片工件本身的形狀。

## 9. 孤兒防護與重造輪子防護

擴充現有 `skill_tool_contract_audit`，不要建立平行 audit。至少檢查：

1. `tools/*.py` 無 owning skill；
2. canonical tool 無 capability ID；
3. capability ID 重複或格式錯誤；
4. capability 指向不存在的 tool；
5. 同一 canonical tool 被多 owner 認領且未明文 shared；
6. Director／Domain lookup 引用不存在的 capability／namespace；
7. canonical command 未進入 command dispatch／command catalog；
8. deprecated／legacy capability 仍被 active Director 引用且無 replacement；
9. supporting/internal/diagnostic tool 被宣稱為 Director public entry。

新增工具前，Agent 必須先查 `dispatch-capabilities --query`。若已有相近能力，
優先擴充既有 public surface；確實不相容時才新增。第一版不新增
`supersedes`／`overlaps_with` 關係機構；語意上是否真為同一輪子仍由
Agent／reviewer 判斷。

## 10. 錯誤處理與 Stop-Loss

### Wave A

- 同一功能失敗類型一次 LOCAL 修復後重現：STRUCTURAL stop。
- 需要改動未授權 owner zone、降低驗收門檻、私有 ffmpeg workaround、
  改寫字幕／語音真相或繞過 preview-only gate：立即停止。
- Wave A 任一 public capability 未通過 forward test，不進 Wave B；不得登記
  尚未存在或未穩定的能力。

### Wave B

- 不得以 copy/paste 建立第三份 Tool Contract parser。
- 不得新增 route state、next_action vocabulary、daemon 或 registry DB。
- Migration 發現 capability 命名歧義時，保留現有 ownership，列入 report；
  不得無證據改變 owner。
- 任何 orphan audit FAIL 都阻止 closure；不得以 waiver 轉成 PASS。

## 11. 測試策略

所有 production behavior 變更採 RED→GREEN；各 Wave 只跑 focused＋adjacent
tests。完整 suite 只在功能、forward test、registry migration 與 audits 全綠後
跑一次。

### Wave A1 focused families

- Material Map／project map；
- material retrieval／map retrieval wiring；
- rough-cut planning／execution；
- visual diversity coverage／review；
- semantic novelty audit；
- B-roll/source-repeat audit。

### Wave A2 focused families

- audio mix plan executor；
- audio handoff acceptance；
- soundtrack arranger／probe；
- delivery gate；
- preview timeline／audio read-back。

### Wave B focused families

- skill tool contracts；
- skill index／pipeline skill boundaries；
- video-tools command catalog；
- pipeline interface discovery／audit；
- dispatch-capability query fixtures；
- Workbench artifact loading／handoff／preview-timeline backward compatibility。

### 必要負向案例

- 新 canonical tool 無 capability ID；
- 重複 capability ID；
- capability tool path 不存在；
- Director 引用不存在 ID；
- internal tool 被當 public；
- query 無結果／歧義；
- 動態 ducking 未產生實際音量變化；
- speech 被截短／重排；
- cutaway 供給足夠卻重複 visual family；
- fallback 未帶理由；
- semantic novelty 無 render 卻宣稱 PASS。

## 12. 施工與提交順序

同一長任務可連續執行，但使用獨立 scoped commits：

1. Material Map／diversity RED→GREEN；
2. 39 秒 picture forward test；
3. speech-aware ducking RED→GREEN；
4. 39 秒四層 candidate 與 fresh L5；
5. 共用 Tool Contract parser 與 capability schema；
6. 唯一 query command；
7. canonical capability ID migration、Domain／Director references；
8. orphan audit 與負向 fixtures；
9. focused/adjacent integration；
10. 一次 full suite、`git diff --check`、最終 evidence read-back。

### 12.1 Owner／Path 矩陣

同一 worker 依序施工；下列 shared/hot paths 不得交給另一個並行 writer：

| Wave | Logical owner | 可編輯 production／contract paths | 可編輯 tests／evidence |
| --- | --- | --- | --- |
| A1 | `material-map` | `video_pipeline_core/material_retrieval.py`、必要時 `video_pipeline_core/project_material_map.py`、`video_pipeline_core/mv_cut.py`、`video_pipeline_core/semantic_novelty_audit.py` | 對應 Material Map／retrieval／mv_cut／semantic-novelty tests；新 run root |
| A2 | `audio-director` | `video_pipeline_core/audio_mix_plan_executor.py`、契約需要時 `video_pipeline_core/audio_handoff_acceptance.py` | 對應 audio executor／handoff／delivery tests；新 run root |
| A3 | integration／review | 不新增 private renderer；只用既有 public assembly surfaces | 新 39 秒 run artifacts、fresh L5 evidence |
| B1 | shared integration | 新的單一 shared Tool Contract parser module；`tools/skill_tool_contract_audit.py`、`tools/pipeline_interface_discovery.py` | 兩者既有 tests 與 shared parser tests |
| B2 | main-pipeline | `video_pipeline_core/tool_command_catalog.py`、`video_tools.py` | command catalog／dispatch query tests |
| B3 | owning Domain Skills＋main-pipeline integrator | 11 個既有 operational `skills/*.md` 的 `TOOL_CONTRACT` blocks、`skills/editing-loop-director.md`、必要的 `docs/stage-tool-simplification.md` lookup 說明 | skill index／tool contract／pipeline boundary tests |

若 A1／A2 實作證明還需要表外 production path，先判斷是否屬同一 logical owner；
跨 owner 或 public schema 擴張即 STRUCTURAL stop，不能自行擴權。

不得 stage、commit 或清理既有 dirty-tree 檔案；每個 commit 只含本 Wave
明文 owner paths。若必須修改目前已 dirty 的 authority file，須先記錄 pre-hash，
只做 patch，不得覆寫使用者內容。

## 13. 完成定義

只有以下全部成立，才可宣稱 campaign 技術完成：

1. 39 秒新版 candidate 的 picture 與 audio 兩項修訂均有 fresh objective evidence；
2. subtitles、lower third、source speech、duration 與 preview-only gate 保持；
3. Owner 只需對最終新版做一次 taste verdict；
4. `dispatch-capabilities` 可依 ID／owner／LOOP／query 檢索；
5. 既有 canonical public tools 全部有唯一 capability ID；
6. 真實 repo 的 `owned_python_tool_count == python_tool_count`，且
   `unclassified_commands == []`；worker 必須記錄 baseline／final count delta，
   不以凍結的 107／149 數字冒充驗收。新增 `dispatch-capabilities` 後 command
   count 預期至少增加 1；本設計不要求新增 `tools/*.py`；
7. orphan audit 的所有必要負向 fixtures 會 exit 1，真實 repo audit exit 0；
8. Director 只引用能力，不取得其他 Domain 的 canonical ownership；
9. 既有 Workbench artifacts 在缺少 capability metadata 時仍可讀，且
   Workbench schema、branch ownership 與 draft-only promotion gate 未漂移；
10. focused＋adjacent tests、一次 full suite 與 `git diff --check` exit 0；
11. worker report 清楚分開 objective PASS、agent judgment、owner taste、
    music rights、creative approval 與 delivery claim；
12. `human_creative_approval=false` 與 `final_delivery_claimed=false` 保持，
    除非 owner 另行明文變更。
