import { escapeHtml, statusPill } from "./StatusPill.js";

function rootName(root) {
  if (!root) return "loading";
  return String(root).split(/[\\/]/).filter(Boolean).pop() || root;
}

function modeLabel(entryPath) {
  if (entryPath === "material-first") return "棕地：素材優先";
  if (entryPath === "structure-first" || entryPath === "story-first") return "綠地：故事優先";
  return "尚未判定";
}

export function AppHeader({ control, materialMap, activeView, root, projects = [] }) {
  const route = [materialMap?.entry_path, materialMap?.route].filter(Boolean).join(" / ") || "loading";
  const artifactRoot = control?.artifact_root || materialMap?.artifact_root || root || "loading";
  const ready = materialMap?.ready_for_build ? statusPill("可進入 BUILD", "good") : statusPill("等待審核", "warn");
  const query = artifactRoot && artifactRoot !== "loading" ? `?root=${encodeURIComponent(artifactRoot)}` : "";
  const dashboardActive = activeView !== "workbench";
  const showRouteBanner = activeView !== "workbench";
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
          <p>影片製作管線工作台</p>
        </div>
      </div>

      <div class="mode-switcher" aria-label="工作模式">
        <a class="mode-tab ${dashboardActive ? "active" : ""}" href="/dashboard${query}">白盒 Dashboard</a>
        <a class="mode-tab ${activeView === "workbench" ? "active" : ""}" href="/workbench${query}">黑盒 Workbench</a>
      </div>

      <div class="header-meta">
        <div class="meta-group">
          <label for="spa-project-select">目前 Run</label>
          <select id="spa-project-select" title="${escapeHtml(artifactRoot)}" aria-label="選擇 Run 資料夾">
            ${projectOptions.length ? projectOptions.map((project) => `
              <option value="${escapeHtml(project.path)}" data-root="${escapeHtml(project.path)}" ${project.path === artifactRoot ? "selected" : ""}>${escapeHtml(project.name || rootName(project.path))}</option>
            `).join("") : `<option value="">loading</option>`}
          </select>
        </div>
        <form class="meta-group root-open-form" id="spa-root-form">
          <label for="spa-root-input">打開資料夾</label>
          <div class="root-open-row">
            <input id="spa-root-input" type="text" value="${artifactRoot !== "loading" ? escapeHtml(artifactRoot) : ""}" placeholder="貼上 run folder 路徑" aria-label="貼上 run folder 路徑" list="spa-project-paths" />
            <button type="submit">開啟</button>
          </div>
          <datalist id="spa-project-paths">
            ${projectOptions.map((project) => `<option value="${escapeHtml(project.path)}">${escapeHtml(project.name || rootName(project.path))}</option>`).join("")}
          </datalist>
        </form>
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
    ${showRouteBanner ? `<section class="pause-banner">
      <div>
        <strong>目前路線</strong>
        <p>${escapeHtml(route)} - ${materialMap?.ready_for_build ? "素材覆蓋已可支撐下一步。" : "素材覆蓋仍需要審核，暫不應直接進入 build。"}</p>
      </div>
      <div class="banner-actions">
        <a href="/material-map${query}">檢查素材地圖</a>
        <a href="/workbench${query}">打開 Workbench</a>
      </div>
    </section>` : ""}
  `;
}
