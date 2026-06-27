/*
 * Pure helpers for the Workbench material browser.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory();
  } else {
    root.WorkbenchMaterials = factory();
  }
}(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";

  function families(assets) {
    var seen = {};
    (assets || []).forEach(function (a) {
      var fam = a && a.visual_family;
      if (fam) seen[fam] = true;
    });
    return Object.keys(seen).sort();
  }

  function searchableText(asset) {
    asset = asset || {};
    return [
      asset.asset_id,
      asset.asset_type,
      asset.visual_family,
      asset.angle_scale,
      asset.action_family,
      asset.subject,
      asset.caption,
    ].join(" ").toLowerCase();
  }

  function sceneSatisfies(scene) {
    scene = scene || {};
    if (Array.isArray(scene.satisfies)) {
      return scene.satisfies.filter(function (edge) {
        return edge && edge.need_id;
      });
    }
    var ids = Array.isArray(scene.need_ids) ? scene.need_ids : [];
    var statuses = Array.isArray(scene.statuses) ? scene.statuses : [];
    return ids.map(function (id, idx) {
      return { need_id: id, status: statuses[idx] || "candidate" };
    });
  }

  function matchStatusForNeed(scene, needId) {
    if (!needId) return "other";
    var edges = sceneSatisfies(scene);
    var match = edges.find(function (edge) {
      return edge.need_id === needId;
    });
    return match ? (match.status || "candidate") : "other";
  }

  function scoreMatch(status) {
    if (status === "accepted") return 0;
    if (status === "candidate") return 1;
    return 2;
  }

  function replacementCandidates(assets, clip) {
    clip = clip || {};
    var candidates = [];
    (assets || []).forEach(function (asset) {
      if (!asset) return;
      if (clip.asset_id && asset.asset_id === clip.asset_id) return;
      if (clip.source_path && asset.source_path && asset.source_path === clip.source_path) return;
      var scenes = Array.isArray(asset.scenes) ? asset.scenes : [];
      if (!scenes.length) scenes = [{ scene_index: 0 }];
      scenes.forEach(function (scene, fallbackIndex) {
        if (!scene) return;
        var sceneIndex = Number.isInteger(scene.scene_index) ? scene.scene_index : fallbackIndex;
        var matchStatus = matchStatusForNeed(scene, clip.need_id);
        candidates.push(Object.assign({}, asset, {
          scene_index: sceneIndex,
          scene: scene,
          match_status: matchStatus,
          match_need_id: clip.need_id || null,
          sort_score: scoreMatch(matchStatus),
        }));
      });
    });
    return candidates.sort(function (a, b) {
      if (a.sort_score !== b.sort_score) return a.sort_score - b.sort_score;
      if (a.asset_id !== b.asset_id) return String(a.asset_id).localeCompare(String(b.asset_id));
      return a.scene_index - b.scene_index;
    });
  }

  function filterAssets(assets, opts) {
    opts = opts || {};
    var q = String(opts.query || "").toLowerCase();
    var family = opts.family || "";
    return (assets || []).filter(function (asset) {
      if (!asset) return false;
      if (family && asset.visual_family !== family) return false;
      if (!q) return true;
      return searchableText(asset).indexOf(q) >= 0;
    });
  }

  return {
    families: families,
    filterAssets: filterAssets,
    replacementCandidates: replacementCandidates,
    sceneSatisfies: sceneSatisfies,
    searchableText: searchableText,
  };
}));
