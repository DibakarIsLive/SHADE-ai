import { useCallback, useEffect, useMemo, useState } from "react";

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
  cameras: presentationCameras,
  events: presentationEvents,
  health: null,
  monitoring: null,
  capabilities: null,
  persistenceUnavailable: false,
};

function readItems(result, fallback) {
  if (result.status !== "fulfilled" || !Array.isArray(result.value?.items)) {
    return fallback;
  }

  return result.value.persistence === "unavailable" ? fallback : result.value.items;
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
  const entries = [...counts.entries()]
    .sort(([, first], [, second]) => second - first)
    .slice(0, 4);
  const values = entries.map(([, count]) => Math.round((count / total) * 100));
  const roundingDifference = 100 - values.reduce((sum, value) => sum + value, 0);

  if (values.length) values[0] += roundingDifference;

  return entries.map(([label], index) => ({
    label,
    value: values[index],
    color: palette[index],
  }));
}

function normalizeHealth(health) {
  return health?.status === "healthy" || health?.status === "degraded" ? health : null;
}

function App() {
  const [activeView, setActiveView] = useState("overview");
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [data, setData] = useState(initialData);
  const [apiConnected, setApiConnected] = useState(false);
  const [presentationMode, setPresentationMode] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [controlPending, setControlPending] = useState(false);
  const [cameraFormOpen, setCameraFormOpen] = useState(false);
  const [cameraSubmitting, setCameraSubmitting] = useState(false);
  const [cameraFormError, setCameraFormError] = useState("");
  const [notice, setNotice] = useState("");
  const [error, setError] = useState("");

  const loadData = useCallback(async ({ quiet = false } = {}) => {
    if (!quiet) setRefreshing(true);
    setError("");

    const [healthResult, cameraResult, eventResult, monitoringResult, capabilitiesResult] = await Promise.allSettled([
      api.getHealth(),
      api.getCameras(),
      api.getEvents(),
      api.getMonitoring(),
      api.getCapabilities(),
    ]);

    const health = healthResult.status === "fulfilled" ? normalizeHealth(healthResult.value) : null;
    const cameras = readItems(cameraResult, presentationCameras);
    const events = readItems(eventResult, presentationEvents);
    const monitoring = monitoringResult.status === "fulfilled" ? monitoringResult.value : null;
    const capabilities = capabilitiesResult.status === "fulfilled" ? capabilitiesResult.value : null;
    const backendReachable = [healthResult, monitoringResult, capabilitiesResult]
      .some((result) => result.status === "fulfilled");
    const persistenceUnavailable = [cameraResult, eventResult]
      .some((result) => result.status !== "fulfilled" || result.value?.persistence === "unavailable");

    setData({ cameras, events, health, monitoring, capabilities, persistenceUnavailable });
    setApiConnected(backendReachable);
    setPresentationMode(!backendReachable);

    if (!backendReachable) {
      setError("The backend is unavailable. Demo data is shown for presentation only; camera controls and stored events are not connected.");
    } else if (persistenceUnavailable) {
      setError("The API is reachable, but stored camera and event records are unavailable. Demo data is shown until MongoDB persistence is available.");
    }

    setRefreshing(false);
    return backendReachable;
  }, []);

  useEffect(() => {
    loadData({ quiet: true });
  }, [loadData]);

  useEffect(() => {
    if (!notice) return undefined;
    const timeoutId = window.setTimeout(() => setNotice(""), 4200);
    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  const monitoringActive = data.monitoring?.status === "armed" || data.monitoring?.status === "running";
  const presentationOnly = presentationMode || data.persistenceUnavailable;
  const operationalCameras = presentationOnly ? [] : data.cameras;
  const operationalEvents = presentationOnly ? [] : data.events;
  const activityData = useMemo(() => deriveActivityMix(operationalEvents), [operationalEvents]);
  const unresolvedCount = operationalEvents.filter((event) => event.status !== "resolved").length;
  const configuredCameraCount = operationalCameras.length;
  const activeCameraCount = monitoringActive && data.monitoring?.camera_id ? 1 : 0;
  const verifiedCount = operationalEvents.filter((event) => event.status === "verified").length;
  const primaryCamera = operationalCameras.find((camera) => camera.enabled !== false);
  const demoMode = presentationOnly || data.health?.runtime?.mode === "synthetic";

  const pageCopy = {
    overview: {
      title: "Monitoring Overview",
      description: "See the current monitoring state, configured cameras, events, and system health in one place.",
    },
    incidents: {
      title: "Event Log",
      description: "Review recorded activity events and keep human judgment in the loop.",
    },
    sources: {
      title: "Camera Sources",
      description: "Manage the camera configurations available to the local monitoring control.",
    },
  }[activeView];

  const handleNavigate = (view) => {
    setActiveView(view);
    setCameraFormOpen(false);
    setCameraFormError("");
    setMobileNavOpen(false);
  };

  const handleConfigure = () => {
    setActiveView("sources");
    setCameraFormOpen(true);
    setCameraFormError("");
    setMobileNavOpen(false);
  };

  const handleMonitor = async (camera) => {
    if (!camera?.camera_id) return;
    if (!apiConnected || presentationOnly) {
      setNotice("Start the backend and make MongoDB available before using camera controls.");
      return;
    }

    setNotice("");
    setControlPending(true);
    try {
      if (monitoringActive && data.monitoring?.camera_id === camera.camera_id) {
        const monitoring = await api.stopMonitoring();
        setData((current) => ({ ...current, monitoring }));
        setNotice("Monitoring is now idle.");
      } else {
        const monitoring = await api.startMonitoring(camera.camera_id);
        setData((current) => ({ ...current, monitoring }));
        setNotice(`Monitoring intent armed for ${camera.name || "the selected camera"}.`);
      }
      setApiConnected(true);
      setPresentationMode(false);
    } catch (requestError) {
      setNotice(requestError.message || "The monitoring control is unavailable.");
    } finally {
      setControlPending(false);
    }
  };

  const handleCreateCamera = async (camera) => {
    setCameraFormError("");
    setCameraSubmitting(true);
    try {
      await api.createCamera(camera);
      setCameraFormOpen(false);
      const connected = await loadData({ quiet: true });
      setNotice(connected ? `${camera.name} was added to Camera Sources.` : "The camera was added, but the API snapshot could not be refreshed.");
    } catch (requestError) {
      setCameraFormError(requestError.message || "The camera could not be saved. Check the backend and MongoDB connection.");
    } finally {
      setCameraSubmitting(false);
    }
  };

  const handleRefresh = async () => {
    const connected = await loadData();
    setNotice(connected ? "Dashboard data refreshed." : "Demo data refreshed; the backend is still unavailable.");
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
          activeView={activeView}
          attentionCount={unresolvedCount}
          collapsed={sidebarCollapsed}
          onNavigate={handleNavigate}
          onClose={() => setMobileNavOpen(false)}
          onToggle={() => setSidebarCollapsed((current) => !current)}
        />
      </div>
      <main className="main-shell">
        <Topbar
          title={pageCopy.title}
          onMenu={() => setMobileNavOpen(true)}
          onRefresh={handleRefresh}
          refreshing={refreshing}
          apiReachable={apiConnected}
          monitoringActive={monitoringActive}
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

          {activeView === "overview" && (
            <>
              <section className={`current-monitoring panel ${monitoringActive ? "current-monitoring--active" : ""}`} aria-labelledby="current-monitoring-title">
                <div className="current-monitoring__copy">
                  <span className="panel-kicker">Current monitoring</span>
                  <div className="current-monitoring__title-row">
                    <span className={`current-monitoring__indicator ${monitoringActive ? "current-monitoring__indicator--active" : ""}`} aria-hidden="true" />
                    <h2 id="current-monitoring-title">{presentationOnly ? "Demo Mode" : monitoringActive ? "Monitoring active" : "Monitoring idle"}</h2>
                  </div>
                  <p>
                    {presentationOnly
                      ? "No backend records are connected. Sample data is shown for presentation only."
                      : monitoringActive
                        ? `Monitoring intent is armed for ${operationalCameras.find((camera) => camera.camera_id === data.monitoring?.camera_id)?.name || "the selected camera"}. Camera capture remains a separate worker boundary.`
                        : configuredCameraCount
                          ? "No camera is currently being monitored. Choose a configured camera to start a local monitoring session."
                          : "No camera sources are configured. Add a camera source before monitoring can begin."}
                  </p>
                  <div className="current-monitoring__actions">
                    {configuredCameraCount === 0 ? (
                      <button className="button button--primary" type="button" onClick={handleConfigure}>
                        <Icon name="add" size={15} /> Add camera source
                      </button>
                    ) : monitoringActive ? (
                      <button className="button button--primary" type="button" onClick={() => handleMonitor({ camera_id: data.monitoring?.camera_id })} disabled={controlPending || presentationOnly}>
                        <Icon name="stop" size={14} /> Stop monitoring
                      </button>
                    ) : (
                      <button className="button button--primary" type="button" onClick={() => handleMonitor(primaryCamera)} disabled={controlPending || presentationOnly || !primaryCamera}>
                        <Icon name="play" size={14} /> Start monitoring
                      </button>
                    )}
                    <button className="button button--secondary" type="button" onClick={() => handleNavigate("sources")}>
                      <Icon name="camera" size={15} /> Manage camera sources
                    </button>
                  </div>
                </div>
                <div className="current-monitoring__state" aria-label="Monitoring summary">
                  <div className={`monitor-orb ${monitoringActive ? "monitor-orb--active" : ""}`}><Icon name={presentationOnly ? "info" : monitoringActive ? "pulse" : "shield"} size={30} /></div>
                  <div>
                    <span className="current-monitoring__state-label">{monitoringActive ? "Session state" : "Next step"}</span>
                    <strong>{monitoringActive ? "Control intent armed" : configuredCameraCount ? "Select a camera" : "Configure a camera"}</strong>
                    <small>{demoMode ? "Backend connection required for live controls" : "Human review remains required"}</small>
                  </div>
                </div>
              </section>

              {demoMode && (
                <div className="demo-banner" role="note">
                  <span className="demo-banner__icon"><Icon name="info" size={16} /></span>
                  <div><strong>Demo Mode</strong><span>{data.health?.runtime?.mode === "synthetic" ? "Synthetic monitoring mode is enabled. Real camera processing is not active." : "Synthetic sample records are shown because the connected backend data is not available."}</span></div>
                </div>
              )}

              <section className="metric-grid" aria-label="Monitoring summary">
                <MetricCard label="Camera Sources" value={configuredCameraCount} detail={configuredCameraCount ? "Configured for local monitoring" : "Add a camera to begin"} icon="camera" tone="mint" />
                <MetricCard label="Verified Events" value={verifiedCount} detail="Confirmed after contextual analysis" icon="pulse" tone="violet" />
                <MetricCard label="Events Requiring Review" value={unresolvedCount} detail={unresolvedCount ? "Human review recommended" : "No unresolved events"} icon="warning" tone={unresolvedCount ? "amber" : "blue"} />
                <MetricCard label="Active Cameras" value={activeCameraCount} detail={activeCameraCount ? "Monitoring intent is armed" : "No camera currently active"} icon="signal" tone="blue" />
              </section>

              <section className="panel panel--wide">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Cameras</span><h2>Camera Sources</h2></div>
                  <div className="panel-heading__actions">
                    <span className="panel-context">{presentationOnly ? "Demo sample" : `${configuredCameraCount} configured`}</span>
                    <button className="text-button" type="button" onClick={handleConfigure}><Icon name="add" size={14} /> Add camera</button>
                  </div>
                </div>
                <CameraGrid cameras={operationalCameras} activeCameraId={data.monitoring?.camera_id} monitoringActive={monitoringActive} controlsAvailable={!presentationOnly} controlPending={controlPending} onMonitor={handleMonitor} onConfigure={handleConfigure} />
              </section>

              <section className="panel panel--wide attention-panel">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Current events</span><h2>Events Requiring Review</h2></div>
                  <button className="text-button" type="button" onClick={() => handleNavigate("incidents")}>View event log <Icon name="chevron" size={15} /></button>
                </div>
                <div className={`attention-summary ${unresolvedCount ? "attention-summary--warning" : ""}`}>
                  <span className="attention-summary__icon"><Icon name={unresolvedCount ? "warning" : "check"} size={20} /></span>
                  <div><strong>{presentationOnly ? "No connected event records" : unresolvedCount ? `${unresolvedCount} event${unresolvedCount === 1 ? "" : "s"} require review` : "No unresolved events"}</strong><span>{presentationOnly ? "Events will appear after stored activity records are available." : unresolvedCount ? "Review the Event Log before taking action." : "Verified and unresolved event counts are based on the current API snapshot."}</span></div>
                </div>
              </section>

              <section className="panel panel--wide">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Recent activity</span><h2>Recent Events</h2></div>
                  <button className="text-button" type="button" onClick={() => handleNavigate("incidents")}>View all events <Icon name="chevron" size={15} /></button>
                </div>
                <EventTable events={operationalEvents} compact onViewAll={() => handleNavigate("incidents")} onConfigure={handleConfigure} />
              </section>

              <section className="overview-grid overview-grid--bottom">
                <article className="panel panel--activity">
                  <div className="panel-heading">
                    <div><span className="panel-kicker">Statistics</span><h2>Activity Mix</h2></div>
                    <span className="panel-context">{presentationOnly ? "Waiting for records" : "From event records"}</span>
                  </div>
                  <ActivityMix data={activityData} onConfigure={handleConfigure} />
                  <div className="panel-footnote"><span className="status-dot status-dot--mint" /> {activityData.length ? "Percentages are derived from the event records currently available." : "Activity statistics will appear after monitoring records activity."}</div>
                </article>

                <article className="panel system-status-panel">
                  <div className="panel-heading">
                    <div><span className="panel-kicker">System health</span><h2>System Status</h2></div>
                    <span className={`status-badge ${data.health?.status === "healthy" ? "status-badge--live" : ""}`} role="status"><span className="status-dot" /> {data.health?.status === "healthy" ? "Healthy" : apiConnected ? "Degraded" : "Unavailable"}</span>
                  </div>
                  <div className="system-status-list">
                    <div><span><span className={`status-dot ${apiConnected ? "status-dot--mint" : ""}`} /> API</span><strong>{apiConnected ? "Connected" : "Unavailable"}</strong></div>
                    <div><span><span className={`status-dot ${data.health?.database?.available ? "status-dot--mint" : ""}`} /> Database</span><strong>{data.health ? data.health.database?.available ? "Connected" : "Unavailable" : "Not reported"}</strong></div>
                    <div><span><span className={`status-dot ${data.monitoring ? "status-dot--mint" : ""}`} /> Monitoring control</span><strong>{data.monitoring ? "Available" : "Not reported"}</strong></div>
                    <div><span><span className="status-dot status-dot--slate" /> Live updates</span><strong>Not active</strong></div>
                  </div>
                  <p className="system-status-note">{data.health?.runtime?.mode ? `Processing mode: ${titleCase(data.health.runtime.mode)}.` : "Infrastructure details will appear after the backend responds."} Database status describes stored-record availability, not monitoring activity.</p>
                </article>
              </section>
            </>
          )}

          {activeView === "incidents" && (
            <section className="panel panel--wide page-panel">
              <div className="panel-heading panel-heading--table">
                <div><span className="panel-kicker">Human review queue</span><h2>Event Log</h2></div>
                <span className="panel-count">{operationalEvents.length} events</span>
              </div>
              <EventTable events={operationalEvents} onConfigure={handleConfigure} />
            </section>
          )}

          {activeView === "sources" && (
            <section className="panel panel--wide page-panel">
              <div className="panel-heading panel-heading--table">
                <div><span className="panel-kicker">Configuration registry</span><h2>Camera Sources</h2></div>
                <div className="panel-heading__actions">
                  <span className="panel-count">{presentationOnly ? "Demo sample" : `${configuredCameraCount} configured`}</span>
                  <button className="button button--primary button--small" type="button" onClick={() => setCameraFormOpen(true)}><Icon name="add" size={14} /> Add camera</button>
                </div>
              </div>
              {cameraFormOpen && <CameraForm onCancel={() => { setCameraFormOpen(false); setCameraFormError(""); }} onSubmit={handleCreateCamera} submitting={cameraSubmitting} error={cameraFormError} />}
              <CameraGrid cameras={operationalCameras} activeCameraId={data.monitoring?.camera_id} monitoringActive={monitoringActive} controlsAvailable={!presentationOnly} controlPending={controlPending} onMonitor={handleMonitor} onConfigure={handleConfigure} />
            </section>
          )}

          <footer className="app-footer"><span>SHADE-ai · local activity intelligence</span><span>{presentationOnly ? "Demo data · backend required for controls" : "API snapshot · review before action"}</span></footer>
        </div>
      </main>
    </div>
  );
}

export default App;
