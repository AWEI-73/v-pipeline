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
    searchableText: searchableText,
  };
}));
