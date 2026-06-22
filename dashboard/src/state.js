export const state = {
  root: new URLSearchParams(window.location.search).get("root") || "",
  activeView: "route",
  control: null,
  materialMap: null,
  artifacts: null,
  workbenchHealth: null,
  projects: [],
  activeStage: "Material Map",
  selectedEvidence: null,
};

export function setActiveView(view) {
  state.activeView = view;
}

export function rootQuery() {
  return state.root ? `?root=${encodeURIComponent(state.root)}` : "";
}

export function setActiveStage(stage) {
  state.activeStage = stage;
}

export function setSelectedEvidence(selectedEvidence) {
  state.selectedEvidence = selectedEvidence;
}
