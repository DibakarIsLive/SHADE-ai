import Icon from "./Icon";

export default function Topbar({ title = "Monitoring Overview", onMenu, onRefresh, refreshing, apiReachable, monitoringActive }) {
  return (
    <header className="topbar">
      <div className="topbar__mobile-menu">
        <button className="icon-button" type="button" onClick={onMenu} aria-label="Open navigation">
          <Icon name="menu" size={20} />
        </button>
      </div>
      <div className="topbar__context">
        <span className="topbar__context-line" />
        <strong>{title}</strong>
      </div>
      <div className="topbar__actions">
        <div className={`connection-pill ${apiReachable ? "connection-pill--live" : "connection-pill--demo"}`} role="status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          {apiReachable ? "API connected" : "Demo data"}
        </div>
        <div className={`monitoring-pill ${monitoringActive ? "monitoring-pill--active" : ""}`} role="status">
          <span className="status-dot" aria-hidden="true" />
          {monitoringActive ? "Monitoring active" : "Monitoring idle"}
        </div>
        <button className="topbar-action" type="button" onClick={onRefresh} disabled={refreshing} aria-label="Refresh dashboard data" title="Refresh dashboard data">
          <Icon name="refresh" size={16} className={refreshing ? "spin" : ""} />
          <span>Refresh data</span>
        </button>
      </div>
    </header>
  );
}
