/*
 * Node smoke test for Workbench material-browser pure helpers.
 *   node tests/workbench_materials_smoke.js
 */
const assert = require("assert");
const path = require("path");

const Materials = require(path.join(__dirname, "..", "dashboard", "workbench_native", "workbench_materials.js"));

const assets = [
  {
    asset_id: "a0",
    asset_type: "video",
    visual_family: "training",
    angle_scale: "wide",
    caption: "rope drill",
    scenes: [{ scene_index: 0, caption: "rope drill", satisfies: [{ need_id: "training", status: "accepted" }] }],
  },
  {
    asset_id: "b0",
    asset_type: "photo",
    visual_family: "ceremony",
    angle_scale: "close",
    subject: "group",
    scenes: [{ scene_index: 0, caption: "group photo", satisfies: [{ need_id: "closing", status: "accepted" }] }],
  },
  {
    asset_id: "c0",
    asset_type: "video",
    visual_family: "training",
    angle_scale: "close",
    action_family: "climb",
    scenes: [{ scene_index: 2, caption: "climb drill", satisfies: [{ need_id: "training", status: "candidate" }] }],
  },
];

assert.deepStrictEqual(Materials.families(assets), ["ceremony", "training"]);
assert.deepStrictEqual(Materials.filterAssets(assets, { family: "ceremony" }).map(a => a.asset_id), ["b0"]);
assert.deepStrictEqual(Materials.filterAssets(assets, { query: "rope" }).map(a => a.asset_id), ["a0"]);
assert.deepStrictEqual(Materials.filterAssets(assets, { query: "VIDEO", family: "training" }).map(a => a.asset_id), ["a0", "c0"]);
assert.strictEqual(Materials.searchableText(assets[2]).includes("climb"), true);
assert.deepStrictEqual(
  Materials.replacementCandidates(assets, { need_id: "training", asset_id: "a0", source_path: "a.mp4" }).map(c => `${c.asset_id}:${c.scene_index}:${c.match_status}`),
  ["c0:2:candidate", "b0:0:other"]
);
assert.deepStrictEqual(
  Materials.replacementCandidates(assets, { need_id: "closing" }).map(c => `${c.asset_id}:${c.scene_index}:${c.match_status}`),
  ["b0:0:accepted", "a0:0:other", "c0:2:other"]
);

console.log("workbench_materials smoke: 7 checks passed");
