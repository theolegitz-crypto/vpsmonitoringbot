const API_BASE = import.meta.env.VITE_API_BASE || "/api";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed with ${response.status}`);
  }

  if (response.status === 204) {
    return null;
  }

  return response.json();
}

export const api = {
  overview: () => request("/dashboard/overview"),
  incidents: () => request("/dashboard/incidents"),
  server: (id) => request(`/servers/${id}`),
  addServer: (payload) =>
    request("/servers", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  runServerCheck: (id) =>
    request(`/servers/${id}/run-check`, {
      method: "POST",
    }),
  muteServer: (id, duration) =>
    request(`/servers/${id}/mute`, {
      method: "POST",
      body: JSON.stringify({ duration }),
    }),
  unmuteServer: (id) =>
    request(`/servers/${id}/unmute`, {
      method: "POST",
    }),
};

