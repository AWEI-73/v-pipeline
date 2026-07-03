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
  var Api = window.WorkbenchApi;
  var Materials = window.WorkbenchMaterials;

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
    effectAssets: [], // selectable effect assets from project_material_map (EF2)
    materialAssets: [], // project material browser; can replace selected timeline clips
    selectedAssetId: null,
    selectedSceneIndex: 0,
    trackSel: null,  // {type:'subtitle'|'cue'|'effect', id}
    trimDrag: null,
    seq: 0,
    thumbs: {},      // slot_index -> thumbnail url (NPE5 filmstrip)
    proxies: {},     // slot_index -> trimmed preview mp4 (NPE6 proxy cache)
  };

  var PRESETS = ["title_reveal", "zoom_punch", "flash", "speed_ramp_hint",
                 "freeze_frame_hint", "shake_light", "caption_emphasis"];
  var CUE_TYPES = ["hit", "whoosh", "riser", "impact", "bell", "transition", "title_pop"];

  var els = {};
  var rafId = null;
  var lastTick = 0;
  var TRACK_LABEL_WIDTH = 72;
  var TIMELINE_PX_PER_SEC = 72;

  function $(id) {
    return document.getElementById(id);
  }

  function cacheEls() {
    [
      "monitor", "stage-image", "stage-video", "preview-audio", "stage-empty",
      "material-map-summary", "asset-search", "asset-family-filter", "material-assets-list",
      "effect-overlay", "effect-label", "subtitle-overlay",
      "stage-meta", "btn-play", "btn-pause", "btn-rewind", "scrubber",
      "time-label", "frame-label", "audio-status", "inspector-empty", "inspector-body",
      "inspector-meta", "in-duration", "in-source-start", "in-source-duration",
      "field-source-start", "field-source-duration", "btn-apply-clip", "btn-replace-clip",
      "btn-move-left", "btn-move-right", "lane-video", "lane-subtitle",
      "lane-audio", "lane-effect", "playhead", "diagnostics", "dirty-flag",
      "timeline-scroll", "timeline-canvas", "timeline-ruler",
      "btn-download-patch", "btn-save-patch", "btn-sync-contract", "btn-export",
      "btn-save-all", "btn-add-cue", "effect-asset-select", "btn-add-fx", "track-inspector",
      "track-insp-title", "t-text", "t-preset", "t-cuetype", "t-start",
      "t-duration", "t-time", "t-strength", "tf-text", "tf-preset", "tf-cuetype",
      "tf-start", "tf-duration", "tf-time", "tf-strength",
      "btn-apply-track", "btn-delete-track", "drawer-media", "btn-drawer", "fit-only",
      "dico-material", "dico-music", "dico-subtitle", "dico-effect",
      "dot-material", "dot-music", "dot-subtitle", "dot-effect", "domain-inspector",
    ].forEach(function (id) {
      els[id.replace(/-/g, "_")] = $(id);
    });
  }

  // -- data ------------------------------------------------------------- //
  function loadPreview() {
    return Api.fetchPreviewTimeline()
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
        state.effects = (data.effects || []).filter(function (e) {
          return e.effect_id && !e.marker_only;
        }).map(function (e) { return Object.assign({}, e); });
        state.effectAssets = (data.effect_assets || []).map(function (a) { return Object.assign({}, a); });
        state.materialAssets = (data.material_assets || []).map(function (a) { return Object.assign({}, a); });
        state.selectedAssetId = null;
        state.selectedSceneIndex = 0;
        state.trackSel = null;
        state.dirty = false;
        state.currentTime = 0;
        renderAll();
        loadThumbnails();
        loadProxies();
        return fetchArtifactsAndUpdateDots();
      })
      .catch(function (err) {
        els.diagnostics.textContent = "載入 preview_timeline 失敗：" + err;
      });
  }

  // Filmstrip thumbnails (NPE5): fetched async; first build runs ffmpeg server-side.
  function loadThumbnails() {
    Api.fetchThumbnails()
      .then(function (m) {
        state.thumbs = (m && m.thumbnails) || {};
        renderTimelineLanes();
      })
      .catch(function () { /* thumbnails are best-effort */ });
  }

  // Preview proxies (NPE6): trimmed browser-friendly MP4s for video clips.
  // First call can be slow; missing proxies gracefully fall back to originals.
  function loadProxies() {
      Api.fetchProxies()
        .then(function (m) {
          state.proxies = (m && m.proxies) || {};
          renderMonitor();
        })
        .catch(function () { /* proxies are best-effort */ });
    }

  // -- render ----------------------------------------------------------- //
  function renderAll() {
    renderMaterialBrowser();
    renderTimelineLanes();
    renderEffectAssetSelect();
    renderDiagnostics();
    renderMonitor();
    renderTransport();
    updateDirty();
  }

  function renderEffectAssetSelect() {
    if (!els.effect_asset_select) return;
    els.effect_asset_select.innerHTML = '<option value="">僅使用預設</option>';
    state.effectAssets.forEach(function (asset) {
      var opt = document.createElement("option");
      opt.value = asset.asset_id;
      opt.textContent = asset.asset_id + " (" + asset.asset_type + ")";
      els.effect_asset_select.appendChild(opt);
    });
  }

  function materialFamilies() {
    return Materials.families(state.materialAssets);
  }

  function renderMaterialBrowser() {
    if (!els.material_assets_list) return;
    var families = materialFamilies();
    var current = els.asset_family_filter ? els.asset_family_filter.value : "";
    if (els.asset_family_filter) {
      els.asset_family_filter.innerHTML = '<option value="">全部類型</option>';
      families.forEach(function (fam) {
        var opt = document.createElement("option");
        opt.value = fam;
        opt.textContent = fam;
        els.asset_family_filter.appendChild(opt);
      });
      els.asset_family_filter.value = families.indexOf(current) >= 0 ? current : "";
    }

    var q = ((els.asset_search && els.asset_search.value) || "").toLowerCase();
    var famFilter = (els.asset_family_filter && els.asset_family_filter.value) || "";
    var assets = Materials.filterAssets(state.materialAssets, {
      query: q,
      family: famFilter,
    });
    var selectedClip = state.selectedSlot == null ? null : state.work.clips.find(function (c) {
      return c.slot_index === state.selectedSlot;
    });

    if (els.drawer_media) {
      var titleH2 = els.drawer_media.querySelector(".materials-head h2");
      if (titleH2) {
        titleH2.textContent = selectedClip ? "適合這段的素材" : "可用素材";
      }
    }

    var cards = selectedClip
      ? Materials.replacementCandidates(assets, selectedClip)
      : assets.map(function (asset) {
        return Object.assign({}, asset, {
          scene_index: 0,
          scene: (asset.scenes || [])[0] || {},
          match_status: "browse",
        });
      });

    if (selectedClip && els.fit_only && els.fit_only.checked) {
      cards = cards.filter(function (c) {
        return c.match_status === "accepted" || c.match_status === "candidate";
      });
    }

    if (els.material_map_summary) {
      els.material_map_summary.textContent = selectedClip
        ? cards.length + " 個可替換場景 / need " + (selectedClip.need_id || "未標")
        : assets.length + "/" + state.materialAssets.length + " 個素材";
    }
    els.material_assets_list.innerHTML = "";
    cards.forEach(function (a) {
      var card = document.createElement("div");
      var isSelected = a.asset_id === state.selectedAssetId && a.scene_index === state.selectedSceneIndex;
      card.className = "material-card" + (isSelected ? " selected" : "") + " match-" + (a.match_status || "browse");
      var preview = Core.materialAssetPreview(a);
      var thumb;
      if (preview.kind === "image" && preview.img_url) {
        thumb = document.createElement("img");
        thumb.src = preview.img_url;
        thumb.alt = "";
      } else {
        thumb = document.createElement("div");
        thumb.textContent = preview.label || "素材";
      }
      thumb.className = "material-thumb material-thumb-" + preview.kind;
      var body = document.createElement("div");
      var title = document.createElement("div");
      title.className = "material-title";
      title.textContent = a.asset_id;

      var badge = document.createElement("span");
      if (a.match_status === "accepted") {
        badge.className = "fit fit-ok";
        badge.textContent = "符合需求";
      } else if (a.match_status === "candidate") {
        badge.className = "fit fit-mid";
        badge.textContent = "候選";
      } else {
        badge.className = "fit fit-low";
        badge.textContent = "其他";
      }
      title.appendChild(badge);

      var meta = document.createElement("div");
      meta.className = "material-meta";
      var scene = a.scene || {};
      var matchLabel = a.match_status === "accepted" ? "符合需求"
        : a.match_status === "candidate" ? "候選需求"
        : selectedClip ? "其他素材" : "瀏覽素材";
      meta.textContent = [
        a.asset_type || "素材",
        scene.visual_family || a.visual_family || "未分類",
        scene.angle_scale || a.angle_scale || "未標角度",
        "scene " + a.scene_index,
        matchLabel,
      ].join(" · ");
      body.appendChild(title);
      body.appendChild(meta);
      card.appendChild(thumb);
      card.appendChild(body);
      card.draggable = true;
      card.title = "拖曳到時間軸片段，或先選片段後雙擊素材，即可替換。";
      card.ondragstart = function (ev) {
        state.selectedAssetId = a.asset_id;
        state.selectedSceneIndex = a.scene_index || 0;
        ev.dataTransfer.setData("application/x-hermes-asset-id", a.asset_id);
        ev.dataTransfer.setData("application/x-hermes-scene-index", String(a.scene_index || 0));
        ev.dataTransfer.setData("text/plain", a.asset_id);
        ev.dataTransfer.effectAllowed = "copy";
        renderMaterialBrowser();
      };
      card.onclick = function () {
        state.selectedAssetId = a.asset_id;
        state.selectedSceneIndex = a.scene_index || 0;
        els.diagnostics.textContent = "已選擇素材 " + a.asset_id + " / scene " + state.selectedSceneIndex + "，可替換目前選取片段。";
        renderMaterialBrowser();
      };
      card.ondblclick = function () {
        state.selectedAssetId = a.asset_id;
        state.selectedSceneIndex = a.scene_index || 0;
        if (state.selectedSlot == null) {
          els.diagnostics.textContent = "請先選擇時間軸片段，再雙擊素材替換。";
          renderMaterialBrowser();
          return;
        }
        replaceClipWithAsset(state.selectedSlot, a.asset_id, state.selectedSceneIndex);
      };
      els.material_assets_list.appendChild(card);
    });
  }

  function timelineMetrics() {
    var total = Math.max(0.1, (state.work && state.work.duration_sec) || 0.1);
    var viewport = els.timeline_scroll ? els.timeline_scroll.clientWidth : 800;
    var laneWidth = Math.max(240, viewport - TRACK_LABEL_WIDTH);
    var timelineWidth = Math.max(laneWidth, Math.ceil(total * TIMELINE_PX_PER_SEC));
    var scale = timelineWidth / total;
    return {
      total: total,
      viewport: viewport,
      timelineWidth: timelineWidth,
      canvasWidth: timelineWidth + TRACK_LABEL_WIDTH,
      scale: scale,
    };
  }

  function formatTimeLabel(sec) {
    var s = Math.max(0, Math.round(sec));
    var m = Math.floor(s / 60);
    var r = s % 60;
    return m + ":" + String(r).padStart(2, "0");
  }

  function renderTimelineRuler(metrics) {
    if (!els.timeline_ruler) return;
    els.timeline_ruler.innerHTML = "";
    els.timeline_ruler.style.width = metrics.canvasWidth + "px";
    var total = Math.ceil(metrics.total);
    var step = total > 120 ? 10 : 5;
    for (var t = 0; t <= total; t += step) {
      var x = TRACK_LABEL_WIDTH + t * metrics.scale;
      var tick = document.createElement("div");
      tick.className = "ruler-tick ruler-tick-major";
      tick.style.left = x + "px";
      els.timeline_ruler.appendChild(tick);
      var label = document.createElement("div");
      label.className = "ruler-label";
      label.style.left = x + "px";
      label.textContent = formatTimeLabel(t);
      els.timeline_ruler.appendChild(label);
    }
  }

  function ensurePlayheadVisible(metrics) {
    if (!els.timeline_scroll || !state.playing) return;
    var x = TRACK_LABEL_WIDTH + state.currentTime * metrics.scale;
    var left = els.timeline_scroll.scrollLeft;
    var right = left + els.timeline_scroll.clientWidth;
    if (x > right - 80) {
      els.timeline_scroll.scrollLeft = Math.max(0, x - els.timeline_scroll.clientWidth + 120);
    }
  }

  function renderTimelineLanes() {
    var lane = els.lane_video;
    var metrics = timelineMetrics();
    var scale = metrics.scale;
    if (els.timeline_canvas) {
      els.timeline_canvas.style.width = metrics.canvasWidth + "px";
    }
    [els.lane_video, els.lane_subtitle, els.lane_audio, els.lane_effect].forEach(function (l) {
      if (l) l.style.width = metrics.timelineWidth + "px";
    });
    renderTimelineRuler(metrics);
    lane.innerHTML = "";
    state.work.clips.forEach(function (c) {
      var b = document.createElement("div");
      b.className = "clip-block clip-" + c.type + " status-" + c.status;
      if (c.slot_index === state.selectedSlot) b.className += " selected";
      b.style.left = (c.timeline_start_sec * scale) + "px";
      b.style.width = Math.max(8, c.duration_sec * scale - 2) + "px";
      var thumb = state.thumbs[String(c.slot_index)];
      if (thumb) {
        b.classList.add("has-thumb");
        b.style.backgroundImage = "url('" + thumb + "')";
      }
      var label = "#" + c.slot_index + " " + (c.caption || c.scene_id || c.type);
      var orig = state.raw && state.raw.clips ? state.raw.clips.find(function (rc) { return rc.slot_index === c.slot_index; }) : null;
      var isReplaced = orig && (orig.asset_id !== c.asset_id || orig.scene_id !== c.scene_id);
      if (isReplaced) {
        label += "「已替換・草稿」";
      }
      b.textContent = label;
      b.title = c.type + " " + c.duration_sec.toFixed(2) + "s" + (isReplaced ? " (已替換・草稿)" : "");
      b.onclick = function () { selectClip(c.slot_index); };
      b.ondragover = function (ev) {
        if (!ev.dataTransfer.types || Array.prototype.indexOf.call(ev.dataTransfer.types, "application/x-hermes-asset-id") < 0) return;
        ev.preventDefault();
        b.classList.add("drop-target");
      };
      b.ondragleave = function () { b.classList.remove("drop-target"); };
      b.ondrop = function (ev) {
        ev.preventDefault();
        b.classList.remove("drop-target");
        var assetId = ev.dataTransfer.getData("application/x-hermes-asset-id") || ev.dataTransfer.getData("text/plain");
        var sceneIndex = parseInt(ev.dataTransfer.getData("application/x-hermes-scene-index") || "0", 10);
        replaceClipWithAsset(c.slot_index, assetId, Number.isInteger(sceneIndex) ? sceneIndex : 0);
      };
      attachTrimHandles(b, c);
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

  function cloneWorkState(work) {
    return {
      clips: (work.clips || []).map(function (c) { return Object.assign({}, c); }),
      subtitles: (work.subtitles || []).map(function (s) { return Object.assign({}, s); }),
      audio: (work.audio || []).map(function (a) { return Object.assign({}, a); }),
      effects: (work.effects || []).map(function (e) { return Object.assign({}, e); }),
      duration_sec: work.duration_sec,
    };
  }

  function attachTrimHandles(block, clip) {
    ["left", "right"].forEach(function (edge) {
      var h = document.createElement("span");
      h.className = "trim-handle trim-" + edge;
      h.title = edge === "left" ? "修剪片段開頭" : "修剪片段結尾";
      h.onpointerdown = function (ev) {
        beginTrimDrag(ev, clip.slot_index, edge);
      };
      block.appendChild(h);
    });
  }

  function beginTrimDrag(ev, slotIndex, edge) {
    ev.preventDefault();
    ev.stopPropagation();
    if (state.playing) pause();
    state.selectedSlot = slotIndex;
    state.trimDrag = {
      slot_index: slotIndex,
      edge: edge,
      start_x: ev.clientX,
      base: cloneWorkState(state.work),
      changed: false,
    };
    document.addEventListener("pointermove", onTrimDragMove);
    document.addEventListener("pointerup", onTrimDragEnd);
    renderTimelineLanes();
  }

  function onTrimDragMove(ev) {
    if (!state.trimDrag) return;
    var metrics = timelineMetrics();
    var deltaSec = Core.round6((ev.clientX - state.trimDrag.start_x) / metrics.scale);
    var next = Core.trimClipEdge(state.trimDrag.base, {
      slot_index: state.trimDrag.slot_index,
      edge: state.trimDrag.edge,
      delta_sec: deltaSec,
      min_duration_sec: 0.1,
    });
    var before = state.trimDrag.base.clips.find(function (c) { return c.slot_index === state.trimDrag.slot_index; });
    var after = next.clips.find(function (c) { return c.slot_index === state.trimDrag.slot_index; });
    state.trimDrag.changed = !!before && !!after && (
      Core.round6(before.duration_sec) !== Core.round6(after.duration_sec) ||
      Core.round6(before.source_start_sec) !== Core.round6(after.source_start_sec) ||
      Core.round6(before.source_duration_sec) !== Core.round6(after.source_duration_sec)
    );
    state.work = next;
    if (next._trim_clamped) {
      els.diagnostics.textContent = "修剪已限制在核准的來源範圍內；若需要更多畫面，請改用素材替換。";
    }
    renderTimelineLanes();
    renderMonitor();
  }

  function onTrimDragEnd() {
    if (!state.trimDrag) return;
    var changed = state.trimDrag.changed;
    var slotIndex = state.trimDrag.slot_index;
    state.trimDrag = null;
    document.removeEventListener("pointermove", onTrimDragMove);
    document.removeEventListener("pointerup", onTrimDragEnd);
    if (changed) {
      state.dirty = true;
      updateDirty();
    }
    selectClip(slotIndex);
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
      els.stage_meta.textContent = "圖片 #" + clip.slot_index + " / 靜態 " + clip.duration_sec.toFixed(2) + "s";
    } else {
      img.hidden = true;
      empty.hidden = true;
      vid.hidden = false;
      var playbackClip = Core.clipForPreviewPlayback(clip, state.proxies);
      var wantTime = Core.getVideoPlaybackTime(playbackClip, state.currentTime);
      var videoPlan = Core.planVideoElementUpdate({
        slot_index: vid.getAttribute("data-slot"),
        src_url: vid.getAttribute("data-src-url") || "",
      }, playbackClip, state.thumbs);
      if (videoPlan.poster_url) {
        vid.poster = videoPlan.poster_url;
      }
      if (videoPlan.set_source) {
        // New source: show the clip thumbnail while the browser loads/seeks.
        // This prevents short clips from disappearing into a black wait state.
        vid.setAttribute("data-slot", String(clip.slot_index));
        vid.setAttribute("data-src-url", videoPlan.src_url);
        vid.src = videoPlan.src_url;
        var seekTarget = wantTime;
        vid.onloadeddata = function () {
          try { vid.currentTime = seekTarget; } catch (e) { /* not seekable yet */ }
          if (state.playing) { vid.play().catch(function () {}); }
        };
      } else if (vid.getAttribute("data-slot") !== String(clip.slot_index)) {
        // Same source, different approved window: keep the decoded .MOV and
        // only seek. This is critical for adjacent 1-2s source windows.
        vid.setAttribute("data-slot", String(clip.slot_index));
        if (Math.abs((vid.currentTime || 0) - wantTime) > 0.03) {
          try { vid.currentTime = wantTime; } catch (e) {}
        }
      } else if (!state.playing) {
        // scrubbing within the same clip: seek precisely
        if (Math.abs((vid.currentTime || 0) - wantTime) > 0.05) {
          try { vid.currentTime = wantTime; } catch (e) {}
        }
      } else {
        // playing within the same clip: let native playback run, correct only
        // on large drift so we don't trigger a re-decode every frame
        if (Math.abs((vid.currentTime || 0) - wantTime) > 0.5) {
          try { vid.currentTime = wantTime; } catch (e) {}
        }
      }
      els.stage_meta.textContent =
        "VID #" + clip.slot_index + " · src " + wantTime.toFixed(2) + "s (start " +
        clip.source_start_sec.toFixed(2) + ")";
    }

    var sub = Core.getActiveSubtitle(state.work.subtitles, state.currentTime);
    els.subtitle_overlay.textContent = sub ? sub.text : "";

    // Playhead position.
    var metrics = timelineMetrics();
    els.playhead.style.left = (TRACK_LABEL_WIDTH + state.currentTime * metrics.scale) + "px";
    ensurePlayheadVisible(metrics);

    els.time_label.textContent =
      state.currentTime.toFixed(2) + " / " + (state.work.duration_sec || 0).toFixed(2) + "s";
    els.frame_label.textContent = "f" + Core.secondsToFrame(state.currentTime, state.fps);
    els.scrubber.value = String(state.currentTime);
    syncAudioPreview(!state.playing);
    renderEffectPreview();
  }

  function renderEffectPreview() {
    var style = Core.buildEffectPreviewStyle(state.effects, state.currentTime);
    var transform = style.transform || "";
    els.stage_video.style.transform = transform;
    els.stage_image.style.transform = transform;
    els.effect_overlay.hidden = !style.active || !(style.overlay_opacity > 0);
    els.effect_overlay.style.opacity = String(style.overlay_opacity || 0);
    els.effect_label.hidden = !style.label;
    els.effect_label.textContent = style.label || "";
  }

  function previewAudioTrack() {
    return (state.work.audio || []).find(function (a) { return a && a.src_url; }) || null;
  }

  function syncAudioPreview(precise) {
    var aud = els.preview_audio;
    if (!aud) return;
    var track = previewAudioTrack();
    var plan = Core.planAudioElementUpdate({
      src_url: aud.getAttribute("data-src-url") || "",
    }, track || {});
    if (!track || !track.src_url) {
      aud.pause();
      if (els.audio_status) els.audio_status.textContent = "音訊：關閉";
      return;
    }
    if (plan.set_source) {
      aud.setAttribute("data-src-url", plan.src_url);
      aud.src = plan.src_url;
      aud.volume = 0.55;
    }
    var mediaTime = Core.getAudioPlaybackTime(track, state.currentTime);
    if (mediaTime == null) {
      aud.pause();
      if (els.audio_status) els.audio_status.textContent = "音訊：關閉";
      return;
    }
    function seek() {
      if (precise || Math.abs((aud.currentTime || 0) - mediaTime) > 0.5) {
        try { aud.currentTime = mediaTime; } catch (e) {}
      }
      if (state.playing) {
        aud.play()
          .then(function () {
            if (els.audio_status) els.audio_status.textContent = "音訊：播放中";
          })
          .catch(function () {
            if (els.audio_status) els.audio_status.textContent = "音訊：被瀏覽器阻擋";
          });
      } else {
        aud.pause();
        if (els.audio_status) els.audio_status.textContent = "音訊：可播放";
      }
    }
    if (aud.readyState === 0) {
      aud.onloadedmetadata = seek;
    } else {
      seek();
    }
  }

  function renderTransport() {
    els.btn_play.hidden = state.playing;
    els.btn_pause.hidden = !state.playing;
  }

  function updateDirty() {
    els.dirty_flag.textContent = state.dirty ? "有尚未儲存的本機修改" : "目前沒有本機修改";
    els.dirty_flag.className = state.dirty ? "dirty" : "muted";
  }

  // -- playback --------------------------------------------------------- //
  function play() {
    if (state.playing) return;
    state.playing = true;
    lastTick = performance.now();
    var vid = els.stage_video;
    if (!vid.hidden) { vid.play().catch(function () {}); }
    syncAudioPreview(true);
    renderTransport();
    rafId = requestAnimationFrame(tick);
  }

  function pause() {
    state.playing = false;
    if (rafId) cancelAnimationFrame(rafId);
    rafId = null;
    var vid = els.stage_video;
    if (!vid.hidden) { vid.pause(); }
    if (els.preview_audio) { els.preview_audio.pause(); }
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
    els.track_insp_title.textContent = "字幕 " + id;
    els.t_text.value = s.text;
    els.t_start.value = s.start_sec;
    els.t_duration.value = s.duration_sec;
    els.btn_delete_track.style.display = "none";
    showTrackFields(["text", "start", "duration"]);
    seekTo(s.start_sec + 0.001);
    renderTimelineLanes();
    renderInspector();
  }

  function selectCue(id) {
    state.trackSel = { type: "cue", id: id };
    var c = state.cues.find(function (x) { return x.cue_id === id; });
    if (!c) return;
    els.track_insp_title.textContent = "音效提示 " + id;
    els.t_cuetype.value = c.cue_type;
    els.t_time.value = c.time_sec;
    els.t_strength.value = c.strength;
    els.btn_delete_track.style.display = "";
    showTrackFields(["cuetype", "time", "strength"]);
    seekTo(c.time_sec);
    renderTimelineLanes();
    renderInspector();
  }

  function selectEffect(id) {
    state.trackSel = { type: "effect", id: id };
    var e = state.effects.find(function (x) { return x.effect_id === id; });
    if (!e) return;
    els.track_insp_title.textContent = "特效 " + id + "（意圖）";
    els.t_preset.value = e.preset;
    els.t_start.value = e.start_sec;
    els.t_duration.value = e.duration_sec;
    els.t_strength.value = e.intensity;
    els.btn_delete_track.style.display = "";
    showTrackFields(["preset", "start", "duration", "strength"]);
    seekTo(e.start_sec + 0.001);
    renderTimelineLanes();
    renderInspector();
  }

  function addCue() {
    var active = Core.getActiveClip(state.work.clips, state.currentTime);
    var id = "cue-" + (++state.seq);
    state.cues.push({
      cue_id: id, time_sec: Core.round6(state.currentTime), cue_type: "impact",
      strength: 3, anchor_clip_slot_index: active ? active.slot_index : null,
    });
    state.dirty = true; updateDirty();
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
    selectCue(id);
  }

  function addFx() {
    if (state.selectedSlot == null) {
      els.diagnostics.textContent = "請先選擇片段，再新增特效。";
      return;
    }
    var clip = state.work.clips.find(function (c) { return c.slot_index === state.selectedSlot; });
    if (!clip) return;
    var id = "fx-" + (++state.seq);
    var fx = {
      effect_id: id, preset: "zoom_punch", target_slot_index: clip.slot_index,
      start_sec: Core.round6(clip.timeline_start_sec),
      duration_sec: Core.round6(Math.min(0.6, clip.duration_sec)), intensity: 3,
    };
    var assetId = els.effect_asset_select ? els.effect_asset_select.value : "";
    if (assetId) fx.asset_id = assetId;
    state.effects.push(fx);
    state.dirty = true; updateDirty();
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
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
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
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
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
  }

  function saveAll() {
    var payload = Core.buildSavePayload({
      timelineBefore: state.raw.clips, timelineAfter: state.work.clips,
      subsBefore: state.rawSubs, subsAfter: state.work.subtitles,
      cues: state.cues, effects: state.effects,
      base_timeline_ref: (state.raw && state.raw.source_artifact) || "timeline.json",
    });
    if (!Object.keys(payload).length) {
      els.diagnostics.textContent = "目前沒有跨軌修改可儲存。";
      return;
    }
    els.diagnostics.textContent = "正在儲存全部軌道...";
    Api.saveAll(payload)
      .then(function (res) {
        if (res.ok && res.j.ok) {
          var s = res.j.summary || {};
          els.diagnostics.textContent = "已儲存全部 -> " + (res.j.written || []).join(", ") +
            " [時間軸 " + (s.timeline_edits || 0) + ", 字幕 " + (s.subtitle_edits || 0) +
            ", 音效提示 " + (s.audio_cues || 0) + ", 特效 " + (s.effect_intents || 0) + "]";
          state.dirty = false; updateDirty();
          fetchArtifactsAndUpdateDots();
        } else {
          els.diagnostics.textContent = "儲存全部被拒絕，未寫入任何檔案：" + JSON.stringify(res.j.errors || res.j);
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "儲存全部失敗：" + err; });
  }

  // -- domain contract inspector views ---------------------------------- //
  function updateDomainDots() {
    var materialActive = true;
    var musicActive = state.raw && state.raw.audio && state.raw.audio.length > 0;
    var subtitleActive = state.raw && state.raw.subtitles && state.raw.subtitles.length > 0;
    var effectActive = (state.raw && state.raw.effects && state.raw.effects.length > 0) || (state.effectAssets && state.effectAssets.length > 0);

    var materialChanged = JSON.stringify(state.work.clips) !== JSON.stringify(state.raw.clips);
    var musicChanged = state.cues && state.cues.length > 0;
    var subtitleChanged = JSON.stringify(state.work.subtitles) !== JSON.stringify(state.rawSubs);
    var effectChanged = JSON.stringify(state.effects) !== JSON.stringify(state.raw.effects || []);

    var artifacts = state.artifacts || {};
    var draftArtifacts = (artifacts.workbench && artifacts.workbench.draft_artifacts) || {};

    function getDotClass(active, changed, patchKey) {
      if (!active) return "dot-off";
      if (changed) return "dot-draft";
      var patch = draftArtifacts[patchKey] || {};
      if (patch.exists) return "dot-ok";
      return "dot-ok";
    }

    if (els.dot_material) {
      els.dot_material.className = "dot " + getDotClass(materialActive, materialChanged, "timeline_patch");
    }
    if (els.dot_music) {
      els.dot_music.className = "dot " + getDotClass(musicActive, musicChanged, "audio_cue_patch");
    }
    if (els.dot_subtitle) {
      els.dot_subtitle.className = "dot " + getDotClass(subtitleActive, subtitleChanged, "subtitle_patch");
    }
    if (els.dot_effect) {
      els.dot_effect.className = "dot " + getDotClass(effectActive, effectChanged, "effect_patch");
    }
  }

  function fetchArtifactsAndUpdateDots() {
    var rootParam = window.location.search || "";
    return Api._fetchJson("/api/artifacts" + rootParam)
      .then(function (res) {
        state.artifacts = res;
        updateDomainDots();
        if (state.currentDomain) {
          renderDomainInspector();
        }
      })
      .catch(function (err) {
        console.error("Failed to fetch artifacts:", err);
      });
  }

  function renderDomainInspector() {
    var d = state.currentDomain;
    if (!d) return;

    var active = true;
    var changed = false;
    var title = "";
    var patchFile = "";
    var rows = [];
    var patchObj = {};

    var summary = (state.artifacts && state.artifacts.workbench && state.artifacts.workbench.draft_summary) || {};

    if (d === "material") {
      title = "素材契約";
      patchFile = "timeline_patch.json";
      active = true;
      changed = JSON.stringify(state.work.clips) !== JSON.stringify(state.raw.clips);
      rows = [
        ["涵蓋", state.work.clips.filter(function (c) { return c.asset_id; }).length + "/" + state.work.clips.length + " 段有素材"],
        ["人工調整", (summary.timeline_edits || 0) + " 段已修剪"],
        ["待補", state.work.clips.filter(function (c) { return !c.asset_id; }).length + " 段缺素材"]
      ];
      patchObj = buildPatch();
    } else if (d === "music") {
      title = "音樂契約";
      patchFile = "audio_cue_patch.json";
      active = state.raw && state.raw.audio && state.raw.audio.length > 0;
      changed = state.cues && state.cues.length > 0;
      rows = [
        ["主軌", (state.raw && state.raw.audio && state.raw.audio[0] ? state.raw.audio[0].label : "無")],
        ["音效提示", (state.cues || []).length + " 個標記"]
      ];
      patchObj = {
        artifact_role: "audio_cue_patch",
        version: 1,
        cues: state.cues
      };
    } else if (d === "subtitle") {
      title = "字幕口白契約";
      patchFile = "subtitle_patch.json";
      active = state.raw && state.raw.subtitles && state.raw.subtitles.length > 0;
      changed = JSON.stringify(state.work.subtitles) !== JSON.stringify(state.rawSubs);
      rows = [
        ["字幕總數", (state.work.subtitles || []).length + " 條"],
        ["草稿變更", (summary.subtitle_edits || 0) + " 條已修改"]
      ];
      patchObj = {
        artifact_role: "subtitle_patch",
        version: 1,
        subtitles: state.work.subtitles
      };
    } else if (d === "effect") {
      title = "特效契約";
      patchFile = "effect_patch.json";
      active = (state.raw && state.raw.effects && state.raw.effects.length > 0) || (state.effectAssets && state.effectAssets.length > 0);
      changed = JSON.stringify(state.effects) !== JSON.stringify(state.raw.effects || []);
      rows = [
        ["特效總數", (state.effects || []).length + " 個意圖"],
        ["可用特效", (state.effectAssets || []).length + " 種預設"]
      ];
      patchObj = {
        artifact_role: "effect_patch",
        version: 1,
        effects: state.effects
      };
    }

    var pillText = "已同步";
    var pillBg = "var(--green-bg)";
    var pillFg = "var(--green)";
    if (!active) {
      pillText = "未啟用";
      pillBg = "var(--gray-bg)";
      pillFg = "var(--muted)";
    } else if (changed) {
      pillText = "草稿修改中";
      pillBg = "var(--amber-bg)";
      pillFg = "var(--amber)";
    }

    var spaRoute = d === "material" ? "/material-map" :
                   d === "music" ? "/verify" :
                   d === "subtitle" ? "/verify" : "/verify";

    var html =
      '<div style="display:flex;align-items:center;margin-bottom:12px;"><h2 style="flex:1;margin:0;font-size:15px;">' + title + '</h2>' +
      '<button id="btn-close-domain-inspector" style="padding:2px 8px;cursor:pointer;background:none;border:1px solid var(--border);border-radius:4px;color:inherit;" type="button">✕</button></div>' +
      '<span class="pill" style="background:' + pillBg + ';color:' + pillFg + ';">' + pillText + '</span>' +
      rows.map(function(r){
        return '<div class="row"><span>' + r[0] + '</span><span>' + r[1] + '</span></div>';
      }).join('') +
      '<p style="font-size:12px;color:var(--muted);margin:10px 0 6px;">人工修改寫入: <code>' + patchFile + '</code></p>' +
      '<details style="margin-top:8px;"><summary style="font-size:12px;color:var(--muted);cursor:pointer;user-select:none;">檢視原始 JSON</summary>' +
      '<div class="jsonbox" style="margin-top:4px;max-height:220px;overflow-y:auto;background:var(--panel-2);padding:8px;border-radius:6px;font-family:monospace;font-size:11px;white-space:pre;">' + JSON.stringify(patchObj, null, 2) + '</div></details>' +
      '<button id="btn-expand-whitebox" style="width:100%;margin-top:14px;padding:8px;border-radius:6px;background:none;border:1px solid var(--accent);color:var(--accent);font-weight:600;cursor:pointer;" type="button">展開完整數據 (白盒)</button>';

    els.domain_inspector.innerHTML = html;

    document.getElementById("btn-close-domain-inspector").onclick = resetDomainInspector;
    document.getElementById("btn-expand-whitebox").onclick = function () {
      window.location.hash = "#" + spaRoute;
    };
  }

  function resetDomainInspector() {
    state.currentDomain = null;
    ["material", "music", "subtitle", "effect"].forEach(function (d) {
      if (els["dico_" + d]) {
        els["dico_" + d].classList.remove("on");
      }
    });
    renderInspector();
  }

  function renderInspector() {
    if (state.currentDomain) {
      els.inspector_empty.hidden = true;
      els.inspector_body.hidden = true;
      els.track_inspector.hidden = true;
      els.domain_inspector.hidden = false;
      renderDomainInspector();
    } else {
      els.domain_inspector.hidden = true;
      if (state.selectedSlot != null) {
        els.inspector_empty.hidden = true;
        els.inspector_body.hidden = false;
        els.track_inspector.hidden = true;
      } else if (state.trackSel != null) {
        els.inspector_empty.hidden = true;
        els.inspector_body.hidden = true;
        els.track_inspector.hidden = false;
      } else {
        els.inspector_empty.hidden = false;
        els.inspector_body.hidden = true;
        els.track_inspector.hidden = true;
      }
    }
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
    if (els.fit_only) {
      els.fit_only.checked = true;
    }
    renderTimelineLanes();
    renderMaterialBrowser();
    renderInspector();
  }

  function applyOp(op, after) {
    var before = state.work;
    state.work = Core.applyLocalPatch(state.work, { op: op, slot_index: state.selectedSlot, after: after });
    state.dirty = true;
    renderTimelineLanes();
    renderMonitor();
    updateDirty();
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
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

  function replaceClipWithAsset(slotIndex, assetId, sceneIndex) {
    var asset = state.materialAssets.find(function (a) { return a.asset_id === assetId; });
    if (!asset) {
      els.diagnostics.textContent = "替換失敗：找不到素材。";
      return;
    }
    var clip = state.work.clips.find(function (c) { return c.slot_index === slotIndex; });
    if (!clip) return;

    var candidates = Materials.replacementCandidates(state.materialAssets, clip);
    var cand = candidates.find(function (c) {
      return c.asset_id === assetId && (c.scene_index || 0) === (Number.isInteger(sceneIndex) ? sceneIndex : 0);
    });
    if (!cand) {
      var scenes = asset.scenes || [];
      var sIdx = Number.isInteger(sceneIndex) ? sceneIndex : 0;
      var scene = scenes[sIdx] || (scenes.length > 0 ? scenes[0] : null);
      var matchStatus = "other";
      if (scene) {
        matchStatus = Materials.matchStatusForNeed ? Materials.matchStatusForNeed(scene, clip.need_id) : "other";
      }
      cand = Object.assign({}, asset, {
        scene_index: sIdx,
        scene: scene,
        match_status: matchStatus,
      });
    }

    var assetType = String(cand.asset_type || "").toLowerCase();
    var isImage = assetType === "photo" || assetType === "image";
    if (!isImage) {
      var sceneObj = cand.scene || {};
      var start = parseFloat(sceneObj.start_sec) || 0;
      var end = parseFloat(sceneObj.end_sec) || 0;
      var sourceDur = Math.max(0.1, end - start);
      var clipDur = parseFloat(clip.duration_sec) || 0;
      if (sourceDur < clipDur) {
        var diff = (clipDur - sourceDur).toFixed(2);
        var msg = "素材長度不足(還差 " + diff + " 秒)";
        els.diagnostics.textContent = "替換失敗：" + msg;
        alert(msg);
        return;
      }
    }

    if (cand.match_status === "other" || cand.match_status === "browse") {
      var ok = confirm("這個素材不符合這段的契約需求,仍要替換?");
      if (!ok) return;
    }

    var before = state.work;
    var next = Core.replaceClipWithAsset(before, {
      slot_index: slotIndex,
      asset: asset,
      scene_index: Number.isInteger(sceneIndex) ? sceneIndex : 0,
    });
    if (next === before) {
      els.diagnostics.textContent = "替換失敗：素材沒有可用的場景或來源。";
      return;
    }
    state.work = next;
    state.selectedSlot = slotIndex;
    state.selectedAssetId = asset.asset_id;
    state.selectedSceneIndex = Number.isInteger(sceneIndex) ? sceneIndex : 0;
    state.dirty = true;
    els.diagnostics.textContent = "已用素材 " + asset.asset_id + " / scene " + state.selectedSceneIndex + " 替換片段 #" + slotIndex + "（草稿 patch）。";
    renderTimelineLanes();
    renderMaterialBrowser();
    renderMonitor();
    renderTransport();
    updateDirty();
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
    selectClip(slotIndex);
  }

  function replaceSelectedClip() {
    if (state.selectedSlot == null) {
      els.diagnostics.textContent = "請先選擇時間軸片段。";
      return;
    }
    if (!state.selectedAssetId) {
      els.diagnostics.textContent = "請先選擇素材。";
      return;
    }
    replaceClipWithAsset(state.selectedSlot, state.selectedAssetId, state.selectedSceneIndex || 0);
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
      els.diagnostics.textContent = "沒有本機修改可儲存。";
      return;
    }
    Api.savePatch(patch)
      .then(function (res) {
        if (res.ok && res.j.ok) {
          var align = res.j.spec_alignment || {};
          var note = "已儲存：" + (res.j.written || []).join(", ");
          if (align.correction_count) {
            note += " / 已對齊規格 " + align.correction_count + " 個欄位（fallback clamp）";
          }
          els.diagnostics.textContent = note;
          state.dirty = false;
          updateDirty();
          fetchArtifactsAndUpdateDots();
        } else {
          els.diagnostics.textContent = "Patch 被拒絕：" + JSON.stringify(res.j.errors || res.j);
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "儲存失敗：" + err; });
  }

  function syncContract() {
    var patch = buildPatch();
    if (!patch.patches.length) {
      els.diagnostics.textContent = "沒有本機修改可同步。";
      return;
    }
    els.diagnostics.textContent = "正在把修改同步成管線契約草稿...";
    Api.syncContract(patch)
      .then(function (res) {
        if (res.ok && res.j.ok) {
          var codes = {};
          (res.j.diagnostics || []).forEach(function (d) { codes[d.code] = (codes[d.code] || 0) + 1; });
          var codeStr = Object.keys(codes).map(function (k) { return k + "×" + codes[k]; }).join(", ");
          els.diagnostics.textContent =
            "契約同步：" + res.j.changes + " 個草稿變更 -> " +
            (res.j.written || []).join(", ") + (codeStr ? " [" + codeStr + "]" : "");
          fetchArtifactsAndUpdateDots();
        } else {
          // fail-closed: surface the reason (e.g. source window beyond scene bounds)
          var errs = (res.j.errors || [JSON.stringify(res.j)]).join(" | ");
          els.diagnostics.textContent = "契約同步被拒絕，未寫入任何檔案：" + errs;
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "同步失敗：" + err; });
  }

  function exportFfmpeg() {
    var patch = buildPatch();
    var savePayload = Core.buildSavePayload({
      timelineBefore: state.raw.clips, timelineAfter: state.work.clips,
      subsBefore: state.rawSubs, subsAfter: state.work.subtitles,
      cues: state.cues, effects: state.effects,
      base_timeline_ref: (state.raw && state.raw.source_artifact) || "timeline.json",
    });
    var effectPatch = savePayload.effect_patch || null;
    els.diagnostics.textContent = "正在透過 ffmpeg 匯出，可能需要一段時間...";
    els.btn_export.disabled = true;
    Api.exportFfmpeg({
      patch: patch.patches.length ? patch : null,
      effects: true,
      effect_patch: effectPatch,
    })
      .then(function (res) {
        if (res.ok && res.j.ok) {
          els.diagnostics.textContent =
            "已匯出 " + res.j.rendered_clips + " 個片段 -> " + res.j.out +
            "（canonical ffmpeg；final.mp4 不會被改動）";
        } else {
          els.diagnostics.textContent = "匯出失敗：" + (res.j.error || JSON.stringify(res.j));
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "匯出失敗：" + err; })
      .finally(function () { els.btn_export.disabled = false; });
  }

  // -- wire -------------------------------------------------------------- //
  function wire() {
    els.btn_play.onclick = play;
    els.btn_pause.onclick = pause;
    els.btn_rewind.onclick = function () { seekTo(0); };
    els.scrubber.oninput = function () { if (state.playing) pause(); seekTo(parseFloat(els.scrubber.value)); };
    els.btn_apply_clip.onclick = applyInspector;
    els.btn_replace_clip.onclick = replaceSelectedClip;
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

    ["material", "music", "subtitle", "effect"].forEach(function (d) {
      var btn = els["dico_" + d];
      if (btn) {
        btn.onclick = function () {
          if (state.currentDomain === d) {
            resetDomainInspector();
          } else {
            state.currentDomain = d;
            ["material", "music", "subtitle", "effect"].forEach(function (d2) {
              if (els["dico_" + d2]) els["dico_" + d2].classList.remove("on");
            });
            btn.classList.add("on");
            renderInspector();
          }
        };
      }
    });

    if (els.asset_search) els.asset_search.oninput = renderMaterialBrowser;
    if (els.asset_family_filter) els.asset_family_filter.onchange = renderMaterialBrowser;
    if (els.fit_only) els.fit_only.onchange = renderMaterialBrowser;
    if (els.btn_drawer && els.drawer_media) {
      els.btn_drawer.onclick = function () {
        var collapsed = els.drawer_media.classList.toggle("collapsed");
        localStorage.setItem("drawer_collapsed", collapsed ? "true" : "false");
        window.dispatchEvent(new Event("resize"));
      };
      if (localStorage.getItem("drawer_collapsed") === "true") {
        els.drawer_media.classList.add("collapsed");
      }
    }
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
