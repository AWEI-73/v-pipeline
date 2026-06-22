export async function fetchProjects() {
  const response = await fetch("/api/projects");
  if (!response.ok) throw new Error(`projects failed: ${response.status}`);
  return response.json();
}
