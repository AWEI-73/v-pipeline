import { escapeHtml } from "../components/StatusPill.js";

export function VerifyView({ artifacts }) {
  const issues = artifacts?.issues || [];
  return `
    <section class="view-main full">
      <div class="section-head">
        <div>
          <p class="eyebrow">驗證</p>
          <h2>審核訊號</h2>
        </div>
        <span class="mode-chip">${escapeHtml(issues.length)} 個問題</span>
      </div>
      <div class="stack">
        ${issues.length ? issues.map((issue) => `
          <article class="need-card">
            <strong>${escapeHtml(issue.type)} / ${escapeHtml(issue.severity)}</strong>
            <p>${escapeHtml(issue.message)}</p>
          </article>
        `).join("") : "<div class='empty-state'>目前沒有載入驗證問題。</div>"}
      </div>
    </section>
  `;
}
