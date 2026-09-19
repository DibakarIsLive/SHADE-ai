import Icon from "./Icon";
import { clamp, formatClock, formatRelativeTime, titleCase } from "../utils/formatters";

const severityIcons = {
  critical: "warning",
  warning: "pulse",
  info: "check",
};

export default function EventTable({ events, compact = false, onViewAll }) {
  const visibleEvents = compact ? events.slice(0, 4) : events;

  return (
    <div className="event-table">
      <div className="event-table__head">
        <div>Event</div>
        <div>Source</div>
        <div>Confidence</div>
        <div>State</div>
        <div>Time</div>
      </div>
      {visibleEvents.length ? visibleEvents.map((event) => {
        const severity = event.severity || "info";
        const confidence = clamp(event.confidence);
        return (
          <div className="event-row" key={event.event_id || `${event.event_type}-${event.occurred_at}`}>
            <div className="event-row__event">
              <span className={`event-severity event-severity--${severity}`}>
                <Icon name={severityIcons[severity] || "info"} size={15} />
              </span>
              <div>
                <strong>{event.event_type || "Activity event"}</strong>
                <span>{event.context?.activity ? titleCase(event.context.activity) : "Temporal observation"}</span>
              </div>
            </div>
            <div className="event-row__source">
              <Icon name="camera" size={14} />
              <span>{event.context?.zone || event.camera_id || "Unassigned source"}</span>
            </div>
            <div className="event-row__confidence">
              <div className="confidence-bar"><span style={{ width: `${confidence * 100}%` }} /></div>
              <strong>{Math.round(confidence * 100)}%</strong>
            </div>
            <div><span className={`event-status event-status--${event.status || "detected"}`}>{titleCase(event.status || "detected")}</span></div>
            <div className="event-row__time">
              <strong>{formatClock(event.occurred_at)}</strong>
              <span>{formatRelativeTime(event.occurred_at)}</span>
            </div>
          </div>
        );
      }) : (
        <div className="empty-state empty-state--table">
          <span className="empty-state__icon"><Icon name="check" size={20} /></span>
          <strong>No activity events yet</strong>
          <span>Verified observations will appear here when the monitor is running.</span>
        </div>
      )}
      {compact && events.length > visibleEvents.length && (
        <button className="table-footer-action" type="button" onClick={onViewAll}>
          View all incidents <Icon name="chevron" size={15} />
        </button>
      )}
    </div>
  );
}
