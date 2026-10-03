import BrandMark from "./BrandMark";
import Icon from "./Icon";

const navigation = [
  { id: "overview", label: "Overview", icon: "dashboard" },
  { id: "incidents", label: "Event Log", icon: "warning" },
  { id: "sources", label: "Camera Sources", icon: "camera" },
];

export default function Sidebar({ sidebarRef, closeButtonRef, activeView, attentionCount = 0, collapsed = false, onNavigate, onClose, onToggle }) {
  return (
    <aside ref={sidebarRef} id="primary-sidebar" className={`sidebar ${collapsed ? "sidebar--collapsed" : ""}`}>
      <div className="sidebar__topline" />
      <div className="sidebar__header">
        <BrandMark />
        <button className="icon-button sidebar__collapse" type="button" onClick={onToggle} aria-label={collapsed ? "Expand navigation" : "Collapse navigation"} title={collapsed ? "Expand navigation" : "Collapse navigation"}>
          <Icon name={collapsed ? "chevron" : "menu"} size={18} />
        </button>
        <button ref={closeButtonRef} className="icon-button sidebar__close" type="button" onClick={onClose} aria-label="Close navigation">
          <Icon name="close" size={18} />
        </button>
      </div>

      <div className="sidebar__section-label">Monitoring</div>
      <nav className="sidebar__nav" aria-label="Primary navigation">
        {navigation.map((item) => (
          <button
            aria-current={activeView === item.id ? "page" : undefined}
            className={`nav-item ${activeView === item.id ? "nav-item--active" : ""}`}
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
            title={collapsed ? item.label : undefined}
          >
            <Icon name={item.icon} size={18} />
            <span>{item.label}</span>
            {item.id === "incidents" && attentionCount > 0 && (
              <em aria-label={`${attentionCount} event${attentionCount === 1 ? "" : "s"} need review`}>{attentionCount}</em>
            )}
          </button>
        ))}
      </nav>

      <div className="sidebar__section-label sidebar__section-label--spaced">Safety</div>
      <div className="sidebar__system-card" title={collapsed ? "Human review required" : undefined}>
        <div className="system-card__orb"><Icon name="shield" size={18} /></div>
        <div>
          <strong>Human review required</strong>
          <span>Safety assistance only</span>
        </div>
        <span className="status-dot status-dot--mint" aria-hidden="true" />
      </div>

      <div className="sidebar__footer" title={collapsed ? "Local operator group" : undefined}>
        <div className="operator-avatar" role="img" aria-label="Local operator group"><Icon name="users" size={15} /></div>
        <div className="operator-copy">
          <strong>Local operator group</strong>
          <span>Control workspace</span>
        </div>
        <Icon name="chevron" size={16} className="muted-icon" />
      </div>
    </aside>
  );
}
