import { rootQuery } from "../state.js";

export async function fetchMaterialMapView() {
  const response = await fetch(`/api/material-map-view${rootQuery()}`);
  if (!response.ok) throw new Error(`material map failed: ${response.status}`);
  return response.json();
}
