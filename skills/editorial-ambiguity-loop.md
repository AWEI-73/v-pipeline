---
name: editorial-ambiguity-loop
description: Use across Hermes Stage 0-2 when a whole-video request still has fuzzy story intent, multiple plausible structures, weak segment composition grammar, or no evidence-need map. Uses one-decision-at-a-time interaction to convert ambiguity into an evidence-carrying story decision, segment story contract, and evidence need map before Stage 3. It is a method overlay, not a Stage router or renderer.
---

# Editorial Ambiguity Loop — 上游模糊消除

## Boundary

先讀 `skills/pipeline-boundary.md`。本 Skill 是 **Stage 0–2 的薄方法層**：

- Stage 0 的 owner 仍是 `video-intent-planner`；
- Stage 1 的 owner 仍是 `story-soul-blueprint`；
- Stage 2 的 owner 仍是 `director` / `spec-contract`；
- Stage cursor、素材真相、選片、BUILD、render、Verify、approval 與 delivery
  均不屬於本 Skill。

它只回答一件事：**上游的模糊故事，是否已被逐層消成一份下游不能亂解讀的
可攜式契約？**

## Tool Contract

<!-- TOOL_CONTRACT_START -->
{
  "version": 1,
  "skill": "editorial-ambiguity-loop",
  "stage_owner": "stage0_2_editorial_method_overlay",
  "triggers": [
    "a fuzzy whole-video request needs progressive ambiguity reduction before Stage 3",
    "Stage 2 has segment names but lacks causal change, composition grammar, or an evidence-need map",
    "an agent needs a deterministic readiness check for the accepted upstream story package"
  ],
  "canonical_tools": [
    {
      "tool": "tools/editorial_ambiguity.py",
      "when": "validate the accepted story decision, segment story grammar, and evidence-need map before Stage 3",
      "inputs": [
        "story_decision_packet.json",
        "segment_story_contract.json",
        "evidence_need_map.json"
      ],
      "outputs": [
        "stage2_ambiguity_gate_report.json"
      ],
      "stop_if": [
        "a route-changing or structural unknown remains open",
        "a required picture role has no evidence need",
        "an accepted decision lacks evidence or downstream interpretation bounds",
        "cross-artifact paths or hashes do not match"
      ],
      "capability_id": "cap.editorial-ambiguity-loop.stage2-gate.v1",
      "execution_class": "deterministic",
      "capability_role": "gate",
      "loops": [],
      "maturity": "experimental",
      "certified_scope": "schema and binding readiness only; no creative-quality or material-availability claim"
    }
  ],
  "forbidden_tools": [
    "Do not use this Skill to advance the Stage cursor, select source windows, render, approve, or deliver",
    "Do not rename observed material into a desired story function",
    "Do not treat validator PASS as story quality, material coverage, or creative approval"
  ],
  "capability_namespace": "cap.editorial-ambiguity-loop.*",
  "capability_lookup_owner": "editorial-ambiguity-loop"
}
<!-- TOOL_CONTRACT_END -->

## The loop

每次只把故事展開一層，再 compact 給下一層：

```text
propose
  → compare
  → owner / delegated-agent verdict
  → expand one level
  → evidence check
  → compact to next level
```

Compact 的意思是**去除重複說明，不是刪除決策理由與證據**。每一層必須保留：

```text
decision
decision_reason
evidence_refs
owner_or_agent
status
remaining_unknowns
allowed_downstream_interpretation
```

下游只讀 compact artifact 與其 evidence refs，不靠聊天記憶補洞。

## Interactive grilling discipline

本節借用 Matt Pocock `grilling`（MIT）的窄問題拆解精神，改寫成 Hermes
Stage 0–2 的互動方法。它不是新 Stage，也不得建立新的 router、gate 或第四份
canonical story artifact。

### Ask decisions; inspect facts

每次互動前先建立目前的決策樹，並自行讀取可得的 brief、素材名稱、Material Map、
牆面、ASR、reference film 與既有 owner verdict。可由證據查得的事實由 Agent 查證，
不要反問 owner。只有會改變目標、因果骨架、公開事實、素材授權或交付行為的選擇，
才進 ASK / SHOW。

每輪固定順序：

```text
enumerate unresolved branches
  → inspect environment facts
  → choose the highest-impact unresolved decision
  → ask exactly one question
  → wait for the answer
  → persist the accepted decision
  → recalculate dependent branches
```

一題只裁決一個主選擇，但可以列出它會填滿的多個欄位。問題必須包含：

