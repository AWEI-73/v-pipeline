(function () {
    const stageLine = document.getElementById("stage-line");
    const artifactStrip = document.getElementById("artifact-strip");
    const assetList = document.getElementById("asset-list");
    const needList = document.getElementById("need-list");
    const status = document.getElementById("material-status");

    function text(value, fallback) {
        if (value === null || value === undefined || value === "") return fallback || "-";
        return String(value);
    }

    function escapeHtml(value) {
        return text(value, "").replace(/[&<>"']/g, function (char) {
            return {
                "&": "&amp;",
                "<": "&lt;",
                ">": "&gt;",
                '"': "&quot;",
                "'": "&#39;"
            }[char];
        });
    }

    function statusClass(value) {
        return String(value || "unknown").toLowerCase().replace(/[^a-z0-9_-]/g, "-");
    }

    function setSummary(data) {
        const stats = data.stats || {};
        document.getElementById("summary-route").textContent = [data.entry_path, data.route].filter(Boolean).join(" / ");
        document.getElementById("summary-audience").textContent = [data.video_type, data.audience].filter(Boolean).join(" | ");
        document.getElementById("summary-coverage").textContent = [
            stats.accepted_edges || 0,
            stats.candidate_edges || 0,
            stats.rejected_edges || 0
        ].join(" / ");
        document.getElementById("summary-build").textContent = data.ready_for_build ? "Ready for BUILD" : "Needs review";
        document.getElementById("summary-root").textContent = data.artifact_root || "-";
        status.textContent = data.ready_for_build ? "Ready" : "Review Needed";
        status.className = "status-pill " + (data.ready_for_build ? "ready" : "blocked");
    }

    function renderStages(stages) {
        stageLine.innerHTML = (stages || []).map(function (stage) {
            const cls = statusClass(stage.status);
            return [
                '<div class="stage-node ' + cls + '">',
                '<div class="stage-label">' + escapeHtml(stage.label) + '</div>',
                '<div class="stage-file mono">' + escapeHtml(stage.artifact) + '</div>',
                '</div>'
            ].join("");
        }).join("");
    }

    function renderArtifacts(stages) {
        artifactStrip.innerHTML = (stages || []).map(function (stage) {
            const cls = statusClass(stage.status);
            return [
                '<article class="artifact-card ' + cls + '">',
                '<strong>' + escapeHtml(stage.label) + '</strong>',
                '<span class="mono">' + escapeHtml(stage.artifact) + '</span>',
                '</article>'
            ].join("");
        }).join("");
    }

    function renderAssets(assets) {
        if (!assets || !assets.length) {
            assetList.innerHTML = '<div class="empty-state">No material assets found in this run folder.</div>';
            return;
        }
        assetList.innerHTML = assets.map(function (asset) {
            const scenes = (asset.scenes || []).map(function (scene) {
                const tags = []
                    .concat(scene.need_ids || [])
                    .concat(scene.statuses || [])
                    .concat([scene.visual_family, scene.angle_scale, scene.action_family].filter(Boolean));
                return [
                    '<div class="scene-row">',
                    '<div class="scene-caption">' + escapeHtml(scene.caption || "Untitled scene") + '</div>',
                    '<div class="scene-tags">',
                    tags.map(function (tag) {
                        return '<span class="scene-chip">' + escapeHtml(tag) + '</span>';
                    }).join(""),
                    '</div>',
                    '</div>'
                ].join("");
            }).join("");
            return [
                '<article class="asset-card">',
                '<div class="asset-top">',
                '<div><div class="asset-id mono">' + escapeHtml(asset.asset_id) + '</div>',
                '<div class="asset-meta">' + escapeHtml(asset.asset_type) + ' | ' + escapeHtml(asset.scene_count) + ' scenes</div></div>',
                '<div class="asset-meta">' + escapeHtml(asset.duration_sec) + ' sec</div>',
                '</div>',
                '<div class="asset-meta mono">' + escapeHtml(asset.source) + '</div>',
                '<div class="scene-list">' + scenes + '</div>',
                '</article>'
            ].join("");
        }).join("");
    }

    function renderNeeds(needs) {
        if (!needs || !needs.length) {
            needList.innerHTML = '<div class="empty-state">No material needs found in this run folder.</div>';
            return;
        }
        needList.innerHTML = needs.map(function (need) {
            const outcome = statusClass(need.outcome);
            return [
                '<article class="need-card">',
                '<div class="need-top">',
                '<div class="need-id mono">' + escapeHtml(need.need_id) + '</div>',
                '<span class="need-outcome ' + outcome + '">' + escapeHtml(need.outcome) + '</span>',
                '</div>',
                '<div class="need-meta">' + escapeHtml(need.purpose) + '</div>',
                '<div class="need-meta">required ' + escapeHtml(need.count) + ' | accepted ' + escapeHtml(need.accepted) + ' | candidate ' + escapeHtml(need.candidate) + '</div>',
                '<div class="need-meta">' + escapeHtml(need.reason) + '</div>',
                '</article>'
            ].join("");
        }).join("");
    }

    async function load() {
        const query = window.location.search || "";
        const response = await fetch("/api/material-map-view" + query);
        if (!response.ok) throw new Error("Failed to load material map view: " + response.status);
        const data = await response.json();
        setSummary(data);
        renderStages(data.stages);
        renderArtifacts(data.stages);
        renderAssets(data.assets);
        renderNeeds(data.needs);
    }

    load().catch(function (err) {
        status.textContent = "Error";
        status.className = "status-pill blocked";
        assetList.innerHTML = '<div class="empty-state">' + escapeHtml(err.message || err) + '</div>';
    });
}());
