/*
 * Node smoke test for Workbench material-browser pure helpers.
 *   node tests/workbench_materials_smoke.js
 */
const assert = require("assert");
const path = require("path");

const Materials = require(path.join(__dirname, "..", "dashboard", "workbench_native", "workbench_materials.js"));

const assets = [
  { asset_id: "a0", asset_type: "video", visual_family: "training", angle_scale: "wide", caption: "rope drill" },
  { asset_id: "b0", asset_type: "photo", visual_family: "ceremony", angle_scale: "close", subject: "group" },
  { asset_id: "c0", asset_type: "video", visual_family: "training", angle_scale: "close", action_family: "climb" },
];

assert.deepStrictEqual(Materials.families(assets), ["ceremony", "training"]);
assert.deepStrictEqual(Materials.filterAssets(assets, { family: "ceremony" }).map(a => a.asset_id), ["b0"]);
assert.deepStrictEqual(Materials.filterAssets(assets, { query: "rope" }).map(a => a.asset_id), ["a0"]);
assert.deepStrictEqual(Materials.filterAssets(assets, { query: "VIDEO", family: "training" }).map(a => a.asset_id), ["a0", "c0"]);
assert.strictEqual(Materials.searchableText(assets[2]).includes("climb"), true);

console.log("workbench_materials smoke: 5 checks passed");
