# Generality Test — SPEC 端跑兩題材(給 REVIEW)

驗「特化但可通用」:同一套 brief→contract→category→fallback→adapter→mv_script,
換 vocab+brief 跑不同題材,看 SPEC 層撐到哪、BUILD 引擎在哪斷。


## event_recap
- brief 驗證: ✅  | contract 驗證(對 vocab): ✅
- adapter→mv_script can_run: ✅  (errors=0)
- Node 8 fallback(若 missing):
    seg1 [venue_establishing] → dashboard_review (review=True)
    seg2 [booth_games] → dashboard_review (review=True)
    seg3 [candid_family] → stock_bridge (review=False)
    seg4 [group_photo] → dashboard_review (review=True)
- ⚠️ 通用性邊界:
    - video_type=event_recap:非已調校題材(僅 graduation_mv 跑通過)。
- 產物: `examples/genre_tests/event_recap/out/spec_result.json`

## knowledge
- brief 驗證: ✅  | contract 驗證(對 vocab): ✅
- adapter→mv_script can_run: ✅  (errors=0)
- Node 8 fallback(若 missing):
    seg1 [concept_broll] → dashboard_review (review=True)
    seg2 [diagram_or_chart] → stock_bridge (review=False)
    seg3 [concept_broll] → dashboard_review (review=True)
- ⚠️ 通用性邊界:
    - video_type=knowledge:非已調校題材(僅 graduation_mv 跑通過)。
    - timeline_source=tts 出現於 seg[1, 2, 3]:adapter(contract_to_mv_script)不讀 timeline_source → 仍生成 beat-driven MV payload。narration/tts 引擎未接 = BUILD 邊界。
    - voiceover_policy 出現於 seg[1, 2, 3]:MV adapter 不消費 voiceover → 旁白會掉。
    - style=narrative:MV chain 假設 style=mv;narrative 需另一條 BUILD。
    - subtitle=from_voiceover(seg[1, 2]):需先有旁白才能轉字幕,MV 線無此來源。
- 產物: `examples/genre_tests/knowledge/out/spec_result.json`

## 小結
- **SPEC 層(brief/contract/category/fallback)= 通用**:兩題材都驗得過,fallback 守門照題材性質正確分流。
- **BUILD adapter/引擎 = MV 特化**:event_recap 落在 MV 引擎內(adapter 生成可跑 payload);
  knowledge(tts/voiceover/narrative)SPEC 驗得過但 **adapter 是 MV-only**,timeline_source=tts、
  voiceover 會被丟 → 需要 narration adapter/引擎(就是既有 video_pipeline.py 那條,尚未接進 contract)。
- 結論:**骨架(SPEC/route/contract)通用且已證;BUILD 引擎特化(MV 已通、narration 待接);詞彙全特化但換 vocab 即換題材(event_recap 實證)。**