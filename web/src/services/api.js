const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || "";
const pendingReads = new Map();

function errorMessage(payload, status) {
  if (typeof payload === "string" && payload.trim()) {
    return payload.trim().slice(0, 240);
  }

  if (payload && typeof payload === "object") {
    if (typeof payload.detail === "string" && payload.detail.trim()) return payload.detail;

    const fieldErrors = Object.entries(payload).flatMap(([field, errors]) => {
      const messages = Array.isArray(errors) ? errors : [errors];
      return messages
        .filter((message) => typeof message === "string" && message.trim())
        .map((message) => field === "non_field_errors" ? message : `${field}: ${message}`);
    });
    if (fieldErrors.length) return fieldErrors.join(" ");
  }

  return `Request failed with status ${status}`;
}

async function request(path, options = {}) {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    headers: {
      Accept: "application/json",
      "Content-Type": "application/json",
      ...(options.headers || {}),
    },
    ...options,
  });

  const contentType = response.headers.get("content-type") || "";
  let payload;
  try {
    payload = contentType.includes("application/json")
      ? await response.json()
      : await response.text();
  } catch {
    throw new Error(`The API returned an unreadable response (${response.status}).`);
  }

  if (!response.ok) throw new Error(errorMessage(payload, response.status));
  return payload;
}

function get(path) {
  if (pendingReads.has(path)) return pendingReads.get(path);

  const pending = request(path).finally(() => {
    if (pendingReads.get(path) === pending) pendingReads.delete(path);
  });
  pendingReads.set(path, pending);
  return pending;
}

async function mutate(path, options, invalidatedRead) {
  const result = await request(path, options);
  pendingReads.delete(invalidatedRead);
  return result;
}

export const api = {
  getRoot: () => get("/api/"),
  getHealth: () => get("/api/health/"),
  getCapabilities: () => get("/api/capabilities/"),
  getCameras: () => get("/api/cameras/"),
  getEvents: () => get("/api/events/"),
  getMonitoring: () => get("/api/monitoring/status/"),
  createCamera: (camera) =>
    mutate("/api/cameras/", {
      method: "POST",
      body: JSON.stringify(camera),
    }, "/api/cameras/"),
  startMonitoring: (cameraId) =>
    mutate("/api/monitoring/start/", {
      method: "POST",
      body: JSON.stringify({ camera_id: cameraId }),
    }, "/api/monitoring/status/"),
  stopMonitoring: () =>
    mutate("/api/monitoring/stop/", {
      method: "POST",
      body: JSON.stringify({}),
    }, "/api/monitoring/status/"),
};