```json
{
  "question_id": "q_stage1_story_shape",
  "branch_id": "story_shape",
  "depends_on": ["audience", "factual_purpose"],
  "fills": ["narrative_contract.thesis", "hypotheses[].causal_promise"],
  "environment_facts": [
    {"claim": "what the repo or material actually supports", "evidence_refs": ["path-or-id"]}
  ],
  "recommended_answer": "one concrete recommendation and why",
  "alternatives": [
    {"answer": "credible alternative", "tradeoff": "what it gains and loses"}
  ],
  "owner_answer": null,
  "blocking_descendants": ["segment architecture", "evidence needs"]
}
```

`recommended_answer` 是降低 owner 判斷成本，不是代替 ASK / SHOW 裁決。若 owner
已明確委任某一類可逆決策，才可用 DECIDE，且仍要寫進 `decision_record`。

### Small-model emission preflight

較小模型在送出問題前，必須逐項自檢；任何一項不符合就先修正問題，不得交給
owner：

- 實際只問一個主決策，不把片長、結構、風格等多題綁成一題；
- `fills` 是非空的 canonical field-path array，不是「全片方向」等散文；
- 每個 `environment_facts[]` 都同時有 `claim` 與非空 `evidence_refs`；
- `alternatives[]` 每個選項都有 `answer` 與 `tradeoff`；
- `recommended_answer` 明確說出推薦與理由，但 `owner_answer` 仍為 null；
- 問題不能由 repo、素材、ASR、牆面或既有 verdict 直接查得；
- 不提前展開後續問題，不在 owner 回答前產生完整劇本或下游契約。

收到回答並 compact 時再檢查：

- owner 原意與限制被保留，不能只留下模型改寫後的摘要；
- 已接受的 branch 不得在 `remaining_unknowns` 被重新打開；
- 可查但尚未查的事實標成 evidence task，不冒充 owner taste question；
- hard constraints、可替換文字與 worker discretion 明確分開；
- 不因 target duration 自動補故事、重複素材或宣稱 creative approval。

### Persist without adding a layer

每個答案先追加到既有 Stage 0 `interaction_log.md`，再把有效內容 compact 到既有的
`story_decision_packet.json`、`segment_story_contract.json` 或
`evidence_need_map.json`。聊天記錄不是真相；互動 log 是 provenance，也不是新的
下游依賴。下一題只讀目前 compact state、未解 branch 與必要 evidence refs，不重讀
整段歷史。

只有 route-changing / structural branch 已解決，而且每個段落的 worker 資訊投影
足以讓下游不靠猜測執行，互動才可結束。Local unknown 可以攜帶，但必須列入
`remaining_unknowns`，不得用含糊文案假裝已決定。

### Canonical vocabulary

不要自創近義 token。v1 固定值如下：

| field | allowed values |
|---|---|
| `decision_mode` | `single`, `ab_comparison`, `delegated` |
| `decision_record.status` | `accepted` |
| `decision_record.owner_or_agent` | `owner`, `agent_delegated`（後者必填 `delegation_scope`） |
| `remaining_unknowns[].route_impact` | `route_changing`, `structural`, `local` |
| `remaining_unknowns[].status` | `open`, `resolved`, `deferred` |
| `stage2_status` | `accepted` |
| `material_truth_status` | `not_started`, `inventory_only`, `reviewed` |
| `evidence_kind` | `visual`, `speech`, `text`, `mixed` |
| `needs[].status` | `needed`, `available_unverified`, `verified`, `deferred_due_to_material` |

`remaining_unknowns[]` 的固定欄位為 `unknown_id`, `question`, `route_impact`,
`status`, `owner_or_agent`, `resolution`, `evidence_refs`。不要把 `question`
改成 `description`，也不要把 `owner_or_agent` 改成 `owner`。

## Stage 0 — fuzzy intent boundary

由 `video-intent-planner` 建立 `project_brief.json` / `video_intent.json`。
只消除會改路線的模糊：目標、觀眾、片長、片型、素材狀態、文本狀態、
生成素材權限與真實性邊界。

### ASK / SHOW / DECIDE

- **ASK**：答案會改變公開行為、事實邊界、片型、素材授權或交付承諾。
- **SHOW**：人看兩個具體方案比描述品味更容易；用 A/B 紙剪或 storyboard。
- **DECIDE**：可逆、局部，而且之後的 evidence / validation 能抓錯；必須記錄
  `owner_or_agent=agent_delegated` 與 `delegation_scope`。

Stage 0 可以保留未知，但 `required_followup_questions` 內的 route-changing 項目
未清空前不得進 Stage 1。

## Stage 1 — story hypotheses, not an activity list

