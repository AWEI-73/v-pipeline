/*
 * Hermes-native preview engine -- pure core logic.
 *
 * This is the Hermes-native distillation of the Remotion-like preview model
 * (frame/currentTime/duration/composition + per-clip media timing), with zero
 * Remotion dependency. It is intentionally side-effect free so it can be unit
 * tested under plain `node` as well as run in the browser.
 *
 * Time is seconds-first (browser playback is in seconds); frames are derived.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module !== "undefined" && module.exports) {
    module.exports = api; // node / tests
  } else {
    root.WorkbenchCore = api; // browser
  }
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  function round6(n) {
    return Math.round((Number(n) || 0) * 1e6) / 1e6;
  }

  function secondsToFrame(seconds, fps) {
    return Math.round((Number(seconds) || 0) * (fps || 30));
  }

  /**
   * Deterministically compute timeline_start_sec / timeline_end_sec from the
   * ordered clip list. Order = array order (slot ordering is the array). The
   * input is not mutated.
   */
  function computeTimeline(clips) {
    let acc = 0;
    return (clips || []).map(function (clip) {
      const duration = Number(clip.duration_sec) || 0;
      const start = round6(acc);
      acc += duration;
      return Object.assign({}, clip, {
        timeline_start_sec: start,
        timeline_end_sec: round6(acc),
      });
    });
  }

  function totalDuration(timeline) {
    if (!timeline || timeline.length === 0) return 0;
    const last = timeline[timeline.length - 1];
    return round6(last.timeline_end_sec);
  }

  /**
   * Return the clip active at `currentTime` ([start, end)). Returns null when
   * before the first clip or at/after the end.
   */
  function getActiveClip(timeline, currentTime) {
    const t = Number(currentTime) || 0;
    for (let i = 0; i < timeline.length; i++) {
      const c = timeline[i];
      if (t >= c.timeline_start_sec && t < c.timeline_end_sec) {
        return c;
      }
    }
    // Clamp: exactly at the very end shows the last clip.
    if (timeline.length && t >= timeline[timeline.length - 1].timeline_end_sec) {
      return null;
    }
    return null;
  }

  /**
   * Local media time for a clip. For video this is source_start + offset into
   * the clip; for images source position is irrelevant (returns the offset).
   */
  function getVideoPlaybackTime(activeClip, currentTime) {
    if (!activeClip) return 0;
    const localOffset = (Number(currentTime) || 0) - (Number(activeClip.timeline_start_sec) || 0);
    const clamped = Math.max(0, localOffset);
    if (activeClip.type === "video") {
      return round6((Number(activeClip.source_start_sec) || 0) + clamped);
    }
    return round6(clamped);
  }

  /** Subtitle overlay active at currentTime, or null. */
  function getActiveSubtitle(subtitles, currentTime) {
    const t = Number(currentTime) || 0;
    for (let i = 0; i < (subtitles || []).length; i++) {
      const s = subtitles[i];
      const end = s.start_sec + s.duration_sec;
      if (t >= s.start_sec && t < end) return s;
    }
    return null;
  }

  /**
   * Apply a single local edit op to a preview state, returning a NEW state with
   * the timeline recomputed. Supported ops mirror the timeline_patch contract:
   *   - set_duration       { slot_index, after:{duration_sec} }
   *   - set_source_window  { slot_index, after:{source_start_sec, source_duration_sec} }
   *   - move_clip          { slot_index, after:{new_index} }
   */
  function applyLocalPatch(state, patch) {
    const next = Object.assign({}, state);
    let clips = (state.clips || []).map(function (c) {
      return Object.assign({}, c);
    });

    const op = patch.op;
    const slotIndex = patch.slot_index;
    const after = patch.after || {};
    const idx = clips.findIndex(function (c) {
      return c.slot_index === slotIndex;
    });
    if (idx === -1) return state; // no-op on unknown slot

    if (op === "set_duration") {
      const d = Number(after.duration_sec);
      if (d > 0) clips[idx].duration_sec = round6(d);
    } else if (op === "set_source_window") {
      if (after.source_start_sec != null) {
        clips[idx].source_start_sec = round6(Math.max(0, Number(after.source_start_sec)));
      }
      if (after.source_duration_sec != null) {
        const sd = Number(after.source_duration_sec);
        if (sd > 0) {
          clips[idx].source_duration_sec = round6(sd);
          // NOTE: timeline length (duration_sec) and consumed source length
          // (source_duration_sec) are independent -- the timeline slot can hold
          // a clip longer/shorter than its source window. duration_sec is owned
          // solely by set_duration, matching the Python timeline_patch side.
        }
      }
    } else if (op === "move_clip") {
      const dest = Math.max(0, Math.min(clips.length - 1, Number(after.new_index)));
      const moved = clips.splice(idx, 1)[0];
      clips.splice(dest, 0, moved);
    }

    next.clips = computeTimeline(clips);
    next.duration_sec = totalDuration(next.clips);
    return next;
  }

  /** Trim a clip edge by seconds and return a recomputed NEW state.
   *
   * edge="left": shorten from the head. For video this also advances
   * source_start_sec and reduces source_duration_sec so the patch remains a
   * real source-window trim. For photos, only timeline duration changes.
   *
   * edge="right": extend/shorten the tail. For video this mirrors the timeline
   * duration into source_duration_sec; photos keep their source timing intact.
   */
  function trimClipEdge(state, edit) {
    const next = Object.assign({}, state);
    const clips = (state.clips || []).map(function (c) {
      return Object.assign({}, c);
    });
    const idx = clips.findIndex(function (c) {
      return c.slot_index === edit.slot_index;
    });
    if (idx === -1) return state;

    const clip = clips[idx];
    const delta = Number(edit.delta_sec) || 0;
    const minDur = Number(edit.min_duration_sec) > 0 ? Number(edit.min_duration_sec) : 0.1;
    if (!delta) return state;

    if (edit.edge === "left") {
      const maxDelta = Math.max(0, (Number(clip.duration_sec) || 0) - minDur);
      const applied = Math.max(-0, Math.min(delta, maxDelta));
      if (!applied) return state;
      clip.duration_sec = round6((Number(clip.duration_sec) || 0) - applied);
      if (clip.type === "video") {
        clip.source_start_sec = round6((Number(clip.source_start_sec) || 0) + applied);
        clip.source_duration_sec = round6(Math.max(minDur, (Number(clip.source_duration_sec) || 0) - applied));
      }
    } else if (edit.edge === "right") {
      const desired = (Number(clip.duration_sec) || 0) + delta;
      clip.duration_sec = round6(Math.max(minDur, desired));
      if (clip.type === "video") {
        clip.source_duration_sec = round6(Math.max(minDur, (Number(clip.source_duration_sec) || 0) + delta));
      }
    } else {
      return state;
    }

    next.clips = computeTimeline(clips);
    next.duration_sec = totalDuration(next.clips);
    return next;
  }

  function _assetScene(asset, sceneIndex) {
    asset = asset || {};
    var scenes = Array.isArray(asset.scenes) ? asset.scenes : [];
    var idx = Number.isInteger(sceneIndex) ? sceneIndex : 0;
    for (var i = 0; i < scenes.length; i++) {
      if (scenes[i] && scenes[i].scene_index === idx) return scenes[i];
    }
    return scenes[idx] || null;
  }

  /** Replace one timeline clip with a project material-map asset scene.
   *
   * This is a draft operation only. The browser updates its preview state so
   * the user can inspect the swap immediately; the saved patch carries only
   * asset_id/scene_index as the canonical target, and Python re-resolves it
   * from project_material_map before writing patched_draft_timeline.json.
   */
  function replaceClipWithAsset(state, edit) {
    const next = Object.assign({}, state);
    const clips = (state.clips || []).map(function (c) {
      return Object.assign({}, c);
    });
    const idx = clips.findIndex(function (c) {
      return c.slot_index === edit.slot_index;
    });
    if (idx === -1) return state;

    const asset = edit.asset || {};
    if (!asset.asset_id || !asset.source_path) return state;
    const sceneIndex = Number.isInteger(edit.scene_index) ? edit.scene_index : 0;
    const scene = _assetScene(asset, sceneIndex);
    if (!scene) return state;

    const old = clips[idx];
    const assetType = String(asset.asset_type || "").toLowerCase();
    const isImage = assetType === "photo" || assetType === "image";
    const start = isImage ? 0 : round6(Number(scene.start_sec) || 0);
    const end = isImage ? null : round6(Number(scene.end_sec) || 0);
    const sourceDur = isImage
      ? round6(Number(old.duration_sec) || 0)
      : round6(Math.max(0.1, end - start));
    const duration = round6(Number(old.duration_sec) || sourceDur || 1);

    clips[idx] = Object.assign({}, old, {
      type: isImage ? "image" : "video",
      source_path: asset.source_path,
      src_url: asset.src_url,
      scene_id: asset.asset_id + ":" + sceneIndex,
      asset_id: asset.asset_id,
      asset_type: asset.asset_type,
      source_start_sec: start,
      source_duration_sec: sourceDur,
      duration_sec: duration,
      visual_family: scene.visual_family || asset.visual_family || null,
      angle_scale: scene.angle_scale || asset.angle_scale || null,
      caption: scene.caption || asset.caption || null,
      _replacement_asset_id: asset.asset_id,
      _replacement_scene_index: sceneIndex,
    });

    next.clips = computeTimeline(clips);
    next.duration_sec = totalDuration(next.clips);
    return next;
  }

  /**
   * Diff two preview states (same slot set) into a timeline_patch op list.
   * Order changes emit move_clip; field changes emit set_duration /
   * set_source_window. Deterministic and minimal.
   */
  function buildTimelinePatch(beforeState, afterState, opts) {
    opts = opts || {};
    const patches = [];
    const beforeClips = beforeState.clips || [];
    const afterClips = afterState.clips || [];

    const beforeById = {};
    beforeClips.forEach(function (c, i) {
      beforeById[c.slot_index] = { clip: c, order: i };
    });
    const afterOrder = {};
    afterClips.forEach(function (c, i) {
      afterOrder[c.slot_index] = i;
    });

    afterClips.forEach(function (c, newIdx) {
      const prior = beforeById[c.slot_index];
      if (!prior) return;
      const b = prior.clip;

      if (round6(b.duration_sec) !== round6(c.duration_sec)) {
        patches.push({
          op: "set_duration",
          slot_id: c.id,
          slot_index: c.slot_index,
          before: { duration_sec: round6(b.duration_sec) },
          after: { duration_sec: round6(c.duration_sec) },
          reason: opts.reason || "manual timing adjustment",
        });
      }

      const replacementChanged =
        b.source_path !== c.source_path ||
        b.scene_id !== c.scene_id ||
        b.asset_id !== c.asset_id ||
        b.type !== c.type;
      if (replacementChanged && c.asset_id != null) {
        patches.push({
          op: "replace_clip",
          slot_id: c.id,
          slot_index: c.slot_index,
          before: {
            scene_id: b.scene_id || null,
            source_path: b.source_path || null,
          },
          after: {
            asset_id: c.asset_id,
            scene_index: Number.isInteger(c._replacement_scene_index) ? c._replacement_scene_index : 0,
            duration_sec: round6(c.duration_sec),
          },
          reason: opts.reason || "material replacement",
        });
        return;
      }

      const startChanged = round6(b.source_start_sec) !== round6(c.source_start_sec);
      const sdurChanged = round6(b.source_duration_sec) !== round6(c.source_duration_sec);
      if (startChanged || sdurChanged) {
        patches.push({
          op: "set_source_window",
          slot_id: c.id,
          slot_index: c.slot_index,
          before: {
            source_start_sec: round6(b.source_start_sec),
            source_duration_sec: round6(b.source_duration_sec),
          },
          after: {
            source_start_sec: round6(c.source_start_sec),
            source_duration_sec: round6(c.source_duration_sec),
          },
          reason: opts.reason || "source window adjustment",
        });
      }

      if (prior.order !== newIdx) {
        patches.push({
          op: "move_clip",
          slot_id: c.id,
          slot_index: c.slot_index,
          after: { new_index: newIdx },
          reason: opts.reason || "reorder",
        });
      }
    });

    return {
      artifact_role: "timeline_patch",
      version: 1,
      base_timeline_ref: opts.base_timeline_ref || "timeline.json",
      patches: patches,
      diagnostics: [],
    };
  }

  // ---- Editorial runtime tracks (NPE4) ------------------------------- //

  /** Apply a local subtitle edit ({id, text?, start_sec?, duration_sec?}). */
  function applySubtitleLocalPatch(subs, edit) {
    return (subs || []).map(function (s) {
      if (s.id !== edit.id) return s;
      var next = Object.assign({}, s);
      if (edit.text != null) next.text = edit.text;
      if (edit.start_sec != null) next.start_sec = round6(Math.max(0, Number(edit.start_sec)));
      if (edit.duration_sec != null && Number(edit.duration_sec) > 0) {
        next.duration_sec = round6(Number(edit.duration_sec));
      }
      return next;
    });
  }

  /** Diff two subtitle lists into subtitle_patch ops. */
  function buildSubtitlePatch(before, after, opts) {
    opts = opts || {};
    var byId = {};
    (before || []).forEach(function (s) { byId[s.id] = s; });
    var patches = [];
    (after || []).forEach(function (s) {
      var b = byId[s.id];
      if (!b) return;
      if (b.text !== s.text) {
        patches.push({ op: "set_subtitle_text", subtitle_id: s.id, after: { text: s.text } });
      }
      if (round6(b.start_sec) !== round6(s.start_sec) || round6(b.duration_sec) !== round6(s.duration_sec)) {
        patches.push({
          op: "set_subtitle_timing", subtitle_id: s.id,
          after: { start_sec: round6(s.start_sec), duration_sec: round6(s.duration_sec) },
        });
      }
    });
    return {
      artifact_role: "subtitle_patch", version: 1,
      base_subtitle_ref: opts.base_subtitle_ref || "review_subtitles.srt",
      patches: patches, diagnostics: [],
    };
  }

  /** Marker left-ratio [0,1] for rendering a cue/effect onto a track lane. */
  function computeTrackMarkers(items, total, key) {
    var t = Number(total) || 1;
    return (items || []).map(function (it) {
      var pos = Number(it[key]) || 0;
      return Object.assign({}, it, { left_ratio: Math.max(0, Math.min(1, pos / t)) });
    });
  }

  /** Deterministic save payload for /api/workbench/save-all. */
  function buildSavePayload(input) {
    input = input || {};
    var timeline = buildTimelinePatch(
      { clips: input.timelineBefore || [] }, { clips: input.timelineAfter || [] },
      { base_timeline_ref: input.base_timeline_ref });
    var subtitle = buildSubtitlePatch(input.subsBefore || [], input.subsAfter || [],
      { base_subtitle_ref: input.base_subtitle_ref });
    var cues = (input.cues || []).map(function (c) {
      return {
        op: "add_cue", cue_id: c.cue_id,
        after: {
          time_sec: round6(c.time_sec), cue_type: c.cue_type,
          strength: c.strength, anchor_clip_slot_index: c.anchor_clip_slot_index == null ? null : c.anchor_clip_slot_index,
        },
      };
    });
    var effects = (input.effects || []).map(function (e) {
      var after = {
        preset: e.preset, target_slot_index: e.target_slot_index,
        start_sec: round6(e.start_sec), duration_sec: round6(e.duration_sec), intensity: e.intensity,
      };
      if (e.asset_id) after.asset_id = e.asset_id;
      return {
        op: "add_effect", effect_id: e.effect_id,
        after: after,
      };
    });
    var payload = {};
    if (timeline.patches.length) payload.timeline_patch = timeline;
    if (subtitle.patches.length) payload.subtitle_patch = subtitle;
    if (cues.length) payload.audio_cue_patch = { artifact_role: "audio_cue_patch", version: 1, patches: cues, diagnostics: [] };
    if (effects.length) payload.effect_patch = { artifact_role: "effect_patch", version: 1, patches: effects, diagnostics: [] };
    return payload;
  }

  /**
   * Decide how the browser <video> element should be updated for the active
   * clip. Slot identity and media source identity are separate: adjacent clips
   * can be different approved windows from the same large .MOV. In that case
   * the preview should keep the current src and only seek, otherwise very short
   * clips can pass before the browser finishes reloading the same file.
   */
  function planVideoElementUpdate(previous, clip, thumbnails) {
    previous = previous || {};
    clip = clip || {};
    thumbnails = thumbnails || {};
    var nextSrc = clip.src_url || "";
    var prevSrc = previous.src_url || "";
    var sameSource = !!nextSrc && nextSrc === prevSrc;
    return {
      slot_index: clip.slot_index,
      src_url: nextSrc,
      poster_url: thumbnails[String(clip.slot_index)] || thumbnails[clip.slot_index] || "",
      reuse_source: sameSource,
      set_source: !sameSource,
    };
  }

  /** Return a playback-only clip using a proxy when available.
   *
   * The original clip remains the contract/patch source of truth. A proxy is a
   * trimmed video file for browser preview, so its media time starts at zero.
   */
  function clipForPreviewPlayback(clip, proxies) {
    proxies = proxies || {};
    var proxy = clip && (proxies[String(clip.slot_index)] || proxies[clip.slot_index]);
    if (!proxy || !proxy.src_url) return clip;
    return Object.assign({}, clip, {
      src_url: proxy.src_url,
      source_start_sec: Number(proxy.source_start_sec) || 0,
      source_duration_sec: Number(proxy.source_duration_sec) || clip.source_duration_sec,
      preview_proxy_ref: proxy.proxy_ref || null,
    });
  }

  /** Local audio media time for the global playhead, or null when inactive. */
  function getAudioPlaybackTime(audio, currentTime) {
    if (!audio || !audio.src_url) return null;
    var start = Number(audio.start_sec) || 0;
    var dur = Number(audio.duration_sec) || 0;
    var t = Number(currentTime) || 0;
    if (!(dur > 0) || t < start || t >= start + dur) return null;
    return round6((Number(audio.source_start_sec) || 0) + (t - start));
  }

  /** Decide if the browser <audio> element needs a new src. */
  function planAudioElementUpdate(previous, audio) {
    previous = previous || {};
    audio = audio || {};
    var nextSrc = audio.src_url || "";
    var prevSrc = previous.src_url || "";
    return {
      src_url: nextSrc,
      set_source: !!nextSrc && nextSrc !== prevSrc,
      reuse_source: !!nextSrc && nextSrc === prevSrc,
    };
  }

  /** Active effect intent markers at currentTime. */
  function getActiveEffects(effects, currentTime) {
    var t = Number(currentTime) || 0;
    return (effects || []).filter(function (e) {
      var start = Number(e.start_sec) || 0;
      var dur = Number(e.duration_sec) || 0;
      return dur > 0 && t >= start && t < start + dur;
    });
  }

  function _effectProgress(e, currentTime) {
    var start = Number(e.start_sec) || 0;
    var dur = Number(e.duration_sec) || 1;
    return Math.max(0, Math.min(1, ((Number(currentTime) || 0) - start) / dur));
  }

  /** Map effect intent markers to lightweight monitor CSS preview state. */
  function buildEffectPreviewStyle(effects, currentTime) {
    var active = getActiveEffects(effects, currentTime);
    var scale = 1;
    var tx = 0;
    var ty = 0;
    var overlay = 0;
    var label = "";
    active.forEach(function (e) {
      var intensity = Math.max(1, Math.min(5, Number(e.intensity) || 1));
      var progress = _effectProgress(e, currentTime);
      var pulse = Math.sin(progress * Math.PI);
      if (e.preset === "flash" || e.preset === "title_reveal" || e.preset === "caption_emphasis") {
        overlay = Math.max(overlay, Math.min(0.8, 0.12 * intensity * (1 - progress)));
      } else if (e.preset === "zoom_punch") {
        scale = Math.max(scale, 1 + (0.012 * intensity * pulse));
      } else if (e.preset === "shake_light") {
        tx += Math.sin(progress * Math.PI * 8) * intensity;
        ty += Math.cos(progress * Math.PI * 6) * intensity * 0.5;
      } else if (e.preset === "speed_ramp_hint" || e.preset === "freeze_frame_hint") {
        label = e.preset;
      }
    });
    var transform = "translate(" + round6(tx) + "px, " + round6(ty) + "px) scale(" + round6(scale) + ")";
    return {
      active: active.length > 0,
      transform: transform,
      overlay_opacity: round6(overlay),
      label: label,
    };
  }

  /** Decide how a material browser card may preview an asset.
   *
   * The material browser is an inventory surface, not the timeline preview.
   * Do not point an <img> at MOV/MP4 sources; browsers render that as a broken
   * image icon. Video thumbnails are derived elsewhere when available.
   */
  function materialAssetPreview(asset) {
    asset = asset || {};
    var type = String(asset.asset_type || "").toLowerCase();
    var src = asset.src_url || "";
    if (type === "photo" || type === "image" || type === "effect_overlay" || type === "effect_image") {
      return { kind: "image", img_url: src, label: "" };
    }
    if (type === "video") {
      return { kind: "placeholder", img_url: "", label: "VIDEO" };
    }
    return { kind: "placeholder", img_url: "", label: (type || "ASSET").toUpperCase() };
  }

  /** Lightweight invariants check; returns {ok, errors}. */
  function validatePreviewState(state) {
    const errors = [];
    (state.clips || []).forEach(function (c) {
      if (!(Number(c.duration_sec) > 0)) {
        errors.push("clip " + c.id + ": duration_sec must be > 0");
      }
      if (Number(c.source_start_sec) < 0) {
        errors.push("clip " + c.id + ": source_start_sec must be >= 0");
      }
      if (c.type === "video" && Number(c.source_duration_sec) <= 0) {
        errors.push("clip " + c.id + ": video source_duration_sec must be > 0");
      }
    });
    return { ok: errors.length === 0, errors: errors };
  }

  return {
    round6: round6,
    secondsToFrame: secondsToFrame,
    computeTimeline: computeTimeline,
    totalDuration: totalDuration,
    getActiveClip: getActiveClip,
    getVideoPlaybackTime: getVideoPlaybackTime,
    getActiveSubtitle: getActiveSubtitle,
    applyLocalPatch: applyLocalPatch,
    trimClipEdge: trimClipEdge,
    replaceClipWithAsset: replaceClipWithAsset,
    buildTimelinePatch: buildTimelinePatch,
    validatePreviewState: validatePreviewState,
    applySubtitleLocalPatch: applySubtitleLocalPatch,
    buildSubtitlePatch: buildSubtitlePatch,
    computeTrackMarkers: computeTrackMarkers,
    buildSavePayload: buildSavePayload,
    planVideoElementUpdate: planVideoElementUpdate,
    clipForPreviewPlayback: clipForPreviewPlayback,
    getAudioPlaybackTime: getAudioPlaybackTime,
    planAudioElementUpdate: planAudioElementUpdate,
    getActiveEffects: getActiveEffects,
    buildEffectPreviewStyle: buildEffectPreviewStyle,
    materialAssetPreview: materialAssetPreview,
  };
});
