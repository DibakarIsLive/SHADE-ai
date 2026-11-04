import { useCallback, useEffect, useMemo, useRef, useState } from "react";

import ActivityMix from "./components/ActivityMix";
import CameraForm from "./components/CameraForm";
import CameraGrid from "./components/CameraGrid";
import EventTable from "./components/EventTable";
import Icon from "./components/Icon";
import MetricCard from "./components/MetricCard";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import { presentationCameras, presentationEvents } from "./data/mockData";
import { api } from "./services/api";
import { titleCase } from "./utils/formatters";

const initialData = {
  cameras: [],
  events: [],
  health: null,
  monitoring: null,
  capabilities: null,
  cameraRecordsAvailable: false,
  eventRecordsAvailable: false,
};

function isRecord(value) {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function isCameraRecord(camera) {
  return isRecord(camera)
    && typeof camera.camera_id === "string"
    && camera.camera_id.length > 0
    && typeof camera.name === "string"
    && ["webcam", "rtsp", "video_file", "synthetic"].includes(camera.source_type)
    && typeof camera.enabled === "boolean"
    && typeof camera.status === "string"
    && (camera.location === undefined || typeof camera.location === "string");
}

function isEventRecord(event) {
  return isRecord(event)
    && typeof event.event_id === "string"
    && event.event_id.length > 0
    && typeof event.event_type === "string"
    && ["info", "warning", "critical"].includes(event.severity)
    && ["detected", "verified", "acknowledged", "resolved"].includes(event.status)
    && typeof event.camera_id === "string"
    && Number.isFinite(event.confidence)
    && event.confidence >= 0
    && event.confidence <= 1
    && typeof event.occurred_at === "string"
    && Number.isFinite(Date.parse(event.occurred_at))
    && isRecord(event.context)
    && (event.context.activity === undefined || typeof event.context.activity === "string")
    && (event.context.zone === undefined || typeof event.context.zone === "string");
}

function isListResponse(result, isValidItem) {
  return isRecord(result)
    && result.status === "fulfilled"
    && isRecord(result.value)
    && typeof isValidItem === "function"
    && Array.isArray(result.value.items)
    && Number.isInteger(result.value.count)
    && result.value.count === result.value.items.length
    && result.value.items.every((item) => isValidItem(item))
    && ["available", "unavailable"].includes(result.value.persistence);
}

function hasAvailableList(result, isValidItem) {
  return isListResponse(result, isValidItem) && result.value.persistence === "available";
}

function readItems(result, fallback, isValidItem) {
  return hasAvailableList(result, isValidItem) ? result.value.items : fallback;
}

function listFailureMessage(label, result, isValidItem) {
  if (result.status !== "fulfilled") return `${label} could not be loaded from the API.`;
  if (isListResponse(result, isValidItem) && result.value.persistence === "unavailable") {
    const detail = result.value.detail;
    return typeof detail === "string" && detail.trim()
      ? detail.trim()
      : `${label} persistence is unavailable.`;
  }
  return `${label} returned an unexpected response.`;
}

function deriveActivityMix(events) {
  if (!events.length) return [];

  const counts = new Map();
  events.forEach((event) => {
    const label = titleCase(event.context?.activity || "other");
    counts.set(label, (counts.get(label) || 0) + 1);
  });

  const total = [...counts.values()].reduce((sum, value) => sum + value, 0);
  const palette = ["mint", "blue", "violet", "slate"];
  const entries = [...counts.entries()].sort(([, first], [, second]) => second - first);
  const displayedEntries = entries.length > 4
    ? [...entries.slice(0, 3), ["Other", entries.slice(3).reduce((sum, [, count]) => sum + count, 0)]]
    : entries;
  const values = displayedEntries.map(([, count]) => Math.round((count / total) * 100));
  const roundingDifference = 100 - values.reduce((sum, value) => sum + value, 0);

  if (values.length) values[0] += roundingDifference;

  return displayedEntries.map(([label], index) => ({
    label,
    value: values[index],
    color: palette[index],
  }));
}

function normalizeHealth(health) {
  return isRecord(health)
    && health.service === "shade-ai-api"
    && ["healthy", "degraded"].includes(health.status)
    && isRecord(health.database)
    && typeof health.database.available === "boolean"
    ? health
    : null;
}

const WORKER_STATES = ["STOPPED", "STARTING", "RUNNING", "STOPPING", "FAILED"];
const ACTIVE_WORKER_STATES = ["STARTING", "RUNNING", "STOPPING"];
const MONITORING_POLL_INTERVAL_MS = 1000;

function normalizeMonitoring(monitoring) {
  if (!isRecord(monitoring) || !WORKER_STATES.includes(monitoring.status)) return null;
  if (typeof monitoring.updated_at !== "string") return null;
  if (typeof monitoring.provider_ready !== "boolean" || typeof monitoring.source_ready !== "boolean") return null;
  if (typeof monitoring.stop_requested !== "boolean" || typeof monitoring.cleanup_pending !== "boolean") return null;
  if (monitoring.inference_available !== null && typeof monitoring.inference_available !== "boolean") return null;
  for (const field of ["camera_id", "worker_id", "started_at", "ready_at", "provider", "model_name", "failure_code", "failure_reason"]) {
    if (monitoring[field] !== undefined && monitoring[field] !== null && typeof monitoring[field] !== "string") return null;
  }
  if (ACTIVE_WORKER_STATES.includes(monitoring.status) && (!monitoring.camera_id || !monitoring.worker_id)) return null;
  if (monitoring.status === "RUNNING" && (!monitoring.provider_ready || !monitoring.source_ready)) return null;
  if (monitoring.status === "FAILED" && !monitoring.failure_code) return null;
  return monitoring;
}

function monitoringStateLabel(status) {
  return ({
    STOPPED: "Stopped",
    STARTING: "Starting…",
    RUNNING: "Running",
    STOPPING: "Stopping…",
    FAILED: "Failed",
  })[status] || "Unavailable";
}

function normalizeCapabilities(capabilities) {
  return isRecord(capabilities)
    && capabilities.service === "shade-ai-api"
    && Array.isArray(capabilities.implemented)
    && Array.isArray(capabilities.planned)
    ? capabilities
    : null;
}

function App() {
  const [activeView, setActiveView] = useState("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [data, setData] = useState(initialData);
  const [apiConnected, setApiConnected] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [controlPending, setControlPending] = useState(false);
  const [cameraFormOpen, setCameraFormOpen] = useState(false);
  const [cameraSubmitting, setCameraSubmitting] = useState(false);
  const [cameraFormError, setCameraFormError] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");
  const [initialLoading, setInitialLoading] = useState(true);
  const [isMobile, setIsMobile] = useState(false);
  const mobileMenuButtonRef = useRef(null);
  const mobileCloseButtonRef = useRef(null);
  const mobileSidebarRef = useRef(null);
  const mainShellRef = useRef(null);
  const navigationWasOpen = useRef(false);
  const loadSequence = useRef(0);
  const monitoringSequence = useRef(0);
  const [monitoringPollError, setMonitoringPollError] = useState("");

  const loadData = useCallback(async ({ quiet = false } = {}) => {
    const requestId = ++loadSequence.current;
    const monitoringRequestId = ++monitoringSequence.current;
    if (!quiet) {
      setRefreshing(true);
      setNotice("");
    }
    setError("");

    const [healthResult, cameraResult, eventResult, monitoringResult, capabilitiesResult] = await Promise.allSettled([
      api.getHealth(),
      api.getCameras(),
      api.getEvents(),
      api.getMonitoring(),
      api.getCapabilities(),
    ]);

    const health = healthResult.status === "fulfilled" ? normalizeHealth(healthResult.value) : null;
    const cameraRecordsAvailable = hasAvailableList(cameraResult, isCameraRecord);
    const eventRecordsAvailable = hasAvailableList(eventResult, isEventRecord);
    const recordsUnavailable = !cameraRecordsAvailable || !eventRecordsAvailable;
    const cameras = readItems(cameraResult, presentationCameras, isCameraRecord);
    const events = readItems(eventResult, presentationEvents, isEventRecord);
    const monitoring = monitoringResult.status === "fulfilled" ? normalizeMonitoring(monitoringResult.value) : null;
    const capabilities = capabilitiesResult.status === "fulfilled" ? normalizeCapabilities(capabilitiesResult.value) : null;
    const backendReachable = Boolean(
      health || monitoring || capabilities
        || isListResponse(cameraResult, isCameraRecord)
        || isListResponse(eventResult, isEventRecord),
    );
    const recordsAvailable = cameraRecordsAvailable && eventRecordsAvailable;
    const availabilityMessages = [];

    if (!backendReachable) {
      availabilityMessages.push("The backend API is unavailable or returned an invalid response.");
    } else {
      if (!health) availabilityMessages.push("Health diagnostics are unavailable; API reachability does not establish database health.");
      if (!monitoring) availabilityMessages.push("The monitoring status endpoint returned no supported control state.");
      if (!capabilities) availabilityMessages.push("The API capability list could not be verified.");
    }
    if (!cameraRecordsAvailable) availabilityMessages.push(listFailureMessage("Camera source records", cameraResult, isCameraRecord));
    if (!eventRecordsAvailable) availabilityMessages.push(listFailureMessage("Event records", eventResult, isEventRecord));
    if (recordsUnavailable) {
      availabilityMessages.push("Synthetic demo examples replace unavailable API datasets and are not live records.");
    }

    if (requestId === loadSequence.current) {
      setData((current) => ({
        cameras,
        events,
        health,
        monitoring: monitoringRequestId === monitoringSequence.current ? monitoring : current.monitoring,
        capabilities,
        cameraRecordsAvailable,
        eventRecordsAvailable,
      }));
      if (monitoringRequestId === monitoringSequence.current) setMonitoringPollError("");
      setApiConnected(backendReachable);
      setError(availabilityMessages.join(" "));
      setInitialLoading(false);
      setRefreshing(false);
    }

    return { backendReachable, recordsAvailable, cameraRecordsAvailable, applied: requestId === loadSequence.current };
  }, []);

  useEffect(() => {
    loadData({ quiet: true });
    return () => {
      loadSequence.current += 1;
      monitoringSequence.current += 1;
    };
  }, [loadData]);

  useEffect(() => {
    const cleanupPending = data.monitoring?.cleanup_pending === true;
    if ((!ACTIVE_WORKER_STATES.includes(data.monitoring?.status) && !cleanupPending) || controlPending) return undefined;

    let cancelled = false;
    let timeoutId;
    const pollStatus = async () => {
      const requestId = ++monitoringSequence.current;
      try {
        const monitoring = normalizeMonitoring(await api.getMonitoring());
        if (!monitoring) throw new Error("The monitoring status endpoint returned an unsupported worker state.");
        if (!cancelled && requestId === monitoringSequence.current) {
          setData((current) => ({ ...current, monitoring }));
          setMonitoringPollError("");
        }
      } catch (requestError) {
        if (!cancelled && requestId === monitoringSequence.current) {
          setMonitoringPollError(requestError.message || "Worker status could not be refreshed.");
        }
      } finally {
        if (!cancelled) timeoutId = window.setTimeout(pollStatus, MONITORING_POLL_INTERVAL_MS);
      }
    };

    timeoutId = window.setTimeout(pollStatus, MONITORING_POLL_INTERVAL_MS);
    return () => {
      cancelled = true;
      window.clearTimeout(timeoutId);
    };
  }, [data.monitoring?.status, data.monitoring?.cleanup_pending, controlPending]);

  useEffect(() => {
    const mediaQuery = window.matchMedia("(max-width: 760px)");
    const syncViewport = (event) => {
      setIsMobile(event.matches);
      if (!event.matches) setMobileNavOpen(false);
    };
    syncViewport(mediaQuery);
    mediaQuery.addEventListener("change", syncViewport);
    return () => mediaQuery.removeEventListener("change", syncViewport);
  }, []);

  useEffect(() => {
    if (mainShellRef.current) mainShellRef.current.inert = isMobile && mobileNavOpen;
    return () => {
      if (mainShellRef.current) mainShellRef.current.inert = false;
    };
  }, [isMobile, mobileNavOpen]);

  useEffect(() => {
    if (mobileNavOpen && isMobile) {
      mobileCloseButtonRef.current?.focus();
    } else if (navigationWasOpen.current && isMobile) {
      mobileMenuButtonRef.current?.focus();
    }
    navigationWasOpen.current = mobileNavOpen;
  }, [isMobile, mobileNavOpen]);

  useEffect(() => {
    if (!mobileNavOpen || !isMobile) return undefined;
    const handleNavigationKey = (event) => {
      if (event.key === "Escape") {
        setMobileNavOpen(false);
        return;
      }
      if (event.key !== "Tab") return;

      const focusable = Array.from(
        mobileSidebarRef.current?.querySelectorAll('button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), [tabindex]:not([tabindex="-1"])') || [],
      ).filter((element) => element.getClientRects().length > 0);
      if (!focusable.length) return;

      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    };
    document.addEventListener("keydown", handleNavigationKey);
    return () => document.removeEventListener("keydown", handleNavigationKey);
  }, [isMobile, mobileNavOpen]);

  useEffect(() => {
    if (!notice) return undefined;
    const timeoutId = window.setTimeout(() => setNotice(""), 4200);
    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  const monitoringStatus = data.monitoring?.status || "unavailable";
  const monitoringStatusLabel = monitoringStateLabel(monitoringStatus);
  const monitoringRunning = monitoringStatus === "RUNNING";
  const monitoringTransitioning = monitoringStatus === "STARTING" || monitoringStatus === "STOPPING";
  const monitoringControlAvailable = Boolean(apiConnected && data.monitoring);
  const cameraConfigurationAvailable = Boolean(apiConnected && data.cameraRecordsAvailable);
  const cameraControlsAvailable = Boolean(monitoringControlAvailable && cameraConfigurationAvailable);
  const displayedCameras = data.cameras;
  const canStartMonitoring = ["STOPPED", "FAILED"].includes(monitoringStatus)
    && !data.monitoring?.cleanup_pending
    && cameraControlsAvailable;
  const canStopMonitoring = ["STARTING", "RUNNING"].includes(monitoringStatus)
    && monitoringControlAvailable;
  const activeCamera = data.monitoring?.camera_id
    ? displayedCameras.find((camera) => camera.camera_id === data.monitoring.camera_id)
    : null;
  const activeCameraName = activeCamera?.name || data.monitoring?.camera_id || "the selected camera";
  const monitoringDetail = monitoringStatus === "STARTING"
    ? "Worker process created; waiting for provider/model initialization and the video source to open."
    : monitoringRunning
      ? `${activeCameraName}: provider ${data.monitoring?.provider || "initialized"}${data.monitoring?.model_name ? ` (${data.monitoring.model_name})` : ""}; video source open. ${data.monitoring?.inference_available === false ? "Inference is unavailable with this provider; no detections or events are produced." : data.monitoring?.inference_available === true ? "Inference provider reports ready." : "Inference readiness was not reported."}`
      : monitoringStatus === "STOPPING"
        ? "Shutdown requested; waiting for the worker process to exit and be reaped."
        : monitoringStatus === "FAILED"
          ? data.monitoring?.failure_reason || "The worker failed; inspect the safe failure code and backend logs."
          : monitoringStatus === "STOPPED"
            ? "No monitoring worker is running. Starting requires a saved, enabled video-file camera."
            : "The backend has not reported a usable worker state.";
  const demoCameras = !data.cameraRecordsAvailable;
  const demoEvents = !data.eventRecordsAvailable;
  const displayedEvents = data.events;
  const activityData = useMemo(() => deriveActivityMix(displayedEvents), [displayedEvents]);
  const unresolvedCount = data.eventRecordsAvailable
    ? displayedEvents.filter((event) => event.status !== "resolved").length
    : null;
  const configuredCameraCount = data.cameraRecordsAvailable ? displayedCameras.length : null;
  const workerStateMetric = data.monitoring ? monitoringStatusLabel : "Unavailable";
  const verifiedCount = data.eventRecordsAvailable
    ? displayedEvents.filter((event) => event.status === "verified").length
    : null;
  const primaryCamera = data.cameraRecordsAvailable
    ? displayedCameras.find((camera) => camera.enabled && camera.camera_id && camera.source_type === "video_file")
    : null;
  const syntheticRuntime = data.health?.runtime?.mode === "synthetic";
  const syntheticSourceVisible = displayedCameras.some((camera) => camera.source_type === "synthetic");
  const demoMessages = [
    demoCameras ? "Camera cards are synthetic examples, not saved camera configurations." : "",
    demoEvents ? "Event rows are synthetic examples, not backend event records." : "",
    syntheticSourceVisible ? "A synthetic source is displayed; it is not a physical camera feed." : "",
    syntheticRuntime ? "The backend reports synthetic processing mode; production camera capture and AI are not integrated." : "",
  ].filter(Boolean);
  const demoBannerVisible = demoMessages.length > 0;
  const demoNoticeTitle = demoCameras || demoEvents
    ? "DEMO DATA · NOT LIVE RECORDS"
    : "SYNTHETIC MODE · NO PRODUCTION AI";

  const pageCopy = {
    overview: {
      title: "Monitoring Overview",
      description: "Observe the supervised worker lifecycle, configured video-file sources, event records, and system health.",
    },
    incidents: {
      title: "Event Log",
      description: "Detected, verified, acknowledged, and resolved are backend event-record states—not confirmed emergencies. No emergency-confirmation or false-positive workflow is implemented; human review is required.",
    },
    sources: {
      title: "Camera Sources",
      description: "Manage saved sources. UI-driven worker control currently accepts enabled video-file configurations only.",
    },
  }[activeView];

  const handleNavigate = (view) => {
    setActiveView(view);
    setCameraFormOpen(false);
    setCameraFormError("");
    setMobileNavOpen(false);
  };

  const handleConfigure = () => {
    if (!cameraConfigurationAvailable) {
      setNotice("Camera configuration is unavailable until the API and camera-record persistence are available.");
      setMobileNavOpen(false);
      return;
    }
    setActiveView("sources");
    setCameraFormOpen(true);
    setCameraFormError("");
    setMobileNavOpen(false);
  };

  const handleMonitor = async (camera) => {
    if (!camera?.camera_id || controlPending) return;
    const stoppingWorker = ["STARTING", "RUNNING"].includes(monitoringStatus)
      && data.monitoring?.camera_id === camera.camera_id;
    if (!apiConnected || !monitoringControlAvailable) {
      setNotice("Worker control requires a reachable API and an observed supervisor state.");
      return;
    }
    if ((monitoringTransitioning && !stoppingWorker) || data.monitoring?.cleanup_pending) {
      setNotice("Wait for the current worker transition and process cleanup to finish.");
      return;
    }
    if (!stoppingWorker && !canStartMonitoring) {
      setNotice(monitoringRunning
        ? `A worker is already running for ${activeCameraName}. Stop it before selecting another camera.`
        : "The worker supervisor is not currently accepting a start request.");
      return;
    }
    if (!stoppingWorker) {
      const configuredCamera = displayedCameras.find((source) => source.camera_id === camera.camera_id);
      if (!configuredCamera || !configuredCamera.enabled || configuredCamera.source_type !== "video_file") {
        setNotice("Monitoring currently requires a saved, enabled video-file camera configuration.");
        return;
      }
    }

    setNotice("");
    setError("");
    setMonitoringPollError("");
    setControlPending(true);
    ++monitoringSequence.current;
    try {
      const monitoring = normalizeMonitoring(stoppingWorker
        ? await api.stopMonitoring()
        : await api.startMonitoring(camera.camera_id));
      const acceptedStates = stoppingWorker ? ["STOPPING", "STOPPED", "FAILED"] : ["STARTING", "RUNNING", "FAILED"];
      if (!monitoring || !acceptedStates.includes(monitoring.status)
        || (!stoppingWorker && monitoring.camera_id !== camera.camera_id)) {
        throw new Error(`The monitoring API returned an unsupported ${stoppingWorker ? "stop" : "start"} response.`);
      }

      // Make the mutation response newer than any in-flight status read or dashboard snapshot.
      loadSequence.current += 1;
      ++monitoringSequence.current;
      setData((current) => ({ ...current, monitoring }));
      setRefreshing(false);
      setApiConnected(true);
      if (stoppingWorker) {
        if (monitoring.status === "FAILED") {
          setError(monitoring.failure_reason || "The worker failed during shutdown.");
        } else {
          setNotice(monitoring.status === "STOPPED"
            ? "The supervisor reports the worker stopped."
            : "Stop requested. Waiting for the worker process to exit.");
        }
      } else if (monitoring.status === "FAILED") {
        setNotice("");
        setError(monitoring.failure_reason || "The worker failed before becoming ready.");
      } else {
        setNotice(monitoring.status === "RUNNING"
          ? `The backend confirms the worker is running for ${camera.name || "the selected camera"}.`
          : `Start accepted for ${camera.name || "the selected camera"}. Waiting for provider and video-source readiness.`);
      }
    } catch (requestError) {
      setNotice("");
      setError(requestError.message || "The monitoring control is unavailable.");
    } finally {
      setControlPending(false);
    }
  };

  const handleCreateCamera = async (camera) => {
    setCameraFormError("");
    setNotice("");
    setCameraSubmitting(true);
    try {
      const createdCamera = await api.createCamera(camera);
      if (!isCameraRecord(createdCamera)) {
        throw new Error("The API returned an unsupported camera record after saving.");
      }
      loadSequence.current += 1;
      setRefreshing(false);
      setCameraFormOpen(false);
      const result = await loadData({ quiet: true });
      if (result.applied && result.cameraRecordsAvailable) {
        setNotice(`${createdCamera.name} was saved as a camera configuration. This does not establish camera connectivity or start a worker.`);
      } else {
        setNotice(`${createdCamera.name} was saved, but the complete camera list could not be confirmed. This does not establish camera connectivity or start a worker.`);
      }
    } catch (requestError) {
      setCameraFormError(requestError.message || "The camera could not be saved. Check the backend and MongoDB connection.");
    } finally {
      setCameraSubmitting(false);
    }
  };

  const handleRefresh = async () => {
    const result = await loadData();
    if (result.applied && result.backendReachable && result.recordsAvailable) setNotice("Dashboard data refreshed.");
  };

  return (
    <div className={`app-shell ${sidebarCollapsed ? "app-shell--sidebar-collapsed" : ""}`}>
      <div
        className={`sidebar-layer ${mobileNavOpen ? "sidebar-layer--open" : ""}`}
        onClick={() => setMobileNavOpen(false)}
        aria-hidden="true"
      />
      <div className={`sidebar-wrapper ${mobileNavOpen ? "sidebar-wrapper--open" : ""}`}>
        <Sidebar
          sidebarRef={mobileSidebarRef}
          closeButtonRef={mobileCloseButtonRef}
          activeView={activeView}
          attentionCount={unresolvedCount}
          collapsed={sidebarCollapsed}
          onNavigate={handleNavigate}
          onClose={() => setMobileNavOpen(false)}
          onToggle={() => setSidebarCollapsed((current) => !current)}
        />
      </div>
      <main className="main-shell" ref={mainShellRef}>
        <Topbar
          title={pageCopy.title}
          onMenu={() => setMobileNavOpen(true)}
          menuButtonRef={mobileMenuButtonRef}
          menuOpen={mobileNavOpen}
          initialLoading={initialLoading}
          onRefresh={handleRefresh}
          refreshing={refreshing}
          apiReachable={apiConnected}
          monitoringStatus={monitoringStatus}
        />

        <div className="content-wrap">
          <section className="page-heading">
            <div className="page-heading__copy">
              <span className="eyebrow"><span className="eyebrow__line" /> Local monitoring</span>
              <h1>{pageCopy.title}</h1>
              <p>{pageCopy.description}</p>
            </div>
            <div className="heading-meta">
              <div className="date-block"><Icon name="clock" size={15} /><span>{new Intl.DateTimeFormat("en-US", { weekday: "long", month: "short", day: "numeric", timeZone: "Asia/Calcutta" }).format(new Date())}</span></div>
            </div>
          </section>

          {error && (
            <div className="notice notice--info" role="status" aria-live="polite">
              <Icon name="info" size={17} />
              <span>{error}</span>
              <button type="button" onClick={() => setError("")} aria-label="Dismiss backend availability notice">
                <Icon name="close" size={15} />
              </button>
            </div>
          )}
          {notice && <div className="notice notice--success" role="status" aria-live="polite"><Icon name="check" size={17} /><span>{notice}</span></div>}
          {monitoringPollError && <div className="notice notice--info" role="status" aria-live="polite"><Icon name="info" size={17} /><span>Worker status may be stale: {monitoringPollError}</span></div>}

          {initialLoading ? (
            <div className="dashboard-loading" role="status" aria-live="polite">
              <Icon name="refresh" size={18} className="spin" />
              <span>Loading dashboard data…</span>
            </div>
          ) : (
            <>
          {demoBannerVisible && (
            <div className="demo-banner" role="note" aria-label={demoNoticeTitle}>
              <span className="demo-banner__icon"><Icon name="info" size={16} /></span>
              <div><strong>{demoNoticeTitle}</strong>{demoMessages.map((message) => <span key={message}>{message}</span>)}</div>
            </div>
          )}

          {activeView === "overview" && (
            <>
              <section className={`current-monitoring panel ${monitoringRunning ? "current-monitoring--active" : ""} ${monitoringStatus === "FAILED" ? "current-monitoring--failed" : ""}`} aria-labelledby="current-monitoring-title" aria-busy={monitoringTransitioning}>
                <div className="current-monitoring__copy">
                  <span className="panel-kicker">Supervised worker</span>
                  <div className="current-monitoring__title-row">
                    <span className={`current-monitoring__indicator ${monitoringRunning ? "current-monitoring__indicator--active" : ""} ${monitoringStatus === "FAILED" ? "current-monitoring__indicator--failed" : ""}`} aria-hidden="true" />
                    <h2 id="current-monitoring-title">{monitoringStatus === "FAILED" ? "Monitoring failed" : monitoringControlAvailable ? `Monitoring ${monitoringStatusLabel.toLowerCase()}` : "Worker state unavailable"}</h2>
                  </div>
                  <p>{monitoringDetail}</p>
                  {data.monitoring?.failure_code && <span className="monitoring-failure-code">Failure code: {data.monitoring.failure_code}</span>}
                  <div className="current-monitoring__actions">
                    {configuredCameraCount === 0 ? (
                      <button className="button button--primary" type="button" onClick={handleConfigure} disabled={!cameraConfigurationAvailable}>
                        <Icon name="add" size={15} /> Add camera source
                      </button>
                    ) : canStopMonitoring ? (
                      <button className="button button--primary" type="button" onClick={() => handleMonitor({ camera_id: data.monitoring?.camera_id })} disabled={controlPending}>
                        <Icon name="stop" size={14} /> {monitoringStatus === "STARTING" ? "Cancel startup" : "Stop monitoring"}
                      </button>
                    ) : monitoringStatus === "STOPPING" ? (
                      <button className="button button--primary" type="button" disabled>
                        <Icon name="stop" size={14} /> Stopping…
                      </button>
                    ) : (
                      <button className="button button--primary" type="button" onClick={() => handleMonitor(primaryCamera)} disabled={!canStartMonitoring || !primaryCamera || controlPending}>
                        <Icon name={monitoringStatus === "FAILED" ? "refresh" : "play"} size={14} />
                        {controlPending ? "Starting…" : primaryCamera ? monitoringStatus === "FAILED" ? "Retry worker" : "Start monitoring" : data.cameraRecordsAvailable ? "No enabled video-file camera" : "Camera records unavailable"}
                      </button>
                    )}
                    <button className="button button--secondary" type="button" onClick={() => handleNavigate("sources")}>
                      <Icon name="camera" size={15} /> Manage camera sources
                    </button>
                  </div>
                </div>
                <div className="current-monitoring__state" aria-label="Worker lifecycle summary">
                  <div className={`monitor-orb ${monitoringRunning ? "monitor-orb--active" : ""} ${monitoringStatus === "FAILED" ? "monitor-orb--failed" : ""}`}><Icon name={monitoringRunning ? "pulse" : monitoringStatus === "FAILED" ? "warning" : "shield"} size={30} /></div>
                  <div>
                    <span className="current-monitoring__state-label">Backend-observed state</span>
                    <strong>{monitoringControlAvailable ? monitoringStatusLabel : "Not reported"}</strong>
                    <small>{data.monitoring?.started_at ? `Started ${new Intl.DateTimeFormat("en-US", { hour: "numeric", minute: "2-digit", timeZone: "Asia/Calcutta" }).format(new Date(data.monitoring.started_at))}. ` : ""}{data.monitoring?.cleanup_pending ? "Process cleanup is pending. " : ""}Status refreshes every second while the worker is active or cleaning up. Human review remains required.</small>
                  </div>
                </div>
              </section>

              <section className="metric-grid" aria-label="Monitoring summary">
                <MetricCard label="Camera Sources" value={configuredCameraCount ?? "Unavailable"} detail={configuredCameraCount === null ? "API records unavailable" : configuredCameraCount ? "Saved configurations; not connected feeds" : "No saved configurations"} icon="camera" tone="mint" />
                <MetricCard label="Verified Event Records" value={verifiedCount ?? "Unavailable"} detail="Backend status label; not emergency confirmation" icon="pulse" tone="violet" />
                <MetricCard label="Unresolved Event Records" value={unresolvedCount ?? "Unavailable"} detail={unresolvedCount ? "Human review required; no emergency guarantee" : unresolvedCount === 0 ? "No unresolved API records" : "API records unavailable"} icon="warning" tone={unresolvedCount ? "amber" : "blue"} />
                <MetricCard label="Worker State" value={workerStateMetric} detail="Supervisor-observed lifecycle; polls every second while active or cleaning up" icon="signal" tone={monitoringStatus === "FAILED" ? "amber" : monitoringRunning ? "mint" : "blue"} />
              </section>

              <section className="panel panel--wide">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Cameras</span><h2>Camera Sources</h2></div>
                  <div className="panel-heading__actions">
                    <span className="panel-context">{demoCameras ? "Synthetic demo" : configuredCameraCount === null ? "Unavailable" : `${configuredCameraCount} configured`}</span>
                    <button className="text-button" type="button" onClick={handleConfigure} disabled={!cameraConfigurationAvailable}><Icon name="add" size={14} /> Add camera</button>
                  </div>
                </div>
<CameraGrid cameras={displayedCameras} activeCameraId={data.monitoring?.camera_id} workerState={monitoringStatus} controlsAvailable={cameraControlsAvailable} canStart={canStartMonitoring} canStop={canStopMonitoring} controlPending={controlPending} onMonitor={handleMonitor} onConfigure={handleConfigure} />
              </section>

              <section className="panel panel--wide attention-panel">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Current events</span><h2>Events Requiring Review</h2></div>
                  <button className="text-button" type="button" onClick={() => handleNavigate("incidents")}>View event log <Icon name="chevron" size={15} /></button>
                </div>
                <div className={`attention-summary ${unresolvedCount ? "attention-summary--warning" : ""}`}>
                  <span className="attention-summary__icon"><Icon name={unresolvedCount ? "warning" : "check"} size={20} /></span>
                  <div><strong>{!data.eventRecordsAvailable ? "API event records unavailable" : unresolvedCount ? `${unresolvedCount} event${unresolvedCount === 1 ? "" : "s"} require review` : "No unresolved API event records"}</strong><span>{!data.eventRecordsAvailable ? "Any visible examples are synthetic presentation data, not live events." : unresolvedCount ? "Review the Event Log; event states do not confirm an emergency." : "Verified and unresolved counts reflect the current API snapshot."}</span></div>
                </div>
              </section>

              <section className="panel panel--wide">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Recent activity</span><h2>Recent Events</h2></div>
                  <button className="text-button" type="button" onClick={() => handleNavigate("incidents")}>View all events <Icon name="chevron" size={15} /></button>
                </div>
                <EventTable events={displayedEvents} synthetic={demoEvents} compact onViewAll={() => handleNavigate("incidents")} />
              </section>

              <section className="overview-grid overview-grid--bottom">
                <article className="panel panel--activity">
                  <div className="panel-heading">
                    <div><span className="panel-kicker">Statistics</span><h2>Activity Mix</h2></div>
                    <span className="panel-context">{demoEvents ? "Synthetic demo" : data.eventRecordsAvailable ? "From API records" : "Unavailable"}</span>
                  </div>
                  <ActivityMix data={activityData} />
                  <div className="panel-footnote"><span className="status-dot status-dot--slate" aria-hidden="true" /> {activityData.length ? demoEvents ? "Percentages use synthetic examples, not saved API records." : "Percentages derive from saved API event records." : "Activity statistics are unavailable until event records load."}</div>
                </article>

                <article className="panel system-status-panel">
                  <div className="panel-heading">
                    <div><span className="panel-kicker">System health</span><h2>System Status</h2></div>
                    <span className={`status-badge ${data.health?.status === "healthy" ? "status-badge--live" : ""}`} role="status"><span className="status-dot" /> {data.health?.status === "healthy" ? "Healthy" : data.health?.status === "degraded" ? "Degraded" : apiConnected ? "Health not reported" : "Unavailable"}</span>
                  </div>
                  <div className="system-status-list">
                    <div><span><span className={`status-dot ${apiConnected ? "status-dot--mint" : ""}`} /> API</span><strong>{apiConnected ? "Connected" : "Unavailable"}</strong></div>
                    <div><span><span className={`status-dot ${data.health?.database?.available ? "status-dot--mint" : ""}`} /> Database</span><strong>{data.health ? data.health.database?.available ? "Connected" : "Unavailable" : "Not reported"}</strong></div>
                    <div><span><span className={`status-dot ${monitoringRunning ? "status-dot--mint" : monitoringStatus === "FAILED" ? "status-dot--red" : ""}`} /> Monitoring worker</span><strong>{data.monitoring ? monitoringStatusLabel : "Not reported"}</strong></div>
                    <div><span><span className="status-dot status-dot--slate" /> Live updates</span><strong>Not active</strong></div>
                  </div>
                  <p className="system-status-note">{data.health?.runtime?.mode ? `Processing mode: ${titleCase(data.health.runtime.mode)}.` : "Infrastructure details will appear after the backend responds."} Worker status comes from the process supervisor; database status describes stored-record availability.</p>
                </article>
              </section>
            </>
          )}

          {activeView === "incidents" && (
            <section className="panel panel--wide page-panel">
              <div className="panel-heading panel-heading--table">
                <div><span className="panel-kicker">Human review queue</span><h2>Event Log</h2></div>
                <span className="panel-count">{data.eventRecordsAvailable ? `${displayedEvents.length} API events` : "Synthetic demo"}</span>
              </div>
              <EventTable events={displayedEvents} synthetic={demoEvents} />
            </section>
          )}

          {activeView === "sources" && (
            <section className="panel panel--wide page-panel">
              <div className="panel-heading panel-heading--table">
                <div><span className="panel-kicker">Configuration registry</span><h2>Camera Sources</h2></div>
                <div className="panel-heading__actions">
                  <span className="panel-count">{demoCameras ? "Synthetic demo" : configuredCameraCount === null ? "Unavailable" : `${configuredCameraCount} configured`}</span>
                  <button className="button button--primary button--small" type="button" onClick={() => setCameraFormOpen(true)} disabled={!cameraConfigurationAvailable}><Icon name="add" size={14} /> Add camera</button>
                </div>
              </div>
              {cameraFormOpen && <CameraForm onCancel={() => { setCameraFormOpen(false); setCameraFormError(""); }} onSubmit={handleCreateCamera} submitting={cameraSubmitting} error={cameraFormError} />}
              <CameraGrid cameras={displayedCameras} activeCameraId={data.monitoring?.camera_id} workerState={monitoringStatus} controlsAvailable={cameraControlsAvailable} canStart={canStartMonitoring} canStop={canStopMonitoring} controlPending={controlPending} onMonitor={handleMonitor} onConfigure={handleConfigure} />
            </section>
          )}

          <footer className="app-footer"><span>SHADE-ai · local activity intelligence</span><span>{demoCameras || demoEvents ? "Synthetic demo data · not live records" : syntheticRuntime || syntheticSourceVisible ? "Synthetic mode · no production AI" : `Supervisor state · ${monitoringStatusLabel}`}</span></footer>
            </>
          )}
        </div>
      </main>
    </div>
  );
}

export default App;
