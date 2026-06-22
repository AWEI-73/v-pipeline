import { rootQuery } from "../state.js";

export async function fetchArtifacts() {
  const response = await fetch(`/api/artifacts${rootQuery()}`);
  if (!response.ok) throw new Error(`artifacts failed: ${response.status}`);
  return response.json();
}
