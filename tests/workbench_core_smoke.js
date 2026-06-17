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

check("set_source_window does NOT clobber timeline duration", function () {
  let state = { clips: Core.computeTimeline(clips) };
  // user sets duration=6, then adjusts source window to a different length
  state = Core.applyLocalPatch(state, { op: "set_duration", slot_index: 1, after: { duration_sec: 6.0 } });
  state = Core.applyLocalPatch(state, {
    op: "set_source_window", slot_index: 1,
    after: { source_start_sec: 2.0, source_duration_sec: 1.0 },
  });
  assert.strictEqual(state.clips[1].duration_sec, 6.0); // duration stays user-set
  assert.strictEqual(state.clips[1].source_duration_sec, 1.0);
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

check("applySubtitleLocalPatch updates a subtitle in state", function () {
  const subs = [
    { id: "sub-1", text: "A", start_sec: 0, duration_sec: 3 },
    { id: "sub-2", text: "B", start_sec: 3, duration_sec: 2 },
  ];
  const next = Core.applySubtitleLocalPatch(subs, { id: "sub-2", text: "B!", start_sec: 3.5 });
  assert.strictEqual(next[1].text, "B!");
  assert.strictEqual(next[1].start_sec, 3.5);
  assert.strictEqual(subs[1].text, "B"); // original untouched
});

check("buildSubtitlePatch emits text + timing ops", function () {
  const before = [{ id: "sub-1", text: "A", start_sec: 0, duration_sec: 3 }];
  const after = [{ id: "sub-1", text: "A2", start_sec: 0.5, duration_sec: 3 }];
  const patch = Core.buildSubtitlePatch(before, after);
  assert.strictEqual(patch.artifact_role, "subtitle_patch");
  const ops = patch.patches.map(function (p) { return p.op; });
  assert.ok(ops.indexOf("set_subtitle_text") >= 0);
  assert.ok(ops.indexOf("set_subtitle_timing") >= 0);
});

check("computeTrackMarkers maps cues/effects to left ratios", function () {
  const cues = [{ cue_id: "c1", time_sec: 0 }, { cue_id: "c2", time_sec: 3 }];
  const marks = Core.computeTrackMarkers(cues, 6, "time_sec");
  assert.strictEqual(marks[0].left_ratio, 0);
  assert.strictEqual(marks[1].left_ratio, 0.5);
  const fx = Core.computeTrackMarkers([{ effect_id: "e1", start_sec: 6 }], 6, "start_sec");
  assert.strictEqual(fx[0].left_ratio, 1); // clamped
});

check("buildSavePayload is deterministic and layer-selective", function () {
  const tl = Core.computeTimeline(clips);
  const after = Core.applyLocalPatch({ clips: tl }, { op: "set_duration", slot_index: 0, after: { duration_sec: 4.0 } });
  const input = {
    timelineBefore: tl, timelineAfter: after.clips,
    subsBefore: [{ id: "sub-1", text: "A", start_sec: 0, duration_sec: 3 }],
    subsAfter: [{ id: "sub-1", text: "A2", start_sec: 0, duration_sec: 3 }],
    cues: [{ cue_id: "c1", time_sec: 1, cue_type: "impact", strength: 3 }],
    effects: [{ effect_id: "e1", preset: "flash", target_slot_index: 0, start_sec: 0, duration_sec: 0.5, intensity: 3 }],
  };
  const a = Core.buildSavePayload(input);
  const b = Core.buildSavePayload(input);
  assert.deepStrictEqual(a, b); // deterministic
  assert.ok(a.timeline_patch && a.subtitle_patch && a.audio_cue_patch && a.effect_patch);
  assert.strictEqual(a.audio_cue_patch.patches[0].op, "add_cue");
  assert.strictEqual(a.effect_patch.patches[0].after.preset, "flash");
});

check("buildSavePayload preserves effect asset_id", function () {
  const input = {
    timelineBefore: clips,
    timelineAfter: clips,
    effects: [{
      effect_id: "e1", preset: "flash", asset_id: "fx-light",
      target_slot_index: 0, start_sec: 0, duration_sec: 0.5, intensity: 3,
    }],
  };
  const payload = Core.buildSavePayload(input);
  assert.strictEqual(payload.effect_patch.patches[0].after.asset_id, "fx-light");
});

check("planVideoElementUpdate reuses same source across adjacent windows", function () {
  const prev = { slot_index: 1, src_url: "/media?src=a.mov" };
  const clip = { slot_index: 2, type: "video", src_url: "/media?src=a.mov" };
  const plan = Core.planVideoElementUpdate(prev, clip, { 2: "/media?src=thumb2.jpg" });
  assert.strictEqual(plan.reuse_source, true);
  assert.strictEqual(plan.set_source, false);
  assert.strictEqual(plan.poster_url, "/media?src=thumb2.jpg");
});

check("planVideoElementUpdate reloads different source and keeps poster fallback", function () {
  const prev = { slot_index: 1, src_url: "/media?src=a.mov" };
  const clip = { slot_index: 2, type: "video", src_url: "/media?src=b.mov" };
  const plan = Core.planVideoElementUpdate(prev, clip, { 2: "/media?src=thumb2.jpg" });
  assert.strictEqual(plan.reuse_source, false);
  assert.strictEqual(plan.set_source, true);
  assert.strictEqual(plan.poster_url, "/media?src=thumb2.jpg");
});

check("clipForPreviewPlayback uses proxy url and resets source timing", function () {
  const clip = {
    slot_index: 4, type: "video", src_url: "/media?src=original.mov",
    source_start_sec: 13.4, source_duration_sec: 1.2,
    timeline_start_sec: 20, duration_sec: 1.2,
  };
  const proxied = Core.clipForPreviewPlayback(clip, {
    4: { src_url: "/media?src=proxy.mp4", source_start_sec: 0, source_duration_sec: 1.2 },
  });
  assert.strictEqual(proxied.src_url, "/media?src=proxy.mp4");
  assert.strictEqual(proxied.source_start_sec, 0);
  assert.strictEqual(Core.getVideoPlaybackTime(proxied, 20.5), 0.5);
  assert.strictEqual(clip.source_start_sec, 13.4); // original clip unchanged
});

check("getAudioPlaybackTime maps playhead to audio source time", function () {
  const audio = { src_url: "/media?src=music.wav", start_sec: 2.0, source_start_sec: 10.0, duration_sec: 8.0 };
  assert.strictEqual(Core.getAudioPlaybackTime(audio, 1.0), null);
  assert.strictEqual(Core.getAudioPlaybackTime(audio, 2.0), 10.0);
  assert.strictEqual(Core.getAudioPlaybackTime(audio, 5.5), 13.5);
  assert.strictEqual(Core.getAudioPlaybackTime(audio, 11.0), null);
});

check("planAudioElementUpdate reloads source only when needed", function () {
  const a = { src_url: "/media?src=music.wav" };
  const reload = Core.planAudioElementUpdate({ src_url: "" }, a);
  assert.strictEqual(reload.set_source, true);
  assert.strictEqual(reload.src_url, "/media?src=music.wav");
  const reuse = Core.planAudioElementUpdate({ src_url: "/media?src=music.wav" }, a);
  assert.strictEqual(reuse.set_source, false);
});

check("getActiveEffects returns only effects active at playhead", function () {
  const effects = [
    { effect_id: "e1", preset: "flash", start_sec: 2, duration_sec: 1, intensity: 3 },
    { effect_id: "e2", preset: "zoom_punch", start_sec: 4, duration_sec: 1, intensity: 3 },
  ];
  assert.deepStrictEqual(Core.getActiveEffects(effects, 1.9), []);
  assert.strictEqual(Core.getActiveEffects(effects, 2.5)[0].effect_id, "e1");
  assert.deepStrictEqual(Core.getActiveEffects(effects, 3.0), []);
});

check("buildEffectPreviewStyle maps intent to css preview state", function () {
  const flash = Core.buildEffectPreviewStyle([{ preset: "flash", start_sec: 2, duration_sec: 1, intensity: 5 }], 2.1);
  assert.ok(flash.overlay_opacity > 0.5);
  const zoom = Core.buildEffectPreviewStyle([{ preset: "zoom_punch", start_sec: 2, duration_sec: 1, intensity: 4 }], 2.5);
  assert.ok(zoom.transform.indexOf("scale(") >= 0);
  const shake = Core.buildEffectPreviewStyle([{ preset: "shake_light", start_sec: 2, duration_sec: 1, intensity: 3 }], 2.25);
  assert.ok(shake.transform.indexOf("translate(") >= 0);
});

check("materialAssetPreview never treats video sources as img thumbnails", function () {
  const video = Core.materialAssetPreview({
    asset_id: "v1", asset_type: "video", src_url: "/media?src=a.mov",
  });
  assert.strictEqual(video.kind, "placeholder");
  assert.strictEqual(video.img_url, "");
  assert.strictEqual(video.label, "VIDEO");

  const image = Core.materialAssetPreview({
    asset_id: "p1", asset_type: "photo", src_url: "/media?src=a.jpg",
  });
  assert.strictEqual(image.kind, "image");
  assert.strictEqual(image.img_url, "/media?src=a.jpg");
});

console.log("\nworkbench_core smoke: " + count + " checks passed");
