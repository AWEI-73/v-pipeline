export const routes = {
  "/": "workbench",
  "/dashboard": "route",
  "/material-map": "material-map",
  "/workbench": "workbench",
  "/timeline": "timeline",
  "/verify": "verify",
  "/artifacts": "artifacts",
};

export function viewFromLocation(pathname = window.location.pathname) {
  return routes[pathname.replace(/\/$/, "") || "/"] || "workbench";
}

export function pathForView(view) {
  if (view === "material-map") return "/material-map";
  if (view === "workbench") return "/";
  if (view === "timeline") return "/timeline";
  if (view === "verify") return "/verify";
  if (view === "artifacts") return "/artifacts";
  return "/dashboard";
}
