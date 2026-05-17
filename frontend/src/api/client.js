const API_BASE = import.meta.env.VITE_API_BASE || "/api";

function tryParseJson(text) {
  if (!text) {
    return null;
  }

  try {
    return JSON.parse(text);
  } catch {
    return null;
  }
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const hasBody = response.status !== 204 && response.status !== 205;
  const text = hasBody ? await response.text() : "";
  const data = tryParseJson(text);

  if (!response.ok) {
    if (response.status === 401) {
      window.dispatchEvent(new CustomEvent("swagmonitor:unauthorized"));
    }

    let message = `Request failed with ${response.status}`;

    if (data && typeof data === "object") {
      message = data.detail || data.message || JSON.stringify(data);
    } else {
      message = text || message;
    }

    const error = new Error(message);
    error.status = response.status;
    throw error;
  }

  if (!hasBody || !text) {
    return null;
  }

  return data ?? text;
}

export const api = {
  me: () => request("/auth/me"),
  login: (payload) =>
    request("/auth/login", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
  logout: () =>
    request("/auth/logout", {
      method: "POST",
    }),
  users: () => request("/auth/users"),
  createUser: (payload) =>
    request("/auth/users", {
      method: "POST",
      body: JSON.stringify(payload),
    }),
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
  runServiceCheck: (id) =>
    request(`/servers/checks/${id}/run`, {
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
