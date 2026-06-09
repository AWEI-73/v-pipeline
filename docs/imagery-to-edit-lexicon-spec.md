# 意象 → 剪輯 語意對照表 (Imagery-to-Edit Lexicon)

Updated: 2026-06-08
Status: draft for implementation

## 這份文件是什麼

它是**靈魂藍圖**（敘述性、模糊、有意境的導演手記）和**機械引擎**（只認 enum 的
`material_treatment` / `shot_slots` / `audio`）之間唯一的翻譯層。

```
寫藍圖的人：自由寫意象、節奏、情緒（軟）
        │
        ▼  ← 這張表（硬）
讀藍圖的導演：把意象翻成受控詞彙，零隨意發揮
        │
        ▼
引擎已存在的消費者：material_treatment.resolve_treatment / shot_slots.expand_shot_slots
```

核心原則（呼應 `editing-intent-sequence-grammar-spec.md`）：

```
prose 可以軟、可以模糊——那是留給選素材的詮釋空間。
但「軟 prose → 硬操作」的這條翻譯，必須是決定論的。
同一段藍圖讀十次，要收斂到接近的剪輯結構。節奏不是用數字填，是從意象讀。
```

**重要：這張表不發明新欄位。** 右欄全部是引擎現在就在讀的 enum：
- `content_pattern` ∈ `material_treatment.VALID_CONTENT_PATTERNS`
- `treatment` ∈ `material_treatment.VALID_TREATMENTS`（由 content_pattern 自動推導）
- `required_functions` → `shot_slots.expand_shot_slots`
- `audio.role` / `original_audio_policy`、`visual_style.pace` / `layout`、`text_layer`

---

## 1. 主軸維度：內容型態 (content_pattern)

這是整段的 DNA。導演讀藍圖那段的**主要情緒/動作意圖**，落到唯一一個 `content_pattern`，
其餘欄位大多由它連動（見 `material_treatment._LANE_TABLE`）。

| 藍圖意象訊號（prose 關鍵語感） | content_pattern | 自動推導 treatment | 連動 lane（photo/sub/music） |
|---|---|---|---|
| 安靜、凝住、一個畫面說完一切、長呼吸、鼻酸 | `emotional` | `single_hold` | 1 still 慢推 / 敘事卡 / swell_or_drop |
| 開場、報到、還沒解釋、慢慢進來、空景定場 | `establishing` | `single_hold` | 1 still 慢推 / 敘事卡 / swell_or_drop |
| 列舉三項、一個接一個、這些那些、項目展示 | `enumeration` | `photo_stack_beat` | N 張對拍 / 逐項標籤 / 快拍不 duck |
| 步驟、流程、先…再…然後、由生到熟 | `process` | `stepped_sequence` | 順序鏡 / 步驟標籤 / steady_low |
| 過場、轉場、喘口氣、帶到下一段 | `bridge` | `quick_cut_bridge` | 2–4 快切 / 短標或無 / beat 驅動 |
| 引擎全開、越切越快、力量、汗水四濺、攻堅 | `action` | `video_primary` | clip / 輕標 / steady（原音則 duck） |
| 他說、致詞、訪談、本人講話 | `testimony` | `real_material_only` 🔒 | 真素材原音 / 人名+ASR / duck 讓位 |
| 證書、合照當證據、名單、是真的發生過 | `proof` | `real_material_only` 🔒 | 同上 |
| 指名道姓、特定那個人、所長/主任本人 | `identity` | `real_material_only` 🔒 | 同上 |

🔒 **誠實守門（不可被覆寫）**：`testimony / proof / identity` 一律 `real_material_only`，
永遠不能被 stock/generated 頂替（`material_treatment._HONESTY_GUARD_PATTERNS`）。導演讀到
「主任說」「大合照」「謝師名單」必須落這三類，**不准為了畫面漂亮改成可生成的東西**。

---

## 2. 鏡頭功能序列 (sequence_grammar.required_functions)

一段不是一個鏡頭。導演讀藍圖的**敘事內部結構**，列出這段該有哪些功能鏡，
餵給 `shot_slots.expand_shot_slots`（它會展開成 1 段 N 鏡）。

功能詞彙（`shot_slots` 既有）：`establish / action / detail / result / reaction / bridge`

| 藍圖意象訊號 | 必出的功能鏡 |
|---|---|
| 「鏡頭從一支筆開始」「窗外的光」 | `detail`（質地特寫先入） |
| 「定場」「整個場地」「遠遠看過去」 | `establish` |
| 「爬桿」「拖纜」「動作進行中」 | `action` |
| 「汗珠」「金屬扣環」「手的特寫」 | `detail` |
| 「線接上了」「攻頂那一刻」「完成」 | `result` |
| 「同伴看著」「笑出來」「點頭」 | `reaction`（optional） |
| 「帶到下一段」「畫面淡開」 | `bridge` / `exit_function` |

決定論規則：

