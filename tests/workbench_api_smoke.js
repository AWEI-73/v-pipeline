/*
 * Node smoke test for the Workbench HTTP API client.
 *   node tests/workbench_api_smoke.js
 */
const assert = require("assert");
const path = require("path");

const Api = require(path.join(__dirname, "..", "dashboard", "workbench_native", "workbench_api.js"));

let calls = [];
global.fetch = function (url, opts) {
  calls.push({ url, opts: opts || {} });
  return Promise.resolve({
    ok: true,
    json: function () { return Promise.resolve({ ok: true, url: url }); },
  });
};

async function check(name, fn) {
  await fn();
  console.log("  ok - " + name);
}

(async function main() {
  await check("fetchPreviewTimeline uses canonical endpoint", async function () {
    calls = [];
    await Api.fetchPreviewTimeline();
    assert.strictEqual(calls[0].url, "/api/workbench/preview-timeline");
    assert.strictEqual(calls[0].opts.method, undefined);
  });

  await check("savePatch wraps patch payload", async function () {
    calls = [];
    await Api.savePatch({ artifact_role: "timeline_patch" });
    assert.strictEqual(calls[0].url, "/api/workbench/patch");
    assert.strictEqual(calls[0].opts.method, "POST");
    assert.deepStrictEqual(JSON.parse(calls[0].opts.body), {
      patch: { artifact_role: "timeline_patch" },
    });
  });

  await check("syncContract wraps patch payload", async function () {
    calls = [];
    await Api.syncContract({ patches: [] });
    assert.strictEqual(calls[0].url, "/api/workbench/sync-contract");
    assert.deepStrictEqual(JSON.parse(calls[0].opts.body), { patch: { patches: [] } });
  });

  await check("saveAll posts multi-layer payload unchanged", async function () {
    calls = [];
    const payload = { timeline_patch: { patches: [] }, effect_patch: { patches: [] } };
    await Api.saveAll(payload);
    assert.strictEqual(calls[0].url, "/api/workbench/save-all");
    assert.deepStrictEqual(JSON.parse(calls[0].opts.body), payload);
  });

  await check("exportFfmpeg posts export payload", async function () {
    calls = [];
    const payload = { patch: null, effects: true };
    await Api.exportFfmpeg(payload);
    assert.strictEqual(calls[0].url, "/api/workbench/export");
    assert.deepStrictEqual(JSON.parse(calls[0].opts.body), payload);
  });
}()).catch(function (err) {
  console.error(err && err.stack ? err.stack : err);
  process.exit(1);
});
