export const routes = {
  "/": "route",
  "/dashboard": "route",
  "/material-map": "material-map",
  "/workbench": "workbench",
  "/timeline": "timeline",
  "/verify": "verify",
  "/artifacts": "artifacts",
};

export function viewFromLocation(pathname = window.location.pathname) {
  return routes[pathname.replace(/\/$/, "") || "/"] || "route";
}

export function pathForView(view) {
  if (view === "material-map") return "/material-map";
  if (view === "workbench") return "/workbench";
  if (view === "timeline") return "/timeline";
  if (view === "verify") return "/verify";
  if (view === "artifacts") return "/artifacts";
  return "/dashboard";
}
