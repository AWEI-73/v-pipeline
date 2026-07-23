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

  function semanticTokens(value) {
    var stop = {
      and: true, the: true, to: true, of: true, for: true, in: true,
      candidate: true, scene: true, shot: true, clip: true,
    };
    return String(value || "")
      .toLowerCase()
      .split(/[^a-z0-9\u4e00-\u9fff]+/)
      .filter(function (token) { return token.length > 2 && !stop[token]; });
  }

  function sharesSemanticToken(left, right) {
    var leftTokens = semanticTokens(left);
    var rightSet = {};
    semanticTokens(right).forEach(function (token) { rightSet[token] = true; });
    return leftTokens.some(function (token) { return rightSet[token]; });
  }

  function matchSceneToClip(scene, asset, clip) {
    scene = scene || {};
    asset = asset || {};
    clip = clip || {};
    var needStatus = matchStatusForNeed(scene, clip.need_id);
    if (needStatus !== "other") return needStatus;

    var sceneFamily = scene.visual_family || asset.visual_family;
    var sceneAction = scene.action_family || asset.action_family;
    if (clip.visual_family && sceneFamily === clip.visual_family) return "family";
    if (clip.action_family && sceneAction === clip.action_family) return "family";

    var clipMeaning = [
      clip.story_role, clip.visual_family, clip.action_family, clip.caption,
    ].join(" ");
    var sceneMeaning = [
      sceneFamily, sceneAction, scene.caption, asset.caption,
    ].join(" ");
    return sharesSemanticToken(clipMeaning, sceneMeaning) ? "related" : "other";
  }

  function scoreMatch(status) {
    if (status === "accepted") return 0;
    if (status === "candidate") return 1;
    if (status === "family") return 2;
    if (status === "related") return 3;
    return 4;
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
        var matchStatus = matchSceneToClip(scene, asset, clip);
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

  function recommendedClipsForAsset(asset, clips) {
    asset = asset || {};
    var scenes = Array.isArray(asset.scenes) && asset.scenes.length
      ? asset.scenes
      : [{ scene_index: 0 }];
    var out = [];
    (clips || []).forEach(function (clip) {
      if (!clip) return;
      var best = null;
      scenes.forEach(function (scene, fallbackIndex) {
        var status = matchSceneToClip(scene, asset, clip);
        var score = scoreMatch(status);
        if (!best || score < best.sort_score) {
          best = {
            clip: clip,
            slot_index: clip.slot_index,
            scene_index: Number.isInteger(scene.scene_index) ? scene.scene_index : fallbackIndex,
            match_status: status,
            sort_score: score,
            is_current_asset: clip.asset_id === asset.asset_id,
          };
        }
      });
      if (best && best.match_status !== "other") out.push(best);
    });
    return out.sort(function (a, b) {
      if (a.sort_score !== b.sort_score) return a.sort_score - b.sort_score;
      return (a.clip.timeline_start_sec || 0) - (b.clip.timeline_start_sec || 0);
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
    matchSceneToClip: matchSceneToClip,
    replacementCandidates: replacementCandidates,
    recommendedClipsForAsset: recommendedClipsForAsset,
    sceneSatisfies: sceneSatisfies,
    searchableText: searchableText,
  };
}));
