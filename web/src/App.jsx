import { useCallback, useEffect, useMemo, useState } from "react";

import ActivityMix from "./components/ActivityMix";
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
  const [mobileNavOpen, setMobileNavOpen] = useState(false);
  const [data, setData] = useState(initialData);
  const [apiConnected, setApiConnected] = useState(false);
  const [presentationMode, setPresentationMode] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
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
    const connected = [healthResult, cameraResult, eventResult, monitoringResult, capabilitiesResult]
      .some((result) => result.status === "fulfilled");
    const persistenceUnavailable = [cameraResult, eventResult]
      .some((result) => result.status === "fulfilled" && result.value?.persistence === "unavailable");

    setData({ cameras, events, health, monitoring, capabilities });
    setApiConnected(connected);
    setPresentationMode(!connected);

    if (!connected) {
      setError("The backend is unavailable. Showing synthetic presentation data; no live camera feed or event persistence is connected.");
    } else if (persistenceUnavailable) {
      setError("The API is reachable, but MongoDB persistence is unavailable. Showing synthetic presentation records until stored data can be read.");
    }

    setRefreshing(false);
    return connected;
  }, []);

  useEffect(() => {
    loadData({ quiet: true });
  }, [loadData]);

  useEffect(() => {
    if (!notice) return undefined;
    const timeoutId = window.setTimeout(() => setNotice(""), 3600);
    return () => window.clearTimeout(timeoutId);
  }, [notice]);

  const monitoringActive = data.monitoring?.status === "armed" || data.monitoring?.status === "running";
  const activityData = useMemo(() => deriveActivityMix(data.events), [data.events]);
  const openAttentionCount = data.events.filter(
    (event) => event.severity === "critical" && event.status !== "resolved",
  ).length;
  const enabledSourceCount = data.cameras.filter((camera) => camera.enabled !== false).length;
  const verifiedCount = data.events.filter((event) => event.status === "verified").length;
  const scoredEvents = data.events.filter((event) => Number.isFinite(Number(event.confidence)));
  const averageConfidence = scoredEvents.length
    ? Math.round((scoredEvents.reduce((sum, event) => sum + Number(event.confidence), 0) / scoredEvents.length) * 100)
    : null;
  const pageCopy = {
    overview: {
      title: "Workspace overview",
      description: "A calm view of what SHADE is observing across the local monitoring workspace.",
    },
    incidents: {
      title: "Event review",
      description: "Review temporal decision records and keep human judgment in the loop.",
    },
    sources: {
      title: "Camera sources",
      description: "Inspect the sources that can feed the local activity intelligence pipeline.",
    },
  }[activeView];

  const handleNavigate = (view) => {
    setActiveView(view);
    setMobileNavOpen(false);
  };

  const handleMonitor = async (camera) => {
    setNotice("");
    try {
      if (monitoringActive && data.monitoring?.camera_id === camera.camera_id) {
        const monitoring = await api.stopMonitoring();
        setData((current) => ({ ...current, monitoring }));
        setNotice("Monitoring intent cleared for the selected source.");
      } else {
        const monitoring = await api.startMonitoring(camera.camera_id);
        setData((current) => ({ ...current, monitoring }));
        setNotice(`Monitoring intent armed for ${camera.name || "the selected source"}.`);
      }
      setApiConnected(true);
      setPresentationMode(false);
    } catch {
      setNotice("The backend control plane is unavailable; presentation mode remains active.");
    }
  };

  const handleRefresh = async () => {
    const connected = await loadData();
    setNotice(connected ? "API snapshot refreshed." : "Presentation data refreshed; the backend is still unavailable.");
  };

  const handleOpenEvents = () => {
    handleNavigate("incidents");
  };

  return (
    <div className="app-shell">
      <div
        className={`sidebar-layer ${mobileNavOpen ? "sidebar-layer--open" : ""}`}
        onClick={() => setMobileNavOpen(false)}
        aria-hidden="true"
      />
      <div className={`sidebar-wrapper ${mobileNavOpen ? "sidebar-wrapper--open" : ""}`}>
        <Sidebar
          activeView={activeView}
          attentionCount={openAttentionCount}
          onNavigate={handleNavigate}
          onClose={() => setMobileNavOpen(false)}
        />
      </div>
      <main className="main-shell">
        <Topbar
          onMenu={() => setMobileNavOpen(true)}
          onRefresh={handleRefresh}
          refreshing={refreshing}
          apiReachable={apiConnected}
          notificationCount={openAttentionCount}
          onOpenIncidents={handleOpenEvents}
        />

        <div className="content-wrap">
          <section className="page-heading">
            <div className="page-heading__copy">
              <span className="eyebrow"><span className="eyebrow__line" /> Local control workspace</span>
              <h1>{pageCopy.title}</h1>
              <p>{pageCopy.description}</p>
            </div>
            <div className="page-heading__visual" aria-hidden="true">
              <img src="/Banner.png" alt="" />
              <span>Observe · Analyze · Verify</span>
            </div>
            <div className="heading-meta">
              <div className="date-block"><Icon name="clock" size={15} /><span>{new Intl.DateTimeFormat("en-US", { weekday: "long", month: "short", day: "numeric", timeZone: "Asia/Calcutta" }).format(new Date())}</span></div>
              <span className="heading-meta__divider" />
              <span className="secure-label"><Icon name="shield" size={14} /> Local-only workspace</span>
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
              <section className="metric-grid" aria-label="Workspace summary">
                <MetricCard label="Enabled sources" value={enabledSourceCount} detail={monitoringActive ? "One source has armed monitoring" : "Available for local monitoring"} icon="camera" tone="mint" />
                <MetricCard label="Verified events" value={verifiedCount} detail="Temporal decisions in the current view" icon="pulse" tone="violet" />
                <MetricCard label="Open attention" value={openAttentionCount} detail={openAttentionCount ? "Human review is recommended" : "No unresolved critical events"} icon="warning" tone={openAttentionCount ? "amber" : "blue"} />
                <MetricCard label="Mean event confidence" value={averageConfidence === null ? "—" : `${averageConfidence}%`} detail={averageConfidence === null ? "No event scores available" : "Mean returned score; not accuracy"} icon="activity" tone="blue" />
              </section>

              <section className="overview-grid">
                <article className="panel panel--activity">
                  <div className="panel-heading">
                    <div><span className="panel-kicker">Distribution</span><h2>Activity mix</h2></div>
                    <span className="panel-context">{presentationMode ? "Synthetic sample" : "Event-derived"}</span>
                  </div>
                  <ActivityMix data={activityData} />
                  <div className="panel-footnote"><span className="status-dot status-dot--mint" /> {activityData.length ? "Percentages are derived from the event records currently available." : "No event records are available for a distribution yet."}</div>
                </article>

                <article className="panel panel--monitor">
                  <div className="panel-heading">
                    <div><span className="panel-kicker">Control plane</span><h2>Monitoring status</h2></div>
                    <span className={`status-badge ${monitoringActive ? "status-badge--live" : ""}`} role="status"><span className="status-dot" /> {monitoringActive ? "Armed" : "Idle"}</span>
                  </div>
                  <div className="monitor-visual">
                    <div className={`monitor-orb ${monitoringActive ? "monitor-orb--active" : ""}`}><Icon name="shield" size={30} /></div>
                    <div className="monitor-rings"><span /><span /><span /></div>
                    <div className="monitor-visual__copy"><strong>{monitoringActive ? "Monitoring intent is armed" : "Ready to observe"}</strong><span>{monitoringActive ? `Armed for ${data.monitoring?.camera_id || "a camera source"}; capture remains a separate worker boundary.` : "Arm a local monitoring session from a source below."}</span></div>
                  </div>
                  <div className="monitor-details">
                    <div><span>Mode</span><strong>{data.health?.runtime?.mode || (presentationMode ? "presentation" : "unreported")}</strong></div>
                    <div><span>Persistence</span><strong>{data.health ? (data.health.database?.available ? "MongoDB online" : "MongoDB unavailable") : "Presentation only"}</strong></div>
                    <div><span>Review</span><strong>Human review required</strong></div>
                  </div>
                </article>
              </section>

              <section className="panel panel--wide">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Recent signals</span><h2>Latest event records</h2></div>
                  <button className="text-button" type="button" onClick={handleOpenEvents}>View event log <Icon name="chevron" size={15} /></button>
                </div>
                <EventTable events={data.events} compact onViewAll={handleOpenEvents} />
              </section>

              <section className="panel panel--wide">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Connected inputs</span><h2>Camera sources</h2></div>
                  <button className="text-button" type="button" onClick={() => handleNavigate("sources")}>Manage sources <Icon name="chevron" size={15} /></button>
                </div>
                <CameraGrid cameras={data.cameras} activeCameraId={data.monitoring?.camera_id} monitoringActive={monitoringActive} onMonitor={handleMonitor} />
              </section>
            </>
          )}

          {activeView === "incidents" && (
            <section className="panel panel--wide page-panel">
              <div className="panel-heading panel-heading--table">
                <div><span className="panel-kicker">Human review queue</span><h2>All event records</h2></div>
                <span className="panel-count">{data.events.length} records</span>
              </div>
              <EventTable events={data.events} />
            </section>
          )}

          {activeView === "sources" && (
            <section className="panel panel--wide page-panel">
              <div className="panel-heading panel-heading--table">
                <div><span className="panel-kicker">Input registry</span><h2>Camera source health</h2></div>
                <span className="panel-count">{data.cameras.length} sources</span>
              </div>
              <CameraGrid cameras={data.cameras} activeCameraId={data.monitoring?.camera_id} monitoringActive={monitoringActive} onMonitor={handleMonitor} />
            </section>
          )}
           <footer className="app-footer"><span>SHADE-ai · local activity intelligence</span><span><Icon name="shield" size={13} /> Safety aid · human review required</span><span>{presentationMode ? "Synthetic presentation data" : "API snapshot · persistence status above"}</span></footer>

        </div>
      </main>
    </div>
  );
}

export default App;
