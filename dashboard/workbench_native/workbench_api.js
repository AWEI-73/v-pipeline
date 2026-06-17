/*
 * Workbench HTTP API client.
 *
 * Centralizes endpoint names and response wrapping so the UI controller can
 * focus on DOM state instead of fetch plumbing.
 */
(function (root, factory) {
  if (typeof module === "object" && module.exports) {
    module.exports = factory(root);
  } else {
    root.WorkbenchApi = factory(root);
  }
}(typeof globalThis !== "undefined" ? globalThis : this, function (root) {
  "use strict";

  var ENDPOINTS = {
    previewTimeline: "/api/workbench/preview-timeline",
    thumbnails: "/api/workbench/thumbnails",
    proxies: "/api/workbench/proxies",
    patch: "/api/workbench/patch",
    syncContract: "/api/workbench/sync-contract",
    saveAll: "/api/workbench/save-all",
    exportFfmpeg: "/api/workbench/export",
    reviewReport: "/api/workbench/review-report",
  };

  function fetchJson(url) {
    return root.fetch(url).then(function (r) { return r.json(); });
  }

  function postJson(url, payload) {
    return root.fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload || {}),
    }).then(function (r) {
      return r.json().then(function (j) { return { ok: r.ok, j: j }; });
    });
  }

  return {
    ENDPOINTS: ENDPOINTS,
    fetchPreviewTimeline: function () {
      return fetchJson(ENDPOINTS.previewTimeline);
    },
    fetchThumbnails: function () {
      return fetchJson(ENDPOINTS.thumbnails);
    },
    fetchProxies: function () {
      return fetchJson(ENDPOINTS.proxies);
    },
    savePatch: function (patch) {
      return postJson(ENDPOINTS.patch, { patch: patch });
    },
    syncContract: function (patch) {
      return postJson(ENDPOINTS.syncContract, { patch: patch });
    },
    saveAll: function (payload) {
      return postJson(ENDPOINTS.saveAll, payload);
    },
    exportFfmpeg: function (payload) {
      return postJson(ENDPOINTS.exportFfmpeg, payload);
    },
    writeReviewReport: function () {
      return postJson(ENDPOINTS.reviewReport, {});
    },
    _fetchJson: fetchJson,
    _postJson: postJson,
  };
}));
