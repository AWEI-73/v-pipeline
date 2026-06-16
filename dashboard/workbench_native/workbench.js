/*
 * Hermes Native Preview Workbench -- UI controller.
 *
 * Drives interactive preview from preview_timeline.json using the pure
 * WorkbenchCore engine. The middle monitor renders the *current material
 * composition* at currentTime (image / video / subtitle overlay) -- it never
 * plays final.mp4. All edits stay local until the user saves a timeline_patch.
 */
(function () {
  "use strict";
  var Core = window.WorkbenchCore;

  var state = {
    raw: null, // last server snapshot (baseline for diff)
    work: null, // working state with computeTimeline applied
    fps: 30,
    currentTime: 0,
    playing: false,
    selectedSlot: null,
    dirty: false,
    rawSubs: [],     // baseline subtitles for diffing
    cues: [],        // audio cue markers (NPE4)
    effects: [],     // effect intent markers (NPE4)
    trackSel: null,  // {type:'subtitle'|'cue'|'effect', id}
    seq: 0,
  };

  var PRESETS = ["title_reveal", "zoom_punch", "flash", "speed_ramp_hint",
                 "freeze_frame_hint", "shake_light", "caption_emphasis"];
  var CUE_TYPES = ["hit", "whoosh", "riser", "impact", "bell", "transition", "title_pop"];

  var els = {};
  var rafId = null;
  var lastTick = 0;

  function $(id) {
    return document.getElementById(id);
  }

  function cacheEls() {
    [
      "monitor", "stage-image", "stage-video", "stage-empty", "subtitle-overlay",
      "stage-meta", "btn-play", "btn-pause", "btn-rewind", "scrubber",
      "time-label", "frame-label", "inspector-empty", "inspector-body",
      "inspector-meta", "in-duration", "in-source-start", "in-source-duration",
      "field-source-start", "field-source-duration", "btn-apply-clip",
      "btn-move-left", "btn-move-right", "lane-video", "lane-subtitle",
      "lane-audio", "lane-effect", "playhead", "diagnostics", "dirty-flag",
      "btn-download-patch", "btn-save-patch", "btn-sync-contract", "btn-export",
      "btn-save-all", "btn-add-cue", "btn-add-fx", "track-inspector",
      "track-insp-title", "t-text", "t-preset", "t-cuetype", "t-start",
      "t-duration", "t-time", "t-strength", "tf-text", "tf-preset", "tf-cuetype",
      "tf-start", "tf-duration", "tf-time", "tf-strength",
      "btn-apply-track", "btn-delete-track",
    ].forEach(function (id) {
      els[id.replace(/-/g, "_")] = $(id);
    });
  }

  // -- data ------------------------------------------------------------- //
  function loadPreview() {
    return fetch("/api/workbench/preview-timeline")
      .then(function (r) { return r.json(); })
      .then(function (data) {
        state.raw = data;
        state.fps = data.fps || 30;
        var baseline = { clips: Core.computeTimeline(data.clips || []), subtitles: data.subtitles || [] };
        state.raw.clips = baseline.clips.map(function (c) { return Object.assign({}, c); });
        state.work = {
          clips: baseline.clips,
          subtitles: data.subtitles || [],
          audio: data.audio || [],
          effects: data.effects || [],
          duration_sec: Core.totalDuration(baseline.clips),
        };
        state.rawSubs = (data.subtitles || []).map(function (s) { return Object.assign({}, s); });
        state.cues = [];
        state.effects = [];
        state.trackSel = null;
        state.dirty = false;
        state.currentTime = 0;
        renderAll();
      })
      .catch(function (err) {
        els.diagnostics.textContent = "Failed to load preview_timeline: " + err;
      });
  }

  // -- render ----------------------------------------------------------- //
  function renderAll() {
    renderTimelineLanes();
    renderDiagnostics();
    renderMonitor();
    renderTransport();
    updateDirty();
  }

  function pxScale(laneWidth) {
    var total = state.work.duration_sec || 1;
    return laneWidth / total;
  }

  function renderTimelineLanes() {
    var lane = els.lane_video;
    var width = lane.clientWidth || 800;
    var scale = pxScale(width);
    lane.innerHTML = "";
    state.work.clips.forEach(function (c) {
      var b = document.createElement("div");
      b.className = "clip-block clip-" + c.type + " status-" + c.status;
      if (c.slot_index === state.selectedSlot) b.className += " selected";
      b.style.left = (c.timeline_start_sec * scale) + "px";
      b.style.width = Math.max(8, c.duration_sec * scale - 2) + "px";
      b.textContent = "#" + c.slot_index + " " + (c.caption || c.scene_id || c.type);
      b.title = c.type + " " + c.duration_sec.toFixed(2) + "s";
      b.onclick = function () { selectClip(c.slot_index); };
      lane.appendChild(b);
    });

    var sub = els.lane_subtitle;
    sub.innerHTML = "";
    (state.work.subtitles || []).forEach(function (s) {
      var b = document.createElement("div");
      b.className = "clip-block clip-subtitle";
      if (state.trackSel && state.trackSel.type === "subtitle" && state.trackSel.id === s.id) b.className += " selected";
      b.style.left = (s.start_sec * scale) + "px";
      b.style.width = Math.max(6, s.duration_sec * scale - 2) + "px";
      b.textContent = s.text;
      b.title = s.text;
      b.onclick = function () { selectSubtitle(s.id); };
      sub.appendChild(b);
    });

    // audio lane = user cue markers (NPE4); music marker shown faintly behind
    var audio = els.lane_audio;
    audio.innerHTML = "";
    (state.work.audio || []).forEach(function (a) {
      var bg = document.createElement("div");
      bg.className = "clip-block clip-audio";
      bg.style.left = "0px";
      bg.style.opacity = "0.25";
      bg.style.width = (Math.max(0.5, a.duration_sec) * scale - 2) + "px";
      bg.textContent = "♪ " + a.label;
      audio.appendChild(bg);
    });
    state.cues.forEach(function (c) {
      var m = document.createElement("div");
      m.className = "cue-marker";
      if (state.trackSel && state.trackSel.type === "cue" && state.trackSel.id === c.cue_id) m.className += " selected";
      m.style.left = (c.time_sec * scale) + "px";
      m.textContent = c.cue_type.slice(0, 2);
      m.title = c.cue_type + " @" + c.time_sec.toFixed(2) + "s ×" + c.strength;
      m.onclick = function () { selectCue(c.cue_id); };
      audio.appendChild(m);
    });

    // effect lane = user effect intent markers (NPE4)
    var fx = els.lane_effect;
    fx.innerHTML = "";
    state.effects.forEach(function (e) {
      var m = document.createElement("div");
      m.className = "fx-marker";
      if (state.trackSel && state.trackSel.type === "effect" && state.trackSel.id === e.effect_id) m.className += " selected";
      m.style.left = (e.start_sec * scale) + "px";
      m.style.width = Math.max(10, e.duration_sec * scale) + "px";
      m.textContent = "✦";
      m.title = e.preset + " on #" + e.target_slot_index + " @" + e.start_sec.toFixed(2) + "s ×" + e.intensity;
      m.onclick = function () { selectEffect(e.effect_id); };
      fx.appendChild(m);
    });

    els.scrubber.max = String(state.work.duration_sec || 0);
  }

  function renderDiagnostics() {
    var diag = (state.raw && state.raw.diagnostics) || [];
    if (!diag.length) { els.diagnostics.textContent = ""; return; }
    els.diagnostics.textContent = diag.map(function (d) {
      return "[" + (d.level || "info") + "] " + (d.code || "") + " " + (d.message || "");
    }).join("\n");
  }

  function renderMonitor() {
    var clip = Core.getActiveClip(state.work.clips, state.currentTime);
    var img = els.stage_image;
    var vid = els.stage_video;
    var empty = els.stage_empty;

    if (!clip) {
      img.hidden = true; vid.hidden = true; empty.hidden = false;
      els.stage_meta.textContent = "";
    } else if (clip.type === "image") {
      vid.hidden = true; vid.pause && vid.pause();
      empty.hidden = true;
      img.hidden = false;
      if (img.getAttribute("data-slot") !== String(clip.slot_index)) {
        img.src = clip.src_url || "";
        img.setAttribute("data-slot", String(clip.slot_index));
      }
      els.stage_meta.textContent = "IMG #" + clip.slot_index + " · still " + clip.duration_sec.toFixed(2) + "s";
    } else {
      img.hidden = true;
      empty.hidden = true;
      vid.hidden = false;
      if (vid.getAttribute("data-slot") !== String(clip.slot_index)) {
        vid.src = clip.src_url || "";
        vid.setAttribute("data-slot", String(clip.slot_index));
      }
      var wantTime = Core.getVideoPlaybackTime(clip, state.currentTime);
      // Only hard-seek when drifted (avoids fighting native playback).
      if (Math.abs((vid.currentTime || 0) - wantTime) > 0.25 || !state.playing) {
        try { vid.currentTime = wantTime; } catch (e) { /* not seekable yet */ }
      }
      els.stage_meta.textContent =
        "VID #" + clip.slot_index + " · src " + wantTime.toFixed(2) + "s (start " +
        clip.source_start_sec.toFixed(2) + ")";
    }

    var sub = Core.getActiveSubtitle(state.work.subtitles, state.currentTime);
    els.subtitle_overlay.textContent = sub ? sub.text : "";

    // Playhead position.
    var lane = els.lane_video;
    var width = lane.clientWidth || 800;
    var scale = pxScale(width);
    var laneLeft = lane.getBoundingClientRect().left - els.lane_video.parentElement.parentElement.getBoundingClientRect().left;
    els.playhead.style.left = (72 + state.currentTime * scale) + "px";

    els.time_label.textContent =
      state.currentTime.toFixed(2) + " / " + (state.work.duration_sec || 0).toFixed(2) + "s";
    els.frame_label.textContent = "f" + Core.secondsToFrame(state.currentTime, state.fps);
    els.scrubber.value = String(state.currentTime);
  }

  function renderTransport() {
    els.btn_play.hidden = state.playing;
    els.btn_pause.hidden = !state.playing;
  }

  function updateDirty() {
    els.dirty_flag.textContent = state.dirty ? "unsaved local edits" : "no local edits";
    els.dirty_flag.className = state.dirty ? "dirty" : "muted";
  }

  // -- playback --------------------------------------------------------- //
  function play() {
    if (state.playing) return;
    state.playing = true;
    lastTick = performance.now();
    var vid = els.stage_video;
    if (!vid.hidden) { vid.play().catch(function () {}); }
    renderTransport();
    rafId = requestAnimationFrame(tick);
  }

  function pause() {
    state.playing = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    var vid = els.stage_video;
    if (!vid.hidden) { vid.pause(); }
    renderTransport();
  }

  function tick(now) {
    if (!state.playing) return;
    var dt = (now - lastTick) / 1000;
    lastTick = now;
    state.currentTime += dt;
    if (state.currentTime >= (state.work.duration_sec || 0)) {
      state.currentTime = state.work.duration_sec || 0;
      renderMonitor();
      pause();
      return;
    }
    renderMonitor();
    rafId = requestAnimationFrame(tick);
  }

  function seekTo(t) {
    state.currentTime = Math.max(0, Math.min(state.work.duration_sec || 0, t));
    renderMonitor();
  }

  // -- track editing (subtitle / cue / effect) -------------------------- //
  function showTrackFields(fields) {
    ["text", "preset", "cuetype", "start", "duration", "time", "strength"].forEach(function (f) {
      els["tf_" + f].style.display = fields.indexOf(f) >= 0 ? "" : "none";
    });
    els.track_inspector.hidden = false;
  }

  function selectSubtitle(id) {
    state.trackSel = { type: "subtitle", id: id };
    var s = state.work.subtitles.find(function (x) { return x.id === id; });
    if (!s) return;
    els.track_insp_title.textContent = "Subtitle " + id;
    els.t_text.value = s.text;
    els.t_start.value = s.start_sec;
    els.t_duration.value = s.duration_sec;
    els.btn_delete_track.style.display = "none";
    showTrackFields(["text", "start", "duration"]);
    seekTo(s.start_sec + 0.001);
    renderTimelineLanes();
  }

  function selectCue(id) {
    state.trackSel = { type: "cue", id: id };
    var c = state.cues.find(function (x) { return x.cue_id === id; });
    if (!c) return;
    els.track_insp_title.textContent = "Audio cue " + id;
    els.t_cuetype.value = c.cue_type;
    els.t_time.value = c.time_sec;
    els.t_strength.value = c.strength;
    els.btn_delete_track.style.display = "";
    showTrackFields(["cuetype", "time", "strength"]);
    seekTo(c.time_sec);
    renderTimelineLanes();
  }

  function selectEffect(id) {
    state.trackSel = { type: "effect", id: id };
    var e = state.effects.find(function (x) { return x.effect_id === id; });
    if (!e) return;
    els.track_insp_title.textContent = "Effect " + id + " (intent)";
    els.t_preset.value = e.preset;
    els.t_start.value = e.start_sec;
    els.t_duration.value = e.duration_sec;
    els.t_strength.value = e.intensity;
    els.btn_delete_track.style.display = "";
    showTrackFields(["preset", "start", "duration", "strength"]);
    seekTo(e.start_sec + 0.001);
    renderTimelineLanes();
  }

  function addCue() {
    var active = Core.getActiveClip(state.work.clips, state.currentTime);
    var id = "cue-" + (++state.seq);
    state.cues.push({
      cue_id: id, time_sec: Core.round6(state.currentTime), cue_type: "impact",
      strength: 3, anchor_clip_slot_index: active ? active.slot_index : null,
    });
    state.dirty = true; updateDirty();
    selectCue(id);
  }

  function addFx() {
    if (state.selectedSlot == null) {
      els.diagnostics.textContent = "Select a clip first, then add an effect on it.";
      return;
    }
    var clip = state.work.clips.find(function (c) { return c.slot_index === state.selectedSlot; });
    if (!clip) return;
    var id = "fx-" + (++state.seq);
    state.effects.push({
      effect_id: id, preset: "zoom_punch", target_slot_index: clip.slot_index,
      start_sec: Core.round6(clip.timeline_start_sec),
      duration_sec: Core.round6(Math.min(0.6, clip.duration_sec)), intensity: 3,
    });
    state.dirty = true; updateDirty();
    selectEffect(id);
  }

  function applyTrack() {
    if (!state.trackSel) return;
    var t = state.trackSel;
    if (t.type === "subtitle") {
      state.work.subtitles = Core.applySubtitleLocalPatch(state.work.subtitles, {
        id: t.id, text: els.t_text.value,
        start_sec: parseFloat(els.t_start.value), duration_sec: parseFloat(els.t_duration.value),
      });
    } else if (t.type === "cue") {
      var c = state.cues.find(function (x) { return x.cue_id === t.id; });
      if (c) { c.cue_type = els.t_cuetype.value; c.time_sec = Core.round6(parseFloat(els.t_time.value)); c.strength = parseInt(els.t_strength.value, 10); }
    } else if (t.type === "effect") {
      var e = state.effects.find(function (x) { return x.effect_id === t.id; });
      if (e) { e.preset = els.t_preset.value; e.start_sec = Core.round6(parseFloat(els.t_start.value)); e.duration_sec = Core.round6(parseFloat(els.t_duration.value)); e.intensity = parseInt(els.t_strength.value, 10); }
    }
    state.dirty = true; updateDirty();
    renderTimelineLanes();
    renderMonitor();
  }

  function deleteTrack() {
    if (!state.trackSel) return;
    var t = state.trackSel;
    if (t.type === "cue") state.cues = state.cues.filter(function (x) { return x.cue_id !== t.id; });
    else if (t.type === "effect") state.effects = state.effects.filter(function (x) { return x.effect_id !== t.id; });
    else return; // subtitles are not deletable from the workbench
    state.trackSel = null;
    els.track_inspector.hidden = true;
    state.dirty = true; updateDirty();
    renderTimelineLanes();
  }

  function saveAll() {
    var payload = Core.buildSavePayload({
      timelineBefore: state.raw.clips, timelineAfter: state.work.clips,
      subsBefore: state.rawSubs, subsAfter: state.work.subtitles,
      cues: state.cues, effects: state.effects,
      base_timeline_ref: (state.raw && state.raw.source_artifact) || "timeline.json",
    });
    if (!Object.keys(payload).length) {
      els.diagnostics.textContent = "Nothing to save across tracks.";
      return;
    }
    els.diagnostics.textContent = "Saving all tracks…";
    fetch("/api/workbench/save-all", {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j.ok) {
          var s = res.j.summary || {};
          els.diagnostics.textContent = "Saved all → " + (res.j.written || []).join(", ") +
            " [timeline " + (s.timeline_edits || 0) + ", subs " + (s.subtitle_edits || 0) +
            ", cues " + (s.audio_cues || 0) + ", fx " + (s.effect_intents || 0) + "]";
          state.dirty = false; updateDirty();
        } else {
          els.diagnostics.textContent = "Save-all refused (nothing written): " + JSON.stringify(res.j.errors || res.j);
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "Save-all failed: " + err; });
  }

  // -- inspector / edits ------------------------------------------------ //
  function selectClip(slot) {
    state.selectedSlot = slot;
    var clip = state.work.clips.find(function (c) { return c.slot_index === slot; });
    if (!clip) return;
    els.inspector_empty.hidden = true;
    els.inspector_body.hidden = false;

    var meta = els.inspector_meta;
    meta.innerHTML = "";
    [["id", clip.id], ["type", clip.type], ["segment", clip.segment],
     ["scene_id", clip.scene_id], ["need_id", clip.need_id],
     ["visual_family", clip.visual_family], ["status", clip.status],
     ["timeline_start", clip.timeline_start_sec.toFixed(2) + "s"]].forEach(function (kv) {
      var dt = document.createElement("dt"); dt.textContent = kv[0];
      var dd = document.createElement("dd"); dd.textContent = (kv[1] == null ? "—" : kv[1]);
      meta.appendChild(dt); meta.appendChild(dd);
    });

    els.in_duration.value = clip.duration_sec;
    els.in_source_start.value = clip.source_start_sec;
    els.in_source_duration.value = clip.source_duration_sec;
    var isVideo = clip.type === "video";
    els.field_source_start.style.display = isVideo ? "" : "none";
    els.field_source_duration.style.display = isVideo ? "" : "none";

    // seek to clip start for immediate visual feedback
    seekTo(clip.timeline_start_sec + 0.001);
    renderTimelineLanes();
  }

  function applyOp(op, after) {
    var before = state.work;
    state.work = Core.applyLocalPatch(state.work, { op: op, slot_index: state.selectedSlot, after: after });
    state.dirty = true;
    renderTimelineLanes();
    renderMonitor();
    updateDirty();
  }

  function applyInspector() {
    if (state.selectedSlot == null) return;
    var clip = state.work.clips.find(function (c) { return c.slot_index === state.selectedSlot; });
    if (!clip) return;
    applyOp("set_duration", { duration_sec: parseFloat(els.in_duration.value) });
    if (clip.type === "video") {
      applyOp("set_source_window", {
        source_start_sec: parseFloat(els.in_source_start.value),
        source_duration_sec: parseFloat(els.in_source_duration.value),
      });
    }
    selectClip(state.selectedSlot);
  }

  function moveClip(dir) {
    if (state.selectedSlot == null) return;
    var idx = state.work.clips.findIndex(function (c) { return c.slot_index === state.selectedSlot; });
    var dest = idx + dir;
    if (dest < 0 || dest >= state.work.clips.length) return;
    applyOp("move_clip", { new_index: dest });
    selectClip(state.selectedSlot);
  }

  // -- patch out -------------------------------------------------------- //
  function buildPatch() {
    return Core.buildTimelinePatch(
      { clips: state.raw.clips },
      { clips: state.work.clips },
      { base_timeline_ref: (state.raw && state.raw.source_artifact) || "timeline.json" }
    );
  }

  function downloadPatch() {
    var patch = buildPatch();
    var blob = new Blob([JSON.stringify(patch, null, 2)], { type: "application/json" });
    var url = URL.createObjectURL(blob);
    var a = document.createElement("a");
    a.href = url; a.download = "timeline_patch.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  function savePatch() {
    var patch = buildPatch();
    if (!patch.patches.length) {
      els.diagnostics.textContent = "No local edits to save.";
      return;
    }
    fetch("/api/workbench/patch", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patch: patch }),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j.ok) {
          var align = res.j.spec_alignment || {};
          var note = "Saved: " + (res.j.written || []).join(", ");
          if (align.correction_count) {
            note += " · spec-aligned " + align.correction_count + " field(s) (fallback clamp)";
          }
          els.diagnostics.textContent = note;
          state.dirty = false;
          updateDirty();
        } else {
          els.diagnostics.textContent = "Patch rejected: " + JSON.stringify(res.j.errors || res.j);
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "Save failed: " + err; });
  }

  function syncContract() {
    var patch = buildPatch();
    if (!patch.patches.length) {
      els.diagnostics.textContent = "No local edits to sync.";
      return;
    }
    els.diagnostics.textContent = "Syncing edits to a draft pipeline contract…";
    fetch("/api/workbench/sync-contract", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patch: patch }),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j.ok) {
          var codes = {};
          (res.j.diagnostics || []).forEach(function (d) { codes[d.code] = (codes[d.code] || 0) + 1; });
          var codeStr = Object.keys(codes).map(function (k) { return k + "×" + codes[k]; }).join(", ");
          els.diagnostics.textContent =
            "Contract sync: " + res.j.changes + " draft change(s) → " +
            (res.j.written || []).join(", ") + (codeStr ? " [" + codeStr + "]" : "");
        } else {
          // fail-closed: surface the reason (e.g. source window beyond scene bounds)
          var errs = (res.j.errors || [JSON.stringify(res.j)]).join(" | ");
          els.diagnostics.textContent = "Contract sync refused (nothing written): " + errs;
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "Sync failed: " + err; });
  }

  function exportFfmpeg() {
    var patch = buildPatch();
    els.diagnostics.textContent = "Exporting via ffmpeg (this can take a while)…";
    els.btn_export.disabled = true;
    fetch("/api/workbench/export", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ patch: patch.patches.length ? patch : null }),
    })
      .then(function (r) { return r.json().then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j.ok) {
          els.diagnostics.textContent =
            "Exported " + res.j.rendered_clips + " clips → " + res.j.out +
            " (canonical ffmpeg; final.mp4 untouched)";
        } else {
          els.diagnostics.textContent = "Export failed: " + (res.j.error || JSON.stringify(res.j));
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "Export failed: " + err; })
      .finally(function () { els.btn_export.disabled = false; });
  }

  // -- wire -------------------------------------------------------------- //
  function wire() {
    els.btn_play.onclick = play;
    els.btn_pause.onclick = pause;
    els.btn_rewind.onclick = function () { seekTo(0); };
    els.scrubber.oninput = function () { if (state.playing) pause(); seekTo(parseFloat(els.scrubber.value)); };
    els.btn_apply_clip.onclick = applyInspector;
    els.btn_move_left.onclick = function () { moveClip(-1); };
    els.btn_move_right.onclick = function () { moveClip(1); };
    els.btn_download_patch.onclick = downloadPatch;
    els.btn_save_patch.onclick = savePatch;
    els.btn_sync_contract.onclick = syncContract;
    els.btn_export.onclick = exportFfmpeg;
    els.btn_save_all.onclick = saveAll;
    els.btn_add_cue.onclick = addCue;
    els.btn_add_fx.onclick = addFx;
    els.btn_apply_track.onclick = applyTrack;
    els.btn_delete_track.onclick = deleteTrack;
    PRESETS.forEach(function (p) { var o = document.createElement("option"); o.value = p; o.textContent = p; els.t_preset.appendChild(o); });
    CUE_TYPES.forEach(function (c) { var o = document.createElement("option"); o.value = c; o.textContent = c; els.t_cuetype.appendChild(o); });
    window.addEventListener("resize", function () { renderTimelineLanes(); renderMonitor(); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    cacheEls();
    wire();
    loadPreview();
  });
})();
