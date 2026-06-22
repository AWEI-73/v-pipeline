import { escapeHtml, statusPill } from "./StatusPill.js";

function rootName(root) {
  if (!root) return "loading";
  return String(root).split(/[\\/]/).filter(Boolean).pop() || root;
}

function modeLabel(entryPath) {
  if (entryPath === "material-first") return "棕地：已有素材";
  if (entryPath === "structure-first") return "綠地：先做結構";
  return "待補上下文";
}

export function AppHeader({ control, materialMap, activeView, root, projects = [] }) {
  const route = [materialMap?.entry_path, materialMap?.route].filter(Boolean).join(" / ") || "loading";
  const artifactRoot = control?.artifact_root || materialMap?.artifact_root || root || "loading";
  const ready = materialMap?.ready_for_build ? statusPill("可進入 BUILD", "good") : statusPill("需要審核", "warn");
  const query = artifactRoot && artifactRoot !== "loading" ? `?root=${encodeURIComponent(artifactRoot)}` : "";
  const dashboardActive = activeView !== "workbench";
  const projectOptions = [
    ...(artifactRoot && artifactRoot !== "loading" && !projects.some((item) => item.path === artifactRoot)
      ? [{ name: rootName(artifactRoot), path: artifactRoot }]
      : []),
    ...projects,
  ];
  return `
    <header class="app-header">
      <div class="brand-section">
        <div class="logo-box">H</div>
        <div>
          <h1>Hermes</h1>
          <p>影片管線儀表板</p>
        </div>
      </div>

      <div class="mode-switcher" aria-label="工作模式">
        <a class="mode-tab ${dashboardActive ? "active" : ""}" href="/dashboard${query}">儀表板</a>
        <a class="mode-tab ${activeView === "workbench" ? "active" : ""}" href="/workbench${query}">剪輯工作區</a>
      </div>

      <div class="header-meta">
        <div class="meta-group">
          <label for="spa-project-select">選擇 Run</label>
          <select id="spa-project-select" title="${escapeHtml(artifactRoot)}" aria-label="選擇 Run 資料夾">
            ${projectOptions.length ? projectOptions.map((project) => `
              <option value="${escapeHtml(project.path)}" data-root="${escapeHtml(project.path)}" ${project.path === artifactRoot ? "selected" : ""}>${escapeHtml(project.name || rootName(project.path))}</option>
            `).join("") : `<option value="">loading</option>`}
          </select>
        </div>
        <div class="meta-group">
          <span>模式</span>
          <strong>${escapeHtml(modeLabel(materialMap?.entry_path))}</strong>
        </div>
        <div class="meta-group">
          <span>關卡</span>
          ${ready}
        </div>
      </div>
    </header>
    <section class="pause-banner">
      <div>
        <strong>審核暫停</strong>
        <p>${escapeHtml(route)} - ${materialMap?.ready_for_build ? "素材覆蓋已可進入 build。" : "素材覆蓋需要先審核再進入 build。"}</p>
      </div>
      <div class="banner-actions">
        <a href="/material-map${query}">審核素材地圖</a>
        <a href="/workbench${query}">開啟剪輯工作區</a>
      </div>
    </section>
  `;
}