```
一段至少要有 ≥2 個功能鏡（min_shots_per_segment，呼應 editing_policy）。
有「動作」語感 → 必含 action + 至少一個 detail（不准只給一個全景帶過）。
有「完成/落點」語感 → 必含 result，且 result 通常配長 hold（見 §3）。
emotional / establishing 可只 1 鏡，但要用 still treatment 撐住（見 §5），不准乾放。
```

---

## 3. 節奏 (pace / pacing) — 你最在意的「頻率」

**節奏從意象讀，不從數字填。** 導演把藍圖的密度語感翻成 `pace` + `preferred_shot_sec` 帶。
數字錨定參考片實測與 mode preset，不是拍腦袋。

| 藍圖密度語感 | pace | preferred_shot_sec | 對照 |
|---|---|---|---|
| 越切越快 / 疊上來 / 喘不過氣 / 引擎全開 | `fast` | `[1.5, 4]`（rhythmic_mv） | 參考片 montage 中位 ~1.47s |
| 快剪、輪播、活潑、日常切換 | `fast` | `[2.5, 6]`（training_recap） | 一般訓練段 |
| 沉穩、敘事推進、一段一段交代 | `hold` | `[3, 8]`（story_documentary） | |
| 安靜兩秒 / 凝住 / 留白 / 只剩風聲 | `hold` | 單鏡可達 `max_meaningful_shot_sec`（6–12s） | 參考片 17 個 >6s 的關鍵 hold |

決定論規則：

```
偵測到「密度語感」→ pace=fast，且該段 shot_slots 至少展開到
   ceil(段長 / preferred_shot_sec 上界) 個 slot（這是頻率達標的硬保證）。
偵測到「留白語感」→ 在該功能鏡（通常是 result/emotional）放一個 long hold，
   並且 max_single_source_sec 放寬、其餘照舊。
一段內可以「先 fast 後 hold」：密集鋪陳 + 落點留白，就是參考片 B5 那種引擎全開後安靜兩秒。
單一素材超過 mode 門檻又沒有 hold 理由 → visual_fatigue 報 fail（已 wired）。
```

---

## 4. 原音 (audio.role + original_audio_policy)

| 藍圖聲音語感 | audio.role | original_audio_policy | music |
|---|---|---|---|
| 純畫面、音樂襯底、無人聲 | `music` | `drop` | 主音軌 |
| 口令、隊呼、金屬聲、現場感、咬牙聲 | `diegetic` | `keep` | 鋪底不搶 |
| 他說、致詞、勉勵、訪談 | `duck` | `keep` | sidechain 讓位（致詞時音樂自動拉小） |

決定論規則：

```
藍圖只要寫到「他說 / 致詞 / 口令 / 現場聲」→ original_audio_policy 必為 keep。
不准因為「音樂比較好聽」把原音 drop 掉——這是把現場的靈魂抽掉。
testimony 段（§1 🔒）一定 duck + keep + ASR 字幕。
```

---

## 5. 靜照與文字層 (still treatment / text_layer)

照片不是「沒影片時的備胎」，是一種語言（呼應 material-treatment grammar）。

| 藍圖意象 | 處理 | 欄位 |
|---|---|---|
| 翻相簿、回憶、慢慢看 | 慢推 slow_push | `single_hold` + kenburns |
| 列舉項目、一張張帶過 | 對拍快切 | `photo_stack_beat` + `label_per_item` |
| 群像、大家一起 | 拼貼 | `collage` |
| 大合照、結訓 | 長 hold（情緒/證據例外允許久放） | `single_hold`，hold 理由=group_photo |

文字層：

| 藍圖訊號 | text_layer |
|---|---|
| 章節點題、段落主題 | `label`（底標） |
| 致詞、訪談、原音內容 | `subtitle: "auto"`（ASR 燒字） |
| 介紹某老師/某人、謝師卡 | `name_super`（人名下標） |
| 主題句、片名 | 片頭/片尾卡（注意：手寫動態/粒子＝特效，本表不涵蓋） |

---

## 5b. 轉場語意 (transition)

轉場也是讀出來的，不是每段套同一個。對應 `transition_philosophy.allowed` 與引擎可執行的
`direct_cut / dissolve(xfade) / beat_cut / graphic_bridge`。

| 藍圖語感 | transition | 引擎操作 |
|---|---|---|
| 硬切、直接接、同場景動作連續 | `direct_cut` | 無 xfade（narrative 預設） |
| 溶接、化開、回憶感、時間流過、柔和過 | `dissolve` | `xfade`（短秒數） |
| 踩拍切、跟著音樂走 | `beat_cut` | 切點對齊 beat grid |
| 章節之間、帶張卡片過去、換段落 | `graphic_bridge` | label/title 卡過場 |

決定論規則：

```
無訊號 → 預設 direct_cut（克制）。不要因為「比較炫」就到處 xfade。
段內動作連續 → direct_cut；跨時間/情緒/章節 → dissolve 或 graphic_bridge。
每個 transition 都要 reason_required；說不出理由就用硬切。
參考片：章節內多硬切+踩拍，章節交界才溶接/卡片過——可當預設手感。
```