先提出故事假說，再寫 beat。每個假說至少包含：

- `thesis`：觀眾最後應理解什麼；
- `causal_promise`：狀態如何一步步改變；
- `material_assumptions`：它假設素材能證明什麼；
- `sacrifices`：選它會放棄什麼；
- `evidence_refs`：已知事實或 owner 語句，不可只寫模型直覺。

高影響、仍有兩個可信方向時，預設 `decision_mode=ab_comparison`。A/B 必須改變
因果骨架或觀眾理解，不能只是換標題、顏色或語氣。若只有一個合理方向，使用
`decision_mode=single` 並寫 `single_option_waiver`，不要製造假選項。

素材先行專案可以在 Stage 1 前做 quick inventory / 牆面沉浸以認識事實，但不能
從檔名或活動分類直接跳成故事。名稱是 prior；像素、語音、owner fact 才是 evidence。

## Stage 2A — whole-film causal architecture

接受的 `narrative_contract.causal_arc` 每個 beat 必須回答：

1. `factual_claim`：畫面或語音實際要證明什麼；
2. `entry_state`：段落開始時觀眾知道／感受到什麼；
3. `story_change`：這段新增了什麼，不是又展示同一類活動；
4. `exit_state`：它把觀眾送到哪個新狀態；
5. `evidence_refs`：這個說法從哪裡來。

一串課程名、活動名或素材資料夾不是 causal arc。若移除某 beat 後全片理解沒有
變化，該 beat 應合併、降為 montage support，或從主線拿掉。

## Stage 2B — segment composition grammar

每個 `segment_story_contract.segments[]` 必須有以下欄位：

| field | meaning |
|---|---|
| `segment_id` | 穩定段落 ID |
| `factual_claim` | 這段能被素材證明的事實 |
| `story_change` | 相對上一段新增的理解／情緒狀態 |
| `entry_state` / `exit_state` | 因果接棒前後狀態 |
| `required_picture_roles` | 例如 establish / prep / action / correction / result / reaction |
| `allowed_source_families` | 可承擔此事實的素材家族，不是已選檔名 |
| `forbidden_substitutions` | 不得拿什麼相似畫面冒充 |
| `minimum_unique_windows` | 不重複撐起這段所需的最低窗口數 |
| `duration_policy` | `min_sec` / `target_sec` / `max_sec` / `shorten_if_material_short` |
| `transition_in` / `transition_out` | 各含 `story_job` 與 `continuity_rule` |
| `title_card_role` | `none` 或 opening / chapter / context / ending 的故事角色 |
| `defer_or_shorten_rule` | 素材不足時先縮、延後或回 owner，不准灌水 |
| `review_question` | owner 看 storyboard 時的一個可回答問題 |
| `evidence_refs` | 本段決策依據 |
| `decision_record` | 七欄最小決策紀錄 |

若 `evidence_refs` 使用 `N_*` 形式引用 Stage 2C 的 need ID，該 ID 必須實際存在於
`evidence_need_map.needs[]`。這是跨 artifact 綁定，不是可忽略的註解；缺少時
`tools/editorial_ambiguity.py` 必須 fail closed。

一個段落若包含多個對外有意義的訓練／事件單元，另帶
`content_taxonomy.training_units[]`。每個單元至少記錄 `unit_id`,
`official_label`, `label_status`, `factual_purpose`, `story_function`,
`required_picture_roles`, `allowed_source_families`, `coverage_status`,
`unknowns`, `evidence_refs`。這讓「基礎訓練」不會被當成一個空泛大類，也不要求
Stage 2 先選實際檔案。

每個段落還要產生 `worker_information_projection`：

```text
required_context
hard_constraints
soft_guidance
worker_discretion
unknowns
evidence_refs
consumer_stage
verification_target
```

投影的目的，是把足夠資訊交給 worker，同時保留可逆的剪輯空間。運鏡、裁切焦點、
字卡角色、聲音優先級等若會改變故事理解，寫成 `hard_constraints` 或
`soft_guidance`；純 renderer 參數仍留給 Stage 5/6，不在 Stage 2 寫死。

`required_picture_roles` 是組合語法，不是鏡頭清單。例如技術微故事可用
`establish → prep → action → correction → result`；訪談可用
`speaker_anchor → claim_cutaway → consequence → return_to_speaker`。片型決定語法，
不要把 Canon 67 的角色硬套到所有影片。

字卡必須在這裡有故事角色。`title_card_role=chapter_boundary` 只表示需要章節邊界，
文字真相與效果做法仍分別交 Writer / Effect Factory；Stage 2 不寫 renderer API。

