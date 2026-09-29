import Icon from "./Icon";
import { clamp, formatClock, formatRelativeTime, titleCase } from "../utils/formatters";

const severityIcons = {
  critical: "warning",
  warning: "pulse",
  info: "check",
};

export default function EventTable({ events, compact = false, onViewAll, onConfigure }) {
  const visibleEvents = compact ? events.slice(0, 4) : events;

  if (!visibleEvents.length) {
    return (
      <div className="empty-state empty-state--table">
        <span className="empty-state__icon"><Icon name="check" size={20} /></span>
        <strong>No events recorded yet</strong>
        <span>Verified events will appear here after SHADE-ai records activity from a monitored camera.</span>
        {onConfigure && <button className="button button--secondary button--small" type="button" onClick={onConfigure}><Icon name="camera" size={14} /> Configure camera</button>}
      </div>
    );
  }

  return (
    <div className="event-table">
      <div className="event-table__head">
        <div>Event</div>
        <div>Camera</div>
        <div>Event score</div>
        <div>State</div>
        <div>Time</div>
      </div>
      {visibleEvents.map((event) => {
        const severity = event.severity || "info";
        const confidence = clamp(event.confidence);
        const eventLabel = event.event_type || "Activity event";
        const activityLabel = event.context?.activity
          ? titleCase(event.context.activity)
          : event.status === "verified" ? "Confirmed after contextual analysis" : "Activity record";
        const confidenceLabel = `Event score ${Math.round(confidence * 100)} percent; not an accuracy measure`;

        return (
          <div className="event-row" key={event.event_id || `${event.event_type}-${event.occurred_at}`}>
            <div className="event-row__event">
              <span className={`event-severity event-severity--${severity}`} aria-hidden="true">
                <Icon name={severityIcons[severity] || "info"} size={15} />
              </span>
              <div>
                <strong>{eventLabel}</strong>
                <span>{activityLabel}</span>
              </div>
            </div>
            <div className="event-row__source">
              <Icon name="camera" size={14} />
              <span>{event.context?.zone || event.camera_id || "Unassigned camera"}</span>
            </div>
            <div className="event-row__confidence" title={confidenceLabel} aria-label={confidenceLabel}>
              <div className="confidence-bar" aria-hidden="true"><span style={{ width: `${confidence * 100}%` }} /></div>
              <strong>{Math.round(confidence * 100)}%</strong>
            </div>
            <div><span className={`event-status event-status--${event.status || "detected"}`}>{titleCase(event.status || "detected")}</span></div>
            <div className="event-row__time">
              <strong>{formatClock(event.occurred_at)}</strong>
              <span>{formatRelativeTime(event.occurred_at)}</span>
            </div>
          </div>
        );
      })}
      {compact && events.length > visibleEvents.length && (
        <button className="table-footer-action" type="button" onClick={onViewAll}>
          View all events <Icon name="chevron" size={15} />
        </button>
      )}
    </div>
  );
}
