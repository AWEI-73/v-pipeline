import { pathForView } from "../router.js";

const navItems = [
  ["route", "流程總覽"],
  ["material-map", "素材地圖"],
  ["timeline", "時間軸"],
  ["verify", "驗證"],
  ["artifacts", "產物"],
];

export function TopNav(activeView, root) {
  const query = root ? `?root=${encodeURIComponent(root)}` : "";
  return `
    <nav class="top-nav" aria-label="儀表板視圖">
      ${navItems.map(([view, label]) => {
        const href = view === "route" ? pathForView("route") : pathForView(view);
        return `<a class="nav-item ${activeView === view ? "active" : ""}" href="${href}${query}" data-view="${view}">${label}</a>`;
      }).join("")}
    </nav>
  `;
}
