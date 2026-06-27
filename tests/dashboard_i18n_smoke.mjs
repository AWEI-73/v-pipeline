import assert from "assert";
import {
  stageLabelsZh,
  valueLabelsZh,
  statusLabelsZh,
  workbenchLabelsZh,
} from "../dashboard/src/i18n/zh.js";

assert.strictEqual(stageLabelsZh["Material Map"], "素材地圖");
assert.strictEqual(valueLabelsZh.material_first, "素材優先");
assert.strictEqual(statusLabelsZh.accepted, "已接受");
assert.strictEqual(workbenchLabelsZh.effectDraft, "特效意圖草稿");

console.log("dashboard_i18n smoke: 4 checks passed");
