import Icon from "./Icon";
import { titleCase } from "../utils/formatters";

export default function CameraGrid({ cameras, activeCameraId, monitoringActive, onMonitor }) {
  if (!cameras.length) {
    return (
      <div className="empty-state empty-state--card">
        <span className="empty-state__icon"><Icon name="camera" size={20} /></span>
        <strong>No camera sources configured</strong>
        <span>Connect a camera source to begin observing activity.</span>
      </div>
    );
  }

  return (
    <div className="camera-grid">
      {cameras.map((camera, index) => {
        const isActive = monitoringActive && activeCameraId === camera.camera_id;
        const status = isActive ? "monitoring" : camera.status || (camera.enabled ? "ready" : "disabled");
        return (
          <article className={`camera-card camera-card--${status}`} key={camera.camera_id || camera.name}>
            <div className={`camera-feed camera-feed--${index % 3}`}>
              <div className="camera-feed__grid" />
              <div className="camera-feed__scanline" />
              <div className="camera-feed__hud camera-feed__hud--top">
                <span className={`feed-status ${isActive ? "feed-status--live" : ""}`}><span />{isActive ? "LIVE" : "STANDBY"}</span>
                <span className="feed-time">12:48:06</span>
              </div>
              <div className="camera-feed__silhouette"><Icon name="user" size={42} strokeWidth={1.3} /></div>
              <div className="camera-feed__hud camera-feed__hud--bottom">
                <span>{camera.location || "Unspecified zone"}</span>
                <span>{camera.source_type === "synthetic" ? "SIM" : "SOURCE"}</span>
              </div>
            </div>
            <div className="camera-card__body">
              <div>
                <div className="camera-card__title"><strong>{camera.name || "Unnamed camera"}</strong><span className={`status-dot status-dot--${isActive ? "mint" : "slate"}`} /></div>
                <span className="camera-card__meta">{camera.location || "No location"} · {titleCase(camera.source_type || "camera")}</span>
              </div>
              <button className={`camera-card__action ${isActive ? "camera-card__action--active" : ""}`} type="button" onClick={() => onMonitor(camera)}>
                <Icon name={isActive ? "stop" : "play"} size={13} />
                {isActive ? "Stop" : "Monitor"}
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
