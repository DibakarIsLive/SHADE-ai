import Icon from "./Icon";

export default function Topbar({ onMenu, onRefresh, refreshing, apiReachable, notificationCount = 0, onOpenIncidents }) {
  const notificationLabel = notificationCount
    ? `Open event log; ${notificationCount} event${notificationCount === 1 ? "" : "s"} need review`
    : "Open event log; no events need review";

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
        <div className={`connection-pill ${apiReachable ? "connection-pill--live" : "connection-pill--demo"}`} role="status" aria-live="polite">
          <span className="status-dot" aria-hidden="true" />
          {apiReachable ? "API reachable" : "Presentation state"}
        </div>
        <button className="topbar-action" type="button" onClick={onRefresh} disabled={refreshing} aria-label="Refresh workspace data">
          <Icon name="refresh" size={16} className={refreshing ? "spin" : ""} />
          <span>Refresh</span>
        </button>
        <button className="notification-button" type="button" onClick={onOpenIncidents} aria-label={notificationLabel} title={notificationLabel}>
          <Icon name="bell" size={18} />
          {notificationCount > 0 && <span className="notification-button__count">{notificationCount}</span>}
        </button>
        <div className="topbar__avatar" role="img" aria-label="Local operator group"><Icon name="users" size={15} /></div>
      </div>
    </header>
  );
}
