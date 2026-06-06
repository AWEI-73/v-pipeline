# ADR 2026-06-04 — SPEC canonical 格式 = JSON;HITL = dashboard

Status: Accepted
Context: Flow review(已整合進 `roadmap.md`,與 Codex 討論)提出 Node 3「core + facets
segment contract」,並問:authoring/canonical 要 YAML 還是 JSON?

## Decision

1. **Canonical / tool-facing 格式 = JSON 唯一。**
   - 所有 BUILD / VERIFY / dashboard / `state.json` / 測試只讀 normalized JSON
     (例:`segment_contract.json`)。工具**只消費、不重解釋** SPEC 意圖。
   - 現況本來就全 JSON(examples/*.json、`validate_mv_script`、`match_script_to_material`、
     `build_mv_state`/state.json)→ 選 JSON = 零遷移、零新依賴(不引 PyYAML)。

2. **不維持 YAML 當平行 canonical。** 雙 canonical = 兩個 validator + 轉換 bug + drift,
   與本專案「單一真相 / 收斂」方向相反。

3. **YAML 降級為「選配、單向 authoring 轉接」,且現階段不做。** 若日後要手寫 bootstrap
   檔,才加 `yaml→json` import adapter;它只 import、工具永不讀 YAML。

4. **Human-in-the-loop = dashboard(讀/複核)。** 長期人類編輯面是 node-timeline dashboard
   (產出 JSON),不是手寫檔。Review 明示「humans should not be forced to hand-edit YAML」。

5. **`reason` 欄位取代註解需求。** core+facets 每個 facet 帶 `reason` → 機器可讀、可稽核、
   verify 可查,優於 YAML 的 `#` 註解。JSON「不能註解」的弱點在此 schema 下消失。

## Consequences
- authoring 三路皆收斂到 JSON:agent 結構化輸出(主)、dashboard 編輯(人,主力)、
  YAML→JSON adapter(選配、未做)。
- segment contract(core+facets normalized JSON)為下一階段 SPEC 地基;**細部 schema 與
  dashboard 編輯 UX 由使用者於「整個流程跑通後」主導設計**(本 ADR 只釘格式決策,不含 schema 細節)。
- 不在 mv_cut / curator / state 任何熱路徑引入 YAML。

## Deferred(等流程 OK 後使用者設計)
- `spec-contract.md` skill + `segment_contract.json` 詳細 schema/validator。
- dashboard 節點互動編輯(目前唯讀呈現)。
- Node 8 fallback_route 第二分類軸(現 vt_core 已有 fix_class 地基)。
