import { rootQuery } from "../state.js";

export async function fetchWorkbenchHealth() {
  const response = await fetch(`/api/workbench/health${rootQuery()}`);
  if (!response.ok) throw new Error(`workbench health failed: ${response.status}`);
  return response.json();
}

export async function fetchPreviewTimeline() {
  const response = await fetch(`/api/workbench/preview-timeline${rootQuery()}`);
  if (!response.ok) throw new Error(`preview timeline failed: ${response.status}`);
  return response.json();
}
