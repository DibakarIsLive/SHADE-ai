import Icon from "./Icon";
import { formatDateTime, titleCase } from "../utils/formatters";

export default function CameraGrid({ cameras, activeCameraId, monitoringActive, onMonitor }) {
  if (!cameras.length) {
    return (
      <div className="empty-state empty-state--card">
        <span className="empty-state__icon"><Icon name="camera" size={20} /></span>
        <strong>No camera sources returned</strong>
        <span>Register a source through the API, or use the synthetic fixture while the backend is unavailable.</span>
      </div>
    );
  }

  return (
    <div className="camera-grid">
      {cameras.map((camera, index) => {
        const isSynthetic = camera.source_type === "synthetic";
        const isActive = monitoringActive && activeCameraId === camera.camera_id;
        const isDisabled = camera.enabled === false;
        const status = isActive ? "monitoring" : camera.status || (isDisabled ? "disabled" : "ready");
        const feedLabel = isSynthetic ? "DEMO" : isActive ? "ARMED" : "STANDBY";
        const sourceLabel = isSynthetic ? "PRESENTATION" : titleCase(camera.source_type || "camera");
        const timestampLabel = camera.updated_at ? `Updated ${formatDateTime(camera.updated_at)}` : "No frame timestamp";

        return (
          <article className={`camera-card camera-card--${status}`} key={camera.camera_id || camera.name}>
            <div className={`camera-feed camera-feed--${index % 3}`}>
              <div className="camera-feed__grid" aria-hidden="true" />
              <div className="camera-feed__scanline" aria-hidden="true" />
              <div className="camera-feed__hud camera-feed__hud--top">
                <span className={`feed-status ${isActive ? "feed-status--live" : ""}`}><span aria-hidden="true" />{feedLabel}</span>
                <span>{sourceLabel}</span>
              </div>
              <div className="camera-feed__silhouette" aria-hidden="true"><Icon name="user" size={42} strokeWidth={1.3} /></div>
              <span className="camera-feed__placeholder-label">Preview boundary</span>
              <div className="camera-feed__hud camera-feed__hud--bottom">
                <span>{camera.location || "Unspecified zone"}</span>
                <span>{timestampLabel}</span>
              </div>
            </div>
            <div className="camera-card__body">
              <div>
                <div className="camera-card__title"><strong>{camera.name || "Unnamed camera"}</strong><span className={`status-dot status-dot--${isActive ? "mint" : isDisabled ? "slate" : "mint"}`} aria-hidden="true" /></div>
                <span className="camera-card__meta">{camera.location || "No location"} · {sourceLabel} · {titleCase(status)}</span>
              </div>
              <button
                aria-pressed={isActive}
                className={`camera-card__action ${isActive ? "camera-card__action--active" : ""}`}
                type="button"
                onClick={() => onMonitor(camera)}
                disabled={isDisabled}
                aria-label={`${isDisabled ? "Disabled" : isActive ? "Clear monitoring intent for" : "Arm monitoring for"} ${camera.name || "camera source"}`}
              >
                <Icon name={isActive ? "stop" : "play"} size={13} />
                {isActive ? "Disarm" : isDisabled ? "Disabled" : "Arm"}
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
