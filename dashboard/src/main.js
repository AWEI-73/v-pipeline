import { state, setActiveView, setActiveStage, setSelectedEvidence } from "./state.js";
import { viewFromLocation } from "./router.js";
import { fetchControlStatus } from "./api/controlApi.js";
import { fetchMaterialMapView } from "./api/materialMapApi.js";
import { fetchArtifacts } from "./api/artifactsApi.js";
import { fetchWorkbenchHealth } from "./api/workbenchApi.js";
import { fetchProjects } from "./api/projectsApi.js";
import { AppHeader } from "./components/AppHeader.js";
import { TopNav } from "./components/TopNav.js";
import { RouteOverviewView } from "./views/RouteOverviewView.js";
import { MaterialMapView } from "./views/MaterialMapView.js";
import { WorkbenchView } from "./views/WorkbenchView.js";
import { TimelineView } from "./views/TimelineView.js";
import { VerifyView } from "./views/VerifyView.js";
import { ArtifactsView } from "./views/ArtifactsView.js";

const app = document.getElementById("app");

function renderView() {
  if (state.activeView === "material-map") return MaterialMapView({ materialMap: state.materialMap, selectedEvidence: state.selectedEvidence });
  if (state.activeView === "workbench") return WorkbenchView({ workbenchHealth: state.workbenchHealth, root: state.root, artifacts: state.artifacts });
  if (state.activeView === "timeline") return TimelineView({ artifacts: state.artifacts });
  if (state.activeView === "verify") return VerifyView({ artifacts: state.artifacts });
  if (state.activeView === "artifacts") return ArtifactsView({ control: state.control, materialMap: state.materialMap, artifacts: state.artifacts });
  return RouteOverviewView({
    control: state.control,
    materialMap: state.materialMap,
    artifacts: state.artifacts,
    activeStage: state.activeStage,
  });
}

function render() {
  app.className = state.activeView === "workbench" ? "app-workbench" : "";
  app.innerHTML = `
    ${AppHeader({ control: state.control, materialMap: state.materialMap, activeView: state.activeView, root: state.root, projects: state.projects })}
    ${TopNav(state.activeView, state.root)}
    <main class="dashboard-canvas">
      ${renderView()}
    </main>
  `;
  bindInteractions();
}

async function boot() {
  setActiveView(viewFromLocation());
  render();
  const [control, materialMap, artifacts, workbenchHealth, projects] = await Promise.all([
    fetchControlStatus(),
    fetchMaterialMapView(),
    fetchArtifacts().catch(() => null),
    fetchWorkbenchHealth().catch(() => null),
    fetchProjects().catch(() => []),
  ]);
  state.control = control;
  state.materialMap = materialMap;
  state.artifacts = artifacts;
  state.workbenchHealth = workbenchHealth;
  state.projects = projects || [];
  if (!state.root && control?.artifact_root) state.root = control.artifact_root;
  render();
}

function bindInteractions() {
  app.querySelectorAll("[data-stage]").forEach((button) => {
    button.addEventListener("click", () => {
      setActiveStage(button.getAttribute("data-stage"));
      render();
    });
  });
  const activateEvidenceCard = (card, type, idAttribute) => {
    setSelectedEvidence({ type, id: card.getAttribute(idAttribute) });
    render();
  };
  const bindEvidenceCard = (card, type, idAttribute) => {
    card.addEventListener("click", () => activateEvidenceCard(card, type, idAttribute));
    card.addEventListener("keydown", (event) => {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        activateEvidenceCard(card, type, idAttribute);
      }
    });
  };
  app.querySelectorAll("[data-asset-id]").forEach((card) => {
    bindEvidenceCard(card, "asset", "data-asset-id");
  });
  app.querySelectorAll("[data-need-id]").forEach((card) => {
    bindEvidenceCard(card, "need", "data-need-id");
  });
  const selector = app.querySelector("#spa-project-select");
  if (selector) {
    selector.addEventListener("change", () => {
      const nextRoot = selector.value;
      if (!nextRoot) return;
      const path = window.location.pathname || "/dashboard";
      window.location.href = `${path}?root=${encodeURIComponent(nextRoot)}`;
    });
  }
  const rootForm = app.querySelector("#spa-root-form");
  const rootInput = app.querySelector("#spa-root-input");
  if (rootForm && rootInput) {
    rootForm.addEventListener("submit", (event) => {
      event.preventDefault();
      const nextRoot = rootInput.value.trim();
      if (!nextRoot) return;
      const path = window.location.pathname || "/dashboard";
      window.location.href = `${path}?root=${encodeURIComponent(nextRoot)}`;
    });
  }
}

boot().catch((err) => {
  app.innerHTML = `<main class="dashboard-canvas"><section class="view-main full"><h1>儀表板載入失敗</h1><pre class="json-panel">${String(err.message || err)}</pre></section></main>`;
});
