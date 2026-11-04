import Icon from "./Icon";

export default function Topbar({ title = "Monitoring Overview", onMenu, menuButtonRef, menuOpen = false, initialLoading = false, onRefresh, refreshing, apiReachable, monitoringStatus = "unavailable" }) {
  const statusLabel = ({ STOPPED: "Stopped", STARTING: "Starting…", RUNNING: "Running", STOPPING: "Stopping…", FAILED: "Failed" })[monitoringStatus] || "Unavailable";
  return (
    <header className="topbar">
      <div className="topbar__mobile-menu">
        <button ref={menuButtonRef} className="icon-button" type="button" onClick={onMenu} aria-label="Open navigation" aria-expanded={menuOpen} aria-controls="primary-sidebar">
          <Icon name="menu" size={20} />
        </button>
      </div>
      <div className="topbar__context">
        <span className="topbar__context-line" />
        <strong>{title}</strong>
      </div>
      <div className="topbar__actions">
        <div className={`connection-pill ${apiReachable ? "connection-pill--live" : ""}`} role="status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          {initialLoading ? "Checking API" : apiReachable ? "API reachable" : "API unavailable"}
        </div>
        <div className={`monitoring-pill monitoring-pill--${monitoringStatus.toLowerCase()}`} role="status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          {initialLoading ? "Worker state checking" : `Worker ${statusLabel.toLowerCase()}`}
        </div>
        <button className="topbar-action" type="button" onClick={onRefresh} disabled={refreshing} aria-label="Refresh dashboard data" title="Refresh dashboard data">
          <Icon name="refresh" size={16} className={refreshing ? "spin" : ""} />
          <span>Refresh data</span>
        </button>
      </div>
    </header>
  );
}
