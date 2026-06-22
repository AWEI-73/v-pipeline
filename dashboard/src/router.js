export const routes = {
  "/": "route",
  "/dashboard": "route",
  "/material-map": "material-map",
  "/workbench": "workbench",
};

export function viewFromLocation(pathname = window.location.pathname) {
  return routes[pathname.replace(/\/$/, "") || "/"] || "route";
}

export function pathForView(view) {
  if (view === "material-map") return "/material-map";
  if (view === "workbench") return "/workbench";
  return "/dashboard";
}
