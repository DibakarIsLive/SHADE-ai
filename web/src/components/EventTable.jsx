import Icon from "./Icon";
import { clamp, formatClock, formatRelativeTime, titleCase } from "../utils/formatters";

const severityIcons = {
  critical: "warning",
  warning: "pulse",
  info: "check",
};

const statusLabels = {
  detected: "Potential · unverified",
  verified: "Verified record",
  acknowledged: "Acknowledged",
  resolved: "Resolved",
};

export default function EventTable({ events, synthetic = false, compact = false, onViewAll }) {
  const visibleEvents = compact ? events.slice(0, 4) : events;

  if (!visibleEvents.length) {
    return (
      <div className="empty-state empty-state--table">
        <span className="empty-state__icon"><Icon name="check" size={20} /></span>
        <strong>No events recorded yet</strong>
        <span>{synthetic ? "Synthetic event examples are not live records." : "Saved event records appear when returned by the backend. The standalone video-file worker uses development-null and cannot produce detections or events."}</span>
      </div>
    );
  }

  return (
    <div className="event-table-scroll" role="region" aria-label="Scrollable event records" tabIndex={0}>
      <div className="event-table" role="table" aria-label={synthetic ? "Synthetic demonstration event records" : "Saved event records"}>
        <div className="event-table__head" role="row">
          <div role="columnheader">Event</div>
          <div role="columnheader">Camera</div>
          <div role="columnheader">Event score</div>
          <div role="columnheader">State</div>
          <div role="columnheader">Time</div>
        </div>
      {visibleEvents.map((event) => {
        const severity = event.severity || "info";
        const confidence = clamp(event.confidence);
        const eventLabel = event.event_type || "Activity event";
        const eventStatus = event.status || "detected";
        const statusLabel = statusLabels[eventStatus] || titleCase(eventStatus);
        const activityLabel = event.context?.activity
          ? titleCase(event.context.activity)
          : "Activity record";
        const severityLabel = titleCase(severity);
        const confidenceLabel = `Event score ${Math.round(confidence * 100)} percent; not an accuracy measure`;

        return (
          <div className="event-row" role="row" key={event.event_id || `${event.event_type}-${event.occurred_at}`}>
            <div className="event-row__event" role="cell">
              <span className={`event-severity event-severity--${severity}`} role="img" aria-label={`Severity: ${severityLabel}; this does not confirm an emergency`}>
                <Icon name={severityIcons[severity] || "info"} aria-hidden="true" size={15} />
              </span>
              <div>
                <strong>{eventLabel}</strong>
                <span>Severity: {severityLabel} · {activityLabel}</span>
              </div>
            </div>
            <div className="event-row__source" role="cell">
              <Icon name="camera" size={14} aria-hidden="true" />
              <span>{event.context?.zone || event.camera_id || "Unassigned camera"}</span>
            </div>
            <div className="event-row__confidence" role="cell" title={confidenceLabel} aria-label={confidenceLabel}>
              <div className="confidence-bar" aria-hidden="true"><span style={{ width: `${confidence * 100}%` }} /></div>
              <strong>{Math.round(confidence * 100)}%</strong>
            </div>
            <div role="cell"><span className={`event-status event-status--${eventStatus}`} title={`${statusLabel}; an event record does not confirm an emergency`} aria-label={`Backend event state: ${statusLabel}; an event record does not confirm an emergency`}>{statusLabel}</span></div>
            <div className="event-row__time" role="cell">
              <strong>{formatClock(event.occurred_at)}</strong>
              <span>{formatRelativeTime(event.occurred_at)}</span>
            </div>
          </div>
        );
      })}
      </div>
      {compact && events.length > visibleEvents.length && (
        <button className="table-footer-action" type="button" onClick={onViewAll}>
          View all events <Icon name="chevron" size={15} />
        </button>
      )}
    </div>
  );
}
