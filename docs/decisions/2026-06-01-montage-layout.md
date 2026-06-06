# Montage 快切 layout（多圖快切蒙太奇）

- 日期：2026-05-31（記錄 2026-06-01）
- 狀態：完成
- 相關：effects-director、roadmap「特效美學進階 ③ 蒙太奇快切」

## 背景

使用者回饋 MV/旅遊段太單調：「都是一張或是幾張變成照片的影片而已」——
一段 = 一張照片撐全程。需要「投影片照片特效切換」：一段內多張照片快切。

## 決策

新增 `layout:"montage"` 段：拿該段 top-N 照片候選（`montage_n`，預設 6），
每張各生一支 Ken Burns 慢推短片，再 xfade-concat 成一段內快切的照片牆（MV 質感）。

- **與 collage 區分**：collage = 多圖**同框**並排（群像/對比）；montage = 多圖**接續**快切（節奏/旅遊 reel）。
- **不評 content_qa**：和 collage/title/local 一樣，montage 是設計版面、非單圖對題，
  content_qa 跳過（`kind in (title, collage, montage) or source==local`）。
- `media_pref:"photo"`；吃 `effects.grade` 與切入 `transition`。

## 實作

- `video_tools.py cmd_montage`：每張照片 → tempdir 生 Ken Burns 短片 → xfade-concat，
  `shutil.rmtree` 清理。**精確時長**：xfade-concat 會 overshoot ~ov+0.1s（末段帶轉場尾巴），
  故最終 `-t d` 裁切到精準目標長（尾巴內容已存在，無黑幀）。
- `video_pipeline.py render_montage` + render-loop 分支 `elif layout=="montage"`。
- `content_qa.py main()` 跳過 montage 段。
- `cmd_validate` 接受 montage layout。

## 踩坑

`zoompan d=frames` 對多幀輸入會**乘倍幀數**（151MB/172s 爆量）→ 改成每張獨立生短片
再 concat（而非單一 zoompan 吃多圖）。

## 驗證

journey MV 段（seg4-8）改 montage 6 張：precompose gate 過（7.800s vs 7.792s Δ8ms），
成片 seg4 三幀為三張不同火車照（駕駛艙 POV→紅色列車→老火車司機），快切成立。
QA 92.2 pass。commit `39e31a5`/`0aaffe3`。
