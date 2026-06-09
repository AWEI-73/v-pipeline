# Gold 範本藍圖 — 66 期養成班

逆推自人工剪好的 `66期養成班-高訓結訓影片全OK.mp4`（13:24 / ~368 shot / ~27.5 cuts/分）。

**這份是三件事的靶：**
1. `blueprint-interview` 引導 skill 的**產出標準**——「有靈魂的藍圖長這樣」。
2. `imagery-to-edit-lexicon` 對照表的**翻譯驗證**——prose 能不能翻成可執行剪輯。
3. 之後 E2E / 測試的**品質基準**。

對照 `video_project/graduation-demo/`（同一場活動的舊產出）：那份是 1 beat=1 segment=
1 clip 的乾目錄；這份每個 beat 的 prose 都藏著節奏/原音/意象/情緒落點，翻出來是多鏡的密集剪輯。

---

## 翻譯驗證：prose → contract enum（照 lexicon，零再創作）

| beat | prose 訊號 | content_pattern | required_functions | pace / preferred_shot_sec | audio | 鏡數(weight) |
|---|---|---|---|---|---|---|
| B5 現場實務 | 「越切越快」「口令/金屬聲」「安靜兩秒」 | `action` | establish/action/detail×2/result | `fast` [1.5,4] + result長hold | diegetic+keep | ~6+（w2.0） |
| B2 所長宣誓 | 「所長…誓言…全班覆誦」「聽得見現場」 | `testimony` 🔒 | establish/action/result | `hold` | duck+keep+ASR | real_material_only |
| B3 基本技能 | 「一張張…剪鐵線/繩結/洗礙子…越切越快」 | `enumeration` | （N項對拍） | `fast` [1.5,4] | music | photo_stack_beat ×3+ |
| B8 大合照 | 「緩緩拉開定住」「停得久一點」「證據」 | `proof` 🔒 | establish/result | `hold` 長hold | music swell | real_material_only |
| B1 開場 | 「一支筆」「慢、安靜」「翻相簿」 | `establishing` | detail/establish | `hold` | 環境音/低樂 | single_hold 慢推 |

每一格都指得回 prose 的字。**密度回來了**：B5/B3 不再是 1 clip，而是多鏡；B2/B8 落
🔒 誠實守門（不可被 stock/生成頂替）。

## 對齊參考片（為什麼這份能逼近 gold）

```
參考片：章節內密集 montage（中位 ~1.47s）+ 關鍵時刻長 hold（17 個 >6s）+ 致詞保留原音 + 大合照久放。
這份藍圖：
  B3/B5/B6 fast[1.5,4]      → 章節內密集快剪（對上 montage 密度）
  B2/B7 testimony + keep    → 宣誓/期勉保留現場原音（對上致詞原音）
  B5 result hold / B8 長hold → 攻頂留白、合照久放（對上關鍵長 hold）
  weight 2.0/1.8/1.5         → 重頭戲（實務/主任/合照）給夠篇幅，不被均分
```

## effects_required（誠實線：這些是「特效」，本鏈不自動做）

逆推時偵測到、但**超出剪輯+輕特效**範圍，標記交 effects-director / 人工 finishing：

```
B1  手寫動態片頭「人生的 0.66」      kinetic typography
B5  爬桿雙畫面 split-screen          多畫面合成
B8  「感謝有您」金粉閃光標題          粒子 / 光暈
B11 各班導師人名下標 + 內嵌人像卡     PiP 去背合成（且導師 identity 🔒）
```

→ 把這些拿掉，其餘（密集剪輯/原音/留白/章節標/大合照/空拍收尾/敘事弧）本鏈都能達成。
這正是「除了特效以外，其他能不能符合品質」的答案：**能**。

## 一步重生 contract（收斂後）

`segment_contract.json` 不是手刻的，是 compiler 從 `blueprint.json` + `decisions.json` 產的：

```powershell
python video_tools.py blueprint-to-contract blueprint.json decisions.json --out segment_contract.json
```

`decisions.json` = 導演的精簡判斷（每 beat 的 content_pattern + 關鍵畫面/節奏/audio/必放）。
機械的部分（functions/pace 三檔→preferred_shot_sec、treatment、weight 擺位、honesty 守門、
blueprint_ref 接線、reason/timeline_source、驗證 + 雙向 beat 閘）由 compiler 保證。改 decisions
就能重生整份 contract，不會再有「editing_grammar 放錯位置 weight 被吃掉」這種手刻 bug。

跑出的剪輯結構（660s 預算，密度感知 Node 9）：fast 章節 ~4s/鏡、calm 章節 ~7s/鏡、
hold 段（宣誓/主任/合照）少鏡長停；全片 ~94 鏡。要更貼近參考片的 27.5 cuts/分，是把更多
calm/hold 改 fast、縮短 hold——這個旋鈕現在完全在 decisions 的 pace 那一欄，引擎都接得住。
