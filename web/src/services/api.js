const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  const payload = contentType.includes("application/json")
    ? await response.json()
    : await response.text();

  if (!response.ok) {
    const detail = typeof payload === "object" ? payload.detail : payload;
    throw new Error(detail || `Request failed with status ${response.status}`);
  }

  return payload;
}

export const api = {
  getRoot: () => request("/api/"),
  getHealth: () => request("/api/health/"),
  getCapabilities: () => request("/api/capabilities/"),
  getCameras: () => request("/api/cameras/"),
  getEvents: () => request("/api/events/"),
  getMonitoring: () => request("/api/monitoring/status/"),
  createCamera: (camera) =>
    request("/api/cameras/", {
      method: "POST",
      body: JSON.stringify(camera),
    }),
  startMonitoring: (cameraId) =>
    request("/api/monitoring/start/", {
      method: "POST",
      body: JSON.stringify({ camera_id: cameraId }),
    }),
  stopMonitoring: () =>
    request("/api/monitoring/stop/", {
      method: "POST",
      body: JSON.stringify({}),
    }),
};
