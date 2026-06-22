import { escapeHtml } from "../components/StatusPill.js";

export function ArtifactsView({ control, materialMap, artifacts }) {
  const payload = { control, materialMap, artifact_role: artifacts?.artifact_role, profile: artifacts?.profile };
  return `
    <section class="view-main full">
      <div class="section-head">
        <div>
          <p class="eyebrow">產物</p>
          <h2>已載入 JSON</h2>
        </div>
      </div>
      <pre class="json-panel">${escapeHtml(JSON.stringify(payload, null, 2))}</pre>
    </section>
  `;
}
