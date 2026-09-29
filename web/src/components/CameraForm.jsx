import Icon from "./Icon";

export default function CameraForm({ onCancel, onSubmit, submitting, error }) {
  const handleSubmit = (event) => {
    event.preventDefault();
    const formData = new FormData(event.currentTarget);
    onSubmit({
      name: String(formData.get("name") || "").trim(),
      source_type: String(formData.get("source_type") || "webcam"),
      source_uri: String(formData.get("source_uri") || "").trim(),
      location: String(formData.get("location") || "").trim(),
      enabled: true,
    });
  };

  return (
    <form className="camera-form" onSubmit={handleSubmit}>
      <div className="camera-form__heading">
        <div>
          <span className="panel-kicker">Camera setup</span>
          <h3>Add camera source</h3>
          <p>Register a camera configuration before starting a local monitoring session.</p>
        </div>
        <button className="icon-button" type="button" onClick={onCancel} aria-label="Close camera setup">
          <Icon name="close" size={18} />
        </button>
      </div>

      {error && <div className="form-error" role="alert"><Icon name="warning" size={15} /><span>{error}</span></div>}

      <div className="camera-form__fields">
        <label>
          <span>Camera name</span>
          <input name="name" type="text" placeholder="Front entry camera" required maxLength={120} autoFocus />
        </label>
        <label>
          <span>Source type</span>
          <select name="source_type" defaultValue="webcam">
            <option value="webcam">Webcam</option>
            <option value="rtsp">RTSP stream</option>
            <option value="video_file">Video file</option>
            <option value="synthetic">Synthetic demo source</option>
          </select>
        </label>
        <label>
          <span>Location <small>Optional</small></span>
          <input name="location" type="text" placeholder="Entryway" maxLength={180} />
        </label>
        <label className="camera-form__uri-field">
          <span>Source URI or file path <small>Required for RTSP and video files</small></span>
          <input name="source_uri" type="text" placeholder="rtsp://… or /path/to/video.mp4" maxLength={500} />
        </label>
      </div>

      <div className="camera-form__actions">
        <button className="button button--secondary" type="button" onClick={onCancel}>Cancel</button>
        <button className="button button--primary" type="submit" disabled={submitting}>
          <Icon name="add" size={15} />
          {submitting ? "Saving…" : "Add camera source"}
        </button>
      </div>
    </form>
  );
}