---

## 6. 反面清單（防「隨意發揮」）

```
不准無訊號上特效：藍圖沒寫「轉場/強調」就不要硬塞 transition / effect。
不准一段一鏡帶過：除非是 emotional/establishing 且有 still treatment 撐住。
不准把 testimony/proof/identity 用 stock/generated 頂替（🔒 誠實守門）。
不准用數字硬湊頻率：cut 要從密度語感長出來，每個 cut 與每個 hold 都要有理由。
不准丟掉 thesis：每個 beat 的 content_pattern/情緒都要能勾回 thesis（意境一致）。
```

---

## 6b. 範圍邊界（哪些本表做，哪些是「特效」不碰）

使用者明確排除「特效」。本表只翻譯「剪輯/輕特效」可達的東西；偵測到下列**真特效**語感時，
**不要假裝用輕特效硬做**，而是標記 `effects_required: true` 並 route 給 effects-director / 人工
finishing，誠實告知「這段需要特效工，非本鏈可自動達成」。

| 本表涵蓋（剪輯 + 輕特效，可自動） | 排除（真特效，需另案 / 人工） |
|---|---|
| 硬切 / 溶接 / 踩拍切 / 卡片過場 | 手寫動態片頭、kinetic typography |
| Ken Burns 慢推/平移、photo_stack、collage | 粒子 / 閃光 / 光暈（如「感謝有您」金粉） |
| 章節標籤、人名下標、ASR 字幕 | split-screen 多畫面並排 |
| 原音 duck / diegetic、章節配樂 | 人名下標**內嵌人像卡**（PiP 合成） |
| 大合照長 hold、定場 | 3D / AE 級運鏡、去背合成 |

```
偵測規則：藍圖出現「手寫動畫/粒子/閃光/雙畫面/子母畫面/去背」→ effects_required，不自動硬幹。
其餘剪輯與輕特效語感 → 照本表翻成可執行操作。
這條邊界是誠實線：寧可標「需特效」也不要用爛替代假裝做到。
```

---

## 7. 走一遍：B5「現場實務」prose → 受控輸出（示範決定論）

輸入藍圖 prose：

> 這裡鏡頭不再客氣。爬桿、拖纜、高空換礙子，一個接一個、越切越快，汗水、口令、
> 金屬撞擊聲全疊上來，音樂往上推。要的是窒息般的密度，讓人喘不過氣。然後在最用力
> 的那一下——線接上的瞬間——突然留一個長鏡頭，世界安靜兩秒，只剩風聲。那兩秒就是驕傲。

導演照表翻譯（零自由發揮）：

```json
{
  "editing_intent": { "content_pattern": "action", "effects_intensity": "restrained" },
  "sequence_grammar": {
    "required_functions": ["establish", "action", "detail", "action", "detail", "result"],
    "exit_function": "bridge_to_next_chapter"
  },
  "pacing": { "preferred_shot_sec": [1.5, 4], "max_meaningful_shot_sec": 10,
              "allow_long_hold_when": ["story_payoff"] },
  "visual_style": { "pace": "fast" },
  "audio": { "role": "diegetic", "original_audio_policy": "keep",
             "reason": "口令/金屬聲/現場感" },
  "result_hold": { "function": "result", "hold_sec": 2.5, "audio": "wind_only",
                   "reason": "『安靜兩秒』『那兩秒就是驕傲』= 情緒落點留白" }
}
```

翻出來的每一格都能指回 prose 的某個字：
`越切越快`→fast/[1.5,4]、`口令/金屬聲`→diegetic+keep、`安靜兩秒`→result long hold、
`驕傲`→情緒落點。**節奏、原音、留白、情緒全是讀出來的，沒有一格是憑感覺填的。**

開場（establishing）同理：「一支筆」→detail 先入、「慢、安靜」→hold、
「快闔上的相簿」→single_hold 慢推、「人生的 0.66」→片頭卡。

---

## 8. 落地掛點（不新增 backend）

```
寫藍圖 skill   : 引導 + 完整性守門（每 beat 是否有 §1 情緒 / §2 結構 / §3 節奏 /
                §4 原音 / 情緒勾回 thesis；缺一個 block 要求補）。
讀藍圖 skill   : 用本表把 prose 翻成 content_pattern + sequence_grammar + pacing +
                audio + text_layer，寫進 segment_contract.json。
引擎（已存在）  : material_treatment.resolve_treatment（content_pattern→treatment→lane）
                + shot_slots.expand_shot_slots（required_functions→N 鏡）。
verify（已 wired）: visual_fatigue / treatment_audit / editorial_qa 檢查
                「頻率 / 留白 / 原音 / 結構」有沒有被忠實執行。
```

唯一缺的就是**中間這條翻譯**——本表把它寫成決定論規則。藍圖負責有靈魂，
這張表負責讓靈魂可被執行且每次一致。
