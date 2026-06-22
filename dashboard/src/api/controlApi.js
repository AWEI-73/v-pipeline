import { rootQuery } from "../state.js";

export async function fetchControlStatus() {
  const response = await fetch(`/api/control/status${rootQuery()}`);
  if (!response.ok) throw new Error(`control status failed: ${response.status}`);
  return response.json();
}
