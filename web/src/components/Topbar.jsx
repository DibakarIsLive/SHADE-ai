import Icon from "./Icon";

export default function Topbar({ title = "Monitoring Overview", onMenu, menuButtonRef, menuOpen = false, initialLoading = false, onRefresh, refreshing, apiReachable, monitoringStatus = "unavailable" }) {
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
        <div className={`monitoring-pill ${monitoringStatus === "armed" ? "monitoring-pill--armed" : ""}`} role="status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          {initialLoading ? "Control state checking" : monitoringStatus === "armed" ? "Intent armed" : monitoringStatus === "idle" ? "Intent idle" : "Control state unavailable"}
        </div>
        <button className="topbar-action" type="button" onClick={onRefresh} disabled={refreshing} aria-label="Refresh dashboard data" title="Refresh dashboard data">
          <Icon name="refresh" size={16} className={refreshing ? "spin" : ""} />
          <span>Refresh data</span>
        </button>
      </div>
    </header>
  );
}
