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
          // A video clip's on-timeline length tracks its source window unless
          // the duration was independently set.
          if (clips[idx].type === "video") {
            clips[idx].duration_sec = round6(sd);
          }
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
  };
});
