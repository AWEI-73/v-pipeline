(function () {
    const dashboardFacts = document.getElementById("dashboard-facts");
    const controlStatus = document.getElementById("control-status");
    const workbenchReadiness = document.getElementById("workbench-readiness");
    const workbenchHealth = document.getElementById("workbench-health");
    const workbenchDrafts = document.getElementById("workbench-drafts");
    const workbenchCommand = document.getElementById("workbench-command");
    const btnOpenWorkbench = document.getElementById("btn-open-workbench");
    const btnOpenDashboard = document.getElementById("btn-open-dashboard");

    function setText(selector, value) {
        const node = dashboardFacts && dashboardFacts.querySelector(selector);
        if (node) node.textContent = value || "-";
    }

    function shortHash(value) {
        return value ? String(value).slice(0, 10) : "-";
    }

    function durationFromSlots(slots) {
        if (!Array.isArray(slots) || slots.length === 0) return 0;
        return slots.reduce(function (max, slot) {
            const end = Number(slot && (slot.end_sec || slot.end || 0));
            return Number.isFinite(end) ? Math.max(max, end) : max;
        }, 0);
    }

    function runLayoutLabel(runLayout) {
        if (!runLayout || !runLayout.exists) return "missing";
        if (runLayout.error) return "error";
        const folders = runLayout.folders && typeof runLayout.folders === "object"
            ? Object.keys(runLayout.folders).length
            : 0;
        return "available (" + folders + " folders)";
    }

    function renderStatus(kind, text) {
        if (!controlStatus) return;
        controlStatus.innerHTML = '<span class="status-dot ' + kind + '"></span><span>' + text + '</span>';
    }

    function renderWorkbench(workbench) {
        const summary = (workbench && workbench.draft_summary) || {};
        const drafts = (workbench && workbench.draft_artifacts) || {};
        const agentReady = Boolean(summary.agent_ready);
        const presentCount = Number(summary.present_count || 0);
        const state = agentReady ? "ready" : (presentCount > 0 ? "draft" : "unknown");
        const label = agentReady ? "agent_ready" : (presentCount > 0 ? "drafts_present" : "clean");

        if (workbenchReadiness) {
            workbenchReadiness.innerHTML = [
                '<span class="readiness-pill ' + state + '">' + label + '</span>',
                '<span class="readiness-text">',
                agentReady
                    ? "Handoff and review report are both present."
                    : presentCount > 0
                        ? "Draft files exist; Agent review may still need a handoff or report."
                        : "No Workbench draft artifacts detected.",
                "</span>"
            ].join("");
        }

        if (workbenchDrafts) {
            const tracked = [
                ["timeline", drafts.timeline_patch],
                ["contract", drafts.workbench_contract_patch],
                ["handoff", drafts.workbench_handoff],
                ["review", drafts.workbench_review_report],
                ["audio", drafts.audio_cue_patch],
                ["effects", drafts.effect_patch],
            ];
            workbenchDrafts.innerHTML = tracked.map(function (entry) {
                const labelText = entry[0];
                const item = entry[1] || {};
                const active = Boolean(item.exists);
                const value = active
                    ? (String(item.size_bytes || 0) + " bytes · " + shortHash(item.sha256))
                    : "none";
                return [
                    '<div class="draft-item ' + (active ? "present" : "") + '">',
                    '<div class="draft-label">' + labelText + '</div>',
                    '<div class="draft-value">' + value + '</div>',
                    '</div>'
                ].join("");
            }).join("");
        }

        if (workbenchCommand && workbench && workbench.command) {
            workbenchCommand.textContent = workbench.command;
        }

        if (btnOpenWorkbench && workbench && workbench.url) {
            btnOpenWorkbench.href = workbench.url;
        }
    }

    function renderWorkbenchHealth(payload) {
        if (!workbenchHealth) return;
        const ok = Boolean(payload && payload.ok);
        workbenchHealth.innerHTML = [
            '<span class="readiness-pill ' + (ok ? "ready" : "draft") + '">' + (ok ? "server_ok" : "server_off") + '</span>',
            '<span class="readiness-text">',
            ok
                ? "Workbench server is reachable."
                : "Workbench server is not reachable yet. Use the start command below.",
            "</span>"
        ].join("");
    }

    async function loadWorkbenchHealth() {
        try {
            const response = await fetch("/api/control/workbench-health");
            if (!response.ok) throw new Error("HTTP " + response.status);
            renderWorkbenchHealth(await response.json());
        } catch (err) {
            renderWorkbenchHealth({ ok: false, error: String(err && err.message || err) });
        }
    }

    async function loadArtifacts() {
        const params = new URLSearchParams(window.location.search);
        const root = params.get("root");
        const query = root ? ("?root=" + encodeURIComponent(root)) : "";
        if (btnOpenDashboard && root) {
            btnOpenDashboard.href = "/dashboard?root=" + encodeURIComponent(root);
        }

        try {
            const response = await fetch("/api/control/status" + query);
            if (!response.ok) throw new Error("HTTP " + response.status);
            const data = await response.json();
            const duration = Number(data.timeline && data.timeline.duration_sec || 0);
            const hasFinal = Boolean(data.final_video && data.final_video.exists);
            setText('[data-field="artifact-root"]', data.artifact_root || "-");
            setText('[data-field="duration"]', duration.toFixed(2) + "s");
            setText('[data-field="final-video"]', hasFinal ? "present" : "missing");
            setText('[data-field="run-layout"]', runLayoutLabel(data.run_layout));
            renderWorkbench(data.workbench || {});

            const ready = data.workbench && data.workbench.draft_summary && data.workbench.draft_summary.agent_ready;
            renderStatus(ready ? "ready" : "warning", ready ? "Agent-ready drafts detected" : "Control index ready");
            loadWorkbenchHealth();
        } catch (err) {
            setText('[data-field="artifact-root"]', "-");
            setText('[data-field="duration"]', "-");
            setText('[data-field="final-video"]', "-");
            setText('[data-field="run-layout"]', "-");
            renderStatus("error", "Unable to load /api/control/status");
            if (workbenchReadiness) {
                workbenchReadiness.innerHTML = '<span class="readiness-pill unknown">error</span><span class="readiness-text">' + String(err.message || err) + '</span>';
            }
            renderWorkbenchHealth({ ok: false });
        }
    }

    loadArtifacts();
}());
