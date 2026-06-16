/*
 * Node smoke test for the Hermes-native preview core (no test runner required).
 *   node tests/workbench_core_smoke.js
 * Exits non-zero on first failure.
 */
const assert = require("assert");
const path = require("path");
const Core = require(path.join(__dirname, "..", "dashboard", "workbench_native", "workbench_core.js"));

let count = 0;
function check(name, fn) {
  fn();
  count++;
  console.log("  ok - " + name);
}

const clips = [
  { id: "slot-0", slot_index: 0, type: "image", duration_sec: 2.0, source_start_sec: 0, source_duration_sec: 2.0 },
  { id: "slot-1", slot_index: 1, type: "video", duration_sec: 3.0, source_start_sec: 1.5, source_duration_sec: 3.0 },
  { id: "slot-2", slot_index: 2, type: "image", duration_sec: 1.0, source_start_sec: 0, source_duration_sec: 1.0 },
];

check("computeTimeline is deterministic", function () {
  const t = Core.computeTimeline(clips);
  assert.strictEqual(t[0].timeline_start_sec, 0);
  assert.strictEqual(t[1].timeline_start_sec, 2.0);
  assert.strictEqual(t[2].timeline_start_sec, 5.0);
  assert.strictEqual(t[2].timeline_end_sec, 6.0);
  assert.strictEqual(Core.totalDuration(t), 6.0);
});

check("getActiveClip picks correct clip per time", function () {
  const t = Core.computeTimeline(clips);
  assert.strictEqual(Core.getActiveClip(t, 0).slot_index, 0);   // image
  assert.strictEqual(Core.getActiveClip(t, 2.5).slot_index, 1); // video
  assert.strictEqual(Core.getActiveClip(t, 5.5).slot_index, 2); // image again
  assert.strictEqual(Core.getActiveClip(t, 99), null);
});

check("getVideoPlaybackTime maps to source_start + offset", function () {
  const t = Core.computeTimeline(clips);
  const v = Core.getActiveClip(t, 3.0); // video clip starts at 2.0, source_start 1.5
  assert.strictEqual(v.type, "video");
  assert.strictEqual(Core.getVideoPlaybackTime(v, 3.0), 2.5); // 1.5 + (3.0-2.0)
});

check("applyLocalPatch set_duration updates and recomputes", function () {
  const state = { clips: Core.computeTimeline(clips) };
  const next = Core.applyLocalPatch(state, { op: "set_duration", slot_index: 0, after: { duration_sec: 4.0 } });
  assert.strictEqual(next.clips[0].duration_sec, 4.0);
  assert.strictEqual(next.clips[1].timeline_start_sec, 4.0); // shifted
  // original untouched (immutability)
  assert.strictEqual(state.clips[0].duration_sec, 2.0);
});

check("applyLocalPatch set_source_window updates video start", function () {
  const state = { clips: Core.computeTimeline(clips) };
  const next = Core.applyLocalPatch(state, {
    op: "set_source_window", slot_index: 1,
    after: { source_start_sec: 5.0, source_duration_sec: 3.0 },
  });
  assert.strictEqual(next.clips[1].source_start_sec, 5.0);
});

check("applyLocalPatch move_clip reorders", function () {
  const state = { clips: Core.computeTimeline(clips) };
  const next = Core.applyLocalPatch(state, { op: "move_clip", slot_index: 2, after: { new_index: 0 } });
  assert.strictEqual(next.clips[0].slot_index, 2);
  assert.strictEqual(next.clips[1].slot_index, 0);
});

check("buildTimelinePatch emits correct ops", function () {
  const before = { clips: Core.computeTimeline(clips) };
  let after = Core.applyLocalPatch(before, { op: "set_duration", slot_index: 0, after: { duration_sec: 4.0 } });
  after = Core.applyLocalPatch(after, { op: "move_clip", slot_index: 2, after: { new_index: 0 } });
  const patch = Core.buildTimelinePatch(before, after);
  assert.strictEqual(patch.artifact_role, "timeline_patch");
  const ops = patch.patches.map(function (p) { return p.op; });
  assert.ok(ops.indexOf("set_duration") >= 0, "expected set_duration");
  assert.ok(ops.indexOf("move_clip") >= 0, "expected move_clip");
  const dur = patch.patches.find(function (p) { return p.op === "set_duration"; });
  assert.strictEqual(dur.before.duration_sec, 2.0);
  assert.strictEqual(dur.after.duration_sec, 4.0);
});

check("validatePreviewState flags bad clips", function () {
  const bad = { clips: [{ id: "x", type: "video", duration_sec: 0, source_start_sec: -1, source_duration_sec: 0 }] };
  const res = Core.validatePreviewState(bad);
  assert.strictEqual(res.ok, false);
  assert.ok(res.errors.length >= 2);
});

check("getActiveSubtitle resolves overlay by time", function () {
  const subs = [
    { id: "sub-1", text: "A", start_sec: 0, duration_sec: 3 },
    { id: "sub-2", text: "B", start_sec: 3, duration_sec: 2 },
  ];
  assert.strictEqual(Core.getActiveSubtitle(subs, 1).text, "A");
  assert.strictEqual(Core.getActiveSubtitle(subs, 4).text, "B");
  assert.strictEqual(Core.getActiveSubtitle(subs, 9), null);
});

console.log("\nworkbench_core smoke: " + count + " checks passed");
