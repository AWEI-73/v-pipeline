import { escapeHtml } from "./StatusPill.js";

export function ArtifactCard({ label, artifact, status }) {
  return `
    <article class="artifact-card ${escapeHtml(status || "unknown")}">
      <strong>${escapeHtml(label)}</strong>
      <span>${escapeHtml(artifact)}</span>
    </article>
  `;
}
