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
    currentDomain: null,
    reviewNotes: [],
    durationPolicy: "flexible",
    whiteboxView: null,
    projects: [],
    trackSel: null,  // {type:'subtitle'|'cue'|'effect', id}
    trimDrag: null,
    history: [],
    historyIndex: -1,
    savedHistoryIndex: 0,
    historyRestoring: false,
    aspectRatio: "16:9",
    seq: 0,
    thumbs: {},      // slot_index -> thumbnail url (NPE5 filmstrip)
    proxies: {},     // slot_index -> trimmed preview mp4 (NPE6 proxy cache)
  };

  var PRESETS = ["title_reveal", "zoom_punch", "flash", "speed_ramp_hint",
                  "freeze_frame_hint", "shake_light", "caption_emphasis"];
  var CUE_TYPES = ["hit", "whoosh", "riser", "impact", "bell", "transition", "title_pop"];
  var PRESET_LABELS = {
    title_reveal: "標題出現", zoom_punch: "快速推近", flash: "閃白",
    speed_ramp_hint: "速度變化", freeze_frame_hint: "畫面定格",
    shake_light: "輕微震動", caption_emphasis: "文字強調",
  };
  var CUE_LABELS = {
    hit: "節拍點", whoosh: "轉場聲", riser: "情緒上升", impact: "重點撞擊",
    bell: "提示鈴聲", transition: "段落轉場", title_pop: "標題出現",
  };
  var FAMILY_LABELS = {
    arrival: "抵達與開場",
    group_activity: "團體活動",
    hands_on: "動手體驗",
    interaction: "互動觀察",
    exhibition: "展項探索",
    learning: "學習過程",
    portrait: "人物",
    group_photo: "合照",
    closing: "結尾",
    transition: "過場",
    dialogue: "人物原聲",
    speech: "人物原聲",
    b_roll: "補充畫面",
    "container handling": "容器操作",
    "curiosity threshold": "入館探索",
    "digital projection": "數位投影互動",
    "foam apparatus observation": "泡沫裝置觀察",
    "foam result handling": "泡沫成果操作",
    "foam station repeat": "泡沫體驗",
    "fog sensory encounter": "霧氣感官體驗",
    "group activity wide": "團體活動全景",
    "illuminated column touch": "發光裝置互動",
    "illuminated installation memory": "發光裝置回憶",
    "light table drawing": "光桌創作",
    "light table drawing alternate": "光桌創作側拍",
    "light table drawing close": "光桌創作特寫",
    "model city operation": "模型城市操作",
    "model train controls": "模型列車操作",
    "rope mechanism challenge": "繩索機構挑戰",
    "sorting result detail": "分類成果特寫",
    "sorting station": "分類裝置體驗",
    "tabletop model exploration": "桌上模型探索",
    "white installation presence": "白色裝置觀察",
    "threshold first look": "初次進入展場",
    "sensory encounter": "感官體驗",
    "illuminated touch": "光影互動",
    "system operation": "操作展項",
    "result resolution": "看見操作成果",
    "group context": "一起探索",
    "mechanism task": "機構挑戰",
    "exhibit system bridge": "展項串連",
    "quiet making": "安靜創作",
    "memory callback": "回看這趟旅程",
  };

  var els = {};
  var rafId = null;
  var lastTick = 0;
  var TRACK_LABEL_WIDTH = 72;
  var TIMELINE_PX_PER_SEC = 72;

  // Keep native Workbench APIs on the selected run without modifying the shared
  // endpoint wrapper; dashboard modules already append root via their state.
  var nativeFetch = window.fetch.bind(window);
  window.fetch = function (input, init) {
    if (typeof input === "string" && input.indexOf("/api/") === 0 && input.indexOf("?") < 0 && window.location.search) {
      return nativeFetch(input + window.location.search, init);
    }
    return nativeFetch(input, init);
  };

  function $(id) {
    return document.getElementById(id);
  }

  function cacheEls() {
    [
      "monitor", "stage-image", "stage-video", "preview-audio", "stage-empty",
      "material-map-summary", "asset-search", "asset-family-filter", "asset-placement-suggestions", "material-assets-list",
      "effect-overlay", "effect-label", "subtitle-overlay",
      "stage-meta", "btn-play", "btn-pause", "btn-rewind", "scrubber",
      "time-label", "frame-label", "audio-status", "inspector-empty", "inspector-body",
      "inspector-meta", "in-duration", "in-source-start", "in-source-duration",
      "field-source-start", "field-source-duration", "btn-apply-clip", "btn-replace-clip",
      "btn-move-left", "btn-move-right", "lane-video", "lane-subtitle",
      "lane-dialogue", "lane-music", "lane-sfx", "lane-effect", "playhead", "diagnostics", "dirty-flag",
      "timeline-scroll", "timeline-canvas", "timeline-ruler",
      "btn-download-patch", "btn-save-patch", "btn-sync-contract", "btn-export",
      "btn-save-all", "btn-save-all-footer", "btn-add-cue", "effect-asset-select", "btn-add-fx", "track-inspector",
      "track-insp-title", "t-text", "t-preset", "t-cuetype", "t-start",
      "t-duration", "t-time", "t-strength", "tf-text", "tf-preset", "tf-cuetype",
      "tf-start", "tf-duration", "tf-time", "tf-strength",
      "btn-apply-track", "btn-delete-track", "track-insertions", "drawer-media", "btn-drawer", "fit-only",
      "dico-material", "dico-music", "dico-subtitle", "dico-effect",
      "dot-material", "dot-music", "dot-subtitle", "dot-effect", "domain-inspector",
      "btn-pipestrip", "pipestrip", "btn-gap", "gap-form", "in-gap-desc", "btn-copy-gap-req",
      "run-selector", "aspect-ratio", "btn-undo", "btn-redo",
      "whitebox-panel", "whitebox-title", "whitebox-body", "btn-whitebox-close",
      "interaction-context", "interaction-hint",
      "segment-navigator", "review-category", "review-note", "btn-add-review-note",
      "review-note-list", "duration-policy", "decision-summary",
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
        state.reviewNotes = [];
        state.durationPolicy = "flexible";
        if (els.duration_policy) els.duration_policy.value = state.durationPolicy;
        state.trackSel = null;
        state.dirty = false;
        state.currentTime = 0;
        state.aspectRatio = localStorage.getItem("workbench_aspect_ratio") || "16:9";
        if (els.aspect_ratio) els.aspect_ratio.value = state.aspectRatio;
        applyAspectRatio(state.aspectRatio);
        resetHistory();
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
    renderInteractionPanel();
    renderSegmentNavigator();
    renderReviewNotes();
    renderDecisionSummary();
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

  function compactHumanLabel(value, limit) {
    var text = String(value || "")
      .replace(/^N_/i, "")
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    var max = limit || 32;
    return text.length > max ? text.slice(0, max - 1) + "…" : text;
  }

  function humanFamilyLabel(value) {
    var raw = String(value || "").trim();
    var normalized = raw.toLowerCase()
      .replace(/^n_/i, "")
      .replace(/[_-]+/g, " ")
      .replace(/\s+/g, " ")
      .trim();
    return FAMILY_LABELS[raw.toLowerCase()] ||
      FAMILY_LABELS[normalized] ||
      compactHumanLabel(raw, 28);
  }

  function clipDisplayLabel(clip) {
    clip = clip || {};
    var raw = clip.display_label || clip.segment_title || clip.story_role ||
      clip.visual_family || clip.need_id || clip.caption || clip.scene_id || clip.type;
    return humanFamilyLabel(raw);
  }

  function renderMaterialBrowser() {
    if (!els.material_assets_list) return;
    var families = materialFamilies();
    var current = els.asset_family_filter ? els.asset_family_filter.value : "";
    if (els.asset_family_filter) {
      els.asset_family_filter.innerHTML = '<option value="">所有分類</option>';
      families.forEach(function (fam) {
        var opt = document.createElement("option");
        opt.value = fam;
        opt.textContent = humanFamilyLabel(fam);
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
        titleH2.textContent = selectedClip ? "適合這一段的畫面" : "這支影片的素材";
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
        return ["accepted", "candidate", "family", "related"].indexOf(c.match_status) >= 0;
      });
    }

    if (els.material_map_summary) {
      var strongCount = cards.filter(function (item) {
        return ["accepted", "candidate", "family"].indexOf(item.match_status) >= 0;
      }).length;
      els.material_map_summary.textContent = selectedClip
        ? strongCount + " 個優先建議，另有 " + Math.max(0, cards.length - strongCount) + " 個相近畫面"
        : assets.length + "/" + state.materialAssets.length + " 個素材";
    }
    renderPlacementSuggestions();
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
      var sceneLabel = (a.scene && (a.scene.display_label || a.scene.visual_family || a.scene.caption)) || "";
      title.textContent = compactHumanLabel(
        humanFamilyLabel(a.display_label || sceneLabel || a.visual_family || a.caption) || a.asset_id,
        25
      );
      title.title = a.asset_id;

      var badge = document.createElement("span");
      if (a.match_status === "accepted") {
        badge.className = "fit fit-ok";
        badge.textContent = "符合需求";
      } else if (a.match_status === "candidate") {
        badge.className = "fit fit-mid";
        badge.textContent = "候選";
      } else if (a.match_status === "family") {
        badge.className = "fit fit-family";
        badge.textContent = "同類畫面";
      } else if (a.match_status === "related") {
        badge.className = "fit fit-related";
        badge.textContent = "語意相近";
      } else {
        badge.className = "fit fit-low";
        badge.textContent = "其他";
      }
      title.appendChild(badge);

      var meta = document.createElement("div");
      meta.className = "material-meta";
      var familyLabel = (a.scene && a.scene.visual_family) || a.visual_family || "";
      var durationLabel = a.duration_sec ? a.duration_sec.toFixed(1) + "s" : "照片";
      meta.textContent = durationLabel +
        (familyLabel ? " · " + humanFamilyLabel(familyLabel) : "");
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

  function renderPlacementSuggestions() {
    var host = els.asset_placement_suggestions;
    if (!host) return;
    host.innerHTML = "";
    var asset = state.materialAssets.find(function (item) {
      return item.asset_id === state.selectedAssetId;
    });
    if (!asset || !state.work) {
      host.hidden = true;
      return;
    }
    var suggestions = Materials.recommendedClipsForAsset(asset, state.work.clips);
    if (!suggestions.length) {
      host.hidden = true;
      return;
    }
    host.hidden = false;
    var heading = document.createElement("div");
    heading.className = "placement-heading";
    heading.textContent = "這個素材適合放在";
    host.appendChild(heading);
    var list = document.createElement("div");
    list.className = "placement-list";
    suggestions.slice(0, 6).forEach(function (item) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "placement-chip";
      if (item.is_current_asset) button.className += " current";
      var start = formatInteractionTime(item.clip.timeline_start_sec || 0);
      button.textContent = start + " · " + (clipDisplayLabel(item.clip) || "片段 #" + item.slot_index);
      button.title = item.is_current_asset
        ? "目前已放在這一段"
        : "跳到這一段，準備用目前素材替換";
      button.onclick = function () {
        state.selectedAssetId = asset.asset_id;
        state.selectedSceneIndex = item.scene_index || 0;
        selectClip(item.slot_index);
        setInteractionHint(item.is_current_asset
          ? "這個素材目前就在此段。"
          : "已跳到建議段落；確認畫面後可按「換成左側素材」。");
      };
      list.appendChild(button);
    });
    host.appendChild(list);
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
    [els.lane_video, els.lane_subtitle, els.lane_dialogue, els.lane_music, els.lane_sfx, els.lane_effect].forEach(function (l) {
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
      var label = "#" + c.slot_index + " " + clipDisplayLabel(c);
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

    // Audio evidence is split by editorial role.  Existing candidates usually
    // bind every placement to one composite master, so these blocks expose
    // structure without pretending that Workbench can independently remix it.
    var audioLanes = {
      dialogue: els.lane_dialogue,
      music: els.lane_music,
      sfx: els.lane_sfx,
      mixed: els.lane_dialogue,
    };
    Object.keys(audioLanes).forEach(function (key) {
      if (audioLanes[key]) audioLanes[key].innerHTML = "";
    });
    (state.work.audio || []).forEach(function (a) {
      var laneName = a.lane || "mixed";
      var audio = audioLanes[laneName] || audioLanes.dialogue;
      var bg = document.createElement("div");
      bg.className = "clip-block clip-audio audio-" + laneName;
      bg.style.left = ((a.start_sec || 0) * scale) + "px";
      bg.style.opacity = a.independent_mix_editable ? "0.78" : "0.46";
      bg.style.width = (Math.max(0.5, a.duration_sec) * scale - 2) + "px";
      var icon = laneName === "music" ? "♪" : (laneName === "sfx" ? "✦" : "◉");
      bg.textContent = icon + " " + (a.label || a.role || "聲音");
      var volume = a.applied_volume == null ? "" : " · 音量 " + a.applied_volume;
      bg.title = (a.role || laneName) + volume +
        (a.independent_mix_editable ? "" : " · 目前為混音完成檔，調整會交給 Audio Director");
      bg.onclick = function () { selectAudioTrack(a.id); };
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
      els.lane_sfx.appendChild(m);
    });

    // Existing pipeline effects are evidence, not editable Workbench
    // proposals.  Keep them visible as a read-only background so the editor
    // does not mistake an already-finished section for an empty effect lane.
    var fx = els.lane_effect;
    fx.innerHTML = "";
    (state.work.effects || []).filter(function (e) { return e.marker_only; }).forEach(function (e) {
      var bg = document.createElement("div");
      bg.className = "fx-marker fx-marker-readonly";
      bg.style.left = ((e.start_sec || 0) * scale) + "px";
      bg.style.width = Math.max(10, (e.duration_sec || 0.2) * scale) + "px";
      bg.style.opacity = "0.32";
      bg.style.pointerEvents = "none";
      bg.textContent = e.label || "既有效果";
      bg.title = (e.label || "既有效果") + "（既有製作結果，唯讀）";
      fx.appendChild(bg);
    });

    // Workbench-created effect intent markers remain editable (NPE4).
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

  function historySnapshot() {
    return JSON.stringify({
      work: cloneWorkState(state.work),
      cues: (state.cues || []).map(function (cue) { return Object.assign({}, cue); }),
      effects: (state.effects || []).map(function (effect) { return Object.assign({}, effect); }),
      reviewNotes: (state.reviewNotes || []).map(function (note) { return Object.assign({}, note); }),
      durationPolicy: state.durationPolicy,
    });
  }

  function updateHistoryButtons() {
    if (els.btn_undo) els.btn_undo.disabled = state.historyIndex <= 0;
    if (els.btn_redo) els.btn_redo.disabled = state.historyIndex >= state.history.length - 1;
  }

  function resetHistory() {
    state.history = [historySnapshot()];
    state.historyIndex = 0;
    state.savedHistoryIndex = 0;
    state.dirty = false;
    updateHistoryButtons();
    updateDirty();
  }

  function commitHistory() {
    if (state.historyRestoring || !state.work) return;
    var snapshot = historySnapshot();
    if (state.history[state.historyIndex] === snapshot) return;
    state.history = state.history.slice(0, state.historyIndex + 1);
    state.history.push(snapshot);
    if (state.history.length > 50) {
      state.history.shift();
      state.savedHistoryIndex = Math.max(-1, state.savedHistoryIndex - 1);
    }
    state.historyIndex = state.history.length - 1;
    state.dirty = state.historyIndex !== state.savedHistoryIndex;
    updateHistoryButtons();
    updateDirty();
  }

  function restoreHistory(index) {
    if (index < 0 || index >= state.history.length) return;
    var snapshot = JSON.parse(state.history[index]);
    state.historyRestoring = true;
    state.work = cloneWorkState(snapshot.work);
    state.cues = (snapshot.cues || []).map(function (cue) { return Object.assign({}, cue); });
    state.effects = (snapshot.effects || []).map(function (effect) { return Object.assign({}, effect); });
    state.reviewNotes = (snapshot.reviewNotes || []).map(function (note) { return Object.assign({}, note); });
    state.durationPolicy = snapshot.durationPolicy || "flexible";
    if (els.duration_policy) els.duration_policy.value = state.durationPolicy;
    state.historyIndex = index;
    state.dirty = state.historyIndex !== state.savedHistoryIndex;
    state.trackSel = null;
    state.historyRestoring = false;
    renderAll();
    if (state.selectedSlot != null && state.work.clips.some(function (clip) {
      return clip.slot_index === state.selectedSlot;
    })) {
      selectClip(state.selectedSlot);
    }
    updateHistoryButtons();
    updateDirty();
  }

  function undo() {
    if (state.historyIndex > 0) restoreHistory(state.historyIndex - 1);
  }

  function redo() {
    if (state.historyIndex < state.history.length - 1) restoreHistory(state.historyIndex + 1);
  }

  function applyAspectRatio(value) {
    var supported = ["16:9", "9:16", "1:1"];
    state.aspectRatio = supported.indexOf(value) >= 0 ? value : "16:9";
    if (els.monitor) els.monitor.setAttribute("data-aspect", state.aspectRatio);
    if (els.aspect_ratio) els.aspect_ratio.value = state.aspectRatio;
    localStorage.setItem("workbench_aspect_ratio", state.aspectRatio);
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
      commitHistory();
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
      if (els.stage_meta) els.stage_meta.textContent = "";
    } else if (clip.type === "image") {
      vid.hidden = true; vid.pause && vid.pause();
      empty.hidden = true;
      img.hidden = false;
      if (img.getAttribute("data-slot") !== String(clip.slot_index)) {
        img.src = clip.src_url || "";
        img.setAttribute("data-slot", String(clip.slot_index));
      }
      if (els.stage_meta) els.stage_meta.textContent = "圖片 #" + clip.slot_index + " / 靜態 " + clip.duration_sec.toFixed(2) + "s";
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
      if (els.stage_meta) {
        els.stage_meta.textContent =
          "VID #" + clip.slot_index + " · src " + wantTime.toFixed(2) + "s (start " +
          clip.source_start_sec.toFixed(2) + ")";
      }
    }

    var sub = Core.getActiveSubtitle(state.work.subtitles, state.currentTime);
    els.subtitle_overlay.textContent = sub ? sub.text : "";

    // Playhead position.
    var metrics = timelineMetrics();
    els.playhead.style.left = (TRACK_LABEL_WIDTH + state.currentTime * metrics.scale) + "px";
    ensurePlayheadVisible(metrics);

    els.time_label.textContent =
      state.currentTime.toFixed(2) + " / " + (state.work.duration_sec || 0).toFixed(2) + "s";
    if (els.frame_label) els.frame_label.textContent = "f" + Core.secondsToFrame(state.currentTime, state.fps);
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

  function renderSegmentNavigator() {
    if (!els.segment_navigator || !state.work) return;
    els.segment_navigator.innerHTML = "";
    (state.work.clips || []).forEach(function (clip) {
      var button = document.createElement("button");
      button.type = "button";
      button.className = "segment-chip" + (clip.slot_index === state.selectedSlot ? " selected" : "");
      var title = document.createElement("strong");
      title.textContent = clipDisplayLabel(clip) || "片段 " + (clip.slot_index + 1);
      var meta = document.createElement("span");
      meta.textContent = formatInteractionTime(clip.timeline_start_sec || 0) +
        " · " + Number(clip.duration_sec || 0).toFixed(1) + " 秒";
      button.appendChild(title);
      button.appendChild(meta);
      button.onclick = function () { selectClip(clip.slot_index); };
      els.segment_navigator.appendChild(button);
    });
  }

  function reviewCategoryLabel(category) {
    return {
      picture: "畫面", timing: "節奏", subtitle: "字幕", audio: "聲音",
      effect: "效果", story: "故事", overall: "整體",
    }[category] || "整體";
  }

  function renderReviewNotes() {
    if (!els.review_note_list) return;
    els.review_note_list.innerHTML = "";
    (state.reviewNotes || []).forEach(function (note) {
      var item = document.createElement("div");
      item.className = "review-note-item";
      var label = document.createElement("b");
      label.textContent = reviewCategoryLabel(note.category);
      var text = document.createElement("span");
      text.textContent = note.text;
      var remove = document.createElement("button");
      remove.type = "button";
      remove.textContent = "×";
      remove.title = "移除這條回饋";
      remove.onclick = function () {
        state.reviewNotes = state.reviewNotes.filter(function (candidate) {
          return candidate.note_id !== note.note_id;
        });
        commitHistory();
        renderReviewNotes();
        renderDecisionSummary();
      };
      item.appendChild(label);
      item.appendChild(text);
      item.appendChild(remove);
      els.review_note_list.appendChild(item);
    });
  }

  function addReviewNote() {
    var clip = selectedClip();
    var text = ((els.review_note && els.review_note.value) || "").trim();
    if (!clip) {
      setInteractionHint("請先選一個片段，再加入這段的回饋。");
      return;
    }
    if (!text) {
      setInteractionHint("先寫下希望 Agent 怎麼調整。");
      if (els.review_note) els.review_note.focus();
      return;
    }
    state.reviewNotes.push({
      note_id: "note-" + (++state.seq),
      scope: "segment",
      category: (els.review_category && els.review_category.value) || "overall",
      segment_id: clip.segment || clip.scene_id || null,
      slot_index: clip.slot_index,
      timeline_window: {
        start_sec: Core.round6(clip.timeline_start_sec || 0),
        end_sec: Core.round6((clip.timeline_start_sec || 0) + (clip.duration_sec || 0)),
      },
      text: text,
    });
    if (els.review_note) els.review_note.value = "";
    commitHistory();
    renderReviewNotes();
    renderDecisionSummary();
    setInteractionHint("已加入本段回饋；送出後會依照這些內容處理下一版。");
  }

  function changeCounts() {
    if (!state.raw || !state.work) return { total: 0, timeline: 0, subtitle: 0 };
    var timeline = Core.buildTimelinePatch(
      { clips: state.raw.clips },
      { clips: state.work.clips },
      { base_timeline_ref: state.raw.source_artifact || "timeline.json" }
    ).patches.length;
    var subtitle = Core.buildSubtitlePatch(
      state.rawSubs,
      state.work.subtitles,
      {}
    ).patches.length;
    return {
      timeline: timeline,
      subtitle: subtitle,
      audio: (state.cues || []).length,
      effect: (state.effects || []).length,
      notes: (state.reviewNotes || []).length,
      total: timeline + subtitle + (state.cues || []).length +
        (state.effects || []).length + (state.reviewNotes || []).length,
    };
  }

  function renderDecisionSummary() {
    if (!els.decision_summary || !state.work || !state.raw) return;
    var counts = changeCounts();
    var before = Core.totalDuration(state.raw.clips || []);
    var after = Core.totalDuration(state.work.clips || []);
    var delta = after - before;
    if (!counts.total) {
      els.decision_summary.textContent = "尚未加入回饋或調整";
      els.decision_summary.className = "decision-summary";
      return;
    }
    var parts = [];
    if (counts.notes) parts.push(counts.notes + " 條回饋");
    if (counts.timeline) parts.push(counts.timeline + " 個畫面／時間調整");
    if (counts.subtitle) parts.push(counts.subtitle + " 個字幕調整");
    if (counts.audio) parts.push(counts.audio + " 個聲音提示");
    if (counts.effect) parts.push(counts.effect + " 個效果意圖");
    var duration = Math.abs(delta) < 0.001
      ? "片長不變"
      : "片長 " + (delta > 0 ? "+" : "") + delta.toFixed(1) + " 秒";
    els.decision_summary.textContent = parts.join("、") + "；" + duration +
      "。送出後會依照這些內容修改並檢查下一版。";
    els.decision_summary.className = "decision-summary has-changes";
  }

  function updateDirty() {
    els.dirty_flag.textContent = state.dirty ? "有尚未送出的調整" : "目前沒有調整";
    els.dirty_flag.className = state.dirty ? "dirty" : "muted";
    renderDecisionSummary();
  }

  function selectedClip() {
    if (!state.work || state.selectedSlot == null) return null;
    return state.work.clips.find(function (clip) {
      return clip.slot_index === state.selectedSlot;
    }) || null;
  }

  function setInteractionHint(message) {
    if (els.interaction_hint) els.interaction_hint.textContent = message;
  }

  function renderInteractionPanel() {
    var clip = selectedClip();
    var buttons = document.querySelectorAll("[data-quick-action]");
    buttons.forEach(function (button) { button.disabled = !clip; });
    if (!els.interaction_context || !els.interaction_hint) return;
    if (!clip) {
      els.interaction_context.textContent = "先從「逐段檢視」選一段";
      els.interaction_hint.textContent = "選取後可立即換畫面、調整長短，或處理字幕與音樂。";
      return;
    }
    var start = formatInteractionTime(clip.timeline_start_sec || 0);
    var end = formatInteractionTime((clip.timeline_start_sec || 0) + (clip.duration_sec || 0));
    els.interaction_context.textContent = "正在調整 " + start + "–" + end + " 的畫面";
    els.interaction_hint.textContent = clipDisplayLabel(clip) || "選一個動作，畫面會立即更新。";
  }

  function formatInteractionTime(sec) {
    var safe = Math.max(0, Number(sec) || 0);
    var minutes = Math.floor(safe / 60);
    var seconds = (safe - minutes * 60).toFixed(1).padStart(4, "0");
    return minutes + ":" + seconds;
  }

  function openDomain(domain) {
    var button = els["dico_" + domain];
    if (!button) return;
    state.currentDomain = domain;
    ["material", "music", "subtitle", "effect"].forEach(function (name) {
      if (els["dico_" + name]) els["dico_" + name].classList.toggle("on", name === domain);
    });
    renderInspector();
  }

  function adjustSelectedDuration(delta) {
    var clip = selectedClip();
    if (!clip) return;
    var next = Math.max(0.5, Core.round6(clip.duration_sec + delta));
    applyOp("set_duration", { duration_sec: next });
    selectClip(clip.slot_index);
    setInteractionHint(delta > 0 ? "已延長 0.5 秒，可直接播放確認。" : "已縮短 0.5 秒，可直接播放確認。");
  }

  function focusReplacementBrowser() {
    var clip = selectedClip();
    if (!clip) return;
    if (els.drawer_media) els.drawer_media.classList.remove("collapsed");
    if (els.fit_only) els.fit_only.checked = true;
    renderMaterialBrowser();
    if (els.asset_search) {
      els.asset_search.focus();
      els.asset_search.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
    setInteractionHint("左側已列出適合這一段的畫面；雙擊素材即可替換。");
  }

  function focusSubtitleAtSelection() {
    var clip = selectedClip();
    if (!clip) return;
    var start = clip.timeline_start_sec || 0;
    var end = start + (clip.duration_sec || 0);
    var subtitle = (state.work.subtitles || []).find(function (item) {
      return item.start_sec < end && item.start_sec + item.duration_sec > start;
    });
    if (subtitle) {
      selectSubtitle(subtitle.id);
      setInteractionHint("已找到這一段的字幕，可直接修改內容或停留時間。");
    } else {
      if (els.review_category) els.review_category.value = "subtitle";
      if (els.review_note) {
        els.review_note.placeholder = "例：這裡補一張說明字卡，文字為……";
        els.review_note.focus();
      }
      setInteractionHint("這一段沒有核准字幕；請把希望的文字或用途寫成回饋交給字幕流程。");
    }
  }

  function runQuickAction(action) {
    if (!selectedClip()) return;
    if (action === "replace") focusReplacementBrowser();
    else if (action === "longer") adjustSelectedDuration(0.5);
    else if (action === "shorter") adjustSelectedDuration(-0.5);
    else if (action === "subtitle") focusSubtitleAtSelection();
    else if (action === "music") {
      openDomain("music");
      setInteractionHint("已打開這支影片的音樂狀態；音量修訂會交給音訊流程處理。 ");
    } else if (action === "effect") {
      if (els.review_category) els.review_category.value = "effect";
      if (els.review_note) {
        els.review_note.placeholder = "例：這裡用淡入轉場；不要再出現復古膠片效果。";
        els.review_note.focus();
      }
      setInteractionHint("先選適合的效果，或把想要的感覺寫成回饋；不會自動亂套預設。");
    }
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
    els.track_insp_title.textContent = "調整這句字幕";
    els.btn_apply_track.style.display = "";
    els.t_text.value = s.text;
    els.t_start.value = s.start_sec;
    els.t_duration.value = s.duration_sec;
    els.btn_delete_track.style.display = "none";
    showTrackFields(["text", "start", "duration"]);
    seekTo(s.start_sec + 0.001);
    renderTimelineLanes();
    renderInspector();
    renderTrackInsertions("subtitle");
  }

  function selectCue(id) {
    state.trackSel = { type: "cue", id: id };
    var c = state.cues.find(function (x) { return x.cue_id === id; });
    if (!c) return;
    els.track_insp_title.textContent = "調整這個音效";
    els.btn_apply_track.style.display = "";
    els.t_cuetype.value = c.cue_type;
    els.t_time.value = c.time_sec;
    els.t_strength.value = c.strength;
    els.btn_delete_track.style.display = "";
    showTrackFields(["cuetype", "time", "strength"]);
    seekTo(c.time_sec);
    renderTimelineLanes();
    renderInspector();
    renderTrackInsertions("cue");
  }

  function selectEffect(id) {
    state.trackSel = { type: "effect", id: id };
    var e = state.effects.find(function (x) { return x.effect_id === id; });
    if (!e) return;
    if (e.target_slot_index != null) state.selectedSlot = e.target_slot_index;
    els.track_insp_title.textContent = "調整這個畫面效果";
    els.btn_apply_track.style.display = "";
    els.t_preset.value = e.preset;
    els.t_start.value = e.start_sec;
    els.t_duration.value = e.duration_sec;
    els.t_strength.value = e.intensity;
    els.btn_delete_track.style.display = "";
    showTrackFields(["preset", "start", "duration", "strength"]);
    seekTo(e.start_sec + 0.001);
    renderTimelineLanes();
    renderInspector();
    renderTrackInsertions("effect");
  }

  function audioLaneLabel(lane) {
    if (lane === "music") return "配樂";
    if (lane === "sfx") return "音效";
    return "原聲／人聲";
  }

  function selectAudioTrack(id) {
    state.trackSel = { type: "audio", id: id };
    var track = (state.work.audio || []).find(function (x) { return x.id === id; });
    if (!track) return;
    els.track_insp_title.textContent = audioLaneLabel(track.lane);
    els.btn_delete_track.style.display = "none";
    els.btn_apply_track.style.display = "none";
    showTrackFields([]);
    seekTo(track.start_sec || 0);
    renderTimelineLanes();
    renderInspector();
    renderTrackInsertions("audio");
  }

  function addInsertionOption(host, title, meta, onClick) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "insert-option";
    var strong = document.createElement("strong");
    strong.textContent = title;
    var span = document.createElement("span");
    span.textContent = meta;
    button.appendChild(strong);
    button.appendChild(span);
    button.onclick = onClick;
    host.appendChild(button);
  }

  function renderTrackInsertions(kind) {
    var host = els.track_insertions;
    if (!host) return;
    host.hidden = false;
    host.innerHTML = "";
    var title = document.createElement("h3");
    var hint = document.createElement("p");
    var options = document.createElement("div");
    options.className = "insert-options";
    host.appendChild(title);
    host.appendChild(hint);
    host.appendChild(options);

    if (kind === "effect") {
      title.textContent = "這段可以套用的效果";
      hint.textContent = "先用少量預設確認方向；套用後可立即播放，細節仍可在上方調整。";
      var effects = state.effectAssets || [];
      if (!effects.length) {
        var empty = document.createElement("div");
        empty.className = "insert-empty";
        empty.textContent = "目前沒有可直接套用的效果素材；可使用預設推近效果。";
        options.appendChild(empty);
      } else {
        effects.slice(0, 8).forEach(function (asset) {
          addInsertionOption(options, asset.label || asset.asset_id || "效果素材", asset.asset_type || "預設效果", function () {
            if (els.effect_asset_select) els.effect_asset_select.value = asset.asset_id || "";
            addFx();
            setInteractionHint("已套用「" + (asset.label || asset.asset_id || "效果") + "」，可播放確認。");
          });
        });
      }
    } else if (kind === "cue") {
      title.textContent = "可以插入的音效提示";
      hint.textContent = "音效提示只留下 draft 標記，真正混音仍由音訊流程處理。";
      (CUE_TYPES || []).slice(0, 6).forEach(function (cueType) {
        addInsertionOption(options, CUE_LABELS[cueType] || cueType, "插入目前時間", function () {
          addCue(cueType);
          setInteractionHint("已插入「" + (CUE_LABELS[cueType] || cueType) + "」提示。");
        });
      });
    } else if (kind === "audio") {
      var selectedAudio = state.trackSel && state.trackSel.type === "audio"
        ? (state.work.audio || []).find(function (track) { return track.id === state.trackSel.id; })
        : null;
      title.textContent = selectedAudio
        ? "這段的" + audioLaneLabel(selectedAudio.lane)
        : "這支影片的聲音";
      hint.textContent = selectedAudio && selectedAudio.independent_mix_editable
        ? "這是可獨立調整的聲音來源。"
        : "目前綁定的是混音完成檔；這裡負責定位與留下需求，音量或 ducking 由 Audio Director 處理。";
      var tracks = state.work.audio || [];
      if (!tracks.length) {
        var noAudio = document.createElement("div");
        noAudio.className = "insert-empty";
        noAudio.textContent = "目前沒有可安全插入的音樂素材。先完成音樂來源與授權，再回到這裡檢視。";
        options.appendChild(noAudio);
      } else {
        tracks.slice(0, 6).forEach(function (track) {
          var volume = track.applied_volume == null ? "" : " · 音量 " + track.applied_volume;
          addInsertionOption(options, audioLaneLabel(track.lane) + "｜" + (track.label || track.role || "聲音"),
            Number(track.duration_sec || 0).toFixed(1) + " 秒" + volume, function () {
            seekTo(track.start_sec || 0);
            setInteractionHint("已定位到「" + (track.label || track.role || "聲音") + "」。音量與 ducking 交由音訊流程處理。");
          });
        });
        addInsertionOption(options, "在此加音效提示", "不改變音樂來源", function () {
          addCue();
          setInteractionHint("已加入音效提示，可在這段時間軸上調整。");
        });
      }
    } else {
      title.textContent = "這段的字幕";
      hint.textContent = "字幕先以核准文字為準；已有字幕可直接點選修改。";
      var subtitle = state.trackSel && state.trackSel.type === "subtitle" ? state.work.subtitles.find(function (x) { return x.id === state.trackSel.id; }) : null;
      if (subtitle) {
        addInsertionOption(options, "編輯這句字幕", subtitle.text || "（空白）", function () {
          els.t_text.focus();
          setInteractionHint("已聚焦字幕內容，可以直接修改後確認。");
        });
      } else {
        var noSubtitle = document.createElement("div");
        noSubtitle.className = "insert-empty";
        noSubtitle.textContent = "這裡沒有現成字幕；請先提供或核准字幕稿，不在工作台猜寫內容。";
        options.appendChild(noSubtitle);
      }
    }
  }

  function addCue(cueType) {
    var active = Core.getActiveClip(state.work.clips, state.currentTime);
    var id = "cue-" + (++state.seq);
    state.cues.push({
      cue_id: id, time_sec: Core.round6(state.currentTime), cue_type: cueType || "impact",
      strength: 3, anchor_clip_slot_index: active ? active.slot_index : null,
    });
    state.dirty = true;
    commitHistory();
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
    state.dirty = true;
    commitHistory();
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
    selectEffect(id);
  }

  function copyGapRequest() {
    var rootPath = (state.artifacts && state.artifacts.artifact_root) || new URLSearchParams(window.location.search).get("root") || "";
    var clipId = "N/A";
    if (state.selectedSlot != null) {
      var clip = state.work.clips.find(function (c) { return c.slot_index === state.selectedSlot; });
      if (clip) clipId = clip.id || clip.slot_index;
    }
    var desc = els.in_gap_desc.value.trim();
    if (!desc) {
      alert("請輸入需要什麼畫面的描述！");
      return;
    }

    var text = "--- HERMES MATERIAL GAP REQUEST ---\n" +
               "Project Root: " + rootPath + "\n" +
               "Clip ID: " + clipId + "\n" +
               "Description: " + desc + "\n" +
               "----------------------------------";

    navigator.clipboard.writeText(text)
      .then(function () {
        els.diagnostics.textContent = "已複製補素材請求到剪貼簿！";
        alert("已複製需求，請貼到任務對話中繼續處理。");
      })
      .catch(function (err) {
        console.error("Failed to copy text: ", err);
        els.diagnostics.textContent = "複製失敗，請手動複製：" + text;
      });
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
    state.dirty = true;
    commitHistory();
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
    state.dirty = true;
    commitHistory();
    renderTimelineLanes();
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
  }

  function saveAll() {
    var counts = changeCounts();
    var hasDurationDecision = state.durationPolicy !== "flexible";
    if (!counts.total && !hasDurationDecision) {
      els.diagnostics.textContent = "目前沒有需要送出的回饋或調整。";
      return;
    }
    var decisionContext = {
      decision_mode: "explicit_submit",
      review_notes: (state.reviewNotes || []).map(function (note) { return Object.assign({}, note); }),
      duration_policy: state.durationPolicy,
      target_duration_sec: Core.round6(state.work.duration_sec || 0),
      duration_tolerance_sec: 2.0,
      selected_slot_index: state.selectedSlot,
    };
    var payload = Core.buildSavePayload({
      timelineBefore: state.raw.clips, timelineAfter: state.work.clips,
      subsBefore: state.rawSubs, subsAfter: state.work.subtitles,
      cues: state.cues, effects: state.effects,
      base_timeline_ref: (state.raw && state.raw.source_artifact) || "timeline.json",
      decision_context: decisionContext,
    });
    els.diagnostics.textContent = "正在整理並送出這次的回饋與調整...";
    Api.saveAll(payload)
      .then(function (res) {
        if (res.ok && res.j.ok) {
          var numPatches = (res.j.written || []).filter(function (x) { return x.indexOf("_patch.json") >= 0; }).length;
          els.diagnostics.textContent = "已簽出 " + (state.reviewNotes || []).length +
            " 條回饋與 " + numPatches + " 類調整；系統會依同一批決定接續處理。";
          state.savedHistoryIndex = state.historyIndex;
          state.dirty = false;
          updateHistoryButtons();
          updateDirty();
          fetchArtifactsAndUpdateDots();
        } else {
          els.diagnostics.textContent = "這些調整暫時無法保存：" + JSON.stringify(res.j.errors || res.j);
        }
      })
      .catch(function (err) { els.diagnostics.textContent = "保存調整失敗：" + err; });
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
    updatePipelineStrip();
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
        return fetchControlStatus();
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
      title = "畫面狀態";
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
      title = "聲音狀態";
      patchFile = "audio_cue_patch.json";
      active = state.raw && state.raw.audio && state.raw.audio.length > 0;
      changed = state.cues && state.cues.length > 0;
      var audioTracks = (state.work && state.work.audio) || [];
      rows = [
        ["原聲／人聲", audioTracks.filter(function (track) { return track.lane === "dialogue"; }).length + " 段"],
        ["配樂", audioTracks.filter(function (track) { return track.lane === "music"; }).length + " 段"],
        ["音效", audioTracks.filter(function (track) { return track.lane === "sfx"; }).length + " 段"],
        ["音效提示", (state.cues || []).length + " 個標記"],
        ["調整方式", audioTracks.some(function (track) { return track.independent_mix_editable; })
          ? "可獨立調整"
          : "目前是混音完成檔，交 Audio Director"]
      ];
      patchObj = {
        artifact_role: "audio_cue_patch",
        version: 1,
        cues: state.cues
      };
    } else if (d === "subtitle") {
      title = "字幕狀態";
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
      title = "效果狀態";
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

    var html =
      '<div style="display:flex;align-items:center;margin-bottom:12px;"><h2 style="flex:1;margin:0;font-size:15px;">' + title + '</h2>' +
      '<button id="btn-close-domain-inspector" style="padding:2px 8px;cursor:pointer;background:none;border:1px solid var(--border);border-radius:4px;color:inherit;" type="button">✕</button></div>' +
      '<span class="pill" style="background:' + pillBg + ';color:' + pillFg + ';">' + pillText + '</span>' +
      rows.map(function(r){
        return '<div class="row"><span>' + r[0] + '</span><span>' + r[1] + '</span></div>';
      }).join('') +
      '<p style="font-size:12px;color:var(--muted);margin:10px 0 6px;">這裡的調整會先存成草稿</p>' +
      '<details style="margin-top:8px;"><summary style="font-size:12px;color:var(--muted);cursor:pointer;user-select:none;">檢視原始 JSON</summary>' +
      '<div class="jsonbox" style="margin-top:4px;max-height:220px;overflow-y:auto;background:var(--panel-2);padding:8px;border-radius:6px;font-family:monospace;font-size:11px;white-space:pre;">' + JSON.stringify(patchObj, null, 2) + '</div></details>' +
      '<button id="btn-expand-whitebox" style="width:100%;margin-top:14px;padding:8px;border-radius:6px;background:none;border:1px solid var(--accent);color:var(--accent);font-weight:600;cursor:pointer;" type="button">展開完整數據 (白盒)</button>';

    els.domain_inspector.innerHTML = html;

    document.getElementById("btn-close-domain-inspector").onclick = resetDomainInspector;
    document.getElementById("btn-expand-whitebox").onclick = function () {
      openWhitebox(whiteboxViewForDomain(d));
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

  function updatePipelineStrip() {
    if (!els.pipestrip) return;

    var artifacts = state.artifacts || {};
    var control = state.control || {};
    var draftArtifacts = (artifacts.workbench && artifacts.workbench.draft_artifacts) || {};
    var draftSummary = (artifacts.workbench && artifacts.workbench.draft_summary) || {};

    var intentStatus = "st-done";

    var specStatus = "st-done";
    if (draftSummary.contract_edits > 0 || (draftArtifacts.workbench_contract_patch && draftArtifacts.workbench_contract_patch.exists)) {
      specStatus = "st-now";
    }

    var materialStatus = "st-done";

    var buildStatus = "st-todo";
    if (state.dirty || draftSummary.timeline_edits > 0) {
      buildStatus = "st-now";
    } else if (control.final_video && control.final_video.exists) {
      buildStatus = "st-done";
    } else if (draftSummary.has_handoff) {
      buildStatus = "st-done";
    }

    var verifyStatus = "st-todo";
    var hasVerify = (artifacts.verify_evidence_bundle && artifacts.verify_evidence_bundle.exists) ||
                    (artifacts.delivery_gate && artifacts.delivery_gate.exists);
    if (hasVerify) {
      verifyStatus = "st-done";
    } else if (control.recommended_next_action === "verify" || buildStatus === "st-done") {
      verifyStatus = "st-now";
    }

    var deliveryStatus = "st-todo";
    var isDelivered = (artifacts.delivery_gate && artifacts.delivery_gate.exists);
    if (isDelivered) {
      deliveryStatus = "st-done";
    } else if (control.recommended_next_action === "deliver" || control.recommended_next_action === "publish") {
      deliveryStatus = "st-now";
    }

    var stages = [
      { id: "pstep-intent", status: intentStatus },
      { id: "pstep-spec", status: specStatus },
      { id: "pstep-material", status: materialStatus },
      { id: "pstep-build", status: buildStatus },
      { id: "pstep-verify", status: verifyStatus },
      { id: "pstep-delivery", status: deliveryStatus }
    ];

    stages.forEach(function (stage) {
      var el = document.getElementById(stage.id);
      if (el) {
        el.className = "pstep " + stage.status;
      }
    });
  }

  function fetchControlStatus() {
    var rootParam = window.location.search || "";
    return Api._fetchJson("/api/control/status" + rootParam)
      .then(function (res) {
        state.control = res;
        updatePipelineStrip();
      })
      .catch(function (err) {
        console.error("Failed to fetch control status:", err);
      });
  }

  function currentRoot() {
    return new URLSearchParams(window.location.search).get("root") || "";
  }

  function whiteboxViewForPipelineStep(stepId) {
    if (stepId === "pstep-material") return "material-map";
    if (stepId === "pstep-verify" || stepId === "pstep-delivery") return "verify";
    if (stepId === "pstep-build") return "artifacts";
    return "route";
  }

  function whiteboxViewForDomain(domain) {
    if (domain === "material") return "material-map";
    if (domain === "music" || domain === "subtitle" || domain === "effect") return "verify";
    return "route";
  }

  function setWhiteboxTab(view) {
    var buttons = document.querySelectorAll("[data-whitebox-view]");
    buttons.forEach(function (btn) {
      btn.classList.toggle("active", btn.getAttribute("data-whitebox-view") === view);
    });
  }

  function openWhitebox(view) {
    view = view || "route";
    state.whiteboxView = view;
    if (!els.whitebox_panel || !els.whitebox_body) return;
    els.whitebox_panel.hidden = false;
    els.whitebox_panel.setAttribute("aria-hidden", "false");
    if (els.whitebox_title && window.WorkbenchWhiteBoxModules) {
      els.whitebox_title.textContent = window.WorkbenchWhiteBoxModules.title(view);
    }
    els.whitebox_body.innerHTML = '<div class="muted">讀取白盒資料...</div>';
    setWhiteboxTab(view);
    if (!window.WorkbenchWhiteBoxModules) {
      els.whitebox_body.innerHTML = '<div class="muted">白盒模組尚未載入。</div>';
      return;
    }
    window.WorkbenchWhiteBoxModules.render(view, {
      root: currentRoot(),
      activeStage: state.currentDomain || "Material Map",
    }).then(function (html) {
      if (state.whiteboxView === view) {
        els.whitebox_body.innerHTML = html;
      }
    }).catch(function (err) {
      els.whitebox_body.innerHTML = '<pre class="jsonbox">白盒資料載入失敗: ' + String(err) + '</pre>';
    });
  }

  function closeWhitebox() {
    state.whiteboxView = null;
    if (!els.whitebox_panel) return;
    els.whitebox_panel.hidden = true;
    els.whitebox_panel.setAttribute("aria-hidden", "true");
    setWhiteboxTab("");
  }

  function loadRunSelector() {
    if (!els.run_selector) return;
    var selectedRoot = currentRoot();
    Api._fetchJson("/api/projects")
      .then(function (res) {
        var projects = Array.isArray(res) ? res : ((res && res.projects) || []);
        state.projects = projects;
        els.run_selector.innerHTML = "";
        var fallback = document.createElement("option");
        fallback.value = "";
        fallback.textContent = selectedRoot ? "目前專案" : "伺服器預設專案";
        els.run_selector.appendChild(fallback);
        projects.forEach(function (project) {
          var opt = document.createElement("option");
          opt.value = project.path || project.root || "";
          opt.textContent = project.name || project.label || opt.value;
          if (selectedRoot && opt.value === selectedRoot) opt.selected = true;
          els.run_selector.appendChild(opt);
        });
      })
      .catch(function () {
        els.run_selector.innerHTML = '<option value="">專案清單讀取失敗</option>';
      });
  }

  // -- inspector / edits ------------------------------------------------ //
  function selectClip(slot) {
    state.selectedSlot = slot;
    state.trackSel = null;
    if (state.currentDomain) resetDomainInspector();
    var clip = state.work.clips.find(function (c) { return c.slot_index === slot; });
    if (!clip) return;
    els.inspector_empty.hidden = true;
    els.inspector_body.hidden = false;

    var meta = els.inspector_meta;
    meta.innerHTML = "";
    [["片段", clip.id], ["類型", clip.type], ["單元", clip.segment],
     ["場景", clip.scene_id], ["用途", clip.need_id],
     ["畫面分類", clip.visual_family], ["狀態", clip.status],
     ["開始時間", clip.timeline_start_sec.toFixed(2) + "s"]].forEach(function (kv) {
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
    renderSegmentNavigator();
    renderMaterialBrowser();
    renderInspector();
    renderInteractionPanel();
  }

  function applyOp(op, after, skipHistory) {
    state.work = Core.applyLocalPatch(state.work, { op: op, slot_index: state.selectedSlot, after: after });
    state.dirty = true;
    if (!skipHistory) commitHistory();
    renderTimelineLanes();
    renderSegmentNavigator();
    renderMonitor();
    updateDirty();
    updateDomainDots();
    if (state.currentDomain) renderDomainInspector();
  }

  function applyInspector() {
    if (state.selectedSlot == null) return;
    var clip = state.work.clips.find(function (c) { return c.slot_index === state.selectedSlot; });
    if (!clip) return;
    applyOp("set_duration", { duration_sec: parseFloat(els.in_duration.value) }, true);
    if (clip.type === "video") {
      applyOp("set_source_window", {
        source_start_sec: parseFloat(els.in_source_start.value),
        source_duration_sec: parseFloat(els.in_source_duration.value),
      }, true);
    }
    commitHistory();
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
        matchStatus = Materials.matchSceneToClip
          ? Materials.matchSceneToClip(scene, asset, clip)
          : (Materials.matchStatusForNeed ? Materials.matchStatusForNeed(scene, clip.need_id) : "other");
      }
      cand = Object.assign({}, asset, {
        scene_index: sIdx,
        scene: scene,
        match_status: matchStatus,
      });
    }

    var assetType = String(cand.asset_type || "").toLowerCase();
    var isImage = assetType === "photo" || assetType === "image";
    var replacementPlan = null;
    if (!isImage) {
      var sceneObj = cand.scene || {};
      var start = parseFloat(sceneObj.start_sec) || 0;
      var end = parseFloat(sceneObj.end_sec) || 0;
      var sourceDur = Math.max(0.1, end - start);
      var clipDur = parseFloat(clip.duration_sec) || 0;
      replacementPlan = Core.planReplacementDuration(clipDur, sourceDur, state.durationPolicy);
      if (!replacementPlan.ok) {
        var msg = "這段素材少了 " + replacementPlan.shortage_sec.toFixed(2) +
          " 秒。若要使用，請將片長處理改為「內容優先」。";
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
      duration_sec: replacementPlan && replacementPlan.shortened
        ? replacementPlan.duration_sec
        : undefined,
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
    commitHistory();
    els.diagnostics.textContent = replacementPlan && replacementPlan.shortened
      ? "已換成所選畫面，這一段依內容縮短 " + replacementPlan.shortage_sec.toFixed(2) + " 秒。"
      : "已用所選畫面替換這一段。";
    renderTimelineLanes();
    renderSegmentNavigator();
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
    if (els.btn_save_all_footer) els.btn_save_all_footer.onclick = saveAll;
    els.btn_add_cue.onclick = addCue;
    els.btn_add_fx.onclick = addFx;
    els.btn_apply_track.onclick = applyTrack;
    els.btn_delete_track.onclick = deleteTrack;
    if (els.btn_undo) els.btn_undo.onclick = undo;
    if (els.btn_redo) els.btn_redo.onclick = redo;
    if (els.aspect_ratio) {
      els.aspect_ratio.onchange = function () {
        applyAspectRatio(els.aspect_ratio.value);
        setInteractionHint("已切換預覽構圖；這不會改變正式輸出規格。");
      };
    }

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
    if (els.btn_pipestrip && els.pipestrip) {
      els.btn_pipestrip.onclick = function () {
        var visible = els.pipestrip.classList.toggle("show");
        localStorage.setItem("pipestrip_visible", visible ? "true" : "false");
        window.dispatchEvent(new Event("resize"));
      };
      if (localStorage.getItem("pipestrip_visible") === "true") {
        els.pipestrip.classList.add("show");
      }
    }
    if (els.btn_gap && els.gap_form) {
      els.btn_gap.onclick = function () {
        var hidden = els.gap_form.style.display === "none";
        els.gap_form.style.display = hidden ? "block" : "none";
      };
    }
    if (els.btn_copy_gap_req) {
      els.btn_copy_gap_req.onclick = copyGapRequest;
    }
    document.querySelectorAll("[data-quick-action]").forEach(function (button) {
      button.onclick = function () { runQuickAction(button.getAttribute("data-quick-action")); };
    });
    if (els.btn_add_review_note) els.btn_add_review_note.onclick = addReviewNote;
    if (els.review_note) {
      els.review_note.onkeydown = function (ev) {
        if ((ev.ctrlKey || ev.metaKey) && ev.key === "Enter") {
          ev.preventDefault();
          addReviewNote();
        }
      };
    }
    if (els.duration_policy) {
      els.duration_policy.onchange = function () {
        state.durationPolicy = els.duration_policy.value || "flexible";
        commitHistory();
        renderDecisionSummary();
      };
    }
    if (els.run_selector) {
      els.run_selector.onchange = function () {
        var root = els.run_selector.value;
        if (!root) return;
        var next = new URL(window.location.href);
        next.searchParams.set("root", root);
        window.location.href = next.toString();
      };
    }
    if (els.btn_whitebox_close) {
      els.btn_whitebox_close.onclick = closeWhitebox;
    }
    document.querySelectorAll("[data-whitebox-view]").forEach(function (btn) {
      btn.onclick = function () {
        openWhitebox(btn.getAttribute("data-whitebox-view"));
      };
    });
    ["pstep-intent", "pstep-spec", "pstep-material", "pstep-build", "pstep-verify", "pstep-delivery"].forEach(function (id) {
      var step = document.getElementById(id);
      if (step) {
        step.setAttribute("role", "button");
        step.tabIndex = 0;
        step.onclick = function () { openWhitebox(whiteboxViewForPipelineStep(id)); };
        step.onkeydown = function (ev) {
          if (ev.key === "Enter" || ev.key === " ") {
            ev.preventDefault();
            openWhitebox(whiteboxViewForPipelineStep(id));
          }
        };
      }
    });
    window.addEventListener("workbench-whitebox-ready", function () {
      if (state.whiteboxView) openWhitebox(state.whiteboxView);
    });
    document.addEventListener("keydown", function (ev) {
      if (ev.key === "Escape" && state.whiteboxView) closeWhitebox();
      var target = ev.target && ev.target.tagName ? ev.target.tagName.toLowerCase() : "";
      var editingText = target === "input" || target === "textarea" || target === "select";
      if (!editingText && (ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "z") {
        ev.preventDefault();
        if (ev.shiftKey) redo();
        else undo();
      } else if (!editingText && (ev.ctrlKey || ev.metaKey) && ev.key.toLowerCase() === "y") {
        ev.preventDefault();
        redo();
      }
    });
    PRESETS.forEach(function (p) { var o = document.createElement("option"); o.value = p; o.textContent = PRESET_LABELS[p] || p; els.t_preset.appendChild(o); });
    CUE_TYPES.forEach(function (c) { var o = document.createElement("option"); o.value = c; o.textContent = CUE_LABELS[c] || c; els.t_cuetype.appendChild(o); });
    window.addEventListener("resize", function () { renderTimelineLanes(); renderMonitor(); });
  }

  document.addEventListener("DOMContentLoaded", function () {
    cacheEls();
    wire();
    loadRunSelector();
    loadPreview();
  });
})();
