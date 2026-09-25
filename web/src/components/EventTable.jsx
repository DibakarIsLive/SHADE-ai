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
        <div>Event record</div>
        <div>Source</div>
        <div>Confidence</div>
        <div>State</div>
        <div>Time</div>
      </div>
      {visibleEvents.length ? visibleEvents.map((event) => {
        const severity = event.severity || "info";
        const confidence = clamp(event.confidence);
        const eventLabel = event.event_type || "Emergency event";
        const activityLabel = event.context?.activity
          ? titleCase(event.context.activity)
          : event.status === "verified" ? "Verified temporal decision" : "Temporal decision record";
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
              <span>{event.context?.zone || event.camera_id || "Unassigned source"}</span>
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
      }) : (
        <div className="empty-state empty-state--table">
          <span className="empty-state__icon"><Icon name="check" size={20} /></span>
          <strong>No event records yet</strong>
          <span>Temporal decisions will appear here when records are returned by the API.</span>
        </div>
      )}
      {compact && events.length > visibleEvents.length && (
        <button className="table-footer-action" type="button" onClick={onViewAll}>
          View all event records <Icon name="chevron" size={15} />
        </button>
      )}
    </div>
  );
}
