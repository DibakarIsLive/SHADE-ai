import { useCallback, useEffect, useMemo, useState } from "react";

import ActivityMix from "./components/ActivityMix";
import CameraGrid from "./components/CameraGrid";
import EventTable from "./components/EventTable";
import Icon from "./components/Icon";
import MetricCard from "./components/MetricCard";
import Sidebar from "./components/Sidebar";
import Topbar from "./components/Topbar";
import { activityMix as fallbackActivityMix, presentationCameras, presentationEvents } from "./data/mockData";
import { api } from "./services/api";
import { formatDateTime, formatRelativeTime, titleCase } from "./utils/formatters";

const initialData = {
  cameras: presentationCameras,
  events: presentationEvents,
  health: null,
  monitoring: null,
  capabilities: null,
};

function mergeItems(payload, fallback) {
  return Array.isArray(payload?.items) && payload.items.length ? payload.items : fallback;
}

function deriveActivityMix(events) {
  const counts = new Map();
  events.forEach((event) => {
    const label = titleCase(event.context?.activity || "other");
    counts.set(label, (counts.get(label) || 0) + 1);
  });

  if (!counts.size) return fallbackActivityMix;

  const total = [...counts.values()].reduce((sum, value) => sum + value, 0);
  const palette = ["mint", "blue", "violet", "slate"];
  return [...counts.entries()]
    .sort(([, first], [, second]) => second - first)
    .slice(0, 4)
    .map(([label, count], index) => ({
      label,
      value: Math.round((count / total) * 100),
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
    const cameras = cameraResult.status === "fulfilled" ? mergeItems(cameraResult.value, presentationCameras) : presentationCameras;
    const events = eventResult.status === "fulfilled" ? mergeItems(eventResult.value, presentationEvents) : presentationEvents;
    const monitoring = monitoringResult.status === "fulfilled" ? monitoringResult.value : null;
    const capabilities = capabilitiesResult.status === "fulfilled" ? capabilitiesResult.value : null;
    const connected = Boolean(health || cameraResult.status === "fulfilled" || eventResult.status === "fulfilled");

    setData({ cameras, events, health, monitoring, capabilities });
    setPresentationMode(!connected);
    if (!connected) setError("The backend is unavailable. Showing safe presentation data instead.");
    setRefreshing(false);
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
  const criticalCount = data.events.filter((event) => event.severity === "critical" && event.status !== "resolved").length;
  const activeCameraCount = data.cameras.filter((camera) => camera.enabled !== false).length;
  const verifiedCount = data.events.filter((event) => event.status === "verified").length;
  const averageConfidence = data.events.length
    ? Math.round((data.events.reduce((sum, event) => sum + Number(event.confidence || 0), 0) / data.events.length) * 100)
    : 0;

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
        setNotice("Monitoring stopped for the selected source.");
      } else {
        const monitoring = await api.startMonitoring(camera.camera_id);
        setData((current) => ({ ...current, monitoring }));
        setNotice(`Monitoring armed for ${camera.name || "the selected source"}.`);
      }
      setPresentationMode(false);
    } catch {
      setNotice("The backend control plane is unavailable in presentation mode.");
    }
  };

  const handleRefresh = async () => {
    await loadData();
    setNotice("Workspace data refreshed.");
  };

  const handleOpenIncidents = () => {
    handleNavigate("incidents");
  };

  return (
    <div className="app-shell">
      <div className={`sidebar-layer ${mobileNavOpen ? "sidebar-layer--open" : ""}`} onClick={() => setMobileNavOpen(false)} />
      <div className={`sidebar-wrapper ${mobileNavOpen ? "sidebar-wrapper--open" : ""}`}>
        <Sidebar activeView={activeView} onNavigate={handleNavigate} onClose={() => setMobileNavOpen(false)} />
      </div>
      <main className="main-shell">
        <Topbar
          onMenu={() => setMobileNavOpen(true)}
          onRefresh={handleRefresh}
          refreshing={refreshing}
          apiReachable={!presentationMode}
          onOpenIncidents={handleOpenIncidents}
        />

        <div className="content-wrap">
          <section className="page-heading">
            <div>
              <span className="eyebrow"><span className="eyebrow__line" /> Local control workspace</span>
              <h1>{activeView === "overview" ? "Good evening, Dibakar" : activeView === "incidents" ? "Incident log" : "Camera sources"}</h1>
              <p>
                {activeView === "overview" && "A calm view of what SHADE is observing across your workspace."}
                {activeView === "incidents" && "Review temporal observations and keep human judgment in the loop."}
                {activeView === "sources" && "Manage the sources that feed the local activity intelligence pipeline."}
              </p>
            </div>
            <div className="heading-meta">
              <div className="date-block"><Icon name="clock" size={15} /><span>{new Intl.DateTimeFormat("en-US", { weekday: "long", month: "short", day: "numeric", timeZone: "Asia/Calcutta" }).format(new Date())}</span></div>
              <span className="heading-meta__divider" />
              <span className="secure-label"><Icon name="shield" size={14} /> Local-only workspace</span>
            </div>
          </section>

          {error && (
            <div className="notice notice--info"><Icon name="info" size={17} /><span>{error}</span><button type="button" onClick={() => setError("")} aria-label="Dismiss notice"><Icon name="close" size={15} /></button></div>
          )}
          {notice && <div className="notice notice--success"><Icon name="check" size={17} /><span>{notice}</span></div>}

          {activeView === "overview" && (
            <>
              <section className="metric-grid" aria-label="Workspace summary">
                <MetricCard label="Active sources" value={activeCameraCount} detail={monitoringActive ? "One source is being monitored" : "Ready for local monitoring"} icon="camera" tone="mint" trend={activeCameraCount ? "Ready" : undefined} />
                <MetricCard label="Verified events" value={verifiedCount} detail="Temporal decisions in current view" icon="pulse" tone="violet" />
                <MetricCard label="Open attention" value={criticalCount} detail={criticalCount ? "Human review is recommended" : "No unresolved critical events"} icon="warning" tone={criticalCount ? "amber" : "blue"} />
                <MetricCard label="Signal confidence" value={`${averageConfidence || 0}%`} detail="Presentation aggregate, not a model score" icon="activity" tone="blue" />
              </section>

              <section className="overview-grid">
                <article className="panel panel--activity">
                  <div className="panel-heading">
                    <div><span className="panel-kicker">Distribution</span><h2>Activity mix</h2></div>
                    <button className="panel-menu" type="button" aria-label="Activity mix information"><Icon name="info" size={16} /></button>
                  </div>
                  <ActivityMix data={activityData} />
                  <div className="panel-footnote"><span className="status-dot status-dot--mint" /> Based on the observations currently available in this workspace</div>
                </article>

                <article className="panel panel--monitor">
                  <div className="panel-heading">
                    <div><span className="panel-kicker">Control plane</span><h2>Monitoring status</h2></div>
                    <span className={`status-badge ${monitoringActive ? "status-badge--live" : ""}`}><span className="status-dot" /> {monitoringActive ? "Armed" : "Idle"}</span>
                  </div>
                  <div className="monitor-visual">
                    <div className={`monitor-orb ${monitoringActive ? "monitor-orb--active" : ""}`}><Icon name="shield" size={30} /></div>
                    <div className="monitor-rings"><span /><span /><span /></div>
                    <div className="monitor-visual__copy"><strong>{monitoringActive ? "Observation is active" : "Ready to observe"}</strong><span>{monitoringActive ? `Listening to ${data.monitoring?.camera_id || "a camera source"}` : "Start a local monitoring session from a source below."}</span></div>
                  </div>
                  <div className="monitor-details">
                    <div><span>Mode</span><strong>{data.health?.runtime?.mode || "synthetic"}</strong></div>
                    <div><span>Persistence</span><strong>{data.health?.database?.available ? "MongoDB online" : "Degraded / inspectable"}</strong></div>
                    <div><span>Review</span><strong>Human review enabled</strong></div>
                  </div>
                </article>
              </section>

              <section className="panel panel--wide">
                <div className="panel-heading panel-heading--table">
                  <div><span className="panel-kicker">Recent signals</span><h2>Latest activity</h2></div>
                  <button className="text-button" type="button" onClick={handleOpenIncidents}>View incident log <Icon name="chevron" size={15} /></button>
                </div>
                <EventTable events={data.events} compact onViewAll={handleOpenIncidents} />
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
                <div><span className="panel-kicker">Human review queue</span><h2>All observed incidents</h2></div>
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

          <footer className="app-footer"><span>SHADE-ai · local activity intelligence</span><span><Icon name="shield" size={13} /> Safety aid · human review required</span><span>Last refreshed {formatRelativeTime(new Date().toISOString())}</span></footer>
        </div>
      </main>
    </div>
  );
}

export default App;
