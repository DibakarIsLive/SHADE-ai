import Icon from "./Icon";
import { formatDateTime, titleCase } from "../utils/formatters";

export default function CameraGrid({
  cameras,
  activeCameraId,
  monitoringActive,
  controlsAvailable = true,
  controlPending = false,
  onMonitor,
  onConfigure,
}) {
  if (!cameras.length) {
    return (
      <div className="empty-state empty-state--card">
        <span className="empty-state__icon"><Icon name="camera" size={20} /></span>
        <strong>{controlsAvailable ? "No camera sources configured" : "No connected camera sources"}</strong>
        <span>{controlsAvailable ? "SHADE-ai needs at least one camera source before monitoring can begin." : "Camera sources will appear after the backend and MongoDB are available."}</span>
        {controlsAvailable && onConfigure && <button className="button button--primary button--small" type="button" onClick={onConfigure}><Icon name="add" size={14} /> Add camera source</button>}
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
        const stateLabel = isSynthetic ? "DEMO MODE" : isActive ? "MONITORING" : "READY";
        const sourceLabel = isSynthetic ? "SYNTHETIC" : titleCase(camera.source_type || "camera");
        const timestampLabel = camera.updated_at ? `Updated ${formatDateTime(camera.updated_at)}` : "Configuration only";

        return (
          <article className={`camera-card camera-card--${status}`} key={camera.camera_id || camera.name}>
            <div className={`camera-feed camera-feed--${index % 3}`}>
              <div className="camera-feed__grid" aria-hidden="true" />
              <div className="camera-feed__scanline" aria-hidden="true" />
              <div className="camera-feed__hud camera-feed__hud--top">
                <span className={`feed-status ${isActive ? "feed-status--live" : ""}`}><span aria-hidden="true" />{stateLabel}</span>
                <span>{sourceLabel}</span>
              </div>
              <div className="camera-feed__silhouette" aria-hidden="true"><Icon name="camera" size={35} strokeWidth={1.3} /></div>
              <span className="camera-feed__placeholder-label">{isSynthetic ? "Synthetic sample" : "No live preview"}</span>
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
                disabled={isDisabled || !controlsAvailable || controlPending}
                aria-label={`${!controlsAvailable ? "Unavailable" : isDisabled ? "Disabled" : isActive ? "Stop monitoring" : "Start monitoring"} ${camera.name || "camera"}`}
              >
                <Icon name={isActive ? "stop" : "play"} size={13} />
                {!controlsAvailable ? "Unavailable" : isActive ? "Stop" : isDisabled ? "Disabled" : controlPending ? "Working" : "Start"}
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
