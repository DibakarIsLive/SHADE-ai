import BrandMark from "./BrandMark";
import Icon from "./Icon";

const navigation = [
  { id: "overview", label: "Overview", icon: "dashboard" },
  { id: "incidents", label: "Incident log", icon: "warning", badge: "2" },
  { id: "sources", label: "Camera sources", icon: "camera" },
];

export default function Sidebar({ activeView, onNavigate, onClose }) {
  return (
    <aside className="sidebar">
      <div className="sidebar__topline" />
      <div className="sidebar__header">
        <BrandMark />
        <button className="icon-button sidebar__close" type="button" onClick={onClose} aria-label="Close navigation">
          <Icon name="close" size={18} />
        </button>
      </div>

      <div className="sidebar__section-label">Workspace</div>
      <nav className="sidebar__nav" aria-label="Primary navigation">
        {navigation.map((item) => (
          <button
            className={`nav-item ${activeView === item.id ? "nav-item--active" : ""}`}
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
          >
            <Icon name={item.icon} size={18} />
            <span>{item.label}</span>
            {item.badge && <em>{item.badge}</em>}
          </button>
        ))}
      </nav>

      <div className="sidebar__section-label sidebar__section-label--spaced">System</div>
      <div className="sidebar__system-card">
        <div className="system-card__orb"><Icon name="shield" size={18} /></div>
        <div>
          <strong>Safety mode</strong>
          <span>Human review enabled</span>
        </div>
        <span className="status-dot status-dot--mint" />
      </div>

      <div className="sidebar__footer">
        <div className="operator-avatar">D</div>
        <div className="operator-copy">
          <strong>Local operator</strong>
          <span>Control workspace</span>
        </div>
        <Icon name="chevron" size={16} className="muted-icon" />
      </div>
    </aside>
  );
}
