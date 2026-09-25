import BrandMark from "./BrandMark";
import Icon from "./Icon";

const navigation = [
  { id: "overview", label: "Overview", icon: "dashboard" },
  { id: "incidents", label: "Event log", icon: "warning" },
  { id: "sources", label: "Camera sources", icon: "camera" },
];

export default function Sidebar({ activeView, attentionCount = 0, onNavigate, onClose }) {
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
            aria-current={activeView === item.id ? "page" : undefined}
            className={`nav-item ${activeView === item.id ? "nav-item--active" : ""}`}
            key={item.id}
            type="button"
            onClick={() => onNavigate(item.id)}
          >
            <Icon name={item.icon} size={18} />
            <span>{item.label}</span>
            {item.id === "incidents" && attentionCount > 0 && (
              <em aria-label={`${attentionCount} event${attentionCount === 1 ? "" : "s"} need review`}>{attentionCount}</em>
            )}
          </button>
        ))}
      </nav>

      <div className="sidebar__section-label sidebar__section-label--spaced">System</div>
      <div className="sidebar__system-card">
        <div className="system-card__orb"><Icon name="shield" size={18} /></div>
        <div>
          <strong>Safety boundary</strong>
          <span>Human review required</span>
        </div>
        <span className="status-dot status-dot--mint" aria-hidden="true" />
      </div>

      <div className="sidebar__footer">
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
