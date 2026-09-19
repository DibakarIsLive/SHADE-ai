import Icon from "./Icon";

export default function Topbar({ onMenu, onRefresh, refreshing, apiReachable, onOpenIncidents }) {
  return (
    <header className="topbar">
      <div className="topbar__mobile-menu">
        <button className="icon-button" type="button" onClick={onMenu} aria-label="Open navigation">
          <Icon name="menu" size={20} />
        </button>
      </div>
      <div className="breadcrumb">
        <span className="breadcrumb__root">Workspace</span>
        <Icon name="chevron" size={14} />
        <strong>Monitoring overview</strong>
      </div>
      <div className="topbar__actions">
        <div className={`connection-pill ${apiReachable ? "connection-pill--live" : "connection-pill--demo"}`}>
          <span className="status-dot" />
          {apiReachable ? "API connected" : "Presentation mode"}
        </div>
        <button className="topbar-action" type="button" onClick={onRefresh} disabled={refreshing}>
          <Icon name="refresh" size={16} className={refreshing ? "spin" : ""} />
          <span>Refresh</span>
        </button>
        <button className="notification-button" type="button" onClick={onOpenIncidents} aria-label="Open incident log">
          <Icon name="bell" size={18} />
          <span className="notification-button__dot" />
        </button>
        <div className="topbar__avatar">D</div>
      </div>
    </header>
  );
}
