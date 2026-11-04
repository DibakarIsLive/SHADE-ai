import Icon from "./Icon";
import { formatDateTime, titleCase } from "../utils/formatters";

export default function CameraGrid({
  cameras,
  activeCameraId,
  workerState = "STOPPED",
  controlsAvailable = true,
  canStart = false,
  canStop = false,
  controlPending = false,
  onMonitor,
  onConfigure,
}) {
  if (!cameras.length) {
    return (
      <div className="empty-state empty-state--card">
        <span className="empty-state__icon"><Icon name="camera" size={20} /></span>
        <strong>{controlsAvailable ? "No saved camera configurations" : "Camera records unavailable"}</strong>
        <span>{controlsAvailable ? "Save an enabled video-file camera configuration to start the supervised worker. The source must exist and open successfully; the configured inference provider must also initialize." : "Camera configurations could not be loaded from the backend."}</span>
        {controlsAvailable && onConfigure && <button className="button button--primary button--small" type="button" onClick={onConfigure}><Icon name="add" size={14} /> Add camera source</button>}
      </div>
    );
  }

  return (
    <div className="camera-grid">
      {cameras.map((camera, index) => {
        const isSynthetic = camera.source_type === "synthetic";
        const isActive = activeCameraId === camera.camera_id && ["STARTING", "RUNNING", "STOPPING"].includes(workerState);
        const isRunning = isActive && workerState === "RUNNING";
        const isFailed = activeCameraId === camera.camera_id && workerState === "FAILED";
        const anotherWorkerOwnsSlot = Boolean(activeCameraId && activeCameraId !== camera.camera_id && ["STARTING", "RUNNING", "STOPPING"].includes(workerState));
        const isDisabled = camera.enabled === false;
        const canStopThisCamera = isActive && canStop;
        const canStartThisCamera = canStart && !isDisabled && camera.source_type === "video_file";
        const canStartThisCard = canStartThisCamera && !anotherWorkerOwnsSlot;
        const cardState = isFailed ? "failed" : isRunning ? "running" : isActive ? workerState.toLowerCase() : isDisabled ? "disabled" : "configured";
        const stateLabel = isFailed ? "FAILED" : isRunning ? "RUNNING" : isActive ? workerState : isSynthetic ? "SYNTHETIC" : isDisabled ? "DISABLED" : "CONFIGURED";
        const stateDescription = isFailed ? "Worker failed" : isRunning ? "Worker is running" : isActive ? `Worker ${workerState.toLowerCase()}` : isDisabled ? "Disabled configuration" : camera.source_type === "video_file" ? "Saved configuration only" : "Not yet supported for worker control";
        const sourceLabel = isSynthetic ? "SYNTHETIC" : titleCase(camera.source_type || "camera");
        const timestampLabel = camera.updated_at ? `Updated ${formatDateTime(camera.updated_at)}` : "Configuration only";
        const buttonDisabled = !controlsAvailable || controlPending || (!canStopThisCamera && !canStartThisCard);
        const actionLabel = canStopThisCamera
          ? workerState === "STARTING" ? "Cancel startup" : "Stop worker"
          : canStartThisCard ? workerState === "FAILED" ? "Retry worker" : "Start worker"
            : anotherWorkerOwnsSlot ? "Worker slot in use" : isFailed ? "Worker failed" : isSynthetic ? "Demo only" : isDisabled ? "Disabled" : !controlsAvailable ? "Unavailable" : "Video file only";

        return (
          <article className={`camera-card camera-card--${cardState}`} key={camera.camera_id || camera.name}>
            <div className={`camera-feed camera-feed--${index % 3}`}>
              <div className="camera-feed__grid" aria-hidden="true" />
              <div className="camera-feed__scanline" aria-hidden="true" />
              <div className="camera-feed__hud camera-feed__hud--top">
                <span className={`feed-status feed-status--${cardState}`}><span aria-hidden="true" />{stateLabel}</span>
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
                <div className="camera-card__title"><strong>{camera.name || "Unnamed camera"}</strong><span className={`status-dot status-dot--${isRunning ? "mint" : isFailed ? "red" : isActive ? "amber" : "slate"}`} aria-hidden="true" /></div>
                <span className="camera-card__meta">{camera.location || "No location"} · {sourceLabel} · {stateDescription}</span>
              </div>
              <button
                aria-pressed={isRunning}
                className={`camera-card__action ${canStopThisCamera ? "camera-card__action--active" : ""}`}
                type="button"
                onClick={() => onMonitor(camera)}
                disabled={buttonDisabled}
                aria-label={`${canStopThisCamera ? "Stop monitoring on" : canStartThisCard ? "Start monitoring on" : anotherWorkerOwnsSlot ? "Worker slot in use; unavailable on" : isFailed ? "Worker failed for" : isSynthetic ? "Synthetic demo source; unavailable for" : isDisabled ? "Disabled" : camera.source_type !== "video_file" ? "Unsupported source for worker control on" : "Unavailable on"} ${camera.name || "camera"}`}
              >
                <Icon name={canStopThisCamera ? "stop" : isFailed && activeCameraId === camera.camera_id ? "warning" : "play"} size={13} />
                {controlPending ? "Working…" : actionLabel}
              </button>
            </div>
          </article>
        );
      })}
    </div>
  );
}