## Stage 2C — evidence-need map

`evidence_need_map.needs[]` 必須把每個 segment 的每個
`required_picture_role` 映射成一條 need：

- `need_id`, `segment_id`, `picture_role`；
- `factual_claim`, `evidence_kind`, `required_observation`；
- `allowed_source_families`, `forbidden_substitutions`；
- `status`, `evidence_refs`。

Stage 2 還沒證明素材存在時，用 `status=needed`；不要填假路徑。Stage 3 找到後可改
`available_unverified` / `verified`。真的找不到只能在 owner 確認後用
`deferred_due_to_material`，並附：

```json
{
  "reason": "not_found | not_present | present_unusable | excluded_by_policy",
  "owner_confirmed": true,
  "evidence_refs": ["inventory-or-review-evidence"]
}
```

「素材可能沒有」與「檢索沒找到」不是同一件事；未經 owner 確認不得把檢索失敗
包裝成素材天花板。

## Artifact package

### `story_decision_packet.json`

頂層固定欄位：

```text
artifact_role=upstream_story_decision_packet
schema_version=1
project_id
stage0_intent_ref {path, sha256}
decision_mode
hypotheses[]
selected_hypothesis_id
decision_record
narrative_contract {subject, audience_change, thesis, causal_arc[]}
remaining_unknowns[]
retired_story_intents[]
deferred_due_to_material[]
```

`remaining_unknowns[]` 使用 `route_impact=route_changing | structural | local` 與
`status=open | resolved | deferred`。Route-changing / structural 項目仍 open 時，
Stage 2 必須 FAIL；local 項目可攜帶到 Stage 3，但下游不得把它當已知事實。

### Cross-artifact binding

- `segment_story_contract.story_decision_ref` 綁 story decision 的 path/hash；
- `evidence_need_map.story_decision_ref` 綁同一份 story decision；
- `evidence_need_map.segment_contract_ref` 綁 segment contract；
- 三份 artifact 的 `project_id` 必須相同。

相對 `path` 一律以**持有該 ref 的 artifact 所在資料夾**為基準；三份檔案在
同一資料夾時只寫 basename，例如 `"path": "story_decision_packet.json"`。
不要寫相對 repo root 的完整 run 路徑，否則會被再次拼接而 fail-closed。

## Completion gate

執行：

```powershell
python tools/editorial_ambiguity.py validate `
  --story-decision RUN/story_decision_packet.json `
  --segment-contract RUN/segment_story_contract.json `
  --evidence-map RUN/evidence_need_map.json `
  --out RUN/stage2_ambiguity_gate_report.json `
  --json
```

只有 exit 0、`stage2_completion=PASS`、`ready_for_stage3=true` 才能交 Stage 3。

PASS 只證明：決策完整、重大未知已處理、段落語法與 evidence needs 一一對上、
hash 沒漂移。它**不證明**素材真的存在、故事好看、剪輯成立、creative approval
或 delivery。

語意欄位不能用形狀合規的佔位句。Validator 會拒絕
`owner-approved evidence statement`、`TBD`、`TODO`、`placeholder` 等泛用值；
若 owner 決策尚未能寫成具體命題，Stage 2 應停在互動補問，而不是把空句送給
Stage 3。`interaction_compaction_audit` 必須逐項列出「決策 → 實際下游欄位與值」；
只列檔名或宣稱 `altered_meaning=false` 不構成證據。

## Handoff to Stage 3

Stage 3 worker 收到的是三份 frozen artifact 與 gate report。它可以：

- 依 need 檢索、rank、提名 source windows；
- 回報 `verified`、`deferred_due_to_material` 或 retrieval failure；
- 提議縮短／合併 segment。

Stage 3 使用 `tools/picture_plan_retrieval_report.py` 時，若輸入來自本 skill 的
Stage 2 package，必須一併傳入 `--evidence-map`。這個公開 adapter 會把
`segment_id` 與每條 need 接到 retrieval surface 的 `segment`、
`material_fit.need_refs`、`role_queries` 與 `visual_desc`；worker 不得自行建立
另一份 crosswalk 或手排候選表。

它不可以：

- 改 `story_change`、重新命名事件或交換段落目的；
- 用 A 類素材填 B 類 need，只因畫面「看起來差不多」；
- 把未選中的 hypothesis、retired intent 或 owner 拒絕的方向撿回來；
- 因目標片長不足而重複事件家族或灌水。

素材證據推翻上游假設時，回 Stage 2 產生新 proposal / verdict / contract revision，
而不是讓 Stage 3 worker 靜默重寫故事。
