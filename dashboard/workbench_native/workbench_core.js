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
      return {
        op: "add_effect", effect_id: e.effect_id,
        after: {
          preset: e.preset, target_slot_index: e.target_slot_index,
          start_sec: round6(e.start_sec), duration_sec: round6(e.duration_sec), intensity: e.intensity,
        },
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
    buildTimelinePatch: buildTimelinePatch,
    validatePreviewState: validatePreviewState,
    applySubtitleLocalPatch: applySubtitleLocalPatch,
    buildSubtitlePatch: buildSubtitlePatch,
    computeTrackMarkers: computeTrackMarkers,
    buildSavePayload: buildSavePayload,
    planVideoElementUpdate: planVideoElementUpdate,
    clipForPreviewPlayback: clipForPreviewPlayback,
  };
});
